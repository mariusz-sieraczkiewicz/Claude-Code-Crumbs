from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

Text = Annotated[str, Field(min_length=1)]
Sha = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
Number = Annotated[int, Field(strict=True, gt=0)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReviewRequest(Contract):
    repository: Text | None = None
    trigger_ci: bool = False
    repair: bool = False
    approve: bool = False
    merge: bool = False
    max_cycles: int = Field(default=2, ge=0, le=2, strict=True)
    wait_minutes: int = Field(default=15, ge=0, le=30, strict=True)


class PRTarget(Contract):
    number: Number
    url: HttpUrl
    author_login: Literal["dependabot[bot]"]
    author_type: Literal["Bot"]
    head_sha: Sha
    base_sha: Sha


class ReviewContext(Contract):
    request: ReviewRequest
    repository: Text | None
    observed_at: AwareDatetime
    inventory_complete: bool
    pull_requests: list[PRTarget]
    access_blockers: list[Text] = Field(default_factory=list)


class SuiteEvidence(Contract):
    suite: Text
    requirement_source: Text
    state: Literal["passed", "failed", "pending", "missing", "blocked", "excluded"]
    head_sha: Sha | None = None
    base_sha: Sha | None = None
    attempt: Number | None = None
    execution_id: Text | None = Field(
        default=None,
        description="Immutable external execution or pipeline identifier when numeric attempts do not exist.",
    )
    links: list[HttpUrl] = Field(default_factory=list)
    explanation: Text

    @model_validator(mode="after")
    def passing_evidence(self) -> Self:
        if self.state == "passed" and (
            self.head_sha is None or self.base_sha is None or not self.links
            or (self.attempt is None and self.execution_id is None)
        ):
            raise ValueError("Passing coverage needs head/base mapping, execution identity and run evidence")
        return self


class PRResult(Contract):
    number: Number
    url: HttpUrl
    observed_at: AwareDatetime
    head_sha: Sha | None
    base_sha: Sha | None
    outcome: Literal[
        "merged", "ready_not_authorized", "pending", "fixed_awaiting_ci",
        "blocked", "diagnosis_proposal", "closed_externally",
    ]
    suites: list[SuiteEvidence] = Field(default_factory=list)
    compatibility_review: Text
    gates_clear: bool = False
    blockers: list[Text] = Field(default_factory=list)
    actions: list[Text] = Field(default_factory=list)
    next_step: Text
    merge_commit: Sha | None = None

    @model_validator(mode="after")
    def readiness_evidence(self) -> Self:
        if self.outcome in {"merged", "ready_not_authorized"}:
            passed = [suite for suite in self.suites if suite.state == "passed"]
            if not passed or not self.gates_clear or self.blockers:
                raise ValueError("Readiness needs executed CI and clear gates")
            if any(suite.state not in {"passed", "excluded"} for suite in self.suites):
                raise ValueError("Readiness cannot contain incomplete or failing coverage")
            if any(
                suite.head_sha != self.head_sha or suite.base_sha != self.base_sha
                for suite in passed
            ):
                raise ValueError("Readiness evidence must match the current head/base")
        if self.outcome == "merged" and self.merge_commit is None:
            raise ValueError("Merged outcome needs the observed merge commit")
        return self


class ReviewResult(Contract):
    request: ReviewRequest
    repository: Text | None
    inventory_complete: bool
    discovered_prs: list[Number]
    outcome: Literal["reviewed", "no_prs", "access_failure"]
    pull_requests: list[PRResult]
    summary: Text

    @model_validator(mode="after")
    def complete_accounting(self) -> Self:
        numbers = [pr.number for pr in self.pull_requests]
        if len(set(self.discovered_prs)) != len(self.discovered_prs):
            raise ValueError("Inventory cannot contain duplicates")
        if len(set(numbers)) != len(numbers) or set(numbers) != set(self.discovered_prs):
            raise ValueError("Account for every discovered PR exactly once")
        if self.outcome != "access_failure" and (
            not self.inventory_complete or self.repository is None
        ):
            raise ValueError("A completed review needs repository identity and full inventory")
        if self.outcome == "no_prs" and numbers:
            raise ValueError("No-PR outcome cannot contain PRs")
        if self.outcome == "reviewed" and not numbers:
            raise ValueError("An empty complete inventory must use no_prs")
        if any(pr.outcome == "merged" for pr in self.pull_requests) and not self.request.merge:
            raise ValueError("Merged outcome requires caller merge authorization")
        return self
