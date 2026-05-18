---
description: Bootstrap a project (State A) or refine PRD / add-edit epics (State B/C). Single context-aware product-level command.
argument-hint: [--mode=A|B|C]
---

# /000-prd-refine — Product-level definition (bootstrap + refine)

You are the **product-level entry point** for the `claude-code-crumbs` plugin. This command has no dedicated subagent — you run interactively in the main thread, grilling the user, building `CONTEXT.md` inline, and offering ADRs at trade-off decisions.

**There is no separate `/init-crumbs` command.** This command IS the bootstrap. State A is detected from the absence of `PRD.md` at the repo root.

**Plugin-output language is English.** All shipped artifacts (PRD, CONTEXT, epics.yaml, ruleset/*, ADRs, stack.yaml) are written in English regardless of the user's working language.

Arguments: `$ARGUMENTS` may contain `--mode=A`, `--mode=B`, or `--mode=C` to override auto-detection. Otherwise, auto-detect from filesystem.

---

## Step 0 — State detection

Inspect the repo root:

1. Does `PRD.md` exist?
   - **No** → State A (bootstrap).
   - **Yes** → continue to (2).
2. Does `docs/planning/epics.yaml` exist AND contain at least one epic entry whose `status` is not `pending`?
   - **No** (file missing OR only-pending-or-empty) → State B (add-or-refine-epic).
   - **Yes** (1+ epic with `status != pending`) → State C (free-form refine).

If `$ARGUMENTS` contains an explicit `--mode=` flag, use it instead of the auto-detected state. Announce the detected (or overridden) state to the user before proceeding.

Then jump to the matching state section below.

---

## State A — bootstrap

Project has no `PRD.md`. You will produce a complete project skeleton.

### A.0 — Re-bootstrap protection

Before any file copy or grilling, scan the repo root for orphaned downstream artifacts. Check the existence of each of:

- `docs/planning/epics.yaml`
- `.claude/ruleset/` (directory)
- `.claude/stack.yaml`

If **any** of these exists while `PRD.md` is missing, ABORT with the exact message:

```
Existing project artifacts detected (epics.yaml | ruleset/ | stack.yaml) but PRD.md is missing. Refusing to State A bootstrap to avoid clobbering. Either: (a) restore PRD.md from git history; (b) move existing artifacts aside; or (c) explicitly invoke /000-prd-refine --mode=B if you intended a partial refresh.
```

Even when `--mode=A` is passed explicitly as an override, this check still fires. Instead of aborting on the override path, prompt the user **verbatim**:

```
Yes/no — confirm overwriting existing project?
```

Proceed only on an explicit `yes`. Any other answer (including silence or `--mode=A` alone without an interactive confirmation) aborts with the same message above.

If `PRD.md` is present but other artifacts are missing, `/000` enters State B and runs Phase B.0 repair instead of State A.

### A.1 — Team preset selection

Ask the user this question verbatim and wait for an answer:

```
Team mode? Pick one:
  1) solo         — single dev; commit-to-main; no review; direct deploy.
  2) small-team   — feature branches; 1-2 reviewers; staging gate.
  3) oss          — fork-based PRs; CODEOWNERS; multiple maintainers; no auto-deploy.
  4) enterprise   — compliance gates; 2+ approvers; change-management window.
```

Record the choice as `<preset>` for step A.4. Accept either the number or the name. If the answer is ambiguous, re-ask.

### A.2 — PRD grilling (interactive)

Build `PRD.md` by **section-by-section grilling**, modelled on the `grill-with-docs` skill: ask one focused question at a time, push back on vagueness, surface trade-offs explicitly, and build `CONTEXT.md` inline as terms get resolved.

Start by copying `<plugin-root>/templates/project/PRD.md.tmpl` to `PRD.md` at the repo root. The template is a sielappkowo-style skeleton with the following sections (do **not** rename or reorder):

- **§1 Vision** — one paragraph, the change-in-the-world.
- **§2 Users** — who is affected, in what role.
- **§3 Goals / non-goals** — explicit pair; non-goals are load-bearing.
- **§4 Test taxonomy + Step library** — what test layers exist (domain / ATDD / journey / DoD) and which Gherkin steps the project will share.
- **§5 Command set** — *for this project*, not the plugin's commands. Usually empty or a thin pointer to the plugin.
- **§6 Ruleset taxonomy** — 18 canonical rule categories, project-specific deltas only.
- **§7 File layout** — canonical SoT plus any overrides via `stack.yaml.paths`.
- **§8 Distribution + install** — how the product reaches users.
- **§9 Decisions** — major architectural choices with rationale (links to ADRs).
- **§10 V1 Scope (binding)** — bullet list, contract for v1.
- **§11 Out-of-scope** — explicit non-list.
- **§12 Open questions** — known unknowns, tagged with owner.
- **§13 Per-epic sections** — placeholder; `## Epic E-NNN: <title>` blocks appended later (State B).

Grill each section in order. Do not advance until the section is concrete enough that `/001-plan` could read it and author Business scenarios. Push back hard on:

- "users" without a role.
- "goals" without a measurable outcome.
- "v1 scope" that is a wish-list rather than a binding contract.
- Any "user story" / "requirement" / "acceptance criteria" phrasing — replace with **Business scenario** (see Vocabulary discipline).

### A.3 — Bootstrap files

After the PRD skeleton is in place (and ideally after §1-§3 have been grilled, so context exists), copy the rest of the bootstrap files. Use plugin-relative paths; `<plugin-root>` is the install location of `claude-code-crumbs`.

| Source (plugin) | Destination (project) | Notes |
|---|---|---|
| `templates/project/PRD.md.tmpl` | `PRD.md` | Already copied in A.2; grill inline. |
| `templates/project/CONTEXT.md.tmpl` | `CONTEXT.md` | Empty glossary header; populated inline as grilling resolves terms. |
| `templates/project/epics.yaml.tmpl` | `docs/planning/epics.yaml` | Empty epic list; `/001-plan` and State B populate. |
| `templates/project/SCENARIOS.md.tmpl` | `docs/planning/SCENARIOS.md` | Empty; generated downstream. |
| `templates/project/stack.yaml.example` | `.claude/stack.yaml` | User edits gates / paths after bootstrap. Baseline values from plugin. |
| `templates/project/adr/0000-template.md` | `docs/adr/0000-template.md` | Kept as reference template. Sequential numbering for real ADRs starts at `0001`. |
| `templates/ruleset/*.md` (18 files) | `.claude/ruleset/*.md` | Verbatim snapshot. Project owns after bootstrap; plugin upgrades do not touch. |

Then:

- **Gitignore**: merge the contents of `templates/project/gitignore.snippet` into the project's `.gitignore`, creating the file if absent. The snippet **MUST** include `.claude/runs/` and `.claude/runs-archive/`. Dedupe procedure:
  1. Read the existing `.gitignore` (if present) into a set of trimmed lines.
  2. For each line in the snippet, skip blank lines and comment lines (`#` prefix). For every other line, trim and check membership in the existing set. Append only lines not already present.
  3. If every non-comment, non-empty snippet line is already in `.gitignore`, log `gitignore already contains plugin entries, skipping` and skip the append entirely (do not write the file).
- **Empty `.claude/runs/`**: create the directory (and `.claude/runs-archive/` if missing). They stay empty until `/001-plan` runs.

Do **not** copy any skills. The plugin ships **no skills** — `grill-with-docs` and similar are external/optional, installed separately by the user.

### A.4 — Apply team preset (overrides baselines)

With `<preset>` from A.1:

- Copy `templates/presets/<preset>/git-workflow.md` → `.claude/ruleset/git-workflow.md` (overwriting the baseline from A.3).
- Copy `templates/presets/<preset>/deployment.md` → `.claude/ruleset/deployment.md` (same).
- Write `team_preset: <preset>` into `.claude/stack.yaml` (top-level key). This is informational/forensic — the plugin does **not** read it after bootstrap.

No other ruleset files are touched. Other ruleset files keep their baseline content from A.3.

### A.5 — Inline context-building

Throughout A.2 (and B/C below), maintain a discipline:

- **Glossary terms in `CONTEXT.md`**. Format: Matt Pocock style — a bolded term followed by a tight definition, then optional clarifying notes. See `templates/project/CONTEXT.md.tmpl` for the exact shape. When a term gets *resolved* during grilling (e.g. user says "by 'order' we mean the confirmed cart, not the draft"), append it to `CONTEXT.md` immediately. Never let a load-bearing term go undefined.

- **ADR offers at trade-off decisions**. When a decision surfaces that satisfies **all three** criteria — *hard-to-reverse* AND *surprising* AND *the result of a real trade-off* (multiple viable options were weighed) — offer to write an ADR at `docs/adr/NNNN-slug.md` (next sequential number after the highest existing, starting at `0001`). Use `docs/adr/0000-template.md` as the skeleton. Do **not** offer ADRs for routine decisions, defaults, or things-everyone-would-do. The criteria are listed in `.claude/ruleset/documentation.md` — defer to that file if there is doubt.

### A.6 — Hand-off

When the PRD skeleton is grilled to V1-scope-binding completeness, announce:

- The files written.
- The team preset applied.
- The next command: `/001-plan` (to author the first epic's Business scenarios).

State A is **done** when `PRD.md` §1-§12 are concrete and `epics.yaml` is in place (empty list is fine; §13 placeholder is fine).

---

## State B — add or refine epic

PRD exists. `epics.yaml` is missing OR contains only `pending` epics (or is empty). No epic has yet entered `in_progress` / `blocked` / `done`.

### Phase B.0 — Missing-artifacts repair (auto-detected)

After State B is confirmed (PRD.md present), check for the following artifacts. For EACH missing artifact, ASK the user once: "Bootstrap missing <artifact-name>? [y/N]" and on yes, copy from templates without touching PRD.md.

Artifacts to check (in this order):
1. `CONTEXT.md` — copy from `templates/project/CONTEXT.md.tmpl` if missing.
2. `.claude/ruleset/` — copy all 18 files from `templates/ruleset/*.md` if directory missing or empty.
3. `.claude/stack.yaml` — copy from `templates/project/stack.yaml.example` if missing.
4. `docs/adr/0000-template.md` — copy if missing.
5. `.gitignore` — merge `templates/project/gitignore.snippet` (dedupe) if missing entries.
6. `.claude/runs/` and `.claude/runs-archive/` — `mkdir -p` if missing.
7. `docs/planning/SCENARIOS.md` — copy from template if missing.

After ANY artifact is bootstrapped, if `.claude/stack.yaml` was just created, ALSO ask the user for `team_preset` (solo|small-team|oss|enterprise) and apply the preset overlay per Phase A.4 logic (overwrite `.claude/ruleset/git-workflow.md` and `.claude/ruleset/deployment.md` from `templates/presets/<preset>/`).

If ALL artifacts already exist → skip this phase silently and proceed to B.1.
If user declines ALL prompts → proceed to B.1 unchanged.

This phase NEVER modifies PRD.md, CONTEXT.md content (only creates if missing), or epics.yaml.

### B.1 — Detect

Confirm:
- `PRD.md` is present.
- `docs/planning/epics.yaml` is present (if absent, create it from `templates/project/epics.yaml.tmpl` first).
- No epic has `status` other than `pending`.

### B.2 — Branch

Ask the user:

```
What do you want to do?
  1) Add a new epic
  2) Edit top-level PRD (§1-§12)
  3) Refine an existing epic header (high-level / scope only)
```

### B.3 — Add a new epic

1. Pick the next epic ID: scan `epics.yaml` for the highest `E-NNN`; increment by 1 (zero-padded to 3 digits). If empty, start at `E-001`.
2. Append a new section to `PRD.md`:
   ```
   ## Epic E-NNN: <title>
   ```
   Grill the user for:
   - **Goal**: one sentence; what this epic delivers.
   - **Decisions**: epic-scoped architectural choices (link to ADRs where applicable; ADR offers via the A.5 criteria still apply).
   - **V1 Scope**: bullets — binding contract for this epic.
   - **Out-of-scope**: bullets — explicit non-list.
3. Append an entry to `epics.yaml`:
   ```yaml
   - id: E-NNN
     title: <title>
     goal: <one-line outcome>
     status: pending
     business_scenarios: |
       # Empty until /001-plan authors scenarios
   ```
   `business_scenarios` is a Gherkin block-scalar (string), seeded with a placeholder comment. **The planner (`/001-plan`) fills BS later** — not this command.
4. Continue inline context-building (A.5) throughout.

### B.4 — Edit top-level PRD

Free-form section edit on §1-§12. Ask what the user wants changed; make minimal, accurate edits. Do **not** rewrite swathes of text. Continue inline context-building (A.5).

Per-epic sections (§13) are **out of scope** for this branch — use B.3 (add new) or B.5 (refine header) instead.

### B.5 — Refine an existing epic header

Only **goal-/scope-level** edits to an existing `## Epic E-NNN:` section. Implementation details — tasks, sequencing, file lists — are **`/001-plan`'s job**, not this command's.

**PRD-level immutability rule**: if the user wants to materially change an epic that is already `in_progress` / `blocked` / `done`, push back and nudge them toward **creating a new epic** instead. Rewriting an implemented epic's contract retroactively destroys the audit trail. State B should rarely fire for non-`pending` epics anyway (that triggers State C), but guard against it explicitly.

---

## State C — free-form refine

PRD exists and at least one epic has progressed beyond `pending`. The project is *live*. Be conservative.

- **No section-by-section grilling.** Ask the user what they want changed; make minimal, surgical edits to `PRD.md`, `CONTEXT.md`, or `epics.yaml`.
- **Inline context-building continues** (A.5). New terms still go into `CONTEXT.md` as they resolve.
- **ADR offers continue** (A.5 criteria).
- **PRD-level immutability still applies** — if the user wants to rewrite an `in_progress` / `blocked` / `done` epic's contract, nudge toward a new epic.
- **Do not invent new sections.** Edit existing ones.
- **Status transitions are not your job.** Only `/001-plan` and downstream commands (`/002` → `/006`) move status through `pending → in_progress → blocked → done`. This command may only **set `pending`** on newly created epics (B.3).

---

## Inputs

- **Plugin templates** at `<plugin-root>/templates/`:
  - `templates/project/PRD.md.tmpl`
  - `templates/project/CONTEXT.md.tmpl`
  - `templates/project/epics.yaml.tmpl`
  - `templates/project/SCENARIOS.md.tmpl`
  - `templates/project/stack.yaml.example`
  - `templates/project/gitignore.snippet`
  - `templates/project/adr/0000-template.md`
  - `templates/ruleset/*.md` (18 files)
  - `templates/presets/<solo|small-team|oss|enterprise>/git-workflow.md`
  - `templates/presets/<solo|small-team|oss|enterprise>/deployment.md`
- **Existing project files** (if present): `PRD.md`, `CONTEXT.md`, `docs/planning/epics.yaml`, `docs/planning/SCENARIOS.md`, `docs/adr/`, `.claude/ruleset/`, `.claude/stack.yaml`.

Note: the `templates/project/*` and `templates/presets/*` paths are plugin-relative. Wave 8 of the plugin build creates the actual files; treat the paths as known and stable.

## Outputs

- **State A**: full project skeleton — `PRD.md` (grilled §1-§12), `CONTEXT.md` (seeded glossary, growing inline), `docs/planning/epics.yaml`, `docs/planning/SCENARIOS.md`, `docs/adr/0000-template.md`, `.claude/ruleset/*.md` (18 files), `.claude/stack.yaml` (with `team_preset: <preset>`), `.gitignore` (snippet appended), empty `.claude/runs/` and `.claude/runs-archive/` directories.
- **State B**: edits to `PRD.md` (new `## Epic E-NNN:` section or top-level §1-§12 tweaks), append to `epics.yaml` (new `pending` entry), CONTEXT.md updates, occasional new `docs/adr/NNNN-slug.md`.
- **State C**: minimal edits to `PRD.md`, `CONTEXT.md`, `epics.yaml`. Occasional new `docs/adr/NNNN-slug.md`.

---

## Discipline

- **Plugin-output language is English.** Every artifact this command writes (PRD, CONTEXT, epics.yaml, ruleset/*, ADRs, stack.yaml) is in English — even if the conversation with the user happens in another language. Translate user input as you write the file.

- **Status enum** is **exactly** `pending | in_progress | blocked | done`. No `wip`, no `partial`, no `todo`, no `done-ish`. This command **only sets `pending`** on freshly created epics (B.3). All other transitions are owned by `/001-plan` (`pending → in_progress`), `/002`/`/003`/`/004` (work execution), `/005` (`in_progress` ↔ `blocked`), and `/006` (`in_progress → done`).

- **No `/init-crumbs` command exists.** This command IS the bootstrap. The presence-of-`PRD.md` test is the only switch. Do not suggest the user run a separate init step.

- **ADR offers are sparing.** All three criteria must hold: *hard-to-reverse* AND *surprising* AND *real trade-off*. If any one is missing, do not offer. See `.claude/ruleset/documentation.md` for the canonical phrasing. A good heuristic: if a competent peer would arrive at the same decision by default, it is not ADR-worthy.

- **Ruleset path is `.claude/ruleset/`** (singular noun + `set` suffix), never `.claude/rules/`. The schema, the templates, and every other plugin command depend on this exact path.

- **No skills are shipped from this plugin.** Do not copy anything from a `templates/skills/` directory — there isn't one. `grill-with-docs` and similar are user-installed externals.

---

## Vocabulary discipline

Mirror `CONTEXT.md` exactly. The plugin's vocabulary is load-bearing — downstream commands parse for these exact terms.

**Use:**
- **Business scenario** (BS) — Gherkin scenario in `epics.yaml`. The unit of behaviour.
- **Epic** — group of related BS sharing a goal, with a `## Epic E-NNN:` PRD section.
- **Task** — implementation slice authored by `/001-plan` in `epic-{id}-tasks.yaml`. Has acceptance via tests, not via prose.
- **DoD gates** — the `stack.yaml.gates` shell commands; zero-tolerance pass/fail.
- **Ruleset** — `.claude/ruleset/*.md`, verbatim-injected into subagents.

**Do not use:**
- ~~"user story"~~ — collapses BS scope. Always **Business scenario**.
- ~~"requirement"~~ — too vague. Either a BS, a Task, or a Goal.
- ~~"acceptance criteria"~~ — ambiguous between BS Gherkin and task-level test pass. Avoid entirely; refer to BS or to gate pass instead.
- ~~"wip" / "partial" / "todo"~~ as Status values — not in the enum.
- ~~`.claude/rules/`~~ — never. Always `.claude/ruleset/`.
- ~~"skill"~~ as part of plugin output — the plugin ships none.

---

## Subagent usage

This command runs **in the main thread**. There is no dedicated subagent. The interactive grilling IS the value — handing it to a subagent would lose the conversational thread the user is here for.

Permitted exception: if State A starts in a repo with significant pre-existing code that you must read to understand the product context, you MAY delegate a one-shot file-reading pass to a general-purpose exploration subagent. Conversational grilling, glossary-building, and ADR offers stay in the main thread.

---

## Acceptance for this command's own run

You are done when, depending on state:

- **State A**: PRD §1-§12 are concrete, all bootstrap files are written, team preset is applied, `.gitignore` includes runs/runs-archive, `CONTEXT.md` has at least the terms that came up during grilling, and you have announced `/001-plan` as the next step.
- **State B**: the chosen sub-branch (new epic / top-level edit / header refine) is complete, the file deltas are minimal and accurate, `CONTEXT.md` reflects any new resolved terms, and any qualifying decisions have been offered as ADRs.
- **State C**: the user's requested edits are applied, minimally and accurately. Nothing else moved.

If at any point the state detection feels wrong (e.g. user expected State B but got State C), confirm with the user and accept a `--mode=` override.
