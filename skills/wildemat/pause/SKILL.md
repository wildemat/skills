---
name: pause
description: Snapshot the current project state into a pause file under ~/.claude so /revive can pick it back up later. Use when the user says they're stopping for now, wrapping up a session, switching contexts, or types /pause. Trigger words include "pause", "wrap up", "stop here for now", "I need to switch projects", "save state". Always pair with /revive — this skill writes what /revive reads.
---

# /pause — Snapshot project state for later revival

The user works across many projects in parallel and frequently switches contexts. This skill writes a single, canonical pause file that captures *just enough* state for `/revive` to get them productive again — without polluting the repo (so no committed plan files).

## Storage location (canonical)

Pause files live at:

```
~/.claude/projects/<encoded-cwd>/pause.md
```

Where `<encoded-cwd>` is the absolute working directory with every `/` replaced by `-`. For example:
- `/Users/wildmat/Github/engage` → `~/.claude/projects/-Users-wildmat-Github-engage/pause.md`
- `/Users/wildmat/workplace/kibana` → `~/.claude/projects/-Users-wildmat-workplace-kibana/pause.md`

This co-locates with Claude's existing per-project state (sessions, memory). The directory usually exists already; create it if not. **One file per project — update in place, never version by filename.**

## What to do

### Step 1 — Identify the project

```bash
pwd                          # absolute current working directory
git rev-parse --show-toplevel 2>/dev/null  # repo root if in a repo
```

If `pwd` is inside a git repo, use the repo root as the project path. Encode it (replace `/` with `-`, prepend `-`) to get the pause file path.

### Step 2 — Gather current reality (in parallel)

```bash
git status --short                                         # uncommitted changes
git branch --show-current                                  # current branch
git log -20 --oneline --no-decorate                        # recent commits
git stash list                                             # stashes
git branch -vv                                             # all local branches w/ upstream
git log --branches --not --remotes --oneline --no-decorate # unpushed commits across branches
```

Also list candidate plan/doc files: `*.md` at repo root, plus `docs/`, `plans/`, `notes/` if they exist (do not read contents yet — just list).

### Step 3 — Read the existing pause file if present

If `pause.md` already exists, read it. You will **update it in place**, preserving:
- The full **Key Decisions** log (append-only — never delete old entries)
- The full **Commit Log** (append-only — append new commits, keep old ones)
- The original `created:` date in frontmatter

Everything else (Current Focus, In-Flight Work, Open Questions, Stale/Cleanup) is **live state** and gets rewritten to reflect today.

### Step 4 — Synthesize the state

Pull from the conversation transcript and the git data:

- **Current Focus** — one short paragraph: what was being worked on this session and *why*.
- **In-Flight Work** — branch name, files touched, uncommitted changes, the concrete next 1-3 steps.
- **Open Questions / Blockers** — anything unresolved, including decisions the user hasn't made yet.
- **Key Decisions** — append new dated entries for any meaningful choice made this session. Format: `- YYYY-MM-DD: <decision> — <one-sentence reason>`. Skip if nothing decided.
- **Commit Log** — append any new commits since the last pause as `- <hash> (YYYY-MM-DD): <one-sentence summary>`. If no prior pause file, seed with the last 10 commits.
- **Stale / Can Cleanup** — branches that were abandoned, plan files superseded by decisions, dead code or notes. Be specific (`branch wip/old-foo`, `PLAN_v1.md`).

Keep it terse. This file is read every revive — every line earns its place. Aim for under 100 lines total.

### Step 5 — Verify reality, prune stale claims

Before writing, check the existing file (if any) against current reality:
- Branches listed as in-flight that no longer exist → move to a `## Recently Closed` entry or drop entirely.
- Decisions that were later reversed → keep the original entry but add a follow-up dated entry noting the reversal.
- Files referenced that no longer exist → drop them.

The goal: **a future read of this file should never lie about the filesystem.**

### Step 6 — Write the file

Use this exact template:

```markdown
---
project_path: <absolute path>
project_name: <basename of project_path>
created: <YYYY-MM-DD — original creation date, preserved>
last_updated: <YYYY-MM-DD — today>
current_branch: <branch name>
last_commit: <short sha>
---

# <project_name> — Paused State

## Current Focus
<one short paragraph: what was being worked on and why>

## In-Flight Work
- Branch: `<branch>` (<N ahead / N behind main>)
- Uncommitted: <short description, or "none">
- Next steps:
  - [ ] <concrete step>
  - [ ] <concrete step>

## Open Questions / Blockers
- <question or blocker, or omit section if none>

## Key Decisions
- YYYY-MM-DD: <decision> — <reason>
- ...

## Commit Log
- <sha> (YYYY-MM-DD): <one-line summary>
- ...

## Stale / Can Cleanup
- <thing to clean up, with why>
- ...
```

Omit any section that has no content rather than leaving it empty.

### Step 7 — Confirm to the user

Print a short confirmation (3-5 lines max):
- Where the file was written
- How many decisions / commits / cleanup items it now tracks
- One sentence on what `/revive` will see next time

Do **not** dump the file contents — the user knows what they just paused.

## Notes

- Never commit pause files. They live in `~/.claude/`, never in the repo.
- If the cwd is not inside a git repo, still write a pause file using the directory itself as `project_path`. Skip git-specific sections.
- The Key Decisions log is append-only — old entries are how `/revive` rebuilds context months later. Never rewrite history; if something is wrong, add a corrective entry.
