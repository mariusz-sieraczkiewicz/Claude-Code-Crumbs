# Visuals — shared contract

Each visual **kind** has its own file in this directory so it can be tuned independently. The Visuals phase reads this contract once, then for each chosen subject applies the per-kind files (`image.md`, `diagram.md`). Every visual is generated **from that subject's verified `subject.md`** and saved into the subject's `assets/` directory.

This file is the *contract* — what to ground in, how to judge, name, and record visuals, and when to skip. Engine setup (key, billing, config knobs) lives in `../integration.md`.

## Skip if not configured (check this first)

The whole phase is opt-in. **Skip — never fail the run — when either:**
- `visuals.enabled` is `false` (or absent) in `{base}/config.yaml`, or
- no usable API key (the helper exits non-zero with "visuals not configured" when the key is unset, empty, or the placeholder `REPLACE_ME` — whether it comes from `~/.config/daily-publishing/secrets.env` or the `$GEMINI_API_KEY` env var).

On skip, do nothing to the drafts and report `visuals skipped (not configured)`. A 429 / `RESOURCE_EXHAUSTED` *mid-run* (free tier or quota) skips **that one asset** — record it as skipped in the manifest and report, then continue with the rest of the run.

## Grounding (mandatory)

Every visual is derived from the **verified `subject.md`** — the same source of truth the formats draw from, already checked against the real code/skill/docs in Phase 6 (verify-against-source). Build the brief from what the subject actually says: its main message, its concrete worked example, its real structure. **Never** generate from the title or a bare topic word — prompted from a word the model draws a pretty, wrong picture. If `subject.md` is missing for a chosen subject, skip visuals for it with a noted reason; do not fabricate from the slug.

## Judgment — what to make (no fixed number)

- **Hero image is mandatory** for every subject (`image.md`).
- **Additional visuals are content-driven**, decided from `subject.md` using best practice — not a fixed count:
  - Add a **dependency/concept diagram** (`diagram.md`) when the subject turns on *structure or relationships* — how parts depend on, feed, or sequence into each other.
  - Add **another image** when a distinct idea in the subject earns its own visual (a second worked example, a before/after).
  - Keep diagrams at **concept altitude (~4–6 nodes)**; push file-level detail into the prose, not the picture.
- When in doubt, fewer and clearer beats more. A subject with one idea wants just the hero.

## Generate N, auto-pick (no interactive pick)

Image-model output is non-deterministic — the same prompt gives different valid compositions. For each visual, generate **N candidates** (default from `visuals.candidates` in config, ~2–3) by calling the helper N times into `-1`, `-2`, … filenames, then **auto-select the best** — no prompt, no `AskUserQuestion`, in interactive *and* unattended runs alike. Best candidate = labels legible and correctly spelled, content matches the brief and the subject, clean uncluttered composition. Keep the picked file; discard the rest.

## Output naming & manifest

Save under the subject's assets dir:

```
{base}/subjects/{date}-{slug}/assets/<slug>-<kind>-<n>.<ext>
```

- `<kind>` is `hero`, `diagram`, or `image`; `<n>` is the candidate index of the picked file.
- `<ext>` is whatever the model returned (**JPEG even when not requested** — the helper sets `.jpg`/`.png` from the response `mimeType`; trust its printed path).

Write `assets/manifest.yaml` listing every kept asset:

```yaml
assets:
  - file: <slug>-hero-1.jpg   # path relative to the subject dir
    kind: hero                # hero | diagram | image
    prompt: |                 # the exact prompt sent to the model
      ...
    alt: "concise alt text describing the visual"
    aspect: "16:9"
    model: "gemini-3-pro-image"
```

Record a skipped asset too (`file: ""`, with a `skipped:` reason) so the report is honest.

## Aspect ratio per format

Pick the aspect from where the visual is referenced:

| Use | Aspect |
| --- | --- |
| blog hero, inline diagram | `16:9` |
| x / social card | `1:1` or `4:5` |
| linkedin | `1.91:1` |
| youtube thumbnail | `16:9` |

## Helper usage

The phase calls `scripts/generate-visual.sh` once per candidate (it reads the key itself; the key is never in this repo):

```bash
scripts/generate-visual.sh \
  --prompt-file /tmp/visual-prompt.txt \
  --out "{base}/subjects/{date}-{slug}/assets/{slug}-hero-1.jpg" \
  --aspect 16:9 --size 2K
```

Write the prompt to a file (no shell-escaping of long prompts). The helper prints the **final saved path** to stdout (the extension may change to match the returned bytes) and usage/cost to stderr. Exit non-zero = skip this asset (non-zero code 2 = not configured → skip the whole phase; 3 = API error such as 429 → skip just this asset).

## Provider

`visuals.provider` is `gemini` — the only provider implemented now (model `gemini-3-pro-image`, GA). The contract above is written provider-neutral (brief → N candidates → auto-pick → save → manifest) so a second provider can be added later by swapping the engine behind the helper, without changing the per-kind files or the phase.

## Adding a visual kind

1. Add `<kind>.md` here following this contract (purpose · when used · prompt shape · aspect · candidate count · skeleton template).
2. If it needs new config, add the keys + setup to `../integration.md`.
3. No `SKILL.md` change needed — the Visuals phase iterates over the kinds the subject's content calls for.
