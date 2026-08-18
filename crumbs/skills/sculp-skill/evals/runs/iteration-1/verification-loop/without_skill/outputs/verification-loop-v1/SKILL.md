---
name: verification-loop
description: Execute a task in a worker subagent, independently verify instruction compliance and outcome quality in parallel, fix issues, repeat until clean or max 5 iterations.
---

# Verification Loop

You orchestrate. Subagents do the work — you never implement and never verify yourself.

```
worker → [verifier-instructions ‖ verifier-outcomes] → clean? done : fixer → re-verify
```

Every subagent receives the task verbatim, never your paraphrase of it.

**Worker** — one subagent executes the task and reports what it did. It does not verify its own work.

**Verifiers** — two subagents spawned in parallel in a single message, each working from the verbatim task and from the artifacts themselves rather than the worker's account of them:

- *instructions* — decompose the task into discrete imperatives; confirm each one was actually executed.
- *outcomes* — decide what success looks like, then judge whether the artifacts achieve it. Run what is runnable; judge quality, not existence.

Each finding carries a status, the evidence behind it, and a hint for fixing it.

**Clean** = no instruction missing or partial, and outcomes pass. Clean → stop. Otherwise → fixer.

**Fixer** — a separate subagent addresses the findings and only the findings; it does not redo passing work and does not judge whether it succeeded. Loop back to the verifiers.

## Constraints

- Five iterations maximum without the user's go-ahead. Thrashing means escalate, not grind.
- When verifiers disagree, the failing one is right.
- A finding the fixer believes is wrong must be rebutted with evidence, never silently dropped.
- Persist each iteration's reports and findings under `.verification-loop/<UTC-timestamp>/iter-N/` so later subagents and the user can read them.
- Tell the user where you are after each phase, and end with an honest result: passed on iteration N, or stopped at the cap with these issues outstanding.
