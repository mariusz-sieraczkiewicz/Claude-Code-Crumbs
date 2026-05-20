---
description: Fork-based PRs, CODEOWNERS approvals, no direct push to main
applyTo: "**/*"
---

# Git Workflow

> **Preset: oss**

**Principle:** the project belongs to its contributors. Maintainers gate `main`; external contributors fork. Every change is documented, signed off by the right humans, and traceable to a CLA-signed identity.

## Branching

- `main` is protected. **Nobody** — maintainer or not — pushes directly.
- Maintainers branch internally as `feat/<slug>` / `fix/<slug>` / `chore/<slug>` for collaborative work, then open a PR from the branch to `main`.
- External contributors **fork** the repo and open PRs from `<their-fork>:<branch>` to `<upstream>:main`.
- Release branches `release/v<major>.<minor>` cut from `main`; patches against them open PRs targeting the release branch with a maintainer label `backport`.

## Commit conventions

Conventional Commits, with stricter rules:

```
<type>(<optional-scope>): <imperative description>

<body explaining why>

Signed-off-by: Contributor Name <email@example.com>
```

Rules:
- `Signed-off-by` line **required** on every commit (`git commit -s`). This is the DCO sign-off — equivalent to acknowledging the project's CLA / DCO.
- A separate CLA may also be required; see `CONTRIBUTING.md`. Maintainers gate merges on the CLA bot status.
- GPG / SSH signing recommended but not required (kept optional so first-time contributors aren't blocked).
- PR title also follows Conventional Commits — it becomes the squash-merge subject and feeds the changelog generator.
- One concern per commit. Maintainers may ask for a force-push to rewrite history before merge; this is normal.

## Pull/Merge request flow

1. Contributor forks, branches, commits with `-s`, opens PR to `upstream:main`.
2. Bots run first pass: CLA check, lint, typecheck, domain-tests, build, license scan.
3. `CODEOWNERS` auto-assigns reviewers based on touched paths.
4. **Required approvals: per `CODEOWNERS` — typically 1 maintainer per touched code-owner group, minimum 1 maintainer overall.**
5. Maintainer review focuses on:
   - Scope creep (one PR = one change).
   - API surface implications (breaking changes flagged with `BREAKING CHANGE:` in commit footer).
   - Documentation parity (`docs/` updated alongside code).
   - Test coverage (domain-tests + ATDD spec for new behavior).
6. PR labels drive automation: `needs-review`, `needs-changes`, `ready-to-merge`, `breaking-change`, `backport-to-<version>`.
7. Merge strategy: **squash-merge** by default. Maintainers may rebase-merge for changesets where commit granularity matters (e.g. a series of refactors).
8. `main` builds publish nightly artefacts; releases are cut manually via tag (`v<major>.<minor>.<patch>`).

## Auto-invoke toggles

```yaml
auto_invoke_review: true
require_reviewers: 1
require_approvers_for_promote: 1
allow_commit_to_main: false
require_signed_commits: false
require_dco_signoff: true
allow_force_push_to_main: false
squash_merge: true
delete_branch_on_merge: true
pr_required: true
require_codeowners_review: true
require_cla: true
auto_invoke_verify: true
auto_fix_on_verify_fail: true   # /003-verify-dod findings auto-dispatch feedback-implementer (loop max 3); false = print findings, contributor runs /005-implement-feedback manually
auto_fix_on_review_fail: true   # /004-code-review Violations auto-dispatch feedback-implementer (loop max 3); false = print Violations and exit read-only — useful when maintainer wants to gate fixes manually
require_plan_approval: false   # default: contributor runs the whole epic without prompting. Flip to true if you want a per-task plan checkpoint (useful for first-time contributors).
branch_name_pattern: "feature/{epic_id}-{slug}"   # OSS convention: feature/ prefix, contributors fork
```

## Mechanical enforcement

- **GitHub branch protection on `main`**:
  - Require PR before merge; no direct push.
  - Require approving review from `CODEOWNERS`.
  - Require status checks: `lint`, `typecheck`, `domain-tests`, `build`, `cla-check`, `license-scan`, `dco-check`.
  - Dismiss stale approvals on push.
  - No force-push, no deletion.
- **`CODEOWNERS`** at repo root maps paths → maintainer teams.
- **DCO bot** (or equivalent action) blocks PRs missing `Signed-off-by:` on any commit.
- **CLA bot** (e.g. cla-assistant) checks each new contributor's CLA status; PRs from unsigned contributors get a comment + status check fail.
- **lefthook** locally: `commit-msg` regex + `pre-push` running fast gates.
- `.github/pull_request_template.md` enforces issue link, scope description, breaking-change flag, test checklist.

## Subagent check

`reviewer` (`/004-code-review`) checks the diff for:
- Conventional Commits format + DCO sign-off on every commit.
- One concern per PR (multi-concern PRs get a "split, please" comment).
- API-breaking changes are flagged in commit footer AND PR body.
- New behavior has at least one domain-test and an ATDD spec.
- Docs (`docs/`, `README.md`, `CHANGELOG`) updated in the same PR.
- No vendored dependencies smuggled in.
- License headers present on new source files (per project policy).

`verifier` (`/003-verify-dod`) checks: clean tree, gates green, ATDD spec written.

## Examples

### Good

```
git clone git@github.com:my-user/upstream-project.git
cd upstream-project
git remote add upstream git@github.com:upstream/project.git
git switch -c feat/add-rate-limit-middleware
# ... TDD via /002-implement ...
git commit -s -m "feat(server): add token-bucket rate-limit middleware"
git push origin feat/add-rate-limit-middleware
gh pr create --repo upstream/project --base main --head my-user:feat/add-rate-limit-middleware \
  --title "feat(server): add token-bucket rate-limit middleware" \
  --body "Closes #1234. ..."
```

### Bad

```
git commit -m "fix things"                             # neither Conventional Commits nor DCO
git push upstream main                                 # protected, will be rejected
# Opening a PR that touches /core/* without a /core CODEOWNERS approval
# Squashing a PR that adds + reverts + re-adds the same feature  (split it)
# Smuggling a license-incompatible dependency into vendor/
```

## Anti-patterns

- "Drive-by" PRs that touch 12 unrelated subsystems.
- Skipping `Signed-off-by` and arguing with the DCO bot.
- Ignoring `CODEOWNERS` by adding `@everyone` as a reviewer.
- Merging your own PR as a maintainer without a second pair of eyes (still requires CODEOWNERS review).
- Reformatting the entire file alongside a one-line behaviour change — review noise hides bugs.
- Pushing a force-update during review without warning reviewers — invalidates in-flight comments.

## Cross-refs

- `deployment.md` — releases (not auto-deploys) are how OSS code reaches users.
- `documentation.md` — docs parity is a merge-blocker here, not a nice-to-have.
- `security.md` — supply-chain rules (signed releases, SBOM) matter disproportionately for OSS.
- `CONTRIBUTING.md` at repo root — onboarding for first-time contributors; references this file.
