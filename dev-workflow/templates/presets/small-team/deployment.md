---
description: Environments, promotion pipeline, rollback policy
applyTo: "**/*"
---

# Deployment

> **Preset: small-team**

**Principle:** every merge to `main` is a candidate for production, but a human promotes it through staging first.

## Environments

- **dev** — ephemeral, per-branch preview if the platform supports it. Optional.
- **staging** — single shared environment, always tracking `main` HEAD. Production-like data shape (anonymised). Runs **Journey** smoke gates on each deploy.
- **prod** — public. Promoted from a known-good staging build, never from `main` directly.

`stack.yaml.promote.environments` lists the actual env names; `/007-promote` reads it.

## Promotion steps

1. Merge to `main` → CI builds, tags artefact `build-<short-sha>`, deploys to **staging** automatically.
2. Staging runs Journey smoke gates (`tests/journeys/` or stack equivalent) against real infrastructure.
3. On green Journeys, the build is marked `promotable`.
4. Human invokes `/007-promote` (or the platform workflow it wraps, e.g. `gh workflow run promote-prod.yml -f build=<sha>`).
5. Plugin does not orchestrate deploy — it triggers the pre-existing platform workflow declared in `stack.yaml.promote.prod_workflow`.
6. Post-promote: `pre_flight` checks (health endpoint, smoke ping) declared in `stack.yaml.promote.pre_flight` must pass.

## Rollback / Approval gates

- **Approval to promote to prod: 1 person** (anyone on the team) clicks the workflow approval.
- **Rollback strategy: redeploy previous tag.** Every prod deploy tags `prod-<timestamp>-<sha>`; rolling back = re-run promote workflow with `build=<previous-sha>`.
- Time-to-rollback target: **< 10 minutes** from "page" to "previous version live".
- Failed Journey on staging blocks promotion — the build never reaches `promotable`.
- No promotion during active incident (SEV-1/SEV-2 open).

## Auto-invoke toggles

```yaml
auto_invoke_review: true
require_reviewers: 1
require_approvers_for_promote: 1
allow_commit_to_main: false
require_signed_commits: false
auto_deploy_staging: true
auto_deploy_prod: false
require_change_window: false
require_change_ticket: false
journey_gate_required: true
auto_invoke_verify: true
branch_name_pattern: "epic/{epic_id}-{slug}"
```

## Mechanical enforcement

- `stack.yaml.promote.staging_workflow` and `prod_workflow` point at concrete CI workflows (GitHub Actions / GitLab CI).
- Branch protection blocks merging without green `journey-smoke-staging` status check.
- Tagging convention (`build-<sha>`, `prod-<ts>-<sha>`) enforced in the CI workflow, not in the plugin.
- Health-check / smoke-ping commands listed in `stack.yaml.promote.pre_flight` run after deploy; nonzero exit auto-rolls back via platform workflow.

## Subagent check

`verifier` (`/003-verify-dod`) confirms that:
- Domain-tests pass locally.
- ATDD spec for the task has been written.
- No pending deploy of a previous task is blocking the pipeline.

`reviewer` (`/004-code-review`) confirms that:
- Migrations are forward-compatible (if `data-modeling.md` flags any).
- Feature flags are wired correctly for staged rollout.
- No environment-specific secrets are hardcoded.

## Examples

### Good

```
# /002-implement finishes T-3 → /006-merge opens PR → squash-merge to main
# CI auto-deploys to staging, runs Journey smoke
# Slack notification: "build-a1b2c3d is promotable"
/007-promote prod --build=a1b2c3d   # triggers gh workflow run promote-prod.yml
# Approve workflow → prod live in ~4 min → pre_flight green
```

### Bad

```
# Direct deploy to prod from a feature branch, skipping staging
# Promoting a build that has a red Journey on staging
# Hot-patching prod by SSH-ing into a server
# Rolling forward with another commit instead of rolling back a clearly broken release
```

## Anti-patterns

- Deploying on Friday afternoon with no rollback rehearsed.
- Bundling DB migration + code change in the same release without a backout plan.
- Manual `scp` / `kubectl apply` from a developer laptop.
- Treating staging as "test env that's allowed to be broken" — staging must stay green or promotion stalls.
- Skipping `/007-promote` and clicking deploy buttons by hand — loses the audit trail.
- Promoting from `develop` or a feature branch.

## Cross-refs

- `git-workflow.md` — the merge flow that produces the build being promoted.
- `monitoring.md` — alerts triggered by failed `pre_flight` checks.
- `observability.md` — trace IDs that let the team confirm a promote landed cleanly.
- `security.md` — secret rotation cadence relative to deploys.
