# letscode — Claude Code context

## What this project is
A Claude Code-like coding agent built from scratch as a learning project, following https://www.mihaileric.com/The-Emperor-Has-No-Clothes/. The agent uses OpenRouter (OpenAI-compatible API) so it works with any LLM — free models like Llama 3.3 or paid ones like Claude/GPT-4o.

## How to run
```bash
uv run letscode        # preferred
# or after pip install -e .
letscode
```

Requires `.env` with `OPENROUTER_API_KEY` (copy `.env.example` to `.env`).

## Project structure
```
src/letscode/
  agent.py       # everything: tools, system prompt, parser, agent loop
pyproject.toml   # package config, entry point: letscode.agent:main
.env.example     # model/key config template
```

## Architecture (all in agent.py)

**Tool protocol** — the LLM emits tool calls as plain text, not native function-calling:
```
tool: TOOL_NAME({"param": "value"})
```
`parse_tool_call()` scans LLM output for these lines and dispatches to `TOOL_REGISTRY`.

**Three tools implemented:**
- `read_file(filename)` — reads file content, returns `{file_path, content}`
- `list_files(path)` — lists directory, returns `{path, files: [{filename, type}]}`
- `edit_file(path, old_str, new_str)` — replaces first match, or creates file if `old_str=""`

**Agent loop (`run_agent_loop`):**
1. Outer loop: read user input → append to conversation history
2. Inner loop (max 10 iterations): call LLM → parse tools → execute → feed `tool_result(...)` back → repeat until no tool calls

**System prompt** is built dynamically: `build_system_prompt()` injects each tool's name, docstring, and signature from `TOOL_REGISTRY` so the LLM always has accurate tool descriptions.

## Key conventions
- Add new tools as plain functions in `agent.py`, register them in `TOOL_REGISTRY`, and the system prompt picks them up automatically — no other wiring needed.
- All file paths go through `resolve_abs_path()` to convert relative → absolute.
- Tool results are injected back as `role: user` messages with content `tool_result({...json...})`.
- The `assistant` message is appended to conversation *before* tool execution (correct ordering).
- `max_iterations = 10` guards against infinite tool-calling loops.

## Dependencies
- `openai>=1.30.0` — used with `base_url` pointing at OpenRouter
- `python-dotenv>=1.0.0` — loads `.env`
- Python 3.12+, managed with `uv`
