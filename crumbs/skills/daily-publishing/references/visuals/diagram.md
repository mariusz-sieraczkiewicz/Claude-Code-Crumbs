# Visual: diagram

**Goal:** a *correct* dependency/concept diagram — real structure from the subject, not decoration. Image models render genuine dependency graphs with crisp labels (unlike diagrams-as-code, which auto-layout into "functional but ugly"); the work is making it accurate, not pretty. → `assets/<slug>-diagram-<n>.<ext>`.

## When used

Add a diagram when the subject **turns on structure or relationships** — how parts depend on, feed into, or sequence after one another. If the subject is a single linear idea, skip it; a wrong-altitude diagram is worse than none.

## Grounding (mandatory)

Derive every node and edge from the **real structure in `subject.md`** (verified against source in Phase 6). Each node is a real component/step/concept the subject describes; each edge is a real relationship. **No decorative nodes, no invented arrows.** If you can't name what a node and an arrow mean from the subject, it doesn't belong.

## Explicit arrow semantics

State in the prompt **what an arrow means and its direction** — the model honors it. Don't leave it implicit. Examples:

- Dependency: *"an arrow A→B means A depends on B; all arrows point up toward the foundation."*
- Flow: *"an arrow A→B means data/control flows from A to B, left to right."*

Pick one meaning and keep it consistent across every edge in the diagram.

## Density & altitude (~4–6 nodes)

Keep it at **concept altitude: roughly 4–6 nodes.** Push file-level detail into the prose, not the picture. Lesson from testing: a "lighthouses" diagram drawn with all five model files + the engine was *correct but too detailed*; the 4-node version (Agent loop → Plan → Problem model → Lighthouses) was the right altitude. If the structure genuinely needs more, group detail into a named node rather than exploding every file.

## Generate N, auto-pick

Generate `visuals.candidates` (default ~2–3) and auto-pick the best — composition non-deterministic, so candidates differ. **Best** = correct structure (nodes/edges match the subject), arrow direction obeys the stated semantics, labels legible and correctly spelled, uncluttered layout.

## Label proofread (do this)

Image models occasionally garble ~1 label on a *complex* diagram (observed: "invariants" → "invariants cleners"). Simpler diagram = lower risk — another reason to hold ~4–6 nodes. After picking, **read every label.** If one is wrong, fix it with an **editing re-prompt that preserves the composition** — feed the chosen image back with: *"Change the label 'X' to 'Y'. Keep everything else — layout, colors, all other labels — identical."* Don't regenerate from scratch (you'll lose the good composition).

## Aspect & size

Inline blog/doc diagrams: `16:9`. Default size `2K`.

## Skeleton prompt

```
A clean concept diagram illustrating the structure described below.

Nodes (use these exact labels, no others):
- {Node 1}
- {Node 2}
- {Node 3}
- {Node 4}            # keep to ~4–6 nodes

Edges and their meaning:
- An arrow A→B means "A depends on B". All arrows point upward.
- {Node 1} → {Node 2}
- {Node 2} → {Node 3}
- {Node 3} → {Node 4}

Style: minimal, editorial, flat. Clear sans-serif labels, generous spacing,
restrained palette (2–3 colors), no clutter, no extra decorative elements.
Spell every label exactly as written above.

Aspect {aspect}.
```
