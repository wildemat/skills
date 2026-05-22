#!/usr/bin/env python3
"""SessionStart hook: inject a /skill-try progress line as additional context.

Counts installed skills (local + plugin) and learned entries, then emits a
SessionStart additionalContext payload instructing the model to print
`/skill-try <learned>/<installed>` at the top of its first response.

Reads:
  ~/.claude/skills/*/SKILL.md                       (local skills)
  ~/.claude/plugins/installed_plugins.json          (plugin install paths)
  <installPath>/skills/*/SKILL.md                   (plugin skills)
  ~/.claude/skill-try-learned.json                  (learned record)
"""
import json
import os
import sys


def count_skill_md(directory: str) -> int:
    if not os.path.isdir(directory):
        return 0
    n = 0
    try:
        for entry in os.scandir(directory):
            try:
                if entry.is_dir(follow_symlinks=True) and os.path.isfile(
                    os.path.join(entry.path, "SKILL.md")
                ):
                    n += 1
            except OSError:
                continue
    except OSError:
        return 0
    return n


def main() -> int:
    home = os.path.expanduser("~")
    local_dir = os.path.join(home, ".claude", "skills")
    manifest = os.path.join(home, ".claude", "plugins", "installed_plugins.json")
    learned_file = os.path.join(home, ".claude", "skill-try-learned.json")

    installed = count_skill_md(local_dir)

    try:
        with open(manifest) as f:
            data = json.load(f)
        for entries in data.get("plugins", {}).values():
            if not entries:
                continue
            entry = max(
                entries,
                key=lambda e: e.get("lastUpdated") or e.get("installedAt") or "",
            )
            path = entry.get("installPath")
            if not path:
                continue
            installed += count_skill_md(os.path.join(path, "skills"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    learned = 0
    try:
        with open(learned_file) as f:
            data = json.load(f)
        learned = len(data.get("learned", []))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    if installed == 0:
        return 0

    line = f"/skill-try {learned}/{installed}"

    payload = {
        "systemMessage": line,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                f"The user has already been shown `{line}` as a SessionStart "
                "notice in their terminal. Do NOT print or echo this line in "
                "your response — it would duplicate. /skill-try is a skill "
                "that tours one of the user's installed skills they haven't "
                "covered yet; the counter is learned/installed."
            ),
        },
    }
    json.dump(payload, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
