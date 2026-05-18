---
description: Run every DoD gate from stack.yaml.gates via the verifier subagent. Zero tolerance. Standalone-invokable or chained from /002-implement.
argument-hint: <task-id> [--epic-close]
---

Run the Definition-of-Done check for **$ARGUMENTS** by dispatching the `verifier` subagent against every gate declared in `.claude/stack.yaml.gates`. **Zero tolerance**: any gate that exits non-zero, any rule violation surfaced by a gate, is a blocker Finding. This command never edits code — fixes are the job of `/005-implement-feedback`.

This command can be invoked **standalone** (user types `/003-verify-dod T-001`) or **chained** (parent `/002-implement` or `/002-auto-implement` runs it as part of the per-task loop). The on-disk contract is identical in both modes: the verifier emits `runs/{epic_id}/{task_id}/03-verify.json`, validated against `schemas/run-phase.schema.json`. Standalone exit prints a human summary; chained exit returns control to the parent, which reads the JSON.

## Modes

1. **Per-task** (default) — `/003-verify-dod T-NNN`. Runs every gate in `stack.yaml.gates` **except** `atdd_specs` and `journeys`. ATDD specs are reserved for **epic close-out** (a task ships its spec file but the spec is not executed until the epic is complete — see `CONTEXT.md` ATDD spec entry). Journeys are reserved for **environment promotion** (see CONTEXT.md Journey entry).
2. **Epic close-out** — `/003-verify-dod T-NNN --epic-close`. Adds `atdd_specs` to the gate run (so every task's spec executes against real or near-real infrastructure). **Still skips** `journeys` — those run only from `/007-promote` as the smoke gate against staging/prod.

The mode is purely additive over the gate set. The discipline, the schema, and the verifier subagent are identical.

## Inputs

- **`<task-id>`** — `$ARGUMENTS` positional (e.g. `T-001`). Optional trailing `--epic-close` flag toggles epic-close-out mode.
- **`docs/planning/epic-{id}-tasks.yaml`** — locate the task by scanning every `epic-*-tasks.yaml`. The first match wins; capture its `epic_id`. If not found anywhere, abort with: `Task <task-id> not found in any epic-*-tasks.yaml. Run /001-plan first.`
- **`docs/planning/epics.yaml`** — informational only. The verifier does **not** re-author or re-check Business scenarios; that mapping belongs to `/001-plan` and `/004-code-review`. Read it only if the gate output references a scenario name.
- **`.claude/stack.yaml`** — read `gates`, `paths`, `extras`, `design_verify`. The `extras` block is propagated verbatim to the verifier (per CONTEXT.md "Ruleset injection" — same channel as ruleset content).
- **`.claude/ruleset/*.md`** — **all 18 canonical rule files**, verbatim-loaded into memory for subagent injection. No `@`-include — content is pasted into the verifier prompt body (CONTEXT.md "Ruleset injection").
- **Prior phase files** under `.claude/runs/{epic_id}/{task_id}/`:
  - `01-plan.json` (planner output — task's `domain_scenarios`, `atdd_spec` path, file list).
  - `02-impl.json` (implementer output — commit hash, file list actually touched, ATDD spec path written, branch name).
  - Any `05*-feedback-impl.json` (one per prior feedback iteration — read in numeric/alphabetic order so the verifier sees the latest state, with letter-suffixed reruns ordered `05a`, `05b`, `05c`).
  The command passes the **paths** to the verifier; the subagent reads them itself (avoids ballooning the dispatching prompt). The verifier may also pass the file list (from `02-impl.json` + any `05*`) to gates that accept a scoped path argument — but most gates run project-wide regardless, and that is the intended behaviour.

## Workflow

### Phase 0 — Pre-flight

- Resolve `task_id` and `epic_id`. Abort patterns as above if either cannot be resolved.
- Confirm `.claude/stack.yaml` exists and parses. If absent, abort with: `stack.yaml missing. Run /000-prd-refine first.`
- Confirm at least one gate in `stack.yaml.gates` is non-null. If **every** gate is null, abort with: `No gates configured in stack.yaml.gates; DoD would trivially pass — but this is suspicious. Edit .claude/stack.yaml to enable at least lint + typecheck + domain_tests before re-running /003-verify-dod.` (Trivial-pass is treated as a configuration bug, not as a success.)
- Confirm `.claude/ruleset/` contains all 18 canonical rule files. If any are missing, list them and abort — the verifier cannot be dispatched without the full ruleset (some gates reference rule sections by name in their error output and the subagent needs the full text to map them back).
- Confirm `runs/{epic_id}/{task_id}/01-plan.json` and `02-impl.json` exist. If either is missing, abort with: `Phase prerequisites missing for <task-id>: <path>. Run /002-implement first.`
- Parse the trailing `--epic-close` flag. If present, set `epic_close = true`.
- Compute the **effective gate set**:
  - Always include: every non-null gate **except** `atdd_specs` and `journeys`.
  - If `epic_close = true`: also include `atdd_specs` when non-null.
  - **Never** include `journeys` here. Journeys are the smoke gate at promotion (see Modes).
- If `epic_close = true` but `stack.yaml.gates.atdd_specs` is null, surface a warning to the user: `--epic-close requested but stack.yaml.gates.atdd_specs is null. Proceeding without ATDD spec execution. This is almost certainly a misconfiguration.` Do **not** abort — the user may be running close-out on a project that genuinely has no ATDD layer (rare, but legal).

### Phase 1 — Dispatch verifier subagent

Use the Task tool with `subagent_type: "verifier"`. The dispatch payload contains:

- `task_id`, `epic_id`.
- `epic_close` boolean (so the verifier knows whether to run `atdd_specs`).
- **Effective gate set** — list of `{name, command}` pairs from `stack.yaml.gates`, filtered as Phase 0 computed. Pass each gate's `name` (key in the YAML) alongside its `command` (the shell string) so the verifier can label Findings.
- **`stack.yaml` verbatim** — or at minimum the `gates`, `design_verify`, `extras`, and `paths` sections. The verifier may need `paths` to resolve relative gate commands (project may override `tests`, `src`, or `atdd_specs` paths); it propagates `extras` to any nested subagent (see Design-verify handling). `extras` is the documented escape hatch for stack-specific quirks (`bash_buffering_warning`, `user_ping_interval_minutes`, etc. — see CONTEXT.md "stack.yaml shape").
- **Ruleset verbatim** — all 18 files, concatenated, each prefixed with `--- <name>.md ---` and suffixed with `--- end <name>.md ---`. CONTEXT.md "Ruleset injection" requires this verbatim form; do not summarise, do not skip files, do not rely on `@`-references (they do not propagate reliably into subagents).
- **Prior phase file paths** — `01-plan.json`, `02-impl.json`, and every `05*-feedback-impl.json` found under `runs/{epic_id}/{task_id}/`, in lexicographic order (so `05a`, `05b`, `05c` are read in that order — matches the rerun numbering in CONTEXT.md "Runs directory"). The verifier opens them itself; the command does **not** inline the JSON content (it would bloat the dispatch prompt).

The verifier's contract (defined in its subagent prompt) is:

1. Run every gate in the effective set. Capture exit code, stdout, stderr.
2. For each non-zero exit, emit one or more `findings[]` entries, each with: `rule` (the gate name or the rule it enforces), `location` (file:line where available), `message` (condensed error), `evidence` (relevant stderr/stdout excerpt).
3. If `stack.yaml.design_verify.type == "prompt"`, emit a single `design_verify_prompt` finding pointing at the prompt file (this command handles it — see below).
4. Write `runs/{epic_id}/{task_id}/03-verify.json` with `status: "ok"` (zero findings) or `status: "fail"` (≥1 finding). Schema: `schemas/run-phase.schema.json`.
5. Never edit source code. Never run `/005-implement-feedback`. The verifier is **read-only**.

### Phase 2 — Read result

Open `runs/{epic_id}/{task_id}/03-verify.json` and branch on `status`:

#### `status: "ok"`

Print a tight summary to the user (counts only, no per-gate noise):

```
DoD ok — <N> gates run, <N> passed, 0 findings.
```

Suggest the next step depending on invocation context:

- **Chained from `/002-implement`** (parent will detect `status: "ok"` itself): no suggestion needed; control returns to the parent which auto-advances to `/004-code-review` (or to merge proposal if `auto_invoke_review: false` in `git-workflow.md`).
- **Standalone**: suggest `/004-code-review <task-id>` next, or `/006-merge <task-id>` if `git-workflow.md` has `auto_invoke_review: false`.

#### `status: "fail"`

Print the finding count followed by a condensed list, one line per finding:

```
DoD fail — <N> findings.

  [<rule>] <location> — <message>
  [<rule>] <location> — <message>
  ...
```

Truncate `message` at ~120 chars. Do **not** dump full stderr; the JSON has it for forensic reading.

Suggest the next step:

- **Chained**: parent will see `status: "fail"` and invoke `/005-implement-feedback <task-id>` itself; do not re-suggest.
- **Standalone**: suggest `/005-implement-feedback <task-id>` to address the findings, then re-run `/003-verify-dod <task-id>`.

The command exits after printing. It does **not** loop, retry, or auto-invoke `/005`. Looping is owned by `/002-implement` and `/002-auto-implement` (CONTEXT.md "Subagent chain" — the chain is iterative, but each command in it is single-shot).

### Phase 3 — Schema validation

Before declaring Phase 2 done, validate `03-verify.json` against `schemas/run-phase.schema.json`. If validation fails:

- Do **not** delete or rewrite the file (the verifier may have written useful Findings even if a schema field is malformed).
- Print: `verifier emitted runs/{epic_id}/{task_id}/03-verify.json but it fails schema validation: <error>. Treating run as fail.`
- Treat the run as `status: "fail"` for the purpose of next-step suggestion.

A schema-failing verifier output is a bug in the subagent prompt, not in the project. Surface it so the user can file an issue against the plugin.

## Design-verify handling

`stack.yaml.design_verify` declares the project's design-fidelity gate. It is special-cased because it has two forms:

- **`type: "script"`** — an executable (e.g. `swiftlint --strict` with custom rules, a Python `design_check.py`). The verifier treats it like any other gate: run, check exit code, capture findings. **No extra handling in this command.**
- **`type: "prompt"`** — a markdown file containing instructions for an LLM-driven design check (e.g. "compare diff against `docs/DESIGN.md` token table; flag any deviation"). The verifier cannot execute prose — it instead emits a single `design_verify_prompt` finding pointing at the prompt file. This command then:
  1. Reads the prompt file's full content.
  2. Computes the diff for the task (compare working tree against the branch base recorded in `02-impl.json`).
  3. Spawns a **separate general-purpose subagent** via the Task tool, with `subagent_type: "general-purpose"`. The prompt content is the subagent's instructions; the diff is the input. Inject `stack.yaml.extras` verbatim (same channel as the verifier).
  4. Collects the general-purpose subagent's findings (it returns the same `findings[]` shape).
  5. Appends them to `03-verify.json.findings`.
  6. Re-evaluates `status`: if any new findings landed, flip to `"fail"`; if not, keep `"ok"`.
  7. Re-writes the JSON.

This indirection exists because `verifier` is a small, gate-focused subagent and design checks frequently need a broader LLM with general code-reading capability. The split keeps `verifier` deterministic and the design check tunable per-project via a markdown file.

## Standalone vs chained

This command behaves the same on-disk in both modes — the only difference is what happens **after** Phase 2 prints:

- **Standalone** (user typed `/003-verify-dod T-NNN` directly): print the summary and suggested next-step command. Exit. The user decides what to do next.
- **Chained** (parent `/002-implement` or `/002-auto-implement` invoked this command in-line): the parent does not need any printed output beyond a confirmation; it reads `03-verify.json` itself and routes accordingly. Avoid extra chatter — keep the summary tight so chained sessions stay readable.

A command does **not** know its invocation context with certainty (no flag passed by the parent — the chain is filesystem-mediated, per CONTEXT.md "Subagent chain"). The safe heuristic: always print the summary; the parent will simply ignore stdout and read the JSON.

Concretely, the per-mode behavioural contract is:

| Aspect | Standalone | Chained |
|---|---|---|
| Writes `03-verify.json` | yes | yes |
| Prints summary | yes | yes (parent ignores) |
| Suggests next command | yes | no (parent routes) |
| Loops on `fail` | no | no (parent loops `/005` → `/003`) |
| Honours `--epic-close` | yes | yes (parent passes flag through) |

## Discipline

- **Zero tolerance.** Any non-zero gate exit produces a blocker Finding. There are no severity tiers, no overrides, no "minor advisory" Findings (CONTEXT.md "Finding policy"). A single `lint` warning that the project's `lint` gate treats as an error is enough to fail DoD.
- The verifier is **read-only**. This command does not stage, commit, or modify any source file. Fixes route through `/005-implement-feedback`, which reads the same `03-verify.json` and edits the working tree.
- **All 18 ruleset files MUST be verbatim-injected** to the verifier, even though the verifier's primary job is running gate commands. Several gates encode rule names in their output (e.g. `tests.md:no-method-level-mocks`, `data-modeling.md:no-anemic-model`), and the verifier needs the full rule text to map gate-emitted rule names back to actionable Findings.
- Idempotent on re-run: re-invoking `/003-verify-dod` on the same task re-runs every gate and overwrites `03-verify.json`. Prior runs are not preserved beyond what the gates themselves produce as artifacts (e.g. lint cache, test reports under `runs/{epic_id}/{task_id}/artifacts/`).
- **No `journeys` execution here, ever** — including in `--epic-close` mode. Journeys are the **promotion** smoke gate and belong to `/007-promote`. They compose multiple Business scenarios across features (CONTEXT.md "Journey") and need a real production-like environment that the per-task DoD loop deliberately does not boot.
- **No source-of-truth mutation.** The verifier never edits `epics.yaml`, `epic-{id}-tasks.yaml`, `stack.yaml`, or any file under `.claude/ruleset/`. The only write is `03-verify.json` under `.claude/runs/`.
- **Gate exit code is the contract.** Stdout/stderr are evidence, but the verifier never tries to "interpret success" out of stderr lines when the exit code is non-zero. A failing gate stays failing even if its stderr happens to contain the word "passed".
- **No partial pass.** A gate either succeeds (exit 0, no findings) or contributes one or more Findings. There is no "ran but inconclusive" state. If a gate command itself crashes (e.g. missing binary), the verifier emits a Finding with `rule: "gate-misconfigured"` and the run is `fail`.

## Vocabulary discipline

This command mirrors the project glossary in `CONTEXT.md` exactly. Use these terms verbatim:

- **Finding** — a single blocker entry in `03-verify.json.findings`. Never "issue", "problem", "violation report".
- **Gate** — one entry in `stack.yaml.gates` (a shell command + exit-code contract). Never "check", "validation".
- **Status** — `ok` or `fail` on the run-phase JSON. Never "PASS/FAIL", "ALL_DONE", "GAPS_REMAINING".
- **Zero tolerance** — the binary blocker policy from CONTEXT.md "Finding policy". Never "critical/major/minor", never "blocker/non-blocker".

If a Finding's `message` is forwarded from a gate that uses different vocabulary (e.g. `swiftlint` says "violation"), preserve the gate's wording inside the message — but the surrounding command output (counts, next-step suggestions, abort messages) must use the project glossary.

## Examples

Per-task DoD on a TypeScript stack with five non-null gates (`lint`, `typecheck`, `domain_tests`, `build`, `security`):

```
/003-verify-dod T-014
```

Effective gate set: `lint`, `typecheck`, `domain_tests`, `build`, `security` (5 gates). `atdd_specs` is skipped (per-task mode). The verifier runs each, exits with `status: "ok"` if all return 0. Output:

```
DoD ok — 5 gates run, 5 passed, 0 findings.
Next: /004-code-review T-014
```

Epic close-out on the same task (terminal task of the epic):

```
/003-verify-dod T-014 --epic-close
```

Effective gate set adds `atdd_specs`. Now 6 gates run. If the ATDD spec for T-014 fails against the near-real test environment, the verifier emits one or more Findings and the output becomes:

```
DoD fail — 1 findings.

  [atdd_specs] tests/e2e/specs/checkout.spec.ts:42 — expected redirect to /confirmation, got /error
Next: /005-implement-feedback T-014
```

