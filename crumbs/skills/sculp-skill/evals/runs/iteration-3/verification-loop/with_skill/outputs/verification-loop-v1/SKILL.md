---
name: verification-loop-v1
description: Runs a task in a worker subagent, has verifiers check it, and fixes what they find, repeating until it passes or the iteration cap is reached. Use when a task must be both completed and independently confirmed correct.
metadata:
  inputs: "task: str"
  output: VerificationResult(`verification-result.yaml`)
  types: "./scripts/contracts.py"
  workspace: default
---

# Verification Loop

You orchestrate; you never do the work yourself.
Every subagent receives the task verbatim, never a summary.
Running the task is iteration 1 and each fix begins the next iteration; give each iteration its own folder, and require each subagent to write its running log into that folder.

After each step below, tell the user what happened and record it in `status.md`.

A subagent that returns no result, or leaves its log empty, has failed silently — report which subagent failed and stop without producing a result.

## Run the task

Subagent: Worker (→ `WorkerReport`)

Carry out the task in full. Do not check your own work.

## Verify

Check the work using these two subagents in parallel, each receiving the task and the report of the subagent that last did the work:

Subagent: Instruction Verifier (→ `InstructionReview`)

Break the task into its separate instructions and establish for each one whether it was carried out. Confirm this from the produced work itself, never from the report.

Subagent: Outcome Verifier (→ `OutcomeReview`)

Determine what success for this task actually looks like, then judge whether the produced work achieves it. Run whatever can be run, and judge quality rather than existence.

## Decide

Where the verifiers disagree about the same point, treat the failing verdict as the correct one.

- If every instruction was carried out and the outcome passes, produce the result.
- If either verifier found a problem and fewer than 5 iterations have run, fix and verify again.
- If 5 iterations have run, stop and produce the result listing every unresolved problem.

## Fix

Subagent: Fixer (→ `FixReport`)

Take the task, the account of the work done so far, and the verifiers' findings, resolve every problem found, and change nothing that already passes. Where a finding is mistaken, say so and give the evidence rather than ignoring it.

## Produce verification result

Combine the outcome, the number of iterations, the changes made, and the unresolved problems into `VerificationResult`.

Return the result and write the same result to `verification-result.yaml`.
