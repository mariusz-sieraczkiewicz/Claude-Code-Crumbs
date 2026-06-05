---
name: daily-publishing
description: Turn your daily activity (Slack, Google Chat, Claude Code sessions, meetings, recordings) into publishable subjects, then draft blog/X/LinkedIn/YouTube content.
argument-hint: "[YYYY-MM-DD] [--base <dir>] [--source <name,...>]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion
---

# Daily Publishing

Mine a day of work activity for things worth publishing, let the user pick, then draft content for each chosen subject. Two halves are kept in separate, independently optimizable reference files:

- **Gathering** → `references/sources.md` (one adapter per source)
- **Creating** → `references/create.md` (one recipe per output format)
- **Setup** → `references/integration.md` (how to connect each service)

Read a reference file only when you reach the phase that needs it. Don't inline its content here.

## Configuration

Resolve the working base directory in this order:
1. `--base <dir>` argument
2. `base:` in `{base-candidate}/config.yaml` — check `~/daily-publishing/config.yaml`
3. Default: `~/daily-publishing`

Default date is today (`currentDate` / `date +%F`); override with the first positional arg. Enabled sources default to all; restrict with `--source slack,cc-sessions`.

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

Read `references/sources.md`. For each enabled source, run its adapter to collect the target day's material into `{base}/raw/{date}/<source>.md`. Each file: timestamped, deduplicated, with a provenance line (link, channel, file path, or session id) per item so subjects can cite where they came from.

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

Read `references/create.md`. For each chosen subject, generate every enabled output format from `subject.md` into the subject directory. Default outputs: `blog.md`, `x-post.md`, `linkedin.md`, `youtube-scenario.md`, `youtube-presentation.md`. Keep each format in its own file so it can be edited or regenerated alone.

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
