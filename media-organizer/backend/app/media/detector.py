"""
Media type detection based on file extension and folder context.
"""

from __future__ import annotations

from pathlib import Path
from enum import Enum
from typing import Optional
from app.config import get_settings


class MediaType(str, Enum):
    AUDIOBOOK = "audiobook"
    EBOOK = "ebook"
    COMIC = "comic"
    UNKNOWN = "unknown"


def get_extension_type(file_path: Path) -> Optional[MediaType]:
    """
    Determine potential media type from file extension alone.
    Returns None if extension is not recognized.
    """
    settings = get_settings()
    ext = file_path.suffix.lower()
    
    if ext in settings.audiobook_extensions:
        return MediaType.AUDIOBOOK
    elif ext in settings.ebook_extensions:
        return MediaType.EBOOK
    elif ext in settings.comic_extensions:
        return MediaType.COMIC
    
    return None


def is_in_audiobook_folder(file_path: Path) -> bool:
    """
    Check if the file is within a folder that suggests it's an audiobook.
    Looks for 'audiobook' (case-insensitive) in path components.
    """
    settings = get_settings()
    pattern = settings.audiobook_folder_pattern.lower()
    
    # Check each parent folder name
    for part in file_path.parts:
        if pattern in part.lower():
            return True
    
    return False


def detect_media_type(file_path: Path) -> MediaType:
    """
    Detect the media type of a file based on extension and folder context.
    
    For audio files (.mp3, .m4b, .m4a, .flac):
    - If in an "audiobook" folder -> AUDIOBOOK
    - Otherwise -> treat as potential audiobook (will verify by duration later)
    
    For ebook files (.epub, .mobi, .pdf, .azw3) -> EBOOK
    For comic files (.cbz, .cbr, .cb7) -> COMIC
    """
    settings = get_settings()
    ext = file_path.suffix.lower()
    
    # Check ebooks first (no ambiguity)
    if ext in settings.ebook_extensions:
        return MediaType.EBOOK
    
    # Check comics (no ambiguity)
    if ext in settings.comic_extensions:
        return MediaType.COMIC
    
    # Check audio files (need context for audiobook detection)
    if ext in settings.audiobook_extensions:
        # If in audiobook folder or standalone .m4b, it's an audiobook
        if is_in_audiobook_folder(file_path) or ext == ".m4b":
            return MediaType.AUDIOBOOK
        # Otherwise, we'll treat as potential audiobook and verify by duration
        return MediaType.AUDIOBOOK  # For now, all audio in scan roots are audiobooks
    
    return MediaType.UNKNOWN


def is_supported_file(file_path: Path) -> bool:
    """Check if a file has a supported extension."""
    settings = get_settings()
    ext = file_path.suffix.lower()
    
    all_extensions = (
        settings.audiobook_extensions + 
        settings.ebook_extensions + 
        settings.comic_extensions
    )
    
    return ext in all_extensions


def should_skip_folder(folder_name: str) -> bool:
    """
    Check if a folder should be skipped during scanning.
    Skips hidden folders and common system folders.
    """
    skip_patterns = [
        ".",  # Hidden folders
        "__",  # Python cache, etc.
        "$",  # Windows system folders
        "node_modules",
        ".git",
        ".svn",
        "Thumbs.db",
        "desktop.ini",
    ]
    
    folder_lower = folder_name.lower()
    
    for pattern in skip_patterns:
        if folder_lower.startswith(pattern):
            return True
    
    return False
