# API Design

**Principle:** Public APIs are a versioned contract — idempotent where they mutate, machine-readable in error, and stable in shape across releases.

## Mechanical enforcement

The following classes of checks are mechanisable. Pick the concrete tools that fit the stack and wire them into the lint/CI step:

- **Schema linting** for OpenAPI / GraphQL / gRPC schema files. Examples: `openapi-cli lint`, `spectral lint`, `graphql-inspector`, `buf lint`. Fail the build on:
  - Missing `operationId` / unique operation names.
  - Missing `4xx`/`5xx` response definitions on mutating endpoints.
  - Path segments not matching the agreed versioning convention (`/v{N}/...` or header-based).
  - Response objects missing the canonical error envelope.
- **Breaking-change detection** between the previous tagged schema and the current one. Examples: `openapi-diff`, `buf breaking`, `graphql-inspector diff`. A breaking change is a build-time error unless the file's major version has been bumped in the same commit.
- **Static checks for idempotency keys** on `POST`/`PUT`/`PATCH`/`DELETE` handlers. A custom linter (e.g. ESLint custom rule, Semgrep pattern, ruff plugin) flags handlers that mutate state without reading an idempotency key.
- **Error envelope shape check.** A unit/contract test asserts every error response matches the agreed envelope: `{ "code": "<machine-readable>", "message": "<human readable>", "details": {...} }`.
- **Forbidden field scanner.** A regex/AST check rejects payloads that include internal identifiers (auto-increment DB IDs, table names, internal service names) — public APIs expose opaque IDs only.
- **Pagination shape check.** Contract tests assert list endpoints return the canonical pagination envelope (cursor or page-based — pick one project-wide, not per-endpoint).

If the project has no schema-first source (hand-written controllers only), introduce one. A schema is the cheapest way to make the contract reviewable.

## Subagent check

The `reviewer` and `verifier` look for what schema linters cannot see:

- **Semantic versioning of behaviour, not just shape.** Renaming a field is a breaking change. Tightening a validation rule (e.g. shortening a max length) is a breaking change. Loosening a response (e.g. dropping a previously-guaranteed field) is a breaking change. The schema diff tool catches the shape; the reviewer catches the behaviour.
- **Idempotency that actually works.** Reviewer checks that the handler reads the idempotency key, stores the result keyed by it, and returns the stored result on retry — not just that the parameter exists.
- **Error codes are stable identifiers.** Reviewer rejects error codes that are free-form strings ("validation failed", "oops"). Codes must be from a documented enum, namespaced (e.g. `billing.payment.declined`), and never reused for a different meaning.
- **No internal identifiers leaked.** Reviewer scans payloads for database primary keys, internal table names, internal service names, or sequential IDs that would let a client enumerate other tenants' records.
- **Pagination and filtering are consistent across endpoints.** If `/orders` uses cursor pagination, `/invoices` does not use offset/limit. Reviewer flags inconsistency.
- **State-mutating verbs are correctly chosen.** `GET` never mutates. `PUT` is idempotent. `POST` is for creation or non-idempotent actions. `DELETE` is idempotent (second call returns the same terminal state, not an error).
- **Authentication and authorisation scope** is documented per endpoint, not assumed from a global middleware.

## Examples

### Good

Versioned path, idempotency key honoured, structured error, opaque ID:

```http
POST /v1/payments
Idempotency-Key: 9b2f8c5e-7a3d-4e8f-bc11-2a9d8e7f6c5b
Content-Type: application/json

{
  "amount": { "currency": "EUR", "minor_units": 1299 },
  "source": "pm_01HXYZABC",
  "description": "Order #A-2026-0184"
}
```

Response on retry — same body, same status:

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "pay_01HXYZDEF",
  "status": "succeeded",
  "created_at": "2026-05-18T09:14:02Z"
}
```

Error envelope:

```json
{
  "code": "payments.source.declined",
  "message": "The payment source was declined by the issuer.",
  "details": {
    "decline_reason": "insufficient_funds",
    "retry_after_seconds": 3600
  }
}
```

List endpoint with consistent pagination:

```json
{
  "data": [ { "id": "pay_01HXYZDEF", "status": "succeeded" } ],
  "page": {
    "next_cursor": "eyJpZCI6InBheV8wMUhYWVpERUYifQ==",
    "has_more": true
  }
}
```

### Bad

```http
POST /payments
Content-Type: application/json

{
  "internal_user_id": 4821,
  "payments_table_row_id": 99182,
  "amount": 12.99
}
```

```json
{
  "error": "something went wrong",
  "stack": "TypeError: cannot read property 'foo' of undefined at ..."
}
```

Problems: no version in the URL or in a header; database row IDs and internal table names exposed; `amount` is an ambiguous float without currency; the error has no machine-readable code, a useless human message, and leaks a stack trace.

## Anti-patterns

- No version at all in URL or header — any change is a breaking change for every client.
- Idempotency advertised in docs but the handler does not actually deduplicate by the key.
- Error responses with HTTP status 200 and `{ "ok": false }` in the body — clients cannot route on status.
- Error codes that are sentences (`"User not found, please check the ID"`) instead of stable identifiers (`"users.not_found"`).
- Exposing auto-increment database IDs, table names, or internal service hostnames in payloads.
- Mixing pagination strategies across endpoints in the same product.
- `GET` endpoints with side effects (creating, mutating, sending mail).
- `DELETE` returning `404` on second call instead of the same terminal state.
- Sniffing the user agent or "client version" to change behaviour silently — version the API instead.
- Free-form `additionalProperties: true` on response objects so the shape drifts over time.
- Stringly-typed enums where a closed enum was possible (`"status": "ok" | "OK" | "Ok" | "success"`).
- Returning `null` and `undefined` interchangeably for "no value".

## Cross-refs

- `error-handling.md` — the error envelope defined here is what server code must produce; how the server gets there is in error-handling.
- `security.md` — authentication, authorisation, rate limiting, and PII handling on the wire.
- `data-modeling.md` — opaque public IDs vs internal primary keys.
- `documentation.md` — every public endpoint has a schema entry and a changelog line on every change.
- `testing.md` — contract tests assert the envelope, the pagination shape, and the breaking-change diff.
