# Running agents in Ona

Ona gives the factory disposable Linux machines called **environments**, each with the repository
checked out under `/workspaces/<repo>`. An agent runs inside one. This file is how you start one,
read whether it is alive, and take it away again.

Read it when you create, inspect, restart or delete an environment or an agent.

## Sending a command to an environment

**Send it as a script on standard input, always:**

```bash
ona environment ssh <env> -- bash -s <<'EOF'
...
EOF
```

`exec` splits its arguments in a way that silently damages them: a multi-word value arrives
truncated, a nested `$( )` loses its command, and `cd X && cmd` runs `cmd` in the home directory.
A bare command with no quotes and no spaces in its arguments survives it — `ona environment exec
<env> -- ls` is fine — and nothing else does.

**Never `bash -lc '...'` over either of them.** The quotes are lost, so the shell receives only the
first word of what you wrote. When that word is `export`, you have run `export` with no arguments,
which prints every environment variable **with its value** — every API token, webhook and password
the environment holds — into your output and your transcript. The command you meant does not run
either, so an empty or failed result gets read as a real answer. A heredoc has no quotes to lose.

## Creating an environment

Create it from the **Ona project id**, never the repository URL. The project is what carries the
application's `.env` secret, and an environment created without it can never start the application.

```bash
ona environment create <ona-project-id> --name "<env-name>" --inactivity-timeout 3h
```

The timeout is an outer fence. An environment stops itself after a stretch it judges idle, and the
default window is short enough to kill an agent mid-task; three hours outlives any single task.

## Starting an agent

```bash
ona environment ssh <env> -- bash -s <<'LAUNCH'
set -e
export PATH="$HOME/.local/bin:$PATH"

python3 - <<'PY'
import json
p = "/home/vscode/.claude.json"
d = json.load(open(p))
d["bypassPermissionsModeAccepted"] = True
json.dump(d, open(p, "w"))
PY

cat > /tmp/lane-mcp.json <<'JSON'
{"mcpServers":{"context7":{"command":"npx","args":["-y","@upstash/context7-mcp@4.0.2"]}}}
JSON

cd /workspaces/<repo>
git config --global core.commentChar ';'
git fetch --all
git checkout -b lane/<short-kebab-summary> origin/<base>   # a new lane
# restarting on an existing branch instead:
#   git checkout <branch> && git pull --ff-only origin <branch>
claude --bg --name <role> --strict-mcp-config --mcp-config /tmp/lane-mcp.json \
  --model opus --effort xhigh --permission-mode bypassPermissions \
  "$(cat .claude/skills/kiss-factory/roles/<role>.md)

Work on issue #<issue>. Base branch: <base>."

sleep 15
setsid nohup ona environment keep-alive --pid "$(pgrep -f 'permission-mode bypassPermissions' | head -1)" \
  > /tmp/keepalive.log 2>&1 < /dev/null &
LAUNCH
```

Seven details in that script are load-bearing. Drop any one and the agent starts and does nothing,
which from outside looks exactly like an agent that is working.

- **`--name <role>`** — this is how anything else finds the agent afterwards. Left off, the name is
  generated, and the same role has come up under a different one every time its prompt or its
  directory changed. Give it the plain role name — `planner`, `triage`, `implementer` — and never
  reason about a name you did not set.
- **`export PATH`** — `claude` lives at `~/.local/bin/claude`, which a non-interactive shell over
  ssh does not have on its path.
- **`bypassPermissionsModeAccepted`** — a background session in that permission mode refuses to
  start until the disclaimer has been accepted once, and a fresh environment has nobody to accept
  it.
- **`--strict-mcp-config`** — without it the repository's `.mcp.json` opens a "new MCP servers
  found" selection screen and the agent waits on it forever.
- **`--mcp-config` must not be the last flag before the prompt** — it takes a list, so a prompt
  placed right after it is swallowed as a second config path and the session comes up with no work
  at all.
- **The prompt is positional, never `-p`** — `--bg` and `-p` conflict: `-p` never opens the session
  the background job attaches to, so the launch is rejected.
- **`git checkout`** — the agent reads its own instructions out of the working tree, so the branch
  it starts on must be one that carries `.claude/skills/kiss-factory/roles/`. **Fetch and checkout
  are enough only when you are creating a new branch.** Restarting an agent on a branch the
  environment is already sitting on — which is the cockpit's usual state — makes the checkout a
  no-op, and the agent comes up on instructions that may be hours old. Add
  `git pull --ff-only origin <branch>` there, or your fix to these files never reaches it.
- **`keep-alive`** — an environment shuts down after a stretch with no activity, and a background
  agent does not count as activity. Nobody is typing in an Ona environment, so left alone the
  machine dies about a quarter of an hour after the last time somebody looked at it, mid-task,
  taking any subagents with it. Tying the watcher to the agent's own process makes the environment
  live exactly as long as the work does. Read the process id and pass it in the same breath: a
  session's process can come back under a different number between two readings, and `keep-alive`
  then refuses with "ensure the process is running" against a process that no longer exists.

The `core.commentChar` line is a different kind of detail — a safety net rather than a requirement.
Git treats a line starting with `#` as a comment and deletes it whenever a commit message passes
through an editor, and a commit here is often titled `#<issue> — …`. During a conflicted rebase that
silently eats the subject line. `roles/implementer.md` tells the lane how to avoid it deliberately;
this setting means an agent that forgets is safe anyway. `;` rather than git's `auto` because it
works on every version.

  **Which way you read that process id depends on when you are asking.** Right after a launch there
  is exactly one agent in the environment and it has just started, so matching the process directly
  is reliable — that is what the script above does. Later, in a supervisor's round, an environment
  may hold several sessions and some of them finished long ago, and the match would also catch the
  very command you are running to ask. Then take the id from `claude agents --json`, filtered to the
  session reporting `busy`.

The planner is started the same way with two differences: no lane branch and no issue in the prompt,
and `--autocompact 450k` so it trims its own context as it runs. Compaction costs the planner
nothing, because it keeps no state that is not already in GitHub.

## Is the agent alive?

```bash
ona environment ssh <env> -- bash -s <<'EOF'
export PATH="$HOME/.local/bin:$PATH"
claude agents --json
EOF
```

`busy` is working. `idle` is finished and waiting for input that will never come. That is the only
reading that cannot lie, and it costs one word per environment.

Every entry carries `name`, `status` and `pid`; only a running one also carries `state` and `id`.
**`pid` is present on finished agents too** — the process stays resident after the work ends, which
is why a process listing is not a heartbeat and `status` is.

**Identify an agent by `name` and `status` together, never by either alone.** Finished agents keep
their entry, so after a few restarts several rows share one name and only one of them is `busy`.

**Read the whole listing. Never pipe it through `head` or `tail`.** The rows come back in no order
you can rely on, so a cut-off listing is not a shorter answer to the same question — it is a
confident wrong one. The reading it produces is always "not there", which for the planner reads as
dead and invites a restart of something that was working. The listing is a handful of lines; there
is nothing to save by trimming it.

**A name you did not set with `--name` is generated** — from the prompt, or from the directory — so
it changes under you without warning, and a role can appear under a different one each time it
starts. Never reason about a name nobody set: if a running agent has one, the launch was wrong, and
relaunching it correctly is the fix.

Inside an environment this lists the agents running there. Run in your own local session it lists
only what **you** started, so it never shows another session on the same machine — see
`references/local-sessions.md` for that.

Two readings look like the truth and are not:

- **A recent comment is not a heartbeat.** The last thing a finishing agent does is write down what
  it did, so its loudest moment is the one after which it will never speak again.
- **A running process is not a heartbeat.** A session that has finished its turn leaves its process
  resident, and a process search also matches the command you are running to ask.

## What is it doing?

Read its transcript: one JSON object per line, in a file named after the id the launch printed.

```
~/.claude/projects/-workspaces-<repo>/<agent-id>-*.jsonl
```

The lines that matter carry `message.content[]` entries of type `text` — what the agent said — and
`tool_use` — what it ran, with its input. The last dozen tell you exactly where it stands, in a form
you can quote onto an issue.

**Never `claude logs`.** It replays the raw terminal — thousands of cursor escapes wrapped around a
spinner, a quarter of a megabyte for one cycle, the real text shredded between them.

**Never `pgrep -af claude`, in any environment.** An agent's whole role prompt sits in its command
line, so that one command floods your context with several thousand words. Count with `pgrep -c`;
match with `pgrep -f <pattern>`, which prints only process ids.

## Stopping an agent

```bash
claude stop <session-id>        # id from `claude agents --json`
```

Killing the process id instead does not work. The daemon that owns background sessions notices the
death and starts the agent again, so a minute later there are two of it — and the second one is
invisible to anybody who watched the kill succeed.

## Deleting an environment

**It takes two calls, and the first one looks like a failure.** Against a running environment,
`ona environment delete` stops it and then exits with `Error: environment has unexpectedly stopped`:
the stop succeeded, the delete did not. Wait a few seconds, run the same command again, and against
the now-stopped environment it prints `environment deleted successfully`. The first error is
progress, not a problem to report.
