from __future__ import annotations

import re
from typing import List

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Default Japanese filler words to remove.
# Sorted longest-first so longer matches take priority in the pattern.
DEFAULT_FILLERS = [
    "えーっと",
    "えーと",
    "えっと",
    "えー",
    "あのー",
    "あのう",
    "あの",
    "そのー",
    "そのう",
    "まぁ",
    "まあ",
    "うーん",
    "なんかその",
    "なんか",
    "ていうか",
    "みたいな",
    "うん",
    "ん",
]

# Boundaries that can surround a filler: whitespace, punctuation, line start/end
_BOUNDARY = r"(?:(?<=[　、。\s\n])|(?<=^))"
_BOUNDARY_END = r"(?=[　、。\s\n]|$)"


def _build_pattern(fillers: List[str]) -> re.Pattern:
    sorted_fillers = sorted(fillers, key=len, reverse=True)
    escaped = [re.escape(f) for f in sorted_fillers]
    joined = "|".join(escaped)
    # Match fillers that appear at a boundary (preceded by punctuation/space/start)
    # This avoids removing substrings from real words.
    pattern = rf"(?:^|(?<=[　、。\s\n]))(?:{joined})(?=[　、。\s\n]|$)"
    return re.compile(pattern, re.MULTILINE)


class FillerRemover:
    def __init__(self, extra_fillers: List[str] | None = None) -> None:
        all_fillers = DEFAULT_FILLERS + (extra_fillers or [])
        self._pattern = _build_pattern(all_fillers)

    def remove(self, text: str) -> str:
        """Remove filler words from transcribed text without altering meaning."""
        cleaned = self._pattern.sub("", text)
        # Collapse multiple spaces/newlines created by removal
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()
        logger.debug(f"Filler removal: {len(text)} -> {len(cleaned)} chars")
        return cleaned
