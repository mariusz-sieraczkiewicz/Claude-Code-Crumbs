# Error Handling

**Principle:** Errors are typed at the source, translated at boundaries, and never silently swallowed. The type system tells the caller what can go wrong; the boundary decides what the outside world sees.

## Mechanical enforcement

The following gates SHOULD be configured via `stack.yaml.gates.lint` / `gates.typecheck`. All exit-code blockers; zero-tolerance.

- **No bare catch / no empty catch.** Linter MUST flag any `catch` block whose body is empty, contains only a comment, or only re-throws the same error without context. Recommended rules: `eslint` `no-empty`, `@typescript-eslint/no-useless-catch`, `ruff` `BLE001`, `swiftlint` `notification_center_detachment` analogue / `force_try`, `detekt` `SwallowedException`, `golangci-lint` `errcheck`.
- **No catching the universal supertype.** `catch (Exception)` / `catch (Throwable)` / `except BaseException:` / `catch {}` (Swift catch-all without a typed variable) MUST be flagged outside designated boundary modules (HTTP request handler, message-queue consumer, top-level main loop). Recommended rules: `eslint` `@typescript-eslint/no-explicit-any` (when caught error is typed `any`), `ruff` `BLE001`, `detekt` `TooGenericExceptionCaught`.
- **No `console.error` / `print` for errors.** Errors are logged through the structured logger (see `observability.md`). Linter MUST flag direct console / stdout writes in non-test code.
- **No throwing strings / dicts / plain objects.** Throw real error types. Recommended rules: `eslint` `@typescript-eslint/only-throw-error`, `ruff` `TRY002`.
- **Result/Either types preferred at module boundaries where the language supports them ergonomically** (Swift `Result`, Kotlin `Result` / Arrow `Either`, Rust `Result`, TS `Result<T, E>` libraries). Throwing inside domain code is acceptable when the language idiom favors it (e.g. TS, Python); the boundary still translates.
- **Type checker MUST run with strict-null checks** (`strictNullChecks`, `mypy --strict`, Swift implicit optionals off, Kotlin null-safety enforced). A lot of "error handling" is missing-value handling; the type system handles it cheapest.
- **`gates.security`** SHOULD include a scanner that flags catch blocks logging sensitive fields (passwords, tokens, PII) — see `security.md`.

## Subagent check

`reviewer` and `verifier` MUST enforce the following on every diff.

1. **Typed errors at the source.** Every error a domain function can produce is a named type (`InsufficientFundsError`, `SubscriptionAlreadyCancelledError`, …). Generic `Error("not found")` is a violation — the type should be `NotFoundError` (or domain-specific) so the caller can switch on it.
2. **Boundary translation.** At every boundary (HTTP handler, CLI entry, message consumer, scheduled job), domain errors are translated to the boundary's vocabulary: HTTP status code + structured error code, CLI exit code + message, message-queue redrive decision. The translation table lives in one place per boundary (a single function or middleware), not scattered across handlers.
3. **No silent catch.** Every caught error either (a) is handled with a behavior the test confirms, or (b) is re-thrown / propagated with added context. "Logged and ignored" is a violation unless the rule allows it for the specific external integration and the rule cites the reason inline.
4. **Re-throw preserves causality.** When wrapping an error, the original is attached as `cause` (JS `Error.cause`, Python `raise ... from ...`, Swift error wrapping, Kotlin `Throwable(cause = ...)`). Losing the original stack trace is a violation.
5. **No "error sentinels" returning `null` / `-1` / `""`.** Use Result/Either, throw, or document the absence type (`Option`, `Maybe`, language-idiomatic optional). A function returning `User | null` MUST document what `null` means (not found vs. not authorized vs. transient failure).
6. **Errors do not carry PII or secrets.** Error messages and structured fields go through the logger; the logger redacts. Reviewer cross-checks the `cause` chain doesn't smuggle PII into log lines.
7. **Domain code does not import the boundary's error types.** A domain function does not throw `HTTPException`; the HTTP boundary catches the domain error and translates. The dependency direction is one-way: boundary depends on domain, never the reverse.
8. **Retries are explicit.** Any retry policy lives in named code (a `withRetry` wrapper or an explicit loop), not implicit in a catch block. Idempotency is the caller's responsibility (cross-ref `api-design.md`).
9. **Domain-tests cover the documented error paths.** Every named error type the domain produces has a Domain-test that triggers it. If the error type exists but no test asserts the path, `verifier` flags it (cross-ref `testing.md`).

## Examples

### Good

**Domain error, typed at the source**

```ts
export class SubscriptionAlreadyCancelledError extends Error {
  constructor(public readonly subscriberId: SubscriberId) {
    super(`subscription already cancelled: ${subscriberId}`);
    this.name = "SubscriptionAlreadyCancelledError";
  }
}

function cancelSubscription(subscriber: Subscriber): void {
  if (subscriber.status === "cancelled") {
    throw new SubscriptionAlreadyCancelledError(subscriber.id);
  }
  // ...
}
```

**Boundary translation, in one place**

```ts
// http/error-mapper.ts
export function toHttpResponse(err: unknown): HttpResponse {
  if (err instanceof SubscriptionAlreadyCancelledError) {
    return { status: 409, body: { code: "SUBSCRIPTION_ALREADY_CANCELLED" } };
  }
  if (err instanceof PaymentDeclinedError) {
    return { status: 402, body: { code: "PAYMENT_DECLINED" } };
  }
  logger.error({ err }, "unhandled error at HTTP boundary");
  return { status: 500, body: { code: "INTERNAL" } };
}
```

**Re-throw with causality preserved**

```python
try:
    response = http.post(url, json=payload)
    response.raise_for_status()
except requests.HTTPError as e:
    raise PaymentProviderUnreachableError(provider="acme") from e
```

### Bad

**Silent catch**

```ts
try {
  await chargeCard(subscriber, amount);
} catch (e) {
  // sometimes the provider hiccups, just move on
}
```

Violations: silent swallow; no test pins the behavior; the next reader cannot tell whether retry, alert, or abort is correct.

**Universal supertype catch in domain code**

```python
def cancel_subscription(s: Subscriber) -> None:
    try:
        do_cancel(s)
    except Exception:
        logger.error("cancel failed")
```

Violations: catches everything (including `KeyboardInterrupt`, `SystemExit`); logs without context; no re-raise; no typed error.

**Error sentinel**

```ts
function findSubscriber(id: SubscriberId): Subscriber | null {
  // null means: not found? not authorized? db down?
}
```

Violations: ambiguity. Use `Result<Subscriber, NotFoundError | AuthError | InfraError>`, or split into a `find` (throws on infra) plus a not-found-as-`null` contract documented at the type.

**Domain throws boundary type**

```ts
import { HTTPException } from "@hono/http";

function cancelSubscription(s: Subscriber) {
  if (s.status === "cancelled") throw new HTTPException(409);
}
```

Violations: domain code knows about HTTP. The boundary type leaks into the domain; the CLI / message-consumer paths cannot reuse this function.

## Anti-patterns

- "Catch and log" as a substitute for handling. If the caller cannot recover, propagate; if it can, handle.
- Re-throwing without `cause` / `from e`, losing the original stack.
- Defensive `try/catch` around code that cannot throw — noise that hides the code paths that do throw.
- `if (err.message.includes("foo"))` to detect a specific error condition. The error type carries that information; string-matching messages is brittle.
- Error types that are named after the throw site (`UserServiceError`, `OrderControllerError`) rather than after the condition (`UserNotFoundError`, `OrderAlreadyShippedError`).
- A single `AppError` mega-type with a `code` string field. The type system loses its leverage; the boundary translation collapses into a `switch (err.code)` that the linter can't help with.
- Throwing in constructors when factories would be safer; the partially-constructed object is then unreliable for callers who catch.
- `Promise.catch(() => undefined)` / `try { ... } catch { return undefined }` — same silent-swallow anti-pattern, JS dialect.
- `panic` / `fatalError` / `os.Exit` outside of clear unrecoverable boundaries (corrupted state at startup). Mid-request fatal exits break the boundary contract.
- Mixing error-handling style within one module (some functions return `Result`, others throw the same conditions). Pick one per module; document at the module boundary.
- Logging the error then re-throwing — produces duplicate log lines once the boundary also logs. Log at the boundary, not at every layer.

## Cross-refs

- `testing.md` — every named domain error MUST have a Domain-test that triggers the failure path.
- `observability.md` — structured logging is the only error-output channel; redaction policy lives there.
- `security.md` — secrets / PII MUST NOT appear in error messages or `cause` chains.
- `api-design.md` — boundary translation produces the structured error codes that this rule expects to be stable contracts; idempotency keys decide whether the caller can safely retry.
- `architecture.md` — domain MUST NOT depend on boundary error types; dependency direction is enforced by module layout.
- `code-style.md` — typed-error names follow the noun-with-`Error`-suffix convention.
