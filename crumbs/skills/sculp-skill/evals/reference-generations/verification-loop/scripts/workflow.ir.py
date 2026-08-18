from pathlib import Path

from contracts import (
    Passed,
    Stopped,
    Task,
    VerificationResult,
    VerifyInstructionsReport,
    VerifyOutcomesReport,
    WorkingReport,
)
from human_skill_runtime import (
    FileEdit,
    FileRead,
    FileWrite,
    Harness,
    RuntimePathValue,
    Shell,
    Workspace,
    WorkspaceSpec,
)

harness = Harness(
    workspace=WorkspaceSpec(
        segments=(".verification-loop", RuntimePathValue.RUN_ID),
        operation="create",
    )
)


@harness.subagent(capabilities=(FileRead, FileWrite, FileEdit, Shell))
async def execute(task: Task, workspace: Path) -> WorkingReport:
    """
    Complete $task and keep its working artifacts in $workspace.
    """
    raise NotImplementedError


@harness.subagent(capabilities=(FileRead, Shell))
async def verify_instructions(
    task: Task,
    workspace: Path,
    working_report: WorkingReport,
) -> VerifyInstructionsReport:
    """
    Turn every imperative in $task into a checklist item and independently
    verify each through source inspection and applicable checks in $workspace.

    Use $working_report only as an untrusted index of claimed work.
    Mark a completed item as done with no issue; mark any other item as partial
    or missing and explain the issue.
    """
    raise NotImplementedError


@harness.subagent(capabilities=(FileRead, Shell))
async def verify_outcomes(
    task: Task,
    workspace: Path,
    working_report: WorkingReport,
) -> VerifyOutcomesReport:
    """
    Define success from $task. Use $working_report only to locate the claimed
    artifacts in $workspace, then read each readable artifact, run each
    runnable artifact, and assess quality rather than existence.

    Report pass only when there are no issues; otherwise report fail and every
    issue.
    """
    raise NotImplementedError


@harness.subagent(capabilities=(FileRead, FileWrite, FileEdit, Shell))
async def fix(
    task: Task,
    iteration: int,
    workspace: Path,
    working_report: WorkingReport,
    instructions_report: VerifyInstructionsReport,
    outcomes_report: VerifyOutcomesReport,
) -> WorkingReport:
    """
    In iteration $iteration, repair $working_report against every missing or
    partial item in $instructions_report and every fail in $outcomes_report in
    $workspace, while preserving the intent of $task.

    Use a fix hint when evidence supports it and it addresses the root cause.
    """
    raise NotImplementedError


@harness.workflow
async def verification_loop(
    task: Task,
    workspace: Workspace,
) -> VerificationResult:
    max_iterations = 5
    working_report = await execute(task=task, workspace=workspace.path)

    for iteration in range(1, max_iterations + 1):
        instructions_report, outcomes_report = await harness.parallel(
            verify_instructions(
                task=task,
                workspace=workspace.path,
                working_report=working_report,
            ),
            verify_outcomes(
                task=task,
                workspace=workspace.path,
                working_report=working_report,
            ),
        )

        if (
            instructions_report.verdict.status == "pass"
            and outcomes_report.verdict.status == "pass"
        ):
            return VerificationResult(
                outcome=Passed(
                    status="passed",
                    iteration=iteration,
                    task=task,
                    workspace=workspace.path,
                    working_report=working_report,
                    instructions_report=instructions_report,
                    outcomes_report=outcomes_report,
                ),
            )

        if iteration == max_iterations:
            return VerificationResult(
                outcome=Stopped(
                    status="stopped",
                    reason="cap_reached",
                    iteration=iteration,
                    task=task,
                    workspace=workspace.path,
                    working_report=working_report,
                    instructions_report=instructions_report,
                    outcomes_report=outcomes_report,
                    remaining_issues=[
                        *instructions_report.verdict.issues,
                        *outcomes_report.verdict.issues,
                    ],
                ),
            )

        working_report = await fix(
            task=task,
            iteration=iteration + 1,
            workspace=workspace.path,
            working_report=working_report,
            instructions_report=instructions_report,
            outcomes_report=outcomes_report,
        )

    raise RuntimeError
