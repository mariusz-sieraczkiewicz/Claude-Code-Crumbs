---
description: Trigger a pre-existing platform workflow to promote an environment. Plugin does not orchestrate the deploy itself.
argument-hint: <environment> [--pre-flight]
---

# /007-promote

You are the trigger for a **pre-existing platform Promotion workflow** (GitHub Actions, GitLab CI). This command is intentionally **lightweight**: the plugin reads the workflow name from `.claude/stack.yaml.promote` and invokes the platform CLI. **The plugin does not orchestrate the Promotion itself** — the workflow file in `.github/workflows/` or `.gitlab-ci.yml` owns the deploy logic. If the project has no `stack.yaml.promote` entry, this command is skipped at install time and should not be invoked.

The command also runs the **Journey gate** (cross-feature smoke gate at Promotion) before triggering, when configured. Journeys are the only zero-tolerance gate this command enforces directly. Every other discipline check (change-management window, prior staging Promotion, release tag) is policy taken from `ruleset/deployment.md` and the active team preset.

Argument: `$ARGUMENTS` — the target Environment plus optional flags. Required positional argument. Examples: `staging`, `prod`, `prod --pre-flight`.

## Inputs

- **`<environment>`** — first positional argument. Must be one of `stack.yaml.promote.environments`. Typically `staging` or `prod`. Required.
- **`--pre-flight`** — optional flag. Forces the pre-flight script to run even when the default flow would skip it. If `stack.yaml.promote.pre_flight` is empty when this flag is set, warn and no-op.
- **`.claude/stack.yaml`** — read the `promote` block:
  - `promote.environments` — allowed Environment names (list).
  - `promote.staging_workflow` — workflow file or pipeline identifier for staging.
  - `promote.prod_workflow` — workflow file or pipeline identifier for prod.
  - `promote.pre_flight` — optional shell command run before the platform trigger.
  - `team_preset` — informational; recorded at bootstrap (`solo` | `small-team` | `oss` | `enterprise`). Used here only to pick the discipline checks below.
- **`.claude/stack.yaml.gates.journeys`** — shell command for the Journey gate. `null` = skip with warning.
- **`.claude/ruleset/deployment.md`** — project-owned Promotion conventions: Environment progression, rollback policy, Journey gate enforcement, and (for enterprise) `change_window`. Read for the discipline checks; do not paraphrase its rules — defer to its text when in doubt.
- **Git remote** — `git remote get-url origin` to detect platform (GitHub vs GitLab vs other).
- **Current ref** — `git rev-parse --abbrev-ref HEAD` and `git describe --tags --exact-match` (the latter may fail; that is information, not an error).

If `stack.yaml.promote` is absent or empty: abort with `No promote config in stack.yaml. Either configure promote.environments + *_workflow, or run promotion manually. /007-promote is optional.` Suggest revisiting `/000-prd-refine` or editing `stack.yaml` directly.

## Workflow

### Phase 0 — Pre-flight (always run)

Validate inputs before doing any work. Each check below is **abort-on-fail** unless explicitly noted. Phase 0 fails fast on misconfiguration before paying the cost of running the pre-flight script or the Journey gate.

1. **Environment whitelist.** If `<environment>` is not in `stack.yaml.promote.environments`, abort:
   `Environment '<env>' not configured. Available: <comma-separated list>.`
2. **Auth check.** After confirming the platform CLI is installed (detect via `git remote get-url origin` — `github.com` → `gh`; `gitlab.com` or self-hosted GitLab → `glab`), run `gh auth status` (or `glab auth status`). If exit code != 0 → ABORT with: `<gh|glab> is installed but not authenticated. Run \`gh auth login\` (or \`glab auth login\`) first, then re-invoke /007-promote.` Capture the auth-status stderr in the abort message for diagnostics. This check belongs **BEFORE** any read of `stack.yaml.promote.*_workflow`.
3. **Workflow configured.** Look up `stack.yaml.promote.<environment>_workflow`. If empty or null, abort:
   `No workflow configured for <env>. Plugin does not orchestrate deploys — set <env>_workflow in stack.yaml or run promotion manually.`
4. **Team-preset discipline.** Read `team_preset` from `stack.yaml`. Apply the matching policy:
   - **`solo`** — allow direct Promotion to any Environment. No staging precondition. No further checks.
   - **`small-team`** — Promotion to `prod` requires staging to have been promoted within the **last 24h**. Read recent deploys via `gh run list --workflow=<staging_workflow> --limit 5 --json conclusion,updatedAt` (GitHub) or equivalent `glab` call. If no successful staging run in the window, **warn** and ask the user to confirm explicitly (`Proceed without recent staging? [y/N]`). Allow override on `y`; abort otherwise.
   - **`oss`** — Promotion to `prod` requires the current commit to carry a release tag. Run `git describe --tags --exact-match HEAD`. If it fails, abort: `prod promote requires a tagged release on HEAD. Tag the commit first (git tag vX.Y.Z && git push --tags).`
   - **`enterprise`** — Promotion to `prod` requires (a) change-management approval and (b) execution **inside the `change_window`** declared in `ruleset/deployment.md`. Parse `change_window` from that file (typically e.g. `Mon-Fri 09:00-17:00 local`). Compare to current local time. If outside the window, abort: `Outside change window (<window>). Override only with explicit user confirmation and CM approval reference.` Permit override only on explicit `y` plus a non-empty CM reference typed by the user.
5. **Concurrent promotion check.** Detect the platform from `git remote get-url origin`:
   - **GitHub** (`github.com` in remote): run `gh run list --workflow=<stack.yaml.promote.<environment>_workflow> --status=in_progress --limit=5 --json status,createdAt`. If the result is a non-empty array, abort: `A promotion workflow is already in progress for <workflow>. Wait for it to finish or cancel it manually before re-invoking /007-promote.`
   - **GitLab** (`gitlab.com` or self-hosted GitLab): run `glab pipeline list --status=running --limit=5` and filter to entries whose pipeline file matches `<stack.yaml.promote.<environment>_workflow>`. If any match, abort with the same message (substituting the workflow name).
   - **Neither `gh` nor `glab` available on `$PATH`** (or remote host unrecognised): skip the check and print a visible warning: `Concurrent promotion check skipped — no platform CLI available. Proceeding without concurrency guard.`

Phase 0 produces no artifact; on success it prints a one-line summary of the checks that passed and proceeds.

### Phase 1 — Optional pre-flight script

If `stack.yaml.promote.pre_flight` is set (a shell command), run it via Bash:

- Stream stdout/stderr to the terminal so the user sees progress.
- On exit code `0`, continue.
- On non-zero exit, abort with the captured stderr verbatim:
  `Pre-flight failed (exit <N>):\n<stderr>`

If `--pre-flight` is passed **and** `stack.yaml.promote.pre_flight` is empty, do not execute anything; emit a warning: `--pre-flight requested but stack.yaml.promote.pre_flight is empty. Skipping.` Then continue.

The pre-flight script is **project-defined**. Typical contents: smoke test against the **source** Environment, lint config files, validate secrets are wired, sanity-check a config bundle, confirm migration scripts apply cleanly to a snapshot. The plugin does not prescribe its shape. Treat it as opaque: run it, check exit code, surface output. If the project wants a more sophisticated pre-flight (parallel checks, structured reports), put it in the script — the plugin will not grow features here.

Phase 1 runs **after** Phase 0 passes and **before** the Journey gate. This ordering is deliberate: pre-flight is the cheap project-specific sanity check; Journey is the expensive cross-feature smoke gate. Fail cheap first.

### Phase 2 — Journey gate

Journeys are the cross-feature smoke gate at Promotion (see `ruleset/testing.md` and the `Journey` glossary entry). **Zero tolerance** — any non-zero exit aborts the Promotion.

- If `stack.yaml.gates.journeys` is set, run it via Bash. Stream output.
  - Exit 0 → continue to Phase 3.
  - Exit non-zero → abort with the full journey output captured:
    `Journey gate failed (exit <N>). Promotion aborted. Output:\n<captured>`
- If `stack.yaml.gates.journeys` is null or empty, **skip** with a visible warning:
  `Journey gate not configured (stack.yaml.gates.journeys is empty). Promotion proceeds without journeys — project decision.`

Do not auto-fix or retry a failed Journey gate. Hand control back to the user. A failing Journey at Promotion almost always means a cross-feature regression that ATDD specs and Domain-tests did not catch — that is the gate's whole job. The fix is at the source (likely a new Domain-test, then a code fix), not in this command.

The Journey gate runs against the **source** Environment in most projects (e.g. journeys against `staging-e2e` before promoting `staging → prod`). The plugin does not enforce that orientation; the command in `gates.journeys` decides which Environment it targets.

### Phase 3 — Trigger platform workflow

Detect the platform from `git remote get-url origin`:

**Auth check.** After confirming the CLI is installed (per the platform branches below), run `gh auth status` (or `glab auth status`) **before** the actual `gh workflow run` / `glab pipeline trigger`. If exit code != 0 → ABORT with: `<gh|glab> is installed but not authenticated. Run \`gh auth login\` (or \`glab auth login\`) first, then re-invoke /007-promote.` Capture the auth-status stderr in the abort message for diagnostics.

**Network timeout posture.** This command invokes GitHub/GitLab CLI commands that perform network I/O. The CLI tools (`gh`, `glab`) use their own default timeouts; this command does NOT wrap them in an external timeout. If a CLI call hangs >120s, halt the command (Ctrl-C) and re-run after checking network connectivity. Do not auto-retry — duplicate PRs/MRs/workflow triggers may result.

- **GitHub** (host contains `github.com`): require `gh` on `$PATH`. Determine the ref:
  - For `staging`: `--ref main` (or the branch configured in `ruleset/deployment.md`).
  - For `prod`: `--ref <tag>` when `team_preset = oss`; otherwise `--ref main` unless the workflow expects an explicit tag (defer to `deployment.md`).
  - Invoke: `gh workflow run <workflow-from-stack-yaml> --ref <ref>`. If the workflow accepts inputs, pass `-f environment=<env>` when the workflow declares an `environment` input; do not invent inputs the workflow does not declare.
- **GitLab** (host contains `gitlab.com` or a self-hosted GitLab): require `glab` on `$PATH`. Invoke:
  - `glab pipeline trigger --ref <ref> -v ENV=<env>` for the default pipeline, or
  - `glab ci run <pipeline-file>` when `*_workflow` names a specific pipeline file.
- **Other** (neither `gh` nor `glab` resolves, or remote host is unrecognised): abort with:
  `Unsupported platform. Trigger the workflow manually: <workflow_name>. Plugin does not implement raw API calls.`

**The plugin does not wait for the workflow to finish.** It triggers and exits immediately. The platform owns execution, logging, rollback, and notification. The user monitors via `gh run watch`, `glab pipeline view`, or the platform UI.

### Phase 4 — Summary

Print a single block to stdout (no JSON, no artifact under `.claude/runs/` — Promotion is product-level, not task-level):

```
Promotion triggered:
  Environment: <env>
  Workflow:    <workflow_name>
  Ref:         <branch-or-tag>
  Platform URL: <link if available>
Monitor with: gh run watch   (or: glab pipeline view)
```

If the platform CLI surfaced a run URL (e.g. `gh` prints one on success), include it on the `Platform URL` line. Otherwise omit that line.

The summary block is the **only** output the user keeps after a successful trigger. Make it scannable. No JSON, no decoration, no progress bars — the platform already provides those at the URL.

## Discipline

- The plugin **does not** orchestrate deploy steps, container builds, migrations, or smoke tests post-trigger. The workflow file in `.github/workflows/` or `.gitlab-ci.yml` owns that logic end-to-end. If the user wants the plugin to do more, the answer is: edit the workflow file.
- **Zero tolerance** on the Journey gate when configured. There is no `--skip-journeys`. To bypass, the user must edit `stack.yaml.gates.journeys` to `null` and accept the recorded warning.
- For **enterprise** preset: enforce the `change_window` from `ruleset/deployment.md`. Outside the window, abort unless the user provides explicit override **and** a change-management reference.
- For **oss** preset: never trigger `prod` without a tag on `HEAD`. Untagged Promotions defeat the release provenance contract.
- `/007-promote` does **not** verify that a prior `/003-verify-dod --epic-close` passed. That linkage belongs in `ruleset/deployment.md` (project policy) and in the platform workflow's own gates. The plugin keeps this command lightweight on purpose — project rules carry the load.
- No subagent dispatch. No `.claude/runs/` write. Promotion is a product-level operation; task-level artifacts do not apply.
- No retry loop. Triggering twice is the user's call, not the plugin's. If a trigger fails (network, auth, rate-limit), the plugin reports and exits — it does not back-off and retry.
- No secret handling. The plugin never reads, prints, or forwards credentials. Auth lives in the platform CLI (`gh auth`, `glab auth`). If the CLI is unauthenticated, abort with the CLI's own error message.

## Failure modes

- **No promote config in stack.yaml** → abort. Suggest `/000-prd-refine` to revisit bootstrap, or a manual `stack.yaml` edit.
- **Environment not in whitelist** → abort. Print the allowed list.
- **Workflow not configured for chosen environment** → abort. Direct user to set `<env>_workflow` or run the Promotion manually on the platform.
- **Unsupported platform / no CLI on `$PATH`** → abort with manual fallback message naming the workflow.
- **Pre-flight script non-zero exit** → abort with captured stderr.
- **Journey gate non-zero exit** → abort with full output. Never auto-retry.
- **Enterprise change-window violation** → abort with window text and current time. Override only on explicit confirmation plus CM reference.
- **`small-team` prod without recent staging** → warn, prompt, allow override on explicit `y`.
- **`oss` prod without tag on HEAD** → abort. Instruct user to tag and push.

In every failure case, exit non-zero so the user's shell history reflects the abort. Print one clear remediation line.

## Vocabulary discipline

Mirror `CONTEXT.md` and `ruleset/deployment.md` exactly:

- **Promote / Promotion** — the act this command performs. Not "deploy", not "release". Those are platform-level terms; the plugin's term is Promote.
- **Journey** — the cross-feature smoke gate run at Promotion. Not "smoke test", not "integration test", not "e2e test".
- **Environment** — the target of a Promotion (`staging`, `prod`, ...). Not "stage", not "target", not "tier".
- **Workflow** — the platform-side artifact (GitHub Actions workflow, GitLab pipeline) that owns the actual deploy logic. The plugin **triggers** workflows; it does not contain them.
- **Gate** — a zero-tolerance check whose exit code decides pass/fail. The Journey gate is the only gate this command runs.

Any deviation from this vocabulary in output, warnings, or abort messages is a defect — fix it in place rather than aliasing terms.
