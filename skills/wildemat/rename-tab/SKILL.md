---
name: rename-tab
description: >
  Rename the current Claude Code terminal tab to a custom title.
  Use when the user types /rename-tab <title> or asks to rename or
  retitle the current tab. Unlike the built-in /rename, this does not
  append MCP server names as a suffix.
allowed-tools: Bash(python3 *)
---

# /rename-tab

Sets the terminal tab title via the tab-title plugin's `--topic` flag,
which writes the OSC sequence directly to the PTY — no MCP suffix.

Extract the desired title from the user's message (everything after `/rename-tab`).
If no title was given, use the basename of the current working directory.

```bash
python3 ~/.claude/plugins/marketplaces/claude-code-tab-title/plugins/tab-title/tab-state.py --topic "TITLE"
```

Reply with a single line: `Tab renamed to "TITLE"`. Nothing else.
