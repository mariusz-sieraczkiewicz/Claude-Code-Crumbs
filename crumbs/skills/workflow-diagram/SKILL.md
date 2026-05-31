---
name: workflow-diagram
description: Generate SVG workflow diagrams from skill definitions, slash commands, or agent configurations using Graphviz DOT.
allowed-tools: Read, Write, Glob, Grep, Bash, Agent
---

# Workflow Diagram Generator

Generate workflow diagrams from Claude Code skills/commands/agents. Uses Graphviz DOT. Read `references/dot-templates.md` for all node/edge styles and color values.

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

## Phase 2: Generate DOT

Structure (define nodes BEFORE edges):
1. Graph settings (`rankdir=LR`, `splines=spline`, `nodesep=0.8`, `ranksep=1.5`)
2. Backbone step nodes (`group=backbone`, green)
3. Side element nodes (inputs/outputs/rules/agents)
4. Positioning (`rank=same` + invisible edges for above/below)
5. Backbone edges (`weight=10` — keeps steps horizontal)
6. Side edges (`weight=1`)

### Critical Rules

- **Backbone edges always `weight=10`**, side edges always `weight=1`
- **Outputs are dead ends** — never connect output to a downstream step
- **Above/below positioning**: `rank=same` + invisible edge chain sets vertical order, visible edges use `constraint=false`
- **Self-loops for verify-fix cycles** — don't split into separate steps
- **Edge labels**: use `xlabel` (prevents edge stretching)
- **Element labels**: up to 3 lines — title, purpose, file path
- **Duplicate elements** near where used rather than drawing long-distance arrows
- **3+ reference files for one step**: fold into step description text instead of separate nodes
- **Color**: local files = data (yellow), remote/network = knowledge (blue). Guideline files are data, NOT knowledge.
- **Arrow direction**: inputs/rules/services → step; step → outputs; step → subagents

## Phase 3: Render

```bash
dot -Tsvg "input.dot" -o "output.svg"
```

If overlapping: increase `ranksep`/`nodesep` or fold elements into descriptions.

## Phase 4: Verify

```bash
qlmanage -t -s 2000 -o /tmp "output.svg" 2>/dev/null
```

Read the PNG. Check: backbone horizontal, text readable, all elements present, arrows correct, no crossings. Fix and re-render if needed. Delete PNG when done.

## Output

Save to `{skill_directory}/diagrams/`:
- `{name}-overview.dot` + `.svg` — steps + flow arrows only
- `{name}-detailed.dot` + `.svg` — steps + all surrounding elements

**Overview**: green step boxes + labeled flow arrows + pattern indicators (loops, subagent icons).
**Detailed**: full diagram with all inputs, outputs, rules, subagents, 3-line labels, connections.
