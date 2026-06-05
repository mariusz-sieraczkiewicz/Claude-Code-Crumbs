# Configuration notes — decisions to make later

Personal scratchpad (kept outside the `daily-publishing` skill). Use it to decide which extra skills/integrations to adopt, then fold the choice into the skill's `config.yaml` / `integration.md`. Nothing here is loaded by the skill.

## Open decisions

- [ ] **Video/presentation tool** for `youtube-presentation` → see options below.
- [ ] **Slack access** (company workspace): official MCP (admin approval) vs. own app + `xoxp` user token vs. browser `xoxc`/`xoxd` tokens → see options below.
- [ ] **Google Chat access**: Chat API (OAuth) vs. Takeout export.
- [ ] **Meeting recording + transcription** (company calls): local-first notetaker vs DIY system-audio + Whisper → see options below.
- [ ] **Scheduling** the 9 pm run: cron/launchd vs `/loop` skill vs `send_later`.

---

## Video / presentation tools (for the YouTube step)

Goal: turn the deck (`youtube-presentation.md`) into a dynamic presentation/video where **I add my own voiceover**. Both are community projects — review code/license before installing.

### Option A — claude-code-video-toolkit (Remotion)  ← best for "video base + my voiceover"

- **What:** AI-native video workspace for Claude Code built on **Remotion** (video = React code; scenes animate by frame, render to MP4 via headless browser + ffmpeg). Ships a project system (plan→script→scenes→render), brand profiles, ~11 components, stylized transitions, Remotion Studio preview.
- **My voiceover:** first-class — I record my own audio, it **times the visuals to my track** (AI TTS optional, not required).
- **Output:** branded MP4.
- **Install:** `git clone https://github.com/digitalsamba/claude-code-video-toolkit` → `pip install -r tools/requirements.txt` → `/setup`, `/video`.
- **Workflow:** scenario+deck → `/video` builds Remotion scenes per point → I record narration → it syncs timing → preview/refine in Studio → render MP4.
- **Trade-off:** most production control + polish, but more setup (clone, pip, learn the project flow).

### Option B — frontend-slides (animated HTML decks)  ← best for "gorgeous deck, I screen-record"

- **What:** Claude Code plugin skill generating a **single standalone animated HTML file** (inline CSS/JS, 16:9, 34+ design systems, PowerPoint import). Advance slides with the keyboard.
- **My voiceover:** none built in — I **screen-record** the browser while narrating live.
- **Output:** HTML file, PDF export, or live Vercel URL.
- **Install:** `/plugin marketplace add https://github.com/zarazhangrui/frontend-slides` → `/plugin install frontend-slides@frontend-slides` → `/frontend-slides:frontend-slides`.
- **Workflow:** deck → it generates animated HTML, pick a style preview → open full-screen → screen-record (OBS/QuickTime/Loom) while I talk through it.
- **Trade-off:** fast and beautiful, but voiceover is a live one-take and final-cut control is limited.

### Net difference

A *ingests* my recorded voice and builds the video around it (control, more setup). B gives a deck I *perform over* with a screen recorder (speed, less control).

Sources:
- https://github.com/digitalsamba/claude-code-video-toolkit
- https://github.com/zarazhangrui/frontend-slides
- https://github.com/jezweb/claude-skills/blob/main/plugins/frontend/skills/walkthrough-video/SKILL.md
- https://pexo.ai/blog/best-video-generation-skills-for-claude-code-agents-2026-3772

### When decided

Set `video_tool: video-toolkit` (or `frontend-slides`) in `{base}/config.yaml`; the `youtube-presentation` format will hand the deck + scenario to it.

---

## Slack access (company workspace → read my recent messages)

Goal: let Claude Code read the day's messages I sent (+ threads I replied in) and save them to `raw/{date}/slack.md`. **Read-only — the skill never posts.** On a company workspace the deciding factor is **app approval**: most corporate workspaces require a workspace admin to approve any app/integration.

### Option 1 — official Slack MCP server  ← cleanest, needs admin approval

- OAuth-based first-party server (endpoint `https://mcp.slack.com/mcp`), auto-configured.
- **Install:** `claude plugin install slack` (or `/plugin install slack` in a session) → complete OAuth.
- **Approval:** requires the MCP integration to be **approved by the workspace admin**. Easy, specific ask.
- Exposes channel history, threads, search.

### Option 2 — own Slack app + user token (`xoxp`)  ← scoped, usually still needs approval

1. [api.slack.com/apps](https://api.slack.com/apps) → create app.
2. OAuth & Permissions → **User Token Scopes**: `channels:history channels:read groups:history groups:read im:history im:read mpim:history mpim:read users:read search:read`.
3. Install to workspace → copy **User OAuth Token** (`xoxp-…`).
- Token inherits **my** permissions — sees only what I can see. Installing to a company workspace typically still needs admin sign-off, but it's a clean "read-only, my own messages" request.

### Option 3 — browser session tokens (`xoxc`/`xoxd`) via community server  ← no approval, use with caution

- [korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server) — **no admin approval**; reuses my logged-in browser session, inherits my permissions, has read-only mode (`SLACK_MCP_READ_ONLY=true`). Also accepts an `xoxp` token (`SLACK_MCP_XOXP_TOKEN`) instead of browser tokens.
- ⚠️ **Caveat:** extracting `xoxc`/`xoxd` bypasses the employer's app-approval controls and may violate IT/security policy or Slack ToS. Only use browser-token mode if the company permits it — otherwise feed this server an approved `xoxp` token, or use Option 1.

### Recommendation

Ask the admin for **Option 1**, or get **Option 2**'s scoped read-only app approved. Fall back to **Option 3** browser tokens only if IT explicitly allows it.

### When decided

- MCP route (Option 1/3): `sources.slack.access: mcp` in `config.yaml` — adapter reads via `mcp__slack__*` tools.
- Token route (Option 2): `sources.slack.access: api`, token in `SLACK_TOKEN` env var.

Sources:
- https://docs.slack.dev/ai/slack-mcp-server/connect-to-claude/
- https://github.com/slackapi/slack-mcp-plugin
- https://github.com/korotovsky/slack-mcp-server/blob/master/docs/01-authentication-setup.md

---

## Meeting recording + transcription (company calls → local-first)

Goal: record video calls externally (not Google Meet's built-in recording) and get a **transcript file** the `meetings` source drops into `transcript_dir`. For **company** calls, prefer **local-first** — no bot joins the call, audio never leaves my machine, which fits the skill's name-redaction and keeps IT/policy happy. (Always still inform participants they're being recorded.)

### Local-first notetakers  ← recommended for company/confidential calls

- **Hyprnote (now "Char")** — local-first, **open-source**, markdown notes (Obsidian-style). Best fit: markdown transcripts route straight into `transcript_dir`.
- **Meetily** — open-source, **100% local**, live Whisper/Parakeet transcription + speaker diarization + local LLM (Ollama) summaries.
- **BB Recorder** — free, fully local, no account; combines Apple Intelligence + Whisper + Llama.
- Why local: captures system + mic audio on-device, no bot in the call, no vendor cloud → no cross-border/GDPR transfer concern.

### DIY — system audio + Whisper

- Record the call audio (OBS / OS audio capture), then transcribe with **whisper.cpp** or **faster-whisper** (large-v3 ≈ 95–97% on English).
- This is the skill's existing `transcribe: true` path — point `sources.meetings.dir`/`transcript_dir` at the audio/transcripts; it caches `.txt` next to each file.

### Cloud bot notetakers (only if IT allows)

- Fireflies (API) / Otter / tl;dv / Fathom — a bot joins the call, cloud transcript + export/API. Convenient auto-pull, but visible bot + vendor cloud → **check company policy first**. Not preferred for confidential calls.

### When decided

- Local notetaker / DIY: set `sources.meetings.transcript_dir` (and `transcribe: true` if only audio). Route the tool's transcript output there.
- Cloud-with-API: the adapter can pull the day's transcripts via API instead of a folder.

Sources:
- https://meetily.ai/blog/best-self-hosted-meeting-transcription-tools-2026
- https://github.com/Zackriya-Solutions/meetily
- https://hyprnote.com/vs/granola
- https://meetingnotes.com/blog/bot-free-ai-note-takers-alternatives
