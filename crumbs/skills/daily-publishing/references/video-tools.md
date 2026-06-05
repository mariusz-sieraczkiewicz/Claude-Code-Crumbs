# Video / presentation tools (configuration)

Candidate external tools for turning a subject's `youtube-presentation.md` into an actual dynamic presentation or video — where **you record your own voiceover**. Not wired in yet: pick one later, then set `video_tool:` in `{base}/config.yaml` and the `youtube-presentation` format hands off to it. Until then the format stays a markdown deck spec.

Both are community projects (not official Anthropic skills) — review code/license before installing.

## Option A — claude-code-video-toolkit (Remotion) — best for "video base + my voiceover"

- **What:** AI-native video workspace for Claude Code built on Remotion (React video framework). Dynamic animated scenes, transitions, reusable components, ffmpeg assembly, Remotion Studio preview.
- **Voiceover:** first-class **human narration** — record your own audio, Claude Code syncs visuals to it (AI TTS optional).
- **Output:** rendered MP4.
- **Install:** `git clone https://github.com/digitalsamba/claude-code-video-toolkit` → `pip install -r tools/requirements.txt` → `/setup`, `/video`.
- **Hand-off:** pass `youtube-presentation.md` + `youtube-scenario.md` as the script/scene plan; record voiceover; let it sync + render.

## Option B — frontend-slides (HTML decks) — best for "beautiful animated deck, I screen-record"

- **What:** Claude Code skill generating standalone animated HTML presentations (inline CSS/JS, 16:9, 34+ design systems, PowerPoint import).
- **Voiceover:** none built in — you **screen-record** the deck while narrating live.
- **Output:** single HTML file, PDF export, or live Vercel URL.
- **Install:** `/plugin marketplace add https://github.com/zarazhangrui/frontend-slides` → `/plugin install frontend-slides@frontend-slides` → `/frontend-slides:frontend-slides`.
- **Hand-off:** pass `youtube-presentation.md` as the deck content; present + screen-record with your voice.

## To enable later

1. Install the chosen tool.
2. Add to `config.yaml`: `video_tool: video-toolkit` (or `frontend-slides`).
3. In `formats/youtube-presentation.md`, the render hand-off invokes the configured tool with the deck + scenario.

Sources: https://github.com/digitalsamba/claude-code-video-toolkit · https://github.com/zarazhangrui/frontend-slides
