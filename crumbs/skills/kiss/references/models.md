# Fixed models for roles

Choose the profile supported by the execution host when starting each role. Explicit human or project model settings take precedence. Keep the model and effort fixed for that role across the agreed batch; do not switch them for each Issue or each reasoning step.

| Role | OpenAI profile | Claude profile |
| --- | --- | --- |
| Analyst / delivery owner | `gpt-6-astra`, `medium` | `claude-opus-5`, `high` |
| Developer | `gpt-5.6-sol`, `high` | `claude-opus-5`, `high` |
| Independent reviewer | `gpt-6-astra`, `high` | `claude-opus-5`, `high` |
| Delegated Supervisor | `gpt-5.6-sol`, `medium` | `claude-sonnet-5`, `medium` |
| Ambiguous synchronization description | `gpt-5.6-luna`, `low` | `claude-sonnet-5`, `low` |

Deterministic synchronization uses scripts or APIs, not a model. An Analyst coordinating execution keeps the Analyst profile; do not create a Supervisor just to relay messages. Review independence requires a separate assessment, not a different model provider.

These are starting settings for the typical delivery workload, not measured optimal settings. The Developer profile retains capacity for contract changes, persistence, concurrency and integration. The reviewer examines a bounded change deeply. The Supervisor profile assumes execution coordination rather than another complete architecture review. Do not default the whole team to `xhigh`, `max` or `ultra`.

## Apply and verify

Use the host's supported launch setting for the exact model and effort; check its schema or CLI help instead of guessing flags. For OpenAI Responses API use `reasoning.effort`; for Claude API use `thinking: {type: adaptive}` with `output_config.effort`. Claude's adaptive thinking may vary work within a fixed effort level; it does not require changing the configured profile. Equal effort names across providers are not a claim of equal cost or capability.

Pin the actual provider model identifier, not an unverified `opus` or `sonnet` alias. Verify the effective model, effort, provider and region in session metadata or the first response, and retain the evidence in the execution record. Subagents and reviewers need their own assigned profile; do not silently inherit a different worker default.

Do not restart a working session just to apply a new default. Record an existing session's actual setting and apply the chosen profile on the next safe launch. If a configured model is unavailable, diagnose host access or use an explicitly authorized fallback. Keep unaffected work moving, report the limitation, and do not silently downgrade or claim the requested profile ran.

## Measure the result

Compare fixed profiles across batches using cost per completed behaviour, delivery time, review repairs, regressions and human interventions. Track the median and the slowest tasks. Separate input, cached input, output and application-model trials by role, session, Issue/PR and provider region. Cached-context totals from a Codex session are not a Portkey invoice or a measure of regional slot use.

Change a role's future default only after reviewing a comparable batch or receiving new human direction. Lower prices per token do not prove lower delivery cost when retries and integration increase.

Sources for model capabilities and settings: [OpenAI models](https://developers.openai.com/api/docs/models), [Astra guidance](https://developers.openai.com/api/docs/guides/latest-model), [Claude effort](https://platform.claude.com/docs/en/build-with-claude/effort), and [Claude Code configuration](https://code.claude.com/docs/en/model-config). These role assignments are KISS defaults, not vendor recommendations for this workflow.
