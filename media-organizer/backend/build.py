#!/usr/bin/env python3
"""
Build script for packaging the Media Organizer backend with PyInstaller.
Produces a standalone executable that can be used as a Tauri sidecar.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_platform_suffix():
    """Get the platform-specific suffix for the binary name."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "windows":
        if machine in ["amd64", "x86_64"]:
            return "x86_64-pc-windows-msvc.exe"
        else:
            return "i686-pc-windows-msvc.exe"
    elif system == "darwin":
        if machine == "arm64":
            return "aarch64-apple-darwin"
        else:
            return "x86_64-apple-darwin"
    else:  # Linux
        if machine in ["aarch64", "arm64"]:
            return "aarch64-unknown-linux-gnu"
        else:
            return "x86_64-unknown-linux-gnu"


def main():
    """Build the backend executable using PyInstaller."""
    
    # Paths
    backend_dir = Path(__file__).parent
    app_dir = backend_dir / "app"
    dist_dir = backend_dir / "dist"
    build_dir = backend_dir / "build"
    tauri_binaries_dir = backend_dir.parent / "frontend" / "src-tauri" / "binaries"
    
    # Ensure we're in the backend directory
    os.chdir(backend_dir)
    
    # Clean previous builds
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    print("=" * 60)
    print("Building Media Organizer Backend")
    print("=" * 60)
    
    # Check PyInstaller is available
    try:
        import PyInstaller.__main__
    except ImportError:
        print("Error: PyInstaller not installed. Run: pip install pyinstaller")
        sys.exit(1)
    
    # Build the executable using PyInstaller API
    pyinstaller_args = [
        "--onefile",
        "--name", "media-organizer-backend",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--specpath", str(backend_dir),
        "--noconfirm",
        # Hidden imports for FastAPI and dependencies
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "fastapi",
        "--hidden-import", "app",
        "--hidden-import", "app.main",
        "--hidden-import", "aiosqlite",
        "--hidden-import", "mutagen",
        "--hidden-import", "httpx",
        # Add data files
        "--add-data", f"{app_dir / 'db' / 'schema.sql'}{os.pathsep}app/db",
        # Console mode for server logging
        "--console",
        # Entry point
        "run_server.py",
    ]
    
    print("\nRunning PyInstaller...")
    print("pyinstaller " + " ".join(pyinstaller_args))
    
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(pyinstaller_args)
    except Exception as e:
        print(f"\nPyInstaller build failed: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Build completed successfully!")
    print("=" * 60)
    
    # Get the output binary
    if platform.system() == "windows":
        binary_name = "media-organizer-backend.exe"
    else:
        binary_name = "media-organizer-backend"
    
    output_binary = dist_dir / binary_name
    
    if output_binary.exists():
        size_mb = output_binary.stat().st_size / (1024 * 1024)
        print(f"\nOutput: {output_binary}")
        print(f"Size: {size_mb:.1f} MB")
        
        # Copy to Tauri binaries directory with platform suffix
        tauri_binaries_dir.mkdir(parents=True, exist_ok=True)
        suffix = get_platform_suffix()
        target_name = f"media-organizer-backend-{suffix}"
        target_path = tauri_binaries_dir / target_name
        
        print(f"\nCopying to: {target_path}")
        shutil.copy2(output_binary, target_path)
        
        print("\n✓ Backend binary ready for Tauri sidecar")
    else:
        print("\nError: Output binary not found!")
        sys.exit(1)


if __name__ == "__main__":
    main()
