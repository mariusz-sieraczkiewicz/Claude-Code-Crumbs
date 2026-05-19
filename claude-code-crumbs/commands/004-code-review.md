---
description: Code-review gate with self-heal. Reviewer subagent emits Findings; on fail the feedback-implementer applies fixes and the reviewer re-runs. Zero tolerance, max 3 iterations.
argument-hint: <task-id>
---

Run the code-review gate for **$ARGUMENTS**. Dispatches the `reviewer` subagent with the verbatim-injected ruleset and the branch diff, reads the resulting Findings, and — when the `auto_fix_on_review_fail` toggle is enabled — self-heals by dispatching `feedback-implementer` to apply the Violations and re-running the reviewer until the run returns `status: ok` or the 3-iteration cap is reached. Zero tolerance: every Finding is a blocker; only **Violations** (not Refactoring Suggestions) trigger the self-heal loop.

This command is standalone-invokable. It is also auto-chained by `/002-implement` after `/003-verify-dod` reports `status: ok`. The chaining mode does not change what this command does — only who reads the final `04X-review.json` afterwards.

## Inputs

- **`<task-id>`** — passed as `$ARGUMENTS` (e.g. `T-014`). Required positional argument.
- **`docs/planning/epic-{id}-tasks.yaml`** — locate the task entry by scanning every `epic-*-tasks.yaml` under `docs/planning/`. The matching file's name yields the `epic_id` (e.g. `epic-003-tasks.yaml` → `E-003`). If the task is not found, abort with: `Task <task-id> not found in any epic-*-tasks.yaml. Run /001-plan first.`
- **`.claude/ruleset/*.md`** — all 18 canonical Rule files, **verbatim-loaded** into memory for subagent injection. The Ruleset is the single source of truth for review checks. Per CONTEXT.md "Ruleset injection", content is pasted into the subagent prompt body — never via `@`-include, which does not always propagate to subagents.
- **YAML toggle block in `.claude/ruleset/git-workflow.md`** — read `default_branch` (fallback `main`), `allow_commit_to_main` (fallback `false`), and `auto_fix_on_review_fail` (fallback `true`). The last governs whether Phase 2/3 + Loop execute or this command degrades to read-only.
- **Prior phase files** under `.claude/runs/{epic_id}/{task_id}/`:
  - `01-plan.json` — planner's task decomposition.
  - `02-impl.json` — implementer's output (commit sha, files changed, ATDD spec path).
  - `03-verify.json` — verifier's gate results. Must be present with `status: "ok"` (see Phase 0).
  - Any `05X-feedback-impl.json` (`05a`, `05b`, `05c`) from prior feedback rounds.
- **The diff** — `git diff <base>...HEAD` where `<base>` is the configured default branch. Read `default_branch` from the YAML toggle block in `.claude/ruleset/git-workflow.md`; fall back to `main` if the key is absent.
- **`.claude/stack.yaml`** — read `extras` (propagated verbatim to all subagents) and `paths` (SoT overrides used when reading prior artifacts).

## Workflow

### Phase 0 — Pre-flight

- Verify the task entry exists. Scan every `docs/planning/epic-*-tasks.yaml`; the first match wins. If absent → abort with the message above.
- Capture `epic_id` from the matching file's name. Cross-check that the same epic id appears in `docs/planning/epics.yaml`; if not, abort with both paths.
- Verify `.claude/ruleset/` contains all 18 canonical Rule files. If any are missing, list them and abort — the reviewer cannot be dispatched without the full Ruleset.
- Confirm `.claude/stack.yaml` exists and parses. If absent, abort with: `stack.yaml missing. Run /000-prd-refine to bootstrap the project.`
- Parse the YAML toggle block in `.claude/ruleset/git-workflow.md`. Read `default_branch` (fallback `main`), `allow_commit_to_main` (fallback `false`), and `auto_fix_on_review_fail` (fallback `true`).
<!-- FREEZE:IF allow_commit_to_main -->
- **Branch check.** `allow_commit_to_main: true` — there is no task branch. Review against the prior commit's parent — set `<base>` to the parent of the implementer's commit (`02-impl.json.payload.commit_sha^`). Warn the user once: `Reviewing commit <sha> against its parent.`
<!-- FREEZE:ELSE -->
- **Branch check.** `allow_commit_to_main: false` — confirm the current branch is the task branch (commonly `task/<task-id>-<slug>`). If the current branch is the default branch, abort with: `On <default_branch>; expected task branch. Did /002-implement run?`
<!-- FREEZE:ENDIF -->
- **Verifier gate check.** Read `.claude/runs/{epic_id}/{task_id}/03-verify.json`. If the file is missing or `status != "ok"`, abort with: `Run /003-verify-dod first.` Additionally, if `.claude/runs/{epic_id}/{task_id}/03-design-verify.json` exists AND its `status != "ok"`, abort with the same message: `Run /003-verify-dod first.` The design-verify sibling artifact is produced by `/003-verify-dod` when `stack.yaml.design_verify.type == "prompt"`; it is append-only and lives alongside `03-verify.json` rather than mutating it. Rationale: review only runs after DoD passes — otherwise Findings would compound with infrastructure noise (failing gates leak through as spurious reviewer Findings). This pre-flight gate is **preserved verbatim** under both branches of the `auto_fix_on_review_fail` toggle below; self-heal does not bypass it.
### Phase 1 — Dispatch reviewer subagent (initial review)

Use the **Task tool** with `subagent_type: "reviewer"`. Inject the following into the subagent prompt body (verbatim, no `@`-includes):

1. **Task identity** — `task_id`, `epic_id`, and the full task YAML entry from `epic-{id}-tasks.yaml` (id, slug, title, status, `domain_scenarios`, `atdd_spec`, acceptance, notes).
2. **Branch base** — the resolved `<base>` ref for `git diff` (the default branch, or the implementer commit's parent under the solo preset). Instruct the reviewer to compute the diff with `git diff <base>...HEAD` and to read every changed file in full (line-level diff context is insufficient for cross-file checks).
3. **Verbatim Ruleset** — for each of the 18 files in `.claude/ruleset/`, paste the file content prefixed by a header line `--- <filename>.md ---`. Order alphabetically. Do not summarise, do not omit. The reviewer enforces every active Rule.
4. **`stack.yaml.extras`** — paste the `extras` mapping verbatim under a header `--- stack.yaml.extras ---`. Stack-specific quirks (e.g. `bash_buffering_warning`, `user_ping_interval_minutes`) propagate via this channel.
5. **Prior phase artifact paths** — list the absolute paths to `01-plan.json`, `02-impl.json`, `03-verify.json`, and every `05X-feedback-impl.json` present. The reviewer reads them directly (filesystem-only subagent comms per CONTEXT.md "Subagent chain"); do not paste their contents.
6. **Output contract** — instruct the reviewer to write its result to `.claude/runs/{epic_id}/{task_id}/04-review.json`, validated against `schemas/run-phase.schema.json`. Top-level `status` ∈ `{ "ok", "fail" }`. The schema (`run-phase.schema.json` `phase: "review"` branch) requires a **top-level `findings: []`** array on every review artifact, regardless of status — pass it as a mirror of `payload.findings` (empty array `[]` when `status: "ok"`). The canonical Violation set lives in `payload.findings`; the top-level field is a schema-compliance duplicate. Payload shape:
   - `status: "ok"` → `payload.rules_checked` (array of rule slug strings, e.g. `["accessibility", "api-design", "architecture", "code-style", ...]` — each entry is a Rule filename without the `.md` suffix or a cross-cutting check name), `payload.files_reviewed` (array of paths), `payload.findings: []` (empty). Top-level `findings: []` mirrors this empty array.
   - `status: "fail"` → `payload.findings` (non-empty array, the **Violations** set — these drive Phase 2; this is the canonical location). Each finding object: `{ rule: "<filename>.md", location: "<path>:<line>", message: "<one-line description>", severity: "Critical" | "High" | "Medium" | "Low" }`. Top-level `findings` mirrors `payload.findings` verbatim (schema compliance). Additionally, `payload.refactoring_suggestions` MAY be present — these are **advisory only** and never trigger Phase 2.

The reviewer is **read-only**. It does not edit files, does not run `git`, does not stage anything. Source-code fixes are produced by the `feedback-implementer` subagent in Phase 2 below; epic-level user feedback rounds remain the job of `/005-implement-feedback`.

Parse `.claude/runs/{epic_id}/{task_id}/04-review.json` and validate it against `schemas/run-phase.schema.json`. If validation fails, halt with the path and the validator error.

- **`status: "ok"`** — review clean on the first pass. Print:
  ```
  Code review ok — <rules_checked> rules checked, 0 findings.
  ```
  Branch on invocation context:
  - If chained from `/002-implement`: the parent reads `04-review.json` and continues to the merge proposal automatically. This command exits here.
  - If standalone: print `Next: /006-merge <task-id>`.

- **`status: "fail"`** — proceed to the self-heal block below.

<!-- FREEZE:IF auto_fix_on_review_fail -->

### Phase 2 — Apply Fixes (feedback-implementer subagent)

When `04-review.json.status == "fail"` and `auto_fix_on_review_fail: true`, dispatch the `feedback-implementer` subagent to apply the Violations. Use the **Task tool** with `subagent_type: "feedback-implementer"`. Inject into the subagent prompt body:

1. **Task identity** — `task_id`, `epic_id`, and the full task YAML entry. Same shape as Phase 1.
2. **Violations to apply** — the `payload.findings` array from the **latest** review artifact (`04-review.json` on iteration 1, `04c-review.json` on iteration 2, `04e-review.json` on iteration 3). Pass the array verbatim — including `rule`, `location`, `message`, and `severity` for each finding. The feedback-implementer treats every Violation as actionable regardless of severity tier; severity is informational metadata, not a filter.
3. **Ruleset subset** — bodies of every rule file whose slug appears in any failing finding's `rule` field. Pass the ruleset subset verbatim (same channel as the reviewer ruleset injection — paste each file content prefixed by `--- <filename>.md ---`). The `feedback-implementer` agent requires this per `agents/feedback-implementer.md`: it interprets rule prose during the fix, and an `@`-include does not propagate to subagents. Mirror /003's Phase 2 dispatch wording: resolve each unique `rule` slug to its `.claude/ruleset/<slug>` file and inject the body.
4. **Refactoring Suggestions are NOT injected.** Per the Discipline section below, `payload.refactoring_suggestions` from the review artifact are advisory only. They are surfaced to the user in the final render but never passed to the feedback-implementer in this loop.
5. **`stack.yaml.extras`** — paste verbatim under `--- stack.yaml.extras ---`. Same channel as Phase 1.
6. **Prior phase artifact paths** — `01-plan.json`, `02-impl.json`, `03-verify.json`, every `05X-feedback-impl.json`, and **every prior in-loop artifact** for this `/004` run (`04-review.json`, `04b-fix.json`, `04c-review.json`, …). The feedback-implementer reads them itself; paths only.
7. **Output contract** — instruct the subagent to write its result to `.claude/runs/{epic_id}/{task_id}/04b-fix.json` on iteration 1, `04d-fix.json` on iteration 2, `04f-fix.json` on iteration 3. Validate against `schemas/run-phase.schema.json`. Top-level `status` ∈ `{ "ok", "blocked" }` (per the schema's `phase: "feedback-impl"` constraint). Payload shape:
   - `status: "ok"` → `payload.files_changed` (array of paths the subagent modified), `payload.violations_addressed` (subset of input findings the subagent claims to have fixed), `payload.commit_sha` (the new commit, if the subagent committed).
   - `status: "blocked"` → `payload.reason` (string explaining why no fix could be produced — e.g. ambiguous Violation, edit conflict, missing context). Treat this as a terminal halt for the loop; do not advance to Phase 3 on a `blocked` fix.

The feedback-implementer is **the only writer of source code in this loop.** The main thread never edits files directly between Phase 1 and Phase 3.

### Phase 3 — Re-review

After Phase 2 produces a `04*-fix.json` with `status: "ok"`, re-dispatch the **reviewer** subagent with an identical injection shape to Phase 1 — verbatim Ruleset, refreshed `git diff <base>...HEAD`, `stack.yaml.extras`, and the updated list of prior-artifact paths (now including the just-written `04b-fix.json` etc.). Crucially, the diff is recomputed against `<base>` (not against the prior commit) so the reviewer sees the cumulative state, not just the delta from Phase 2.

The output contract changes only in the artifact name: iteration 1 writes `04c-review.json`, iteration 2 writes `04e-review.json`, iteration 3 writes `04g-review.json`. Schema and payload shape are identical to `04-review.json`.

Validate the new artifact against `schemas/run-phase.schema.json`. If validation fails, halt with the path and the validator error.

### Loop

The self-heal loop is bounded at **3 fix iterations**. The artifact sequence is fixed:

```
04-review.json    (Phase 1 — initial review)
04b-fix.json      (Phase 2 — fix iteration 1)
04c-review.json   (Phase 3 — re-review after iteration 1)
04d-fix.json      (Phase 2 — fix iteration 2)
04e-review.json   (Phase 3 — re-review after iteration 2)
04f-fix.json      (Phase 2 — fix iteration 3)
04g-review.json   (Phase 3 — re-review after iteration 3)
```

Loop termination:

- **Success** — any `04X-review.json` (where `X` ∈ `{ "", "c", "e", "g" }`) returns `status: "ok"`. Exit the loop and print the success render below.
- **Hard cap** — after `04g-review.json` is written and still `status: "fail"`, exit with final status `fail`. Print:
  ```
  Code review fail — self-heal exhausted (3 iterations). <N> Violations remain.

  <grouped violations render — same shape as the read-only branch below>

  Manual remediation: edit the working tree to address each Violation above, then re-run `/004-code-review <task-id>` to confirm fixes. (`/005-implement-feedback` is for epic-level user feedback, not Violation fixes.)
  ```
- **Fix-step terminal halt** — if any `04X-fix.json` itself returns `status: "blocked"` (the feedback-implementer could not produce a fix), do **not** advance to the next re-review. Print:
  ```
  Code review fail — feedback-implementer halted at <artifact> with: <payload.reason>.

  Manual remediation: edit the working tree to address each Violation above, then re-run `/004-code-review <task-id>` to confirm fixes. (`/005-implement-feedback` is for epic-level user feedback, not Violation fixes.)
  ```

Refactoring Suggestions accumulated across all review artifacts in the loop are surfaced once, at the end of the final render, regardless of terminal status. They never appear in fix-step input.

On loop success, the success render is:

```
Code review ok — <iterations> iteration(s), <fixes_applied> Violations auto-fixed, 0 remaining.
```

Branch on invocation context:
- Chained from `/002-implement`: control returns to the parent which auto-advances to the merge proposal.
- Standalone: print `Next: /006-merge <task-id>`.

<!-- FREEZE:ELSE -->

### Phase 2 — Read result (read-only mode)

`auto_fix_on_review_fail: false` — no Phase 2 fix dispatch, no Phase 3 re-review, no Loop. The reviewer's Findings are reported to the user and the command exits. This is the historical pre-self-heal contract.

When `04-review.json.status == "fail"`: group `payload.findings` by `rule` (alphabetical order on the Rule filename). For each Rule, print the Rule header once, then list its Violations:

```
<rule>:
  [<severity>] <location> — <message>
  [<severity>] <location> — <message>
```

Then list any `payload.refactoring_suggestions` under a separate `Refactoring Suggestions:` header — these are advisory only.

After the full list, print the suggested next step:

```
Manual remediation: edit the working tree to address each Violation above, then re-run `/004-code-review <task-id>` to confirm fixes. (`/005-implement-feedback` is for epic-level user feedback, not Violation fixes.)
```

Exit. The user edits the working tree manually and re-runs `/004-code-review`.

<!-- FREEZE:ENDIF -->

## Standalone vs chained

- **Chained** from `/002-implement`: the parent command reads the final `04X-review.json` (whichever letter the loop terminated on) after this command returns and decides whether to advance (to the merge proposal) or surface the failure. This command does not loop on its own when chained — the in-`/004` self-heal loop is internal; the chained `/002` loop is a separate, outer construct.
- **Standalone**: this command prints the final result, suggests the next slash command, and exits. The user invokes `/005-implement-feedback` or `/006-merge` manually.

Either way, the contract is the set of artifacts under `.claude/runs/{epic_id}/{task_id}/` matching `04*.json`. The terminal output is a convenience render of the same data.

## Discipline

- **Zero tolerance.** Every Violation is a blocker. There is no "advisory" Violation. Severity tiers (Critical / High / Medium / Low) are informational metadata only — they ride along on each finding to help the feedback-implementer prioritise edits and to inform the user's render, but they never gate the loop. A single `Low` severity Violation is enough to fail the review.
- **Refactoring Suggestions stay advisory.** They appear in `payload.refactoring_suggestions`, are surfaced in the terminal render, and are **never** passed into Phase 2's fix dispatch. The feedback-implementer only ever sees the `payload.findings` (Violations) array. This separation is load-bearing: it keeps the self-heal loop focused on contract violations and lets discretionary refactors remain a human decision.
- **Reviewer is read-only.** It does not edit files, run formatters, or commit. Any code change is the job of the feedback-implementer subagent (Phase 2) or, for epic-level user-feedback rounds, `/005-implement-feedback`. This separation keeps the review immutable as a forensic record.
- **Verbatim Ruleset injection.** All 18 Rule files MUST be pasted into the subagent prompt body — on Phase 1 **and on every Phase 3 re-review**. The `@`-include syntax does not propagate to subagents (per CONTEXT.md "Ruleset injection"); using it would silently strip the Ruleset and produce a vacuous review.
- **Cross-cutting reviewer checks live in the subagent prompt.** Test discipline (Domain-test + ATDD spec coverage), Step library discipline (shared steps, no per-test helpers), coverage policy, commit hygiene (Conventional Commits per `git-workflow.md`), vocabulary discipline (CONTEXT.md terms only — no "unit test", no "acceptance criteria", no "wip"), ADR-missing detection (hard-to-reverse decisions surfaced in the diff without a corresponding `docs/adr/NNNN-*.md`) — all of these live in `agents/reviewer.md`. This command does **not** enumerate them; it only dispatches.
- **Filesystem-only subagent comms.** The reviewer's output is the `04X-review.json` family. The feedback-implementer's output is the `04X-fix.json` family. The main thread never relies on a subagent's in-memory state or chat-style return value — it re-reads the artifact after the subagent returns.
- **Append-only runs history.** Never overwrite a prior `04*.json` within the same `/004` run. Each iteration writes a new letter-suffixed file (`04`, `04b`, `04c`, `04d`, `04e`, `04f`, `04g`); the prior artifacts remain on disk as a forensic trail. The only case where an existing `04-review.json` is replaced is when the user invokes `/004-code-review` **standalone on a new round** — for example, after a `/005-implement-feedback` epic-feedback round has produced new commits, the next `/004` run starts fresh from `04-review.json`. The historical narrative around "overwriting `04-review.json` after `/005` runs" predates the self-heal loop; under the new shape, only an explicit user re-run of `/004` (standalone, new round) overwrites — the in-`/004` self-heal never overwrites.
- **Max 3 fix iterations.** The cap is a hard ceiling. After `04g-review.json` is written, the loop exits regardless of status. There is no `--max-iterations` flag; the cap is structural.
- **Verifier gate is preserved across both toggle branches.** Whether `auto_fix_on_review_fail` is true or false, Phase 0 still aborts when `03-verify.json.status != "ok"` (and when `03-design-verify.json` exists with `status != "ok"`). Self-heal does not bypass the verifier gate — reviewing on a broken build still produces noise, regardless of whether we plan to auto-fix.

## Vocabulary discipline

Mirror `CONTEXT.md` exactly. Use only these terms when communicating with the user or writing artifacts:

- **Finding** / **Violation** — the canonical entries in `payload.findings`. The two terms are interchangeable within `/004` because the reviewer subagent's output uses both: "Finding" is the run-phase schema name; "Violation" is the user-facing label that distinguishes them from advisory Refactoring Suggestions. Never "issue", "blocker", "problem".
- **Refactoring Suggestion** — advisory-only entries in `payload.refactoring_suggestions`. Never "nit", "minor", "optional".
- **Rule** — a single-purpose policy file in `.claude/ruleset/`. Never "convention", "guideline", "principle", "policy".
- **Ruleset** — the 18-file collection. Never "rules folder", "standards", "style guide".
- **Severity** — `Critical` / `High` / `Medium` / `Low` on each Violation. Informational only. Never "priority", "blocker class".
- **Zero tolerance** — the Finding policy. Never "strict", "no-exceptions" as substitutes; the canonical phrase is "Zero tolerance".

Do not introduce synonyms. If you find yourself reaching for one, re-read the relevant CONTEXT.md entry.

## What the reviewer subagent does (informational)

This command does not enumerate review checks — they live in `agents/reviewer.md`. The list below is a reference for what the reviewer is expected to apply, **not a contract this command enforces**. If a check is missing from the reviewer prompt, fix the subagent definition; do not patch this command.

- **Per-Rule application** — for each of the 18 Rule files, the reviewer walks the changed files and applies the Rule's intent. Rules are free-form markdown; the reviewer interprets them, it does not lint them.
- **Test discipline** — verify the task added at least one Domain-test (per `testing.md`) and exactly one ATDD spec (per CONTEXT.md "ATDD spec"). Extra Domain-tests are fine; missing or duplicated ATDD specs are Violations.
- **Step library discipline** — new test verbs route through the shared Step library (per CONTEXT.md "Step library"). Inline Playwright/XCUITest selectors in spec bodies are Violations.
- **Coverage policy** — every Business scenario referenced in the task's `domain_scenarios` has at least one Domain-test asserting it. Missing coverage is a Violation.
- **Commit hygiene** — commit messages follow `git-workflow.md` (Conventional Commits by default). Mixed-concern commits, missing scope, or non-Conventional subjects are Violations.
- **Vocabulary discipline** — code comments, commit messages, log strings, and ATDD spec titles use CONTEXT.md vocabulary. "Unit test", "acceptance criteria", "wip", "blocker/non-blocker" anywhere in the diff are Violations.
- **ADR-missing detection** — if the diff contains a hard-to-reverse, surprising decision (new dependency, schema change, public API shape) with no corresponding `docs/adr/NNNN-*.md`, the reviewer emits a Violation pointing at the change and the missing ADR slot.

These checks compose with — they do not replace — the per-Rule walkthrough. A diff can pass every individual Rule and still fail on coverage, vocabulary, or ADR-missing.

## Failure modes

- **Task not found** → abort at Phase 0 with the path and id.
- **Ruleset incomplete** (fewer than 18 files in `.claude/ruleset/`) → abort at Phase 0 with the list of missing files.
- **`03-verify.json` missing or `status != "ok"`** → abort at Phase 0 with `Run /003-verify-dod first.` (preserved verbatim under both `auto_fix_on_review_fail` toggle branches).
- **Wrong branch** (not on the task branch under non-solo presets) → abort at Phase 0 with the expected vs actual branch.
- **Schema validation fails** on any `04*.json` → halt with the artifact path and the validator error.
- **Subagent invocation error** (Task tool failure, ruleset directory unreadable, diff command fails) → halt with the underlying error and the offending path. Do not retry silently.
- **Feedback-implementer halts** (`04X-fix.json.status == "blocked"`) → terminal halt for the loop; surface the `payload.reason` and instruct the user to manually edit the working tree and re-run `/004-code-review`. Do not advance to the next re-review.
- **3-iteration cap reached** (`04g-review.json.status == "fail"`) → exit with final `fail`, surface remaining Violations grouped by Rule, suggest `/005-implement-feedback`.

## Subagent chain position

```
/002-implement → /003-verify-dod (status: ok, self-healed) → /004-code-review (self-heals internally)
                                                                      |
                                                                      ├─ status: ok   → /006-merge (suggested or auto-chained)
                                                                      └─ status: fail → /005-implement-feedback (epic-level user-feedback round)
                                                                                              │
                                                                                              └→ loops back to /003-verify-dod
```

Two distinct loops are in play and must not be confused:

- **Intra-`/004` self-heal loop** — Phase 1 → Phase 2 → Phase 3, max 3 iterations, governed by `auto_fix_on_review_fail`. Fixes are mechanical applications of reviewer Violations by the `feedback-implementer` subagent. No user involvement.
- **Epic-level user-feedback loop** — `/005-implement-feedback` triggered after the intra-`/004` loop exhausts or when the toggle is off. This is a user-driven round that may add new tasks to `epic-{id}-tasks.yaml`, edit the PRD, or otherwise reshape the epic. It is not a finding-fixer.

The reviewer subagent definition lives in `agents/reviewer.md` (plugin-owned). The feedback-implementer subagent definition lives in `agents/feedback-implementer.md` (plugin-owned). This command owns only the dispatch + loop-orchestration + result-rendering surface — the review and fix logic themselves are the subagents' responsibility.

## Output rendering details

The terminal render is a deterministic projection of the final `04X-review.json` (plus a tally of in-loop iterations). The contract:

- One blank line between the headline and the suggested next step.
- Rules are listed in **alphabetical order on the filename** (`accessibility.md` before `api-design.md`, etc.). Violations within a Rule preserve the order they appear in `payload.findings`.
- The location format is `<path>:<line>` — never `<path> line <line>` or `<line> of <path>`. Reviewer output must match exactly; if it does not, halt with a schema-validation error rather than reformatting on the fly.
- Severity, when rendered, appears in square brackets before the location: `[Critical] src/foo.ts:42 — message`. Lowercase `critical`/`high`/etc. is a schema-validation error.
- The headline finding-count under `status: "ok"` uses the literal string `0 findings.` (lowercase, no severity, no parenthetical). Mirror CONTEXT.md "Finding policy".

## Re-run semantics

`/004-code-review` is idempotent against a clean tree: invoking it twice in a row on the same task with no intervening commits — and with `auto_fix_on_review_fail: false` — produces the same `04-review.json`. Re-running it is useful when:

- The user manually edits the Ruleset between runs (e.g. tightens `code-style.md`) and wants the new Rules applied.
- A previous run halted on a subagent error before writing `04-review.json`.

Under `auto_fix_on_review_fail: true`, re-running on the same task between epic-feedback rounds replays the self-heal loop from scratch — the `04`-series artifacts are overwritten on the new round (this is the only legal overwrite; in-loop iterations never overwrite each other). The prior round is preserved in git history via the commits the feedback-implementer made and via the `05X-feedback-impl.json` artifact (if any) that referenced it.

## Worked example

Given task `T-014` in epic `E-003` under the `small-team` preset (`auto_fix_on_review_fail: true`):

1. **Phase 0** — locate `docs/planning/epic-003-tasks.yaml`; find `id: T-014`. Confirm 18 files in `.claude/ruleset/`. Read `.claude/runs/E-003/T-014/03-verify.json` — `status: "ok"`. Current branch is `task/T-014-cancel-subscription`. `default_branch: main`. `auto_fix_on_review_fail: true`. Proceed.
2. **Phase 1** — reviewer dispatched. Writes `04-review.json` with `status: "fail"`, two Violations under `accessibility.md` and `observability.md`, one Refactoring Suggestion against `code-style.md`.
3. **Phase 2 (iteration 1)** — feedback-implementer dispatched with the two Violations (the Refactoring Suggestion is withheld). Subagent edits `src/billing/CancelButton.svelte` and `src/billing/cancel.ts`, commits, writes `04b-fix.json` with `status: "ok"` and `files_changed: [...]`.
4. **Phase 3 (iteration 1)** — reviewer re-dispatched against the refreshed diff. Writes `04c-review.json` with `status: "ok"`, 0 Violations. Loop exits.
5. **Final render**:
   ```
   Code review ok — 1 iteration, 2 Violations auto-fixed, 0 remaining.

   Refactoring Suggestions (advisory):
     code-style.md: src/billing/cancel.ts:42 — extract the retry constant.

   Next: /006-merge T-014
   ```
6. If `auto_fix_on_review_fail` were `false`, the command would have stopped at Phase 1, rendered the two Violations grouped by Rule with their severities, and printed `Next: /005-implement-feedback T-014`.

<!-- FREEZE:IF allow_commit_to_main -->
With `allow_commit_to_main: true` the only differences in the example are: no branch check, `<base>` is the implementer commit's parent, and the suggested merge step after a clean review reads `Task T-014 already on main; /006-merge is a no-op.`
<!-- FREEZE:ENDIF -->

## Why review runs after verify, not before

The chain order `/003-verify-dod → /004-code-review` is deliberate. Gates run first because:

- A failing gate (lint, typecheck, security scan) often produces collateral diffs that look like Rule violations to a reviewer. Running review on top of a broken build surfaces noise that disappears the moment the gate is fixed.
- The reviewer cannot meaningfully assess test discipline if the test suite does not currently pass — a missing assertion looks identical to a passing one when the file does not compile.
- Violations from review are expected to be substantive (architecture, vocabulary, ADR-missing). Violations from review on a broken build are usually downstream of the gate failure, which wastes a self-heal iteration.

Phase 0 enforces this by hard-aborting when `03-verify.json` is missing or failing. The error message points the user at `/003-verify-dod` rather than offering a `--force` flag — there is no scenario where reviewing a build-broken tree produces useful output, and the self-heal loop would burn its 3-iteration budget on noise.
