# Pivot events

A pivot event changed the course or the cost of the run. Look for the families below; the signals are
starting points, and the thresholds are defaults to adjust when the run's context justifies it. Record a
pivot only with evidence you can point to. Something that happened but cost nothing is not a pivot.

## Families

| Category | What happened | Signals | Default threshold |
|---|---|---|---|
| `access` | No VPN, expired login, missing token, service or registry unreachable, MCP server not connected, sandbox or permission refusal | `ENOTFOUND`, `ECONNREFUSED`, timeouts to internal hosts, `401`/`403`, `gh auth`, "needs authentication", "failed to connect", refused tool calls | any occurrence that cost a retry; high when it stopped the work |
| `long-running` | A single test run, build, E2E suite or CI run took long | call or span duration; CI run times from GitHub | 10 min for one local run, 20 min for CI; or tests and CI above 30% of agent activity |
| `loop` | The same step repeated without progress: failing test re-run unchanged, same error three times, repeated polling | identical commands or errors in a row, no edit between runs | 3 repeats |
| `review-loop` | Review → repair → re-review cycles on the same change | review skill invocations per PR or Issue; reviewer subagent spawns; amends after findings | more than 2 rounds, or re-review of content that had not changed |
| `rework` | Work undone or redone: revert, reset, re-planned checklist, return to an earlier phase, a review finding that a requirement is unmet | `git revert`/`reset`, phase regression, checklist rewritten after implementation began | any, when it discarded 15 min or more of work |
| `waiting` | Blocked on the user: gate, question, document acceptance, answer that took long | `wait-user` spans, open questions to the user | 15 min during working hours; mark as human availability when the user was away |
| `handoff` | Latency between sessions: a task handed to another session, its acceptance reply, returned results, held or refused cross-session messages | message times in both sessions | 10 min from sending to acceptance or to the first action |
| `context` | Context compaction, `/clear`, resume after a quit app, lost state that had to be rebuilt | compaction records, continuation prompts, re-reading files already read | automatic compaction; any resume that repeated work |
| `scope` | The user or an agent changed direction: new requirement, split of work, "stop", correction of a wrong assumption | human prompts that redirect; declined proposals | any change that altered the plan |
| `failure` | Tool or model errors: API overload, rate limit, crashes, a worker that exited | error results, retries, `turn_aborted`, exited sessions | when it cost a retry of more than a minute |

## Severity

- **high**: stopped the run or cost 30 minutes or more, or changed what was delivered.
- **medium**: cost 5 to 30 minutes, or recurred enough to matter.
- **low**: worth seeing on the timeline for context, cost under 5 minutes.

## Impact estimate

Estimate `impact_min` as the time the run would have saved had the pivot not happened, not the pivot's
duration. Examples: a 25-minute full suite where a focused 3-minute run was enough costs about 22 minutes;
twelve refused commands that each needed a rewrite cost about a minute each; a gate the user answered
after lunch costs the wait on the wall clock but no agent effort. Leave `impact_min` out when it cannot be
estimated, and say why in `detail`.

## Recording

- One pivot per cause. Put repeats in `occurrences`, and for a lasting state set `end`.
- Attribute the pivot to the agent that experienced it. When several agents hit the same cause, one pivot
  per agent keeps the lanes honest.
- Number pivots `P1`, `P2`, … in time order.
- Write `title` as what happened, e.g. `Maven repository unreachable without VPN`, not as a judgement.
