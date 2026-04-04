from __future__ import annotations

import re
from typing import List

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Conservative filler list per RDD-v2 section 12.1.
# なんか / まあ are intentionally excluded (high false-positive risk).
_DEFAULT_FILLERS = [
    "えーっと", "えーと", "えっと", "えー",
    "あのー", "あのう",
    "そのー", "そのう",
    "うーん",
]

_SENTENCE_ENDS = frozenset("。？！…")
_MERGE_TARGET_CHARS = 40   # accumulate fragments until this length
_PARAGRAPH_SENTENCES = 3   # sentences per paragraph (RDD-v2 §12.3: 2-4)
_PARAGRAPH_MAX_CHARS = 100  # also split if paragraph exceeds this


def _build_filler_pattern(fillers: List[str]) -> re.Pattern:
    sorted_fillers = sorted(fillers, key=len, reverse=True)
    escaped = [re.escape(f) for f in sorted_fillers]
    joined = "|".join(escaped)
    return re.compile(rf"(?:^|(?<=[　、。\s\n]))(?:{joined})(?=[　、。\s\n]|$)", re.MULTILINE)


class Formatter:
    def __init__(self, extra_fillers: List[str] | None = None) -> None:
        all_fillers = _DEFAULT_FILLERS + (extra_fillers or [])
        self._filler_pattern = _build_filler_pattern(all_fillers)

    def format(self, segments: List[str]) -> str:
        """Apply all formatting passes to raw transcription segments.

        Processing order:
          1. Remove consecutive exact duplicates
          2. Remove filler words
          3. Merge short fragments into sentences
          4. Add closing punctuation
          5. Split into readable paragraphs
        """
        lines = list(segments)
        lines = self._remove_consecutive_duplicates(lines)
        lines = self._remove_fillers(lines)
        lines = self._merge_short_lines(lines)
        lines = self._add_punctuation(lines)
        text = self._split_into_paragraphs(lines)
        logger.debug(f"Formatter: {len(segments)} segments → {len(lines)} sentences")
        return text

    # ------------------------------------------------------------------ #
    # Pass 1: consecutive exact-duplicate removal (RDD-v2 §6.1.5)
    # ------------------------------------------------------------------ #
    def _remove_consecutive_duplicates(self, lines: List[str]) -> List[str]:
        result: List[str] = []
        prev = None
        for line in lines:
            if line != prev:
                result.append(line)
            prev = line
        return result

    # ------------------------------------------------------------------ #
    # Pass 2: filler removal (RDD-v2 §6.1.1) — formatted version only
    # ------------------------------------------------------------------ #
    def _remove_fillers(self, lines: List[str]) -> List[str]:
        cleaned = []
        for line in lines:
            line = self._filler_pattern.sub("", line)
            line = re.sub(r"[ \t]{2,}", " ", line).strip()
            if line:
                cleaned.append(line)
        return cleaned

    # ------------------------------------------------------------------ #
    # Pass 3: short-line merging (RDD-v2 §6.1.2)
    # Accumulate fragments until MERGE_TARGET chars or sentence-end punct.
    # ------------------------------------------------------------------ #
    def _merge_short_lines(self, lines: List[str]) -> List[str]:
        result: List[str] = []
        buffer = ""

        for line in lines:
            if not line:
                continue
            buffer = buffer + line if buffer else line
            if len(buffer) >= _MERGE_TARGET_CHARS or buffer[-1] in _SENTENCE_ENDS:
                result.append(buffer)
                buffer = ""

        if buffer:
            result.append(buffer)

        return result

    # ------------------------------------------------------------------ #
    # Pass 4: punctuation completion (RDD-v2 §6.1.3)
    # Add 。 to lines that lack sentence-ending punctuation.
    # ------------------------------------------------------------------ #
    def _add_punctuation(self, lines: List[str]) -> List[str]:
        _ALL_ENDS = frozenset("。？！…、,.!?")
        return [
            line + "。" if line and line[-1] not in _ALL_ENDS else line
            for line in lines
        ]

    # ------------------------------------------------------------------ #
    # Pass 5: paragraph splitting (RDD-v2 §6.1.4, §12.3)
    # Group every PARAGRAPH_SENTENCES sentences; also break on char count.
    # ------------------------------------------------------------------ #
    def _split_into_paragraphs(self, lines: List[str]) -> str:
        paragraphs: List[List[str]] = []
        current: List[str] = []
        current_chars = 0

        for line in lines:
            current.append(line)
            current_chars += len(line)
            if len(current) >= _PARAGRAPH_SENTENCES or current_chars >= _PARAGRAPH_MAX_CHARS:
                paragraphs.append(current)
                current = []
                current_chars = 0

        if current:
            paragraphs.append(current)

        return "\n\n".join("\n".join(p) for p in paragraphs)
