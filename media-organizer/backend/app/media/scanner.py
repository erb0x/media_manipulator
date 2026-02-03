"""
Folder scanner for discovering media files.
Recursively scans directories and catalogs files into the database.
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable
import uuid
from datetime import datetime

from app.media.detector import (
    detect_media_type,
    is_supported_file,
    should_skip_folder,
    is_in_audiobook_folder,
    MediaType as DetectorMediaType,
)
from app.media.audio_meta import extract_audio_metadata, get_audio_duration, AudioMetadata
from app.media.parser import parse_filename, merge_metadata
from app.media.grouper import group_audiobook_files, AudiobookGroup
from app.config import get_settings
from app.utils.hashing import compute_sha256 as compute_file_hash


@dataclass
class ScannedFile:
    """A file discovered during scanning."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    file_path: Optional[Path] = None
    file_hash: Optional[str] = None
    file_size: int = 0
    media_type: str = "unknown"
    
    # Extracted metadata
    extracted_title: Optional[str] = None
    extracted_author: Optional[str] = None
    extracted_narrator: Optional[str] = None
    extracted_series: Optional[str] = None
    extracted_series_index: Optional[float] = None
    extracted_year: Optional[int] = None
    duration_seconds: int = 0
    
    # Grouping
    group_id: Optional[str] = None
    is_group_primary: bool = False
    track_number: Optional[int] = None
    
    confidence: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "file_path": str(self.file_path),
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "media_type": self.media_type,
            "extracted_title": self.extracted_title,
            "extracted_author": self.extracted_author,
            "extracted_narrator": self.extracted_narrator,
            "extracted_series": self.extracted_series,
            "extracted_series_index": self.extracted_series_index,
            "extracted_year": self.extracted_year,
            "duration_seconds": self.duration_seconds,
            "group_id": self.group_id,
            "is_group_primary": self.is_group_primary,
            "track_number": self.track_number,
            "confidence": self.confidence,
        }


@dataclass
class ScanProgress:
    """Progress information during scanning."""
    scan_id: str
    root_path: str
    status: str = "running"
    files_found: int = 0
    files_processed: int = 0
    groups_created: int = 0
    current_folder: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ScanResult:
    """Result of a folder scan."""
    scan_id: str
    root_path: Path
    files: list[ScannedFile] = field(default_factory=list)
    groups: list[AudiobookGroup] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass(frozen=True)
class ScanOptions:
    """
    Options that control scan behavior.

    These are primarily intended to make testing and dry-runs predictable.
    """
    hash_files: bool = True
    extract_audio_metadata: bool = True
    verify_audio_duration: bool = False
    min_audiobook_duration_seconds: Optional[int] = None

    def resolved_min_duration(self) -> int:
        """Return the duration threshold to use for audiobook detection."""
        if self.min_audiobook_duration_seconds is not None:
            return self.min_audiobook_duration_seconds
        return get_settings().audiobook_min_duration


@dataclass
class DiscoveryResult:
    """Files discovered during directory walk."""
    standalone_files: list[Path] = field(default_factory=list)
    folder_audio_files: dict[Path, list[Path]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def discover_files(
    root_path: Path,
    exclusion_patterns: list[str] = None,
    options: Optional[ScanOptions] = None,
) -> DiscoveryResult:
    """
    Discover all supported media files in a directory tree.
    
    Returns:
        DiscoveryResult with standalone files, audio folders, and discovery errors.
    """
    exclusion_patterns = exclusion_patterns or []
    options = options or ScanOptions()
    result = DiscoveryResult()
    
    def should_exclude(path: Path) -> bool:
        """Check if path matches any exclusion pattern."""
        path_str = str(path).lower()
        for pattern in exclusion_patterns:
            if pattern.lower() in path_str:
                return True
        return False

    def should_keep_audio_file(file_path: Path) -> bool:
        """
        Optional duration-based filter for ambiguous audio files.
        This helps skip short music tracks when scanning large libraries.
        """
        if not options.verify_audio_duration:
            return True

        # If explicitly in an audiobook folder or an .m4b, keep it.
        if is_in_audiobook_folder(file_path) or file_path.suffix.lower() == ".m4b":
            return True

        duration = get_audio_duration(file_path)
        if duration == 0:
            # If we can't read duration, keep the file to avoid false negatives.
            return True

        return duration >= options.resolved_min_duration()
    
    def walk_directory(current_path: Path):
        """Recursively walk directory tree."""
        try:
            entries = sorted(current_path.iterdir(), key=lambda p: p.name.lower())
        except PermissionError:
            result.errors.append(f"Permission denied: {current_path}")
            return
        except Exception as exc:
            result.errors.append(f"Error scanning {current_path}: {exc}")
            return

        for item in entries:
            if item.is_dir():
                if not should_skip_folder(item.name) and not should_exclude(item):
                    walk_directory(item)
                continue

            if not item.is_file():
                continue

            if should_exclude(item):
                continue

            if not is_supported_file(item):
                continue

            media_type = detect_media_type(item)

            if media_type == DetectorMediaType.AUDIOBOOK:
                if not should_keep_audio_file(item):
                    continue

                # Collect audio files by folder for grouping.
                folder = item.parent
                if folder not in result.folder_audio_files:
                    result.folder_audio_files[folder] = []
                result.folder_audio_files[folder].append(item)
            else:
                # Non-audiobook files are standalone.
                result.standalone_files.append(item)
    
    walk_directory(root_path)

    # Ensure deterministic ordering for tests and UI stability.
    result.standalone_files.sort(key=lambda p: str(p).lower())
    for files in result.folder_audio_files.values():
        files.sort(key=lambda p: p.name.lower())
    
    return result


def process_audio_file(
    file_path: Path,
    group_id: Optional[str] = None,
    is_primary: bool = False,
    track_number: Optional[int] = None,
    audio_metadata: Optional[AudioMetadata] = None,
    options: Optional[ScanOptions] = None,
) -> ScannedFile:
    """
    Process a single audio file and extract metadata.
    """
    options = options or ScanOptions()
    scanned = ScannedFile(file_path=file_path)
    
    try:
        # Get file info
        stat = file_path.stat()
        scanned.file_size = stat.st_size
        scanned.media_type = "audiobook"
        
        # Extract audio metadata (unless disabled for dry-run tests).
        if audio_metadata is None and options.extract_audio_metadata:
            audio_metadata = extract_audio_metadata(file_path)
        elif audio_metadata is None:
            audio_metadata = AudioMetadata()

        scanned.duration_seconds = audio_metadata.duration_seconds
        
        # Parse filename for additional metadata
        parsed = parse_filename(file_path.name)
        merged = merge_metadata(
            parsed,
            audio_title=audio_metadata.title,
            audio_author=audio_metadata.author,
            audio_album=audio_metadata.album,
        )
        
        # Set extracted metadata
        scanned.extracted_title = merged.title or audio_metadata.title or audio_metadata.album
        scanned.extracted_author = merged.author or audio_metadata.author
        scanned.extracted_narrator = audio_metadata.narrator or merged.narrator
        scanned.extracted_series = merged.series
        scanned.extracted_series_index = merged.series_index
        scanned.extracted_year = merged.year or audio_metadata.year
        scanned.confidence = merged.confidence
        
        # Set grouping info
        scanned.group_id = group_id
        scanned.is_group_primary = is_primary
        scanned.track_number = track_number or audio_metadata.track_number
        
        # Compute hash (can be slow for large files)
        if options.hash_files:
            scanned.file_hash = compute_file_hash(file_path)
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        scanned.confidence = 0.0
    
    return scanned


def scan_folder(
    root_path: Path,
    scan_id: str = None,
    exclusion_patterns: list[str] = None,
    progress_callback: Callable[[ScanProgress], None] = None,
    options: Optional[ScanOptions] = None,
) -> ScanResult:
    """
    Scan a folder for media files and create the scan result.
    
    Args:
        root_path: Root folder to scan
        scan_id: Optional scan ID (generated if not provided)
        exclusion_patterns: List of patterns to exclude
        progress_callback: Optional callback for progress updates
    
    Returns:
        ScanResult with discovered files and groups
    """
    scan_id = scan_id or str(uuid.uuid4())
    result = ScanResult(scan_id=scan_id, root_path=root_path)
    options = options or ScanOptions()
    files_processed = 0
    
    def update_progress(status: str, folder: str = None, error: str = None):
        if progress_callback:
            progress = ScanProgress(
                scan_id=scan_id,
                root_path=str(root_path),
                status=status,
                files_found=len(result.files),
                files_processed=files_processed,
                groups_created=len(result.groups),
                current_folder=folder,
                error_message=error,
            )
            progress_callback(progress)
    
    update_progress("discovering")

    if not root_path.exists() or not root_path.is_dir():
        error_msg = f"Scan root does not exist or is not a directory: {root_path}"
        result.errors.append(error_msg)
        result.completed_at = datetime.now()
        update_progress("failed", error=error_msg)
        return result
    
    try:
        # Discover all files
        discovery = discover_files(
            root_path,
            exclusion_patterns,
            options=options,
        )
        result.errors.extend(discovery.errors)
        standalone_files = discovery.standalone_files
        folder_audio_files = discovery.folder_audio_files
        
        # Process audio folders for grouping
        update_progress("grouping")
        
        for folder, audio_files in folder_audio_files.items():
            update_progress("processing", str(folder))
            
            if len(audio_files) == 1:
                # Single file in folder - check if standalone M4B
                single_file = audio_files[0]
                if single_file.suffix.lower() == ".m4b":
                    # Standalone M4B - process without grouping
                    scanned = process_audio_file(single_file, options=options)
                    result.files.append(scanned)
                    files_processed += 1
                else:
                    # Single non-M4B file - still process it
                    scanned = process_audio_file(single_file, options=options)
                    result.files.append(scanned)
                    files_processed += 1
            else:
                # Multiple files - create a group
                group = group_audiobook_files(
                    folder,
                    audio_files,
                    read_audio_metadata=options.extract_audio_metadata,
                )
                
                if group:
                    result.groups.append(group)
                    
                    # Process each file in the group
                    sorted_files = group.get_sorted_files()
                    for idx, audio_file in enumerate(sorted_files):
                        scanned = process_audio_file(
                            audio_file.file_path,
                            group_id=group.id,
                            is_primary=(idx == 0),
                            track_number=audio_file.track_number,
                            audio_metadata=audio_file.metadata,
                            options=options,
                        )
                        result.files.append(scanned)
                        files_processed += 1
        
        # Process standalone files (ebooks, comics)
        for file_path in standalone_files:
            update_progress("processing", str(file_path.parent))
            
            scanned = ScannedFile(file_path=file_path)
            scanned.file_size = file_path.stat().st_size
            scanned.media_type = str(detect_media_type(file_path).value)
            if options.hash_files:
                scanned.file_hash = compute_file_hash(file_path)
            
            # Basic filename parsing
            parsed = parse_filename(file_path.name)
            scanned.extracted_title = parsed.title
            scanned.extracted_author = parsed.author
            scanned.extracted_year = parsed.year
            scanned.confidence = parsed.confidence
            
            result.files.append(scanned)
            files_processed += 1
        
        result.completed_at = datetime.now()
        update_progress("completed")
        
    except Exception as e:
        error_msg = f"Scan error: {str(e)}"
        result.errors.append(error_msg)
        result.completed_at = datetime.now()
        update_progress("failed", error=error_msg)
    
    return result
