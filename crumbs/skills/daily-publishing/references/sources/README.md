# Sources — shared contract

Each source has its own file in this directory so it can be tuned and developed independently. Phase 1 reads this contract once, then runs each source in the active set (see "Resolving" below). Files here cover **processing already-collected data into raw material** — not service setup (that's `../integration.md`).

## Output contract (every source file obeys this)

Write the target day's material to `{base}/raw/{date}/<source>.md`, one item per line:

```
- HH:MM | <provenance ref> | <content, one or few lines>
```

- `provenance ref` — a link, channel, file path, or session id specific enough to cite later.
- Sort ascending by time. Deduplicate near-identical lines.
- Redact secrets/tokens. Mark anything still sensitive after redaction `⚠️confidential` (kept here, filtered in Phase 2) — never drop it silently.

## Redaction (every source, while gathering)

Strip identifying names as you write each item — this happens during gathering, not later:

- **Company / employer names** → "the company" / "work".
- **Project / product / codename** → "the project" / "a service".
- **People's names** (colleagues, clients, attendees) → role or "a teammate" / "a stakeholder".
- **Internal systems, repos, hostnames, URLs, ticket ids** → a generic noun ("an internal service", "the deploy pipeline").

Keep the transferable lesson; drop the identifier. Provenance refs (channel/file/session id) stay — they're local and never published. When unsure whether something identifies, redact it.

## Resolving the active set & where data lives

Which sources run is decided by the precedence in `SKILL.md` → Configuration → Active source set: `--source` override → else `sources.<name>.enabled: true` → else (no config) all.

For each source in that set, read its block under `sources.<name>` in `{base}/config.yaml` for paths/access. If the required path or access is missing, **skip** the source and record `skipped (not configured)` — do not fail the run. (`enabled: false` excludes a source up front; a missing-config skip is the fallback for an enabled-but-unconfigured one.)

## Adding a source

1. Add `<name>.md` here following the output contract.
2. Add its config keys + setup to `../integration.md`.
3. No `SKILL.md` change needed — Phase 1 iterates over enabled sources generically.
