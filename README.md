<p align="center">
  <img src="assets/cc-digest.jpg" width="640" alt="cc-digest">
  <h1 align="center">cc-digest</h1>
  <p align="center">
    Extract, digest and search your <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a> sessions using local LLMs.
  </p>
  <p align="center">
    <a href="https://github.com/vayaSEO/cc-digest/actions/workflows/ci.yml"><img src="https://github.com/vayaSEO/cc-digest/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <img src="https://img.shields.io/pypi/pyversions/cc-digest" alt="Python">
    <img src="https://img.shields.io/github/license/vayaSEO/cc-digest" alt="License">
  </p>
  <p align="center">
    <a href="README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.zh.md">中文</a> · <a href="README.ja.md">日本語</a>
  </p>
</p>

---

Turn thousands of lines of conversation transcripts into concise, searchable summaries — entirely offline, no API keys needed.

<p align="center">
  <video src="https://github.com/user-attachments/assets/15970642-2674-4497-9e8d-eb18d3c60c64" width="700" controls></video>
</p>

## What it does

1. **Extract** — reads Claude Code's JSONL transcripts from `~/.claude/projects/` and stores structured session data
2. **Digest** — summarizes each session into ~10 bullet points using a local LLM via [Ollama](https://ollama.com)
3. **Embed** — generates vector embeddings of digests for semantic search
4. **Search** — find relevant past sessions by meaning, not just keywords
5. **Stats** — overview of your session history

## Install

```bash
pip install cc-digest
```

Or from source:

```bash
git clone https://github.com/vayaSEO/cc-digest.git
cd cc-digest
pip install -e .
```

<details>
<summary>Optional: MongoDB backend</summary>

```bash
pip install cc-digest[mongo]
```

Set `STORAGE_BACKEND=mongo` and `MONGO_URI` in your `.env` file.

</details>

## Quick start

```bash
# 1. Extract sessions from Claude Code transcripts
cc-digest extract

# 2. Summarize with local LLM (requires Ollama running)
cc-digest digest

# 3. Generate embeddings for semantic search
cc-digest embed

# 4. Search your sessions
cc-digest search "CORS error in FastAPI"

# 5. View stats
cc-digest stats
```

## Requirements

- **Python** >= 3.11
- **Ollama** (for digest and search) — [install](https://ollama.com/download)

```bash
# Pull the recommended models
ollama pull qwen3:14b          # digest
ollama pull nomic-embed-text   # embeddings
```

## Commands

### `cc-digest extract`

Reads JSONL transcripts and stores sessions.

```bash
cc-digest extract                     # process all sessions
cc-digest extract --session UUID      # single session
cc-digest extract --dry-run           # preview without writing
cc-digest extract --export-md         # also save .md files
cc-digest extract --min-messages 10   # skip short sessions
```

### `cc-digest digest`

Summarizes sessions using a local LLM.

```bash
cc-digest digest                      # digest all unprocessed
cc-digest digest --force              # re-digest everything
cc-digest digest --model gemma3:12b   # use a different model
cc-digest digest --limit 10           # only digest first 10
cc-digest digest --export-md          # save digest .md files
```

### `cc-digest embed`

Generates vector embeddings for semantic search.

```bash
cc-digest embed                       # embed all unprocessed digests
cc-digest embed --force               # re-embed everything
cc-digest embed --limit 10            # only embed first 10
```

### `cc-digest search`

Find sessions by query.

```bash
cc-digest search "docker compose issue"
cc-digest search "auth middleware" --project myapp
cc-digest search "deploy" --mode grep    # force text search
cc-digest search "pipeline" --top 10     # more results
```

### `cc-digest stats`

Overview of your session data.

```bash
cc-digest stats
cc-digest stats --project myapp
```

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

<details>
<summary>All configuration variables</summary>

| Variable | Default | Description |
|---|---|---|
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects` | Where Claude Code stores transcripts |
| `USER_DISPLAY_NAME` | `User` | Your name in exported markdown |
| `STORAGE_BACKEND` | `sqlite` | `sqlite` (default) or `mongo` |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `DIGEST_MODEL` | `qwen3:14b` | LLM model for digesting |
| `EMBED_MODEL` | `nomic-embed-text` | Model for embeddings |
| `MIN_MESSAGES` | `4` | Skip sessions with fewer messages |

</details>

## Storage

**SQLite** (default) — zero dependencies, stores everything in `~/.local/share/cc-digest/cc-digest.db`.

**MongoDB** (opt-in) — install with `pip install cc-digest[mongo]`, set `STORAGE_BACKEND=mongo` and `MONGO_URI` in `.env`.

## Performance

8 models benchmarked on Apple Silicon M4 Pro — 30 sessions, 67K words input:

| Model | Params | Avg/session | Compression | Notes |
|---|---|---|---|---|
| **`qwen3:14b`** | 14B | ~36s | 15:1 | **Default** — best accuracy, respects conversation language |
| `glm4:9b` | 9B | ~20s | 18:1 | Fastest reliable option |
| `mistral-nemo` | 12B | ~27s | 14:1 | Solid all-rounder |
| `gemma3:12b` | 12B | ~34s | 10:1 | More detailed output |
| `granite3.3:8b` | 8B | ~26s | 11:1 | Good balance speed/quality |

> `qwen3:14b` for accuracy. `glm4:9b` or `granite3.3:8b` for faster runs. Embedding + search is instant (<1s).

<details>
<summary>Full benchmark details (3 more models + quality analysis)</summary>

| Model | Params | Avg/session | Compression | Notes |
|---|---|---|---|---|
| `qwen3.5:9b` | 9B | ~32s | 10:1 | Slower than expected for its size |
| `phi4-mini` | 3.8B | ~10s | 12:1 | Fastest, but introduced factual errors |
| `nemotron-mini` | 4.2B | ~4s | 550:1 | Not recommended — 8/30 empty responses |

**Quality comparison** (3-session side-by-side):
- `qwen3:14b`: best factual accuracy, structured bullets, respects conversation language
- `phi4-mini`: 3.4x faster but inverted a decision in one session
- `granite3.3:8b`: solid middle ground between speed and quality

Session condensation uses a smart head/tail strategy — keeps context from beginning and end, compresses the middle. Handles sessions from 1K to 1M+ characters.

> Times vary with session length and hardware. GPU acceleration recommended.

</details>

## How it works

```
~/.claude/projects/**/*.jsonl
         │
    cc-digest extract
         │
    ┌────▼────┐
    │ SQLite  │  (or MongoDB)
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
    cc-digest search "your query"
         │
    ┌────▼────┐
    │ Results │
    └─────────┘
```

## License

MIT
