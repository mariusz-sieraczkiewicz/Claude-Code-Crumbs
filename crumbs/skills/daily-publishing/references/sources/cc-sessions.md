# Source: cc-sessions

Processes already-collected Claude Code session history — split into **work (Roche)** and **private** profiles. Output contract: see `README.md`.

## Locate

Session files: `~/.claude/projects/{encoded-project-path}/*.jsonl` (path `/`→`-`, leading `-`). `sources.cc_sessions` in `config.yaml`: `work_paths` / `private_paths` map project roots to profiles; unlisted projects default to `private`. JSONL shape: see `learn-from-conversation-analyzer`.

## Collect

1. Select `.jsonl` files modified on the target day.
2. Per file: read compaction summaries first (richest), then scan user↔assistant turns.
3. Extract publishable moments — problems solved, decisions, techniques, gotchas, before/after, "why this approach" reasoning. Tag each `profile:work` or `profile:private`.

## Confidentiality (Roche / work)

For `profile:work` items, abstract away client names, internal systems, and proprietary detail — keep only the transferable, generic lesson. Mark residual sensitivity `⚠️confidential`. When in doubt, abstract harder.

## Emit

- Provenance ref: `cc:<profile>:<session-id-short>`.

→ `raw/{date}/cc-sessions.md`
