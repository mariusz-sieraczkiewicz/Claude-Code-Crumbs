# KISS setup guide

KISS coordinates delivery through an Analyst, Developers and an optional Supervisor. See [the skill](SKILL.md) for the workflow. This guide is for the person configuring the agents.

## Model recommendations

The user or host sets each agent's model and reasoning effort. These profiles are optional starting points, not measured optima or instructions to reconfigure roles. KISS selects settings only for Developers it launches on ONA, within user or project constraints.

For a useful comparison, keep the chosen settings stable across a batch rather than changing them for every Issue.

| Role | OpenAI profile | Claude profile |
| --- | --- | --- |
| Analyst / delivery owner | `gpt-6-astra`, `medium` | `claude-opus-5`, `high` |
| Developer | `gpt-5.6-sol`, `high` | `claude-opus-5`, `high` |
| Independent reviewer | `gpt-6-astra`, `high` | `claude-opus-5`, `high` |
| Delegated Supervisor | `gpt-5.6-sol`, `medium` | `claude-sonnet-5`, `medium` |
| Ambiguous synchronization description | `gpt-5.6-luna`, `low` | `claude-sonnet-5`, `low` |

Deterministic synchronization uses scripts or APIs, not a model. An Analyst can coordinate execution without an additional Supervisor to relay messages. Review independence requires a separate assessment, not a different model provider.

The Developer profile covers contracts, persistence, concurrency and integration; the reviewer examines a bounded change deeply. The Supervisor profile assumes coordination, not a second architecture review. Compare the suggested settings before selecting the highest effort for every role.

## Configure the host

Choose exact model identifiers and effort levels supported by the host. Provider effort names do not imply equal cost or capability. For ONA Developers, the coordinator follows the [launch and verification procedure](references/ona.md#select-the-developer-model); other roles retain the settings supplied by the user or host.

An existing session does not need a restart to adopt a recommendation. Apply any chosen change at the next safe launch.

## Measure the result

Compare fixed profiles across batches using cost per completed behaviour, delivery time, review repairs, regressions and human interventions. Track the median and the slowest tasks. Separate input, cached input, output and application-model trials by role, session, Issue/PR and provider region. Cached-context totals from a Codex session are not a Portkey invoice or a measure of regional slot use.

Use a comparable batch to decide whether to change your future setup. Lower prices per token do not prove lower delivery cost when retries and integration increase.

Sources for model capabilities and settings: [OpenAI models](https://developers.openai.com/api/docs/models), [Astra guidance](https://developers.openai.com/api/docs/guides/latest-model), [Claude effort](https://platform.claude.com/docs/en/build-with-claude/effort), and [Claude Code configuration](https://code.claude.com/docs/en/model-config). The role assignments are suggestions for this workflow, not vendor recommendations.

## ONA setup

The KiaKia AI Native ONA project has runners for Europe and the United States. Use its configured runners and verify their current identifiers and capacity through the [ONA procedure](references/ona.md).
