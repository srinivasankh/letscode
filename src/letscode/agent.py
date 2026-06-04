import os
import re
import subprocess

from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

from prompt_toolkit import PromptSession, ANSI
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings

load_dotenv()

# OpenRouter is OpenAI-API-compatible — same SDK, different base_url
API_KEY = os.environ.get("OPENROUTER_API_KEY")
client = (
    OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)
    if API_KEY
    else None
)

MODEL = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

# Terminal colours
YOU_COLOR       = "\u001b[94m"   # blue
ASSISTANT_COLOR = "\u001b[93m"   # yellow
RESET_COLOR     = "\u001b[0m"


BANNER = f"""{ASSISTANT_COLOR}
██╗     ███████╗████████╗███████╗ ██████╗ ██████╗ ██████╗ ███████╗
██║     ██╔════╝╚══██╔══╝██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝
██║     █████╗     ██║   ███████╗██║     ██║   ██║██║  ██║█████╗  
██║     ██╔══╝     ██║   ╚════██║██║     ██║   ██║██║  ██║██╔══╝  
███████╗███████╗   ██║   ███████║╚██████╗╚██████╔╝██████╔╝███████╗
╚══════╝╚══════╝   ╚═╝   ╚══════╝ ╚═════╝ ╚═════╝ ╚═════╝╚══════╝
{RESET_COLOR}"""

def print_welcome() -> None:
    """Prints the welcome screen."""
    print(BANNER)
    print(f"  by Srini · v0.1.0\n")
    print(f"  {'─' * 58}")
    print(f"  Model   : {ASSISTANT_COLOR}{MODEL}{RESET_COLOR}")
    print(f"  BYOK    : Add your OpenRouter key to .env")
    print(f"  Keys    : openrouter.ai/keys")
    print(f"  {'─' * 58}\n")
    print(f"  Type your coding task below. {YOU_COLOR}/exit{RESET_COLOR} or {YOU_COLOR}Ctrl+C{RESET_COLOR} to quit.\n")



def resolve_abs_path(path_str: str) -> Path:
    """Converts a relative path like 'hello.py' to an absolute path."""
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path



from typing import Any, Dict

def read_file(filename: str) -> Dict[str, Any]:
    """
    Gets the full content of a file provided by the user.
    :param filename: The name of the file to read.
    :return: The full content of the file.
    """
    try:
        full_path = resolve_abs_path(filename)
        with open(str(full_path), "r") as f:
            content = f.read()
        return {"file_path": str(full_path), "content": content}
    except FileNotFoundError:
        return {"error": f"file not found: {filename}"}
    except Exception as e:
        return {"error": str(e)}


def list_files(path: str) -> Dict[str, Any]:
    """
    Lists the files in a directory provided by the user.
    :param path: The path to a directory to list files from.
    :return: A list of files in the directory.
    """
    try:
        full_path = resolve_abs_path(path)
        all_files = []
        for item in full_path.iterdir():
            all_files.append({
                "filename": item.name,
                "type": "file" if item.is_file() else "dir",
            })
        return {"path": str(full_path), "files": all_files}
    except FileNotFoundError:
        return {"error": f"directory not found: {path}"}
    except Exception as e:
        return {"error": str(e)}


def edit_file(path: str, old_str: str, new_str: str) -> Dict[str, Any]:
    """
    Replaces first occurrence of old_str with new_str in a file.
    If old_str is empty, creates or overwrites the file with new_str.
    :param path: The path to the file to edit.
    :param old_str: The string to replace. Pass empty string to create a new file.
    :param new_str: The string to replace with, or the full content of the new file.
    :return: A dictionary with the path and the action taken.
    """
    try:
        full_path = resolve_abs_path(path)

        if old_str == "":
            full_path.write_text(new_str, encoding="utf-8")
            return {"path": str(full_path), "action": "created_file"}

        original = full_path.read_text(encoding="utf-8")

        if original.find(old_str) == -1:
            return {"path": str(full_path), "action": "old_str_not_found"}

        edited = original.replace(old_str, new_str, 1)
        full_path.write_text(edited, encoding="utf-8")
        return {"path": str(full_path), "action": "edited"}

    except FileNotFoundError:
        return {"error": f"file not found: {path}"}
    except Exception as e:
        return {"error": str(e)}





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

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "command timed out after 30s"}


_SEARCH_IGNORE_DIRS = {".git", "__pycache__", ".venv", "node_modules"}
_SEARCH_MAX_RESULTS = 100


def search_text(pattern: str, path: str = ".") -> Dict[str, Any]:
    """
    Searches file contents for a regular expression and returns matching lines.
    Use this to locate where code lives instead of reading whole files.
    :param pattern: A Python regular expression to search for.
    :param path: A file or directory to search. Directories are searched
        recursively. Defaults to the current directory.
    :return: pattern, path, count, and a list of matches ({file, line, text}).
        Results are capped at 100 (truncated=True when the cap is hit).
    """
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return {"error": f"invalid regex: {e}"}

    full_path = resolve_abs_path(path)
    if not full_path.exists():
        return {"error": f"path not found: {path}"}

    # Collect the files to scan: a single file, or every file under a directory.
    if full_path.is_file():
        files = [full_path]
    else:
        files = []
        for root, dirs, filenames in os.walk(full_path):
            dirs[:] = [
                d for d in dirs
                if d not in _SEARCH_IGNORE_DIRS and not d.endswith(".egg-info")
            ]
            for name in filenames:
                files.append(Path(root) / name)

    matches: List[Dict[str, Any]] = []
    truncated = False
    for file_path in files:
        try:
            with open(str(file_path), "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    if regex.search(line):
                        matches.append({
                            "file": str(file_path),
                            "line": line_no,
                            "text": line.rstrip("\n"),
                        })
                        if len(matches) >= _SEARCH_MAX_RESULTS:
                            truncated = True
                            break
        except (UnicodeDecodeError, OSError):
            continue  # skip binary / unreadable files
        if truncated:
            break

    result = {
        "pattern": pattern,
        "path": str(full_path),
        "count": len(matches),
        "matches": matches,
    }
    if truncated:
        result["truncated"] = True
    return result


# ── Registry: name → function ──────────────────────────────────────────────

TOOL_REGISTRY = {
    "read_file": read_file,
    "list_files": list_files,
    "edit_file": edit_file,
    "run_command": run_command,
    "search_text": search_text,
}


def dispatch_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Looks up tool_name in TOOL_REGISTRY and calls it with **args."""
    tool_fn = TOOL_REGISTRY.get(tool_name)
    if tool_fn is None:
        return {"error": f"unknown tool: {tool_name}"}
    try:
        return tool_fn(**args)
    except TypeError as e:
        return {"error": f"bad arguments for {tool_name}: {e}"}


import inspect
from typing import List

# ── System prompt ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are letscode, a coding agent that helps users with coding tasks.
You have access to tools you can use to read, navigate, and edit files.

Here are your available tools:

{tool_list}

When you want to use a tool, reply with EXACTLY this format on its own line:
tool: TOOL_NAME({{"param": "value"}})

Use compact single-line JSON with double quotes inside the parentheses.
After receiving a tool_result(...) message, continue the task.
If no tool is needed, respond normally.

Important rules:
- Only call one tool per reply
- Wait for the tool result before calling another tool
- Never make up file contents — always read first
"""


def _get_tool_description(tool_name: str) -> str:
    """Builds a text description of one tool from its name, docstring, and signature."""
    tool_fn = TOOL_REGISTRY[tool_name]
    return (
        f"Tool: {tool_name}\n"
        f"Description: {tool_fn.__doc__}\n"
        f"Signature: {inspect.signature(tool_fn)}\n"
    )


def build_system_prompt() -> str:
    """Assembles the full system prompt with all tool descriptions injected."""
    tool_descriptions = "\n---\n".join(
        _get_tool_description(name) for name in TOOL_REGISTRY
    )
    return SYSTEM_PROMPT.format(tool_list=tool_descriptions)

import json
from typing import Tuple

# ── LLM call ───────────────────────────────────────────────────────────────

def call_llm(conversation: List[Dict[str, str]]) -> str:
    """Sends conversation to OpenRouter, streams tokens to stdout, returns full response text."""
    stream = client.chat.completions.create(
        model=MODEL, messages=conversation, stream=True
    )
    print(f"{ASSISTANT_COLOR}letscode:{RESET_COLOR} ", end="", flush=True)
    buffer = ""
    for chunk in stream:
        delta = getattr(chunk.choices[0].delta, 'content', None)
        if delta:
            print(delta, end="", flush=True)
            buffer += delta
    print()
    return buffer


# ── Tool call parser ────────────────────────────────────────────────────────

def parse_tool_call(text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Scans the LLM response for tool invocation lines.
    Looks for lines in the format: tool: TOOL_NAME({"key": "value"})
    Returns a list of (tool_name, args) tuples.
    """
    invocations = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line.startswith("tool:"):
            continue

        try:
            after = line[len("tool:"):].strip()       # 'read_file({"filename": "hello.py"})'
            name, rest = after.split("(", 1)          # 'read_file', '{"filename": "hello.py"})'
            name = name.strip()

            if not rest.endswith(")"):
                continue

            json_str = rest[:-1].strip()              # '{"filename": "hello.py"}'
            args = json.loads(json_str)

            invocations.append((name, args))

        except Exception:
            continue                                   # malformed line — skip silently

    return invocations


# ── Slash commands ───────────────────────────────────────────────────────────
# Typed /commands are handled locally and never sent to the LLM — no tokens,
# instant, guaranteed. Mirrors the TOOL_REGISTRY / dispatch_tool pattern.

def _first_doc_line(fn) -> str:
    """First non-blank line of a function's docstring, for menu/help summaries."""
    doc = (fn.__doc__ or "").strip()
    return doc.splitlines()[0] if doc else ""


def cmd_exit() -> bool:
    """Quits letscode."""
    print("bye!")
    return True   # True signals run_agent_loop to stop


def cmd_help() -> bool:
    """Lists available commands and tools."""
    print("\n  Commands:")
    for name, fn in SLASH_REGISTRY.items():
        print(f"    /{name:<12} {_first_doc_line(fn)}")
    print("\n  Tools (run as /tool({\"arg\": \"value\"})):")
    for name, fn in TOOL_REGISTRY.items():
        print(f"    /{name:<12} {_first_doc_line(fn)}")
    print()
    return False


SLASH_REGISTRY = {
    "exit": cmd_exit,
    "help": cmd_help,
}


def _format_tool_result(result: Dict[str, Any]) -> str:
    """Human-readable rendering of a tool result for manual /tool runs.

    The agent loop still feeds raw JSON to the LLM — this is only for the
    person typing a /tool(...) command at the prompt.
    """
    if "error" in result:
        return f"  error: {result['error']}"

    # search_text — {pattern, path, count, matches:[{file, line, text}]}
    if "matches" in result:
        count = result.get("count", len(result["matches"]))
        header = f"  {count} match" + ("" if count == 1 else "es")
        if result.get("truncated"):
            header += " (truncated)"
        lines = [header]
        lines += [f"    {m['file']}:{m['line']}: {m['text']}" for m in result["matches"]]
        return "\n".join(lines)

    # list_files — {path, files:[{filename, type}]}
    if "files" in result:
        lines = [f"  {result.get('path', '')}"]
        for f in result["files"]:
            suffix = "/" if f.get("type") == "dir" else ""
            lines.append(f"    {f['filename']}{suffix}")
        return "\n".join(lines)

    # read_file — {file_path, content}
    if "content" in result:
        return f"  {result.get('file_path', '')}\n{result['content'].rstrip(chr(10))}"

    # run_command — {stdout, stderr, exit_code}
    if "exit_code" in result:
        lines = []
        if result.get("stdout"):
            lines.append(result["stdout"].rstrip("\n"))
        if result.get("stderr"):
            lines.append(result["stderr"].rstrip("\n"))
        lines.append(f"  exit code: {result['exit_code']}")
        return "\n".join(lines)

    # edit_file — {path, action}
    if "action" in result:
        return f"  {result['action']}: {result.get('path', '')}"

    return f"  {json.dumps(result)}"


def dispatch_slash_command(user_input: str) -> bool:
    """
    Handles a /command line. Returns True if the app should exit.

    Two forms, both handled locally (never sent to the LLM):
      /command            — runs a SLASH_REGISTRY handler (e.g. /exit, /help)
      /tool({"arg": ...}) — runs a TOOL_REGISTRY tool directly and prints the result

    Unknown commands print a hint and return False.
    """
    body = user_input[1:].strip()           # drop leading slash
    name = body.split("(", 1)[0].strip()    # "/read_file({...})" -> "read_file"

    # ── Tool form: /tool({...}) — run the tool locally, no LLM ─────
    if name in TOOL_REGISTRY:
        calls = parse_tool_call("tool: " + body)
        if not calls:
            print(f'  usage: /{name}({{"arg": "value"}})')
            return False
        for tool_name, args in calls:
            print(f"  ⚙ {tool_name}({args})")
            result = dispatch_tool(tool_name, args)
            print(_format_tool_result(result))
        return False

    # ── Command form: /exit, /help, … ──────────────────────────────
    parts = body.split()                    # "exit foo" -> ["exit", "foo"]
    if not parts:                            # bare "/" -> no crash
        return False
    handler = SLASH_REGISTRY.get(parts[0])
    if handler is None:
        known = ", ".join("/" + c for c in SLASH_REGISTRY)
        print(f"  unknown command: /{parts[0]}  (available: {known})")
        return False
    return handler()


# ── Interactive prompt: live /-menu of commands and tools ────────────────────
# Typing "/" opens a navigable dropdown (arrow keys + Enter) listing both slash
# commands and tools, like Claude Code. Powered by prompt_toolkit.

def _tool_arg_template(fn) -> str:
    """Builds a JSON arg skeleton from a tool's signature, e.g. {"filename": ""}."""
    params = inspect.signature(fn).parameters
    return json.dumps({p: "" for p in params})


class SlashCompleter(Completer):
    """Completes "/" into the list of slash commands and tools.

    Commands complete to their name (run on Enter). Tools complete to a
    fill-in-the-args template like /read_file({"filename": ""}).
    """

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        if "(" in text:                      # past name selection — filling args
            return
        word = text[1:]                      # text after the slash
        word_lower = word.lower()

        # Commands first, then tools — preserves a natural grouping in the menu.
        for name, fn in SLASH_REGISTRY.items():
            if name.lower().startswith(word_lower):
                yield Completion(
                    name,
                    start_position=-len(word),
                    display=HTML(f"<b>/{name}</b>"),
                    display_meta="command · " + _first_doc_line(fn),
                )
        for name, fn in TOOL_REGISTRY.items():
            if name.lower().startswith(word_lower):
                yield Completion(
                    f"{name}({_tool_arg_template(fn)})",
                    start_position=-len(word),
                    display=f"/{name}",
                    display_meta="tool · " + _first_doc_line(fn),
                )


def _make_key_bindings() -> KeyBindings:
    """Enter accepts a highlighted completion; commands also run immediately."""
    kb = KeyBindings()

    @kb.add("enter")
    def _(event):
        buf = event.current_buffer
        state = buf.complete_state
        if state and state.current_completion:
            comp = state.current_completion
            buf.apply_completion(comp)
            if "(" not in comp.text:         # a command → run on this Enter
                buf.validate_and_handle()
            # a tool template has "(" → stay so the user can fill in args
        else:
            buf.validate_and_handle()

    return kb


_prompt_session = None


def prompt_user(message) -> str:
    """Reads a line of input with the interactive /-menu enabled."""
    global _prompt_session
    if _prompt_session is None:
        _prompt_session = PromptSession(
            completer=SlashCompleter(),
            complete_while_typing=True,
            key_bindings=_make_key_bindings(),
        )
    return _prompt_session.prompt(message)


def run_agent_loop() -> None:
    """The main agent loop — outer loop gets user input, inner loop runs tools."""
    conversation = [
        {"role": "system", "content": build_system_prompt()}
    ]

    print_welcome()

    print(f"letscode — model: {MODEL}")
    print("Type your coding task. /exit or Ctrl+C to quit.\n")

    while True:
        # ── Get user input ─────────────────────────────────────────────
        try:
            user_input = prompt_user(ANSI(f"{YOU_COLOR}You:{RESET_COLOR} ")).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nbye!")
            break

        if not user_input:
            continue

        # ── Slash commands: handled locally, never sent to the LLM ─────
        if user_input.startswith("/"):
            if dispatch_slash_command(user_input):
                break         # quit
            continue          # handled (or unknown) — don't call the LLM

        conversation.append({"role": "user", "content": user_input})

        # ── Inner loop: run until LLM stops calling tools ──────────────
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            response_text = call_llm(conversation)
            tool_calls = parse_tool_call(response_text)

            if not tool_calls:
                conversation.append({"role": "assistant", "content": response_text})
                break

            conversation.append({"role": "assistant", "content": response_text})

            for tool_name, args in tool_calls:
                print(f"  ⚙ {tool_name}({args})")

                result = dispatch_tool(tool_name, args)

                conversation.append({
                    "role": "user",
                    "content": f"tool_result({json.dumps(result)})",
                })

        else:
            print(f"{ASSISTANT_COLOR}letscode:{RESET_COLOR} Hit max iterations — something went wrong. Try again.\n")


def main() -> None:
    if client is None:
        print(
            "OPENROUTER_API_KEY is not set. Add it to a .env file or your "
            "environment.\nGet a free key at https://openrouter.ai/keys"
        )
        raise SystemExit(1)
    run_agent_loop()


if __name__ == "__main__":
    main()