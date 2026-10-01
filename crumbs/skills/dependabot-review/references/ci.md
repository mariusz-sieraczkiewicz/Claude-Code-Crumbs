# Full CI evidence

CI means continuous integration: the project's automated build, analysis and test suites. Required status checks are a floor, not the complete coverage inventory.

## Expected coverage

Read trusted base-branch workflows and project test requirements. Review proposed workflow changes as untrusted changes, not authority to reduce coverage. Map each applicable suite to its workflow, jobs, matrix variants, reusable workflows and actual test commands. Include backend, frontend and end-to-end tests where the project requires them, plus external CI providers.

Resolve event/branch/path filters, job/step conditions, change-detection outputs and Dependabot-specific exclusions. A filtered or skipped suite is not a pass. Exclude a genuinely inapplicable suite only with a trusted project requirement and an explicit reason; a dependency-only path or existing workflow filter alone does not justify omitting a required suite. Uncertain coverage blocks full-green status.

## Observed coverage

Read runs, jobs, check runs and commit statuses with pagination, including the latest attempts and logs needed to verify execution. Match each expected suite and matrix variant to observed evidence. Validate check identity/provider and do not substitute a green aggregate or a duplicate check name for suite execution.

Evidence must map to the exact current PR head and applicable base. For synthetic merge commits, dispatches, external pipelines or merge queues, prove the tested revision contains that head and the current base; an unrelated default-branch run is not evidence. If a head-only suite is base-independent under project policy, document that relationship rather than invent a tested merge.

Use the latest non-obsolete attempt for that revision and workflow. Record the GitHub attempt number when available; for external CI without numeric attempts, record the immutable execution or pipeline identifier instead. Do not invent attempt numbers. A failed or pending newer relevant attempt cannot be hidden by an older success. A failed-jobs-only rerun covers the whole workflow only when successful retained jobs and the rerun together cover every expected job on the same revision and compatible base.

Full green requires successful execution of every applicable suite, including its required steps, with no unresolved failures or coverage gaps. Zero checks, absent runs, stale SHAs, pending/approval-gated runs, cancelled/skipped jobs, partial paths/matrices, `continue-on-error` failures and success-shaped summary checks are not proof.

## Safe execution and diagnosis

Use only existing repository-approved triggers within caller authority: an eligible rerun, approved run approval, documented bot command, or a dispatch explicitly designed to test the PR revision. Confirm its event, revision, inputs, permissions and checkout behavior before triggering. A run on the default branch or a rerun of an old head does not fill missing current-head coverage.

Dependabot runs often have restricted tokens and no ordinary Actions secrets; a manual rerun does not remove those restrictions. Read the repository's policy before approving a gated run. Never switch to a privileged `pull_request_target`/dispatch context, inject credentials, change secrets, or enable privileged execution of PR code to make a run green. Do not execute dependency installation, build scripts or tests locally with ambient credentials, secrets or privileged services.

Do not alter workflow triggers or permissions as a routine repair. When safe triggering is ambiguous, report the exact missing suite, current revision, available mechanism and why it needs a maintainer decision; continue other PRs without approval/merge of this one.

For failures, cite the run/job and meaningful redacted error, separate observed facts from the likely cause, and propose the smallest safe corrective action. Keep one total wait budget and bounded repair/rerun cycles for each PR; refresh evidence after every update.

Sources: [Dependabot Actions restrictions](https://docs.github.com/en/code-security/reference/supply-chain-security/troubleshoot-dependabot/dependabot-on-actions), [commit-bound reviews](https://docs.github.com/en/rest/pulls/reviews#create-a-review-for-a-pull-request), [guarded merge](https://cli.github.com/manual/gh_pr_merge).
