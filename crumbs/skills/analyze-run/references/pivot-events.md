# Pivot events

A pivot event changed the course or the cost of the run. Look for the families below; the signals are
starting points, and the thresholds are defaults to adjust when the run's context justifies it. Record a
pivot only with evidence you can point to. Something that happened but cost nothing is not a pivot.

## Families

| Category | What happened | Signals | Default threshold |
|---|---|---|---|
| `access` | No network or VPN, expired login, missing token, service or registry unreachable, rate limit, tool server not connected, sandbox or permission refusal | `ENOTFOUND`, `ECONNREFUSED`, timeouts to internal hosts, `401`/`403`/`429`, "needs authentication", "failed to connect", refused tool calls | any occurrence that cost a retry; high when it stopped the work |
| `long-running` | One tool call, command, check or remote job took long | call or span duration; job times from the system that ran them | 10 min for one local call, 20 min for a remote job; or checks and remote jobs above 30% of agent activity |
| `loop` | The same step repeated without progress: a failing command or check re-run unchanged, the same error three times, repeated polling, the same text or file rewritten back and forth | identical calls or errors in a row, no change between attempts | 3 repeats |
| `review-loop` | Review → repair → re-review cycles on the same output: code, a document, an analysis | review skill or reviewer subagent runs per output; changes made after findings | more than 2 rounds, or re-review of content that had not changed |
| `rework` | Work undone or redone: reverted or restored files, a discarded draft, a rewritten plan, a return to an earlier phase, a review finding that a requirement is unmet | revert, reset or restore; phase regression; a plan or outline rewritten after execution began | any, when it discarded 15 min or more of work |
| `skill-gap` | The run and the running skill's definition disagree: the agent skipped, reordered or improvised a step, asked about something the definition should answer, followed an instruction that did not fit, or was corrected by the user for breaking one | the definition read in step 2 compared with the agent's actions; questions and corrections around a skill step; the definition re-read mid-run | any, when it cost time or changed the result |
| `discovery` | The agent spent long finding something that could have been given: where files or commands are, a project convention, which tool or account to use | long stretches of listing, searching and reading before the first productive action; the answer later found in a known place | 10 min, or the same search repeated in later runs |
| `waiting` | Blocked on a person: a gate, a question, an approval, an answer that took long | `wait-user` spans, open questions to the user | 15 min during working hours; mark as human availability when the user was away |
| `handoff` | Latency between sessions: a task handed to another session, its acceptance reply, returned results, held or refused cross-session messages | message times in both sessions | 10 min from sending to acceptance or to the first action |
| `context` | Context compaction or reset, resume after a quit app, lost state that had to be rebuilt | compaction records, continuation prompts, re-reading files already read | automatic compaction; any resume that repeated work |
| `scope` | The user or an agent changed direction: new requirement, split of work, "stop", correction of a wrong assumption | human prompts that redirect; declined proposals | any change that altered the plan |
| `failure` | Tool or model errors: API overload, crashes, a worker or session that exited | error results, retries, aborted turns, exited sessions | when it cost a retry of more than a minute |

## Severity

- **high**: stopped the run or cost 30 minutes or more, or changed what was delivered.
- **medium**: cost 5 to 30 minutes, or recurred enough to matter.
- **low**: worth seeing on the timeline for context, cost under 5 minutes.

## Impact estimate

Estimate `impact_min` as the time the run would have saved had the pivot not happened, not the pivot's
duration. Examples: a 25-minute full test suite where a focused 3-minute run was enough costs about
22 minutes; twelve refused commands that each needed a rewrite cost about a minute each; a skill step
that was improvised and then redone costs the time of the first attempt; a gate the user answered after
lunch costs the wait on the wall clock but no agent effort. Leave `impact_min` out when it cannot be
estimated, and say why in `detail`.

## Recording

- One pivot per cause. Put repeats in `occurrences`, and for a lasting state set `end`.
- Attribute the pivot to the agent that experienced it. When several agents hit the same cause, one pivot
  per agent keeps the lanes honest.
- For a `skill-gap`, name the skill and quote or point to the instruction in `detail`.
- Number pivots `P1`, `P2`, … in time order.
- Write `title` as what happened, e.g. `Package registry unreachable without VPN`, not as a judgement.
