# Code Style

**Principle:** Style is mechanical. A linter and formatter decide; humans don't argue. Naming carries intent — types are nouns, functions are verbs, booleans read as predicates.

## Mechanical enforcement

The project's chosen formatter and linter MUST be invoked by `stack.yaml.gates.lint`. Exit code `0` = pass; anything else blocks DoD. Zero-tolerance — no warnings-as-okay mode.

- **Formatter** runs in `--check` mode in CI and `--write` locally via pre-commit hook. The formatter is the sole authority on whitespace, line length, quote style, trailing commas, and import order. Recommended tools: `prettier`, `ruff format`, `black`, `swift-format`, `ktlint`, `gofmt`. Project picks one and commits its config.
- **Linter** runs with `--max-warnings=0`. Recommended tools: `eslint`, `ruff`, `pylint`, `swiftlint`, `detekt`, `golangci-lint`. Project commits the config and pins the version.
- **Type checker** runs as a separate gate (`gates.typecheck`). Recommended tools: `tsc --noEmit`, `mypy --strict`, Swift compiler in strict-concurrency mode, Kotlin compiler with `-Werror`. `any`/`Any`/`AnyObject` casts MUST be flagged.
- **Pre-commit hook** wires formatter + linter so a developer cannot create a malformed commit. The same hook runs in CI as a belt-and-braces gate.
- **Editor config** (`.editorconfig`) MUST exist and align with formatter output (tab width, charset, final newline). The editor and the formatter agree; the developer doesn't choose.
- **Naming-convention lint rules** SHOULD be enabled where the linter supports them: `naming-convention` (eslint), `pep8-naming` (ruff), `identifier_name` (swiftlint), etc. The project's preferred casing per identifier kind lives in the linter config, not in human memory.
- **File length / function length / complexity** thresholds SHOULD be set as warnings (not errors) to surface drift; consistent threshold breaches indicate a refactoring opportunity rather than a per-PR blocker, but `verifier` MAY escalate based on context.

## Subagent check

`reviewer` reviews intent and naming — things a linter cannot judge.

1. **Names express intent.** A function called `process` or `handle` does not pass. The reviewer asks: "What does it actually do?" and proposes a verb-phrase name (`reconcileInvoice`, `dispatchRefund`).
2. **No abbreviations except the project's accepted ones.** `usr`, `cfg`, `mgr`, `ctx` (unless documented), `tmp` (outside trivial scopes) — all flagged. Industry-standard abbreviations (`url`, `id`, `http`, `db`) are fine.
3. **Boolean names read as predicates.** `isActive`, `hasPermission`, `canCancel`, `shouldRetry`. Names like `active`, `permission`, `cancel` for booleans are violations.
4. **Type names are nouns; function names are verbs.** A type called `ProcessOrder` is a violation (use `OrderProcessor` or a free function `processOrder`). A function called `order` is a violation (use `placeOrder`, `getOrder`, `findOrder`).
5. **Domain vocabulary mirrors CONTEXT.md.** If `CONTEXT.md` defines "Subscriber", the code says `Subscriber`, not `Customer`, `User`, `Account`. Synonym drift is a violation. Reviewer cross-references CONTEXT.md on every PR.
6. **No leaked implementation detail in public names.** A public method called `saveToPostgres` is a violation; it's `save` (the storage technology is a private concern of the adapter). Same for `*Json`, `*Http`, `*Cache` suffixes on domain APIs.
7. **Comments explain "why", not "what".** A comment that paraphrases the next line of code is noise; the linter can't tell. Reviewer flags it. Comments that document a non-obvious business constraint, a workaround for an external bug, or a deliberate deviation from the rule are good.
8. **No dead code, no commented-out code.** Reviewer rejects any commented-out block without a tracked-ticket reference in the same line.

## Examples

### Good

```ts
// Names express intent; type is a noun; function is a verb.
type Subscriber = { id: SubscriberId; planId: PlanId; status: SubscriptionStatus };

function cancelSubscription(subscriber: Subscriber): CancellationResult { ... }

const canCancel = subscriber.status === "active" && !subscriber.hasPendingInvoice;
```

```python
# Boolean reads as a predicate; domain vocabulary matches CONTEXT.md.
def is_eligible_for_refund(subscriber: Subscriber) -> bool: ...
```

```swift
// Verb-phrase, no abbreviations, no implementation leak.
func cancelSubscription(_ subscriber: Subscriber) async throws -> CancellationResult
```

### Bad

```ts
// Generic verb, abbreviation, boolean-without-predicate, implementation leak.
function process(s: Subscriber): boolean { ... }
function saveToPostgres(sub: Subscriber): void { ... }
const active = subscriber.status === "active";
```

```python
# Wrong casing, abbreviation, vague verb, comment paraphrases code.
def Proc_Usr(u):  # process the user
    return u.s == 1
```

```swift
// Type named like a function; function named like a noun.
struct ProcessOrder { ... }
func order(_ id: String) -> Order? { ... }
```

## Anti-patterns

- Negotiating formatter rules in PR comments. The formatter config is the negotiation; once committed, code is what the formatter produces.
- "Personal preference" comments on style. Style is mechanical, not personal.
- Disabling lint rules inline (`// eslint-disable-next-line`, `# noqa`, `// swiftlint:disable`) without a tracked-ticket reference and a one-line explanation on the same line.
- Renaming "for clarity" across many files in a single PR. Renames belong in dedicated refactor commits with a clear before/after rationale; otherwise they balloon review burden.
- Hungarian notation (`strName`, `iCount`) — the type system carries that information.
- Single-letter variable names outside trivial scopes (loop indices, simple coordinates).
- Mirror-image function pairs that don't match (`createUser` / `removeUser` instead of `createUser` / `deleteUser`). Pick one verb pair and stay consistent.
- Comments left from copy-pasted templates (`// TODO: implement`).
- Files mixing snake_case and camelCase identifiers inside the same language.
- Trailing commented-out experiments. If it might come back, it's in version control.
- Disagreeing with the linter by adjusting code to "shut it up" rather than fixing the issue.

## Cross-refs

- `testing.md` — naming convention for test files (`*.domain.test.*`, `*.atdd.spec.*`, `*.journey.*`) is enforced by the same linter.
- `documentation.md` — CONTEXT.md is the canonical vocabulary source for the naming reviewer check.
- `architecture.md` — public API names must not leak adapter / infrastructure detail; that boundary is shaped by architecture.
- `error-handling.md` — typed-error names follow the same noun/verb discipline (`PaymentDeclinedError`, not `PaymentError1`).
- `language-patterns.md` — stack-specific idioms refine (never contradict) the universal rules above.
