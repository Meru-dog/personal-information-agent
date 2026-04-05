from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
あなたは音声メモの文字起こし原文を整理するアシスタントです。
入力された原文をもとに、以下のMarkdown形式で構造化メモを生成してください。

【出力フォーマット（厳守）】
### [全体タイトル]

#### [テーマ1見出し]
[要点 2〜4文]

#### [テーマ2見出し]
[要点 2〜4文]

【ルール】
- ### で始まる全体タイトルを必ず1つ付けること
- テーマは #### で区切ること（内容に応じて複数）
- 各テーマの要点は2〜4文程度の自然な日本語とすること
- 原文に存在しない事実を創作しないこと
- Markdownのみを出力し、前置き・後書きは不要\
"""


class SummarizationError(Exception):
    pass


class Summarizer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def summarize(
        self,
        raw_segments: List[str],
        audio_path: Path,
        timestamp: datetime,
    ) -> str:
        """Generate a structured memo from raw transcription segments using Qwen via Ollama."""
        cfg = self._settings.qwen

        try:
            import ollama
        except ImportError:
            raise SummarizationError(
                "ollama package is not installed. Run: pip install ollama"
            )

        raw_text = "\n".join(raw_segments)
        user_message = (
            f"音声ファイル: {audio_path.name}\n"
            f"録音時刻: {timestamp.strftime('%H:%M')}\n\n"
            f"【原文】\n{raw_text}"
        )

        logger.info(f"Summarizing with Qwen ({cfg.model})...")
        print("\n--- Qwen 構造化メモ生成中 ---\n", flush=True)

        try:
            client = ollama.Client(host=cfg.base_url)
            stream = client.chat(
                model=cfg.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                stream=True,
            )

            chunks: List[str] = []
            for chunk in stream:
                token = chunk["message"]["content"]
                print(token, end="", flush=True)
                chunks.append(token)

            print("\n--- 生成完了 ---\n", flush=True)
            result = "".join(chunks).strip()
            logger.info("Qwen summarization complete.")
            return result

        except SummarizationError:
            raise
        except Exception as e:
            raise SummarizationError(f"Qwen call failed: {e}") from e
