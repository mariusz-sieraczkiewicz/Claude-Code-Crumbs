---
description: Solo deploy — green on main goes straight to prod
applyTo: "**/*"
---

# Deployment

> **Preset: solo**

**Principle:** small steps, fast feedback. The gates on `main` (lint, typecheck, domain-tests) are the only guard between you and production. Keep them ruthless.

## Environments

- **dev** — your laptop. Optional ephemeral preview if the platform supports it for free.
- **prod** — the live thing. Deployed from `main` HEAD after gates pass.
- **No staging environment by default.** A staging env you don't actually exercise is worse than no staging env. If you genuinely use one, add it back via `stack.yaml.promote.environments` and adopt the `small-team` preset.

## Promotion steps

1. `/002-implement` finishes the task on `main`, gates green.
2. CI builds and deploys to **prod** automatically on every push to `main` that has green gates.
3. Post-deploy: `pre_flight` check (health endpoint + a single smoke ping) declared in `stack.yaml.promote.pre_flight`.
4. `/007-promote` is normally a no-op for solo (deploy is push-driven). It exists only if you want a manual gate; in that case, `stack.yaml.promote.prod_workflow` points at the same workflow CI would run.

## Rollback / Approval gates

- **Approval to promote to prod: none.** Green CI is the gate.
- **Rollback strategy: redeploy previous tag.** CI tags every deploy `prod-<timestamp>-<sha>`. Roll back by re-running the deploy workflow with the previous sha.
- Time-to-rollback target: **< 5 minutes**, because you are the on-call and the responder.
- A failed `pre_flight` triggers auto-rollback if the platform supports it; otherwise you get a notification and roll back manually.

## Auto-invoke toggles

```yaml
auto_invoke_review: false
require_reviewers: 0
require_approvers_for_promote: 0
allow_commit_to_main: true
require_signed_commits: false
auto_deploy_staging: false
auto_deploy_prod: true
require_change_window: false
require_change_ticket: false
journey_gate_required: false
auto_invoke_verify: true                  # gates still run even though review is skipped
branch_name_pattern: "epic/{epic_id}-{slug}"   # informational only; allow_commit_to_main=true means usually no branch is created
```

`journey_gate_required: false` reflects the lack of a staging env to run Journey smoke against. Run Journeys locally on the dev box before risky changes.

## Mechanical enforcement

- CI workflow on push to `main`: gates → build → deploy → `pre_flight`. Single pipeline, no manual approvals.
- Tagging convention (`prod-<ts>-<sha>`) lives in the CI workflow.
- Health-check command in `stack.yaml.promote.pre_flight`.
- Optional: feature flags for risky deploys, so you can dark-launch without a second environment.

## Subagent check

`verifier` (`/003-verify-dod`):
- Domain-tests green.
- ATDD spec for the task written.
- No uncommitted changes that would land in the next push.

`reviewer` (`/004-code-review`), when invoked:
- Migrations are forward-compatible (no flag-day schema swaps without a clear rollback recipe).
- Feature flags wired so partial rollout is possible.
- No secrets in the diff.

## Examples

### Good

```
# /002-implement finishes, commits to main, pushes
# CI: lint OK → typecheck OK → domain-tests OK → build OK → deploy
# pre_flight: health endpoint OK
# Done. Live in ~3 min.
```

### Bad

```
# Pushing to main with a known-red domain-test "I'll fix it after"
# Manual deploy from laptop via scp / kubectl apply
# Deploying a migration with no rollback path on a Friday at 5pm
# Disabling gates because "they're slowing me down"
```

## Anti-patterns

- Treating prod as a test environment. The cost of being your own ops team is being your own incident commander.
- Skipping `pre_flight` because "it's always fine".
- Bundling 5 days of work into one push because you forgot to commit incrementally.
- Hand-rolled deploy scripts that only work on your laptop.
- No tagging — when something breaks, you can't roll back to "last good".
- Adding a staging env on paper that you never actually deploy to.

## Cross-refs

- `git-workflow.md` — solo commits land on `main` directly; this file picks up from there.
- `monitoring.md` — your alerts page *you*. Set them up before they're needed.
- `error-handling.md` — typed errors and a panic-safe boundary matter even more without a review buddy.
