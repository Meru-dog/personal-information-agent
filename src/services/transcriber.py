from __future__ import annotations

from pathlib import Path
from typing import Generator, Tuple

from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TranscriptionError(Exception):
    pass


class Transcriber:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = None

    def load_model(self) -> None:
        """Load the Whisper model. Called once at startup."""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError("faster-whisper is not installed. Run: pip install faster-whisper")

        cfg = self._settings.whisper
        logger.info(f"Loading Whisper model: {cfg.model_size} (device={cfg.device}, compute={cfg.compute_type})")
        self._model = WhisperModel(
            cfg.model_size,
            device=cfg.device,
            compute_type=cfg.compute_type,
        )
        logger.info("Whisper model loaded.")

    def transcribe_stream(self, audio_path: Path) -> Generator[str, None, None]:
        """Yield transcribed text segment by segment as Whisper processes the audio.

        Each yielded value is the text of one segment. Progress is logged to console
        so the user can see how far along transcription is.
        """
        if self._model is None:
            self.load_model()

        cfg = self._settings.whisper
        logger.info(f"Transcribing: {audio_path.name}")

        try:
            segments, info = self._model.transcribe(
                str(audio_path),
                language=cfg.language,
                beam_size=cfg.beam_size,
                vad_filter=True,
            )
        except Exception as e:
            raise TranscriptionError(f"Failed to start transcription for {audio_path.name}: {e}") from e

        total_sec = info.duration
        total_min, total_s = divmod(int(total_sec), 60)
        logger.info(f"Audio duration: {total_min}:{total_s:02d} ({total_sec / 60:.1f} min) — transcribing...")

        try:
            for segment in segments:
                text = segment.text.strip()
                elapsed_min, elapsed_s = divmod(int(segment.end), 60)
                pct = int(segment.end / total_sec * 100) if total_sec > 0 else 0
                logger.info(f"  [{elapsed_min}:{elapsed_s:02d} / {total_min}:{total_s:02d} ({pct}%)] {text}")
                if text:
                    yield text
        except Exception as e:
            raise TranscriptionError(f"Transcription failed mid-stream for {audio_path.name}: {e}") from e

        logger.info(f"Transcription complete: {audio_path.name}")
