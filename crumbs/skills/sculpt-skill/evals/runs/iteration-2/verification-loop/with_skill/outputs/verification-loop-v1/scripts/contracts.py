"""Domain types for the verification loop."""

from typing import Literal

from pydantic import BaseModel, Field


class WorkReport(BaseModel):
    """What a worker or fixer did, handed on as context for the checks."""

    done: list[str]
    changed_files: list[str] = Field(description="Absolute paths of files created or modified.")
    not_done: list[str] = Field(description="Anything left undone, each with its reason.")
    judgement_calls: list[str] = Field(
        description="Points where the task allowed more than one reading, and the reading chosen."
    )


class InstructionCheck(BaseModel):
    asked_for: str = Field(description="One thing the task asks for, in the task's own wording.")
    status: Literal["done", "partial", "missing"]
    evidence: str = Field(description="What was inspected to reach this status.")
    fix_hint: str | None = Field(default=None, description="Where fixing should start, when not done.")


class InstructionReview(BaseModel):
    checks: list[InstructionCheck]


class OutcomeCheck(BaseModel):
    criterion: str = Field(description="Something that must hold for the person to call the work a success.")
    status: Literal["pass", "concern", "fail"]
    evidence: str = Field(description="What was inspected, run or read to reach this status.")
    fix_hint: str | None = Field(default=None, description="Where fixing should start, when not passing.")


class OutcomeReview(BaseModel):
    checks: list[OutcomeCheck]


class VerificationResult(BaseModel):
    verified: bool = Field(description="True when the last check left nothing outstanding.")
    rounds: int
    changes: list[str] = Field(description="What the work produced or changed, across all rounds.")
    unresolved: list[str] = Field(description="Findings still open when checking stopped.")
