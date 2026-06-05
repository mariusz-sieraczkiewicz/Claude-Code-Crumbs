# Configuration

Every setting lives in one file: `{base}/config.yaml` (default base `~/daily-publishing`). This documents each knob. Service setup (credentials, install) is separate → `integration.md`.

## Slides / video tool

Controls how `youtube-presentation.md` becomes an actual dynamic presentation or video you voice over.

```yaml
video_tool: ""        # "" (leave as markdown deck) | video-toolkit | frontend-slides
```

- **unset** — the presentation stays a markdown deck spec; no rendering.
- **video-toolkit** / **frontend-slides** — the `youtube-presentation` format hands the deck (+ `youtube-scenario.md`) to that tool. Install it first; the two tools and how each handles your voiceover are described separately (not stored here).

## Identity

Drives the voice of every created format.

```yaml
identity:
  name: "Your Name"
  handles: { x: "@you", linkedin: "in/you" }
  links: { blog: "https://...", youtube: "https://..." }
  tone: "practical, first-person, no hype"
  audience: "developers / engineering leaders"
```

## Outputs

Which formats Phase 6 generates (filenames in `formats/`).

```yaml
outputs: [blog, x-post, linkedin, youtube-scenario, youtube-presentation]
```

## Sources

Which sources Phase 1 gathers, and where their data lives. Per-service setup → `integration.md`.

```yaml
sources:
  slack:
    enabled: true
    access: mcp          # mcp | export | api
    export_dir: ""       # when access: export
    channels: []         # empty = all the user participates in
  gchat:
    enabled: true
    access: api          # api | export
    credentials: ""      # OAuth creds path (api)
    export_dir: ""       # Takeout dir (export)
  cc_sessions:
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

## Base

```yaml
base: ~/daily-publishing   # root for raw/, subjects/, index.yaml
```

Keep secrets out of this file — reference paths/env vars, never raw tokens.
