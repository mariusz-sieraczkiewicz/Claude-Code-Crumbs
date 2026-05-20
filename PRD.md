# Claude-Code-Crumbs — Product Requirements Document

## §1. Vision

One Claude Code plugin that ships a single, opinionated discipline for product-driven software delivery — distilled from the patterns that worked in two prior projects (web/Svelte, iOS/Swift) and made portable across stacks, sources-of-truth, and team shapes.

The plugin's value is the **workflow**, not the technology. Stacks are adapters. The workflow stays invariant.

## §2. Users

- **Solo developers** running personal projects who want planning + verification + review discipline without inventing it.
- **Small product teams** standardising on a shared workflow across multiple repos and stacks.
- **OSS maintainers** who want consistent contribution flow (fork-based PRs, multiple maintainers).
- **Enterprise teams** needing compliance gates layered on top of a known-good workflow.

The plugin is opinionated about *how* to deliver and *what* artifacts exist; it stays config-driven about *where* files live and *which* commands run.

## §3. Goals and non-goals

### Goals

- **Stack-agnostic** — adapters bind the universal workflow to web, iOS, server, CLI, library, etc. (axis (a))
- **Source-of-truth agnostic** — canonical SoT layout with `stack.yaml` overrides (axis (b))
- **Team-agnostic** — four collaboration presets (solo, small-team, OSS, enterprise) seed `git-workflow.md` + `deployment.md` at bootstrap (axis (c))
- **Opinionated discipline** — TDD entry-point is mandatory; both planning and implementation start from failing tests (constrained axis (d))
- **Zero-tolerance gates** — any finding from `/003` or `/004` blocks DoD; no severity tiers, no overrides
- **Iterative planning ↔ implementation** — `/002-implement` can signal "task too big" and kick back to `/001-plan` for re-split; per-task plan checkpoint allows the user to iterate the plan before TDD begins

### Non-goals

- Not a build system, not a test runner — wraps the project's own commands via `stack.yaml.gates`
- Not workflow-agnostic — TDD entry-point and subagent chain are non-negotiable
- Not a migration tool for existing mentora/sielappkowo projects (out of scope for v1)
- Not a deployment orchestrator — `/007-promote` only triggers a pre-existing platform workflow (`gh workflow run`, GitLab pipeline)
- Not self-bootstrapping (dogfooding is real but informal — no formal in-repo self-host story committed)

## §4. Test taxonomy and Step library architecture

Four distinct test/spec artifacts, sharing one execution layer:

| Artifact | Level | Cadence | World |
|---|---|---|---|
| **Business scenario** | Epic | Authored upfront (Gherkin, domain-oriented, UI-ignorant) | N/A — prose |
| **Domain-test** | Task | Frequent (inner loop, every RED-GREEN-REFACTOR) | `DomainWorld` (in-memory aggregates, no infra) |
| **ATDD spec** | Task | Written during task; **executed only at epic close-out** | `BrowserWorld` / `DeviceWorld` (real browser/device, near-real infra) |
| **Journey** | Product | Promotion smoke gate; real production-like environment | `BrowserWorld` / `DeviceWorld` (real env) |

### Step library + World pattern (ADR-0001)

A single, shared **Step library** maps Business scenario verbs to executable actions. Steps are written world-agnostic; the same `cancelSubscription()` step runs against `DomainWorld` for Domain-tests and `BrowserWorld` for ATDD specs and Journeys. Test bodies become near-identical sequences of step calls — only World wiring differs.

### Coverage policy

- Every Business scenario gets **one ATDD spec** (happy path only) and **one or more Domain-tests** (happy + edge cases).
- Edge cases live **exclusively** in Domain-tests. ATDD spec never carries edge variants.
- Journeys are composed at the **product** level, typically 3-7 per product.

## §5. Command set

| Command | Role | Subagent |
|---|---|---|
| `/000-prd-refine` | Context-aware product-level definition. Bootstraps project on first invocation; adds/edits epics afterwards. Builds `CONTEXT.md` glossary inline; offers ADRs at trade-off decisions. | (interactive, no dedicated subagent) |
| `/001-plan` | Epic decomposition + Business scenario authoring (epic-level Gherkin) + per-task `acceptance_criteria` authoring (verbose prose, the DoD bar audited by `/003`). Reads PRD per-epic section as the brief source; grills user when underspecified. Re-split mode handles "task too big" callbacks and redistributes existing acceptance criteria across smaller tasks. | `planner` |
| `/002-implement` | Dual-mode TDD orchestrator. **Epic-default mode** (`<epic-id>` arg): creates a single **epic branch** (`epic/{epic_id}-{slug}` by default; pattern in `git-workflow.md`) once at the start, then iterates all pending tasks in dependency order. Each task is dispatched to its own `implementer` subagent; per task a **plan checkpoint** (plan-only dispatch + Approve/Iterate/Cancel) precedes the TDD loop (Domain-test RED → code GREEN → REFACTOR → write ATDD spec → commit). Every commit (impl + later self-heal fixes from `/003`/`/004`) stacks on the same epic branch. After every task is done, auto-chains to `/003-verify-dod <epic-id>` then `/004-code-review <epic-id>` (gated by `auto_invoke_review` toggle). **Single-task mode** (`<task-id>` arg): same TDD loop scoped to one task; creates or reuses the epic branch for that task's parent epic. | `implementer` |
| `/003-verify-dod` | Dual-mode DoD gate with self-healing. **Epic-default mode** (`<epic-id>` arg): iterates every `status: done` task, dispatches one `verifier` per task in parallel (5-way cap), aggregates epic status (ok iff every per-task verify is ok); writes a summary at `runs/{epic_id}/03-verify-epic.json`. **Task mode** (`<task-id>` arg, legacy): single per-task verify. Phase 1 detect audits **two independent axes**: (a) every entry in `task.acceptance_criteria: [...]` against files touched (per-criterion `satisfied`/`partial`/`not_satisfied` with file:line evidence), AND (b) every gate in `stack.yaml.gates`. Both axes must be clean for `ok`. Phase 2 fix (dispatches `feedback-implementer` with criterion + gate findings) → Phase 3 re-verify → Loop max 3 iter **per task**. Self-heal gated by `auto_fix_on_verify_fail` toggle (default true for solo/small-team/oss; false for enterprise → read-only fallback). Zero tolerance on both axes. Standalone-invokable. | `verifier` |
| `/004-code-review` | Dual-mode review gate with self-healing. **Epic-default mode** (`<epic-id>` arg): iterates every `status: done` task, dispatches one `reviewer` per task in parallel (5-way cap), aggregates epic status; writes summary at `runs/{epic_id}/04-review-epic.json`. **Task mode** (`<task-id>` arg, legacy): single per-task review. Same Phase 1 detect → Phase 2 fix → Phase 3 re-review → Loop (max 3 iter per task) shape as `/003`, gated by `auto_fix_on_review_fail` toggle (same default split). Ruleset content verbatim-injected. Per-task diff scope. Zero tolerance. Standalone-invokable. | `reviewer` |
| `/005-implement-feedback` | **Epic-level user feedback flow**: gather feedback (interactive if absent) → clarify + research → plan new tasks (appended to `epic-{id}-tasks.yaml`) → ATDD implementation of new tasks → DoD verify (scoped to new tasks) → code review (scoped to new diff) → gatekeeper audit. **NOT a finding-fixer** — `/003` and `/004` self-heal internally. | `planner` → `implementer` → `verifier` → `reviewer` + gatekeeper (general-purpose) |
| `/006-merge` | Opens MR/PR for a completed **epic** (one PR per epic, not per task). Argument: `<epic-id>`. Pushes the epic branch, composes title (`epic(E-NNN): <title>`) + body (aggregate of every task's acceptance criteria + ATDD specs + gate/review status from `03-verify-epic.json` / `04-review-epic.json`), invokes `gh pr create` / `glab mr create`. Never auto-merges, never `--force` pushes, never amends. Solo preset (`pr_required: false`) → no-op + optional epic tag. | (no subagent — direct CLI) |
| `/007-promote` | Triggers a pre-existing platform workflow (`gh workflow run …`). Plugin does not orchestrate deploy logic. Optional — skipped if `stack.yaml.promote` empty. | (no subagent — direct CLI) |

### Subagent communication

Subagents communicate via **filesystem** under `.claude/runs/{epic-id}/{task-id}/NN-<phase>.json`. Each phase reads all prior phase files (append-only history). Ruleset content is **verbatim-injected** into subagent prompts (not via `@`-include). `stack.yaml.extras` propagates verbatim to all subagents. On epic close-out, `runs/{epic-id}/` is auto-archived to `runs-archive/`.

## §6. Ruleset taxonomy

Plugin ships **18 canonical rule categories** in `templates/ruleset/`, each with a baseline principle. At bootstrap, `/000-prd-refine` copies all 18 into the project's `.claude/ruleset/`. Project edits freely; plugin upgrades do **not** touch project-side ruleset.

`accessibility`, `api-design`, `architecture`, `code-style`, `copy-and-i18n`, `data-access`, `data-modeling`, `deployment`, `documentation`, `error-handling`, `git-workflow`, `language-patterns`, `monitoring`, `observability`, `performance`, `security`, `testing`, `ui-components`.

`git-workflow.md` and `deployment.md` are seeded from one of four **team-model presets** chosen at bootstrap:

- **solo** — commit-to-main; no review; direct deploy.
- **small-team** — feature branches; 1-2 reviewers; staging gate.
- **oss** — fork-based PRs; multiple maintainers; no auto-deploy.
- **enterprise** — compliance gates; 2+ approvers; change-management window.

Chosen preset is recorded in `.claude/stack.yaml.team_preset` for forensics. Plugin does not auto-migrate between presets.

## §7. File layout and ownership

### Canonical SoT layout

```
PRD.md                              # produkt-level + per-epic sections (## Epic E-NNN)
CONTEXT.md                          # project glossary
docs/
  planning/
    epics.yaml                      # epic registry + business_scenarios (Gherkin block-scalars)
    epic-{id}-tasks.yaml            # per-epic task list (PR-friendly)
    SCENARIOS.md                    # generated flat scenario index
  adr/
    NNNN-slug.md                    # ADRs (Matt Pocock minimal format)
.claude/
  ruleset/*.md                      # 18 rules, snapshotted at bootstrap, project-owned
  stack.yaml                        # stack-adaptation config
  runs/                             # gitignored — subagent comms
  runs-archive/                     # gitignored — closed-out archives
```

`stack.yaml.paths.*` may override the canonical paths.

### Ownership split

- **Plugin-owned** (`~/.claude/plugins/claude-code-crumbs/`, upgraded as a unit): `agents/`, `commands/`, `schemas/`, `templates/`, `scripts/`. Plugin ships **no skills** — `grill-with-docs` and any other skills are external/optional.
- **Project-owned** (committed per-project): `PRD.md`, `CONTEXT.md`, `docs/planning/`, `docs/adr/`, `.claude/ruleset/`, `.claude/stack.yaml`.
- **Project-owned but gitignored**: `.claude/runs/`, `.claude/runs-archive/`.

## §8. Distribution and install

- **Distribution channel**: Claude Code marketplace / global install. Plugin lives in `~/.claude/plugins/claude-code-crumbs/` and is shared across all the user's projects. Git submodule is a fallback channel for environments without marketplace support.
- **Install flow** (two-step, explicit):
  1. User-level: `claude install plugin claude-code-crumbs` — once per developer machine.
  2. Project-level: inside a project, run `/000-prd-refine`. Plugin detects absent `PRD.md` and bootstraps everything (PRD, epics.yaml, SCENARIOS.md, ruleset/*, CONTEXT.md, stack.yaml.example, docs/adr/).

## §9. Decisions

### Vocabulary

- `Status` for tasks and epics: `pending | in_progress | blocked | done`. No `partial`, no `wip`.
- `Finding policy`: zero tolerance — any finding blocks DoD; no severity tiers.
- `PRD-level epic immutability`: PRD epic sections are not modified after creation; scope change at PRD level = new epic. Implementation-level adjustments (BS tweaks, task additions, re-splits) remain flexible.
- `Domain-oriented (UI-ignorant)`: Business scenarios and Domain-tests describe behavior, never UI mechanics.

### Architectural ADRs

- [ADR-0001 — Shared Step library with World pattern](docs/adr/0001-shared-step-library-with-world-pattern.md)

### Flagged ambiguities resolved during grilling

- "Universal" was overloaded across 4 axes; resolved as a+b+c fully universal, (d) constrained to "TDD entry-point mandatory".
- "TDD" was overloaded with unit-test TDD; resolved by splitting into Business scenario / ATDD spec / Domain-test / Journey.
- "AC" collapsed two concepts; resolved as Business scenario (epic-level) vs task AC (derived).
- "Cross-cutting concerns" were initially conflated with Business scenarios; resolved as **Rules** in `.claude/ruleset/`.
- `.claude/rules/` was initially proposed; resolved as `.claude/ruleset/` (sielappkowo convention; `rules/` is reserved).

## §10. V1 scope (binding)

In v1 the plugin must deliver:

- All 8 commands listed in §5 (`/000-prd-refine` through `/007-promote`).
- 5 subagent types: `planner`, `implementer`, `verifier`, `reviewer`, `feedback-implementer`.
- 18 ruleset templates with English baseline principles.
- 4 team-model presets seeding `git-workflow.md` + `deployment.md`.
- JSON Schemas for `stack.yaml`, `epics.yaml`, `runs/*.json`, validated at install time.
- Filesystem-based subagent communication under `.claude/runs/{epic-id}/{task-id}/`.
- Auto-archival of `runs/{epic-id}/` to `runs-archive/` on epic close-out.
- `/000-prd-refine` State A bootstrap that produces a complete, runnable project skeleton.
- Plugin output language: **English** for all shipped artifacts regardless of project working language.

## §11. Out-of-scope for v1

- Migration from existing mentora / sielappkowo projects.
- Formal dogfooding (the plugin's own self-hosted development workflow) — handled informally for v1.
- Workflow-agnostic mode (non-TDD pipelines).
- First-class team-model object — presets are starting points only; migration between them stays manual.
- Custom team presets beyond the four shipped.
- Claude Code marketplace UX details (assume the marketplace exists; fall back to git submodule otherwise).
- Failure modes and recovery semantics — the agent is trusted to handle them sensibly without explicit spec.
- Detailed phase-by-phase rewrite of `/003 / /004 / /005` — inherit from mentora/sielappkowo patterns, adapt only where v1 decisions require it.

## §12. Open questions deferred past v1

- Plugin versioning policy and upgrade migration scripts for ruleset templates.
- Plugin repo internal layout (the layout of the plugin's own code, not the project layout it produces).
- Schema validation timing (install only, on every command, on demand).
- Whether the plugin should ship its own canonical scripts directory (helpers) or leave them per-stack.
- Cross-cutting concerns expressed as Rules vs. expressed as gate commands — current model says both, with rules pointing at gate commands inline; revisit if the distinction blurs in practice.

## §13. Per-epic sections

> Populated by `/000-prd-refine` in State B/C as epics are added. Each section begins `## Epic E-NNN: <title>` with subsections `### Goal`, `### Decisions`, `### V1 Scope`, `### Out-of-scope`. Business scenarios for each epic live in `docs/planning/epics.yaml`, not here.

*(none yet)*
