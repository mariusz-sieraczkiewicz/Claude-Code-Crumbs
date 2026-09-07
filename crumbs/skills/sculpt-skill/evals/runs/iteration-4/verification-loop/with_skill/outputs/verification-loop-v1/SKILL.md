---
name: verification-loop-v1
description: Execute a task in a worker subagent, independently verify instruction compliance and outcome quality in parallel, fix issues, repeat until clean or max 5 iterations. Use when a task must be independently checked before its result is accepted.
metadata:
  types: ./contracts.py
  workspace: ./.verification-loop/<timestamp-id>
---

# Verification Loop

Input (→ `TaskBrief`(`task.md`))

You orchestrate; you never carry out the task yourself, and no subagent checks its own work. After every phase, update the running log in the workspace and tell the user where the loop stands.

Every iteration keeps its own folder in the workspace holding each subagent's log and report. A subagent log that is missing or empty means that subagent failed silently — report it instead of reading the result as success.

## Worker

Subagent: Worker (→ `WorkerReport`)

Carry out the task in full, logging each action as it happens.

## Verify

Verify the result with these two subagents in parallel. Both receive the task and the latest worker or fixer report.

Subagent: Instruction Verifier (→ `InstructionReport`)

Break the task into its separate imperatives and confirm each one against the files, commands and outputs themselves, never against that report's account of them.

Subagent: Outcome Verifier (→ `OutcomeReport`)

Determine what success means for this task, then judge whether the produced artifacts achieve it. Run whatever can be run, and judge quality rather than existence.

When the verifiers disagree, trust the failing one.

## Decide

Run at most 5 verify–fix iterations.

- If every imperative was carried out and the outcome verifier passes the result, finish and report.
- If issues remain and fewer than 5 iterations are complete, run the fixer and verify again.
- If issues remain after the fifth iteration, stop and report every unresolved issue; continue only if the user asks for further iterations.

## Fixer

Subagent: Fixer (→ `FixerReport`)

Given the task, the report just verified and both verifier reports, resolve every finding they raised, without redoing work that already passed. If a finding is wrong, refute it with evidence instead of ignoring it.

Output (→ `LoopResult`(`status.md`))
