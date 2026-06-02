# Design: `/exit` slash command (+ slash-command registry)

**Date:** 2026-06-02
**Status:** Approved (design phase)

## Problem
The only way to leave `letscode` today is `Ctrl+C` / `Ctrl+D`, caught as
`KeyboardInterrupt` / `EOFError` in the input loop. Typing `/exit` does nothing
special — it gets sent to the LLM as a coding task. We want a typed `/exit`
command that quits the app cleanly and locally.

## Scope
Build a small **slash-command registry** that `/exit` is the first entry of —
not a one-off check. This mirrors the existing `TOOL_REGISTRY` / `dispatch_tool`
pattern so the codebase stays internally consistent and future commands
(`/help`, `/clear`, ...) drop in with no loop changes.

Out of scope: any command other than `/exit`. No `/help`, `/clear`, etc. yet.

## Core principle
Slash commands are handled **locally and never sent to the LLM**. Typing `/exit`
quits instantly — no API call, no tokens consumed.

## Design

### Registry & handlers
A new section in `agent.py`, parallel to the tools section:

```python
def cmd_exit() -> bool:
    """Quits letscode."""
    print("bye!")
    return True   # signals the agent loop to stop

SLASH_REGISTRY = {
    "exit": cmd_exit,
}
```

### Handler contract (Option A)
`handler() -> bool`, where `True` means "quit the app." Non-exit commands
(future) return `False`. This is the smallest contract that works. If/when a
state-mutating command like `/clear` arrives, we widen the signature then
(e.g. pass `conversation` in) — we don't pay for that flexibility now.

### Dispatcher
Mirrors `dispatch_tool`:

```python
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

### Loop integration
In `run_agent_loop`, after the empty-input check and before appending to
`conversation`:

```python
if user_input.startswith("/"):
    if dispatch_slash_command(user_input):
        break        # quit
    continue          # handled (or unknown) — don't send to LLM
```

### Cosmetic
Update welcome text in `print_welcome()` (currently `Ctrl+C to exit`) and the
secondary prompt line in `run_agent_loop` to mention `/exit`.

## Edge cases
- `/exit` → quit.
- `/exit anything` → quit (extra args ignored; first token wins).
- `/foo` (unknown) → print hint, continue, do **not** call the LLM.
- `/` (bare slash) → no crash, treated as no-op, continue.
- A normal message that merely contains `/` mid-string (e.g. `read src/x.py`)
  is unaffected — only a leading `/` triggers command handling.

## Testing
Add tests to `tests/test_agent.py`, matching its style: pytest, import from
`letscode.agent`, a `# ── Task N: ... ──` comment header, `capsys` to capture
stdout. `dispatch_slash_command()` is unit-testable (its only side effect is
`print`):
- `/exit` returns `True`.
- `/foo` returns `False` (unknown) and prints a hint containing `/exit`
  (assert via `capsys`).
- `/` (bare slash) returns `False` (no crash / no IndexError).

## Files touched
- `src/letscode/agent.py` — new slash-command section + loop integration + welcome text.
- `tests/test_agent.py` — tests for `dispatch_slash_command`.
