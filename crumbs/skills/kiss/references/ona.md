# ONA environments

ONA environments are reusable slots. Each region has up to `maxEnvironments` slots, with a maximum of seven: up to seven in Europe and another seven in the United States. Use Europe by default. When Europe reaches its capacity limit, use the US runner without waiting for human approval. The KiaKia AI Native ONA project already has runners configured for both regions; use those runners rather than creating new ones.

Before allocating a slot, inspect environments in both regions and resolve their runner IDs from the configured project. Count capacity separately for each region. Select the runner through the installed ONA CLI or API, checking its supported options, and verify the new environment's region before starting a Developer. A capacity limit triggers the regional fallback; other failures require diagnosis.

Keep `Developer <N>` names unique across both regions, from `Developer 1` through `Developer 14`. Reuse `Developer 1` and `Developer 2` first when available in the selected region. Create the next unused numbered environment only when explicitly assigned parallel work needs more capacity. Never exceed `maxEnvironments` or seven in either region. If both regions are full, reuse a safe idle slot or wait for capacity while continuing other work. Never delete an environment without a specific human instruction.

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

## Prepare KISS

Before starting a Developer, work from the repository root and ensure the current `crumbs@Claude-Code-Crumbs` version is installed and enabled at `local` scope for that repository. A `user`-scope installation alone is not evidence that the background service can load KISS. Use `--scope local` when installing, updating, or enabling it. `claude plugin list` must show the current version with `Scope: local` and `Status: enabled`.

When a plugin change says that a restart is required, start a fresh background service only after the local-scope check passes. Never restart a working Developer to apply an update.

## Inspect a Developer

Developers run in Claude Code. Read their structured session state:

```bash
ona environment ssh "<environment>" -- bash -s <<'EOF'
export PATH="$HOME/.local/bin:$PATH"
claude agents --json
EOF
```

Read the whole response. Exactly one session with the assigned Developer name must have `status` set to `busy` and `state` set to `working`. `idle` means the turn has ended. A process or recent comment is not a heartbeat.

For details, read the Developer's JSONL transcript:

```text
~/.claude/projects/-workspaces-<repository>/<agent-id>-*.jsonl
```

After launch, also inspect that session's transcript before treating the task as started. It must show KISS expansion with `attributionSkill` set to `crumbs:kiss`. If the transcript reports an unknown command or lacks KISS attribution, stop every just-started matching session by ID, preserve the checkout, and reconcile the card and labels with the last phase proven by the branch and pull request. Keep an assigned task `Blocked` while the plugin remains an external dependency; return an abandoned assignment to `Todo` without `in-flight`. Report the failure and do not retry unchanged.

Do not use `claude logs` or `pgrep -af claude`. Stop a session with `claude stop <session-id>` using the ID from `claude agents --json`. Do not kill its process; Claude Code may restart it.

## Reuse, rebuild, or create

Before reuse, confirm that no active agent owns the environment and that no uncommitted work would be lost. Preserve uncertain work and report it.

Treat an idle slot as safe to rebuild only when all of these are true:

- its assigned Issue and pull request are merged, closed, cancelled, or explicitly moved elsewhere;
- `claude agents --json` shows no working Developer;
- every checkout and worktree has been inspected, with no commit that exists only locally and no unique uncommitted change;
- any apparently dirty checkout is proven equivalent to a durable remote commit. A familiar branch name, an idle session, or old activity is not proof.

When the human explicitly asks to clean unused slots and these checks pass, delete the environment by its exact ID and recreate it from `projectId` with the same `Developer <N>` name. Wait for deletion to finish before creating the replacement. Before reuse, verify that the replacement is running, its default branch is clean and current, and the current KISS plugin passes the local-scope check above. If any check is inconclusive, preserve the environment and report what remains uncertain.

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
