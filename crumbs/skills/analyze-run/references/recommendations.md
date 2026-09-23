# Recommendation rules

Recommend a change only when the evidence shows avoidable time and a concrete lever to remove it. When
the run went well, or when it would be hard to have done better in hindsight, say so and stop.

## Avoidable time

Sum `impact_min` over the pivots whose cause could be changed: a skill's instructions, the project's
instructions or rules, the environment or tooling setup, or the way the run was driven. Leave out:

- the user's thinking and availability, such as answering a gate the next morning;
- one-off external outages with no cheap prevention;
- work that the task inherently needed, such as the test runs of a test refactoring or the searches of a
  literature review.

Those still appear as observations.

## Verdict

Compare avoidable time with agent activity, the union of non-waiting spans across agents:

| Verdict | When | Recommendations |
|---|---|---|
| `healthy` | avoidable time under 10% of agent activity and under 15 minutes | none; observations only |
| `friction` | 10–25%, or 15–60 minutes | up to three |
| `waste` | over 25%, or over 60 minutes | as many as pass the rules below, largest saving first |

A different verdict is allowed when the numbers mislead, for example one pivot that changed what was
delivered. State the reason in `summary`.

## A recommendation must

- cite the pivot ids it would remove (`evidence`);
- name one concrete change and where it lives (`target`):
  - the definition of the skill, command or prompt file that was running, by path and section, when the
    pivot is a `skill-gap` or happened inside it and its instructions caused it or failed to prevent it;
  - the project's agent instructions or rules, e.g. `CLAUDE.md`, `AGENTS.md` or a rules file, for
    knowledge every run needs (typical for `discovery`);
  - the environment or tooling, e.g. a faster check, a job configuration, a preflight access check;
  - the way the run was driven, e.g. running long commands in the background, resetting context between
    independent tasks, answering questions in one batch;
- estimate the saving per run and state what it is based on (`saving`);
- state its cost and risk (`cost`) and your `confidence`. Confidence is high only when the cause recurred
  or the mechanism is certain.

## A recommendation must not

- remove or weaken a required gate, independent review, check or authorization to save time;
- give generic advice without a lever, such as "write faster tests";
- repeat another recommendation for a different pivot of the same cause; merge them;
- count the user's waiting time as waste;
- follow from a single external outage unless the prevention is cheap, such as a preflight check that
  fails fast.

## Earlier analyses

Earlier analyses of the same repository in the output root show whether a cause recurs. Recurrence across
runs raises confidence and moves a pivot from observation to recommendation; name the earlier runs in
`why`.
