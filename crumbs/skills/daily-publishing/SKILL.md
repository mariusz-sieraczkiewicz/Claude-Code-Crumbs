---
name: daily-publishing
description: Turn your daily activity (Slack, Google Chat, Claude Code sessions, meetings, recordings) into publishable subjects, then draft blog/X/LinkedIn/YouTube content.
argument-hint: "[YYYY-MM-DD] [--base <dir>] [--source <name,...>]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion
---

# Daily Publishing

Mine a day of work activity for things worth publishing, let the user pick, then draft content for each chosen subject. The two halves are split into **one file per source** and **one file per output format**, so each can be tuned and developed on its own:

- **Gathering** → `references/sources/<source>.md` (one file per source) + `references/sources/README.md` (shared contract)
- **Creating** → `references/formats/<format>.md` (one file per format) + `references/formats/README.md` (shared voice)
- **Setup** → `references/integration.md` (how to connect each service + scheduling)

Read a reference file only when you reach the phase that needs it. Don't inline its content here.

## Configuration

Resolve the working base directory in this order:
1. `--base <dir>` argument
2. `base:` in `{base-candidate}/config.yaml` — check `~/daily-publishing/config.yaml`
3. Default: `~/daily-publishing`

Default date is today (`currentDate` / `date +%F`); override with the first positional arg. Enabled sources default to all; restrict with `--source slack,cc-sessions`. All config knobs are documented in `references/integration.md`.

Layout under `{base}`:

```
config.yaml                       # optional; sources, base, identity, defaults
index.yaml                        # registry of every published subject (dedup source of truth)
raw/{date}/<source>.md            # gathered material per source
subjects/{date}-{slug}/           # one directory per chosen subject
  subject.md  blog.md  x-post.md  linkedin.md
  youtube-scenario.md  youtube-presentation.md  sources.md
```

Create missing directories. If `index.yaml` is absent, start one (`subjects: []`).

## Scheduling

This skill does not run itself at 9 pm — invocation is the harness's job. To run it on a schedule, see "Scheduling" in `references/integration.md` (cron, the `/loop` skill, or `send_later`). When invoked, always run the full pipeline below for the target date.

## Phase 1 — Gather

Read `references/sources/README.md` for the shared output contract. Then, for each enabled source, read and run its file `references/sources/<source>.md` to collect the target day's material into `{base}/raw/{date}/<source>.md`. Each file: timestamped, deduplicated, with a provenance line (link, channel, file path, or session id) per item so subjects can cite where they came from.

Skip a source cleanly if it is not configured — note it as "skipped (not configured)", don't fail. If **no** source produced material, stop and tell the user, pointing at `references/integration.md`.

## Phase 2 — Mine subjects

Read all `raw/{date}/*.md`. Extract candidate **subjects** — each one a topic that:
- Can be **presented self-contained in ≤10 minutes** (no missing prerequisites the audience would need).
- Has a real hook: a problem solved, a decision made, a lesson learned, a pattern noticed, a tool or technique used.

For each candidate produce: `slug`, one-line `title`, a 1–2 sentence `pitch`, `est_minutes` (≤10), and `sources` (provenance refs). Drop chatter, secrets, and anything client-confidential — flag borderline items rather than including them.

## Phase 3 — Dedupe against existing subjects

Read `{base}/index.yaml`. Compare candidates against already-published subjects by title and theme. For each candidate mark: `new`, `duplicate` (skip), or `extends` (a fresh angle on a prior subject — keep, and note the parent slug). Present duplicates only as a brief "skipped as already covered" note.

## Phase 4 — Choose

Present the surviving candidates and ask the user to pick with `AskUserQuestion` (`multiSelect: true`). One option per candidate: label = title, description = `pitch` + `~{est_minutes} min` + status (`new`/`extends parent`). Include the provenance compactly. The user may also type custom subjects.

If there are no candidates, say so and stop.

## Phase 5 — Scaffold

For each chosen subject, create `{base}/subjects/{date}-{slug}/`. On slug collision append `-2`, `-3`. Write:
- `subject.md` — the ≤10-minute brief: title, hook, key points (3–5), the "so what", and any code/links. This is the self-contained source of truth every output draws from.
- `sources.md` — provenance refs for this subject.

## Phase 6 — Create

Read `references/formats/README.md` for the shared voice. Then, for each chosen subject, generate every enabled output by applying its format file `references/formats/<format>.md` to `subject.md`, writing into the subject directory. Default outputs: `blog.md`, `x-post.md`, `linkedin.md`, `youtube-scenario.md`, `youtube-presentation.md`. Each format file defines that format's structure, length, and writing style — follow it. Keep each output in its own file so it can be edited or regenerated alone.

## Phase 7 — Index & report

Append each new subject to `{base}/index.yaml`:

```yaml
subjects:
  - slug: ""
    title: ""
    date: ""          # YYYY-MM-DD
    dir: ""           # relative path under base
    status: new       # new | extends
    parent: ""        # set when status is extends
    outputs: [blog, x-post, linkedin, youtube-scenario, youtube-presentation]
```

Report: subjects found / skipped as duplicate / chosen, the directories written, and any sources skipped for lack of configuration.
