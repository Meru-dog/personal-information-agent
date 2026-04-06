from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

_DATE_PATTERN = re.compile(r"^(\d{4})(\d{2})(\d{2})")


def get_recording_date(audio_path: Path) -> datetime:
    """Derive the recording date from the filename (YYYYMMDD prefix) or fall back to mtime."""
    m = _DATE_PATTERN.match(audio_path.stem)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    # fallback: file modification time (iPhone preserves recording time on sync)
    return datetime.fromtimestamp(audio_path.stat().st_mtime)


class MarkdownWriter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def write_session(
        self,
        structured_memo: str,
        raw_text: str,
        audio_path: Path,
        recording_date: datetime,
        processed_at: datetime,
    ) -> Path:
        """Write one Markdown file per recording inside a YYYY-MM-DD directory."""
        date_str = recording_date.strftime("%Y-%m-%d")
        date_dir = self._settings.obsidian_vault / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        target = date_dir / (audio_path.stem + ".md")

        lines = [
            f"# {audio_path.stem}",
            "",
            f"録音日: {date_str}",
            f"音声ファイル: {audio_path.name}",
            f"処理日時: {processed_at.strftime('%Y-%m-%d %H:%M')}",
            "",
        ]

        if structured_memo:
            lines += ["## 要点（構造化メモ）", "", structured_memo, ""]

        lines += ["## 原文", "", raw_text, ""]

        target.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Saved: {target.relative_to(self._settings.obsidian_vault)}")
        return target
