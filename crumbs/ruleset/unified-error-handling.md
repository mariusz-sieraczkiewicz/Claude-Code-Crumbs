# Error Handling Rules

## Core Philosophy

- Only use try-catch when you can genuinely recover from the error
- Don't create fallbacks for failures — let errors propagate; catch unrecoverable errors at the top of the stack
- Never swallow errors silently — always log at minimum
- Never expose internal error details to clients in production

## Fail Fast

- Validate on boundaries (system edges, user input, external APIs)
- Validation is the first instruction in a function — fail before doing any work
- If a required resource (file, env var, config) is missing, fail immediately with a clear message
- No shallow fallbacks — a fallback for a non-existent value is misleading

## Domain Errors

- Use custom error classes with a `code` field and descriptive context
- Services throw domain errors; boundary layers (routes, controllers) catch and map to appropriate responses
- Wrap provider-specific errors into a common domain error class (include provider name, original error as cause)
- Centralize error classification — reusable taxonomy for network, timeout, validation, authorization, and not-found errors

## Error Context

Rich context in every error — what was expected, what was found, where to look, how to fix:
- Entity name and ID when something is not found
- Operation that failed and at what step
- Input that caused the failure (sanitized)
- Suggestion for resolution when deterministic

## Error Boundaries

- Global error boundary at the top of the stack catches unhandled errors
- Log all errors with request ID and relevant context at the boundary
- Return safe error responses to clients (no stack traces, no internal paths)
- Map domain errors to appropriate HTTP status codes at the route/controller layer

## HTTP Error Responses

- Validation errors → 400 with field-level details
- Authentication errors → 401 with generic message
- Authorization errors → 403 with role information
- Not found → 404 with entity type
- Internal errors → 500 with correlation ID only (no details)
- Always include a correlation/request ID so users can report it for support

## Anti-Patterns

- Catch-log-rethrow (adds noise, loses nothing by removing the catch)
- Fallback values for missing critical data (hides bugs)
- Generic `Error`/`Exception` without context or classification
- Logging exception at ERROR level when it was caught and handled (that's WARN)
- try-catch around validation logic (validation should throw, not be caught locally)
- Exposing stack traces, internal paths, or query details in client responses
