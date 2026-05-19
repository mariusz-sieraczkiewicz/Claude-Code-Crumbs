---
description: Open a merge/pull request for a completed task. Uses conventions from ruleset/git-workflow.md.
argument-hint: <task-id>
---

# /006-merge

Open a merge/pull request (MR/PR) for a completed task using conventions defined in `.claude/ruleset/git-workflow.md`. No dedicated subagent — the main thread orchestrates `gh` or `glab` directly.

This command **only opens** the MR/PR. It never auto-merges, never `--force` pushes, and never amends commits. Merge timing is a human or platform-automation decision.

## Inputs

- `<task-id>` — argument (e.g. `T-001`). Required.
- `docs/planning/epic-{id}-tasks.yaml` — locate the task entry. The task MUST have `status: done`.
- `.claude/ruleset/git-workflow.md` — parse the YAML toggle block. Relevant keys:
  - `pr_required` (bool) — if `false`, skip MR creation (solo preset).
  - `allow_commit_to_main` (bool) — informational; not enforced here.
  - `pr_title_pattern` (string) — default `"<type>(T-NNN): <title>"`.
  - `pr_body_template` (string or multi-line) — default below.
  - `base_branch` (string) — default `main`.
  - `default_reviewers` (list) — comma-joined for `--reviewer`.
  - `pr_labels` (list) — comma-joined for `--label`.
<!-- FREEZE:IF require_signed_commits -->
  - `require_signed_commits` (bool) — if `true`, verify `%G?` is `G` for all commits on the branch.
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_dco_signoff -->
  - `require_dco_signoff` (bool) — if `true` (typical for `oss`), verify every commit in `<base>..HEAD` has a `Signed-off-by:` trailer. Enforced in Phase 0, BEFORE `git push`.
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_codeowners_review -->
  - `require_codeowners_review` (bool) — if `true` (typical for `enterprise` and `oss`), skip `--reviewer` because CODEOWNERS auto-assigns server-side.
<!-- FREEZE:ENDIF -->
  - `branch_name_pattern` (string) — for the pre-flight branch check.
<!-- FREEZE:IF preset == "oss" -->
- `.claude/stack.yaml` — `extras.upstream_remote` (default `upstream`) and `extras.upstream_repo` (optional `owner/repo`) for OSS fork→upstream PR routing.
<!-- FREEZE:ENDIF -->
- `runs/{epic_id}/{task_id}/` — context for body composition (final findings, commit summary, gate results).
- Local git state: `git rev-parse --abbrev-ref HEAD`, `git remote get-url origin`, `git log <base>..HEAD`.

The active preset variant of `git-workflow.md` is in `.claude/ruleset/`:
<!-- FREEZE:IF preset == "solo" -->
- `solo` — `pr_required: false`. Command exits early.
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF preset == "small-team" -->
- `small-team` — standard PR with reviewers + labels.
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF preset == "enterprise" -->
- `enterprise` — adds Change-management section; ticket id REQUIRED.
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF preset == "oss" -->
- `oss` — adds DCO sign-off section; CLA reference.
<!-- FREEZE:ENDIF -->

Honour whatever toggles the user has customised.

## Workflow

### Phase 0 — Pre-flight

> **Step ordering is load-bearing.** The `pr_required: false` short-circuit (step 2) MUST run BEFORE any host/remote/network operation (steps 3+). Solo + no-remote setups have no `origin`; running host detection first surfaces a confusing `Cannot resolve host` error instead of the clean `Solo preset — no MR required` exit. Do not reorder.

1. **Task exists and done.** Load the task entry from `epic-{id}-tasks.yaml` (the `{id}` comes from the task's epic linkage). If the task is missing → abort: `Task <id> not found in any epic-*-tasks.yaml.` If `status != done` → abort: `Task must be /002-implement-complete (status: done) before merging.`
<!-- FREEZE:IF !pr_required -->
2. **`pr_required` toggle short-circuit (runs BEFORE any remote/host/network operation).** Read the `pr_required` toggle from `.claude/ruleset/git-workflow.md`. If `pr_required: false`:
<!-- FREEZE:IF tag_task_commits -->
   - If the toggle block also has `tag_task_commits: true` (solo preset default): run `git tag "${EPIC_ID}/${TASK_ID}" HEAD` (substitute the literal epic id and task id resolved in step 1, e.g. `git tag E-007/T-014 HEAD`). If the tag already exists (`git rev-parse --verify "${EPIC_ID}/${TASK_ID}" >/dev/null 2>&1`), skip the tag creation silently. Print: `Solo preset — tagged HEAD as <epic_id>/<task_id>. No MR required.` Exit 0.
<!-- FREEZE:ELSE -->
   - Print `Solo preset — /006-merge is a no-op for this task. Task complete on main.` Exit 0.
<!-- FREEZE:ENDIF -->

   This short-circuit ensures solo + no-remote runs never reach host detection. Do NOT push, do NOT call `gh`/`glab`, do NOT touch the network on the solo path.
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF pr_required -->
3. **Branch matches pattern.** Compare `git rev-parse --abbrev-ref HEAD` against `branch_name_pattern`. Mismatch → warn (`Branch <name> does not match pattern <pattern>; proceeding.`) but do not abort.
4. **Detect remote and platform.** Use the 3-step host-aware detection algorithm (works for GitHub Enterprise and self-hosted GitLab — host is **not** matched against `github.com` / `gitlab.com` literals). Host resolution order: `stack.yaml.extras.git_host` (override; useful when `origin` is a fork) → `git remote get-url origin`. Once resolved, the same `gh|glab auth status --hostname` probe determines the platform.

   ```sh
   # Step 1 — resolve host. extras.git_host (override) wins; else derive from origin.
   HOST=""
   if [ -f .claude/stack.yaml ]; then
       HOST="$(awk '
           /^extras:[[:space:]]*$/ { in_e=1; next }
           in_e && /^[^[:space:]]/ { in_e=0 }
           in_e && /^[[:space:]]+git_host:[[:space:]]*/ {
               line=$0
               sub(/^[[:space:]]+git_host:[[:space:]]*/, "", line)
               gsub(/^["'\'']|["'\'']$/, "", line)
               sub(/[[:space:]]+#.*$/, "", line)
               gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
               print line
               exit
           }
       ' .claude/stack.yaml)"
   fi
   if [ -z "$HOST" ]; then
       HOST="$(git remote get-url origin | sed -E 's#^(https?://|git@)([^:/]+)[:/].*#\2#')"
   fi
   if [ -z "$HOST" ]; then
       echo "Cannot resolve host. Set stack.yaml.extras.git_host or configure git remote origin." >&2
       exit 1
   fi

   # Step 2 — detect platform via authenticated CLI (run `command -v` first; see step 5)
   if gh auth status --hostname "$HOST" >/dev/null 2>&1; then
     PLATFORM=github; GH_HOST="$HOST"
   elif glab auth status --hostname "$HOST" >/dev/null 2>&1; then
     PLATFORM=gitlab; GLAB_HOST="$HOST"
   else
     # abort — no authenticated CLI for this host
     echo "No authenticated CLI for host $HOST. Run \`gh auth login --hostname $HOST\` (or \`glab auth login --hostname $HOST\`) then re-run." >&2
     exit 1
   fi
   ```

   GitHub Enterprise and self-hosted GitLab are supported via per-host `gh auth login --hostname <host>` / `glab auth login --hostname <host>`. If `origin` points at a fork and the user wants PRs against an upstream on a different host, set `stack.yaml.extras.git_host` to override origin-derived detection; otherwise the host is derived from `git remote get-url origin`.

5. **CLI installed.** `command -v gh` or `command -v glab` — this check runs **before** the auth-status probe in step 4. If missing → abort with the install hint: `Install <tool> first: https://cli.github.com` or `https://gitlab.com/gitlab-org/cli`.
6. **Auth check.** Already folded into step 4 — the `gh auth status --hostname "$HOST"` / `glab auth status --hostname "$HOST"` probe doubles as platform detection AND auth verification. If neither CLI is authenticated for `$HOST`, the abort message from step 4 names the exact `--hostname` flag the user needs.

   **Plugin cannot verify external CM-system state.** Whether the referenced CM ticket is in `Approved for Deployment` state is enforced server-side by the platform (workflow `required_reviewers`, branch protection, or a `ticket-link-check` CI job). The plugin does not contact your CM/Jira/ServiceNow API.
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_signed_commits -->
7. **Signed commits (conditional).** If `require_signed_commits: true`, run `git log --pretty='%G?' <base_branch>..HEAD` and confirm every line is `G`. Any other value (`N`, `B`, `U`, `X`, `Y`, `R`, `E`) → abort: `Unsigned or invalid signature on commit <sha>. Sign commits before opening the MR.`
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_dco_signoff -->
8. **DCO sign-off (conditional, pre-push).** If `require_dco_signoff: true` (typical for the `oss` preset), iterate every commit in `<base>..HEAD` and verify each commit message body contains a `Signed-off-by:` trailer:

   ```sh
   MISSING=0
   for sha in $(git rev-list <base>..HEAD); do
       if ! git log -1 --format=%B "$sha" | grep -qE '^Signed-off-by: '; then
           echo "Commit $sha is missing DCO sign-off." >&2
           MISSING=1
       fi
   done
   [ "$MISSING" -eq 0 ] || exit 1
   ```

   On any miss → ABORT BEFORE Phase 1 push with:

   ```
   Commits in this branch lack DCO sign-off. Re-run /002-implement (it now signs commits when require_dco_signoff: true), OR rebase with: git rebase --signoff <base>..HEAD. Force-push to the FORK after rebase is acceptable.
   ```

   This check runs in Phase 0 (BEFORE any `git push`) so the fork's remote branch is not advanced with sign-off-less commits.
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF preset == "oss" -->
9. **Upstream remote resolution (OSS).** If the active preset is `oss`, resolve fork→upstream topology now (Phase 3 needs it for `--repo` and `--head`):

   - Read `extras.upstream_remote` from `.claude/stack.yaml` (default: `upstream`).
   - Read `extras.upstream_repo` from `.claude/stack.yaml` (optional override).
   - Probe `git remote get-url <upstream_remote>`:
     - **Succeeds:** if `extras.upstream_repo` is unset, derive it:

       ```sh
       UPSTREAM_REPO="$(git remote get-url "$UPSTREAM_REMOTE" | sed -E 's#^(https?://|git@)[^:/]+[:/]([^/]+/[^/.]+)(\.git)?$#\2#')"
       FORK_OWNER="$(git remote get-url origin | sed -E 's#^(https?://|git@)[^:/]+[:/]([^/]+)/[^/.]+(\.git)?$#\2#')"
       ```

       Hold `UPSTREAM_REPO` and `FORK_OWNER` in memory for Phase 3.
     - **Fails (no upstream remote):** print a warning and continue against `origin`:

       ```
       OSS preset typically expects an `upstream` remote pointing at the canonical repo. Set one or run `git remote add upstream <url>` before /006-merge to get fork→upstream PR. Currently opening against origin.
       ```

       Leave `UPSTREAM_REPO`/`FORK_OWNER` unset; Phase 3 falls back to the default `gh pr create` behaviour (PR opens against origin's own default branch).
<!-- FREEZE:ENDIF -->

<!-- FREEZE:IF pr_required -->
### Phase 1 — Push branch

```bash
git push -u origin <branch-name>
```

If push fails (non-fast-forward, rejected, network) → abort and surface the raw git error verbatim. **Never** retry with `--force` or `--force-with-lease`. The user must resolve the divergence manually.

### Phase 2 — Compose PR title and body

**Title.** Render `pr_title_pattern`. Default `"<type>(T-NNN): <title>"`. Substitutions:
- `<type>` — derived from the task's primary commit message (typically `feat`, `fix`, `chore`, `refactor`). Read from `git log <base>..HEAD --format=%s` and pick the type prefix of the most recent commit; fall back to `feat` if none parseable.
- `T-NNN` — the task id.
- `<title>` — the task's `title` field from `epic-{id}-tasks.yaml`.

**Body.** Render `pr_body_template`. Default template:

```
## Summary
- <task title>
- Epic: E-NNN
- Acceptance criteria: <list from epic-{id}-tasks.yaml task.acceptance_criteria, one per bullet>

## Tests
- Domain-tests: <count from 03-verify.json or grep on diff>
- ATDD spec: <path from task.atdd_spec> (executed at epic close-out)

## Gates
- All gates from .claude/stack.yaml.gates passed.
- Code review passed (0 findings).

## Notes
<optional — from task.notes if present; omit section if empty>
```

<!-- FREEZE:IF preset == "enterprise" -->
**Enterprise preset addendum.** When the active preset is `enterprise`, append:

```
## Change-management
- Ticket: <ticket-id>  (REQUIRED — abort if missing in branch name or commit messages)
- Risk: <low|medium|high>
- Affected systems: <list>
- Rollback procedure: <steps or link>
- Test evidence: <links to /003+/004 outputs>
- Security impact: <none | summary>

## Approvers
- Code owner: @<owner>
- Compliance: @<compliance>
```

Parse `<ticket-id>` from the branch name (e.g. `task/T-001-CM-12345-something` → `CM-12345`) or from any commit message body. The pattern is preset-defined (default: `[A-Z]+-\d+`). If no match → abort: `Enterprise preset requires a change-management ticket id (pattern: <pattern>) in branch name or commit messages.`
<!-- FREEZE:ENDIF -->

<!-- FREEZE:IF preset == "oss" -->
**OSS preset addendum.** When the active preset is `oss`, append:

```
## DCO
- Signed-off-by: <author>  (verified in Phase 0 pre-flight)
- CLA: <linked or not applicable>
```

DCO sign-off is enforced in Phase 0 step 8 — BEFORE `git push`. Phase 2 only renders the body section; it does not re-check. If Phase 0 passed, every commit in `<base>..HEAD` carries a `Signed-off-by:` trailer by construction.
<!-- FREEZE:ENDIF -->

### Phase 3 — Open MR/PR

**Network timeout posture.** This command invokes GitHub/GitLab CLI commands that perform network I/O. The CLI tools (`gh`, `glab`) use their own default timeouts; this command does NOT wrap them in an external timeout. If a CLI call hangs >120s, halt the command (Ctrl-C) and re-run after checking network connectivity. Do not auto-retry — duplicate PRs/MRs/workflow triggers may result.

<!-- FREEZE:IF require_codeowners_review -->
**CODEOWNERS-driven review.** When any preset has `require_codeowners_review: true` (both **enterprise** and **oss** typically set this), required reviewers, CODEOWNERS, and merge-block-until-checks-pass are enforced server-side by GitHub/GitLab branch protection. The plugin does NOT pass `--reviewer` flags in that case — CODEOWNERS auto-assigns server-side. For other presets, `--reviewer <default_reviewers>` applies as normal.
<!-- FREEZE:ENDIF -->

<!-- FREEZE:IF preset == "oss" -->
**Fork→upstream topology (OSS).** When the active preset is `oss` AND Phase 0 step 9 resolved an `UPSTREAM_REPO` + `FORK_OWNER`, the GitHub PR MUST target the upstream repo with `--repo "$UPSTREAM_REPO"` and the cross-fork head `--head "$FORK_OWNER:$BRANCH"`. Without these flags, `gh` defaults to opening the PR on the fork's own default branch, which violates the OSS contract (fork→upstream:main).
<!-- FREEZE:ENDIF -->

GitHub (prepend `GH_HOST="$HOST"` so GHE hosts route correctly):

```bash
GH_HOST="$HOST" gh pr create \
  ${UPSTREAM_REPO:+--repo "$UPSTREAM_REPO"} \
  ${UPSTREAM_REPO:+--head "$FORK_OWNER:$BRANCH"} \
  --base <base_branch> \
  --title "<title>" \
  --body "<body>" \
  --reviewer <reviewers-csv> \
  --label <labels-csv>
```

`${UPSTREAM_REPO:+...}` expansion only emits `--repo`/`--head` when the variable is set (i.e. OSS preset with an upstream remote resolved). For non-OSS presets, or OSS without an upstream remote (the Phase 0 step 9 warning case), the flags are absent and `gh` falls back to its default behaviour (PR opens on origin).

GitLab (prepend `GLAB_HOST="$HOST"` so self-hosted GitLab routes correctly):

```bash
GLAB_HOST="$HOST" glab mr create \
  --target-branch <base_branch> \
  --title "<title>" \
  --description "<body>" \
  --reviewer <reviewers-csv> \
  --label <labels-csv>
```

Omit `--reviewer` if `default_reviewers` is empty OR if `require_codeowners_review: true` for the active preset (enterprise OR oss — CODEOWNERS handles assignment server-side). Omit `--label` if `pr_labels` is empty. Capture stdout — both tools print the resulting URL. Print the URL verbatim.

### Phase 4 — Update task entry

Append `pr_url: <url>` to the task entry in `epic-{id}-tasks.yaml`. Preserve the existing `status: done`. **Do not** introduce a post-done state — `/006-merge` does not advance the task lifecycle beyond `done`.

### Phase 5 — Summary

Print a 3-line summary:

```
Title: <title>
URL:   <url>
Base:  <base_branch>
```

Then a next-step hint:
- If more pending tasks remain in the epic → suggest `/002-implement T-NNN`.
- If this was the last task in the epic → suggest `/003-verify-dod T-LAST --epic-close` to run ATDD specs, then `/007-promote` if `stack.yaml.promote` is configured.
<!-- FREEZE:ENDIF -->

## Discipline

- **Never `--force` push.** Not `--force`, not `--force-with-lease`. Push failure is a signal, not a problem to bulldoze.
- **Never bypass `git-workflow.md`.** If the user customised the preset's toggles, honour them. Do not silently substitute defaults when a key is present.
- **Never auto-merge.** No `gh pr merge`, no `glab mr merge`, no squash, no rebase. `/006-merge` opens the MR. Merging is a human or platform decision.
- **Never amend.** This command never touches commit content. DCO/signing failures surface as aborts with manual fix instructions.
- **One MR per task.** If `pr_url` already exists on the task entry, surface it and exit rather than opening a duplicate.

## Failure modes

| Condition | Action |
|---|---|
| Task not found or `status != done` | Abort with the message above. |
| Branch mismatch with `branch_name_pattern` | Warn, proceed. |
| Remote host unsupported | Abort: `Unsupported remote. Push branch and open MR manually.` |
| `gh` or `glab` not installed | Abort with install hint URL. |
| `pr_required: false` (solo) | Print solo notice, exit cleanly. |
<!-- FREEZE:IF require_signed_commits -->
| `require_signed_commits: true` + unsigned commit | Abort with the offending sha. |
<!-- FREEZE:ENDIF -->
| `git push` fails | Abort, surface raw git stderr, no retry. |
<!-- FREEZE:IF preset == "enterprise" -->
| Enterprise preset + no CM ticket id | Abort with the expected ticket-id pattern. |
<!-- FREEZE:ENDIF -->
<!-- FREEZE:IF require_dco_signoff -->
| OSS preset + missing DCO sign-off | Abort in Phase 0 (BEFORE push) with the re-run-`/002-implement` or `git rebase --signoff` hint. |
<!-- FREEZE:ENDIF -->
| Task already has `pr_url` | Print existing URL, exit (no duplicate MR). |

## Vocabulary discipline

Mirror `CONTEXT.md` and `.claude/ruleset/git-workflow.md` exactly. "MR" and "PR" are both valid and depend on the remote — use the term that matches the platform. "Pull request" / "merge request" — never "change list", "patch", "diff submission", "code drop". The task lifecycle term is "done", not "merged" — merging happens later, by a human or platform automation.
