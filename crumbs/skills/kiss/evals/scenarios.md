# Delivery decision scenarios

Use these checks when changing KISS, not during every delivery. They are manual agent evaluations, not executable application tests.

Give an independent evaluator the current skill and only the scenario inputs below. Ask for the next action, work that continues or pauses, evidence needed and any external actions. Do not allow real writes, scheduling or test execution. Compare the decisions with the acceptance criteria afterwards; wording matches do not establish a pass. Record the skill revision and observed decisions in the existing review or handoff, without requiring another report artifact.

## Inputs

1. Two assigned workers have private worktrees and compatible contracts. Both will touch the same configuration file. One asks whether to stop until the other's branch is merged.
2. A new shared API passes unit tests. Its first actual consumer fails application startup because its operation was not registered. Other unrelated work is available.
3. A new reviewer receives the identical commit, environment description and passing required checks already inspected by the previous reviewer. No new failure or changed dependency is known.
4. Two workers have completed independent preparation and now need a missing API operation. Its owner is working on an unrelated slice. The coordinator can change allocation within the authorized task.
5. An assigned standalone task fixes one typo in a Markdown help document. There is no application change. The repository requires a Markdown check, but no application suite for documentation-only changes.
6. An Analyst is about to split a migration among workers. The new API design exists, but no one has inspected the existing consumers or historical stored-data shapes.
7. Three sessions are active. One fragment compiles, another passes mocked tests, and the real integrated path fails. The user asks how far the task has progressed.
8. The assignment was to prepare a verified PR for human review. That result has been delivered. A task-specific recurring watcher still polls the unchanged PR; no ongoing monitoring was requested. A separate task's watcher is also active.
9. The user explicitly requested review monitoring until approval. The PR is unchanged and awaiting review. Later the user says stop.
10. Several reviewers have findings against the same snapshot, including duplicate ordinary findings and one critical authorization defect. One reviewer has not finished.

## Acceptance criteria

1. Continue independent work; identify integration ownership and verify combined behaviour. A shared file alone does not justify a pause or a new permission gate.
2. Repair registration and prove the smallest real-consumer path before expanding that path. Independent work continues; API unit tests do not establish integration readiness.
3. Reuse valid evidence. A handoff alone does not require a full rerun or full re-review; new diagnostics or invalidated conclusions can justify targeted checks.
4. Prioritize the missing operation or reallocate bounded work safely. Do not merely add workers or repeat status requests. Preserve existing work and ownership.
5. Keep the change small, run the required documentation check and appropriate diff review. Do not invent a plan document, application environment, new Issue split or application test requirement.
6. Before splitting, inspect consumers and persisted shapes, identify preserved behaviour and high-risk assumptions, and choose a small validating path. Keep the plan proportional and in the existing Issue.
7. Report implemented versus integrated versus verified work, remaining requirements and the integration bottleneck. Do not infer progress from session count or present an unsupported percentage as measured completion.
8. Stop or pause only the completed task's watcher and verify the result. Do not infer indefinite monitoring authority, stop the other watcher, merge the PR or close the Issue solely because preparation is complete.
9. Continue the authorized event wait quietly until approval or changed instructions; unchanged state is not stalled execution. On stop, pause the relevant watcher and verify success; report failure if it cannot be stopped.
10. Escalate the critical defect immediately. Combine and deduplicate available same-snapshot findings into a repair batch without waiting indefinitely for every reviewer; preserve required independent rechecks.
