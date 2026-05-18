---
description: Feature branches, Conventional Commits, PR review before merge to main
applyTo: "**/*"
---

# Git Workflow

> **Preset: small-team (baseline)**

**Principle:** main is always releasable. Work happens on short-lived feature branches, lands via reviewed PRs, and history is told in Conventional Commits.

## Branching

- Long-lived: `main` (releasable at all times). Optional `develop` only if the team has an explicit reason.
- Short-lived: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`, `refactor/<slug>`, `test/<slug>`.
- One task (per `epics.yaml` / `epic-{id}-tasks.yaml`) = one branch = one PR.
- Branch off `main` at HEAD. Rebase onto `main` before opening PR if it has moved.
- Delete the branch on merge (server-side and locally).

## Commit conventions

Conventional Commits, enforced by a `commit-msg` lefthook hook:

```
<type>(<optional-scope>): <imperative description>
```

Allowed types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `perf`, `ci`, `build`, `revert`.

Rules:
- One concern per commit. Atomic. Reversible.
- PR title also follows Conventional Commits and becomes the squash-merge commit message.
- Don't commit generated files, build artefacts, or secrets — keep `.gitignore` honest.
- Body explains the *why* when not obvious from the subject. Wrap at 72 cols.
- Signed commits optional for small-team (see `enterprise` preset for mandatory signing).

## Pull/Merge request flow

1. `/002-implement` finishes the task on its branch, runs `/003-verify-dod` and `/004-code-review`.
2. On clean review, `/006-merge` opens a PR via `gh pr create` (or `glab mr create`).
3. PR body template:
   - Linked task id (`E-007 / T-3`)
   - Linked Business scenario(s)
   - DoD summary (from `runs/.../03-verify.json`)
   - Reviewer checklist
4. **Required reviewers: 1-2.** At least 1 approval before merge.
5. **Base branch: `main`.** Squash-merge is the default — keeps `main` linear, preserves task-granular history.
6. CI gates must be green: lint, typecheck, domain-tests, build.
7. Merge button only after: green CI + required approvals + no unresolved comments.

## Auto-invoke toggles

Machine-readable hints consumed by `/002-implement` and `/006-merge`. Keep valid YAML — the orchestrator parses it.

```yaml
auto_invoke_review: true
require_reviewers: 1
require_approvers_for_promote: 1
allow_commit_to_main: false
require_signed_commits: false
allow_force_push_to_main: false
squash_merge: true
delete_branch_on_merge: true
pr_required: true
auto_invoke_verify: true
auto_fix_on_verify_fail: true   # when /003-verify-dod finds gaps, auto-dispatch feedback-implementer (loop max 3); false = /003 prints findings and exits read-only (user runs /005-implement-feedback manually)
auto_fix_on_review_fail: true   # when /004-code-review finds Violations, auto-dispatch feedback-implementer (loop max 3); false = /004 prints Violations and exits read-only
branch_name_pattern: "task/{task_id}-{slug}"
```

## Mechanical enforcement

- **lefthook** hooks:
  - `commit-msg` — regex `^(feat|fix|chore|docs|refactor|test|style|perf|ci|build|revert)(\([a-z0-9-]+\))?: .+`
  - `pre-push` — run lint + typecheck + domain-tests; reject on red.
- **GitHub branch protection on `main`**:
  - Require PR before merge.
  - Require status checks: `lint`, `typecheck`, `domain-tests`.
  - Require 1 approving review; dismiss stale approvals on new pushes.
  - Disallow force pushes and deletions.
- `gh` CLI defaults (`gh repo set-default`, `gh config set prompt disabled`) keep `/006-merge` non-interactive.
- `.github/pull_request_template.md` carries the PR body skeleton.

## Subagent check

`reviewer` (`/004-code-review`) checks the diff and commits for:
- Commit message regex compliance.
- One-concern-per-commit (no "and also" commits).
- Branch name matches `<type>/<slug>`.
- No secrets, no build artefacts, no generated files in the diff.
- PR body filled in (linked task, scenarios, DoD summary).

`verifier` (`/003-verify-dod`) is git-workflow-agnostic but flags missing branch / dirty tree before signalling DONE.

## Examples

### Good

```
git switch -c feat/voice-add-task
# ... TDD loop via /002-implement ...
git commit -m "feat(voice): add 1-tap voice capture with offline fallback"
git push -u origin feat/voice-add-task
/006-merge          # opens PR, squash-merge after 1 approval
```

### Bad

```
git commit -m "stuff"                                 # not Conventional Commits
git commit -am "fix bug and also refactor parser"     # two concerns
git push origin HEAD:main                             # bypasses PR
git push --force-with-lease origin main               # rewrites shared history
```

## Anti-patterns

- Long-lived feature branches (`> 1 week` without rebase).
- Committing directly to `main` (allowed only in `solo` preset).
- Merge commits cluttering `main` history (use squash-merge).
- "WIP" / "fix stuff" / "asdf" commit messages.
- Force-push to `main` or any shared branch.
- Mixing unrelated changes in one PR ("while I was there…").
- Skipping the PR because "it's just a one-liner".

## Cross-refs

- `deployment.md` — promotion of merged commits to staging/prod happens after this flow lands them on `main`.
- `testing.md` — gates referenced under "Mechanical enforcement" are defined there.
- `security.md` — secret-leak rules complement the "no secrets in diff" check.
