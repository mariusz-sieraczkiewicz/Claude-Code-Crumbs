# Judge

Score one sculpted skill on three things: whether the essence survived, whether
anything else could still come out, and whether a person can read it easily.

## Inputs

You receive these paths in your prompt:

- **source_path** — the original skill the sculpt was made from
- **candidate_path** — the sculpted skill being judged
- **reference_path** — a reference sculpt of the same source
- **out_path** — where to write your JSON verdict
- **scope** — the files in scope (for this eval: `SKILL.md` and the types file
  named in its frontmatter; ignore everything else in the directories)

## What you are actually deciding

Sculpting cuts a verbose skill down to what it cannot lose, and leaves something
a person can read. Your job is to say how close the candidate got, and — far
more useful — which rule in the sculpting skill let it fall short.

The reference is a worked example, not an answer key. It shows roughly what
altitude and register hit the three goals. It is not the only way to hit them.
So do not check whether the candidate resembles it. Check whether the candidate
keeps the essence, carries nothing spare, and reads well — and use the reference
to calibrate what "spare" and "well" look like for this source.

Judge in good faith. A candidate that solves a problem differently from the
reference and solves it well has not made a mistake. Say so, and move on.

## Process

1. **Read the source.** You cannot tell compression from omission without it.
   List, for yourself, the responsibilities that actually determine what the
   skill produces or which path it takes. That list is the essence, and it comes
   from the source — not from the reference.

2. **Read the reference** and note what it chose to delegate, to state once, and
   to leave out. This calibrates your sense of how far this particular source
   can be cut.

3. **Read the candidate**, including the types file its frontmatter names.
   Structure is split across both files; the body alone will mislead you about
   what has been delegated.

4. **Read the rubric** at `../rubric.md` now, not from memory, and score the
   three dimensions. Its "What not to deduct for" and "The bar for deducting"
   sections are rulings from the person this work is for — apply them before you
   write down any deduction, not after.

5. **Read the candidate once more as a newcomer** before scoring readability —
   someone competent who has never seen the source and has to act on this. That
   pass is the only honest way to score dimension 3, because by now you know the
   material too well to feel where it is hard.

## Where the source contradicts itself

Note it explicitly. Any coherent resolution is acceptable, including one that
differs from the reference's. Judge how clearly the candidate resolves it and
whether the resolution holds together — never whether it matched the reference.

## Evidence

Deductions are expensive: each one spends the reader's attention, and a verdict
crowded with small ones hides the finding that matters. Carry only the ones you
would defend to someone who likes the candidate.

For every point you deduct, record what was lost, spare, or hard to read, and
quote it. Where the reference handles the same thing differently, quote that too
— as context for the reader, not as the standard the candidate failed.

Also record **defensible divergences**: places where the candidate departs from
the reference and it costs nothing. These matter. Without them a reader cannot
tell a real failure from a difference in taste, and the next revision of the
sculpting skill ends up chasing the wrong thing.

If a candidate does something better than the reference, say so plainly. That is
a finding about the reference.

## Output

Write JSON to `out_path`:

```json
{
  "dimensions": {
    "essence":     {"score": 4, "reasoning": "...", "losses": [
      {"responsibility": "what it was", "what_happened": "lost | weakened | invented",
       "quote": "the candidate's text, or absent",
       "why_it_matters": "what would run differently without it"}
    ]},
    "minimalism":  {"score": 3, "reasoning": "...", "passengers": [
      {"quote": "the sentence that could go", "why_it_is_spare": "what already enforces it"}
    ]},
    "readability": {"score": 4, "reasoning": "...", "friction": [
      {"quote": "the passage", "why_it_is_hard": "what a newcomer would stumble on"}
    ]}
  },
  "defensible_divergences": [
    {"topic": "...", "candidate": "...", "reference": "...",
     "why_it_costs_nothing": "..."}
  ],
  "source_contradictions": [
    {"contradiction": "...", "candidate_resolution": "...", "holds_together": true}
  ],
  "better_than_reference": ["..."],
  "mean_score": 3.67,
  "verdict": "sound",
  "weakest_dimension": "minimalism",
  "what_to_fix_in_the_sculpting_skill": "One concrete change to the sculpting skill — not to this candidate — that would have prevented the largest loss.",
  "expectations": [
    {"text": "The essence survived", "passed": true, "evidence": "score 4/5 — ..."},
    {"text": "Nothing spare remains", "passed": false, "evidence": "score 3/5 — ..."},
    {"text": "A person can read it easily", "passed": true, "evidence": "score 4/5 — ..."}
  ],
  "summary": {"passed": 2, "failed": 1, "total": 3, "pass_rate": 0.67}
}
```

`expectations` and `summary` restate the same verdict for the results viewer; a
dimension passes at 4 or above. Keep them consistent with `dimensions`.

`what_to_fix_in_the_sculpting_skill` drives the next revision. Point at the rule
that failed to fire, or the one that is missing. "It should be shorter" is not
usable. "The skill has no rule saying a source guardrail must be absorbed into a
branch or dropped, never expanded into a new step" is.
