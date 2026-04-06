#!/usr/bin/env python3
"""
Voice Memo Auto-Transcription + Obsidian Integration
Entry point. Run with: python main.py [--config path/to/config.yaml] [--once]
"""
from __future__ import annotations

import argparse
import signal
import traceback
from datetime import datetime
from pathlib import Path

from src.config.settings import load_settings
from src.services.file_watcher import FileWatcher
from src.services.markdown_writer import MarkdownWriter, get_recording_date
from src.services.summarizer import Summarizer, SummarizationError
from src.services.transcriber import Transcriber, TranscriptionError
from src.utils import processed_tracker as tracker
from src.utils.logger import get_logger, setup_logging


def process_file(
    audio_path: Path,
    transcriber: Transcriber,
    summarizer: Summarizer,
    writer: MarkdownWriter,
    settings,
    logger,
) -> None:
    logger.info(f"Processing: {audio_path.name}")
    recording_date = get_recording_date(audio_path)
    processed_at = datetime.now()
    raw_segments: list[str] = []

    try:
        # Phase 1: transcribe
        for text in transcriber.transcribe_stream(audio_path):
            raw_segments.append(text)

        if not raw_segments:
            logger.warning(f"Empty transcription for {audio_path.name} — moving to failed.")
            tracker.mark_failed(audio_path, settings.failed_dir, "Transcription returned empty text.")
            return

        # Phase 2: structured memo via Qwen (optional)
        structured_memo = ""
        if settings.qwen.enabled:
            try:
                structured_memo = summarizer.summarize(raw_segments, audio_path, recording_date)
            except SummarizationError as e:
                logger.error(f"Summarization failed: {e}")
                structured_memo = f"*構造化メモの生成に失敗しました。エラー: {e}*"

        # Phase 3: write per-recording file in date directory
        raw_text = "\n".join(raw_segments)
        writer.write_session(structured_memo, raw_text, audio_path, recording_date, processed_at)
        tracker.mark_processed(audio_path, settings.processed_dir)
        logger.info(f"Done: {audio_path.name}")

    except TranscriptionError as e:
        logger.error(f"Transcription failed for {audio_path.name}: {e}")
        tracker.mark_failed(audio_path, settings.failed_dir, traceback.format_exc())

    except Exception as e:
        logger.error(f"Unexpected error processing {audio_path.name}: {e}", exc_info=True)
        tracker.mark_failed(audio_path, settings.failed_dir, traceback.format_exc())


def main() -> None:
    parser = argparse.ArgumentParser(description="Voice memo transcription daemon")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process all pending files once then exit (useful for cron)",
    )
    args = parser.parse_args()

    settings = load_settings(Path(args.config))

    setup_logging(
        level=settings.logging.level,
        log_file=settings.logging.log_file,
        max_bytes=settings.logging.max_bytes,
        backup_count=settings.logging.backup_count,
    )
    log = get_logger("main")

    tracker.ensure_dirs(settings.processed_dir, settings.failed_dir)

    transcriber = Transcriber(settings)
    transcriber.load_model()

    summarizer = Summarizer(settings)
    writer = MarkdownWriter(settings)

    def handle_file(audio_path: Path) -> None:
        process_file(audio_path, transcriber, summarizer, writer, settings, log)

    watcher = FileWatcher(settings, on_new_file=handle_file)

    def shutdown(signum, frame):
        log.info("Shutdown signal received.")
        watcher.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    if args.once:
        log.info("--once mode: processing all pending files then exiting.")
        exts = set(settings.watcher.supported_extensions)
        excluded = {settings.processed_dir, settings.failed_dir}
        audio_files = [
            p for p in settings.sync_folder.iterdir()
            if p.is_file() and p.suffix.lower() in exts and p.parent not in excluded
        ] if settings.sync_folder.exists() else []
        log.info(f"Found {len(audio_files)} file(s) to process.")
        for audio_path in audio_files:
            handle_file(audio_path)
        log.info("--once mode complete.")
    else:
        log.info("Starting continuous watch mode. Press Ctrl+C to stop.")
        watcher.run()


if __name__ == "__main__":
    main()
