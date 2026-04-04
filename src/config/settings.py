from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class WhisperConfig:
    model_size: str = "large-v2"
    device: str = "auto"
    compute_type: str = "int8"
    language: str = "ja"
    beam_size: int = 5


@dataclass
class WatcherConfig:
    poll_interval_seconds: int = 10
    file_stability_checks: int = 2
    supported_extensions: List[str] = field(
        default_factory=lambda: [".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac", ".opus", ".caf", ".mp4"]
    )


@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_file: str = "~/.voice_transcribe/app.log"
    max_bytes: int = 5 * 1024 * 1024
    backup_count: int = 3


@dataclass
class Settings:
    sync_folder: Path
    obsidian_vault: Path
    obsidian_subfolder: str
    whisper: WhisperConfig
    watcher: WatcherConfig
    filler_enabled: bool
    extra_fillers: List[str]
    logging: LoggingConfig

    @property
    def processed_dir(self) -> Path:
        return self.sync_folder / "processed"

    @property
    def failed_dir(self) -> Path:
        return self.sync_folder / "failed"


def _expand(path_str: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path_str)))


def load_settings(config_path: Path = Path("config.yaml")) -> Settings:
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw:
        raise ValueError("Config file is empty")

    for required in ("sync_folder", "obsidian_vault", "obsidian_subfolder"):
        if required not in raw:
            raise ValueError(f"Missing required config key: {required}")

    whisper_raw = raw.get("whisper", {})
    whisper = WhisperConfig(
        model_size=whisper_raw.get("model_size", "large-v2"),
        device=whisper_raw.get("device", "auto"),
        compute_type=whisper_raw.get("compute_type", "int8"),
        language=whisper_raw.get("language", "ja"),
        beam_size=whisper_raw.get("beam_size", 5),
    )

    watcher_raw = raw.get("watcher", {})
    watcher = WatcherConfig(
        poll_interval_seconds=watcher_raw.get("poll_interval_seconds", 10),
        file_stability_checks=watcher_raw.get("file_stability_checks", 2),
        supported_extensions=watcher_raw.get(
            "supported_extensions",
            [".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac", ".opus", ".caf", ".mp4"],
        ),
    )

    filler_raw = raw.get("filler_removal", {})
    filler_enabled = filler_raw.get("enabled", True)
    extra_fillers = filler_raw.get("extra_fillers", [])

    logging_raw = raw.get("logging", {})
    logging_cfg = LoggingConfig(
        level=logging_raw.get("level", "INFO"),
        log_file=logging_raw.get("log_file", "~/.voice_transcribe/app.log"),
        max_bytes=logging_raw.get("max_bytes", 5 * 1024 * 1024),
        backup_count=logging_raw.get("backup_count", 3),
    )

    return Settings(
        sync_folder=_expand(raw["sync_folder"]),
        obsidian_vault=_expand(raw["obsidian_vault"]),
        obsidian_subfolder=raw["obsidian_subfolder"],
        whisper=whisper,
        watcher=watcher,
        filler_enabled=filler_enabled,
        extra_fillers=extra_fillers,
        logging=logging_cfg,
    )
