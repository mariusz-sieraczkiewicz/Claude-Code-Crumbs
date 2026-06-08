# Source: recorder

Processes already-collected all-day audio recorder capture (continuous, noisy). Output contract: see `README.md`.

## Locate

`sources.recorder` in `config.yaml`: `dir`, `transcribe` (bool). Transcribe per `../integration.md` if needed and enabled.

## Collect

1. Find the target day's recordings/transcripts.
2. Segment by topic. These are long and mostly ambient — keep only spans with a clear idea, a spoken note, or an explicit "I should write about this" moment.
3. Discard idle/ambient audio, small talk, and anything private/personal not meant for publishing.

## Emit

- Provenance ref: `recorder:<file-stem>@<HH:MM>`.
- One item per kept idea.

→ `raw/{date}/recorder.md`
