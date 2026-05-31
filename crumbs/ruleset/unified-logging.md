# Logging Rules

## Logger Setup

- One logger per module — never per instance (prevents memory leaks), never a global root logger
- Use a structured logging library, not raw print/console.log
- JSON output in production for log aggregation; human-readable output in development
- Library code: attach a null handler only — never configure logging or add handlers

## Log Levels

| Level | When to Use |
|-------|-------------|
| **DEBUG** | Diagnostic detail, off in production by default (query params, cache hit/miss, intermediate values) |
| **INFO** | Business events, normal milestones (request start/end, auth events, business actions, external calls) |
| **WARN** | Degraded but recoverable state (retries, fallbacks, approaching limits, deprecated API usage) |
| **ERROR** | Operation failed, app continues (all retries exhausted, DB failure, unhandled exception) |
| **CRITICAL** | Application-wide failure, usually followed by shutdown (connection pool exhausted, OOM, missing startup config) |

### Common mistakes

- Expected conditions as ERROR ("user not found" on lookup is INFO/DEBUG)
- Retry attempts as ERROR (attempt = WARN, final failure = ERROR)
- Caught-and-handled exceptions as ERROR (if recovered, it's WARN)
- WARN when immediate action is required (that's ERROR)
- DEBUG in production by default (noise + performance cost)

## Structured Logging

- Use structured fields, not string interpolation — context goes in separate fields, not embedded in the message
- Message field: human-readable event name describing what happened
- Standard field names (snake_case) enforced across all services — never `user_id` in one and `userId` in another
- Sanitize user-controlled inputs before logging to prevent log injection

## Essential Context ("3 AM Test")

Every log entry should let you diagnose an issue if it's all you have:

| Category | Fields |
|----------|--------|
| **When** | timestamp (ISO8601+tz), duration_ms |
| **Who** | user_id, tenant_id, source IP |
| **Where** | request_id, trace_id, service name |
| **What** | action, input params (sanitized), outcome |
| **Why** | decision branch taken, fallback reason, config applied |

## Canonical Log Line

Emit ONE comprehensive structured log per request consolidating all key telemetry — don't scatter multiple partial log lines requiring correlation.

## What to Log

- Request start/end with timing
- Authentication events (success and failure)
- Authorization failures and access control violations
- Business actions (create, update, delete domain entities)
- External service calls and outcomes (status, latency, retry count)
- State transitions ("Order PENDING → FAILED, trigger: payment_declined")
- Retry exhaustion, fallback activations, circuit breaker transitions
- Startup configuration (all non-secret values)
- Scheduled job execution (start, end, outcome)
- Input validation failures

## Never Log

- Passwords, tokens, API keys, secrets, encryption keys — not even hashed
- Session identifiers, JWTs
- Credit card numbers, government IDs, health data
- Database connection strings with embedded credentials
- Full request/response bodies of sensitive endpoints

## Log with Caution (always redact)

- Email addresses, phone numbers, IP addresses, user names — mask or anonymize
- Request bodies — log structure, redact sensitive field values

## Sensitive Data Redaction

- **Redact at application level before data reaches the logger** — pipeline-level regex is a safety net, not the primary mechanism
- Never log raw error objects — destructure to known fields; `error.message` may contain tokens or connection strings that bypass field-level redaction
- Define redaction rules for known sensitive keys (password, token, api_key, secret, authorization, credit_card)

## Log Correlation

| ID | Scope |
|----|-------|
| `trace_id` | Cross-service, full request lifecycle |
| `span_id` | Single operation within a service |
| `request_id` | Single service, single request |
| `correlation_id` | Business process spanning multiple requests |
| `session_id` | User session |

- Generate trace_id at the edge (API gateway)
- Propagate via standard headers (W3C Trace Context)
- Store in thread-local / context-local storage for automatic injection into all log statements
- Return correlation ID in error responses for support

## Performance

- **Lazy evaluation** — never construct expensive log messages if the level is disabled; check level first or use deferred formatting
- **Async logging** — offload serialization and I/O to background threads/queues; never block the request path
- **Avoid logging in tight loops** — aggregate or sample; log batch summary instead of per-iteration
- **Sampling for high-volume systems** — sample a percentage for detailed logging; always log 100% of errors, warnings, and slow requests
- **Dynamic log levels** — enable runtime changes without redeployment; auto-revert after timeout to prevent forgotten debug logging
