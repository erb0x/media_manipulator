from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure "app" is importable when running this script directly.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.media.scanner import scan_folder, ScanOptions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run scanner for Media Organizer (no DB writes, no file moves)."
    )
    parser.add_argument("root", help="Root path to scan")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Substring exclusion pattern (can be repeated)",
    )
    parser.add_argument(
        "--hash",
        action="store_true",
        help="Compute file hashes (slower, but validates hashing flow)",
    )
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="Read audio metadata (slower, but validates mutagen reads)",
    )
    parser.add_argument(
        "--verify-duration",
        action="store_true",
        help="Filter short audio outside audiobook folders by duration",
    )
    parser.add_argument(
        "--min-duration",
        type=int,
        default=None,
        help="Minimum duration in seconds when --verify-duration is set",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write a JSON summary",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root)

    options = ScanOptions(
        hash_files=args.hash,
        extract_audio_metadata=args.metadata,
        verify_audio_duration=args.verify_duration,
        min_audiobook_duration_seconds=args.min_duration,
    )

    result = scan_folder(
        root_path=root,
        exclusion_patterns=args.exclude,
        options=options,
    )

    summary = {
        "scan_root": str(result.root_path),
        "files_found": len(result.files),
        "groups_found": len(result.groups),
        "errors": result.errors,
        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
    }

    print("Dry-run scan summary:")
    print(json.dumps(summary, indent=2))

    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote summary to {args.json_out}")

    return 0 if not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
