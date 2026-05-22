#!/usr/bin/env python3
"""Enumerate all installed skills (local + plugin) and the learned record.

One call replaces N bash invocations (`ls`, `head -5`, etc.) the agent
would otherwise make. Output goes to stdout as JSON.

Shape:
{
  "installed": [
    {"id": "handoff", "name": "handoff", "description": "...",
     "source": "local", "path": "/.../handoff"},
    {"id": "figma:figma-use", "name": "figma-use", "description": "...",
     "source": "figma", "marketplace": "claude-plugins-official", "path": "..."}
  ],
  "learned": [{"id": "...", "source": "...", "covered_at": "YYYY-MM-DD"}],
  "candidates": [ ...installed entries whose id is NOT in learned... ],
  "counts": {"installed": N, "learned": M, "candidates": K}
}
"""
import json
import os
import re
import sys


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
# description: can be a single line OR a YAML folded block (`description: >`)
# We capture until the next top-level YAML key or the end of frontmatter.
DESC_RE = re.compile(
    r"^description:\s*(.*?)(?=\n[A-Za-z_][A-Za-z0-9_-]*:\s|\Z)",
    re.DOTALL | re.MULTILINE,
)


def parse_frontmatter(path: str):
    try:
        with open(path) as f:
            content = f.read(8192)
    except OSError:
        return None, None
    m = FRONTMATTER_RE.match(content)
    if not m:
        return None, None
    body = m.group(1)
    name_m = NAME_RE.search(body)
    desc_m = DESC_RE.search(body)
    name = name_m.group(1).strip() if name_m else None
    description = ""
    if desc_m:
        raw = desc_m.group(1).strip()
        # Strip a leading '>' or '|' YAML folded/literal indicator.
        raw = re.sub(r"^[>|][-+]?\s*\n?", "", raw)
        # Strip surrounding quotes if it was a single-line quoted string.
        if (raw.startswith('"') and raw.endswith('"')) or (
            raw.startswith("'") and raw.endswith("'")
        ):
            raw = raw[1:-1]
        # Collapse whitespace.
        description = re.sub(r"\s+", " ", raw).strip()
    return name, description


def collect_skills(skills_dir: str, source: str, marketplace: str | None = None):
    out = []
    if not os.path.isdir(skills_dir):
        return out
    try:
        for entry in os.scandir(skills_dir):
            try:
                if not entry.is_dir(follow_symlinks=True):
                    continue
            except OSError:
                continue
            skill_md = os.path.join(entry.path, "SKILL.md")
            if not os.path.isfile(skill_md):
                continue
            name, description = parse_frontmatter(skill_md)
            display_name = name or entry.name
            skill_id = entry.name if source == "local" else f"{source}:{entry.name}"
            record = {
                "id": skill_id,
                "name": display_name,
                "description": description or "",
                "source": source,
                "path": entry.path,
            }
            if marketplace:
                record["marketplace"] = marketplace
            out.append(record)
    except OSError:
        pass
    return out


def main() -> int:
    home = os.path.expanduser("~")
    local_dir = os.path.join(home, ".claude", "skills")
    manifest = os.path.join(home, ".claude", "plugins", "installed_plugins.json")
    learned_file = os.path.join(home, ".claude", "skill-try-learned.json")

    installed = collect_skills(local_dir, "local")

    try:
        with open(manifest) as f:
            data = json.load(f)
        for key, entries in data.get("plugins", {}).items():
            if not entries:
                continue
            entry = max(
                entries,
                key=lambda e: e.get("lastUpdated") or e.get("installedAt") or "",
            )
            install_path = entry.get("installPath")
            if not install_path:
                continue
            plugin_name, _, marketplace = key.partition("@")
            installed.extend(
                collect_skills(
                    os.path.join(install_path, "skills"),
                    plugin_name,
                    marketplace or None,
                )
            )
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    learned = []
    try:
        with open(learned_file) as f:
            data = json.load(f)
        learned = data.get("learned", [])
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    learned_ids = {item.get("id") or item.get("name") for item in learned}
    learned_ids.discard(None)

    candidates = [s for s in installed if s["id"] not in learned_ids]

    installed.sort(key=lambda s: s["id"])
    candidates.sort(key=lambda s: s["id"])

    output = {
        "installed": installed,
        "learned": learned,
        "candidates": candidates,
        "counts": {
            "installed": len(installed),
            "learned": len(learned),
            "candidates": len(candidates),
        },
    }
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
