import pytest
from letscode.agent import dispatch_tool
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
