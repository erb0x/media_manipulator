"""
Safe file operation executor.
Handles move, rename, and copy-delete operations with hash verification.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from enum import Enum

from app.db.database import get_db
from app.utils.hashing import compute_sha256 as compute_file_hash


class OperationResult(str, Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class ExecutionResult:
    """Result of executing a single operation."""
    operation_id: str
    result: OperationResult
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "operation_id": self.operation_id,
            "result": self.result.value,
            "error_message": self.error_message,
        }


def verify_file(file_path: Path, expected_hash: str) -> tuple[bool, str]:
    """
    Verify a file exists and matches expected hash.
    
    Returns:
        (success, error_message)
    """
    if not file_path.exists():
        return False, f"File does not exist: {file_path}"
    
    if not file_path.is_file():
        return False, f"Path is not a file: {file_path}"
    
    if expected_hash:
        actual_hash = compute_file_hash(file_path)
        if actual_hash != expected_hash:
            return False, f"Hash mismatch: expected {expected_hash[:16]}..., got {actual_hash[:16]}..."
    
    return True, ""


def safe_move(source_path: Path, target_path: Path) -> tuple[bool, str]:
    """
    Safely move a file within the same volume.
    Uses os.rename for atomic operation.
    
    Returns:
        (success, error_message)
    """
    try:
        # Create target directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if target exists
        if target_path.exists():
            return False, f"Target already exists: {target_path}"
        
        # Atomic rename/move
        os.rename(source_path, target_path)
        
        return True, ""
    
    except OSError as e:
        return False, f"Move failed: {str(e)}"


def safe_copy_delete(
    source_path: Path, 
    target_path: Path, 
    expected_hash: str
) -> tuple[bool, str]:
    """
    Safely copy a file across volumes, then delete original after verification.
    
    Steps:
    1. Copy file to target
    2. Verify target hash matches
    3. Delete original
    
    Returns:
        (success, error_message)
    """
    try:
        # Create target directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if target exists
        if target_path.exists():
            return False, f"Target already exists: {target_path}"
        
        # Copy file with metadata
        shutil.copy2(source_path, target_path)
        
        # Verify copy
        if expected_hash:
            target_hash = compute_file_hash(target_path)
            if target_hash != expected_hash:
                # Delete bad copy
                target_path.unlink()
                return False, f"Copy verification failed: hash mismatch"
        
        # Delete original
        source_path.unlink()
        
        return True, ""
    
    except Exception as e:
        # Try to clean up failed copy
        try:
            if target_path.exists():
                target_path.unlink()
        except:
            pass
        
        return False, f"Copy-delete failed: {str(e)}"


async def execute_operation(
    operation_id: str,
    operation_type: str,
    source_path: str,
    target_path: str,
    file_hash: Optional[str],
    plan_id: str,
) -> ExecutionResult:
    """
    Execute a single file operation.
    
    Args:
        operation_id: ID of the operation
        operation_type: Type of operation (move, rename, copy_delete)
        source_path: Source file path
        target_path: Target file path
        file_hash: Expected file hash for verification
        plan_id: ID of the parent plan
    
    Returns:
        ExecutionResult with status
    """
    source = Path(source_path)
    target = Path(target_path)
    
    # Verify source file
    valid, error = verify_file(source, file_hash)
    if not valid:
        await log_operation(plan_id, operation_id, "verify", source_path, None, "failed", error)
        return ExecutionResult(
            operation_id=operation_id,
            result=OperationResult.FAILED,
            error_message=error,
        )
    
    # Execute based on type
    success = False
    error_message = ""
    
    if operation_type in ["move", "rename"]:
        success, error_message = safe_move(source, target)
    elif operation_type == "copy_delete":
        success, error_message = safe_copy_delete(source, target, file_hash)
    else:
        error_message = f"Unknown operation type: {operation_type}"
    
    # Log result
    result = OperationResult.SUCCESS if success else OperationResult.FAILED
    await log_operation(
        plan_id, operation_id, operation_type,
        source_path, target_path,
        "success" if success else "failed",
        error_message if not success else None
    )
    
    # Update operation status in database
    async with get_db() as db:
        await db.execute(
            """
            UPDATE planned_operations
            SET status = ?, executed_at = datetime('now'), error_message = ?
            WHERE id = ?
            """,
            ("completed" if success else "failed", error_message or None, operation_id)
        )
        await db.commit()
    
    return ExecutionResult(
        operation_id=operation_id,
        result=result,
        error_message=error_message if not success else None,
    )


async def execute_plan(plan_id: str) -> list[ExecutionResult]:
    """
    Execute all operations in a plan.
    
    Operations are executed in order.
    Fails fast on critical errors.
    
    Returns:
        List of ExecutionResults
    """
    results = []
    
    async with get_db() as db:
        # Update plan status to applying
        await db.execute(
            "UPDATE plans SET status = 'applying' WHERE id = ?",
            (plan_id,)
        )
        await db.commit()
        
        # Get operations in order
        cursor = await db.execute(
            """
            SELECT id, operation_type, source_path, target_path, file_hash
            FROM planned_operations
            WHERE plan_id = ? AND status = 'pending'
            ORDER BY execution_order
            """,
            (plan_id,)
        )
        operations = await cursor.fetchall()
    
    completed = 0
    failed = 0
    
    for op in operations:
        result = await execute_operation(
            operation_id=op["id"],
            operation_type=op["operation_type"],
            source_path=op["source_path"],
            target_path=op["target_path"],
            file_hash=op["file_hash"],
            plan_id=plan_id,
        )
        
        results.append(result)
        
        if result.result == OperationResult.SUCCESS:
            completed += 1
        else:
            failed += 1
    
    # Update plan status
    async with get_db() as db:
        if failed > 0:
            status = "failed"
        else:
            status = "completed"
        
        await db.execute(
            """
            UPDATE plans 
            SET status = ?, applied_at = datetime('now'), completed_count = ?
            WHERE id = ?
            """,
            (status, completed, plan_id)
        )
        
        # Update file statuses for successful operations
        await db.execute(
            """
            UPDATE media_files 
            SET status = 'applied', updated_at = datetime('now')
            WHERE id IN (
                SELECT media_file_id FROM planned_operations
                WHERE plan_id = ? AND status = 'completed' AND media_file_id IS NOT NULL
            )
            """,
            (plan_id,)
        )
        
        # Update group statuses
        await db.execute(
            """
            UPDATE audiobook_groups 
            SET status = 'applied', updated_at = datetime('now')
            WHERE id IN (
                SELECT DISTINCT group_id FROM planned_operations
                WHERE plan_id = ? AND status = 'completed' AND group_id IS NOT NULL
            )
            """,
            (plan_id,)
        )
        
        await db.commit()
    
    return results


async def log_operation(
    plan_id: str,
    operation_id: str,
    action: str,
    source_path: Optional[str],
    target_path: Optional[str],
    result: str,
    error_message: Optional[str],
) -> None:
    """Log an operation to the audit log."""
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO audit_log (
                plan_id, operation_id, action,
                source_path, target_path, result, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (plan_id, operation_id, action, source_path, target_path, result, error_message)
        )
        await db.commit()
