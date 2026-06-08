---
name: session-monitor
description: >-
  Launch, install, or stop the Session Monitor web UI — a live dashboard that tails Claude Code
  session transcripts and shows user intents and agent progress as a real-time timeline. Use whenever
  the user wants to watch, monitor, or observe what Claude is doing, see a live timeline of agent
  progress, run the "session monitor" or "session dashboard", or start/stop it for the current project
  — even without naming the tool (e.g. "show me what the agent is doing", "open the monitor for this
  repo", "stop the monitor"). Supports multiple projects at once on different ports.
---

# Session Monitor

A web UI that tails this project's Claude Code session transcripts in real time, using the Claude SDK
to summarize user intents and agent progress into a live timeline at `http://localhost:<port>`.

The engine (code + deps) is installed **once** at user level in the plugin. Each project gets its own
data directory and port, so several projects can be monitored simultaneously without interference.

## Layout

- **Engine** (shared, installed once): `${CLAUDE_PLUGIN_ROOT}/apps/session-monitor/` — `viewer.ts`,
  `index.html`, `package.json`, `node_modules`.
- **Per-project data**: `~/.claude/session-monitor/<encoded-path>/` — logs, watcher state, entries,
  and the running instance's `viewer.pid` / `viewer.port`. `<encoded-path>` is the project's absolute
  path with every `/` replaced by `-` (e.g. `-Users-sieracm2-Projects-kiakia-ai-assisted`), mirroring
  `~/.claude/projects/`.

Compute it from the project root:

```bash
PROJECT_DIR="$(pwd)"
ENCODED="-$(echo "$PROJECT_DIR" | sed 's:/:-:g' | sed 's/^-//')"
DATA_DIR="$HOME/.claude/session-monitor/$ENCODED"
```

## Subcommands

Dispatch on the skill argument. `start` is the default for no/unrecognized argument.

### `install` — user-level, run once (idempotent)

1. Check `bun`: `command -v bun`. If missing, stop and tell the user to install it (https://bun.sh) —
   do not install it for them.
2. `cd ${CLAUDE_PLUGIN_ROOT}/apps/session-monitor && bun install`
3. Confirm the engine is installed and that `start` will launch it for any project.

### `start` — default, current project

1. If `${CLAUDE_PLUGIN_ROOT}/apps/session-monitor/node_modules` is missing, run `install` first.
2. Compute `DATA_DIR` (see **Layout**); `mkdir -p "$DATA_DIR"`.
3. If `$DATA_DIR/viewer.pid` exists and the PID is alive (`kill -0 <pid> 2>/dev/null`), it's already
   running — read `$DATA_DIR/viewer.port`, report `http://localhost:<port>`, and stop. No second copy.
4. Pick a starting port from 7891 upward (a hint — `viewer.ts` re-checks and advances on its own if
   this one gets taken before it binds):
   ```bash
   PORT=7891; while lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; do PORT=$((PORT+1)); done
   ```
5. Ask whether to start now (the user may only want it configured). If yes:
   ```bash
   SESSION_MONITOR_PROJECT="$PROJECT_DIR" \
   SESSION_MONITOR_DATA_DIR="$DATA_DIR" \
   SESSION_MONITOR_PORT="$PORT" \
   nohup bun run ${CLAUDE_PLUGIN_ROOT}/apps/session-monitor/viewer.ts > "$DATA_DIR/viewer.out" 2>&1 &
   echo $! > "$DATA_DIR/viewer.pid"
   ```
   `viewer.ts` writes the port it actually bound to `$DATA_DIR/viewer.port`. Read it back (give it a
   moment to appear) — that, not `$PORT`, is the real port:
   ```bash
   for _ in $(seq 1 10); do [ -s "$DATA_DIR/viewer.port" ] && break; sleep 0.2; done
   PORT="$(cat "$DATA_DIR/viewer.port")"
   ```
6. If launched: "Session Monitor running at http://localhost:<port> — select a session to start
   watching." If declined: report it's configured and how to start later.

### `stop` — current project

1. Compute `DATA_DIR`. No `$DATA_DIR/viewer.pid` → report nothing is running for this project.
2. `kill "$(cat "$DATA_DIR/viewer.pid")"` (`kill -9` only if it refuses).
3. Remove `viewer.pid` and `viewer.port`; confirm stopped. Leave logs/state/entries so a later `start`
   resumes.

## Notes

- Stops/starts only the **current project's** instance; other projects keep running on their ports.
- The viewer reads `SESSION_MONITOR_DATA_DIR` (logs/state) and `SESSION_MONITOR_PORT`, defaulting to
  the in-plugin `logs/` and `7891` — so running `viewer.ts` directly still works.
