# claude-code-crumbs

A universal, stack-agnostic Claude Code workflow plugin: TDD entry-point, a five-subagent chain, and zero-tolerance Definition-of-Done gates wired into your repo.

## What it is

`claude-code-crumbs` is a workflow, not a framework. It ships a small set of slash commands that orchestrate a fixed pipeline — **plan → implement → verify → review → feedback → merge → promote** — and it delegates the heavy lifting to five dedicated subagents. The plugin never picks your language, your test runner, your CI, or your branching model: those are read from `.claude/stack.yaml`, which you fill in once during bootstrap.

The value is in the discipline. Every task starts with a failing **domain test** (TDD entry-point). Every task ends behind a Definition-of-Done gate that runs every check declared in `stack.yaml.gates` with **zero tolerance** — any non-zero exit, any rule violation, is a blocker. Code reviews read your project-specific ruleset verbatim. Findings loop back through a feedback subagent, capped at three iterations before halting for human input. Business scenarios are written in domain-oriented Gherkin (UI-ignorant) and indexed flat into `docs/planning/SCENARIOS.md`.

The plugin is intentionally **lightweight**: it owns the workflow surface (commands, subagents, schemas, ruleset). It does not own your deploy pipeline (`/007-promote` triggers an existing platform workflow), does not auto-merge (`/006-merge` opens a PR and stops), and does not edit code outside of a task branch.

## Quick start

### Install

```bash
claude install plugin claude-code-crumbs@Claude-Code-Crumbs
```

### Bootstrap a project

```bash
cd your-project
/000-prd-refine
```

This builds `PRD.md`, `CONTEXT.md`, `.claude/ruleset/`, `.claude/stack.yaml`, `docs/planning/`, and `docs/adr/` interactively. It detects bootstrap mode automatically from the absence of `PRD.md` at the repo root. You will be prompted to pick a team preset:

| Preset       | Use when                                                          |
| ------------ | ----------------------------------------------------------------- |
| `solo`       | Single contributor, fast iteration, minimal ceremony.             |
| `small-team` | 2–8 contributors, PR review required, lightweight ADRs.           |
| `oss`        | Public repo, CLA/DCO, conventional commits, strict review.        |
| `enterprise` | Change-management windows, mandatory ADRs, gated promotions.      |

Presets seed the ruleset files in `.claude/ruleset/`. You can edit them at any time — the ruleset is the source of truth for the reviewer subagent.

### Plan an epic

```bash
/001-plan E-001
```

Reads the `E-001` section of `PRD.md`, dispatches the `planner` subagent, writes `docs/planning/epic-E-001-tasks.yaml` plus per-task Business scenarios (Gherkin, UI-ignorant), and regenerates the flat `docs/planning/SCENARIOS.md` index.

### Implement a task

```bash
/002-implement T-001            # single task, interactive
/002-auto-implement E-001       # whole epic, hands-off
```

`/002-implement` is the single-task TDD orchestrator: new branch, `implementer` subagent, auto-chain to `/003-verify-dod` and `/004-code-review`, propose `/006-merge` on clean. `/002-auto-implement` is the batch counterpart: it iterates every `pending` task in the epic, runs the full chain per task, and never edits code itself.

## Commands

| Command                     | One-line                                                                                                  |
| --------------------------- | --------------------------------------------------------------------------------------------------------- |
| `/000-prd-refine`           | Bootstrap a project (State A) or refine PRD / add-edit epics (State B/C). Single context-aware product-level command. |
| `/001-plan`                 | Decompose an epic into tasks and author Business scenarios. Reads PRD per-epic section as the brief.      |
| `/002-implement`            | Single-task TDD orchestrator. New branch, implementer subagent, auto-invokes verify+review, proposes merge on clean. |
| `/002-auto-implement`       | Epic-level batch orchestrator. Runs the full /002 → /003 → /004 → /005 chain per task in an epic. Each step is a dedicated subagent. |
| `/003-verify-dod`           | Run every DoD gate from stack.yaml.gates via the verifier subagent. Zero tolerance. Standalone-invokable or chained from /002-implement. |
| `/004-code-review`          | Code-review gate. Reviewer subagent reads verbatim-injected ruleset + branch diff and emits blocking findings. Zero tolerance. |
| `/005-implement-feedback`   | Address findings from /003 or /004 via the feedback-implementer subagent. Loops back to verify. Caps at 3 iterations. |
| `/006-merge`                | Open a merge/pull request for a completed task. Uses conventions from ruleset/git-workflow.md.            |
| `/007-promote`              | Trigger a pre-existing platform workflow to promote an environment. Plugin does not orchestrate the deploy itself. |

## Subagents

Five dedicated subagents are shipped under `<plugin-root>/agents/`. The commands dispatch them with verbatim-injected ruleset and task context; the subagents emit JSON artifacts under `.claude/runs/{epic_id}/{task_id}/` validated against `schemas/run-phase.schema.json`.

```
                          +-----------+
   /001-plan ----------> | planner    |
                          +-----------+
                                |
                                v
                          +-----------+
   /002-implement -----> | implementer|   (TDD: RED -> GREEN -> REFACTOR)
                          +-----------+
                                |
                                v
                          +-----------+
   /003-verify-dod ----> | verifier   |   gates from stack.yaml.gates
                          +-----------+
                                |
                                +-- fail --+
                                |          v
                                |    +----------------------+
                                |    | feedback-implementer | <-- /005
                                |    +----------------------+
                                |          |
                                v          v
                          +-----------+    (loop back to verifier, cap 3)
   /004-code-review ---> | reviewer   |
                          +-----------+
                                |
                                +-- fail --> feedback-implementer
                                |
                                v
                          /006-merge -> /007-promote
```

The chain halts on the third failed feedback iteration. Re-planning is the human escalation path.

## File layout produced in your project

The plugin treats the following layout as the canonical Source-of-Truth. Everything is plain text and git-tracked except `.claude/runs/`.

```
your-project/
├── PRD.md                          # product brief, per-epic sections
├── CONTEXT.md                      # project glossary + decisions
├── docs/
│   ├── planning/
│   │   ├── epics.yaml              # epic registry
│   │   ├── epic-E-001-tasks.yaml   # tasks + Business scenarios (Gherkin)
│   │   └── SCENARIOS.md            # flat index, auto-regenerated
│   └── adr/
│       └── ADR-0001-*.md           # architecture decision records
├── .claude/
│   ├── stack.yaml                  # gates, test runners, branching, promote
│   ├── ruleset/                    # verbatim-injected into reviewer prompt
│   │   ├── code-style.md
│   │   ├── testing.md
│   │   ├── git-workflow.md
│   │   ├── deployment.md
│   │   └── ...
│   ├── runs/                       # gitignored. Per-task phase artifacts.
│   │   └── E-001/T-001/
│   │       ├── 02-implement.json
│   │       ├── 03-verify.json
│   │       ├── 04-review.json
│   │       └── 05-feedback.json
│   └── runs-archive/               # tar.gz snapshots, created by scripts/archive-epic-runs.sh
└── ...
```

`.claude/runs/` is **gitignored** by design. Phase artifacts are ephemeral execution traces, not project state. Project state lives in `docs/` and `PRD.md`.

## Customising

- **Ruleset.** Edit any file under `.claude/ruleset/`. The `reviewer` subagent reads the directory verbatim at every `/004-code-review` invocation. Add a new `.md` file and it is picked up automatically.
- **Stack overrides.** `.claude/stack.yaml` holds gate commands, test runners, branching convention, and the promote workflow name. Override paths and tool versions here — no plugin file needs editing.
- **Team preset switch.** Re-run `/000-prd-refine` and pick a different preset, or hand-edit the ruleset files. Presets are seeds, not constraints.
- **Schemas.** `schemas/*.json` validate `stack.yaml`, `epics.yaml`, and phase artifacts. Run `scripts/validate-schemas.sh` from your project root to lint everything.
- **Scripts.** Helper scripts ship under `<plugin-root>/scripts/`:
    - `archive-epic-runs.sh <epic-id>` — tar-gz `.claude/runs/<epic-id>/` on epic close-out.
    - `validate-schemas.sh` — validate project YAML/JSON against schemas.
    - `regen-scenarios.sh` — rebuild `docs/planning/SCENARIOS.md` from `epics.yaml`.
    - `inject-ruleset.sh` — emit the concatenated ruleset (used internally by subagent prompts).

## Discipline

- **Zero tolerance.** A gate is pass-or-fail. There is no warn level. Every Finding from `/003` or `/004` is a blocker until `/005` resolves it.
- **TDD entry-point.** Every task begins with a failing **domain test** (RED). Implementation only after RED. ATDD spec written after GREEN.
- **Step library + World pattern.** Acceptance scenarios use a project-owned step library plus a shared World object. Scenarios are domain-oriented; UI is not a concern at this layer.
- **Business scenarios.** Written in Gherkin under each task. Aggregated flat into `docs/planning/SCENARIOS.md`. Domain language only — no element selectors, no HTTP verbs in scenario names.
- **Status enum.** Tasks move through a fixed status set: `pending → in_progress → done → archived`. Failed tasks return to `in_progress` after `/005`.
- **No auto-merge, no force-push, no amend.** `/006-merge` opens the PR. Humans or platform automation own merge timing.

## Vocabulary

Project-specific glossary lives in `CONTEXT.md` (created on bootstrap). The plugin's own canonical terms:

- **Epic.** A PRD-level deliverable, id `E-NNN`. Decomposed into tasks by `/001-plan`.
- **Task.** A unit of work, id `T-NNN`, owned by a single epic. Drives one branch, one PR.
- **Phase.** One step of the per-task pipeline: implement, verify, review, feedback. Each phase emits one JSON artifact under `.claude/runs/`.
- **Gate.** A command declared in `stack.yaml.gates` that the verifier runs. Exit code is the truth.
- **Ruleset.** The set of `.md` files under `.claude/ruleset/`. Verbatim-injected into the reviewer prompt.
- **Finding.** A blocker emitted by `/003-verify-dod` or `/004-code-review`. Always actionable, always specific to a file/line or a gate.
- **Run.** The collection of phase artifacts for one task under `.claude/runs/{epic_id}/{task_id}/`.

## Known limitations (v0.1.0)

The v0.1 release ships the workflow surface end-to-end, but a handful of edges are deliberately unpolished. None block daily use; all are scheduled for v0.2+.

- **Archive rotation unbounded.** `.claude/runs-archive/` grows over time as `scripts/archive-epic-runs.sh` deposits tar-gz snapshots on epic close-out. There is no built-in pruning. Manual cleanup is required — delete old snapshots when the directory gets noisy. v0.2+ will add policy-driven rotation (size cap, age cap, or keep-last-N).
- **`stack.yaml.extras` size.** The free-form `extras` block is injected verbatim into every subagent prompt. Keep it small — under ~4 KB — or it will bloat every dispatch and burn context for no signal. v0.2+ may enforce a hard cap and warn on overflow.
- **Network call timeouts.** `/006-merge` and `/007-promote` shell out to `gh` / `glab` for the actual MR/PR/workflow trigger. The commands rely on the CLI's own default timeouts and do **not** wrap the calls in an external timeout. If the CLI hangs >120s, abort manually (Ctrl-C) and check network connectivity. Do not auto-retry — see the "Network timeout posture" notes in `commands/006-merge.md` and `commands/007-promote.md`.
- **Single-host concurrency.** Epic locks are local `mkdir`-based guards under `.claude/runs/.lock-<epic_id>/`. They are safe against concurrent runs on the same machine but **not** safe against NFS-shared `.claude/` directories or multi-host shared storage. If two machines mount the same project tree over NFS, the lock may not arbitrate correctly. Run from local disk for v0.1.
- **Ruleset section order.** Seven of the shipped process rules have non-canonical section ordering relative to the others. The reviewer subagent looks rules up by header rather than by position, so behaviour is unaffected — only readability varies. Re-ordering is a v0.2 cleanup.

## License

MIT
