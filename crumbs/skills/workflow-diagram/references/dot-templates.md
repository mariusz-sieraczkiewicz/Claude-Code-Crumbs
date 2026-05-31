# Graphviz DOT Templates Reference

Node/edge styles and patterns for workflow diagrams. Use these templates in every generated `.dot` file.

## Graph Preamble (paste at top of every .dot file)

```dot
digraph workflow {
    rankdir=LR
    splines=spline
    nodesep=0.8
    ranksep=1.5
    compound=true
    fontname="Helvetica"

    // Global defaults
    node [shape=box, style="filled,rounded", fontname="Helvetica", fontsize=11, margin="0.3,0.2"]
    edge [fontname="Helvetica", fontsize=9]
}
```

**Why these settings:**
- `rankdir=LR` — left-to-right flow (backbone is horizontal)
- `splines=spline` — smooth curves. Do NOT use `ortho` (it drops edge labels)
- `nodesep=0.8` — vertical spacing between nodes in the same rank
- `ranksep=1.5` — horizontal spacing between ranks (columns)
- `compound=true` — allows edges to/from subgraph clusters

## Node Styles by Element Type

### Process Step (green)
```dot
step1 [label="Read Sources\nLoad AED, template, guidelines\nAED is primary source"
       fillcolor="#c8e6c9" color="#388e3c" fontcolor="#1b5e20"
       penwidth=2 style="filled,rounded,bold" group=backbone]
```
Always include `group=backbone` on step nodes to keep them horizontally aligned.

### Data Element — inputs, outputs, rules, any file on disk (yellow)
```dot
aed [label="AED Chapters\nglobal clinical evidence\nAED_*.md"
     fillcolor="#fff9c4" color="#f9a825" fontcolor="#f57f17"
     style="filled,rounded"]
```

### Subagent (peach/orange)
```dot
verifier [label="Verifier Agent\nindependent compliance\nchecker (subagent)"
          fillcolor="#ffe0b2" color="#e65100" fontcolor="#bf360c"
          penwidth=2 style="filled,rounded,bold"]
```

### External Knowledge — ONLY remote/network sources (blue)
```dot
confluence [label="Architecture Docs\nlatest design decisions\nconfluence.company.com/arch"
            fillcolor="#e3f2fd" color="#1976d2" fontcolor="#0d47a1"
            style="filled,rounded"]
```

### External Service — MCP servers, external CLIs (lavender)
```dot
jira [label="JIRA\ncreate and link tasks\nglobaljira MCP"
      fillcolor="#e1bee7" color="#7b1fa2" fontcolor="#4a148c"
      style="filled,rounded"]
```

### User Interaction (light blue)
```dot
reviewer [label="User\narchitect review\ninteractive approval"
          fillcolor="#bbdefb" color="#1565c0" fontcolor="#0d47a1"
          style="filled,rounded"]
```

## Edge Patterns

### Backbone flow (step → step) — HIGH weight
```dot
step1 -> step2 [weight=10, xlabel="mapped content\nper subsection", fontcolor="#555555"]
```
Always `weight=10`. This is the most important edge type — it keeps the backbone horizontal.

### Input feeds step — LOW weight
```dot
aed -> step1 [weight=1]
template -> step1 [weight=1]
```

### Step produces output — LOW weight
```dot
step2 -> draft [weight=1]
```
Outputs are dead ends. NEVER connect an output to a downstream step.

### Rules BELOW step + Subagent ABOVE step (positioning pattern)

Use `rank=same` + invisible edge chain to control vertical ordering:
```dot
// Force into same column, set vertical order: verifier(top) → step3(mid) → rules(bottom)
{rank=same; verifier; step3; gen_rules}
verifier -> step3 [style=invis]
step3 -> gen_rules [style=invis]

// Visible edges carry semantics, use constraint=false (rank already forced)
gen_rules -> step3 [weight=1, constraint=false]
step3 -> verifier [weight=1, constraint=false, color="#e65100", fontcolor="#e65100", xlabel="delegates"]
```

### Self-loop (verify-fix cycle)
```dot
step3 -> step3 [style=dashed, xlabel="verify → fix gaps\n→ re-verify (max 3)"]
```

### Service feeds step (BELOW, same pattern as rules)
```dot
jira -> step1 [weight=1, constraint=false, color="#7b1fa2"]
```

## Cluster (Visual Grouping)

Use `subgraph cluster_name` for visual grouping (e.g., parallel workers):

```dot
subgraph cluster_parallel {
    label="Parallel Execution"
    style=dashed
    color="#999999"
    fillcolor="#fafafa"
    style="dashed,filled"

    worker1 [label="Backend Worker\nimplements API\nchanges"
             fillcolor="#ffe0b2" color="#e65100" fontcolor="#bf360c"
             style="filled,rounded,bold"]
    worker2 [label="Frontend Worker\nimplements UI\nchanges"
             fillcolor="#ffe0b2" color="#e65100" fontcolor="#bf360c"
             style="filled,rounded,bold"]
}
step_before -> worker1 [weight=1]
step_before -> worker2 [weight=1]
worker1 -> step_after [weight=1]
worker2 -> step_after [weight=1]
```

## Colors Quick Reference

| Element | Fill | Border | Font |
|---------|------|--------|------|
| Step | `#c8e6c9` | `#388e3c` | `#1b5e20` |
| Data | `#fff9c4` | `#f9a825` | `#f57f17` |
| Agent | `#ffe0b2` | `#e65100` | `#bf360c` |
| Knowledge | `#e3f2fd` | `#1976d2` | `#0d47a1` |
| Service | `#e1bee7` | `#7b1fa2` | `#4a148c` |
| User | `#bbdefb` | `#1565c0` | `#0d47a1` |

## Rendering Command

```bash
dot -Tsvg "input.dot" -o "output.svg"
dot -Tpng "input.dot" -o "output.png"
```

Use `dot` engine (the default). Do NOT use `neato`, `fdp`, or other engines — they don't respect `rankdir` or `weight`.
