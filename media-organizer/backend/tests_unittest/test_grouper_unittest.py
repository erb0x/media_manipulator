from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.media.grouper import group_audiobook_files


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


class GrouperTests(unittest.TestCase):
    def test_group_audiobook_files_extracts_track_numbers(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            folder = Path(tmp_dir) / "My Book"
            file_one = _touch(folder / "01 - Chapter One.mp3")
            file_two = _touch(folder / "Track 02 - Chapter Two.mp3")

            group = group_audiobook_files(folder, [file_two, file_one], read_audio_metadata=False)
            self.assertIsNotNone(group)

            sorted_files = group.get_sorted_files()
            self.assertEqual([f.file_path for f in sorted_files], [file_one, file_two])
            self.assertEqual(sorted_files[0].track_number, 1)
            self.assertEqual(sorted_files[1].track_number, 2)


if __name__ == "__main__":
    unittest.main()
