# sculp-skill eval

Measures whether the sculpting skill lands on the intended **form**: the way it
writes, how deep it goes, and how it declares conditions and structures. It does
this by sculpting a known source skill and having judges compare the result to a
reference sculpt of that same source.

Text similarity to the reference is deliberately not scored. Two good sculpts of
one source read differently.

```
evals/
├── evals.json                            the eval set
├── rubric.md                             five dimensions, 1–5, with anchors
├── agents/judge.md                       judge subagent instructions
├── source-skills/<name>/                 input: the verbose skill
├── reference-generations/<name>/         target form: the reference sculpt
└── runs/iteration-N/<eval>/              results, created as you go
```

## Running an iteration

**1. Produce the outputs.** Spawn both runs in the same turn so they finish
together.

- *with_skill* — a subagent given the sculpting skill and the eval prompt,
  saving to `runs/iteration-N/<eval>/with_skill/outputs/`.
- *without_skill* — the same prompt, no skill, saving to
  `.../without_skill/outputs/`. This is what tells you whether the skill is
  doing the work or the model is. It only answers that question if it is
  genuinely isolated — see below.

Judge the baseline with the same number of judges as the candidate. A
three-judge median against a one-judge score is not a comparison.

When improving the skill rather than creating it, snapshot the current version
first and use that as the baseline instead of the no-skill run.

### Isolating the baseline

The baseline has to represent what the model does with no help. Everything it
borrows from work already done here inflates it, and an inflated baseline hides
the skill's value rather than measuring it.

Three rules, in order of how much they actually buy you:

**Move the work out of the repository.** Copy the source skill into a scratch
directory outside this project and point the baseline agent there. This is the
only measure that removes the temptation rather than forbidding it — the other
skills, the reference sculpts and the rubric are simply not reachable.

**Forbid borrowing explicitly.** The agent must not invoke any skill, plugin or
command, must not open any skill, template or document other than the source,
and must not reproduce a known method it can name. It writes from the task and
the source text alone.

**Check afterwards, before you trust the score.** Read the run's transcript and
confirm: no skill invocations, and no file opened outside the scratch
directory. A baseline you did not verify is a number you cannot cite. Note that
the harness advertises the names and one-line descriptions of installed skills
in every agent's context and there is no way to suppress that from inside a
prompt — moving the work out of the repository is what keeps that exposure down
to names.

Paste this into the baseline agent's prompt:

```
Work only from the task and the source file. Do not invoke any skill, plugin
or command. Do not open any other skill, template, checklist or example, here
or anywhere else on this machine. Do not reproduce a named method you already
know. Decide what to cut from the source text itself.
```

**2. Judge.** For each output, spawn 3 judges reading `agents/judge.md`. Take
the median score per dimension. Three judges cost little and the spread tells
you whether a dimension is being scored reliably or is just noisy.

Write each verdict to `<run>/judge-<n>.json` and the median to
`<run>/grading.json`.

**3. Anchor the scale.** In the first iteration — and again whenever the rubric
changes — judge two known quantities alongside the real candidates:

- the **source** as if it were a candidate, which should score near 1
- the **reference** against itself, which should score 5

If either anchor lands far from its expected value, the rubric is
miscalibrated and the candidate scores mean nothing yet. Fix the rubric before
reading the results.

**4. Read the divergences, not the numbers.** Each judge records, for every
point deducted, the candidate's form and the reference's form for the same
responsibility. That side-by-side is what tells you which rule in the sculpting
skill failed to fire. The `what_to_fix_in_the_sculpting_skill` field is written
for exactly this.

**5. Revise the sculpting skill and repeat** into `iteration-N+1`.

## Adding an eval

Drop a verbose skill into `source-skills/` and a hand-made target sculpt into
`reference-generations/` under the same name, then add an entry to
`evals.json`. Pick sources that carry something to remove on several dimensions
at once — a skill that only needs shortening cannot distinguish a good sculpt
from a short one.
