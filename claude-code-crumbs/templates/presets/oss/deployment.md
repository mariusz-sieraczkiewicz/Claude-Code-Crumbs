---
description: Release-based distribution — no auto-deploy, tagged versions only
applyTo: "**/*"
---

# Deployment

> **Preset: oss**

**Principle:** OSS doesn't deploy — it **releases**. Users pull updates on their schedule. Maintainers cut versioned releases, sign artefacts, and write changelogs that downstream operators can actually act on.

## Environments

- **dev** — contributor machines + ephemeral CI builds per PR.
- **main** — integration branch; nightly / `latest` artefacts may be published as `unstable`. Not production.
- **release** — tagged versions (`v<major>.<minor>.<patch>`). Artefacts: signed packages on the project's distribution channels (npm, crates.io, PyPI, container registry, GitHub Releases, Homebrew, etc.).
- **There is no project-owned "prod".** Downstream users own their production.

## Promotion steps

1. Maintainers cut a release branch (`release/v1.4`) from `main` when scope is frozen.
2. Release candidates published: `v1.4.0-rc.1`, `-rc.2`, ... — built and signed by CI, distributed via the project's package channels with a pre-release flag.
3. Community testing window (project-defined; typically 1-2 weeks for minor, days for patch).
4. Final release: maintainer tags `v1.4.0` on the release branch; CI builds, signs (GPG / Sigstore / minisign), and publishes.
5. `CHANGELOG.md` updated as part of the release PR (generated from Conventional Commits + hand-curated highlights).
6. GitHub Release notes generated from the changelog; binary / source artefacts attached.
7. Backports to previous release lines (`v1.3.x`) go via PRs against `release/v1.3`, then a new patch tag.

`/007-promote` for OSS triggers the **release workflow**, not a server deploy. `stack.yaml.promote.prod_workflow` points at `release.yml` (or equivalent).

## Rollback / Approval gates

- **Approval to release: 2 maintainers** (matches "multiple approvers per CODEOWNERS"). Recorded as approvals on the release PR + the tag push.
- **Rollback strategy: yank + patch.**
  - Yank the bad version on the package registry where supported (npm `deprecate`, crates.io `yank`, PyPI `yank`).
  - Publish a patch release (`v1.4.1`) that fixes the regression.
  - **Do not delete tags.** Tags are immutable contracts with downstream users.
- A security advisory (GHSA) accompanies any release that fixes a vulnerability; CVE assigned if the project participates in MITRE's CNA program.

## Auto-invoke toggles

```yaml
auto_invoke_review: true
require_reviewers: 1
require_approvers_for_promote: 2
allow_commit_to_main: false
require_signed_commits: false
require_dco_signoff: true
auto_deploy_staging: false
auto_deploy_prod: false
require_change_window: false
require_change_ticket: false
journey_gate_required: true
require_signed_artefacts: true
require_changelog: true
require_release_notes: true
auto_invoke_verify: true
branch_name_pattern: "feature/{task_id}-{slug}"   # OSS convention: feature/ prefix, contributors fork
```

## Mechanical enforcement

- **GitHub Actions release workflow** triggered by tag push matching `v[0-9]+.[0-9]+.[0-9]+`.
- **Artefact signing** in CI: GPG-sign with project key (stored as repo secret with restricted access) or Sigstore keyless signing.
- **SBOM** generated per release (CycloneDX or SPDX) and attached to the GitHub Release.
- **Provenance attestation** (SLSA Level 3+ recommended) — CI signs a statement linking source commit → artefact hash.
- `CHANGELOG.md` checked by a release-gate workflow: PR fails if `## [v<x.y.z>]` section missing for the new tag.
- Branch protection on `release/*` mirrors `main` — PRs only, CODEOWNERS approval, gates green.

## Subagent check

`verifier` (`/003-verify-dod`):
- All gates green on the release commit.
- Journey smoke gate green (run by CI on the release candidate).
- `CHANGELOG.md` updated.
- Version bumped consistently (manifest file, `package.json` / `Cargo.toml` / `pyproject.toml`, etc.).

`reviewer` (`/004-code-review`):
- Release notes accurate (no surprises vs the commit list).
- Breaking changes flagged with migration notes.
- No new license-incompatible dependencies introduced since the previous release.
- Security advisories drafted for any CVE-bearing fixes.

## Examples

### Good

```
# Maintainer prep:
git switch -c release/v1.4
# ... PRs land into release/v1.4, including CHANGELOG updates ...
git tag -s v1.4.0-rc.1 -m "v1.4.0-rc.1"
git push origin v1.4.0-rc.1            # CI builds + publishes pre-release
# Community testing window passes
git tag -s v1.4.0 -m "v1.4.0"
git push origin v1.4.0                 # CI builds, signs, publishes to npm + GitHub Releases
```

### Bad

```
# Force-pushing a tag to "fix" a release  (tags are immutable; cut v1.4.1 instead)
# Releasing without updating CHANGELOG  (downstream operators rely on it)
# Cutting v2.0.0 without flagging breaking changes in commits  (semver violation)
# Deleting yanked versions from the registry  (breaks lockfiles for existing users)
```

## Anti-patterns

- "Latest" tag as a moving target — downstream pins break unpredictably.
- Manual artefact uploads from a maintainer laptop — bypasses signing + provenance.
- Skipping the release-candidate window for "small" releases — the smallest releases break the most users.
- Bundling unrelated features into a major version because "we're due for a 2.0".
- Releasing on a Friday before maintainer vacation — leaves the community without an on-call.
- Treating downstream users as adversaries when they report regressions in a fresh release.

## Cross-refs

- `git-workflow.md` — fork-based PR flow that feeds the release branches.
- `documentation.md` — release notes, migration guides, deprecation notices.
- `security.md` — vulnerability disclosure policy (`SECURITY.md`), advisory workflow.
- `api-design.md` — semver discipline depends on a stable, well-versioned API surface.
