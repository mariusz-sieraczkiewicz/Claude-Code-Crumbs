# Validation Rules

## Fail Fast

- Reject invalid data immediately at the point of entry — never let bad input propagate deeper
- If validation fails, stop execution and return a clear error; no partial processing, no fallback logic
- Environment configuration validates on startup — the app crashes if required values are missing

## Parse, Don't Validate

- Transform and validate in one step, producing typed output directly
- Never validate data and then cast it separately — parsing gives both correctness and the typed result
- Derive types from the validation schema (schema is the single source of truth), not the other way around

## Validate at System Boundaries Only

- **Boundaries** (untrusted → trusted): API request input, environment variables, database reads, LLM responses, file uploads, external service responses
- **Internal code** (trusted): services, domain logic — do not re-validate data that was already parsed at the boundary
- Once data crosses a boundary via schema parsing, it is trusted for the remainder of that execution path
- Redundant validation deeper in the stack is a code smell — it means the boundary wasn't enforced properly

## Boundary Responsibilities

- **Controllers / route handlers**: parse request body, query params, path params before calling services
- **Repositories / data access**: parse database output on read to guarantee domain types
- **External service adapters**: parse third-party responses (APIs, LLMs, file content) before returning to callers
- **Services / domain logic**: receive already-validated domain types — no validation calls inside service logic

## Schema Design

- One validation schema per domain entity — reused across boundaries
- Compose schemas via derivation (omit, pick, extend) to avoid duplication
- Colocate schemas with their domain (alongside models and services)
- Reject unknown fields on input schemas (strict mode) to prevent silent data leakage
