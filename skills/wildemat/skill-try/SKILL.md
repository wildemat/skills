---
name: skill-try
description: Suggest installed skills the user hasn't tried yet (including plugin-managed skills), walk them through one in detail (purpose, when to use, how to invoke, examples, gotchas) with attribution to the source plugin if applicable, and record it as "learned" so future suggestions skip it. Use when the user types /skill-try, asks "what skills do I have", "teach me a skill", "show me an unused skill", or wants to explore their skill library. Accepts an optional argument as a topic, category, or natural-language filter (e.g. /skill-try testing, /skill-try writing, /skill-try "stuff for cleaning up code").
argument-hint: "Optional topic, category, or kind of skill you want to try"
---

# Skill Try

Tour one of the user's installed skills they haven't covered before. Suggest, walk through, record as learned.

## First-run setup (Claude Code only)

Before enumerating, verify the SessionStart progress counter is wired up. This puts `/skill-try <learned>/<installed>` in the session-start area of every new Claude Code session, so the user is reminded the skill exists.

Check both of these:

- File `~/.claude/bin/skill-try-count.py` exists.
- `~/.claude/settings.json` has a `SessionStart` hook whose command invokes that script (`python3 $HOME/.claude/bin/skill-try-count.py` or equivalent).

If either is missing, ask the user (one `AskUserQuestion`, default "Install") whether to install the counter. On "Install":

1. Copy `scripts/skill-try-count.py` (bundled next to this `SKILL.md`) to `~/.claude/bin/skill-try-count.py`. Create `~/.claude/bin/` if missing. `chmod +x` it.
2. Read `~/.claude/settings.json`, parse JSON, and merge in:
   ```json
   "hooks": {
     "SessionStart": [
       {
         "hooks": [
           {"type": "command", "command": "python3 $HOME/.claude/bin/skill-try-count.py"}
         ]
       }
     ]
   }
   ```
   If a `hooks.SessionStart` array already exists, append the command entry only if no existing entry already points at `skill-try-count.py`. Preserve all other settings exactly.
3. Tell the user the counter will appear from their next Claude Code session onward — it won't show in the current one (hook only fires at session start).

If the user declines, drop the setup and proceed to enumeration. Don't ask again this session.

Skip this section entirely for non-Claude-Code agents (Cursor etc.) — they get the line via the `~/.agents/extensions/AGENTS.md` directive instead, which is a model-side instruction, not a hook.

## Storage

Every skill has a fully-qualified id used in storage and presentation:

- **Local skill** → id is just the directory name. Example: `handoff`.
- **Plugin skill** → id is `<plugin>:<skill-name>`, matching how the harness exposes it. Example: `figma:figma-use`.

Sources:

- **Local skills:** every directory under `~/.claude/skills/` containing a `SKILL.md`. Source = `local`.
- **Plugin skills:** read `~/.claude/plugins/installed_plugins.json`. For each `<plugin>@<marketplace>` key, take the most-recent entry's `installPath`. Then list `<installPath>/skills/*/SKILL.md`. Source = the `<plugin>` portion of the key. A plugin with no `skills/` directory contributes nothing.
- **Learned record:** `~/.claude/skill-try-learned.json`. Shape:
  ```json
  {"learned": [{"id": "figma:figma-use", "source": "figma", "covered_at": "2026-05-22"}]}
  ```
  If the file is missing or malformed, treat as `{"learned": []}` and create it on first write. Old entries using `name` instead of `id` should be treated as ids (read-compat).

## Process

### 1. Enumerate (single call)

Run the bundled list script in **one** Bash call — do not stack `ls`, `head`, or per-skill greps:

```
python3 ~/.claude/skills/skill-try/scripts/skill-try-list.py
```

It returns JSON with `installed`, `learned`, `candidates`, and `counts`. Each skill entry has `id`, `name`, `description`, `source`, `path`, and (for plugin skills) `marketplace`. Use `candidates` directly — it's installed minus learned, already filtered.

Do NOT re-enumerate by hand. The script handles local skills, plugin skills via `~/.claude/plugins/installed_plugins.json`, frontmatter parsing (including folded YAML descriptions), and learned-record filtering in a single pass.

### 2. Handle the argument

`$ARGUMENTS` may be empty, a topic ("testing", "writing"), a category, a fuzzy phrase, or an exact skill id.

- **Empty** — pick exactly **4** candidates at random, biased for variety: mix local and plugin sources, and spread across plugins when possible.
- **Exact id match** on a candidate (`handoff`, `figma:figma-use`) — skip suggestion, go straight to step 4.
- **Otherwise** — semantic match `$ARGUMENTS` against each candidate's name + description + source. Pick the top **4**. Source counts as signal: "figma" should rank figma skills high.

Cap at 4 (never more) because `AskUserQuestion` rejects >4 options. If fewer than 4 candidates exist, present what you have (min 2).

If the candidate set is empty (everything learned), congratulate the user and stop. Mention they can reset by deleting `~/.claude/skill-try-learned.json`.

### 3. Present candidates

Use `AskUserQuestion` with **2–4 options** (hard tool limit — never pass more). Each option:

- `label` — the skill id (e.g. `handoff`, `figma:figma-use`).
- `description` — trimmed one-line summary plus source tag, e.g. `(figma plugin) Translate code into Figma designs` or `(local) Compact the current conversation into a handoff document`. Pull the summary from the script's `description` field; trim to ~100 chars.

### 4. Walk through the chosen skill

Read the chosen skill's full `SKILL.md` from its `path` (which the list script already gave you — no need to re-search). Read any sibling reference files in the same directory if they exist. Reply with these sections, in order, in markdown:

1. **Source** — one line. For local: ``Local skill — `<path>/SKILL.md` ``. For plugin: `From the **<plugin>** plugin (marketplace: <marketplace>)`. Both `path` and `marketplace` come from the list script's output.
2. **What it does** — one or two plain-language sentences. No jargon dump.
3. **When to use it** — trigger conditions. Pull from the `description` and any inline trigger lists.
4. **How to invoke** — slash command, trigger phrases, or natural conversation cues. If it takes an argument, show the shape. Note any required prerequisite skills (e.g. figma's MANDATORY-prerequisite skills).
5. **Examples** — 2–3 concrete scenarios. Ground them in the user's actual repos / context when obvious; otherwise realistic synthetic ones.
6. **Gotchas** — non-obvious bits a user only learns by trying it: prerequisites, side effects, what it does NOT do, common confusions. For plugin skills, mention any plugin-specific quirks (MCP server required, auth flow, etc.).

Keep it tight — a guided tour, not a re-render of the file.

### 5. Q&A

Ask: "Any questions about this one, or ready to move on?" Answer follow-ups by re-reading the skill's files. Don't guess.

### 6. Mark as learned

When the user signals they're done with this skill (says "done", "got it", "next", "ok thanks", asks for another skill, or otherwise wraps up), append to `~/.claude/skill-try-learned.json`:

```json
{"id": "<skill-id>", "source": "<local-or-plugin-name>", "covered_at": "YYYY-MM-DD"}
```

Use today's date. Read-modify-write — don't overwrite previous entries.

### 7. Offer another

Ask if they want another tour. If yes, loop to step 2 with the same `$ARGUMENTS` (or fresh ones if they give new direction). If no, stop.

## Notes

- The learned record is global, not per-project. Once learned, a skill won't be suggested in any project until the user clears the record.
- Don't suggest the same skill twice in one session.
- If the user explicitly names a skill that's already learned, walk through it anyway — they asked for it. Don't double-record it.
- This skill does not track built-in harness skills (`/loop`, `/run`, `/verify`, etc.) — those aren't user-installed.
