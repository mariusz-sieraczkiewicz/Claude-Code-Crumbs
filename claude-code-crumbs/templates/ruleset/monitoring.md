# Monitoring

**Principle:** Define SLOs in user terms, alert only on things a human must act on, and route every alert to a named owner with a runbook.

Monitoring is the **operations plane**: the active watch over a running system. It consumes the signals produced by observability (`observability.md`) and turns them into alerts, dashboards, SLOs, and on-call rotations. If observability is the camera, monitoring is the security guard.

Two failures dominate practice:
1. **Alert noise** — pagers that fire on non-actionable conditions; on-call burnout; real signals lost in the noise.
2. **Blind spots** — critical user journeys with no SLO and no alert; outages discovered via support tickets.

This file aims at both.

## SLOs — service level objectives

- Defined in **user-visible terms**, not implementation terms: "checkout completes successfully within 2 seconds, 99.9% of the time over 30 days", not "the order service has 99.9% CPU availability".
- Three components per SLO:
  - **SLI** (indicator) — what is measured (e.g. ratio of successful requests under 2 s).
  - **Target** — the number (e.g. 99.9% over 30 days).
  - **Window** — rolling period (typically 7, 28, or 30 days).
- **Error budget** — the inverse (1 − SLO). Track burn rate; when burn is fast, slow change and prioritise reliability.
- One SLO per critical user journey. Not one per microservice. The user does not care about your microservices.

## Alerts — page only on action

An alert must satisfy three tests:

1. **Actionable** — there is something a human can do *now*. If the answer is "wait and see", it is not an alert.
2. **User-impacting** — it correlates with a real user-visible effect (or an imminent one).
3. **Owned** — it routes to a named team / on-call who knows the system.

Alert types:

- **Page** (wakes someone up) — user-impacting outages, SLO fast-burn (e.g. 2% of monthly budget in 1 hour), data-loss risk, security incidents.
- **Ticket** (next business day) — slow-burn SLO erosion, capacity trends, certificate expiry within N days, known-flaky job that needs investigation.
- **Notification only** (Slack/email, no action) — informational; should be rare. If nobody reads it, delete it.

Alert hygiene:

- Every page-level alert has a **runbook link** in the alert payload: "what is this, first three diagnostic steps, who owns it, escalation path".
- **No naked thresholds** without rationale (`CPU > 80%` is not an alert; "checkout p95 > 2s for 5 min" is).
- **Multi-window, multi-burn-rate** for SLO alerts (e.g. fast: 2% in 1h; slow: 10% in 6h) — avoids both flapping and slow-burn blindness.
- **Maintenance / silence windows** are explicit and time-bounded; never silence indefinitely.

## Dashboards — one per audience

- **Service health** (per service): RED metrics (Rate / Errors / Duration), saturation, error budget remaining.
- **User journey** (per critical flow): end-to-end success rate, latency, drop-off.
- **Incident dashboard**: pre-built views referenced from runbooks — the on-call should not be building queries during an outage.

Dashboard hygiene:

- Each panel answers a stated question (named in the title or description).
- Time range and refresh defaults make sense for the audience.
- Dashboards are version-controlled (dashboards-as-code where the platform allows: e.g. Terraform, Grafana JSON in git).

## On-call

- A named rotation, documented schedule, documented handoff.
- Every page-level alert has a **primary owner** in the alerting config.
- **Post-incident review** for every page-level incident: blameless, written, with action items tracked. Repeated incidents without action items are a process failure.
- On-call load is monitored: if pages-per-shift exceeds the agreed threshold, the team stops feature work and fixes the alerts.

## Mechanical enforcement

The verifier subagent enforces this rule via the **`gates.monitoring`** entry in `.claude/stack.yaml`. Bind your alert-config linter, monitoring-as-code validator, and runbook-link CI check to that gate (e.g. `promtool check rules ...`, `amtool check-config ...`, plus a project script that asserts every page-level alert carries a non-empty `runbook` annotation). Zero tolerance: any non-zero exit blocks DoD. Leaving `gates.monitoring: null` is a deliberate, recorded opt-out — not a default.

- **Monitoring-as-code** — alerts, SLOs, and dashboards defined in code (e.g. Prometheus rules in YAML, Datadog Terraform provider, Grafana JSON). Pull requests reviewed.
- **Synthetic checks** — black-box probes against critical endpoints / journeys (e.g. uptime checks, k6 synthetic, Pingdom-style). Independent of the system they monitor.
- **Certificate expiry monitors** — TLS, signing keys, secrets nearing rotation.
- **Linting / validation** for alert config — e.g. `promtool check rules`, `amtool` for Alertmanager, provider-specific linters. Wire these into `gates.monitoring`.
- **Runbook link required field** — a CI check that every page-level alert has a non-empty runbook URL. Wire into `gates.monitoring`.
- **SLO burn-rate alerts** generated from the SLO definition rather than hand-written thresholds.

## Subagent check

What `reviewer` and `verifier` look for that tools cannot:

- **Is the SLO in user terms?** A reviewer rejects "service is up" SLOs in favour of "user can complete X".
- **Is the alert actionable?** Ask: "If this fires at 3am, what do I do?" If the answer is "nothing useful", the alert is wrong.
- **Runbook quality.** Does the linked runbook actually help? Or is it "TODO" / a stub? Empty runbooks are worse than no runbook (they signal false safety).
- **Coverage of critical journeys.** Is there an SLO and alert for every flow the PRD calls critical? Common blind spots: auth, webhook delivery, payment, async jobs, scheduled tasks.
- **Threshold provenance.** Where does "5 minutes" or "2%" come from? Is it tied to a budget or a guess?
- **Ownership.** Does the alert route somewhere a human reads? `#alerts-archive` does not count.
- **Noise budget.** Has this alert fired recently without action? If yes and repeatedly — fix or delete.
- **Silenced forever.** A long-silenced alert is a deleted alert in disguise; either restore intent or remove it.

## Examples

### Good

```
# SLO: checkout completes within 2s, 99.9% over 30d
- alert: CheckoutSLOFastBurn
  expr: |
    (
      sum(rate(checkout_requests_total{status="error"}[5m]))
      / sum(rate(checkout_requests_total[5m]))
    ) > 14.4 * (1 - 0.999)        # 2% of budget in 1h
  for: 2m
  labels:
    severity: page
    team: payments
  annotations:
    summary: "Checkout error rate burning SLO fast"
    runbook: "https://runbooks.example.com/checkout-slo-burn"
    dashboard: "https://grafana.example.com/d/checkout"
```

### Bad

```
# Naked threshold, not tied to user impact, no runbook, no owner
- alert: HighCPU
  expr: cpu_usage > 80
  for: 1m
  annotations:
    summary: "CPU is high"
```

## Anti-patterns

- **Alerting on causes, not symptoms.** "CPU high" wakes you up even when users are fine; "checkout failing" wakes you up when they are not.
- **No SLOs, only thresholds.** Thresholds drift; SLOs anchor to user experience and an error budget.
- **Alerts without runbooks.** Whoever wrote the alert knew what to do; the on-call at 3am does not.
- **Alert flapping.** Conditions that toggle every few minutes — fix the threshold, the smoothing, or the alert.
- **Unowned alerts.** Routed to a channel nobody watches.
- **Dashboards with no question.** Panels added "because we had the data"; nobody knows what to do with the curve.
- **Silenced for "the foreseeable future".** Either fix it or delete it.
- **Monitoring the monitor only.** Synthetic checks against `/healthz` that return 200 while the actual user journey is broken.
- **No post-incident review.** Recurring incidents indicate the alert worked but the system did not learn.

## Cross-refs

- `observability.md` — the source of the signals this file watches. No structured logs/metrics/traces ⇒ no useful monitoring.
- `performance.md` — defines the latency / throughput budgets that become SLO targets here.
- `security.md` — security events (auth failures, secret rotation, suspicious access) are first-class alert categories; route to security on-call.
- `deployment.md` — release gates and rollback triggers are tied to monitoring signals.
- `error-handling.md` — error classification feeds alert severity; not every exception is a page.
