---
name: verification-loop
description: Runs a task through a worker subagent, then checks independently that every instruction was carried out and that the result is good, fixes what is wrong, and repeats. Use when a task must be proven complete and correct, not only attempted.
metadata:
  types: "./contracts.py"
  workspace: ./.verification-loop/<UTC-timestamp>
---

# Verification Loop

Input (→ `Task`)

You orchestrate and never carry out the task yourself. Tell the person the outcome of each phase.

A subagent that returns no report has failed silently — do not treat its phase as complete.

Subagent: Worker (→ `WorkerReport`)

Carry out the task completely. Do not check your own work.

## Verification

Verify the work using these two subagents in parallel:

Subagent: Instruction Verifier (→ `InstructionReview`)

Break the task into its separate instructions and establish for each one whether it was carried out, by examining the produced work rather than the report about it.

Subagent: Outcome Verifier (→ `OutcomeReview`)

Establish what success means for this task, then judge whether the produced work achieves it. Existence is not achievement.

## Decide and fix

Run at most 5 work–verification iterations.

- If every instruction was carried out and every outcome criterion passes, produce the result and stop.
- If an iteration resolves nothing, record the unresolved issues in the result and stop.
- If anything is unresolved and fewer than 5 iterations are complete, run the fixer and verify again.
- If anything is unresolved after 5 iterations, record every unresolved issue in the result and stop. Continue only if the person asks for it.

Subagent: Fixer (→ `FixReport`)

Resolve every finding both verifications left open and change nothing that already passes.

Output (→ `LoopResult`(`result.yaml`))
