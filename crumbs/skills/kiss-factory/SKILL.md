---
name: kiss-factory
description: Runs a factory of coding agents over one GitHub backlog — plans work into issues, dispatches parallel lanes into Ona environments, collects what comes back. Use when the user wants to feed, start, inspect, or stop the factory, or to turn a discussion into backlog work for it.
---

# kiss-factory

A fleet of coding agents works one GitHub backlog and turns issues into pull requests waiting for
the human to merge. Two of them run on the human's own machine. The rest run in disposable Linux
machines in Ona and never speak to the human directly.

Most of what follows describes that arrangement: several tasks at once, each in its own machine. The
factory can also run entirely on the human's machine, one task at a time — same roles, same backlog,
far less machinery. `references/local-flow.md` says what changes.

`kiss` is a different skill, for work the human drives by hand. This is not that.

## Which one are you

The human names it in the argument they invoke this skill with: `supervisor` or `analyst`. Read
`roles/supervisor.md` or `roles/analyst.md` and follow it — this file is common ground, that one is
your job. If they named neither, ask before doing anything.

Load the rest only when you need it:

| File | Read it when |
| --- | --- |
| `references/board.md` | you move a card, or check the board against reality |
| `references/ona.md` | you start, inspect, restart or delete an environment or an agent |
| `references/secrets.md` | you dispatch a lane, or the application cannot reach the model |
| `references/invariant-sweep.md` | one invariant crosses components, or a repair finds another missed path to it |
| `references/local-sessions.md` | you are the supervisor or the analyst |
| `references/setup.md` | the factory has never run on this repository |
| `added-comments.sh` | you are about to check a diff for comments added to production code |
| `flow-metrics.sh` | you want to know where the time goes and what keeps coming back |
| `references/local-flow.md` | the factory is running on the human's machine, one task at a time |

## The words this skill uses

- **Lane** — one task being worked on: a fresh Ona environment, a fresh branch, one implementer, and
  the reviewer and tester it launches. It is deleted after the merge.
- **Base branch** — the branch a lane starts from and merges back into. Named by the `base:<branch>`
  label on the issue; no label means `main`.
- **Cockpit** — the long-lived Ona environment that hosts the planner.
- **The gate** — the supervisor's check of a finished pull request, before it merges.
- **Trace** — the comment a role leaves on the issue or the pull request saying what it did. It is
  how anybody later knows a step happened rather than being skipped.

## Where things live

- **The backlog is GitHub issues** on the repository of the current directory. Goal, context, key
  decision, acceptance criteria and discussion all live in the issue. There is no task file.
- **Priority and progress are the Project board.** See `references/board.md`.
- **A question for the human is the label `needs-human`**, with the question itself as a comment.
  The analyst answers it. The human never opens GitHub.
- **A fault in these instructions is the label `factory-defect`**, with what was measured as the
  issue body. Any role may raise one; the analyst repairs it and no lane is ever dispatched onto
  one. Writing it down rather than messaging is what makes it survive to the next morning.
- **A raw report from a lane is the label `needs-shaping`.** A tester judges the screen and never
  the code, so what it files says what happened, not what to change. No lane is dispatched onto one
  until a triage has read the code and turned it into a task with acceptance criteria.
- **Role instructions are `roles/`, next to this file.** A lane reads them from its own base branch.
- **A lane's branch is `lane/<short-kebab-summary>`** — the same shape as every other branch in the
  repository, with `lane` as the type. The summary says what the change does, never which issue
  asked for it: these branches sit in one list with everybody else's, and a number tells the next
  reader nothing. The lane's environment takes the same name with the slash turned into a dash, so
  `lane/extract-review-module` runs in `lane-extract-review-module`. A merge-verifier gets its own
  fresh environment on the same branch, named `verify-` plus that same summary. Those two names are
  what lets anything reading a list of machines tell which lane a machine belongs to, and which of
  the pair is the one still building.
- **What the fleet has learned about working here is the factory brain**, on the repository's GitHub
  wiki under **Factory brain**. Not how to work — that is these instructions — and not what the
  product should be, which is `docs/`. It holds only what a run showed and the code does not say:
  what was tried and failed, what is unreliable, what things cost, where the migration stands. The
  librarian writes it; the planner and a triage read it, because ordering work and shaping a report
  are the two jobs that go wrong without it. **The code always wins** — an entry the code
  contradicts is out of date, not authoritative.
- **Everything durable is in GitHub.** An agent's memory is not durable. If it has to survive a
  restart, it is a comment, a label, or a commit.
- **Everything the fleet writes into GitHub is in English.** Issue bodies, comments, commit
  subjects and messages, pull request titles and bodies, branch names. The human may speak to you in
  another language and you answer in theirs — but what lands in the repository is read later by
  people who were not in that conversation, and a history in two languages cannot be searched or
  skimmed as one. **This applies to what you write from now on, and never backwards.** Most of the
  backlog predates the rule and stays in the language it was written in — translating it would
  rewrite work nobody asked to have rewritten, and a task half-translated is worse than a task not
  translated. Leave an existing issue alone unless you are rewriting its content anyway.
- **Every pull request the factory opens carries the label `kiss-factory`**, set when it is opened.
  People work this repository by hand alongside the fleet, so this is what tells the two apart at a
  glance and what makes "show me everything the factory produced" a single filter.
- **Every comment a role writes starts with its own name in square brackets** — `[supervisor]`,
  `[analyst]`, `[planner]`, `[implementer]`, `[reviewer]`, `[tester]`, `[triage]`,
  `[merge-verifier]` — as the very first characters. Every agent writes to GitHub as the same user,
  so without the tag an issue reads as one voice arguing with itself and nobody can tell which step
  happened. With it, checking that a lane did what it was told is a search rather than a judgement.
- **Work comes from GitHub and nowhere else.** `.kiss/` is the backlog of the `kiss` skill, which
  the human drives by hand. No role takes work from it, and no role authors work there. A file under
  `.kiss/` that is *generated* from the board is a convenience and harmless; a file anybody edits by
  hand is a second backlog, and within a day the two disagree and whichever an agent happens to open
  becomes the truth.

## The fleet

| Role | Runs in | Lives for |
| --- | --- | --- |
| supervisor | the human's own machine | as long as the factory runs |
| analyst | the human's own machine | as long as the conversation |
| planner | the cockpit | long-lived, restartable at any moment |
| implementer | a fresh environment per lane | one task |
| reviewer | the implementer's own environment | one pull request |
| tester | the implementer's own environment | one pull request |
| triage | the cockpit, called by the planner | one batch of reports |
| librarian | the cockpit, called by the planner | one pass over the day |
| merge-verifier | a fresh environment | one conflict resolution |

Every one of them runs `--model opus --effort xhigh`.

## Rules the whole fleet obeys

1. **A lane is a fresh environment on a fresh branch off its base**, deleted after the merge. Its
   pull request targets that base branch, which is `main` only when `main` is the base.

2. **At most five pull requests wait for the human at once, and at most five lanes run at once.**
   Count only what the factory produced: pull requests off a `lane/` branch, marked ready, drafts
   excluded, across all bases. A repository normally carries long-lived integration pull requests
   that nobody is waiting on — count those and the factory refuses to dispatch from its first cycle.

   The two numbers are the same on purpose: a finished pull request holds its slot until it is
   merged, so a sixth lane could only ever wait behind one.

   **Raising the number costs conflicts, and not in proportion.** Every lane on one base branch is
   another pair of hands in the same files, and a lane that takes long enough gets overtaken more
   than once — the second time by a change that has already moved the file it was editing. Watch the
   rate rather than the count: if lanes start spending more time rebasing than building, the number
   is too high for how coupled this base branch is, and the fix is a lower number.

3. **Progress is read from GitHub, never from a held connection.** The implementer opens its pull
   request as a draft immediately, pushes as it goes, and writes its plan and findings as issue
   comments. Nothing valuable may exist only inside an agent.

4. **The first to merge wins a conflict outright.** The loser rebases and resolves after reading the
   other task's issue, not just its diff, so that both intentions survive. A fresh merge-verifier
   then checks the acceptance criteria of **both** tasks — that is the guard against a resolution
   that quietly undoes the winner's work.

5. **Nothing is ever given up on.** A task that fails is re-planned and tried again, without limit,
   but it drops in the order every cycle so it yields to fresh work. The count of attempts lives on
   the issue.

6. **The tester never blocks the human; it blocks ready.** Deterministic tests belong to the
   implementer, and the repository's own checks answer whether the code runs. The tester answers a
   different question — whether a person can use what was built — and runs in the implementer's
   environment before the pull request is marked ready. What it finds splits in two: this task's own
   acceptance criteria broken on screen go back to the implementer and hold the pull request in
   draft; everything else becomes issues and holds up nothing. A change to a build file, a workflow
   or a developer script has no screen to visit, so it skips this.

7. **Refuse rather than guess.** A base branch without `.claude/skills/kiss-factory/roles/` gets no
   lane. An implementer without its instructions is worse than no implementer.

8. **`hands-off` means a person is on it.** The factory never dispatches such an issue and never
   removes the label — only the human does. This is what lets a person work the same backlog
   alongside the fleet without the two colliding.

9. **No diff reaches the human unread.** With the checks green and before the pull request leaves
   draft, a reviewer reads the diff against the issue's acceptance criteria and the repository's
   rules under `.claude/rules`, and the implementer fixes what it finds. It runs in the
   implementer's own environment, because a finding is cheap while its author is still running and
   holds the context, and expensive once the lane is gone. The repository's checks prove the code
   runs; they never read it.

11. **Re-verification is sized to what changed, not to the fact that something changed.** A pull
    request sent back over something that cannot alter a single execution — comment lines, a rename,
    a label — is repaired against that list alone: checks green, a reviewer confirming those
    findings, no tester. The rest was read and driven while its author was still alive, and reading
    it again cannot make it more finished. Whoever sends the work back says which kind it is, and
    when in doubt says it can change behaviour.

10. **Only the two local agents speak to the human.** Any other role that needs a decision pushes
    what it has, writes the question as an issue comment, labels the issue `needs-human`, and ends.
    It does not wait — a lane sitting on a question holds an environment and a slot for as long as
    the human is asleep. The analyst brings the question to them and writes the answer back as a
    comment; the planner then restarts the lane from the branch already pushed.

## Watching from outside

`gh pr list`, `gh issue list --label in-flight`, and the board. None of them requires asking an
agent anything.
