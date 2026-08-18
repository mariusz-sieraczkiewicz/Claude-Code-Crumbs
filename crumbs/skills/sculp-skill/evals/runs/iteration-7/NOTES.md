Iteration 7 — one eval (verification-loop), with_skill arm only.

Under test: the version that moves conventions out of the method and into a
`runtime.md` file copied into every sculpted skill, which then says how to read
the skill's implicit notation — typed results, subagent hand-off through files,
the workspace layout, the arrow notation.

Result: 5 / 4 / 4, mean 4.33, sound. Identical to iteration 6, and this time
all three judges agreed on every dimension — no spread at all. The score held
while the method's own body got shorter, which is the useful part.

## Did the conventions file work?

All three judges say yes, and for the same reason: the sculpted body never
drops into execution detail, because there is now somewhere else for execution
detail to live. What it absorbed, in the judges' words — serialisation, typed
results, subagents handing over through files, workspace naming, the arrow
notation. Cost is one line of boilerplate pointing at the file.

Two judges add that this is the main reason the sculpt reads as cleanly as it
does.

## The one finding worth acting on

Two of three judges name the same defect, and it is the whole of the minimalism
deduction: a sentence about keeping each round's records separately survived in
the body. The source described per-iteration folders; the sculpt did not delete
that, it abstracted it. Abstracting bookkeeping is not removing it.

The rule to add: once a workspace is declared in the frontmatter, no sentence
about the run's own record-keeping may remain in the body — paraphrases
included. Only a guard a person would act on survives, and only restated in
terms of the result rather than the artifact.

The third judge names a different, compatible rule: a subagent's mandate in the
body may state only what its result type cannot already hold. If a required
field already obliges the subagent to report something, the sentence saying so
goes.

## Better than the reference

Reported by all three judges, so worth folding back into the reference sculpt:

  - the silent-failure guard, restated away from its log file ("if a subagent
    returns nothing, treat that as a failure and tell the person") — the
    reference dropped the guard along with the artifact
  - the failing-verifier-wins tie-break, which the reference lost

Named by one judge each: the verbatim-task rule, per-phase reporting to the
person, and honouring the source's "max 5 iterations without user permission"
by actually asking at the cap, where the reference hard-stops.

## Source contradiction

The guardrails allow going past five rounds with the person's permission; the
decide phase stops unconditionally at five. The sculpt honours both — at the
cap it presents the unresolved issues and what another round would attempt,
asks, and stops unless told to continue. All three judges accepted the
resolution.
