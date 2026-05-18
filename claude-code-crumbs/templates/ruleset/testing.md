# Testing

**Principle:** One Step library, three Worlds. Every Business scenario yields one ATDD spec (happy) and one or more Domain-tests (happy + edges). Journeys compose scenarios at the product level for promotion smoke gating.

## Mechanical enforcement

The following gates are wired into `stack.yaml.gates` and run automatically during `/003-verify-dod`. Exit code `0` = pass, anything else = blocker (zero-tolerance, see Finding policy).

- `gates.domain_tests` — runs the full Domain-test suite. MUST pass on every commit, every gate-check, every `/002-implement` GREEN transition. Domain-tests have no infrastructure, so the suite SHOULD complete in seconds; if it slows below the project's "inner loop" budget, the rule has been violated (likely a real I/O leak — see Anti-patterns).
- `gates.atdd_specs` — runs the ATDD spec suite against near-real infrastructure. MUST pass at epic close-out. Project decides whether to also run per-task or only at epic-end; the plugin assumes epic-end only.
- `gates.journeys` — runs Journey suite at environment promotion (`/007-promote`). MUST pass before promoting to staging/prod.
- Lint/format gates (`gates.lint`) MUST enforce a test-naming convention that distinguishes the three artifacts (e.g. `*.domain.test.ts` / `*.atdd.spec.ts` / `*.journey.ts`, or analogous Swift target names). Mixing artifact types in one file is a lint error.
- A custom lint rule (or repository pre-commit hook) MUST reject any direct test-body call to a Page Object, HTTP client, or DB driver. All actuation MUST go through the Step library. Recommended tools: project's existing linter (`eslint` with a custom rule, `ruff` plugin, `swiftlint` custom rule, `detekt` rule, etc.) or a simple `grep`-based pre-commit check.
- A custom lint rule MUST reject UI vocabulary inside Domain-tests and inside Business scenario Gherkin files. Banned tokens at minimum: `click`, `button`, `screen`, `page`, `url`, `selector`, `tap`, `scroll`. The same tokens are allowed in ATDD spec / Journey sources because those Worlds actuate UI.
- The Step library directory (e.g. `tests/steps/`, `Tests/Steps/`) MUST be the only place where step functions are defined. Lint MUST flag step definitions outside this directory.
- Coverage tooling MUST report Domain-test coverage separately from ATDD/Journey coverage. The two coverage numbers serve different purposes (Domain-test coverage = correctness of business logic; ATDD/Journey coverage = behavior coverage) and conflating them hides gaps.

## Subagent check

`verifier` and `reviewer` MUST enforce the following on every diff. None of these is fully mechanizable.

1. **Step library discipline.** Every action verb inside a Business scenario MUST map 1:1 to exactly one function in the Step library, named identically (case-normalized). If a task introduces a new scenario verb, the diff MUST include the corresponding step function. New ad-hoc test helpers are a violation — they belong in the Step library.
2. **World-agnostic steps.** Step function bodies MUST receive a `World` (e.g. `DomainWorld`, `BrowserWorld`, `DeviceWorld`) and route all side effects through it. A step that branches on World type (`if (world instanceof BrowserWorld) ...`) is a violation; split it into two step functions or push the branch into the World implementation.
3. **Coverage policy.** For every Business scenario touched by the task: confirm exactly one ATDD spec exists (happy path only) and at least one Domain-test exists (happy + each documented edge case). Edge cases living inside an ATDD spec are a violation — move them to Domain-tests.
4. **UI-ignorance of Business scenarios and Domain-tests.** Reviewer reads every modified scenario / Domain-test and flags any UI vocabulary that slipped past the lint rule (paraphrases, screenshots, image diffs, accessibility selectors used as "the cancel button"). The behavior must read as business behavior even if the entire UI is rewritten.
5. **No method-level mocks in Domain-tests.** Domain-tests use in-memory repositories, in-memory event buses, and stub external systems at their public boundary. Mocking a method on a domain object under test (`jest.spyOn(order, 'cancel')`, equivalent in Swift/Kotlin) is a violation — it tests the mock, not the behavior. Vertex Testing principle: instantiate the real domain object graph.
6. **ATDD spec is the executable form, not a re-write.** Each ATDD spec body MUST be a near-verbatim sequence of Step library calls matching the Gherkin order of its Business scenario. Reordering, additional assertions outside the scenario's Then-clauses, or extra setup that changes the meaning are violations.
7. **Journey composition.** Journeys MUST be authored as ordered sequences of step calls drawn from existing Business scenarios. A Journey that introduces a new step (not present in any scenario) is a violation — the step belongs to a scenario first.
8. **TDD entry-point.** No production code change without a prior failing test (Domain-test in the inner loop; ATDD spec at planning time). `reviewer` MUST check the commit ordering inside the task branch (or the diff structure if squashed) and flag implementation-before-test.
9. **No skipped tests, no `.only`, no commented-out tests.** Any `xit`/`xdescribe`/`it.skip`/`fdescribe`/`it.only`/`fit`/Swift `XCTSkip` without a tracked ticket reference in the same diff is a violation.
10. **One ATDD spec per task.** The task's `atdd_spec:` field in `epic-{id}-tasks.yaml` MUST point to exactly one file. Multiple ATDD specs per task indicates the task is too big — `implementer` should have signaled `too_big_proposal`.

## Examples

### Good

**Business scenario (epic-level, domain-oriented, UI-ignorant)**

```gherkin
## Scenario: Subscriber cancels mid-cycle and is refunded the unused portion

Given an active monthly subscription that started 10 days ago
When the subscriber cancels the subscription
Then the subscription is cancelled effective immediately
And a refund is issued for the unused 20 days
And no further invoices are generated
```

Note: no mention of buttons, screens, URLs, forms. The same scenario survives a complete UI rewrite.

**Step library function (world-agnostic)**

```ts
// tests/steps/subscription.ts
export async function cancelSubscription(world: World, subscriberId: string) {
  await world.cancelSubscription(subscriberId);
}

export async function aRefundIsIssued(world: World, subscriberId: string, days: number) {
  const refund = await world.lastRefundFor(subscriberId);
  expect(refund.days).toBe(days);
}
```

The same step runs against `DomainWorld` (in-memory aggregates) for Domain-tests and against `BrowserWorld` (real browser) for the ATDD spec.

**Domain-test (multi-class, no infrastructure, edge case)**

```ts
// tests/domain/subscription-cancel.domain.test.ts
test("cancellation on day 0 issues full refund", async () => {
  const world = new DomainWorld();
  await world.givenActiveSubscription({ id: "s-1", startedDaysAgo: 0 });
  await cancelSubscription(world, "s-1");
  await aRefundIsIssued(world, "s-1", 30);
});
```

The body reads as Gherkin. The aggregates are real; the repositories are in-memory; no HTTP, no DB.

**ATDD spec (one per task, happy path only)**

```ts
// tests/e2e/specs/subscription-cancel.atdd.spec.ts
test("subscriber cancels mid-cycle and is refunded the unused portion", async () => {
  const world = new BrowserWorld(page);
  await world.givenActiveSubscription({ id: "s-1", startedDaysAgo: 10 });
  await cancelSubscription(world, "s-1");
  await aRefundIsIssued(world, "s-1", 20);
});
```

Identical body to the Domain-test, different World. Edge cases (day 0, day 29, already-cancelled, payment provider down) live in Domain-tests, never here.

**Journey (product-level smoke gate)**

```ts
// tests/journeys/lifecycle.journey.ts
test("signup → onboard → first purchase → downgrade → cancel", async () => {
  const world = new BrowserWorld(page);
  await signUp(world, ...);
  await completeOnboarding(world, ...);
  await purchaseFirstItem(world, ...);
  await downgradePlan(world, ...);
  await cancelSubscription(world, ...);
  await accountIsClosed(world, ...);
});
```

Every line is a step drawn from an existing Business scenario. The Journey adds no new vocabulary.

### Bad

**Business scenario contaminated with UI**

```gherkin
## Scenario: User clicks Cancel button
Given the user is on /account/subscription
When the user clicks the "Cancel subscription" button
And confirms in the modal
Then the page navigates to /account/cancelled
```

Violations: UI vocabulary throughout (`clicks`, `button`, `/account/subscription`, `modal`, `page navigates`). The scenario does not survive a UI rewrite. Rephrase in terms of business outcomes (cancellation effective, refund issued, etc.).

**Domain-test that mocks individual method calls instead of using in-memory aggregates**

```ts
test("OrderService.cancel calls repository.save", () => {
  const repo = { save: jest.fn() };
  const svc = new OrderService(repo);
  svc.cancel("o-1");
  expect(repo.save).toHaveBeenCalled();
});
```

Note: this is what "unit test" connotes in many codebases — single-class, method-mocked. CONTEXT.md lists "unit test" as a forbidden synonym because Domain-tests cover multi-class behaviour with in-memory aggregates, not method-mocked single classes.

Violations: mocks the collaborator, tests the wiring not the behavior, single-class scope. A Domain-test instantiates the real domain graph and asserts business outcomes.

**ATDD spec carrying edge cases**

```ts
test("cancel flow", async () => {
  // happy path
  await cancelSubscription(world, "s-1");
  // edge case 1: already cancelled
  await cancelSubscription(world, "s-2"); // expect error
  // edge case 2: payment provider down
  await world.simulatePaymentOutage();
  await cancelSubscription(world, "s-3"); // expect retry
});
```

Violations: multiple paths in one ATDD spec; edge cases live exclusively in Domain-tests. Split: one ATDD spec on the happy path; three Domain-tests for the happy + two edges.

**Step branching on World**

```ts
async function cancelSubscription(world: World, id: string) {
  if (world instanceof BrowserWorld) {
    await world.page.click('[data-testid="cancel-btn"]');
  } else {
    await world.repo.cancel(id);
  }
}
```

Violations: the step is no longer world-agnostic. Push both behaviors into the respective World implementations; the step just calls `world.cancelSubscription(id)`.

## Anti-patterns

- Calling Page Objects or HTTP clients directly from a test body. All actuation goes through the Step library.
- Using "unit test" as a synonym for Domain-test. Domain-tests are multi-class by construction; the word "unit" is misleading and forbidden in CONTEXT and rule discussions.
- Using "e2e test", "acceptance test", or "feature test" as a synonym for ATDD spec. The plugin's vocabulary is precise; synonyms erode it.
- Using "smoke test", "integration test", or "regression suite" as a synonym for Journey.
- Method-level mocks (`spyOn`, `mock.method`, partial mocks) inside Domain-tests. Stub at the external boundary (HTTP client, DB driver) or use in-memory implementations; never mock the system under test.
- Sharing mutable state across Domain-tests. Each test instantiates its own World; isolation is part of the rule.
- Snapshot tests as a substitute for behavior assertions. Snapshots capture rendering, not behavior; they belong to UI-component tests at most, never to Domain-tests / ATDD specs / Journeys.
- "Flaky" tests marked as known-flaky and retried. A flaky ATDD spec or Journey is a real defect (race condition, leaky infrastructure, non-deterministic data). Retries hide the bug.
- Running ATDD specs per-task. ATDD specs execute at epic close-out only; per-task execution slows the inner loop and contradicts the cadence rule.
- Authoring a Journey at the epic level. Journeys are decided at the product level (typically 3-7 per product) and compose scenarios across many epics.
- Edge cases authored only as Gherkin examples (Examples tables) in the Business scenario. The Business scenario covers the canonical behavior; edge cases live in Domain-tests where they execute cheaply.
- Generating ATDD specs from Business scenarios at task-end as an afterthought. The ATDD spec is written during the task; planner records its target path in `atdd_spec:` before implementation begins.
- Hiding setup inside `beforeEach`/`setUp` that mutates the World in ways the test body doesn't show. The Step library's `given*` functions exist precisely so setup is visible at the call site.
- "Helper" files outside the Step library that wrap multiple steps into shortcuts. The Step library is the only abstraction; shortcuts erode the 1:1 verb mapping.

## Cross-refs

- `architecture.md` — vertical slices and the layered domain/application/infra split shape which classes the Domain-test exercises; the Step library lives at the application boundary.
- `code-style.md` — naming and lint rules that enforce the test-file taxonomy (`*.domain.test.*`, `*.atdd.spec.*`, `*.journey.*`).
- `error-handling.md` — typed errors and boundary translation determine what assertions Domain-tests make on failure paths.
- `data-access.md` — protocol-per-aggregate is what enables in-memory repositories for `DomainWorld`; without it, Domain-tests cannot avoid infrastructure.
- `documentation.md` — Business scenarios are the lighthouse; their authorship cadence and SCENARIOS.md sync are documented there.
- `git-workflow.md` — per-task branch lifecycle defines when Domain-tests run (every commit) vs ATDD specs (epic-end) vs Journeys (promotion).
- See ADR-0001 in the canonical layout (`docs/adr/0001-shared-step-library-with-world-pattern.md`) for the full rationale behind Step library + World pattern.
