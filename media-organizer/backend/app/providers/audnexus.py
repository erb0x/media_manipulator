"""
Audnexus API integration for audiobook metadata.
Uses the public API at api.audnex.us for Audible-based metadata.
"""

from __future__ import annotations

import httpx
from dataclasses import dataclass, field
from typing import Optional
import re

from app.config import get_settings
from app.providers.cache import get_cached_response, set_cached_response, normalize_query


@dataclass
class AudiobookResult:
    """Result from Audnexus API."""
    asin: str
    title: str
    authors: list[str] = field(default_factory=list)
    narrators: list[str] = field(default_factory=list)
    series: Optional[str] = None
    series_position: Optional[float] = None
    publisher: Optional[str] = None
    release_date: Optional[str] = None
    description: Optional[str] = None
    runtime_minutes: Optional[int] = None
    cover_url: Optional[str] = None
    genres: list[str] = field(default_factory=list)
    language: Optional[str] = None
    
    @property
    def author(self) -> str:
        """Get primary author as string."""
        return self.authors[0] if self.authors else ""
    
    @property
    def narrator(self) -> str:
        """Get primary narrator as string."""
        return self.narrators[0] if self.narrators else ""
    
    @property
    def year(self) -> Optional[int]:
        """Extract year from release date."""
        if not self.release_date:
            return None
        match = re.match(r'(\d{4})', self.release_date)
        if match:
            return int(match.group(1))
        return None
    
    @property
    def duration_hours(self) -> Optional[float]:
        """Get runtime in hours."""
        if self.runtime_minutes:
            return round(self.runtime_minutes / 60, 1)
        return None
    
    def to_dict(self) -> dict:
        return {
            "asin": self.asin,
            "title": self.title,
            "authors": self.authors,
            "author": self.author,
            "narrators": self.narrators,
            "narrator": self.narrator,
            "series": self.series,
            "series_position": self.series_position,
            "publisher": self.publisher,
            "release_date": self.release_date,
            "year": self.year,
            "description": self.description,
            "runtime_minutes": self.runtime_minutes,
            "duration_hours": self.duration_hours,
            "cover_url": self.cover_url,
            "genres": self.genres,
            "language": self.language,
        }


def parse_audnexus_book(data: dict) -> AudiobookResult:
    """Parse an Audnexus book response into AudiobookResult."""
    # Extract authors
    authors = []
    for author in data.get("authors", []):
        if isinstance(author, dict):
            authors.append(author.get("name", ""))
        else:
            authors.append(str(author))
    
    # Extract narrators
    narrators = []
    for narrator in data.get("narrators", []):
        if isinstance(narrator, dict):
            narrators.append(narrator.get("name", ""))
        else:
            narrators.append(str(narrator))
    
    # Extract series info
    series_name = None
    series_position = None
    series_primary = data.get("seriesPrimary", {})
    if series_primary:
        series_name = series_primary.get("name")
        position = series_primary.get("position")
        if position:
            try:
                series_position = float(position)
            except ValueError:
                pass
    
    # Extract genres
    genres = []
    for genre in data.get("genres", []):
        if isinstance(genre, dict):
            genres.append(genre.get("name", ""))
        else:
            genres.append(str(genre))
    
    return AudiobookResult(
        asin=data.get("asin", ""),
        title=data.get("title", "Unknown Title"),
        authors=authors,
        narrators=narrators,
        series=series_name,
        series_position=series_position,
        publisher=data.get("publisherName"),
        release_date=data.get("releaseDate"),
        description=data.get("summary"),
        runtime_minutes=data.get("runtimeLengthMin"),
        cover_url=data.get("image"),
        genres=genres,
        language=data.get("language"),
    )


async def get_book_by_asin(
    asin: str,
    region: str = "us",
    use_cache: bool = True,
) -> Optional[AudiobookResult]:
    """
    Get audiobook details by ASIN.
    
    Args:
        asin: Amazon Standard Identification Number
        region: Amazon region (default: us)
        use_cache: Whether to use cached responses
    
    Returns:
        AudiobookResult if found, None otherwise
    """
    settings = get_settings()
    
    # Check cache
    cache_key = f"asin:{asin}:{region}"
    if use_cache:
        cached = await get_cached_response("audnexus", cache_key)
        if cached:
            return AudiobookResult(**cached)
    
    # Make API request
    url = f"{settings.audnexus_base_url}/books/{asin}"
    params = {"region": region}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        print(f"Audnexus API error: {e}")
        return None
    
    # Parse result
    result = parse_audnexus_book(data)
    
    # Cache result
    if use_cache:
        await set_cached_response("audnexus", cache_key, result.to_dict())
    
    return result


async def search_books(
    query: str,
    region: str = "us",
    max_results: int = 10,
    use_cache: bool = True,
) -> list[AudiobookResult]:
    """
    Search Audnexus for audiobooks.
    
    Note: Audnexus doesn't have a native search endpoint, so this
    uses a workaround of searching through authors or book titles.
    For better results, use get_book_by_asin when ASIN is known.
    
    Args:
        query: Search query
        region: Amazon region
        max_results: Maximum results to return
        use_cache: Whether to use cache
    
    Returns:
        List of AudiobookResult objects
    """
    settings = get_settings()
    
    # Check cache
    cache_key = normalize_query(f"search:{query}:{region}")
    if use_cache:
        cached = await get_cached_response("audnexus", cache_key)
        if cached:
            return [AudiobookResult(**item) for item in cached]
    
    # Audnexus search endpoint
    url = f"{settings.audnexus_base_url}/books"
    params = {
        "name": query,
        "region": region,
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            
            if response.status_code == 404:
                return []
            
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        print(f"Audnexus search error: {e}")
        return []
    
    # Parse results
    results = []
    items = data if isinstance(data, list) else [data]
    
    for item in items[:max_results]:
        try:
            result = parse_audnexus_book(item)
            results.append(result)
        except Exception as e:
            print(f"Error parsing Audnexus result: {e}")
    
    # Cache results
    if use_cache and results:
        await set_cached_response(
            "audnexus",
            cache_key,
            [r.to_dict() for r in results],
        )
    
    return results


async def get_author_books(
    author_asin: str,
    region: str = "us",
    use_cache: bool = True,
) -> list[AudiobookResult]:
    """
    Get all books by an author.
    
    Args:
        author_asin: Author's ASIN
        region: Amazon region
        use_cache: Whether to use cache
    
    Returns:
        List of AudiobookResult objects
    """
    settings = get_settings()
    
    # Check cache
    cache_key = f"author:{author_asin}:{region}"
    if use_cache:
        cached = await get_cached_response("audnexus", cache_key)
        if cached:
            return [AudiobookResult(**item) for item in cached]
    
    url = f"{settings.audnexus_base_url}/authors/{author_asin}"
    params = {"region": region}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            
            if response.status_code == 404:
                return []
            
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        print(f"Audnexus author error: {e}")
        return []
    
    # Get books from author response
    books = data.get("books", [])
    results = []
    
    for book_data in books:
        try:
            result = parse_audnexus_book(book_data)
            results.append(result)
        except Exception as e:
            print(f"Error parsing author book: {e}")
    
    # Cache results
    if use_cache and results:
        await set_cached_response(
            "audnexus",
            cache_key,
            [r.to_dict() for r in results],
        )
    
    return results
