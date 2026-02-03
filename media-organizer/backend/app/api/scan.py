"""
Scan API endpoints for the Media Organizer.
Handles starting scans, checking status, and retrieving results.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pathlib import Path
from datetime import datetime
import uuid

from app.db.models import (
    ScanRequest,
    ScanResponse,
    ScanListResponse,
    ScanStatus,
    MediaType,
    FileStatus,
)
from app.db.database import get_db
from app.media.scanner import scan_folder, ScanProgress


router = APIRouter(prefix="/scan", tags=["scan"])


# In-memory scan status tracking (for active scans)
_active_scans: dict[str, ScanProgress] = {}


async def run_scan_background(
    scan_id: str,
    root_path: str,
    exclusion_patterns: list[str],
):
    """
    Background task to run a folder scan.
    Updates database with progress and results.
    """
    def progress_callback(progress: ScanProgress):
        _active_scans[scan_id] = progress
    
    try:
        # Update scan status to running
        async with get_db() as db:
            await db.execute(
                """
                UPDATE scans 
                SET status = 'running', started_at = datetime('now')
                WHERE id = ?
                """,
                (scan_id,)
            )
            await db.commit()
        
        # Run the scan
        result = scan_folder(
            root_path=Path(root_path),
            scan_id=scan_id,
            exclusion_patterns=exclusion_patterns,
            progress_callback=progress_callback,
        )
        
        # Save results to database
        async with get_db() as db:
            # Insert scanned files
            for scanned_file in result.files:
                await db.execute(
                    """
                    INSERT INTO media_files (
                        id, scan_id, file_path, file_hash, file_size, media_type,
                        group_id, is_group_primary, track_number,
                        extracted_title, extracted_author, extracted_narrator,
                        extracted_series, extracted_series_index, extracted_year,
                        duration_seconds, status, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                    ON CONFLICT(file_path) DO UPDATE SET
                        file_hash = excluded.file_hash,
                        file_size = excluded.file_size,
                        updated_at = datetime('now')
                    """,
                    (
                        scanned_file.id,
                        scan_id,
                        str(scanned_file.file_path),
                        scanned_file.file_hash,
                        scanned_file.file_size,
                        scanned_file.media_type,
                        scanned_file.group_id,
                        scanned_file.is_group_primary,
                        scanned_file.track_number,
                        scanned_file.extracted_title,
                        scanned_file.extracted_author,
                        scanned_file.extracted_narrator,
                        scanned_file.extracted_series,
                        scanned_file.extracted_series_index,
                        scanned_file.extracted_year,
                        scanned_file.duration_seconds,
                        scanned_file.confidence,
                    )
                )
            
            # Insert audiobook groups
            for group in result.groups:
                data = group.to_dict()
                await db.execute(
                    """
                    INSERT INTO audiobook_groups (
                        id, scan_id, folder_path, file_count, total_duration_seconds,
                        title, author, narrator, series, series_index, year,
                        status, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                    ON CONFLICT(folder_path) DO UPDATE SET
                        file_count = excluded.file_count,
                        total_duration_seconds = excluded.total_duration_seconds,
                        updated_at = datetime('now')
                    """,
                    (
                        data["id"],
                        scan_id,
                        data["folder_path"],
                        data["file_count"],
                        data["total_duration_seconds"],
                        data["title"],
                        data["author"],
                        data["narrator"],
                        data["series"],
                        data["series_index"],
                        data["year"],
                        data["confidence"],
                    )
                )
            
            # Update scan status to completed
            status = "completed" if not result.errors else "failed"
            error_msg = "; ".join(result.errors) if result.errors else None
            
            await db.execute(
                """
                UPDATE scans 
                SET status = ?, completed_at = datetime('now'), 
                    files_found = ?, groups_created = ?, error_message = ?
                WHERE id = ?
                """,
                (status, len(result.files), len(result.groups), error_msg, scan_id)
            )
            await db.commit()
        
    except Exception as e:
        # Update scan status to failed
        async with get_db() as db:
            await db.execute(
                """
                UPDATE scans 
                SET status = 'failed', completed_at = datetime('now'), 
                    error_message = ?
                WHERE id = ?
                """,
                (str(e), scan_id)
            )
            await db.commit()
    
    finally:
        # Clean up active scan tracking
        if scan_id in _active_scans:
            del _active_scans[scan_id]


@router.post("/start", response_model=ScanResponse)
async def start_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
) -> ScanResponse:
    """
    Start a new folder scan.
    The scan runs in the background and updates the database.
    """
    # Validate root paths exist
    for root_path in request.root_paths:
        path = Path(root_path)
        if not path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Path does not exist: {root_path}"
            )
        if not path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Path is not a directory: {root_path}"
            )
    
    # For now, just use the first root path (multi-root can be added later)
    root_path = request.root_paths[0]
    scan_id = str(uuid.uuid4())
    
    # Create scan record
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO scans (id, root_path, status)
            VALUES (?, ?, 'pending')
            """,
            (scan_id, root_path)
        )
        await db.commit()
    
    # Start background scan
    background_tasks.add_task(
        run_scan_background,
        scan_id,
        root_path,
        request.exclusion_patterns,
    )
    
    return ScanResponse(
        id=scan_id,
        root_path=root_path,
        status=ScanStatus.PENDING,
    )


@router.get("/status/{scan_id}", response_model=ScanResponse)
async def get_scan_status(scan_id: str) -> ScanResponse:
    """Get the status of a scan."""
    # Check active scans first
    if scan_id in _active_scans:
        progress = _active_scans[scan_id]
        return ScanResponse(
            id=scan_id,
            root_path=progress.root_path,
            status=ScanStatus.RUNNING,
            files_found=progress.files_found,
            groups_created=progress.groups_created,
        )
    
    # Check database
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, root_path, status, started_at, completed_at,
                   files_found, groups_created, error_message
            FROM scans WHERE id = ?
            """,
            (scan_id,)
        )
        row = await cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    return ScanResponse(
        id=row["id"],
        root_path=row["root_path"],
        status=ScanStatus(row["status"]),
        started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        files_found=row["files_found"] or 0,
        groups_created=row["groups_created"] or 0,
        error_message=row["error_message"],
    )


@router.get("", response_model=ScanListResponse)
async def list_scans(
    page: int = 1,
    page_size: int = 20,
) -> ScanListResponse:
    """List all scans with pagination."""
    offset = (page - 1) * page_size
    
    async with get_db() as db:
        # Get total count
        cursor = await db.execute("SELECT COUNT(*) FROM scans")
        total = (await cursor.fetchone())[0]
        
        # Get scans
        cursor = await db.execute(
            """
            SELECT id, root_path, status, started_at, completed_at,
                   files_found, groups_created, error_message
            FROM scans
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset)
        )
        rows = await cursor.fetchall()
    
    items = [
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
        for row in rows
    ]
    
    return ScanListResponse(
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(items)) < total,
        items=items,
    )


@router.delete("/{scan_id}")
async def delete_scan(scan_id: str) -> dict:
    """Delete a scan and all its associated files."""
    async with get_db() as db:
        # Check if scan exists
        cursor = await db.execute(
            "SELECT id FROM scans WHERE id = ?",
            (scan_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Scan not found")
        
        # Delete associated data (cascades due to foreign keys)
        await db.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
        await db.commit()
    
    return {"message": "Scan deleted", "id": scan_id}
