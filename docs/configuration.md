# Configuration notes — decisions to make later

Personal scratchpad (kept outside the `daily-publishing` skill). Use it to decide which extra skills/integrations to adopt, then fold the choice into the skill's `config.yaml` / `integration.md`. Nothing here is loaded by the skill.

## Open decisions

- [ ] **Video/presentation tool** for `youtube-presentation` → see options below.
- [ ] **Slack access**: MCP server vs. workspace export vs. Web API token.
- [ ] **Google Chat access**: Chat API (OAuth) vs. Takeout export.
- [ ] **Transcription** for meetings + all-day recorder: `whisper` vs `whisper.cpp` vs the recorder tool's own export.
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
