"""
Media Organizer Backend - FastAPI Application

Main entry point for the backend API.
Runs on localhost only for security.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.database import init_database, db_manager
from app.api import health, settings, scan, files, plans, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print("Starting Media Organizer Backend...")
    await init_database()
    await db_manager.connect()
    print("Database initialized and connected.")
    
    yield
    
    # Shutdown
    print("Shutting down Media Organizer Backend...")
    await db_manager.disconnect()
    print("Database connection closed.")


# Create FastAPI application
app = FastAPI(
    title="Media Organizer API",
    description="Backend API for the Media Organizer desktop application",
    version="0.1.0",
    lifespan=lifespan,
)


# CORS middleware for local UI
settings_instance = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",  # Tauri dev
        "http://localhost:5173",  # Vite dev
        "http://127.0.0.1:1420",
        "http://127.0.0.1:5173",
        "tauri://localhost",  # Tauri production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers
app.include_router(health.router)
app.include_router(settings.router, prefix="/api")
app.include_router(scan.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(plans.router, prefix="/api")
app.include_router(search.router, prefix="/api")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Media Organizer API",
        "version": "0.1.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings_instance.host,
        port=settings_instance.port,
        reload=settings_instance.debug,
    )
