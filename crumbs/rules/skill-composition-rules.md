---
paths:
  - ".claude/skills/**"
---

# Skill Composition Rules

## Architecture Rules

### 1. Skills are atomic units

Each skill file contains instructions for exactly ONE unit of work. No orchestration, no parallelism, no dispatch inside skills. A skill must be readable and executable in complete isolation — hand it to a subagent with no other context and it must be self-sufficient.

### 2. Flat orchestration only

The orchestrator template calls ALL skills directly. No skill calls another skill — ever. Sequencing is the orchestrator's job: it runs skill A, then passes A's output files as B's input. This is "a rule for every pipeline stage."

### 3. Subagent execution pattern

Skills run as subagents (Agent tool with skill content as prompt), NOT via the Skill tool (which pollutes main context). This prevents context accumulation — each skill executes in isolation and writes output to files.

### 4. Subagents cannot nest

Hard Claude Code platform limit. A subagent cannot spawn another subagent. All parallelism (N documents = N subagents) is dispatched by the orchestrator, never by the skill itself.

### 5. File I/O is the only communication channel

Inter-skill communication is exclusively through files. Input = file paths passed as arguments. Output = files written to specified paths. No in-memory passing, no shared state, no return values.

### 6. Fail-fast on missing inputs

When a skill finds required input files are missing, it must STOP with an error. It must NOT try to produce the missing prerequisites itself. The orchestrator ensures prerequisites are met before invoking a skill.

### 7. Self-contained skills — all declarations inline

Everything needed by a skill (schemas, YAML examples, type definitions, rules) must be inlined in that skill file. No reliance on definitions in a shared header, other skills, or the orchestrator. No cross-referencing.

### 8. Name by function, not pipeline position

Skill names reflect what they DO: `evidence-extractor`, `gap-hunter`, `compliance-verificator`. Not `stage-2-processor` or `phase-4-step-3`.

---

## Orchestrator Rules

### 9. Lean orchestrator — schemas belong in skills

After extracting sub-skills, the orchestrator contains ONLY:
- One-liner stage invocations ("run X as subagent with [inputs]")
- Pipeline sequencing logic (what runs when, input/output connections)
- Cross-cutting rules that the Writer (if inline) needs
- Output structure (directory tree)
- Schemas for artifacts the Writer produces directly

Everything else — YAML schemas, detailed procedures, examples — belongs in the skill that uses it.

### 10. One-liner stage references

After extracting a pipeline stage into a skill, the stage reference in the orchestrator should be ONE LINE. If the extracted stage's section is more than 2-3 lines, something is still duplicated.

### 11. No duplicate content

When content is extracted into a skill, the corresponding inline content in the orchestrator MUST be removed immediately. Content has exactly one owner. If something appears in both places, it's wrong.

### 12. Orchestrator shrinks after extraction

After each extraction, verify that the source section shrank. If it retains the same length, either the extraction is incomplete or duplicate content remains.

---

## Content Rules

### 13. No overfitting to examples

Skills must generalize. Counts, structures, and patterns observed in one example are not universal requirements. Do not encode example-specific details as rules — only encode constraints from authoritative sources.

Illustrative values must also be **valid**: an example value must satisfy the schema, enum, or field it demonstrates (e.g. don't show `localisation: singapore` when the field only accepts `mandatory`/`optional`). An invalid example is a defect even when it parses.

### 14. Agency/domain neutrality

Reusable skills (templates and atomic pipeline skills) must be agency-, country-, and product-agnostic. Do not hardcode agency-specific terms — committee acronyms (ERC, DAC), body names, registries, drug/product names, or country-specific paths — into instructions, labels, markers, or headings. Such terms belong only in the concrete skill that is *generated/instantiated* for a specific agency, never in the generic source.

Two exceptions, both must stay clearly illustrative:
- **Multi-agency examples** that list several agencies side by side specifically to demonstrate agnosticism (e.g. "singapore, nice, pbac") are encouraged.
- **Placeholder forms** (`docs/{country}/`, `{Agency}_Template.md`, `DrugX`) instead of one real value.

Distinguish the two tiers: a *generic skill* must obey this rule; an *instantiated deliverable skill* (e.g. `ace-section1`) is agency-specific by design and is exempt.

### 15. Referential integrity — no orphaned or stale references

Every file or skill a skill points to must exist and actually be consumed. When content is moved, a stage is re-wired, or a reference is removed, update every cross-reference and every claim about what references what in the same change. No orphaned files (referenced but unused, or copied but never read), no dangling pointers (referenced but missing), and no stale claims (e.g. "the template references X" after X was removed from the template).
