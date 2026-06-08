---
name: daily-publishing
description: Turn your daily activity (Slack, Google Chat, Claude Code sessions, meetings, recordings) into publishable subjects, then draft blog/X/LinkedIn/YouTube content.
argument-hint: "[YYYY-MM-DD] [--base <dir>] [--source <name,...>]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent
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

Default date is today (`currentDate` / `date +%F`); override with the first positional arg. All config knobs are documented in `references/integration.md`.

### Active source set

Resolve which sources run, in this precedence:

1. **`--source a,b` given** → exactly those (intersected with known sources). Explicit override wins, ignoring `enabled`.
2. **Else, with a `config.yaml`** → every source where `sources.<name>.enabled: true`. `enabled: false` reliably turns a source off.
3. **No `config.yaml`** → all sources (zero-config default).

Then, for each source in the resolved set, if its required config (access/paths) is missing, **skip it** with `skipped (not configured)` — never fail the run.

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

Read `references/sources/README.md` for the shared output contract. Then, for each source in the **active source set** (resolved per Configuration above), read and run its file `references/sources/<source>.md` to collect the target day's material into `{base}/raw/{date}/<source>.md`. Each file: timestamped, deduplicated, with a provenance line (link, channel, file path, or session id) per item so subjects can cite where they came from.

A source whose required config is missing is skipped as `skipped (not configured)`, never a failure. If **no** source produced material, stop and tell the user, pointing at `references/integration.md`.

## Phase 2 — Mine subjects

Read all `raw/{date}/*.md`. Mine in two passes:

1. **Surface pass** — the obvious candidates: problems solved, decisions made, gotchas, tools used.
2. **Deep pass** — spawn 2–3 parallel subagents over the richest raw material (for cc-sessions, point them back at the underlying session logs) tasked with understanding the *system being built*, not just the day's fixes. Hunt for: named principles and mental models invented in the work, decisions that changed the course of the work or its results, non-typical approaches, and small-but-novel gotchas that can be extended into a full piece. Novelty outranks size — a reader should find something here they can't find in generic posts.

When the richest material is a real system the user built (a skill, codebase, doc set), treat the gathered raw as **leads, not facts** — session summaries paraphrase and drift. The canonical definition lives in the source files; record where it lives so the chosen subject can be verified there before any drafting (Phase 6). Never characterize a system from session summaries alone.

Each candidate **subject** is a topic that:
- Can be **presented self-contained in ≤10 minutes** (no missing prerequisites the audience would need).
- Has a real hook: a problem solved, a decision made, a lesson learned, a pattern noticed, a tool or technique used.

For each candidate produce: `slug`, one-line `title`, a 1–2 sentence `pitch`, `est_minutes` (≤10), and `sources` (provenance refs). Drop chatter, secrets, and anything client-confidential — flag borderline items rather than including them.

## Phase 3 — Dedupe against existing subjects

Read `{base}/index.yaml`. Compare candidates against already-published subjects by title and theme. For each candidate mark: `new`, `duplicate` (skip), or `extends` (a fresh angle on a prior subject — keep, and note the parent slug). Present duplicates only as a brief "skipped as already covered" note.

## Phase 4 — Choose

Present **all** surviving candidates as a markdown table in the reply — title, pitch, `~{est_minutes} min`, status (`new`/`extends parent`), compact provenance. Do **not** use `AskUserQuestion` — plain text only; option widgets cap and hide the list. Ask the user to reply with their picks by number or slug; custom subjects are welcome.

If there are no candidates, say so and stop.

## Phase 5 — Define the message

For each chosen subject, **before writing any content**, interview the user — one question at a time — until these are pinned down:
- the **main message**: the one sentence the reader should walk away with,
- the **outline**: 3–6 beats/sections,
- include/exclude: angle, audience, examples to use or avoid,
- **grounding & example**: where the subject's authoritative source lives (repo/skill/docs) so Phase 6 can verify against it; and the concrete worked example the piece will turn on. If an example must be a stand-in (e.g. confidential real domain), agree it up front — and it must faithfully mirror the real system, flagged as a stand-in.

Confirm the agreed main message + outline back to the user, then proceed. Keep every subsequent draft on the agreed audience/angle — if a draft drifts off it, that's a defect. In unattended runs skip the interview, draft from the mined material with your own judgment, and say so in the report.

## Phase 6 — Scaffold

For each chosen subject, create `{base}/subjects/{date}-{slug}/`. On slug collision append `-2`, `-3`. Write:
- `subject.md` — the ≤10-minute brief: title, hook, **main message + outline from Phase 5**, key points (3–5), the "so what", and any code/links. This is the self-contained source of truth every output draws from. Before writing it: **verify every technical/conceptual claim against the authoritative source** (the actual code/skill/docs the work produced), not the mined summaries — read those files. For a technical or system subject the brief must carry a **concrete worked example: an example problem, the actual example artifacts shown with real content (not just file names), and a before/after that shows the idea solving the problem (the result with vs without it).** Flag any stand-in example as such and keep it faithful to the real system.
- `sources.md` — provenance refs for this subject, including the authoritative source files verified against (separate from the session-summary raw).

## Phase 7 — Create

Read `references/formats/README.md` for the shared voice. Then, for each chosen subject, generate every enabled output by applying its format file `references/formats/<format>.md` to `subject.md`, writing into the subject directory. Default outputs: `blog.md`, `x-post.md`, `linkedin.md`, `youtube-scenario.md`, `youtube-presentation.md`. Each format file defines that format's structure, length, and writing style — follow it. Keep each output in its own file so it can be edited or regenerated alone.

## Phase 8 — Index & report

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
