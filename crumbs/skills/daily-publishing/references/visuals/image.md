# Visual: image

**Goal:** a clean, on-brand companion image that carries the subject's *idea* — the hero at the top of the post, or a second image when a distinct idea earns its own picture. → `assets/<slug>-image-<n>.<ext>` (`hero` for the mandatory top image).

## When used

- **Hero** — always, one per subject. It sits above the fold; it should read as "what this piece is about" at a glance, not as generic stock art.
- **Additional image** — only when a distinct idea in `subject.md` (a second worked example, a before/after) earns its own visual. Judgment call per the README; not required.

## Prompt shape (grounded in `subject.md`)

Build the prompt from the subject's **main message** plus its **concrete worked example** — not the title. Describe the *idea made visual*, then constrain the style:

- **Subject** — the one thing the reader should take away, expressed as a scene/metaphor or a stylized depiction of the worked example. Stay faithful to what the subject actually describes.
- **Style** — clean, modern, editorial; restrained palette (2–3 colors); generous whitespace; flat or soft-3D, not busy stock-photo realism. No logos, no watermarks, no fake UI chrome.
- **Text** — prefer no text. If a short label is essential, give the *exact* words in quotes and keep it to a few words so the model renders them crisply and correctly (see the label-proofread note in `diagram.md`).
- **Negative** — say what to avoid: clutter, gibberish text, busy backgrounds, generic "tech" clichés (glowing brains, circuit boards) unless the subject truly calls for them.

## Aspect & size

Aspect comes from where the image is used (see README table): blog hero `16:9`; x/social `1:1` or `4:5`; linkedin `1.91:1`; youtube thumbnail `16:9`. Default size `2K` (≈$0.13/image).

## Candidates & "best"

Generate `visuals.candidates` (default ~2–3) and auto-pick. **Best** = communicates the subject's idea at a glance, clean composition, restrained palette, and — if any text was requested — that text is legible and correctly spelled. Discard candidates with garbled text or cluttered framing.

## Skeleton prompt

```
A clean editorial {hero|companion} image for an article whose core message is:
"{main message from subject.md, one sentence}".

Depict: {the worked example / idea from subject.md, described as a concrete scene
or stylized representation — faithful to what the subject actually describes}.

Style: modern, minimal, editorial illustration. Restrained palette of 2–3 colors,
generous whitespace, soft flat shapes. No logos, no watermarks, no UI chrome.
{If a label is essential: Include only the text "EXACT WORDS", rendered crisply.}
Avoid: clutter, gibberish text, busy backgrounds, generic tech clichés.

Aspect {aspect}.
```
