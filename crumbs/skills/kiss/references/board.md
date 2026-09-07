# GitHub Project

The configured GitHub Project is the backlog and progress view. Resolve it from `githubProject.owner` and `githubProject.number`; do not guess an organisation-owned board.

## Content

- Issue body: current requirements and verified context.
- Project position: priority.
- Project status: current phase.
- Pull request: implementation, review, and verification.
- Pull request discussion: implementation feedback.
- Issue comment: only a question, its answer, or a durable decision.

Do not post plans, phase traces, routine progress, or agent conversations to the Issue.

The order of cards in `Todo` is their priority. Only the Analyst changes it. Resolve the Project and item identifiers, then move the highest-priority item to the top:

```bash
gh api graphql -f query='mutation($p:ID!,$i:ID!){
  updateProjectV2ItemPosition(input:{projectId:$p,itemId:$i}){clientMutationId}}' \
  -f p="<project-id>" -f i="<item-id>"
```

To place an item lower, pass `afterId` for the item that should precede it.

## Status

Use the existing Project phases:

| Status | Meaning | Owner |
| --- | --- | --- |
| `Todo` | Defined and not assigned | Analyst |
| `Planning` | Assigned; Developer is inspecting the task | Supervisor |
| `Implementing` | Code and tests are changing | Developer |
| `Reviewing` | Internal diff review or repair | Developer |
| `Testing` | Exploratory testing is the remaining gate | Developer |
| `Blocked` | Waiting for a human decision, external dependency, or pull request review | Role that found the blocker |
| `Ready` | Pull request approved and ready to merge | Supervisor |
| `Last done` / `Done archive` | Merged work | Supervisor |

After internal `Reviewing`, request pull request review and start exploratory testing in parallel. While review is pending, keep the card in `Blocked` with `waiting-for-pr-review`. If review finishes first, remove the label and use `Testing`. Move to `Ready` only after both pass.

Move a card before starting its phase. The Supervisor reconciles the board with the agent and pull request when they disagree.

## Commands

Read the board without changing it:

```bash
gh project item-list <number> --owner <owner> --format json --limit 100
gh project field-list <number> --owner <owner> --format json
```

Before a write, resolve the current project, item, field, and option identifiers from these commands. GitHub identifiers are not constants. Use `gh project item-add` for a new Issue and `gh project item-edit` for its status.
