---
description: Decompose an epic into tasks and author Business scenarios. Reads PRD per-epic section as the brief.
argument-hint: <epic-id> [--resplit <task-id>]
---

# /001-plan

You are the orchestrator for Wave 1 of the crumbs pipeline: planning. You translate one epic from `PRD.md` into a set of tasks, each anchored to one or more domain-oriented **Business scenarios** (Gherkin, UI-ignorant). The heavy lifting is delegated to the `planner` subagent shipped by this plugin (`<plugin-root>/agents/planner.md`). Your job in the main thread is to gather inputs, decide whether the brief is sufficient, dispatch the subagent with a verbatim payload, and regenerate the flat scenario index.

Argument: `$ARGUMENTS`.

## Modes

1. **Fresh** — `/001-plan E-NNN` — author Business scenarios for the epic (Gherkin block-scalar in `epics.yaml`), decompose into tasks (`epic-{id}-tasks.yaml`).
2. **Re-split** — `/001-plan --resplit T-NNN` — the implementer flagged this task as too big; decompose it into smaller tasks linked to the same Business scenarios.

Detect mode by the presence of `--resplit` in `$ARGUMENTS`. If absent, treat the first token as an epic id and run **Fresh** mode. If present, treat the following token as a task id and run **Re-split** mode.

## Workflow (Fresh mode)

### Phase 0 — Read inputs

Use the Read tool for every file below. Do not rely on `@`-includes — `@`-references are resolved by the main thread only and never propagate into a subagent prompt.

- `PRD.md` — locate and extract the `## Epic E-NNN: <title>` per-epic section. This is the planner's brief. If the section is missing, halt with: "PRD has no section for E-NNN. Run /000-prd-refine first."
- `docs/planning/epics.yaml` — locate the existing epic entry (status, goal). If absent, halt with: "Run /000-prd-refine first to create the epic header."
- `.claude/ruleset/*.md` — all 18 files. **Verbatim-inject** the contents into the planner subagent's prompt. Use the Read tool to load each file, then concatenate the bodies into the Task tool prompt, each preceded by a `--- <filename>.md ---` separator.
- `.claude/stack.yaml` — read `paths.*` overrides (used by the planner to compute ATDD spec paths) and the `extras` block, which is propagated verbatim into the planner brief.

If any of the 18 ruleset files is missing, halt with: "Ruleset incomplete: <name>.md missing. Run plugin setup."

### Phase 1 — Adaptive grilling

Read the PRD per-epic section. Decide:

- **Sufficient** — the section covers the happy path, at least one edge case, and a scope boundary (an explicit "out of scope" or "not included" note). Proceed to Phase 2.
- **Underspecified** — any of the three pillars is missing. Emit clarifying questions inline to the user. Do NOT proceed without user answers. Wait. Typical questions:
  - "What is the primary success path for this epic, in one sentence?"
  - "What is the most plausible failure mode you want covered?"
  - "What is explicitly out of scope for this epic?"

Once answers arrive, append them to the brief under a `### Clarifications` heading and proceed.

### Phase 2 — Dispatch planner subagent

Use the Task tool with `subagent_type: "planner"` (the agent we ship in this plugin). The brief includes:

- Mode: `fresh`
- Epic id
- Verbatim PRD per-epic section
- Verbatim ruleset (all 18 files concatenated, each preceded by `--- <name>.md ---`)
- `stack.yaml.extras` propagated verbatim as YAML
- `paths.*` overrides from `stack.yaml`

The planner produces:

- `runs/{epic_id}/01-plan.json` — validated against `schemas/run-phase.schema.json`. Contains the planner's decisions, BS list, task list, and any open questions.
- Updated `docs/planning/epics.yaml` — adds a `business_scenarios:` key on the epic entry, whose value is a Gherkin block-scalar (`|`) containing all scenarios for this epic. Existing keys (`status`, `goal`, `out_of_scope`) are preserved.
- New `docs/planning/epic-{id}-tasks.yaml` — flat list of task entries. Each entry has: `id`, `title`, `status: pending`, `domain_scenarios: [<BS title>, ...]`, `atdd_spec: <path>`, optional `notes`.

If the planner returns `status: "needs_clarification"` in `01-plan.json`, surface the questions to the user, collect answers, and re-dispatch with the expanded brief.

### Phase 3 — Regenerate SCENARIOS.md

Run `scripts/regen-scenarios.sh` (plugin-shipped, built in Wave 8). It reads `epics.yaml`, extracts every `## Scenario:` title, and overwrites `docs/planning/SCENARIOS.md` with a flat index, one scenario title per line, grouped by epic. If the script is not yet on disk (pre-Wave 8 install), warn the user but do not fail the command.

The regen script ALSO follows the write-to-tmp + rename pattern documented in `agents/planner.md` under "Atomic writes": it writes `docs/planning/SCENARIOS.md.tmp` first, then atomically renames into place on success. On error, the `.tmp` file is left behind for inspection and the script exits non-zero. This guards against half-written `SCENARIOS.md` if the script is interrupted mid-write.

### Phase 4 — Summary to user

Print a tight summary:

- Epic id and title
- Business scenario count
- Task count
- File paths written (`docs/planning/epics.yaml`, `docs/planning/epic-{id}-tasks.yaml`, `runs/{epic_id}/01-plan.json`, `docs/planning/SCENARIOS.md`)
- Next-step suggestion: `/002-implement T-001` for single-task execution, or `/002-auto-implement E-NNN` for batch implementation across the whole epic.

## Workflow (Re-split mode)

### Phase 0 — Validate input

Read `runs/{epic_id}/{task_id}/02-impl.json`. Required:

- `status: "too_big_proposal"`
- `payload.suggested_split` — non-empty array of proposed sub-task descriptors

If either is missing, abort with: "Task T-NNN was not flagged as too_big. Re-split requires an implementer's too_big_proposal."

Also read the original task entry from `epic-{id}-tasks.yaml` (for its `domain_scenarios` list — these are the anchor the new tasks inherit).

### Phase 1 — Dispatch planner subagent (re-split mode)

Use the Task tool with `subagent_type: "planner"`, mode set to `resplit`. Brief:

- Mode: `resplit`
- Task id and the `reason` field from `02-impl.json`
- `payload.suggested_split` from `02-impl.json` (verbatim)
- Original task entry from `epic-{id}-tasks.yaml`
- Verbatim ruleset (all 18 files, same convention as Fresh mode)
- `stack.yaml.extras` propagated verbatim

The planner produces:

- New task entries replacing the original in `epic-{id}-tasks.yaml`. New task ids continue the existing numbering (e.g., if the original was `T-007` and the epic had tasks up to `T-012`, new tasks become `T-013`, `T-014`, …). **All new tasks inherit the original task's `domain_scenarios` list verbatim** — re-split does not change BS coverage, only granularity.
- `runs/{epic_id}/{task_id}/01-plan.json` — re-split phase output, recording which task was split, the reason, and the new task ids.

### Phase 2 — Archive old task

Move the old task's `runs/{epic_id}/{task_id}/` directory to `runs-archive/{epic_id}/{task_id}-resplit-{timestamp}-{short_uuid}/` where `{timestamp}` is `YYYYMMDD-HHMMSS` UTC and `{short_uuid}` is the first 8 chars of `uuidgen | tr -d '-'` (POSIX equivalent: `date +%s%N | sha1sum | cut -c1-8`). The suffix avoids collisions on sub-second re-splits. Example: `runs-archive/E-003/T-014-resplit-20260518-143022-a3f9b2c1/`. The main thread invokes `mv` directly (or a small shell snippet); the planner does not touch the filesystem outside the planning artifacts.

Do NOT preserve a `parent` pointer on the new task entries. The history of the too_big_proposal lives in the archive directory only — new tasks start with a clean slate.

### Phase 3 — Summary

Print:

- Which task was split (id and title)
- Reason (one line from `02-impl.json`)
- Number of new tasks and their ids
- Archive path
- Next-step suggestion: `/002-implement T-<first-new-id>`.

## Discipline

- **PRD per-epic immutability** — the planner only reads PRD; it never writes to PRD. PRD-level changes (renaming an epic, adjusting scope) belong to `/000-prd-refine`. If the planner suggests a PRD edit, surface it as a question to the user, do not apply it.
- **Business scenarios MUST be domain-oriented (UI-ignorant)**. Reject planner output if any BS contains UI vocabulary: buttons, pages, clicks, URLs, selectors, CSS, screens, modals, forms, fields, tabs. If detected, re-dispatch the planner with a clarifying instruction quoting the offending line.
- **Coverage policy** — every BS must map to at least one task (via `domain_scenarios` on that task). Every task must have at least one entry in `domain_scenarios` and exactly one `atdd_spec` path. Reject planner output that violates this; surface the gap and re-dispatch.
- **Status enum on new tasks** — always `pending`. The planner never sets any other status; status transitions are owned by `/002-implement` and `/003-finalize`.
- **No silent rewrites** — if the planner's output would overwrite existing scenarios in `epics.yaml` for the same epic, halt and ask the user whether to merge or replace. Default: refuse and surface the conflict.

## Subagent invocation

```
Task tool, subagent_type: "planner"
prompt: |
  Mode: fresh | resplit
  Epic: E-NNN
  Task (resplit only): T-NNN
  Reason (resplit only): "<from 02-impl.json>"

  PRD epic section:
  <verbatim copy of ## Epic E-NNN: ... section from PRD.md>

  Ruleset (verbatim, 18 files):
  --- architecture.md ---
  <body>
  --- api-design.md ---
  <body>
  ... (all 18) ...

  Stack paths (overrides):
  <stack.yaml.paths as YAML>

  Stack extras (verbatim):
  <stack.yaml.extras as YAML>
```

The subagent reads the brief, performs its decomposition, writes the artifacts, and returns a short status summary to the main thread. The main thread is responsible for: regenerating `SCENARIOS.md`, archiving on re-split, and printing the user-facing summary.

## Vocabulary discipline

Mirror `CONTEXT.md` exactly. Use these terms verbatim in all user-facing output, in YAML keys, and in the planner brief:

- **Business scenario** — UI-ignorant Gherkin describing a domain rule. Lives in `epics.yaml` as a block-scalar under the epic.
- **Domain-test** — the executable form of a Business scenario, produced by the next wave.
- **ATDD spec** — the path on a task that points to the test file backing its Business scenarios.
- **Step library** — the shared set of Gherkin step definitions reused across domain-tests.
- **Status enum** — the closed vocabulary of task states; new tasks start at `pending`.

Do not introduce synonyms ("user story", "use case", "feature spec", "acceptance test") in any output. If the user uses a synonym, restate the canonical term in your reply.
