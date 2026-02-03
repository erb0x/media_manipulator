"""
Plan generator for organizing media files.
Creates plans with operations based on approved files and templates.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from app.ops.templates import (
    MediaMetadata,
    generate_audiobook_paths,
    DEFAULT_AUDIOBOOK_FOLDER_TEMPLATE,
    DEFAULT_AUDIOBOOK_FILE_TEMPLATE,
)
from app.db.database import get_db
from app.config import get_settings


@dataclass
class PlannedOperation:
    """A single file operation in a plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    media_file_id: Optional[str] = None
    group_id: Optional[str] = None
    operation_type: str = "move"  # move, rename, copy_delete
    source_path: str = ""
    target_path: str = ""
    file_hash: Optional[str] = None
    execution_order: int = 0
    
    # For collision detection
    has_collision: bool = False
    collision_type: Optional[str] = None  # exists, duplicate_target
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "media_file_id": self.media_file_id,
            "group_id": self.group_id,
            "operation_type": self.operation_type,
            "source_path": self.source_path,
            "target_path": self.target_path,
            "file_hash": self.file_hash,
            "execution_order": self.execution_order,
        }


@dataclass
class Plan:
    """A complete organization plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    description: Optional[str] = None
    operations: list[PlannedOperation] = field(default_factory=list)
    
    # Warnings and issues
    collisions: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def item_count(self) -> int:
        return len(self.operations)
    
    @property
    def has_issues(self) -> bool:
        return len(self.collisions) > 0 or len(self.duplicates) > 0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "item_count": self.item_count,
            "collisions": self.collisions,
            "duplicates": self.duplicates,
            "warnings": self.warnings,
        }


def determine_operation_type(source_path: Path, target_path: Path) -> str:
    """
    Determine the type of file operation needed.
    
    - Same volume: move (atomic)
    - Different volume: copy_delete
    - Same folder: rename
    """
    # Check if same parent folder (just rename)
    if source_path.parent == target_path.parent:
        return "rename"
    
    # Check if same drive/volume (Windows drive letter comparison)
    source_drive = source_path.drive.upper() if source_path.drive else ""
    target_drive = target_path.drive.upper() if target_path.drive else ""
    
    if source_drive == target_drive:
        return "move"
    else:
        return "copy_delete"


async def generate_plan(
    name: Optional[str] = None,
    description: Optional[str] = None,
    file_ids: list[str] = None,
    group_ids: list[str] = None,
    include_all_approved: bool = True,
) -> Plan:
    """
    Generate an organization plan for approved files and groups.
    
    Args:
        name: Optional plan name
        description: Optional description
        file_ids: Specific file IDs to include
        group_ids: Specific group IDs to include
        include_all_approved: Include all approved items
    
    Returns:
        Plan with all operations
    """
    plan = Plan(name=name, description=description)
    
    # Get output root from settings
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = 'output_root'"
        )
        row = await cursor.fetchone()
        output_root_str = row["value"] if row else None
    
    if not output_root_str:
        plan.warnings.append("No output root configured. Please set output folder in Settings.")
        return plan
    
    output_root = Path(output_root_str)
    
    # Track target paths for collision detection
    target_paths: set[Path] = set()
    execution_order = 0
    
    async with get_db() as db:
        # Get templates from settings
        cursor = await db.execute(
            "SELECT key, value FROM settings WHERE key LIKE 'audiobook_%_template'"
        )
        template_rows = await cursor.fetchall()
        templates = {row["key"]: row["value"] for row in template_rows}
        
        folder_template = templates.get(
            "audiobook_folder_template",
            DEFAULT_AUDIOBOOK_FOLDER_TEMPLATE
        )
        file_template = templates.get(
            "audiobook_file_template",
            DEFAULT_AUDIOBOOK_FILE_TEMPLATE
        )
        
        # Build query for files
        if file_ids:
            placeholders = ",".join("?" * len(file_ids))
            file_query = f"SELECT * FROM media_files WHERE id IN ({placeholders})"
            file_params = file_ids
        elif include_all_approved:
            file_query = "SELECT * FROM media_files WHERE status = 'approved' AND group_id IS NULL"
            file_params = []
        else:
            file_query = "SELECT * FROM media_files WHERE 1=0"  # Empty
            file_params = []
        
        cursor = await db.execute(file_query, file_params)
        file_rows = await cursor.fetchall()
        
        # Process standalone files (not in groups)
        for row in file_rows:
            # Build metadata
            metadata = MediaMetadata(
                title=row["final_title"] or row["extracted_title"],
                author=row["final_author"] or row["extracted_author"],
                narrator=row["final_narrator"] or row["extracted_narrator"],
                series=row["final_series"] or row["extracted_series"],
                series_index=row["final_series_index"] or row["extracted_series_index"],
                year=row["final_year"] or row["extracted_year"],
                extension=Path(row["file_path"]).suffix,
            )
            
            source_path = Path(row["file_path"])
            
            # Generate target path
            target_path = generate_audiobook_paths(
                metadata,
                output_root / "Audiobooks",  # Audiobooks subfolder
                folder_template,
                file_template,
                target_paths,
            )
            
            # Check for collision with existing files
            has_collision = False
            collision_type = None
            
            if target_path.exists() and target_path != source_path:
                has_collision = True
                collision_type = "exists"
                plan.collisions.append(
                    f"Target exists: {target_path}"
                )
            
            if target_path in target_paths:
                has_collision = True
                collision_type = "duplicate_target"
                plan.duplicates.append(
                    f"Duplicate target: {target_path}"
                )
            
            target_paths.add(target_path)
            
            # Create operation
            operation = PlannedOperation(
                media_file_id=row["id"],
                operation_type=determine_operation_type(source_path, target_path),
                source_path=str(source_path),
                target_path=str(target_path),
                file_hash=row["file_hash"],
                execution_order=execution_order,
                has_collision=has_collision,
                collision_type=collision_type,
            )
            
            plan.operations.append(operation)
            execution_order += 1
        
        # Build query for groups
        if group_ids:
            placeholders = ",".join("?" * len(group_ids))
            group_query = f"SELECT * FROM audiobook_groups WHERE id IN ({placeholders})"
            group_params = group_ids
        elif include_all_approved:
            group_query = "SELECT * FROM audiobook_groups WHERE status = 'approved'"
            group_params = []
        else:
            group_query = "SELECT * FROM audiobook_groups WHERE 1=0"
            group_params = []
        
        cursor = await db.execute(group_query, group_params)
        group_rows = await cursor.fetchall()
        
        # Process audiobook groups
        for group_row in group_rows:
            group_id = group_row["id"]
            
            # Get files in this group
            cursor = await db.execute(
                """
                SELECT * FROM media_files 
                WHERE group_id = ?
                ORDER BY track_number, file_path
                """,
                (group_id,)
            )
            group_file_rows = await cursor.fetchall()
            
            total_parts = len(group_file_rows)
            
            for part_num, file_row in enumerate(group_file_rows, start=1):
                # Build metadata from group
                metadata = MediaMetadata(
                    title=group_row["final_title"] or group_row["title"],
                    author=group_row["final_author"] or group_row["author"],
                    narrator=group_row["final_narrator"] or group_row["narrator"],
                    series=group_row["final_series"] or group_row["series"],
                    series_index=group_row["final_series_index"] or group_row["series_index"],
                    year=group_row["final_year"] or group_row["year"],
                    extension=Path(file_row["file_path"]).suffix,
                    part_number=part_num if total_parts > 1 else None,
                    total_parts=total_parts if total_parts > 1 else None,
                )
                
                source_path = Path(file_row["file_path"])
                
                # Generate target path
                target_path = generate_audiobook_paths(
                    metadata,
                    output_root / "Audiobooks",
                    folder_template,
                    file_template,
                    target_paths,
                )
                
                # Check for collision
                has_collision = False
                collision_type = None
                
                if target_path.exists() and target_path != source_path:
                    has_collision = True
                    collision_type = "exists"
                    plan.collisions.append(f"Target exists: {target_path}")
                
                if target_path in target_paths:
                    has_collision = True
                    collision_type = "duplicate_target"
                    plan.duplicates.append(f"Duplicate target: {target_path}")
                
                target_paths.add(target_path)
                
                # Create operation
                operation = PlannedOperation(
                    media_file_id=file_row["id"],
                    group_id=group_id,
                    operation_type=determine_operation_type(source_path, target_path),
                    source_path=str(source_path),
                    target_path=str(target_path),
                    file_hash=file_row["file_hash"],
                    execution_order=execution_order,
                    has_collision=has_collision,
                    collision_type=collision_type,
                )
                
                plan.operations.append(operation)
                execution_order += 1
    
    return plan


async def save_plan(plan: Plan) -> str:
    """Save a plan to the database."""
    async with get_db() as db:
        # Insert plan
        await db.execute(
            """
            INSERT INTO plans (id, name, description, status, item_count)
            VALUES (?, ?, ?, 'ready', ?)
            """,
            (plan.id, plan.name, plan.description, plan.item_count)
        )
        
        # Insert operations
        for op in plan.operations:
            await db.execute(
                """
                INSERT INTO planned_operations (
                    id, plan_id, media_file_id, group_id,
                    operation_type, source_path, target_path,
                    file_hash, execution_order, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    op.id, plan.id, op.media_file_id, op.group_id,
                    op.operation_type, op.source_path, op.target_path,
                    op.file_hash, op.execution_order,
                )
            )
        
        await db.commit()
    
    return plan.id
