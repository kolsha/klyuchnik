from __future__ import annotations

from pathlib import Path

import pytest
from aiogram.types import FSInputFile, InputMediaPhoto

from klyuchnik.content import WelcomeContent, load_welcome_content


def _make_png(path: Path) -> None:
    path.write_bytes(b"\x89PNG\r\n\x1a\nfake")


def test_load_welcome_content_reads_text_and_photos(tmp_path: Path) -> None:
    (tmp_path / "welcome.md").write_text("Hello **world**", encoding="utf-8")
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    _make_png(photos_dir / "02.png")
    _make_png(photos_dir / "01.png")
    _make_png(photos_dir / "03.png")

    content = load_welcome_content(tmp_path / "welcome.md", photos_dir)

    assert isinstance(content, WelcomeContent)
    assert content.text == "Hello **world**"
    assert [p.name for p in content.photo_paths] == ["01.png", "02.png", "03.png"]


def test_load_welcome_content_without_photos(tmp_path: Path) -> None:
    (tmp_path / "welcome.md").write_text("Just text", encoding="utf-8")
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    content = load_welcome_content(tmp_path / "welcome.md", photos_dir)

    assert content.text == "Just text"
    assert content.photo_paths == []


def test_load_welcome_content_missing_markdown(tmp_path: Path) -> None:
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        load_welcome_content(tmp_path / "missing.md", photos_dir)


def test_load_welcome_content_caps_at_10_photos(tmp_path: Path) -> None:
    (tmp_path / "welcome.md").write_text("x", encoding="utf-8")
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    for i in range(15):
        _make_png(photos_dir / f"{i:02d}.png")

    content = load_welcome_content(tmp_path / "welcome.md", photos_dir)

    assert len(content.photo_paths) == 10


def test_welcome_content_as_media_group_attaches_caption_to_first(tmp_path: Path) -> None:
    (tmp_path / "welcome.md").write_text("Short caption", encoding="utf-8")
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    _make_png(photos_dir / "a.png")
    _make_png(photos_dir / "b.png")

    content = load_welcome_content(tmp_path / "welcome.md", photos_dir)
    media = content.as_media_group()

    assert len(media) == 2
    assert all(isinstance(m, InputMediaPhoto) for m in media)
    assert isinstance(media[0].media, FSInputFile)
    assert media[0].caption == "Short caption"
    assert media[0].parse_mode == "MarkdownV2"
    assert media[1].caption is None


def test_welcome_content_with_no_photos_media_group_is_empty(tmp_path: Path) -> None:
    (tmp_path / "welcome.md").write_text("text", encoding="utf-8")
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    content = load_welcome_content(tmp_path / "welcome.md", photos_dir)
    assert content.as_media_group() == []


def test_welcome_content_caption_split_when_too_long(tmp_path: Path) -> None:
    long_text = "x" * 1500
    (tmp_path / "welcome.md").write_text(long_text, encoding="utf-8")
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    _make_png(photos_dir / "a.png")

    content = load_welcome_content(tmp_path / "welcome.md", photos_dir)
    assert content.caption_fits is False
    media = content.as_media_group()
    assert media[0].caption is None  # caption will go as a separate message


def test_welcome_content_caption_fits_under_1024(tmp_path: Path) -> None:
    (tmp_path / "welcome.md").write_text("x" * 1024, encoding="utf-8")
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    _make_png(photos_dir / "a.png")

    content = load_welcome_content(tmp_path / "welcome.md", photos_dir)
    assert content.caption_fits is True
