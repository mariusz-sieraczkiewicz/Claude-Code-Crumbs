---
description: Single-dev workflow — commit to main, no PR, no review
applyTo: "**/*"
---

# Git Workflow

> **Preset: solo**

**Principle:** you are the only voice in the room. Discipline replaces ceremony — Conventional Commits and a clean local tree do the work that reviewers would do on a team.

## Branching

- Default branch: `main`. **Commits to `main` are allowed and expected.**
- Optional short-lived branches when you want a checkpoint for an experiment:
  - `wip/<slug>` — discardable spike.
  - `feat/<slug>` — only when a change spans days and you want a graveyard if it dies.
- No `develop`, no release branches.
- Branches that survive the experiment get rebased onto `main` and fast-forwarded, not merged with a merge commit.

## Commit conventions

Conventional Commits, same regex as the baseline, enforced locally by `lefthook` `commit-msg`:

```
<type>(<optional-scope>): <imperative description>
```

Rules:
- One concern per commit — atomicity matters even more solo, because future-you is the reviewer.
- Write the *why* in the body whenever the subject doesn't carry it. You will not remember.
- Signed commits optional.
- `git commit --amend` and `git rebase -i` on local-only history are encouraged — clean up before pushing.
- Once a commit is pushed to `origin/main`, treat it as immutable.

## Pull/Merge request flow

**There is no PR flow.** Implications for the plugin:
- `/002-implement` runs the TDD loop and commits straight to `main` (or to the branch you happen to be on).
- `/006-merge` is effectively a **no-op**: it tags the commit with the task id (`E-007/T-3`) for traceability and exits. It does not call `gh pr create`.
  - Tag format: `<epic_id>/<task_id>` (e.g. `E-007/T-014`). Implemented by `/006-merge` Phase 0 step 2 when `pr_required: false` AND `tag_task_commits: true`. Existing tags are skipped silently (idempotent).
- `/004-code-review` still runs as a self-review subagent — it just has no human reviewer to hand off to. Findings still block DoD.

## Auto-invoke toggles

```yaml
auto_invoke_review: false
require_reviewers: 0
require_approvers_for_promote: 0
allow_commit_to_main: true
require_signed_commits: false
allow_force_push_to_main: true
squash_merge: false
delete_branch_on_merge: true
pr_required: false
tag_task_commits: true
auto_invoke_verify: true                  # gates still run even though review is skipped
branch_name_pattern: "task/{task_id}-{slug}"   # informational only; allow_commit_to_main=true means usually no branch is created
```

`auto_invoke_review: false` — solo dev opts out of automatic `/004-code-review` after `/002-implement`. Run it manually when you want a second pair of (LLM) eyes.

## Mechanical enforcement

- `lefthook`:
  - `commit-msg` — Conventional Commits regex.
  - `pre-push` — run gates (lint, typecheck, domain-tests). Solo is the one preset where you might bypass with `--no-verify`; don't make a habit of it.
- **No GitHub branch protection on `main`** (would block your own commits). If you accidentally enable it, you'll be stuck.
- `.gitignore` does the heavy lifting for "no secrets / no artefacts" — keep it tight.

## Subagent check

`reviewer` (`/004-code-review`), when invoked, checks:
- Conventional Commits compliance.
- One-concern-per-commit.
- No secrets / no build artefacts in the diff.
- That you actually wrote a useful commit body for non-trivial changes (anti-laziness check tuned higher for solo).

`verifier` (`/003-verify-dod`) checks: clean working tree, ATDD spec written, domain-tests green.

## Examples

### Good

```
# /002-implement runs, finishes the task, commits:
git commit -m "feat(today): add 1-tap mark-done with undo until midnight"
git push
/006-merge   # tags origin/main with E-007/T-3, exits
```

### Bad

```
git commit -am "stuff"                              # not Conventional Commits
git commit -am "feat: add foo and fix bar"          # two concerns
git push --force origin main                        # technically allowed; almost always a mistake
# Skipping /003-verify-dod because "it's just me"   # the gate exists to catch your own mistakes
```

## Anti-patterns

- Treating "solo" as "no rules". Discipline degrades fastest with no second voice.
- Letting `main` go red for hours because no CI shouts at you.
- Forgetting to push for days — laptop disk failure becomes a project-ending event.
- Mixing experimental spikes with shipping commits on `main`. Spike on `wip/<slug>` and rebase clean (or drop) before pushing.
- Disabling `/004-code-review` permanently. Re-enable it the moment a second contributor joins.
- Writing "fix" without a body — future-you will not know what was broken.

## Cross-refs

- `deployment.md` — solo deploys straight from `main` to prod after green gates; no staging gate.
- `testing.md` — domain-tests and ATDD specs are your only safety net here.
- `documentation.md` — keep ADRs honest; you are the only audit trail.
