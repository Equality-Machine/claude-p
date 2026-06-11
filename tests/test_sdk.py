from argparse import Namespace
import json

from claude_p import ClaudePOptions
from claude_p.cli import (
    build_tui_env,
    classify_failure,
    classify_interactive_block,
    extract_assistant_snapshot,
    is_terminal_assistant_message,
    maybe_accept_workspace_trust_prompt,
    read_persisted_assistant,
    recover_prompt_from_variadic_args,
    suppress_prompt_echo_block,
    timeout_expired,
    tool_approval_prompt_visible,
    workspace_trust_prompt_visible,
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


def test_cli_help_includes_safe_mode():
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "-m", "claude_p.cli", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--safe-mode" in proc.stdout
    assert "--no-auto-trust" in proc.stdout


def test_rate_limit_is_error_even_when_tui_contains_text():
    transcript = "You've hit your limit · resets May 17 at 10am (Asia/Shanghai)"
    assert classify_failure(transcript, "You've hit your limit", timed_out=False) == "rate_limit"


def test_auth_errors_are_detected():
    transcript = "Please run /login · API Error: 403 api key disabled or expired"
    assert classify_failure(transcript, "", timed_out=False) == "auth_blocked"


def test_workspace_trust_quick_safety_is_detected():
    transcript = "Quicksafetycheck:Isthisaprojectyoucreated? ❯1.Yes,Itrustthisfolder"
    assert classify_failure(transcript, "", timed_out=False) == "workspace_trust_blocked"


def test_workspace_trust_prompt_is_not_failure_after_assistant_answer():
    transcript = "Quicksafetycheck:Isthisaprojectyoucreated? ❯1.Yes,Itrustthisfolder"
    assert classify_failure(transcript, "CLAUDE_P_OK", timed_out=False) is None


def test_extract_assistant_snapshot_requires_line_start_marker():
    transcript = 'Review diff:\n+        "⏺ Done reviewing."\n'
    assert extract_assistant_snapshot(transcript) == ""


def test_extract_assistant_snapshot_reads_tui_line_marker():
    assert extract_assistant_snapshot("thinking\n⏺ Done reviewing.\n") == "Done reviewing."


def test_extract_assistant_snapshot_collects_continued_tui_chunks():
    transcript = (
        "⏺ First finding.\n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "❯ \n"
        "────────────────────────────────────────────────────────────────────────────────\n"
        "⏵⏵don'taskon(shift+tabtocycle)·esctointerrupt\n"
        "  Second finding.\n"
    )
    assert extract_assistant_snapshot(transcript) == "First finding.\n  Second finding."


def test_workspace_trust_prompt_detection_is_specific():
    assert workspace_trust_prompt_visible("Accessingworkspace: /repo Quicksafetycheck:Isthisaprojectyoucreated? ❯1.Yes,Itrustthisfolder")
    assert workspace_trust_prompt_visible("Accessingworkspace: /repo Quicksafetycheck:Isthisaprojectyoucreated? Entertoconfirm")
    assert not workspace_trust_prompt_visible("The assistant mentions workspace trust in prose.")


def test_workspace_trust_prompt_text_in_user_prompt_is_not_live_block():
    transcript = "Review diff: Accessingworkspace: /repo Quicksafetycheck:Isthisaprojectyoucreated? Entertoconfirm"
    assert classify_interactive_block(transcript, live_screen=True) is None


def test_tool_approval_wins_over_old_workspace_trust_prompt():
    transcript = (
        "Quicksafetycheck:Isthisaprojectyoucreated? ❯1.Yes,Itrustthisfolder\n"
        "Permission request: ❯1.Allow 2.Deny Entertoconfirm"
    )
    assert classify_interactive_block(transcript, live_screen=True) == "tool_approval_blocked"


def test_tool_approval_prompt_detection_requires_live_chrome():
    assert tool_approval_prompt_visible("Permission request: ❯1.Allow 2.Deny Entertoconfirm")
    assert not tool_approval_prompt_visible("Permission request: allow tool use or deny?")
    assert not tool_approval_prompt_visible('Permission deny rule "LS" matches no known tool. ❯ Try "create a file"')
    assert not tool_approval_prompt_visible("Permission handling mentions Allow/Deny/Enter to confirm in prose.")
    assert not tool_approval_prompt_visible("An example says: Do you want to allow Bash? ❯ 1. Yes 2. No")
    assert tool_approval_prompt_visible(
        'Permission deny rule "LS" matches no known tool.\n'
        "Permission request: ❯1.Allow 2.Deny Entertoconfirm"
    )


def test_tool_approval_text_in_user_prompt_is_not_live_block():
    transcript = "Review diff: Permission request: allow tool use or deny?"
    assert classify_interactive_block(transcript, live_screen=True) is None


def test_prompt_echo_tool_approval_is_suppressed_until_assistant_starts():
    prompt = "Review diff: Permission request: ❯1.Allow 2.Deny Entertoconfirm"
    assert suppress_prompt_echo_block("tool_approval_blocked", prompt, assistant_started=False) is None
    assert suppress_prompt_echo_block("tool_approval_blocked", prompt, assistant_started=True) == "tool_approval_blocked"
    assert suppress_prompt_echo_block("workspace_trust_blocked", prompt, assistant_started=False) == "workspace_trust_blocked"


def test_prompt_echo_tool_approval_suppression_ignores_unrelated_diagnostic():
    prompt = (
        'Permission deny rule "LS" matches no known tool.\n'
        "Review diff: Permission request: ❯1.Allow 2.Deny Entertoconfirm"
    )
    assert suppress_prompt_echo_block("tool_approval_blocked", prompt, assistant_started=False) is None


def test_prompt_echo_workspace_trust_is_suppressed_until_assistant_starts():
    prompt = "Accessingworkspace: /repo Quicksafetycheck:Isthisaprojectyoucreated? ❯1.Yes,Itrustthisfolder Security guide 2.No,exit Entertoconfirm"
    assert suppress_prompt_echo_block("workspace_trust_blocked", prompt, assistant_started=False) is None
    assert suppress_prompt_echo_block("workspace_trust_blocked", prompt, assistant_started=True) == "workspace_trust_blocked"


def test_broad_interactive_classifier_still_detects_diagnostic_tool_text():
    assert classify_interactive_block("Permission request: allow tool use or deny?") == "tool_approval_blocked"


def test_maybe_accept_workspace_trust_prompt_writes_enter_once():
    import os

    read_fd, write_fd = os.pipe()
    try:
        transcript = "Accessingworkspace: /repo Quicksafetycheck:Isthisaprojectyoucreated? ❯1.Yes,Itrustthisfolder Security guide 2.No,exit Entertoconfirm"

        assert maybe_accept_workspace_trust_prompt(write_fd, transcript, already_accepted=False)
        assert os.read(read_fd, 1) == b"\r"
        assert not maybe_accept_workspace_trust_prompt(write_fd, transcript, already_accepted=True)
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_maybe_accept_workspace_trust_prompt_requires_active_prompt():
    import os

    read_fd, write_fd = os.pipe()
    try:
        transcript = "Assistant said: QuickSafetyCheck and Yes, I trust this folder."

        assert not maybe_accept_workspace_trust_prompt(write_fd, transcript, already_accepted=False)
        assert not maybe_accept_workspace_trust_prompt(
            write_fd,
            "Accessingworkspace: /repo Quicksafetycheck:Isthisaprojectyoucreated? ❯1.Yes,Itrustthisfolder Security guide 2.No,exit Entertoconfirm",
            already_accepted=False,
            assistant_started=True,
        )
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_maybe_accept_workspace_trust_prompt_ignores_prompt_echo():
    import os

    read_fd, write_fd = os.pipe()
    try:
        transcript = "Accessingworkspace: /repo Quicksafetycheck:Isthisaprojectyoucreated? ❯1.Yes,Itrustthisfolder Security guide 2.No,exit Entertoconfirm"

        assert not maybe_accept_workspace_trust_prompt(
            write_fd,
            transcript,
            already_accepted=False,
            prompt=transcript,
        )
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_successful_assistant_text_is_not_failure():
    assert classify_failure("normal transcript", "CLAUDE_P_OK", timed_out=False) is None


def test_prompt_echo_tool_approval_is_not_failure_after_assistant_answer():
    transcript = (
        "Review diff: Permission request: ❯1.Allow 2.Deny Entertoconfirm\n"
        "⏺ Done reviewing."
    )
    assert classify_failure(transcript, "Done reviewing.", timed_out=False) is None


def test_tool_approval_text_after_assistant_answer_is_not_failure():
    transcript = (
        "Review diff: Permission request: ❯1.Allow 2.Deny Entertoconfirm\n"
        "⏺ I need to inspect a file.\n"
        "Permission request: ❯1.Allow 2.Deny Entertoconfirm"
    )
    assert classify_failure(transcript, "I need to inspect a file.", timed_out=False) is None


def test_timeout_expired_disabled_with_zero_or_negative_values():
    assert not timeout_expired(start=100.0, timeout_sec=0, now=10000.0)
    assert not timeout_expired(start=100.0, timeout_sec=-1, now=10000.0)


def test_timeout_expired_for_positive_values():
    assert not timeout_expired(start=100.0, timeout_sec=90, now=189.9)
    assert timeout_expired(start=100.0, timeout_sec=90, now=190.0)


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
