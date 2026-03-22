<p align="center">
  <img src="assets/cc-digest.jpg" width="640" alt="cc-digest">
  <h1 align="center">cc-digest</h1>
  <p align="center">
    ローカル LLM を使って <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a> のセッションを抽出・要約・検索。
  </p>
  <p align="center">
    <a href="https://github.com/vayaSEO/cc-digest/actions/workflows/ci.yml"><img src="https://github.com/vayaSEO/cc-digest/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <img src="https://img.shields.io/pypi/pyversions/cc-digest" alt="Python">
    <img src="https://img.shields.io/github/license/vayaSEO/cc-digest" alt="ライセンス">
  </p>
  <p align="center">
    <a href="README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.zh.md">中文</a> · <a href="README.ja.md">日本語</a>
  </p>
</p>

---

数千行の会話トランスクリプトを、簡潔で検索可能な要約に変換 — 完全オフライン、API キー不要。

<p align="center">
  <video src="https://github.com/user-attachments/assets/15970642-2674-4497-9e8d-eb18d3c60c64" width="700" controls></video>
</p>

## 機能

1. **Extract** — `~/.claude/projects/` から Claude Code の JSONL トランスクリプトを読み取り、構造化されたセッションデータを保存
2. **Digest** — [Ollama](https://ollama.com) 経由のローカル LLM を使用して、各セッションを約 10 個の箇条書きに要約
3. **Embed** — セマンティック検索用に要約のベクトル埋め込みを生成
4. **Search** — キーワードだけでなく、意味で関連する過去のセッションを検索
5. **Stats** — セッション履歴の概要

## インストール

```bash
pip install cc-digest
```

ソースからインストール：

```bash
git clone https://github.com/vayaSEO/cc-digest.git
cd cc-digest
pip install -e .
```

<details>
<summary>オプション：MongoDB バックエンド</summary>

```bash
pip install cc-digest[mongo]
```

`.env` ファイルで `STORAGE_BACKEND=mongo` と `MONGO_URI` を設定してください。

</details>

## クイックスタート

```bash
# 1. Claude Code のトランスクリプトからセッションを抽出
cc-digest extract

# 2. ローカル LLM で要約（Ollama の起動が必要）
cc-digest digest

# 3. セマンティック検索用のベクトル埋め込みを生成
cc-digest embed

# 4. セッションを検索
cc-digest search "FastAPI の CORS エラー"

# 5. 統計を表示
cc-digest stats
```

## 必要条件

- **Python** >= 3.11
- **Ollama**（要約と検索用）— [インストール](https://ollama.com/download)

```bash
# 推奨モデルをダウンロード
ollama pull qwen3:14b          # 要約
ollama pull nomic-embed-text   # 埋め込み
```

## コマンド

### `cc-digest extract`

JSONL トランスクリプトを読み取り、セッションを保存。

```bash
cc-digest extract                     # 全セッションを処理
cc-digest extract --session UUID      # 単一セッション
cc-digest extract --dry-run           # 書き込みなしでプレビュー
cc-digest extract --export-md         # .md ファイルも保存
cc-digest extract --min-messages 10   # 短いセッションをスキップ
```

### `cc-digest digest`

ローカル LLM でセッションを要約。

```bash
cc-digest digest                      # 未処理のセッションを要約
cc-digest digest --force              # すべて再要約
cc-digest digest --model gemma3:12b   # 別のモデルを使用
cc-digest digest --limit 10           # 最初の 10 件のみ
cc-digest digest --export-md          # 要約を .md として保存
```

### `cc-digest embed`

セマンティック検索用のベクトル埋め込みを生成。

```bash
cc-digest embed                       # 未処理の要約を埋め込み
cc-digest embed --force               # すべて再埋め込み
cc-digest embed --limit 10            # 最初の 10 件のみ
```

### `cc-digest search`

クエリでセッションを検索。

```bash
cc-digest search "docker compose の問題"
cc-digest search "auth middleware" --project myapp
cc-digest search "deploy" --mode grep    # テキスト検索を強制
cc-digest search "pipeline" --top 10     # より多くの結果
```

### `cc-digest stats`

セッションデータの概要。

```bash
cc-digest stats
cc-digest stats --project myapp
```

## 設定

`.env.example` を `.env` にコピーして必要に応じて調整：

```bash
cp .env.example .env
```

<details>
<summary>全設定変数</summary>

| 変数 | デフォルト | 説明 |
|---|---|---|
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects` | Claude Code がトランスクリプトを保存する場所 |
| `USER_DISPLAY_NAME` | `User` | エクスポートされた markdown でのユーザー名 |
| `STORAGE_BACKEND` | `sqlite` | `sqlite`（デフォルト）または `mongo` |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama サーバー URL |
| `DIGEST_MODEL` | `qwen3:14b` | 要約用 LLM モデル |
| `EMBED_MODEL` | `nomic-embed-text` | 埋め込み用モデル |
| `MIN_MESSAGES` | `4` | これより少ないメッセージのセッションをスキップ |

</details>

## ストレージ

**SQLite**（デフォルト）— 依存関係なし、すべて `~/.local/share/cc-digest/cc-digest.db` に保存。

**MongoDB**（オプション）— `pip install cc-digest[mongo]` でインストール、`.env` で `STORAGE_BACKEND=mongo` と `MONGO_URI` を設定。

## パフォーマンス

Apple Silicon M4 Pro で 8 モデルをベンチマーク — 30 セッション、67K ワード入力：

| モデル | パラメータ | 平均/セッション | 圧縮率 | 備考 |
|---|---|---|---|---|
| **`qwen3:14b`** | 14B | ~36s | 15:1 | **デフォルト** — 最高精度、会話言語を尊重 |
| `glm4:9b` | 9B | ~20s | 18:1 | 最速の信頼できるオプション |
| `mistral-nemo` | 12B | ~27s | 14:1 | 安定したオールラウンダー |
| `gemma3:12b` | 12B | ~34s | 10:1 | より詳細な出力 |
| `granite3.3:8b` | 8B | ~26s | 11:1 | 速度と品質の良いバランス |

> 精度重視なら `qwen3:14b`。高速化なら `glm4:9b` または `granite3.3:8b`。埋め込み + 検索は即時（<1s）。

<details>
<summary>完全なベンチマーク詳細（3 モデル追加 + 品質分析）</summary>

| モデル | パラメータ | 平均/セッション | 圧縮率 | 備考 |
|---|---|---|---|---|
| `qwen3.5:9b` | 9B | ~32s | 10:1 | サイズの割に遅い |
| `phi4-mini` | 3.8B | ~10s | 12:1 | 最速だが事実誤りを導入 |
| `nemotron-mini` | 4.2B | ~4s | 550:1 | 非推奨 — 8/30 空レスポンス |

**品質比較**（3 セッション並列比較）：
- `qwen3:14b`：最高の事実精度、構造化された箇条書き、会話言語を尊重
- `phi4-mini`：3.4 倍速いがあるセッションで決定を逆にした
- `granite3.3:8b`：速度と品質の間の堅実な中間点

セッション圧縮はスマートな head/tail 戦略を使用 — 冒頭と末尾のコンテキストを保持し、中間を圧縮。1K ～ 1M+ 文字のセッションに対応。

> 時間はセッションの長さとハードウェアにより異なります。GPU アクセラレーション推奨。

</details>

## 仕組み

```
~/.claude/projects/**/*.jsonl
         │
    cc-digest extract
         │
    ┌────▼────┐
    │ SQLite  │（または MongoDB）
    │ sessions│
    └────┬────┘
         │
    cc-digest digest (Ollama → qwen3:14b)
         │
    ┌────▼────┐
    │ SQLite  │
    │ digests │
    └────┬────┘
         │
    cc-digest embed (Ollama → nomic-embed-text)
         │
    ┌────▼──────┐
    │ SQLite    │
    │ embeddings│
    └────┬──────┘
         │
    cc-digest search "クエリ"
         │
    ┌────▼──┐
    │ 結果  │
    └───────┘
```

## ライセンス

MIT
