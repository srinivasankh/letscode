import pytest
import subprocess
from letscode.agent import dispatch_tool, run_command
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
