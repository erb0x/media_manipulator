"""
Hashing utilities.
Centralizes file hashing to avoid duplicate implementations.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def compute_sha256(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Compute SHA-256 hash of a file using streaming reads.
    Keeps memory usage small even for large audiobook files.
    """
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256.update(chunk)

    return sha256.hexdigest()
