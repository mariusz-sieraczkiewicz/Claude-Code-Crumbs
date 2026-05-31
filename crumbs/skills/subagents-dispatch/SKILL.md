---
name: subagents-dispatch
description: Use when executing any task that involves implementation, research, or multi-step work. Triggers on requests like "do X", "implement Y", "fix Z", "research W" — anything beyond a single trivial action. Also use when the user says "dispatch", "parallelize", "use subagents", or "split this up".
---

```yaml
bias: spawn more agents, not fewer

steps:
  - decompose task into independent units of work
  - dispatch:
      one_unit: one subagent with self-contained brief
      multiple_independent_units: all subagents in single message (parallel)
      units_with_dependencies:
        - wave 1: independent units in parallel
        - collect results
        - wave 2: dependent units in parallel
  - collect results and synthesise for user

subagent_brief:
  - what: specific deliverable
  - why: enough context for judgment calls
  - constraints: boundaries
  - output: what to report back
```
