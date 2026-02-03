"""
Audio metadata extraction using mutagen.
Supports MP3, M4B, M4A, and FLAC formats.
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import mutagen
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.id3 import ID3


@dataclass
class AudioMetadata:
    """Extracted audio metadata."""
    title: Optional[str] = None
    author: Optional[str] = None  # Artist/Author
    narrator: Optional[str] = None
    album: Optional[str] = None  # Often the book title
    series: Optional[str] = None
    series_index: Optional[float] = None
    year: Optional[int] = None
    duration_seconds: int = 0
    track_number: Optional[int] = None
    total_tracks: Optional[int] = None
    genre: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "author": self.author,
            "narrator": self.narrator,
            "album": self.album,
            "series": self.series,
            "series_index": self.series_index,
            "year": self.year,
            "duration_seconds": self.duration_seconds,
            "track_number": self.track_number,
            "total_tracks": self.total_tracks,
            "genre": self.genre,
        }


def extract_mp3_metadata(file_path: Path) -> AudioMetadata:
    """Extract metadata from MP3 file using ID3 tags."""
    metadata = AudioMetadata()
    
    try:
        audio = MP3(file_path)
        metadata.duration_seconds = int(audio.info.length)
        
        # Try to get ID3 tags
        if audio.tags:
            tags = audio.tags
            
            # Title (TIT2)
            if "TIT2" in tags:
                metadata.title = str(tags["TIT2"])
            
            # Artist/Author (TPE1)
            if "TPE1" in tags:
                metadata.author = str(tags["TPE1"])
            
            # Album (TALB) - often the audiobook title
            if "TALB" in tags:
                metadata.album = str(tags["TALB"])
            
            # Composer (TCOM) - sometimes used for narrator
            if "TCOM" in tags:
                metadata.narrator = str(tags["TCOM"])
            
            # Year (TYER or TDRC)
            if "TYER" in tags:
                try:
                    metadata.year = int(str(tags["TYER"])[:4])
                except ValueError:
                    pass
            elif "TDRC" in tags:
                try:
                    metadata.year = int(str(tags["TDRC"])[:4])
                except ValueError:
                    pass
            
            # Track number (TRCK)
            if "TRCK" in tags:
                track_str = str(tags["TRCK"])
                if "/" in track_str:
                    parts = track_str.split("/")
                    try:
                        metadata.track_number = int(parts[0])
                        metadata.total_tracks = int(parts[1])
                    except ValueError:
                        pass
                else:
                    try:
                        metadata.track_number = int(track_str)
                    except ValueError:
                        pass
            
            # Genre (TCON)
            if "TCON" in tags:
                metadata.genre = str(tags["TCON"])
            
            # Try to extract series info from content group (TIT1) or subtitle (TIT3)
            if "TIT1" in tags:
                series_info = str(tags["TIT1"])
                metadata.series = series_info
            
    except Exception as e:
        print(f"Error reading MP3 metadata from {file_path}: {e}")
    
    return metadata


def extract_m4b_metadata(file_path: Path) -> AudioMetadata:
    """Extract metadata from M4B/M4A file using MP4 tags."""
    metadata = AudioMetadata()
    
    try:
        audio = MP4(file_path)
        metadata.duration_seconds = int(audio.info.length)
        
        if audio.tags:
            tags = audio.tags
            
            # Title (\xa9nam)
            if "\xa9nam" in tags:
                metadata.title = tags["\xa9nam"][0]
            
            # Artist/Author (\xa9ART)
            if "\xa9ART" in tags:
                metadata.author = tags["\xa9ART"][0]
            
            # Album (\xa9alb)
            if "\xa9alb" in tags:
                metadata.album = tags["\xa9alb"][0]
            
            # Composer (\xa9wrt) - often the narrator
            if "\xa9wrt" in tags:
                metadata.narrator = tags["\xa9wrt"][0]
            
            # Year (\xa9day)
            if "\xa9day" in tags:
                year_str = tags["\xa9day"][0]
                try:
                    metadata.year = int(year_str[:4])
                except ValueError:
                    pass
            
            # Track number (trkn)
            if "trkn" in tags:
                track_info = tags["trkn"][0]
                if isinstance(track_info, tuple):
                    metadata.track_number = track_info[0]
                    metadata.total_tracks = track_info[1] if len(track_info) > 1 else None
            
            # Genre (\xa9gen)
            if "\xa9gen" in tags:
                metadata.genre = tags["\xa9gen"][0]
            
            # Try to get narrator from description or comment
            if metadata.narrator is None:
                if "desc" in tags:
                    desc = tags["desc"][0]
                    # Try to extract narrator from description
                    if "narrated by" in desc.lower():
                        # Simple extraction
                        idx = desc.lower().find("narrated by")
                        narrator_part = desc[idx + 12:].strip()
                        # Take until end or punctuation
                        for end_char in [".", ",", ";", "\n"]:
                            if end_char in narrator_part:
                                narrator_part = narrator_part[:narrator_part.find(end_char)]
                        metadata.narrator = narrator_part.strip()
    
    except Exception as e:
        print(f"Error reading M4B/M4A metadata from {file_path}: {e}")
    
    return metadata


def extract_flac_metadata(file_path: Path) -> AudioMetadata:
    """Extract metadata from FLAC file using Vorbis comments."""
    metadata = AudioMetadata()
    
    try:
        audio = FLAC(file_path)
        metadata.duration_seconds = int(audio.info.length)
        
        if audio.tags:
            tags = audio.tags
            
            # Title
            if "TITLE" in tags:
                metadata.title = tags["TITLE"][0]
            
            # Artist
            if "ARTIST" in tags:
                metadata.author = tags["ARTIST"][0]
            
            # Album
            if "ALBUM" in tags:
                metadata.album = tags["ALBUM"][0]
            
            # Composer (narrator)
            if "COMPOSER" in tags:
                metadata.narrator = tags["COMPOSER"][0]
            
            # Date/Year
            if "DATE" in tags:
                try:
                    metadata.year = int(tags["DATE"][0][:4])
                except ValueError:
                    pass
            
            # Track number
            if "TRACKNUMBER" in tags:
                try:
                    metadata.track_number = int(tags["TRACKNUMBER"][0])
                except ValueError:
                    pass
            
            # Total tracks
            if "TRACKTOTAL" in tags or "TOTALTRACKS" in tags:
                tag_name = "TRACKTOTAL" if "TRACKTOTAL" in tags else "TOTALTRACKS"
                try:
                    metadata.total_tracks = int(tags[tag_name][0])
                except ValueError:
                    pass
            
            # Genre
            if "GENRE" in tags:
                metadata.genre = tags["GENRE"][0]
    
    except Exception as e:
        print(f"Error reading FLAC metadata from {file_path}: {e}")
    
    return metadata


def extract_audio_metadata(file_path: Path) -> AudioMetadata:
    """
    Extract metadata from an audio file.
    Automatically detects format and uses appropriate extractor.
    """
    ext = file_path.suffix.lower()
    
    if ext == ".mp3":
        return extract_mp3_metadata(file_path)
    elif ext in [".m4b", ".m4a"]:
        return extract_m4b_metadata(file_path)
    elif ext == ".flac":
        return extract_flac_metadata(file_path)
    else:
        # Try generic mutagen
        try:
            audio = mutagen.File(file_path)
            if audio:
                return AudioMetadata(duration_seconds=int(audio.info.length))
        except Exception:
            pass
    
    return AudioMetadata()


def get_audio_duration(file_path: Path) -> int:
    """
    Get just the duration of an audio file in seconds.
    More efficient than full metadata extraction.
    """
    try:
        audio = mutagen.File(file_path)
        if audio and audio.info:
            return int(audio.info.length)
    except Exception:
        pass
    
    return 0
