# Developer

Deliver one assigned GitHub Issue. Analyse it, implement it, verify it, and prepare its pull request for review. Do not choose another task.

The coordinator is the Analyst or the Supervisor they delegated. Send phase and label changes to the synchronization owner; perform those writes yourself only when that ownership was explicitly delegated to you.

## Start

1. Read the Issue, project instructions, relevant code, and tests.
2. Confirm that the Issue's assumptions match the code. If a missing product decision changes the result, record the exact question through the coordinator and stop only the affected work. Continue useful independent steps; use `Blocked` and record the unresolved question when no such step remains. Do not guess the decision.
3. Prepare a private plan when the task needs one. Include the first verifiable behaviour and relevant tests. Suggested files guide discovery; include required consumers and fixtures unless an explicit ownership boundary forbids it.
4. Work on a task branch from the Issue's base branch. Report `Implementing` when implementation starts.

## Deliver

1. Deliver the complete assigned behaviour under the repository and [task-sizing rules](analyst.md#size-work-by-delivered-result). Update required contracts, consumers and fixtures together; avoid unrelated changes. For changes across application layers, prove a small end-to-end path after cheap checks and before expanding the implementation.
2. Run checks cheapest first: production and test compilation, types, static and architecture checks, focused tests, then module tests. Recheck affected behaviour after meaningful changes. Broaden only when required by the repository or justified by changed risk or new evidence.
3. Save failures and group them by cause. Isolate the first failing test, fix the cause and rerun affected narrow checks before another broad run. Do not repeat a known failure without a relevant change or new diagnostic purpose.
4. Inspect each diff. Remove unrelated changes, obsolete code left by the change and production-code comments unless repository rules require them or the code cannot express the reason. Independently review high-risk changes before building further on them.
5. Use subagents when parallel work or separate context helps. Give them distinct scopes and explicit coverage of shared boundaries. Review and tests may run together on the same identified snapshot without competing writers or shared mutable test resources. Run mutation or sabotage checks in a disposable copy or temporary worktree, never in the active checkout.
6. Commit coherent changes and publish at useful integration checkpoints; open a draft pull request with the first push. Do not require a separate push, full suite or coordinator approval for each local step. Preserve work before a handoff and keep the remote PR current enough for independent review and recovery.

## Follow CI

After each push, assign one agent or process to track automated build, test and deployment checks (CI/CD) through completion. Implementation can continue while checks run. Reuse the collected results rather than polling the same unchanged run from several agents.

Inspect failed, stalled or unusually long jobs and their step logs immediately; do not wait for the whole workflow to finish. If failure details are unavailable, report that limitation. A running job is not evidence of success.

Diagnose before rerunning. Fix within the assignment or send the finding, impact and independent work to the coordinator, then verify the affected checks. Reuse an existing shared-failure investigation and coordinate its repair. Record the cause, action and evidence in the PR, following the [blocking rules](../references/board.md#decide-what-actually-blocks-work).

Resolve ordinary conflicts within the assigned scope using the [integration rules](supervisor.md#parallel-work-and-integration). If no independent step remains, return to the coordinator under the [Waiting rules](../references/board.md#waiting-and-resumption).

## Finish

1. Report `Reviewing`. Use independent review to cover the Issue, this skill and repository rules on the identified state. Reuse valid earlier review; split reviewers' main scopes only when useful.
2. Combine and deduplicate findings. Fix defects in the agreed behaviour, integrity or acceptance criteria and violations of required repository or skill rules. Send other findings to the coordinator for Analyst triage; do not dismiss findings or defer requirements yourself. Recheck changed behaviour and dependencies; repeat the whole review only if the change invalidates its wider conclusions.
3. On a stable candidate, run the full test suite for application changes and all other required checks after narrower checks pass. Confirm that required CI/CD checks which run in draft passed for the current PR revision; a handoff alone does not require repeating valid checks.
4. Take the pull request out of draft to run any remaining required checks. Report readiness for `Code review` to the synchronization owner and hand it to the coordinator only after the [Code review entry condition](../references/board.md#code-review-entry-condition) passes. For application changes, start independent exploratory testing of the real application with `agent-browser` at the same time. Human review and exploratory testing do not wait for each other.
5. Apply the same finding and recheck rules to later feedback. Record the checked source revision, relevant local changes, checks and limitations in the pull request; link that evidence in the handoff. For live checks, confirm the running build matches that state and describe the exact scenario, distinguishing real services, substitutes and unavailable checks.

The coordinator completes the [merge gate](supervisor.md#merge-gate). Report any unavailable live check precisely, help restore it, and continue independent work under the blocking rules.

If you find work outside the Issue, report it to the coordinator. Do not expand the Issue or create another task.
