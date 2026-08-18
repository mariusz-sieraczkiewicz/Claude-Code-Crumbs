---
name: verification-loop
description: Execute a task in a worker subagent, independently verify instruction compliance and outcome quality in parallel, fix issues, repeat until clean or max 5 iterations.
---

# Verification Loop

You orchestrate — never implement. After every phase, update `status.md` and report to the user.

Workspace: `.verification-loop/<UTC-timestamp>/` holding `task.md` (the verbatim task), `status.md` (running log), and one `iter-N/` per iteration for each subagent's log, report, and verifier JSON. An empty or missing log means the subagent failed silently — surface that to the user.

## 1. Worker

Spawn one `general-purpose` subagent with the verbatim task and its `iter-N/` path. It executes the task completely, appends to its log as it works, and writes `worker-report.md`: what was done, files created/modified (absolute paths), anything skipped and why, ambiguities resolved. It must not self-verify.

## 2. Verifiers — both spawned in parallel, in a single message

Each gets the verbatim task, the worker (or fixer) report, and the workspace path. Neither may trust that report — they read files, grep, and run checks themselves.

**verifier-instructions** — decompose the task into a checklist of imperatives and verify each one. Writes `verifier-instructions.json`:
`{"instructions":[{"id","instruction","status":"done|missing|partial","evidence","fix_hint"}],"summary":{"total","done","missing","partial"}}`

**verifier-outcomes** — identify what success looks like (not the literal instructions), then assess the artifacts: run what's runnable, read what's readable, judge quality rather than existence. Writes `verifier-outcomes.json`:
`{"criteria":[{"id","criterion","status":"pass|fail|concern","evidence","fix_hint"}],"overall":"pass|fail|concern","summary"}`

## 3. Decide

Clean = no `missing`/`partial` instruction AND outcomes `overall == "pass"`.

- Clean → stop. Final summary: passed on iter-N, what changed, workspace path.
- Not clean, iter < 5 → fixer.
- Not clean, iter == 5 → stop and report the remaining issues honestly. Continuing needs the user's permission.

## 4. Fixer

Spawn one subagent with the verbatim task, the prior report, both verifier JSONs, and `iter-(N+1)/`. It addresses every `missing`/`partial`/`fail`/`concern` finding, starting from its `fix_hint`; it fixes only those and never redoes passing work; it writes `fixer-report.md` with before/after per fix. If a finding is wrong, it says so with evidence instead of silently ignoring it.

Then return to phase 2 with `fixer-report.md` as the report input.
