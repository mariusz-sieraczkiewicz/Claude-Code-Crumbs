from typing import Literal

from pydantic import BaseModel, Field


class Task(BaseModel):
    request: str = Field(description="The task exactly as the person stated it.")


class WorkerReport(BaseModel):
    actions: list[str]
    changed_files: list[str] = Field(description="Absolute paths.")
    omissions: list[str] = Field(description="Each with its reason.")
    resolved_ambiguities: list[str] = Field(
        description="Each unclear point and the interpretation chosen for it."
    )


class InstructionCheck(BaseModel):
    instruction: str
    state: Literal["done", "partial", "missing"]
    evidence: str = Field(description="What was inspected to reach this state.")
    fix_hint: str | None = Field(
        default=None, description="Where a fixer should start. Absent when done."
    )


class InstructionReview(BaseModel):
    checks: list[InstructionCheck]


class OutcomeCheck(BaseModel):
    criterion: str = Field(description="One aspect of what success means for the task.")
    state: Literal["pass", "concern", "fail"]
    evidence: str = Field(description="What was inspected to reach this state.")
    fix_hint: str | None = Field(
        default=None, description="Where a fixer should start. Absent when the criterion passes."
    )


class OutcomeReview(BaseModel):
    checks: list[OutcomeCheck]


class Fix(BaseModel):
    finding: str
    before: str
    after: str


class FixReport(BaseModel):
    fixes: list[Fix]
    disputed: list[str] = Field(
        default_factory=list,
        description="Findings judged wrong, each with the evidence against it.",
    )


class LoopResult(BaseModel):
    iterations: int
    changes: list[str]
    unresolved: list[str] = Field(default_factory=list)
