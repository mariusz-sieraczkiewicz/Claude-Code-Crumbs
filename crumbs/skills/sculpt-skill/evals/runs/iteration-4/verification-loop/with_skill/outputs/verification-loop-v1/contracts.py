"""Typed data passed between the verification loop and its subagents."""

from typing import Literal

from pydantic import BaseModel, Field


class TaskBrief(BaseModel):
    text: str = Field(description="The user's task, word for word, never summarised.")


class WorkerReport(BaseModel):
    done: list[str] = Field(description="What was carried out, one item each.")
    changed_files: list[str] = Field(description="Absolute paths of files created or modified.")
    skipped: list[str] = Field(description="Anything left undone, each with its reason.")
    ambiguities_resolved: list[str] = Field(
        description="Each unclear point in the task and the reading chosen for it."
    )


class InstructionCheck(BaseModel):
    instruction: str = Field(description="One imperative taken from the task.")
    status: Literal["done", "missing", "partial"]
    evidence: str = Field(description="What was read, run or searched to reach this status.")
    fix_hint: str | None = None


class InstructionReport(BaseModel):
    checks: list[InstructionCheck]


class OutcomeCheck(BaseModel):
    criterion: str = Field(description="One condition the result must meet to count as success.")
    status: Literal["pass", "fail", "concern"]
    evidence: str = Field(description="What was read, run or searched to reach this status.")
    fix_hint: str | None = None


class OutcomeReport(BaseModel):
    checks: list[OutcomeCheck]
    verdict: Literal["pass", "fail", "concern"]


class Fix(BaseModel):
    finding: str
    before: str
    after: str


class RefutedFinding(BaseModel):
    finding: str
    evidence: str = Field(description="Why the finding is wrong.")


class FixerReport(BaseModel):
    fixes: list[Fix]
    refuted: list[RefutedFinding]


class LoopResult(BaseModel):
    passed: bool
    iterations: int
    changes: list[str]
    unresolved: list[str]
    workspace: str
