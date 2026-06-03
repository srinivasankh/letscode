```
██╗     ███████╗████████╗███████╗ ██████╗ ██████╗ ██████╗ ███████╗
██║     ██╔════╝╚══██╔══╝██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝
██║     █████╗     ██║   ███████╗██║     ██║   ██║██║  ██║█████╗  
██║     ██╔══╝     ██║   ╚════██║██║     ██║   ██║██║  ██║██╔══╝  
███████╗███████╗   ██║   ███████║╚██████╗╚██████╔╝██████╔╝███████╗
╚══════╝╚══════╝   ╚═╝   ╚══════╝ ╚═════╝ ╚═════╝ ╚═════╝╚══════╝
```

> **Building Claude Code from scratch** — a minimal coding agent you own and understand.

---

## What is this?

`letscode` is a coding agent built from first principles. It replicates the core loop of tools like Claude Code:

- You describe a coding task in plain English
- The agent calls tools (read files, list directories, edit files) to get the job done
- It keeps looping — reading, reasoning, editing — until the task is complete

The entire agent fits in a single file. No magic, no abstractions you didn't write yourself.

---

## Features

- **Model-agnostic** — works with any model on [OpenRouter](https://openrouter.ai): Claude, GPT-4o, Gemini, Llama, Mistral, DeepSeek, and more
- **Free tier support** — defaults to `meta-llama/llama-3.3-70b-instruct:free` (no cost)
- **Built-in tools** — read files, list directories, edit files, search file contents, run shell commands
- **Interactive `/` menu** — type `/` for a navigable dropdown of every command and tool (arrow keys + Enter), just like Claude Code; pick a tool to run it locally without spending tokens
- **Text-protocol tool-calling** — no vendor lock-in; the LLM emits tool calls as plain text
- **Full conversation history** — the agent remembers context across turns

---

## Quickstart

### 1. Clone the repo

```bash
git clone https://github.com/srinivasankh/letscode.git
cd letscode
```

### 2. Set up your API key

Copy the example config and add your [OpenRouter](https://openrouter.ai/keys) key:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENROUTER_API_KEY=sk-or-your-key-here
```

That's all you need. The default model is free — no credit card required.

### 3. Run it

```bash
uv run letscode
```

Or, if you prefer pip:

```bash
pip install -e .
letscode
```

---

## Bring Your Own API Key (BYOK)

`letscode` routes all LLM calls through [OpenRouter](https://openrouter.ai), which gives you a single API key that works with dozens of models.

**Get a free key:**
1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Go to [openrouter.ai/keys](https://openrouter.ai/keys) → create a key
3. Paste it into your `.env` file as `OPENROUTER_API_KEY`

**Choose your model** by setting `OPENROUTER_MODEL` in `.env`:

```env
# Free models (no cost)
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
OPENROUTER_MODEL=google/gemma-3-27b-it:free
OPENROUTER_MODEL=deepseek/deepseek-r1:free

# Frontier models (paid, best quality)
OPENROUTER_MODEL=anthropic/claude-sonnet-4
OPENROUTER_MODEL=openai/gpt-4o
OPENROUTER_MODEL=google/gemini-2.5-pro
```

Browse all available models at [openrouter.ai/models](https://openrouter.ai/models).

---

## How it works

The agent runs a simple loop:

```
User input
    └─▶ LLM reasons about the task
            └─▶ Emits a tool call  (e.g. tool: read_file({"filename": "app.py"}))
                    └─▶ Agent executes the tool
                            └─▶ Result fed back to LLM
                                    └─▶ Repeat until done
```

**Available tools:**

| Tool | What it does |
|---|---|
| `read_file(filename)` | Read the full content of a file |
| `list_files(path)` | List files and directories at a path |
| `edit_file(path, old_str, new_str)` | Replace text in a file, or create a new file |
| `search_text(pattern, path)` | Recursively search file contents for a regex, returning `file:line:text` hits |
| `run_command(command)` | Run a shell command (with confirm-before-run gate) |

**Slash menu:** type `/` to open an interactive dropdown of commands (`/exit`, `/help`)
and tools. Use the arrow keys and Enter to select. Picking a command runs it; picking a
tool inserts a `/tool({"arg": "value"})` template you fill in — the tool then runs locally
(no LLM call) and prints its result.

---

## Project structure

```
src/letscode/
  agent.py       # the entire agent: tools, prompt, parser, loop
pyproject.toml   # package config
.env.example     # config template — copy to .env
```

---

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- A free [OpenRouter](https://openrouter.ai/keys) API key
- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) (installed automatically) — powers the interactive `/` menu
