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
  - `require_signed_commits` (bool) — if `true`, verify `%G?` is `G` for all commits on the branch.
  - `branch_name_pattern` (string) — for the pre-flight branch check.
- `runs/{epic_id}/{task_id}/` — context for body composition (final findings, commit summary, gate results).
- Local git state: `git rev-parse --abbrev-ref HEAD`, `git remote get-url origin`, `git log <base>..HEAD`.

Four preset variants of `git-workflow.md` ship under `templates/presets/<preset>/git-workflow.md`:
- `solo` — `pr_required: false`. Command exits early.
- `team` — standard PR with reviewers + labels.
- `enterprise` — adds Change-management section; ticket id REQUIRED.
- `oss` — adds DCO sign-off section; CLA reference.

The active preset is determined by which `git-workflow.md` is present in `.claude/ruleset/`. Honour whatever toggles the user has customised.

## Workflow

### Phase 0 — Pre-flight

1. **Task exists and done.** Load the task entry from `epic-{id}-tasks.yaml` (the `{id}` comes from the task's epic linkage). If the task is missing → abort: `Task <id> not found in any epic-*-tasks.yaml.` If `status != done` → abort: `Task must be /002-implement-complete (status: done) before merging.`
2. **Branch matches pattern.** Compare `git rev-parse --abbrev-ref HEAD` against `branch_name_pattern`. Mismatch → warn (`Branch <name> does not match pattern <pattern>; proceeding.`) but do not abort.
3. **Detect remote.** Read `git remote get-url origin`:
   - Contains `github.com` → tool is `gh`.
   - Contains `gitlab.com` or a self-hosted GitLab host (detected via the workflow toggle or the URL pattern) → tool is `glab`.
   - Anything else → abort: `Unsupported remote <url>. Push branch and open MR manually.`
4. **Solo preset short-circuit.** If `pr_required: false`: print `Solo preset — no MR required. Branch <name> is on main.` and exit cleanly. Do not push, do not call `gh`/`glab`.
5. **CLI installed.** `command -v gh` or `command -v glab`. If missing → abort with the install hint: `Install <tool> first: https://cli.github.com` or `https://gitlab.com/gitlab-org/cli`.
6. **Auth check.** After confirming the CLI is installed, run `gh auth status` (or `glab auth status`). If exit code != 0 → ABORT with: `<gh|glab> is installed but not authenticated. Run \`gh auth login\` (or \`glab auth login\`) first, then re-invoke /006-merge.` Capture the auth-status stderr in the abort message for diagnostics.
7. **Signed commits (conditional).** If `require_signed_commits: true`, run `git log --pretty='%G?' <base_branch>..HEAD` and confirm every line is `G`. Any other value (`N`, `B`, `U`, `X`, `Y`, `R`, `E`) → abort: `Unsigned or invalid signature on commit <sha>. Sign commits before opening the MR.`

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
- Business scenarios: <list from epic-{id}-tasks.yaml task.domain_scenarios>

## Tests
- Domain-tests: <count from 03-verify.json or grep on diff>
- ATDD spec: <path from task.atdd_spec> (executed at epic close-out)

## Gates
- All gates from .claude/stack.yaml.gates passed.
- Code review passed (0 findings).

## Notes
<optional — from task.notes if present; omit section if empty>
```

**Enterprise preset addendum.** When the active preset is `enterprise`, append:

```
## Change-management
- Ticket: <ticket-id>  (REQUIRED — abort if missing in branch name or commit messages)
- Risk: <low|medium|high>
- Approvers required: 2+
```

Parse `<ticket-id>` from the branch name (e.g. `task/T-001-CM-12345-something` → `CM-12345`) or from any commit message body. The pattern is preset-defined (default: `[A-Z]+-\d+`). If no match → abort: `Enterprise preset requires a change-management ticket id (pattern: <pattern>) in branch name or commit messages.`

**OSS preset addendum.** When the active preset is `oss`, append:

```
## DCO
- Signed-off-by: <author>  (verified from commit messages)
- CLA: <linked or not applicable>
```

Verify every commit in `<base>..HEAD` carries a `Signed-off-by:` trailer (`git log --format=%B`). Missing trailer on any commit → abort: `OSS preset requires DCO sign-off. Re-commit with 'git commit --amend -s' (manual — this command does not amend).`

### Phase 3 — Open MR/PR

**Network timeout posture.** This command invokes GitHub/GitLab CLI commands that perform network I/O. The CLI tools (`gh`, `glab`) use their own default timeouts; this command does NOT wrap them in an external timeout. If a CLI call hangs >120s, halt the command (Ctrl-C) and re-run after checking network connectivity. Do not auto-retry — duplicate PRs/MRs/workflow triggers may result.

GitHub:

```bash
gh pr create \
  --base <base_branch> \
  --title "<title>" \
  --body "<body>" \
  --reviewer <reviewers-csv> \
  --label <labels-csv>
```

GitLab:

```bash
glab mr create \
  --target-branch <base_branch> \
  --title "<title>" \
  --description "<body>" \
  --reviewer <reviewers-csv> \
  --label <labels-csv>
```

Omit `--reviewer` if `default_reviewers` is empty. Omit `--label` if `pr_labels` is empty. Capture stdout — both tools print the resulting URL. Print the URL verbatim.

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
- If more pending tasks remain in the epic → suggest `/002-implement T-NNN` or `/002-auto-implement E-NNN`.
- If this was the last task in the epic → suggest `/003-verify-dod T-LAST --epic-close` to run ATDD specs, then `/007-promote` if `stack.yaml.promote` is configured.

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
| `require_signed_commits: true` + unsigned commit | Abort with the offending sha. |
| `git push` fails | Abort, surface raw git stderr, no retry. |
| Enterprise preset + no CM ticket id | Abort with the expected ticket-id pattern. |
| OSS preset + missing DCO sign-off | Abort with manual `git commit --amend -s` hint. |
| Task already has `pr_url` | Print existing URL, exit (no duplicate MR). |

## Vocabulary discipline

Mirror `CONTEXT.md` and `.claude/ruleset/git-workflow.md` exactly. "MR" and "PR" are both valid and depend on the remote — use the term that matches the platform. "Pull request" / "merge request" — never "change list", "patch", "diff submission", "code drop". The task lifecycle term is "done", not "merged" — merging happens later, by a human or platform automation.
