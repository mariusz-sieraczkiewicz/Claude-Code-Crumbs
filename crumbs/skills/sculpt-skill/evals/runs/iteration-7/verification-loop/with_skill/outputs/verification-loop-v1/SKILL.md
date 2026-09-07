---
name: verification-loop-v1
description: Runs a task through a worker subagent, then checks the result independently against both the instructions and the intended outcome, fixes what is wrong, and repeats until clean. Use when a task must be proven done rather than merely attempted.
metadata:
  workspace: ./.verification-loop/<timestamp-id>
---

Read first and follow rules defined in `references/runtime.md` file. They define context and definitions for implicit assumptions in the skill.

# Verification loop

Input (→ `TaskSpec`)

You arrange the work and never carry it out yourself. Keep the task in the person's own words and give that same wording to every subagent. No subagent checks its own work. Tell the person what happened after each phase. Keep each round's records separately so the history stays inspectable.

## Do the work

Subagent: Worker (→ `WorkerReport`)

Carry out the task completely. Report anything you left undone and why, and every ambiguity you decided for yourself.

## Check the work

Check the work using these two subagents in parallel. Neither may rely on the worker's own account; both establish what actually happened from the files themselves.

Subagent: Instruction Verifier (→ `InstructionVerification`)

Break the task into its separate demands and establish for each one whether it was carried out.

Subagent: Outcome Verifier (→ `OutcomeVerification`)

Work out what success means for this task beyond its literal wording, then judge whether the delivered work achieves it. Run what can be run, and judge quality rather than mere existence.

If a subagent returns nothing, treat that as a failure and tell the person.

If the two checks disagree, the failing one prevails.

## Decide and repeat

The work is clean when every demand was carried out and the outcome is judged successful.

Run at most 5 rounds, counting the first pass as round one.

- If the work is clean, finish and produce the result.
- If issues remain, have them fixed and checked again.
- If issues remain after the last round, present the unresolved issues and what a further round would attempt, and ask the person whether to continue or to stop there. Stop unless the person allows more rounds; the result is still produced.

Subagent: Fixer (→ `FixerReport`)

Repair every issue the checks raised, starting from the repair each one suggests. Leave work that already passed untouched. Where a check is mistaken, say so and give the evidence instead of passing over it.

The checks then read the fixer's account in place of the worker's.

Output (→ LoopResult(`loop-result.yaml`))
