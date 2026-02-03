from __future__ import annotations

from pathlib import Path

from app.media.parser import parse_filename, parse_folder_path, merge_metadata, ParsedFilename


def test_parse_filename_author_title_year_narrator_quality() -> None:
    parsed = parse_filename(
        "Brandon Sanderson - The Way of Kings (2010) [Michael Kramer] Unabridged"
    )

    assert parsed.author == "Brandon Sanderson"
    assert parsed.title == "The Way of Kings"
    assert parsed.year == 2010
    assert parsed.narrator == "Michael Kramer"
    assert parsed.quality == "Unabridged"


def test_parse_filename_series_with_title() -> None:
    parsed = parse_filename("The Expanse 01 - Leviathan Wakes")

    assert parsed.series == "The Expanse"
    assert parsed.series_index == 1
    assert parsed.title == "Leviathan Wakes"


def test_parse_folder_path_uses_parent_for_author(tmp_path: Path) -> None:
    folder = tmp_path / "Brandon Sanderson" / "The Way of Kings"
    parsed = parse_folder_path(folder)

    assert parsed.title == "The Way of Kings"
    assert parsed.author == "Brandon Sanderson"


def test_merge_metadata_prefers_audio_title_and_author() -> None:
    parsed = ParsedFilename(title="Parsed Title", author="Parsed Author", confidence=0.2)

    merged = merge_metadata(
        parsed,
        audio_title="Audio Title",
        audio_author="Audio Author",
        audio_album="Audio Album",
    )

    assert merged.title == "Audio Title"
    assert merged.author == "Audio Author"
