"""Core extraction logic — reads Claude Code JSONL transcripts."""

from __future__ import annotations

import json
import re
from pathlib import Path


def slugify(text: str, max_len: int = 60) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len] or "session"


def extract_text_from_content(content: list) -> str:
    """Extract only text blocks from a content array, ignoring tools/images."""
    parts = []
    for block in content:
        if isinstance(block, str):
            if block.strip().startswith("<system-reminder"):
                continue
            parts.append(block)
        elif isinstance(block, dict):
            if block.get("type") == "text":
                text = block.get("text", "")
                if text.strip().startswith("<system-reminder"):
                    continue
                if "<system-reminder" in text and len(text) < 200:
                    continue
                text = re.sub(
                    r"<system-reminder>.*?</system-reminder>",
                    "",
                    text,
                    flags=re.DOTALL,
                ).strip()
                if text:
                    parts.append(text)
    return "\n".join(parts)


def get_first_user_text(messages: list[dict]) -> str:
    """Get the first user message as title."""
    for msg in messages:
        if msg["role"] == "user" and msg.get("text"):
            text = msg["text"].split("\n")[0].strip()
            text = re.sub(r"\s+", " ", text)
            return text[:120] + "..." if len(text) > 120 else text
    return "sin-titulo"


def infer_project(
    cwd: str,
    first_message: str = "",
    jsonl_dir_name: str = "",
    project_roots: tuple[str, ...] = ("Projects", "Proyectos", "dev", "workspace", "repos", "src"),
) -> str:
    """Infer project name from cwd, first user message (@mentions), or JSONL directory.

    Priority:
    1. cwd path — first directory after a known project_root
    2. @mention in first message (e.g. "@myapp/ let's fix..." → myapp)
    3. JSONL parent directory name (Claude Code project dir)
    4. Fallback: "general"
    """
    roots_lower = {r.lower() for r in project_roots}

    # 1. From cwd
    if cwd:
        parts = Path(cwd).parts
        for i, part in enumerate(parts):
            if part.lower() in roots_lower and i + 1 < len(parts):
                candidate = parts[i + 1]
                if candidate.lower() not in ("utils",):
                    return candidate

    # 2. From @mention in first message
    if first_message:
        match = re.search(r"@([\w-]+)/?", first_message)
        if match:
            return match.group(1).rstrip("/")

    # 3. From JSONL directory (e.g. "-Users-foo-Projects-myapp")
    if jsonl_dir_name:
        segments = [s for s in jsonl_dir_name.split("-") if s]
        if len(segments) > 1:
            for i, seg in enumerate(segments):
                if seg.lower() in roots_lower and i + 1 < len(segments):
                    rest = "-".join(segments[i + 1 :])
                    if rest:
                        return rest

    return "general"


def process_jsonl(filepath: str | Path) -> dict:
    """Process a single JSONL file and extract the dialogue."""
    filepath = Path(filepath)
    session_id = filepath.stem
    messages = []
    first_ts = None
    last_ts = None
    cwd = None

    with open(filepath, "r") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type")
            ts = obj.get("timestamp")

            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

            if msg_type == "user":
                if not cwd:
                    cwd = obj.get("cwd", "")
                msg = obj.get("message", {})
                content = msg.get("content", [])
                text = extract_text_from_content(content)
                if text.strip():
                    messages.append({"role": "user", "text": text, "timestamp": ts})

            elif msg_type == "assistant":
                msg = obj.get("message", {})
                content = msg.get("content", [])
                text = extract_text_from_content(content)
                if text.strip():
                    messages.append({"role": "assistant", "text": text, "timestamp": ts})

    return {
        "session_id": session_id,
        "messages": messages,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "cwd": cwd or "",
    }


def find_all_jsonl(projects_dir: Path) -> list[dict]:
    """Find all JSONL session files across all project directories."""
    results = []
    if not projects_dir.exists():
        return results
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        for jsonl_file in project_dir.glob("*.jsonl"):
            results.append(
                {
                    "path": str(jsonl_file),
                    "project_dir": project_dir.name,
                    "session_id": jsonl_file.stem,
                }
            )
    return results


def session_to_document(data: dict, project: str) -> dict:
    """Convert extracted session data into a storage document."""
    title = get_first_user_text(data["messages"])

    # Convert messages for storage (drop timestamps, rename text->content)
    messages = [{"role": m["role"], "content": m["text"]} for m in data["messages"]]

    return {
        "session_id": data["session_id"],
        "project": project,
        "title": title,
        "cwd": data.get("cwd", ""),
        "message_count": len(messages),
        "started_at": data.get("first_ts", ""),
        "ended_at": data.get("last_ts", ""),
        "messages": messages,
        "source_file": "",
    }


def session_to_markdown(doc: dict, user_name: str = "User") -> str:
    """Render a session document as markdown."""
    lines = []
    lines.append(f"# {doc.get('title', 'sin-titulo')}")
    lines.append("")
    lines.append(f"- **Session ID**: `{doc.get('session_id', '')}`")
    lines.append(f"- **Project**: {doc.get('project', '')}")
    if doc.get("started_at"):
        lines.append(f"- **Started**: {doc['started_at']}")
    if doc.get("ended_at"):
        lines.append(f"- **Ended**: {doc['ended_at']}")
    lines.append(f"- **Messages**: {doc.get('message_count', 0)}")
    if doc.get("cwd"):
        lines.append(f"- **CWD**: `{doc['cwd']}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    for msg in doc.get("messages", []):
        role_label = f"**{user_name}**" if msg["role"] == "user" else "**Claude**"
        lines.append(f"### {role_label}")
        lines.append("")
        lines.append(msg.get("content", ""))
        lines.append("")

    return "\n".join(lines)
