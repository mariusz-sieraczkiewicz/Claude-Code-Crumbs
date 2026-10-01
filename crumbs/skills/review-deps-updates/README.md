# Review dependency updates

Review open Dependabot pull requests against the project's complete continuous integration (CI) requirements, not just green badges. The skill diagnoses failures and only triggers CI, repairs, approves or merges when the invoking user authorizes that action.

In Claude Code, invoke `/crumbs:review-deps-updates`. For a read-only run:

```text
/crumbs:review-deps-updates Review open Dependabot PRs in owner/repository. Report only.
```

To authorize maintenance:

```text
/crumbs:review-deps-updates Check full CI on open Dependabot PRs in owner/repository. Trigger safe approved CI, fix deterministic dependency-related failures, and approve and merge only fully green PRs under repository rules. Report uncertain failures with a proposed next step.
```

In other clients that load the plugin's skill directory, request `review-deps-updates` by name. GitHub read access is required; each mutation also needs appropriate account permissions. API permission alone does not grant user authorization.

The default limit is two repair/rerun cycles and 15 total waiting minutes per PR. The [workflow](SKILL.md) writes validated YAML evidence to a new `.workspaces/review-deps-updates/` run directory in the target project. Do not commit that directory or retain secrets in reports.

Contract validation needs Python 3.11 or later, Pydantic 2 and PyYAML 6. Use an isolated environment with `scripts/requirements.txt`; no dependency installation or live PR mutation runs automatically when the skill loads.

To check the contracts from this skill directory:

```sh
uv run --with-requirements scripts/requirements.txt python -m unittest discover -s scripts -p test_contracts.py
```
