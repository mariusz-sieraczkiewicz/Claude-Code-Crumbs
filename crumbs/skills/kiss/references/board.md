# GitHub Project

The configured GitHub Project is the backlog and progress view. Resolve it from `githubProject.owner` and `githubProject.number`; do not guess an organisation-owned board.

## Content

- Issue body: current requirements, verified context and authorized deferrals with follow-up links.
- Project position: priority.
- Project status: current phase.
- Pull request: implementation, review, and verification.
- Pull request discussion: implementation feedback.
- Issue comment: only a question, its answer, or a durable decision.

Do not post plans, phase traces, routine progress, or agent conversations to the Issue.

## Write for a human

Apply [Simple Talk](../../clean-ai-text/references/simple-talk.md) to every Issue title, body and comment. Use the task's agreed language and terminology. The reader knows neither the agent conversation nor the implementation details.

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

Use the existing Project phases:

| Status | Meaning | Owner |
| --- | --- | --- |
| `Todo` | Defined and not assigned | Analyst |
| `Planning` | Assigned; Developer is inspecting the task | Supervisor |
| `Implementing` | Code and tests are changing | Developer |
| `Reviewing` | Internal diff review or repair | Developer |
| `Testing` | Required verification is the remaining gate | Developer |
| `Blocked` | Waiting for a human decision, external dependency, or pull request review | Role that found the blocker |
| `Ready` | Pull request approved and ready to merge | Supervisor |
| `Last done` / `Done archive` | Merged work | Supervisor |

After internal `Reviewing`, request pull request review and start required exploratory testing in parallel. While review is pending, keep the card in `Blocked` with `waiting-for-pr-review`. When review finishes, remove the label and use `Testing` if required verification remains. Move to `Ready` only after approval and required verification pass.

Move a card before starting its phase. The Supervisor reconciles the board with the agent and pull request when they disagree. When closing an Issue, remove stale active-status text and reconcile its criteria with delivery and authorized deferrals; keep verification evidence in the pull request.

## Commands

Read the board without changing it:

```bash
gh project item-list <number> --owner <owner> --format json --limit 100
gh project field-list <number> --owner <owner> --format json
```

Before a write, resolve the current project, item, field, and option identifiers from these commands. GitHub identifiers are not constants. Use `gh project item-add` for a new Issue and `gh project item-edit` for its status.
