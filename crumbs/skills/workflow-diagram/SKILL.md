---
name: workflow-diagram
description: Generate workflow diagram images from skill definitions, slash commands, or agent configurations using Gemini 3 Pro Image (Nano Banana Pro).
allowed-tools: Read, Write, Glob, Grep, Bash, Agent
---

# Workflow Diagram Generator

Generate workflow diagrams from Claude Code skills/commands/agents as **images**, via
Gemini 3 Pro Image (Nano Banana Pro). Read `references/diagram-prompt.md` for how to turn
the extracted workflow into a grounded prompt (element colors, arrow semantics, skeletons).

The model renders genuine workflow graphs with crisp labels, but only when grounded in the
**real** steps and elements — so extraction (Phase 1) and the self-check/repair loop
(Phase 4) carry the accuracy. The picture is generated from that extraction, never from the
skill's name alone.

## Setup (read once)

Generation calls a paid API, so the skill is gated on a key being configured:

- The key is read by `scripts/generate-diagram.sh` from `~/.config/workflow-diagram/secrets.env`
  (`GEMINI_API_KEY=...`, chmod 600, **outside this repo** — never commit it). An exported
  `$GEMINI_API_KEY` overrides the file.
- **Billing must be enabled** on the key's GCP project: the free tier for `gemini-3-pro-image`
  is `limit: 0`, so every call 429s without billing. Cost ≈ $0.13/image at 1K–2K, $0.24 at 4K.
- Model is pinned to the GA id `gemini-3-pro-image` — **not** the deprecated `-preview`
  variant (shut down 2026-06-25). The helper hardcodes this; don't parameterize it.

If the helper exits non-zero for a missing/empty/placeholder key (exit 2), tell the user how
to configure it and stop — don't fail noisily.

## Input

Accept skill path/name or multiple space-separated names. Resolution:
1. `.claude/skills/{name}/SKILL.md` (project)
2. `.claude/commands/{name}.md` (project)
3. `~/.claude/skills/{name}/SKILL.md` or `~/.claude/commands/{name}.md` (user-level)
4. Direct path

Read resolved files. If a skill references subagents, read those too.

## Phase 1: Extract Workflow

Extract **steps** (named with verbs: "Read", "Generate", "Verify") and **per-step elements**.

Physicality test — only draw elements you can point to a file path, URL, or named system:

| Element | Qualifies | Does NOT |
|---------|-----------|----------|
| Input/Output | Real files (`AED_*.md`, `section1.md`) | In-memory context |
| Rules | Guideline files (`DAC_PATTERNS.md`) | Internal prompt principles |
| Service | MCP servers, external CLIs, APIs | Built-in tools (Read/Write) |
| Subagent | Named spawned agents | — |

Non-physical things → step description text or edge labels.

This extraction is the **ground truth** the rest of the run is checked against — capture
exact labels (file paths, agent names, service names), the step order, and which element
attaches to which step.

## Phase 2: Build the prompts

Read `references/diagram-prompt.md`. Translate the Phase 1 extraction into two prompts:

- **overview** — concept altitude (~5–8 step nodes, flow arrows, pattern indicators).
- **detailed** — full completeness (every step + every physical element, exact labels).

Apply the element-color legend, the explicit arrow semantics, and the density rules from the
reference. Write each prompt to its own temp file (e.g. `/tmp/wfd-overview.txt`,
`/tmp/wfd-detailed.txt`) so long multi-line prompts need no shell escaping.

## Phase 3: Generate candidates → auto-pick

For each diagram (overview, detailed), call the helper **N times** (~2–3) into `-1`, `-2`, …
filenames:

```bash
scripts/generate-diagram.sh \
  --prompt-file /tmp/wfd-overview.txt \
  --out "{skill_dir}/diagrams/{name}-overview-1.jpg" \
  --aspect 16:9 --size 1K
```

The helper prints the **final saved path** on stdout (extension may be `.jpg`/`.png` per the
returned bytes — trust it) and usage/cost on stderr. Read each candidate and **auto-pick the
best** (every real node present, no invented nodes, arrow directions correct, labels legible
and correctly spelled, clean layout). No interactive prompt. Discard the rest.

Helper exit codes: 0 = saved; 2 = not configured → stop per Setup; 3 = API error (e.g. 429) →
skip that candidate (if every candidate for a diagram fails, report it and move on).

## Phase 4: Self-check & repair loop

For each picked diagram, **read the image** and check it against the Phase 1 ground truth:

- **Completeness** — every real step and element is present; nothing important missing.
- **No fabrication** — no invented nodes, arrows, or labels that aren't in the extraction.
- **Labels** — every label is spelled correctly and matches the exact name/path from Phase 1.
- **Arrows** — directions obey the stated semantics (flow L→R, inputs into steps, outputs are
  dead ends, subagents above, self-loop for verify-fix cycles).
- **Legibility** — text readable, backbone horizontal, minimal/no crossings.

If anything is wrong, **repair with an editing re-prompt** (don't regenerate from scratch —
you'd lose the good composition). Write a surgical instruction to a temp file and feed the
picked image back:

```bash
scripts/generate-diagram.sh \
  --prompt-file /tmp/wfd-fix.txt \
  --edit-image "{skill_dir}/diagrams/{name}-detailed-2.jpg" \
  --out "{skill_dir}/diagrams/{name}-detailed-fixed.jpg" \
  --aspect 16:9 --size 1K
```

Example fix prompt: *"Change the label 'invariants cleners' to 'invariants'. Keep everything
else — layout, colors, every other label, all arrows — exactly identical."*

Re-read the result and repeat. **Max 3 repair iterations** per diagram; if issues remain after
3, keep the best version and report the residual problems plainly rather than looping forever.

## Output

Save the final picked (and repaired) images to `{skill_directory}/diagrams/`:
- `{name}-overview.<ext>` — steps + flow arrows + pattern indicators (loops, subagent markers).
- `{name}-detailed.<ext>` — full diagram: all steps + inputs, outputs, rules, services,
  subagents, user interactions, with exact labels.

`<ext>` is whatever the model returned (`.jpg` or `.png`). Report the saved paths, the
candidate/repair counts, approximate cost, and any residual issues the repair loop couldn't fix.
