---
description: Address findings from /003 or /004 via the feedback-implementer subagent. Loops back to verify. Caps at 3 iterations.
argument-hint: <task-id>
---

# /005-implement-feedback

You are the orchestrator for the feedback loop of the crumbs pipeline. A prior phase — either `/003-verify-dod` or `/004-code-review` — reported `status: "fail"` with one or more **Findings** against task `$ARGUMENTS`. Your job is to dispatch the `feedback-implementer` subagent (`<plugin-root>/agents/feedback-implementer.md`) with the failing phase artifact, every prior phase artifact, and the verbatim ruleset; read its output; and either loop back to verify, escalate to re-planning, or halt on the hard cap.

This command is invokable in two ways:

- **Chained** — auto-invoked by `/002-implement` or `/002-auto-implement` when verify or review returns `status: "fail"`. The parent reads the resulting `05<letter>-feedback-impl.json` and continues the chain.
- **Standalone** — typed directly by the user against a task whose latest phase artifact reports `status: "fail"`. Same workflow; there is simply no parent chain to advance.

Argument: `$ARGUMENTS` — the task id (e.g. `T-014`). Required.

## Inputs

- **`<task-id>`** — passed as `$ARGUMENTS`. Required positional argument.
- **`docs/planning/epic-{id}-tasks.yaml`** — locate the task entry by scanning every `epic-*-tasks.yaml` under `docs/planning/`. The first match wins. If not found anywhere, abort with: `Task <task-id> not found in any epic-*-tasks.yaml. Run /001-plan first.` Capture the `epic_id` from the matching file name (e.g. `epic-03-tasks.yaml` → `epic_id = E-003`).
- **`.claude/ruleset/*.md`** — all 18 canonical rule files, verbatim-loaded into memory for downstream subagent injection. No `@`-include — content is pasted into the subagent prompt body. If any file is missing, halt with: `Ruleset incomplete: <name>.md missing. Run plugin setup.`
- **All prior phase files** in `.claude/runs/{epic_id}/{task_id}/`:
  - `01-plan.json` — planner output (always present after `/001-plan`).
  - `02-impl.json` — implementer output (always present after `/002-implement`).
  - `03-verify.json` — verifier output (present if `/003-verify-dod` has run for the current cycle).
  - `04-review.json` — reviewer output (present if `/004-code-review` has run for the current cycle).
  - `05a-feedback-impl.json`, `05b-feedback-impl.json` — earlier feedback rounds in the same cycle, if any.
- **`.claude/stack.yaml`** — read `extras` (propagated verbatim to the subagent), `paths` (SoT overrides), and `gates` (referenced by the subagent for shape-of-DoD awareness).

## Workflow

### Phase 0 — Pre-flight

- Verify the task entry exists in some `epic-{id}-tasks.yaml`. If absent → abort (see Inputs).
- Verify the task `status` is `in_progress`. If `pending` or `blocked`, abort with: `Task <task-id> is not in_progress. /005-implement-feedback runs only on an active task.` If `done`, abort with: `Task <task-id> is already done. Nothing to feed back on.`
- Confirm `.claude/runs/{epic_id}/{task_id}/` exists. If absent, abort with: `No runs directory for <task-id>. Run /002-implement first.`
- Confirm `.claude/ruleset/` contains all 18 canonical rule files.
- Confirm `.claude/stack.yaml` exists and parses. If absent, abort with: `stack.yaml missing. Run /000-prd-refine to bootstrap the project.`
- **Determine the latest failing phase file.** Enumerate every file in `.claude/runs/{epic_id}/{task_id}/` matching `NN-*.json` (sorted by numeric prefix descending). Pick the highest-numbered one whose top-level `status` is `"fail"`. Skip `05*` files in this search — those are feedback artifacts, not gate artifacts. The candidate set is `{03-verify.json, 04-review.json}`. If neither has `status: "fail"`, abort with: `No failing phase to address. Run /003-verify-dod or /004-code-review first.` Record the chosen path as `failing_phase_path` and its content as `failing_phase_content`.
- **Determine the iteration counter.** Count existing `05*-feedback-impl.json` files in the same directory. Possible values:
  - `0` → next iteration is `05a`.
  - `1` → next iteration is `05b`.
  - `2` → next iteration is `05c`.
  - `≥3` → halt with: `Loop limit reached. Iterations: 05a, 05b, 05c. Escalating to user. Last failing phase: <failing_phase_path>.` Then print the escalation route verbatim:
    ```
    Suggested resolution paths: (1) /001-plan --resplit <task-id> — decompose the task; (2) edit findings manually then re-run /003-verify-dod and /004-code-review; (3) inspect runs/<epic>/<task>/05c-feedback-impl.json payload.diagnosis for the agent's analysis.
    ```
    Leave task `status: in_progress`. Do not dispatch.
- Compute the next artifact path: `.claude/runs/{epic_id}/{task_id}/05<letter>-feedback-impl.json` where `<letter>` is `a`, `b`, or `c`.

### Phase 1 — Dispatch feedback-implementer subagent

Use the **Task tool** with `subagent_type: "feedback-implementer"`. Inject the following into the subagent prompt body (verbatim, no `@`-includes):

1. **Task id and epic id** — `T-NNN` and `E-NNN`, plus the path to `epic-{id}-tasks.yaml`.
2. **Failing phase pointer** — the absolute path `failing_phase_path` and the parsed `failing_phase_content` pasted verbatim under a header `--- Failing phase: 03-verify.json ---` or `--- Failing phase: 04-review.json ---`. The subagent reads `payload.findings[]` and addresses each at the root cause. Include the following instruction verbatim in the prompt body:
   ```
   Before fixing, validate every finding's `location` field. If the file no longer exists at HEAD (e.g. it was deleted in a prior fix iteration), drop that finding and note it in `payload.dropped_findings: [{ rule, location, reason: 'file_deleted' }]`. Do NOT attempt to fix findings against non-existent files.
   ```
3. **Task entry (YAML)** — the entire YAML entry for the task as it appears in `epic-{id}-tasks.yaml`. Include `id`, `slug`, `title`, `status`, `domain_scenarios`, `atdd_spec`, `acceptance`, `notes`, and any other fields present.
4. **All prior phase files** — for every `NN-*.json` in `.claude/runs/{epic_id}/{task_id}/` (including `05a`, `05b` if present), paste the content verbatim under headers `--- Prior phase: 01-plan.json ---`, `--- Prior phase: 02-impl.json ---`, `--- Prior phase: 03-verify.json ---`, `--- Prior phase: 04-review.json ---`, `--- Prior phase: 05a-feedback-impl.json ---`, etc. Order by numeric prefix ascending, then letter. The subagent must understand the full task history before fixing.
5. **Verbatim ruleset** — for each of the 18 files in `.claude/ruleset/`, paste the content prefixed by a header `--- <filename>.md ---`. Order alphabetically. Do not summarise, do not omit.
6. **`stack.yaml.extras`** — paste the `extras` mapping verbatim under a header `--- stack.yaml.extras ---`. Escape hatch for stack-specific quirks (e.g. `bash_buffering_warning`, `user_ping_interval_minutes`).
7. **Output contract** — instruct the subagent to write its result to `.claude/runs/{epic_id}/{task_id}/05<letter>-feedback-impl.json`, validated against `schemas/run-phase.schema.json`. The top-level `status` field must be one of `ok`, `blocked`. Required `payload` keys vary by status:
   - `ok` → `commit_shas` (array, one or few), `files_changed`, `findings_addressed` (array of finding ids from the failing phase artifact).
   - `blocked` → `reason` (prose), `next` (one of `re-plan`, `loop_limit_exceeded`, `external_decision_required`), optional `suggested_follow_up`.

The feedback-implementer is expected to:

- Read `payload.findings[]` from the failing phase artifact and address **each** at the root cause. **Zero tolerance** — every Finding blocks DoD; the subagent does not argue with Findings, it fixes them. Exception: if a Finding's `location` points at a file that no longer exists at `HEAD` (e.g. deleted in a prior fix iteration), drop that Finding and record it under `payload.dropped_findings: [{ rule, location, reason: 'file_deleted' }]`. Never attempt to fix Findings against non-existent files.
- **Never silently expand scope.** If a Finding requires reverting an architectural choice from the plan (`01-plan.json`) — e.g. dropping an aggregate boundary, changing the chosen pattern, removing a contract — the subagent emits `status: "blocked"` with `next: "re-plan"` and a `payload.reason` explaining why. The fix is not attempted; control returns to `/001-plan --resplit`.
- Make **one or a few commits** on the task branch (never amend, never force-push). Commit messages follow Conventional Commits with a `fix(T-NNN):` or `refactor(T-NNN):` prefix per `.claude/ruleset/git-workflow.md`.
- Sign commits if `require_signed_commits: true` is set in the `git-workflow.md` toggle block.
- Write the final artifact `05<letter>-feedback-impl.json` with a top-level `status` field: `ok` or `blocked`.

### Phase 2 — Read feedback-implementer output

Parse `.claude/runs/{epic_id}/{task_id}/05<letter>-feedback-impl.json` and validate it against `schemas/run-phase.schema.json`. If validation fails, halt with the artifact path and the validator error.

Branch on `status`:

- **`status: "ok"`** — the subagent claims every Finding has been addressed. **Trust nothing; re-verify.** Auto-invoke `/003-verify-dod $ARGUMENTS`. The verifier writes a fresh `03-verify.json`, **overwriting** any prior failing one (the prior is preserved in git history of the runs dir only if it was committed elsewhere — runs are gitignored, so prior failing verifies are intentionally transient). Read the new `03-verify.json` and branch:

  - **Verify pass** — continue:
    - If the failing phase that originally triggered this command was `03-verify.json`, the chain is now complete from this command's perspective. If invoked **chained**, return control to the parent (`/002-implement` or `/002-auto-implement`); the parent reads `05<letter>-feedback-impl.json` and the fresh `03-verify.json` and decides whether to invoke `/004-code-review`. If invoked **standalone**, print: `Verify now passes for <task-id>. Run /004-code-review <task-id> to gate the diff, or /006-merge <task-id> if review is disabled by toggle.`
    - If the failing phase was `04-review.json`, auto-invoke `/004-code-review $ARGUMENTS`. Read the new `04-review.json`:
      - **Review pass** → the chain is complete. Print: `Task <task-id> chain complete. Suggest: /006-merge <task-id>.` Do **not** auto-invoke `/006-merge` — merge is always user-triggered.
      - **Review fail** → recurse: invoke `/005-implement-feedback <task-id>` again. The iteration counter increments (`05a` → `05b` → `05c`). The next invocation's Phase 0 enforces the hard cap.

  - **Verify fail** — recurse: invoke `/005-implement-feedback <task-id>` again. The iteration counter increments. The next invocation's Phase 0 enforces the hard cap.

- **`status: "blocked"`** with `payload.next: "re-plan"` — the subagent declared the task needs re-planning because a Finding requires reverting an architectural choice. Halt. Print:
  ```
  feedback-implementer requests re-planning for <task-id>.
  Reason: <payload.reason>
  Suggest: /001-plan --resplit <task-id>
  ```
  Leave task `status: in_progress`. The user invokes `/001-plan --resplit` to decompose the task into smaller ones. Do not advance the chain.

- **`status: "blocked"`** with `payload.next: "loop_limit_exceeded"` — the subagent itself detected loop limit before this command's Phase 0 did (e.g. partial run, race). Halt and surface the message to the user verbatim. Leave task `status: in_progress`.

- **`status: "blocked"`** with `payload.next: "external_decision_required"` — the subagent hit a blocker requiring an external decision (missing dependency, ambiguous Finding, infra not available). Print `payload.reason` and the suggested follow-up if present. Leave task `status: in_progress`.

## Iteration tracking

- **File naming**: the first iteration writes `05a-feedback-impl.json`, the second `05b-feedback-impl.json`, the third `05c-feedback-impl.json`. The command counts existing `05*` files at Phase 0 to determine the next letter.
- **Cap**: 3 iterations per task. `05c` is the last attempt. After `05c` produces another verify or review fail, the **next** invocation of this command halts at Phase 0 and refuses to dispatch a 4th feedback subagent.
- **Append-only**: feedback artifacts are never overwritten or renumbered. If `05a` already exists, the next run writes `05b`; it does not replace `05a`.
- **Counter scope**: the counter is per-task, not per-gate. Three rounds total across verify and review combined — not three per gate. This is consistent with the cap enforced by `/002-implement` Phase 4/5.
- **Why three?** Empirically: round 1 fixes the obvious surface Findings; round 2 catches second-order effects from the round-1 patch; round 3 is the last honest attempt before the diagnosis itself is suspect. After three rounds the bottleneck is almost certainly upstream — wrong plan, wrong scenario decomposition, or wrong rule — and the right move is `/001-plan --resplit`, not another fix.
- **What "consecutive" means**: this command's cap counts feedback artifacts in the task's runs directory regardless of whether the most recent verify/review was triggered by chained orchestration or standalone invocation. The counter is purely filesystem-derived, so it stays accurate across parent restarts.

## Discipline

- **The feedback loop does NOT bypass gates.** Every Finding from `/003` or `/004` blocks DoD. The feedback-implementer addresses them; it never overrides, downgrades, or rationalises them away. There are no severity tiers.
- **Never silently expand scope.** If addressing a Finding would require reverting an architectural choice from `01-plan.json`, the subagent emits `status: "blocked"` with `next: "re-plan"`. Scope expansion goes through `/001-plan --resplit`, not through a feedback round.
- **Append-only commits.** The subagent makes one or a few commits stacked on top of the implementer's commit. **Never amend.** **Never force-push.** History cleanup (squash) is a `/006-merge` concern, governed by `.claude/ruleset/git-workflow.md`.
- **Read all prior phase files.** The subagent must understand the full task history (plan → impl → verify/review → earlier feedback rounds) before fixing. Skipping context is how regressions are introduced.
- **Filesystem-only subagent comms.** The main thread reads `05<letter>-feedback-impl.json` after the subagent returns. Ruleset content is verbatim-injected into the prompt body, never via `@`-include (per CONTEXT.md "Ruleset injection").
- **Honour `require_signed_commits`.** If the toggle block in `git-workflow.md` sets it to `true`, every feedback commit is signed.
- **Task `status` stays `in_progress`.** This command never flips `status` to `done` or back to `pending`. Those transitions are owned by `/002-implement` Phase 6 (`done`) and `/001-plan --resplit` (`pending`). On any hard halt, the task stays `in_progress` and the user is told what to do next.

## Standalone vs chained

- **Chained** (auto-invoked by `/002-implement` or `/002-auto-implement` on verify or review fail): the parent reads `05<letter>-feedback-impl.json` and continues the chain. The parent owns the overall iteration cap for the task; this command's Phase 0 cap is the safety net for standalone invocation and for parent miscounts.
- **Standalone** (user-typed): same workflow; just no parent chain to advance. After Phase 2 success, this command prints a one-liner suggesting the next step (`/004-code-review` if the failing phase was verify; `/006-merge` if review). It does not chain further than the auto-invoked `/003` and `/004` runs needed to confirm the fix.

## Re-plan handoff (`next: "re-plan"`)

The `re-plan` signal is the feedback loop's pressure-release valve. It exists because some Findings cannot be honestly fixed without violating the plan recorded in `01-plan.json`. Examples:

- A Finding from `/004-code-review` says the chosen aggregate boundary leaks domain state into infrastructure. The fix is to redraw the boundary, which would invalidate the task's `domain_scenarios` mapping.
- A Finding from `/003-verify-dod` says the implemented contract drifts from the Business scenario. The drift is structural — the scenario itself needs to be re-decomposed.
- A Finding requires changing the pattern (e.g. repository → event-sourced) chosen during planning. This is not a fix; it is a re-plan.

In all such cases the feedback-implementer emits `status: "blocked"` with `next: "re-plan"` and a precise `payload.reason` pointing at the conflicting plan element. The main thread halts and prints the re-plan suggestion. The user invokes `/001-plan --resplit <task-id>` which replaces the offending task with smaller ones linked to the same Business scenarios. The old task is archived to `runs-archive/`. The new tasks each begin their own `/002-implement` cycle.

This guard is the reason the feedback loop is bounded and honest. Silent scope expansion (fixing the Finding by quietly rewriting the plan) would invalidate every downstream artifact and destroy the audit trail.

## Failure modes

- **Task not found** → abort at Phase 0 with the path and id.
- **Task not `in_progress`** → abort at Phase 0 with the specific message.
- **No failing phase artifact** → abort at Phase 0 with: `No failing phase to address. Run /003-verify-dod or /004-code-review first.`
- **3 iterations exhausted** → halt at Phase 0 with the escalation message; leave task `status: in_progress`.
- **Subagent emits `next: "re-plan"`** → halt at Phase 2 with the re-plan suggestion; leave task `status: in_progress`.
- **Subagent emits `next: "loop_limit_exceeded"` or `next: "external_decision_required"`** → halt at Phase 2; surface the message verbatim; leave task `status: in_progress`.
- **Subagent crashes or schema validation fails** on `05<letter>-feedback-impl.json` → halt with the artifact path and the validator error. Do not retry silently.
- **Ruleset directory missing or incomplete** → abort at Phase 0; list the missing files.
- **`stack.yaml` missing** → abort at Phase 0 pointing at `/000-prd-refine`.

## Vocabulary discipline

Mirror `CONTEXT.md` exactly. Use only these terms when communicating with the user or writing artifacts:

- **Finding** — any violation surfaced by `/003-verify-dod` or `/004-code-review`. Never use "issue", "blocker", "non-blocker", "critical/major/minor". Findings have no severity tiers.
- **Status** — `pending | in_progress | blocked | done`. Never `todo`, `wip`, `complete`, `partial`. This command operates only on `in_progress` tasks and never transitions `status`.
- **Zero tolerance** — every Finding blocks DoD; every gate exit code `!= 0` blocks; every rule violation blocks. The feedback loop addresses Findings; it never argues with them.

Do not introduce synonyms. If you find yourself reaching for one, re-read the relevant CONTEXT.md entry.

## Subagent chain summary

```
/005-implement-feedback <task-id>
   |
   ├─ Phase 0  pre-flight (locate failing phase; count 05* files; enforce cap)
   ├─ Phase 1  feedback-implementer subagent → 05<letter>-feedback-impl.json
   │            (reads all prior phase files; addresses every Finding at root cause)
   └─ Phase 2  branch on status:
                ok          → auto-invoke /003-verify-dod
                              ├─ pass + failing was 03 → return to parent / suggest /004
                              ├─ pass + failing was 04 → auto-invoke /004-code-review
                              │     ├─ pass → suggest /006-merge
                              │     └─ fail → recurse (counter +1)
                              └─ fail → recurse (counter +1)
                blocked re-plan          → halt; suggest /001-plan --resplit
                blocked loop_limit_*     → halt; surface verbatim
                blocked external_*       → halt; surface verbatim
```

The feedback-implementer subagent lives in `<plugin-root>/agents/feedback-implementer.md` (plugin-owned, not project-owned). The chain is iterative: `verifier` / `reviewer` → `feedback-implementer` → back to `verifier`. This command owns one feedback round's traversal of that loop; the iteration counter (`05a`, `05b`, `05c`) bounds the loop at three rounds per task.

## Worked example

Given task `T-014` belonging to epic `E-003`, `/004-code-review` just reported one Finding (`missing aria-label per accessibility.md`) and wrote `04-review.json` with `status: "fail"`:

1. **Phase 0** — `/005-implement-feedback T-014` locates `docs/planning/epic-03-tasks.yaml`, confirms `T-014.status = in_progress`. Enumerates `.claude/runs/E-003/T-014/`: finds `01-plan.json`, `02-impl.json`, `03-verify.json` (status `pass`), `04-review.json` (status `fail`). Picks `04-review.json` as `failing_phase_path`. Counts `05*` files: 0 → next iteration is `05a`.
2. **Phase 1** — `feedback-implementer` subagent receives task YAML, `04-review.json` content (with the one Finding), all prior phase files, all 18 ruleset files verbatim, and `stack.yaml.extras`. It adds the `aria-label` per `accessibility.md`, commits with `fix(T-014): add aria-label to cancel button`, and writes `05a-feedback-impl.json` with `status: ok`, `findings_addressed: ["F-001"]`.
3. **Phase 2** — Main thread auto-invokes `/003-verify-dod T-014`. Verify passes. The original failing phase was `04-review.json`, so main thread auto-invokes `/004-code-review T-014`. Review passes. Print: `Task T-014 chain complete. Suggest: /006-merge T-014.`

Total feedback iterations: 1 of 3 allowed. Had the subagent's fix introduced a new Finding, the counter would have advanced to `05b` on the next round.
