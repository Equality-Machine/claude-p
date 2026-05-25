from argparse import Namespace
import json

from claude_p import ClaudePOptions
from claude_p.cli import (
    ASSISTANT_MARKERS,
    build_tui_env,
    classify_failure,
    extract_assistant_snapshot,
    is_terminal_assistant_message,
    read_persisted_assistant,
    recover_prompt_from_variadic_args,
)


def test_options_command_includes_stream_json():
    cmd = ClaudePOptions(model="sonnet", tools="").command("hello")
    assert "--output-format" in cmd
    assert "stream-json" in cmd
    assert "--tools" in cmd
    assert "" in cmd


def test_console_scripts_declared():
    import tomllib
    from pathlib import Path

    data = tomllib.loads(Path("pyproject.toml").read_text())
    scripts = data["project"]["scripts"]
    assert scripts["claude-p"] == "claude_p.cli:main"
    assert scripts["claude-p.py"] == "claude_p.cli:main"


def test_rate_limit_is_error_even_when_tui_contains_text():
    transcript = "You've hit your limit · resets May 17 at 10am (Asia/Shanghai)"
    assert classify_failure(transcript, "You've hit your limit", timed_out=False) == "rate_limit"


def test_auth_errors_are_detected():
    transcript = "Please run /login · API Error: 403 api key disabled or expired"
    assert classify_failure(transcript, "", timed_out=False) == "auth_blocked"


def test_workspace_trust_quick_safety_is_detected():
    transcript = "Quicksafetycheck:Isthisaprojectyoucreated? ❯1.Yes,Itrustthisfolder"
    assert classify_failure(transcript, "", timed_out=False) == "workspace_trust_blocked"


def test_successful_assistant_text_is_not_failure():
    assert classify_failure("normal transcript", "CLAUDE_P_OK", timed_out=False) is None


def test_tool_use_assistant_message_is_not_terminal():
    assert not is_terminal_assistant_message({"stop_reason": "tool_use"})
    assert is_terminal_assistant_message({"stop_reason": "end_turn"})


def test_read_persisted_assistant_waits_for_terminal_message(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    session_id = "11111111-1111-4111-8111-111111111111"
    session_dir = tmp_path / ".claude" / "projects" / "-tmp-project"
    session_dir.mkdir(parents=True)
    path = session_dir / f"{session_id}.jsonl"
    lines = [
        {
            "type": "assistant",
            "message": {
                "id": "msg_tool",
                "model": "sonnet",
                "stop_reason": "tool_use",
                "content": [{"type": "text", "text": "Checking..."}],
            },
        },
        {
            "type": "assistant",
            "message": {
                "id": "msg_final",
                "model": "sonnet",
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "DONE"}],
            },
        },
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines))

    result = read_persisted_assistant(session_id, require_terminal=True)

    assert result is not None
    assert result["text"] == "DONE"
    assert result["terminal"] is True


def test_recover_prompt_from_variadic_tools(monkeypatch):
    args = Namespace(prompt=None, tools=[["Bash", "Edit", "hello"]])
    for attr in ["allowed_tools", "disallowed_tools", "add_dir", "files", "mcp_config", "betas"]:
        setattr(args, attr, [])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    recover_prompt_from_variadic_args(args)

    assert args.prompt == "hello"
    assert args.tools == ["Bash", "Edit"]


def test_subscription_backend_strips_provider_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "disabled-token")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.invalid")
    args = Namespace(term="xterm-256color", preserve_provider_env=False)

    env = build_tui_env(args)

    assert "ANTHROPIC_AUTH_TOKEN" not in env
    assert "ANTHROPIC_BASE_URL" not in env
    assert env["NO_COLOR"] == "1"


def test_assistant_markers_includes_both_legacy_and_current():
    assert "⏺" in ASSISTANT_MARKERS  # U+23FA (legacy claude < 2.1)
    assert "●" in ASSISTANT_MARKERS  # U+25CF (claude 2.1+)


def test_extract_assistant_snapshot_legacy_marker():
    transcript = "❯ ping\n⏺ pong\n"
    assert extract_assistant_snapshot(transcript) == "pong"


def test_extract_assistant_snapshot_current_marker():
    transcript = "❯ ping\n● pong\n"
    assert extract_assistant_snapshot(transcript) == "pong"


def test_extract_assistant_snapshot_prefers_latest_marker_across_variants():
    # If both markers appear, use the right-most one regardless of variant —
    # that's the most recent assistant turn in the transcript.
    transcript = "⏺ old answer\n❯ new prompt\n● new answer\n"
    assert extract_assistant_snapshot(transcript) == "new answer"

    transcript_reversed = "● old answer\n❯ new prompt\n⏺ new answer\n"
    assert extract_assistant_snapshot(transcript_reversed) == "new answer"


def test_extract_assistant_snapshot_returns_empty_when_no_marker():
    assert extract_assistant_snapshot("just some text without any marker") == ""
