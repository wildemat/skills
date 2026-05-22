---
name: project-state
description: Show an interactive cross-project dashboard — paused projects (from ~/.claude pause files) plus un-paused candidates from ~/Github (personal) and ~/workplace (work). Lets the user pick a project, drill into its state, and get a time-boxed recommendation for what to work on next. Use when the user types /project-state, asks "what should I work on", "what projects do I have going", "what's on my plate", "show me my projects", or wants to choose between projects to resume.
---

# /project-state — Cross-project dashboard

The user runs many parallel projects across two roots: `~/Github` (personal) and `~/workplace` (work). Some have pause files written by `/pause`; many don't. This skill gives them an interactive way to see *everything* and pick the right next thing to work on — possibly with a time budget.

The interaction model is conversational, not a TUI. Use `AskUserQuestion` for selections; let the user type "back" to return to the previous level.

## Step 1 — Choose scope

If the user did not include scope in their invocation, ask:

```
AskUserQuestion:
  question: "Personal or work projects?"
  header: "Scope"
  options:
    - label: "Personal (~/Github)"
    - label: "Work (~/workplace)"
    - label: "Both"
```

Default to whichever the user mentions if they include hints (e.g., "show me my elastic projects" → work).

## Step 2 — Build the project list

For the chosen scope, list immediate subdirectories of `~/Github` and/or `~/workplace`. Filter to plausible projects: directories that contain a `.git`, a `package.json`, a `pyproject.toml`, a `Cargo.toml`, a `go.mod`, a `pom.xml`, or any other obvious project marker. Skip dotfiles, `.zip` archives, `*.code-workspace` files, and bare files.

For each project, also check for a pause file at:

```
~/.claude/projects/-Users-wildmat-<root>-<projectname>/pause.md
```

This gives every project one of three statuses:

- **Paused** — pause file exists. Has rich state from `/pause`.
- **Active (no pause)** — `.claude/projects/<encoded-path>/` exists (Claude has been used in it) but no pause file. Pull last-used date from the session file mtime.
- **Cold** — directory exists but never used with Claude. Pull last-modified date from the directory itself.

Sort by recency descending (most recently touched first).

## Step 3 — Show the top-level summary

Present the list compactly. Aim for one line per project. Group by status:

```
## Projects — Personal (~/Github)

### Paused (have /pause state)
 1. engage             — 2026-05-20 (2 days ago) — feature/search-refactor • 2 next steps
 2. foqos              — 2026-05-10 — main • cleanup recommended
 3. handshaker         — 2026-04-22 — 1 blocker

### Active (recent Claude sessions, no pause)
 4. immich-app         — 2026-05-19
 5. fizzfinder         — 2026-05-15

### Cold (no recent Claude work)
 6. hyrox              — 2026-03-01
 7. iosFitnessStream   — 2026-02-14
 ...
```

For paused projects, pull the one-line "Current Focus" first sentence and the count of unchecked next steps from the pause file. For active/cold, just show the date.

If the list is long (>15), show the top 10 and offer to expand.

End with:

> *Type a number to drill in, "back" to change scope, or "what fits 30 minutes" to get a recommendation.*

## Step 4 — Drill-down on a project

When the user picks a project, show its detail view. Pull from the pause file if it exists; otherwise gather minimal git state.

### Paused project detail
```
## engage — paused 2026-05-20

Current focus: <one-paragraph from pause file>

Branch: feature/search-refactor (3 ahead of main)
Uncommitted: src/foo.ts, src/bar.ts

Next steps:
 1. [ ] Wire up the new search result formatter
 2. [ ] Add tests for the empty-query path

Open questions:
 - Should we keep the legacy fallback or remove it?

Recent decisions:
 - 2026-05-19: chose protobuf over JSON for the internal payload (perf)
 - 2026-05-15: dropped support for v1 clients

Cleanup pending: branch `wip/old-search`, PLAN_v1.md
```

End with:

> *Type "revive" to start a session here (I'll give you the command), "back" to return to the list, or ask anything about this project.*

### Active / cold project detail
Skip pause-file sections; just show git branch, last commit, top-level markdown files. Mention that running `/revive` in this directory will build initial context.

## Step 5 — Time-boxed recommendation

If the user asks something like "what fits 30 minutes" or "what can I knock out in an hour":

1. Look across **all paused projects** in the current scope.
2. Score candidates by:
   - **Fit** — does the smallest concrete next step plausibly fit the budget? (Use rough heuristics: a single bug fix = 30 min, a refactor = 1-2h.)
   - **Momentum** — projects paused more recently are easier to resume than cold ones.
   - **Cleanup wins** — projects with stale state listed under "Stale / Can Cleanup" are great for short sessions because cleanup is mechanical and high-value.
3. Surface 2-3 candidates with the suggested step and rough time estimate. Example:

```
For 30 minutes, I'd suggest:

  1. foqos — delete 3 merged branches + close out stale TODO in README (~15 min cleanup)
  2. engage — write the test for the empty-query path (small, well-scoped, ~25 min)
  3. handshaker — only good if you want to think; the open blocker is a real decision

Pick one and I'll give you the command to start.
```

When the user picks one, output the command to run:

```bash
cd /Users/wildmat/Github/engage && claude
```

And the suggested first message to Claude in that new session:

> `/revive 30m`

## Step 6 — Navigation

Throughout the interaction, accept these commands without making the user re-invoke the skill:
- A number → drill into that project
- `back` → return to the previous view
- `scope` → change personal/work/both
- `quit` / `done` → end the interaction
- Any free-text question about the current project → answer from the pause file + git data

## Notes

- Read pause files at most once per project per invocation. Cache the parsed result in memory.
- Never modify pause files in this skill — that's `/pause`'s job. This skill is read-only.
- If a pause file references a directory that no longer exists, surface it under a small "Orphaned pause files — likely safe to delete" footer rather than mixing it into the live list.
- If both roots are requested ("both"), interleave by recency rather than showing two separate sections.
- The user's home is `/Users/wildmat`. Personal root: `/Users/wildmat/Github`. Work root: `/Users/wildmat/workplace`. Hard-code these — they're stable.
