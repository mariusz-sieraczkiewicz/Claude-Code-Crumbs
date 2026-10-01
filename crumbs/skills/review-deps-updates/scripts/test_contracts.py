import unittest

import yaml
from pydantic import ValidationError

from contracts import PRResult, PRTarget, ReviewRequest, ReviewResult, SuiteEvidence

HEAD = "a" * 40
BASE = "b" * 40
MERGE = "c" * 40
NOW = "2026-10-01T10:00:00Z"
URL = "https://github.com/example/project/pull/1"


def pr(**changes):
    result = {
        "number": 1, "url": URL, "observed_at": NOW,
        "head_sha": HEAD, "base_sha": BASE, "outcome": "ready_not_authorized",
        "suites": [{
            "suite": "tests", "requirement_source": ".github/workflows/ci.yml",
            "state": "passed", "head_sha": HEAD, "base_sha": BASE, "attempt": 1,
            "links": ["https://github.com/example/project/actions/runs/1"],
            "explanation": "All expected test jobs executed successfully.",
        }],
        "compatibility_review": "Release changes and project usage reviewed.",
        "gates_clear": True, "next_step": "Caller merge authorization is needed.",
    }
    return result | changes


def report(**changes):
    return {
        "request": {}, "repository": "example/project", "inventory_complete": True,
        "discovered_prs": [1], "outcome": "reviewed", "pull_requests": [pr()],
        "summary": "One PR is healthy; merge is not authorized.",
    } | changes


class ContractTests(unittest.TestCase):
    def test_official_dependabot_identity_is_accepted(self):
        target = PRTarget(
            number=1, url=URL, author_login="dependabot[bot]", author_type="Bot",
            head_sha=HEAD, base_sha=BASE,
        )
        self.assertEqual(target.author_login, "dependabot[bot]")

    def test_other_bots_and_dependabot_lookalikes_are_rejected(self):
        for login in (
            "renovate[bot]", "github-actions[bot]", "dependabot",
            "fake-dependabot[bot]", "dependabot[bot]-fake", "Dependabot[bot]",
            "dependabot-preview[bot]",
        ):
            with self.subTest(login=login), self.assertRaises(ValidationError):
                PRTarget(
                    number=1, url=URL, author_login=login, author_type="Bot",
                    head_sha=HEAD, base_sha=BASE,
                )

    def test_read_only_defaults_and_bounded_budgets(self):
        request = ReviewRequest()
        self.assertFalse(any((request.trigger_ci, request.repair, request.approve, request.merge)))
        self.assertEqual((request.max_cycles, request.wait_minutes), (2, 15))
        for changes in ({"max_cycles": 3}, {"wait_minutes": 31}, {"max_cycles": -1}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                ReviewRequest(**changes)

    def test_ready_report_yaml_round_trip(self):
        result = ReviewResult.model_validate(report())
        serialized = yaml.safe_dump(result.model_dump(mode="json"))
        self.assertEqual(ReviewResult.model_validate(yaml.safe_load(serialized)), result)

    def test_incomplete_or_failing_coverage_is_not_green(self):
        for state in ("failed", "pending", "missing", "blocked"):
            candidate = pr()
            candidate["suites"][0]["state"] = state
            with self.subTest(state=state), self.assertRaisesRegex(
                ValidationError, "Readiness needs executed CI and clear gates",
            ):
                PRResult.model_validate(candidate)

    def test_skipped_and_cancelled_are_not_suite_state_literals(self):
        for state in ("skipped", "cancelled"):
            candidate = pr()["suites"][0] | {"state": state}
            with self.subTest(state=state), self.assertRaises(ValidationError) as error:
                SuiteEvidence.model_validate(candidate)
            self.assertEqual(error.exception.errors()[0]["type"], "literal_error")

    def test_zero_or_excluded_only_ci_is_not_green(self):
        for suites in ([], [pr()["suites"][0] | {"state": "excluded"}]):
            with self.subTest(suites=suites), self.assertRaises(ValidationError):
                PRResult.model_validate(pr(suites=suites))

    def test_stale_head_or_base_is_not_green(self):
        for revision in ("head_sha", "base_sha"):
            candidate = pr()
            candidate["suites"][0][revision] = MERGE
            with self.subTest(revision=revision), self.assertRaises(ValidationError):
                PRResult.model_validate(candidate)

    def test_success_requires_links_and_mapping(self):
        for changes in ({"links": []}, {"head_sha": None}, {"base_sha": None}):
            candidate = pr()
            candidate["suites"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                PRResult.model_validate(candidate)

    def test_success_requires_execution_identity(self):
        candidate = pr()
        del candidate["suites"][0]["attempt"]
        with self.assertRaisesRegex(ValidationError, "execution identity"):
            PRResult.model_validate(candidate)

    def test_success_accepts_numeric_attempt(self):
        result = PRResult.model_validate(pr())
        self.assertEqual(result.suites[0].attempt, 1)
        self.assertIsNone(result.suites[0].execution_id)

    def test_success_accepts_external_execution_without_numeric_attempt(self):
        candidate = pr()
        suite = candidate["suites"][0]
        del suite["attempt"]
        suite["execution_id"] = "pipeline-123"
        suite["links"] = ["https://ci.example.com/pipelines/123"]
        result = PRResult.model_validate(candidate)
        self.assertIsNone(result.suites[0].attempt)
        self.assertEqual(result.suites[0].execution_id, "pipeline-123")

    def test_repository_gates_and_review_blockers(self):
        for changes in ({"gates_clear": False}, {"blockers": ["Breaking API change"]}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                PRResult.model_validate(pr(**changes))

    def test_merge_requires_authorization_and_observed_commit(self):
        merged = pr(outcome="merged", merge_commit=MERGE)
        with self.assertRaises(ValidationError):
            ReviewResult.model_validate(report(pull_requests=[merged]))
        result = ReviewResult.model_validate(report(
            request={"merge": True}, pull_requests=[merged],
        ))
        self.assertEqual(result.pull_requests[0].merge_commit, MERGE)
        with self.assertRaises(ValidationError):
            PRResult.model_validate(pr(outcome="merged"))

    def test_inventory_accounts_for_every_pr_once(self):
        for changes in (
            {"discovered_prs": [1, 2]}, {"discovered_prs": [1, 1]},
            {"pull_requests": [pr(), pr()]}, {"pull_requests": []},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                ReviewResult.model_validate(report(**changes))

    def test_no_prs_is_distinct_from_missing_access(self):
        ReviewResult.model_validate(report(
            discovered_prs=[], pull_requests=[], outcome="no_prs",
        ))
        ReviewResult.model_validate(report(
            repository=None, inventory_complete=False, discovered_prs=[],
            pull_requests=[], outcome="access_failure",
        ))
        with self.assertRaises(ValidationError):
            ReviewResult.model_validate(report(
                inventory_complete=False, discovered_prs=[],
                pull_requests=[], outcome="no_prs",
            ))

    def test_non_green_outcomes_remain_reportable(self):
        for outcome in (
            "pending", "fixed_awaiting_ci", "blocked", "diagnosis_proposal", "closed_externally",
        ):
            candidate = pr(outcome=outcome, suites=[], gates_clear=False)
            with self.subTest(outcome=outcome):
                ReviewResult.model_validate(report(pull_requests=[candidate]))


if __name__ == "__main__":
    unittest.main()
