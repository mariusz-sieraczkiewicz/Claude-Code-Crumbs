# Observability

**Principle:** Emit structured logs, metrics, and traces with stable IDs so any production question can be answered from the data alone — and never log PII or secrets.

Observability is the **data plane**: the signals a running system emits. It is what makes the system explainable after the fact. Monitoring (the operations plane — alerts, dashboards, on-call) is built **on top of** observability and lives in `monitoring.md`. If observability is missing, monitoring is blind.

## The three signals

- **Logs** — discrete, structured events ("what happened, with what fields"). Searchable, high-cardinality safe within reason.
- **Metrics** — numeric time series ("how much, how often"). Low-cardinality labels, cheap aggregation.
- **Traces** — causal spans across services / async boundaries ("where did the time go, who called whom"). Carry a `trace_id` end-to-end.

Pick the right tool: do not store counts in logs you have to grep, do not store individual request payloads in metrics. Logs are for events, metrics for trends, traces for causality.

## Logs — structured, not prose

- **Structured fields**, not interpolated sentences. Each event has a stable `event` name and typed fields. JSON is the lingua franca; the renderer is the consumer's choice.
- **Levels** used consistently:
  - `error` — failure requiring action (downstream down, persistence failed, invariant violated)
  - `warning` — degraded state (retry, fallback, near-limit, expired token)
  - `info` / `notice` — business events (request handled, job completed, entity created)
  - `debug` — development detail (intermediate values, query plans); off in production
- **One event name per call site.** `event=order.created` not `"order was created OK"`. Stable names are searchable; sentences are not.
- **Correlation IDs on every record.** Minimum: `trace_id`, `request_id`. If the operation has a user actor, `user_id` as an opaque ID (UUID, hash) — never email.

## Metrics — low cardinality, named for the question

- Names follow a consistent convention (e.g. `http_requests_total`, `job_duration_seconds`, `cache_hit_ratio`).
- Labels are bounded: `route`, `status_class`, `region` — never `user_id`, `email`, raw URLs with parameters, or anything else high-cardinality. Cardinality explosions break the backend.
- Histograms for latency (so you can derive p50/p95/p99 later), counters for events, gauges for levels.
- RED for services (Rate / Errors / Duration), USE for resources (Utilisation / Saturation / Errors).

## Traces — propagate `trace_id` end-to-end

- A request entering at the boundary gets a `trace_id` (W3C `traceparent` if you have a choice). It is propagated to every downstream call (HTTP header, message attribute, job context).
- Span names describe the operation, not the user (`db.query items.list`, not `loading Mariusz's items`).
- Every span carries the same `trace_id`; logs emitted inside the span include it so a single ID joins all three signals.

## PII and secrets — never

The list below is non-exhaustive; the rule is *if in doubt, do not log it*:

- **Secrets** — API keys, tokens (access/refresh/JWT), passwords, session cookies, signing keys. Never, at any level, in any signal.
- **PII** — full email addresses, phone numbers, full names, addresses, government IDs, payment data, IP addresses where regulated.
- **User content** — message bodies, document contents, search queries containing user input, voice transcripts in production.
- **URL query strings** that may contain tokens or PII (`?token=…`, `?email=…`). Log the path, drop or redact the query.
- **Request / response bodies** by default. If a body is essential for debugging, redact or hash sensitive fields; consider `debug`-only with sampling.

Use opaque identifiers instead: `user_id=<uuid>` or `user_id=<short-hash>` for correlation without revealing identity.

## Mechanical enforcement

- **Forbid `print`/`console.log` in production code** — e.g. `eslint-plugin-no-console`, `ruff` (`T201`), Go `forbidigo`, custom linter rule. Use the project logger.
- **Schema for log events** — optional but powerful: a registry / typed wrapper that rejects unknown fields, enforces required fields (`trace_id`, `event`, `level`).
- **Secret scanners** — `gitleaks`, `trufflehog` on commits and in CI to catch secrets that slipped into log strings or fixtures.
- **PII detectors / redaction middleware** — pre-emission redaction of known field names (`email`, `password`, `token`, `authorization`) at the logger / HTTP-log layer.
- **Trace propagation tests** — infra-layer tests (called "integration tests" by tools like Vitest/Pytest — distinct from plugin Domain-tests) that assert a `trace_id` arrives at the downstream service unchanged.
- **Cardinality budgets** — alert (or fail CI) when a metric label set exceeds a declared cardinality ceiling. Most metrics backends offer this.
- **OpenTelemetry / equivalent SDK** in use across services for a single propagation contract.

## Subagent check

What `reviewer` and `verifier` look for that mechanical tools miss:

- **Is the event name stable and meaningful?** Could you grep it next year? `event="ok"` is useless; `event="payment.captured"` is reusable.
- **Are correlation IDs threaded through?** Async boundaries (queues, background jobs, retries) commonly drop `trace_id`. Reviewer follows the request from boundary to persistence and back.
- **Right signal for the question.** A metric question ("how often does X happen?") answered by grepping logs is a smell.
- **Cardinality.** A label that takes one of millions of values (user id, full URL, request id) on a Prometheus-style metric is a production incident waiting to happen.
- **PII leakage in error messages.** Exceptions that include the bad input (`DecodingError` with the offending substring, ORM errors echoing SQL parameters) — must be redacted before logging.
- **Sampling that hides errors.** Trace sampling that drops error spans defeats the purpose; errors should be sampled at 100%.
- **Log levels chosen by reflex.** "Everything is error" or "everything is info" — both are useless. The reviewer asks: would this event wake someone up? then is it `error`. Otherwise it is not.

## Examples

### Good

```
logger.info(
    event="order.created",
    order_id=order.id,
    user_id=user.id,                     # opaque UUID
    amount_cents=order.amount_cents,
    currency=order.currency,
    trace_id=ctx.trace_id,
    request_id=ctx.request_id,
)
```

```
# Metric — bounded labels
http_requests_total{route="/v1/orders", method="POST", status_class="2xx"} 1
order_amount_cents_histogram{currency="EUR"} 1299
```

```
# Trace propagation across an HTTP boundary
GET /v1/items
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

### Bad

```
# Prose log, no fields, leaks PII, no correlation
logger.info(f"user {user.email} placed order for {order.items} totaling ${total}")

# Metric with unbounded label — cardinality bomb
http_requests_total{route="/v1/orders", user_id="9b1e…", url="/v1/orders?token=abc"} 1

# Secret in URL, logged verbatim
logger.info(f"calling {url}")   # url = "https://api.example.com/x?api_key=sk-live-…"
```

## Anti-patterns

- **`print` / `console.log` in production code.** Bypasses level, redaction, structure, and shipping.
- **String-interpolated log messages.** Unsearchable, fragile under refactor, easy to leak fields.
- **Secrets or PII anywhere in logs / metrics / traces / URLs.** Including in error messages.
- **High-cardinality labels on metrics.** Per-user, per-request, per-URL labels.
- **Errors logged without context.** `logger.error("failed")` with no ID, no trace, no fields.
- **Dropped `trace_id` at async boundaries.** Queue handlers, retries, scheduled jobs that re-enter without propagation.
- **Trace-sampling that drops errors.** Sample successful traffic; never error traffic.
- **Logs used as metrics.** Counting events by grepping logs in a dashboard instead of emitting a counter.
- **Debug logs left on in production.** Volume cost and information leak.

## Cross-refs

- `monitoring.md` — consumes these signals to fire alerts and feed SLOs. Observability is the data, monitoring is the watch.
- `security.md` — defines the PII/secret rules this file enforces in the emission layer.
- `error-handling.md` — error shape and propagation; this file says how errors are *logged*, that file says how they are *raised and handled*.
- `performance.md` — traces and latency histograms are how you verify budgets; without them, "fast" is unfalsifiable.
- `data-access.md` — query timing and N+1 surface in traces; instrument the data layer.
