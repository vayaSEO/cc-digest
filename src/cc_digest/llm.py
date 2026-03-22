"""Ollama client — shared LLM and embedding calls."""

from __future__ import annotations

import httpx

from cc_digest.config import Config


def check_ollama(cfg: Config) -> None:
    """Verify Ollama is reachable. Raises RuntimeError if not."""
    try:
        httpx.get(f"{cfg.ollama_url}/api/tags", timeout=5.0).raise_for_status()
    except Exception as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {cfg.ollama_url}\nMake sure Ollama is running: ollama serve"
        ) from exc


def chat(
    cfg: Config, prompt: str, *, model: str | None = None, system: str = "", think: bool = False
) -> str:
    """Send a chat request to Ollama and return the response text."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model or cfg.digest_model,
        "messages": messages,
        "stream": False,
        "think": think,
        "options": {"temperature": 0.3, "num_predict": 1024},
    }

    resp = httpx.post(
        f"{cfg.ollama_url}/api/chat",
        json=payload,
        timeout=300.0,
    )
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "")


def embed(cfg: Config, text: str) -> list[float]:
    """Get embedding vector from Ollama. Returns empty list on failure."""
    resp = httpx.post(
        f"{cfg.ollama_url}/api/embed",
        json={"model": cfg.embed_model, "input": text},
        timeout=30.0,
    )
    resp.raise_for_status()
    embeddings = resp.json().get("embeddings", [])
    return embeddings[0] if embeddings else []
