"""
Pydantic models for API requests and responses.
These define the data structures used throughout the application.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


# Enums for type safety
class MediaType(str, Enum):
    AUDIOBOOK = "audiobook"
    EBOOK = "ebook"
    COMIC = "comic"


class FileStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    APPLIED = "applied"


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    APPLYING = "applying"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class OperationStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


class OperationType(str, Enum):
    MOVE = "move"
    RENAME = "rename"
    COPY_DELETE = "copy_delete"


# Request models
class ScanRequest(BaseModel):
    """Request to start a new scan."""
    root_paths: list[str] = Field(..., min_length=1, description="Paths to scan")
    exclusion_patterns: list[str] = Field(default=[], description="Glob patterns to exclude")


class FileUpdateRequest(BaseModel):
    """Request to update file metadata."""
    final_title: Optional[str] = None
    final_author: Optional[str] = None
    final_narrator: Optional[str] = None
    final_series: Optional[str] = None
    final_series_index: Optional[float] = None
    final_year: Optional[int] = None
    status: Optional[FileStatus] = None


class GroupUpdateRequest(BaseModel):
    """Request to update audiobook group metadata."""
    final_title: Optional[str] = None
    final_author: Optional[str] = None
    final_narrator: Optional[str] = None
    final_series: Optional[str] = None
    final_series_index: Optional[float] = None
    final_year: Optional[int] = None
    status: Optional[FileStatus] = None


class PlanCreateRequest(BaseModel):
    """Request to create a new plan."""
    name: Optional[str] = None
    description: Optional[str] = None
    file_ids: list[str] = Field(default=[], description="Specific file IDs to include")
    group_ids: list[str] = Field(default=[], description="Specific group IDs to include")
    include_all_approved: bool = Field(default=True, description="Include all approved items")


class SettingsUpdateRequest(BaseModel):
    """Request to update settings."""
    output_root: Optional[str] = None
    audiobook_folder_template: Optional[str] = None
    audiobook_file_template: Optional[str] = None
    enable_llm: Optional[bool] = None
    enable_providers: Optional[bool] = None


# Response models
class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "0.1.0"
    database: str = "connected"


class ScanResponse(BaseModel):
    """Scan status response."""
    id: str
    root_path: str
    status: ScanStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    files_found: int = 0
    groups_created: int = 0
    error_message: Optional[str] = None


class MediaFileResponse(BaseModel):
    """Media file details response."""
    id: str
    file_path: str
    file_hash: Optional[str] = None
    file_size: Optional[int] = None
    media_type: MediaType
    group_id: Optional[str] = None
    is_group_primary: bool = False
    track_number: Optional[int] = None
    
    # Extracted metadata
    extracted_title: Optional[str] = None
    extracted_author: Optional[str] = None
    extracted_narrator: Optional[str] = None
    extracted_series: Optional[str] = None
    extracted_series_index: Optional[float] = None
    extracted_year: Optional[int] = None
    duration_seconds: Optional[int] = None
    
    # Final metadata
    final_title: Optional[str] = None
    final_author: Optional[str] = None
    final_narrator: Optional[str] = None
    final_series: Optional[str] = None
    final_series_index: Optional[float] = None
    final_year: Optional[int] = None
    
    # Status
    status: FileStatus = FileStatus.PENDING
    confidence: float = 0.0
    proposed_path: Optional[str] = None
    
    # Provider info
    provider_match_source: Optional[str] = None
    provider_match_id: Optional[str] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AudiobookGroupResponse(BaseModel):
    """Audiobook group details response."""
    id: str
    folder_path: str
    file_count: int = 0
    total_duration_seconds: int = 0
    
    # Metadata
    title: Optional[str] = None
    author: Optional[str] = None
    narrator: Optional[str] = None
    series: Optional[str] = None
    series_index: Optional[float] = None
    year: Optional[int] = None
    
    # Final metadata
    final_title: Optional[str] = None
    final_author: Optional[str] = None
    final_narrator: Optional[str] = None
    final_series: Optional[str] = None
    final_series_index: Optional[float] = None
    final_year: Optional[int] = None
    
    # Status
    status: FileStatus = FileStatus.PENDING
    confidence: float = 0.0
    proposed_path: Optional[str] = None
    
    # Files in this group
    files: list[MediaFileResponse] = []
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PlannedOperationResponse(BaseModel):
    """Planned operation details."""
    id: str
    operation_type: OperationType
    source_path: str
    target_path: str
    status: OperationStatus = OperationStatus.PENDING
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class PlanResponse(BaseModel):
    """Plan details response."""
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    status: PlanStatus = PlanStatus.DRAFT
    created_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    item_count: int = 0
    completed_count: int = 0
    error_message: Optional[str] = None
    operations: list[PlannedOperationResponse] = []


class SettingsResponse(BaseModel):
    """Current settings response."""
    output_root: Optional[str] = None
    audiobook_folder_template: str
    audiobook_file_template: str
    enable_llm: bool
    enable_providers: bool
    gemini_key_loaded: bool
    google_books_key_loaded: bool


class ProviderSearchResult(BaseModel):
    """Result from provider search."""
    provider: str
    id: str  # ASIN, ISBN, etc.
    title: str
    author: Optional[str] = None
    narrator: Optional[str] = None
    series: Optional[str] = None
    series_index: Optional[float] = None
    year: Optional[int] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    confidence: float = 0.0


class ProviderSearchResponse(BaseModel):
    """Response from provider search."""
    query: str
    results: list[ProviderSearchResult] = []
    cached: bool = False


# List responses with pagination
class PaginatedResponse(BaseModel):
    """Base for paginated responses."""
    total: int
    page: int = 1
    page_size: int = 50
    has_more: bool = False


class MediaFileListResponse(PaginatedResponse):
    """Paginated list of media files."""
    items: list[MediaFileResponse] = []


class AudiobookGroupListResponse(PaginatedResponse):
    """Paginated list of audiobook groups."""
    items: list[AudiobookGroupResponse] = []


class PlanListResponse(PaginatedResponse):
    """Paginated list of plans."""
    items: list[PlanResponse] = []


class ScanListResponse(PaginatedResponse):
    """Paginated list of scans."""
    items: list[ScanResponse] = []


# Dashboard stats
class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_files: int = 0
    total_groups: int = 0
    pending_count: int = 0
    reviewed_count: int = 0
    approved_count: int = 0
    applied_count: int = 0
    total_duration_hours: float = 0.0
    total_size_gb: float = 0.0
    recent_scans: list[ScanResponse] = []
    recent_plans: list[PlanResponse] = []
