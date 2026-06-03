## [0.1.0] - 2026-06-03

### 🚀 Features

- Add three tools — read_file, list_files, edit_file
- Enhance system prompt and tool descriptions in agent
- Add LLM call and tool call parser functions
- Implement main agent loop for user interaction and tool execution
- Add welcome banner and print_welcome function to agent
- Update agent to record assistant responses before tool execution
- Enhance file handling functions with error handling and iteration limit in agent loop
- Add run_command tool with confirm-before-run gate
- Stream LLM output token-by-token to terminal
- Add slash-command registry and dispatch_slash_command
- Handle /exit in agent loop, mention it in help text

### 🐛 Bug Fixes

- Catch TimeoutExpired in run_command, add timeout test
- Use getattr for delta.content to guard against missing attribute in stream

### 🚜 Refactor

- Extract dispatch_tool, replace elif chain with **kwargs dispatch

### 📚 Documentation

- Add CLAUDE.md with project architecture and context
- Rewrite README with full project overview and BYOK guide
- Remove credits section and external reference from README
- Add design spec for generic dispatch, run_command, and streaming
- Add implementation plan for generic dispatch, run_command, and streaming
- Design spec for /exit slash command + registry
- Implementation plan for /exit slash command
- Add loop-integration tests to Task 2 (TDD)

### 🧪 Testing

- Set up pytest infrastructure with dev dependencies
- Guard that normal prompts still reach the LLM

### ⚙️ Miscellaneous Tasks

- Add project config files and scaffold
- Update .gitignore to include hello.py and *.egg-info
- Prepare package for PyPI (letscode-cli, MIT, graceful no-key exit)
- Sync uv.lock with letscode-cli rename
- Exclude CLAUDE.md and docs/ from sdist
