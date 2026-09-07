Rubric, judge instructions and calibration rulings are unchanged since
iteration-4, so the anchors and the baseline carry over rather than being
re-measured. Only the with_skill run is new.

  low anchor  (raw source)        5 / 1 / 3   mean 3.00
  baseline    (no skill)          5 / 2 / 4   mean 3.67   weak
  high anchor (reference sculpt)  4 / 4 / 4   mean 4.00   sound
  iteration-5 with_skill          5 / 3 / 4   mean 4.00   sound
  iteration-6 with_skill          5 / 4 / 4   mean 4.33   sound
  iteration-7 with_skill          5 / 4 / 4   mean 4.33   sound

Dimensions: essence / minimalism / readability.

One scope change was made for this iteration and must be carried forward while
the method ships a conventions file. Candidates now contain
`references/runtime.md`, copied verbatim by the method rather than written by
the candidate. Judges were told to read it — the body delegates to it, and
delegation cannot be told from omission without it — but not to score its
contents and never to deduct because a reader must open it. This is the ruling
that already covers the types file, extended to the conventions file.

The sculpting skill was frozen to `skill-snapshot/` before the run, after
iteration 6 was measured against a version that changed mid-run.

  SKILL.md    7ffd055a3e650cb714ce702c5a6b39ce10a7a1b0
  runtime.md  622e114cd3d0039beb47d61045a240b8eadf99e1
