# Security

**Principle:** Secrets live in a vault, authentication and input validation happen at trust boundaries, PII never enters logs or URLs, and every dependency is scanned.

Security is not a feature you add at the end; it is a property of where you put the boundaries and what you let cross them. This ruleset is OWASP-aware (Top 10 / ASVS) but does not lock the project to any specific framework — concrete tools are examples, not mandates.

## Secrets

- **Vault, not files.** Secrets (API keys, tokens, signing keys, DB credentials, service-account JSON) live in a secret store: cloud KMS / secret manager (e.g. AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault, Doppler, 1Password CLI for local dev). Never in git, never in env files committed to the repo, never in CI logs.
- **Environment variables at runtime** are an acceptable injection mechanism *from* the vault; they are not themselves storage.
- **`.env.example`** documents required keys with placeholder values. Real `.env` is gitignored.
- **Rotation** — every secret has a documented rotation cadence and a documented rotation procedure. A secret that cannot be rotated is a liability.
- **Least privilege** — each service / human has only the secrets it needs. No shared "god" credentials.
- **Detection in CI** — `gitleaks` / `trufflehog` on every push and pull request; CI fails on a hit.

## Authentication and authorisation — at boundaries

- **Authenticate at the trust boundary** (HTTP edge, API gateway, message ingress) — not deep inside the domain. The domain layer receives an already-authenticated principal.
- **Authorize on every access**, not only at login. Resource-level checks (`can this principal read this resource?`) live next to the resource access, not in a UI guard.
- **Sessions** — use established libraries; never roll your own. Short-lived access tokens + refresh; rotate on use where appropriate.
- **Passwords** — only via vetted hashing (e.g. argon2id, bcrypt with sufficient cost). Never plain, never MD5/SHA1, never reversible.
- **MFA / step-up** for sensitive actions where the threat model warrants.

## Input validation — at boundaries, fail closed

- Validate **at the boundary**, parse into typed domain objects, then trust the type. Do not validate ad-hoc deep in the call stack.
- **Allow-list, not deny-list** — define what is valid; reject everything else.
- **Bounded sizes** for every string, list, file upload. Unbounded inputs are DoS vectors.
- **Output encoding contextual to the sink** — HTML-escape for HTML, parameterise for SQL, escape shell metacharacters for shell, etc. Never concatenate user input into a query / command / template.
- **Deserialisation** — never of untrusted data into rich object graphs (pickle, Java serial, YAML `load`). Use safe loaders.

## PII — minimise, isolate, never leak

- **Minimise collection** — if you don't need it, do not store it.
- **Never in logs.** See `observability.md` for the full list. Log opaque IDs, not emails / names / content.
- **Never in URLs / query strings.** URLs end up in browser history, proxy logs, referrer headers, third-party analytics. Use POST bodies and short-lived signed tokens.
- **Never in error messages** returned to users beyond their own data.
- **Encrypted at rest** for any PII column / bucket the threat model requires; encrypted in transit always (TLS).
- **Right to erasure** — deletion paths exist and are tested where regulation requires (e.g. GDPR / CCPA).

## Dependencies and supply chain

- **Pin and lock** — lockfiles committed (`package-lock.json`, `poetry.lock`, `Cargo.lock`, etc.).
- **Vulnerability scanning** — e.g. `npm audit`, `pip-audit`, `cargo audit`, `osv-scanner`, `trivy`, GitHub Dependabot / Renovate. CI fails on known-high issues.
- **Container scanning** — e.g. `trivy`, `grype` on every image build.
- **SAST** — e.g. `semgrep`, `bandit`, `gosec`, language-native security linters, in CI.
- **License compliance** — scanned where the project requires.
- **Reproducible builds** where feasible; signed releases where the threat model warrants.

## Transport and headers

- TLS everywhere — HTTPS only, HSTS where applicable.
- Modern cipher suites; old protocols (SSLv3, TLS 1.0/1.1) disabled.
- Security headers for web responses: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Strict-Transport-Security`, `Permissions-Policy`, frame-ancestor controls.
- CORS allow-list explicit, not `*`, when credentials are involved.

## Mechanical enforcement

- **Secret scanning** — `gitleaks`, `trufflehog` in pre-commit and CI.
- **SAST** — `semgrep` (custom rules + community packs), language-specific scanners (`bandit`, `gosec`, `brakeman`, `eslint-plugin-security`).
- **Dependency / container scanners** — `trivy`, `osv-scanner`, `grype`, `npm audit`, `pip-audit`, `cargo audit`.
- **License scanners** — e.g. `license-checker`, `pip-licenses`, when applicable.
- **Lint rules forbidding dangerous APIs** — `eval`, `pickle.load` on untrusted input, `subprocess` with `shell=True`, raw string SQL, `dangerouslySetInnerHTML` without sanitiser.
- **PII / secret redaction middleware** at the logger.
- **HTTPS / security-header check** in synthetic monitoring (e.g. `testssl.sh`, Mozilla Observatory style checks in CI).
- **Auth tests** that assert every protected endpoint rejects unauthenticated and cross-tenant access.

## Subagent check

What `reviewer` and `verifier` look for beyond tooling:

- **Where is the trust boundary?** Identify it in the change. If authn/validation happens *after* domain logic, that is wrong.
- **Authorization at the resource.** A `GET /thing/:id` that returns the thing without checking the caller may read it — even with a valid session — is broken. Reviewer reads the access path.
- **Cross-tenant leakage.** Multi-tenant systems: every query carries the tenant filter; the reviewer looks for queries that don't.
- **Secret in code / config / fixture.** Even "test" secrets should be obviously fake; real-looking strings in repos get scraped.
- **PII in new log lines, URL parameters, error messages.** Read every new `logger.*` and `raise/throw` for content.
- **Unsanitised user input flowing to a sink** — SQL, shell, HTML, file path, redirect URL, deserialiser. Trace the flow.
- **Open redirect / SSRF surface** — endpoints that take a URL parameter and fetch / redirect to it must validate against an allow-list.
- **Token handling.** Tokens in localStorage when a cookie with `HttpOnly`/`Secure`/`SameSite` would be safer; tokens logged; tokens in URLs.
- **Dependency added without review.** Every new dependency is a supply-chain surface; the reviewer asks "do we need it, and is it maintained?".
- **Default-deny on new endpoints.** New routes start protected unless there is an explicit reason; not the other way round.

## Examples

### Good

```
# Auth at boundary, authorization at resource, parameterised query, opaque log id
@router.get("/v1/items/{item_id}")
def get_item(item_id: UUID, principal: Principal = Depends(authenticate)):
    item = repo.get_item(item_id, owner_id=principal.user_id)   # tenant-scoped
    if item is None:
        raise NotFound()
    logger.info(event="item.read", item_id=item_id, user_id=principal.user_id)
    return item
```

```
# Secret loaded from vault-backed env, never logged
api_key = os.environ["PAYMENTS_API_KEY"]   # injected from secret manager
client = PaymentsClient(api_key=api_key)
logger.info(event="payments.client.ready")  # no key in the log
```

### Bad

```
# Hard-coded secret, no authn check, string-built SQL, PII in URL and log
API_KEY = "sk-live-9f3a…"                                            # secret in code
@app.get("/items")
def get_item(req):
    item_id = req.args["id"]
    rows = db.execute(f"SELECT * FROM items WHERE id = '{item_id}'") # SQL injection
    logger.info(f"user {req.args['email']} read item {item_id}")      # PII in log
    return rows
# Called as GET /items?id=1&email=alice@example.com&token=abc        # PII + token in URL
```

## Anti-patterns

- **Secrets in git** (including history) or in committed `.env` files.
- **Authentication only at the UI.** Backend endpoints reachable without a valid principal.
- **Authorization only at login.** No per-resource checks; horizontal privilege escalation by changing an ID.
- **String-built SQL / shell / HTML.** Use parameterisation / safe templates.
- **`shell=True`, `eval`, unsafe deserialisers** on data that crosses a trust boundary.
- **PII / secrets / tokens in URLs, logs, error messages, analytics events.**
- **Catch-all CORS** (`*` with credentials), catch-all redirects (open redirect), unrestricted file upload paths.
- **"Temporary" disabled TLS** in non-local environments.
- **Dependencies pinned by hope** — no lockfile, no scanner, no review on bump.
- **Rolling your own crypto / auth / session.** Use vetted libraries.
- **Default-allow new endpoints.** Protection should be opt-out by exception, not opt-in.

## Cross-refs

- `observability.md` — owns the PII / secret rules at the emission layer; security defines them as policy.
- `monitoring.md` — security events (auth failures, secret rotation, anomalous access) are alert categories; route to security on-call.
- `api-design.md` — boundary contracts; authn / validation hooks live where API boundaries are defined.
- `data-access.md` — parameterised queries, tenant scoping, encryption-at-rest belong here in implementation; security defines the policy.
- `error-handling.md` — error responses must not leak internals (stack traces, SQL, paths) to untrusted callers.
- `deployment.md` — secret injection, image signing, environment hardening at deploy time.
