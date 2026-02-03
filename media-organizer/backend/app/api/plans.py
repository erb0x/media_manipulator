"""
Plans API endpoints for the Media Organizer.
Handles plan creation, viewing, execution, and rollback.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
from typing import Optional

from app.db.models import (
    PlanResponse,
    PlanListResponse,
    PlannedOperationResponse,
    PlanCreateRequest,
    PlanStatus,
    OperationType,
    OperationStatus,
)
from app.db.database import get_db
from app.ops.planner import generate_plan, save_plan
from app.ops.executor import execute_plan
from app.ops.rollback import rollback_plan


router = APIRouter(prefix="/plans", tags=["plans"])


def row_to_plan_response(row, operations: list = None) -> PlanResponse:
    """Convert a database row to PlanResponse."""
    return PlanResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        status=PlanStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        applied_at=datetime.fromisoformat(row["applied_at"]) if row["applied_at"] else None,
        rolled_back_at=datetime.fromisoformat(row["rolled_back_at"]) if row["rolled_back_at"] else None,
        item_count=row["item_count"] or 0,
        completed_count=row["completed_count"] or 0,
        error_message=row["error_message"],
        operations=operations or [],
    )


def row_to_operation_response(row) -> PlannedOperationResponse:
    """Convert a database row to PlannedOperationResponse."""
    return PlannedOperationResponse(
        id=row["id"],
        operation_type=OperationType(row["operation_type"]),
        source_path=row["source_path"],
        target_path=row["target_path"],
        status=OperationStatus(row["status"]),
        executed_at=datetime.fromisoformat(row["executed_at"]) if row["executed_at"] else None,
        error_message=row["error_message"],
    )


@router.get("", response_model=PlanListResponse)
async def list_plans(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
) -> PlanListResponse:
    """List all plans with optional filtering."""
    offset = (page - 1) * page_size
    
    conditions = []
    params = []
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    async with get_db() as db:
        # Get total count
        cursor = await db.execute(
            f"SELECT COUNT(*) FROM plans {where_clause}",
            params
        )
        total = (await cursor.fetchone())[0]
        
        # Get plans
        cursor = await db.execute(
            f"""
            SELECT * FROM plans
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()
    
    items = [row_to_plan_response(row) for row in rows]
    
    return PlanListResponse(
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(items)) < total,
        items=items,
    )


@router.post("/generate", response_model=PlanResponse)
async def create_plan(request: PlanCreateRequest) -> PlanResponse:
    """
    Generate a new plan from approved files and groups.
    The plan is saved and can be applied later.
    """
    # Generate the plan
    plan = await generate_plan(
        name=request.name,
        description=request.description,
        file_ids=request.file_ids,
        group_ids=request.group_ids,
        include_all_approved=request.include_all_approved,
    )
    
    if not plan.operations:
        raise HTTPException(
            status_code=400,
            detail="No approved items to include in plan"
        )
    
    # Save to database
    await save_plan(plan)
    
    # Return plan details
    operations = [
        PlannedOperationResponse(
            id=op.id,
            operation_type=OperationType(op.operation_type),
            source_path=op.source_path,
            target_path=op.target_path,
            status=OperationStatus.PENDING,
        )
        for op in plan.operations
    ]
    
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        status=PlanStatus.READY,
        created_at=plan.created_at,
        item_count=plan.item_count,
        operations=operations,
    )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str) -> PlanResponse:
    """Get a plan with all its operations."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM plans WHERE id = ?",
            (plan_id,)
        )
        plan_row = await cursor.fetchone()
        
        if not plan_row:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        cursor = await db.execute(
            """
            SELECT * FROM planned_operations
            WHERE plan_id = ?
            ORDER BY execution_order
            """,
            (plan_id,)
        )
        op_rows = await cursor.fetchall()
    
    operations = [row_to_operation_response(row) for row in op_rows]
    
    return row_to_plan_response(plan_row, operations)


@router.post("/{plan_id}/apply")
async def apply_plan(
    plan_id: str,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Apply a plan to execute all its operations.
    Runs in the background and updates status.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT status FROM plans WHERE id = ?",
            (plan_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        if row["status"] != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Plan cannot be applied (status: {row['status']})"
            )
    
    # Run in background
    background_tasks.add_task(execute_plan, plan_id)
    
    return {
        "message": "Plan execution started",
        "plan_id": plan_id,
    }


@router.post("/{plan_id}/rollback")
async def rollback_plan_endpoint(plan_id: str) -> dict:
    """
    Rollback a completed or failed plan.
    Reverses all successful operations.
    """
    result = await rollback_plan(plan_id)
    
    if not result.success and result.error_message:
        raise HTTPException(status_code=400, detail=result.error_message)
    
    return {
        "message": "Rollback completed",
        "plan_id": plan_id,
        "operations_rolled_back": result.operations_rolled_back,
        "operations_failed": result.operations_failed,
        "conflicts": result.conflicts,
    }


@router.delete("/{plan_id}")
async def delete_plan(plan_id: str) -> dict:
    """Delete a plan (only if not applied)."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT status FROM plans WHERE id = ?",
            (plan_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        if row["status"] in ["completed", "applying"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete an applied or running plan"
            )
        
        await db.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        await db.commit()
    
    return {"message": "Plan deleted", "plan_id": plan_id}


@router.get("/{plan_id}/preview")
async def preview_plan(plan_id: str) -> dict:
    """
    Get a preview of plan operations with statistics.
    Useful for showing a summary before applying.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM plans WHERE id = ?",
            (plan_id,)
        )
        plan_row = await cursor.fetchone()
        
        if not plan_row:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Get operation stats
        cursor = await db.execute(
            """
            SELECT operation_type, COUNT(*) as count
            FROM planned_operations
            WHERE plan_id = ?
            GROUP BY operation_type
            """,
            (plan_id,)
        )
        type_counts = {row["operation_type"]: row["count"] for row in await cursor.fetchall()}
        
        # Get sample operations
        cursor = await db.execute(
            """
            SELECT source_path, target_path
            FROM planned_operations
            WHERE plan_id = ?
            ORDER BY execution_order
            LIMIT 10
            """,
            (plan_id,)
        )
        sample_ops = [
            {"from": row["source_path"], "to": row["target_path"]}
            for row in await cursor.fetchall()
        ]
    
    return {
        "plan_id": plan_id,
        "name": plan_row["name"],
        "status": plan_row["status"],
        "total_operations": plan_row["item_count"],
        "operation_types": type_counts,
        "sample_operations": sample_ops,
    }
