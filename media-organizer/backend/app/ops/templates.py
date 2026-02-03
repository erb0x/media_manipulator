"""
Naming templates for organizing media files.
Handles path generation and Windows-safe filename normalization.
"""

from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


# Characters not allowed in Windows filenames
WINDOWS_FORBIDDEN = '<>:"/\\|?*'
# Control characters
CONTROL_CHARS = ''.join(chr(i) for i in range(32))


@dataclass
class MediaMetadata:
    """Metadata for generating paths."""
    title: Optional[str] = None
    author: Optional[str] = None
    narrator: Optional[str] = None
    series: Optional[str] = None
    series_index: Optional[float] = None
    year: Optional[int] = None
    extension: str = ""
    
    # For multi-file audiobooks
    part_number: Optional[int] = None
    total_parts: Optional[int] = None
    
    @property
    def author_sort(self) -> str:
        """Get author in 'Last, First' format for sorting."""
        if not self.author:
            return "Unknown Author"
        
        # Simple split on last space
        parts = self.author.strip().split()
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            return f"{parts[1]}, {parts[0]}"
        else:
            # Assume last word is surname
            return f"{parts[-1]}, {' '.join(parts[:-1])}"
    
    @property
    def series_index_formatted(self) -> str:
        """Format series index with leading zero if needed."""
        if self.series_index is None:
            return ""
        
        if self.series_index == int(self.series_index):
            # Integer, format with leading zero
            return f"{int(self.series_index):02d}"
        else:
            # Has decimal
            return f"{self.series_index:05.2f}"


def normalize_filename(name: str, max_length: int = 200) -> str:
    """
    Normalize a string for use as a Windows filename.
    
    - Removes forbidden characters
    - Collapses multiple spaces
    - Trims to max length
    - Handles edge cases
    """
    if not name:
        return "Unknown"
    
    # Remove control characters
    name = ''.join(c for c in name if c not in CONTROL_CHARS)
    
    # Replace forbidden characters with space
    for char in WINDOWS_FORBIDDEN:
        name = name.replace(char, ' ')
    
    # Replace common problematic characters
    replacements = {
        '…': '...',
        '"': "'",
        '"': "'",
        ''': "'",
        ''': "'",
        '–': '-',
        '—': '-',
        '\t': ' ',
        '\n': ' ',
        '\r': ' ',
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    # Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name)
    
    # Strip leading/trailing spaces and dots
    name = name.strip(' .')
    
    # Trim to max length
    if len(name) > max_length:
        name = name[:max_length].rsplit(' ', 1)[0]
    
    # Handle empty result
    if not name:
        return "Unknown"
    
    return name


def normalize_path_segment(segment: str, max_length: int = 200) -> str:
    """Normalize a single path segment (folder or file name)."""
    return normalize_filename(segment, max_length)


def apply_template(template: str, metadata: MediaMetadata) -> str:
    """
    Apply a template string with metadata placeholders.
    
    Supported placeholders:
    - {title}
    - {author}
    - {author_sort}
    - {narrator}
    - {series}
    - {series_index}
    - {year}
    - {ext}
    - {part_num}
    - {total_parts}
    """
    # Build replacements
    replacements = {
        "{title}": normalize_filename(metadata.title or "Unknown Title"),
        "{author}": normalize_filename(metadata.author or "Unknown Author"),
        "{author_sort}": normalize_filename(metadata.author_sort),
        "{narrator}": normalize_filename(metadata.narrator or "Unknown Narrator"),
        "{series}": normalize_filename(metadata.series or ""),
        "{series_index}": metadata.series_index_formatted,
        "{year}": str(metadata.year) if metadata.year else "Unknown",
        "{ext}": metadata.extension.lstrip('.'),
        "{part_num}": f"{metadata.part_number:02d}" if metadata.part_number else "",
        "{total_parts}": str(metadata.total_parts) if metadata.total_parts else "",
    }
    
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    # Clean up empty parts
    # Remove double slashes from empty placeholders
    result = re.sub(r'/+', '/', result)
    # Remove empty segments like "/ /" or "/-/"
    result = re.sub(r'/[\s\-]+/', '/', result)
    # Remove trailing slashes or dashes
    result = result.rstrip('/ -')
    # Remove leading dashes in segments
    result = re.sub(r'/([\s\-]+)', '/', result)
    
    return result


def generate_audiobook_path(
    metadata: MediaMetadata,
    output_root: Path,
    folder_template: str,
    file_template: str,
) -> Path:
    """
    Generate the target path for an audiobook file.
    
    Args:
        metadata: File metadata
        output_root: Root output directory
        folder_template: Template for folder structure
        file_template: Template for filename
    
    Returns:
        Complete target path
    """
    # Apply templates
    folder_path = apply_template(folder_template, metadata)
    filename = apply_template(file_template, metadata)
    
    # Normalize each path segment
    segments = folder_path.split('/')
    normalized_segments = [normalize_path_segment(s) for s in segments if s]
    
    # Build full path
    target_folder = output_root
    for segment in normalized_segments:
        if segment:
            target_folder = target_folder / segment
    
    target_path = target_folder / normalize_filename(filename)
    
    return target_path


def generate_unique_path(target_path: Path, existing_paths: set[Path] = None) -> Path:
    """
    Generate a unique path by adding suffix if collision exists.
    
    Args:
        target_path: Desired target path
        existing_paths: Set of paths already in use (or check filesystem if None)
    
    Returns:
        Path that doesn't conflict
    """
    existing_paths = existing_paths or set()
    
    if target_path not in existing_paths and not target_path.exists():
        return target_path
    
    # Add suffix
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        
        if new_path not in existing_paths and not new_path.exists():
            return new_path
        
        counter += 1
        
        # Safety limit
        if counter > 1000:
            raise RuntimeError(f"Could not find unique path for {target_path}")


# Default templates
DEFAULT_AUDIOBOOK_FOLDER_TEMPLATE = "{author_sort}/{series}/{series_index} - {title} ({year})"
DEFAULT_AUDIOBOOK_FILE_TEMPLATE = "{series_index} - {title}.{ext}"
DEFAULT_AUDIOBOOK_MULTIFILE_TEMPLATE = "{title} - Part {part_num}.{ext}"

# Templates without series
DEFAULT_AUDIOBOOK_FOLDER_NO_SERIES = "{author_sort}/{title} ({year})"
DEFAULT_AUDIOBOOK_FILE_NO_SERIES = "{title}.{ext}"


def generate_audiobook_paths(
    metadata: MediaMetadata,
    output_root: Path,
    folder_template: str = None,
    file_template: str = None,
    existing_paths: set[Path] = None,
) -> Path:
    """
    Generate target path for an audiobook, handling series/no-series cases.
    
    Args:
        metadata: File metadata
        output_root: Root output directory (e.g., E:\Media\Audiobooks)
        folder_template: Custom folder template (uses default if None)
        file_template: Custom file template (uses default if None)
        existing_paths: Set of paths already planned (for collision detection)
    
    Returns:
        Unique target path
    """
    # Choose templates based on whether series exists
    if metadata.series:
        folder_template = folder_template or DEFAULT_AUDIOBOOK_FOLDER_TEMPLATE
        if metadata.part_number:
            file_template = file_template or DEFAULT_AUDIOBOOK_MULTIFILE_TEMPLATE
        else:
            file_template = file_template or DEFAULT_AUDIOBOOK_FILE_TEMPLATE
    else:
        folder_template = folder_template or DEFAULT_AUDIOBOOK_FOLDER_NO_SERIES
        if metadata.part_number:
            file_template = file_template or DEFAULT_AUDIOBOOK_MULTIFILE_TEMPLATE
        else:
            file_template = file_template or DEFAULT_AUDIOBOOK_FILE_NO_SERIES
    
    target_path = generate_audiobook_path(
        metadata, output_root, folder_template, file_template
    )
    
    # Ensure unique
    return generate_unique_path(target_path, existing_paths)
