# Diagram Prompt Reference

How to turn the Phase 1 extraction into a grounded prompt for Gemini 3 Pro Image
(Nano Banana Pro). The image model renders genuine workflow graphs with crisp labels —
but only when the prompt names the **real** nodes, edges, and arrow meanings. Prompted
loosely, it draws a pretty, wrong picture. The whole job here is **accuracy**, not polish.

Two diagrams come out of every run, built from the same extraction at different altitude:

- **overview** — concept altitude (~5–8 step nodes + flow arrows + pattern indicators).
- **detailed** — full completeness: every step plus every surrounding element (inputs,
  outputs, rules, services, subagents, user interactions) with exact file-path labels.

The detailed diagram is the hard case for an image model (many exact labels). Lean on
grounding + N candidates + the self-check/repair loop in `SKILL.md` to keep it correct.

## Element types → visual style

Carry the original six-type color legend into the prompt as **style instructions** (the
model has no node "types" — you describe each node's color and role in words). Keep the
palette consistent across both diagrams.

| Element | Role in the prompt | Fill | Border | Font |
|---------|--------------------|------|--------|------|
| Step (process) | backbone boxes, the spine of the flow | `#c8e6c9` green | `#388e3c` | `#1b5e20` |
| Data (file on disk: input, output, rule) | feeds or is produced by a step | `#fff9c4` yellow | `#f9a825` | `#f57f17` |
| Subagent (named spawned agent) | delegated work above a step | `#ffe0b2` peach | `#e65100` | `#bf360c` |
| External knowledge (remote/network only) | blue reference source | `#e3f2fd` blue | `#1976d2` | `#0d47a1` |
| External service (MCP, external CLI/API) | lavender service node | `#e1bee7` lavender | `#7b1fa2` | `#4a148c` |
| User interaction | light-blue human-in-the-loop node | `#bbdefb` light blue | `#1565c0` | `#0d47a1` |

State the colors explicitly in the prompt (e.g. *"step boxes are green (#c8e6c9 fill,
#388e3c border); file/data boxes are yellow; subagent boxes are peach; …"*). The model
honors named hex colors well enough to keep the legend readable.

## Arrow semantics (state them explicitly)

The model honors arrow direction **only if you spell it out**. Pick the meanings below and
write them into every prompt verbatim — don't leave direction implicit:

- **Backbone flow:** *"the green step boxes form a left-to-right backbone; an arrow
  step A → step B means the workflow proceeds from A to B."* This is the dominant axis —
  say the backbone runs horizontally, left to right.
- **Inputs / rules / services → step:** *"an arrow from a yellow/lavender/blue box into a
  step means that box feeds the step."*
- **Step → output:** *"an arrow from a step to a yellow box below/after it means the step
  produces that file; output boxes are dead ends — no arrow leaves an output."*
- **Step → subagent:** *"an arrow from a step up to a peach box means the step delegates to
  that subagent."*
- **Self-loop (verify-fix cycle):** *"a curved arrow from a step back to itself, dashed,
  labeled with the cycle, means the step repeats until it passes — do not split it into
  two boxes."*

Keep one consistent meaning per arrow style across the whole diagram.

## Labels (exact, and proofread after)

- Use the **exact file paths and names** from the Phase 1 extraction as node labels
  (`AED_*.md`, `subject.md`, `globaljira MCP`). Tell the model to render them verbatim.
- Each node label may carry up to **3 short lines**: title, one-line purpose, file path.
- Image models occasionally garble ~1 label on a dense diagram (observed elsewhere:
  "invariants" → "invariants cleners"). The **detailed** diagram is most at risk. The
  `SKILL.md` self-check/repair loop exists for exactly this — read every label back and
  fix wrong ones with an editing re-prompt (see below). Simpler picture = lower risk.

## Density & altitude

- **overview:** ~5–8 step nodes, flow arrows, and pattern indicators only (loops, a
  parallel-work cluster, subagent markers). Fold inputs/outputs/rules into short edge or
  step captions instead of separate boxes.
- **detailed:** all steps + every physical element from Phase 1. If a step has 3+ reference
  files, group them into one "rules" box rather than drawing a box per file. Prefer
  duplicating a shared element near each place it's used over one long-distance arrow.

## Layout & composition

- Horizontal backbone, left to right; surrounding elements sit above (subagents, services,
  knowledge, user) or below (inputs, rules) the step they attach to.
- Minimal, editorial, flat. Generous spacing, no clutter, no decorative extras, no fake UI
  chrome, no logos/watermarks. The restrained palette is the six legend colors above.
- Outputs are visual dead ends. No arrow crosses through a box. Avoid arrow crossings where
  the layout allows.

## Generate N, auto-pick

Generate N candidates (N from the skill default, ~2–3) into `-1`, `-2`, … filenames, then
auto-pick the best — no interactive prompt. **Best** = every real node present, no invented
nodes, arrow directions obey the stated semantics, labels legible and correctly spelled,
clean uncluttered layout, backbone reads left-to-right.

## Repair via editing re-prompt (don't regenerate from scratch)

When the self-check finds a wrong label or a small structural slip, fix it by feeding the
chosen image back with `--edit-image` and a **surgical** instruction that preserves the
composition:

> *"Change the label 'X' to 'Y'. Keep everything else — layout, colors, every other label,
> all arrows — exactly identical."*

> *"Add an arrow from the green 'Generate' box to the green 'Verify' box, pointing right.
> Change nothing else."*

Regenerating from scratch loses the good composition; edit instead. Loop per `SKILL.md`.

## Skeleton prompt — overview

```
A clean, editorial workflow diagram. A horizontal backbone of green step boxes runs
left to right; an arrow from step A to step B means the workflow proceeds A → B.

Steps, in order (use these exact labels, green boxes — #c8e6c9 fill, #388e3c border):
1. {Step 1}
2. {Step 2}
3. {Step 3}
   ...                         # ~5–8 steps

Flow notes (render as short labels on the arrows, not extra boxes):
- {A → B}: {what passes between them}
- {Step N} repeats until it passes: draw a dashed curved arrow from {Step N} back to
  itself, labeled "{cycle}". Do not split it into two boxes.

Style: minimal, flat, editorial. Generous spacing, restrained palette, clear sans-serif
labels rendered exactly as written, no clutter, no decorative extras, no UI chrome.

Aspect {aspect}.
```

## Skeleton prompt — detailed

```
A clean, editorial workflow diagram. A horizontal backbone of green step boxes runs
left to right (an arrow step A → step B means the workflow proceeds A → B). Surrounding
elements attach above or below the step they belong to.

Steps (green boxes — #c8e6c9 fill, #388e3c border), left to right:
1. {Step 1}
2. {Step 2}
   ...

Elements attached to each step (use these EXACT labels; render every label verbatim):
- Inputs/rules (yellow boxes, below the step, arrow pointing INTO the step):
    {Step 1} ← {file label, e.g. AED_*.md}
- Outputs (yellow boxes, after the step, arrow FROM step into the box; outputs are
  dead ends — no arrow leaves them):
    {Step 2} → {output file label}
- Subagents (peach boxes, above the step, arrow from step UP to the agent):
    {Step 3} → {agent label} (subagent)
- Services (lavender boxes) / external knowledge (blue boxes) / user interaction
  (light-blue boxes): attach to their step with an arrow into the step.

Arrow meaning is fixed: into a step = feeds it; step to an output = produces it; step to
a peach box = delegates to that subagent; a dashed self-loop = a verify→fix cycle.

Colors: steps green; files/data yellow (#fff9c4); subagents peach (#ffe0b2); external
knowledge blue (#e3f2fd); external services lavender (#e1bee7); user light blue (#bbdefb).

Style: minimal, flat, editorial. Generous spacing, no clutter, no decorative extras, no
UI chrome, no logos. Spell every label exactly as written above.

Aspect {aspect}.
```
