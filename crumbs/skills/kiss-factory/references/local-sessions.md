# The two sessions on the human's machine

The human never opens GitHub. Everything that needs them reaches them in a local conversation, and
their answer travels back to GitHub from there.

That is two jobs, not one, and they get in each other's way. **Watching a machine** wakes every few
minutes whether or not anybody is there. **Thinking with a person** must never be interrupted. Run
them as one session and either the monitoring stops for the length of a design discussion, or the
discussion is cut every five minutes by a status report.

| | **supervisor** | **analyst** |
| --- | --- | --- |
| Wakes | on its own timer, always | only when the human speaks |
| Owns | the running factory | the backlog, and this skill's own instructions |
| Talks about | what happened | what should happen |
| Ends when | the factory stops | the conversation ends |

They are started independently, each told which one it is:

```
claude --name supervisor   # then: /kiss-factory supervisor
claude --name analyst      # in another terminal, then: /kiss-factory analyst
```

**Name them.** Left alone, a session names itself after its directory, so two sessions started in
one directory come up with near-identical generated names and nothing says which is which. The name
is also the address the other one is reached by.

## Seeing the other one

**`ListAgents`, and nothing else.** It is the only listing that crosses the boundary between
sessions; it prints each one's name, whether it is busy or idle, and how long it has been up.

`claude agents --json` will never show a sibling. That command answers "what is running *under
me*" — this session and the agents it started itself — so a session launched at another terminal is
absent from it by design. Reading that absence as "the other one is not running" is wrong every
time.

## Messaging the other one

`SendMessage` delivers plain text from one local session into another over a socket on this machine,
never through a server. It addresses a peer by exactly the name `ListAgents` prints.

It needs Claude Code v2.1.224 or later — or **v2.1.248 or later** on a custom `ANTHROPIC_BASE_URL`
such as a corporate gateway, or with feature flags off. Below that the socket is never bound,
`CLAUDE_CODE_MESSAGING_SOCKET` is empty, `ListAgents` finds no peers, and every send fails with "no
agent named … is reachable".

Those two failures look identical from inside: a peer that is genuinely absent, and a channel that
was never built. Check `CLAUDE_CODE_MESSAGING_SOCKET` before concluding anything about the other
session.

**The handover of record is the label and the comment, never the message.** A direct message dies
with whichever session restarts first; `needs-human` on the issue outlives both. Hand a question
over by labelling it, and only then, optionally, by a nudge.

## One working tree, two writers

Both sessions are started in the same directory, so they share one checkout, one set of uncommitted
changes and one branch. There is no lock and there will not be one: a lock is a mechanism, and a
mechanism that lives in a local session dies with it. Two agents writing to one file is ordinary
here, and the only question worth asking is which collisions announce themselves.

**An exact-string edit announces itself, and it is the only protection there is.** It refuses when
the text you were matching has moved, and it refuses when the file changed at all since you read it.
Either way you re-read and retry, and nothing is lost. Because it costs a retry rather than silence,
it needs no warning beforehand.

**Everything that cannot fail that way needs one message first, before you start:**

- **Writing a file end to end, or rewriting a whole section.** A whole-file write does not check
  what it is replacing — it destroys whatever the other one wrote since you last read, without a
  word.
- **Pulling, rebasing, or changing branch.** That moves the ground under a session in the middle of
  an edit, and it is the one collision neither of you can see coming.

Send the message, then proceed. You are announcing, not asking permission — waiting for an answer
from a session that may be busy for ten minutes is what stops the announcement being worth making.

**Never `git stash` and never `git stash pop`.** A pull refuses to start against a dirty working
tree, and the obvious way out is the one that destroys work silently: the stash stack is shared by
every worktree of the repository, so a bare `pop` can restore — and then drop — an entry another
session pushed seconds earlier, into a different tree than it came from. Use
`git pull --rebase --autostash`, which sets the change aside and puts it back inside one operation,
leaving nothing on the stack for anybody else to take. When something has to be set aside for
longer, a throwaway commit on the branch is safer, because a commit has your name on it and nobody
pops it by accident.

Expect a dirty tree that belongs to neither of you: the human leaves edits of their own sitting
there. Do not commit them and do not clear them — `--autostash` carries them across untouched.

**Before you commit, read `git status`.** Anything modified that you did not touch is the other
one's, still being written. Add the paths you changed and only those; never `git add -A`. Where one
file carries both of your work, committing it beats leaving it at risk — but say so, because your
message is then describing writing that is not yours.

**With the channel down, do only the half that fails loudly.** No `SendMessage` means no
announcement, so keep to exact-string edits and commits scoped to your own paths, and leave the
whole-file writes and the rebases until the other session can hear you.

## Correcting these instructions

**An instruction usually lives in one file; a fact about how something behaves almost never does.**
Fix the step a role takes and the file that owns that step is the whole job. Fix a fact — how a tool
behaves, when a change reaches an environment, what a failure means — and you have probably left
copies of the old fact standing elsewhere, each still being reasoned from.

So when what you are correcting is a fact, search every file under `roles/` and `references/`, and
this skill's `SKILL.md`, and treat the correction as unfinished until that search comes back empty.

**An edit reaches only the next agent to start.** One already running holds its instructions in its
context. Worse, an agent whose instructions live in a scheduled task or in the prompt it was
launched with never reads the file again at all, so it stays invisible to your correction until
somebody rearms or restarts it — and it will go on doing the wrong thing while agreeing with you
that the wrong thing is wrong.

So finish a correction by naming, one by one, who is still carrying the old version. Not "the fleet
will pick this up": the names.

**An agent that repeats on a schedule can escape this, and should.** If it begins each firing by
reading its own instructions off the branch, the prompt stops being a copy that ages and becomes a
short fallback for when that read fails. The supervisor works that way — see `roles/supervisor.md`.
It is the only shape here that makes a correction arrive without anybody carrying it.

**A line added to the launch recipe is the same problem wearing a different hat.** The recipe in
`references/ona.md` runs once, when a machine is created, so a setting added to it exists only in
machines created afterwards. Every machine already running is missing it, and unlike an instruction
it cannot be re-read — somebody has to go and apply it.

That somebody is the supervisor, and this is one of the few things it may do without waiting: run
the line over every running environment, read the value back to confirm, and say which machines it
covered. It costs seconds and it closes a window that otherwise stays open until the last lane
finishes. Whoever adds the line names the machines; the supervisor applies it.

## Neither session may be load-bearing

The factory runs in Ona. Both local sessions sit on a laptop that gets closed, loses its network and
reboots. **Nothing in the running factory may depend on a local session being up.** Without the
supervisor the factory keeps building, unsupervised; without the analyst it keeps building, unfed.

That is a constraint on design, not a hope. Every mechanism the factory needs to survive a night
lives where the work lives:

- A lane stays alive because the planner armed it at dispatch. The supervisor's sweep repairs what
  was missed; it is not what keeps lanes running.
- The board stays honest because the lane moves its own card.
- A dead lane is restarted by the planner, from GitHub, on its own cycle.
- A question waits on its label for as long as it takes, and nothing burns while it is open, because
  a lane that asks one ends rather than waiting.

What genuinely stops without the supervisor is the merge gate: nobody checks, nobody merges. Lanes
finish, the ready queue fills, the planner stops dispatching, and the factory idles with its work
intact. That is the correct failure — it waits rather than breaking.
