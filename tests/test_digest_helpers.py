"""Tests for digest command helpers — filler detection, text condensation."""

from cc_digest.commands.digest import (
    _condense_assistant,
    _is_filler,
    _prepare_session_text,
    _truncate_code_blocks,
)


# --- _is_filler ---


def test_known_filler_strings():
    for text in ["ok", "sí", "si", "vale", "dale", "yes", "no", "", "Tool loaded."]:
        assert _is_filler(text), f"Expected '{text}' to be filler"


def test_filler_case_insensitive():
    assert _is_filler("OK")
    assert _is_filler("Vale")
    assert _is_filler("TOOL LOADED.")


def test_interrupted_request_is_filler():
    assert _is_filler("[request interrupted by user")
    assert _is_filler("  [Request interrupted  ")


def test_normal_text_not_filler():
    assert not _is_filler("Please fix the database migration")
    assert not _is_filler("I need help with Docker")


def test_filler_whitespace_padding():
    assert _is_filler("  ok  ")
    assert _is_filler("\n  \n")


# --- _truncate_code_blocks ---


def test_short_code_block_unchanged():
    text = "```python\nline1\nline2\n```"
    assert _truncate_code_blocks(text) == text


def test_long_code_block_truncated():
    lines = ["```python"] + [f"line{i}" for i in range(20)] + ["```"]
    text = "\n".join(lines)
    result = _truncate_code_blocks(text)
    assert "[..." in result
    assert "line0" in result
    assert "line19" not in result


def test_no_code_blocks_unchanged():
    text = "Just regular text without any code fences."
    assert _truncate_code_blocks(text) == text


def test_multiple_code_blocks():
    short = "```\na\nb\n```"
    long_lines = ["```python"] + [f"x{i}" for i in range(15)] + ["```"]
    long = "\n".join(long_lines)
    text = f"before\n{short}\nmiddle\n{long}\nafter"
    result = _truncate_code_blocks(text)
    assert "a\nb" in result  # short block intact
    assert "[..." in result  # long block truncated


def test_custom_max_lines():
    lines = ["```"] + [f"line{i}" for i in range(10)] + ["```"]
    text = "\n".join(lines)
    result = _truncate_code_blocks(text, max_lines=5)
    assert "line4" in result
    assert "line8" not in result


# --- _condense_assistant ---


def test_short_message_unchanged():
    text = "Short assistant reply."
    assert _condense_assistant(text) == text


def test_long_message_cut_at_paragraph():
    first_para = "A" * 200
    second_para = "B" * 400
    text = f"{first_para}\n\n{second_para}"
    result = _condense_assistant(text)
    assert result.endswith("[...]")
    assert "B" * 10 not in result


def test_hard_cap_at_800():
    text = "A" * 1000  # no paragraph break
    result = _condense_assistant(text)
    assert len(result) <= 800


# --- _prepare_session_text ---


def test_filters_filler_messages():
    messages = [
        {"role": "user", "content": "real question"},
        {"role": "assistant", "content": "real answer"},
        {"role": "user", "content": "ok"},
        {"role": "assistant", "content": "another answer"},
    ]
    result = _prepare_session_text(messages)
    assert "real question" in result
    assert "[User]: ok" not in result


def test_head_and_tail_kept():
    messages = []
    for i in range(20):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": f"message_{i}"})
    result = _prepare_session_text(messages)
    # First and last messages should be present
    assert "message_0" in result
    assert "message_19" in result


def test_respects_max_chars():
    messages = [
        {"role": "user", "content": "A" * 200},
        {"role": "assistant", "content": "B" * 200},
        {"role": "user", "content": "C" * 200},
    ]
    result = _prepare_session_text(messages, max_chars=300)
    assert "omitted" in result or len(result) <= 500


def test_empty_messages_returns_empty():
    assert _prepare_session_text([]) == ""
