from __future__ import annotations

import time
import threading
from pathlib import Path
from typing import Callable, Dict, List, Tuple

from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# (size, mtime, consecutive_stable_count)
_FileState = Tuple[int, float, int]


class FileWatcher:
    def __init__(self, settings: Settings, on_new_file: Callable[[Path], None]) -> None:
        self._settings = settings
        self._on_new_file = on_new_file
        self._stop_event = threading.Event()
        self._seen: Dict[Path, _FileState] = {}

    def scan_once(self) -> List[Path]:
        """Return audio files that are stable and ready for processing."""
        sync_folder = self._settings.sync_folder
        if not sync_folder.exists():
            logger.warning(f"Sync folder does not exist: {sync_folder}")
            return []

        exts = set(self._settings.watcher.supported_extensions)
        excluded = {self._settings.processed_dir, self._settings.failed_dir}

        candidates = [
            p for p in sync_folder.iterdir()
            if p.is_file() and p.suffix.lower() in exts and p.parent not in excluded
        ]

        ready = []
        for path in candidates:
            try:
                stat = path.stat()
                size, mtime = stat.st_size, stat.st_mtime
            except OSError:
                # File disappeared between listing and stat
                self._seen.pop(path, None)
                continue

            prev = self._seen.get(path)
            if prev is None:
                self._seen[path] = (size, mtime, 1)
            elif prev[0] == size and prev[1] == mtime:
                stable_count = prev[2] + 1
                self._seen[path] = (size, mtime, stable_count)
                if stable_count >= self._settings.watcher.file_stability_checks:
                    ready.append(path)
                    del self._seen[path]
            else:
                # File changed — reset counter
                self._seen[path] = (size, mtime, 1)

        return ready

    def run(self) -> None:
        """Blocking poll loop. Calls on_new_file for each stable audio file found."""
        logger.info(f"Watching: {self._settings.sync_folder}")
        logger.info(f"Poll interval: {self._settings.watcher.poll_interval_seconds}s")

        while not self._stop_event.is_set():
            ready_files = self.scan_once()
            for audio_path in ready_files:
                if self._stop_event.is_set():
                    break
                self._on_new_file(audio_path)

            self._stop_event.wait(timeout=self._settings.watcher.poll_interval_seconds)

        logger.info("File watcher stopped.")

    def stop(self) -> None:
        self._stop_event.set()
