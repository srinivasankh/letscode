# `/exit` Slash Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a typed `/exit` command that quits `letscode` instantly and locally, built on a small reusable slash-command registry.

**Architecture:** A `SLASH_REGISTRY` (name → handler) and a `dispatch_slash_command()` function mirror the existing `TOOL_REGISTRY` / `dispatch_tool` pattern. Slash commands are intercepted in `run_agent_loop` on a leading `/` and handled locally — never sent to the LLM. Handlers return `bool`; `True` means "quit the loop."

**Tech Stack:** Python 3.12, pytest, `uv`.

**Spec:** `docs/superpowers/specs/2026-06-02-slash-command-exit-design.md`

---

## File Structure

- **Modify** `src/letscode/agent.py` — add a `# ── Slash commands` section (`cmd_exit`, `SLASH_REGISTRY`, `dispatch_slash_command`) between `parse_tool_call` and `run_agent_loop`; intercept slash input inside `run_agent_loop`; update welcome/prompt text.
- **Modify** `tests/test_agent.py` — add a `# ── Task 4: slash commands` section (dispatcher unit tests) and a `# ── Task 5: slash commands in the loop` section (loop-integration tests).

---

## Task 1: Slash-command registry & dispatcher (TDD)

**Files:**
- Modify: `tests/test_agent.py` (import line + new test section at end)
- Modify: `src/letscode/agent.py` (new section between `parse_tool_call` ~line 271 and `run_agent_loop` ~line 274)

- [ ] **Step 1: Update the test import line**

In `tests/test_agent.py`, change the existing import (currently line 3):

```python
from letscode.agent import dispatch_tool, run_command, call_llm
```

to:

```python
from letscode.agent import dispatch_tool, run_command, call_llm, dispatch_slash_command
```

- [ ] **Step 2: Write the failing tests**

Append to the end of `tests/test_agent.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_agent.py -k "slash" -v`
Expected: collection/import error or FAIL — `dispatch_slash_command` does not exist yet (ImportError on the updated import line).

- [ ] **Step 4: Write the minimal implementation**

In `src/letscode/agent.py`, insert this new section immediately **after** the `parse_tool_call` function (ends ~line 271) and **before** `def run_agent_loop`:

```python
# ── Slash commands ───────────────────────────────────────────────────────────
# Typed /commands are handled locally and never sent to the LLM — no tokens,
# instant, guaranteed. Mirrors the TOOL_REGISTRY / dispatch_tool pattern.

def cmd_exit() -> bool:
    """Quits letscode."""
    print("bye!")
    return True   # True signals run_agent_loop to stop


SLASH_REGISTRY = {
    "exit": cmd_exit,
}


def dispatch_slash_command(user_input: str) -> bool:
    """
    Handles a /command line. Returns True if the app should exit.
    Unknown commands print a hint and return False (not forwarded to the LLM).
    """
    parts = user_input[1:].split()          # "/exit foo" -> ["exit", "foo"]
    if not parts:                            # bare "/" -> no crash
        return False
    name = parts[0]
    handler = SLASH_REGISTRY.get(name)
    if handler is None:
        known = ", ".join("/" + c for c in SLASH_REGISTRY)
        print(f"  unknown command: /{name}  (available: {known})")
        return False
    return handler()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_agent.py -k "slash" -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/letscode/agent.py tests/test_agent.py
git commit -m "feat: add slash-command registry and dispatch_slash_command"
```

---

## Task 2: Wire slash commands into the agent loop + update help text (TDD)

This task wires the dispatcher into `run_agent_loop`. We test the loop behaviour
directly — and crucially **without calling the real LLM** — by mocking the two
boundaries the loop touches: `builtins.input` (to feed typed lines) and
`letscode.agent.call_llm` (the network boundary). Asserting `call_llm` was
**never called** proves a slash command short-circuited before any API round-trip.

**Files:**
- Modify: `tests/test_agent.py` (import line + new test section at end)
- Modify: `src/letscode/agent.py` (`run_agent_loop`; `print_welcome` line 42; secondary prompt line ~283)

- [ ] **Step 1: Add `run_agent_loop` to the test import**

In `tests/test_agent.py`, change the import line to also import `run_agent_loop`:

```python
from letscode.agent import dispatch_tool, run_command, call_llm, dispatch_slash_command, run_agent_loop
```

- [ ] **Step 2: Write the failing loop-integration tests**

Append to the end of `tests/test_agent.py`:

```python
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
```

- [ ] **Step 3: Run the loop tests to verify they fail**

Run: `uv run pytest tests/test_agent.py -k "loop" -v`
Expected: FAIL — `run_agent_loop` does not yet intercept slash commands, so it
appends `/exit` to the conversation and calls `call_llm` (mock_llm.assert_not_called
fails), or raises `StopIteration` when `input` runs out. Either way: not passing.

- [ ] **Step 4: Intercept slash input in the loop**

In `src/letscode/agent.py`, inside `run_agent_loop`, find the empty-input guard:

```python
        if not user_input:
            continue
```

Insert directly **after** it:

```python
        # ── Slash commands: handled locally, never sent to the LLM ─────
        if user_input.startswith("/"):
            if dispatch_slash_command(user_input):
                break        # quit
            continue          # handled (or unknown) — don't call the LLM
```

- [ ] **Step 5: Update the welcome text**

In `print_welcome()`, change line 42:

```python
    print(f"  Type your coding task below. {YOU_COLOR}Ctrl+C{RESET_COLOR} to exit.\n")
```

to:

```python
    print(f"  Type your coding task below. {YOU_COLOR}/exit{RESET_COLOR} or {YOU_COLOR}Ctrl+C{RESET_COLOR} to quit.\n")
```

- [ ] **Step 6: Update the secondary prompt line**

In `run_agent_loop`, change the line (~283):

```python
    print("Type your coding task. Ctrl+C to exit.\n")
```

to:

```python
    print("Type your coding task. /exit or Ctrl+C to quit.\n")
```

- [ ] **Step 7: Run the loop tests to verify they pass**

Run: `uv run pytest tests/test_agent.py -k "loop" -v`
Expected: 2 passed.

- [ ] **Step 8: Run the full test suite**

Run: `uv run pytest -v`
Expected: all tests pass (4 dispatcher tests + 2 loop tests + the pre-existing suite).

- [ ] **Step 9: Optional manual smoke test**

Requires `.env` with `OPENROUTER_API_KEY` present (project requirement). `/exit`
short-circuits before any network call, so the key need not be valid — it just
must exist so the module imports.

Run: `printf '/foo\n/exit\n' | uv run letscode`
Expected output includes, in order: the welcome banner, `unknown command: /foo  (available: /exit)`, then `bye!`, with **no** `letscode:` LLM response line in between.

- [ ] **Step 10: Commit**

```bash
git add src/letscode/agent.py tests/test_agent.py
git commit -m "feat: handle /exit in agent loop, mention it in help text"
```

---

## Self-Review

**Spec coverage:**
- Registry & `cmd_exit` → Task 1, Step 4. ✓
- Handler contract (Option A, `-> bool`) → Task 1, Step 4 (`cmd_exit` returns `True`). ✓
- `dispatch_slash_command` (unknown-command hint, bare-`/` guard) → Task 1, Step 4 + tests Step 2. ✓
- Loop integration (leading `/`, local handling, no LLM forward) → Task 2, Step 4, verified by loop tests in Task 2, Step 2. ✓
- Cosmetic welcome/prompt text → Task 2, Steps 5-6. ✓
- Edge cases `/exit args`, `/foo`, `/` → dispatcher tests (Task 1, Step 2); `/exit` and `/foo` also verified at the loop level (Task 2, Step 2). ✓
- Tests in `tests/test_agent.py` matching style (pytest, `capsys`, Task-N header) → Task 1, Step 2 + Task 2, Step 2. ✓

**Placeholder scan:** No TBD/TODO/"handle edge cases" — every code step shows full code. ✓

**Type consistency:** `dispatch_slash_command(user_input: str) -> bool`, `cmd_exit() -> bool`, `SLASH_REGISTRY`, and `run_agent_loop()` used identically in implementation, tests, and loop. ✓
