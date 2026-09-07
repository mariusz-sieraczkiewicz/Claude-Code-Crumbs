---
name: verification-loop
description: Orchestrates delegated execution, independent instruction and outcome verification, and evidence-based repair. Use when a task needs separate implementer and verifier roles or repeated verification after fixes.
metadata:
  inputs: Task
  output: VerificationResult
  types: "./scripts/contracts.py"
  workspace: ".verification-loop/$runtime.run_id/"
---

Use a new workspace for each execution.
The implementer and fixer may change the caller's project when the task requires
it; the workspace does not confine task effects.

Run at most 5 work–verification iterations.

1. Spawn a subagent to complete the user’s task. (→ `WorkingReport`)

2. Verify its result using two subagents in parallel:

Subagent: Instructions Verifier (→ `VerifyInstructionsReport`)

Turn every imperative into a checklist item and independently verify each through source inspection and applicable checks, without trusting the working report.
Mark a completed item as done with no issue; mark any other item as partial or missing and explain the issue.

Subagent: Outcomes Verifier (→ `VerifyOutcomesReport`)

Define success from user intent, read each readable artifact, run each runnable artifact, and assess quality rather than existence.
Pass only when there are no issues; otherwise fail and report every issue.

3. Decide:

- If every instruction is done and the outcome is passed, finish successfully.
- If iteration 5 has been reached, stop and report every remaining issue.
- Otherwise, spawn a fixer to address every unresolved issue reported by either verifier. Use a fix hint only when supported by evidence and it addresses the root cause. (→ `WorkingReport`) Then verify the fixed result in the next iteration.

Report the terminal result and workspace.
