# Changelog

## [0.1.0] - 2026-03-21

### Added
- CLI with 5 commands: `extract`, `digest`, `embed`, `search`, `stats`
- **extract**: reads Claude Code JSONL transcripts, detects projects automatically, optional markdown export
- **digest**: summarizes sessions using local LLMs via Ollama (default: `qwen3:14b`). Configurable model, incremental processing
- **embed**: generates vector embeddings for semantic search (`nomic-embed-text`)
- **search**: semantic search (cosine similarity) with automatic grep fallback
- **stats**: session overview by project with digest/embed coverage
- Storage backends: SQLite (default, zero deps) and MongoDB (opt-in)
- Configuration via `.env` file or environment variables
- Rich terminal output with tables and progress bars
- CI with GitHub Actions: lint (ruff) + tests across Python 3.11–3.14
