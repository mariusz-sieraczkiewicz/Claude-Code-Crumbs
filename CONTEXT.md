# Claude-Code-Crumbs

Universal Claude Code workflow plugin distilled from mentora (web/Svelte) and sielappkowo (iOS/Swift) projects. Goal: one plugin, many stacks, one opinionated discipline.

**Plugin output language: English.** All plugin-shipped artifacts (commands, agent prompts, ruleset templates, schemas, scripts, PRD/CONTEXT/ADR templates) are written in English regardless of the project's working language.

## Language

**Plugin**:
The shippable artifact in `.claude-plugin/` — bundle of skills + commands + agents installable per-project.
_Avoid_: extension, package, module

**Workflow**:
The opinionated sequence `plan-tasks → plan-and-implement → verify-dod → code-review → implement-feedback` (and optional `promote`).
_Avoid_: pipeline, process, methodology

**Universality**:
Spans four axes — **(a) stack**, **(b) source-of-truth**, **(c) team-model**, **(d) workflow-discipline**. (a)(b)(c) fully load-bearing for v1; (d) is constrained: TDD entry-point is mandatory, inner-loop details flex.

**TDD entry-point**:
Both **planning** and **implementation** start from a failing test. Plan = AC expressed as failing **ATDD spec**. Implementation = no production code without a prior red test (typically an **ATDD spec** or a **Domain-test**).
_Avoid_: "test-first", "test-driven" (too vague)

**Business scenario**:
Epic-level user-facing behavior, authored **before planning** in **Gherkin** (`## Scenario: <name>` + `Given/When/Then/And/But`). Serves as (1) the **lighthouse** that orients implementation and (2) the **basis for DoD verification**. Lives **inline in `epics.yaml`** as a block-scalar field on the epic entry (preserves Gherkin verbatim). One epic has 1..n scenarios. **MUST be domain-oriented (UI-ignorant)** — describes business behavior, not interaction mechanics.
_Avoid_: "acceptance criteria" (overloaded), "user story", "requirement"

**Domain-oriented (UI-ignorant)**:
Property of a **Business scenario** (and **Domain-test**) — describes the behavior in terms of business actions and outcomes, never in terms of buttons, screens, clicks, pages, URLs, selectors. UI is a delivery mechanism for the behavior, not part of it.
_Allowed_: "user cancels subscription", "subscription is cancelled", "invoice is issued for the remaining period"
_Forbidden_: "user clicks Cancel button", "page navigates to /confirm", "Cancel form submitted"
_Avoid_: "behavior-only", "implementation-free" (too vague)

**Scenario index**:
A flat, easy-to-scan list of all **Business scenarios** across all epics — only the `## Scenario: <name>` titles, no bodies. Lives at `docs/planning/SCENARIOS.md`. Generated/maintained so a stakeholder can read the full product behavior surface in one screen. Plugin keeps it in sync with epic files.
_Avoid_: "scenario list", "feature list" (overloaded)

**Step library**:
Domain-oriented abstraction layer that maps **Business scenario** verbs into executable actions. **Shared** across **ATDD specs** and **Domain-tests** — the same step function executes against different **Worlds**. One function per scenario verb, named 1:1 with Gherkin. ATDD spec body and Domain-test body look **identical**; only the World differs. Mentora: `tests/steps/*.ts`. Sielappkowo: `Tests/Steps/*.swift`.
_Avoid_: "page object", "helpers" (too generic), "test utilities"

**World**:
The execution context injected into a **Step library** function. Determines whether a step actuates a real browser/device (`BrowserWorld`, `DeviceWorld`) or an in-memory domain (`DomainWorld`). Steps are written world-agnostic; the test type (ATDD vs Domain) is determined by which World wires up the steps.
_Avoid_: "fixture", "context", "harness", "driver"

**Rule**:
A single-purpose policy file that captures a **cross-cutting concern not expressible as a Business scenario** — coding conventions, security constraints, accessibility requirements, observability mandates, repository pattern, error handling, etc. Lives in `.claude/ruleset/` (one rule per file). Body is **free-form markdown** (no enforced template). When a rule has a mechanical enforcement mechanism, the file points to it inline (e.g. `Enforced by: .swiftlint.yml/no_print_use_logger`). Referenced by **002-plan-and-implement** (during impl), **003-verify-dod** (during DoD), **004-code-review** (during review).
_Avoid_: "convention", "guideline", "principle", "policy" (all overloaded)

**Team-model preset**:
Plugin ships **4 preset variants** for `ruleset/git-workflow.md` + `ruleset/deployment.md` covering common collaboration shapes. User picks **one preset at `/000-prd-refine` bootstrap** (State A) via **interactive prompt** ("Team mode? [solo|small-team|oss|enterprise]"). Picked preset's templates populate the project's `git-workflow.md` and `deployment.md`. The chosen preset is recorded as `team_preset: <name>` in `.claude/stack.yaml` for forensics (informational only — plugin does not act on it after bootstrap). Other ruleset files unchanged. After bootstrap, project owns the files and edits freely. Migration between presets (e.g. solo → small-team) is a manual dev decision; plugin does not auto-migrate. No first-class "team mode" object in the plugin — preset is just a starting point.

Presets:
- **solo** — single dev; commit-to-main OK; no review; direct deploy
- **small-team** — feature branches; PR review (1-2 reviewers) required; staging gate before prod
- **oss** — fork-based PRs; multiple maintainers; no auto-deploy; community contribution flow
- **enterprise** — compliance gates (security scan, audit log); 2+ approvers; change-management window for promotion

**Canonical rule taxonomy**:
Plugin ships a fixed set of **18 rule categories** with baseline principles for each. All arrive with sensible defaults on plugin install. Project edits, extends, or empties any category. The taxonomy IS the plugin's opinion about which concerns deserve a rule file; project votes by editing.

Categories (alphabetical):
- `accessibility.md` — a11y identifiers, keyboard nav, WCAG AA
- `api-design.md` — versioned contracts, idempotency, structured error codes
- `architecture.md` — vertical slices, composition root, layered domain/application/infra
- `code-style.md` — lint/format settings, naming
- `copy-and-i18n.md` — i18n layer, no hardcoded strings, no internal labels
- `data-access.md` — protocol per aggregate, no leaky ORM in domain
- `data-modeling.md` — aggregates own consistency, FKs by ID, forward-only migrations
- `deployment.md` — pipelines, environments, rollback policy
- `documentation.md` — CONTEXT.md, ADRs, README maintenance cadence
- `error-handling.md` — typed errors, boundary translation, no silent catch
- `git-workflow.md` — branches off main, Conventional Commits, PR review
- `language-patterns.md` — stack-specific idioms (empty default)
- `monitoring.md` — alerts, dashboards, SLOs, on-call
- `observability.md` — structured logs, trace IDs, no PII
- `performance.md` — latency budgets, throughput targets, profiling
- `security.md` — secrets via vault, authn at boundaries, no PII in logs/URLs
- `testing.md` — Step library + Worlds + Vertex; ATDD per task, Domain frequent, Journey at promote
- `ui-components.md` — pure presentation, design tokens, domain logic outside

**Rule enforcement**:
A **Rule** is enforced through one or both of: (1) **mechanical gate** — linter custom rule, type checker, security scanner, etc. (preferred when expressible); (2) **subagent check** — LLM reads the rule file + diff during 003/004 (fallback for rules that resist mechanisation).
_Avoid_: "validation", "check"

**Finding policy**:
**Zero tolerance.** Any finding from `/003` or `/004` blocks DoD. No severity tiers, no overrides, no "Minor advisory". Every gate exit code != 0 blocks. Every rule violation blocks. Every code-review issue blocks. Rationale: severity tiers leak into rationalisation; binary policy keeps gates honest and tasks small.
_Avoid_: "critical/major/minor", "blocker/non-blocker"

**ATDD spec**:
**Executable** form of a **Business scenario**, scoped to a single task. Test code (Playwright / XCUITest / etc.) that asserts the scenario passes against real or near-real infrastructure. Written **during** the task (not at task start). Each task has exactly one `atdd_spec`. Executed **only at epic close-out**, never per-task. Mentora: Playwright in `tests/e2e/specs/`. Sielappkowo: XCUITest test class.
_Avoid_: "e2e test", "acceptance test", "feature test" (all too vague)

**Journey**:
End-to-end test for a **logical sequence of multiple Business scenarios** executed in order, covering cross-cutting consequences of actions across features. **Composition** of step library calls drawn from many scenarios. Runs as a **smoke gate at environment promotion** against real (production-like) infrastructure — the combination of "multi-feature flow" + "real env" is what makes Journey distinct from ATDD spec. Examples: signup→onboard→first-purchase→downgrade→cancel. Mentora: `tests/journeys/` against `staging-e2e` (real AWS+Gemini). Sielappkowo: cross-feature UITest plans.
_Avoid_: "smoke test", "integration test", "regression suite", "user story test"

**Domain-test**:
Test that exercises **multi-class domain scenarios** with **no infrastructure** — in-memory repositories, external-system stubs, fully instantiated domain objects (no method-level mocks). Following Vertex Testing (https://technicalleadership.pl/blog/095-systematic-approach-to-automated-software-testing-with-vertex-testing/). Runs in the inner TDD loop. Mentora: `bun run test`. Sielappkowo: currently absent (policy: XCUITest carries this load) — flagged for revisit.
_Avoid_: "unit test" (misleading — tests multiple classes), "integration test"

**Subagent chain**:
The orchestration pattern used by `/001`..`/005` commands. Each command spawns a **dedicated subagent type** (defined in `.claude-plugin/agents/`) with isolated context. Communication between subagents goes through the **filesystem** (artifacts written under `.claude/runs/{epic-id}/{task-id}/`), not through main thread. The chain is **iterative, not linear**: `planner` → `implementer` → `verifier` → `reviewer` → (on fail) `feedback-implementer` → loop back to `verifier`. **Implementer may also signal "task too big"** and kick back to `planner` for re-split.

**Planner role expansion** (vs mentora/sielappkowo):
`/001-plan` not only decomposes an epic into tasks but **also authors Business scenarios** for the epic (writes them into `epics.yaml` as Gherkin block-scalar) when they are absent or underspecified. Planner has two entry modes: (1) **fresh** — given epic id, author BS + decompose; (2) **re-split** — given an existing task flagged "too big" by implementer, decompose that one task into smaller tasks. BS authoring source = **PRD per-epic section** (`## Epic E-007: ...` in `PRD.md`) + **adaptive grilling**: if the PRD section is sufficient (covers happy path + at least one edge case + scope boundary), planner generates BS directly; otherwise emits clarifying questions in `runs/{epic}/00-plan-questions.json` and waits for user answers before proceeding.

**Command names** (universal plugin):
- `/000-prd-refine` — *(NEW)* **single context-aware command** for product-level definition. Auto-detects state from filesystem (optional `--mode=...` override). Builds/extends `CONTEXT.md` glossary inline as terms get resolved during PRD/epic discussion, and offers ADRs when decisions are hard-to-reverse + surprising + the result of a real trade-off. Modes:
  - **State A (no PRD.md)**: bootstraps everything — `PRD.md` (interactive grilling), `docs/planning/epics.yaml` (empty), `docs/planning/SCENARIOS.md` (empty), `.claude/ruleset/*.md` (18 plugin templates), `CONTEXT.md` (empty glossary, populated inline during the session), `docs/adr/` (empty), `.claude/stack.yaml.example`. **No separate `/init-crumbs` command** — `/000-prd-refine` IS the bootstrap.
  - **State B (PRD exists, no/few epics)**: prompts to add epic, edit top-level PRD, or refine an epic header. New epic = `## Epic E-NNN` section in PRD + entry in `epics.yaml` (status: pending, no BS). Term-resolution into `CONTEXT.md` and ADR offers continue inline.
  - **State C (PRD + epics exist)**: edit guidance (free-form refine with plugin pointing at sections), not section-by-section grilling. Same inline context-building behaviour.
  - **PRD-level immutability**: `/000-prd-refine` does not modify existing epic sections in PRD. If user wants PRD-level change to an existing epic, command nudges toward creating a new epic. Implementation-level adjustments stay with `/001-plan`.
- `/001-plan` — epic decomposition + BS authoring (replaces mentora `plan-tasks`)
- `/002-implement` — **task orchestrator** (replaces `plan-and-implement`). Per task:
  1. Starts a new branch (naming convention in `git-workflow.md`)
  2. TDD impl loop (Domain-tests RED → code GREEN → REFACTOR → write ATDD spec)
  3. Commit after task green (single commit per task by default)
  4. **Auto-invokes** `/003-verify-dod` then `/004-code-review` — toggleable via `.claude/ruleset/git-workflow.md`
  5. On clean review: proposes opening MR/PR (does not auto-open; surfaces command for user)
- `/003-verify-dod` — DoD gate (also invokable standalone)
- `/004-code-review` — review gate (also invokable standalone)
- `/005-implement-feedback` — fixes from /003/004 findings; loops back to verifier
- `/006-merge` — opens MR/PR (separate command, user-invoked after `/002` proposes it). **Applies conventions from `.claude/ruleset/git-workflow.md`**: PR title format, description template, base branch, reviewers, labels. Invokes `gh pr create` / `glab mr create` accordingly.
- `/007-promote` — *(lightweight)* triggers a **pre-existing platform workflow** (e.g. `gh workflow run promote-staging.yml`, GitLab pipeline). Plugin reads target workflow from `stack.yaml.promote`. Plugin does **not** orchestrate the promotion itself; the platform (GitHub Actions / GitLab CI) owns the actual deploy logic. Optional command — skipped if `stack.yaml.promote` is empty.
- `/002-auto-implement` — *(NEW)* **epic-level orchestrator**. Takes finished `/001-plan` output and runs the full chain (`/002-implement` → `/003-verify-dod` → `/004-code-review` → `/005-implement-feedback` on fail) for **every pending task** in the epic. **Each step runs as a dedicated subagent** (isolated context). Alternative to running each command manually per task.

**Too-big detection** (`/002` → `/001` re-split):
Implementer signals "task too big" via **agent judgment** (LLM-driven, no hard metrics). Signal mechanism: implementer writes `runs/{epic}/{task}/02-impl.json` with `status: "too_big_proposal"`, `reason`, `suggested_split: [draft tasks]`, then halts. User reviews and decides to invoke `/001-plan --resplit <task-id>`. Re-split **replaces** the old task in `tasks.yaml` with new ones (linked to the same Business scenarios); old task is archived to `runs-archive/`, not preserved as a `parent`.

**Runs directory**:
Filesystem location for subagent handoff artifacts. Gitignored. Layout:
```
.claude/runs/{epic-id}/{task-id}/
  01-plan.json
  02-impl.json
  03-verify.json
  04-review.json
  05-feedback-impl.json   # numbered with letter suffix if rerun: 05a, 05b
  artifacts/              # transient files (logs, drafts)
```
Each `NN-<phase>.json` validated against plugin-shipped JSON Schema on write. Each phase reads **all prior phase files** as input (append-only history). On epic close-out, plugin **auto-archives** `runs/{epic-id}/` into `runs-archive/{epic-id}-{timestamp}.tar.gz`.

**Ruleset injection**:
Plugin reads `.claude/ruleset/*.md` verbatim and **injects content directly** into subagent prompts (not via `@`-include — `@`-references do not always propagate in subagents). Same for `stack.yaml.extras` field, propagated verbatim to **all** subagents.

**Status**:
The state of a **Task** or an **Epic**. Vocabulary: `pending | in_progress | blocked | done`. `pending` = initial (set by `/001`). `in_progress` = actively being worked. `blocked` = waiting on external clarification/decision/dependency. `done` = all gates passed (`/003` ALL_DONE + `/004` PASS). No `partial` (mentora's vocab) — it hides ambiguity and signals tasks too large or gates too soft.
_Avoid_: "todo", "wip", "complete", "partial"

**Plugin distribution**:
Plugin distributed via **Claude Code marketplace / global install** — plugin files live in `~/.claude/plugins/claude-code-crumbs/` (user-level, shared across all projects). Single source of truth for plugin code; upgrade once, all projects benefit. Per-project state (PRD, ruleset, stack.yaml, runs/) stays in the project. Git submodule may be a fallback channel for environments without marketplace support.

**Install flow**:
Two-step, explicit:
1. **User-level**: `claude install plugin claude-code-crumbs` — once per developer machine.
2. **Project-level**: inside a project, run `/000-prd-refine` — plugin detects absent `PRD.md`, bootstraps the project (PRD, epics.yaml, SCENARIOS.md, ruleset/, CONTEXT.md, stack.yaml.example, docs/adr/).

**File ownership split**:
- **Plugin-owned** (`~/.claude/plugins/claude-code-crumbs/`, upgraded as a unit): `agents/`, `commands/`, `schemas/`, `templates/`, `scripts/`. Read-only from a project's perspective. **Plugin does NOT ship skills** — `grill-with-docs` and any other skills are external/optional (user installs separately if desired).
- **Project-owned** (commited per-project): `PRD.md`, `CONTEXT.md`, `docs/planning/`, `docs/adr/`, `.claude/ruleset/`, `.claude/stack.yaml`.
- **Project-owned but gitignored**: `.claude/runs/`, `.claude/runs-archive/` (transient subagent comms, local forensics).
- **Ruleset policy**: `.claude/ruleset/*.md` is a **snapshot copied from plugin templates at install time** (via `/000-prd-refine` first invocation). Subsequent plugin upgrades do **not** touch project-side ruleset — drift is the project's responsibility.

**Stack-adaptation**:
The mechanism by which the universal workflow binds to a project's gates/SoT/test-cmds/lint-rules/design-verify. Implemented via `.claude/stack.yaml` (project-owned config, validated against plugin-shipped JSON Schema at install time). May override canonical SoT paths.

**stack.yaml shape**:
- `stack: {name, language, runtime}` — informational
- `paths: {...}` — override canonical SoT paths
- `gates: {lint, typecheck, domain_tests, atdd_specs, journeys, build, security, a11y, perf, ...}` — shell commands; exit 0 = pass, nonzero = blocker. `null` to skip
- `design_verify: {type: "script"|"prompt", path: <file>}` — either an executable script (exit 0/non-zero) or a prompt file (markdown with custom instructions injected into a verification subagent)
- `promote: {environments, *_workflow, pre_flight}` — promotion config
- `extras: {...}` — escape hatch for stack-specific quirks (e.g. `bash_buffering_warning`, `user_ping_interval_minutes`). Plugin propagates to subagents in prompt; no built-in logic


**Canonical SoT layout**:
Plugin's default file layout. Project keeps it unless overriding via `.claude/stack.yaml`.
```
PRD.md                              # project-owned narrative w/ structured sections (sielappkowo-style: §1..§N including §Decisions, §V1 Scope binding, AND per-epic sections `## Epic E-NNN: ...` that feed /001-plan BS authoring)
docs/
  planning/
    epics.yaml                      # all epics in one file, each with inline business_scenarios (Gherkin block-scalar) — mentora-style registry, BS authored inline
    epic-{id}-tasks.yaml            # per-epic task list — mentora-style split (PR-friendly, no cross-epic conflicts)
    SCENARIOS.md                    # flat scenario index (generated from epics.yaml)
  adr/
    NNNN-slug.md                    # ADRs (Matt Pocock minimal format)
.claude/
  ruleset/*.md                      # 18 canonical rules (plugin-shipped principles, project-edited)
  stack.yaml                        # stack-adaptation config (path overrides, test cmds, gate commands)
CONTEXT.md                          # project glossary (grill-with-docs format)
```

## Relationships

- **Workflow** is invariant across **Stacks**. **Stack-adaptation** is the only thing that changes per project.
- **TDD entry-point** is a property of **Workflow**, not of **Stack-adaptation**.
- An **Epic** declares **1..n Business scenarios** upfront (before planning); they are the lighthouse + DoD basis.
- A **Business scenario** is realized by **1..n Tasks**. (Typical: 1:1 or 1:few.)
- A **Task** has **exactly one ATDD spec** — executable form of the scenario it primarily realizes, **happy path only**.
- A **Task** has **1..n Domain-tests** — the **decomposition** of its scenario(s) into happy path + edge cases, all in-memory (Vertex-style).
- Coverage rule: **every Business scenario gets both** an ATDD spec (happy) and Domain-test(s) (happy + edges). Edge cases live **exclusively** in Domain-tests.
- A **Journey** is a **sequence of Business scenarios** (not a new scenario type) — composed via the shared **Step library**. Journeys are decided at the **product** level, not the epic level. Typically 3-7 per product.
- **Cross-cutting concerns** are NOT Business scenarios. They are **Rules** — separate files, mechanically enforced where possible, subagent-checked otherwise.
- **PRD-level epic immutability**: PRD epic sections are not modified after epic creation. If a change needs PRD-level rewrite of an epic, create a new epic. Implementation-level adjustments (BS tweaks, task additions, re-splits) remain flexible.
- **Domain-tests** run **frequently** in the inner loop (every RED-GREEN-REFACTOR cycle, every gate-check). Drive per-task RED.
- **ATDD specs** are **written per task** (one per task, `atdd_spec` field) but **executed only at epic close-out**.
- **Journeys** run as **smoke gate at environment promotion** (staging, prod). Never per-task, never per-epic in isolation.
- A **Task** record carries: `domain_scenarios: [name...]` (drives per-task RED) and `atdd_spec: <path>` (one spec, written during task, executed at epic-end).
- AC of a **Task** is derived from the **Business scenario** it realizes. Planner translates the scenario into **Domain-test scenarios** (Vertex Testing). ATDD spec is captured during the task as the executable form of the scenario, but not executed until epic close-out.

## Flagged ambiguities

- "uniwersalny" was overloaded across 4 axes (a/b/c/d) — resolved 2026-05-17: a+b+c full universality; d is constrained to "TDD entry-point mandatory, inner-loop flexible".
- "TDD" was overloaded with "unit-test TDD" — resolved 2026-05-17: split into **ATDD spec** (per-task acceptance), **Journey** (cross-cutting), **Domain-test** (multi-class no-infra, Vertex Testing). "Unit test" deprecated as misleading.
- "AC" (acceptance criteria) collapsed into two distinct concepts — resolved 2026-05-17: **Business scenario** (epic-level, prose-Gherkin, upfront, domain-oriented) vs **task AC** (derived from BS, drives Domain-tests + ATDD spec).
- "Scenario" was ambiguous between business behavior and test code — resolved 2026-05-17: **Business scenario** = domain-oriented prose (lighthouse); **ATDD spec** = its executable form; **Domain-test scenario** = in-memory decomposition.
- "Cross-cutting concerns" were initially conflated with Business scenarios — resolved 2026-05-17: they are **Rules** (separate files in `.claude/ruleset/`), referenced by impl/DoD/review, never expressed as scenarios.
- `.claude/rules/` was initially proposed for rules — resolved 2026-05-17: directory is reserved/special in Claude Code and must not be used. Rules live in `.claude/ruleset/` (sielappkowo convention).
