---
description: Compliance-grade git — signed commits, 2+ approvers, change-management ticket per PR
applyTo: "**/*"
---

# Git Workflow

> **Preset: enterprise**

**Principle:** every change is attributable, reviewed by at least two humans, and traceable to a change-management record. Auditability is not optional — it is the product of the workflow.

## Branching

- `main` is the production-tracking branch. Strictly protected.
- Feature work: `feat/<JIRA-or-CM-id>-<slug>`, e.g. `feat/CHG-12345-rate-limit-middleware`. **Ticket id in branch name is mandatory** — this is the audit anchor.
- Other types: `fix/<id>-<slug>`, `chore/<id>-<slug>`, `refactor/<id>-<slug>`, `hotfix/<id>-<slug>`.
- Release branches: `release/v<major>.<minor>` cut from `main` for staged production rollouts.
- Hotfix branches: `hotfix/<id>-<slug>` cut from the current `release/` branch; merged to `release/` and forward-merged to `main`.
- Long-lived branches outside the above set require an ADR.

## Commit conventions

Conventional Commits **with** mandatory signing **and** ticket reference:

```
<type>(<scope>): <imperative description> [<TICKET-ID>]

<body>

Refs: <TICKET-ID>
Signed-off-by: Real Name <corp-email@org.com>
```

Rules:
- **Signed commits required** (GPG or SSH signing key registered with the org's identity provider). Unsigned commits are rejected by branch protection.
- **Ticket id required** in the subject (last bracket) AND in `Refs:` trailer. The CM/Jira integration reads this to link commits to change records.
- One concern per commit. Atomic, reversible.
- Body explains *why* and references any threat-model / risk-assessment artefacts when applicable.
- No `--no-verify`. No bypass.

## Pull/Merge request flow

1. Engineer creates a Change-Management ticket in Jira / ServiceNow / equivalent **before** opening the PR. Captures: risk, blast radius, rollback plan, test plan.
2. `/006-merge` opens the PR with body template populated from the CM ticket.
3. PR body **must** include: linked CM ticket, risk level (low / medium / high), affected systems, rollback procedure, test evidence, security-impact statement.
4. Bots run: lint, typecheck, domain-tests, build, SAST / SCA security scan, license scan, secret scan, signed-commit check, ticket-link check.
5. **Required approvals: 2+ from distinct CODEOWNERS groups.** Self-approval blocked. Approvals from contributors who pushed to the PR are dismissed on every new push.
6. **Security-sensitive paths** (`auth/`, `crypto/`, `iam/`, infra-as-code) require an additional approval from the security CODEOWNERS group.
7. PR labels: `risk:low|medium|high`, `cm-approved`, `security-reviewed`, `requires-change-window`.
8. Merge strategy: **squash-merge** with the CM ticket id preserved in the squash commit subject. Linear history on `main`.
9. **Force-push to any shared branch is disabled** at the platform level.

## Auto-invoke toggles

```yaml
auto_invoke_review: true
require_reviewers: 2
require_approvers_for_promote: 2
allow_commit_to_main: false
require_signed_commits: true
allow_force_push_to_main: false
squash_merge: true
delete_branch_on_merge: true
pr_required: true
require_ticket_reference: true
ticket_pattern: "[A-Z]+-\\d+"
ticket_locations: ["branch_name", "commit_subject"]   # where to look for the id
require_codeowners_review: true
require_security_review_for_sensitive_paths: true
dismiss_stale_approvals_on_push: true
block_self_approval: true
auto_invoke_verify: true
branch_name_pattern: "task/{ticket_id}/{task_id}-{slug}"   # nested under change-management ticket id
```

## Mechanical enforcement

- **GitHub / GitLab branch protection on `main` and `release/*`**:
  - Require signed commits.
  - Require linear history (no merge commits).
  - Require status checks: `lint`, `typecheck`, `domain-tests`, `build`, `sast`, `sca`, `secret-scan`, `license-scan`, `dco-or-signoff`, `ticket-link-check`.
  - Require 2 approving reviews + CODEOWNERS review.
  - Dismiss stale approvals on push.
  - Restrict who can push: only the merge bot / release engineers.
  - No force-push, no deletion, no bypass for admins.
- **Commit-msg lefthook hook**: regex `^(feat|fix|chore|docs|refactor|test|style|perf|ci|build|revert|hotfix)(\([a-z0-9-]+\))?: .+ \[[A-Z]+-[0-9]+\]$` enforces ticket id in subject.
- **Ticket id enforcement**: all branches and commits MUST reference a change-management ticket id matching `ticket_pattern` (default `[A-Z]+-\d+`). `/006-merge` parses this id from the locations listed in `ticket_locations` and embeds it in the PR description's Change-management section. PR creation fails if no match is found in any of `ticket_locations`.
- **`ticket-link-check` CI job** verifies the referenced ticket exists, is in an allowed status, and is assigned to a human (not unassigned).
- **Audit log**: PR events streamed to the org's SIEM via webhook. Retained per compliance policy.
- **CODEOWNERS** at multiple granularities; security paths owned by `@org/security`.
- **Signing keys** provisioned through the corporate IdP; rotation policy documented in `security.md`.

## Subagent check

`reviewer` (`/004-code-review`):
- Conventional Commits + ticket id + `Refs:` trailer + signed.
- One concern per commit / PR.
- PR body fully populated (risk, rollback, test plan, security statement).
- Touched sensitive paths have explicit security-team approval.
- No new dependencies without an SCA-clean status.
- Logs do not leak PII (cross-checks `observability.md`).
- IaC changes have a corresponding plan output attached.

`verifier` (`/003-verify-dod`):
- All gates green including SAST / SCA / secret-scan.
- ATDD spec written; domain-tests green.
- Linked CM ticket in `approved-for-implementation` state.

## Examples

### Good

```
# 1. Create CM ticket CHG-12345 (risk: medium, rollback: feature-flag off)
git switch -c feat/CHG-12345-rate-limit-middleware
# ... TDD via /002-implement ...
git commit -S -s -m "feat(server): add token-bucket rate-limit middleware [CHG-12345]

Mitigates abuse vector documented in THREAT-2026-04. Behind feature flag
rate_limit.enabled; default off; rollout plan in CHG-12345.

Refs: CHG-12345"
git push -u origin feat/CHG-12345-rate-limit-middleware
/006-merge
# PR opened, 2 CODEOWNERS approve, security CODEOWNERS approve (auth path)
# All gates green, ticket in approved state -> squash-merge to main
```

### Bad

```
git commit -m "fix bug"                                 # no signing, no ticket, not Conv-Commits
git commit -S -s -m "feat: add thing"                   # no ticket id
git push --force-with-lease origin main                 # force-push blocked
# Self-approving a PR by switching accounts                # block_self_approval catches it
# Merging without security CODEOWNERS on /auth/* change    # rejected by branch protection
```

## Anti-patterns

- "Emergency" bypasses that become routine. Bypass = ADR + retro.
- Splitting one logical change across many tickets to dodge the 2-approver gate.
- Treating CM tickets as paperwork written after the fact — they must precede the PR.
- Using shared / service signing keys instead of per-engineer keys — destroys attributability.
- Skipping the security CODEOWNERS for "a tiny tweak" near auth code.
- Long-lived branches that accumulate weeks of unreviewed work, then land as a 4000-line PR.
- Pushing during a freeze window (see `deployment.md` change-management window).

## Cross-refs

- `deployment.md` — change-management window governs when merged commits may be promoted.
- `security.md` — signing key policy, secret-handling, SAST/SCA rules referenced in gates.
- `observability.md` — audit-log shape; no PII in commit messages or branch names.
- `documentation.md` — ADRs are mandatory for architectural changes (`feat:` that crosses bounded contexts).
