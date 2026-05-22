---
name: skill-try
description: Suggest installed skills the user hasn't tried yet, walk them through one in detail (purpose, when to use, how to invoke, examples, gotchas), and record it as "learned" so future suggestions skip it. Use when the user types /skill-try, asks "what skills do I have", "teach me a skill", "show me an unused skill", or wants to explore their skill library. Accepts an optional argument as a topic, category, or natural-language filter (e.g. /skill-try testing, /skill-try writing, /skill-try "stuff for cleaning up code").
argument-hint: "Optional topic, category, or kind of skill you want to try"
---

# Skill Try

Tour one of the user's installed skills they haven't covered before. Suggest, walk through, record as learned.

## Storage

- **Installed skills:** every directory under `~/.claude/skills/` that contains a `SKILL.md`. The directory name is the skill name.
- **Learned record:** `~/.claude/skill-try-learned.json`. Shape:
  ```json
  {"learned": [{"name": "handoff", "covered_at": "2026-05-22"}]}
  ```
  If the file is missing or malformed, treat as `{"learned": []}` and create it on first write.

## Process

### 1. Enumerate

- `ls ~/.claude/skills/` and keep only directories with a `SKILL.md` inside.
- Read each `SKILL.md`'s frontmatter `name` and `description`.
- Load `~/.claude/skill-try-learned.json`. Build a set of learned names.
- Candidate set = installed minus learned.

### 2. Handle the argument

`$ARGUMENTS` may be empty, a topic ("testing", "writing"), a category, a fuzzy phrase, or an exact skill name.

- **Empty** — pick ~5 candidates at random, biased for variety across categories (infer category from path if possible).
- **Exact match** on a candidate skill name — skip suggestion, go straight to step 4 with that skill.
- **Otherwise** — semantic match `$ARGUMENTS` against each candidate's name + description. Pick the top 3–5.

If the candidate set is empty (everything is learned), congratulate the user and stop. Mention they can reset by deleting `~/.claude/skill-try-learned.json`.

### 3. Present candidates

Use `AskUserQuestion` with one question, options labelled by skill name. Each option's description is the skill's own one-line summary (trim/paraphrase its `description` field — don't dump the whole thing).

### 4. Walk through the chosen skill

Read the chosen skill's full `SKILL.md` (and any sibling `REFERENCE.md` / `EXAMPLES.md` if you need them). Reply with these sections, in order, in markdown:

1. **What it does** — one or two plain-language sentences. No jargon dump.
2. **When to use it** — the trigger conditions. Pull from the `description` and any inline trigger lists.
3. **How to invoke** — slash command, trigger phrases, or natural conversation cues. If it takes an argument, show the shape.
4. **Examples** — 2–3 concrete scenarios. Ground them in the user's actual repos / context when obvious; otherwise use realistic synthetic ones.
5. **Gotchas** — non-obvious bits a user only learns by trying it: prerequisites, side effects, what it does NOT do, common confusions.

Keep it tight — a guided tour, not a re-render of the file.

### 5. Q&A

Ask: "Any questions about this one, or ready to move on?" Answer follow-ups by re-reading the skill's files. Don't guess.

### 6. Mark as learned

When the user signals they're done with this skill (says "done", "got it", "next", "ok thanks", asks for another skill, or otherwise wraps up), append to `~/.claude/skill-try-learned.json`:

```json
{"name": "<skill-name>", "covered_at": "YYYY-MM-DD"}
```

Use today's date. Read-modify-write the file; don't overwrite previous entries.

### 7. Offer another

Ask if they want another tour. If yes, loop to step 2 with the same `$ARGUMENTS` (or fresh ones if they give new direction). If no, stop.

## Notes

- The learned record is global, not per-project. Once learned, a skill won't be suggested in any project until the user clears the record.
- Don't suggest the same skill twice in one session.
- If the user explicitly names a skill that's already in the learned list, walk through it anyway — they asked for it. Don't double-record it.
- This skill counts only `~/.claude/skills/`. Plugin-managed and built-in skills aren't tracked here; that keeps "installed" stable and user-controlled.
