---
name: verification-loop
description: Execute a task in a worker subagent, independently verify instruction compliance and outcome quality in parallel, fix issues, repeat until clean or max 5 iterations.
---

# Verification Loop

Delegate work to subagents, verify independently, fix, repeat. You orchestrate — never implement. Report status to the user after every phase.

## Guardrails

- Never skip a verifier run. Never let worker/fixer self-verify.
- Max 5 iterations without user permission. Thrashing = escalate, don't grind.
- Trust failing verifier over passing one when they disagree.
- Empty/missing `.log` = silent failure — surface to user.

## Workspace

Create `.verification-loop/<UTC-timestamp>/` with `task.md` (verbatim task) and `status.md` (running log). Each iteration gets `iter-N/` containing: `worker.log`, `worker-report.md`, `verifier-instructions.{log,json}`, `verifier-outcomes.{log,json}`, `fixer.{log,report.md}` (if needed).

Update `status.md` after every phase.

## Loop

```
worker → verifier-instructions + verifier-outcomes (parallel)
  → clean? done : fixer → re-verify (back to verifiers)
```

## Phase 1 — Worker

Spawn 1 `general-purpose` subagent. Provide: verbatim task from `task.md`, workspace path `iter-N/`.

Worker instructions:
1. Execute the task completely
2. Append running log to `worker.log` — one line per action, written regularly
3. Write `worker-report.md`: what was done (bulleted), files created/modified (abs paths), anything skipped and why, ambiguities resolved
4. Do NOT self-verify

Read `worker-report.md`, report to user: "Worker done. Modified N files. Verifying."

## Phase 2 — Verifiers (parallel, single message)

Spawn 2 subagents simultaneously. Both receive: verbatim task, worker report, workspace path.

**Verifier-instructions** — checks every discrete instruction was executed:
1. Decompose task into checklist of imperatives
2. Independently verify each — read files, grep, run checks (don't trust worker report)
3. Write `verifier-instructions.json`: `{"instructions": [{"id", "instruction", "status": "done|missing|partial", "evidence", "fix_hint"}], "summary": {"total", "done", "missing", "partial"}}`

**Verifier-outcomes** — checks produced artifacts satisfy the user's intent:
1. Identify expected outcome (what success looks like, not literal instructions)
2. Assess artifacts — run if runnable, read if readable, judge quality not just existence
3. Write `verifier-outcomes.json`: `{"criteria": [{"id", "criterion", "status": "pass|fail|concern", "evidence", "fix_hint"}], "overall": "pass|fail|concern", "summary"}`

Report to user: "Instructions: X/Y done. Outcomes: <overall>."

## Phase 3 — Decide

Clean = no `missing`/`partial` instructions AND outcomes `overall == "pass"`.
- **Clean**: stop, write final summary to `status.md`, report to user.
- **Issues + iter < 5**: proceed to fixer.
- **Issues + iter == 5**: stop, report remaining issues honestly.

## Phase 4 — Fixer

Spawn 1 subagent with: verbatim task, prior worker report, both verifier JSONs, new iteration workspace `iter-(N+1)/`.

Fixer instructions:
1. Address every `missing`/`partial`/`fail`/`concern` finding — use `fix_hint` as starting point
2. Only fix — don't redo passing work
3. Log to `fixer.log`, write `fixer-report.md` with before/after for each fix
4. If a verifier finding is wrong, say so with evidence — don't silently ignore

After fixer completes, return to Phase 2 with fixer-report as the "worker report" input.

## Final Report

1. One-line result: passed on iter-N / stopped at cap with K remaining issues
2. What changed — bulleted, from iteration reports
3. Workspace path for inspection
