# Create

One recipe per output format. Every output is generated from the subject's `subject.md` (the ≤10-minute self-contained brief) and written as its own file in the subject directory, so any single format can be regenerated or optimized alone.

Shared rules for all formats:
- **Source of truth is `subject.md`.** Don't invent facts beyond it; if a format needs detail the brief lacks, leave a `[TODO: …]` marker rather than fabricating.
- **One voice.** Read `identity:` from `{base}/config.yaml` (name, handle, tone, audience, links) and write in it. Default tone: practical, first-person, no hype.
- **Respect confidentiality.** Never surface anything marked `⚠️confidential` or any client/internal name carried from sources.
- **Self-contained.** Each piece must stand alone — the audience has not seen the others.
- Enabled formats come from `outputs:` in config; default = all five below.

---

## blog.md

Long-form post (~600–1200 words).
- Title (clear, searchable) + 1-line subtitle.
- Hook → context → the meat (the points from `subject.md`, with code blocks/examples where relevant) → takeaway.
- Markdown headings, short paragraphs. End with a one-line CTA and links from `identity`.
- Front matter block (`title`, `date`, `tags`, `slug`) at top.

## x-post.md

X/Twitter. Provide **both**:
1. A single ≤280-char post.
2. A thread (3–7 numbered tweets) for when the single post can't carry it.

Lead with the hook, one idea per tweet, last tweet = takeaway + link. **Tags:** 2–4 hashtags chosen to target the blog entry's topic (match its `tags`), plus relevant @handles when natural. List the chosen tags explicitly at the bottom under `Tags:` so they can be tuned.

## linkedin.md

LinkedIn post (~150–300 words).
- Professional but personal first line that earns the "see more" expand.
- Short lines / line breaks, 1 concrete insight, light use of 3–5 hashtags at the end.
- Soft CTA (question to the audience or link).

## youtube-scenario.md

Short shooting scenario / outline for the video.
- One line logline.
- Beat sheet: Hook (0:00–0:15) → Setup → 2–4 main beats → Payoff → Outro/CTA, with rough timestamps totaling ≤10 min.
- Per beat: what's on screen + the point to land. B-roll / screen-recording notes in italics.

## youtube-presentation.md

Slide/presentation deck for the talking-head or screencast video, derived from the scenario beats.
- One slide per `##` section: title + 3–5 bullet talking points + optional speaker note (`> note:`).
- Title slide + closing slide (CTA + links).
- **If a video/presentation skill is available** (e.g. a `video` or slide-generation skill in this plugin or the user's setup), hand this file to it to render the deck and note that in the report. Otherwise leave it as the markdown deck spec.

---

## Adding a format

Add a recipe section here and add its filename to the default `outputs` list (and to the Phase 7 `outputs` index field in `SKILL.md`). The create phase iterates over enabled outputs generically.
