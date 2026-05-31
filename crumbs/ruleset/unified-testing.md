# Testing Rules (Vertex Testing)

## Two Types of Tests

Instead of the traditional test pyramid, use two domain/scenario-oriented test levels:

1. **Component tests** — instantiate real domain objects (facades, services, business rules) with in-memory adapters/stubs at the boundary (Ports and Adapters). Fast, no infrastructure, full domain coverage.
2. **E2E tests** — exercise the system through the most external boundary (UI or HTTP). Verify the full stack including real adapters, infrastructure, and deployment wiring.

Both levels are **domain/scenario-oriented** — tests describe business behaviors, not implementation details.

## TDD Sequence (Non-Negotiable)

1. Write all test scenarios first (RED)
2. Create minimal fixtures to make tests run and fail properly
3. Create stubs/in-memory adapters for boundary dependencies
4. Run tests to confirm proper failures
5. Implement production code
6. Run tests to confirm GREEN

Tests define the contract — everything else serves the tests.

## BDD Structure & Naming

Tests use given/when/then naming with domain language:

- **`given*`** — setup/preconditions, must return domain objects for chaining
- **`when*`** — the core action under test (exactly one per test)
- **`then*`** — assertions, must contain expect/assert internally, never return booleans

Example:

```
test('should create user with valid data', async () => {
    const team = await fixture.givenExistingTeam('Engineering');

    const user = await fixture.whenCreatingUser('John', team.id);

    fixture.thenUserShouldExist(user, 'John');
    await fixture.thenUserShouldBelongToTeam(user.id, team.id);
});
```

Naming rules:
- **`given*`** — MUST return domain objects (e.g., `givenExistingUser(name) → User`), never void
- **`when*`** — MUST delegate to corresponding `given*` to avoid duplication (e.g., `whenCreatingUser` calls `givenCreatedUser` internally)
- **`then*`** — MUST contain expect/assert internally, NEVER return booleans (e.g., `thenUserShouldExist(user, name): void`)
- **`_get*`**, **`_fetch*`** — private helpers without assertions
- Use descriptive fixture variable names (`userFixture`, `orderFixture`) — never generic `app` when multiple fixtures exist
- User-friendly method names hiding internals: `whenUpdatingUser()` not `whenCreatingUserVersion()`
- Mandatory blank lines between given/when/then phases
- Test names read like business specifications

## Fixture Design

One fixture class per domain concept. Fixtures compose the domain scenario API:

```
class UserFixture {
    constructor(private client: UserClient) {}

    async givenExistingUser(name: string): Promise<User> { ... }
    async whenCreatingUser(name: string, teamId: string): Promise<User> { ... }
    thenUserShouldExist(user: User, expectedName: string): void { ... }
    async thenUserShouldBelongToTeam(userId: string, teamId: string): Promise<void> { ... }
}
```

Rules:
- Accept transport/client abstraction via constructor — no coupling to protocol
- All helper methods accept variable data as parameters — no hardcoded values
- `when*` delegates to `given*` to avoid duplication
- Private helpers without assertions: prefix with `_`

## Stubbing Strategy (Ports and Adapters)

- Real, fully instantiated domain objects — facades, services, business rules run as-is
- In-memory implementations or fixed-response stubs ONLY at adapter boundaries (repositories, external clients, message publishers)
- Stubs implement the same interface (port) as the real adapter
- Fixed responses, not dynamic mocks — predictable behavior per input pattern
- Prefer real state over mocking — domain logic is authoritative

## Test Independence

- Each test gets isolated data with automatic cleanup
- No shared state between tests
- Reset all relevant state in beforeEach; restore/clear in afterEach
- Separate databases/directories per test level

## Data Flow Rules

- All verified data must be explicitly used in given/when sections
- No magic numbers — use actual returned data, not hardcoded expectations
- Inline literal test data specific to one scenario
- Literal values shared across 2+ test files → import from shared constants module
- Deterministic seeding — explicit IDs/names, no randomness

## Assertion Rules

- No intermediate assertions in helper methods
- Let schema validation catch malformed responses
- Two-assertion pattern for creation: verify returned object + verify persistence
- Assertions cover: domain state, side effects, observable behavior — not implementation details
- Each test focuses on one specific functionality — don't mix concerns

## Component Tests (with in-memory adapters)

- Instantiate real application/domain services with in-memory adapters injected at ports
- Test domain behaviors — not HTTP plumbing or framework mechanics
- Test happy path + error cases for every domain operation
- Domain model-first: work with typed domain objects, not raw data
- Same scenarios can be shared with E2E tier via transport-agnostic fixture interfaces

## E2E Tests (through external boundary)

- Exercise the system through UI or HTTP — the most external boundary
- Scenario-driven (ATDD): each acceptance criterion → one E2E test covering the full flow
- Tests read like domain scenarios — name after what the user accomplishes
- A test that only checks rendering is NOT a scenario test — every test must exercise a complete flow
- Use accessible queries (by role, label, text) for element selection
- Always wait for async UI updates before asserting

## Shared Scenario Pattern

- Scenario logic lives in shared location as transport-agnostic functions
- Runner-specific wrappers are thin — just wire the appropriate client/adapter
- Same domain scenarios run in both component (in-memory) and E2E (real boundary) tiers

## Test Execution Visibility

- Always use a live reporter — never run tests blind
- Never truncate output with pipes during test runs
- For long-running suites: stream output and monitor for pass/fail events
- Regular progress updates during long runs — silence is failure

## Coverage

- A feature without tests covering its domain scenarios is incomplete
- Both levels (component + E2E) should cover the same domain scenarios through different boundaries
- Meaningful coverage, not vanity metrics

## Anti-Patterns

- Writing implementation before test scenarios
- Mocking domain objects instead of using real instances with in-memory adapters
- Working with raw untyped data instead of validated domain types
- Status code assertions in helper methods
- Testing only metadata without verifying actual content
- Running tests without live output visibility
- Skipping async wait/guard after state changes
- Testing implementation details instead of domain behaviors
