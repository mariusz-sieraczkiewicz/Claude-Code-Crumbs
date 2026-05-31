# Architecture

**Principle:** Organise code as vertical slices around business capabilities, with a single composition root and a strict layered dependency direction (domain → application → infrastructure, never reversed).

## Mechanical enforcement

The structural shape of this rule is largely mechanisable. A project SHOULD configure at least the following:

- **Import-graph linter** — forbid imports that violate the layering. Examples:
  - JS/TS: `eslint-plugin-boundaries`, `eslint-plugin-import` `no-restricted-paths`, or `dependency-cruiser`.
  - Python: `import-linter` contracts (`layers`, `forbidden`).
  - Swift: SwiftLint `file_header` + a custom `script_phases` grep gate (see `check-anti-patterns.sh` in stacks that ship one).
  - JVM: ArchUnit rules on package layers.
- **Single composition root** — a grep gate that flags any DI-container, service-locator, or `new`/`init` of an infrastructure class outside the entrypoint module. The composition root is conventionally the application entrypoint (`main.ts`, `Program.cs`, `AppDelegate`/`@main`, `wsgi.py` factory, etc.).
- **Forbidden symbols in domain layer** — domain modules must not import ORM types, HTTP clients, framework annotations, environment lookups, or `process.env` equivalents. Encode as a `no-restricted-imports` / equivalent rule.
- **Slice ownership check** — a script that fails when a file under `features/<slice>/` imports a sibling slice's internals (only the slice's public surface is reachable).

If the toolchain cannot express one of the above, the rule falls back to the subagent check.

## Subagent check

The `reviewer` and `verifier` inspect the diff for things linters miss:

- **Slice cohesion** — does the new code belong to a single vertical slice, or does it leak responsibilities into a sibling slice? A new endpoint that "just needs" to write to two unrelated aggregates is the canonical smell.
- **Composition-root drift** — is wiring being silently inlined into a feature module (e.g. `const repo = new PgRepo(...)` inside a use case)? All wiring belongs at the entrypoint.
- **Layering by intent** — even when no import is technically illegal, a domain object that "knows" it will be persisted by a specific ORM (e.g. fields named to match an ORM's metadata, methods named after database operations) is a layering violation in spirit.
- **Stable abstractions** — application layer depends on domain abstractions (interfaces / protocols / traits), never on infrastructure concretes. Reviewer should challenge any `import` that crosses a slice from application into infrastructure directly.
- **Framework leakage** — framework annotations, decorators, or base classes appearing in domain types. Domain stays plain.

## Examples

### Good

```
src/
  features/
    billing/
      domain/          # entities, value objects, domain services, errors
      application/     # use cases, ports (interfaces)
      infrastructure/  # adapters: db, http, queue
      ui/              # controllers / views / handlers
    onboarding/
      domain/
      application/
      infrastructure/
      ui/
  shared/              # cross-cutting value types only (Money, Email, IDs)
  app/
    main.ts            # composition root: wires concretes into ports
```

```ts
// features/billing/application/cancel-subscription.ts
export interface SubscriptionRepository {
  load(id: SubscriptionId): Promise<Subscription>;
  save(s: Subscription): Promise<void>;
}

export class CancelSubscription {
  constructor(private readonly repo: SubscriptionRepository) {}
  async execute(id: SubscriptionId): Promise<void> {
    const sub = await this.repo.load(id);
    sub.cancel(); // domain decides
    await this.repo.save(sub);
  }
}

// app/main.ts — the ONLY place that knows about Postgres
const repo = new PgSubscriptionRepository(pool);
const cancel = new CancelSubscription(repo);
```

### Bad

```ts
// features/billing/ui/cancel-handler.ts
import { db } from "../../../infrastructure/db"; // UI reaches into infra
import { sendEmail } from "../../onboarding/infrastructure/mail"; // cross-slice infra import

export async function handler(req, res) {
  const row = await db.query("SELECT * FROM subscriptions WHERE id=$1", [req.params.id]);
  row.status = "cancelled";                      // domain logic in UI
  await db.query("UPDATE subscriptions SET status=$1 WHERE id=$2", [row.status, row.id]);
  await sendEmail(row.user_email, "Cancelled");  // cross-cutting wiring inlined
  res.json(row);
}
```

## Anti-patterns

- Service locators or global containers resolved deep inside use cases.
- "Utils" or "common" packages that grow into a parallel hidden domain.
- Cross-slice imports (`features/a/...` reaching into `features/b/...`) instead of routing through a shared contract or the composition root.
- Domain entities annotated with ORM/serialisation decorators.
- Wiring (instantiating adapters, reading env vars) anywhere outside the composition root.
- "God" application services that orchestrate three unrelated slices.
- Feature flags evaluated inside the domain layer.
- Frameworks invoking domain code via base-class inheritance instead of plain function/interface calls.

## Cross-refs

- `data-access.md` — defines the port-per-aggregate shape that the application layer depends on.
- `data-modeling.md` — defines aggregate boundaries, which in turn drive slice boundaries.
- `language-patterns.md` — project-specific idioms for expressing layers (modules, packages, access modifiers).
- `testing.md` — Domain-tests assume a clean domain layer with no infrastructure imports; this rule is the precondition.
- `error-handling.md` — boundary translation between layers; errors cross layers only through defined ports.
