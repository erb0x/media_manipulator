"""
Configuration and settings for Media Organizer backend.
Loads API keys from files and manages application settings.
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


# Default paths for Windows
KEYS_DIR = Path(r"C:\Users\mendj\keys")


def load_key_from_file(filename: str) -> Optional[str]:
    """Load an API key from a text file."""
    key_path = KEYS_DIR / filename
    if key_path.exists():
        return key_path.read_text().strip()
    return None


class Settings(BaseSettings):
    """Application settings with API key loading."""
    
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8742
    debug: bool = False
    
    # Database
    database_path: Path = Field(
        default_factory=lambda: Path.home() / ".media-organizer" / "media_organizer.db"
    )
    
    # API Keys (loaded from files)
    gemini_api_key: Optional[str] = Field(default_factory=lambda: load_key_from_file("gemini_key_local.txt"))
    google_books_api_key: Optional[str] = Field(default_factory=lambda: load_key_from_file("google_books_api_key.txt"))
    
    # Feature flags
    enable_llm: bool = True
    enable_providers: bool = True
    
    # Audnexus public API (no key needed)
    audnexus_base_url: str = "https://api.audnex.us"
    
    # Scan settings
    audiobook_folder_pattern: str = "audiobook"  # Case-insensitive folder detection
    audiobook_extensions: List[str] = [".mp3", ".m4b", ".m4a", ".flac"]
    ebook_extensions: List[str] = [".epub", ".mobi", ".pdf", ".azw3"]
    comic_extensions: List[str] = [".cbz", ".cbr", ".cb7"]
    
    # Duration threshold for audiobook detection (30 minutes in seconds)
    audiobook_min_duration: int = 1800
    
    # Output settings (user-configurable)
    output_root: Optional[Path] = None
    
    # Naming templates
    audiobook_folder_template: str = "{author_sort}/{series}/{series_index} - {title} ({year})"
    audiobook_file_template: str = "{series_index} - {title}.{ext}"
    
    class Config:
        env_prefix = "MEDIA_ORGANIZER_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def ensure_database_dir() -> Path:
    """Ensure the database directory exists and return the database path."""
    settings = get_settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    return settings.database_path
