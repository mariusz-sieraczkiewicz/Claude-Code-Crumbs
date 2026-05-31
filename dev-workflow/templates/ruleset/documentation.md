# Documentation

**Principle:** Three documents carry the project's memory — `CONTEXT.md` (vocabulary), `docs/adr/` (decisions), `README.md` (entry point). They are updated as decisions crystallise, not as an afterthought. Code is the implementation; these documents are why it is the way it is.

## Mechanical enforcement

The following gates MUST or SHOULD be wired into `stack.yaml.gates`.

- **`CONTEXT.md` MUST exist** and be non-empty after the first epic ships. A pre-commit hook or CI check SHOULD fail if `CONTEXT.md` is missing.
- **ADR filenames MUST follow `NNNN-slug.md`** (zero-padded sequential ID, lowercase kebab-case slug). A lint rule (filename regex) MUST enforce this on `docs/adr/`. Recommended tools: `markdownlint`, a small CI script (`find docs/adr -type f ! -regex '.*/[0-9]\{4\}-[a-z0-9-]\+\.md$'`).
- **ADR numbers MUST be unique and sequential.** CI script flags gaps and duplicates.
- **`README.md` MUST exist at repo root** and link to `PRD.md`, `CONTEXT.md`, and `docs/adr/`.
- **Markdown lint** (`markdownlint`, `vale`, or equivalent) SHOULD run via `gates.lint` to catch broken internal links, missing headings, malformed lists.
- **Link checker** (`lychee`, `markdown-link-check`) SHOULD run weekly or in CI to catch rot in external references.
- **`docs/planning/SCENARIOS.md` MUST be regenerated** from `epics.yaml` whenever scenarios change. A CI check SHOULD diff the generated file against the committed one and fail on drift.
- **Spell-check** (`cspell`, `aspell`, or `vale`) MAY run with a project dictionary that includes domain terms from `CONTEXT.md`.

## Subagent check

`reviewer` and `/000-prd-refine` (inline during PRD/epic discussion) enforce the substance these documents must carry.

1. **CONTEXT.md is updated inline.** When a term gets resolved during PRD / epic / task discussion, it is added or refined in `CONTEXT.md` in the same turn. Reviewer flags a PR that introduces a new domain term in code without a corresponding `CONTEXT.md` entry. The grill-with-docs cadence is non-negotiable: terminology drift kills universality.
2. **CONTEXT.md format.** Each entry: `**Term**:` (bold term followed by colon) then a definition paragraph, optionally `_Avoid_: <synonyms to reject>`, optionally `_Allowed_:` / `_Forbidden_:` example bullets. Reviewer enforces format.
3. **ADR cadence.** An ADR is created whenever a decision is **hard-to-reverse + surprising + the result of a real trade-off**. Reviewer judges, during `/004`, whether a PR contains a decision that meets all three criteria and lacks an ADR. The format is Matt Pocock minimal: Context, Decision, Consequences. No fluff.
4. **ADR immutability.** Once an ADR is committed, its decision section is not edited in place. Superseding an ADR means a new ADR with `Supersedes: NNNN-…` in the header and a one-line `Status: Superseded by NNNN-…` appended to the old one.
5. **README is an entry point, not a manual.** README answers: what is this, how do I run it, how do I contribute. It links to PRD / CONTEXT / ADRs for depth. Reviewer flags a README that has drifted into an out-of-date manual.
6. **No documentation in code comments that belongs in `CONTEXT.md`.** A comment defining what "Subscriber" means is a sign `CONTEXT.md` is missing the entry. Reviewer moves it.
7. **Plain language.** No marketing voice ("blazingly fast", "robust", "world-class"). No filler ("simply", "just", "easily"). Documentation is operational, not promotional.
8. **PRD epic sections are immutable once shipped.** PRD-level changes to an existing epic = new epic. Reviewer flags edits to historical epic sections.

## Examples

### Good

**CONTEXT.md entry**

```markdown
**Subscriber**:
A party with at least one active or cancelled subscription. Identified by `SubscriberId` (UUID v7). Owns the subscription lifecycle (create, upgrade, downgrade, cancel).
_Avoid_: "customer" (overloaded — billing-side concept), "user" (auth-side concept), "account" (org-level)
```

**ADR (Matt Pocock minimal)**

```markdown
# 0007. Use SQS for inter-service async messaging

Date: 2026-05-18
Status: Accepted

## Context
Two services need to exchange events; latency budget is 5s p95; existing infra is AWS.

## Decision
Use SQS with a single-consumer pattern per queue. Dead-letter queue after 3 failures.

## Consequences
- Plus: no new infra; integrates with existing IAM.
- Minus: at-least-once delivery — consumers must be idempotent (see `api-design.md`).
- Minus: no fan-out without SNS in front; revisit if a third consumer appears.
```

**README skeleton**

```markdown
# Acme

One-line description of what this product does, in user-facing terms.

## Quick start
- Install: `…`
- Run: `…`
- Test: `…`

## Documentation
- [PRD](PRD.md) — product requirements
- [CONTEXT.md](CONTEXT.md) — domain glossary
- [ADRs](docs/adr/) — architectural decisions
- [Scenarios](docs/planning/SCENARIOS.md) — behavior surface

## Contributing
See [git-workflow](.claude/ruleset/git-workflow.md) for branch and PR conventions.
```

### Bad

**CONTEXT.md entry with synonyms tolerated**

```markdown
**User / Customer / Account**:
Someone who uses the system.
```

Violations: three synonyms collapsed; no `_Avoid_` discipline; vague definition that doesn't disambiguate.

**ADR with marketing voice**

```markdown
# 0007. We chose the best message queue
We picked SQS because it is robust and battle-tested.
It scales effortlessly and is the industry standard.
```

Violations: no Context section; no trade-offs in Consequences; promotional language; no concrete constraints (latency, existing infra, alternatives considered).

**README as out-of-date manual**

```markdown
# Acme
First, clone the repo. Then set up Postgres 12 on port 5432 (we used to support
MySQL but that changed in 2023). Edit the config.yaml — note that line 47 has
a deprecated field, ignore the warning. ...
```

Violations: drifted into operational trivia, contradicts itself, references things "we used to do". Move runtime details to a `docs/operations.md` or to the deployment rule; keep README short.

## Anti-patterns

- Writing ADRs after the decision has shipped, as archaeology. ADRs document trade-offs at the moment of the decision; retrofit ADRs are weaker but better than nothing — mark them `Status: Accepted (retrospective)` and keep moving.
- Treating `CONTEXT.md` as an optional addendum. It is the lighthouse for naming; the project drifts without it.
- Long, narrative ADRs with sections for "Alternatives Considered" listing every option in detail. Matt Pocock minimal: Context, Decision, Consequences. Alternatives appear in Context if they shaped the decision.
- Documentation in code comments that should be in `CONTEXT.md` or an ADR. Code comments document the local "why"; project-level "why" lives in dedicated documents.
- `docs/` becoming a graveyard of stale design proposals. Either commit (ADR), reject (delete), or mark draft with an owner and date.
- README that duplicates `CONTEXT.md` or `PRD.md`. Each document has one job; README links, doesn't restate.
- Numbered ADRs reused after deletion. ADR numbers are immutable; deletion is rare and leaves a placeholder (`0007-RESERVED.md`) or just a gap with the reason recorded.
- Documentation written for a future reader who "should just know the context". Write for a developer joining the project in six months.
- Mixing "design doc" and "runbook" content. Design = PRD / ADR / CONTEXT. Runbook = `monitoring.md`, `deployment.md`, `docs/operations.md`.
- Updating `SCENARIOS.md` by hand. It is generated from `epics.yaml`; hand-edits will be overwritten.
- Marketing voice anywhere in the documentation set. Operational tone only.

## Cross-refs

- `testing.md` — Business scenarios in `epics.yaml` are the source for `docs/planning/SCENARIOS.md`; scenario authorship is part of the documentation cadence.
- `code-style.md` — `CONTEXT.md` vocabulary is the source of truth for code naming; the reviewer cross-checks both rules together.
- `architecture.md` — significant architectural decisions become ADRs; the rule defines the threshold.
- `git-workflow.md` — Conventional Commits + PR description format are documented there; the README links to it.
- `monitoring.md` / `deployment.md` — operational runbook content lives there, not in README.
