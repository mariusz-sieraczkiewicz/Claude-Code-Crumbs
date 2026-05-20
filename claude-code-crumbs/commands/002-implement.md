---
description: Implement an epic (default) or a single task. Epic mode iterates every pending task and auto-invokes /003-verify-dod then /004-code-review at the end. The per-task plan checkpoint (Phase 1.5) is gated by the `require_plan_approval` toggle in git-workflow.md (default `false` — runs every task to completion without prompting; flip `true` to restore the sielappkowo Approve/Iterate/Cancel discipline). Task mode runs the single-task TDD chain.
argument-hint: <epic-id> | <task-id>
---

Implement the work for **$ARGUMENTS**. The command dispatches on argument shape:

- **`<epic-id>`** (matches `^E-`) → **epic mode** (default). Iterate every `status: pending` task in `epic-{id}-tasks.yaml` in dependency order. Each task runs the full per-task flow below (Phase 0 → Phase 6). Phase 1.5 (per-task plan checkpoint) runs only when `require_plan_approval: true` in `git-workflow.md` (default `false` — Phase 1.5 is skipped and the implementer goes straight to full-TDD Phase 2). When the epic loop finishes (every task at `status: done`), auto-invoke `/003-verify-dod <epic-id>` and — gated by the `auto_invoke_review` toggle — `/004-code-review <epic-id>`.
- **`<task-id>`** (matches `^T-`) → **single-task mode** (legacy). Runs the single-task flow (Phase 0 → Phase 6) for that one task only. No auto-chain at epic granularity. This preserves the legacy `/002-implement <task-id>` contract for resume scenarios and ad-hoc task re-runs.
- Anything else → abort with: `Argument "<value>" is neither an epic id (E-…) nor a task id (T-…). Run /001-plan first or supply a valid id.`

The per-task flow dispatches the `implementer` subagent in **one or two phases** depending on the `require_plan_approval` toggle:
- **`require_plan_approval: true`** — two phases: first **plan-only** (Phase 1.5, written as a `phase: "impl-plan"` artifact and presented to the user for Approve/Iterate/Cancel via `AskUserQuestion`), then **full TDD** (Phase 2, written as a `phase: "impl"` artifact). The plan checkpoint is the human-in-the-loop gate restoring the sielappkowo "Present plan, iterate until accepted" discipline.
- **`require_plan_approval: false`** (default) — single phase: the implementer is dispatched in **full TDD** mode directly (Phase 2), no plan-only stage, no prompt. The epic loop iterates every task to completion without user interaction.

## Mode dispatch

```
$ARGUMENTS
   ├─ matches ^E-      → epic mode      (default; batch over pending tasks)
   ├─ matches ^T-      → task mode      (single-task, legacy semantics)
   └─ otherwise        → abort with usage error
```

The id is resolved at Phase 0 against the filesystem:

- Epic mode: locate `docs/planning/epic-{id}-tasks.yaml` (3-digit zero-padded form, e.g. `E-001` → `epic-001-tasks.yaml`; or by exact filename match for non-numeric ids like `epic-restore-flow-tasks.yaml`). If not found, abort with the search path.
- Task mode: scan every `docs/planning/epic-*-tasks.yaml` for an entry whose `id` matches the argument. The first match wins; capture `epic_id` from the matching file's name.

## Inputs

- **`<epic-id>`** or **`<task-id>`** — passed as `$ARGUMENTS`. Required positional argument.
- **`docs/planning/epic-{id}-tasks.yaml`** — the task list. Epic mode reads the whole file (iterating pending tasks); task mode reads the one matching entry.
- **`docs/planning/epics.yaml`** — Business scenarios for the epic (Gherkin block-scalars), injected verbatim into the implementer so it can author the ATDD spec. Read the matching epic entry's `business_scenarios` field. If the field is missing on the epic entry, abort with the path and a hint to re-run `/001-plan`.
- **`.claude/ruleset/*.md`** — all 18 canonical rule files, verbatim-loaded into memory for downstream subagent injection (no `@`-include — content is pasted into the subagent prompt body).
- **`.claude/ruleset/git-workflow.md`** — parse the YAML toggle block at the top of the file. Toggle keys consulted:
  - `auto_invoke_review`, `auto_invoke_verify`, `allow_commit_to_main`, `pr_required`, `branch_name_pattern`
<!-- FREEZE:IF require_signed_commits -->
  - `require_signed_commits`
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_dco_signoff -->
  - `require_dco_signoff`
<!-- FREEZE:ENDIF -->
  Defaults for each toggle are documented inline alongside the toggle block under "Toggle precedence" below; a missing key takes its documented default with no warning.
- **`.claude/stack.yaml`** — read `extras` (propagated verbatim to all subagents), `paths` (SoT overrides used by downstream gates), and `gates` (referenced by `/003-verify-dod`).

## Epic mode workflow

**Per-task phase skip table (epic mode).** The following per-task phases are SKIPPED in epic mode — the epic-level auto-chain to `/003-verify-dod` and `/004-code-review` runs once after the whole task loop completes:

| Phase | Per-task purpose                | Skipped in epic mode? |
|-------|----------------------------------|------------------------|
| 3     | Verify per task                  | Yes — verify runs once at epic close-out |
| 4     | Review per task                  | Yes — review runs once at epic close-out |
| 5     | Feedback-implement per task      | Yes — handled by `/005-implement-feedback` against the epic if findings surface at close-out |

The per-phase sections below restate this with a one-line pointer back here; the table above is authoritative.

**Epic-mode outcome discriminator.** Every halt branch and the success branch print a final summary line of the form `epic_outcome: <value>`. The values are:

- `done` — every task reached `status: done` AND the epic-level `/003` (and `/004` if enabled) returned `status: ok`.
- `cancelled` — user picked **Cancel** at Phase 1.5 (only reachable when `require_plan_approval: true`).
- `halted_too_big` — implementer returned `status: too_big_proposal` at Phase 3 of some task.
- `halted_blocked` — implementer returned `status: blocked` at Phase 3 of some task.
- `halted_verify` — `/003-verify-dod` returned `status: fail` after exhausting its own self-heal cap.
- `halted_review` — `/004-code-review` returned `status: fail` after exhausting its own self-heal cap.

The discriminator is the LAST line of the orchestrator's output for the run. Callers (CI scripts, sub-orchestrators) parse it to branch on outcome.

Epic mode is a thin loop around the per-task flow. The loop body IS the per-task flow (Phase 0 → Phase 6) executed exactly as in task mode. The differences are:

1. **Pre-loop pre-flight** (epic-level): validate the epic file exists, the working tree is clean, git identity is configured, and acquire the **epic lock** (see "Lock semantics" below). The epic lock is held for the entire batch.
2. **Task iteration**: select the next `status: pending` task whose `depends_on` are all `done`. If multiple tasks are eligible, pick the lexicographically smallest `id` (stable, predictable order). If no task is eligible but pending tasks remain, abort with the unresolvable dependency cycle printed.
3. **Per-task flow**: run Phase 0 → Phase 6 for the selected task. The task acquires its own task lock (see "Lock semantics") nested under the epic lock. On per-task halt (`too_big_proposal`, `blocked`, loop-limit), the epic loop also halts — there is no skip-and-continue. Emit the appropriate `epic_outcome` discriminator (`halted_too_big`, `halted_blocked`, etc.) as the final summary line. The user re-runs `/002-implement <epic-id>` after fixing.
4. **Post-loop auto-chain** (epic-level, runs ONLY after every task in the epic reaches `status: done`):
   - Auto-invoke `/003-verify-dod <epic-id>` unconditionally. No user prompt.
   - If `/003-verify-dod` returns `status: ok` AND `auto_invoke_review` is **not** `false` (default: `true`) → auto-invoke `/004-code-review <epic-id>`. The self-healing Phase 2/3 loops inside `/003` and `/004` are owned by those commands; this command only chains them.
   - If `/003-verify-dod` returns `status: fail` (after its own self-heal cap has been exhausted) → halt epic mode with the verifier findings; do NOT invoke `/004`. Emit `epic_outcome: halted_verify`. The user re-runs after fixing or runs `/005-implement-feedback <epic-id>` for a fresh feedback round.
   - If `/004-code-review` returns `status: fail` (after its own self-heal cap has been exhausted) → halt epic mode with the reviewer findings. Emit `epic_outcome: halted_review`.
   - If `auto_invoke_review: false` → skip the `/004` call and print: `Auto-review disabled by toggle. Run /004-code-review <epic-id> manually.`
   - On success (every step ok) → emit `epic_outcome: done`.
5. **Lock release**: the epic lock is released on success (after the auto-chain returns) AND on every halt/abort branch.

### Epic mode pseudo-code

```
acquire_epic_lock(EPIC_ID)
try:
    while pending_tasks_remain(EPIC_ID):
        task = next_eligible_pending_task(EPIC_ID)
        if task is None:
            abort("Pending tasks remain but dependencies unresolvable.")
        outcome = run_per_task_flow(EPIC_ID, task.id)        # Phase 0 → Phase 6 below
        if outcome == "cancelled":
            print("epic_outcome: cancelled"); return
        if outcome == "too_big_proposal":
            print("epic_outcome: halted_too_big"); return
        if outcome == "blocked":
            print("epic_outcome: halted_blocked"); return
    # All tasks done.
    verify_result = invoke("/003-verify-dod", EPIC_ID)
    if verify_result.status != "ok":
        surface(verify_result.findings)
        print("epic_outcome: halted_verify"); return
    if toggles.auto_invoke_review:
        review_result = invoke("/004-code-review", EPIC_ID)
        if review_result.status != "ok":
            surface(review_result.findings)
            print("epic_outcome: halted_review"); return
    else:
        inform("Auto-review disabled by toggle. Run /004-code-review <epic-id> manually.")
    print("epic_outcome: done")
finally:
    release_epic_lock(EPIC_ID)
```

## Per-task flow (used by both modes)

### Phase 0 — Pre-flight

- Verify the task entry exists in some `epic-{id}-tasks.yaml`. In task mode, scan every file matching that glob; the first match wins. In epic mode, the file is already known. If absent → abort (see Inputs).
- Capture the `epic_id` from the matching file's name (e.g. `epic-001-tasks.yaml` → `epic_id = E-001`, matching the entry in `epics.yaml`). Cross-check that the same epic id appears in `epics.yaml`; if not, abort with both paths.
- **Detached HEAD check.** Run `git rev-parse --abbrev-ref HEAD`. If it returns the literal string `HEAD`, the working tree is in a detached-HEAD state and branch logic downstream will misbehave. ABORT with: `HEAD is detached. Check out a branch first: \`git checkout <branch-name>\` (e.g. main).`
- **Dirty working tree check.** Run `git status --porcelain`. If the output is non-empty:
<!-- FREEZE:IF allow_commit_to_main -->
  - `allow_commit_to_main: true` (solo preset) → proceed but print a visible warning: `Working tree dirty; proceeding under allow_commit_to_main=true (solo preset). Implementer commit will include all current staged/unstaged changes.`
<!-- FREEZE:ELSE -->
  - `allow_commit_to_main: false` (default; non-solo presets) → abort: `Working tree has uncommitted changes. Commit or stash them before /002-implement.`
<!-- FREEZE:ENDIF -->
- **Acceptance criteria sanity check.** Before dispatching the implementer, verify the task entry has a non-empty `acceptance_criteria: [...]` array:
  1. Read the task entry from `epic-{id}-tasks.yaml`.
  2. If `acceptance_criteria` is missing or empty, abort: `Task <task-id> has no acceptance_criteria. Re-run /001-plan or edit the task entry.`
  3. If any entry is the empty string or whitespace only, abort: `Task <task-id> acceptance_criteria contains an empty entry. Fix the task entry.`
  4. The implementer is responsible for the substantive interpretation of each criterion; this command only enforces shape.
- Verify the task `status` is `pending` or `blocked`. If `done` or `in_progress`, behaviour depends on mode:
  - Task mode: `done` → `Task <task-id> is already done. Use /001-plan --resplit to revisit.`; `in_progress` → `Task <task-id> is already in_progress. Clear status manually before re-running /002-implement.`
  - Epic mode: `done` → skip silently (task already complete, loop continues to next eligible); `in_progress` → abort the entire epic with the same message as task mode (do not silently overwrite an in-flight task).
- Set the task `status: in_progress` in `epic-{id}-tasks.yaml` (write back; preserve YAML formatting, comments, and key order).
- Ensure `.claude/runs/{epic_id}/{task_id}/` exists (create recursively if missing).
- Ensure `.claude/runs/{epic_id}/{task_id}/artifacts/` exists for transient subagent outputs (logs, drafts).
- Confirm `.claude/ruleset/` contains all 18 canonical rule files. If any are missing, list them and abort — the implementer cannot be dispatched without the full ruleset.
- Confirm `.claude/stack.yaml` exists and parses. If absent, abort with: `stack.yaml missing. Run /000-prd-refine to bootstrap the project.`
- **Git identity preflight.** The implementer subagent will `git commit`; a fresh machine with no global git identity fails mid-task with a cryptic git error. Run these checks first:
  1. `git config --get user.email` must return non-empty.
  2. `git config --get user.name` must return non-empty.
  3. If either is empty → ABORT with: `Git identity not configured. Run \`git config --global user.email "<you@example>"\` and \`git config --global user.name "<Your Name>"\` then re-run.`
<!-- FREEZE:IF require_signed_commits -->
- **Signed-commits preflight.** If `git-workflow.md.require_signed_commits: true`:
  1. Run `git config --get user.signingkey` — must return non-empty.
  2. Run `git config --get commit.gpgsign` — must return `true` (or `gpg.format=ssh` plus `user.signingkey` set).
  3. Verify the agent is available:
     - For GPG: `gpg --list-secret-keys "$(git config --get user.signingkey)" >/dev/null`
     - For SSH: `ssh-add -L | grep -q "$(git config --get user.signingkey)"` or accept if `gpg.format=ssh` and the key file exists on disk.
  4. If any check fails → ABORT with: `require_signed_commits=true but signing not configured. Set git config user.signingkey and ensure your agent (gpg-agent / ssh-agent) is running. Re-run after fixing.`
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_dco_signoff -->
- **DCO sign-off flag.** Read `require_dco_signoff` from the `git-workflow.md` YAML toggle block (default: `false`; the `oss` preset ships it as `true`). If true, set the in-memory flag `REQUIRE_DCO_SIGNOFF=true` and pass it into the implementer dispatch context (Phase 2, step 8 below). The implementer agent uses `git commit -s` (which appends a `Signed-off-by:` trailer) when this flag is set. The plugin does NOT validate the DCO trailer here — that is `/006-merge`'s Phase 0 pre-flight job (and it runs before `git push` so the user can rebase the fork branch without a force-push from origin).
<!-- FREEZE:ENDIF -->
- **Task lock.** Per-task lock prevents concurrent invocations of `/002-implement` against the same task id (two terminals racing on the branch, commit, or `02-impl.json`). The orchestrator substitutes the resolved epic id and task id into the path string BEFORE invoking the Bash tool (environment variables do not persist across separate Bash tool calls in this harness):

  ```sh
  LOCK_DIR=".claude/runs/.lock-${EPIC_ID}-${TASK_ID}"
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
      LOCK_INFO=""
      [ -f "$LOCK_DIR/info" ] && LOCK_INFO=" (held by: $(cat "$LOCK_DIR/info"))"
      echo "Error: task ${TASK_ID} is already being processed${LOCK_INFO}." >&2
      echo "If you are sure no other process is running, remove $LOCK_DIR and retry." >&2
      exit 5
  fi
  echo "$$@$(hostname) $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LOCK_DIR/info"
  ```

  Exit code `5` is reserved for the "already running" case so callers can distinguish concurrency from other pre-flight failures.

  **No `trap`-based cleanup.** A `trap` set inside a Bash tool call only lives for the duration of that single invocation; the orchestrator returns to the Claude harness immediately after, and the trap exits — releasing the lock prematurely. Instead, the lock is released by an explicit `rm -rf "$LOCK_DIR"` in the FINAL Phase (success path, Phase 6) AND in every halt/abort branch (`too_big_proposal`, `blocked`, verify/review loop-limit, schema validation failure, dispatch error). Every halt path MUST explicitly release the lock; do not assume any wrapper does it.

  **Trade-off:** if the orchestrator itself crashes (host crash, harness terminated), the lock directory persists as a stale lock and manual `rm -rf .claude/runs/.lock-<epic>-<task>/` is required. The error message at acquisition points the user at the exact path.

### Phase 0.5 — Resume detection

After acquiring the Task lock and BEFORE re-dispatching the implementer subagent, scan `.claude/runs/${EPIC_ID}/${TASK_ID}/` for prior artifacts from a previously interrupted run (Ctrl-C, host crash, halt that left `status: in_progress`). The goal is to give the user a meaningful resume hint instead of a bare `Task in_progress, clear status manually` error.

Branch on the highest-numbered artifact present:

- If `04-review.json` exists with `status: "ok"` AND `03-verify.json.status == "ok"` AND `02-impl.json.payload.commit_sha` matches HEAD (or is an ancestor of HEAD per `git merge-base --is-ancestor <sha> HEAD`) → fast-forward to Phase 6 (mark task `done`, suggest `/006-merge` in task mode; loop to next task in epic mode). Print: `Task already complete (verify ok, review ok, commit on HEAD). Marked done.`
- If `04-review.json` has `status: "fail"` OR `03-verify.json.status == "fail"` AND any `05{a|b|c}-feedback-impl.json` exists → suggest `/005-implement-feedback ${EPIC_ID}` to continue the feedback loop. Print a resume summary with the last 2 findings from the most recent failing artifact. Halt; do not re-dispatch the implementer. (In epic mode, this halts the whole batch — the user must clear the failing finding before re-running.)
- If `02-impl.json` exists with `status: "ok"` but no `03-verify.json` → in task mode, resume by invoking `/003-verify-dod` (skip the implementer phase) and continue from Phase 4; in epic mode, the per-task `/003`/`/004` slots are no-ops (the epic-level auto-chain runs at the end), so mark the task `done` and continue the epic loop.
- If `02-impl.json` exists with `status: "too_big_proposal"` → halt with the prior `payload.reason` and `payload.suggested_split`; suggest `/001-plan --resplit ${TASK_ID}`.
- If `02-impl.json` exists with `status: "blocked"` → halt with the prior blockers summary from `payload.reason`.
<!-- FREEZE:IF require_plan_approval -->
- If `02X-plan.json` artifacts exist (Phase 1.5 plan-only history) but no `02-impl.json` → resume at Phase 1.5: re-present the most recent plan to the user via `AskUserQuestion(Approve / Iterate / Cancel)` (same wording as the original Phase 1.5 Step 2). Branch on the user's choice:
  - **Approve** → record the re-presented plan path and continue to Phase 2.
  - **Iterate** → collect verbatim feedback and re-dispatch the implementer in `plan-only` mode with `payload.user_feedback` set; the new plan is written to the next-letter artifact (e.g. `02c-plan.json`). Then re-present (loop).
  - **Cancel** → set `epic_outcome: cancelled` and exit; the orchestrator's cleanup releases the task (and, in epic mode, epic) lock via the `finally` block.

  Do not re-dispatch a fresh plan unless the user picks **Iterate**.
<!-- FREEZE:ELSE -->
- If `02X-plan.json` artifacts exist but `require_plan_approval: false` is now active → ignore them (stale from a prior config). Continue as if only `01-plan.json` were present (run Phase 1 → Phase 2 directly).
<!-- FREEZE:ENDIF -->
- If only `01-plan.json` exists (or no `NN-*.json` files at all) → run the per-task flow normally (Phase 1 → [Phase 1.5 plan checkpoint if `require_plan_approval: true`] → Phase 2).

In all "resume" paths above, the task status in `epic-{id}-tasks.yaml` is set to `in_progress` (idempotent re-set; no-op if already `in_progress`). On any halt path inside Phase 0.5, the Task lock acquired in Phase 0 MUST be released via `rm -rf "$LOCK_DIR"` before exit.

### Phase 1 — Branch

**Branch model.** One branch per **epic** (not per task). The branch is created once at the start of the `/002-implement` invocation (epic-mode outer Phase 1, or task-mode first-task entry) and reused for every task in the epic. Each task contributes one or more commits on the same branch (impl commit from the implementer; subsequent verify-fix and review-fix commits from the feedback-implementer during `/003` and `/004` self-heal). The merge happens once at epic close via `/006-merge <epic-id>`.

**Branch handling dispatch.** Read `allow_commit_to_main` from the YAML toggle block. The toggle determines whether `branch_name_pattern` is even consulted:

- If `allow_commit_to_main: true` (solo preset) → SKIP branch creation entirely. Do NOT read `branch_name_pattern`. Implementer + feedback-implementer commit directly to `main` (or the configured default branch). Jump to Phase 1.5.
- If `allow_commit_to_main: false` (default) → read `branch_name_pattern` and compute the **epic branch** name as described below, then check out it (or create from base if it does not exist).

The remainder of this section applies ONLY when `allow_commit_to_main: false`:

- Read `branch_name_pattern` from the YAML toggle block in `.claude/ruleset/git-workflow.md`. Default: <!-- FREEZE:VAL branch_name_pattern -->`epic/{epic_id}-{slug}`<!-- FREEZE:ENDVAL -->. Recognised substitution keys: `{epic_id}`, `{slug}`, `{ticket_id}`.
  1. Substitute `{epic_id}` with the resolved epic id (e.g. `E-003`).
  2. **Resolve `{slug}`** — read the epic entry from `docs/planning/epics.yaml`. Prefer the explicit `slug:` field if present; otherwise derive from `title:` via kebab-case (lowercase, strip non-alphanumerics, collapse runs of `-`). Example: title `"Subscription cancellation"` → slug `subscription-cancellation`. If the derived slug is empty (title is non-Latin / pure punctuation), abort: `Cannot derive {slug} for epic <epic-id> from title "<...>". Add an explicit slug: field to the epic entry in epics.yaml.`
<!-- FREEZE:IF require_ticket_reference -->
  3. **Resolve `{ticket_id}`** (only required when the pattern contains the placeholder; enterprise default `epic/{ticket_id}/{epic_id}-{slug}`):
     a. Read `epic.cm_ticket` from the matching epic entry in `epics.yaml`.
     b. If absent AND the pattern contains `{ticket_id}`:
        - If `git-workflow.md.require_ticket_reference: true` → ABORT with: `Epic E-NNN has no cm_ticket. Add one via /001-plan or edit epics.yaml. (Enterprise preset requires CM ticket per epic.)`
        - Else → substitute `{ticket_id}` with the empty string and emit a visible warning.
     c. **Validate against `ticket_prefixes`** from `git-workflow.md` (if the key is present): the resolved `<id>` must start with one of the configured prefixes (e.g. `CHG-`, `CM-`, `JIRA-`, `INC-`). Reject anything starting with `E-` or `T-` — the plugin's own id namespace is reserved and must never be reused as a ticket id. On mismatch → ABORT with the resolved id, the allowed prefixes, and the source (epic) from which the id was read.
<!-- FREEZE:ENDIF -->
- Determine the default base branch (`main` unless `stack.yaml.paths.default_branch` overrides).
- **Epic branch check.** Run `git show-ref --verify --quiet refs/heads/<computed-branch-name>`. Two cases:
  - **Branch exists** → this is a **resume** (a prior `/002-implement <epic-id>` run created it; later tasks reuse it). Run `git checkout <computed-branch-name>`. Do NOT pull from base — that would drag in main-branch changes mid-epic and risk conflicts with the in-progress epic work; rebases against base are owned by the user before opening the PR. Skip the `git checkout -b` step. Continue at Phase 1.5.
  - **Branch does NOT exist** → this is a **fresh epic start**. Run `git checkout <base>` then `git pull --ff-only` to sync. Then create and check out the epic branch: `git checkout -b <computed-branch-name>`.
- The branch persists across the entire epic loop. Subsequent tasks in the same epic loop iteration find the branch already checked out (HEAD on the epic branch) and skip both the create and the checkout step — they simply commit on top.

### Phase 1.5 — Plan checkpoint (plan-only implementer dispatch + user approval)

<!-- FREEZE:IF require_plan_approval -->

The plan checkpoint is the human-in-the-loop gate between branch creation and full TDD execution. It restores the sielappkowo "Present plan, iterate until accepted" discipline inside the crumbs JSON-artifact contract.

This phase runs only when `require_plan_approval: true` in `.claude/ruleset/git-workflow.md`. When the toggle is `false` (default for solo/small-team/oss), Phase 1.5 is skipped entirely and control jumps to Phase 2 (full-TDD dispatch).

**Goal.** Before any RED test is written or any production code is touched, the implementer produces a written plan (files to touch + RED test sketch + GREEN shape + REFACTOR notes), the user reviews it, and the user either **Approves**, requests **Iterate** (with feedback), or **Cancels**. Approval is the trigger for Phase 2.

#### Step 1 — Dispatch implementer in plan-only mode (phase `impl-plan`)

Use the **Task tool** with `subagent_type: "implementer"`. Inject everything that Phase 2 would normally inject (task YAML, Business scenarios verbatim, ruleset SUBSET via `scripts/inject-ruleset.sh`, `stack.yaml.extras`, prior history) PLUS a header:

```
--- mode ---
phase: impl-plan
```

In plan-only mode (phase `impl-plan`) the implementer does **NOT** write code, does **NOT** create or modify any test, does **NOT** commit, and does **NOT** touch the working tree. It only produces a plan artifact.

The plan artifact contract:

- **Path.** `.claude/runs/{epic_id}/{task_id}/02<letter>-plan.json`, where `<letter>` increments per iteration: first dispatch writes `02a-plan.json`, an Iterate response writes `02b-plan.json`, then `02c-plan.json`, etc. Append-only — never overwrite a prior iteration.
- **Schema.** Conforms to `schemas/run-phase.schema.json` with `phase: "impl-plan"`, `agent: "implementer"`, `status: "ok"`. The `phase` value `impl-plan` is itself the discriminator — there is no `sub_mode` field. Required `payload` fields (per the schema's `impl-plan` branch):
  - `payload.iteration: <integer>` — 1-based iteration counter (1 for `02a-plan.json`, 2 for `02b-plan.json`, 3 for `02c-plan.json`, …). Filename letter and iteration integer are kept in sync by the orchestrator; the schema only validates the integer.
  - `payload.files_to_touch: [<string>, …]` — array of file paths the implementer intends to create or edit. One path per element. (Per-file intent is communicated via the per-file `red_sketch`/`green_shape` prose, not as a structured per-element record.)
  - `payload.red_sketch: <string>` — the failing Domain-test sketch, scoped to the first acceptance criterion on the task. Includes the World wiring, the Step library calls, and the assertion that will go red.
  - `payload.green_shape: <string>` — the minimal production-code shape that will make RED go green (interfaces, function signatures, data flow). NO implementation bodies.
  - `payload.refactor_notes: <string>` — known refactor moves anticipated after GREEN (extract function, push concept into domain model, etc.). Empty string is acceptable for trivial tasks.
  - `payload.user_feedback: <string>` — OPTIONAL. For iterations 2 and later, set to the verbatim feedback text from the previous `AskUserQuestion` Iterate option. Omit on iteration 1.

  Additional non-schema-required fields the orchestrator surfaces (kept under `payload` for audit but not required by the schema):
  - `payload.atdd_spec_shape: <string>` — how the single ATDD spec will be authored after Domain-tests are green (path, happy-path Step-library calls, World wiring).
  - `payload.open_questions: [<string>, …]` — any ambiguity the user should resolve before approval. Empty array is the happy case.

- **Status semantics.** `ok` means "plan produced, awaiting user decision". `too_big_proposal` and `blocked` are valid `impl-plan` outcomes too — the implementer may decide during planning that the task is unsplittable-but-too-large, or that a prerequisite is missing. Both halt the per-task flow exactly as in Phase 3.

#### Step 2 — Present plan to user via `AskUserQuestion`

After the plan artifact is written, validate it against the schema (the `phase: "impl-plan"` branch enforces the required payload fields above) and then call the `AskUserQuestion` tool with:

- **Question.** A short prompt referencing the task id and the current plan iteration, e.g. `Task T-014 plan iteration 1 (02a-plan.json): approve, iterate, or cancel?`
- **Header.** `Plan checkpoint`.
- **Multi-select.** `false` (single choice).
- **Options.**
  1. `label: "Approve"`, `description: "Proceed to Phase 2 (full TDD) with this plan as input context."`
  2. `label: "Iterate"`, `description: "Provide feedback; the implementer re-plans (next letter, e.g. 02b-plan.json)."`
  3. `label: "Cancel"`, `description: "Abort this task. Release lock. In epic mode, the whole epic loop halts."`

Beneath the question, surface a compact rendering of the plan payload (the user reads JSON poorly; flatten it into bullets):

```
Iteration: <int> (file: 02<letter>-plan.json)
Files to touch:
  - <path>
  - ...
RED sketch: <one-paragraph summary>
GREEN shape: <one-paragraph summary>
REFACTOR notes: <one-paragraph or "none">
ATDD spec shape: <one-paragraph summary>
Open questions: <bullet list or "none">
```

If `payload.open_questions` is non-empty, the user is strongly encouraged to pick **Iterate** (the plan is not yet ready). Do not block the Approve option, but flag the open questions in the prompt.

#### Step 3 — Branch on user choice

- **Approve** → record the approved plan path (e.g. `02b-plan.json`) for Phase 2 to inject. Continue to Phase 2.
- **Iterate** → collect the user's free-form feedback (via a follow-up `AskUserQuestion` with a single `open` option, or via the `additional` field if the harness supports it). Re-dispatch the implementer in plan-only mode (phase `impl-plan`) with `payload.user_feedback` set to the verbatim feedback text and `payload.iteration` incremented. The new plan is written to the next letter (`02b-plan.json`, then `02c-plan.json`, …). Re-present (Step 2). The iteration counter has no hard cap, but emit a visible warning to the user after every 3 plan iterations: `3 plan iterations and counting — consider /001-plan --resplit ${TASK_ID} or accepting the current plan.`
- **Cancel** → halt the per-task flow:
  - Revert task `status` from `in_progress` back to `pending` in `epic-{id}-tasks.yaml`.
  - Set `epic_outcome: cancelled` and exit; the orchestrator's `finally` cleanup releases the task lock (and, in epic mode, the epic lock).
  - Print: `Task <task-id> cancelled at plan checkpoint. Status reverted to pending. Re-run /002-implement to resume.`
  - Print as the final summary line: `epic_outcome: cancelled`.

The approved plan path is the SINGLE input passed to Phase 2 below (as a `--- approved plan ---` block alongside the existing injection set). Phase 2 does not re-plan; it executes.

<!-- FREEZE:ELSE -->

**Phase 1.5 is disabled** by the active `require_plan_approval: false` toggle. The implementer is dispatched directly in full-TDD mode (Phase 2 below) with no plan-only stage and no `02X-plan.json` artifacts. The Phase 2 injection set omits the `--- approved plan ---` block; the implementer authors its own internal plan as part of the TDD discipline. Cancel/Iterate user paths do not exist under this configuration; the epic loop iterates every pending task to completion or the first non-recoverable halt (`too_big_proposal`, `blocked`, verify/review loop-limit).

<!-- FREEZE:ENDIF -->

### Phase 2 — Dispatch implementer subagent (full TDD)

Use the **Task tool** with `subagent_type: "implementer"`. Inject the following into the subagent prompt body (verbatim, no `@`-includes):

1. **Task entry (YAML)** — the entire YAML entry for the task as it appears in `epic-{id}-tasks.yaml`. Include `id`, `slug`, `title`, `status`, `acceptance_criteria`, `atdd_spec`, `rules_in_scope`, `depends_on`, `notes`, and any other fields present. The `acceptance_criteria` array is the authoritative DoD bar — the implementer writes Domain-tests asserting each criterion.
2. **Business scenarios (epic-level)** — paste the entire `business_scenarios` Gherkin block-scalar from the matching epic entry in `epics.yaml` verbatim under a header `--- Business Scenarios (epic-level) ---`. The implementer uses this to author the task's `atdd_spec` happy-path file; it is not a per-task DoD source (the DoD bar is `acceptance_criteria` on the task).
3. **Verbatim ruleset SUBSET** — inject the ruleset **subset** via `scripts/inject-ruleset.sh --rules <comma-separated-slugs>` where slugs = the planner's `01-plan.json.payload.rules_in_scope` for this task ∪ the mandatory core `{architecture, testing, code-style, git-workflow}`. Capture the script's stdout via the Bash tool and inline it verbatim into the implementer's prompt. The script handles path resolution (honours `paths.ruleset` from `stack.yaml`, falls back to `.claude/ruleset/`), alphabetical ordering of `*.md` files, the `--- <basename> ---` header per file, and the subset filter (mandatory core is always included regardless of `--rules`). Do not re-implement the read+concatenate logic inline. Do not summarise, do not omit any rule in the subset. The remaining rules outside the subset are the reviewer's concern (`/004`), not the implementer's — they are the holistic gate that sweeps the full 18.
4. **`stack.yaml.extras`** — paste the `extras` mapping verbatim under a header `--- stack.yaml.extras ---`. This is the escape hatch for stack-specific quirks (e.g. `bash_buffering_warning`, `user_ping_interval_minutes`).
5. **Approved plan** (only when `require_plan_approval: true`) — paste the contents of the approved plan artifact (e.g. `02b-plan.json` from Phase 1.5) verbatim under a header `--- approved plan ---`. The implementer treats this as binding: file set, RED sketch, GREEN shape, REFACTOR notes, and ATDD spec shape are pre-agreed with the user. Deviations are allowed only when the implementer hits an issue the plan missed; in that case the implementer emits `status: blocked` with a `payload.reason` describing the gap, and the flow halts back to the user. When `require_plan_approval: false` (default), this item is **omitted** from the injection set; the implementer authors its own internal plan as part of the TDD discipline (no prior `02X-plan.json` artifact exists).
6. **Output contract** — instruct the implementer to write its result to `.claude/runs/{epic_id}/{task_id}/02-impl.json`, validated against `schemas/run-phase.schema.json`. The top-level `status` field must be one of `ok`, `too_big_proposal`, `blocked`. Required `payload` keys vary by status:
   - `ok` → `commit_sha`, `files_changed`, `domain_tests_added`, `atdd_spec_path`.
   - `too_big_proposal` → `reason` (prose), `suggested_split` (array of draft task titles, 2..n entries).
   - `blocked` → `reason` (prose), optional `suggested_follow_up`.
7. **Prior history** — paste any pre-existing artifacts under `.claude/runs/{epic_id}/{task_id}/` (e.g. `01-plan.json` from `/001-plan` and the approved `02<letter>-plan.json`) verbatim under headers `--- Prior phase: 01-plan.json ---` etc. Subagents are append-only readers of the runs history.

**Commit context (preset-driven).** Beyond items 1–7, the following commit-related context blocks are appended to the implementer prompt when (and only when) the corresponding `git-workflow.md` toggle is active. Each block is emitted as an unnumbered bullet so that pruning under any preset combination cannot leave an orphan header in a numbered list:

<!-- FREEZE:IF require_ticket_reference -->
- **Commit-msg context** — under a header `--- commit-msg context ---`, pass the values needed for the implementer to compose a compliant commit subject (per enterprise `^... \[TICKET-ID\]$` pattern from `git-workflow.md`):
  - `cm_ticket: <resolved-ticket-id-or-null>` — the value resolved in Phase 1 (task `cm_ticket`, falling back to epic `cm_ticket`, or `null` if neither was set and the pattern did not require one).
  - `commit_subject_pattern: <from git-workflow.md commit-msg toggle>` — verbatim regex/string from the toggle block (e.g. `^(feat|fix|chore|refactor|test|docs)(\([a-z0-9-]+\))?: .+ \[[A-Z]+-[0-9]+\]$`).
  The implementer is responsible for including the ticket id in the commit subject when one is present; the main thread is responsible for surfacing it.
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_signed_commits -->
- **Commit signing flag** — under a header `--- commit policy ---`, pass `require_signed_commits: true`. The implementer commits with `-S` (GPG/SSH signing).
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_dco_signoff -->
- **Commit DCO sign-off flag** — under a header `--- commit policy ---`, pass `require_dco_signoff: true`. The implementer commits with `-s` (appends a `Signed-off-by: Name <email>` trailer). MUST be applied on the ORIGINAL commit — amending later to add `-s` is forbidden by the no-amend rule, and `/006-merge` enforces the trailer in its Phase 0 pre-flight BEFORE `git push`.
<!-- FREEZE:ENDIF -->

If none of the three commit-context toggles is active for the active preset (e.g. `solo`), no commit-context block is emitted — the implementer relies on the generic Conventional-Commits convention from `git-workflow.md`.

The implementer is expected to:

- Execute the approved plan from Phase 1.5. The plan is binding for file scope, RED sketch, GREEN shape, and ATDD spec shape.
- Run the **TDD entry-point** loop per `.claude/ruleset/testing.md`: Domain-test RED → minimal production code GREEN → REFACTOR. Repeat per acceptance until the task is fully green.
- Produce **one ATDD spec** at `tests/atdd/<slug>.spec.ts` (path may differ per `stack.yaml.paths.atdd_dir`). The spec is **authored only** during the task — it is **not executed per-task**. It will be executed at epic close-out.
- Produce **one or more Domain-tests** covering happy path + edge cases.
- Make **one commit** on the epic branch (or on `main` if the solo preset is active). The commit covers only this task's files. Commit message follows `.claude/ruleset/git-workflow.md` conventions (Conventional Commits by default); the scope should include the task id, e.g. `feat(billing): cancel subscription (T-014)`. Never amend. Each subsequent task's implementer commit stacks on top of the previous one — the epic branch grows linearly through the epic loop.
<!-- FREEZE:IF require_signed_commits -->
- Sign the commit if `require_signed_commits: true` is set in the toggle block.
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_dco_signoff -->
- Sign-off the commit (`git commit -s`) if `require_dco_signoff: true` is set. The sign-off MUST be applied on the original commit; amending to add it later is forbidden.
<!-- FREEZE:ENDIF -->
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
  Set the task `status` back to `pending` in `epic-{id}-tasks.yaml`. Halt; do **not** proceed to verify or review. In epic mode, also halt the epic loop and emit `epic_outcome: halted_too_big` as the final summary line. Note: the planner re-split (`/001-plan --resplit`) is responsible for archiving the pending task's stub `01-plan.json` if it exists.

- **`status: "blocked"`** — implementer hit a blocker it cannot resolve (missing dependency, ambiguous scenario, external decision required). Print `payload.reason` verbatim and the suggested follow-up if present. Leave task `status: in_progress` so the user can clear it manually after resolution. Halt. In epic mode, also halt the epic loop and emit `epic_outcome: halted_blocked` as the final summary line.

- **`status: "ok"`** — implementation green. Continue to Phase 4 (task mode) or directly to Phase 6 task-status-update + loop-continue (epic mode — per-task verify/review are skipped per the epic-mode skip table above; `/003`/`/004` run once at epic close-out).

### Phase 4 — Auto-invoke /003-verify-dod (task mode only)

This phase runs **only in task mode**. See the epic-mode skip table above — Phase 4 is skipped per-task in epic mode (the epic-level auto-chain runs `/003-verify-dod <epic-id>` once after every task is `done`).

If `auto_invoke_verify` is **not** `false` (default: `true`):

1. Spawn `/003-verify-dod` against `<task-id>`. The verifier runs all `stack.yaml.gates` plus rule-based DoD checks. `/003`'s own Phase 2/3 self-heal loop (max 3 iterations) is owned by `/003`, not this command.
2. After completion, read `.claude/runs/{epic_id}/{task_id}/03-verify.json` (or the last `03X-verify.json` iteration if `/003` self-healed) and validate against the schema.
3. Branch on `status`:
   - **`status: "ok"`** → continue to Phase 5.
   - **`status: "fail"`** → `/003`'s self-heal cap was exhausted. Halt the per-task flow with the verifier findings; surface the path of the last failing artifact. Leave task `status: in_progress`. (Task mode only; in epic mode this branch is reachable instead at the epic-level auto-chain and emits `epic_outcome: halted_verify` per the epic-mode discriminator section.)

If `auto_invoke_verify: false`, skip Phase 4 entirely and inform the user: `Auto-verify disabled by toggle. Run /003-verify-dod <task-id> manually.`

### Phase 5 — Auto-invoke /004-code-review (task mode only)

This phase runs **only in task mode**. See the epic-mode skip table above — Phase 5 is skipped per-task in epic mode (the epic-level auto-chain runs `/004-code-review <epic-id>` once after `/003` returns ok).

If `auto_invoke_review` is **not** `false` (default: `true`):

1. Spawn `/004-code-review` against `<task-id>`. The reviewer reads the verbatim-injected ruleset, the diff, and the runs history. `/004`'s own Phase 2/3 self-heal loop (max 3 iterations) is owned by `/004`, not this command.
2. After completion, read `.claude/runs/{epic_id}/{task_id}/04-review.json` (or the last `04X-review.json` iteration if `/004` self-healed) and validate against the schema.
3. Branch on `status`:
   - **`status: "ok"`** → continue to Phase 6.
   - **`status: "fail"`** → `/004`'s self-heal cap was exhausted. Halt the per-task flow with the reviewer findings; surface the path of the last failing artifact. Leave task `status: in_progress`. (Task mode only; in epic mode this branch is reachable instead at the epic-level auto-chain and emits `epic_outcome: halted_review` per the epic-mode discriminator section.)

If `auto_invoke_review: false`, skip Phase 5 and inform the user: `Auto-review disabled by toggle. Run /004-code-review <task-id> manually.`

### Phase 6 — Close task (task mode: propose merge; epic mode: loop)

Reached only when both verify and review are `ok` (or their toggles disabled the auto-invoke).

- Set task `status: done` in `epic-{id}-tasks.yaml`. Update any `summary.by_status` counter if the file maintains one.
- Release the task lock (`rm -rf .claude/runs/.lock-${EPIC_ID}-${TASK_ID}`).
- **Task mode**:
<!-- FREEZE:IF pr_required -->
  - Print a one-liner to the user:
    ```
    Task <task-id> complete. Open MR? Run /006-merge <task-id>
    ```
  - **Do NOT auto-invoke `/006-merge`.** Merging is always user-triggered to preserve a human checkpoint before the PR/MR lands.
<!-- FREEZE:ELSE -->
  - Print a one-liner to the user:
    ```
    Task <task-id> complete and on main. /006-merge is a no-op for the solo preset.
    ```
<!-- FREEZE:ENDIF -->
- **Epic mode**: do not print merge guidance. Return control to the epic loop, which will pick the next eligible pending task (Phase 0) or, if none remain, run the epic-level auto-chain (`/003-verify-dod` → optional `/004-code-review`).

## Lock semantics

Two lock granularities coexist and are **orthogonal** — they live in different directories and never collide:

- **Epic lock** (`.claude/runs/.lock-<epic_id>/`) — acquired at the start of epic mode, held across every per-task iteration AND across the post-loop `/003` / `/004` auto-chain, released at the end (success or any halt branch). Task mode does NOT acquire the epic lock.
- **Task lock** (`.claude/runs/.lock-<epic_id>-<task_id>/`) — acquired inside Phase 0 of the per-task flow, held until Phase 6 (success) or any halt branch. Both modes use the task lock.

Because the lock directory names differ structurally (`<epic>` vs `<epic>-<task>`), a running epic and an ad-hoc task-mode invocation of the same task id will fail-fast on the **task** lock at Phase 0, not the epic lock — the task lock is the narrowest concurrency guard and is checked first inside Phase 0. The epic lock guards the higher-order semantic ("an epic batch is in flight; do not start another epic batch").

Acquisition uses the same `mkdir`-then-write-info atomic pattern as the task lock (Phase 0). Exit code `5` is reserved for "already running" on either lock so callers can distinguish concurrency from other failures.

**Stale-lock recovery.** If the orchestrator crashes (host crash, harness terminated), the lock directory persists. The error message at acquisition points the user at the exact path; manual `rm -rf <lock-dir>` is required. Do NOT auto-clean stale locks — silent reclamation hides bugs and corrupts concurrent runs.

## Toggle precedence

The YAML toggle block at the top of `.claude/ruleset/git-workflow.md` is the single source of truth for orchestration behaviour. It overrides every default in this command. Recognised keys:

```yaml
auto_invoke_verify: true | false       # default true
auto_invoke_review: true | false       # default true
allow_commit_to_main: true | false     # default false
pr_required: true | false              # default true
<!-- FREEZE:IF require_signed_commits -->
require_signed_commits: true | false   # default false
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_dco_signoff -->
require_dco_signoff: true | false      # default false (true for oss preset)
<!-- FREEZE:ENDIF -->
branch_name_pattern: "epic/{epic_id}-{slug}"
```

Notes:
- Missing block or missing key → defaults apply (no warning).
- The toggle block is parsed once at the start of the run and held for the entire batch; mid-run edits are ignored.
- The chosen `team_preset` recorded in `.claude/stack.yaml` is informational only — this command never reads it. Behaviour is driven solely by the toggle block, which the preset wrote at bootstrap.

### Preset → toggle mapping (informational)

The active preset populates the toggle block at bootstrap as follows. After bootstrap the project owns the file and may edit freely; the mapping below is a reference for the defaults of THIS preset, not a runtime contract.

<!-- FREEZE:IF preset == "solo" -->
| Toggle                    | solo  |
|---------------------------|-------|
| `auto_invoke_verify`      | true  |
| `auto_invoke_review`      | false |
| `allow_commit_to_main`    | true  |
| `pr_required`             | false |
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF preset == "small-team" -->
| Toggle                    | small-team |
|---------------------------|------------|
| `auto_invoke_verify`      | true       |
| `auto_invoke_review`      | true       |
| `allow_commit_to_main`    | false      |
| `pr_required`             | true       |
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF preset == "oss" -->
| Toggle                    | oss   |
|---------------------------|-------|
| `auto_invoke_verify`      | true  |
| `auto_invoke_review`      | true  |
| `allow_commit_to_main`    | false |
| `pr_required`             | true  |
| `require_dco_signoff`     | true  |
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF preset == "enterprise" -->
| Toggle                    | enterprise |
|---------------------------|------------|
| `auto_invoke_verify`      | true       |
| `auto_invoke_review`      | true       |
| `allow_commit_to_main`    | false      |
| `pr_required`             | true       |
| `require_signed_commits`  | true       |
<!-- FREEZE:ENDIF -->

The `branch_name_pattern` is `epic/{epic_id}-{slug}` across all presets unless the project overrides (enterprise typically adds the ticket prefix: `epic/{ticket_id}/{epic_id}-{slug}`).

## Failure modes

- **Bad argument** → abort at mode-dispatch with the usage error (`Argument "<value>" is neither an epic id (E-…) nor a task id (T-…). …`).
- **Task not found** → abort at Phase 0 with the path and id.
- **Epic not found** → abort at the epic-mode pre-flight with the search path.
- **Task already `done`** → task mode aborts; epic mode skips silently and continues the loop.
- **Task already `in_progress`** → both modes abort with the specific message.
- **Schema validation fails** on any of `02X-plan.json`, `02-impl.json`, `03-verify.json`, `04-review.json`, `05X-feedback-impl.json` → halt with the artifact path and the validator error.
- **User picks Cancel at Phase 1.5** → halt; revert task to `pending`; release both locks; epic mode halts the batch.
- **Implementer returns `too_big_proposal`** → halt at Phase 3; revert task to `pending`; epic mode halts the batch.
- **Implementer returns `blocked`** → halt at Phase 3; leave task `in_progress`; epic mode halts the batch.
- **Verify fails after `/003`'s self-heal cap** → halt at Phase 4 (task mode) or at the epic-level auto-chain (epic mode); leave task `in_progress`.
- **Review fails after `/004`'s self-heal cap** → halt at Phase 5 (task mode) or at the epic-level auto-chain (epic mode); leave task `in_progress`.
- **Subagent invocation error** (missing file, tool failure, ruleset directory absent) → halt with the underlying error and the offending path. Do not retry silently.
- **Branch creation fails** (dirty working tree, base branch behind, etc.) → halt at Phase 1 with the git error verbatim. Do not force any operation.

## Discipline

- Task `status` transitions:
  - `pending`/`blocked` → `in_progress` at Phase 0 start.
  - `in_progress` → `done` only on full success at Phase 6.
  - `in_progress` → `pending` on `too_big_proposal` (Phase 3) or on user **Cancel** at Phase 1.5.
  - `in_progress` stays `in_progress` on any hard halt — the user clears it manually once the underlying issue is resolved.
- **Plan checkpoint is gated by `require_plan_approval`.** When `true`, Phase 1.5 runs before Phase 2 and the user must Approve/Iterate/Cancel each task's plan; the point is to catch wrong assumptions before they become commits (sielappkowo-style). When `false` (default), Phase 1.5 is skipped entirely — the implementer is dispatched in full-TDD mode directly and the epic loop iterates every task to completion without prompting.
- **Plan artifacts are append-only.** `02a-plan.json`, `02b-plan.json`, … are never overwritten. If the user picks Iterate, the next letter is written; the previous letter remains as audit history.
- **Never amend commits.** The implementer makes one commit per task; self-heal feedback rounds inside `/003` and `/004` produce additional commits stacked on top of the epic branch (one commit per fix iteration).
- **Never force-push.** If history needs cleanup, leave it for `/006-merge` (which may squash on PR creation per `git-workflow.md`).
<!-- FREEZE:IF require_signed_commits -->
- **Honour `require_signed_commits`** from the chosen preset. If true, every commit (implementer + feedback rounds) is signed.
<!-- FREEZE:ENDIF -->
- **Honour `branch_name_pattern`.** Do not improvise branch names; the pattern is the contract.
- **Filesystem-only subagent comms.** Never rely on in-memory state between subagent invocations — the main thread reads artifacts from `.claude/runs/{epic_id}/{task_id}/` after each subagent returns. Ruleset content is verbatim-injected into the prompt body, never via `@`-include (per CONTEXT.md "Ruleset injection").
- **Append-only runs history.** Never overwrite or delete prior phase artifacts within a task run. Plan iterations get letter suffixes (`02a`, `02b`, `02c`). Self-heal rounds inside `/003` and `/004` get letter suffixes (`03b`, `03c`, `04b`, `04c`) and are governed by those commands.
- **One commit per stage.** The implementer produces one commit per task (impl stage). Self-heal rounds inside `/003`/`/004` each add one commit per fix iteration (`fix(verify): T-NNN <summary>`, `fix(review): T-NNN <summary>`). All commits stack on the epic branch; no amend, no squash. Squashing (if desired) is a `/006-merge` concern, governed by `git-workflow.md`. Epic branch grows monotonically through the whole epic loop.
- **Zero tolerance on Findings.** Any finding from `/003` or `/004` blocks DoD. No severity tiers, no overrides. The self-heal loops inside those commands address every finding; they never argue with them.

## Vocabulary discipline

Mirror `CONTEXT.md` exactly. Use only these terms when communicating with the user or writing artifacts:

- **TDD entry-point** — both planning and implementation start from a failing test. No production code without a prior red test.
- **Domain-test** — multi-class no-infra test in the inner loop (Vertex Testing). Drives RED-GREEN-REFACTOR.
- **ATDD spec** — executable form of a Business scenario, one per task, written during the task, executed only at epic close-out.
- **Business scenario** — the Gherkin block in `epics.yaml`. Source of truth for what the user-visible behaviour must be.
- **Step library** — domain-oriented abstraction shared across Domain-tests and ATDD specs; one function per scenario verb.
- **World** — execution context injected into a Step library function (`DomainWorld` for Domain-tests, `BrowserWorld` / `DeviceWorld` for ATDD specs and Journeys).
- **Status** — two namespaces exist and MUST NOT be confused:
  - **Task status** (in `epic-{id}-tasks.yaml`): `pending | in_progress | blocked | done`. Drives the per-task lifecycle and the epic-mode iteration filter.
  - **Artifact status** (in `.claude/runs/{epic_id}/{task_id}/NN-*.json`, per `schemas/run-phase.schema.json`): `ok | fail | blocked | too_big_proposal`. Drives the orchestrator's branch decisions inside each phase.
  - Both namespaces use `blocked`, but the semantics differ: task `blocked` means the task itself cannot proceed (external dependency, ambiguous scenario, etc.); artifact `blocked` means the agent producing the artifact could not complete its work in this invocation.
  - Never use `todo`, `wip`, `complete`, `partial`.
- **Finding** — any violation surfaced by `/003` or `/004`. Zero tolerance; no severity tiers.

Do not introduce synonyms (no "unit test", no "acceptance criteria", no "blocker/non-blocker", no "wip"). If you find yourself reaching for one, re-read the relevant CONTEXT.md entry.

## Subagent chain summary

### Epic mode

```
/002-implement <epic-id>
   │
   ├─ acquire epic lock (.claude/runs/.lock-<epic_id>/)
   ├─ FOR EACH eligible pending task in dependency order:
   │     ├─ Phase 0     pre-flight + acquire task lock (.lock-<epic_id>-<task_id>/)
   │     ├─ Phase 0.5   resume detection
   │     ├─ Phase 1     branch (or skip if allow_commit_to_main)
   │     ├─ Phase 1.5   plan-only implementer → 02a-plan.json
   │     │              AskUserQuestion(Approve / Iterate / Cancel)
   │     │              Iterate → re-dispatch → 02b/02c/… ; Cancel → halt
   │     ├─ Phase 2     implementer (full TDD) → 02-impl.json
   │     ├─ Phase 3     branch on status (ok → continue; too_big/blocked → halt)
   │     └─ Phase 6     status=done; release task lock; loop
   │
   ├─ auto-invoke /003-verify-dod <epic-id>   (no user prompt)
   │     on fail → halt epic, surface findings
   │
   ├─ auto-invoke /004-code-review <epic-id>  (gated by auto_invoke_review)
   │     on fail → halt epic, surface findings
   │
   └─ release epic lock; print epic-complete one-liner
```

### Task mode

```
/002-implement <task-id>
   │
   ├─ Phase 0     pre-flight + acquire task lock (.lock-<epic_id>-<task_id>/)
   ├─ Phase 0.5   resume detection
   ├─ Phase 1     branch (or skip if allow_commit_to_main)
   ├─ Phase 1.5   plan-only implementer → 02a-plan.json
   │              AskUserQuestion(Approve / Iterate / Cancel)
   ├─ Phase 2     implementer (full TDD) → 02-impl.json
   ├─ Phase 3     branch on status
   ├─ Phase 4     /003-verify-dod (its own self-heal loop owned by /003)
   ├─ Phase 5     /004-code-review (its own self-heal loop owned by /004)
   └─ Phase 6     status=done; release task lock; print /006-merge suggestion
```

Each subagent type lives in `agents/` (plugin-owned, not project-owned). The chain is iterative (`planner` → `implementer (plan-only)` → user → `implementer (full)` → `verifier` → `reviewer` → `feedback-implementer` → back to `verifier`), not linear. This command owns one task's traversal of that chain in task mode, and the whole-epic traversal in epic mode.

## Worked example — epic mode

Given epic `E-003` with three pending tasks `T-014`, `T-015`, `T-016` (each depending on the previous):

1. **Pre-flight** — `/002-implement E-003` locates `docs/planning/epic-003-tasks.yaml`. Acquires `.claude/runs/.lock-E-003/`. Selects `T-014` as the first eligible pending task.
2. **T-014 per-task flow** — Phase 0 → Phase 6. Plan checkpoint dispatches `implementer` in `plan-only`; writes `02a-plan.json`. User picks **Iterate** with feedback "use SwiftData over Core Data". Implementer re-plans → `02b-plan.json`. User picks **Approve**. Phase 2 implementer runs full TDD, commits, writes `02-impl.json` (`status: ok`). Phase 4/5 are skipped in epic mode. Phase 6 marks T-014 `done`, releases its task lock, returns to loop.
3. **T-015 per-task flow** — same shape. Plan approved on first iteration.
4. **T-016 per-task flow** — same shape. Plan approved.
5. **Epic auto-chain** — all three tasks `done`. Auto-invoke `/003-verify-dod E-003`. The verifier runs `stack.yaml.gates` across the epic diff. One finding — `/003`'s Phase 2 self-heal dispatches a `feedback-implementer`, fixes, Phase 3 re-verifies → `ok`. Return to this command. `auto_invoke_review: true` → auto-invoke `/004-code-review E-003`. Reviewer returns `ok` on first pass.
6. **Done** — release epic lock. Print: `Epic E-003 complete. /003 ok (1 self-heal round). /004 ok. Run /006-merge E-003 to open the MR.`

## Worked example — task mode

Given task `T-014` belonging to epic `E-003`:

1. **Phase 0** — `/002-implement T-014` locates `docs/planning/epic-003-tasks.yaml`, finds entry `id: T-014, status: pending, slug: cancel-subscription, acceptance_criteria: ["SubscriptionService.cancel(...) persists status=cancelled and emits SubscriptionCancelled event", "Calling cancel on already-cancelled subscription is a no-op"]`. Flips status to `in_progress`. Acquires `.claude/runs/.lock-E-003-T-014/`. Creates `.claude/runs/E-003/T-014/`.
2. **Phase 1** — Branch pattern `epic/{epic_id}-{slug}` resolves to `epic/E-003-subscription-cancellation` (slug derived from epic title "Subscription cancellation"). Branch does not exist → checked out from `main` as fresh epic start. (If the user is re-running `/002-implement E-003` to resume an interrupted batch, the branch already exists → reuse without pulling base.)
3. **Phase 1.5** — `implementer` (plan-only) writes `02a-plan.json` with file list, RED sketch, GREEN shape, REFACTOR notes, ATDD spec shape. User picks **Approve**.
4. **Phase 2** — `implementer` (full) receives task YAML, the Gherkin block for `User cancels subscription`, ruleset subset verbatim, `stack.yaml.extras`, and the approved `02a-plan.json`. Writes Domain-tests in `tests/domain/cancel-subscription.test.ts`, production code in `src/billing/cancel.ts`, an ATDD spec in `tests/atdd/cancel-subscription.spec.ts`, commits with message `feat(billing): cancel subscription (T-014)`, writes `02-impl.json` with `status: ok`.
5. **Phase 4** — `/003-verify-dod T-014` runs `stack.yaml.gates`. All pass → `03-verify.json` status `ok`.
6. **Phase 5** — `/004-code-review T-014` reads ruleset + diff. One finding: missing `aria-label` per `accessibility.md`. `/004`'s self-heal loop fixes (`04b-fix.json`, `04c-review.json`) → final `status: ok`.
7. **Phase 6** — Task `status: done`. Release task lock. Print: `Task T-014 complete. Open MR? Run /006-merge T-014`.
