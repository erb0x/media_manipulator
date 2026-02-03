"""
Google Books API integration for metadata lookup.
"""

from __future__ import annotations

import httpx
from dataclasses import dataclass
from typing import Optional
import re

from app.config import get_settings
from app.providers.cache import get_cached_response, set_cached_response, normalize_query


GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"


@dataclass
class BookResult:
    """Result from Google Books API."""
    id: str
    title: str
    authors: list[str]
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    description: Optional[str] = None
    page_count: Optional[int] = None
    categories: list[str] = None
    cover_url: Optional[str] = None
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    
    @property
    def author(self) -> str:
        """Get primary author as string."""
        return self.authors[0] if self.authors else ""
    
    @property
    def year(self) -> Optional[int]:
        """Extract year from published date."""
        if not self.published_date:
            return None
        match = re.match(r'(\d{4})', self.published_date)
        if match:
            return int(match.group(1))
        return None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "author": self.author,
            "publisher": self.publisher,
            "published_date": self.published_date,
            "year": self.year,
            "description": self.description,
            "page_count": self.page_count,
            "categories": self.categories or [],
            "cover_url": self.cover_url,
            "isbn_10": self.isbn_10,
            "isbn_13": self.isbn_13,
        }


def parse_book_result(item: dict) -> BookResult:
    """Parse a Google Books API item into a BookResult."""
    volume_info = item.get("volumeInfo", {})
    
    # Extract ISBNs
    isbn_10 = None
    isbn_13 = None
    for identifier in volume_info.get("industryIdentifiers", []):
        if identifier.get("type") == "ISBN_10":
            isbn_10 = identifier.get("identifier")
        elif identifier.get("type") == "ISBN_13":
            isbn_13 = identifier.get("identifier")
    
    # Extract cover URL (prefer larger image)
    image_links = volume_info.get("imageLinks", {})
    cover_url = (
        image_links.get("thumbnail") or
        image_links.get("smallThumbnail")
    )
    
    return BookResult(
        id=item.get("id", ""),
        title=volume_info.get("title", "Unknown Title"),
        authors=volume_info.get("authors", []),
        publisher=volume_info.get("publisher"),
        published_date=volume_info.get("publishedDate"),
        description=volume_info.get("description"),
        page_count=volume_info.get("pageCount"),
        categories=volume_info.get("categories"),
        cover_url=cover_url,
        isbn_10=isbn_10,
        isbn_13=isbn_13,
    )


async def search_books(
    query: str,
    max_results: int = 10,
    use_cache: bool = True,
) -> list[BookResult]:
    """
    Search Google Books API for books matching a query.
    
    Args:
        query: Search query (title, author, or combined)
        max_results: Maximum number of results to return
        use_cache: Whether to use cached responses
    
    Returns:
        List of BookResult objects
    """
    settings = get_settings()
    
    if not settings.google_books_api_key:
        return []
    
    # Check cache
    cache_key = normalize_query(query)
    if use_cache:
        cached = await get_cached_response("google_books", cache_key)
        if cached:
            return [BookResult(**item) for item in cached]
    
    # Make API request
    params = {
        "q": query,
        "maxResults": max_results,
        "key": settings.google_books_api_key,
        "printType": "books",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        print(f"Google Books API error: {e}")
        return []
    
    # Parse results
    items = data.get("items", [])
    results = [parse_book_result(item) for item in items]
    
    # Cache results
    if use_cache and results:
        await set_cached_response(
            "google_books",
            cache_key,
            [r.to_dict() for r in results],
        )
    
    return results


async def search_by_isbn(isbn: str, use_cache: bool = True) -> Optional[BookResult]:
    """
    Search for a book by ISBN.
    
    Args:
        isbn: ISBN-10 or ISBN-13
        use_cache: Whether to use cached responses
    
    Returns:
        BookResult if found, None otherwise
    """
    # Clean ISBN
    isbn = re.sub(r'[^0-9X]', '', isbn.upper())
    
    results = await search_books(f"isbn:{isbn}", max_results=1, use_cache=use_cache)
    
    return results[0] if results else None


async def search_by_title_author(
    title: str,
    author: Optional[str] = None,
    use_cache: bool = True,
) -> list[BookResult]:
    """
    Search for books by title and optionally author.
    
    Args:
        title: Book title
        author: Optional author name
        use_cache: Whether to use cached responses
    
    Returns:
        List of BookResult objects
    """
    # Build query
    query_parts = []
    
    if title:
        query_parts.append(f"intitle:{title}")
    
    if author:
        query_parts.append(f"inauthor:{author}")
    
    if not query_parts:
        return []
    
    query = "+".join(query_parts)
    
    return await search_books(query, use_cache=use_cache)
