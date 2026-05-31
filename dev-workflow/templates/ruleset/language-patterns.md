# Language Patterns

**Principle:** Codify stack-specific idioms that are too local for the universal rules but too important to leave to taste. This file is intentionally empty by default — the project owns its content.

This rule is the only one in the canonical taxonomy that ships with no opinionated baseline. The plugin cannot prescribe Swift access modifiers, TypeScript `strict` flags, Python type-hint policies, Go error-wrapping conventions, Rust lifetime patterns, or Kotlin null-safety idioms without picking a stack — which would contradict the plugin's universality goal. The project's first job after bootstrap is to populate this file with the idioms its language and team actually rely on.

Examples of what belongs here (illustrative, not prescriptive — pick what applies to your stack and delete the rest):

- **Swift** — access modifier defaults (`internal` vs `fileprivate` vs `private`), `@MainActor` placement, `Sendable` conformance policy, when to prefer `struct` over `class`, `async/await` over completion handlers, `Result` vs throwing functions.
- **TypeScript** — `strict: true` posture, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `readonly` defaults, branded types for IDs, `unknown` over `any`, narrowing patterns, discriminated unions over enums.
- **Python** — type-hint coverage policy, `from __future__ import annotations`, `dataclass(frozen=True)` vs `pydantic.BaseModel` defaults, `typing.Protocol` for ports, `match`/`case` usage, exception base class hierarchy.
- **Go** — error wrapping with `%w`, sentinel-error policy, when to use `context.Context`, channel patterns, struct embedding conventions.
- **Rust** — newtype patterns for IDs, `thiserror` vs `anyhow` placement, lifetime-elision policy, `#[must_use]` discipline, `Cow<'a, T>` usage.
- **Kotlin** — null-safety posture, sealed-class hierarchies for domain errors, coroutine scope policy, data class vs value class.
- **Java / JVM** — record vs class, sealed interfaces for ADTs, `Optional` policy at boundaries, exception checked/unchecked discipline.

The pattern entries SHOULD follow the same template as other ruleset files (Principle / Mechanical enforcement / Subagent check / Examples / Anti-patterns / Cross-refs) so that the `reviewer` and `verifier` subagents can consume them uniformly. A pragmatic minimum: one section per idiom, with a Good and Bad example.

## Mechanical enforcement

Empty by default. Project fills this in once the stack is chosen — typically a combination of:

- the language's official linter (`eslint`, `ruff`, `swiftlint`, `clippy`, `gofmt`/`golangci-lint`, `ktlint`, `detekt`, `mypy`, `pyright`, `tsc --strict`),
- a formatter pinned in CI (`prettier`, `black`, `swift-format`, `rustfmt`, `gofmt`, `ktlint --format`),
- a small set of project-specific custom rules where the standard linter is silent.

## Subagent check

Empty by default. Once populated, the `reviewer` reads this file verbatim and applies whichever idioms have been written down. Until then, the reviewer skips this rule.

## Examples

<!-- Project fills in stack-specific idioms here. -->

### Good

<!-- e.g. an idiomatic Swift access-control example, or a TS branded-ID example. -->

### Bad

<!-- the matching anti-pattern. -->

## Anti-patterns

<!-- Project fills in stack-specific idioms here. -->

- <!-- bullet -->
- <!-- bullet -->

## Cross-refs

- `code-style.md` — formatting and naming concerns that are not stack-idiomatic per se.
- `architecture.md` — layering rules constrain what language features are appropriate where (e.g. no framework annotations in domain types).
- `error-handling.md` — typed-error conventions interact heavily with the language's error model.
- `testing.md` — test-double idioms are often language-specific (mock libraries, fake objects, in-memory adapters).
