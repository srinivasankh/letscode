# letscode Immediate Wins — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add generic tool dispatch, a `run_command` tool, and streaming output to `src/letscode/agent.py`.

**Architecture:** All three changes are confined to a single file (`agent.py`). Dispatch logic is extracted into a testable `dispatch_tool()` helper. `run_command` is a new function registered in `TOOL_REGISTRY`. `call_llm` is rewritten to use the OpenAI streaming API while returning the full buffer for tool call parsing.

**Tech Stack:** Python 3.12, `openai>=1.30.0`, `subprocess` (stdlib), `pytest>=8.0` (dev)

---

### Task 0: Set up test infrastructure

**Files:**
- Modify: `pyproject.toml` — add pytest dev dependency and config
- Create: `tests/__init__.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Add pytest to pyproject.toml**

Add two sections to `pyproject.toml` (after `[tool.uv]`):

```toml
[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Install dev dependencies**

Run: `uv sync --group dev`

Expected output includes: `Resolved ... packages` with no errors.

- [ ] **Step 3: Create test files**

Create `tests/__init__.py` — empty file.

Create `tests/test_agent.py`:

```python
# Tests added task-by-task below
```

- [ ] **Step 4: Verify pytest runs**

Run: `uv run pytest tests/ -v`

Expected: `no tests ran` — 0 collected, no errors.

---

### Task 1: Generic tool dispatch

**Files:**
- Modify: `src/letscode/agent.py` — add `dispatch_tool()`, update `run_agent_loop`
- Modify: `tests/test_agent.py`

- [ ] **Step 1: Write failing tests**

Replace `tests/test_agent.py` with:

```python
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
```

- [ ] **Step 2: Run tests — expect ImportError**

Run: `uv run pytest tests/test_agent.py -v`

Expected: `ImportError: cannot import name 'dispatch_tool'`

- [ ] **Step 3: Add `dispatch_tool` to `agent.py`**

In `src/letscode/agent.py`, add this function directly after the `TOOL_REGISTRY` dict:

```python
def dispatch_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Looks up tool_name in TOOL_REGISTRY and calls it with **args."""
    tool_fn = TOOL_REGISTRY.get(tool_name)
    if tool_fn is None:
        return {"error": f"unknown tool: {tool_name}"}
    try:
        return tool_fn(**args)
    except TypeError as e:
        return {"error": f"bad arguments for {tool_name}: {e}"}
```

- [ ] **Step 4: Replace the `elif` chain in `run_agent_loop`**

In `run_agent_loop`, find and replace this entire block:

```python
                tool_fn = TOOL_REGISTRY.get(tool_name)

                if tool_fn is None:
                    result = {"error": f"unknown tool: {tool_name}"}
                elif tool_name == "read_file":
                    result = tool_fn(args.get("filename", ""))
                elif tool_name == "list_files":
                    result = tool_fn(args.get("path", "."))
                elif tool_name == "edit_file":
                    result = tool_fn(
                        args.get("path", ""),
                        args.get("old_str", ""),
                        args.get("new_str", ""),
                    )
                else:
                    result = {"error": f"unhandled tool: {tool_name}"}
```

With:

```python
                result = dispatch_tool(tool_name, args)
```

- [ ] **Step 5: Run tests — expect 3 passing**

Run: `uv run pytest tests/test_agent.py -v`

Expected:
```
PASSED tests/test_agent.py::test_dispatch_unknown_tool
PASSED tests/test_agent.py::test_dispatch_bad_args
PASSED tests/test_agent.py::test_dispatch_valid_tool
3 passed
```

- [ ] **Step 6: Commit**

```bash
git add src/letscode/agent.py tests/
git commit -m "refactor: extract dispatch_tool, replace elif chain with **kwargs dispatch"
```

---

### Task 2: `run_command` tool

**Files:**
- Modify: `src/letscode/agent.py` — add `import subprocess`, add `run_command`, update `TOOL_REGISTRY`
- Modify: `tests/test_agent.py`

- [ ] **Step 1: Append failing tests**

First update the import line at the top of `tests/test_agent.py`:

```python
from letscode.agent import dispatch_tool, run_command
```

Then add to the end of `tests/test_agent.py`:

```python
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
```

- [ ] **Step 2: Run new tests — expect ImportError**

Run: `uv run pytest tests/test_agent.py::test_run_command_rejected -v`

Expected: `ImportError: cannot import name 'run_command'`

- [ ] **Step 3: Add `import subprocess` to `agent.py`**

At the top of `src/letscode/agent.py`, add `import subprocess` alongside the existing imports.

- [ ] **Step 4: Add `run_command` function to `agent.py`**

Add after `edit_file`, before `TOOL_REGISTRY`:

```python
def run_command(command: str) -> Dict[str, Any]:
    """
    Runs a shell command and returns stdout, stderr, and exit code.
    :param command: The shell command to run.
    :return: stdout, stderr, and exit code.
    """
    print(f"\n  Command: {command}")
    confirm = input("  Allow? [y/N] ").strip().lower()
    if confirm != "y":
        return {"error": "command rejected by user"}

    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=30
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
    }
```

- [ ] **Step 5: Register `run_command` in `TOOL_REGISTRY`**

Update `TOOL_REGISTRY`:

```python
TOOL_REGISTRY = {
    "read_file": read_file,
    "list_files": list_files,
    "edit_file": edit_file,
    "run_command": run_command,
}
```

- [ ] **Step 6: Run all tests — expect 6 passing**

Run: `uv run pytest tests/ -v`

Expected:
```
PASSED tests/test_agent.py::test_dispatch_unknown_tool
PASSED tests/test_agent.py::test_dispatch_bad_args
PASSED tests/test_agent.py::test_dispatch_valid_tool
PASSED tests/test_agent.py::test_run_command_rejected
PASSED tests/test_agent.py::test_run_command_accepted_stdout
PASSED tests/test_agent.py::test_run_command_nonzero_exit
6 passed
```

- [ ] **Step 7: Commit**

```bash
git add src/letscode/agent.py tests/test_agent.py
git commit -m "feat: add run_command tool with confirm-before-run gate"
```

---

### Task 3: Streaming output

**Files:**
- Modify: `src/letscode/agent.py` — rewrite `call_llm`, remove redundant print from `run_agent_loop`
- Modify: `tests/test_agent.py`

- [ ] **Step 1: Append failing tests**

First update the import line at the top of `tests/test_agent.py`:

```python
from letscode.agent import dispatch_tool, run_command, call_llm
```

Then add to the end of `tests/test_agent.py`:

```python
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
```

- [ ] **Step 2: Run new tests — expect failure**

Run: `uv run pytest tests/test_agent.py::test_call_llm_returns_full_text -v`

Expected: FAIL — current `call_llm` returns `response.choices[0].message.content` (non-streaming), not a buffered string from a stream.

- [ ] **Step 3: Rewrite `call_llm` in `agent.py`**

Replace the current `call_llm` function:

```python
def call_llm(conversation: List[Dict[str, str]]) -> str:
    """Sends conversation to OpenRouter, streams tokens to stdout, returns full response text."""
    stream = client.chat.completions.create(
        model=MODEL, messages=conversation, stream=True
    )
    print(f"{ASSISTANT_COLOR}letscode:{RESET_COLOR} ", end="", flush=True)
    buffer = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
            buffer += delta
    print()
    return buffer
```

- [ ] **Step 4: Remove redundant print from `run_agent_loop`**

In `run_agent_loop`, find the no-tool-calls branch:

```python
            if not tool_calls:
                print(f"{ASSISTANT_COLOR}letscode:{RESET_COLOR} {response_text}\n")
                conversation.append({"role": "assistant", "content": response_text})
                break
```

Replace with (streaming already printed the response):

```python
            if not tool_calls:
                conversation.append({"role": "assistant", "content": response_text})
                break
```

- [ ] **Step 5: Run all tests — expect 9 passing**

Run: `uv run pytest tests/ -v`

Expected:
```
PASSED tests/test_agent.py::test_dispatch_unknown_tool
PASSED tests/test_agent.py::test_dispatch_bad_args
PASSED tests/test_agent.py::test_dispatch_valid_tool
PASSED tests/test_agent.py::test_run_command_rejected
PASSED tests/test_agent.py::test_run_command_accepted_stdout
PASSED tests/test_agent.py::test_run_command_nonzero_exit
PASSED tests/test_agent.py::test_call_llm_returns_full_text
PASSED tests/test_agent.py::test_call_llm_prints_tokens
PASSED tests/test_agent.py::test_call_llm_skips_none_delta
9 passed
```

- [ ] **Step 6: Commit**

```bash
git add src/letscode/agent.py tests/test_agent.py
git commit -m "feat: stream LLM output token-by-token to terminal"
```
