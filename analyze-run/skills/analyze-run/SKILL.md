---
name: analyze-run
description: Analyse how an agent run actually went — a skill-driven workflow, such as a delivery flow with analyst, developer and reviewer sessions, or any longer agent task. Rebuilds its timeline from Claude Code, Codex and GitHub Copilot session transcripts plus git and GitHub records, renders a self-contained HTML timeline that shows which agent did what, when and in which skill, marks pivot events (lost access, long tests, review loops, waits, rework), and recommends changes only where the evidence shows avoidable time.
argument-hint: "[<issue-url-or-number> | <pr> | <branch> | <session-id-or-transcript-path> | --since <time>] [--out <dir>]"
---

# Analyze run

Reconstruct what happened during a run, where the time went and which agent spent it, then say whether
anything is worth changing. A run that went well is a valid finding; do not invent improvements.

The analysis is read-only. It never edits skills, code, settings or configuration, and never posts to
GitHub, Slack or Jira. It proposes; the user decides and acts, or asks for the change separately.

## 1. Identify the run

**Input:** an Issue or PR (URL or number), a branch, a session UUID or transcript path, a time window, or
nothing.

Establish the **subject** (Issue, PR or branch), the **repository** and its checkouts or worktrees, and
the **time window**. Use the Issue and PR timelines, the branch history and the sessions' own timestamps;
widen the window by a few minutes on each side.

With no input, list the recent candidate runs for the current repository (recent Issues and PRs worked on
by agents, recent sessions whose working directory is this repository or its worktrees) and ask the user
to pick one. Ask as well when two candidates fit equally.

## 2. Collect the sources

Read [transcript sources](references/transcript-sources.md). Find every transcript that touched the run
inside the window, in all three runtimes: the main session, its subagents, continuation sessions after
`/clear` or a resume, and peer sessions that worked on the same task, such as analyst, developer or
reviewer sessions. Peer sessions are often named by the session UUIDs quoted in their messages to each
other. Add git and GitHub records for milestones and CI duration.

Remove duplicates: a forked or relocated session repeats earlier records in several files. Record each
source's path, runtime, role and time span; they go into the timeline's `sources`.

## 3. Extract events

Transcripts run to tens or hundreds of megabytes. Never read a whole one into context. Sample its first
lines and a few records of each type to learn its shape, then write a throwaway script that streams the
file and prints one compact event per line: time, agent, event kind, tool name, a summary of at most
200 characters, call id and error flag. Summarise a command by its description when it has one, a file
operation by the file name, and a skill or subagent start by its name.

Never copy full tool output, credentials, tokens or environment values. The extraction script masks
secret-looking strings before printing: GitHub tokens (`ghp_…`, `gho_…`, `github_pat_…`), API keys
(`sk-…`, `AKIA…`, `xox…-`), `Bearer …` values and `password=`, `secret=` or `token=` values.

Save the scripts next to the outputs (step 7) so the analysis can be re-run.

## 4. Build the timeline

Write `timeline.json` in the format described in [timeline schema](references/timeline-schema.md):

- **Agents:** one lane per session; subagents and background jobs sit under their parent; the user has a lane.
- **Phases:** the workflow's own phases when the run followed a workflow skill that names them, located as
  the schema reference describes. Otherwise use the user's own chapters.
- **Skills:** every skill run per lane, nested where one skill calls another, plus a `skill_catalog` entry
  with each skill's description and a link to its `SKILL.md`.
- **Spans:** derived from the events with the segmentation method in the schema reference. Give each span
  its `items`, the actions that happened inside it, so the reader can click a span and see what was done.
- **Events:** milestones, messages between agents and the user, and pivot events (step 5).

## 5. Find the pivot events

Use the [pivot event catalogue](references/pivot-events.md). A pivot is something that changed the course
or the cost of the run. Each pivot needs evidence (source and time), an agent, a severity and, where
measurable, an estimated impact in minutes. Merge repeats of the same cause into one pivot with
`occurrences`. Number pivots in time order. Most runs have three to ten.

## 6. Assess

Apply [recommendation rules](references/recommendations.md): set the verdict from the avoidable share of
time, write recommendations only where they pass those rules, and record everything else as observations.
Put the result in the timeline's `analysis` block.

## 7. Render and report

Write the outputs to `--out`, or by default to
`${XDG_STATE_HOME:-$HOME/.local/state}/analyze-run/<repository>/<subject>-<YYYYMMDD-HHMM>/`, outside every
repository:

```bash
python3 <this-skill>/scripts/render_timeline.py timeline.json -o timeline.html --md summary.md
```

The script needs Python 3.9 or later and nothing else. It validates the input and lists every problem;
fix them and re-run. Open the page and look at it: every lane labelled, skills and pivots visible, no
label collisions, collapsed gaps where the run paused.

Write the timeline texts in English unless the user asks otherwise, because the page may be shared with
a team. Report to the user in their language and in plain words, assuming they know only what they wrote
themselves: the verdict in one sentence, the two or three largest time sinks, recommendation titles with
their expected saving, and where `timeline.html` and `summary.md` are. Explain a term or pivot id the
first time it appears instead of assuming the reader remembers it.

Then offer the next steps without doing them: open or share the page, turn a recommendation into an Issue
in the repository that owns the change, or apply a change.
