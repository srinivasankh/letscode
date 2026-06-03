import pytest
import subprocess
from letscode.agent import dispatch_tool, run_command, call_llm, dispatch_slash_command, run_agent_loop, search_text
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


# ── Task 5: slash commands in the loop ──────────────────────────────────────

def test_loop_exits_on_slash_exit_without_calling_llm(capsys):
    # /exit must break the loop locally — the LLM is never invoked.
    with patch("builtins.input", side_effect=["/exit"]):
        with patch("letscode.agent.call_llm") as mock_llm:
            run_agent_loop()        # returns cleanly when the loop breaks
    mock_llm.assert_not_called()
    captured = capsys.readouterr()
    assert "bye!" in captured.out

def test_loop_continues_on_unknown_command_then_exits(capsys):
    # /foo is handled locally (hint printed, loop continues), then /exit quits.
    # If /foo crashed or exited, we'd never reach /exit. The LLM is never called.
    with patch("builtins.input", side_effect=["/foo", "/exit"]):
        with patch("letscode.agent.call_llm") as mock_llm:
            run_agent_loop()
    mock_llm.assert_not_called()
    captured = capsys.readouterr()
    assert "unknown command" in captured.out
    assert "bye!" in captured.out

def test_loop_forwards_normal_prompt_to_llm():
    # A non-slash message must STILL reach the LLM — the intercept only diverts /commands.
    # call_llm returns plain text with no tool call, so the inner loop ends cleanly,
    # then /exit quits the outer loop.
    with patch("letscode.agent.call_llm", return_value="hi there") as mock_llm:
        with patch("builtins.input", side_effect=["write a hello world", "/exit"]):
            run_agent_loop()
    mock_llm.assert_called_once()


# ── Task: search_text ───────────────────────────────────────────────────────

def test_search_text_finds_match_across_files(tmp_path):
    (tmp_path / "a.py").write_text("import os\ndef hello():\n    return 1\n")
    (tmp_path / "b.py").write_text("x = 2\ndef hello_again():\n    pass\n")
    result = search_text("def hello", str(tmp_path))
    assert result["count"] == 2
    files = {m["file"] for m in result["matches"]}
    assert str(tmp_path / "a.py") in files
    assert str(tmp_path / "b.py") in files
    a_hit = next(m for m in result["matches"] if m["file"] == str(tmp_path / "a.py"))
    assert a_hit["line"] == 2
    assert a_hit["text"] == "def hello():"

def test_search_text_no_match_returns_zero(tmp_path):
    (tmp_path / "a.py").write_text("nothing here\n")
    result = search_text("zzz_not_found", str(tmp_path))
    assert result["count"] == 0
    assert result["matches"] == []

def test_search_text_single_file_path(tmp_path):
    f = tmp_path / "only.py"
    f.write_text("line one\ntarget line\nline three\n")
    result = search_text("target", str(f))
    assert result["count"] == 1
    assert result["matches"][0]["line"] == 2
    assert result["matches"][0]["text"] == "target line"

def test_search_text_bad_regex_returns_error(tmp_path):
    result = search_text("(unclosed", str(tmp_path))
    assert "error" in result

def test_search_text_skips_ignored_dirs(tmp_path):
    (tmp_path / "keep.py").write_text("needle here\n")
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("needle here too\n")
    result = search_text("needle", str(tmp_path))
    assert result["count"] == 1
    assert result["matches"][0]["file"] == str(tmp_path / "keep.py")

def test_search_text_via_dispatch(tmp_path):
    (tmp_path / "a.py").write_text("foo bar\n")
    result = dispatch_tool("search_text", {"pattern": "foo", "path": str(tmp_path)})
    assert result["count"] == 1
    assert result["matches"][0]["text"] == "foo bar"
