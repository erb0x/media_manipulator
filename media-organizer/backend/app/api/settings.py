"""
Settings API endpoints for the Media Organizer.
"""

from __future__ import annotations

from fastapi import APIRouter
from app.db.models import SettingsResponse, SettingsUpdateRequest
from app.db.database import get_db
from app.config import get_settings


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_current_settings() -> SettingsResponse:
    """Get current application settings."""
    settings = get_settings()
    
    # Get output_root from database if set
    output_root = None
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = 'output_root'"
        )
        row = await cursor.fetchone()
        if row:
            output_root = row["value"]
    
    return SettingsResponse(
        output_root=output_root,
        audiobook_folder_template=settings.audiobook_folder_template,
        audiobook_file_template=settings.audiobook_file_template,
        enable_llm=settings.enable_llm,
        enable_providers=settings.enable_providers,
        gemini_key_loaded=settings.gemini_api_key is not None,
        google_books_key_loaded=settings.google_books_api_key is not None,
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(request: SettingsUpdateRequest) -> SettingsResponse:
    """Update application settings."""
    async with get_db() as db:
        # Update each provided setting
        if request.output_root is not None:
            await db.execute(
                """
                INSERT INTO settings (key, value) VALUES ('output_root', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')
                """,
                (request.output_root,)
            )
        
        if request.audiobook_folder_template is not None:
            await db.execute(
                """
                INSERT INTO settings (key, value) VALUES ('audiobook_folder_template', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')
                """,
                (request.audiobook_folder_template,)
            )
        
        if request.audiobook_file_template is not None:
            await db.execute(
                """
                INSERT INTO settings (key, value) VALUES ('audiobook_file_template', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')
                """,
                (request.audiobook_file_template,)
            )
        
        if request.enable_llm is not None:
            await db.execute(
                """
                INSERT INTO settings (key, value) VALUES ('enable_llm', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')
                """,
                (str(request.enable_llm).lower(),)
            )
        
        if request.enable_providers is not None:
            await db.execute(
                """
                INSERT INTO settings (key, value) VALUES ('enable_providers', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')
                """,
                (str(request.enable_providers).lower(),)
            )
        
        await db.commit()
    
    # Return updated settings
    return await get_current_settings()


@router.get("/keys")
async def get_api_key_status() -> dict:
    """Get status of configured API keys."""
    settings = get_settings()
    return {
        "gemini": {
            "configured": settings.gemini_api_key is not None,
            "enabled": settings.enable_llm,
        },
        "google_books": {
            "configured": settings.google_books_api_key is not None,
            "enabled": settings.enable_providers,
        },
        "audnexus": {
            "configured": True,  # Public API, always available
            "enabled": settings.enable_providers,
            "note": "Using public API at api.audnex.us"
        },
    }
