# Timeline schema

`scripts/render_timeline.py` reads one JSON document, `analyze-run-timeline/1`. It is independent of any
agent's transcript format and of any workflow: the analysis maps each source onto it. Timestamps are
ISO-8601 with `Z` or an offset.

## Document

| Field | Required | Meaning |
|---|---|---|
| `schema` | yes | `"analyze-run-timeline/1"` |
| `title` | yes | what ran, e.g. `Q3 market report draft` or `#418 — cancel an order before it ships` |
| `subject` | no | object of short facts shown under the title, e.g. `task`, `skill`, `session`, `folder`, `issue`, `pr`, `branch` |
| `timezone` | no | IANA zone for display, e.g. `Europe/Warsaw`; the system zone when absent |
| `agents` | yes | lanes, in display order (below) |
| `phases` | no | workflow phases or the run's chapters (below) |
| `skills` | no | which skill, command or prompt file each lane was running, and when (below) |
| `skill_catalog` | no | per skill name: `label`, one-line `description`, `url` of its definition (below) |
| `spans` | yes, or `events` | what each lane was doing (below) |
| `events` | yes, or `spans` | pivots, milestones, messages (below) |
| `analysis` | no | verdict, recommendations, observations (below) |
| `sources` | no | `{runtime, path, role, note}` per transcript or record used |
| `notes` | no | caveats: estimates, missing data, anything the reader must know |

## Agents

`{id, label, runtime, role, session, parent}`. `id` and `label` are required.

- `runtime`: `claude-code`, `codex`, `copilot`, `human`, or another agent's name.
- `role`: the part the session played, e.g. `main`, `researcher`, `writer`, `developer`, `reviewer`,
  `coordinator`, `background`.
- `parent`: another agent's `id`. The lane is drawn indented under its parent; use it for subagents and
  background jobs.
- Give the user a lane with `runtime: "human"` so prompts and answers show as messages.

## Phases

`{id, label, start, end}`. One band across all lanes; a return to an earlier phase is a new entry with the
same label.

When a workflow skill drove the run, use the phases or steps its definition names, in its own order and
wording. Locate them from, in order of reliability:

1. status or phase lines the workflow writes on each change, such as `Phase: … | Skill: …`;
2. the skill in use, when the definition assigns different skills to different phases;
3. the records the definition says each phase produces: a plan written, a draft saved, a pull request
   opened, a review requested, a file published.

Without a workflow skill, use the run's chapters: stretches with one goal, split where the user starts a
new request or changes direction. Name each chapter by its goal, e.g. `Collect sources`, `Draft`,
`Revise after feedback`.

## Skills

`{agent, name, start, end, detail}`: one entry per run of a skill, custom slash command or prompt file in
one lane. `name` is the full name as invoked, e.g. `research-kit:web-search` or `write-report`. Skills
nest: a workflow skill can span the whole run with the skills it calls inside it; the page stacks up to
three levels above the lane's bar. Record a skill used by a subagent in the subagent's lane too.

Find the boundaries as [transcript sources](transcript-sources.md#skills) describes. A skill ends when the
next skill starts in the same lane at the same nesting level, when the agent reports the skill's result
and returns to its caller, or at the end of the turn in which it ran. Built-in commands such as
`/compact`, `/clear` or `/model` are not skills; record them as events.

`skill_catalog` maps each `name` to `{label, description, url}`. Take `description` from the first
sentence of the definition's description. Point `url` at the definition that ran: its web address in the
repository it comes from, at the version used, when you know it; otherwise the local copy as a `file://`
path. Only `https://`, `http://` and `file://` links are accepted.

## Spans

`{agent, start, end, kind, label, detail, skill, items}`. `kind` is one of:

| kind | Use for |
|---|---|
| `work` | the agent reasoning, reading, writing, editing, short tool calls |
| `check` | verification runs: tests, linters, type checks, validators, evaluations, including loops that wait for them |
| `tool` | any other tool call or command that ran a minute or longer: builds, installs, downloads, data processing, web research, long API calls |
| `remote` | waiting for a job that runs elsewhere: CI, a cloud build or deployment, a batch or scheduled job |
| `review` | review of the work by another agent or a reviewer subagent, or the agent reading the findings |
| `wait-agent` | blocked on another agent or subagent |
| `wait-user` | blocked on a person: a gate, a question, an approval, or no reply yet |
| `blocked` | stopped by the environment: no network or VPN, expired credentials, service down, permission refused |

`label` is a short text drawn on wide spans (a command, check or step name); `detail` is one sentence
shown in the span's details.

`items` answers "what happened here": the actions inside the span in time order, each
`{"at": "<timestamp>", "text": "<at most 200 characters>"}`. Use one item per tool call (the command's
description or the command itself, the file edited or read, the page fetched, the skill or subagent
started), per error (`error: …`) and per short message from the agent (`said: …`). The page lists them
when the span is clicked, limited to the zoomed-in window first. At most 200 items per span are kept.

`skill` names the skill a span belongs to when the `skills` list cannot say it, for example a reviewer
subagent's span. Otherwise the page uses the innermost skill running at the span's midpoint in that lane,
or in the nearest parent lane: a subagent or background job works for the skill its parent is running.

**Segmentation:** walk each agent's events in time order and classify each interval between two
consecutive events:

1. a call has been running for 60 s or more → that call's kind (`check`, `tool`, `remote`, `wait-user`
   for a question to a person, `wait-agent` for waiting on another agent);
2. the next event is a human prompt and the interval is over a minute → `wait-user`;
3. the interval is 5 minutes or less → `work`;
4. otherwise → idle; leave it empty.

Merge neighbouring intervals of the same kind and label. Put background jobs on their own child lane.
A span in the environment's failure state (the retries after a refusal, a login that failed) becomes
`blocked` when the evidence shows the agent could not proceed.

## Events

`{id, type, at, end, agent, to, title, detail, category, severity, impact_min, occurrences, evidence}`.

| type | Required fields | Drawn as |
|---|---|---|
| `pivot` | `id` (`P1`, `P2`, … in time order), `severity` (`high`, `medium`, `low`) | numbered marker; `end` adds a bar for its duration; each `occurrences` time adds a tick |
| `milestone` | — | diamond: a result produced, e.g. a draft saved, a commit, a pull request, a check passing, a handoff |
| `message` | `to` | arrow from `agent` to `to`: user prompts, handoffs between sessions, subagent results |

`category` names the pivot family from the catalogue. `impact_min` is the estimated time the pivot cost.
`evidence` lists where the pivot can be checked, such as `claude:<session-id-prefix> tool_result 14:02`
or `codex:<thread-id-prefix> exec 09:40`.

## Analysis

```json
{
  "verdict": "healthy | friction | waste",
  "summary": "One or two sentences for the reader.",
  "recommendations": [
    {"title": "…", "why": "…", "evidence": ["P2", "P5"], "change": "…", "target": "…",
     "saving": "…", "cost": "…", "confidence": "high | medium | low"}
  ],
  "observations": ["P4: … — no change proposed."]
}
```

Every recommendation `evidence` entry must be a pivot `id`; the renderer rejects anything else.

## Minimal example

```json
{
  "schema": "analyze-run-timeline/1",
  "title": "Q3 market report draft",
  "subject": {"task": "market report", "skill": "write-report", "folder": "~/reports/q3"},
  "timezone": "Europe/Warsaw",
  "agents": [
    {"id": "user", "label": "User", "runtime": "human"},
    {"id": "main", "label": "Main session", "runtime": "claude-code", "role": "writer"},
    {"id": "res", "label": "Researcher", "runtime": "claude-code", "role": "researcher", "parent": "main"}
  ],
  "phases": [{"id": "c1", "label": "Collect sources", "start": "2026-09-20T09:00:00Z", "end": "2026-09-20T09:45:00Z"}],
  "skills": [{"agent": "main", "name": "write-report", "start": "2026-09-20T09:00:00Z", "end": "2026-09-20T09:45:00Z"}],
  "spans": [
    {"agent": "main", "start": "2026-09-20T09:00:00Z", "end": "2026-09-20T09:10:00Z", "kind": "work", "label": "outline",
     "items": [{"at": "2026-09-20T09:02:00Z", "text": "Write outline.md"}]},
    {"agent": "main", "start": "2026-09-20T09:10:00Z", "end": "2026-09-20T09:40:00Z", "kind": "wait-agent", "label": "research"},
    {"agent": "res", "start": "2026-09-20T09:10:00Z", "end": "2026-09-20T09:40:00Z", "kind": "tool", "label": "web research",
     "items": [{"at": "2026-09-20T09:12:00Z", "text": "search: Q3 retail sales Poland"},
               {"at": "2026-09-20T09:25:00Z", "text": "error: 429 Too Many Requests"}]}
  ],
  "events": [
    {"type": "message", "at": "2026-09-20T09:00:00Z", "agent": "user", "to": "main", "title": "draft the Q3 report"},
    {"type": "pivot", "id": "P1", "at": "2026-09-20T09:25:00Z", "end": "2026-09-20T09:35:00Z", "agent": "res",
     "severity": "medium", "category": "access", "title": "Search API rate-limited for 10 min",
     "impact_min": 10, "evidence": ["claude:3f2a… subagent tool_result 09:25Z"]}
  ]
}
```
