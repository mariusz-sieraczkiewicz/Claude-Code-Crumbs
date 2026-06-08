# Source: slack

Processes already-collected Slack activity for the day. Output contract: see `README.md`.

## Locate

`sources.slack` in `config.yaml`: `access` (`mcp` | `export` | `api`), `export_dir`, `channels` (empty = all the user participates in). Setup → `../integration.md`.

## Collect

1. Gather messages the user **sent** plus threads they actively replied in, across configured channels/DMs, for the target day.
2. Drop pure reactions, +1s, logistics ("on my way"), and bot noise.
3. Keep: explanations the user wrote, problems debated, decisions, links shared with commentary, questions answered.

## Emit

- Provenance ref: permalink when available, else `slack#<channel>`.
- Collapse a thread into one item summarizing the exchange + the user's contribution.

→ `raw/{date}/slack.md`
