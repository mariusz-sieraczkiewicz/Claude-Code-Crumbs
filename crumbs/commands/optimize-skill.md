---
description: Optimize a skill file for token efficiency without sacrificing accuracy or compliance.
argument-hint: "<skill-path>"
---

# /optimize-skill

If no path argument provided, ask which skill to optimize. Read the skill file first.

## Constraints

- Only compress and relocate — never remove behavioral directives, output contracts, or safety constraints.
- Preserve all tool references and agent names exactly.
- When uncertain whether a block is decoration or directive, keep it.

## Phase 1 — Baseline Analysis

1. Count lines, estimate tokens (words × 1.3).
2. Classify every block:

| Type | Action |
|------|--------|
| **DIRECTIVE** — changes model behavior | Keep |
| **EXAMPLE** — disambiguates a directive | Keep 1 per pattern, compress rest |
| **EXPLANATION** — non-obvious *why* | Keep only if *why* is non-obvious |
| **DECORATION** — filler, redundancy | Remove |

3. Flag: repeated directives, verbose conditionals (→ table/enum), multi-sentence options (→ flags), prose lists (→ bullets), duplicate examples.

Report baseline to the user before proceeding.

## Phase 2 — Optimization Transforms

Apply in order:

**A. Prune decoration** — Remove filler ("please", "make sure to", "it is important that"), restated context, trailing summaries.

**B. Deduplicate** — Same directive in multiple places → keep strongest version in most prominent position, delete rest.

**C. Compress examples** — 1 per pattern. Convert multi-line → slot-fill when regular. 3+ teaching same lesson → keep most discriminating.

**D. Restructure verbose blocks**
- Multi-sentence options → `enum | shorthand`
- Conditional prose → decision table
- Narrative steps → numbered micro-instructions
- Paragraph lists → bullets

**E. Canonicalize phrasing** — Imperative mood, active voice. Remove meta-references ("In this prompt...") and "do not" instructions obvious from the positive form.

**F. Anchor constraints** — Place non-negotiable constraints at top. Repeat as one-line anchor at bottom if skill exceeds 100 lines.

**G. Tighten frontmatter** — Description: 1 sentence, under 160 chars. Remove redundant fields.

## Phase 3 — Diff, Validate, Apply

1. Present before/after diff.
2. Report metrics:
   - Lines: before → after (% reduction)
   - Tokens: ~before → ~after (% reduction)
   - Directives preserved: N/N (must be 100%)
   - Examples: N of M kept (justify removals)
3. For each removed block, state which remaining block covers its intent.
4. Ask "Apply these changes?" — then write the optimized file. Preserve file path and frontmatter `name`.

## Output

```
Optimized: <path>
Lines:     <before> → <after> (<% reduction>)
Tokens:    ~<before> → ~<after> (<% reduction>)
Directives: <preserved>/<total> preserved
```
