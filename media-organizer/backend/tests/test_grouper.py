from __future__ import annotations

from pathlib import Path

from app.media.grouper import group_audiobook_files


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def test_group_audiobook_files_extracts_track_numbers(tmp_path: Path) -> None:
    folder = tmp_path / "My Book"
    file_one = _touch(folder / "01 - Chapter One.mp3")
    file_two = _touch(folder / "Track 02 - Chapter Two.mp3")

    group = group_audiobook_files(folder, [file_two, file_one], read_audio_metadata=False)
    assert group is not None

    sorted_files = group.get_sorted_files()
    assert [f.file_path for f in sorted_files] == [file_one, file_two]
    assert sorted_files[0].track_number == 1
    assert sorted_files[1].track_number == 2
