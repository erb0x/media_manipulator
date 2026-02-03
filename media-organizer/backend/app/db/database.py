"""
Database connection and initialization for Media Organizer.
Uses aiosqlite for async SQLite operations.
"""

from __future__ import annotations

import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from app.config import ensure_database_dir


# Module-level database path
_db_path: Optional[Path] = None


def get_db_path() -> Path:
    """Get the database path, ensuring directory exists."""
    global _db_path
    if _db_path is None:
        _db_path = ensure_database_dir()
    return _db_path


def get_schema_path() -> Path:
    """Get the path to the schema.sql file."""
    return Path(__file__).parent / "schema.sql"


async def init_database() -> None:
    """Initialize the database with schema if needed."""
    db_path = get_db_path()
    schema_path = get_schema_path()
    
    async with aiosqlite.connect(db_path) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")
        
        # Read and execute schema
        schema_sql = schema_path.read_text()
        await db.executescript(schema_sql)
        await db.commit()
        
        print(f"Database initialized at: {db_path}")


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Async context manager for database connections.
    Use this for all database operations.
    """
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        # Enable foreign keys and return rows as dicts
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        yield db


async def get_db_connection() -> aiosqlite.Connection:
    """
    Get a database connection for dependency injection.
    Caller is responsible for closing.
    """
    db_path = get_db_path()
    db = await aiosqlite.connect(db_path)
    await db.execute("PRAGMA foreign_keys = ON")
    db.row_factory = aiosqlite.Row
    return db


class DatabaseManager:
    """
    Database manager for use as a FastAPI dependency.
    Provides connection lifecycle management.
    """
    
    def __init__(self):
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Establish database connection."""
        if self._connection is None:
            db_path = get_db_path()
            self._connection = await aiosqlite.connect(db_path)
            await self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.row_factory = aiosqlite.Row
    
    async def disconnect(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
    
    @property
    def connection(self) -> aiosqlite.Connection:
        """Get the current connection."""
        if self._connection is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._connection


# Global database manager instance
db_manager = DatabaseManager()
