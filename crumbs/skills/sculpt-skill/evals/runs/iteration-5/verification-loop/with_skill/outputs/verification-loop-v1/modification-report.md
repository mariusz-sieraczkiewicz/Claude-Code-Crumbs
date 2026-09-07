# Modification report — verification-loop

Source: `verification-loop` (82 lines). Result: `SKILL.md` (51 lines) + `scripts/contracts.py`.

## Deleted

- **ASCII loop diagram** — repeated the phase sequence the sections already spell out.
- **Workspace file layout** (`task.md`, `status.md`, `iter-N/`, `worker.log`,
  `verifier-*.{log,json}`, `fixer.{log,report.md}`) — storage mechanics. Only the two facts
  that change behaviour survive: a workspace exists (frontmatter) and each iteration is kept
  apart from the others.
- **Both JSON schemas** for the verifier outputs — moved into typed contracts.
- **Per-phase running logs** and the guardrail `Empty/missing .log = silent failure` as a
  file-level rule — kept as a behaviour ("if a subagent produced nothing …"), dropped as a
  file convention. Cost: a silent failure is now noticed when the loop decides rather than
  mid-run.
- **`status.md` as a named artifact** — folded into "after each phase record where the loop
  stands and tell the user", which also absorbs the duplicated "Report status to the user
  after every phase" / "Update `status.md` after every phase" pair.
- **Literal user-message wording** (`"Worker done. Modified N files. Verifying."`,
  `"Instructions: X/Y done. Outcomes: <overall>."`) — examples of phrasing, not decisions.
- **Things the model already knows**: "Execute the task completely", "read files, grep, run
  checks", "read if readable", "Spawn 1 `general-purpose` subagent", "parallel, single
  message", "Never skip a verifier run", "Thrashing = escalate, don't grind", "report
  remaining issues honestly", "don't silently ignore" as a separate clause.
- **`Phase 1..4` numbering** and the separate `Guardrails` / `Final Report` sections — the
  guardrails were distributed to the step each one governs; the final report became the
  output contract.
- **Enumeration of instruction statuses in the body** ("carried out, only partly carried out,
  or missed") — the three-way distinction lives in the contract only.

## Shortened / rephrased

| Original | Now |
| --- | --- |
| `You orchestrate — never implement` + `Never let worker/fixer self-verify` | one opening sentence covering both |
| `Trust failing verifier over passing one when they disagree` | "believe the one reporting a failure" |
| Worker steps 1–4 | one paragraph: carry out the task, report what was done, what changed, what was left undone and why, how ambiguity was decided |
| Verifier bullet lists | one paragraph each, stating what to establish or judge |
| `Clean = no missing/partial instructions AND outcomes overall == "pass"` | plain-language clean test |
| Fixer steps 1–4 | one paragraph; `use fix_hint as a starting point` dropped as the contract carries the hint |
| `description` | now also says when to reach for the skill |

## Changed behaviour (deliberate)

- The original both capped the loop at 5 iterations (Phase 3: stop) and allowed more "with
  user permission" (Guardrails). The sculpted version keeps the permission route: from the
  fifth iteration on, the user is shown the unresolved issues and chooses between continuing
  and finishing.
- Silent subagent failure was `surface to user` with no stated continuation. It is now a
  complete branch: tell the user which subagent failed and let them choose between rerunning
  it and stopping without a result.

## Moved into typed contracts — `scripts/contracts.py`

`TaskRequest`, `WorkReport`, `InstructionReview` (+ `InstructionCheck`, `ComplianceStatus`),
`OutcomeReview` (+ `OutcomeCheck`, `OutcomeStatus`), `FixReport` (+ `Fix`,
`RejectedFinding`), `LoopResult`.

The derived counters from the original JSON summaries (`total/done/missing/partial`) were
dropped — they are computable from the checks. `LoopResult` carries what the original's
Final Report listed: whether it came out clean, the iteration count, what changed, anything
unresolved, and the workspace path. Written to `result.yaml`.

## Verification

Four rounds, each run by a subagent that saw only the sculp-skill rules, the original skill
and the sculpted files inline — no project files.

1. Escalation at the iteration cap had been dropped; the running status record had been
   dropped; silent failure had been turned into a unilateral stop. All three fixed. (A fourth
   finding — "`FixReport` is undefined" — was an artefact of the type being missing from the
   prompt paste, not from the file.)
2. The cap sentence contradicted the escalation branch; the instruction statuses were spelled
   out in the body as well as the contract. Both fixed.
3. The cap branch fired only at exactly 5 iterations, so continuing past it left the loop
   unbounded. Changed to "at least 5".
4. The cap sentence had become redundant once the branch carried the limit and the permission
   escape. Deleted.

No issues outstanding.
