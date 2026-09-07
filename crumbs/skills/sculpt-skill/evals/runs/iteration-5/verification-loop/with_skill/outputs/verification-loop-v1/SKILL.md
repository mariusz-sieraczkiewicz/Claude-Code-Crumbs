---
name: verification-loop
description: Runs a task in a worker subagent, then checks instruction compliance and outcome quality in two parallel verifier subagents, fixes what they find, and repeats until clean. Use when a task must be proven done rather than reported done.
metadata:
  types: "./scripts/contracts.py"
  workspace: ./.verification-loop/<utc-timestamp>
---

# Verification Loop

Input (→ `TaskRequest`)

You orchestrate: never carry out the task yourself, and never let a subagent judge its own work. Give each iteration its own folder inside the workspace, and after each phase record where the loop stands and tell the user.

## Work

Subagent: Worker (→ `WorkReport`)

Carry out the task. Report what was done, which files changed, anything left undone and why, and how each unclear point was decided.

## Verify

Verify the work with these two subagents in parallel. Each receives the task word for word and the report of the work it is checking, and each judges the produced artifacts themselves rather than trusting that report.

Subagent: Instruction Verifier (→ `InstructionReview`)

Break the task into its separate instructions and establish for each whether it was carried out.

Subagent: Outcome Verifier (→ `OutcomeReview`)

Work out what success means for this task beyond its literal wording, then judge whether the artifacts achieve it, running them wherever they can be run.

## Decide

Work is clean when every instruction was carried out and the outcome verifier passes it. Where the two verifiers contradict each other, believe the one reporting a failure.

- If the work is clean, produce the result and stop.
- If a subagent produced nothing, tell the user which one failed silently and let them choose between running it again and stopping without a result.
- If the work is not clean and at least 5 iterations are complete, show the user the unresolved issues and what another iteration would attempt, and let them choose between continuing and finishing; unless they continue, produce the result listing those issues and stop.
- Otherwise fix the issues and verify again.

## Fix

Subagent: Fixer (→ `FixReport`)

Given the task, the report of the work being fixed and both verifier findings, resolve every issue they raise and change nothing that already passed. Report each fix as the state before and after it. Where a finding is mistaken, say so with the evidence instead of ignoring it.

Then verify again, treating the fix report as the work being checked.

Output (→ `LoopResult`(`result.yaml`))
