from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from aiogram.types import FSInputFile, InputMediaPhoto

TELEGRAM_MEDIA_GROUP_MAX = 10
TELEGRAM_CAPTION_LIMIT = 1024
_PHOTO_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})


@dataclass(frozen=True)
class WelcomeContent:
    text: str
    photo_paths: list[Path] = field(default_factory=list)
    parse_mode: str = "MarkdownV2"

    @property
    def caption_fits(self) -> bool:
        return len(self.text) <= TELEGRAM_CAPTION_LIMIT

    def as_media_group(self) -> list[InputMediaPhoto]:
        if not self.photo_paths:
            return []
        media: list[InputMediaPhoto] = []
        for idx, path in enumerate(self.photo_paths):
            if idx == 0 and self.caption_fits:
                media.append(
                    InputMediaPhoto(
                        media=FSInputFile(path),
                        caption=self.text,
                        parse_mode=self.parse_mode,
                    )
                )
            else:
                media.append(InputMediaPhoto(media=FSInputFile(path)))
        return media


def load_welcome_content(markdown_path: Path, photos_dir: Path) -> WelcomeContent:
    if not markdown_path.is_file():
        raise FileNotFoundError(markdown_path)
    text = markdown_path.read_text(encoding="utf-8").strip()

    photo_paths: list[Path] = []
    if photos_dir.is_dir():
        photo_paths = sorted(
            (p for p in photos_dir.iterdir() if p.suffix.lower() in _PHOTO_SUFFIXES),
            key=lambda p: p.name,
        )[:TELEGRAM_MEDIA_GROUP_MAX]

    return WelcomeContent(text=text, photo_paths=photo_paths)
