# GitHub Project

The configured GitHub Project is the backlog and progress view. Resolve it from `githubProject.owner` and `githubProject.number`; do not guess an organisation-owned board.

## Content

- Issue body: current requirements, verified context and authorized deferrals with follow-up links.
- Project position: priority.
- Project status: current phase.
- Pull request: implementation, review, and verification.
- Pull request discussion: implementation feedback.
- Issue comment: only a question, its answer, or a durable decision.
- Execution record: one compact, replaceable section in the Issue body or equivalent Project fields. Keep the coordinator, executor/session/environment/checkout/branch, latest verified result and time, next action, and any awaited event, resume phase and follow-up deadline. Link detailed verification from the PR; do not copy logs.

Do not post plans, phase traces, routine progress comments, or agent conversations to the Issue. Update the execution record in place only when its facts change. A synchronization cache may store event IDs and Slack mappings, but it is not a second backlog.

## Write for a human

Follow the [Issue writing guide](writing.md) for titles, descriptions and comments.

## Labels

Use these labels on Issues and PRs:

- One task-group label, such as `engine` or `review and protocol`. Reuse the project's established names; these examples are not mandatory groups. The Analyst chooses the group by delivered responsibility, not every file touched. Apply it to both the Issue and its implementing PR; classify a standalone PR by its own scope.
- Optional `bug` when the work fixes incorrect behaviour, not for every enhancement or refactor. A failed CI run alone does not make the underlying task a bug.

- `needs-human` only when further progress requires a specific human decision not covered by existing instructions or authority. Record the question on the affected Issue or standalone PR and ask the human; the label alone is not a notification. Remove it as soon as the answer or existing evidence resolves the question. Routine review, failed CI and technical dependencies do not qualify.

Do not create or maintain other workflow labels such as `in-flight` or `waiting-for-pr-review`. The board records phase, the PR records reviews and checks, and the execution record identifies the active worker and any unresolved question. KISS removes its obsolete workflow labels from assigned Issues and PRs during synchronization, but preserves unrelated labels owned by other tools or required by the repository. Any other KISS classification needs an explicit project requirement.

## Priority

The order of cards in `Todo` is their priority. Only the Analyst changes it. Resolve the Project and item identifiers, then move the highest-priority item to the top:

```bash
gh api graphql -f query='mutation($p:ID!,$i:ID!){
  updateProjectV2ItemPosition(input:{projectId:$p,itemId:$i}){clientMutationId}}' \
  -f p="<project-id>" -f i="<item-id>"
```

To place an item lower, pass `afterId` for the item that should precede it.

## Status

Use these phases in display order. The owner in this table is responsible for the work; the synchronization owner writes the status. `Waiting` and `Blocked` are exceptions, not mandatory stages:

| Status | Meaning | Owner |
| --- | --- | --- |
| `Todo` | Defined and not currently assigned; preserve any prior checkpoint | Analyst |
| `Planning` | Assigned; Developer is inspecting the task | Coordinator |
| `Blocked` | Progress requires a human decision, or a confirmed defect makes the entire system unusable | Role that found the blocker |
| `Implementing` | Code and tests are changing, including ordinary conflict or CI repair | Developer |
| `Waiting` | No useful independent step remains; a named result will allow work to resume | Coordinator |
| `Reviewing` | Internal diff review or repair | Developer |
| `Testing` | Required verification is the remaining gate | Developer |
| `Code review` | Non-draft PR with all required CI/CD checks green for its current revision, awaiting external review or merge | Coordinator |
| `Last done` | Recently merged work with its acceptance criteria complete | Coordinator |
| `Done archive` | Earlier completed work | Coordinator |

After internal review and the Developer's [readiness checks](../roles/developer.md#finish), external review and exploratory testing run in parallel. Choose the phase in this order:

1. A qualifying `Blocked` condition takes precedence.
2. Active repair uses `Implementing`, or `Reviewing` for internal-review fixes, even if external review is pending.
3. Apply the [Code review entry condition](#code-review-entry-condition). Unfinished automated verification uses `Testing`, or `Waiting` only under the rules below; it does not qualify for `Code review`.
4. Once that condition passes, pending external review uses `Code review`. After approval, remaining exploratory verification uses `Testing`; when it also passes, use `Code review` for the [merge gate](../roles/supervisor.md#merge-gate).

Read pending reviews and approvals from the PR, independently of the board phase. Missing merge authority requires a human decision; permission already given does not need renewal.

### Code review entry condition

Before entering or remaining in `Code review`, a PR must be non-draft and every required CI/CD check must have completed successfully for its current head and applicable integration revision. Pending, failed, cancelled, missing or unknown results do not qualify. An approval, review request, local pass or green result from an older revision cannot replace that evidence.

Recheck this condition after each push and CI/CD result. If it no longer holds, move the card out of `Code review`: assign failed checks to a repair owner in `Implementing`, or use `Testing` for unfinished verification and `Waiting` only when no useful independent work remains. A shared or apparently unrelated failure still prevents this PR from entering `Code review`; continue useful work under the rules below.

### Waiting and resumption

Use `Waiting` only after checking that no useful independent step remains. Record the exact dependency or CI run, who owns its resolution, who will resume the task, the saved checkpoint, return phase and next follow-up time. Preserve genuine native dependency links. Keep one coordinator responsible even if the Developer is idle or reassigned safely.

`Waiting` still counts as started work against the agreed work-in-progress limit; it does not free unlimited capacity for new tasks. Record whether a Developer is actively executing in the execution record and verify it on resumption. Agent allocation and started-work count are different facts.

A running required check can justify `Waiting` when no useful independent work remains; an outstanding external review request does not override the Code review entry condition. Before waiting for a colleague, check their state and arrange recovery if needed. Shared files and ordinary conflicts follow the [integration rules](../roles/supervisor.md#parallel-work-and-integration).

The coordinator resumes the same Issue when its event arrives, after checking remaining dependencies. An expired follow-up triggers investigation and, if needed, reassignment. It does not require renewed permission or automatically mean `Blocked`. Notify the human when the impact changes or a decision is needed.

### Decide what actually blocks work

An edge-case defect that leaves the application usable does not stop other work by default. Establish its actual impact: a failed shared test alone does not prove that every affected task depends on the repair. Continue implementation, review and checks that can proceed independently; keep their cards in the phase being performed. Do not add blocking dependencies merely because tasks share a failing check.

Record the finding and evidence in the pull request. The coordinator establishes an owner and next action for the finding. A delegated Supervisor sends the impact and continuing work to the Analyst, who notifies the human; when coordinating directly or when the Analyst is unreachable, the coordinator sends that notice. This is a notification, not a request for permission to continue. Do not wait for an answer unless a specific unresolved decision is required. Follow a human instruction to stop, and notify again only if the impact changes materially.

Use `Blocked` only in two cases:

- Work cannot proceed without a specific human decision that existing instructions and authority do not answer. Record one clear question, apply `needs-human` under the [label rules](#labels), and ask the human through the Analyst, or directly through the coordinator if the Analyst is unreachable.
- A confirmed defect makes the entire system unusable. Record evidence of that impact and the repair needed, notify the human, and have the coordinator coordinate recovery. Ask a question only if a human decision is also required.

Failed checks, unavailable test environments, plugin failures and dependencies do not qualify by themselves. The coordinator assigns their diagnosis and repair, keeps independent work moving and uses `Waiting` only under the rules above. Releasing an assignment to `Todo` preserves its checkpoint. Genuine dependency links do not automatically mean `Blocked`.

These phase rules do not waive acceptance criteria, required checks, review or branch protection. Merge exceptions require explicit human authorization.

Report a phase when it starts. A failed metadata write does not stop independent implementation; the [synchronization owner](synchronization.md) repairs it and verifies the board state.

## Commands

Read the board without changing it:

```bash
gh project item-list <number> --owner <owner> --format json --limit <enough-to-include-all-items>
gh project field-list <number> --owner <owner> --format json
```

Ensure the read covers every item; use pagination when needed. Before a write, resolve the current project, item, field, and option identifiers from these commands. GitHub identifiers are not constants. Use `gh project item-add` for a new Issue and `gh project item-edit` for its status.
