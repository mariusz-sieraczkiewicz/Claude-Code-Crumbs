# Sources

One adapter per source. Each writes the target day's material to `{base}/raw/{date}/<source>.md`. Setup for every service lives in `integration.md`; this file is the *collection* logic only, so it can be optimized independently.

Common output contract for every adapter — a markdown file where each item is:

```
- HH:MM | <provenance ref> | <content, one or few lines>
```

`provenance ref` = a link, channel name, file path, or session id specific enough to cite later. Sort ascending by time. Deduplicate near-identical lines. Redact secrets/tokens. Mark client-confidential items with `⚠️confidential` instead of dropping silently — they get filtered in Phase 2.

Read config from `{base}/config.yaml` (`sources:` block) to know which adapters are enabled and where their data lives. Skip any source whose config/path is missing; record it as `skipped (not configured)`.

---

## slack

1. Resolve access (in priority order): Slack MCP server → `sources.slack.export_dir` (a Slack export folder) → `SLACK_TOKEN` for the Web API. See `integration.md`.
2. Collect the day's messages the user **sent**, plus threads they participated in, across configured channels/DMs.
3. Provenance ref: `slack#<channel>` or permalink when available.

→ `raw/{date}/slack.md`

## gchat

1. Resolve access: Google Chat API (`sources.gchat.credentials`) → Google Takeout export under `sources.gchat.export_dir`. See `integration.md`.
2. Collect the user's messages and active spaces/DMs for the day.
3. Provenance ref: `gchat#<space>` or message link.

→ `raw/{date}/gchat.md`

## cc-sessions

Claude Code session history — split into **work** and **private** profiles.

1. Session files live at `~/.claude/projects/{encoded-project-path}/*.jsonl` (path `/`→`-`, leading `-`). Config `sources.cc_sessions.work_paths` / `private_paths` list which project roots map to which profile; unlisted projects default to `private`.
2. For the target day, select `.jsonl` files modified that day. Per file, read compaction summaries first (richest), then scan user↔assistant turns. (JSONL shape: see `learn-from-conversation-analyzer`.)
3. Extract publishable moments: problems solved, decisions, techniques, gotchas, before/after. Tag each item `profile:work` or `profile:private`.
4. **Roche / work confidentiality:** for `profile:work` items, abstract away client names, internal systems, and proprietary detail — keep the transferable lesson, mark residual sensitivity `⚠️confidential`.
5. Provenance ref: `cc:<profile>:<session-id-short>`.

→ `raw/{date}/cc-sessions.md`

## meetings

Recorded meetings with transcripts.

1. Find transcripts for the day under `sources.meetings.transcript_dir` (`.txt`/`.vtt`/`.srt`/`.md`). If only audio exists, transcribe per `integration.md` (whisper) when `sources.meetings.transcribe: true`, else skip with a note.
2. Summarize each meeting into decisions, action items, and any insight worth sharing publicly (strip names/confidential specifics).
3. Provenance ref: `meeting:<file-stem>` (+ timestamp range when present).

→ `raw/{date}/meetings.md`

## recorder

All-day audio recorder (continuous capture).

1. Locate the day's recordings/transcripts under `sources.recorder.dir`. Transcribe per `integration.md` if needed and enabled.
2. These are long and noisy — segment by topic, keep only spans with a clear idea, spoken note, or "I should write about this" moment. Discard ambient/idle audio.
3. Provenance ref: `recorder:<file-stem>@<HH:MM>`.

→ `raw/{date}/recorder.md`

---

## Adding a source

1. Add an adapter section here following the output contract above.
2. Add its config keys + setup steps to `integration.md`.
3. No change to `SKILL.md` is needed — Phase 1 iterates over enabled sources generically.
