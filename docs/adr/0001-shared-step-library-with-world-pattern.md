# Shared Step library with World pattern

ATDD specs and Domain-tests share one Step library, parametrised by a World (BrowserWorld, DeviceWorld, DomainWorld). The same step function — e.g. `cancelSubscription()` — executes against a real browser/device in an ATDD spec and against in-memory aggregates in a Domain-test; only the World wiring differs.

We chose this over separate-but-similarly-named step libraries (one per test type) because Vertex Testing prescribes that tests across levels "can be expressed in the same way, reducing duplication". A single Step library is also the only way the Business scenario stays a true single source of truth — refactoring a scenario's verbs becomes a one-place change instead of an N-place sync problem. Journeys (cross-feature flows at promotion) reuse the same Step library by composition.

## Consequences

- Step library is the central testing abstraction; ad-hoc steps inside test files are an anti-pattern caught by code review.
- Each World implementation is its own well-defined contract; adding a stack means adding a World, not duplicating steps.
- Test bodies (ATDD spec, Domain-test, Journey) become near-identical sequences of step calls — diff is World setup only.
