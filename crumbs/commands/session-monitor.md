---
description: Launch the session monitor web UI to watch Claude Code sessions in real-time
argument-hint: "[project-path]"
---

# /session-monitor

Starts a web UI that monitors Claude Code session transcripts in real-time, showing user intents and agent progress as a live timeline.

## What it does

- Watches `.claude/projects/{encoded-path}/*.jsonl` session files
- Polls for new transcript entries every 2 seconds
- Uses Claude SDK to summarize user intents and agent progress into short status lines
- Serves a dashboard at `http://localhost:7891`

## Steps

1. Check if `bun` is installed (`command -v bun`). If not, tell the user to install it.

2. Install dependencies if needed:
   ```bash
   cd ${CLAUDE_PLUGIN_ROOT}/apps/session-monitor && bun install
   ```

3. Determine the project path:
   - If `$ARGUMENTS` is provided, use it as the project path
   - Otherwise use the current working directory

4. Launch the monitor in the background:
   ```bash
   SESSION_MONITOR_PROJECT=<project-path> bun run ${CLAUDE_PLUGIN_ROOT}/apps/session-monitor/viewer.ts &
   ```

5. Tell the user: "Session Monitor running at http://localhost:7891 — select a session to start watching."
