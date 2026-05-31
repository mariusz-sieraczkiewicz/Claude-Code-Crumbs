# `.claude/runs/` — subagent communication

This directory is the **filesystem-based IPC layer** between subagents spawned by `/001-plan`, `/002-implement`, `/003-verify-dod`, `/004-code-review`, and `/005-implement-feedback`. Each subagent runs in isolated context; phase artifacts here are how they hand off state.

## Purpose

Subagents do not share memory. Each phase writes one JSON file; the next phase reads **all prior phase files for the same task** as input. The history is append-only — earlier phase files are never edited in place.

## Layout

```
.claude/runs/
  {epic-id}/                          # e.g. E-007/
    {task-id}/                        # e.g. T-007-03/
      01-plan.json                    # planner output
      02-impl.json                    # implementer output (incl. "too_big_proposal" signal)
      03-verify.json                  # verifier (DoD gate) output
      04-review.json                  # reviewer output
      05a-feedback-impl.json          # feedback-implementer, first iteration
      05b-feedback-impl.json          # second iteration (if needed)
      05c-feedback-impl.json          # third iteration (rare)
      artifacts/                      # transient files (logs, drafts, diffs) — not schema-validated
    00-plan-questions.json            # epic-level clarifying questions from planner (optional)
```

## Phase files

| File | Producer | Trigger |
|---|---|---|
| `01-plan.json` | `planner` | `/001-plan` (fresh or re-split) |
| `02-impl.json` | `implementer` | `/002-implement` per task |
| `03-verify.json` | `verifier` | `/003-verify-dod` |
| `04-review.json` | `reviewer` | `/004-code-review` |
| `05{a,b,c…}-feedback-impl.json` | `feedback-implementer` | `/005-implement-feedback`; letter suffix increments per re-run |

## Validation

Every `NN-<phase>.json` file is validated against `schemas/run-phase.schema.json` on write. Schema violations fail the producing subagent — fix the data, don't relax the schema.

## Gitignore

Both `.claude/runs/` and `.claude/runs-archive/` are **gitignored**. They are project-owned but transient — local forensics only. The `templates/project/gitignore.snippet` snippet is appended to the project `.gitignore` during `/000-prd-refine` State A bootstrap.

## Lifecycle

1. `/001-plan` creates `runs/{epic-id}/` and the first `01-plan.json` per task.
2. Subsequent phases append `02-…`, `03-…`, `04-…`, `05a-…` as the chain progresses.
3. On **epic close-out** (all tasks `done`), `scripts/archive-epic-runs.sh` tars and gzips the entire `runs/{epic-id}/` directory into `runs-archive/{epic-id}-{timestamp}.tar.gz` and removes the source.
4. The archive stays gitignored. Restore manually with `tar -xzf` if forensics are needed later.

## Conventions

- **Append-only**: never edit a phase file after the next phase has read it. If a value is wrong, write a corrective entry in the next phase.
- **One task per directory**: keep epic-level artifacts (questions, summaries) at `runs/{epic-id}/` root; task artifacts under `runs/{epic-id}/{task-id}/`.
- **Ruleset content is verbatim-injected** into subagent prompts before they write here — phase files capture the run *output*, not the rules themselves.
