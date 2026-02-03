from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.media import scanner
from app.media.audio_meta import AudioMetadata
from app.media.scanner import ScanOptions, discover_files, process_audio_file, scan_folder


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


class ScannerTests(unittest.TestCase):
    def test_discover_files_duration_filter(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "Library"
            audio_keep = _touch(root / "Audiobook" / "Book One" / "01 - Chapter.mp3")
            audio_skip = _touch(root / "Music" / "song.mp3")
            ebook = _touch(root / "Books" / "Some Book.epub")

            def fake_duration(path: Path) -> int:
                if path == audio_skip:
                    return 100
                return 1900

            options = ScanOptions(
                verify_audio_duration=True,
                min_audiobook_duration_seconds=1800,
            )

            with patch.object(scanner, "get_audio_duration", fake_duration):
                discovery = discover_files(root, [], options=options)

            self.assertIn(ebook, discovery.standalone_files)
            self.assertIn(audio_keep.parent, discovery.folder_audio_files)
            self.assertIn(audio_keep, discovery.folder_audio_files[audio_keep.parent])

            for files in discovery.folder_audio_files.values():
                self.assertNotIn(audio_skip, files)

    def test_scan_folder_groups_and_files_dry_run(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            folder = Path(tmp_dir) / "Audiobook" / "My Book"
            file_one = _touch(folder / "01 - Part One.mp3")
            file_two = _touch(folder / "02 - Part Two.mp3")

            options = ScanOptions(hash_files=False, extract_audio_metadata=False)
            result = scan_folder(Path(tmp_dir), options=options)

            self.assertEqual(result.errors, [])
            self.assertEqual(len(result.groups), 1)
            self.assertEqual(len(result.files), 2)

            group = result.groups[0]
            self.assertEqual(group.folder_path, folder)

            file_map = {f.file_path: f for f in result.files}
            self.assertEqual(file_map[file_one].group_id, group.id)
            self.assertEqual(file_map[file_two].group_id, group.id)
            self.assertEqual(file_map[file_one].track_number, 1)
            self.assertEqual(file_map[file_two].track_number, 2)
            self.assertIsNone(file_map[file_one].file_hash)
            self.assertIsNone(file_map[file_two].file_hash)

    def test_scan_folder_missing_root(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            missing = Path(tmp_dir) / "missing"
            result = scan_folder(missing, options=ScanOptions(hash_files=False, extract_audio_metadata=False))

            self.assertIsNotNone(result.completed_at)
            self.assertTrue(result.errors)

    def test_process_audio_file_uses_metadata(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            path = _touch(Path(tmp_dir) / "Book.mp3")
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

            self.assertEqual(scanned.extracted_title, "The Title")
            self.assertEqual(scanned.extracted_author, "The Author")
            self.assertEqual(scanned.extracted_narrator, "The Narrator")
            self.assertEqual(scanned.extracted_year, 2020)
            self.assertEqual(scanned.duration_seconds, 123)
            self.assertEqual(scanned.track_number, 3)


if __name__ == "__main__":
    unittest.main()
