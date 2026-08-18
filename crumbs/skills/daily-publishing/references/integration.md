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
visuals:
  enabled: false           # opt-in; true to generate companion visuals
  provider: gemini         # only 'gemini' implemented; knob reserved for future providers
  model: gemini-3-pro-image  # pin the GA id; do NOT use the deprecated `-preview` variant (shut down 2026-06-25)
  candidates: 3            # candidates generated per visual; best is auto-picked
  aspect_default: "16:9"   # blog hero default; per-format overrides in references/visuals/README.md
sources:
  slack:
    enabled: true
    access: codex        # codex | mcp | export | api
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

Note: under `visuals:`, `model` is currently pinned by the generator (the knob is reserved for the future provider router) and `aspect_default` is only a fallback — the per-format table in `references/visuals/README.md` overrides it; the genuinely-active knobs are `enabled`, `provider`, and `candidates`.

## Slack

Pick one:
- **Codex CLI (recommended):** install the OpenAI Codex CLI and enable its Slack plugin — Slack must be connected as a connector on the ChatGPT account Codex is logged into (connect it via the Codex desktop app or ChatGPT settings; auth rides on that account, no token or OAuth setup here). Set `access: codex`. Verify with `codex plugin list | grep slack` (expect `slack@openai-curated  installed, enabled`) and a live read-only test:
  `codex exec --skip-git-repo-check "Using your Slack tools only, list up to 3 channels you can see. Read-only."`
  The adapter then shells out to `codex exec` per `sources/slack.md`.
- **MCP:** add a Slack MCP server to your Claude Code config; set `access: mcp`. The adapter then reads via `mcp__slack__*` tools.
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

## Visuals

Companion images and diagrams are fully opt-in. With `visuals.enabled: false` (or absent) or no usable key, the run skips the phase and reports `visuals skipped (not configured)` — nothing else changes. To turn it on:

- **API key:** store it at `~/.config/daily-publishing/secrets.env` (chmod 600, *outside* the repo so it is never committed) as `GEMINI_API_KEY=...`. The generator (`scripts/generate-visual.sh`) sources that file, or falls back to the `$GEMINI_API_KEY` env var if it isn't there. Never put a token in `config.yaml` or any tracked file.
- **Billing is required.** The free tier for `gemini-3-pro-image` is `0`, so without billing every call returns HTTP 429 (`RESOURCE_EXHAUSTED`). Enable billing on the Google Cloud project the API key belongs to — a key is bound to one specific project, so billing must be on *that* project. Cost is ≈ $0.13/image at 1K–2K, ≈ $0.24 at 4K.
- **Model:** pin the GA id `gemini-3-pro-image` (the `model:` default). Do **not** use the `-preview` variant — it is deprecated and was shut down 2026-06-25.
- **Provider:** only `gemini` is implemented. The `provider:` knob exists so a second provider can be added later without changing the config schema.

## Scheduling (the "9 pm" run)

The skill doesn't self-trigger. Pick one:
- **cron / launchd / Task Scheduler** — run a headless Claude Code invocation nightly, e.g.
  `0 21 * * * claude -p "Use the daily-publishing skill for today" >> ~/daily-publishing/cron.log 2>&1`
- **`/loop` skill** — `/loop 24h Use the daily-publishing skill for today` keeps a recurring run inside a session.
- **`send_later`** (claude-code-remote MCP, when available) — schedule a self check-in that re-invokes the skill.

Whichever you choose, the run is still interactive at Phase 4 (subject selection) and Phase 5 (main message + outline). For a fully unattended run, tell the skill to auto-select all `new` subjects (or the top N) and skip the Phase 5 interview, drafting from the mined material directly.

## Verifying setup

Dry-run a single day: `Use daily-publishing for <recent-date>`. Phase 1's report shows which sources produced material vs. were `skipped (not configured)` — fix the skipped ones here until each enabled source reports items.
