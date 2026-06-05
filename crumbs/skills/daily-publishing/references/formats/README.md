# Formats — shared voice

Each output format has its own file so it can be tuned and developed independently. Phase 6 reads this once, then for each enabled output applies its format file. Every format is written **from the subject's `subject.md`** and saved as its own file in the subject directory.

## Voice

Read `identity:` from `{base}/config.yaml` (name, handles, links, tone, audience) and write in it. Defaults if unset:
- **First person, practical, specific.** You did the thing — say so plainly.
- **No hype.** Ban: "game-changer", "revolutionary", "unlock", "in today's fast-paced world", "leverage" (as a verb), "delve", emoji-as-bullets, em-dash-heavy AI cadence.
- **Concrete over abstract.** Real numbers, real names of tools, real code. One idea, well lit, beats five gestured at.
- **Earn each line.** Cut anything that doesn't add information or momentum.

## Hard rules (all formats)

- **`subject.md` is the only source of truth.** Don't invent facts. Missing a detail a format needs → leave a `[TODO: …]` marker, don't fabricate.
- **Never surface `⚠️confidential` material** or client/internal names carried from sources.
- **Self-contained.** The reader has not seen the other formats.
- Enabled formats come from `outputs:` in config; default = all five files here.

## Adding a format

Add `<name>.md` here (purpose · structure · voice for that channel · skeleton), then add its filename to the default `outputs` list and the Phase 7 `outputs` index field in `SKILL.md`.
