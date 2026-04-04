# 音声メモ自動文字起こし・Obsidian連携システム

スマートフォンで録音した音声ファイルを、PCローカルのWhisperで文字起こしし、Obsidian Vaultの日付別Markdownへ自動追記するシステムです。

## 機能

- 同期フォルダ（iCloud Drive、Google Drive等）を監視し、新規音声ファイルを自動検知
- `faster-whisper` によるローカル文字起こし（従量課金API不使用）
- 日本語フィラー語（えー、あのー、そのー等）の除去
- `YYYY-MM-DD.md` 形式でObsidian Vaultへ日付別追記
- 処理済みファイルの移動による重複処理防止

## セットアップ

### 1. システム依存パッケージのインストール

```bash
brew install ffmpeg
```

### 2. Pythonパッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. 設定ファイルの編集

`config.yaml` を開き、以下のパスを環境に合わせて設定してください。

```yaml
sync_folder: "~/iCloud Drive/VoiceMemos"   # 録音ファイルの同期先フォルダ
obsidian_vault: "~/Documents/MyVault"       # Obsidian Vaultのパス
```

その他の設定項目はコメントを参照してください。

### 4. 実行

**常駐監視モード（推奨）：**

```bash
python main.py
```

**ワンショットモード（既存ファイルを処理して終了）：**

```bash
python main.py --once
```

**設定ファイルを指定する場合：**

```bash
python main.py --config /path/to/config.yaml
```

## 出力形式

Obsidian Vault の `Daily Voice Logs/YYYY-MM-DD.md` へ以下の形式で追記されます。

```markdown
# 2026-04-03

## 09:10
今日考えたいのは、契約レビューをAIでどう補助できるかという点で…

## 13:42
午前中の続きだが、実務で使うには…
```

## フォルダ構成

```
sync_folder/
├── recording.m4a          # 処理待ちファイル
├── processed/             # 処理済みファイル（自動移動）
└── failed/                # 処理失敗ファイル（.error.txt 付き）

ObsidianVault/
└── Daily Voice Logs/
    ├── 2026-04-03.md
    └── 2026-04-04.md
```

## 対応音声フォーマット

`.m4a` `.mp3` `.wav` `.aac` `.ogg` `.flac` `.opus` `.caf` `.mp4`

## Whisperモデルの選択

`config.yaml` の `whisper.model_size` で変更できます。

| モデル | 精度 | 速度 | VRAM目安 |
|--------|------|------|---------|
| `large-v2` | 高（推奨） | 遅め | 10GB |
| `medium` | 中 | 中 | 5GB |
| `small` | 低め | 速い | 2GB |

CPUのみの場合は `compute_type: "int8"` のままで動作します（デフォルト）。

## ログ

ログは `~/.voice_transcribe/app.log` に保存されます（設定変更可）。

## プロジェクト構成

```
src/
├── config/settings.py          # 設定読み込み
├── services/
│   ├── file_watcher.py         # フォルダ監視（ポーリング方式）
│   ├── transcriber.py          # Whisper文字起こし
│   ├── filler_remover.py       # フィラー除去
│   └── markdown_writer.py      # Obsidian Markdown書き込み
└── utils/
    ├── logger.py               # ログ設定
    └── processed_tracker.py    # 処理済み管理
```
# personal-information-agent
