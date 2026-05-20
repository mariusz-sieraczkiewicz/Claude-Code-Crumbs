---
description: Dual-mode DoD gate. Epic mode (default, `<epic-id>` arg) verifies every status=done task in the epic by dispatching one verifier subagent per task in parallel; aggregates epic-level status. Task mode (`<task-id>` arg, legacy) verifies one task. Both modes audit two axes: acceptance_criteria + stack.yaml.gates. Zero tolerance. Standalone-invokable or chained from /002-implement. Optionally self-heals via feedback-implementer + re-verify loop (max 3 iterations per task) when the toggle is on.
argument-hint: <epic-id> | <task-id> [--epic-close]
---

Run the Definition-of-Done check for **$ARGUMENTS**. The command dispatches on argument shape:

- **`<epic-id>`** (matches `^E-`) → **epic mode** (default). Locate `docs/planning/epic-{id}-tasks.yaml`, gather every task with `status: done`, and dispatch one `verifier` subagent **per task in parallel**. Each per-task dispatch audits **two independent axes** for that task: every entry in `task.acceptance_criteria: [...]` against files touched (file:line evidence required) AND every gate declared in `.claude/stack.yaml.gates`. After all per-task dispatches return, aggregate: epic `status: ok` iff every per-task `03-verify.json` is `ok`. Self-heal (when toggle on) runs **per task** — each failing task gets its own Phase 2/3 loop (max 3 iterations per task); other tasks proceed independently. The aggregate epic status is computed after all per-task loops settle.
- **`<task-id>`** (matches `^T-`) → **task mode** (legacy). Verify exactly one task. Single verifier dispatch, two-axis audit, optional self-heal loop. Preserves the legacy `/003-verify-dod <task-id>` contract for resume scenarios and standalone task re-verifies.

**Zero tolerance on both axes**: any unsatisfied/partial criterion is a blocker Finding regardless of gate status; any gate that exits non-zero is a blocker Finding regardless of criterion status. Aggregate epic status is the AND of every per-task status — one failing task fails the epic.

This command operates in one of two behavioural modes, gated by the `auto_fix_on_verify_fail` toggle from `git-workflow.md` (resolved at freeze time via the same mechanism as other ruleset toggles):

- **Self-heal on (`auto_fix_on_verify_fail: true`)** — default for solo / small-team / oss. On `fail`, dispatch a `feedback-implementer` subagent to fix the findings, then re-dispatch the `verifier` to confirm. Loop up to 3 fix iterations. Stop early on first `status: ok`. Escalate to user if still failing after the third re-verify.
- **Self-heal off (`auto_fix_on_verify_fail: false`)** — default for enterprise. Behave strictly read-only: print findings and a manual-remediation pointer (user edits the working tree, then re-runs `/003-verify-dod`). Never edit code. `/005-implement-feedback` is reserved for epic-level user feedback, not gate-finding fixes.

The on-disk contract is identical in both modes for Phase 1 — the verifier always emits `.claude/runs/{epic_id}/{task_id}/03-verify.json`, validated against `schemas/run-phase.schema.json`. The self-heal mode appends additional artifacts (`03b-fix.json`, `03c-verify.json`, `03d-fix.json`, ...) — see "Artifact numbering" below. Append-only history: no prior file is ever overwritten.

This command can be invoked **standalone** (user types `/003-verify-dod T-001`) or **chained** (parent `/002-implement` runs it as part of the per-task loop). Standalone exit prints a human summary; chained exit returns control to the parent, which reads the JSON.

## Modes

**Mode dispatch** is by argument shape (see top-of-file dispatch table). Within each mode, two gate-scope sub-modes are available via the optional `--epic-close` flag:

1. **Per-task scope** (default for both epic mode and task mode) — runs every gate in `stack.yaml.gates` **except** `atdd_specs` and `journeys`. ATDD specs are reserved for **epic close-out** (a task ships its spec file but the spec is not executed until the epic is complete — see `CONTEXT.md` ATDD spec entry). Journeys are reserved for **environment promotion** (see CONTEXT.md Journey entry).
2. **Epic close-out scope** — `/003-verify-dod <id> --epic-close`. Adds `atdd_specs` to the gate run (every task's spec executes against real or near-real infrastructure). **Still skips** `journeys` — those run only from `/007-promote`. In epic mode, `--epic-close` is the canonical close-out invocation; in task mode it is the per-task close-out path used when a single task is the terminal task of its epic.

The gate-scope toggle is purely additive over the gate set. The discipline, the schema, and the verifier subagent are identical across all four (epic|task) × (per-task|epic-close) combinations.

## Epic mode workflow

When invoked with `<epic-id>`, the command runs an outer loop over every `status: done` task in `epic-{id}-tasks.yaml`. The inner per-task workflow (Phase 0 → Phase 3 below) is unchanged — what changes is the orchestration around it.

### Epic-mode Phase 0 — Pre-flight (outer)

- Resolve epic-id, locate `docs/planning/epic-{id}-tasks.yaml` (3-digit zero-padded form, e.g. `E-001` → `epic-001-tasks.yaml`). If absent, abort: `epic-{id}-tasks.yaml not found at <path>. Run /001-plan first.`
- Gather every task with `status: done` (the eligible set). If the eligible set is empty, abort: `Epic <epic-id> has no done tasks to verify. Run /002-implement first.`
- Common pre-flight checks (`.claude/stack.yaml` present + parseable, `gates` non-trivial, `.claude/ruleset/` complete, git identity if relevant) run **once** here, not per task.
- Acquire an epic lock at `.claude/runs/.lock-verify-<epic_id>/` via `mkdir` (atomic; fails if directory exists). Held for the duration of the outer loop. Released in every exit branch (success, abort, halt).

### Epic-mode Phase 1 — Parallel per-task dispatch

For every task `T` in the eligible set, dispatch one `verifier` subagent **in parallel** (single message, multiple Task tool calls). Each per-task dispatch follows the per-task Phase 1 contract below (acceptance_criteria + gates audit, writes `runs/{epic_id}/{T}/03-verify.json`).

**Parallelism bound.** Maximum concurrent verifier dispatches is `min(eligible_count, 5)`. If the eligible set exceeds 5, run in batches of 5 (sequentially batched, parallel within a batch). This bounds memory and avoids saturating the host machine when gates spawn heavy subprocesses (typecheck, build).

**Gate-command concurrency caveat.** Gates that mutate or contend on shared state (e.g. simulator boot, port binding, write to a single build cache) cannot run safely in parallel. Project authors must encode gate commands as idempotent reads; if a gate is known to be non-concurrent-safe, the project should declare it as a single epic-level gate in `stack.yaml.extras.concurrent_unsafe_gates: [gate_name, ...]` — in epic mode, those gates run **once** after all parallel verifiers complete (sequential epic-close pass), and their findings are folded into a synthetic per-task `03-verify.json` for the **terminal task** of the epic (the last task by id in the eligible set, sorted lexicographically). This keeps the artifact contract per-task even when the gate run is epic-level.

### Epic-mode Phase 2 — Per-task self-heal (independent)

When `auto_fix_on_verify_fail` is on, each failing task gets its own self-heal loop (per-task Phase 2 → Phase 3 → loop max 3 iter) — these run **independently per task**, sequentially within a failing task and in parallel across failing tasks (bounded by the same 5-way concurrency cap as Phase 1). A failing task does not block a passing task. The artifact numbering (`03b-fix.json`, `03c-verify.json`, ...) lives under each task's own subdir.

When `auto_fix_on_verify_fail` is off, every failing task halts at its own `03-verify.json` with `status: "fail"`; the command prints the aggregate epic summary and exits.

### Epic-mode Phase 3 — Aggregate epic status

After every per-task loop settles (success, blocked fix, or 3-iter exhaustion), aggregate:

- Epic `status: ok` iff every per-task **final** `03-verify.json` (or `03c/03e/03g-verify.json` after self-heal) has `status: "ok"`.
- Epic `status: fail` if any per-task final verify is `fail`.

Write an epic-level summary artifact at `runs/{epic_id}/03-verify-epic.json`:

```json
{
  "phase": "verify",
  "epic_id": "E-NNN",
  "agent": "verifier",
  "status": "ok" | "fail",
  "started_at": "<ISO8601>",
  "finished_at": "<ISO8601>",
  "findings": [],
  "next": "review" | "feedback-impl",
  "payload": {
    "criteria_audit": [],
    "scope": "epic",
    "tasks_verified": ["T-001", "T-002", ...],
    "tasks_passed":   ["T-001"],
    "tasks_failed":   ["T-002"],
    "per_task_artifacts": {
      "T-001": ".claude/runs/E-003/T-001/03-verify.json",
      "T-002": ".claude/runs/E-003/T-002/03c-verify.json"
    }
  }
}
```

The epic-level artifact is a **summary only**; per-task `03-verify.json` files remain the canonical source of truth. The epic artifact carries empty top-level `findings[]` and `payload.criteria_audit[]` — those live on per-task artifacts. The `scope: "epic"` discriminator distinguishes this from per-task artifacts; downstream consumers (`/004-code-review`, `/002-implement` auto-chain) read the epic file's `status` for the aggregate signal.

Schema note: the epic-level artifact validates against the same `run-phase.schema.json` (`phase: "verify"`). The required `criteria_audit` array is satisfied by an empty array (criteria are recorded per task, not at epic level).

### Epic-mode summary print

```
Epic E-001 DoD: N tasks verified, M passed, K failed.
  ok  T-001 (3 criteria satisfied, 5 gates run, 5 passed, 0 findings)
  ok  T-002 (4 criteria satisfied, 5 gates run, 5 passed, 0 findings, self-healed in 1 iter)
  fail T-003 (1 criterion not_satisfied, 0 gate findings, 3 iters exhausted)
```

Suggest next step:
- `ok` → `/004-code-review <epic-id>` (or chained: control returns to `/002-implement`).
- `fail` → manual remediation pointer (edit working tree for failing tasks, re-run `/003-verify-dod <epic-id>`).

## Per-task inner workflow

The sections below (Inputs, Phase 0, Phase 1, Phase 2, Phase 3, Loop) describe the **per-task** verify flow. In task mode, this runs once for the given task. In epic mode, this runs **per eligible task** under the outer loop described in "Epic mode workflow" above (parallel up to 5-way concurrency, independent self-heal per task).

## Inputs

- **`<task-id>`** — in task mode: `$ARGUMENTS` positional (e.g. `T-001`). In epic mode: the current task in the outer loop iteration. Optional trailing `--epic-close` flag toggles epic-close-out gate scope.
- **`docs/planning/epic-{id}-tasks.yaml`** — locate the task by scanning every `epic-*-tasks.yaml`. The first match wins; capture its `epic_id`. If not found anywhere, abort with: `Task <task-id> not found in any epic-*-tasks.yaml. Run /001-plan first.`
- **`docs/planning/epics.yaml`** — informational only. The verifier does **not** re-author or re-check Business scenarios; that mapping belongs to `/001-plan` and `/004-code-review`. Read it only if the gate output references a scenario name.
- **`.claude/stack.yaml`** — read `gates`, `paths`, `extras`, `design_verify`. The `extras` block is propagated verbatim to the verifier and the feedback-implementer (per CONTEXT.md "Ruleset injection" — same channel as ruleset content).
- **`.claude/ruleset/*.md`** — **NOT injected into the verifier.** The verifier receives no ruleset bodies. It runs commands from `stack.yaml.gates` and surfaces their exit codes; Findings reference rule slugs by name only, sourced from the failing gate's command output. The **feedback-implementer** in Phase 2 *does* receive the subset of rulesets that the failing gates reference, so it can interpret rule prose during the fix.
- **Prior phase files** under `.claude/runs/{epic_id}/{task_id}/`:
  - `01-plan.json` (planner output — task's `acceptance_criteria`, `atdd_spec` path, file list).
  - `02-impl.json` (implementer output — commit hash, file list actually touched, ATDD spec path written, branch name).
  - Any `05*-feedback-impl.json` (one per prior epic-feedback iteration — read in numeric/alphabetic order so the verifier sees the latest state, with letter-suffixed reruns ordered `05a`, `05b`, `05c`).
  - Any prior intra-`/003` self-heal artifacts (`03b-fix.json`, `03c-verify.json`, ...) — used by subsequent loop iterations within the same `/003` invocation; not pre-existing on first entry.
  The command passes the **paths** to the verifier; the subagent reads them itself (avoids ballooning the dispatching prompt). The verifier may also pass the file list (from `02-impl.json` + any `05*` and any prior `03X-fix.json`) to gates that accept a scoped path argument — but most gates run project-wide regardless, and that is the intended behaviour.

## Artifact numbering

Append-only. No prior file is ever overwritten or deleted. The full possible artifact sequence for a single `/003-verify-dod` invocation under self-heal mode:

| File | Phase | Writer | Status field |
|---|---|---|---|
| `03-verify.json` | Phase 1 (initial detect) | `verifier` | `ok` \| `fail` |
| `03b-fix.json` | Phase 2 iteration 1 (fix) | `feedback-implementer` | `ok` \| `blocked` |
| `03c-verify.json` | Phase 3 iteration 1 (re-verify) | `verifier` | `ok` \| `fail` |
| `03d-fix.json` | Phase 2 iteration 2 (fix) | `feedback-implementer` | `ok` \| `blocked` |
| `03e-verify.json` | Phase 3 iteration 2 (re-verify) | `verifier` | `ok` \| `fail` |
| `03f-fix.json` | Phase 2 iteration 3 (fix) | `feedback-implementer` | `ok` \| `blocked` |
| `03g-verify.json` | Phase 3 iteration 3 (re-verify) | `verifier` | `ok` \| `fail` |

Design-fidelity (`stack.yaml.design_verify.type == "prompt"`) writes a sibling `03-design-verify.json` only on the **initial** Phase 1 run — see "Design-verify handling". That artifact lives alongside `03-verify.json` and is **not** renumbered or repeated for subsequent loop iterations; it is treated as part of the initial detect.

Stopping rules:
- Any `03X-verify.json` (X ∈ {`""`, `c`, `e`, `g`}) with `status: "ok"` → loop ends, run succeeds. The "final" status of the `/003` invocation is `ok`.
- `03g-verify.json` with `status: "fail"` (third re-verify still failing) → loop ends, run fails. Escalate to user; do not start a fourth fix iteration. The "final" status of the `/003` invocation is `fail`.
- Any `03X-fix.json` with `status: "blocked"` (feedback-implementer reports it cannot proceed — e.g. ambiguous finding, missing file, ruleset conflict) → loop ends immediately, run fails, escalate to user. Do not run another Phase 3 in this case (no `03X-verify.json` follows a blocked fix).

## Workflow

### Phase 0 — Pre-flight

- Resolve `task_id` and `epic_id`. Abort patterns as above if either cannot be resolved.
- Confirm `.claude/stack.yaml` exists and parses. If absent, abort with: `stack.yaml missing. Run /000-prd-refine first.`
- Confirm at least one gate in `stack.yaml.gates` is non-null. If **every** gate is null, abort with: `No gates configured in stack.yaml.gates; DoD would trivially pass — but this is suspicious. Edit .claude/stack.yaml to enable at least lint + typecheck + domain_tests before re-running /003-verify-dod.` (Trivial-pass is treated as a configuration bug, not as a success.)
- Confirm `.claude/ruleset/` contains all 18 canonical rule files (project sanity check — if any are missing, list them and abort with a pointer to `/000-prd-refine`). The verifier itself receives **no** ruleset bodies; this check protects downstream phases (`/004-code-review`, and Phase 2 here) that do need full or partial ruleset content.
- Confirm `.claude/runs/{epic_id}/{task_id}/01-plan.json` and `02-impl.json` exist. If either is missing, abort with: `Phase prerequisites missing for <task-id>: <path>. Run /002-implement first.`
- Read the task entry from `docs/planning/epic-{id}-tasks.yaml`. Confirm `acceptance_criteria` field exists and is a non-empty array of non-empty strings. If missing, empty, or contains an empty/whitespace-only entry, abort with: `Task <task-id>.acceptance_criteria missing or malformed. Re-run /001-plan or edit the task entry.` DoD has no bar to verify against without it.
- Parse the trailing `--epic-close` flag. If present, set `epic_close = true`.
- Compute the **effective gate set**:
  - Always include: every non-null gate **except** `atdd_specs` and `journeys`.
  - If `epic_close = true`: also include `atdd_specs` when non-null.
  - **Never** include `journeys` here. Journeys are the smoke gate at promotion (see Modes).
- If `epic_close = true` but `stack.yaml.gates.atdd_specs` is null, surface a warning to the user: `--epic-close requested but stack.yaml.gates.atdd_specs is null. Proceeding without ATDD spec execution. This is almost certainly a misconfiguration.` Do **not** abort — the user may be running close-out on a project that genuinely has no ATDD layer (rare, but legal).

### Phase 1 — Dispatch verifier subagent (detect)

Use the Task tool with `subagent_type: "verifier"` (canonical payload shape: `agents/verifier.md`). The dispatch payload contains:

- `task_id`, `epic_id`.
- `epic_close` boolean (so the verifier knows whether to run `atdd_specs`).
- **Task `acceptance_criteria` array** — the verbatim array from the task entry in `epic-{id}-tasks.yaml`, preserving the 1-based ordering. The verifier audits each entry against files touched (Phase A in `agents/verifier.md`). Pre-flight check by this command: if the array is missing or empty, abort with: `Task <task-id>.acceptance_criteria missing or empty. Re-run /001-plan or edit the task entry.`
- **Files touched by the task** — the union of `02-impl.json.payload.files_changed` and the task entry's `files: [...]` field (if present). The verifier uses this to scope its criterion audit (do not range over the whole codebase).
- **Effective gate set** — list of `{name, command}` pairs from `stack.yaml.gates`, filtered as Phase 0 computed. Pass each gate's `name` (key in the YAML) alongside its `command` (the shell string) so the verifier can label Findings.
- **`stack.yaml` verbatim** — or at minimum the `gates`, `design_verify`, `extras`, and `paths` sections. The verifier may need `paths` to resolve relative gate commands (project may override `tests`, `src`, or `atdd_specs` paths); it propagates `extras` to any nested subagent (see Design-verify handling). `extras` is the documented escape hatch for stack-specific quirks (`bash_buffering_warning`, `user_ping_interval_minutes`, etc. — see CONTEXT.md "stack.yaml shape").
- **Ruleset bodies are NOT injected.** The verifier does not interpret rule prose; it runs the gate commands and surfaces exit codes, plus it audits criterion prose (a task-level DoD check that operates on the criterion text, not on cross-cutting rule files). Gate findings carry rule slugs (e.g. `tests.md:no-method-level-mocks`) only as they appear in the gate's own output — the verifier does not look them up against rule text. Rule-prose interpretation is the reviewer's job (`/004-code-review`) and, in self-heal mode, the feedback-implementer's job (Phase 2 below).
- **Prior phase file paths** — `01-plan.json`, `02-impl.json`, and every `05*-feedback-impl.json` found under `.claude/runs/{epic_id}/{task_id}/`, in lexicographic order (so `05a`, `05b`, `05c` are read in that order — matches the rerun numbering in CONTEXT.md "Runs directory"). The verifier opens them itself; the command does **not** inline the JSON content (it would bloat the dispatch prompt).

The verifier's contract (defined in its subagent prompt) is:

1. **Phase A — Audit every acceptance criterion** against the files touched. For each criterion (1-based index), classify `satisfied | partial | not_satisfied` with concrete `evidence: [{file, line, snippet}]`. For each `partial`/`not_satisfied`, emit a Finding with `rule: "acceptance_criterion:<i>"`, `severity: "blocker"`, `location: "<file:line if known, else epic-{id}-tasks.yaml>"`, `message`, `details`. Always populate `payload.criteria_audit[]` with one entry per criterion regardless of status.
2. Run every gate in the effective set. Capture exit code, stdout, stderr.
3. For each non-zero exit, emit one or more `findings[]` entries, each with: `rule` (the gate name or the rule it enforces), `severity: "blocker"` (zero-tolerance — there is no other severity), `location` (file:line where available), `message` (condensed error), `details` (relevant stderr/stdout excerpt — per the Finding object in `schemas/run-phase.schema.json`).
4. If `stack.yaml.design_verify.type == "prompt"`, emit a single `design_verify_prompt` finding pointing at the prompt file (this command handles it — see below).
5. Write `.claude/runs/{epic_id}/{task_id}/03-verify.json` with `status: "ok"` (every criterion `satisfied` AND zero gate findings) or `status: "fail"` (≥1 finding from either axis). Schema: `schemas/run-phase.schema.json`.
6. Never edit source code. Never invoke another slash command. The verifier is **read-only** at the subagent level. (Fix execution, when enabled, is owned by Phase 2 of this command, which dispatches a **separate** subagent.)

After the verifier returns, **validate `03-verify.json` against `schemas/run-phase.schema.json`** before branching (see "Schema validation" below). Then branch on `status`.

### Schema validation (shared helper for every `03X-verify.json` and `03X-fix.json`)

Before declaring any iteration's artifact "done", validate it against `schemas/run-phase.schema.json`. If validation fails:

- Do **not** delete or rewrite the file (the subagent may have written useful Findings even if a schema field is malformed).
- Print: `<agent> emitted <path> but it fails schema validation: <error>. Treating run as fail.`
- Treat the artifact's effective status as `"fail"` (for `verify` artifacts) or `"blocked"` (for `feedback-impl` artifacts) for the purpose of loop control and next-step suggestion.

A schema-failing subagent output is a bug in the subagent prompt, not in the project. Surface it so the user can file an issue against the plugin. **Do not retry** the same subagent in-place — break the loop and escalate.

### Branch on `03-verify.json.status`

#### `status: "ok"` (initial detect passed)

Print a tight summary to the user (counts only, no per-gate noise):

```
DoD ok — <N> criteria satisfied, <N> gates run, <N> passed, 0 findings.
```

Suggest the next step depending on invocation context:

<!-- FREEZE:IF auto_invoke_review -->
- **Chained from `/002-implement`** (parent will detect `status: "ok"` itself): no suggestion needed; control returns to the parent which auto-advances to `/004-code-review`.
- **Standalone**: invoke `/004-code-review <task-id>` immediately via the SlashCommand tool (`auto_invoke_review` is on for this preset). Do not wait for the user — the toggle says auto, so go.
<!-- FREEZE:ELSE -->
- **Chained from `/002-implement`** (parent will detect `status: "ok"` itself): no suggestion needed; control returns to the parent which advances to the merge proposal (`auto_invoke_review` is off in `git-workflow.md`).
- **Standalone**: suggest `/006-merge <task-id>` next (`auto_invoke_review` is off for this preset; review is opt-in via explicit `/004-code-review`).
<!-- FREEZE:ENDIF -->

Exit. No further phases run in this command.

#### `status: "fail"` (initial detect found blockers)

Branch on the `auto_fix_on_verify_fail` toggle.

<!-- FREEZE:IF auto_fix_on_verify_fail -->

### Phase 2 — Dispatch feedback-implementer (fix)

Self-heal is ON. Dispatch a `feedback-implementer` subagent to address the findings.

Use the Task tool with `subagent_type: "feedback-implementer"` (canonical payload shape: `agents/feedback-implementer.md`). The dispatch payload contains:

- `task_id`, `epic_id`.
- **Iteration index** — `1` on first entry, `2` after `03c-verify.json` failed, `3` after `03e-verify.json` failed.
- **Target artifact path** — the file the feedback-implementer must write: `03b-fix.json` on iteration 1, `03d-fix.json` on iteration 2, `03f-fix.json` on iteration 3.
- **Source findings path** — the most recent `03X-verify.json` (`03-verify.json` for iteration 1, `03c-verify.json` for iteration 2, `03e-verify.json` for iteration 3). The feedback-implementer reads the `findings[]` array AND the `payload.criteria_audit[]` array from this file — both axes drive the fix.
- **Task `acceptance_criteria` array** — verbatim from `epic-{id}-tasks.yaml`. Findings with rule `acceptance_criterion:<i>` map to the i-th criterion; the feedback-implementer must write production code AND a Domain-test asserting the criterion (strict ATDD-E2E: test first if missing, then implementation).
- **Ruleset subset** — bodies of every ruleset file referenced (by slug) in `findings[].rule`. For findings whose rule slug is just a gate name with no `.md:` prefix (e.g. `lint`, `typecheck`), no ruleset injection is needed — the gate command output is the authority. For criterion findings (`acceptance_criterion:<i>`), the criterion prose itself is the authority — no ruleset injection. The dispatching command resolves rule-slug findings to file paths and reads each body; pass the bodies verbatim in the dispatch payload (same channel as the reviewer ruleset injection — see CONTEXT.md "Ruleset injection").
- **`stack.yaml.extras` verbatim** — propagate the escape hatch.
- **Prior phase file paths** — `01-plan.json`, `02-impl.json`, every `05*-feedback-impl.json`, and **every prior `03X-fix.json` from the current loop** (so iteration 2 sees what iteration 1 already changed). Pass paths, not inlined content.

The feedback-implementer's contract (defined in its subagent prompt) is:

1. Read the findings file. For each finding, edit source files to address the root cause. Strict ATDD-E2E: if the finding is a missing/failing test, write/fix the test first (RED), then the implementation (GREEN).
2. After all fixes, re-run the failing gate commands locally (subset of `stack.yaml.gates` whose names appear in `findings[].rule`) to confirm exit 0. If any still fail, the fix is incomplete — emit `status: "blocked"` with `payload.reason` populated AND skip the commit step below (do not commit broken fixes).
3. **Commit the fix.** When `status: "ok"` (gates re-pass locally), make **one commit** on the current epic branch (or `main` under solo). Commit message format: `fix(verify): <task-id> <one-line summary of the change>` (Conventional Commits scope = `verify`; the body MAY list the rule slugs addressed). Stage only files modified during this fix iteration. Never amend. The new commit stacks on top of the prior task impl commit and any earlier `fix(verify): ...` / `fix(review): ...` commits in this epic. Record the resulting sha in `payload.commits_made[0]`. Skip the commit step entirely under `status: "blocked"` (no clean state to capture).
4. Write the target artifact (`03b-fix.json` / `03d-fix.json` / `03f-fix.json`) with (canonical payload shape: `agents/feedback-implementer.md`):
   - `phase: "feedback-impl"`, `agent: "feedback-implementer"`, `task_id`, `epic_id`, `status: "ok" | "blocked"`, `started_at`, `finished_at`.
   - `payload.fixes_applied`: array of `{finding_id, file, change_summary}` entries describing each touched file.
   - `payload.commits_made`: array with exactly one sha when `status: "ok"`; empty array when `status: "blocked"`.
   - `payload.reason`: single-paragraph explanation (required when `status: "blocked"`).
   - `payload.unresolved_rules` (optional): array of rule slugs the implementer could not address.
   - `payload.iteration`: the iteration index (1, 2, or 3) for forensic tracing.
5. Do **not** invoke `/003-verify-dod` recursively. Do **not** invoke any other slash command. The next Phase (re-verify) is dispatched by **this** command, not by the subagent.

After the feedback-implementer returns, **validate the new `03X-fix.json` against the schema** (shared helper above). Then branch:

- `status: "blocked"` → loop ends. Print the unresolved findings, print the manual-remediation pointer (`edit the working tree to address each finding, then re-run /003-verify-dod <task-id>`; `/005-implement-feedback` is for epic-level user feedback, not gate-finding fixes), exit with run status `fail`.
- `status: "ok"` → proceed to Phase 3.

### Phase 3 — Re-dispatch verifier (re-verify)

Dispatch `verifier` again with the **same payload shape as Phase 1** (canonical payload shape: `agents/verifier.md`), except:

- **Target artifact path** — `03c-verify.json` on iteration 1, `03e-verify.json` on iteration 2, `03g-verify.json` on iteration 3.
- **Prior phase file paths** — include the just-written `03X-fix.json` and every earlier `03X-fix.json` / `03X-verify.json` from the current loop.

The verifier runs the full effective gate set again (not a subset — a fix in one area can regress another). It writes the target artifact with the same schema as `03-verify.json`.

Validate the new `03X-verify.json` against the schema (shared helper). Then branch:

- `status: "ok"` → loop ends, run succeeds. Print:

  ```
  DoD ok — self-healed in <iteration> fix iteration(s). <N> criteria satisfied, <N> gates run, <N> passed, 0 findings.
  ```

  Then follow the same "ok" next-step suggestion as the initial-detect ok branch above (chained vs standalone; honour `auto_invoke_review`). Exit.

- `status: "fail"` → loop continues if iteration index < 3, else loop ends with run status `fail` (see escalation below).

### Loop

The Phase 2 → Phase 3 cycle repeats at most **3 iterations**. After each iteration:

- If the latest `03X-verify.json.status == "ok"` → success, exit loop, run succeeds.
- If iteration index < 3 and the latest `03X-verify.json.status == "fail"` → go to Phase 2 with iteration index + 1.
- If iteration index == 3 and `03g-verify.json.status == "fail"` → loop ends, run fails. Print:

  ```
  DoD fail — 3 fix iterations exhausted, <N> findings remain. Escalating to user.

    [<rule>] <location> — <message>
    ...
  ```

  Truncate `message` at ~120 chars; the JSON has full details. Print the manual-remediation pointer (`edit the working tree to address each finding above, then re-run /003-verify-dod <task-id>`); intra-`/003` looping is an automation convenience, not a guarantee, and `/005-implement-feedback` is reserved for epic-level user feedback rather than gate-finding fixes.

- If any `03X-fix.json.status == "blocked"` → loop ends immediately (no Phase 3 follows a blocked fix). Print the unresolved findings and the same manual-remediation pointer.

The hard maximum is 3 fix iterations regardless of how it ends — there is no override flag, no "just one more try". This bounds the worst-case cost (3 × feedback-implementer + 4 × verifier including the initial detect) and forces a human checkpoint when the loop cannot converge automatically.

**Chained mode note.** When `/002-implement` invokes this command, the parent will see the **final** artifact (the last `03X-verify.json` written) and route accordingly. The intra-`/003` loop is invisible to the parent except via the additional artifacts on disk; the parent does **not** restart its own outer loop. Looping discipline stays single-owner: the parent routes on `/003`'s final status per its own contract, but it does so **once**, not in a tight retry — the in-command loop here is the only auto-retry layer for verify findings.

<!-- FREEZE:ELSE -->

### Phase 2 — Read result (read-only)

Self-heal is OFF (`auto_fix_on_verify_fail: false`, e.g. enterprise preset where compliance requires a review board to mediate fixes). This command is strictly read-only after Phase 1.

Print the finding count followed by a condensed list, one line per finding:

```
DoD fail — <N> findings.

  [<rule>] <location> — <message>
  [<rule>] <location> — <message>
  ...
```

Truncate `message` at ~120 chars. Do **not** dump full stderr; the JSON has it for forensic reading.

Suggest the next step:

- **Chained**: parent will see `status: "fail"` and route accordingly; do not re-suggest.
- **Standalone**: print a manual-remediation pointer:
  > Manual remediation: edit the working tree to address each finding above, then re-run `/003-verify-dod <task-id>` to confirm fixes. (`/005-implement-feedback` is for epic-level user feedback, not gate-finding fixes.)

The command exits after printing. It does **not** loop, retry, or auto-invoke any other command. Remediation in this preset is owned by the human reviewer board: they edit the working tree manually to address each Finding, then re-run `/003-verify-dod` to confirm. This matches the enterprise compliance expectation that no automated agent edits code in response to a failing gate without an explicit human-mediated remediation step. (`/005-implement-feedback` covers a different flow — epic-level user feedback — and is not the right escalation for gate-finding fixes.)

<!-- FREEZE:ENDIF -->

## Design-verify handling

`stack.yaml.design_verify` declares the project's design-fidelity gate. It is special-cased because it has two forms:

- **`type: "script"`** — an executable (e.g. `swiftlint --strict` with custom rules, a Python `design_check.py`). The verifier treats it like any other gate: run, check exit code, capture findings. **No extra handling in this command.** Script form contributes a single Finding to `03-verify.json` (under `findings[]`) — no `03-design-verify.json` sibling is written. Only the `prompt` form writes the sibling artifact. In self-heal mode, a script-form design-verify finding flows through Phase 2 like any other finding — the feedback-implementer fixes it, the next verifier re-runs the script.
- **`type: "prompt"`** — a markdown file containing instructions for an LLM-driven design check (e.g. "compare diff against `docs/DESIGN.md` token table; flag any deviation"). The verifier cannot execute prose — it instead emits a single `design_verify_prompt` finding pointing at the prompt file. This command then (only on the **initial** Phase 1 detect — not repeated for loop iterations):
  1. Reads the prompt file's full content.
  2. Computes the diff for the task (compare working tree against the branch base recorded in `02-impl.json`).
  3. Spawns a **separate general-purpose subagent** via the Task tool, with `subagent_type: "general-purpose"`. The prompt content is the subagent's instructions; the diff is the input. Inject `stack.yaml.extras` verbatim (same channel as the verifier).
  4. Collects the general-purpose subagent's findings (it returns the same `findings[]` shape).
  5. **Does not mutate `03-verify.json`.** Phase artifacts are append-only history; the verifier's output stays untouched. Instead, write a NEW sibling file `.claude/runs/{epic_id}/{task_id}/03-design-verify.json` with shape:

     ```json
     {
       "phase": "verify",
       "agent": "design-verifier",
       "task_id": "T-NNN",
       "epic_id": "E-NNN",
       "status": "ok|fail",
       "findings": [...],
       "started_at": "<ISO8601>",
       "payload": { "design_verify_type": "prompt", "prompt_path": "<path>" }
     }
     ```

     `status: "ok"` when the general-purpose subagent returned an empty findings list; `status: "fail"` otherwise.
  6. Downstream consumers (notably `/004-code-review` Phase 0) gate on **both** files: review aborts if `03-verify.json.status != "ok"` OR `03-design-verify.json` exists AND `03-design-verify.json.status != "ok"`.
  7. In self-heal mode, if `03-design-verify.json.status == "fail"`, the design-fidelity findings are **merged into the Phase 2 dispatch payload** alongside the verifier's own findings — the feedback-implementer addresses both in the same fix iteration. The design-verify sibling artifact is **not** rewritten on subsequent re-verifies (it is a once-per-initial-detect artifact); to re-check design fidelity after a fix iteration, the project must encode that as a script-form gate in `stack.yaml.gates` (which then flows through the normal loop).

**Note on artifact naming.** The `03-design-verify.json` design-fidelity sibling sits alongside `03-verify.json` (initial detect) and is not part of the self-heal iteration sequence (`03b-fix.json`, `03c-verify.json`, ...). The leading prefix `03-` (with no letter suffix) marks it as a once-per-initial-detect artifact; downstream consumers branch on the basename, not the prefix letter.

This indirection exists because `verifier` is a small, gate-focused subagent and design checks frequently need a broader LLM with general code-reading capability. The split keeps `verifier` deterministic, the design check tunable per-project via a markdown file, and the runs history append-only.

## Standalone vs chained

This command behaves the same on-disk in both modes — the only difference is what happens **after** the final summary prints:

- **Standalone** (user typed `/003-verify-dod T-NNN` directly): print the summary and suggested next-step command. Exit. The user decides what to do next.
- **Chained** (parent `/002-implement` invoked this command in-line): the parent does not need any printed output beyond a confirmation; it reads the latest `03X-verify.json` itself and routes accordingly. Avoid extra chatter — keep the summary tight so chained sessions stay readable.

A command does **not** know its invocation context with certainty (no flag passed by the parent — the chain is filesystem-mediated, per CONTEXT.md "Subagent chain"). The safe heuristic: always print the summary; the parent will simply ignore stdout and read the JSON.

Concretely, the per-mode behavioural contract is:

| Aspect | Standalone | Chained |
|---|---|---|
| Writes `03-verify.json` | yes | yes |
| Writes `03b-fix.json` … `03g-verify.json` (self-heal on) | yes | yes |
| Prints summary | yes | yes (parent ignores) |
| Suggests next command | yes | no (parent routes) |
| Self-heal loop on `fail` (toggle on) | yes (max 3 iter) | yes (max 3 iter) |
| Honours `--epic-close` | yes | yes (parent passes flag through) |

## Discipline

- **Zero tolerance.** Any non-zero gate exit produces a blocker Finding. There are no severity tiers, no overrides, no "minor advisory" Findings (CONTEXT.md "Finding policy"). A single `lint` warning that the project's `lint` gate treats as an error is enough to fail DoD.
- **Self-heal is bounded.** Max 3 fix iterations. There is no escape hatch to extend the loop — projects that consistently need more iterations have a configuration smell (overlapping gates, unstable tests, ruleset contradictions) that the human should diagnose, not the agent.
- **Append-only history.** Every iteration writes a fresh artifact (`03b-fix`, `03c-verify`, ...). No prior NN-*.json is ever overwritten or deleted by this command. Re-invoking `/003-verify-dod` on the same task **does** overwrite `03-verify.json` only — the initial-detect artifact is idempotent per invocation, but the loop artifacts from a previous invocation are preserved alongside the new ones (the loop letter-suffix scheme allows arbitrary numbers of historical artifacts to coexist).
- The verifier is **read-only at the subagent level**. The feedback-implementer subagent is the only writer of source files in this command's chain, and only when the toggle is on. When the toggle is off, this command does not stage, commit, or modify any source file; the user manually edits the working tree to address each Finding (reading the latest `03X-verify.json` for the full forensic detail) and then re-runs `/003-verify-dod` to confirm. `/005-implement-feedback` is reserved for epic-level user feedback flows and is not the right tool for gate-finding fixes.
- **Verifier receives NO ruleset bodies.** Several gates encode rule names in their output (e.g. `tests.md:no-method-level-mocks`, `data-modeling.md:no-anemic-model`); the verifier passes those slugs through verbatim into `findings[].rule` without interpreting them. The feedback-implementer in Phase 2 **does** receive the subset of rulesets referenced in the findings (so it can read rule prose during the fix). Mapping a slug back to actionable prose at review time belongs to the reviewer (`/004-code-review`), which receives all 18 ruleset files.
- **No `journeys` execution here, ever** — including in `--epic-close` mode. Journeys are the **promotion** smoke gate and belong to `/007-promote`. They compose multiple Business scenarios across features (CONTEXT.md "Journey") and need a real production-like environment that the per-task DoD loop deliberately does not boot.
- **No source-of-truth mutation.** Neither the verifier nor the feedback-implementer edits `epics.yaml`, `epic-{id}-tasks.yaml`, `stack.yaml`, or any file under `.claude/ruleset/`. The only writes are under `.claude/runs/` (artifacts) and, in self-heal mode, under the project's source tree (the files the feedback-implementer fixes).
- **Gate exit code is the contract.** Stdout/stderr are evidence, but the verifier never tries to "interpret success" out of stderr lines when the exit code is non-zero. A failing gate stays failing even if its stderr happens to contain the word "passed".
- **No partial pass.** A gate either succeeds (exit 0, no findings) or contributes one or more Findings. There is no "ran but inconclusive" state. If a gate command itself crashes (e.g. missing binary), the verifier emits a Finding with `rule: "gate-misconfigured"` and the run is `fail`.

## Vocabulary discipline

This command mirrors the project glossary in `CONTEXT.md` exactly. Use these terms verbatim:

- **Finding** — a single blocker entry in any `03X-verify.json.findings`. Never "issue", "problem", "violation report".
- **Gate** — one entry in `stack.yaml.gates` (a shell command + exit-code contract). Never "check", "validation".
- **Status** — `ok` or `fail` on the run-phase JSON (`ok` / `blocked` for fix artifacts). Never "PASS/FAIL", "ALL_DONE", "GAPS_REMAINING".
- **Iteration** — one Phase 2 → Phase 3 cycle within the self-heal loop. Never "round", "attempt", "retry".
- **Zero tolerance** — the binary blocker policy from CONTEXT.md "Finding policy". Never "critical/major/minor", never "blocker/non-blocker".

If a Finding's `message` is forwarded from a gate that uses different vocabulary (e.g. `swiftlint` says "violation"), preserve the gate's wording inside the message — but the surrounding command output (counts, next-step suggestions, abort messages) must use the project glossary.

## Examples

Per-task DoD on a TypeScript stack with five non-null gates (`lint`, `typecheck`, `domain_tests`, `build`, `security`), self-heal toggle on:

```
/003-verify-dod T-014
```

Effective gate set: `lint`, `typecheck`, `domain_tests`, `build`, `security` (5 gates). `atdd_specs` is skipped (per-task mode). The task has 3 entries in `acceptance_criteria`. The verifier audits each criterion against `02-impl.json.payload.files_changed`, then runs each gate. Initial detect passes on both axes:

```
DoD ok — 3 criteria satisfied, 5 gates run, 5 passed, 0 findings.
Next: /004-code-review T-014
```

Same task, but criterion #2 (`"Calling cancel on already-cancelled subscription is a no-op"`) is `not_satisfied` (no guard clause found in `src/billing/cancel.ts`) and `lint` returns 2 violations on first detect. The feedback-implementer fixes all three in iteration 1 (writes the missing Domain-test + guard clause + fixes lint), re-verify passes:

```
DoD ok — self-healed in 1 fix iteration(s). 3 criteria satisfied, 5 gates run, 5 passed, 0 findings.
Next: /004-code-review T-014
```

Artifacts written: `03-verify.json` (status: fail, 3 findings — 1 criterion + 2 lint) → `03b-fix.json` (status: ok, 3 fixes_applied) → `03c-verify.json` (status: ok, 0 findings, 3 criteria satisfied).

Epic close-out on the same task (terminal task of the epic), self-heal off (enterprise preset):

```
/003-verify-dod T-014 --epic-close
```

Effective gate set adds `atdd_specs`. Now 6 gates run. If the ATDD spec for T-014 fails against the near-real test environment, the verifier emits one or more Findings and the output becomes:

```
DoD fail — 1 findings.

  [atdd_specs] tests/e2e/specs/checkout.spec.ts:42 — expected redirect to /confirmation, got /error
Next: edit the working tree to address each finding above, then re-run /003-verify-dod T-014.
```

No `03b-fix.json` is written — the toggle is off, the command is read-only after Phase 1.

Same task with self-heal on, three iterations exhaust without convergence:

```
DoD fail — 3 fix iterations exhausted, 1 findings remain. Escalating to user.

  [atdd_specs] tests/e2e/specs/checkout.spec.ts:42 — expected redirect to /confirmation, got /error
Next: edit the working tree to address each finding above, then re-run /003-verify-dod T-014.
```

Artifacts written: `03-verify.json`, `03b-fix.json`, `03c-verify.json`, `03d-fix.json`, `03e-verify.json`, `03f-fix.json`, `03g-verify.json` — all seven coexist under the task directory for forensic reading.
