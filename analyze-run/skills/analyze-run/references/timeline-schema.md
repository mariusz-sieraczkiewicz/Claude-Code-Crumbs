# Timeline schema

`scripts/render_timeline.py` reads one JSON document, `analyze-run-timeline/1`. It is independent of any
agent's transcript format: the analysis maps each source onto it. Timestamps are ISO-8601 with `Z` or an
offset.

## Document

| Field | Required | Meaning |
|---|---|---|
| `schema` | yes | `"analyze-run-timeline/1"` |
| `title` | yes | what ran, e.g. `#418 — cancel an order before it ships` |
| `subject` | no | object of short facts shown under the title: `issue`, `pr`, `branch`, `repo`, `mode` |
| `timezone` | no | IANA zone for display, e.g. `Europe/Warsaw`; the system zone when absent |
| `agents` | yes | lanes, in display order (below) |
| `phases` | no | delivery steps or chapters (below) |
| `skills` | no | which skill each lane was running, and when (below) |
| `skill_catalog` | no | per skill name: `label`, one-line `description`, `url` of its `SKILL.md` (below) |
| `spans` | yes, or `events` | what each lane was doing (below) |
| `events` | yes, or `spans` | pivots, milestones, messages (below) |
| `analysis` | no | verdict, recommendations, observations (below) |
| `sources` | no | `{runtime, path, role, note}` per transcript or record used |
| `notes` | no | caveats: estimates, missing data, anything the reader must know |

## Agents

`{id, label, runtime, role, session, parent}`. `id` and `label` are required.

- `runtime`: `claude-code`, `codex`, `copilot`, `human`, or another host name.
- `role`: for example `main`, `analyst`, `developer`, `supervisor`, `reviewer (spec)`, `background`.
- `parent`: another agent's `id`. The lane is drawn indented under its parent; use it for subagents,
  reviewer subagents and background jobs.
- Give the user a lane with `runtime: "human"` so prompts and answers show as messages.

## Phases

`{id, label, start, end}`. One band across all lanes. Use the phases of the workflow the run followed,
numbered in its own order, for example `1 Define`, `2 Prepare`, `3 Implement`, `4 Review`, `5 Finish` for a
delivery workflow. Read the workflow's `SKILL.md` for its phase names. Locate them from, in order of
reliability:

1. status or phase lines the workflow writes on each phase change, such as `Phase: … | Skill: …`;
2. the skill in use, when the workflow runs different skills in different phases: for example planning or
   interview skills → preparation, implementation or test-first skills → implementation, review skills →
   review, end-to-end tests and completion → finish;
3. GitHub records: Issue selected → definition; plan or checklist written → end of preparation; draft PR
   and pushes → implementation; review requested → review; ready for review, merge or closing → finish.

A return to an earlier step is a new phase entry with the same label.

## Skills

`{agent, name, start, end, detail}`: one entry per skill run in one lane. `name` is the skill's full name,
e.g. `my-plugin:code-review`. Skills nest: a workflow skill spans the whole delivery, `implement` sits
inside it and `tdd` inside `implement`; the page stacks them in up to three rows above the lane's bar. Record a
skill used by a subagent in the subagent's lane too.

Find the boundaries as [transcript sources](transcript-sources.md#skills) describes. A skill ends when the
next skill starts in the same lane at the same nesting level, when the agent reports the skill's result
and returns to its caller, or at the end of the turn in which it ran. Built-in commands such as
`/compact`, `/clear` or `/model` are not skills; record them as events.

`skill_catalog` maps each `name` to `{label, description, url}`. Take `description` from the first
sentence of the skill's frontmatter description. Point `url` at the `SKILL.md` that ran: its web address
in the plugin's repository at the version used when you know it, otherwise the installed copy as a
`file://` path. Only `https://`, `http://` and `file://` links are accepted.

## Spans

`{agent, start, end, kind, label, detail, skill, items}`. `kind` is one of:

| kind | Use for |
|---|---|
| `work` | the agent reasoning, reading, editing, short commands |
| `test` | test runs, including polling loops that wait for tests |
| `tool` | builds, installs, other commands that ran a minute or longer |
| `ci` | waiting for remote checks, such as GitHub Actions |
| `review` | review work, such as a reviewer subagent's lane or the delivery owner reading findings |
| `wait-agent` | blocked on another agent or subagent |
| `wait-user` | blocked on the user: a gate, a question, or no reply yet |
| `blocked` | stopped by the environment: no VPN, expired credentials, service down, permission refused |

`label` is a short text drawn on wide spans (a test suite, command or step name); `detail` is one
sentence shown in the span's details.

`items` answers "what happened here": the actions inside the span in time order, each
`{"at": "<timestamp>", "text": "<at most 200 characters>"}`. Use one item per tool call (the command's
description or the command itself, the file edited or read, the skill or subagent started), per error
(`error: …`) and per short message from the agent (`said: …`). The page lists them when the span is
clicked, limited to the zoomed-in window first. At most 200 items per span are kept.

`skill` names the skill a span belongs to when the `skills` list cannot say it, for example a reviewer
subagent's span. Otherwise the page uses the innermost skill running in that lane at the span's midpoint.

**Segmentation:** walk each agent's events in time order and classify each interval between two
consecutive events:

1. a call has been running for 60 s or more → that call's kind (`test`, `tool`, `ci`, `wait-user` for a
   question to the user, `wait-agent` for waiting on another agent);
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
| `milestone` | — | diamond: commit, PR opened, checks green, merge, phase handoff |
| `message` | `to` | arrow from `agent` to `to`: user prompts, handoffs between sessions, subagent results |

`category` names the pivot family from the catalogue. `impact_min` is the estimated time the pivot cost.
`evidence` lists where the pivot can be checked, such as `claude:<session-uuid-prefix> tool_result 14:02`
or `gh run 35826159026`.

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
  "title": "#418 — cancel an order before it ships",
  "subject": {"issue": "#418", "pr": "#421", "mode": "full-flow"},
  "timezone": "Europe/Warsaw",
  "agents": [
    {"id": "user", "label": "User", "runtime": "human"},
    {"id": "main", "label": "Delivery owner", "runtime": "claude-code", "role": "full-flow"},
    {"id": "spec", "label": "Spec reviewer", "runtime": "claude-code", "role": "reviewer", "parent": "main"}
  ],
  "phases": [{"id": "p3", "label": "3 Implement", "start": "2026-09-20T09:00:00Z", "end": "2026-09-20T10:10:00Z"}],
  "spans": [
    {"agent": "main", "start": "2026-09-20T09:00:00Z", "end": "2026-09-20T09:40:00Z", "kind": "work", "label": "implement"},
    {"agent": "main", "start": "2026-09-20T09:40:00Z", "end": "2026-09-20T10:05:00Z", "kind": "test", "label": "gradlew test"}
  ],
  "events": [
    {"type": "message", "at": "2026-09-20T09:00:00Z", "agent": "user", "to": "main", "title": "whole checklist, autonomously"},
    {"type": "pivot", "id": "P1", "at": "2026-09-20T09:40:00Z", "end": "2026-09-20T10:05:00Z", "agent": "main",
     "severity": "medium", "category": "long-running", "title": "Full backend suite took 25 min",
     "impact_min": 18, "evidence": ["claude:3f2a… Bash ./gradlew test 09:40Z–10:05Z"]}
  ]
}
```
