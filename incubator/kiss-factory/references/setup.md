# Setting the factory up on a repository

Done once, before the factory first runs. Steps 3 and 4 change things outside this repository, so
ask the human before either.

**1. Give the local machine permission to write the board.**

```bash
gh auth refresh -s project
```

Only needed if something running locally has to write the board. The token inside Ona already
carries that permission.

**2. Create the board and the labels.**

The labels are `in-flight` (a lane is running on this issue), `hands-off` (a person is working it by
hand), `needs-human` (a lane stopped on a decision only the human can take), `needs-shaping` (a raw
report from a lane, not yet a task), `factory-defect` (something is wrong in the factory's own
instructions), `kiss-factory` (this pull request came from the fleet, not from a person), and one
`base:<branch>` per group of work that shares a branch.

A new Project board ships with Todo / In Progress / Done. Replace those three with the nine columns
listed in `references/board.md`, in that order. One lump of "in progress" is exactly what the human
cannot read.

**3. Turn any existing backlog files into issues, then delete the files.**

This creates a lot of issues in a shared repository, so **ask the human first**. Two lists both
claiming to be the backlog is worse than either alone — whichever one an agent happens to read
becomes the truth, and the two drift apart within a day.

**4. Mount the application's `.env` as an Ona project secret.**

Without it no environment can start the application, so the tester has nothing to drive. The
commands are in `references/secrets.md`.

**5. Start the planner** in the cockpit environment, following `references/ona.md`. It needs a
branch that already carries `.claude/skills/kiss-factory/roles/`, because it reads its own
instructions out of the working tree.
