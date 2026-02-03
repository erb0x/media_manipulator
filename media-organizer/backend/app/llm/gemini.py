"""
Gemini AI integration for metadata parsing and matching.
Uses Google's Gemini Flash for efficient processing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional
import google.generativeai as genai

from app.config import get_settings
from app.db.database import get_db


# Prompt version for cache invalidation
PROMPT_VERSION = "v1"


@dataclass
class ParsedMetadata:
    """Metadata parsed from a filename by LLM."""
    title: Optional[str] = None
    author: Optional[str] = None
    narrator: Optional[str] = None
    series: Optional[str] = None
    series_index: Optional[float] = None
    year: Optional[int] = None
    search_query: Optional[str] = None
    confidence: float = 0.0


# JSON schema for filename parsing
PARSE_FILENAME_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Book/audiobook title"},
        "author": {"type": "string", "description": "Author name"},
        "narrator": {"type": "string", "description": "Narrator name if present"},
        "series": {"type": "string", "description": "Series name if book is part of a series"},
        "series_index": {"type": "number", "description": "Position in series (e.g., 1, 2, 2.5)"},
        "year": {"type": "integer", "description": "Publication year"},
        "search_query": {"type": "string", "description": "Best query to search for this book"},
        "confidence": {"type": "number", "description": "Confidence score 0-1"},
    },
    "required": ["title", "search_query", "confidence"],
}


def get_gemini_model():
    """Initialize and return Gemini model."""
    settings = get_settings()
    
    if not settings.gemini_api_key:
        return None
    
    genai.configure(api_key=settings.gemini_api_key)
    
    # Use Flash for speed and efficiency
    return genai.GenerativeModel('gemini-1.5-flash')


async def get_cached_llm_response(
    file_hash: str,
    function_name: str,
) -> Optional[dict]:
    """Get cached LLM response from database."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT response_json FROM llm_cache
            WHERE file_hash = ? AND prompt_version = ? AND function_name = ?
            """,
            (file_hash, PROMPT_VERSION, function_name)
        )
        row = await cursor.fetchone()
    
    if row:
        try:
            return json.loads(row["response_json"])
        except json.JSONDecodeError:
            pass
    
    return None


async def set_cached_llm_response(
    file_hash: str,
    function_name: str,
    response: dict,
) -> None:
    """Cache an LLM response."""
    response_json = json.dumps(response)
    
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO llm_cache (file_hash, prompt_version, function_name, response_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(file_hash, prompt_version, function_name) DO UPDATE SET
                response_json = excluded.response_json,
                created_at = datetime('now')
            """,
            (file_hash, PROMPT_VERSION, function_name, response_json)
        )
        await db.commit()


def extract_json_from_response(text: str) -> Optional[dict]:
    """Extract JSON from LLM response text."""
    # Try to find JSON in markdown code block
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    
    # Try to parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON object in the text
    brace_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass
    
    return None


async def parse_filename(
    filename: str,
    folder_name: Optional[str] = None,
    file_hash: Optional[str] = None,
    use_cache: bool = True,
) -> ParsedMetadata:
    """
    Parse a messy filename into structured metadata using Gemini.
    
    Args:
        filename: The filename to parse
        folder_name: Optional parent folder name for context
        file_hash: File hash for caching
        use_cache: Whether to use cached responses
    
    Returns:
        ParsedMetadata with extracted fields
    """
    settings = get_settings()
    
    if not settings.enable_llm or not settings.gemini_api_key:
        return ParsedMetadata()
    
    # Check cache
    if file_hash and use_cache:
        cached = await get_cached_llm_response(file_hash, "parse_filename")
        if cached:
            return ParsedMetadata(**cached)
    
    model = get_gemini_model()
    if not model:
        return ParsedMetadata()
    
    # Build prompt
    context = f"Filename: {filename}"
    if folder_name:
        context += f"\nFolder: {folder_name}"
    
    prompt = f"""Parse this audiobook filename and extract metadata.

{context}

Rules:
- Extract title, author, narrator, series, series position, and year if present
- If series info is present, include the series name and position number
- Generate a good search query to find this audiobook
- Rate your confidence from 0 to 1

Respond with ONLY a JSON object matching this schema:
{json.dumps(PARSE_FILENAME_SCHEMA, indent=2)}"""
    
    try:
        response = model.generate_content(prompt)
        result_json = extract_json_from_response(response.text)
        
        if result_json:
            # Validate and create result
            result = ParsedMetadata(
                title=result_json.get("title"),
                author=result_json.get("author"),
                narrator=result_json.get("narrator"),
                series=result_json.get("series"),
                series_index=result_json.get("series_index"),
                year=result_json.get("year"),
                search_query=result_json.get("search_query"),
                confidence=result_json.get("confidence", 0.5),
            )
            
            # Cache result
            if file_hash and use_cache:
                await set_cached_llm_response(
                    file_hash,
                    "parse_filename",
                    {
                        "title": result.title,
                        "author": result.author,
                        "narrator": result.narrator,
                        "series": result.series,
                        "series_index": result.series_index,
                        "year": result.year,
                        "search_query": result.search_query,
                        "confidence": result.confidence,
                    }
                )
            
            return result
    
    except Exception as e:
        print(f"Gemini parse error: {e}")
    
    return ParsedMetadata()


async def parse_filenames_batch(
    items: list[dict],  # List of {"filename": str, "folder": str, "hash": str}
    use_cache: bool = True,
) -> list[ParsedMetadata]:
    """
    Parse multiple filenames in a batch for efficiency.
    
    Args:
        items: List of dicts with filename, folder, and hash keys
        use_cache: Whether to use cached responses
    
    Returns:
        List of ParsedMetadata in same order as input
    """
    settings = get_settings()
    
    if not settings.enable_llm or not settings.gemini_api_key:
        return [ParsedMetadata() for _ in items]
    
    results = []
    uncached_indices = []
    uncached_items = []
    
    # Check cache for each item
    for i, item in enumerate(items):
        if use_cache and item.get("hash"):
            cached = await get_cached_llm_response(item["hash"], "parse_filename")
            if cached:
                results.append(ParsedMetadata(**cached))
                continue
        
        results.append(None)  # Placeholder
        uncached_indices.append(i)
        uncached_items.append(item)
    
    if not uncached_items:
        return results
    
    model = get_gemini_model()
    if not model:
        return [r if r else ParsedMetadata() for r in results]
    
    # Build batch prompt (limit batch size)
    batch_size = 50
    for batch_start in range(0, len(uncached_items), batch_size):
        batch = uncached_items[batch_start:batch_start + batch_size]
        batch_indices = uncached_indices[batch_start:batch_start + batch_size]
        
        items_text = "\n".join([
            f"{i+1}. Filename: {item['filename']}" + 
            (f" | Folder: {item.get('folder', '')}" if item.get('folder') else "")
            for i, item in enumerate(batch)
        ])
        
        prompt = f"""Parse these audiobook filenames and extract metadata for each.

{items_text}

For each item, extract: title, author, narrator, series, series_index, year, search_query, confidence.

Respond with a JSON array where each element corresponds to an input item:
[{{"title": "...", "author": "...", ...}}, ...]"""
        
        try:
            response = model.generate_content(prompt)
            
            # Parse array response
            text = response.text
            
            # Find JSON array
            array_match = re.search(r'\[.*\]', text, re.DOTALL)
            if array_match:
                parsed_array = json.loads(array_match.group())
                
                for j, parsed in enumerate(parsed_array):
                    if j < len(batch):
                        idx = batch_indices[j]
                        result = ParsedMetadata(
                            title=parsed.get("title"),
                            author=parsed.get("author"),
                            narrator=parsed.get("narrator"),
                            series=parsed.get("series"),
                            series_index=parsed.get("series_index"),
                            year=parsed.get("year"),
                            search_query=parsed.get("search_query"),
                            confidence=parsed.get("confidence", 0.5),
                        )
                        results[idx] = result
                        
                        # Cache
                        if use_cache and batch[j].get("hash"):
                            await set_cached_llm_response(
                                batch[j]["hash"],
                                "parse_filename",
                                {
                                    "title": result.title,
                                    "author": result.author,
                                    "narrator": result.narrator,
                                    "series": result.series,
                                    "series_index": result.series_index,
                                    "year": result.year,
                                    "search_query": result.search_query,
                                    "confidence": result.confidence,
                                }
                            )
        
        except Exception as e:
            print(f"Gemini batch parse error: {e}")
    
    # Fill in any remaining None values
    return [r if r else ParsedMetadata() for r in results]


async def choose_best_match(
    file_info: dict,
    candidates: list[dict],
    file_hash: Optional[str] = None,
    use_cache: bool = True,
) -> Optional[int]:
    """
    Use LLM to choose the best match from provider search results.
    
    Args:
        file_info: Dict with filename, folder, extracted metadata
        candidates: List of provider results
        file_hash: File hash for caching
        use_cache: Whether to use cache
    
    Returns:
        Index of best candidate, or None if no good match
    """
    settings = get_settings()
    
    if not settings.enable_llm or not settings.gemini_api_key:
        return None
    
    if not candidates:
        return None
    
    # Check cache
    cache_key = f"match:{file_hash}" if file_hash else None
    if cache_key and use_cache:
        cached = await get_cached_llm_response(file_hash, "choose_best_match")
        if cached and "index" in cached:
            idx = cached["index"]
            if idx is not None and 0 <= idx < len(candidates):
                return idx
    
    model = get_gemini_model()
    if not model:
        return None
    
    # Build prompt
    file_desc = f"Filename: {file_info.get('filename', 'Unknown')}"
    if file_info.get('folder'):
        file_desc += f"\nFolder: {file_info['folder']}"
    if file_info.get('title'):
        file_desc += f"\nExtracted title: {file_info['title']}"
    if file_info.get('author'):
        file_desc += f"\nExtracted author: {file_info['author']}"
    
    candidates_text = "\n".join([
        f"{i+1}. {c.get('title', 'Unknown')} by {c.get('author', 'Unknown')}" +
        (f" (Series: {c['series']})" if c.get('series') else "") +
        (f" [{c.get('year', '')}]" if c.get('year') else "")
        for i, c in enumerate(candidates)
    ])
    
    prompt = f"""Choose the best matching audiobook from these candidates.

File:
{file_desc}

Candidates:
{candidates_text}

Respond with ONLY a JSON object:
{{"index": <1-based index of best match, or null if no good match>, "reason": "brief explanation"}}"""
    
    try:
        response = model.generate_content(prompt)
        result_json = extract_json_from_response(response.text)
        
        if result_json and "index" in result_json:
            idx = result_json["index"]
            
            if idx is None:
                return None
            
            # Convert to 0-based index
            idx = int(idx) - 1
            
            if 0 <= idx < len(candidates):
                # Cache result
                if file_hash and use_cache:
                    await set_cached_llm_response(
                        file_hash,
                        "choose_best_match",
                        {"index": idx, "reason": result_json.get("reason")}
                    )
                return idx
    
    except Exception as e:
        print(f"Gemini match error: {e}")
    
    return None
