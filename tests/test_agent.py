import pytest
import subprocess
from letscode.agent import dispatch_tool, run_command, call_llm, dispatch_slash_command
from unittest.mock import patch, MagicMock


# ── Task 1: dispatch_tool ──────────────────────────────────────────────────

def test_dispatch_unknown_tool():
    result = dispatch_tool("nonexistent", {})
    assert result == {"error": "unknown tool: nonexistent"}

def test_dispatch_bad_args():
    # read_file expects 'filename', not 'wrong_param'
    result = dispatch_tool("read_file", {"wrong_param": "value"})
    assert "error" in result
    assert "bad arguments" in result["error"]

def test_dispatch_valid_tool(tmp_path):
    test_file = tmp_path / "hello.txt"
    test_file.write_text("world")
    result = dispatch_tool("read_file", {"filename": str(test_file)})
    assert result["content"] == "world"


# ── Task 2: run_command ────────────────────────────────────────────────────

def test_run_command_rejected():
    with patch("builtins.input", return_value="n"):
        result = run_command("echo hello")
    assert result == {"error": "command rejected by user"}

def test_run_command_accepted_stdout():
    with patch("builtins.input", return_value="y"):
        result = run_command("echo hello")
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]
    assert "stderr" in result

def test_run_command_nonzero_exit():
    with patch("builtins.input", return_value="y"):
        result = run_command("ls /this_path_does_not_exist_xyz_abc_123")
    assert result["exit_code"] != 0
    assert result["stderr"] != "" or result["stdout"] != ""

def test_run_command_timeout():
    with patch("builtins.input", return_value="y"):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sleep 60", 30)):
            result = run_command("sleep 60")
    assert result == {"error": "command timed out after 30s"}


# ── Task 3: streaming ──────────────────────────────────────────────────────

def _make_chunk(content):
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta.content = content
    return chunk

def test_call_llm_returns_full_text(capsys):
    chunks = [_make_chunk("Hello"), _make_chunk(" world")]
    with patch("letscode.agent.client") as mock_client:
        mock_client.chat.completions.create.return_value = iter(chunks)
        result = call_llm([{"role": "user", "content": "hi"}])
    assert result == "Hello world"

def test_call_llm_prints_tokens(capsys):
    chunks = [_make_chunk("Hello"), _make_chunk(" world")]
    with patch("letscode.agent.client") as mock_client:
        mock_client.chat.completions.create.return_value = iter(chunks)
        call_llm([{"role": "user", "content": "hi"}])
    captured = capsys.readouterr()
    assert "Hello world" in captured.out

def test_call_llm_skips_none_delta(capsys):
    # OpenAI streams often emit None delta on the first/last chunk
    chunks = [_make_chunk("Hello"), _make_chunk(None), _make_chunk(" world")]
    with patch("letscode.agent.client") as mock_client:
        mock_client.chat.completions.create.return_value = iter(chunks)
        result = call_llm([{"role": "user", "content": "hi"}])
    assert result == "Hello world"


# ── Task 4: slash commands ──────────────────────────────────────────────────

def test_dispatch_slash_exit_returns_true():
    # /exit signals the loop to quit
    assert dispatch_slash_command("/exit") is True

def test_dispatch_slash_exit_ignores_extra_args():
    # only the first token matters
    assert dispatch_slash_command("/exit now please") is True

def test_dispatch_slash_unknown_returns_false_and_hints(capsys):
    result = dispatch_slash_command("/foo")
    assert result is False
    captured = capsys.readouterr()
    assert "unknown command" in captured.out
    assert "/exit" in captured.out          # hint lists available commands

def test_dispatch_slash_bare_slash_no_crash():
    # "/" alone must not raise IndexError
    assert dispatch_slash_command("/") is False
