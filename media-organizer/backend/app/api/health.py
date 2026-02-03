"""
Health check endpoint for the Media Organizer API.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from app.db.models import HealthResponse
from app.db.database import get_db


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    Returns OK if the API is running and database is accessible.
    """
    try:
        async with get_db() as db:
            await db.execute("SELECT 1")
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="ok",
        version="0.1.0",
        database=db_status
    )
