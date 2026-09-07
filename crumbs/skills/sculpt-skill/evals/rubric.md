# Rubric — essence, minimalism, readability

Sculpting has one goal in three parts: **keep the essence, cut everything else,
and make what remains easy for a person to read.** Score a sculpted skill on
those three things and nothing else.

Important: the essence is human intent and flow expression, not technical details. Human skill (text) should abstract from details. The only exception is reference to Pydantic models on input/output declaration. The rest (technical) details must be inferred from type definitions, conventions and defined patterns (eg. workspace).

## The reference is a calibration sample, not a template

You are given a reference sculpt of the same source. Use it to see roughly what
altitude, register and degree of delegation hit these three goals — the way you
would use a worked example, not an answer key.

The candidate does not have to look like it. Two good sculpts of one source
read differently. So:

- A difference that serves the three goals as well as the reference does is
  **not** a deduction. Record it as a defensible divergence and say why it holds.
- A difference that serves them **better** than the reference is a finding worth
  reporting — it means the reference has something to learn.
- Deduct only where the candidate loses essence, carries weight it does not
  need, or is harder to read than it has to be.
- Never deduct for different wording, different section boundaries, or a
  different but coherent decomposition.

Where the source contradicts itself, any coherent resolution is acceptable.
Judge how clearly the candidate resolves it, not whether it resolved it the way
the reference did.

## What not to deduct for

These are rulings from the person the sculpting is for. They settle cases that
judges have previously got wrong. When one applies, pass it and move on.

**Anything the types file carries is properly placed.** A rule held by a field,
a status set, or a field description is delegated, not weakened. Restating it in
the body would be the defect. Never deduct because a reader has to open the
types file — that file is part of the skill, and reading it is expected.

**The `(→ Type)` arrow is an established convention.** It needs no explanation,
gloss or legend, in the body or anywhere else.

**A defect the reference shares is still a defect** — say so plainly. But be
clear in your wording whether you are describing something that genuinely costs
a reader or a run, or merely something that cannot tell two candidates apart.
Those are different claims and readers conflate them.

## The bar for deducting

Deduct only where a reader or a run would actually pay for it. If your reasoning
reduces to "the reference says this more fully", "this could be stated more
explicitly", or "a newcomer might prefer more here", you have not found a defect.

Judges before you have been too strict, and it cost the verdict its usefulness: a
page of small deductions buries the one finding worth acting on. When a call is
genuinely close, pass it. You lose nothing by passing a marginal case, and you
lose the reader's attention by not.

---

## 1. Esencja — is the essence intact?

Everything that determines what the skill produces, or which path it takes, is
still there. Nothing has been invented that the source did not ask for.

Test each responsibility by asking what breaks without it. If a run would end
differently, produce a different result, or leave a person unable to act, it is
essence.

| 5 | Every outcome-bearing responsibility survives, in a form that still determines behaviour. Nothing invented. |
| 4 | Everything survives, but one responsibility is stated so lightly that it may not bind in practice. |
| 3 | One outcome-bearing responsibility is lost, weakened to a description, or invented. |
| 2 | Two or three are lost or invented. |
| 1 | The skill would behave materially differently from the source's intent. |

Losing a responsibility to compression and never carrying it in the first place
are the same failure. Check the source, not just the reference.

## 2. Minimalizm — could anything more come out?

Nothing remains whose removal would leave behaviour unchanged.

The usual passengers: narration of progress, reassurance, rules the structure
already enforces, restatements of the same rule in two places, enumerated
examples of actions the reader can infer, and facts any competent reader
already knows. Detail about shapes and fields belongs in the types file, and
detail about where results go belongs in the frontmatter contract — a body that
spells either out is carrying weight it could delegate.

**A run's own bookkeeping is execution detail and does not belong in the body.**
Status logs, running logs, per-iteration folders, report filenames, artifact
inventories — all of it. A workspace declared in the frontmatter is the whole of
what a sculpt keeps about where a run writes; naming what goes inside it is a
passenger, however faithfully the source described it. Ruled by the person this
work is for, against earlier judges who scored these as preserved essence.

A rule that depends on one of those artifacts has to be restated in terms of the
result rather than the artifact, or dropped with it. "An empty log means the
subagent failed silently" becomes "a subagent that returns no result has failed";
the guard survives, the log does not.

| 5 | Nothing could be removed without changing behaviour. Detail sits wherever it can be delegated. |
| 4 | One or two sentences could go. |
| 3 | A recognisable class of passenger survives — progress narration, a duplicated rule, or field shapes spelled out in the body. |
| 2 | Several classes survive; the body still carries mechanics it could delegate. |
| 1 | Little was actually removed; it is the source with smaller words. |

Shorter is not automatically better. A cut that costs essence is scored in
dimension 1, and a cut that makes the skill harder to follow is scored in
dimension 3.

## 3. Czytelność — can a person read it easily?

Someone competent who has never seen the source should be able to read it once
and know what to do. Judge it as that reader.

What helps: plain words, short sentences, one idea per sentence, terms explained
where they first appear, an order that matches how the work actually happens,
and visual structure used where it genuinely aids scanning.

What hurts: jargon, dense clause-stacking, abbreviations and internal names
introduced without explanation, decoration that carries no information,
structure that fragments one idea across several places, and compression so
aggressive that the reader has to reconstruct the intent.

| 5 | Reads cleanly first time. Every term lands. Nothing has to be re-read to be understood. |
| 4 | Clear throughout, with one passage that needs a second pass. |
| 3 | Followable, but something recurring gets in the way — unexplained jargon, decoration, or an idea split across places. |
| 2 | Several passages need rereading, or the reader must infer intent the text should have stated. |
| 1 | A newcomer could not act on it confidently. |

Headings, lists and ordering are **not** penalised as leftovers from the source.
Judge them only by whether they help this reader or clutter the page. A heading
that helps someone find a stage earns its place; one that restates the sentence
beneath it does not.

---

## Verdict

Take the mean of the three scores.

- **strong** — mean ≥ 4.5, no dimension below 4
- **sound** — mean ≥ 3.5, no dimension below 3
- **weak** — anything else

Name the dimension costing the most, and state the one change to the sculpting
skill that would have prevented the largest loss. That change is the point of
the whole exercise; the numbers are only how you got there.
