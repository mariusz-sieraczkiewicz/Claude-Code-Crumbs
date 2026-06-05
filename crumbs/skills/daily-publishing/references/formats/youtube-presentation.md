# Format: youtube-presentation

**Goal:** the slide deck for the video, derived from the scenario's beats. Markdown deck spec, ready to render. → `youtube-presentation.md`

## Shape

- **One slide per `##` section**, in the scenario's beat order.
- **Title slide** (video title + subtitle/identity) and **closing slide** (CTA + links) bookend it.
- Per content slide: a short title + **3–5 bullet talking points** (phrases, not paragraphs) + optional speaker note as `> note:`.

## Writing rules

- Slides carry *anchors*, not the script — the spoken words live in `youtube-scenario.md`. One idea per slide.
- ≤6 words per bullet where possible; no full sentences on the slide.
- Note where a slide should show code/a diagram/a demo (`> show: …`) rather than pasting walls of text.
- Slide count roughly tracks beats — don't exceed ~1 slide per 30–45s of video.

## Render hand-off

If a video/slide-generation skill is available (a `video` skill, a deck renderer, or marp/reveal in the user's setup), pass this file to it to produce the actual deck and note that in the run report. Otherwise leave it as this markdown spec.

## Skeleton

```markdown
## {Video Title}
{subtitle} · {identity.name}

## {Beat 1 title}
- point
- point
> note: ...

## {Beat 2 title}
- point
> show: {code/diagram/demo}

## Thanks
- {CTA}
- {links}
```
