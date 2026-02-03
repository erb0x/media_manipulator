"""
Provider response caching using SQLite.
Caches API responses to minimize external calls.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional, Any

from app.db.database import get_db


async def get_cached_response(
    provider: str,
    query_key: str,
) -> Optional[dict]:
    """
    Get a cached response for a provider query.
    
    Args:
        provider: Provider name (e.g., 'google_books', 'audnexus')
        query_key: Normalized query string
    
    Returns:
        Cached response dict or None if not found/expired
    """
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT response_json, expires_at
            FROM provider_cache
            WHERE provider = ? AND query_key = ?
            """,
            (provider, query_key)
        )
        row = await cursor.fetchone()
    
    if not row:
        return None
    
    # Check expiration
    if row["expires_at"]:
        expires_at = datetime.fromisoformat(row["expires_at"])
        if datetime.now() > expires_at:
            return None
    
    try:
        return json.loads(row["response_json"])
    except json.JSONDecodeError:
        return None


async def set_cached_response(
    provider: str,
    query_key: str,
    response: dict,
    ttl_days: int = 30,
) -> None:
    """
    Cache a provider response.
    
    Args:
        provider: Provider name
        query_key: Normalized query string
        response: Response data to cache
        ttl_days: Time-to-live in days
    """
    expires_at = datetime.now() + timedelta(days=ttl_days)
    response_json = json.dumps(response)
    
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO provider_cache (provider, query_key, response_json, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(provider, query_key) DO UPDATE SET
                response_json = excluded.response_json,
                expires_at = excluded.expires_at,
                created_at = datetime('now')
            """,
            (provider, query_key, response_json, expires_at.isoformat())
        )
        await db.commit()


def normalize_query(query: str) -> str:
    """Normalize a query string for cache key generation."""
    # Lowercase, strip, collapse whitespace
    import re
    normalized = query.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


async def clear_expired_cache() -> int:
    """
    Clear expired cache entries.
    
    Returns:
        Number of entries deleted
    """
    async with get_db() as db:
        cursor = await db.execute(
            """
            DELETE FROM provider_cache
            WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
            """
        )
        deleted = cursor.rowcount
        await db.commit()
    
    return deleted


async def clear_provider_cache(provider: str) -> int:
    """
    Clear all cache entries for a specific provider.
    
    Returns:
        Number of entries deleted
    """
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM provider_cache WHERE provider = ?",
            (provider,)
        )
        deleted = cursor.rowcount
        await db.commit()
    
    return deleted
