---
description: Code-review gate. Reviewer subagent reads verbatim-injected ruleset + branch diff and emits blocking findings. Zero tolerance.
argument-hint: <task-id>
---

Run the code-review gate for **$ARGUMENTS**. Dispatches the `reviewer` subagent with the verbatim-injected ruleset and the branch diff, then reads the resulting Findings. Zero tolerance: every Finding is a blocker.

This command is standalone-invokable. It is also auto-chained by `/002-implement` and `/002-auto-implement` after `/003-verify-dod` reports `status: ok`. The chaining mode does not change what this command does — only who reads `04-review.json` afterwards.

## Inputs

- **`<task-id>`** — passed as `$ARGUMENTS` (e.g. `T-014`). Required positional argument.
- **`docs/planning/epic-{id}-tasks.yaml`** — locate the task entry by scanning every `epic-*-tasks.yaml` under `docs/planning/`. The matching file's name yields the `epic_id` (e.g. `epic-003-tasks.yaml` → `E-003`). If the task is not found, abort with: `Task <task-id> not found in any epic-*-tasks.yaml. Run /001-plan first.`
- **`.claude/ruleset/*.md`** — all 18 canonical Rule files, **verbatim-loaded** into memory for subagent injection. The Ruleset is the single source of truth for review checks. Per CONTEXT.md "Ruleset injection", content is pasted into the subagent prompt body — never via `@`-include, which does not always propagate to subagents.
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
- Parse the YAML toggle block in `.claude/ruleset/git-workflow.md`. Read `default_branch` (fallback `main`) and `allow_commit_to_main` (fallback `false`).
- **Branch check.**
  - If `allow_commit_to_main: false` (typical for `small-team`, `oss`, `enterprise`): confirm the current branch is the task branch (commonly `task/<task-id>-<slug>`). If the current branch is the default branch, abort with: `On <default_branch>; expected task branch. Did /002-implement run?`
  - If `allow_commit_to_main: true` (typical for the `solo` preset): there is no task branch. Review against the prior commit's parent — set `<base>` to the parent of the implementer's commit (`02-impl.json.payload.commit_sha^`). Warn the user once: `Solo preset: reviewing commit <sha> against its parent.`
- **Verify gate check.** Read `.claude/runs/{epic_id}/{task_id}/03-verify.json`. If the file is missing or `status != "ok"`, abort with: `Run /003-verify-dod first.` Additionally, if `.claude/runs/{epic_id}/{task_id}/03b-design-verify.json` exists AND its `status != "ok"`, abort with the same message: `Run /003-verify-dod first.` The design-verify sibling artifact is produced by `/003-verify-dod` when `stack.yaml.design_verify.type == "prompt"`; it is append-only and lives alongside `03-verify.json` rather than mutating it. Rationale: review only runs after DoD passes — otherwise Findings would compound with infrastructure noise (failing gates leak through as spurious reviewer Findings).
- Ensure `.claude/runs/{epic_id}/{task_id}/artifacts/` exists for transient subagent outputs.

### Phase 1 — Dispatch reviewer subagent

Use the **Task tool** with `subagent_type: "reviewer"`. Inject the following into the subagent prompt body (verbatim, no `@`-includes):

1. **Task identity** — `task_id`, `epic_id`, and the full task YAML entry from `epic-{id}-tasks.yaml` (id, slug, title, status, `domain_scenarios`, `atdd_spec`, acceptance, notes).
2. **Branch base** — the resolved `<base>` ref for `git diff` (the default branch, or the implementer commit's parent under the solo preset). Instruct the reviewer to compute the diff with `git diff <base>...HEAD` and to read every changed file in full (line-level diff context is insufficient for cross-file checks).
3. **Verbatim Ruleset** — for each of the 18 files in `.claude/ruleset/`, paste the file content prefixed by a header line `--- <filename>.md ---`. Order alphabetically. Do not summarise, do not omit. The reviewer enforces every active Rule.
4. **`stack.yaml.extras`** — paste the `extras` mapping verbatim under a header `--- stack.yaml.extras ---`. Stack-specific quirks (e.g. `bash_buffering_warning`, `user_ping_interval_minutes`) propagate via this channel.
5. **Prior phase artifact paths** — list the absolute paths to `01-plan.json`, `02-impl.json`, `03-verify.json`, and every `05X-feedback-impl.json` present. The reviewer reads them directly (filesystem-only subagent comms per CONTEXT.md "Subagent chain"); do not paste their contents.
6. **Output contract** — instruct the reviewer to write its result to `.claude/runs/{epic_id}/{task_id}/04-review.json`, validated against `schemas/run-phase.schema.json`. Top-level `status` ∈ `{ "ok", "fail" }`. Payload shape:
   - `status: "ok"` → `payload.rules_checked` (array of rule slug strings, e.g. `["accessibility", "api-design", "architecture", "code-style", ...]` — each entry is a Rule filename without the `.md` suffix or a cross-cutting check name), `payload.files_reviewed` (array of paths).
   - `status: "fail"` → `payload.findings` (non-empty array). Each finding object: `{ rule: "<filename>.md", location: "<path>:<line>", message: "<one-line description>" }`.

The reviewer is **read-only**. It does not edit files, does not run `git`, does not stage anything. Fixes happen exclusively via `/005-implement-feedback`.

### Phase 2 — Read result

Parse `.claude/runs/{epic_id}/{task_id}/04-review.json` and validate it against `schemas/run-phase.schema.json`. If validation fails, halt with the path and the validator error.

Branch on `status`:

- **`status: "ok"`** — review clean. Print:
  ```
  Code review ✅ — <rules_checked> rules checked, 0 findings.
  ```
  Suggested next step:
  - If chained from `/002-implement` or `/002-auto-implement`: the parent reads `04-review.json` and continues to the merge proposal automatically. This command exits here.
  - If standalone: print `Next: /006-merge <task-id>`.

- **`status: "fail"`** — Findings present. Group `payload.findings` by `rule` (alphabetical order on the Rule filename). For each Rule, print the Rule header once, then list its Findings:
  ```
  <rule>:
    <location> — <message>
    <location> — <message>
  ```
  After the full list, print the suggested next step:
  ```
  Next: /005-implement-feedback <task-id>
  ```

## Standalone vs chained

- **Chained** from `/002-implement` or `/002-auto-implement`: the parent command reads `04-review.json` after this command returns and decides whether to advance (to the merge proposal) or spawn `/005-implement-feedback`. This command does not loop on its own when chained.
- **Standalone**: this command prints the result, suggests the next slash command, and exits. The user invokes `/005-implement-feedback` or `/006-merge` manually.

Either way, the artifact at `.claude/runs/{epic_id}/{task_id}/04-review.json` is the contract. The terminal output is a convenience render of the same data.

## Discipline

- **Zero tolerance.** Every Finding is a blocker. There are no severity tiers, no overrides, no "advisory" Findings. Per CONTEXT.md "Finding policy": one Finding = `status: "fail"`.
- **Reviewer is read-only.** It does not edit files, run formatters, or commit. Any code change is the job of `/005-implement-feedback`. This separation keeps the review immutable as a forensic record.
- **Verbatim Ruleset injection.** All 18 Rule files MUST be pasted into the subagent prompt body. The `@`-include syntax does not propagate to subagents (per CONTEXT.md "Ruleset injection"); using it would silently strip the Ruleset and produce a vacuous review.
- **Cross-cutting reviewer checks live in the subagent prompt.** Test discipline (Domain-test + ATDD spec coverage), Step library discipline (shared steps, no per-test helpers), coverage policy, commit hygiene (Conventional Commits per `git-workflow.md`), vocabulary discipline (CONTEXT.md terms only — no "unit test", no "acceptance criteria", no "wip"), ADR-missing detection (hard-to-reverse decisions surfaced in the diff without a corresponding `docs/adr/NNNN-*.md`) — all of these live in `.claude-plugin/agents/reviewer.md`. This command does **not** enumerate them; it only dispatches.
- **Filesystem-only subagent comms.** The reviewer's only output is `04-review.json`. The main thread never relies on the subagent's in-memory state or chat-style return value — it re-reads the artifact after the subagent returns.
- **Append-only runs history.** Never overwrite `04-review.json` from a prior run within the same task without first archiving. Re-running `/004-code-review` on the same task overwrites only after the user explicitly confirms — or after `/005-implement-feedback` has produced a new `05X-feedback-impl.json` (in which case the next review is a fresh round and overwriting is expected).
- **No retries on Finding production.** If the reviewer returns `fail`, do not re-dispatch hoping for a different verdict. The next move is `/005-implement-feedback`.

## Vocabulary discipline

Mirror `CONTEXT.md` exactly. Use only these terms when communicating with the user or writing artifacts:

- **Finding** — any issue surfaced by `/003-verify-dod` or `/004-code-review`. Never "violation", "issue", "blocker", "critical/major/minor".
- **Rule** — a single-purpose policy file in `.claude/ruleset/`. Never "convention", "guideline", "principle", "policy".
- **Ruleset** — the 18-file collection. Never "rules folder", "standards", "style guide".
- **Zero tolerance** — the Finding policy. Never "strict", "no-exceptions" as substitutes; the canonical phrase is "Zero tolerance".

Do not introduce synonyms. If you find yourself reaching for one, re-read the relevant CONTEXT.md entry.

## What the reviewer subagent does (informational)

This command does not enumerate review checks — they live in `.claude-plugin/agents/reviewer.md`. The list below is a reference for what the reviewer is expected to apply, **not a contract this command enforces**. If a check is missing from the reviewer prompt, fix the subagent definition; do not patch this command.

- **Per-Rule application** — for each of the 18 Rule files, the reviewer walks the changed files and applies the Rule's intent. Rules are free-form markdown; the reviewer interprets them, it does not lint them.
- **Test discipline** — verify the task added at least one Domain-test (per `testing.md`) and exactly one ATDD spec (per CONTEXT.md "ATDD spec"). Extra Domain-tests are fine; missing or duplicated ATDD specs are Findings.
- **Step library discipline** — new test verbs route through the shared Step library (per CONTEXT.md "Step library"). Inline Playwright/XCUITest selectors in spec bodies are Findings.
- **Coverage policy** — every Business scenario referenced in the task's `domain_scenarios` has at least one Domain-test asserting it. Missing coverage is a Finding.
- **Commit hygiene** — commit messages follow `git-workflow.md` (Conventional Commits by default). Mixed-concern commits, missing scope, or non-Conventional subjects are Findings.
- **Vocabulary discipline** — code comments, commit messages, log strings, and ATDD spec titles use CONTEXT.md vocabulary. "Unit test", "acceptance criteria", "wip", "blocker/non-blocker" anywhere in the diff are Findings.
- **ADR-missing detection** — if the diff contains a hard-to-reverse, surprising decision (new dependency, schema change, public API shape) with no corresponding `docs/adr/NNNN-*.md`, the reviewer emits a Finding pointing at the change and the missing ADR slot.

These checks compose with — they do not replace — the per-Rule walkthrough. A diff can pass every individual Rule and still fail on coverage, vocabulary, or ADR-missing.

## Failure modes

- **Task not found** → abort at Phase 0 with the path and id.
- **Ruleset incomplete** (fewer than 18 files in `.claude/ruleset/`) → abort at Phase 0 with the list of missing files.
- **`03-verify.json` missing or `status != "ok"`** → abort at Phase 0 with `Run /003-verify-dod first.`
- **Wrong branch** (not on the task branch under non-solo presets) → abort at Phase 0 with the expected vs actual branch.
- **Schema validation fails** on `04-review.json` → halt with the artifact path and the validator error.
- **Subagent invocation error** (Task tool failure, ruleset directory unreadable, diff command fails) → halt with the underlying error and the offending path. Do not retry silently.

## Subagent chain position

```
/002-implement → /003-verify-dod (status: ok) → /004-code-review
                                                      |
                                                      ├─ status: ok   → /006-merge (suggested or auto-chained)
                                                      └─ status: fail → /005-implement-feedback → loop back to /003-verify-dod
```

The reviewer subagent definition lives in `.claude-plugin/agents/reviewer.md` (plugin-owned). This command owns only the dispatch + result-rendering surface — the review logic itself is the subagent's responsibility.

## Output rendering details

The terminal render is a deterministic projection of `04-review.json`. The contract:

- One blank line between the headline (`Code review ✅` or the first Rule group) and the suggested next step.
- Rules are listed in **alphabetical order on the filename** (`accessibility.md` before `api-design.md`, etc.). Findings within a Rule preserve the order they appear in `payload.findings`.
- The location format is `<path>:<line>` — never `<path> line <line>` or `<line> of <path>`. Reviewer output must match exactly; if it does not, halt with a schema-validation error rather than reformatting on the fly.
- The headline finding-count under `status: "ok"` uses the literal string `0 findings.` (lowercase, no severity, no parenthetical). Mirror CONTEXT.md "Finding policy" — there is no "zero blocking findings" wording.

## Re-run semantics

`/004-code-review` is idempotent against a clean tree: invoking it twice in a row on the same task with no intervening commits produces the same artifact. Re-running it is useful when:

- The user manually edits the Ruleset between runs (e.g. tightens `code-style.md`) and wants the new Rules applied.
- A previous run halted on a subagent error before writing `04-review.json`.

Re-running after `/005-implement-feedback` is the normal chained case — the feedback round has produced new commits, so the diff is genuinely different and the new review is a fresh round. Overwriting `04-review.json` in that case is expected; the prior version is preserved in git history via the feedback artifact (`05X-feedback-impl.json`) that referenced it.

## Worked example

Given task `T-014` in epic `E-003` under the `small-team` preset:

1. **Phase 0** — locate `docs/planning/epic-003-tasks.yaml`; find `id: T-014`. Confirm 18 files in `.claude/ruleset/`. Read `.claude/runs/E-003/T-014/03-verify.json` — `status: "ok"`. Current branch is `task/T-014-cancel-subscription` (matches the configured pattern). `default_branch: main`. Proceed.
2. **Phase 1** — Task tool with `subagent_type: "reviewer"`. Inject task YAML, `git diff main...HEAD` base, 18 Ruleset files verbatim, `stack.yaml.extras`, and prior-artifact paths (`01-plan.json`, `02-impl.json`, `03-verify.json`). The reviewer reads the diff, applies every Rule's checklist, and writes `.claude/runs/E-003/T-014/04-review.json`.
3. **Phase 2** — `04-review.json` returns `status: "fail"`, `payload.findings: [{ rule: "accessibility.md", location: "src/billing/CancelButton.svelte:18", message: "Missing aria-label on confirm action." }, { rule: "observability.md", location: "src/billing/cancel.ts:42", message: "Log line includes user email — strip per security.md." }]`. The command renders:
   ```
   accessibility.md:
     src/billing/CancelButton.svelte:18 — Missing aria-label on confirm action.
   observability.md:
     src/billing/cancel.ts:42 — Log line includes user email — strip per security.md.

   Next: /005-implement-feedback T-014
   ```
4. If invoked standalone, the command exits here. If chained from `/002-implement`, the parent reads the same artifact and spawns `/005-implement-feedback T-014` itself.

Under the `solo` preset the only differences are: no branch check, `<base>` is the implementer commit's parent, and the suggested merge step is replaced with `Task T-014 already on main; /006-merge is a no-op.` after a clean review.

## Why review runs after verify, not before

The chain order `/003-verify-dod → /004-code-review` is deliberate. Gates run first because:

- A failing gate (lint, typecheck, security scan) often produces collateral diffs that look like Rule violations to a reviewer. Running review on top of a broken build surfaces noise that disappears the moment the gate is fixed.
- The reviewer cannot meaningfully assess test discipline if the test suite does not currently pass — a missing assertion looks identical to a passing one when the file does not compile.
- Findings from review are expected to be substantive (architecture, vocabulary, ADR-missing). Findings from review on a broken build are usually downstream of the gate failure, which wastes a feedback iteration.

Phase 0 enforces this by hard-aborting when `03-verify.json` is missing or failing. The error message points the user at `/003-verify-dod` rather than offering a `--force` flag — there is no scenario where reviewing a build-broken tree produces useful output.
