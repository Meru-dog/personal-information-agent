from __future__ import annotations

import fcntl
from datetime import datetime
from pathlib import Path
from typing import Iterator

from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MarkdownWriter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def write_raw_stream(
        self,
        segments: Iterator[str],
        audio_path: Path,
        timestamp: datetime,
    ) -> tuple[Path, int]:
        """Stream raw transcription segments to YYYY-MM-DD.raw.md as they arrive.

        Writes the session header immediately, then flushes each segment so
        the file grows in real time. Returns (path, segments_written).
        """
        target = self._target_path(timestamp, suffix=".raw.md")
        segments_written = 0

        with target.open("a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                self._write_date_heading_if_new(f, target, timestamp)
                self._write_session_header(f, audio_path, timestamp)
                f.flush()

                for segment_text in segments:
                    if segment_text:
                        f.write(segment_text + "\n")
                        f.flush()
                        segments_written += 1
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

        logger.info(f"Raw saved: {target.name} ({segments_written} segments)")
        return target, segments_written

    def write_formatted(
        self,
        text: str,
        audio_path: Path,
        timestamp: datetime,
    ) -> Path:
        """Write formatted transcription to YYYY-MM-DD.md all at once."""
        target = self._target_path(timestamp, suffix=".md")

        with target.open("a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                self._write_date_heading_if_new(f, target, timestamp)
                self._write_session_header(f, audio_path, timestamp)
                f.write(text + "\n")
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

        logger.info(f"Formatted saved: {target.name}")
        return target

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _target_path(self, timestamp: datetime, suffix: str) -> Path:
        output_dir = self._settings.obsidian_vault / self._settings.obsidian_subfolder
        output_dir.mkdir(parents=True, exist_ok=True)
        date_str = timestamp.strftime("%Y-%m-%d")
        # suffix is either ".md" or ".raw.md"
        name = date_str + suffix
        return output_dir / name

    def _write_date_heading_if_new(self, f, target: Path, timestamp: datetime) -> None:
        """Write the top-level # YYYY-MM-DD heading for a brand new file."""
        if target.stat().st_size == 0:
            f.write(f"# {timestamp.strftime('%Y-%m-%d')}\n")

    def _write_session_header(self, f, audio_path: Path, timestamp: datetime) -> None:
        """Write the ## HH:MM heading and source/processed metadata."""
        time_str = timestamp.strftime("%H:%M")
        processed_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(
            f"\n## {time_str}\n"
            f"source: {audio_path.name}\n"
            f"processed: {processed_str}\n\n"
        )
