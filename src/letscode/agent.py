import os

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


def resolve_abs_path(path_str: str) -> Path:
    """Converts a relative path like 'hello.py' to an absolute path."""
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path



from typing import Any, Dict


# ── Tool 1: Read a file ────────────────────────────────────────────────────

def read_file(filename: str) -> Dict[str, Any]:
    """
    Gets the full content of a file provided by the user.
    :param filename: The name of the file to read.
    :return: The full content of the file.
    """
    full_path = resolve_abs_path(filename)
    with open(str(full_path), "r") as f:
        content = f.read()
    return {
        "file_path": str(full_path),
        "content": content,
    }


# ── Tool 2: List files in a directory ─────────────────────────────────────

def list_files(path: str) -> Dict[str, Any]:
    """
    Lists the files in a directory provided by the user.
    :param path: The path to a directory to list files from.
    :return: A list of files in the directory.
    """
    full_path = resolve_abs_path(path)
    all_files = []
    for item in full_path.iterdir():
        all_files.append({
            "filename": item.name,
            "type": "file" if item.is_file() else "dir",
        })
    return {
        "path": str(full_path),
        "files": all_files,
    }


# ── Tool 3: Edit (or create) a file ───────────────────────────────────────

def edit_file(path: str, old_str: str, new_str: str) -> Dict[str, Any]:
    """
    Replaces first occurrence of old_str with new_str in a file.
    If old_str is empty, creates or overwrites the file with new_str.
    :param path: The path to the file to edit.
    :param old_str: The string to replace. Pass empty string to create a new file.
    :param new_str: The string to replace with, or the full content of the new file.
    :return: A dictionary with the path and the action taken.
    """
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


# ── Registry: name → function ──────────────────────────────────────────────

TOOL_REGISTRY = {
    "read_file": read_file,
    "list_files": list_files,
    "edit_file": edit_file,
}

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



def main() -> None:
    print(f"letscode — model: {MODEL} ✓")
    print(f"tools loaded: {list(TOOL_REGISTRY.keys())}")
    print("\n── System prompt preview ──")
    print(build_system_prompt())


if __name__ == "__main__":
    main()