---
description: Single-task TDD orchestrator. New branch, implementer subagent, auto-invokes verify+review, proposes merge on clean.
argument-hint: <task-id>
---

Orchestrate one task end-to-end for **$ARGUMENTS** following the TDD entry-point discipline: Domain-test RED → code GREEN → REFACTOR → write one ATDD spec → commit → auto-invoke `/003-verify-dod` → `/004-code-review` → propose `/006-merge` on clean.

This command is the single-task counterpart of `/002-auto-implement`. It dispatches the `implementer` subagent, reads its output artifact, and chains the verify/review/feedback loop with a hard cap.

## Inputs

- **`<task-id>`** — passed as `$ARGUMENTS` (e.g. `T-001`). Required positional argument.
- **`docs/planning/epic-{id}-tasks.yaml`** — locate the task entry by scanning every `epic-*-tasks.yaml` under `docs/planning/`. If not found anywhere, abort with: `Task <task-id> not found in any epic-*-tasks.yaml. Run /001-plan first.`
- **`docs/planning/epics.yaml`** — locate the Business scenarios referenced by the task's `domain_scenarios` field. Read the Gherkin block-scalar verbatim from the matching epic entry. If a referenced scenario is missing, abort with the path and missing scenario name.
- **`.claude/ruleset/*.md`** — all 18 canonical rule files, verbatim-loaded into memory for downstream subagent injection (no `@`-include — content is pasted into the subagent prompt body).
- **`.claude/ruleset/git-workflow.md`** — parse the YAML toggle block at the top of the file for `auto_invoke_review`, `auto_invoke_verify`, `allow_commit_to_main`, `pr_required`, `branch_name_pattern`, `require_signed_commits`. Defaults below apply when a key is absent.
- **`.claude/stack.yaml`** — read `extras` (propagated verbatim to all subagents), `paths` (SoT overrides used by downstream gates), and `gates` (referenced by `/003-verify-dod`).

## Workflow

### Phase 0 — Pre-flight

- Verify the task entry exists in some `epic-{id}-tasks.yaml`. Scan every file matching that glob; the first match wins. If absent → abort (see Inputs).
- Capture the `epic_id` from the matching file's name (e.g. `epic-01-tasks.yaml` → `epic_id = E-001`, matching the entry in `epics.yaml`). Cross-check that the same epic id appears in `epics.yaml`; if not, abort with both paths.
- **Dirty working tree check.** Run `git status --porcelain`. If the output is non-empty:
  - If `allow_commit_to_main: false` (default; non-solo presets) → abort: `Working tree has uncommitted changes. Commit or stash them before /002-implement.`
  - If `allow_commit_to_main: true` (solo preset) → proceed but print a visible warning: `Working tree dirty; proceeding under allow_commit_to_main=true (solo preset). Implementer commit will include all current staged/unstaged changes.`
- **Domain-scenario name validation.** Before dispatching the implementer, verify every entry in the task's `domain_scenarios: [name1, name2, ...]` array matches a scenario header in the epic's `business_scenarios` Gherkin block-scalar:
  1. Open `docs/planning/epics.yaml` and locate the matching epic by `epic_id`.
  2. Extract the `business_scenarios` block-scalar verbatim.
  3. Regex-extract every `## Scenario: (.+)` header from that block; collect the captured names into a set.
  4. For each name in the task's `domain_scenarios`, check membership in that set.
  5. On the first miss, abort: `Task <task-id> references domain_scenario "<name>" which is not in epic <epic-id>'s business_scenarios. Fix the task entry or re-run /001-plan.`
- Verify the task `status` is `pending` or `blocked`. If `done` or `in_progress`, abort with:
  - `done` → `Task <task-id> is already done. Use /001-plan --resplit to revisit.`
  - `in_progress` → `Task <task-id> is already in_progress. Clear status manually before re-running /002-implement.`
- Set the task `status: in_progress` in `epic-{id}-tasks.yaml` (write back; preserve YAML formatting, comments, and key order).
- Ensure `.claude/runs/{epic_id}/{task_id}/` exists (create recursively if missing).
- Ensure `.claude/runs/{epic_id}/{task_id}/artifacts/` exists for transient subagent outputs (logs, drafts).
- Confirm `.claude/ruleset/` contains all 18 canonical rule files. If any are missing, list them and abort — the implementer cannot be dispatched without the full ruleset.
- Confirm `.claude/stack.yaml` exists and parses. If absent, abort with: `stack.yaml missing. Run /000-prd-refine to bootstrap the project.`

### Phase 1 — Branch

- Read `branch_name_pattern` from the YAML toggle block in `.claude/ruleset/git-workflow.md`. Default: `task/{task_id}-{slug}`. Substitute `{task_id}` with the actual id and `{slug}` with the task's `slug` field (or a kebab-cased `title` fallback).
- If `allow_commit_to_main: true` (typical for the **solo** preset):
  - Skip branch creation entirely.
  - The implementer will commit directly to `main` (or the configured default branch).
- Otherwise:
  - Determine the default base branch (`main` unless `stack.yaml.paths.default_branch` overrides).
  - **Branch collision check.** Before syncing, run `git show-ref --verify --quiet refs/heads/<computed-branch-name>`. If the branch exists:
    - If `HEAD` already points at that branch (`git rev-parse --abbrev-ref HEAD` equals the computed name) AND the most recent commit message on it matches the pattern `feat(<task-id>):` or `WIP(<task-id>):` (i.e. it is a prior partial `/002-implement` run on the same task) → treat this as a **resume**: skip base checkout, skip branch creation, continue at Phase 2.
    - Otherwise → abort: `Branch <computed-branch-name> exists but does not appear to be a resume from a prior /002-implement run. Inspect manually before retrying.`
  - Run `git checkout <base>` then `git pull --ff-only` to sync.
  - Create and check out the new branch: `git checkout -b <computed-branch-name>`.

### Phase 2 — Dispatch implementer subagent

Use the **Task tool** with `subagent_type: "implementer"`. Inject the following into the subagent prompt body (verbatim, no `@`-includes):

1. **Task entry (YAML)** — the entire YAML entry for the task as it appears in `epic-{id}-tasks.yaml`. Include `id`, `slug`, `title`, `status`, `domain_scenarios`, `atdd_spec`, `acceptance`, `notes`, and any other fields present.
2. **Business scenarios** — for each name listed in the task's `domain_scenarios`, paste the matching `## Scenario: <name>` Gherkin block verbatim from `epics.yaml`. Preface with `--- Business Scenario: <name> ---`.
3. **Verbatim ruleset** — for each of the 18 files in `.claude/ruleset/`, paste the file content prefixed by a header line `--- <filename>.md ---`. Order alphabetically. Do not summarise, do not omit. The implementer is expected to follow every active rule.
4. **`stack.yaml.extras`** — paste the `extras` mapping verbatim under a header `--- stack.yaml.extras ---`. This is the escape hatch for stack-specific quirks (e.g. `bash_buffering_warning`, `user_ping_interval_minutes`).
5. **Output contract** — instruct the implementer to write its result to `.claude/runs/{epic_id}/{task_id}/02-impl.json`, validated against `schemas/run-phase.schema.json`. The top-level `status` field must be one of `ok`, `too_big_proposal`, `blocked`. Required `payload` keys vary by status:
   - `ok` → `commit_sha`, `files_changed`, `domain_tests_added`, `atdd_spec_path`.
   - `too_big_proposal` → `reason` (prose), `suggested_split` (array of draft task titles, 2..n entries).
   - `blocked` → `reason` (prose), optional `suggested_follow_up`.
6. **Prior history** — paste any pre-existing artifacts under `.claude/runs/{epic_id}/{task_id}/` (e.g. `01-plan.json` from `/001-plan`) verbatim under a header `--- Prior phase: 01-plan.json ---`. Subagents are append-only readers of the runs history.

The implementer is expected to:

- Run the **TDD entry-point** loop per `.claude/ruleset/testing.md`: Domain-test RED → minimal production code GREEN → REFACTOR. Repeat per acceptance until the task is fully green.
- Produce **one ATDD spec** at `tests/atdd/<slug>.spec.ts` (path may differ per `stack.yaml.paths.atdd_dir`). The spec is **authored only** during the task — it is **not executed per-task**. It will be executed at epic close-out.
- Produce **one or more Domain-tests** covering happy path + edge cases.
- Make **one commit** on the task branch (or on `main` if the solo preset is active). Commit message follows `.claude/ruleset/git-workflow.md` conventions (Conventional Commits by default). Never amend.
- Sign the commit if `require_signed_commits: true` is set in the toggle block.
- Write the final artifact `02-impl.json` with a top-level `status` field: `ok`, `too_big_proposal`, or `blocked`.

### Phase 3 — Read implementer output

Parse `.claude/runs/{epic_id}/{task_id}/02-impl.json` and validate it against `schemas/run-phase.schema.json`. If validation fails, halt with the path and the validation error.

Branch on `status`:

- **`status: "too_big_proposal"`** — implementer judged the task too large to complete cleanly. Print a clear notice to the user:
  ```
  Task <task-id> flagged as too big.

  Reason: <payload.reason>

  Suggested split:
    - <payload.suggested_split[0]>
    - <payload.suggested_split[1]>
    - ...

  Next step: /001-plan --resplit <task-id>
  ```
  Set the task `status` back to `pending` in `epic-{id}-tasks.yaml`. Halt; do **not** proceed to verify or review. Note: the planner re-split (`/001-plan --resplit`) is responsible for archiving the pending task's stub `01-plan.json` if it exists.

- **`status: "blocked"`** — implementer hit a blocker it cannot resolve (missing dependency, ambiguous scenario, external decision required). Print `payload.reason` verbatim and the suggested follow-up if present. Leave task `status: in_progress` so the user can clear it manually after resolution. Halt.

- **`status: "ok"`** — implementation green. Continue to Phase 4.

### Phase 4 — Auto-invoke /003-verify-dod

If `auto_invoke_verify` is **not** `false` (default: `true`):

1. Spawn `/003-verify-dod` against `<task-id>`. The verifier runs all `stack.yaml.gates` plus rule-based DoD checks.
2. After completion, read `.claude/runs/{epic_id}/{task_id}/03-verify.json` and validate against the schema.
3. Branch on `status`:
   - **`status: "ok"`** → continue to Phase 5.
   - **`status: "fail"`** → spawn `/005-implement-feedback` with the verifier findings. The feedback-implementer fixes implementation and the chain loops back to `/003-verify-dod`. Number the feedback artifacts `05a-feedback-impl.json`, `05b-...`, `05c-...`.

**Hard cap: 3 feedback iterations per task, SHARED across verify and review gates (matches /005-implement-feedback letter-suffix scheme 05a/05b/05c). On the 4th would-be iteration, halt the auto-loop and surface findings to the user (do not emit a synthetic phase file with a non-enum status).**
```
Verify failed 3 times in a row for task <task-id>. Escalating to user.
Last findings: .claude/runs/{epic_id}/{task_id}/03-verify.json
Last feedback attempt: .claude/runs/{epic_id}/{task_id}/05c-feedback-impl.json
```
Leave task `status: in_progress`.

If `auto_invoke_verify: false`, skip Phase 4 entirely and inform the user: `Auto-verify disabled by toggle. Run /003-verify-dod <task-id> manually.`

### Phase 5 — Auto-invoke /004-code-review

If `auto_invoke_review` is **not** `false` (default: `true`):

1. Spawn `/004-code-review` against `<task-id>`. The reviewer reads the verbatim-injected ruleset, the diff, and the runs history.
2. After completion, read `.claude/runs/{epic_id}/{task_id}/04-review.json` and validate against the schema.
3. Branch on `status`:
   - **`status: "ok"`** → continue to Phase 6.
   - **`status: "fail"`** → spawn `/005-implement-feedback` with reviewer findings. The chain loops: feedback-impl → back to `/003-verify-dod` → back to `/004-code-review`. The feedback iteration counter is **shared** with Phase 4 (a single task has at most 3 feedback rounds total, not 3 per gate).

**Hard cap: 3 feedback iterations per task, SHARED across verify and review gates (matches /005-implement-feedback letter-suffix scheme 05a/05b/05c). On the 4th would-be iteration, halt the auto-loop and surface findings to the user (do not emit a synthetic phase file with a non-enum status).** Halt with the same escalation pattern as Phase 4, pointing at `04-review.json` and the latest `05X-feedback-impl.json`.

If `auto_invoke_review: false`, skip Phase 5 and inform the user: `Auto-review disabled by toggle. Run /004-code-review <task-id> manually.`

### Phase 6 — Propose merge

Reached only when both `03-verify.json` and `04-review.json` show `status: "ok"` (or the corresponding toggle disabled them).

- Set task `status: done` in `epic-{id}-tasks.yaml`. Update any `summary.by_status` counter if the file maintains one.
- Print a one-liner to the user:
  ```
  Task <task-id> complete. Open MR? Run /006-merge <task-id>
  ```
- **Do NOT auto-invoke `/006-merge`.** Merging is always user-triggered to preserve a human checkpoint before the PR/MR lands.

If `pr_required: false` (typical for the **solo** preset where commits go straight to main), substitute:
```
Task <task-id> complete and on main. /006-merge is a no-op for the solo preset.
```

## Toggle precedence

The YAML toggle block at the top of `.claude/ruleset/git-workflow.md` is the single source of truth for orchestration behaviour. It overrides every default in this command. Recognised keys:

```yaml
auto_invoke_verify: true | false       # default true
auto_invoke_review: true | false       # default true
allow_commit_to_main: true | false     # default false
pr_required: true | false              # default true
require_signed_commits: true | false   # default false
branch_name_pattern: "task/{task_id}-{slug}"
```

Notes:
- Missing block or missing key → defaults apply (no warning).
- The toggle block is parsed once at Phase 0 and held for the entire run; mid-run edits are ignored.
- The chosen `team_preset` recorded in `.claude/stack.yaml` is informational only — this command never reads it. Behaviour is driven solely by the toggle block, which the preset wrote at bootstrap.

### Preset → toggle mapping (informational)

The four shipped presets populate the toggle block at bootstrap as follows. After bootstrap the project owns the file and may edit freely; the mapping below is a reference for the defaults, not a runtime contract.

| Toggle                    | solo  | small-team | oss   | enterprise |
|---------------------------|-------|------------|-------|------------|
| `auto_invoke_verify`      | true  | true       | true  | true       |
| `auto_invoke_review`      | false | true       | true  | true       |
| `allow_commit_to_main`    | true  | false      | false | false      |
| `pr_required`             | false | true       | true  | true       |
| `require_signed_commits`  | false | false      | false | true       |

The `branch_name_pattern` is `task/{task_id}-{slug}` across all presets unless the project overrides.

## Failure modes

- **Task not found** → abort at Phase 0 with the path and id.
- **Task already `done` or `in_progress`** → abort at Phase 0 with the specific message.
- **Schema validation fails** on any of `02-impl.json`, `03-verify.json`, `04-review.json`, `05X-feedback-impl.json` → halt with the artifact path and the validator error.
- **Implementer returns `too_big_proposal`** → halt at Phase 3; revert task to `pending`.
- **Implementer returns `blocked`** → halt at Phase 3; leave task `in_progress`.
- **Verify fails 3 consecutive times** → halt at Phase 4; leave task `in_progress`.
- **Review fails 3 consecutive times** (counter shared with verify) → halt at Phase 5; leave task `in_progress`.
- **Subagent invocation error** (missing file, tool failure, ruleset directory absent) → halt with the underlying error and the offending path. Do not retry silently.
- **Branch creation fails** (dirty working tree, base branch behind, etc.) → halt at Phase 1 with the git error verbatim. Do not force any operation.

## Discipline

- Task `status` transitions:
  - `pending`/`blocked` → `in_progress` at Phase 0 start.
  - `in_progress` → `done` only on full success at Phase 6.
  - `in_progress` → `pending` on `too_big_proposal` (Phase 3).
  - `in_progress` stays `in_progress` on any hard halt — the user clears it manually once the underlying issue is resolved.
- **Never amend commits.** The implementer makes one commit; feedback rounds produce additional commits stacked on top.
- **Never force-push.** If history needs cleanup, leave it for `/006-merge` (which may squash on PR creation per `git-workflow.md`).
- **Honour `require_signed_commits`** from the chosen preset. If true, every commit (implementer + feedback rounds) is signed.
- **Honour `branch_name_pattern`.** Do not improvise branch names; the pattern is the contract.
- **Filesystem-only subagent comms.** Never rely on in-memory state between subagent invocations — the main thread reads artifacts from `.claude/runs/{epic_id}/{task_id}/` after each subagent returns. Ruleset content is verbatim-injected into the prompt body, never via `@`-include (per CONTEXT.md "Ruleset injection").
- **Append-only runs history.** Never overwrite or delete prior phase artifacts within a task run. Feedback rounds get letter suffixes (`05a`, `05b`, `05c`).
- **Single commit by default.** The implementer produces one commit per task. Feedback rounds add commits on top — they do not amend or squash. Squashing (if desired) is a `/006-merge` concern, governed by `git-workflow.md`.
- **Zero tolerance on Findings.** Any finding from `/003` or `/004` blocks DoD. No severity tiers, no overrides. The feedback loop addresses every finding; it never argues with them.

## Vocabulary discipline

Mirror `CONTEXT.md` exactly. Use only these terms when communicating with the user or writing artifacts:

- **TDD entry-point** — both planning and implementation start from a failing test. No production code without a prior red test.
- **Domain-test** — multi-class no-infra test in the inner loop (Vertex Testing). Drives RED-GREEN-REFACTOR.
- **ATDD spec** — executable form of a Business scenario, one per task, written during the task, executed only at epic close-out.
- **Step library** — domain-oriented abstraction shared across Domain-tests and ATDD specs; one function per scenario verb.
- **World** — execution context injected into a Step library function (`DomainWorld` for Domain-tests, `BrowserWorld` / `DeviceWorld` for ATDD specs and Journeys).
- **Status** — `pending | in_progress | blocked | done`. Never use `todo`, `wip`, `complete`, `partial`.
- **Finding** — any violation surfaced by `/003` or `/004`. Zero tolerance; no severity tiers.

Do not introduce synonyms (no "unit test", no "acceptance criteria", no "blocker/non-blocker", no "wip"). If you find yourself reaching for one, re-read the relevant CONTEXT.md entry.

## Subagent chain summary

```
/002-implement <task-id>
   |
   ├─ Phase 0  pre-flight (status flip → in_progress)
   ├─ Phase 1  branch (or skip if allow_commit_to_main)
   ├─ Phase 2  implementer subagent → 02-impl.json
   ├─ Phase 3  branch on status:
   │            ok → continue
   │            too_big_proposal → status=pending, halt
   │            blocked → halt
   ├─ Phase 4  /003-verify-dod → 03-verify.json
   │            on fail → /005-implement-feedback → 05a/05b/05c → loop
   │            cap: 3 consecutive fails (shared with Phase 5)
   ├─ Phase 5  /004-code-review → 04-review.json
   │            on fail → /005-implement-feedback → loop back to /003
   │            cap: 3 consecutive fails (shared with Phase 4)
   └─ Phase 6  status=done; print /006-merge suggestion (user-triggered)
```

Each subagent type lives in `.claude-plugin/agents/` (plugin-owned, not project-owned). The chain is iterative (`planner` → `implementer` → `verifier` → `reviewer` → `feedback-implementer` → back to `verifier`), not linear. This command owns one task's traversal of that chain — `/002-auto-implement` owns the epic-level batch.

## Worked example

Given task `T-014` belonging to epic `E-003`, with a small-team preset:

1. **Phase 0** — `/002-implement T-014` locates `docs/planning/epic-03-tasks.yaml`, finds entry `id: T-014, status: pending, slug: cancel-subscription, domain_scenarios: ["User cancels subscription"]`. Flips status to `in_progress`. Creates `.claude/runs/E-003/T-014/`.
2. **Phase 1** — Branch pattern `task/{task_id}-{slug}` resolves to `task/T-014-cancel-subscription`. Checked out from `main`.
3. **Phase 2** — `implementer` subagent receives task YAML, the Gherkin block for `User cancels subscription`, all 18 ruleset files verbatim, and `stack.yaml.extras`. It writes Domain-tests in `tests/domain/cancel-subscription.test.ts`, production code in `src/billing/cancel.ts`, an ATDD spec in `tests/atdd/cancel-subscription.spec.ts`, commits with message `feat(billing): cancel subscription (T-014)`, and writes `02-impl.json` with `status: ok`.
4. **Phase 4** — `/003-verify-dod` runs `stack.yaml.gates` (lint, typecheck, domain_tests, build, security). All pass → `03-verify.json` status `pass`.
5. **Phase 5** — `/004-code-review` reads ruleset + diff. One finding: missing `aria-label` per `accessibility.md`. `04-review.json` status `fail`. `/005-implement-feedback` fires (`05a-feedback-impl.json`), fix commits, loops back to `/003-verify-dod` (pass), then `/004-code-review` (pass).
6. **Phase 6** — Task `status: done`. Print: `Task T-014 complete. Open MR? Run /006-merge T-014`.

Total feedback iterations: 1 of 3 allowed.
