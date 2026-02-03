"""
Rollback functionality for reversing applied plans.
Restores files to their original locations.
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.ops.executor import (
    safe_move,
    safe_copy_delete,
    compute_file_hash,
    log_operation,
    ExecutionResult,
    OperationResult,
)


@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    plan_id: str
    success: bool
    operations_rolled_back: int
    operations_failed: int
    conflicts: list[str]
    error_message: Optional[str] = None


async def rollback_operation(
    operation_id: str,
    operation_type: str,
    source_path: str,  # Original source (now target of rollback)
    target_path: str,  # Original target (now source of rollback)
    file_hash: Optional[str],
    plan_id: str,
) -> ExecutionResult:
    """
    Rollback a single operation by reversing it.
    
    The original target becomes the source,
    and the original source becomes the target.
    """
    # Swap paths for rollback
    rollback_source = Path(target_path)  # File is now here
    rollback_target = Path(source_path)  # Move it back here
    
    # Check if source exists for rollback
    if not rollback_source.exists():
        error = f"Cannot rollback: file not found at {rollback_source}"
        await log_operation(plan_id, operation_id, "rollback", str(rollback_source), str(rollback_target), "failed", error)
        return ExecutionResult(
            operation_id=operation_id,
            result=OperationResult.FAILED,
            error_message=error,
        )
    
    # Check if target already exists (conflict)
    if rollback_target.exists():
        error = f"Cannot rollback: original location occupied at {rollback_target}"
        await log_operation(plan_id, operation_id, "rollback", str(rollback_source), str(rollback_target), "failed", error)
        return ExecutionResult(
            operation_id=operation_id,
            result=OperationResult.FAILED,
            error_message=error,
        )
    
    # Perform rollback
    success = False
    error_message = ""
    
    if operation_type in ["move", "rename"]:
        success, error_message = safe_move(rollback_source, rollback_target)
    elif operation_type == "copy_delete":
        # For rollback, we copy from target back to source and delete target
        current_hash = compute_file_hash(rollback_source)
        success, error_message = safe_copy_delete(rollback_source, rollback_target, current_hash)
    else:
        error_message = f"Unknown operation type: {operation_type}"
    
    # Log result
    await log_operation(
        plan_id, operation_id, "rollback",
        str(rollback_source), str(rollback_target),
        "success" if success else "failed",
        error_message if not success else None
    )
    
    # Update operation status
    async with get_db() as db:
        await db.execute(
            """
            UPDATE planned_operations
            SET status = ?, error_message = ?
            WHERE id = ?
            """,
            ("rolled_back" if success else "failed", error_message or None, operation_id)
        )
        await db.commit()
    
    return ExecutionResult(
        operation_id=operation_id,
        result=OperationResult.SUCCESS if success else OperationResult.FAILED,
        error_message=error_message if not success else None,
    )


async def rollback_plan(plan_id: str) -> RollbackResult:
    """
    Rollback all completed operations in a plan.
    
    Operations are rolled back in reverse order.
    Conflicts are tracked but don't stop the rollback.
    """
    async with get_db() as db:
        # Check plan exists and was applied
        cursor = await db.execute(
            "SELECT status FROM plans WHERE id = ?",
            (plan_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return RollbackResult(
                plan_id=plan_id,
                success=False,
                operations_rolled_back=0,
                operations_failed=0,
                conflicts=[],
                error_message="Plan not found",
            )
        
        if row["status"] not in ["completed", "failed"]:
            return RollbackResult(
                plan_id=plan_id,
                success=False,
                operations_rolled_back=0,
                operations_failed=0,
                conflicts=[],
                error_message=f"Plan cannot be rolled back (status: {row['status']})",
            )
        
        # Get completed operations in reverse order
        cursor = await db.execute(
            """
            SELECT id, operation_type, source_path, target_path, file_hash
            FROM planned_operations
            WHERE plan_id = ? AND status = 'completed'
            ORDER BY execution_order DESC
            """,
            (plan_id,)
        )
        operations = await cursor.fetchall()
    
    rolled_back = 0
    failed = 0
    conflicts = []
    
    for op in operations:
        result = await rollback_operation(
            operation_id=op["id"],
            operation_type=op["operation_type"],
            source_path=op["source_path"],
            target_path=op["target_path"],
            file_hash=op["file_hash"],
            plan_id=plan_id,
        )
        
        if result.result == OperationResult.SUCCESS:
            rolled_back += 1
        else:
            failed += 1
            if "occupied" in (result.error_message or ""):
                conflicts.append(result.error_message)
    
    # Update plan status
    async with get_db() as db:
        await db.execute(
            """
            UPDATE plans 
            SET status = 'rolled_back', rolled_back_at = datetime('now')
            WHERE id = ?
            """,
            (plan_id,)
        )
        
        # Reset file statuses back to approved
        await db.execute(
            """
            UPDATE media_files 
            SET status = 'approved', updated_at = datetime('now')
            WHERE id IN (
                SELECT media_file_id FROM planned_operations
                WHERE plan_id = ? AND status = 'rolled_back' AND media_file_id IS NOT NULL
            )
            """,
            (plan_id,)
        )
        
        # Reset group statuses
        await db.execute(
            """
            UPDATE audiobook_groups 
            SET status = 'approved', updated_at = datetime('now')
            WHERE id IN (
                SELECT DISTINCT group_id FROM planned_operations
                WHERE plan_id = ? AND status = 'rolled_back' AND group_id IS NOT NULL
            )
            """,
            (plan_id,)
        )
        
        await db.commit()
    
    return RollbackResult(
        plan_id=plan_id,
        success=(failed == 0),
        operations_rolled_back=rolled_back,
        operations_failed=failed,
        conflicts=conflicts,
    )
