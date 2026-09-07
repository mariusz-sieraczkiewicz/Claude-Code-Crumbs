# Modification report — verification-loop → verification-loop-v1

## Moved into the typed contract (`contracts.py`)

Everything that was a data shape written out as prose or inline JSON is now a Pydantic
type, and the skill body names the type instead of its fields:

- The two inline JSON schemas for the verifiers (instruction entries with id, status,
  evidence and fix hint; outcome criteria with pass/fail/concern plus an overall verdict
  and summary) → `InstructionReview` / `OutcomeReview` and their per-item types.
- The worker report contents (what was done, files created or modified with absolute
  paths, what was skipped and why, ambiguities resolved) → `WorkerReport`.
- The fixer report contents (before/after per fix, disputed findings with evidence)
  → `FixReport`.
- The final report contents (pass or stop-at-cap, iteration count, list of changes,
  remaining issues) → `LoopResult`, saved as `result.yaml`.
- The verbatim task → `Task`.

## Deleted

- **The ASCII loop diagram.** It restated the phase order that the phase headings
  already give.
- **The per-iteration file inventory** (`worker.log`, `worker-report.md`,
  `verifier-instructions.{log,json}`, `verifier-outcomes.{log,json}`,
  `fixer.{log,report.md}`, `task.md`, `status.md`, `iter-N/`). These describe how
  results are stored and passed between phases, which the model handles from the
  workspace declaration in the frontmatter.
- **The three scripted status lines** ("Worker done. Modified N files. Verifying.",
  "Instructions: X/Y done. Outcomes: …", and "Update `status.md` after every phase")
  → one rule at the top: tell the person the outcome of each phase.
- **"Trust failing verifier over passing one when they disagree."** The decision rule
  already requires both verifications to be clean, so a single failure blocks the exit.
- **"Never skip a verifier run"** and **"Never let worker/fixer self-verify"** as a
  separate guardrail block. Verification is an unconditional phase, and the worker is
  already told not to check its own work.
- **"Spawn 1 `general-purpose` subagent" / "Spawn 2 subagents simultaneously" /
  "parallel, single message"** — mechanics of launching subagents, which the model knows.
- **"Read `worker-report.md`"**, **"use `fix_hint` as a starting point"**, and
  **"return to Phase 2 with the fixer report as the worker report input"** — plumbing
  between phases that follows from the loop itself.
- **"Phase 1 / 2 / 3 / 4" numbering** — the order is the order of the sections.

## Rephrased

- **Description.** Was a summary of the mechanics ("execute in a worker subagent,
  verify in parallel, fix, repeat until clean or max 5 iterations"). Now states what
  the skill does and when to reach for it.
- **Verifier briefs.** "Checks every discrete instruction was executed" and its
  numbered steps became one instruction naming what the subagent must establish and on
  what basis (the produced work, not the report about it). Same for the outcome
  verifier, keeping the one point that carries weight: judge achievement, not existence.
- **"Empty/missing `.log` = silent failure — surface to user."** Now says what to
  conclude: a subagent that leaves no work log has failed silently, so its phase must
  not be counted as complete.
- **Input and output** are now declared as typed data at the start and the end.

## Kept

- One worker, two independent verifications in parallel, a fixer, and a repeat.
- The orchestrator never does the task itself.
- The worker never checks its own work.
- The instruction/outcome split — they answer different questions and can disagree.
- The cap of 5 iterations and the complete set of exit branches.
- The workspace.

## Contradictions in the source and how they were resolved

1. **Where the fixer writes.** The workspace section put the fixer's files inside the
   same iteration folder as the worker's; the fixer phase sent the fixer to the *next*
   iteration folder. Resolved by removing the folder mechanics altogether — the
   iteration count is what the loop needs, not the directory layout.

2. **What happens at iteration 5.** The guardrails said the cap holds only "without
   user permission" (so it can be lifted); the decide phase said stop and report.
   Resolved in favour of stopping and reporting every unresolved issue, with
   continuation possible only if the person asks for it — this keeps both statements
   true and leaves the decision with the person rather than with the loop.

3. **"Thrashing = escalate, don't grind"** had no condition and no defined action. It
   was first dropped as unactionable, then restored during verification as a proper
   branch: an iteration that resolves nothing ends the loop. Without it the loop grinds
   to the cap even when the fixer is making no headway, which is the behaviour the
   original guardrail existed to prevent.

## Verification

Four rounds ran, each with a fresh subagent that read only the authoring rules, the
original skill, and the two sculpted files.

**Round 1 — 6 issues.** Prose in the worker and fixer sections still spelled out the
fields of their own result types; the silent-failure rule still pointed at a log file
the sculpt no longer asks anyone to write; the outcome verifier listed two obvious
inspection actions; and the types file carried a roll-up verdict and a boolean that were
both derivable from the lists beside them. All six removed.

**Round 2 — 7 issues.** The stop-at-the-cap branch did not say whether the result is
still produced; the iteration unit was unnamed, so the count was ambiguous; the
description stopped at "checks" and omitted fixing and repeating; the anti-thrashing
exit was missing; the two verification result types described the same two fields
inconsistently; one field description restated its own field name; and the "Worker" and
"Fixer" headings only repeated the subagent line under them. All seven applied.

**Round 3 — 3 issues.** The anti-thrashing branch added in round 2 had been placed last,
where the branch above it already matched the same state — it could never fire, and the
two branches contradicted each other. Moved to second position, which makes all four
branches reachable and mutually exclusive. The fixer sat under a heading that announced
only deciding, so the heading became "Decide and fix". One clause repeated the standing
instruction to keep the person informed and was cut.

**Round 4 — no issues.** Final state confirmed conformant.
