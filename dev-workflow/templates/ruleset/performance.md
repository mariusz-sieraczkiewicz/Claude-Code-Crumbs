# Performance

**Principle:** Define explicit latency budgets and throughput targets per critical path; profile before optimising; never tune on a hunch.

Performance is a feature with a number attached to it. Every user-facing operation has a budget (p95 latency, throughput, memory ceiling). Code that ships without a budget is code whose performance is undefined — and undefined performance regresses silently.

## Budgets

Every critical path declares a budget in the epic plan or the code itself (comment or constant). Examples of categories:

- **Interactive API request** — p95 ≤ 300 ms, p99 ≤ 800 ms
- **Background job per item** — p95 ≤ 2 s
- **Page-load critical render** — LCP ≤ 2.5 s, TTI ≤ 3.5 s
- **Batch / cron run** — wall-clock ceiling defined per epic
- **Memory** — per-request RSS ceiling, per-process heap ceiling

If your project has no measured baseline yet, start by recording the current numbers and treat them as the floor — regressions need justification, improvements need a new floor.

## Mechanical enforcement

- **Bundle / asset size budgets** — e.g. `webpack-bundle-analyzer`, `bundlesize`, `size-limit`. Fail CI when a bundle exceeds the declared ceiling.
- **Lighthouse CI** — assert against performance budgets on PR.
- **Load tests in CI** — e.g. `k6`, `locust`, `vegeta`. A smoke run with assertions on p95 / error rate gates merges to main.
- **Linters for obvious traps** — e.g. `eslint-plugin-react-hooks` (unnecessary re-renders), `ruff`/`pylint` rules against quadratic patterns, `golangci-lint` (`prealloc`, `gocritic`), `clippy` (`needless_collect`, `inefficient_to_string`).
- **N+1 query detection** — e.g. ORM-specific plugins (Bullet for ActiveRecord, `nplusone` for SQLAlchemy), or query-count assertions in infra-layer tests (called "integration tests" by tools like Vitest/Pytest — distinct from plugin Domain-tests).
- **Static complexity caps** — cyclomatic complexity / function length limits in the linter (a proxy for hot-path readability under profiling).
- **Profiler artefacts** — when an epic touches a hot path, the implementer attaches a profile (e.g. `pprof`, `py-spy`, Chrome DevTools flamegraph) to the run history.

## Subagent check

The `verifier` and `reviewer` look for things tools cannot infer:

- **Is a budget stated?** If the change touches a critical path and no p95/throughput/memory number is referenced, ask for one.
- **Was it measured, not guessed?** Optimisations without a before/after measurement are suspect; "this should be faster" is not evidence.
- **Hot path vs cold path** — micro-optimising a once-a-day admin job is waste; failing to measure a per-request loop is negligence. The reviewer flags inverted effort.
- **Algorithmic vs constant-factor** — an O(n²) loop hidden in a helper does not become acceptable because the constant is small; flag the asymptote when `n` is unbounded by input validation.
- **Lazy vs eager** — was data fetched in bulk where a stream would suffice (memory blow-up), or one-by-one where a batch would (latency)?
- **Caching correctness** — every cache introduces an invalidation problem; the reviewer asks "what writes invalidate this, and is that wired up?" before accepting a cache as a fix.
- **Realistic load shape** — was the benchmark run with realistic data volume, concurrency, and payload size? A microbenchmark on `n=10` is theatre.

## Examples

### Good

```
# Critical path: list endpoint /v1/items
# Budget: p95 ≤ 300ms, p99 ≤ 800ms (measured on staging, 2026-04, baseline p95=180ms)
# Load: 50 RPS sustained, 200 RPS peak

def list_items(user_id: UUID, page: PageRequest) -> Page[Item]:
    # Single query with pagination; index on (user_id, created_at desc) — see migration 0034.
    return repo.list_items(user_id, page)
```

```
# CI step (excerpt)
- name: k6 smoke
  run: k6 run --vus 20 --duration 60s tests/load/list_items.js
  # script asserts: http_req_duration{p(95)} < 300, http_req_failed < 0.01
```

### Bad

```
# No budget, no measurement, sequential I/O inside a loop, no pagination.
def list_items(user_id):
    items = db.query("SELECT id FROM items WHERE user_id = ?", user_id)
    result = []
    for item_id in items:                       # N round-trips to DB
        item = db.query("SELECT * FROM items WHERE id = ?", item_id)
        item.tags = db.query("SELECT * FROM tags WHERE item_id = ?", item_id)  # N more
        result.append(item)
    return result                                # unbounded — could be 100k rows
```

## Anti-patterns

- **No declared budget.** "It feels fast on my machine" is not a budget.
- **Optimising without profiling.** Rewriting a function before measuring where the time goes.
- **N+1 queries.** Loops issuing one query per element instead of a single batched query or join.
- **Unbounded result sets.** Endpoints / queries with no `LIMIT`, no pagination, no max-size guard.
- **Sequential I/O that could be concurrent.** Awaiting calls one-at-a-time when they are independent.
- **Cache-as-bandaid.** Adding a cache to mask an algorithmic problem; the real fix is the algorithm or the query plan.
- **Premature micro-optimisation.** Choosing a less readable construct on a cold path "for speed" with no measurement.
- **Benchmarks on toy data.** Asserting performance with `n=10` rows when production has `n=10^6`.
- **Silent regressions.** No CI gate, no dashboard — regressions ship and are noticed weeks later by users.

## Cross-refs

- `monitoring.md` — the SLOs that the budgets in this file feed; latency alerts fire when budgets are breached in production.
- `observability.md` — without traces / structured metrics you cannot tell where a budget was spent.
- `data-access.md` — N+1 patterns and query bounds live here; performance enforces the consequences.
- `architecture.md` — caching tiers, async boundaries, and concurrency model are architecture decisions; performance verifies the choice survives load.
- `testing.md` — load tests and benchmarks are tests; same discipline (deterministic, reproducible) applies.
