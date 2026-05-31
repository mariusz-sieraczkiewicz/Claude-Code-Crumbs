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

<!-- FREEZE:IF require_ticket_reference -->
**CM ticket awareness.** When the project's `.claude/ruleset/git-workflow.md` declares `require_ticket_reference: true` (the default for `team_preset: enterprise`), `/001-plan` will prompt for a change-management ticket id during epic creation and store it as `cm_ticket:` on the epic entry in `epics.yaml`. The id must match one of the `ticket_prefixes:` declared in the same `git-workflow.md` (e.g. `CHG`, `CM`, `JIRA`, `INC`). Downstream `/002-implement` and `/006-merge` substitute `{ticket_id}` from this field; if a task carries its own `cm_ticket:` override, that takes precedence over the epic-level value.
<!-- FREEZE:ENDIF -->

Example invocations:

```
/001-plan E-007              # solo / oss preset: no ticket prompt
```
<!-- FREEZE:IF require_ticket_reference -->
```
/001-plan E-007              # enterprise preset: planner halts with `Ticket id for epic E-007?` and waits for a CHG-/CM-/JIRA-/INC- prefixed id
```
<!-- FREEZE:ENDIF -->
```
/001-plan --resplit T-014    # re-split mode (no ticket prompt; cm_ticket is inherited from the epic)
```

If any of the 18 ruleset files is missing, halt with: "Ruleset incomplete: <name>.md missing. Run plugin setup."

### Phase 1 — Epic branch creation

**Branch model.** One branch per **epic** (not per task). The epic branch is created HERE, in `/001-plan`, so every downstream stage (`/002-implement`, `/003`, `/004`, `/005`, `/006-merge`) operates on the same branch. The planning artifacts produced in Phase 3 and 4 land as the first commit on the branch (Phase 5 below).

**Preflight checks** (run before branch creation; abort on failure with the verbatim message):

- **Detached HEAD check.** Run `git rev-parse --abbrev-ref HEAD`. If the output is the literal string `HEAD` → ABORT: `HEAD is detached. Check out a branch first: \`git checkout <branch-name>\` (e.g. main).`
- **Dirty working tree check.** Run `git status --porcelain`. If non-empty:
<!-- FREEZE:IF allow_commit_to_main -->
  - `allow_commit_to_main: true` (solo preset) → proceed; print warning: `Working tree dirty; proceeding under allow_commit_to_main=true. Planning-artifact commit will include all current staged/unstaged changes.`
<!-- FREEZE:ELSE -->
  - `allow_commit_to_main: false` (default) → ABORT: `Working tree has uncommitted changes. Commit or stash them before /001-plan.`
<!-- FREEZE:ENDIF -->
- **Git identity preflight.** `git config --get user.email` and `git config --get user.name` must both return non-empty. If either is empty → ABORT: `Git identity not configured. Run \`git config --global user.email "<you@example>"\` and \`git config --global user.name "<Your Name>"\` then re-run.`

**Branch handling dispatch.** Read `allow_commit_to_main` from the YAML toggle block in `.claude/ruleset/git-workflow.md`:

- If `allow_commit_to_main: true` (solo preset) → SKIP branch creation entirely. Do NOT read `branch_name_pattern`. Planning artifacts will be committed on the current branch (typically `main`). Proceed to Phase 2.
- If `allow_commit_to_main: false` (default) → read `branch_name_pattern` and create the epic branch as described below.

**Branch name resolution** (only when `allow_commit_to_main: false`):

- Read `branch_name_pattern` from the YAML toggle block. Default: <!-- FREEZE:VAL branch_name_pattern -->`epic/{epic_id}-{slug}`<!-- FREEZE:ENDVAL -->. Recognised substitution keys: `{epic_id}`, `{slug}`, `{ticket_id}`.
  1. Substitute `{epic_id}` with the argument (e.g. `E-003`).
  2. **Resolve `{slug}`** — read the epic entry from `docs/planning/epics.yaml`. Prefer the explicit `slug:` field if present; otherwise derive from `title:` via kebab-case (lowercase, strip non-alphanumerics, collapse runs of `-`). Example: title `"Subscription cancellation"` → slug `subscription-cancellation`. If the derived slug is empty (non-Latin title / pure punctuation), ABORT: `Cannot derive {slug} for epic <epic-id> from title "<...>". Add an explicit slug: field to the epic entry in epics.yaml.`
<!-- FREEZE:IF require_ticket_reference -->
  3. **Resolve `{ticket_id}`** (only when the pattern contains the placeholder; enterprise default `epic/{ticket_id}/{epic_id}-{slug}`):
     a. Read `epic.cm_ticket` from the epic entry in `epics.yaml`.
     b. If absent AND the pattern contains `{ticket_id}`:
        - If `git-workflow.md.require_ticket_reference: true` → ABORT: `Epic E-NNN has no cm_ticket. Add one via /001-plan or edit epics.yaml. (Enterprise preset requires CM ticket per epic.)`
        - Else → substitute with empty string and emit a visible warning.
     c. **Validate against `ticket_prefixes`** from `git-workflow.md` (if present): the resolved id must start with one of the configured prefixes (e.g. `CHG-`, `CM-`, `JIRA-`, `INC-`). Reject ids starting with `E-` or `T-`. On mismatch → ABORT with the resolved id, allowed prefixes, and source.
<!-- FREEZE:ENDIF -->
- Determine the default base branch (`main` unless `stack.yaml.paths.default_branch` overrides).
- **Epic branch check.** Run `git show-ref --verify --quiet refs/heads/<computed-branch-name>`. Two cases:
  - **Branch exists** → this is a **resume** (a prior `/001-plan <epic-id>` run created it; e.g. user halted during grilling). Run `git checkout <computed-branch-name>`. Do NOT pull from base. Proceed to Phase 2.
  - **Branch does NOT exist** → this is a **fresh epic start**. Run `git checkout <base>` then `git pull --ff-only` to sync. Then create and check out: `git checkout -b <computed-branch-name>`.

The branch persists across `/001-plan` (resume), every `/002-implement` task iteration, `/003`, `/004`, `/005`, and is closed by `/006-merge`. Downstream commands assume the branch exists and abort with a hint to run `/001-plan` if it does not.

### Phase 2 — Adaptive grilling

Read the PRD per-epic section. Decide:

- **Sufficient** — the section covers the happy path, at least one edge case, and a scope boundary (an explicit "out of scope" or "not included" note). Proceed to Phase 3.
- **Underspecified** — any of the three pillars is missing. Emit clarifying questions inline to the user. Do NOT proceed without user answers. Wait. Typical questions:
  - "What is the primary success path for this epic, in one sentence?"
  - "What is the most plausible failure mode you want covered?"
  - "What is explicitly out of scope for this epic?"

Once answers arrive, append them to the brief under a `### Clarifications` heading and proceed.

### Phase 3 — Dispatch planner subagent

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
- New `docs/planning/epic-{id}-tasks.yaml` — flat list of task entries. Each entry has: `id`, `title`, `status: pending`, `acceptance_criteria: [<verbose prose string>, ...]` (machine-verifiable facts, audited per-criterion by `/003-verify-dod`), `atdd_spec: <path>`, optional `notes`. See `agents/planner.md` § "Task YAML shape" for full field semantics.

If the planner returns `status: "needs_clarification"` in `01-plan.json`, surface the questions to the user, collect answers, and re-dispatch with the expanded brief.

### Phase 4 — Regenerate SCENARIOS.md

Run `scripts/regen-scenarios.sh` (plugin-shipped, built in Wave 8). It reads `epics.yaml`, extracts every `## Scenario:` title, and overwrites `docs/planning/SCENARIOS.md` with a flat index, one scenario title per line, grouped by epic. If the script is not yet on disk (pre-Wave 8 install), warn the user but do not fail the command.

The regen script ALSO follows the write-to-tmp + rename pattern documented in `agents/planner.md` under "Atomic writes": it writes `docs/planning/SCENARIOS.md.tmp` first, then atomically renames into place on success. On error, the `.tmp` file is left behind for inspection and the script exits non-zero. This guards against half-written `SCENARIOS.md` if the script is interrupted mid-write.

### Phase 5 — Commit planning artifacts

Commit the planning artifacts on the epic branch so the branch is self-contained from the start (downstream stages can clone, branch, or rebase against a meaningful starting point). Skip this phase when `allow_commit_to_main: true` AND working tree was dirty at Phase 1 (solo preset path) — in that case the artifacts are left as working-tree changes and rolled into the next implementer commit.

Files staged:

- `docs/planning/epics.yaml` (updated `business_scenarios:` block on the epic entry)
- `docs/planning/epic-{NN}-tasks.yaml` (new flat task list)
- `.claude/runs/{epic_id}/01-plan.json` (planner output)
- `docs/planning/SCENARIOS.md` (regenerated flat index)

Commit message follows `.claude/ruleset/git-workflow.md` conventions (Conventional Commits by default):

```
plan({epic_id_lower}): decompose <epic-title> into N tasks

- M Business scenarios on epic
- N tasks with acceptance criteria + ATDD spec paths
```

<!-- FREEZE:IF require_ticket_reference -->
When `require_ticket_reference: true`, append the resolved `cm_ticket` to the subject per the `commit_subject_pattern`, e.g. `plan(e-003): decompose Subscription cancellation into 5 tasks [CHG-12345]`.
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_signed_commits -->
When `require_signed_commits: true`, commit with `-S` (GPG/SSH signing). The Phase 1 git-identity preflight does NOT validate signing config; `/002-implement` Phase 0 will repeat with stricter checks. If signing fails here, ABORT with the git error verbatim — never commit unsigned when the toggle is true.
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_dco_signoff -->
When `require_dco_signoff: true`, commit with `-s` (appends a `Signed-off-by:` trailer).
<!-- FREEZE:ENDIF -->

Re-split mode commits to the same epic branch with a different prefix:

```
plan({epic_id_lower}): resplit <task-id> into N tasks

Reason: <one-line reason from 02-impl.json>
```

Never amend. Never force-push. If `git commit` exits non-zero (e.g. pre-commit hook failure), surface the hook output verbatim and halt — do not auto-fix or bypass hooks.

### Phase 6 — Summary to user

Print a tight summary:

- Epic id and title
- Business scenario count
- Task count
- Epic branch name (or `main` when `allow_commit_to_main: true`) and the plan commit SHA from Phase 5
- File paths written (`docs/planning/epics.yaml`, `docs/planning/epic-{id}-tasks.yaml`, `runs/{epic_id}/01-plan.json`, `docs/planning/SCENARIOS.md`)
- Next-step suggestion: `/002-implement <epic-id>` (default — runs every pending task in the epic). The legacy single-task form `/002-implement T-001` remains available for ad-hoc re-runs but is not the default.

## Workflow (Re-split mode)

### Phase 0 — Validate input

Read `runs/{epic_id}/{task_id}/02-impl.json`. Required:

- `status: "too_big_proposal"`
- `payload.suggested_split` — non-empty array of proposed sub-task descriptors

If either is missing, abort with: "Task T-NNN was not flagged as too_big. Re-split requires an implementer's too_big_proposal."

Also read the original task entry from `epic-{id}-tasks.yaml` (for its `acceptance_criteria` list — these are the anchor the new tasks inherit; the resplit redistributes criteria across smaller tasks rather than introducing new ones).

### Phase 1 — Ensure on epic branch

The epic branch was created during the original Fresh-mode `/001-plan <epic-id>` invocation. Re-split runs against the same branch.

- Read `allow_commit_to_main`. If `true` → SKIP (no branch to check; planning artifacts and resplit commits land on the current branch).
- Otherwise resolve the expected branch name via the same logic as Fresh-mode Phase 1 (substitute `{epic_id}`, `{slug}`, `{ticket_id}`).
- Run `git show-ref --verify --quiet refs/heads/<computed-branch-name>`:
  - **Branch exists** → if HEAD is already on it, no-op; else `git checkout <computed-branch-name>`.
  - **Branch does NOT exist** → ABORT: `Epic branch <name> not found. The original /001-plan <epic-id> run should have created it. Re-run /001-plan <epic-id> (Fresh mode) to recreate the branch, or check out it manually if it was renamed.`
- Detached-HEAD and dirty-tree checks: same as Fresh-mode Phase 1.

### Phase 2 — Resplit depth check

Before dispatching the planner, count prior resplit archives for this epic whose archived `01-plan.json` references **any acceptance criterion** present on the current task. Maximum resplit depth is 3 per criterion lineage. Beyond that, the planner is failing to decompose meaningfully and manual intervention is required.

Criterion overlap is detected by substring match: each archived plan artifact is searched for a unique 40-char fragment of every current criterion. If any fragment hits, the archive is part of this task's lineage.

```sh
# Extract source task's acceptance_criteria entries from epic-{id}-tasks.yaml.
# Prefer yq when available; fall back to a POSIX awk parser for the flat task list.
EPIC_NUM="${EPIC_ID#E-}"
TASKS_FILE="docs/planning/epic-${EPIC_NUM}-tasks.yaml"

if command -v yq >/dev/null 2>&1; then
    CRITERIA="$(yq -r ".tasks[] | select(.id == \"$TASK_ID\") | .acceptance_criteria[]" "$TASKS_FILE" 2>/dev/null)"
else
    CRITERIA="$(awk -v t="$TASK_ID" '
        /^  - id:/ { in_task = ($3 == t) ? 1 : 0; in_ac = 0 }
        in_task && /^    acceptance_criteria:/ { in_ac = 1; next }
        in_task && in_ac && /^      - / { sub(/^      - /, ""); gsub(/^"|"$/, ""); print; next }
        in_ac && /^    [a-zA-Z]/ { in_ac = 0 }
    ' "$TASKS_FILE")"
fi

# For each criterion, take the first 40 chars (after stripping leading whitespace) as a lineage probe.
# Criteria are verbose prose — a 40-char fragment is enough to avoid accidental matches.
DEPTH=0
ARCHIVE_ROOT=".claude/runs-archive/${EPIC_ID}"
if [ -d "$ARCHIVE_ROOT" ]; then
    for archive in "$ARCHIVE_ROOT"/*-resplit-*/; do
        [ -d "$archive" ] || continue
        plan="${archive}01-plan.json"
        [ -f "$plan" ] || continue
        printf '%s\n' "$CRITERIA" | while IFS= read -r criterion; do
            [ -n "$criterion" ] || continue
            probe="$(printf '%s' "$criterion" | sed 's/^[[:space:]]*//' | cut -c1-40)"
            [ -n "$probe" ] || continue
            if grep -qF -- "$probe" "$plan"; then
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
    echo "Resplit lineage for criteria sharing this task has depth $DEPTH (>= 3)." >&2
    echo "The planner is failing to decompose. Halting." >&2
    echo "Manual remediation options:" >&2
    echo "  1. Inspect the prior resplit archives in .claude/runs-archive/${EPIC_ID}/" >&2
    echo "  2. Re-author the acceptance_criteria on this task to be narrower in scope" >&2
    echo "  3. Edit ${TASKS_FILE} directly and accept the task as written" >&2
    exit 6
fi
```

Exit code `6` is reserved for this halt (distinct from existing planner exit codes). If the check passes, proceed to Phase 3.

### Phase 3 — Dispatch planner subagent (re-split mode)

Use the Task tool with `subagent_type: "planner"`, mode set to `resplit`. Brief:

- Mode: `resplit`
- Task id and the `reason` field from `02-impl.json`
- `payload.suggested_split` from `02-impl.json` (verbatim)
- Original task entry from `epic-{id}-tasks.yaml`
- Verbatim ruleset (all 18 files, same convention as Fresh mode)
- `stack.yaml.extras` propagated verbatim

The planner produces:

- New task entries replacing the original in `epic-{id}-tasks.yaml`. New task ids continue the existing numbering (e.g., if the original was `T-007` and the epic had tasks up to `T-012`, new tasks become `T-013`, `T-014`, …). **The original task's `acceptance_criteria` are redistributed across the new tasks** — every criterion from the original must appear on exactly one new task (no orphans, no duplicates). Re-split does not author new criteria; it only redistributes existing ones to smaller chunks. Business scenarios at the epic level are unchanged.
- `runs/{epic_id}/{task_id}/01-plan.json` — re-split phase output, recording which task was split, the reason, and the new task ids.

### Phase 4 — Archive old task

Move the old task's `runs/{epic_id}/{task_id}/` directory to `runs-archive/{epic_id}/{task_id}-resplit-{timestamp}-{short_uuid}/` where `{timestamp}` is `YYYYMMDD-HHMMSS` UTC and `{short_uuid}` is the first 8 chars of `uuidgen | tr -d '-'` (POSIX equivalent: `date +%s%N | sha1sum | cut -c1-8`). The suffix avoids collisions on sub-second re-splits. Example: `runs-archive/E-003/T-014-resplit-20260518-143022-a3f9b2c1/`. The main thread invokes `mv` directly (or a small shell snippet); the planner does not touch the filesystem outside the planning artifacts.

Do NOT preserve a `parent` pointer on the new task entries. The history of the too_big_proposal lives in the archive directory only — new tasks start with a clean slate.

### Phase 5 — Commit resplit artifacts

Same semantics as Fresh-mode Phase 5 (commit on epic branch). Files staged:

- `docs/planning/epic-{NN}-tasks.yaml` (replaced task entry + new entries)
- `.claude/runs/{epic_id}/{task_id}/01-plan.json` (resplit phase output)
- `.claude/runs-archive/{epic_id}/{task_id}-resplit-{ts}-{uuid}/` (archived prior run)

Commit message:

```
plan({epic_id_lower}): resplit <task-id> into N tasks

Reason: <one-line reason from 02-impl.json>
```

Skip when `allow_commit_to_main: true` AND working tree dirty (artifacts roll into next implementer commit). Same signing/sign-off/ticket toggles apply as Fresh-mode Phase 5.

### Phase 6 — Summary

Print:

- Which task was split (id and title)
- Reason (one line from `02-impl.json`)
- Number of new tasks and their ids
- Archive path
- Next-step suggestion: `/002-implement <epic-id>` (re-enters epic loop; the newly resplit tasks are picked up automatically as the next `pending` entries in the dependency-ordered iteration). For an ad-hoc single-task run, `/002-implement T-<first-new-id>` remains valid.

## Discipline

- **PRD per-epic immutability** — the planner only reads PRD; it never writes to PRD. PRD-level changes (renaming an epic, adjusting scope) belong to `/000-prd-refine`. If the planner suggests a PRD edit, surface it as a question to the user, do not apply it.
- **Business scenarios MUST be domain-oriented (UI-ignorant)**. Reject planner output if any BS contains UI vocabulary: buttons, pages, clicks, URLs, selectors, CSS, screens, modals, forms, fields, tabs. If detected, re-dispatch the planner with a clarifying instruction quoting the offending line.
- **Coverage policy** — every BS must be realised by at least one task (a task realises a BS when its `acceptance_criteria` collectively cover the BS's Given/When/Then). Every task must have at least one entry in `acceptance_criteria` and exactly one `atdd_spec` path. Reject planner output that violates this; surface the gap and re-dispatch.
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
