---
description: 'Epic-level user feedback flow: gather → plan new tasks → ATDD → verify → review → gatekeeper'
argument-hint: '<epic-id> [feedback-text]'
---

# /005-implement-feedback

Implement user feedback for epic **$1**.

This command runs **after** an epic has been implemented (typically via `/002-implement <epic-id>`). The user has now observed the assembled epic — running app, deployed feature, integration result — and has feedback on it: bugs, missing behaviour, UI issues, scope adjustments. `/005-implement-feedback` is the disciplined intake for that feedback: it gathers it, decomposes it into new tasks, drives those new tasks through the full ATDD → verify → review chain, and gates the whole round behind a strict gatekeeper subagent.

**Scope is the epic, not a single task.** Feedback is observed at the epic level — the user does not file findings against `T-014` in isolation; they say "the checkout flow feels wrong" or "import is missing the CSV path". The command translates that into new task entries appended to `epic-{id}-tasks.yaml`.

**This command does NOT participate in the intra-/003 or intra-/004 self-heal loop.** `/003-verify-dod` and `/004-code-review` heal their own findings internally (Phase 2/3 loops, bounded at 3 iterations). When those gates pass, control flows back to whoever invoked them. `/005` is invoked explicitly by the user after an epic settles, not auto-dispatched by a failing gate.

**MANDATORY: every step below runs, regardless of fix size.** A one-line CSS change still goes through: gather → clarify → plan → ATDD impl → verify → review → gatekeeper. No shortcuts. Use the harness's `TaskCreate` tool (not to be confused with planning tasks `T-NNN` in `epic-{id}-tasks.yaml`) to track per-step progress in the conversation.

Argument: `$ARGUMENTS` — `<epic-id>` (required) and optional `[feedback-text]` as `$2`. Examples:

```
/005-implement-feedback E-003
/005-implement-feedback E-003 "the import button is enabled even when no file is selected"
```

## Code rules — single source of truth

**Rules live in `.claude/ruleset/`.** This command does NOT redefine them. Implementation in Step 3 follows `/002-implement` semantics; verification in Step 4 follows `/003-verify-dod`; review in Step 5 follows `/004-code-review`. Each of those commands owns its own gate stack, ATDD discipline, and ruleset injection — `/005` only orchestrates the steps in order and scopes them to the new tasks. Do not redefine code rules, gate stacks, or the ATDD loop inline here.

## Step 0 — Gather feedback

If `$2` is provided, treat it as the verbatim feedback string.

Otherwise, prompt the user via `AskUserQuestion`:

> What feedback do you have for epic **$1**? (bugs found, missing behaviour, UI issues, scope adjustments observed on the assembled epic)

Do NOT proceed without a non-empty feedback string. Record the feedback verbatim for the audit trail.

### Round lock

`mkdir .claude/runs/.lock-feedback-$1/`. Exit 5 on collision (another `/005` round in progress for this epic). Release via `rm -rf` on every halt branch and on completion.

## Step 1 — Clarify and research

1. Read the epic definition: PRD epic section for `$1` (search `PRD.md` for the matching epic-id) and the task breakdown `docs/planning/epic-$1-tasks.yaml`.
2. Read the relevant ruleset files in `.claude/ruleset/` that the feedback touches (e.g. if it is UI feedback, pull the UI-relevant rules; if it is data/contract, pull architecture/testing). Do not re-state their content — read them so the new task entries land in the right scope.
3. Read the affected source files, test files, and any design documentation referenced by the feedback so you can describe what changes.
4. **Trigger `AskUserQuestion` ONLY if:**
   - the feedback names a feature that does not appear in `PRD.md` or `epics.yaml`, OR
   - the feedback could legitimately mean two or more different code changes, OR
   - the feedback implies a PRD scope change (new epic, deprecation, contract change).

   Otherwise proceed to the Step 1 summary + user confirmation.
5. Summarise your understanding of the feedback and the proposed approach — which tasks you will add, which existing tasks they depend on, and what the acceptance shape will look like. Confirm with the user before moving to Step 2.

IMPORTANT: Do not modify `PRD.md` without explicit user approval. If the feedback implies a PRD change (new business scenario, scope revision), ask explicitly.

## Step 2 — Plan new tasks

Once the feedback is understood and the user has confirmed the approach, **append** new task entries to `docs/planning/epic-$1-tasks.yaml`.

- **Append-only.** New tasks land after existing tasks. **Never renumber existing tasks. Never modify tasks already marked `done`.** Tasks in `pending`, `in_progress`, or `blocked` from prior cycles also remain untouched unless the user has explicitly approved a change.
- Each new task follows the same schema as existing entries: `id`, `title`, `story` (where applicable), `status: pending`, `description`, `acceptance_criteria`, `files`, `depends_on`, `effort`.
- Every new task that produces user-observable behaviour MUST have at least one acceptance criterion expressed as an end-to-end action → outcome → assertion (the ATDD spine — exact form depends on the stack's E2E framework; `/002-implement` injects the per-stack flavour).
- Mark `depends_on` on existing tasks where applicable.
- Update the summary section (`total_tasks`, `by_status`, `by_effort`).
- **Record the IDs of every new task created in this round** — `new_task_ids`. These IDs scope Steps 3, 4, and 5. Tasks done before this feedback cycle are NOT re-implemented or re-reviewed by /005.

Emit the planning artifact:

- **Path:** `.claude/runs/{epic_id}/_feedback/{round_id}/05a-plan.json`
- **`round_id`** is a monotonically-increasing identifier for the feedback round. Compute it as: list existing subdirectories under `.claude/runs/{epic_id}/_feedback/`; if none exist, `round_id = 001`; otherwise take the highest numeric prefix and increment. (Equivalent timestamp form `YYYYMMDDTHHMMSS` is acceptable when monotonicity is preserved; pick one form per project and stay consistent.) Multiple feedback rounds therefore accumulate as sibling directories `_feedback/001/`, `_feedback/002/`, ...
- **Payload:** the verbatim feedback string, the clarified interpretation, the list of new task IDs with titles, and any cross-references to existing tasks or PRD sections touched.

## Step 3 — Implement (strict ATDD-E2E)

Implement **only the new tasks recorded as `new_task_ids` in Step 2**, by delegating to `/002-implement` semantics scoped to those IDs. Do NOT re-implement done tasks. Do NOT redefine the implementation protocol here — `/002-implement` owns the per-task loop.

For each new task, in dependency order:

1. **Phase 1.5 plan checkpoint** — the implementer subagent presents its plan first; the user approves, requests iteration, or cancels. (T-002 adds this checkpoint to `/002-implement`.)
2. **Phase 2 TDD execution** — per `/002-implement` Phase 2.
3. **Mark the task `status: done`** in `epic-$1-tasks.yaml` only after its acceptance criteria pass and the gates exit clean.

Tasks done before this feedback cycle are out of scope and MUST NOT be re-implemented.

**Step 3 completion check:** if `/002-implement <id>` (task mode, auto-invoke=true) has already produced `03-verify.json` with `status: ok` and `04-review.json` with `status: ok` for every new task, Steps 4 and 5 SKIP per-task re-invocation and just aggregate the existing artifacts into `05c-verify.json` / `05d-review.json`. Re-invoke only the new tasks where per-task chain is missing or non-ok.

Emit the impl artifact: `.claude/runs/{epic_id}/_feedback/{round_id}/05b-impl.json` — either emitted directly by this command after Step 3 completes, or delegated to `/002-implement` to write under this path (preferred when `/002-implement` accepts a feedback-round-id parameter). The artifact summarises per-task: id, title, commit shas, final status (`done` or `blocked`).

## Step 4 — Verify Definition of Done

For each id in `new_task_ids`, invoke `/003-verify-dod <id>` and collect the per-task verdict. Emit the aggregated result as `05c-verify.json`. Do NOT redefine the audit protocol — `/003-verify-dod` owns the per-task DoD check, the gate stack, and the self-heal Phase 2/3 loop (T-003 makes `/003` self-healing internally; `/005` simply waits for it to settle).

Zero tolerance applies: per-task verdict from `/003` must be `status: ok`; every gate exits 0. Do NOT dismiss failures as "pre-existing", "flaky", or "unrelated".

Emit the verify artifact: `.claude/runs/{epic_id}/_feedback/{round_id}/05c-verify.json` — aggregated by this command from the per-task `/003` outcomes. Contents: per-new-task verdict (`ok` or `fail`), aggregate verdict, references to any heal iterations inside `/003`.

## Step 5 — Code review

For each id in `new_task_ids`, invoke `/004-code-review <id>` and collect the per-task verdict. Emit the aggregated result as `05d-review.json`. The review applies to the branch diff per `git-workflow.md` branch policy produced by the new tasks from Step 3. Do NOT redefine the review protocol — `/004-code-review` owns the reviewer subagent, the verbatim ruleset injection, the severity policy, and the self-heal Phase 2/3 loop (T-004 makes `/004` self-healing internally).

Emit the review artifact: `.claude/runs/{epic_id}/_feedback/{round_id}/05d-review.json` — aggregated by this command from the per-task `/004` outcomes. Contents: per-finding outcome, aggregate verdict (`ok` or `fail`), references to any heal iterations inside `/004`.

## Step 6 — Gatekeeper audit (strict subagent)

**MANDATORY** before reporting to the user. Launch a dedicated audit subagent via the `Task` tool with `subagent_type: general-purpose`. The gatekeeper does NOT re-run gates — it audits your draft completion report against the actual artifact contents to catch any rationalised-away failures, missed steps, or scope drift.

Pass the subagent: the draft completion report you intend to send to the user, plus this prompt verbatim:

> You are a strict audit gatekeeper for an epic-level user-feedback round on epic **$1**. Review the completion report below against a zero-tolerance bar. You may read the artifacts in `.claude/runs/{epic_id}/_feedback/{round_id}/` directly (`05a-plan.json`, `05b-impl.json`, `05c-verify.json`, `05d-review.json`).
>
> **Audit checklist (every item must hold):**
> 1. Was feedback gathered (Step 0) and clarified (Step 1) with user confirmation before any task was planned?
> 2. Are the new tasks present in `epic-{id}-tasks.yaml` as appended entries (not replacements), with full schema (id, title, status, description, acceptance_criteria, files, depends_on, effort)? Were any existing `done` tasks modified? Modifying a done task is a **FAIL**.
> 3. Were ALL new tasks implemented via `/002-implement` semantics including the Phase 1.5 plan checkpoint, then driven through the per-stack gate stack to exit 0?
> 4. Did `/003-verify-dod` return `status: ok` for every new task, AND is every new task `status: done` in `epic-{id}-tasks.yaml` (Step 4)? Pull the raw numbers from `05c-verify.json`. (`/003` artifact status is `"ok"`; task YAML status is `"done"`. The two namespaces must be disambiguated.)
> 5. Did `/004-code-review` reach `ok` for the branch diff per `git-workflow.md` branch policy (Step 5)? Pull the raw numbers from `05d-review.json`.
> 6. Does the report dismiss, rationalise, or explain away ANY failure using phrases like "pre-existing", "flaky", "timing", "unrelated", or "not caused by our changes"? If so → **FAIL**. Zero tolerance is zero tolerance.
> 7. Are tasks marked `done` before this feedback cycle untouched in implementation and review scope?
>
> **VERDICT: PASS or FAIL.** If FAIL, list exactly what was missed or rationalised away, and what must be fixed before COMPLETE.

If the gatekeeper returns `FAIL`, fix every identified issue (which may mean looping back into Step 3, 4, or 5) and re-launch the gatekeeper. Loop until `PASS`. Do NOT report COMPLETE to the user before the gatekeeper passes.

Emit the gatekeeper artifact: `.claude/runs/{epic_id}/_feedback/{round_id}/05e-gatekeeper.json` — contents: verdict (`PASS` or `FAIL`), list of audit items with per-item pass/fail, references to the artifacts the gatekeeper consulted, and (on FAIL) the precise required fixes.

## Completion

Report to the user:

1. **Feedback summary** — the verbatim feedback string and the clarified interpretation.
2. **New tasks** — IDs and titles of the tasks appended in Step 2.
3. **Implementation** — per-new-task status (`done` or `blocked`) and commit shas.
4. **DoD result** — aggregate verdict from `/003` scoped to new tasks.
5. **Review result** — aggregate verdict from `/004` on the branch diff per `git-workflow.md` branch policy.
6. **Gatekeeper verdict** — `PASS` or `FAIL` (must be `PASS` to claim COMPLETE).
7. **Final status:** **COMPLETE** (every new task done, `/003` clean, `/004` clean, gatekeeper PASS) or **NEEDS_ATTENTION** (with the precise blocker and the artifact path that documents it).

## Artifacts

All artifacts for a single feedback round live under `.claude/runs/{epic_id}/_feedback/{round_id}/`:

| File | Step | Owner |
|---|---|---|
| `05a-plan.json` | Step 2 | `/005-implement-feedback` |
| `05b-impl.json` | Step 3 | `/005` summary, or `/002-implement` delegate |
| `05c-verify.json` | Step 4 | `/005` summary, or `/003-verify-dod` delegate |
| `05d-review.json` | Step 5 | `/005` summary, or `/004-code-review` delegate |
| `05e-gatekeeper.json` | Step 6 | `/005-implement-feedback` |

Multiple feedback rounds accumulate as sibling subdirectories `_feedback/001/`, `_feedback/002/`, ..., one per `/005` invocation against the same epic. No artifact is ever overwritten or renumbered across rounds — the audit trail is append-only across rounds as well as within a round.

## Failure modes

- **Epic not found** — `docs/planning/epic-$1-tasks.yaml` is absent → abort at Step 1 with: `Epic $1 not found. Run /001-plan to plan the epic first.`
- **Empty feedback string** — `$2` empty and the interactive prompt also returns empty → abort at Step 0; do not proceed.
- **User does not confirm Step 1 summary** — abort at Step 1; do not write any task entries.
- **Existing `done` task modified during Step 2** — abort with: `Step 2 must not modify done tasks. Revert and re-plan.` (The gatekeeper also catches this in Step 6 as a FAIL.)
- **`/003-verify-dod` final verdict is `fail`** (after its own self-heal exhausted) — surface verbatim, leave new tasks `in_progress` for the offenders, final status `NEEDS_ATTENTION`.
- **`/004-code-review` final verdict is `fail`** (after its own self-heal exhausted) — surface verbatim, final status `NEEDS_ATTENTION`.
- **Gatekeeper returns FAIL after the loop bound is reached** — surface every audit item that failed; final status `NEEDS_ATTENTION`; never report COMPLETE.

## Vocabulary discipline

Mirror `CONTEXT.md` exactly:

- **Finding** — any violation surfaced by `/003-verify-dod` or `/004-code-review`. No severity tiers.
- **Status** — `pending | in_progress | blocked | done`. Never `todo`, `wip`, `complete`, `partial`.
- **Zero tolerance** — every Finding blocks DoD; every gate exit code `!= 0` blocks; every rule violation blocks. The feedback round addresses Findings by planning and implementing real tasks, never by arguing with them.

Do not introduce synonyms.
