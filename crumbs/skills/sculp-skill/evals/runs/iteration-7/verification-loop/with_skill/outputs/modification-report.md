# Modification report — verification-loop → verification-loop-v1

Source: `evals/source-skills/verification-loop/SKILL.md` (81 lines, single file).
Result: `verification-loop-v1/` — `SKILL.md` (54 lines), `references/runtime.md` (copied
unchanged), `scripts/contracts.py` (typed contracts).

## Moved into the typed contracts

Everything that described the *shape* of data left the skill body and became Pydantic
models in `scripts/contracts.py`:

- The two inline JSON schemas for the verifiers (`{"instructions": [{"id", "instruction",
  "status", "evidence", "fix_hint"}], "summary": {...}}` and the criteria/overall
  equivalent) → `InstructionCheck` / `InstructionVerification` and `OutcomeCriterion` /
  `OutcomeVerification`.
- The worker report's four required sections → `WorkerReport`.
- The fixer's before/after record → `FixFinding` / `FixerReport`.
- The three-part "Final Report" section (one-line result, what changed, workspace path)
  → `LoopResult`, declared as the skill output.
- The verbatim task → `TaskSpec`, declared as the skill input.

## Deleted

- **`## Loop` ASCII diagram** — restated the phase order that the phase headings already
  give.
- **All `.log` file mechanics** — `worker.log`, `fixer.log`, "append running log", "one
  line per action, written regularly", the `iter-N/` per-round folders, the
  `verifier-*.{log,json}` file inventory, and `status.md`. How subagents record and hand
  over their work is a runtime convention, and `references/runtime.md` already states it:
  every structured result is a validated Pydantic model serialised to YAML in the
  workspace, and subagent communication always goes through files.
- **The `status.md` running log and "Update `status.md` after every phase"** — same
  reason; the audit trail is the runtime's job.
- **The three scripted user messages** (`"Worker done. Modified N files. Verifying."`,
  `"Instructions: X/Y done. Outcomes: <overall>."`, and the final one) — enumerated
  wordings of one rule that is now stated once: tell the person what happened after each
  phase.
- **`Spawn 1 general-purpose subagent` / `Spawn 2 subagents simultaneously`** — subagent
  count and type follow from the declarations themselves; `references/runtime.md` defines
  how a declared subagent is spawned.
- **"Never skip a verifier run"** — the checking phase is unconditional in the flow, so
  the prohibition adds nothing.
- **"Trust failing verifier over passing one"** kept, but "Thrashing = escalate, don't
  grind" deleted — it duplicates the round cap and its escalation branch.
- **"Workspace path for inspection"** in the final report — the workspace is declared in
  the frontmatter and is a runtime convention.
- **Bare restatements a model does not need**: "Read `worker-report.md`", "return to
  Phase 2 with fixer-report as the input" reduced to one sentence, "Only fix — don't redo
  passing work" kept but shortened.

## Compressed (same effect, smaller concept)

- Two separate self-verification prohibitions (`Never let worker/fixer self-verify` in the
  guardrails, `Do NOT self-verify` in the worker steps) → one line in the opening:
  *No subagent checks its own work.*
- `Empty/missing .log = silent failure — surface to user` → *If a subagent returns
  nothing, treat that as a failure and tell the person* — the same rule without naming a
  file format.
- The verifiers' numbered three-step procedures ("decompose… independently verify… write
  JSON") → one sentence each stating what the verifier must establish, since the writing
  step is now the declared typed result.
- The `## Guardrails` section dissolved: each guardrail moved next to the phase it governs
  instead of living in a preamble the reader must hold in mind.

## Rephrased for a non-expert reader

- "iterations" → "rounds"; "artifacts" → "the delivered work"; "instruction compliance and
  outcome quality" → checking "against both the instructions and the intended outcome".
- The description gained a *when to use it* clause, which the original lacked.

## Kept because removing them changes behaviour

Orchestrator never implements; the task passed on verbatim; two independent checks run in
parallel; verifiers must not trust the worker's account; failing check beats passing check;
a missing result is a failure; the 5-round cap and its exit branches; the fixer leaves
passing work alone and may rebut a finding with evidence; a fixed result re-enters the same
two checks.

## Contradiction found in the source, and how it was resolved

The guardrails say **"Max 5 iterations *without user permission*"** — which permits going
past five if the person agrees — while Phase 3 says **"Issues + iter == 5: stop, report
remaining issues honestly"** — which permits no such thing.

Resolved by keeping both readings: at the cap, the skill presents the unresolved issues and
what a further round would attempt, asks the person whether to continue or stop, and stops
unless the person allows more rounds. This also absorbs the deleted "thrashing = escalate"
guardrail. The question is stated as a specific decision with its consequences rather than
a vague request for clarification.

## Workspace

The source declared its own workspace (`.verification-loop/<UTC-timestamp>/`) rather than
the runtime default, so it is preserved as a `workspace` entry in the frontmatter metadata.
The per-round `iter-N/` subfolders were dropped; round-scoped artefacts are ordinary
workspace files.

## Verification

Three rounds ran. Each used a fresh subagent restricted to the sculpting method, the
runtime conventions, the original skill and the sculpted result — nothing else in the
project — so its judgement stayed uncontaminated.

**Round 1 — 9 findings.** Six were accepted and fixed:

1. The frontmatter still called the copy `verification-loop`, colliding with the original.
   → renamed `verification-loop-v1` to match the copy.
2. The round cap was off by one. The original counts the first worker pass as iteration 1,
   so five iterations allow four fix rounds; the sculpt read as five *fix* rounds.
   → "Run at most 5 rounds, counting the first pass as round one."
3. The decision branches said whether the loop continues but not whether the result is
   still produced. → added to the clean branch and to the cap branch.
4. Two sentences recited a contract's field list — the worker's "what you did, which files
   you created or changed" and the instruction verifier's "on what evidence, and what would
   repair it". → both trimmed to the part the type cannot imply.
6. The fixer hand-back repeated the decision branch. → reduced to the one new fact, that
   the checks now read the fixer's account.
7. "Run what can be run, read what can be read" — the second half is something the model
   already knows. → dropped.

Findings 5, 6 and 7 of that round (the lost `status.md` running log, the per-action
subagent logs, and the per-round `iter-N/` folders) were **overruled** as a group. The
method states plainly *"Do not describe how the result is serialized, stored, or
transferred"*, and the runtime conventions already require every structured result to be a
validated model serialised to the workspace, with all subagent communication through files.
Naming log files in the body would put back exactly what the method removes. The one
behaviour underneath them that the conventions do *not* supply — that the history of
earlier rounds survives later ones — was kept as a single sentence: *"Keep each round's
records separately so the history stays inspectable."*

**Round 2 — 1 finding.** `TaskSpec` carried a speculative `context` field that nothing in
the skill reads or reasons about, and whose bare name did not say what belonged in it.
→ deleted.

**Round 3 — no findings.** The check confirmed every ground rule and writing rule, and
traced each load-bearing behaviour of the original into the sculpted version.
