# UI Components

**Principle:** Components are pure presentation — they render inputs and emit events; they do not fetch data, mutate state directly, or hardcode design values.

## Mechanical enforcement

Choose the linter/scanner toolchain that fits the stack; the categories below are the contract:

- **No direct data fetching inside presentation components.** A custom linter rule (e.g. ESLint custom rule, Semgrep pattern, SwiftLint custom rule) flags imports of HTTP clients, ORMs, storage SDKs, or `fetch`/`URLSession`/`HttpClient` from files inside the components/views layer. Data enters through props, observable inputs, or a hook/view-model boundary.
- **No direct state mutation outside the declared store boundary.** Components do not write to global state, the database, or platform storage. They emit events (callbacks, signals, intents) and a container layer handles the side effect.
- **Design tokens only — no magic values.** Linter rules forbid raw color literals (`#ff0080`, `rgb(...)`, `Color(red: ...)` ), inline pixel values for spacing/radius, and ad-hoc font sizes inside components. All values come from a tokens module (`tokens.spacing.m`, `Color.brandPrimary`, `theme.radius.l`).
- **No business logic in components.** A reviewer-runnable check (cyclomatic complexity threshold per component file, or a "no domain imports" rule that forbids importing from `domain/`, `services/`, `usecases/` inside `components/`) keeps logic out.
- **Props/inputs are typed.** Static typing is mandatory for the component boundary; untyped props (or `any`/`Any`) are a lint error.
- **No translation strings as literals.** See `copy-and-i18n.md` — all user-facing strings go through the i18n layer; the linter forbids string literals in JSX/SwiftUI/Compose text slots.
- **Storybook / preview / snapshot coverage** for every reusable component (one preview per documented state).

Example concrete tools: `eslint-plugin-react`, `eslint-plugin-boundaries`, `stylelint`, `SwiftLint custom_rules`, `ktlint` custom rules, `detekt`. Use tool names as examples, not as a mandate.

## Subagent check

The `reviewer` and `verifier` catch what linters miss:

- **Pure presentation in spirit, not just in imports.** A component that takes a callback prop but then computes pricing, applies discount rules, or decides what to send to the server has business logic in disguise. Move the decision out; the component should only call the callback.
- **One reason to re-render.** Components that own unrelated pieces of state (e.g. a form input that also tracks "is the user premium") are doing too much. Split them.
- **No conditional rendering driven by domain knowledge.** A component that checks `if (user.subscription.tier === 'gold' && user.country === 'DE')` is encoding policy. Lift the decision to a container or a feature flag.
- **Events are named for the user intent, not the implementation.** `onSubmit` / `onConfirm` / `onCancel` — not `onPostToServer` / `onCallApi`.
- **Tokens used semantically, not aesthetically.** Using `Color.brandError` for a "delete" affordance is good; using `Color.brandError` because the designer picked a red that happens to match is bad — find or add the right semantic token.
- **No leaked storage/platform concerns.** Components do not read from `localStorage`, `UserDefaults`, cookies, environment variables, or feature-flag SDKs directly.
- **Accessibility is part of the component contract** — see `accessibility.md`. The component exposes a stable a11y identifier and the right role, not the consumer.

## Examples

### Good

A pure presentation component (illustrative; same idea in any UI stack):

```tsx
type Props = {
  title: string;                 // already translated
  amountLabel: string;           // already formatted, already translated
  isLoading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function PaymentConfirmCard(props: Props) {
  return (
    <Card padding={tokens.spacing.m} radius={tokens.radius.l}>
      <Text style={tokens.font.heading}>{props.title}</Text>
      <Text style={tokens.font.body}>{props.amountLabel}</Text>
      <Button
        label={i18n.t("payment.confirm")}
        onPress={props.onConfirm}
        disabled={props.isLoading}
        testID="payment.confirm.button"
      />
      <Button
        label={i18n.t("payment.cancel")}
        variant="secondary"
        onPress={props.onCancel}
        testID="payment.cancel.button"
      />
    </Card>
  );
}
```

The container decides what `title`, `amountLabel`, and the callbacks do.

### Bad

```tsx
export function PaymentConfirmCard({ orderId }: { orderId: string }) {
  const [order, setOrder] = useState(null);

  useEffect(() => {
    fetch(`/api/orders/${orderId}`).then(r => r.json()).then(setOrder);
  }, [orderId]);

  const submit = async () => {
    if (order.user.tier === "gold") {
      await fetch(`/api/payments`, {
        method: "POST",
        body: JSON.stringify({ orderId, discount: 0.1 })
      });
    } else {
      await fetch(`/api/payments`, {
        method: "POST",
        body: JSON.stringify({ orderId })
      });
    }
  };

  return (
    <div style={{ padding: 17, borderRadius: 9, background: "#fafafa" }}>
      <h2 style={{ color: "#222" }}>Confirm payment</h2>
      <p>{order?.total} EUR</p>
      <button onClick={submit} style={{ background: "#0a84ff" }}>Confirm</button>
    </div>
  );
}
```

Problems: fetches data, mutates server state, encodes pricing policy, hardcodes colours, hardcodes spacing/radius, hardcodes English strings, no test selector, no a11y identifier, no loading/error states.

## Anti-patterns

- Components that import HTTP clients, ORMs, or storage SDKs directly.
- Components that own domain state (user tier, feature flags, subscription status) instead of receiving it as a prop.
- Inline colors, font sizes, spacing, or radius values.
- String literals for user-facing text instead of i18n keys.
- "God components" that switch on a `mode` prop with 6+ branches — split per mode.
- Components that know about routing (push/pop navigation) — receive `onConfirm` as a prop instead.
- Reusable components that hardcode their width/height in pixels — let the parent decide layout.
- Components without a documented preview / story state.
- Components without a stable a11y identifier — ATDD specs cannot select them.
- Mixing controlled and uncontrolled patterns within one component.
- Inline animation/timing values (`duration: 237`) instead of motion tokens.

## Cross-refs

- `accessibility.md` — every interactive component exposes a testable a11y identifier and the right role; keyboard navigation works.
- `copy-and-i18n.md` — no user-facing strings live in component files; everything goes through the i18n layer.
- `architecture.md` — components are a layer; their permitted dependencies are spelled out there.
- `testing.md` — ATDD specs select by a11y identifier; component previews are the unit-level visual contract.
- `code-style.md` — naming conventions for component files, props types, and event handlers.
