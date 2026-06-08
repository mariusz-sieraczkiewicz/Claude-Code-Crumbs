# Integration

How to connect each source and run the skill on a schedule. The collection logic is in `sources/<source>.md`; this file is the *setup* (credentials, paths, install steps). Configure once, then the adapters just work.

## config.yaml

Create `{base}/config.yaml` (default base `~/daily-publishing`):

```yaml
base: ~/daily-publishing
identity:
  name: "Your Name"
  handles: { x: "@you", linkedin: "in/you" }
  links: { blog: "https://...", youtube: "https://..." }
  tone: "practical, first-person, no hype"
  audience: "developers / engineering leaders"
outputs: [blog, x-post, linkedin, youtube-scenario, youtube-presentation]
video_tool: ""         # "" (markdown deck only) | video-toolkit | frontend-slides
sources:
  slack:
    enabled: true
    access: mcp          # mcp | export | api
    export_dir: ""       # when access: export
    channels: []         # empty = all the user participates in
  gchat:
    enabled: true
    access: api          # api | export | cli
    credentials: ""      # path to OAuth creds (api)
    export_dir: ""       # Takeout dir (export)
  cc-sessions:
    enabled: true
    work_paths: []       # project roots treated as work
    private_paths: []    # project roots treated as private
  meetings:
    enabled: true
    transcript_dir: "~/recordings/meetings"
    transcribe: false
  recorder:
    enabled: true
    dir: "~/recordings/allday"
    transcribe: true
```

Keep secrets out of this file — reference paths/env vars, not raw tokens.

## Slack

Pick one:
- **MCP (recommended):** add a Slack MCP server to your Claude Code config; set `access: mcp`. The adapter then reads via `mcp__slack__*` tools.
- **Export:** Workspace export → unzip → point `export_dir` at it; set `access: export`. Good for personal/offline use; refresh exports periodically.
- **Web API:** create a Slack app with `channels:history`, `groups:history`, `im:history`, `users:read`; put the token in `SLACK_TOKEN` (env); set `access: api`.

## Google Chat

- **API:** enable the Google Chat API in a Google Cloud project, create OAuth client creds, point `credentials` at the JSON, complete the consent flow once. Scope: `chat.messages.readonly`.
- **CLI:** if a Google Workspace CLI (e.g. `gws`) is already authenticated, set `access: cli` — no credentials path needed. Its OAuth grant must include `chat.spaces.readonly` + `chat.messages.readonly`; if a scope upgrade looks applied but still 403s, clear the CLI's token cache so it mints a token from the new grant.
- **Export:** Google Takeout → Google Chat → download → point `export_dir` at the unzipped folder.

## Claude Code sessions (work / private)

No setup beyond classification. List which project roots are work vs private under `work_paths` / `private_paths`. Session files are read locally from `~/.claude/projects/`. Work items are abstracted before publishing — confirm the redaction rules in `sources/README.md` match your employer's policy.

## Meetings & all-day recorder

- Point `transcript_dir` / `dir` at where your recorder/meeting tool drops files.
- If you only have audio, enable `transcribe: true` and install a transcriber:
  - `whisper` (OpenAI) or `whisper.cpp` locally — `whisper <file> --output_format txt`.
  - The adapter calls it via Bash and caches the `.txt` next to the audio so it isn't re-run.
- Common meeting tools (Zoom/Meet/Granola/Otter/Fireflies) can auto-export transcripts to a folder — route them to `transcript_dir`.

## Scheduling (the "9 pm" run)

The skill doesn't self-trigger. Pick one:
- **cron / launchd / Task Scheduler** — run a headless Claude Code invocation nightly, e.g.
  `0 21 * * * claude -p "Use the daily-publishing skill for today" >> ~/daily-publishing/cron.log 2>&1`
- **`/loop` skill** — `/loop 24h Use the daily-publishing skill for today` keeps a recurring run inside a session.
- **`send_later`** (claude-code-remote MCP, when available) — schedule a self check-in that re-invokes the skill.

Whichever you choose, the run is still interactive at Phase 4 (subject selection) and Phase 5 (main message + outline). For a fully unattended run, tell the skill to auto-select all `new` subjects (or the top N) and skip the Phase 5 interview, drafting from the mined material directly.

## Verifying setup

Dry-run a single day: `Use daily-publishing for <recent-date>`. Phase 1's report shows which sources produced material vs. were `skipped (not configured)` — fix the skipped ones here until each enabled source reports items.
