from __future__ import annotations

from pathlib import Path

import pytest

from app.media import scanner
from app.media.audio_meta import AudioMetadata
from app.media.scanner import ScanOptions, discover_files, process_audio_file, scan_folder


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def test_discover_files_duration_filter(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "Library"
    audio_keep = _touch(root / "Audiobook" / "Book One" / "01 - Chapter.mp3")
    audio_skip = _touch(root / "Music" / "song.mp3")
    ebook = _touch(root / "Books" / "Some Book.epub")

    def fake_duration(path: Path) -> int:
        if path == audio_skip:
            return 100  # too short
        return 1900  # long enough

    monkeypatch.setattr(scanner, "get_audio_duration", fake_duration)

    options = ScanOptions(
        verify_audio_duration=True,
        min_audiobook_duration_seconds=1800,
    )
    discovery = discover_files(root, [], options=options)

    assert ebook in discovery.standalone_files
    assert audio_keep.parent in discovery.folder_audio_files
    assert audio_keep in discovery.folder_audio_files[audio_keep.parent]

    # Short audio file outside audiobook folders should be excluded.
    for files in discovery.folder_audio_files.values():
        assert audio_skip not in files


def test_scan_folder_groups_and_files_dry_run(tmp_path: Path) -> None:
    folder = tmp_path / "Audiobook" / "My Book"
    file_one = _touch(folder / "01 - Part One.mp3")
    file_two = _touch(folder / "02 - Part Two.mp3")

    options = ScanOptions(hash_files=False, extract_audio_metadata=False)
    result = scan_folder(tmp_path, options=options)

    assert result.errors == []
    assert len(result.groups) == 1
    assert len(result.files) == 2

    group = result.groups[0]
    assert group.folder_path == folder

    file_ids = {f.file_path: f for f in result.files}
    assert file_ids[file_one].group_id == group.id
    assert file_ids[file_two].group_id == group.id
    assert file_ids[file_one].track_number == 1
    assert file_ids[file_two].track_number == 2
    assert file_ids[file_one].file_hash is None
    assert file_ids[file_two].file_hash is None


def test_scan_folder_missing_root(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    result = scan_folder(missing, options=ScanOptions(hash_files=False, extract_audio_metadata=False))

    assert result.completed_at is not None
    assert result.errors


def test_process_audio_file_uses_metadata(tmp_path: Path) -> None:
    path = _touch(tmp_path / "Book.mp3")
    metadata = AudioMetadata(
        title="The Title",
        author="The Author",
        narrator="The Narrator",
        year=2020,
        duration_seconds=123,
        track_number=3,
    )

    scanned = process_audio_file(
        path,
        audio_metadata=metadata,
        options=ScanOptions(hash_files=False, extract_audio_metadata=False),
    )

    assert scanned.extracted_title == "The Title"
    assert scanned.extracted_author == "The Author"
    assert scanned.extracted_narrator == "The Narrator"
    assert scanned.extracted_year == 2020
    assert scanned.duration_seconds == 123
    assert scanned.track_number == 3
