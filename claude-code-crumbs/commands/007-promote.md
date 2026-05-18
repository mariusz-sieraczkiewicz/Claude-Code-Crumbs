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
2. **Detect host, platform, and auth.** Use the 3-step host-aware detection algorithm (works for GitHub Enterprise and self-hosted GitLab — host is **not** matched against `github.com` / `gitlab.com` literals). `command -v gh` / `command -v glab` runs **first**; abort with an install hint if neither exists.

   ```bash
   # Step 1 — extract host from origin URL
   HOST="$(git remote get-url origin | sed -E 's#^(https?://|git@)([^:/]+)[:/].*#\2#')"

   # Step 2 — detect platform via authenticated CLI
   if gh auth status --hostname "$HOST" >/dev/null 2>&1; then
     PLATFORM=github; GH_HOST="$HOST"
   elif glab auth status --hostname "$HOST" >/dev/null 2>&1; then
     PLATFORM=gitlab; GLAB_HOST="$HOST"
   else
     echo "No authenticated CLI for host $HOST. Run \`gh auth login --hostname $HOST\` (or \`glab auth login --hostname $HOST\`) then re-run." >&2
     exit 1
   fi
   ```

   GitHub Enterprise and self-hosted GitLab are supported via per-host `gh auth login --hostname <host>` / `glab auth login --hostname <host>`. The command honours whatever host the local CLI is authenticated against; no `stack.yaml` override is required.

   This check belongs **BEFORE** any read of `stack.yaml.promote.*_workflow`.

   **Plugin cannot verify external CM-system state.** Whether the referenced CM ticket is in `Approved for Deployment` state is enforced server-side by the platform (workflow `required_reviewers`, branch protection, or a `ticket-link-check` CI job). The plugin does not contact your CM/Jira/ServiceNow API.
3. **Workflow configured.** Look up `stack.yaml.promote.<environment>_workflow`. If empty or null, abort:
   `No workflow configured for <env>. Plugin does not orchestrate deploys — set <env>_workflow in stack.yaml or run promotion manually.`
   Then verify the workflow file actually exists at HEAD: `test -f .github/workflows/<workflow>` (or the GitLab-equivalent path). If missing, abort: `Workflow file .github/workflows/<workflow> not found at HEAD. Check stack.yaml.promote.<env>_workflow points to an existing file.`
4. **Team-preset discipline.** Read `team_preset` from `stack.yaml`. Apply the matching policy:
   - **`solo`** — allow direct Promotion to any Environment. No staging precondition. No further checks.
   - **`small-team` and `enterprise`** — Promotion to `prod` requires staging to have been promoted within the **last 24h**. Read recent deploys via `gh run list --workflow=<staging_workflow> --limit 5 --json conclusion,updatedAt` (GitHub) or equivalent `glab` call. If no successful staging run in the window:
     - For `small-team`: **warn** and ask the user to confirm explicitly (`Proceed without recent staging? [y/N]`). Allow override on `y`; abort otherwise.
     - For `enterprise`: abort with `Enterprise preset requires staging promotion within the last 24h before prod. Run /007-promote staging first.` (No interactive override — enterprise discipline is non-negotiable.)
   - **`oss`** — Promotion to `prod` requires the current commit to carry a release tag. Run `git describe --tags --exact-match HEAD`. If it fails, abort: `prod promote requires a tagged release on HEAD. Tag the commit first (git tag vX.Y.Z && git push --tags).`
   - **`enterprise`** — In addition to the staging-within-24h precondition above, Promotion to `prod` requires execution **inside the `change_window`**. Read the structured change-window config from `stack.yaml.extras.change_window` (preferred) — keys: `days` (e.g. `[Mon, Tue, Wed, Thu, Fri]`), `hours` (e.g. `"09:00-17:00"`), `timezone` (IANA, e.g. `"Europe/Warsaw"`). If `stack.yaml.extras.change_window` is absent, fall back to parsing the toggle block in `ruleset/deployment.md`. Compute current local time in the specified `timezone`. If outside the window AND the CM ticket id is NOT listed in `stack.yaml.extras.change_window.allow_outside_window_for`, abort: `Outside change window (<days> <hours> <timezone>). Override only with explicit user confirmation and CM approval reference, or add the ticket to allow_outside_window_for.` Permit override only on explicit `y` plus a non-empty CM reference typed by the user.
5. **Concurrent promotion check.** Use the `PLATFORM` / `HOST` resolved in step 2 (no re-detection from `git remote`):
   - **`PLATFORM=github`**: run `GH_HOST="$HOST" gh run list --workflow=<stack.yaml.promote.<environment>_workflow> --status=in_progress --limit=5 --json status,createdAt`. If the result is a non-empty array, abort: `A promotion workflow is already in progress for <workflow>. Wait for it to finish or cancel it manually before re-invoking /007-promote.`
   - **`PLATFORM=gitlab`**: run `GLAB_HOST="$HOST" glab pipeline list --status=running --limit=5` and filter to entries whose pipeline file matches `<stack.yaml.promote.<environment>_workflow>`. If any match, abort with the same message (substituting the workflow name).
   - **Neither CLI authenticated for `$HOST`** (step 2 already aborts in this case): skip — control never reaches step 5. The legacy "no platform CLI available" warning path is retained only for environments where the operator deliberately bypasses step 2; in normal flow it is unreachable.

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

Use the `PLATFORM` / `HOST` resolved in Phase 0 step 2. Auth has already been verified there (the `gh auth status --hostname "$HOST"` / `glab auth status --hostname "$HOST"` probe doubles as platform detection AND auth verification), so no separate auth re-check is needed here.

**Network timeout posture.** This command invokes GitHub/GitLab CLI commands that perform network I/O. The CLI tools (`gh`, `glab`) use their own default timeouts; this command does NOT wrap them in an external timeout. If a CLI call hangs >120s, halt the command (Ctrl-C) and re-run after checking network connectivity. Do not auto-retry — duplicate PRs/MRs/workflow triggers may result.

- **`PLATFORM=github`**: determine the ref:
  - For `staging`: `--ref main` (or the branch configured in `ruleset/deployment.md`).
  - For `prod`: `--ref <tag>` when `team_preset = oss`; otherwise `--ref main` unless the workflow expects an explicit tag (defer to `deployment.md`).
  - Invoke: `GH_HOST="$HOST" gh workflow run <workflow-from-stack-yaml> --ref <ref>`. If the workflow accepts inputs, pass `-f environment=<env>` when the workflow declares an `environment` input; do not invent inputs the workflow does not declare.
- **`PLATFORM=gitlab`**: invoke:
  - `GLAB_HOST="$HOST" glab pipeline trigger --ref <ref> -v ENV=<env>` for the default pipeline, or
  - `GLAB_HOST="$HOST" glab ci run <pipeline-file>` when `*_workflow` names a specific pipeline file.
- **Other** (Phase 0 step 2 already aborts when neither CLI is authenticated for `$HOST`): this branch is unreachable in normal flow. Retained as a defence-in-depth fallback: `Unsupported platform. Trigger the workflow manually: <workflow_name>. Plugin does not implement raw API calls.`

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
