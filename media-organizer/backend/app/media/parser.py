"""
Filename parsing heuristics for extracting metadata from file/folder names.
Handles common audiobook naming patterns.
"""

from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedFilename:
    """Result of parsing a filename or folder name."""
    title: Optional[str] = None
    author: Optional[str] = None
    series: Optional[str] = None
    series_index: Optional[float] = None
    year: Optional[int] = None
    narrator: Optional[str] = None
    quality: Optional[str] = None  # e.g., "Unabridged", "Abridged"
    confidence: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "author": self.author,
            "series": self.series,
            "series_index": self.series_index,
            "year": self.year,
            "narrator": self.narrator,
            "quality": self.quality,
            "confidence": self.confidence,
        }


# Common patterns in audiobook filenames
YEAR_PATTERN = re.compile(r"\((\d{4})\)")
SERIES_PATTERNS = [
    # "Series Name, Book 1" or "Series Name Book 1"
    re.compile(r"^(.+?)[,\s]+Book\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
    # "Series Name #1" or "Series Name - #1"
    re.compile(r"^(.+?)\s*[-–—]?\s*#(\d+(?:\.\d+)?)", re.IGNORECASE),
    # "Series 01 - Title" or "Series Book 01 - Title"
    re.compile(r"^(.+?)\s+(?:Book\s*)?(\d+)\s*[-–—]\s*(.+)", re.IGNORECASE),
]

# Author - Title pattern
AUTHOR_TITLE_PATTERN = re.compile(r"^(.+?)\s*[-–—]\s*(.+)$")

# Title (Year) pattern
TITLE_YEAR_PATTERN = re.compile(r"^(.+?)\s*\((\d{4})\)\s*$")

# Narrator patterns
NARRATOR_PATTERNS = [
    re.compile(r"(?:narrated by|read by|narrator)[:\s]+(.+?)(?:\s*[-–—(]|$)", re.IGNORECASE),
    re.compile(r"\[(.+?)\]$"),  # [Narrator Name] at end
]

# Quality indicators
QUALITY_PATTERNS = [
    (re.compile(r"\bunabridged\b", re.IGNORECASE), "Unabridged"),
    (re.compile(r"\babridged\b", re.IGNORECASE), "Abridged"),
]

# Cleanup patterns
CLEANUP_PATTERNS = [
    re.compile(r"\s*\[.*?\]\s*"),  # Remove bracketed content
    re.compile(r"\s*\((?![\d]{4}\)).*?\)\s*"),  # Remove parenthetical except (year)
    re.compile(r"\s+[-–—]\s+$"),  # Trailing dashes
    re.compile(r"^\s+|\s+$"),  # Leading/trailing whitespace
]


def clean_string(s: str) -> str:
    """Clean up a string for use as metadata."""
    if not s:
        return ""
    
    # Basic cleanup
    s = s.strip()
    
    # Remove common file artifacts
    s = re.sub(r"_+", " ", s)  # Underscores to spaces
    s = re.sub(r"\s+", " ", s)  # Collapse multiple spaces
    
    return s.strip()


def looks_like_person_name(text: str) -> bool:
    """
    Heuristic for author-like names.
    Keeps it conservative to avoid mislabeling titles as authors.
    """
    parts = [p for p in clean_string(text).split() if p]
    if not (2 <= len(parts) <= 4):
        return False

    for part in parts:
        if any(ch.isdigit() for ch in part):
            return False
        if len(part) <= 1:
            return False

    return True


def extract_year(text: str) -> tuple[Optional[int], str]:
    """
    Extract a year from text and return (year, remaining_text).
    """
    match = YEAR_PATTERN.search(text)
    if match:
        year = int(match.group(1))
        if 1900 <= year <= 2100:  # Sanity check
            remaining = text[:match.start()] + text[match.end():]
            return year, clean_string(remaining)
    return None, text


def extract_series(text: str) -> tuple[Optional[str], Optional[float], Optional[str]]:
    """
    Extract series name and number from text.
    Returns (series_name, series_index, remaining_text or title).
    """
    for pattern in SERIES_PATTERNS:
        match = pattern.match(text)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                # Pattern like "Series Name, Book 1"
                series = clean_string(groups[0])
                try:
                    index = float(groups[1])
                except ValueError:
                    index = None
                return series, index, None
            elif len(groups) == 3:
                # Pattern like "Series 01 - Title"
                series = clean_string(groups[0])
                try:
                    index = float(groups[1])
                except ValueError:
                    index = None
                title = clean_string(groups[2])
                return series, index, title
    
    return None, None, text


def extract_author_title(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extract author and title from "Author - Title" pattern.
    Returns (author, title).
    """
    match = AUTHOR_TITLE_PATTERN.match(text)
    if match:
        author = clean_string(match.group(1))
        title = clean_string(match.group(2))
        return author, title
    
    return None, text


def extract_quality(text: str) -> tuple[Optional[str], str]:
    """
    Extract quality indicator (Unabridged/Abridged) from text.
    Returns (quality, remaining_text).
    """
    for pattern, quality in QUALITY_PATTERNS:
        if pattern.search(text):
            remaining = pattern.sub("", text)
            return quality, clean_string(remaining)
    
    return None, text


def extract_narrator(text: str) -> tuple[Optional[str], str]:
    """
    Extract narrator name from text.
    Returns (narrator, remaining_text).
    """
    for pattern in NARRATOR_PATTERNS:
        match = pattern.search(text)
        if match:
            narrator = clean_string(match.group(1))
            remaining = text[:match.start()] + text[match.end():]
            return narrator, clean_string(remaining)
    
    return None, text


def parse_filename(filename: str) -> ParsedFilename:
    """
    Parse a filename or folder name to extract audiobook metadata.
    Uses multiple heuristics to identify common patterns.
    """
    result = ParsedFilename()
    
    # Remove extension if present
    name = Path(filename).stem if "." in filename else filename
    name = clean_string(name)
    
    if not name:
        return result
    
    confidence = 0.0
    remaining = name
    
    # Extract year first
    year, remaining = extract_year(remaining)
    if year:
        result.year = year
        confidence += 0.1
    
    # Extract quality
    quality, remaining = extract_quality(remaining)
    if quality:
        result.quality = quality
        confidence += 0.05
    
    # Extract narrator
    narrator, remaining = extract_narrator(remaining)
    if narrator:
        result.narrator = narrator
        confidence += 0.1
    
    # Try to extract series info
    series, series_index, title_from_series = extract_series(remaining)
    if series:
        result.series = series
        result.series_index = series_index
        confidence += 0.2
        if title_from_series:
            remaining = title_from_series
    
    # Try to extract author - title
    author, title = extract_author_title(remaining)
    if author and title:
        # Accept author-title even if author is longer; lower confidence if so.
        result.author = author
        result.title = title
        confidence += 0.3 if len(author) < len(title) else 0.2
    elif title:
        # Might just be a title
        result.title = clean_string(remaining)
        confidence += 0.1
    else:
        result.title = clean_string(remaining)
    
    # If we got title but no author, check if album/folder might have author
    if result.title and not result.author:
        # Title alone gets lower confidence
        confidence = max(confidence - 0.1, 0.1)
    
    result.confidence = min(confidence, 1.0)
    
    return result


def parse_folder_path(folder_path: Path) -> ParsedFilename:
    """
    Parse a folder path to extract metadata.
    Tries parent folders if the immediate folder name doesn't parse well.
    """
    # Try the folder name itself
    result = parse_filename(folder_path.name)
    
    # If confidence is low, try parent folder
    if result.confidence < 0.3 and folder_path.parent.name:
        parent_result = parse_filename(folder_path.parent.name)
        
        # Merge if parent has useful info
        if parent_result.author and not result.author:
            result.author = parent_result.author
            result.confidence += 0.1
        elif parent_result.title and not result.author and looks_like_person_name(parent_result.title):
            # Treat a parent folder that looks like a person as the author.
            result.author = parent_result.title
            result.confidence += 0.1
        if parent_result.series and not result.series:
            result.series = parent_result.series
            result.series_index = parent_result.series_index
            result.confidence += 0.1
    
    return result


def merge_metadata(
    parsed: ParsedFilename,
    audio_title: Optional[str] = None,
    audio_author: Optional[str] = None,
    audio_album: Optional[str] = None,
) -> ParsedFilename:
    """
    Merge parsed filename metadata with extracted audio metadata.
    Audio metadata takes precedence when available.
    """
    # Create a copy to avoid modifying original
    result = ParsedFilename(
        title=parsed.title,
        author=parsed.author,
        series=parsed.series,
        series_index=parsed.series_index,
        year=parsed.year,
        narrator=parsed.narrator,
        quality=parsed.quality,
        confidence=parsed.confidence,
    )
    
    # Override with audio metadata if available
    if audio_title and len(audio_title) > 2:
        result.title = audio_title
        result.confidence += 0.1
    
    if audio_author and len(audio_author) > 2:
        result.author = audio_author
        result.confidence += 0.1
    
    # Album might be the book title if we don't have one
    if audio_album and not result.title and len(audio_album) > 2:
        result.title = audio_album
        result.confidence += 0.05
    
    result.confidence = min(result.confidence, 1.0)
    
    return result
