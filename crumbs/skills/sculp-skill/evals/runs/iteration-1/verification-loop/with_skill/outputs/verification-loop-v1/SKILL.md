---
name: verification-loop-v1
description: Runs a task through a worker, has independent verifiers check both that every instruction was followed and that the produced work is good, and fixes what they find. Use when a task must be proven correct instead of assumed correct.
metadata:
  inputs: "task: Task"
  output: VerificationResult(`verification-result.yaml`)
  types: "./scripts/contracts.py"
  workspace: default
---

Orchestrate this workflow. Never carry out the task yourself.

No subagent verifies its own work.

After every stage, tell the participant what that stage found.

If any subagent returns no report, report which stage produced nothing and stop
without producing the verification result.

## Do the work

Subagent: Worker (→ `WorkReport`)

The Worker receives the verbatim task and carries it out in full.

## Verify the work

Verify with these two subagents in parallel. Both receive the verbatim task and
the work report, and both establish the facts themselves.

Subagent: Instruction Verifier (→ `InstructionVerification`)

Separate the task into its individual instructions and establish, for each one,
whether it was carried out.

Subagent: Outcome Verifier (→ `OutcomeVerification`)

Establish what success for this task looks like beyond its literal instructions,
and judge whether the produced work achieves it. Judge quality, not existence.

## Decide

Run at most 5 verify–fix rounds.

- If every instruction was carried out and the outcome passes, produce the result.
- If anything is missing, incomplete, or unsatisfactory and fewer than 5 rounds
  have run, fix it.
- If the fifth round is complete, produce the result and list every finding that
  is still unresolved.

## Fix the findings

The Fixer receives the verbatim task, the report under review, and both
verifications.

Subagent: Fixer (→ `WorkReport`)

Address every finding from both verifiers and change nothing that already
passes. Where a finding is mistaken, dispute it with evidence rather than
ignoring it.

Verify again, with the fixer's report as the work under review.

## Produce the verification result

Combine whether the work passed, the number of rounds, the changes made, and
the unresolved findings into `VerificationResult`.

Return the result and write the same result to `verification-result.yaml`.
