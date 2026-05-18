---
description: Epic-level batch orchestrator. Runs the full /002 → /003 → /004 → /005 chain per task in an epic. Each step is a dedicated subagent.
argument-hint: <epic-id>
---

Drive an entire epic to `done` by iterating every `pending` task in `epic-{id}-tasks.yaml` and running the full subagent chain (`implementer` → `verifier` → `reviewer`, with `feedback-implementer` on fail) for each one. This command is the **conductor**: it spawns subagents, reads their artifacts under `.claude/runs/{epic_id}/{task_id}/`, and decides whether to advance, loop, or halt. It never edits code itself.

This is the batch counterpart of `/002-implement`. Use it when an epic is fully planned and the user wants hands-off execution across all tasks. Use `/002-implement` instead when iterating one task at a time.

Output language for all artifacts and user-facing messages is **English**, regardless of the project's working language.

## Inputs

- **`<epic-id>`** — passed as `$ARGUMENTS` (e.g. `E-007`). Required positional argument. Format: `E-NNN` (uppercase, zero-padded to three digits). If the argument is missing or malformed → abort with: `Usage: /002-auto-implement <epic-id> (e.g. /002-auto-implement E-007).`
- **`docs/planning/epic-{id}-tasks.yaml`** — task list for the epic, where `{id}` is the 3-digit zero-padded epic id (e.g. `epic-001-tasks.yaml`). Iterate only entries with `status: pending`. Skip `done`, `in_progress`, `blocked` silently (they are reported in the pre-flight count, not processed).
- **`docs/planning/epics.yaml`** — Business scenarios for the epic, referenced by each task's `domain_scenarios` field. Loaded once and reused across every per-task subagent dispatch.
- **`.claude/ruleset/*.md`** — all 18 canonical rule files, verbatim-loaded into memory once at the start of the batch. The same content block is injected into every subagent dispatch (`implementer`, `verifier`, `reviewer`, `feedback-implementer`).
- **`.claude/ruleset/git-workflow.md`** — parse the YAML toggle block (same keys as `/002-implement`: `auto_invoke_review`, `auto_invoke_verify`, `allow_commit_to_main`, `pr_required`, `branch_name_pattern`, `require_signed_commits`, `require_dco_signoff`). Toggles apply uniformly to every task in the batch.
- **`.claude/stack.yaml`** — read `extras` (propagated verbatim to all subagents), `paths` (SoT overrides), and `gates` (referenced by the `verifier` subagent).

## Workflow

### Phase 0 — Pre-flight

- **Step 0: resolve epic id from `$ARGUMENTS`.** Parse the epic id (e.g. `E-007`) out of `$ARGUMENTS` and validate it matches `^E-[0-9]{3}$`. On mismatch, emit the usage error from the Inputs section and exit. The orchestrator MUST hold this resolved id as a string and substitute the LITERAL value into the lock path below before invoking the Bash tool — environment variables do not persist across separate Bash tool calls in this harness, so `${EPIC_ID}` in a snippet authored once would be unset on the next invocation.
- **Acquire epic lock (atomic, explicit cleanup).** Before any other pre-flight step, take an exclusive lock on the epic id via `mkdir` (atomic on POSIX). This prevents two terminals from racing on the same `epic-{id}-tasks.yaml` and `.claude/runs/{epic_id}/` tree. The orchestrator substitutes the resolved epic id (from Step 0) into the path string BEFORE invoking the Bash tool. Example, with the literal id `E-007` already substituted:

  ```sh
  # NOTE: the orchestrator writes "E-007" verbatim here — there is no shell variable.
  if ! mkdir ".claude/runs/.lock-E-007" 2>/dev/null; then
      LOCK_INFO=""
      if [ -f ".claude/runs/.lock-E-007/info" ]; then
          LOCK_INFO=" (held by: $(cat ".claude/runs/.lock-E-007/info"))"
      fi
      echo "Error: epic E-007 is already being processed${LOCK_INFO}." >&2
      echo "If you are sure no other process is running, remove .claude/runs/.lock-E-007 and retry." >&2
      exit 5
  fi
  echo "$$@$(hostname) $(date -u +%Y-%m-%dT%H:%M:%SZ)" > ".claude/runs/.lock-E-007/info"
  ```

  Exit code `5` is reserved for the "already running" case so callers can distinguish concurrency from other pre-flight failures.

  **No `trap`-based cleanup.** A `trap` set inside a Bash tool call only lives for the duration of that single invocation; the orchestrator returns to the Claude harness immediately after, and the trap exits — releasing the lock prematurely if it were trap-based. Instead, the lock is held across the entire command run by simply leaving the directory in place, and is removed at the very end:

  - **Successful Phase 2 close-out** — after the final archive step, the orchestrator invokes a final Bash call that runs `rm -rf .claude/runs/.lock-E-007` (literal id substituted again).
  - **Halt paths** (`too_big_proposal`, `blocked`, `loop-limit`, dispatch error, schema validation failure) — the same `rm -rf .claude/runs/.lock-E-007` is invoked from the halt-handling Bash call, in the same step that prints the halt diagnostic. Every halt path MUST explicitly release the lock; do not assume any wrapper does it.

  **Trade-off:** if the orchestrator itself crashes mid-run (host crash, harness terminated), the lock directory is left behind as a stale lock and must be removed manually. The error message at acquisition points the user at the exact path, so manual cleanup is one `rm -rf` away. This is the same trade-off documented under "Concurrent run" in Failure modes; the explicit-cleanup pattern is preferred over `trap` because it correctly holds the lock across the conductor's many Bash tool calls, where a `trap` would silently release after the first one.
- Verify `<epic-id>` exists as an entry in `docs/planning/epics.yaml`. If not → abort with: `Epic <epic-id> not found in docs/planning/epics.yaml. Run /000-prd-refine or /001-plan first.`
- Verify `docs/planning/epic-{id}-tasks.yaml` exists (filename derived from the epic id, e.g. `E-007` → `epic-007-tasks.yaml`; the `{id}` placeholder always expands to the 3-digit zero-padded epic id). If not → abort with the expected path and: `Run /001-plan E-NNN first.`
- Load the tasks list. Group entries by `status`. Compute:
  - `pending_ids` — ordered list of task ids with `status: pending`.
  - Counts for `pending | in_progress | blocked | done`.
- If `pending_ids` is empty → print: `Nothing to do. All tasks for <epic-id> are done, in_progress, or blocked.` Exit cleanly (no error).
- Verify `.claude/stack.yaml` exists and contains a `gates` block. If missing → abort with the path.
- Verify `.claude/ruleset/` contains all 18 rule files. If any are missing → abort listing the missing filenames and suggest: `Run /000-prd-refine to re-seed the ruleset/ directory.`
- Confirm the 18 ruleset files are present on disk. Do **not** pre-load a single mega-block: ruleset injection is now subagent-specific. The implementer/feedback-implementer get a per-task subset (`rules_in_scope` ∪ mandatory core), the verifier gets none, the reviewer gets all 18. Invoke `scripts/inject-ruleset.sh` (with or without `--rules <slugs>`) at each dispatch site to capture the appropriate slice on stdout.
- **Capture business-scenarios hash.** Extract the epic's `business_scenarios` block-scalar verbatim from `docs/planning/epics.yaml` for the resolved `<epic-id>` and compute `sha256` over the raw bytes. Hold the value as a shell variable `EPIC_BS_HASH` (substituted as a literal by the orchestrator before each subsequent Bash tool call — environment variables do not persist across separate Bash tool invocations in this harness). This hash is the baseline for the per-iteration stale-detect check in Phase 1 Step 1. Example capture (with the literal epic id substituted):

  ```sh
  # The orchestrator extracts the business_scenarios block-scalar from
  # docs/planning/epics.yaml for the resolved epic id and pipes it into sha256sum.
  EPIC_BS_HASH="$(yq -r '.epics[] | select(.id=="E-007") | .business_scenarios' docs/planning/epics.yaml | sha256sum | awk '{print $1}')"
  ```

  The hash MUST be captured AFTER the epic-existence verification above and BEFORE the user-confirmation prompt, so the baseline reflects the state the user agrees to.
- **Detached HEAD check.** Run `git rev-parse --abbrev-ref HEAD`. If it returns the literal string `HEAD`, the working tree is in a detached-HEAD state and downstream branch logic will misbehave. ABORT (release the Phase 0 lock first per the close-out cleanup contract) with: `HEAD is detached. Check out a branch first: \`git checkout <branch-name>\` (e.g. main).`
- Verify the current branch is clean (no uncommitted changes outside `.claude/runs/` and `docs/planning/`). If dirty → abort with: `Working tree has uncommitted changes outside the runs and planning directories. Commit or stash before /002-auto-implement.`
- Resolve the branch base from `git-workflow.md` (`base_branch` key; defaults to `main`). Hold the resolved base ref in memory for the reviewer dispatches (they diff against it).
- **Git identity preflight.** Every per-task implementer dispatch runs `git commit`; a fresh machine with no global git identity will fail mid-batch with a cryptic git error. Run these checks before the loop starts:
  1. `git config --get user.email` must return non-empty.
  2. `git config --get user.name` must return non-empty.
  3. If either is empty → ABORT (release the Phase 0 lock first per the close-out cleanup contract) with: `Git identity not configured. Run \`git config --global user.email "<you@example>"\` and \`git config --global user.name "<Your Name>"\` then re-run.`
- **Signed-commits preflight.** If `git-workflow.md.require_signed_commits: true`:
  1. Run `git config --get user.signingkey` — must return non-empty.
  2. Run `git config --get commit.gpgsign` — must return `true` (or `gpg.format=ssh` plus `user.signingkey` set).
  3. Verify the agent is available:
     - For GPG: `gpg --list-secret-keys "$(git config --get user.signingkey)" >/dev/null`
     - For SSH: `ssh-add -L | grep -q "$(git config --get user.signingkey)"` or accept if `gpg.format=ssh` and the key file exists on disk.
  4. If any check fails → ABORT (release the Phase 0 lock first per the close-out cleanup contract) with: `require_signed_commits=true but signing not configured. Set git config user.signingkey and ensure your agent (gpg-agent / ssh-agent) is running. Re-run after fixing.`
- **DCO sign-off flag.** Read `require_dco_signoff` from the `git-workflow.md` YAML toggle block (default: `false`; the `oss` preset ships it as `true`). If true, set the in-memory flag `REQUIRE_DCO_SIGNOFF=true` and pass it into every per-task `implementer` dispatch payload (Step 1 commit-policy header below). The implementer agent uses `git commit -s` (which appends a `Signed-off-by:` trailer) when this flag is set. The plugin does NOT validate the DCO trailer at this stage — that is `/006-merge`'s Phase 0 pre-flight job (BEFORE `git push`).
- Print the plan to the user (single block):

  ```
  Batch run for <epic-id> — N pending tasks: T-001, T-002, T-003, …
  (skipping M done, K in_progress, J blocked)
  Proceed? (y/N)
  ```

- Wait for explicit user confirmation. Treat only `y` or `yes` (case-insensitive, trimmed) as proceed. Anything else → exit silently with no further output.

### Phase 1 — Per-task loop

For each task id in `pending_ids`, **in declared order** (sequential, never parallel):

#### Step 1 — Implementer subagent

- **Stale-epic detection.** At the start of each per-task iteration (before resolving the branch name, before any subagent dispatch):
  1. Re-read the epic entry for `${EPIC_ID}` from `docs/planning/epics.yaml`.
  2. If the epic entry is MISSING (the user deleted it mid-batch): HALT the batch (release the Phase 0 lock first per the close-out cleanup contract). Print: `Epic ${EPIC_ID} no longer present in epics.yaml. Batch aborted at task ${TASK_ID}. Subsequent pending tasks were not processed.`
  3. Compute `sha256` of the epic's `business_scenarios` block (the Gherkin block-scalar) using the same extraction recipe as Phase 0. Compare against the baseline `EPIC_BS_HASH` captured at Phase 0 pre-flight.
  4. If the hash differs: HALT the batch (release the Phase 0 lock first). Print: `Business scenarios for ${EPIC_ID} were modified during /002-auto-implement. Stop to avoid acting on stale data. Re-run /002-auto-implement to pick up the new scenarios.`

  This guard exists because Phase 0 reads `epics.yaml` once and holds the result for the batch lifetime. A user editing `epics.yaml` mid-batch (deleting the epic, rewording a `## Scenario:` block) would otherwise drive the inner loop with stale data. The check is per-task, not per-subagent — re-reading on every Task-tool dispatch would be overkill — but it MUST run before the implementer subagent for the current task is invoked.

- **Pre-dispatch: resolve branch name and commit-msg context.** Mirrors `/002-implement` Phase 1 substitution rules. Recognised substitution keys for `branch_name_pattern`: `{task_id}`, `{slug}`, `{ticket_id}`.
  1. Substitute `{task_id}` with the current task id and `{slug}` with the task's `slug` (or kebab-cased `title` fallback).
  2. **Resolve `{ticket_id}`** (only required when the pattern contains the placeholder; enterprise default `task/{ticket_id}/{task_id}-{slug}`):
     a. Read `task.cm_ticket` from the current task entry in `epic-{id}-tasks.yaml`.
     b. If absent, fall back to `epic.cm_ticket` from the matching epic entry in `epics.yaml`.
     c. If still absent AND the pattern contains `{ticket_id}`:
        - If `git-workflow.md.require_ticket_reference: true` → HALT the batch (release the Phase 0 lock first) with: `Task T-NNN has no cm_ticket and parent epic has none either. Add one via /001-plan or edit epic-NNN-tasks.yaml. (Enterprise preset requires CM ticket per task or epic.)`
        - Else → substitute `{ticket_id}` with the empty string and emit a visible warning (non-enterprise edge case).
     d. **Validate against `ticket_prefixes`** from `git-workflow.md` (if present): the resolved `<id>` must start with one of the configured prefixes (e.g. `CHG-`, `CM-`, `JIRA-`, `INC-`). Reject anything starting with `T-` — the plugin's own task-id namespace is reserved. On mismatch → HALT the batch with the resolved id, the allowed prefixes, and the source (task vs epic).
  3. **Branch collision / resume check.** Before any sync, run `git show-ref --verify --quiet refs/heads/<computed-branch-name>`. If the branch exists:
     - If `HEAD` already points at that branch AND any commit on that branch carries the current task id OR the resolved ticket id in its subject (`git log --oneline --grep="$TASK_ID\|$TICKET_ID" <branch>`) — treat as **resume**: skip base checkout, skip branch creation.
     - Otherwise → HALT the batch: `Branch <computed-branch-name> exists but does not appear to be a resume from a prior /002-auto-implement run. Inspect manually before retrying.`
- Invoke the `Task` tool with `subagent_type: "implementer"`.
- Prompt body MUST include, verbatim:
  - the task entry from `epic-{id}-tasks.yaml`,
  - the referenced Business scenarios from `epics.yaml` (Gherkin block-scalar copied as-is),
  - the **ruleset SUBSET** for this task — invoke `scripts/inject-ruleset.sh --rules <slugs>` where `<slugs>` = the planner's `01-plan.json.payload.rules_in_scope` for this task ∪ the mandatory core `{architecture, testing, code-style, git-workflow}`. The script honours the subset filter and always includes the mandatory core. Do **not** inline the full 18-file block — the implementer works under the planner's per-task scope; the reviewer in Step 5 is the one that sweeps all 18.
  - `stack.yaml.extras`,
  - the resolved `git-workflow.md` toggles,
  - **commit-msg context** under a header `--- commit-msg context ---`:
    - `cm_ticket: <resolved-ticket-id-or-null>` — the value resolved in the pre-dispatch step above.
    - `commit_subject_pattern: <from git-workflow.md commit-msg toggle>` — verbatim regex/string (e.g. `^(feat|fix|chore|refactor|test|docs)(\([a-z0-9-]+\))?: .+ \[[A-Z]+-[0-9]+\]$`).
    The implementer is responsible for including the ticket id in the commit subject (per the enterprise `^... \[TICKET-ID\]$` pattern); the conductor's job is to surface it.
  - **commit policy** under a header `--- commit policy ---`:
    - `require_signed_commits: <true|false>` — when true, the implementer commits with `-S` (GPG/SSH signing).
    - `require_dco_signoff: <true|false>` — when true, the implementer commits with `-s` (appends `Signed-off-by:` trailer). MUST be applied on the ORIGINAL commit — amending later to add `-s` is forbidden by the no-amend rule, and `/006-merge` enforces the trailer in its Phase 0 pre-flight BEFORE `git push`.
- The subagent reads/writes `.claude/runs/{epic_id}/{task_id}/02-impl.json` (and any prior phase files in that directory).
- Wait for completion. On return, read `02-impl.json`.
- Before dispatch, set the task `status: in_progress` in `epic-{id}-tasks.yaml` (preserve YAML formatting, comments, and key order). This matches `/002-implement` behaviour and ensures that if the user kills the batch mid-task, the runs-directory state is consistent with the tasks file.
- If `02-impl.json` is missing after dispatch return → treat as a dispatch error per Failure modes.
- If `02-impl.json` exists but does not validate against the implementer JSON Schema (shipped with the plugin) → treat as a schema validation failure per Failure modes.

#### Step 2 — Branch on implementer result

Read `02-impl.json.status`:

- **`too_big_proposal`** → print the `reason` and `suggested_split` to the user, then:
  - Suggest: `Run /001-plan --resplit <task-id> to decompose this task, then re-run /002-auto-implement <epic-id>.`
  - Explicitly write `status: pending` to the task entry in `epic-{id}-tasks.yaml` (preserve YAML formatting, comments, and key order). The task was set to `in_progress` in Phase 0 / Step 1; this reverts it. Matches `/002-implement` behaviour: both commands revert task status to `pending` on `too_big_proposal`. Do **not** mark `blocked` — the task is splittable, not blocked.
  - Note: the planner re-split (`/001-plan --resplit`) is responsible for archiving the pending task's stub `01-plan.json` if it exists.
  - **HALT the batch.** Do not advance to the next pending task. Exit.
- **`blocked`** → record the blocker:
  - Set `status: blocked` for this task in `epic-{id}-tasks.yaml`.
  - Print the blocker description from `02-impl.json`.
  - **HALT the batch.** Exit.
- **`ok`** → proceed to Step 3.

#### Step 3 — Verifier subagent

- Invoke `Task` tool with `subagent_type: "verifier"`.
- Prompt body MUST include: `stack.yaml.gates`, `stack.yaml.extras`, the task id, the epic id, and pointers to read all prior phase files in `.claude/runs/{epic_id}/{task_id}/`. **Do NOT inject ruleset bodies.** The verifier does not interpret rule prose — it runs gate commands and surfaces their exit codes; Findings reference rule slugs by name only, sourced from the failing gate's command output.
- Subagent writes `.claude/runs/{epic_id}/{task_id}/03-verify.json`.
- Wait for completion.

#### Step 4 — Verifier feedback loop (cap 3 iterations)

Read `03-verify.json.status`:

- **`status: "ok"`** → proceed to Step 5.
- **`fail`** → enter the feedback loop. Iterations are numbered with letter suffix `a`, `b`, `c` (matching the runs-directory convention in `CONTEXT.md`):
  - **Parent-context env marker.** This command MUST set `CRUMBS_PARENT_COMMAND=002-auto-implement` in the dispatch environment before any feedback-implementer dispatch (and, if the conductor ever falls back to invoking `/005-implement-feedback` directly, before that too), and `unset CRUMBS_PARENT_COMMAND` after the dispatch returns. This is how `/005-implement-feedback` distinguishes chained from standalone invocation when it is invoked from within this batch. Example:

    ```sh
    export CRUMBS_PARENT_COMMAND=002-auto-implement
    # dispatch feedback-implementer (or /005-implement-feedback fallback)
    unset CRUMBS_PARENT_COMMAND
    ```
  1. Invoke `Task` tool with `subagent_type: "feedback-implementer"`. Prompt includes the ruleset **subset** (`scripts/inject-ruleset.sh --rules <slugs>` where `<slugs>` = `01-plan.json.payload.rules_in_scope` ∪ mandatory core `{architecture, testing, code-style, git-workflow}` — same subset the implementer received), prior `02-impl.json`, prior `03-verify.json`, `stack.yaml.extras`, the iteration suffix, and explicit instruction to fix only the gate findings — not to refactor unrelated code.
  2. Subagent writes `.claude/runs/{epic_id}/{task_id}/05a-feedback-impl.json` (then `05b-…`, `05c-…` on subsequent iterations). Each file is a fresh artifact, not an overwrite.
  3. Re-dispatch `verifier` subagent. It overwrites `03-verify.json` (latest result wins). Prior verify outputs are not preserved by this command — if the user needs the history, they inspect the runs directory before the next iteration overwrites it. The `05{a|b|c}-feedback-impl.json` files retain the per-iteration fix record.
  4. Read the refreshed `03-verify.json`. If `ok` → exit the loop and continue to Step 5.
- After 3 full iterations (`a`, `b`, `c`) still failing → **HALT the batch** with `loop-limit`:
  - Print: `Verify loop exceeded 3 iterations for <task-id>. Halting batch. Review .claude/runs/<epic_id>/<task_id>/ and rerun /005-implement-feedback manually.`
  - Leave task `status: in_progress` (it is partially done; user must intervene).
  - Exit.

#### Step 5 — Reviewer subagent

- Invoke `Task` tool with `subagent_type: "reviewer"`.
- Prompt body MUST include: the **full 18-file ruleset block** (invoke `scripts/inject-ruleset.sh` with no `--rules` flag — the reviewer is the holistic gate, cross-cutting checks span the full set), `stack.yaml.extras`, pointers to all prior phase files, and an instruction to `git diff` against the branch base (resolved from `git-workflow.md`).
- Subagent writes `.claude/runs/{epic_id}/{task_id}/04-review.json`.
- Wait for completion.

#### Step 6 — Reviewer feedback loop (cap 3 iterations)

Same shape as Step 4, but driven by `04-review.json.status`:

- **`status: "ok"`** → proceed to Step 7.
- **`fail`** → loop:
  - **Parent-context env marker.** As in Step 4: set `CRUMBS_PARENT_COMMAND=002-auto-implement` before the feedback-implementer dispatch and `unset CRUMBS_PARENT_COMMAND` after it returns. The marker must be set for every iteration of the loop.
  1. `feedback-implementer` subagent → writes next `05{a|b|c}-feedback-impl.json` (continuing the same letter sequence — do not reset; if Step 4 used `a` and `b`, this loop starts at `c`, and the cap is per-task not per-gate).
  2. `verifier` subagent → overwrites `03-verify.json`.
  3. `reviewer` subagent → overwrites `04-review.json`.
- After 3 full iterations total per task still failing → **HALT** as in Step 4 with `loop-limit`. The 3-iteration cap is shared across verify and review feedback for a single task. Once spent, the batch halts even if review feedback was the only failing gate.

#### Step 7 — Mark task done

- Set `status: done` for this task in `epic-{id}-tasks.yaml` (write back; preserve YAML formatting and comments).
- Print a one-line confirmation: `<task-id> ✅` (the check mark is part of the contract — it is the only emoji this command emits, used as a status glyph not decoration).

#### Step 8 — Continue

- Move to the next id in `pending_ids`. Resume at Step 1 for that task.
- If the list is exhausted → proceed to Phase 2.

### Phase 2 — End-of-epic close-out

After every task in `pending_ids` reaches `status: done` (the loop completed without halting):

Order is MANDATORY:
1. Write `status: done` to epic entry in `docs/planning/epics.yaml` AND mark all tasks `status: done` in `docs/planning/epic-{id}-tasks.yaml`.
2. `git add docs/planning/epics.yaml docs/planning/epic-{id}-tasks.yaml` and `git commit -m "chore(planning): close epic {id}"`.
3. ONLY AFTER successful commit: invoke `scripts/archive-epic-runs.sh {epic_id}`.
4. If commit fails: abort, do NOT archive. Surface error to user. Then release the Phase 0 lock (step 5) before exiting.
5. **Release the Phase 0 lock** — `rm -rf .claude/runs/.lock-<epic_id>` (with the literal epic id substituted by the orchestrator). This is the final Bash call of the command on the success path. On every halt path (Phase 1 `too_big_proposal`, `blocked`, `loop-limit`, dispatch error, schema validation failure), the same `rm -rf` MUST execute in the halt-handling Bash call before the orchestrator returns.

Print summary after step 2 (or step 3 on success): tasks completed, suggest `/006-merge T-LAST` and `/003-verify-dod T-LAST --epic-close` (ATDD specs).

If you reverse this order — archive before mark-done — and the archive succeeds while mark-done fails (e.g. file lock), the runs artifacts are gone but the epic is still `in_progress`. AVOID.

Additional close-out details (subject to the ordering above):

- Print summary: `Epic <epic-id>: N/N tasks complete.` (`N` = original `pending_ids` length, counted at the start of Phase 1). Use the literal word "complete" here only as a colloquial summary phrase — the underlying task status field is `done`, never `complete`. The summary line is the single permitted exception to the vocabulary discipline below; do not propagate "complete" into any artifact.
- List the task ids that transitioned `pending → done` during this run, one per line, prefixed with `<task-id> ✅`. This mirrors the per-task confirmation from Step 7 and gives the user a scannable final report.
- Suggest next steps in this order:
  1. **Merge** — `Run /006-merge <epic-id> to open MR(s).` Note: per `git-workflow.md`, this is **one MR per task** for the team presets; for the **solo** preset, no MR is needed and `/006-merge` is a no-op. The command itself reads the toggle and acts accordingly.
  2. **ATDD close-out** — `Epic close-out: run bash <stack.yaml.gates.atdd_specs> to execute all ATDD specs against near-real infra.` Make clear: per-task subagents authored ATDD specs but did **not** execute them. The epic close-out is when the suite actually runs end-to-end.
- Archive the runs directory (step 3 above):
  - Invoke `bash scripts/archive-epic-runs.sh <epic-id>` (the helper script is shipped with the plugin; it tars `.claude/runs/{epic_id}/` into `.claude/runs-archive/{epic_id}-<timestamp>.tar.gz` and removes the source directory).
  - On script failure → print the script's stderr; do not abort the summary (the epic is functionally complete; archival is best-effort and re-runnable).

## Why a dedicated batch command (and not a shell loop)

A user could in principle write `for t in T-001 T-002 …; do /002-implement "$t"; done`. They should not. Reasons:

1. **Subagent isolation is per-`Task` dispatch.** A shell loop running `/002-implement` re-enters the main thread every iteration and accretes context across tasks — the very thing the subagent chain is designed to avoid. This command stays in the main thread *once* and dispatches subagents *N times*, so each task starts from a clean per-subagent context with the ruleset re-injected verbatim.
2. **Halt-on-block is centralised.** A shell loop has no view into `02-impl.json.status: too_big_proposal` — it would naively proceed to the next task. This command halts and surfaces the proposal to the user.
3. **Feedback loops are gated.** The 3-iteration cap is per-task and shared across verify/review gates. A shell loop cannot enforce this; it would either ignore failures or run unbounded.
4. **End-of-epic actions** (archival, ATDD close-out, merge suggestion) happen exactly once, after the final task. A shell loop would either skip them or fire them per iteration.

## Discipline

- **Each task step runs as a fresh subagent** via the `Task` tool, with isolated context. The main `/002-auto-implement` thread is the **conductor**: it reads inputs, dispatches subagents, parses their JSON artifacts, decides the next step. It never writes code, never runs gates, never edits files (except the two it owns: `epic-{id}-tasks.yaml` for `status` updates and the runs directory for housekeeping).
- **Sequential per task**, never parallel. Each task may depend on commits from the previous one (shared branch base or chained branches per `git-workflow.md`).
- **Halt-on-block** is non-negotiable. Any of the three halt conditions stops the batch:
  - `too_big_proposal` from an `implementer`,
  - `blocked` from an `implementer`,
  - `loop-limit` (3 feedback iterations per task without a clean pass).
- After a halt, the user intervenes (re-splits, unblocks, manually re-runs `/005-implement-feedback`). They then **re-run `/002-auto-implement <epic-id>`**, which picks up from the next `pending` task. Tasks already marked `done` stay `done` (the command skips them in Phase 0). Tasks left `in_progress` after `loop-limit` require manual resolution before re-running, otherwise pre-flight will treat them as already-in-progress and skip them silently.
- **No auto-merge, no auto-promote.** Even after a clean Phase 2 summary, `/006-merge` and `/007-promote` are user-triggered. This command surfaces the suggested invocations; the user runs them.

## Failure modes

- **Empty pending list** (Phase 0) → `Nothing to do. All tasks for <epic-id> are done, in_progress, or blocked.` Clean exit, no error.
- **User declines confirmation** (Phase 0) → exit silently. No log line, no marker.
- **Subagent halts** (`too_big_proposal`, `blocked`) → write the relevant `status` to the task, print the diagnostic, halt. The runs directory is preserved for the user to inspect.
- **Loop limit exceeded** → halt, leave task `in_progress`, point user at the runs directory.
- **Missing inputs** (epic not in `epics.yaml`, tasks file absent, ruleset incomplete, stack.yaml missing `gates`) → abort with the exact path(s) and the remediation command (`/000-prd-refine`, `/001-plan`, or a manual fix).
- **Subagent dispatch error** (Task tool returns non-zero or no artifact written at the expected path) → print the subagent type and task id, halt the batch. Do not retry automatically — the user resumes after diagnosis.
- **Schema validation failure on a subagent artifact** (JSON does not match the plugin-shipped schema for that phase) → halt the batch; print the validation error and the offending path. The task stays at whatever status it had before dispatch (typically `in_progress`).
- **Concurrent run of `/002-auto-implement` for the same epic** is rejected by the Phase 0 atomic lock (`mkdir .claude/runs/.lock-<epic_id>`). The second invocation exits with code `5` and prints the holder's `pid@host` plus timestamp. Stale locks (orchestrator crashed mid-run, host died) require manual cleanup of `.claude/runs/.lock-<epic_id>/`; the error message points the user at the exact path. The lock is released by an explicit `rm -rf` in the orchestrator's final Phase 2 step on success, or in the halt-handling Bash call on any failure path — there is no `trap`-based cleanup because traps do not survive across the orchestrator's separate Bash tool invocations. Different epic ids do not contend, so two terminals can drive two different epics in parallel without interference.

## Idempotency and resumability

This command is **resumable by design**. The state of the batch lives entirely in two places:

- `epic-{id}-tasks.yaml` — the authoritative `status` field per task.
- `.claude/runs/{epic_id}/{task_id}/*.json` — the per-task subagent artifacts.

Re-running `/002-auto-implement <epic-id>` after any halt picks up the next `pending` task and continues. There is no in-memory batch state and no resume token; the Phase 0 lock directory (`.claude/runs/.lock-<epic_id>/`) is held for the lifetime of a single invocation and is removed by the orchestrator's explicit `rm -rf` call in the final close-out step (or the halt-handling step on any failure path). The Phase 0 pre-flight rebuilds `pending_ids` fresh on every invocation, so any tasks marked `done` mid-batch are correctly skipped on the next run, and any tasks the user manually re-opened (set back to `pending`) are correctly re-processed.

If a task halted with `loop-limit` and was left `in_progress`, the next run will **skip it** (because `pending_ids` only includes `pending`). The user must either:
- Manually re-run `/005-implement-feedback <task-id>` until verify/review pass, then set the task to `done` themselves, **or**
- Reset the task to `pending` and accept that `/002-auto-implement` will re-dispatch the full chain from scratch (the prior `02-impl.json` is still readable by the implementer subagent as historical context).

## Subagent invocation contract

`Task` tool calls dispatched by this command include the verbatim ruleset content from `.claude/ruleset/*.md` (each file prefixed with `--- <basename> ---` as emitted by `scripts/inject-ruleset.sh`), but the **scope of injection varies per subagent**:

- **implementer** and **feedback-implementer** receive a **subset** — the planner's `01-plan.json.payload.rules_in_scope` for the current task ∪ the mandatory core `{architecture, testing, code-style, git-workflow}`. Invoke `scripts/inject-ruleset.sh --rules <slugs>`. Rationale: the planner already decided which task-specific rules apply; injecting only that subset plus the always-relevant core keeps the subagent focused on the slice at hand.
- **verifier** receives **NO ruleset bodies**. It runs gate commands from `stack.yaml.gates` and surfaces exit codes; rule slugs in Findings come from the gate's own output.
- **reviewer** receives **all 18 files** — invoke `scripts/inject-ruleset.sh` with no flags. Cross-cutting checks span the full set; the reviewer is the holistic gate.

Do not use `@`-include — `@`-references are not guaranteed to propagate into subagent contexts, which is the whole reason this batch command exists rather than the user invoking `/002-implement` in a shell loop.

Each dispatch prompt also includes:

- the task entry (YAML stanza from `epic-{id}-tasks.yaml`),
- the referenced Business scenarios (Gherkin block-scalar from `epics.yaml`),
- `stack.yaml.extras`,
- the resolved `git-workflow.md` toggles,
- explicit instruction to read all prior `NN-*.json` files in `.claude/runs/{epic_id}/{task_id}/` before writing its own output,
- explicit instruction to write a single JSON artifact at the canonical filename for its phase (`02-impl.json`, `03-verify.json`, `04-review.json`, `05{a|b|c}-feedback-impl.json`),
- the epic id and task id passed as structured fields so the subagent does not have to parse them out of free-form prose.

The conductor reads each artifact **only after** the subagent returns. It does not poll the filesystem mid-dispatch. If the artifact is missing or empty after dispatch return → treat as a dispatch error (see Failure modes).

The four subagent types this command dispatches map 1:1 to the entries in `.claude-plugin/agents/`:

| Step | `subagent_type` | Reads | Writes |
|---|---|---|---|
| 1 | `implementer` | task entry, BS scenarios, ruleset, extras | `02-impl.json` |
| 3 | `verifier` | all prior `NN-*.json`, `stack.yaml.gates` | `03-verify.json` |
| 4 / 6 | `feedback-implementer` | all prior `NN-*.json`, latest gate result | `05{a|b|c}-feedback-impl.json` |
| 5 | `reviewer` | all prior `NN-*.json`, branch diff vs base | `04-review.json` |

## Observability

- Per-task progress is visible from two places: the conductor's stdout (one line per subagent dispatch start, one line on return with the artifact path, plus the final `<task-id> ✅` confirmation), and the runs directory itself (which accumulates `NN-*.json` files as the chain proceeds).
- The conductor does **not** print full subagent output. Diagnostics live in the artifacts. The conductor's job is to keep the user oriented — task id, current phase, halt reason — not to mirror the subagent transcripts.
- On halt, the conductor prints the path of the artifact that triggered the halt (`Halt: see .claude/runs/<epic_id>/<task_id>/02-impl.json`) so the user can jump straight to the diagnostic.
- The runs directory is gitignored. It is **not** the durable record of what happened — `epic-{id}-tasks.yaml` status fields and the commit log are. The runs directory is scratch space, archived on epic close-out (Phase 2) and otherwise treated as ephemeral.

## Vocabulary discipline

Mirror `CONTEXT.md` exactly. Only these status tokens may appear in artifacts and user-facing output for tasks and epics: `pending | in_progress | blocked | done`. Do not invent batch-specific words like "running", "wip", "todo", "complete", "partial" — every such word maps to one of the four canonical statuses. The `02-impl.json` `status` field uses its own enum (`ok | too_big_proposal | blocked`) which is **subagent-result vocabulary**, not task-status vocabulary; the conductor translates `blocked` (impl result) into `status: blocked` (task status) when writing back to the tasks file. Keep the two enums distinct in user-facing language: say "the implementer signalled blocked" vs "the task is now blocked".

The verify and review gate results use a third enum: `pass | fail`. This is **gate vocabulary**, distinct from both task status and impl result. A `fail` gate result never directly becomes a task status — it triggers the feedback loop, and only after the 3-iteration cap is exceeded does the task transition to a halt state (left at `in_progress` per the `loop-limit` rule). The three enums are kept separate by design: conflating them would let a transient gate `fail` look like a permanent task `blocked`, which it is not.

Domain tests are called **"Domain-tests"** in user-facing output (per `CONTEXT.md`), not "unit tests" or "integration tests". ATDD specs are called **"ATDD specs"** (also per `CONTEXT.md`), not "acceptance tests" or "BDD tests" or "Cucumber tests". The conductor mirrors the implementer/verifier/reviewer subagents in this terminology; do not translate.

## Worked example

For an epic `E-007` with five tasks (`T-001` done, `T-002 T-003 T-004` pending, `T-005` blocked):

1. **Phase 0** prints: `Batch run for E-007 — 3 pending tasks: T-002, T-003, T-004. (skipping 1 done, 0 in_progress, 1 blocked) Proceed? (y/N)`.
2. User types `y`.
3. **T-002**: implementer returns `ok` → verifier returns `ok` → reviewer returns `ok` → status set to `done` → `T-002 ✅`.
4. **T-003**: implementer returns `ok` → verifier returns `fail` → feedback iteration `a` → verifier `ok` → reviewer `ok` → `T-003 ✅`.
5. **T-004**: implementer returns `too_big_proposal` → conductor prints the proposal, suggests `/001-plan --resplit T-004`, halts. `T-004` stays `pending`. `T-005` stays `blocked` and is never touched.
6. User runs `/001-plan --resplit T-004`, which replaces `T-004` with `T-004a` and `T-004b` (both `pending`).
7. User re-runs `/002-auto-implement E-007`. Pre-flight rebuilds `pending_ids = [T-004a, T-004b]`. The two new tasks proceed through the chain.
8. After both reach `done`, **Phase 2** prints: `Epic E-007: 2/2 tasks complete.` (counted from *this* run's pending list — `T-002` and `T-003` from the prior run are not double-counted), followed by the merge and ATDD suggestions, then archives the runs directory.

## Cross-references

- `/002-implement` — single-task counterpart. Same per-task chain, no batching, no halt-on-block across tasks (because there is only one task).
- `/001-plan --resplit <task-id>` — the user's escape hatch when an implementer signals `too_big_proposal`. Re-decomposes the offending task into smaller ones, then the user re-runs `/002-auto-implement <epic-id>` to resume.
- `/005-implement-feedback <task-id>` — invokable standalone to manually drive the feedback loop on a single task that this command halted with `loop-limit`.
- `/003-verify-dod <task-id>` and `/004-code-review <task-id>` — standalone gate invocations, useful for inspecting a halted task without re-running the implementer.
- `/006-merge <epic-id>` — invoked by the user after Phase 2 prints its merge suggestion. Honours `git-workflow.md` for one-MR-per-task vs solo-no-MR behaviour.
- `scripts/archive-epic-runs.sh` (Wave 8) — helper script invoked from Phase 2 to tar+remove the runs directory.
- `scripts/inject-ruleset.sh` — helper script invoked per subagent dispatch. Pass `--rules <slugs>` to emit a per-task subset (mandatory core always included); omit the flag to emit all 18 files.
- `CONTEXT.md` — canonical glossary. Statuses, subagent chain, ruleset injection, too-big detection, and runs directory layout are all defined there; this command must not drift from those definitions.
- `PRD.md §5` and `§10` — command roster and v1 scope. `/002-auto-implement` is one of the nine commands in v1; this command's behaviour must remain consistent with the role described in §5 ("Epic-level batch orchestrator").
- `.claude-plugin/agents/` — the four subagent definitions (`implementer`, `verifier`, `reviewer`, `feedback-implementer`) that this command dispatches. The `planner` subagent is **not** dispatched by this command (it is the `/001-plan` agent; re-split happens out-of-band when the user runs `/001-plan --resplit`).
