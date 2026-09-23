# analyze-run

A plugin with one skill, `analyze-run`. It shows how an agent run actually went: which agent did what,
when and in which skill, what slowed it down, and whether anything is worth changing.

A run is any piece of agent work you want to look back on: a skill-driven workflow such as a delivery flow
with analyst, developer and reviewer sessions, or a single long session.

## What you get

One self-contained HTML page and a short Markdown summary:

- **A lane per agent:** the main session, its subagents, background jobs, peer sessions and you. Above
  each lane, the skills it was running, nested (for example `implement` → `tdd`). A band across the top
  shows the workflow's phases.
- **Pivot events:** things that changed the course or the cost of the run, such as a lost VPN or login,
  a long test or CI run, review loops, rework, waiting for an answer, a slow handoff between sessions, or
  context compaction. Each has evidence and an estimated cost.
- **Zoom and details:** buttons, dragging along the time axis, or Ctrl/⌘ + scroll to zoom in; an overview
  map to move around. Click any bar to see the actions that happened in it, with times, and the skill it
  belonged to, with a link to that skill's `SKILL.md`.
- **An assessment:** a verdict and recommendations only where the evidence shows avoidable time. A run
  that went well gets observations, not invented fixes. Waiting for you is never counted as waste, and
  removing required reviews or checks is never proposed.

The analysis is read-only: it never edits code, skills or settings, and never posts anywhere.

## Install

Claude Code:

```text
/plugin marketplace add mariusz-sieraczkiewicz/Claude-Code-Crumbs
/plugin install analyze-run@Claude-Code-Crumbs
```

The skill also works in Codex and GitHub Copilot CLI through the same plugin directory.

## Use

The argument says which run to analyse. Give whichever you have:

- the GitHub Issue or pull request the agents worked on — the skill finds every session that touched it;
- a branch name;
- a session id or the path of one transcript file;
- a time window, with `--since`.

```text
/analyze-run:analyze-run https://github.com/owner/repo/issues/123
/analyze-run:analyze-run feat/cancel-order
/analyze-run:analyze-run 139949ae-50bc-4d84-8a31-3d3a9f1f962e
/analyze-run:analyze-run --since "2026-09-22 20:00"
```

With no argument, the skill lists recent candidate runs for the current repository and asks which one
to analyse.

It reads session transcripts from their usual places: `~/.claude/projects/` (Claude Code),
`~/.codex/sessions/` (Codex), `~/.copilot/session-state/` and VS Code's `chatSessions` (GitHub Copilot).
It adds `git` and `gh` records when they are available. Transcripts are large, so the agent streams them
with a throwaway script instead of reading them whole, and masks anything that looks like a secret.

Outputs go outside your repositories, to
`${XDG_STATE_HOME:-~/.local/state}/analyze-run/<repository>/<subject>-<date>/`: `timeline.json`,
`timeline.html`, `summary.md` and the extraction scripts.

## Requirements

Python 3.9 or later for the renderer. `git` and an authenticated `gh` are optional and add milestones
and CI times.

## Layout

```text
skills/analyze-run/
  SKILL.md                        the seven steps the agent follows
  references/transcript-sources.md  where each agent keeps its sessions and which records matter
  references/timeline-schema.md     the timeline JSON the renderer reads
  references/pivot-events.md        pivot event families, thresholds, severity, impact
  references/recommendations.md     when to recommend, and when not to
  scripts/render_timeline.py        timeline JSON → HTML page and Markdown summary
tests/test_render_timeline.py       renderer tests
```

## Test

From this directory:

```bash
python3 -m unittest discover -s tests -v
```

One test checks the page's JavaScript with `node --check`; it is skipped when Node.js is not installed.
