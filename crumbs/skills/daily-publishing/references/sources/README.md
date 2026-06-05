# Sources — shared contract

Each source has its own file in this directory so it can be tuned and developed independently. Phase 1 reads this contract once, then runs each enabled source's file. Files here cover **processing already-collected data into raw material** — not service setup (that's `../integration.md`).

## Output contract (every source file obeys this)

Write the target day's material to `{base}/raw/{date}/<source>.md`, one item per line:

```
- HH:MM | <provenance ref> | <content, one or few lines>
```

- `provenance ref` — a link, channel, file path, or session id specific enough to cite later.
- Sort ascending by time. Deduplicate near-identical lines.
- Redact secrets/tokens. Mark client-confidential items `⚠️confidential` (kept here, filtered in Phase 2) — never drop them silently.

## Resolving where data lives

Read the source's block under `sources.<name>` in `{base}/config.yaml` for paths/access. If the path or access is missing, **skip** the source and record `skipped (not configured)` — do not fail the run.

## Adding a source

1. Add `<name>.md` here following the output contract.
2. Add its config keys + setup to `../integration.md`.
3. No `SKILL.md` change needed — Phase 1 iterates over enabled sources generically.
