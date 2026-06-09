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

Generation calls a paid API, so the skill is gated on a key being configured. Two backends
exist; `scripts/generate-diagram.sh` dispatches on `~/.config/workflow-diagram/config.toml`:

```toml
backend = "gemini"            # "gemini" (default) | "portkey"

[gemini]
model = "gemini-3-pro-image"

[portkey]
base_url = "https://us.aigw.galileo.roche.com/v1"   # US only (see caveats)
model    = "gpt-image-1.5-2025-12-16"
key_env  = "PORTKEY_AZURE_API_KEY"                  # secrets.env var holding the key
```

No config file (or `backend = "gemini"`) → the default Gemini backend, unchanged. API keys
live ONLY in `~/.config/workflow-diagram/secrets.env` (chmod 600, **outside this repo** —
never commit). The helper hands off to `scripts/portkey-image.py` for the portkey backend.

### Gemini backend (default)

- Key `GEMINI_API_KEY` read from `secrets.env`; an exported `$GEMINI_API_KEY` overrides the file.
- **Billing must be enabled** on the key's GCP project: the free tier for `gemini-3-pro-image`
  is `limit: 0`, so every call 429s without billing. Cost ≈ $0.13/image at 1K–2K, $0.24 at 4K.
- Model pinned to the GA id `gemini-3-pro-image` — **not** the deprecated `-preview` variant
  (shut down 2026-06-25). Full repair loop (true `--edit-image`).

### Portkey backend (Roche Galileo gateway)

- Runs `portkey-image.py` via `uv run --with portkey-ai` (no project venv needed). Key read
  from the `secrets.env` var named by `key_env` (default `PORTKEY_AZURE_API_KEY`); an exported
  env var of that name overrides the file.
- **Requires Roche VPN / Corporate Network.** Off-VPN the gateway is unreachable (calls hang).
- **US gateway only.** Image generation works on `us.aigw.galileo.roche.com`; the EU gateway's
  Azure image route is misconfigured (every image model misroutes to a non-existent
  `gpt-4o-2024-05-13`). Keep `base_url` on US until Galileo fixes EU.
- **Use `gpt-image-1.5-2025-12-16`.** `gpt-image-2` and `dall-e-3` are NOT deployed ("Unknown
  model"); Stability/Imagen render worse text. gpt-image-1.5 produces clean, correctly-labeled
  diagrams in the house style.
- **Intermittent "unknown_model" is expected and handled.** The US gateway load-balances across
  Azure backends and ~20% lack the gpt-image deployment, so a given call may 400 with
  `unknown_model` even though the model works. `portkey-image.py` retries (up to 6×) on this
  specific error — a transient routing miss, not a misconfig. You may see "routing miss …
  retrying" on stderr before success; that is normal.
- **Repair regenerates, it does not edit.** The gateway does not expose `images.edit`, so under
  the portkey backend `--edit-image` regenerates from the (fix-amended) prompt rather than
  editing the prior image. Generate more candidates to compensate.

If the helper exits non-zero for a missing/empty/placeholder key (exit 2), tell the user how
to configure it and stop — don't fail noisily.

**Portkey + VPN:** the Galileo gateway is only reachable on the Roche VPN / Corporate Network.
When the portkey backend fails with a connection or timeout error (exit 3, message mentions
"gateway unreachable"), tell the user clearly and first that **this is most likely because the
VPN is not connected** — have them connect and retry before investigating anything else.

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

Read `references/diagram-prompt.md` (structure) **and** `references/diagram-style.md` (look).
Translate the Phase 1 extraction into two prompts:

- **overview** — concept altitude (~5–8 step nodes, flow arrows, pattern indicators).
- **detailed** — full completeness (every step + every physical element, exact labels).

Apply the arrow semantics and density rules from `diagram-prompt.md`. Then append the
ready-to-paste **Style Block** from `diagram-style.md` (Section 9) verbatim to every prompt —
it carries the locked "Internal Workflow" house style (white canvas, bold title + subtitle,
numbered green step boxes with a short description line, orthogonal right-angle gray routing,
the color-matched multi-arrow feed bundles, tilted blue decision node, stacked-card multi-file
boxes, dashed bypass/self-loop arrows). Write each prompt to its own temp file (e.g. `/tmp/wfd-overview.txt`,
`/tmp/wfd-detailed.txt`) so long multi-line prompts need no shell escaping.

## Phase 3: Generate candidates → auto-pick

For each diagram (overview, detailed), call the helper **N times** (~2–3) into `-1`, `-2`, …
filenames. **Always generate at `--size 1K`** — pass it on every call (generate and repair
alike). 1K is the cheapest tier for this model (same token cost as 2K but smaller files) and
is sharp enough for these label-driven diagrams. Only override to `2K`/`4K` if the user
explicitly asks for a larger image.

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
- **Style** — matches the house style in `references/diagram-style.md` (Section 8 checklist):
  white canvas, bold title + gray subtitle, numbered green step boxes with a short description
  line, exact palette, orthogonal right-angle gray routing, color-matched feed bundles, tilted
  blue decision node, stacked-card multi-file boxes, dashed bypass/self-loop arrows.

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
