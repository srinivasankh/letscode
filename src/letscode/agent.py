import os
import subprocess

from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# OpenRouter is OpenAI-API-compatible — same SDK, different base_url
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
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


# ── Registry: name → function ──────────────────────────────────────────────

TOOL_REGISTRY = {
    "read_file": read_file,
    "list_files": list_files,
    "edit_file": edit_file,
    "run_command": run_command,
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
            user_input = input(f"{YOU_COLOR}You:{RESET_COLOR} ").strip()
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
    run_agent_loop()


if __name__ == "__main__":
    main()