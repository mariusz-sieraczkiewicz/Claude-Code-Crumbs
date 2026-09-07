# ONA environments

ONA environments are reusable slots named `Developer 1` through `Developer 7`. Reuse `Developer 1` and `Developer 2` first. Create the next numbered environment only when explicitly assigned parallel work needs more capacity. Never exceed `maxEnvironments` or seven. Never delete an environment without a specific human instruction.

## Send commands safely

Send any command with spaces, quoting, variables, substitutions, or multiple steps as a script on standard input:

```bash
ona environment ssh "<environment>" -- bash -s <<'EOF'
set -e
export PATH="$HOME/.local/bin:$PATH"
cd /workspaces/<repository>
...
EOF
```

Do not use `ona environment exec` or `bash -lc` for such commands. Argument splitting can corrupt the command or expose environment variables.

## Inspect a Developer

Developers run in Claude Code. Read their structured session state:

```bash
ona environment ssh "<environment>" -- bash -s <<'EOF'
export PATH="$HOME/.local/bin:$PATH"
claude agents --json
EOF
```

Read the whole response. Identify the Developer by both `name` and `status`. `busy` means working; `idle` means the turn has ended. A process or recent comment is not a heartbeat.

For details, read the Developer's JSONL transcript:

```text
~/.claude/projects/-workspaces-<repository>/<agent-id>-*.jsonl
```

Do not use `claude logs` or `pgrep -af claude`. Stop a session with `claude stop <session-id>` using the ID from `claude agents --json`. Do not kill its process; Claude Code may restart it.

## Reuse, rebuild, or create

Before reuse, confirm that no active agent owns the environment and that no uncommitted work would be lost. Preserve uncertain work and report it.

Treat an idle slot as safe to rebuild only when all of these are true:

- its assigned Issue and pull request are merged, closed, cancelled, or explicitly moved elsewhere;
- `claude agents --json` shows no working Developer;
- every checkout and worktree has been inspected, with no commit that exists only locally and no unique uncommitted change;
- any apparently dirty checkout is proven equivalent to a durable remote commit. A familiar branch name, an idle session, or old activity is not proof.

When the human explicitly asks to clean unused slots and these checks pass, delete the environment by its exact ID and recreate it from `projectId` with the same `Developer <N>` name. Wait for deletion to finish before creating the replacement. Before reuse, verify that the replacement is running, its default branch is clean and current, and the current KISS plugin is installed and enabled. If any check is inconclusive, preserve the environment and report what remains uncertain.

Use the environment ID for rename operations. While an Issue is assigned, rename its slot to:

```text
Developer <N> (#<issue> <three-word title>)
```

The title is a readable three-word summary of the Issue. Rename before starting the Developer:

```bash
ona environment update <environment-id> --name "Developer <N> (#<issue> <three-word title>)"
```

Keep this name while the task is active or blocked. When the task is merged, cancelled, or otherwise released, restore the slot:

```bash
ona environment update <environment-id> --name "Developer <N>"
```

If the installed ONA CLI has no `environment update` command, report it. Do not create a replacement environment.

Create an additional environment from the configured ONA project, never from a repository URL:

```bash
ona environment create <projectId> --name "Developer <N>" --inactivity-timeout 3h
```

The project supplies application secrets. Start a background Developer as a named Claude Code session, attach ONA keep-alive while it works, and invoke `/kiss --role developer --continue` with the assigned Issue.
