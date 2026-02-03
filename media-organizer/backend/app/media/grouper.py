"""
Multi-file audiobook grouping logic.
Groups audio files in the same folder into a single audiobook entity.
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import uuid

from app.media.audio_meta import extract_audio_metadata, AudioMetadata
from app.media.parser import parse_folder_path


@dataclass
class AudiobookFile:
    """A single audio file within an audiobook."""
    file_path: Path
    file_size: int
    metadata: AudioMetadata
    track_number: Optional[int] = None
    
    def __post_init__(self):
        # Try to determine track number from metadata or filename
        if self.track_number is None:
            if self.metadata.track_number:
                self.track_number = self.metadata.track_number
            else:
                # Try to extract from filename
                self.track_number = self._extract_track_from_filename()
    
    def _extract_track_from_filename(self) -> Optional[int]:
        """Try to extract track number from filename."""
        import re
        name = self.file_path.stem
        
        # Common patterns: "01 - Chapter", "Track 01", "Part 1"
        patterns = [
            r"^(\d+)\s*[-–—.]",  # "01 - " or "01."
            r"(?:track|part|chapter)\s*(\d+)",  # "Track 01"
            r"[-–—]\s*(\d+)$",  # "- 01" at end
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
        
        return None


@dataclass
class AudiobookGroup:
    """A group of audio files that form a single audiobook."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    folder_path: Path = None
    files: list[AudiobookFile] = field(default_factory=list)
    
    # Consolidated metadata
    title: Optional[str] = None
    author: Optional[str] = None
    narrator: Optional[str] = None
    series: Optional[str] = None
    series_index: Optional[float] = None
    year: Optional[int] = None
    
    confidence: float = 0.0
    
    @property
    def file_count(self) -> int:
        return len(self.files)
    
    @property
    def total_duration_seconds(self) -> int:
        return sum(f.metadata.duration_seconds for f in self.files)
    
    @property
    def total_size_bytes(self) -> int:
        return sum(f.file_size for f in self.files)
    
    @property
    def primary_file(self) -> Optional[AudiobookFile]:
        """Get the primary file (for metadata extraction)."""
        if not self.files:
            return None
        
        # Sort by track number, then by duration (longest first)
        sorted_files = sorted(
            self.files,
            key=lambda f: (f.track_number or 999, -f.metadata.duration_seconds)
        )
        
        # Prefer track 1, otherwise the longest file
        return sorted_files[0]
    
    def consolidate_metadata(self) -> None:
        """
        Consolidate metadata from files and folder name.
        Uses the primary file's metadata as base, supplements with folder parsing.
        """
        primary = self.primary_file
        if not primary:
            return
        
        # Start with primary file's metadata
        meta = primary.metadata
        self.title = meta.title or meta.album
        self.author = meta.author
        self.narrator = meta.narrator
        self.year = meta.year
        
        # Parse folder name for additional info
        if self.folder_path:
            parsed = parse_folder_path(self.folder_path)
            
            # Fill in gaps from folder name parsing
            if not self.title and parsed.title:
                self.title = parsed.title
            if not self.author and parsed.author:
                self.author = parsed.author
            if not self.narrator and parsed.narrator:
                self.narrator = parsed.narrator
            if not self.year and parsed.year:
                self.year = parsed.year
            if parsed.series:
                self.series = parsed.series
                self.series_index = parsed.series_index
            
            self.confidence = parsed.confidence
        
        # If still no title, use folder name as fallback
        if not self.title and self.folder_path:
            self.title = self.folder_path.name
            self.confidence = 0.2
        
        # Boost confidence if we have good metadata
        if self.author:
            self.confidence += 0.1
        if self.narrator:
            self.confidence += 0.1
        if self.year:
            self.confidence += 0.05
        
        self.confidence = min(self.confidence, 1.0)
    
    def get_sorted_files(self) -> list[AudiobookFile]:
        """Get files sorted by track number, then alphabetically."""
        return sorted(
            self.files,
            key=lambda f: (f.track_number or 999, f.file_path.name.lower())
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "folder_path": str(self.folder_path),
            "file_count": self.file_count,
            "total_duration_seconds": self.total_duration_seconds,
            "title": self.title,
            "author": self.author,
            "narrator": self.narrator,
            "series": self.series,
            "series_index": self.series_index,
            "year": self.year,
            "confidence": self.confidence,
        }


def should_group_files(folder_path: Path, files: list[Path]) -> bool:
    """
    Determine if files in a folder should be grouped as a single audiobook.
    
    Rules:
    - Single .m4b file: standalone audiobook, no grouping
    - Multiple audio files in same folder: group them
    - Mixed formats: group them (likely same audiobook)
    """
    if len(files) == 1:
        # Single file: check if it's a standalone .m4b
        ext = files[0].suffix.lower()
        if ext == ".m4b":
            return False  # Standalone M4B, don't group
        # Other single files might be part of incomplete set, still don't group
        return False
    
    # Multiple files in same folder: group them
    return len(files) > 1


def group_audiobook_files(
    folder_path: Path,
    file_paths: list[Path],
    read_audio_metadata: bool = True,
) -> Optional[AudiobookGroup]:
    """
    Create an audiobook group from files in a folder.
    
    Args:
        folder_path: The folder containing the files
        file_paths: List of audio file paths in the folder
        read_audio_metadata: If False, skip mutagen reads (useful for dry-runs/tests)
    
    Returns:
        AudiobookGroup if grouping is appropriate, None otherwise
    """
    if not file_paths:
        return None
    
    if not should_group_files(folder_path, file_paths):
        return None
    
    # Create the group
    group = AudiobookGroup(folder_path=folder_path)
    
    # Process each file
    for file_path in sorted(file_paths, key=lambda p: p.name.lower()):
        try:
            file_size = file_path.stat().st_size
            metadata = extract_audio_metadata(file_path) if read_audio_metadata else AudioMetadata()
            
            audio_file = AudiobookFile(
                file_path=file_path,
                file_size=file_size,
                metadata=metadata,
            )
            group.files.append(audio_file)
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    if not group.files:
        return None
    
    # Consolidate metadata from all files
    group.consolidate_metadata()
    
    return group


def process_folder_for_groups(
    folder_path: Path,
    all_audio_files: dict[Path, list[Path]],
    read_audio_metadata: bool = True,
) -> list[AudiobookGroup]:
    """
    Process a collection of folders and their audio files into audiobook groups.
    
    Args:
        folder_path: Root folder being scanned
        all_audio_files: Dict mapping folder paths to list of audio files
    
    Returns:
        List of AudiobookGroup objects
    """
    groups = []
    
    for folder, files in all_audio_files.items():
        if not files:
            continue
        
        # Check if this should be grouped
        if should_group_files(folder, files):
            group = group_audiobook_files(folder, files, read_audio_metadata=read_audio_metadata)
            if group:
                groups.append(group)
    
    return groups
