# letscode Immediate Wins — Design Spec

**Date:** 2026-06-02
**Scope:** Three improvements to `src/letscode/agent.py`

---

## Overview

Three self-contained improvements implemented in order of dependency:

1. **Generic tool dispatch** — remove hardcoded `elif` chain, use `**kwargs`
2. **`run_command` tool** — execute shell commands with user confirmation
3. **Streaming output** — stream LLM tokens to terminal as they arrive

---

## 1. Generic Tool Dispatch

### Problem
`run_agent_loop` contains a hardcoded `elif` branch for every tool (lines 276–287). Adding a new tool requires editing the dispatch logic in addition to registering it.

### Solution
Replace the `elif` chain with `tool_fn(**args)`. Python unpacks the JSON args dict as keyword arguments at the call site. A `try/except TypeError` handles malformed args from the LLM.

```python
# Before (in run_agent_loop):
elif tool_name == "read_file":
    result = tool_fn(args.get("filename", ""))
elif tool_name == "list_files":
    result = tool_fn(args.get("path", "."))
elif tool_name == "edit_file":
    result = tool_fn(args.get("path", ""), args.get("old_str", ""), args.get("new_str", ""))
else:
    result = {"error": f"unhandled tool: {tool_name}"}

# After:
try:
    result = tool_fn(**args)
except TypeError as e:
    result = {"error": f"bad arguments for {tool_name}: {e}"}
```

### Effect
New tools require zero changes to dispatch — register in `TOOL_REGISTRY` only.

---

## 2. `run_command` Tool

### Design
New function in `agent.py`, registered in `TOOL_REGISTRY`.

```python
import subprocess

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

### Key decisions
- **`shell=True`** — allows compound commands (`cd src && python main.py`, pipes, redirects)
- **`capture_output=True`** — both stdout and stderr captured and returned to LLM
- **`timeout=30`** — kills runaway commands after 30 seconds
- **`[y/N]` gate** — user sees and approves every command; default is reject (N)
- **exit_code in result** — LLM can reason about failures (non-zero = error)

---

## 3. Streaming Output

### Design
`call_llm` passes `stream=True` and iterates over chunks, printing each token immediately with `flush=True` while accumulating a buffer. Returns the full buffer for downstream tool call parsing.

```python
def call_llm(conversation: List[Dict[str, str]]) -> str:
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
    print()  # final newline
    return buffer
```

`run_agent_loop` removes the `print(f"{ASSISTANT_COLOR}letscode:...")` line from the no-tool-calls branch — streaming already printed the response.

### Key decisions
- **Stream display, buffer for parsing** — user sees tokens arrive; tool call parsing still happens on the complete buffer after streaming ends
- **`flush=True`** — forces stdout buffer to drain after each chunk, producing the live typing effect
- Raw `tool: TOOL_NAME(...)` lines are visible during streaming — intentional, makes the protocol transparent

---

## Implementation Order

| Step | Change | File |
|------|--------|------|
| 1 | Replace `elif` chain with `tool_fn(**args)` | `agent.py` — `run_agent_loop` |
| 2 | Add `import subprocess` and `run_command` function | `agent.py` |
| 3 | Register `run_command` in `TOOL_REGISTRY` | `agent.py` |
| 4 | Rewrite `call_llm` to use `stream=True` | `agent.py` |
| 5 | Remove redundant print from `run_agent_loop` | `agent.py` |

---

## What Does Not Change
- `parse_tool_call` — unchanged; still parses the complete buffer
- `build_system_prompt` — unchanged; auto-picks up `run_command` from registry
- All three existing tools (`read_file`, `list_files`, `edit_file`) — unchanged
- Tool result format (`tool_result({...json...})`) — unchanged
