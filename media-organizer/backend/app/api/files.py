"""
Files API endpoints for the Media Organizer.
Handles listing, viewing, and updating media files and audiobook groups.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional

from app.db.models import (
    MediaFileResponse,
    MediaFileListResponse,
    AudiobookGroupResponse,
    AudiobookGroupListResponse,
    FileUpdateRequest,
    GroupUpdateRequest,
    FileStatus,
    MediaType,
    DashboardStats,
)
from app.db.database import get_db


router = APIRouter(prefix="/files", tags=["files"])


def row_to_file_response(row) -> MediaFileResponse:
    """Convert a database row to MediaFileResponse."""
    return MediaFileResponse(
        id=row["id"],
        file_path=row["file_path"],
        file_hash=row["file_hash"],
        file_size=row["file_size"],
        media_type=MediaType(row["media_type"]) if row["media_type"] in ["audiobook", "ebook", "comic"] else MediaType.AUDIOBOOK,
        group_id=row["group_id"],
        is_group_primary=bool(row["is_group_primary"]),
        track_number=row["track_number"],
        extracted_title=row["extracted_title"],
        extracted_author=row["extracted_author"],
        extracted_narrator=row["extracted_narrator"],
        extracted_series=row["extracted_series"],
        extracted_series_index=row["extracted_series_index"],
        extracted_year=row["extracted_year"],
        duration_seconds=row["duration_seconds"],
        final_title=row["final_title"],
        final_author=row["final_author"],
        final_narrator=row["final_narrator"],
        final_series=row["final_series"],
        final_series_index=row["final_series_index"],
        final_year=row["final_year"],
        status=FileStatus(row["status"]),
        confidence=row["confidence"] or 0.0,
        proposed_path=row["proposed_path"],
        provider_match_source=row["provider_match_source"],
        provider_match_id=row["provider_match_id"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
    )


def row_to_group_response(row, files: list = None) -> AudiobookGroupResponse:
    """Convert a database row to AudiobookGroupResponse."""
    return AudiobookGroupResponse(
        id=row["id"],
        folder_path=row["folder_path"],
        file_count=row["file_count"] or 0,
        total_duration_seconds=row["total_duration_seconds"] or 0,
        title=row["title"],
        author=row["author"],
        narrator=row["narrator"],
        series=row["series"],
        series_index=row["series_index"],
        year=row["year"],
        final_title=row["final_title"],
        final_author=row["final_author"],
        final_narrator=row["final_narrator"],
        final_series=row["final_series"],
        final_series_index=row["final_series_index"],
        final_year=row["final_year"],
        status=FileStatus(row["status"]),
        confidence=row["confidence"] or 0.0,
        proposed_path=row["proposed_path"],
        files=files or [],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
    )


@router.get("", response_model=MediaFileListResponse)
async def list_files(
    page: int = 1,
    page_size: int = 50,
    media_type: Optional[str] = Query(None, description="Filter by media type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    group_id: Optional[str] = Query(None, description="Filter by group ID"),
    ungrouped: bool = Query(False, description="Only show ungrouped files"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence threshold"),
) -> MediaFileListResponse:
    """List media files with filtering and pagination."""
    offset = (page - 1) * page_size
    
    # Build query
    conditions = []
    params = []
    
    if media_type:
        conditions.append("media_type = ?")
        params.append(media_type)
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    if group_id:
        conditions.append("group_id = ?")
        params.append(group_id)
    
    if ungrouped:
        conditions.append("group_id IS NULL")
    
    if min_confidence is not None:
        conditions.append("confidence >= ?")
        params.append(min_confidence)
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    async with get_db() as db:
        # Get total count
        cursor = await db.execute(
            f"SELECT COUNT(*) FROM media_files {where_clause}",
            params
        )
        total = (await cursor.fetchone())[0]
        
        # Get files
        cursor = await db.execute(
            f"""
            SELECT * FROM media_files
            {where_clause}
            ORDER BY 
                CASE WHEN is_group_primary THEN 0 ELSE 1 END,
                file_path
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()
    
    items = [row_to_file_response(row) for row in rows]
    
    return MediaFileListResponse(
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(items)) < total,
        items=items,
    )


@router.get("/groups", response_model=AudiobookGroupListResponse)
async def list_groups(
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = Query(None, description="Filter by status"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence threshold"),
) -> AudiobookGroupListResponse:
    """List audiobook groups with filtering and pagination."""
    offset = (page - 1) * page_size
    
    # Build query
    conditions = []
    params = []
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    if min_confidence is not None:
        conditions.append("confidence >= ?")
        params.append(min_confidence)
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    async with get_db() as db:
        # Get total count
        cursor = await db.execute(
            f"SELECT COUNT(*) FROM audiobook_groups {where_clause}",
            params
        )
        total = (await cursor.fetchone())[0]
        
        # Get groups
        cursor = await db.execute(
            f"""
            SELECT * FROM audiobook_groups
            {where_clause}
            ORDER BY folder_path
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()
    
    items = [row_to_group_response(row) for row in rows]
    
    return AudiobookGroupListResponse(
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(items)) < total,
        items=items,
    )


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats() -> DashboardStats:
    """Get dashboard statistics."""
    async with get_db() as db:
        # File counts
        cursor = await db.execute("SELECT COUNT(*) FROM media_files")
        total_files = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM audiobook_groups")
        total_groups = (await cursor.fetchone())[0]
        
        # Status counts
        cursor = await db.execute(
            "SELECT status, COUNT(*) FROM media_files GROUP BY status"
        )
        status_counts = {row[0]: row[1] for row in await cursor.fetchall()}
        
        # Duration and size
        cursor = await db.execute(
            "SELECT COALESCE(SUM(duration_seconds), 0), COALESCE(SUM(file_size), 0) FROM media_files"
        )
        row = await cursor.fetchone()
        total_duration = row[0]
        total_size = row[1]
        
        # Recent scans
        cursor = await db.execute(
            """
            SELECT id, root_path, status, started_at, completed_at,
                   files_found, groups_created, error_message
            FROM scans ORDER BY created_at DESC LIMIT 5
            """
        )
        scan_rows = await cursor.fetchall()
        
        # Recent plans
        cursor = await db.execute(
            """
            SELECT id, name, description, status, created_at, applied_at,
                   rolled_back_at, item_count, completed_count, error_message
            FROM plans ORDER BY created_at DESC LIMIT 5
            """
        )
        plan_rows = await cursor.fetchall()
    
    from app.db.models import ScanResponse, PlanResponse, ScanStatus, PlanStatus
    
    recent_scans = [
        ScanResponse(
            id=row["id"],
            root_path=row["root_path"],
            status=ScanStatus(row["status"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            files_found=row["files_found"] or 0,
            groups_created=row["groups_created"] or 0,
            error_message=row["error_message"],
        )
        for row in scan_rows
    ]
    
    recent_plans = [
        PlanResponse(
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
        )
        for row in plan_rows
    ]
    
    return DashboardStats(
        total_files=total_files,
        total_groups=total_groups,
        pending_count=status_counts.get("pending", 0),
        reviewed_count=status_counts.get("reviewed", 0),
        approved_count=status_counts.get("approved", 0),
        applied_count=status_counts.get("applied", 0),
        total_duration_hours=total_duration / 3600 if total_duration else 0.0,
        total_size_gb=total_size / (1024 ** 3) if total_size else 0.0,
        recent_scans=recent_scans,
        recent_plans=recent_plans,
    )


@router.get("/{file_id}", response_model=MediaFileResponse)
async def get_file(file_id: str) -> MediaFileResponse:
    """Get a single file by ID."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM media_files WHERE id = ?",
            (file_id,)
        )
        row = await cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    
    return row_to_file_response(row)


@router.put("/{file_id}", response_model=MediaFileResponse)
async def update_file(file_id: str, request: FileUpdateRequest) -> MediaFileResponse:
    """Update file metadata."""
    async with get_db() as db:
        # Check if file exists
        cursor = await db.execute(
            "SELECT id FROM media_files WHERE id = ?",
            (file_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Build update query
        updates = []
        params = []
        
        if request.final_title is not None:
            updates.append("final_title = ?")
            params.append(request.final_title)
        
        if request.final_author is not None:
            updates.append("final_author = ?")
            params.append(request.final_author)
        
        if request.final_narrator is not None:
            updates.append("final_narrator = ?")
            params.append(request.final_narrator)
        
        if request.final_series is not None:
            updates.append("final_series = ?")
            params.append(request.final_series)
        
        if request.final_series_index is not None:
            updates.append("final_series_index = ?")
            params.append(request.final_series_index)
        
        if request.final_year is not None:
            updates.append("final_year = ?")
            params.append(request.final_year)
        
        if request.status is not None:
            updates.append("status = ?")
            params.append(request.status.value)
        
        if updates:
            updates.append("updated_at = datetime('now')")
            params.append(file_id)
            
            await db.execute(
                f"UPDATE media_files SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()
        
        # Return updated file
        cursor = await db.execute(
            "SELECT * FROM media_files WHERE id = ?",
            (file_id,)
        )
        row = await cursor.fetchone()
    
    return row_to_file_response(row)


@router.post("/{file_id}/approve", response_model=MediaFileResponse)
async def approve_file(file_id: str) -> MediaFileResponse:
    """Approve a file for inclusion in the next plan."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM media_files WHERE id = ?",
            (file_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="File not found")
        
        await db.execute(
            """
            UPDATE media_files 
            SET status = 'approved', updated_at = datetime('now')
            WHERE id = ?
            """,
            (file_id,)
        )
        await db.commit()
        
        cursor = await db.execute(
            "SELECT * FROM media_files WHERE id = ?",
            (file_id,)
        )
        row = await cursor.fetchone()
    
    return row_to_file_response(row)


@router.get("/groups/{group_id}", response_model=AudiobookGroupResponse)
async def get_group(group_id: str) -> AudiobookGroupResponse:
    """Get an audiobook group with its files."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM audiobook_groups WHERE id = ?",
            (group_id,)
        )
        group_row = await cursor.fetchone()
        
        if not group_row:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get files in this group
        cursor = await db.execute(
            """
            SELECT * FROM media_files 
            WHERE group_id = ?
            ORDER BY track_number, file_path
            """,
            (group_id,)
        )
        file_rows = await cursor.fetchall()
    
    files = [row_to_file_response(row) for row in file_rows]
    
    return row_to_group_response(group_row, files)


@router.put("/groups/{group_id}", response_model=AudiobookGroupResponse)
async def update_group(group_id: str, request: GroupUpdateRequest) -> AudiobookGroupResponse:
    """Update audiobook group metadata."""
    async with get_db() as db:
        # Check if group exists
        cursor = await db.execute(
            "SELECT id FROM audiobook_groups WHERE id = ?",
            (group_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Build update query
        updates = []
        params = []
        
        if request.final_title is not None:
            updates.append("final_title = ?")
            params.append(request.final_title)
        
        if request.final_author is not None:
            updates.append("final_author = ?")
            params.append(request.final_author)
        
        if request.final_narrator is not None:
            updates.append("final_narrator = ?")
            params.append(request.final_narrator)
        
        if request.final_series is not None:
            updates.append("final_series = ?")
            params.append(request.final_series)
        
        if request.final_series_index is not None:
            updates.append("final_series_index = ?")
            params.append(request.final_series_index)
        
        if request.final_year is not None:
            updates.append("final_year = ?")
            params.append(request.final_year)
        
        if request.status is not None:
            updates.append("status = ?")
            params.append(request.status.value)
        
        if updates:
            updates.append("updated_at = datetime('now')")
            params.append(group_id)
            
            await db.execute(
                f"UPDATE audiobook_groups SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()
        
        # Return updated group
        cursor = await db.execute(
            "SELECT * FROM audiobook_groups WHERE id = ?",
            (group_id,)
        )
        group_row = await cursor.fetchone()
        
        cursor = await db.execute(
            "SELECT * FROM media_files WHERE group_id = ? ORDER BY track_number, file_path",
            (group_id,)
        )
        file_rows = await cursor.fetchall()
    
    files = [row_to_file_response(row) for row in file_rows]
    
    return row_to_group_response(group_row, files)


@router.post("/groups/{group_id}/approve", response_model=AudiobookGroupResponse)
async def approve_group(group_id: str) -> AudiobookGroupResponse:
    """Approve an audiobook group for inclusion in the next plan."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM audiobook_groups WHERE id = ?",
            (group_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Group not found")
        
        await db.execute(
            """
            UPDATE audiobook_groups 
            SET status = 'approved', updated_at = datetime('now')
            WHERE id = ?
            """,
            (group_id,)
        )
        await db.commit()
        
        cursor = await db.execute(
            "SELECT * FROM audiobook_groups WHERE id = ?",
            (group_id,)
        )
        group_row = await cursor.fetchone()
        
        cursor = await db.execute(
            "SELECT * FROM media_files WHERE group_id = ? ORDER BY track_number, file_path",
            (group_id,)
        )
        file_rows = await cursor.fetchall()
    
    files = [row_to_file_response(row) for row in file_rows]
    
    return row_to_group_response(group_row, files)


@router.post("/bulk-approve")
async def bulk_approve(
    file_ids: list[str] = [],
    group_ids: list[str] = [],
) -> dict:
    """Approve multiple files and/or groups at once."""
    async with get_db() as db:
        files_updated = 0
        groups_updated = 0
        
        if file_ids:
            placeholders = ",".join("?" * len(file_ids))
            cursor = await db.execute(
                f"""
                UPDATE media_files 
                SET status = 'approved', updated_at = datetime('now')
                WHERE id IN ({placeholders})
                """,
                file_ids
            )
            files_updated = cursor.rowcount
        
        if group_ids:
            placeholders = ",".join("?" * len(group_ids))
            cursor = await db.execute(
                f"""
                UPDATE audiobook_groups 
                SET status = 'approved', updated_at = datetime('now')
                WHERE id IN ({placeholders})
                """,
                group_ids
            )
            groups_updated = cursor.rowcount
        
        await db.commit()
    
    return {
        "files_approved": files_updated,
        "groups_approved": groups_updated,
    }
