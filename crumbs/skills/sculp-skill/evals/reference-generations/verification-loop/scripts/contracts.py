from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Task(Contract):
    description: str


class WorkingReport(Contract):
    summary: str
    artifacts: list[str]
    claims: list[str]


class DoneInstructionCheck(Contract):
    instruction: str
    status: Literal["done"]
    issue: None


class UnresolvedInstructionCheck(Contract):
    instruction: str
    status: Literal["partial", "missing"]
    issue: str


InstructionCheck = DoneInstructionCheck | UnresolvedInstructionCheck


class PassedInstructionsReport(Contract):
    status: Literal["pass"]
    items: list[DoneInstructionCheck]
    issues: tuple[()]
    summary: str

    def all_done(self) -> bool:
        return True


class FailedInstructionsReport(Contract):
    status: Literal["fail"]
    items: list[InstructionCheck]
    issues: list[str]
    summary: str

    def all_done(self) -> bool:
        return False


InstructionsVerdict = PassedInstructionsReport | FailedInstructionsReport


class VerifyInstructionsReport(Contract):
    verdict: InstructionsVerdict

    def all_done(self) -> bool:
        return self.verdict.status == "pass"


class PassedOutcomesReport(Contract):
    status: Literal["pass"]
    issues: tuple[()]
    summary: str

    def overall_pass(self) -> bool:
        return True

class FailedOutcomesReport(Contract):
    status: Literal["fail"]
    issues: list[str]
    summary: str

    def overall_pass(self) -> bool:
        return False

OutcomesVerdict = PassedOutcomesReport | FailedOutcomesReport


class VerifyOutcomesReport(Contract):
    verdict: OutcomesVerdict

    def overall_pass(self) -> bool:
        return self.verdict.status == "pass"


class Passed(Contract):
    status: Literal["passed"]
    iteration: int
    task: Task
    workspace: Path
    working_report: WorkingReport
    instructions_report: VerifyInstructionsReport
    outcomes_report: VerifyOutcomesReport


class Stopped(Contract):
    status: Literal["stopped"]
    reason: Literal["cap_reached"]
    iteration: int
    task: Task
    workspace: Path
    working_report: WorkingReport
    instructions_report: VerifyInstructionsReport
    outcomes_report: VerifyOutcomesReport
    remaining_issues: list[str]


VerificationOutcome = Passed | Stopped


class VerificationResult(Contract):
    outcome: VerificationOutcome


def collect_remaining_issues(
    instructions_report: VerifyInstructionsReport,
    outcomes_report: VerifyOutcomesReport,
) -> list[str]:
    return [
        *instructions_report.verdict.issues,
        *outcomes_report.verdict.issues,
    ]
