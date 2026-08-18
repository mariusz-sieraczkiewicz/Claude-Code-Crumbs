"""Typed data contracts for the verification loop skill."""

from typing import Literal

from pydantic import BaseModel, Field


class TaskSpec(BaseModel):
    task: str = Field(description="The task to execute, held verbatim as the person wrote it.")


class WorkerReport(BaseModel):
    actions_performed: list[str]
    files_touched: list[str] = Field(
        description="Absolute paths of files created or modified."
    )
    deliberately_skipped: dict[str, str] = Field(
        default_factory=dict,
        description="Anything left undone, mapped to the reason it was left undone.",
    )
    ambiguities_resolved: list[str] = Field(
        default_factory=list,
        description="Ambiguities in the task the worker decided on its own.",
    )


class InstructionCheck(BaseModel):
    id: str
    demand: str = Field(description="One separate demand extracted from the task.")
    status: Literal["done", "missing", "partial"]
    evidence: str
    repair_hint: str | None = None


class InstructionVerification(BaseModel):
    checks: list[InstructionCheck]
    total: int
    done: int
    missing: int
    partial: int


class OutcomeCriterion(BaseModel):
    id: str
    criterion: str = Field(description="One quality bar the intended outcome must meet.")
    status: Literal["pass", "fail", "concern"]
    evidence: str
    repair_hint: str | None = None


class OutcomeVerification(BaseModel):
    criteria: list[OutcomeCriterion]
    verdict: Literal["pass", "fail", "concern"]
    summary: str


class FixFinding(BaseModel):
    finding_id: str = Field(description="Id of the verifier check or criterion being addressed.")
    before: str | None = None
    after: str | None = None
    rebutted: bool = Field(
        default=False, description="True when the fixer judges the finding mistaken."
    )
    rebuttal_evidence: str | None = None


class FixerReport(BaseModel):
    findings: list[FixFinding]
    files_changed: list[str] = Field(description="Absolute paths of files the fixer changed.")


class LoopResult(BaseModel):
    exit_reason: Literal["clean", "max_rounds"]
    final_round: int
    unresolved_issues: list[str] = Field(default_factory=list)
    all_changes: list[str] = Field(
        default_factory=list,
        description="Consolidated list of every change made across all rounds.",
    )
