---
name: verification-loop-v1
description: Carries out a task and has it checked by reviewers who did not do the work, fixing and re-checking until nothing is left outstanding or the round limit is reached. Use when a task must satisfy both what was asked for and what was meant before it can be accepted.
metadata:
  inputs: "task: str"
  output: VerificationResult
  types: "./scripts/contracts.py"
---

Every subagent receives the task exactly as the person who asked for it wrote it.

Subagent: Worker (→ `WorkReport`)

Carry out the task in full.

## Check the work

Check the work with these two subagents in parallel. Each reaches its findings from what the work produced; the worker's report is context, not evidence.

Subagent: Instruction Reviewer (→ `InstructionReview`)

Separate the task into the individual things it asks for, and establish for each whether it was carried out.

Subagent: Outcome Reviewer (→ `OutcomeReview`)

Establish what success means for the person who asked, rather than what the task literally says, then judge whether what the work produced achieves it.

Anything a review does not record as done or passing is outstanding.

## Fix and check again

Check at most five times unless the person who asked for the task agrees to more.

- If nothing is outstanding, the work is verified and the result is produced.
- If something is outstanding and fewer than five checks have run, fix it and check again.
- If something is outstanding after the fifth check, present the open findings and what another round would attempt, and ask whether to carry on. Continue only on a yes; otherwise the result is produced with those findings unresolved.

Subagent: Fixer (→ `WorkReport`)

Settle every outstanding finding and leave work that already passed untouched. Where a finding is itself mistaken, say so with the evidence instead of acting on it.

## Produce the verification result

Report the verification result.
