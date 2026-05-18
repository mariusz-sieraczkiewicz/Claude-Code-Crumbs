# Data Access

**Principle:** One protocol (port) per aggregate root; the domain depends on the protocol, never on the ORM, query builder, or HTTP client; adapters live in infrastructure and translate provider errors into typed domain errors at the boundary.

## Mechanical enforcement

- **Import-graph rule** — no domain or application file may import the ORM / query builder / driver. Examples to forbid in `eslint` `no-restricted-imports`, `import-linter`, or equivalent: `prisma`, `typeorm`, `sequelize`, `knex`, `mongoose`, `pg`, `sqlalchemy`, `django.db`, `Room`, `CoreData`, `SwiftData`, `Realm`, `axios`, `fetch` (when used as a transport, not a runtime).
- **Naming convention check** — each aggregate has exactly one `XRepository` (or `XPort`, `XGateway` — pick one name in `code-style.md` and stay consistent). A `find_files`/grep gate fails when two adapters claim the same aggregate.
- **Adapter location** — repository implementations live under `features/<slice>/infrastructure/`. A path-based ESLint / `import-linter` rule fails when an `*Repository` implementation is defined elsewhere.
- **Type check** — the port's signature must use domain types (entities, value objects, IDs) as parameters and return types. A `tsc`/`mypy`/compiler error is the desired outcome of any DTO leakage.
- **In-memory adapter** — the test suite ships an `InMemoryXRepository` for every port; CI can grep for "for each port, there is a fake" to enforce.

## Subagent check

Reviewer / verifier look for:

- **Leaky abstractions in the port signature** — methods named after SQL/ORM operations (`findManyWhere`, `executeQuery`, `batchInsert`) rather than after use cases (`findActiveSubscriptions`, `assignOwner`).
- **Predicate logic in callers** — application services or domain methods constructing query predicates, filter trees, or pagination cursors. That logic belongs inside the adapter; the port exposes use-case methods.
- **DTO bleed** — the adapter returning raw ORM rows or DTOs that the application layer must then map. Adapter returns domain types.
- **Per-field reads/writes** — the port offering `getName`, `setName`, `getEmail`, `setEmail`. The port loads and saves the whole aggregate; granular mutators are a sign of an anaemic model.
- **Provider errors crossing the boundary** — an ORM exception, `psycopg.OperationalError`, `URLError`, `PostgrestError`, etc. propagating into the application layer. Adapters catch, log raw, and translate to domain errors (see `error-handling.md`).
- **Hidden I/O** — lazy-loading proxies, ORM session leaks across requests, queries triggered by `toString()`. The application layer must never trigger network or disk I/O outside an explicit port call.
- **Cross-aggregate joins inside one repository** — a `SubscriptionRepository` method that also reads `Invoice` and `Customer` rows and returns a denormalised blob. That is a read model / projection, and belongs to its own port.

## Examples

### Good

```ts
// features/billing/application/ports/subscription-repository.ts (domain-owned port)
export interface SubscriptionRepository {
  load(id: SubscriptionId): Promise<Subscription | null>;
  findActiveFor(customerId: CustomerId): Promise<Subscription[]>;
  save(s: Subscription): Promise<void>;
}

// features/billing/infrastructure/pg-subscription-repository.ts (adapter)
export class PgSubscriptionRepository implements SubscriptionRepository {
  constructor(private readonly pool: Pool, private readonly log: Logger) {}

  async load(id: SubscriptionId): Promise<Subscription | null> {
    try {
      const row = await this.pool.query("SELECT ... WHERE id = $1", [id.value]);
      return row.rows[0] ? Subscription.fromRow(row.rows[0]) : null;
    } catch (e) {
      this.log.error({ err: e }, "subscription load failed");
      throw new PersistenceError("subscription.load", { cause: e });
    }
  }

  async save(s: Subscription): Promise<void> { /* whole-aggregate upsert */ }
}
```

```python
# Python equivalent: port lives next to the use case.
class SubscriptionRepository(Protocol):
    def load(self, id: SubscriptionId) -> Subscription | None: ...
    def save(self, s: Subscription) -> None: ...
```

### Bad

```ts
// Application service builds the query — adapter is a thin pass-through.
class CancelSubscription {
  constructor(private readonly orm: PrismaClient) {}  // ORM in the application layer

  async execute(id: string) {
    const row = await this.orm.subscription.findFirst({
      where: { id, status: { not: "cancelled" } },     // predicate logic outside the adapter
      include: { customer: true, invoices: true },     // cross-aggregate join
    });
    if (!row) throw new Error("not found");            // untyped error
    await this.orm.subscription.update({               // per-field write
      where: { id },
      data: { status: "cancelled", cancelledAt: new Date() },
    });
  }
}
```

## Anti-patterns

- Importing ORM types (`Prisma.Subscription`, `Session`, `QuerySet`, `ModelContext`) from the domain or application layer.
- Repositories returning ORM rows, raw `dict`/`Record` shapes, or framework DTOs instead of domain types.
- "Generic" `Repository<T>` with `findAll`, `findById`, `save`, `delete` shared across all aggregates — encourages anaemic domain and predicate leakage.
- The application layer constructing predicates, filter trees, projections, or pagination cursors.
- Throwing provider exceptions (`PostgrestError`, `OperationalError`, `URLError`) into application code.
- Lazy-loading proxies that trigger queries when the domain object is merely read.
- Multiple adapters for the same aggregate within a single deploy (pick one; if you need two, name the boundary explicitly — e.g. read vs write).
- No in-memory adapter — tests are forced to spin up real infrastructure for unit-level scenarios.
- Caching inside the domain. Caching is an infrastructure concern; if needed, layer a caching adapter that implements the same port.

## Cross-refs

- `architecture.md` — defines the layer the port and adapter belong to.
- `data-modeling.md` — defines the aggregate boundary that the port wraps.
- `error-handling.md` — defines how provider errors are translated at the adapter boundary.
- `testing.md` — Domain-tests rely on in-memory adapters defined alongside each port.
- `observability.md` — adapters are the place where raw provider errors are logged with full context.
