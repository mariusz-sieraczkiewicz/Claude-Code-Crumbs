# Transcript sources

Where each agent keeps its sessions and which records carry the signals the timeline needs. Formats
change between versions: treat the field names below as hints, confirm them on a sample of the actual
file, and follow what the file shows. All timestamps in these stores are UTC.

## Claude Code

**Where:** `${CLAUDE_CONFIG_DIR:-~/.claude}/projects/<dir>/<session-uuid>.jsonl`, where `<dir>` is the
session's working directory with every `/` and `.` replaced by `-`. Each git worktree has its own `<dir>`.
Subagents: `<session-uuid>/subagents/agent-<id>.jsonl`, with `agent-<id>.meta.json` holding `agentType`,
`description` and `toolUseId`, the id of the parent's spawning call. `~/.claude/history.jsonl` indexes typed
prompts by project and session.

**Records:** one JSON object per line with `type`, `timestamp`, `uuid`, `sessionId`, `cwd`, `gitBranch`.

| Signal | Where it shows |
|---|---|
| Tool call | `assistant` record, `message.content[]` item `tool_use` with `id`, `name`, `input` |
| Tool result and duration | `user` record, content item `tool_result` with `tool_use_id`, `is_error`; duration = result time − call time |
| Human prompt | `user` record with string content or `origin.kind: human`; exclude the look-alikes below |
| Slash command | human prompt starting `<command-name>` |
| Skill used | see [Skills](#skills) |
| Subagent | `tool_use` named `Agent` or `Task` (`input.subagent_type`, `input.description`); its transcript under `subagents/` |
| Message to another session | `tool_use` named `SendMessage`; incoming ones arrive as a prompt wrapped in `<cross-session-message from="…">` |
| Background job | `Bash` call with `input.run_in_background`; completion as a `<task-notification>` prompt naming `<tool-use-id>`, or an `attachment` of type `task_status` |
| Context compaction | `system` record, `subtype: compact_boundary`, `compactMetadata` with `trigger` (auto/manual), `preTokens`, `durationMs` |
| Interrupt | text `[Request interrupted by user`; the prompt "The app was quit while you were working" after a restart |
| Refusal | `tool_result` with `is_error`: "The user doesn't want to proceed" (declined), sandbox or permission messages |
| User typed while the agent worked | `attachment` of type `queued_command` |
| Long silence from the agent | `attachment` of type `silent_turn_reminder` |

**Look-alikes of a human prompt:** `<task-notification>` (a background job finished), "This session is
being continued from a previous conversation" (compaction summary), "The app was quit while you were
working", `<system-reminder>` and `isMeta` records.

**Duplicates:** a forked session copies the parent's records, and a session that moved to another worktree
can appear under two project directories. Deduplicate by `uuid` across all files and attribute a record to
the session that first wrote it.

`/clear` starts a new session file; a resumed run therefore spans several sessions.

## Codex

**Where:** `${CODEX_HOME:-~/.codex}/sessions/YYYY/MM/DD/rollout-<local-time>-<thread-uuid>.jsonl`.
`session_index.jsonl` maps thread UUIDs to names.

**Records:** `{timestamp, type, payload}`. The first record is `session_meta` with `cwd`, `originator` and
`source`; for a subagent, `source.subagent.thread_spawn` holds `parent_thread_id`, `agent_path` and
`agent_nickname`.

| Signal | Where it shows |
|---|---|
| Tool call and result | `response_item` payload `function_call` or `custom_tool_call`, answered by `…_output` with the same `call_id`; command output starts with `Wall time N seconds` |
| Human prompt | `event_msg` payload `user_message`, or `response_item` `message` with `role: user` minus environment and instruction blocks |
| Turn boundaries | `event_msg` `task_started` / `task_complete`; `turn_aborted` with `reason` (for example `interrupted`) |
| Subagents and peers | calls to `spawn_agent`, `send_message`, `followup_task`, `wait_agent`, `list_agents`; message bodies may be encrypted, so use `task_name` or `target` and read the child's own rollout |
| Context compaction | record type `compacted` |
| Token use | `event_msg` `token_count` |

## GitHub Copilot

**Copilot CLI:** `~/.copilot/session-state/<session-uuid>/events.jsonl`.
**Copilot Chat in VS Code:** `<VS Code user dir>/workspaceStorage/<hash>/chatSessions/*.json` or `*.jsonl`;
the sibling `workspace.json` names the folder. The user dir is
`~/Library/Application Support/Code/User` on macOS and `~/.config/Code/User` on Linux.

Structures differ by version. Sample first, then map requests, responses, tool invocations and their
timestamps to the same compact events.

## Other agents

For any other agent (for example Gemini CLI, Cursor, Aider, OpenCode or an agent built on an SDK), find
where it stores sessions: its documentation, its folder under the home directory, or the application
support folder. Sample a file, then map it to the same compact events. When an agent keeps no local
history, say so in `notes` and build its lane from what other sessions and records show about it.

## Skills

A skill here is any reusable instruction set the agent ran: a skill, a custom slash command or a prompt
file. Where a run of one starts, in each runtime:

- **Claude Code:** a `tool_use` named `Skill` (`input.skill`, `input.args`); a user's slash command
  `<command-name>/<plugin>:<skill>`; an `attachment` of type `invoked_skills`; a subagent's `description`
  such as "Spec review".
- **Codex:** the skill's `SKILL.md` being read by an `exec` call, or `$<skill>` in the user's message.
- **Copilot:** the skill selected in the picker, `/<plugin>:<skill>`, or a prompt file attached to the
  request; confirm on the sample.
- **Any runtime:** the agent reading a skill's `SKILL.md` or a command file right before acting on it.
- **Workflow skills** often announce a phase or skill change in their messages, as a status block or a
  line such as `Phase: … | Skill: …`; use it when present.

Where it ends: the next skill at the same level in that lane, the agent reporting the skill's result, or
the end of that turn.

Where its definition is, to read it and to link it from `skill_catalog`:

- **In the transcript:** Claude Code prints `Base directory for this skill: <path>` when it loads a skill,
  and an `invoked_skills` attachment holds its path and content. Prefer this: it is the version that ran.
- **Claude Code:** `~/.claude/skills/<name>/`, the project's `.claude/skills/<name>/`, installed plugins
  under `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/skills/<name>/`, and custom commands in a
  `commands/<name>.md` file next to them.
- **Codex:** `~/.codex/skills/<name>/` and installed plugins under
  `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/skills/<name>/`.
- **Copilot:** the repository's `.github/` folder (skills, prompt files) and the user's `~/.copilot/`
  folder; confirm on the machine.

The definition may have changed since the run; when the path carries a version, use that version.

## Git and trackers

Use these when the work lives in a git repository or is tracked in GitHub. For another tracker (GitLab,
Jira and so on), use whatever tool the session has for it; without one, rely on the transcripts.

- `git log --format='%H %aI %cI %s' <base>..<head>`: author and committer time; an amend or rebase moves
  the committer time.
- `gh issue view <n> --json createdAt,closedAt,…` and
  `gh api repos/<owner>/<repo>/issues/<n>/timeline`: creation, assignment, linked PR, closing.
- `gh pr view <n> --json commits,reviews,statusCheckRollup,createdAt,mergedAt`: PR opened, draft to ready,
  reviews, check results.
- `gh run list --branch <branch> --json databaseId,createdAt,updatedAt,conclusion,name`: CI duration and
  failures, to fill `remote` spans when no agent was watching them.

## Pitfalls

- Clocks on different machines, such as remote workers, can disagree by seconds or minutes; align peer
  sessions on the message exchanges they share.
- A background job's end is often not recorded. Estimate it from the job's output file time or the agent's
  next read of that output, and name the estimate in `notes`.
- A session that waits for a question overnight is waiting, not working; a quit app is an interrupt, not
  the end of the run.
