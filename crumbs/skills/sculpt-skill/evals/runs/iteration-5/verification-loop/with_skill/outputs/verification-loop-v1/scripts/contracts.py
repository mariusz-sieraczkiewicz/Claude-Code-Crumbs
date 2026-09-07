"""Typed data exchanged by the verification-loop skill."""

from enum import Enum

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    task: str = Field(description="The task as the user stated it, word for word.")


class WorkReport(BaseModel):
    completed: list[str]
    changed_files: list[str] = Field(description="Absolute paths.")
    left_undone: list[str] = Field(description="Each omission with its reason.")
    decisions: list[str] = Field(
        description="Each unclear point in the task and how it was decided."
    )


class ComplianceStatus(str, Enum):
    CARRIED_OUT = "carried_out"
    PARTLY_CARRIED_OUT = "partly_carried_out"
    MISSED = "missed"


class InstructionCheck(BaseModel):
    instruction: str
    status: ComplianceStatus
    evidence: str = Field(description="What the verifier inspected to reach this status.")
    suggested_fix: str | None = None


class InstructionReview(BaseModel):
    checks: list[InstructionCheck]


class OutcomeStatus(str, Enum):
    PASS = "pass"
    CONCERN = "concern"
    FAIL = "fail"


class OutcomeCheck(BaseModel):
    criterion: str = Field(description="One aspect of what success means for this task.")
    status: OutcomeStatus
    evidence: str
    suggested_fix: str | None = None


class OutcomeReview(BaseModel):
    checks: list[OutcomeCheck]
    overall: OutcomeStatus
    summary: str


class Fix(BaseModel):
    finding: str
    before: str
    after: str


class RejectedFinding(BaseModel):
    finding: str
    evidence: str = Field(description="Why the finding is mistaken.")


class FixReport(BaseModel):
    fixes: list[Fix]
    rejected: list[RejectedFinding] = []


class LoopResult(BaseModel):
    clean: bool
    iterations: int
    changes: list[str]
    unresolved: list[str] = []
    workspace: str
