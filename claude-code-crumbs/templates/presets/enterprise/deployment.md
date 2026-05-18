---
description: Compliance-gated promotion — change-management window, 2+ approvers, full audit trail
applyTo: "**/*"
---

# Deployment

> **Preset: enterprise**

**Principle:** production change is a privileged event. It happens inside an approved window, with multi-party approval, full audit logging, and a rehearsed rollback. Nothing about a deploy is implicit.

## Environments

- **dev** — engineer machines + ephemeral preview envs per PR (where the platform allows).
- **ci** — build and run gates per PR.
- **staging** — production-like, behind the corporate network. Tracks `main` HEAD on a schedule (not on every commit). Used for integration testing and acceptance by stakeholders.
- **pre-prod / canary** — narrow slice of production traffic (or shadowed traffic). Used for the final smoke before fan-out.
- **prod** — fan-out to full traffic.

All env names declared in `stack.yaml.promote.environments`. Each environment owns its own secrets store, audit log, and change-window calendar.

## Promotion steps

1. PR merges to `main` after the full git-workflow gate (2+ approvers, signed commits, CM ticket linked).
2. CI builds a **signed, attested artefact** tagged `build-<sha>` and pushes to the internal registry. SBOM + provenance attestation attached.
3. **Staging deploy** runs automatically (or on a schedule) — full Journey smoke gate against staging data.
4. Stakeholder acceptance recorded against the CM ticket (UAT sign-off).
5. **Change-window check**: `/007-promote` to canary / prod is **rejected outside the approved change window** (typically business hours, Tue-Thu, excluding declared freeze periods).
6. **Approval to promote**: 2+ approvers click "approve" on the deployment workflow. Approvers must be distinct from the merge approvers (separation of duty).
7. **Canary deploy**: artefact rolled out to canary slice; canary smoke + SLO comparison run for a defined soak period (e.g. 30 min).
8. **Fan-out**: progressive rollout to full prod (e.g. 5% → 25% → 100%) with automated rollback if SLOs regress.
9. Post-deploy: `pre_flight` checks + a deployment record written to the CM ticket (artefact sha, approvers, timestamps, SLO snapshot).

## Rollback / Approval gates

- **Approval to promote to prod: 2+ humans**, recorded in the workflow + the CM ticket.
- **Change window**: business hours only, Tue-Thu by default. Configurable per project via `stack.yaml.extras.change_window`.
- **Freeze periods**: declared by org calendar (end-of-quarter, holidays, major incidents). `/007-promote` refuses during a freeze; emergency bypass requires VP-level approval + an ADR-equivalent post-mortem.
- **Rollback strategy**:
  - Automated: SLO breach during canary / fan-out triggers automatic rollback to the previous tag.
  - Manual: any approver may invoke `gh workflow run rollback-prod.yml -f to=<previous-sha>`; same audit trail as forward deploy.
  - Tagging: `prod-<timestamp>-<sha>-<release-id>` makes "previous good" unambiguous.
- **Time-to-rollback target**: < 15 minutes from alert to traffic restored to previous version.
- **Post-incident**: every prod rollback generates a CM ticket of its own and a scheduled post-mortem.

## Auto-invoke toggles

```yaml
auto_invoke_review: true
require_reviewers: 2
require_approvers_for_promote: 2
allow_commit_to_main: false
require_signed_commits: true
auto_deploy_staging: true
auto_deploy_prod: false
require_change_window: true
require_change_ticket: true
journey_gate_required: true
canary_required: true
require_signed_artefacts: true
require_sbom: true
require_provenance: true
separation_of_duty: true
block_self_approval: true
auto_invoke_verify: true
branch_name_pattern: "task/{ticket_id}/{task_id}-{slug}"   # nested under change-management ticket id
```

## Mechanical enforcement

- **CI workflows** declared in `stack.yaml.promote.{staging_workflow, prod_workflow, rollback_workflow}`. Plugin only triggers them; the workflows own deploy logic, signing, attestation.
- **Artefact signing**: GPG / Sigstore / corporate KMS. Unsigned artefacts cannot be promoted (admission controller in the registry refuses them).
- **SBOM** (CycloneDX / SPDX) generated and stored per release.
- **Provenance** (SLSA Level 3+) attestation links source commit + build environment + artefact hash.
- **Change-window gate**: workflow step queries the org calendar API; outside window = job fails with "change-window-closed".
- **Ticket-status gate**: workflow checks the linked CM ticket is in `approved-for-deployment` state.
- **Approval gate**: GitHub deployment environments / GitLab manual approvals configured with `required_reviewers: 2` and `prevent_self_review: true`.
- **Audit pipeline**: every promote / rollback event streamed to SIEM with actor, artefact sha, ticket id, approvers, timestamp.
- **Separation of duty**: workflow rejects if any of the 2 deploy-approvers also appears in the PR-approver list for the included commits.

## Subagent check

`verifier` (`/003-verify-dod`):
- All gates green, including SAST / SCA / secret-scan / license-scan.
- Domain-tests + ATDD spec present.
- Journey smoke green on staging.
- Linked CM ticket in `approved-for-deployment` state.
- SBOM + provenance attached to the artefact.

`reviewer` (`/004-code-review`):
- Migrations are forward-compatible AND have a tested rollback procedure.
- Feature flags wired for progressive rollout (no flag-day cutovers without explicit ADR).
- No new secrets committed; all new config goes through the secrets manager.
- IaC `plan` output reviewed; no unintended infra drift.
- Logs / traces respect PII rules per `observability.md`.

## Examples

### Good

```
# PR with CHG-12345 merged Wed 10:00 by 2 CODEOWNERS + security review
# Build build-a1b2c3d signed, SBOM + provenance attached
# Auto-deploy to staging at 11:00; Journey smoke green; UAT sign-off on CHG-12345 by 14:00
# /007-promote prod --build=a1b2c3d
#   change-window: Wed 15:00 -> within window OK
#   ticket-status: approved-for-deployment OK
#   approvers required: 2 (distinct from merge approvers)
#   approved by @alice and @bob at 15:05
# Canary at 15:08, 30-min soak, SLO comparison: pass
# Fan-out 5% -> 25% -> 100% completes 16:15
# pre_flight green; deployment record written to CHG-12345
```

### Bad

```
# Promoting Friday 17:30 (outside change window) "just this once"
# Same engineer approving the PR and approving the deploy (separation-of-duty violation)
# Deploying an unsigned artefact via a hand-edited workflow file
# Skipping canary because "the change is small"
# Rolling forward through a SEV-1 instead of rolling back to known-good
# Bundling a schema migration with an app change in the same release with no rollback path
```

## Anti-patterns

- "Hotfix culture" — every change framed as urgent enough to bypass the window. Tracks as a process smell on the post-mortem.
- Long-lived `staging` environment that diverges from prod and stops being a meaningful gate.
- Approvers who rubber-stamp without inspecting the artefact diff vs the merged code.
- Manual deploys via console / kubectl from operator workstations — bypasses audit.
- Feature flags with no documented owner and no expiry — flag debt becomes risk debt.
- Treating SBOM / provenance generation as "the security team's problem" rather than a build-time invariant.

## Cross-refs

- `git-workflow.md` — the merge flow that produces signed, ticket-linked commits is the upstream for everything here.
- `security.md` — signing keys, secrets management, vulnerability response, supply-chain controls.
- `monitoring.md` — SLOs and alerts that gate canary fan-out and trigger automatic rollback.
- `observability.md` — audit-log schema, no-PII rules, trace propagation across deploy boundaries.
- `data-modeling.md` — forward-only migrations + tested rollback for any schema change in the release.
