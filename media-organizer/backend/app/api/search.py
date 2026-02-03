"""
Search API endpoint for provider integrations.
Allows searching for metadata across multiple providers.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from typing import Optional

from app.db.models import ProviderSearchResult, ProviderSearchResponse
from app.providers.google_books import search_by_title_author as google_search
from app.providers.audnexus import search_books as audnexus_search, get_book_by_asin
from app.config import get_settings


router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=ProviderSearchResponse)
async def search_providers(
    query: str = Query(..., description="Search query"),
    title: Optional[str] = Query(None, description="Title to search"),
    author: Optional[str] = Query(None, description="Author to search"),
    asin: Optional[str] = Query(None, description="Audible ASIN"),
    provider: Optional[str] = Query(None, description="Specific provider to use"),
) -> ProviderSearchResponse:
    """
    Search for metadata across providers.
    
    Priority:
    1. ASIN lookup (if provided) - Audnexus
    2. Google Books - for book/audiobook search
    3. Audnexus - for audiobook-specific search
    """
    settings = get_settings()
    results = []
    
    # Construct query string for response
    query_str = query or f"{title or ''} {author or ''}".strip()
    
    # ASIN lookup takes priority
    if asin:
        audiobook = await get_book_by_asin(asin)
        if audiobook:
            results.append(ProviderSearchResult(
                provider="audnexus",
                id=audiobook.asin,
                title=audiobook.title,
                author=audiobook.author,
                narrator=audiobook.narrator,
                series=audiobook.series,
                series_index=audiobook.series_position,
                year=audiobook.year,
                description=audiobook.description,
                cover_url=audiobook.cover_url,
                confidence=0.95,  # High confidence for direct ASIN match
            ))
    
    # Search specified provider or all
    if provider is None or provider == "google_books":
        if settings.google_books_api_key:
            if title or author:
                google_results = await google_search(title or query, author)
            else:
                from app.providers.google_books import search_books
                google_results = await search_books(query)
            
            for book in google_results:
                results.append(ProviderSearchResult(
                    provider="google_books",
                    id=book.id,
                    title=book.title,
                    author=book.author,
                    year=book.year,
                    description=book.description,
                    cover_url=book.cover_url,
                    confidence=0.7,
                ))
    
    if provider is None or provider == "audnexus":
        if not asin:  # Don't duplicate ASIN search
            search_query = query or f"{title or ''} {author or ''}".strip()
            if search_query:
                audnexus_results = await audnexus_search(search_query)
                
                for audiobook in audnexus_results:
                    # Avoid duplicates from ASIN lookup
                    if not any(r.id == audiobook.asin for r in results):
                        results.append(ProviderSearchResult(
                            provider="audnexus",
                            id=audiobook.asin,
                            title=audiobook.title,
                            author=audiobook.author,
                            narrator=audiobook.narrator,
                            series=audiobook.series,
                            series_index=audiobook.series_position,
                            year=audiobook.year,
                            description=audiobook.description,
                            cover_url=audiobook.cover_url,
                            confidence=0.75,
                        ))
    
    # Sort by confidence
    results.sort(key=lambda r: r.confidence, reverse=True)
    
    return ProviderSearchResponse(
        query=query_str,
        results=results,
        cached=False,  # Could track this per-result
    )


@router.post("/apply/{file_id}")
async def apply_search_result(
    file_id: str,
    result: ProviderSearchResult,
) -> dict:
    """
    Apply a search result to a file's metadata.
    Sets the final metadata fields from the provider result.
    """
    from app.db.database import get_db
    
    async with get_db() as db:
        # Check if file exists
        cursor = await db.execute(
            "SELECT id FROM media_files WHERE id = ?",
            (file_id,)
        )
        if not await cursor.fetchone():
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="File not found")
        
        # Update metadata
        await db.execute(
            """
            UPDATE media_files SET
                final_title = ?,
                final_author = ?,
                final_narrator = ?,
                final_series = ?,
                final_series_index = ?,
                final_year = ?,
                provider_match_source = ?,
                provider_match_id = ?,
                confidence = ?,
                status = 'reviewed',
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                result.title,
                result.author,
                result.narrator,
                result.series,
                result.series_index,
                result.year,
                result.provider,
                result.id,
                result.confidence,
                file_id,
            )
        )
        await db.commit()
    
    return {"message": "Metadata applied", "file_id": file_id}


@router.post("/apply-group/{group_id}")
async def apply_search_result_to_group(
    group_id: str,
    result: ProviderSearchResult,
) -> dict:
    """
    Apply a search result to an audiobook group's metadata.
    """
    from app.db.database import get_db
    
    async with get_db() as db:
        # Check if group exists
        cursor = await db.execute(
            "SELECT id FROM audiobook_groups WHERE id = ?",
            (group_id,)
        )
        if not await cursor.fetchone():
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Update metadata
        await db.execute(
            """
            UPDATE audiobook_groups SET
                final_title = ?,
                final_author = ?,
                final_narrator = ?,
                final_series = ?,
                final_series_index = ?,
                final_year = ?,
                provider_match_source = ?,
                provider_match_id = ?,
                confidence = ?,
                status = 'reviewed',
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                result.title,
                result.author,
                result.narrator,
                result.series,
                result.series_index,
                result.year,
                result.provider,
                result.id,
                result.confidence,
                group_id,
            )
        )
        await db.commit()
    
    return {"message": "Metadata applied", "group_id": group_id}
