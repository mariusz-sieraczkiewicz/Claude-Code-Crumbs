"""Domain types for the verification-loop skill."""

from typing import Literal

from pydantic import BaseModel, Field


class WorkerReport(BaseModel):
    work_done: list[str] = Field(
        description="One entry per meaningful change made while carrying out the task."
    )
    changed_files: list[str] = Field(
        description="Absolute paths of the files created or modified."
    )
    skipped: list[str] = Field(description="Anything left undone, each with its reason.")
    resolved_ambiguities: list[str] = Field(
        description="Each unclear point in the task and the reading that was chosen."
    )


class InstructionCheck(BaseModel):
    instruction: str = Field(description="One discrete instruction taken from the task.")
    status: Literal["done", "partial", "missing"]
    evidence: str = Field(description="What the verifier observed that establishes the status.")
    fix_hint: str | None = Field(
        default=None, description="Where to start when the instruction is not done."
    )


class InstructionReview(BaseModel):
    checks: list[InstructionCheck]


class OutcomeCheck(BaseModel):
    criterion: str = Field(
        description="Something the finished work must achieve for the task to count as successful."
    )
    status: Literal["pass", "concern", "fail"]
    evidence: str = Field(description="What the verifier observed that establishes the status.")
    fix_hint: str | None = Field(
        default=None, description="Where to start when the criterion is not met."
    )


class OutcomeReview(BaseModel):
    checks: list[OutcomeCheck]
    overall: Literal["pass", "concern", "fail"] = Field(
        description=(
            "Verdict over all the checks together; anything short of every check passing "
            "is not a pass."
        )
    )


class Fix(BaseModel):
    finding: str
    before: str = Field(description="The state of the work the finding described.")
    after: str = Field(description="The state of the work once the finding was resolved.")


class FixReport(BaseModel):
    fixes: list[Fix]
    disputed_findings: list[str] = Field(
        description="Findings judged mistaken, each with the evidence against it."
    )


class VerificationResult(BaseModel):
    passed: bool
    iterations: int
    changes: list[str] = Field(
        description="One entry per meaningful change made across every iteration."
    )
    unresolved: list[str] = Field(
        description="One entry per verifier finding still outstanding when the run ended."
    )
