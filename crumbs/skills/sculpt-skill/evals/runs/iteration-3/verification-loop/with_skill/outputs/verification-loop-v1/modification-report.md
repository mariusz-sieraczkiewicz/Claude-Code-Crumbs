# Modification report — verification-loop → verification-loop-v1

Source: `verification-loop/SKILL.md`, 82 lines, one file.
Result: `verification-loop-v1/SKILL.md` (49 lines) + `verification-loop-v1/scripts/contracts.py`.

Progressive disclosure was considered and rejected: six short linear steps do not
justify reference files, so the skeleton stays in one file and only the types move out.

## Deleted

| Removed | Reason |
| --- | --- |
| The `## Loop` ASCII diagram (`worker → verifier-instructions + verifier-outcomes (parallel) → clean? done : fixer → re-verify`) | Restates the order the sections themselves impose. |
| "Never skip a verifier run. Never let worker/fixer self-verify." | The verify step is unconditional and the worker is separately told not to check its own work. |
| "Max 5 iterations without user permission. Thrashing = escalate, don't grind." | Duplicated the cap now carried by the decision branches. |
| The artifact filename inventory (`worker.log`, `worker-report.md`, `verifier-instructions.{log,json}`, `verifier-outcomes.{log,json}`, `fixer.{log,report.md}`) | A naming convention, not a rule that changes what any subagent does. |
| The requirement that each subagent write its **report** to a file | Each result now travels as its declared contract type; describing where a result is stored is not the skill's job. The running-log requirement is kept, because the silent-failure rule depends on it. |
| "Append running log to `worker.log` — one line per action, written regularly" and the matching fixer line | Logging mechanics; the requirement that a log exists is kept in one sentence. |
| "Spawn 1 `general-purpose` subagent", "Spawn 2 subagents simultaneously", "(parallel, single message)" | How subagents are launched is known to the model. Parallelism is now declared in prose before the two verifiers. |
| The worker's report specification ("what was done (bulleted), files created/modified (abs paths), anything skipped and why, ambiguities resolved") | Enumerated every field of `WorkerReport` one-for-one; the contract carries it. |
| "Do NOT self-verify" as a numbered step | Folded into the worker's paragraph. |
| The fixed status strings "Worker done. Modified N files. Verifying." and "Instructions: X/Y done. Outcomes: <overall>." | Wording of user-facing messages. |
| "Read `worker-report.md`" | A mechanical read of a result the orchestrator already has. |
| The numbered 1–4 step lists inside Worker, both Verifiers, and Fixer | Artificial micro-steps inside a single responsibility; each is now one paragraph. |
| "use `fix_hint` as starting point" and the `missing`/`partial`/`fail`/`concern` enumerations | Direct references to contract fields and their values. |
| The three `Final Report` items | Presentation of the result; replaced by the result type. |
| "Workspace path for inspection" | Execution detail; the official result must not carry it. |

## Moved into the typed contract (`scripts/contracts.py`)

The two inline JSON schemas and the prose describing report contents became Pydantic
types, so the skill body no longer names a single field:

- `verifier-instructions.json` → `InstructionReview` / `InstructionCheck`
- `verifier-outcomes.json` → `OutcomeReview` / `OutcomeCheck`
- `worker-report.md` contents → `WorkerReport`
- `fixer-report.md` before/after → `FixReport` / `Fix`, plus disputed findings
- `Final Report` → `VerificationResult`

Dropped from the schemas: the per-check `id` and the `summary` totals block
(`total`, `done`, `missing`, `partial`) — both derivable from the list of checks.

Descriptions were added only where a field name does not carry its meaning. The
load-bearing one is `OutcomeReview.overall`: "anything short of every check passing is
not a pass" is what stops the loop exiting with unaddressed concerns, and the original
carried it as `overall == "pass"` in prose.

## Shortened / rephrased

| Before | After |
| --- | --- |
| description: "Execute a task in a worker subagent, independently verify instruction compliance and outcome quality in parallel, fix issues, repeat until clean or max 5 iterations." | States what the skill does **and** when to use it, in plain words, without promising a guaranteed pass. |
| "Delegate work to subagents, verify independently, fix, repeat. You orchestrate — never implement." | "You orchestrate; you never do the work yourself." |
| Four separate statements that the task travels verbatim (workspace, worker, verifiers, fixer) | One: "Every subagent receives the task verbatim, never a summary." |
| "Empty/missing `.log` = silent failure — surface to user." | "A subagent that returns no result, or leaves its log empty, has failed silently — report which subagent failed and stop without producing a result." — names the consequence, which the original left open. |
| "Report status to the user after every phase." + "Update `status.md` after every phase." | One sentence covering both. |
| "**Verifier-instructions** — checks every discrete instruction was executed:" | `Subagent: Instruction Verifier (→ `InstructionReview`)` with role, task, data and result. |
| "Independently verify each — read files, grep, run checks (don't trust worker report)" | "Confirm this from the produced work itself, never from the report." — the tool list is inferable; the independence constraint is not. |
| Phase 3's clean-condition line plus three bullets | One governing sentence (failing verdict wins a disagreement) above three branches. |
| Headings "Phase 1 — Worker", "Phase 2 — Verifiers", "Phase 3 — Decide", "Phase 4 — Fixer" | Named by what happens: "Run the task", "Verify", "Decide", "Fix". |
| `## Workspace` as its own section | Folded into the opening block of constraints. |

## Kept because removing them changes the outcome

The orchestrator never implements. The task text travels verbatim. The two verifiers run
in parallel and judge the produced work, not the account of it. They ask different
questions — were the instructions carried out, versus was the intent achieved. A failing
verdict wins a disagreement. The cap is 5 iterations and the loop closes back to
verification after a fix. The fixer receives the account of the work so far plus the
findings, touches only what failed, and may dispute a finding with evidence. Each
iteration gets its own folder and a running log, and the user hears what happened after
each step.

## Deliberate change of behaviour

The original guardrail allowed exceeding 5 iterations "without user permission" while
Phase 3 said to stop at 5. v1 resolves the contradiction one way: it stops at 5 and
produces the result listing every unresolved problem. The escape hatch is gone.

v1 also anchors the counter, which the original expressed only through folder names
(`iter-N/`, fixer gets `iter-(N+1)/`): running the task is iteration 1, each fix begins
the next. Budget is one worker run plus at most four fixes — the same as the original.

## Verification

Four rounds ran. Each used a fresh subagent given the sculpting rules, the original skill,
the current version and this report, and forbidden from reading any file on disk so that
nothing outside those texts could colour its judgement. A Fixer subagent applied the
findings after each round.

**Round 1 — 15 findings, 13 accepted.**

1. The Fixer was the only subagent with no stated input data.
2. Re-verification after a fix had no defined input — the Verify step named the worker's
   report, but on later iterations the account of the work comes from the fixer.
3. The workspace path sat in the domain result, which the rules forbid.
4. `status.md` was doing two incompatible jobs: the running per-step log and the
   serialized official result, with no statement of whether the final write appended or
   replaced.
5. The cap branch both produced the official result and asked the user whether to
   continue, specifying no consequence for either answer.
6. The disagreement rule was a bullet inside the branch list, overlapping the other
   branches instead of governing them.
7. The silent-failure guard had been narrowed from the original's OR to an AND (it
   required both log and report to be missing), and nothing required a log to exist.
8. "the working system" was vaguer than the phrase it replaced and does not apply to
   non-software tasks.
9. "Store the task verbatim; every subagent receives that exact text, never a summary."
   stated one constraint three times.
10. "Then verify again." duplicated a decision branch.
11. The description promised a pass the skill cannot guarantee.
12. `fix_hint: str | None = Field(description=...)` was a required field despite the
    `| None`, because `Field()` had no default.
13. `OutcomeReview.overall`, `Fix.before`/`after`, `WorkerReport.work_done` and
    `VerificationResult.changes` lacked descriptions their names do not supply.

Two findings were rejected: the name/directory suffix question (deferred to round 2, where
it was decided) and a suggestion that "You orchestrate; you never do the work yourself."
is redundant — the second clause is the operative constraint.

**Round 2 — 9 findings, 8 accepted, including 2 regressions from round 1.**

1. *Regression.* Fixing finding 1 above gave the fixer the task and the findings but
   silently dropped the prior account of the work — the only inventory of what exists
   and where.
2. The silent-failure rule stated no consequence for the workflow, unlike every branch
   in Decide.
3. The worker paragraph enumerated all four `WorkerReport` fields in order, which the
   frontmatter rule forbids.
4. *Regression.* Requiring each subagent to write its report into the iteration folder
   described storage of a result that already travels as a declared type, and made the
   silent-failure guard ambiguous about whether it checks a file or a return value.
5. `VerificationResult.unresolved` was the last field left without a description.
6. "After each phase" pointed at "Phase N" headings that had been renamed away, and the
   verbatim-task rule sat under a "Prepare the workspace" heading it does not belong to.
7. `name: verification-loop` collided with the skill it was copied from.
8. The description said "reviewers" while the body said "verifiers".

One finding was rejected: that the verifiers' input list should also name the iteration
folder — the opening block already requires every subagent to log there.

**Round 3 — 1 finding, accepted.**

The skill counted iterations but never said what starts one. An agent could read the
worker run as iteration 1 (four fix rounds) or count only fix–verify cycles (five), giving
a different number of subagent runs and a different reported count. The original had
pinned this down through the `iter-N/` folder numbering that was deleted as a naming
convention — true of the filenames, but the numbering also carried the loop's anchor.
Fixed with one clause rather than by restoring the folder inventory.

**Round 4 — no issues.** The verifier walked the cap arithmetic (iteration 1 → fix starts
iteration 2 → … → fix starts iteration 5 → stop) and confirmed no off-by-one, no
unreachable state, no overshoot, and that the new clause introduced no redundancy or
conflict. Loop closed.
