# Data Modeling

**Principle:** Aggregates own their consistency boundary; cross-aggregate references are by ID only; schema evolves through forward-only, reviewable migrations.

## Mechanical enforcement

Parts of this rule are mechanisable; the conceptual core (aggregate boundaries) is not.

- **Migration tooling** — the project MUST use a migration tool that produces ordered, append-only, reviewable files. Examples: Flyway, Liquibase, `prisma migrate`, `alembic`, `sqlx migrate`, Rails migrations, `goose`, `dbmate`, `golang-migrate`. Down-migrations are allowed as a courtesy for local development but MUST NOT be relied on in production rollback.
- **Migration linter / CI gate** — a CI job that:
  - rejects edits to already-applied migration files (`git diff` against the last release tag on the migrations directory must be additive only),
  - rejects destructive statements (`DROP COLUMN`, `DROP TABLE`, `ALTER COLUMN ... TYPE`) without an accompanying ADR reference in the migration header,
  - rejects `NOT NULL` additions without a default or backfill step.
- **Schema dump in VCS** — the canonical schema (`schema.sql`, `schema.rb`, Prisma client output, etc.) is committed and reviewed; drift between dump and migrations fails CI.
- **FK type rule** — a static check (custom linter or schema-test) that any foreign-key column is typed as the referenced aggregate's ID type, never as an inlined object/struct. JS/TS projects can use `eslint-plugin-import` `no-restricted-syntax`; Python projects can write a `pytest` schema test against SQLAlchemy / Pydantic metadata.

## Subagent check

Reviewer / verifier look for:

- **Aggregate boundary integrity** — is the new write transaction modifying state that crosses what was previously a single-aggregate boundary? If so, is the new boundary justified, or should the cross-aggregate effect be a domain event / outbox / saga?
- **ID references vs object references** — does the model embed a full related entity where an ID would suffice? Embedding suggests two aggregates were merged into one accidentally.
- **Invariants in the right place** — invariants ("a subscription cannot be cancelled twice", "an order's total equals the sum of its lines") MUST live in the aggregate, not in the database (CHECK constraints are a belt-and-braces safety net, not the source of truth).
- **Forward-only discipline** — any deletion / rename / type change is preceded by an additive migration, a code release that writes to both shapes, and only later the removal. Reviewer rejects "rename column" in a single migration when the column is in use.
- **Migration reversibility note** — if a migration is logically destructive, the PR must reference an ADR or carry an inline rationale block.

## Examples

### Good

```sql
-- 2026_05_18_120000_add_subscription_status.sql
ALTER TABLE subscriptions
  ADD COLUMN status text;                              -- additive, nullable
UPDATE subscriptions SET status = 'active' WHERE status IS NULL;  -- backfill
-- A later migration, after a deploy that writes the column, sets NOT NULL.
```

```ts
// Subscription aggregate; Customer is referenced by ID only.
class Subscription {
  constructor(
    readonly id: SubscriptionId,
    readonly customerId: CustomerId,   // ID, not Customer
    private status: Status,
    private readonly lines: ReadonlyArray<Line>,
  ) {}

  cancel(now: Instant): void {
    if (this.status === "cancelled") throw new AlreadyCancelled(this.id);
    this.status = "cancelled";
  }
}
```

### Bad

```ts
// Embeds Customer inside Subscription — two aggregates collapsed by accident.
class Subscription {
  customer!: Customer; // entire Customer graph hangs off Subscription
  // Now "rename customer.email" suddenly invalidates Subscription invariants.
}
```

```sql
-- 2026_05_18_120000_rename_status.sql   <-- destructive, single-step
ALTER TABLE subscriptions RENAME COLUMN status TO state;  -- breaks the live deployment
```

## Anti-patterns

- One transaction that modifies more than one aggregate without an explicit reason (saga, outbox, well-justified consistency island).
- Foreign keys typed as something other than the referenced aggregate's ID type (e.g. a JSON blob carrying duplicated fields).
- Bi-directional ORM relationships between aggregates that load entire object graphs implicitly.
- Editing a migration file after it has been applied to any shared environment.
- Down-migrations as the rollback strategy in production.
- Adding `NOT NULL` columns without a default or a backfill step.
- Storing derived state (e.g. `order.total`) without an invariant that recomputes it on every mutation.
- Enums modelled as free-form strings without a constraint, lookup table, or domain-level value object.

## Cross-refs

- `architecture.md` — slice boundaries usually align with aggregate boundaries; misalignment is a smell.
- `data-access.md` — one port per aggregate, loading/saving the aggregate as a whole.
- `documentation.md` — destructive or surprising schema changes go through an ADR.
- `api-design.md` — external IDs exposed in API contracts come from this rule's ID typing decisions.
- `error-handling.md` — invariant violations raise typed domain errors, never generic DB exceptions.
