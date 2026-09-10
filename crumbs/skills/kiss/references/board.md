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

Apply [Simple Talk](../../clean-ai-text/references/simple-talk.md) to every Issue title, body and comment. Keep the task's terminology. The reader knows neither the agent conversation nor the implementation details.

- **Title:** name the change and its effect in plain words, preferably 5–8 words. Preserve required project prefixes, identifiers and suffixes. Avoid vague titles such as "Refactor engine" and titles built from class names or unexplained abbreviations.
- **Body:** start with a short paragraph explaining the problem and intended behaviour. Follow with observable acceptance criteria, usually 3–5 bullets. Aim for 1,500 characters or fewer; use more only when needed to preserve agreed requirements, authority or essential constraints. Omit empty sections and repeated summaries.
- **Technical context:** keep only details that change what a correct solution must do. Link to the relevant source instead of copying architecture, workflow rules, file lists or logs. Describe what a link or identifier refers to; a section number or path alone is not an explanation. Keep exact names when they are necessary.
- **Comments and notes:** record only a question, its answer or a durable decision, usually in 2–4 sentences. State what needs deciding or what was decided, why it matters, and the effect on the task. Do not paste agent handoffs, reasoning transcripts, command output or progress reports. Implementation and verification evidence belongs in the pull request.
- **Updates:** keep one coherent current description, not successive addenda or duplicated requirements. Preserve agreed scope and criteria when shortening; follow the Analyst's rules for changes after work starts.

For example, prefer **"Keep user edits when AI finishes"** to **"Implement draftVersion guard in result hydration"**. Explain that a late AI result must not overwrite text edited after generation started; use the exact technical name only if the implementation needs it.

Before saving, reread the title and text as a new reader: can they tell what changes, why, and when it is done? Remove repetition and unnecessary detail, not requirements. Check that the final Markdown has real paragraphs and lists rather than escaped newlines.

## Priority

The order of cards in `Todo` is their priority. Only the Analyst changes it. Resolve the Project and item identifiers, then move the highest-priority item to the top:

```bash
gh api graphql -f query='mutation($p:ID!,$i:ID!){
  updateProjectV2ItemPosition(input:{projectId:$p,itemId:$i}){clientMutationId}}' \
  -f p="<project-id>" -f i="<item-id>"
```

To place an item lower, pass `afterId` for the item that should precede it.

## Status

Use these Project phases in this display order. The coordinator is the Analyst or their delegated Supervisor; Waiting and Blocked are exceptions, not mandatory stages:

| Status | Meaning | Owner |
| --- | --- | --- |
| `Todo` | Defined and not currently assigned; preserve any prior checkpoint | Analyst |
| `Planning` | Assigned; Developer is inspecting the task | Coordinator |
| `Blocked` | Progress requires a human decision, or a confirmed defect makes the entire system unusable | Role that found the blocker |
| `Implementing` | Code and tests are changing, including ordinary conflict or CI repair | Developer |
| `Waiting` | No useful independent step remains; a named result will allow work to resume | Coordinator |
| `Reviewing` | Internal diff review or repair | Developer |
| `Testing` | Required verification is the remaining gate | Developer |
| `Code review` | Pull request awaiting external review or completion of the merge gate | Coordinator |
| `Last done` | Recently merged work | Coordinator |
| `Done archive` | Earlier merged work | Coordinator |

After internal `Reviewing`, request pull request review and start required exploratory testing in parallel. While review is pending, keep the card in `Code review` with `waiting-for-pr-review`. After approval, remove the label and use `Testing` if required verification remains. Once approval and required verification pass, use `Code review` for the final merge gate; the coordinator merges under existing human authority. If merge authorization is missing, use `Blocked` with `needs-human`.

### Waiting and resumption

Use `Waiting` only after checking that no useful independent step remains. Record the exact dependency or CI run, who owns its resolution, who will resume the task, the saved checkpoint, return phase and next follow-up time. Preserve genuine native dependency links. Keep one coordinator responsible even if the Developer is idle or reassigned safely.

`Waiting` still counts as started work against the agreed work-in-progress limit; it does not free unlimited capacity for new tasks. Remove `in-flight` when no Developer is actively executing the task, and restore it on verified resumption. Agent allocation and started-work count are different facts.

A running required check can justify `Waiting` when nothing else remains. A repair in progress stays `Implementing` or `Testing`; ordinary external review stays `Code review`. Waiting for a colleague to answer is not a substitute for checking their state and arranging recovery. Shared files and ordinary conflicts follow the [integration rules](../roles/supervisor.md#parallel-work-and-integration).

The coordinator resumes the same Issue when its event arrives, checks any remaining dependencies and returns to the appropriate phase. The follow-up deadline triggers investigation and reassignment if needed, not another permission request or automatic `Blocked`. Keep the human informed only when the impact changes or a decision is required.

### Decide what actually blocks work

An edge-case defect that leaves the application usable does not stop other work by default. Establish its actual impact: a failed shared test alone does not prove that every affected task depends on the repair. Continue implementation, review and checks that can proceed independently; keep their cards in the phase being performed. Do not add blocking dependencies merely because tasks share a failing check.

Record the finding and evidence in the pull request. The coordinator establishes an owner and next action for the finding. A delegated Supervisor sends the impact and continuing work to the Analyst, who notifies the human; when coordinating directly or when the Analyst is unreachable, the coordinator sends that notice. This is a notification, not a request for permission to continue. Do not add `needs-human` or wait for an answer unless a specific unresolved decision is required. Follow a human instruction to stop, and notify again only if the impact changes materially.

Use `Blocked` only in two cases:

- Work cannot proceed without a specific human decision that existing instructions and authority do not answer. Record one clear question, add `needs-human`, and ask the human through the Analyst, or directly through the coordinator if the Analyst is unreachable.
- A confirmed defect makes the entire system unusable. Record evidence of that impact and the repair needed, notify the human, and have the coordinator coordinate recovery. Do not add `needs-human` unless a human decision is also required.

Edge cases, failed checks, unavailable test environments and waiting for another task do not qualify by themselves. KISS must diagnose and resolve them: the coordinator establishes an owner and a concrete next action and follows through. Keep active work in its actual phase. Use `Waiting` only under the rules above; retain the checkpoint if an assignment is released back to `Todo`. Preserve genuine dependency links without treating them as an automatic reason for `Blocked`.

A pending merge gate does not waive acceptance criteria, required checks, review or branch protection. Resolve technical failures within the workflow; merge exceptions still require explicit human authorization.

Ordinary pull request review wait belongs in `Code review`. Retain `waiting-for-pr-review` while that review is pending, even if another step is blocked. When the blocker is resolved, return to the phase that matches the remaining work.

Publish a phase change when that phase starts; a failed metadata write does not prevent independent implementation. The [synchronization owner](synchronization.md) reconciles the board with verified worker and PR state. Native links and GitHub automations must be checked after writes, not inferred from text references. Only close an Issue when its own criteria are complete. When closing it, remove stale active-status text and reconcile its criteria with delivery and authorized deferrals; keep verification evidence in the pull request.

## Commands

Read the board without changing it:

```bash
gh project item-list <number> --owner <owner> --format json --limit <enough-to-include-all-items>
gh project field-list <number> --owner <owner> --format json
```

Ensure the read covers every item; use pagination when needed. Before a write, resolve the current project, item, field, and option identifiers from these commands. GitHub identifiers are not constants. Use `gh project item-add` for a new Issue and `gh project item-edit` for its status.
