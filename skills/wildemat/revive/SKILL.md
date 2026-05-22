---
name: revive
description: Get the user productive again on a project they haven't touched in a while. Reads ~/.claude pause files, scans recent commits and branches, surfaces stale plans, and produces a brief, time-boxed plan for the next work session. Use when the user types /revive (optionally with a duration like `/revive 30m`), or says things like "let's pick this back up", "resume this project", "get me back into this", "what was I doing here". Pairs with /pause — always check for a pause file first.
---

# /revive — Resume a project without drowning in context

The user juggles many projects. Most of the time they come back to a repo cold: branches half-merged, plan files out of date, no memory of what they decided last time. This skill gets them productive again in a few minutes — **without** dumping everything they ever wrote at them.

The key idea: **bias toward brevity.** A great revive is 15-25 lines of output that ends with a concrete next action. A bad revive is a wall of summary the user has to re-read to find the point.

## Arguments

The skill takes an optional time budget:

- `/revive` — no budget, give the full picture and let the user choose
- `/revive 30m` / `/revive 1h` / `/revive 2h` — fit the recommended plan into that window

Parse the argument loosely: `30`, `30m`, `30 min`, `30 minutes`, `1h`, `1 hour`, `2 hours`. If parsing fails, ignore it and run with no budget.

## Step 1 — Locate the pause file

Compute the encoded project path from `pwd` (or `git rev-parse --show-toplevel` if in a repo): replace `/` with `-`, prepend `-`. Look for:

```
~/.claude/projects/<encoded-path>/pause.md
```

**If it exists:** announce it. Something like *"Resuming from pause file last updated 2026-05-20 (3 days ago)."* Read it and use it as the spine of the revive.

**If it does not exist:** announce that too — *"No pause file found, building context from scratch."* The revive still works, it just leans entirely on git and the filesystem.

## Step 2 — Gather current reality (in parallel)

Run these regardless of pause file existence:

```bash
git status --short
git branch --show-current
git log -15 --oneline --no-decorate
git branch -vv                                              # local branches + tracking
git log --branches --not --remotes --oneline --no-decorate  # unpushed commits
git stash list
```

Also list:
- `*.md` files at repo root (candidate plan/notes files)
- `docs/`, `plans/`, `notes/` directories if they exist
- Past Claude sessions: `ls -t ~/.claude/projects/<encoded-path>/*.jsonl 2>/dev/null | head -3` (just count and recency, don't read contents unless you need to)
- Past Cursor sessions: workspaces are keyed by hash under `~/Library/Application Support/Cursor/User/workspaceStorage/<hash>/`. Find the one for this project by grepping for the project path in `workspace.json` files:
  ```bash
  grep -l "$(pwd)" ~/Library/Application\ Support/Cursor/User/workspaceStorage/*/workspace.json 2>/dev/null | head -1
  ```
  If a match is found, note the workspace dir and surface the mtime of its `state.vscdb` as "last Cursor session: <date>". Do not try to parse the SQLite chat history inline — just acknowledge it exists. If the user wants to dig in, they can open the workspace in Cursor.

Do not read plan-file contents wholesale. Get filenames and last-modified dates first; only open one if it's clearly load-bearing for the next step.

## Step 3 — Reconcile pause file vs reality

If a pause file existed, cross-check every concrete claim it makes:

- Branches it lists as "in-flight" — do they still exist? Are they merged?
- Decisions it logs — are they reflected in the code (grep for the relevant symbol/file)?
- Files it points at as stale or as plans — do they still exist?
- The `last_commit` in frontmatter — how many commits has the branch moved since?

Build a small mental delta:
- **What's new** since last pause (commits, branches, files)
- **What's gone** (deleted branches, merged PRs, removed files)
- **What's stale** (plan files older than the latest related decision, abandoned branches)

You will surface the delta to the user, and you will update the pause file with corrected state at the end.

## Step 4 — Identify cleanup work

This is a first-class output of `/revive`, not an afterthought. From the reconciliation:

- **Stale branches** — merged into main and safe to delete locally
- **Stale plan files** — superseded by later decisions in the pause log
- **Outdated TODOs** in markdown that conflict with current code

Cleanup is fast, mechanical, and tends to *unblock thinking*. **If a time budget was given and there is cleanup work, cleanup gets the first chunk of the budget.** Tell the user upfront: *"30 minutes — I'd spend ~10 cleaning up X and Y, then ~20 on Z."*

Be specific. "Delete branch `wip/old-search-refactor` (merged 2026-04-10)" — not "tidy up branches."

## Step 5 — Compose the revive output

Use this structure. **Keep each section to 1-5 bullets max.** Cut ruthlessly. The goal is for the user to read this once, top to bottom, and know exactly what to do.

```
## Revive: <project-name>

**Last paused:** <date or "never">    **Branch:** <current> (<N ahead/behind>)
<one sentence: where the work stood — pulled from pause file Current Focus, or inferred from recent commits>

### What's changed since pause
<3-5 bullets — new commits, merged PRs, deleted branches, anything material. Skip the section if nothing changed.>

### Stale / cleanup
<2-5 bullets, each one a concrete deletable thing. Skip if clean.>

### Open questions
<from pause file Open Questions, filtered to ones still relevant. Skip if none.>

### Recommended plan<if a time budget was given, suffix with: " (<duration>)">
1. <concrete action — start here>
2. <next action>
3. <stretch goal if there's room>
```

End the output with the offer:

> *Want me to start on step 1?*

### Time budgeting

If a budget was given, allocate roughly:
- **< 30 min**: cleanup only, or one small focused step. Don't try to start something deep.
- **30-60 min**: cleanup (if any) + one substantive step.
- **1-2 hours**: cleanup + 1-2 substantive steps + maybe a stretch.
- **> 2 hours**: full plan but call out natural break points.

Annotate each step with a rough estimate in parens: `1. Delete merged branches (~5 min)`.

## Step 6 — Update the pause file

After the user has the revive in front of them, **silently update the pause file** to reflect reconciled reality:
- Bump `last_updated` to today.
- Update `current_branch` and `last_commit` in frontmatter.
- Append any new commits to the Commit Log.
- Drop branches/files that no longer exist from In-Flight / Stale sections.
- Preserve the full Key Decisions log unchanged.

If no pause file existed, **do not** create one here — `/pause` is the canonical way to create one. Just leave a note in the revive output: *"No pause file yet — run /pause when you stop to save state for next time."*

## Tone

- Direct, dry, oriented to action. No "Great question!" / "Here's a comprehensive overview!".
- Lead with what's actionable. Background context is a footnote at most.
- If something is genuinely uncertain (e.g., "I can't tell if this branch was abandoned or paused"), say so in one short line. Don't paper over ambiguity.
- It's fine — preferred, actually — to return a short revive when the project is in good shape. "Three uncommitted edits in auth.ts, no stale state, pick up where you left off." is a great revive.

## Notes

- The pause file format is documented in the `/pause` skill. Frontmatter fields: `project_path`, `project_name`, `created`, `last_updated`, `current_branch`, `last_commit`. Body sections: Current Focus, In-Flight Work, Open Questions, Key Decisions, Commit Log, Stale / Can Cleanup.
- If past Claude sessions are unusually rich (e.g., a long planning session yesterday), mention that the session is available without quoting it: *"Yesterday's session went deep on the migration strategy — open it if you need the full thinking."*
- Do not perform cleanup actions yourself. Recommend them; let the user trigger.
