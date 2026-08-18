---
name: simplify-agent-instructions
description: Aggressively simplifies agent skills, commands, prompts, templates, and workflow instructions into declarative contracts that retain only non-inferable requirements. Use when asked to simplify, shorten, or declutter instructions; make them declarative; remove schema duplication; compare instruction versions; or propose reductions for acceptance or rejection.
---

# Simplify Agent Instructions

## Definitions

**Canonical source:** the authoritative place that defines a rule, such as the original instruction, schema, validator, or referenced contract.
**Fragility:** how easily a small deviation can cause a materially wrong result.

## Establish scope

Read the complete instruction and any directly referenced sources needed to identify its contract.
Keep each rule in one authoritative place. Resolve conflicting versions using the source of truth for that rule; if none resolves the conflict, report it instead of guessing.
Edit the original instruction only when explicitly requested.

## Apply the retention test

Match instruction specificity to the task’s fragility and variability.

Retain an instruction only when both are true:
- Removing it could materially change behaviour, authority, safety, lifecycle, validation, or the required result.
- It cannot be reliably inferred from the intent, context, repository, or canonical sources.

When a requirement is intentionally removed from the contract, update dependent artifacts and validations.
Do not invent triggers, thresholds, retry policies, terminal states, authority rules, or validation semantics. Report unsupported hardening separately from the simplification.

## Rewrite declaratively

- Express the desired state declaratively unless a specific action, tool, or sequence is required.
- Prefer contextual guidance over universal rules when acceptable behaviour varies.
- Remove examples that only illustrate inferable usage; retain those that define required semantics or edge cases.
- Use / introduce scripts for deterministic or repeatable procedures.
- Preserve exact literals only when required; never compress exact names, paths, or formats into ambiguous shorthand.
- Leave implementation choices to the agent unless constrained by the contract.
- State domain decisions and human authority explicitly; leave routine execution implicit.

## Preserve required contracts

- Structure skills with clear headings and lists, and place global rules under their owning section.
- For accuracy-critical steps, define required inputs, expected outputs, gates, constraints, cross-step invariants, validation, and terminal outcomes.
- For every accuracy-critical structured artifact consumed by a later step, preserve source-owned validation gates and name an existing validator when available. Report missing validation as hardening rather than inventing it.
- When using structured data format (eg. json, yaml, xml) always attach schema.
- Name required MCP tools by their fully qualified identifiers (`Server:tool`).
- State file paths when they cannot be inferred from convention.
- For each source-defined non-success or stop branch, retain its trigger, next action or terminal status, recorded artifact, user output, preserved state, and resumption authority. Report missing elements instead of inventing them.
- Remove duplicates and resolve contradictions across the instruction.
- When simplifying a skill, apply progressive disclosure: aim to keep `SKILL.md` under 500 lines and move necessary detail to directly linked reference files loaded on demand.
- Apply the Compose Method: keep the main flow at one level of abstraction and move lower-level details to linked references.
- Format a skill’s `description` as a concise third-person what statement plus an explicit `Use when` trigger clause. Name distinct trigger-relevant responsibilities; keep limits, sequences, validation, and lifecycle policy in the body unless they determine activation.

## Respect schema ownership

Before simplifying instructions for schema-backed structured data, read the schema and validator.

- Let the schema own every machine-checkable constraint.
- Replace schema-owned prose with a direct link to the narrowest relevant schema element.
- Retain only semantics not derivable nor expressable based on the schema and other canonical sources.
- Confirm that the validator enforces every schema feature relied on by the simplified instruction.
- Remove duplicate field and enum lists outside their canonical source.

For artifacts not governed by a schema, reference one canonical template or format contract instead of repeating their structure.

## Verify coverage

For fragile or accuracy-critical rewrites, use separate fresh-context subagents for both checks when available; otherwise perform both locally:
- Compare the rewrite with the source, distinguishing omissions from intentional contract changes and verifying that each retained requirement appears once.
- Audit the rewrite against every applicable rule in this skill.

Before finalizing:
- Trace every added normative clause to the source or another canonical owner; move unsupported additions to separate hardening proposals.
- Build a completeness table for every non-success or stop branch; add a separate hardening item for each source-absent trigger, action or status, artifact, user output, preserved state, or resumption rule.
- Compare word and line counts. Treat net word expansion as failed simplification unless every added clause is required to preserve a source-owned contract.
- Search for repeated global requirements and keep one owner.

Resolve or report every finding. Verify that references resolve and run applicable validators.
