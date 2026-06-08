# Formats — shared voice

Each output format has its own file so it can be tuned and developed independently. Phase 7 reads this once, then for each enabled output applies its format file. Every format is written **from the subject's `subject.md`** and saved as its own file in the subject directory.

## Voice

Read `identity:` from `{base}/config.yaml` (name, handles, links, tone, audience) and write in it. Defaults if unset:
- **First person, practical, specific.** You did the thing — say so plainly.
- **No hype.** Ban: "game-changer", "revolutionary", "unlock", "in today's fast-paced world", "leverage" (as a verb), "delve", emoji-as-bullets, em-dash-heavy AI cadence.
- **Concrete over abstract.** Real numbers, real names of tools, real code. One idea, well lit, beats five gestured at.
- **Teach, don't assume context.** Define every term, framework, or named concept the first time it appears, and build from first principles. Assume a competent peer — but NOT one who shares your project's vocabulary or context. If a reader without the backstory couldn't follow it, it isn't done. A metaphor may aid intuition but never replaces the plain, down-to-earth explanation.
- **Earn each line.** Cut anything that doesn't add information or momentum.

## Hard rules (all formats)

- **`subject.md` is the only source of truth.** Don't invent facts. Missing a detail a format needs → leave a `[TODO: …]` marker, don't fabricate. `subject.md` itself is verified against the real source in Phase 6 — so describe the real system, never a plausible-sounding paraphrase, and keep any stand-in example faithful and flagged.
- **Never surface `⚠️confidential` material** or client/internal names carried from sources.
- **Self-contained.** The reader has not seen the other formats.
- Enabled formats come from `outputs:` in config; default = all five files here.

## Adding a format

Add `<name>.md` here (purpose · structure · voice for that channel · skeleton), then add its filename to the default `outputs` list and the Phase 8 `outputs` index field in `SKILL.md`.
