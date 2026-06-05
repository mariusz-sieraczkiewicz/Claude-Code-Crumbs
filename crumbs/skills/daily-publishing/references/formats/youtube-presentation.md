# Format: youtube-presentation

**Goal:** the slide deck for the video, derived from the scenario's main points. Markdown deck spec, ready to render. → `youtube-presentation.md`

## Shape

- **One slide per `##` section**, in the scenario's main-point order.
- **Title slide** (video title + subtitle/identity) and **closing slide** (CTA + links) bookend it.
- Per content slide: a short title + **3–5 bullet talking points** (phrases, not paragraphs) + optional speaker note as `> note:`.

## Writing rules

- Slides carry *anchors*, not the script — the spoken words live in `youtube-scenario.md`. One idea per slide.
- ≤6 words per bullet where possible; no full sentences on the slide.
- Note where a slide should show code/a diagram/a demo (`> show: …`) rather than pasting walls of text.
- Slide count roughly tracks the main points — don't exceed ~1 slide per 30–45s of video.

## Render hand-off

If `video_tool:` is set in `{base}/config.yaml`, hand this file (plus `youtube-scenario.md`) to that tool to produce the actual presentation/video and note it in the run report. Candidate tools and how each consumes this deck are documented in `../video-tools.md`. Otherwise leave it as this markdown spec.

## Skeleton

```markdown
## {Video Title}
{subtitle} · {identity.name}

## {Point 1 title}
- point
- point
> note: ...

## {Point 2 title}
- point
> show: {code/diagram/demo}

## Thanks
- {CTA}
- {links}
```
