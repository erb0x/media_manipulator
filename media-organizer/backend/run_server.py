#!/usr/bin/env python3
"""
Entry point script for running the Media Organizer backend server.
Used by PyInstaller to create the standalone executable.
"""

import uvicorn


def main():
    """Run the FastAPI server."""
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8742,
        log_level="info",
        # Disable reload in packaged version
        reload=False,
    )


if __name__ == "__main__":
    main()
