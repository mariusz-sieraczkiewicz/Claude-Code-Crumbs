# Source: gchat

Processes already-collected Google Chat activity for the day. Output contract: see `README.md`.

## Locate

`sources.gchat` in `config.yaml`: `access` (`api` | `export` | `cli`), `credentials`, `export_dir`. With `access: cli`, read via a Google Workspace CLI (e.g. `gws chat spaces list`, `gws chat spaces messages list`) — auth lives in the CLI, no credentials path needed. Setup → `../integration.md`.

## Collect

1. Gather the user's messages and the spaces/DMs they were active in for the target day.
2. Drop logistics and one-word replies; keep substantive exchanges, decisions, and shared resources with commentary.

## Emit

- Provenance ref: message link when available, else `gchat#<space>`.
- Collapse a back-and-forth into one item capturing the point and the user's contribution.

→ `raw/{date}/gchat.md`
