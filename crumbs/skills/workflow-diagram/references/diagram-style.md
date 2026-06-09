# Diagram Visual Style — "Internal Workflow" house style

The locked visual style for workflow diagrams. `diagram-prompt.md` covers **structure**
(which nodes/edges exist, arrow *semantics*, grounding). This file covers **appearance**
(palette, fonts, box anatomy, arrow rendering, layout) so every diagram comes out looking
like it belongs to the same set.

Distilled from two reference renders that defined the look:
- **Overall styling** (canvas, palette, title block, element rendering, colored feed-arrows,
  tilted decision node, fonts, layout) — from the *005 Technical Assessment* render.
- **Step-box descriptions** (a numbered title plus a short plain-language line of what the
  step does — concise, not verbose) — from the *002 Elaborate Requirements* render.

When building a prompt in Phase 2, apply `diagram-prompt.md` for the structure **and** this
file for the look. The ready-to-paste **Style Block** at the bottom carries the whole look in
one chunk — append it to every prompt.

---

## 1. Canvas & title block

- **Background:** flat **white** (`#FFFFFF`) across the whole canvas. No gray, no gradient,
  no texture, no border frame. (The reference render is white — an earlier draft of this spec
  wrongly specified light gray; white is correct.)
- **Title:** top-left, heavy **bold** neo-grotesque sans-serif (Helvetica / Arial / Inter
  feel), large (~32–40px-equivalent), near-black `#1A1A1A`. Format:
  `NNN Command Name — Internal Workflow` (use an em-dash `—`, not a hyphen).
- **Subtitle:** directly under the title, regular weight, ~40–50% of the title size, medium
  gray `#555555`. One line of provenance, e.g. `delivery pipeline step | kiakia-ai-assisted`.
- Title block is left-aligned to the diagram's left margin; the backbone starts below it.

---

## 2. Step boxes (the green backbone) — title + concise description

Each step is a **rounded rectangle**, green fill `#C8E6C9`, medium-green border `#43A047`
(~2px), with **two stacked text zones**:

1. **Title line** — bold, dark `#1B5E20`/near-black. Prefix with an ordinal so order is
   unambiguous: `1. Load Inputs`, `2. Preanalysis Scan`, … (numbered preferred; `STEP A/B/C`
   is an acceptable alternative but pick **one** scheme per diagram).
2. **Description** — directly below the title, **regular** weight, smaller, dark gray. One
   short plain-language line (occasionally two) saying what the step *does*. This is the
   borrowed "002" trait: **concise, not verbose.**
   - Budget: **≤ 12 words / ≤ 2 lines.** If it needs more, it's two steps.
   - May use a light inline arrow to show a decision inside the step, e.g.
     `score 0–4 criteria → Fast Track or Guided`.
   - Name real artifacts in the description when natural (`reads business-intent.yaml and
     req-template.md`) — but the artifact *boxes* (Section 4) are still the source of truth.
- Text is centered in the box. Boxes in a row share the same height; widths may vary slightly
  with content. Flat fill, no drop shadow, no gradient.

---

## 3. Element legend (fill / border / text)

One color = one role. Keep it identical across every diagram in a set.

| Element | Role | Fill | Border | Text |
|---------|------|------|--------|------|
| **Step** (process) | green backbone box | `#C8E6C9` | `#43A047` | `#1B5E20` |
| **Data** (input / output / rule file) | yellow file box | `#FFF9C4` | `#F9A825` | `#5D4037` |
| **External service** (MCP / CLI / API) | lavender service box | `#E1BEE7` | `#8E24AA` | `#4A148C` |
| **Subagent** (named spawned agent) | warm-peach box | `#FFCC80` | `#EF6C00` | `#BF360C` |
| **User interaction** (human gate) | light-blue annotation box | `#BBDEFB` | `#1E88E5` | `#0D47A1` |
| **Decision** (branch/mode select) | tilted medium-blue box | `#64B5F6` | `#1976D2` | `#0D47A1` |

All boxes are rounded rectangles **except** Decision (Section 5). Borders ~2px, flat fills.

---

## 4. Data boxes & the stacked-card multi-file treatment

- A single file → one yellow rounded box, label = exact filename (`technical-assessment.yaml`).
- **Multiple files in one box** → render a **stacked-card** motif: 2–3 yellow rectangles
  offset a few px down-right behind the front card, so it reads as "a stack of files." Put the
  filename list (one per line) on the front card. Use this instead of N separate boxes when a
  step reads/writes 3+ files (e.g. an input bundle, an artefact chain).
- Inputs/rules sit **below** their step; outputs sit **below/after** their step. Outputs are
  **dead ends** — no arrow leaves an output box.

---

## 5. Decision node (distinct shape)

A branch/mode-selection point is drawn as a **slightly rotated (tilted) rounded rectangle**
in medium blue (`#64B5F6` fill, `#1976D2` border) — visually distinct from every axis-aligned
box so a decision is spotted instantly. Two short lines: a bold title and the options, e.g.
`Mode Decision` / `Fast Track / Guided`. Branch arrows leave the decision (or its owning step)
labeled with each condition (see Section 6).

---

## 6. Arrow system (the signature look)

Four arrow kinds, each visually distinct. Getting these right *is* the house style.

**All gray connectors are routed ORTHOGONALLY** — pure horizontal and vertical segments with
**90° (right-angle) corners**, like a PCB / flowchart. **No diagonal lines, no sweeping
curves** on backbone or routing — this includes annotation/leader lines (Section below).
Every line is a run of horizontal and vertical segments only. (The dashed *self-loop* curl in
#4 is the single exception.) This "rectangular" routing is part of the look — get it right.

1. **Backbone flow** — solid **medium-gray** (`#616161`, ~2.5px) with a single filled
   arrowhead, horizontal, left→right between step boxes. `A → B` = flow proceeds A then B.
   Straight horizontal segment between boxes in the same row.
2. **Colored feed bundles** — when a Data / Service / Subagent box feeds a step, draw the
   connector **in the source box's own color** (yellow-amber for data, purple for service,
   orange for subagent), and render it as a **bundle of exactly 3 short thin parallel arrows**
   (always 3 — not one fat arrow, not 4 or 5), evenly spaced and **vertical**, pointing
   **into** the step. Outputs use the same 3-arrow colored bundle pointing **from** the step
   **into** the (dead-end) output box. This color-matched 3-arrow bundle is the most
   recognizable trait of the style — use it (always 3 arrows) everywhere a box feeds or is
   produced by a step.
3. **Dashed bypass branch** — a "skip / fast-track / alternate" path is a **dashed gray**
   arrow **routed orthogonally** (right-angle elbows) around the steps it skips, labeled with
   the condition (e.g. `Fast Track (accept)`). Normal taken branches stay solid gray with a
   condition label (e.g. `Guided`, `1–4 criteria strong`, `0 criteria → ESCALATE (stop)`).
4. **Dashed self-loop** — a verify→fix / retry cycle is a short **dashed gray** curved arrow
   from a step back onto itself, with a small label beside it (`fix & re-verify`,
   `Refine & re-verify until clean`, `fix retries ×3`). **Never** split a cycle into two boxes.

**Annotation connectors:** a User-interaction (light-blue) box attaches to its step with a
**thin plain gray line, no arrowhead** — it annotates the step, it isn't flow. This line is
**orthogonal too** — a straight vertical drop (or a right-angle elbow), **never a diagonal**.
Like every gray connector, it runs only horizontal/vertical.

**Row-wrap connector:** when the backbone wraps to a new row, join end-of-row to start-of-
next-row with a single gray **orthogonal elbow** connector (right → down → left, 90° corners
— not a curve, not a diagonal). Keep it clear of boxes; no arrow crosses through a box.

---

## 7. Layout & composition

- Horizontal backbone, **left→right**, wrapping into 2–3 rows for long flows (≤ ~6 steps per
  row). Read order: row 1 L→R, then row 2 L→R, etc.
- Surrounding elements sit **above** the step (services, subagents, user-interaction,
  decisions) or **below** it (inputs, outputs, rules).
- A subagent or service that runs **once** is drawn **once**, near its step.
- Minimal, editorial, flat: generous spacing, no clutter, no decorative extras, no UI chrome,
  no logos, no watermarks, no drop shadows (the stacked-card offset is the only "depth" cue).
- Avoid arrow crossings where layout allows. Outputs are visual dead ends.

---

## 8. Style self-check (add to Phase 4)

On top of the structural checks in `SKILL.md`, verify the *look*:
- **White** canvas; bold title + gray subtitle, top-left, em-dash.
- Steps: green, numbered title + a short (≤2-line) description; one numbering scheme.
- Palette matches Section 3 exactly (no off-palette colors).
- Feed arrows are **color-matched bundles of exactly 3** parallel arrows (yellow/purple/
  orange) — count them; not 1, 4, or 5. Backbone is gray.
- **Every** gray line is **orthogonal** (horizontal/vertical only, right-angle elbows) — no
  diagonals, no curves (except the dashed self-loop curl). This includes annotation/leader
  lines to user-interaction boxes — they are vertical drops or elbows, never diagonal.
- Decision is a **tilted blue** box; bypass branch is **dashed gray**; verify-loops are
  **dashed self-loops** (not duplicate boxes); user-interaction connectors are plain orthogonal
  lines (no arrowhead).
- Multi-file boxes use the **stacked-card** motif.
Repair off-style renders with a surgical `--edit-image` re-prompt, same as label fixes.

---

## 9. Style Block (paste verbatim into every prompt)

```
VISUAL STYLE — "Internal Workflow" house style. Follow exactly.

Canvas: flat WHITE background (#FFFFFF). No gray, no gradient, no texture, no border frame.
Title (top-left, heavy bold sans-serif, near-black #1A1A1A): "{NNN Command Name} — Internal
Workflow". Subtitle directly below, regular weight, gray #555555: "{provenance line}".
Clean neo-grotesque sans-serif (Helvetica/Arial/Inter) throughout; no serifs; no shadows.

STEP boxes (green backbone): rounded rectangles, fill #C8E6C9, border #43A047, left-to-right.
Each shows a BOLD numbered title ("1. Load Inputs") and, below it, ONE short regular-weight
description line (≤12 words) of what the step does. Backbone wraps into 2–3 rows for long
flows (≤6 steps/row); join rows with a single gray orthogonal elbow connector.

ELEMENT COLORS (one role per color, rounded boxes unless noted):
- Data / file (input, output, rule): fill #FFF9C4, border #F9A825 — BELOW the step.
- External service (MCP/CLI/API): fill #E1BEE7, border #8E24AA — ABOVE the step.
- Subagent (named agent): fill #FFCC80, border #EF6C00 — ABOVE the step.
- User interaction (human gate): fill #BBDEFB, border #1E88E5 — annotation, attached by a
  thin plain gray line with NO arrowhead, routed ORTHOGONALLY (a straight vertical drop or a
  right-angle elbow) — NEVER a diagonal line.
- Decision (branch/mode select): a slightly ROTATED (tilted) blue rounded box, fill #64B5F6,
  border #1976D2, with a bold title + options line.

MULTI-FILE: when a box holds 3+ files, draw a stacked-card motif (2–3 offset rectangles
behind the front card) with the filenames listed on the front card.

ARROWS — ALL gray connectors are routed ORTHOGONALLY: pure horizontal/vertical segments with
90° right-angle corners (PCB/flowchart style). NO diagonal lines and NO sweeping curves on the
backbone, any routing, OR annotation/leader lines (the only curved line is the dashed self-loop
curl below). Four kinds:
- Backbone flow: solid medium-gray (#616161) arrow, single arrowhead, straight horizontal L→R
  between boxes in a row.
- Row-wrap: join end-of-row to start-of-next-row with ONE gray orthogonal elbow (right → down
  → left, 90° corners). No arrow crosses through a box.
- Feed arrows: when a data/service/subagent box feeds a step (or a step produces an output),
  draw a BUNDLE OF EXACTLY 3 SHORT THIN PARALLEL VERTICAL ARROWS IN THE SOURCE BOX'S OWN COLOR
  (always 3 — never 1, 4, or 5; yellow-amber for data, purple for service, orange for
  subagent), pointing into the step (or from the step into a dead-end output box). Outputs
  never have an outgoing arrow.
- Bypass/alternate branch: a DASHED gray arrow routed ORTHOGONALLY (right-angle elbows) around
  skipped steps, labeled with its condition (e.g. "Fast Track (accept)"). Taken branches:
  solid gray with a condition label.
- Verify→fix / retry cycle: a small DASHED gray curved SELF-LOOP on the step, label beside it
  (e.g. "fix & re-verify"); never split a cycle into two boxes.

Style: minimal, flat, editorial. Generous spacing; no clutter, no UI chrome, no logos, no
watermarks. Spell every label exactly as given. Aspect {aspect}.
```
