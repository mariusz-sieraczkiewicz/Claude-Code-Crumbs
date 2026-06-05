# Source: meetings

Processes already-collected meeting transcripts for the day. Output contract: see `README.md`.

## Locate

`sources.meetings` in `config.yaml`: `transcript_dir`, `transcribe` (bool). Transcripts as `.txt`/`.vtt`/`.srt`/`.md`. If only audio exists and `transcribe: true`, transcribe per `../integration.md`; else skip with a note.

## Collect

1. Find transcripts dated to the target day.
2. Per meeting, extract: decisions, action items, and any insight worth sharing publicly.
3. Apply the shared Redaction rules from `README.md` — keep the generalizable idea, drop the specifics.

## Emit

- Provenance ref: `meeting:<file-stem>` (+ timestamp range when present).
- One item per distinct insight, not one per meeting.

→ `raw/{date}/meetings.md`
