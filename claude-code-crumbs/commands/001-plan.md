---
description: Decompose an epic into tasks and author Business scenarios. Reads PRD per-epic section as the brief.
argument-hint: <epic-id> [--resplit <task-id>]
---

# /001-plan

You are the orchestrator for Wave 1 of the crumbs pipeline: planning. You translate one epic from `PRD.md` into a set of tasks, each anchored to one or more domain-oriented **Business scenarios** (Gherkin, UI-ignorant). The heavy lifting is delegated to the `planner` subagent shipped by this plugin (`<plugin-root>/agents/planner.md`). Your job in the main thread is to gather inputs, decide whether the brief is sufficient, dispatch the subagent with a verbatim payload, and regenerate the flat scenario index.

Argument: `$ARGUMENTS`.

## Modes

1. **Fresh** — `/001-plan E-NNN` — author Business scenarios for the epic (Gherkin block-scalar in `epics.yaml`), decompose into tasks (`epic-{id}-tasks.yaml`, where `{id}` is the 3-digit zero-padded epic id, e.g. `epic-001-tasks.yaml`).
2. **Re-split** — `/001-plan --resplit T-NNN` — the implementer flagged this task as too big; decompose it into smaller tasks linked to the same Business scenarios.

Detect mode by the presence of `--resplit` in `$ARGUMENTS`. If absent, treat the first token as an epic id and run **Fresh** mode. If present, treat the following token as a task id and run **Re-split** mode.

## Workflow (Fresh mode)

### Phase 0 — Read inputs

Use the Read tool for every file below. Do not rely on `@`-includes — `@`-references are resolved by the main thread only and never propagate into a subagent prompt.

- `PRD.md` — locate and extract the `## Epic E-NNN: <title>` per-epic section. This is the planner's brief. If the section is missing, halt with: "PRD has no section for E-NNN. Run /000-prd-refine first."
- `docs/planning/epics.yaml` — locate the existing epic entry (status, goal). If absent, halt with: "Run /000-prd-refine first to create the epic header."
- `.claude/ruleset/*.md` — all 18 files. **Verbatim-inject** the contents into the planner subagent's prompt. Use the Read tool to load each file, then concatenate the bodies into the Task tool prompt, each preceded by a `--- <filename>.md ---` separator.
- `.claude/stack.yaml` — read `paths.*` overrides (used by the planner to compute ATDD spec paths) and the `extras` block, which is propagated verbatim into the planner brief.

**CM ticket awareness.** When the project's `.claude/ruleset/git-workflow.md` declares `require_ticket_reference: true` (the default for `team_preset: enterprise`), `/001-plan` will prompt for a change-management ticket id during epic creation and store it as `cm_ticket:` on the epic entry in `epics.yaml`. The id must match one of the `ticket_prefixes:` declared in the same `git-workflow.md` (e.g. `CHG`, `CM`, `JIRA`, `INC`). Downstream `/002-implement` and `/006-merge` substitute `{ticket_id}` from this field; if a task carries its own `cm_ticket:` override, that takes precedence over the epic-level value.

Example invocations:

```
/001-plan E-007              # solo / oss preset: no ticket prompt
/001-plan E-007              # enterprise preset: planner halts with `Ticket id for epic E-007?` and waits for a CHG-/CM-/JIRA-/INC- prefixed id
/001-plan --resplit T-014    # re-split mode (no ticket prompt; cm_ticket is inherited from the epic)
```

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

### Phase 1.5 — Resplit depth check

Before dispatching the planner, count prior resplit archives whose lineage overlaps this task's Business Scenarios. Maximum resplit depth is 3 per Business Scenario lineage. Beyond that, the planner is failing to decompose meaningfully and manual intervention is required.

```sh
# Extract source task's domain_scenarios names from epic-{id}-tasks.yaml.
# Prefer yq when available; fall back to a POSIX awk parser for the flat task list.
EPIC_NUM="${EPIC_ID#E-}"
TASKS_FILE="docs/planning/epic-${EPIC_NUM}-tasks.yaml"

if command -v yq >/dev/null 2>&1; then
    SCENARIO_NAMES="$(yq -r ".tasks[] | select(.id == \"$TASK_ID\") | .domain_scenarios[]" "$TASKS_FILE" 2>/dev/null)"
else
    SCENARIO_NAMES="$(awk -v t="$TASK_ID" '
        /^  - id:/ { in_task = ($3 == t) ? 1 : 0; in_ds = 0 }
        in_task && /^    domain_scenarios:/ { in_ds = 1; next }
        in_task && in_ds && /^      - / { sub(/^      - /, ""); print; next }
        in_ds && /^    [a-zA-Z]/ { in_ds = 0 }
    ' "$TASKS_FILE")"
fi

# Count prior resplit archives whose archived 01-plan.json references any of these scenarios.
DEPTH=0
ARCHIVE_ROOT=".claude/runs-archive/${EPIC_ID}"
if [ -d "$ARCHIVE_ROOT" ]; then
    for archive in "$ARCHIVE_ROOT"/*-resplit-*/; do
        [ -d "$archive" ] || continue
        plan="${archive}01-plan.json"
        [ -f "$plan" ] || continue
        # Match if any scenario name appears in the archived plan artifact.
        printf '%s\n' "$SCENARIO_NAMES" | while IFS= read -r name; do
            [ -n "$name" ] || continue
            if grep -qF -- "$name" "$plan"; then
                exit 9
            fi
        done
        # `exit 9` from the subshell signals overlap.
        if [ $? -eq 9 ]; then
            DEPTH=$((DEPTH + 1))
        fi
    done
fi

if [ "$DEPTH" -ge 3 ]; then
    echo "Resplit lineage for scenarios sharing this task has depth $DEPTH (>= 3)." >&2
    echo "The planner is failing to decompose. Halting." >&2
    echo "Manual remediation options:" >&2
    echo "  1. Inspect the prior resplit archives in .claude/runs-archive/${EPIC_ID}/" >&2
    echo "  2. Re-author the Business Scenario in epics.yaml to be smaller in scope" >&2
    echo "  3. Edit ${TASKS_FILE} directly and accept the task as written" >&2
    exit 6
fi
```

Exit code `6` is reserved for this halt (distinct from existing planner exit codes). If the check passes, proceed to Phase 2.

### Phase 2 — Dispatch planner subagent (re-split mode)

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

### Phase 3 — Archive old task

Move the old task's `runs/{epic_id}/{task_id}/` directory to `runs-archive/{epic_id}/{task_id}-resplit-{timestamp}-{short_uuid}/` where `{timestamp}` is `YYYYMMDD-HHMMSS` UTC and `{short_uuid}` is the first 8 chars of `uuidgen | tr -d '-'` (POSIX equivalent: `date +%s%N | sha1sum | cut -c1-8`). The suffix avoids collisions on sub-second re-splits. Example: `runs-archive/E-003/T-014-resplit-20260518-143022-a3f9b2c1/`. The main thread invokes `mv` directly (or a small shell snippet); the planner does not touch the filesystem outside the planning artifacts.

Do NOT preserve a `parent` pointer on the new task entries. The history of the too_big_proposal lives in the archive directory only — new tasks start with a clean slate.

### Phase 4 — Summary

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
