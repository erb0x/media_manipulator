from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.media.parser import parse_filename, parse_folder_path, merge_metadata, ParsedFilename


class ParserTests(unittest.TestCase):
    def test_parse_filename_author_title_year_narrator_quality(self) -> None:
        parsed = parse_filename(
            "Brandon Sanderson - The Way of Kings (2010) [Michael Kramer] Unabridged"
        )

        self.assertEqual(parsed.author, "Brandon Sanderson")
        self.assertEqual(parsed.title, "The Way of Kings")
        self.assertEqual(parsed.year, 2010)
        self.assertEqual(parsed.narrator, "Michael Kramer")
        self.assertEqual(parsed.quality, "Unabridged")

    def test_parse_filename_series_with_title(self) -> None:
        parsed = parse_filename("The Expanse 01 - Leviathan Wakes")

        self.assertEqual(parsed.series, "The Expanse")
        self.assertEqual(parsed.series_index, 1)
        self.assertEqual(parsed.title, "Leviathan Wakes")

    def test_parse_folder_path_uses_parent_for_author(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            folder = Path(tmp_dir) / "Brandon Sanderson" / "The Way of Kings"
            parsed = parse_folder_path(folder)

            self.assertEqual(parsed.title, "The Way of Kings")
            self.assertEqual(parsed.author, "Brandon Sanderson")

    def test_merge_metadata_prefers_audio_title_and_author(self) -> None:
        parsed = ParsedFilename(title="Parsed Title", author="Parsed Author", confidence=0.2)

        merged = merge_metadata(
            parsed,
            audio_title="Audio Title",
            audio_author="Audio Author",
            audio_album="Audio Album",
        )

        self.assertEqual(merged.title, "Audio Title")
        self.assertEqual(merged.author, "Audio Author")


if __name__ == "__main__":
    unittest.main()
