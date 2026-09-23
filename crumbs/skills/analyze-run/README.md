# analyze-run

The `analyze-run` skill of the `crumbs` plugin shows how an agent run actually went: which agent did what,
when and in which skill, what slowed it down, and whether anything is worth changing.

A run is any piece of agent work you want to look back on: one long session or several sessions that
handed work to each other, driven by any set of skills, custom commands or prompt files, or by none. The
task can be coding, writing, research, data work or anything else an agent does.

It works best for tuning a skill: it reads the definition of every skill that ran and shows where the
run departed from it and what that cost.

## What you get

One self-contained HTML page and a short Markdown summary:

- **A lane per agent:** the main session, its subagents, background jobs, peer sessions and you. Above
  each lane, the skills it was running, nested when one skill calls another. A band across the top shows
  the phases named by the workflow skill that drove the run, or the run's own chapters when there is none.
- **Pivot events:** things that changed the course or the cost of the run, such as a lost VPN or login,
  a long tool call, check or remote job, loops and rework, a departure from a skill's instructions, a long
  search for something that could have been given, waiting for an answer, a slow handoff between
  sessions, or context compaction. Each has evidence and an estimated cost.
- **Zoom and details:** buttons, dragging along the time axis, or Ctrl/⌘ + scroll to zoom in; an overview
  map to move around. Click any bar to see the actions that happened in it, with times, and the skill it
  belonged to, with a link to that skill's definition.
- **An assessment:** a verdict and recommendations only where the evidence shows avoidable time. A run
  that went well gets observations, not invented fixes. Waiting for you is never counted as waste, and
  removing required reviews or checks is never proposed.

The analysis is read-only: it never edits code, skills or settings, and never posts anywhere.

## Install

It ships with the `crumbs` plugin. In Claude Code:

```text
/plugin marketplace add mariusz-sieraczkiewicz/Claude-Code-Crumbs
/plugin install crumbs@Claude-Code-Crumbs
```

The skill also works in Codex and GitHub Copilot CLI through the same plugin.

## Use

The argument says which run to analyse. Give whichever you have:

- a session id or the path of one transcript file;
- `--skill <name>`: the last run of that skill, or its runs inside `--since`;
- the Issue or pull request the agents worked on, when the work is tracked — the skill finds every
  session that touched it;
- a branch, or the folder the work happened in;
- a time window, with `--since`.

```text
/crumbs:analyze-run 139949ae-50bc-4d84-8a31-3d3a9f1f962e
/crumbs:analyze-run --skill write-report
/crumbs:analyze-run https://github.com/owner/repo/issues/123
/crumbs:analyze-run ~/reports/q3 --since "2026-09-22 20:00"
```

With no argument, the skill lists recent sessions in the current folder, with their first prompt and the
skills they used, and asks which run to analyse.

It reads session transcripts from their usual places: `~/.claude/projects/` (Claude Code),
`~/.codex/sessions/` (Codex), `~/.copilot/session-state/` and VS Code's `chatSessions` (GitHub Copilot).
For other agents it finds and samples their session store the same way. It adds git and tracker records
when the work has them. Transcripts are large, so the agent streams them
with a throwaway script instead of reading them whole, and masks anything that looks like a secret.

Outputs go outside your repositories, to
`${XDG_STATE_HOME:-~/.local/state}/analyze-run/<repository-or-folder>/<subject>-<date>/`: `timeline.json`,
`timeline.html`, `summary.md` and the extraction scripts.

## Requirements

Python 3.9 or later for the renderer. `git` and an authenticated `gh` are optional; for tracked work
they add milestones and CI times.

## Layout

```text
analyze-run/
  SKILL.md                        the seven steps the agent follows
  references/transcript-sources.md  where each agent keeps its sessions and which records matter
  references/timeline-schema.md     the timeline JSON the renderer reads
  references/pivot-events.md        pivot event families, thresholds, severity, impact
  references/recommendations.md     when to recommend, and when not to
  scripts/render_timeline.py        timeline JSON → HTML page and Markdown summary
  tests/test_render_timeline.py     renderer tests
```

## Test

From this skill's folder:

```bash
python3 -m unittest discover -s tests -v
```

One test checks the page's JavaScript with `node --check`; it is skipped when Node.js is not installed.
