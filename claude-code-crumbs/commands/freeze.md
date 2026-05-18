---
description: Freeze preset-driven configuration into project-local commands and agents.
argument-hint: "[--dry-run] [--reset] [--force]"
---

# /freeze

Freeze the plugin's preset-driven commands and agents into project-local copies under `.claude/commands/` and `.claude/agents/`. Once frozen, the project consumes its own local copies — not the plugin's source — so toggles encoded in `<!-- FREEZE:IF ... -->` markers resolve **once**, at freeze time, against the project's resolved configuration.

This command delegates to `scripts/freeze.sh`. See `MARKERS.md` for the marker spec.

## What it does

1. Reads `.claude/stack.yaml` for `team_preset`.
2. Reads the YAML toggle block from `.claude/ruleset/git-workflow.md` and `.claude/ruleset/deployment.md`.
3. Builds a resolver dictionary (`preset`, `pr_required`, `require_reviewers`, …).
4. Walks every `commands/*.md` and `agents/*.md` in the plugin source.
5. Parses `<!-- FREEZE:IF/ELIF/ELSE/ENDIF -->` blocks and `<!-- FREEZE:VAL key -->fallback<!-- FREEZE:ENDVAL -->` inline substitutions.
6. Emits the resolved output to `.claude/commands/<name>.md` / `.claude/agents/<name>.md` — **markers stripped, only the selected branch present**.
7. Files marked `<!-- FREEZE:SKIP -->` (e.g. `/000-prd-refine`, the bootstrap) are excluded.
8. Files with no markers are copied verbatim (still creates a project-local override).

## When to re-freeze

Run `/freeze --force` after any of:

- **Preset change** — you edited `.claude/stack.yaml` and switched `team_preset` (e.g. solo → small-team).
- **Toggle change** — you hand-edited `git-workflow.md` or `deployment.md` to override a single toggle (e.g. flipped `pr_required: true` while staying on solo preset).
- **Plugin update** — `claude-code-crumbs` published a new version of a command/agent. `git pull` in the plugin dir won't reach you until you re-freeze.

`/freeze` without `--force` refuses to overwrite an already-frozen tree (exit 5). This is intentional — refreezing is a deliberate act.

## How to revert

```
/freeze --reset           # prompts for confirmation
/freeze --reset --force   # no prompt
```

`--reset` removes `.claude/commands/` and `.claude/agents/` entirely. The project falls back to the plugin's source files (which still contain the markers, which are inert in Claude Code's command runner — they render as HTML comments).

## Dry run

```
/freeze --dry-run
```

Prints a per-file summary (`+taken/-pruned branches`) without writing anything. Use this before a destructive re-freeze to preview what will change.

## Scope

`/freeze` resolves the **preset-driven** subset of configuration. The following stay dynamic (re-read at every command invocation, not baked in):

- `stack.yaml.gates` — gate commands change with the stack (lint/typecheck/build) and shift mid-project; they're shell strings, not preset toggles.
- Runtime state — `runs/`, `epic-*-tasks.yaml`, the working PRD.
- Per-task `rules_in_scope` selection — task-level, not preset-level.
- The `extras: {}` free-form map in `stack.yaml`, propagated verbatim to subagents.

Scope is fixed to **preset-driven** keys. Stack-level toggles, gates, and runtime state remain dynamic by design.

## One-way ticket

Freezing is **not** a fully reversible operation. `/freeze --reset` restores plugin-source fallback, but any **hand-edits** you made to the frozen `.claude/commands/*.md` after the freeze are lost. The frozen files exist to be customised — that's the whole point — but the cost is that revert is destructive. Commit your frozen tree to git before you start hand-editing, and you have a recovery path; otherwise the only recovery is re-freeze + re-apply edits.

## Underlying script

`scripts/freeze.sh` — same flags. Run directly for CI / non-interactive contexts:

```
bash scripts/freeze.sh --force --plugin-root=/path/to/claude-code-crumbs
```

Self-test: `bash scripts/test-freeze.sh` (exit 0 = pass).

## Exit codes

- `0` — success
- `1` — missing config (`stack.yaml`, ruleset files)
- `2` — marker parse error (unterminated IF, stray ELIF, malformed expression)
- `3` — expression evaluation error (bad key syntax)
- `4` — IO error (read/write/mkdir failed)
- `5` — already frozen; re-run with `--force` or `--reset`
