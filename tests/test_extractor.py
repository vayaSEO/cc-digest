"""Tests for cc_digest.extractor — core extraction logic."""

import json

from cc_digest.extractor import (
    extract_text_from_content,
    get_first_user_text,
    infer_project,
    process_jsonl,
    session_to_document,
    session_to_markdown,
    slugify,
)


# --- extract_text_from_content ---


def test_extract_plain_string():
    assert extract_text_from_content(["hello"]) == "hello"


def test_extract_text_block_dict():
    content = [{"type": "text", "text": "hello"}]
    assert extract_text_from_content(content) == "hello"


def test_ignores_non_text_block():
    content = [{"type": "tool_use", "name": "bash"}]
    assert extract_text_from_content(content) == ""


def test_ignores_system_reminder_string():
    content = ["<system-reminder>some internal info</system-reminder>"]
    assert extract_text_from_content(content) == ""


def test_ignores_system_reminder_text_block():
    content = [{"type": "text", "text": "<system-reminder>internal</system-reminder>"}]
    assert extract_text_from_content(content) == ""


def test_strips_inline_system_reminder():
    # Text must be >200 chars to avoid the short-message discard rule
    padding = "x" * 200
    text = f"{padding} Before reminder <system-reminder>secret</system-reminder> after reminder"
    content = [{"type": "text", "text": text}]
    result = extract_text_from_content(content)
    assert "secret" not in result
    assert "Before reminder" in result
    assert "after reminder" in result


def test_short_text_with_system_reminder_discarded():
    # Short text (<200 chars) containing system-reminder is discarded entirely
    text = "short <system-reminder>secret</system-reminder> text"
    content = [{"type": "text", "text": text}]
    result = extract_text_from_content(content)
    assert result == ""


def test_mixed_content_blocks():
    content = [
        "plain text",
        {"type": "text", "text": "text block"},
        {"type": "tool_use", "name": "bash"},
        {"type": "image", "source": {}},
    ]
    result = extract_text_from_content(content)
    assert "plain text" in result
    assert "text block" in result
    assert "bash" not in result


def test_empty_content_list():
    assert extract_text_from_content([]) == ""


# --- get_first_user_text ---


def test_returns_first_user_message():
    messages = [
        {"role": "assistant", "text": "Hi there"},
        {"role": "user", "text": "fix the bug"},
    ]
    assert get_first_user_text(messages) == "fix the bug"


def test_truncates_at_120_chars():
    long_text = "a" * 200
    messages = [{"role": "user", "text": long_text}]
    result = get_first_user_text(messages)
    assert len(result) == 123  # 120 + "..."
    assert result.endswith("...")


def test_collapses_whitespace():
    messages = [{"role": "user", "text": "fix   the\t  bug"}]
    assert get_first_user_text(messages) == "fix the bug"


def test_takes_first_line_only():
    messages = [{"role": "user", "text": "first line\nsecond line"}]
    assert get_first_user_text(messages) == "first line"


def test_returns_sin_titulo_when_no_user():
    assert get_first_user_text([]) == "sin-titulo"
    assert get_first_user_text([{"role": "assistant", "text": "hi"}]) == "sin-titulo"


# --- infer_project ---


def test_infer_from_cwd_known_root():
    assert infer_project("/Users/foo/Projects/myapp/src") == "myapp"


def test_infer_from_cwd_proyectos():
    assert infer_project("/Users/foo/Proyectos/myapp/src") == "myapp"


def test_infer_from_cwd_skips_utils():
    result = infer_project("/Users/foo/Projects/utils/something")
    # utils is skipped, falls through to "general"
    assert result == "general"


def test_infer_from_at_mention():
    result = infer_project("", first_message="@myapp/ fix the bug")
    assert result == "myapp"


def test_infer_from_jsonl_dir_name():
    result = infer_project("", "", jsonl_dir_name="-Users-foo-Projects-myapp")
    assert result == "myapp"


def test_infer_fallback_general():
    assert infer_project("") == "general"


def test_infer_cwd_takes_priority_over_mention():
    result = infer_project(
        "/Users/foo/Projects/realproject/src",
        first_message="@otherproject fix this",
    )
    assert result == "realproject"


def test_infer_case_insensitive_roots():
    result = infer_project("/home/user/proyectos/myapp")
    assert result == "myapp"


# --- slugify ---


def test_basic_slugify():
    assert slugify("Hello World!") == "hello-world"


def test_slugify_max_len():
    result = slugify("a very long title that should be truncated", max_len=10)
    assert len(result) <= 10


def test_slugify_empty_returns_session():
    assert slugify("") == "session"
    assert slugify("!!!") == "session"


# --- process_jsonl ---


def test_processes_valid_jsonl(tmp_path):
    jsonl_file = tmp_path / "test-session-id.jsonl"
    lines = [
        {
            "type": "user",
            "timestamp": "2026-03-20T10:00:00Z",
            "cwd": "/tmp/proj",
            "message": {"content": [{"type": "text", "text": "hello"}]},
        },
        {
            "type": "assistant",
            "timestamp": "2026-03-20T10:01:00Z",
            "message": {"content": [{"type": "text", "text": "hi there"}]},
        },
    ]
    jsonl_file.write_text("\n".join(json.dumps(line) for line in lines))

    result = process_jsonl(jsonl_file)
    assert result["session_id"] == "test-session-id"
    assert len(result["messages"]) == 2
    assert result["messages"][0]["role"] == "user"
    assert result["messages"][0]["text"] == "hello"
    assert result["first_ts"] == "2026-03-20T10:00:00Z"
    assert result["last_ts"] == "2026-03-20T10:01:00Z"
    assert result["cwd"] == "/tmp/proj"


def test_skips_malformed_lines(tmp_path):
    jsonl_file = tmp_path / "bad.jsonl"
    jsonl_file.write_text(
        "not valid json\n"
        + json.dumps({"type": "user", "timestamp": "t1", "message": {"content": ["valid"]}})
    )
    result = process_jsonl(jsonl_file)
    assert len(result["messages"]) == 1


def test_ignores_empty_text_messages(tmp_path):
    jsonl_file = tmp_path / "empty.jsonl"
    lines = [
        {"type": "user", "timestamp": "t1", "message": {"content": [{"type": "tool_use"}]}},
        {
            "type": "user",
            "timestamp": "t2",
            "message": {"content": [{"type": "text", "text": "real message"}]},
        },
    ]
    jsonl_file.write_text("\n".join(json.dumps(line) for line in lines))
    result = process_jsonl(jsonl_file)
    assert len(result["messages"]) == 1
    assert result["messages"][0]["text"] == "real message"


# --- session_to_document ---


def test_session_to_document_structure():
    data = {
        "session_id": "abc123",
        "messages": [{"role": "user", "text": "hello"}],
        "first_ts": "t1",
        "last_ts": "t2",
        "cwd": "/tmp",
    }
    doc = session_to_document(data, "myproject")
    assert doc["session_id"] == "abc123"
    assert doc["project"] == "myproject"
    assert doc["messages"][0]["content"] == "hello"
    assert "text" not in doc["messages"][0]  # renamed to content
    assert doc["message_count"] == 1


# --- session_to_markdown ---


def test_session_to_markdown_output():
    doc = {
        "title": "Test Session",
        "session_id": "abc123",
        "project": "myapp",
        "started_at": "2026-03-20T10:00:00Z",
        "ended_at": "2026-03-20T10:30:00Z",
        "message_count": 1,
        "cwd": "/tmp",
        "messages": [{"role": "user", "content": "hello"}],
    }
    md = session_to_markdown(doc, user_name="David")
    assert "# Test Session" in md
    assert "**David**" in md
    assert "abc123" in md
