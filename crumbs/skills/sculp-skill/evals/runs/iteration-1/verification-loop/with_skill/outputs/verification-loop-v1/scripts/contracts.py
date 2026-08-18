"""Domain types for the verification-loop skill."""

from dataclasses import dataclass
from typing import Literal

InstructionStatus = Literal["done", "partial", "missing"]
OutcomeStatus = Literal["pass", "concern", "fail"]


@dataclass
class Task:
    """The work to be done, in the participant's own words."""

    statement: str


@dataclass
class WorkReport:
    """What a worker or fixer did. Produced by whoever changed something."""

    done: list[str]
    files_touched: list[str]
    not_done: list[str]  # each with its reason
    ambiguities_resolved: list[str]
    disputed_findings: list[str]  # findings judged mistaken, each with evidence


@dataclass
class InstructionCheck:
    instruction: str
    status: InstructionStatus
    evidence: str
    fix_hint: str | None


@dataclass
class InstructionVerification:
    checks: list[InstructionCheck]


@dataclass
class OutcomeCheck:
    criterion: str
    status: OutcomeStatus
    evidence: str
    fix_hint: str | None


@dataclass
class OutcomeVerification:
    checks: list[OutcomeCheck]
    overall: OutcomeStatus


@dataclass
class VerificationResult:
    passed: bool
    rounds: int
    changes: list[str]
    unresolved: list[str]
