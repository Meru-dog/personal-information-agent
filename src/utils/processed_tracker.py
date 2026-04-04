from __future__ import annotations

import shutil
import traceback
from datetime import datetime
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_dirs(processed_dir: Path, failed_dir: Path) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)


def _timestamped_name(original: Path) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{ts}_{original.name}"


def mark_processed(file_path: Path, processed_dir: Path) -> None:
    dest = processed_dir / _timestamped_name(file_path)
    try:
        shutil.move(str(file_path), str(dest))
        logger.debug(f"Moved to processed: {dest.name}")
    except Exception as e:
        logger.error(f"Failed to move {file_path.name} to processed dir: {e}")


def mark_failed(file_path: Path, failed_dir: Path, error_msg: str) -> None:
    dest = failed_dir / _timestamped_name(file_path)
    try:
        shutil.move(str(file_path), str(dest))
        sidecar = dest.with_suffix(dest.suffix + ".error.txt")
        sidecar.write_text(error_msg, encoding="utf-8")
        logger.debug(f"Moved to failed: {dest.name}")
    except Exception as e:
        logger.error(f"Failed to move {file_path.name} to failed dir: {e}")


def is_already_processed(file_path: Path, processed_dir: Path) -> bool:
    """Check if a file with the same stem already exists in the processed directory."""
    stem = file_path.stem
    return any(p.stem.endswith(stem) for p in processed_dir.glob(f"*{file_path.suffix}"))
