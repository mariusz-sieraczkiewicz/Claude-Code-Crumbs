# Copy and i18n

**Principle:** Every user-facing string flows through the i18n layer — no hardcoded literals, no internal labels, no debug strings leaking to the UI.

## Mechanical enforcement

The categories below are the contract; pick the concrete linters/scanners that fit the stack:

- **No string literals in user-facing render slots.** Linter rules forbid raw strings inside text-rendering positions: JSX `<Text>literal</Text>` / `<button>literal</button>`, SwiftUI `Text("literal")`, Compose `Text("literal")`, Android XML `android:text="literal"`. The accepted form goes through the i18n function (`t("key")`, `LocalizedStringKey("key")`, `stringResource(R.string.key)`).
  - Tool examples: `eslint-plugin-i18next` / `eslint-plugin-formatjs`, SwiftLint custom rule, `detekt` rule, Android Lint `HardcodedText`.
- **No keys without a translation entry.** A CI step extracts every i18n key referenced in code and asserts each one exists in the canonical locale file (the source-of-truth language). Examples: `i18next-parser`, `formatjs extract`, custom AST extractor. Missing key = build failure.
- **No orphan keys.** Keys present in the locale file but not referenced anywhere in code are flagged. Stale copy rots; orphans are removed every release.
- **Banned-substrings scanner over locale files.** A grep/regex gate over the canonical locale file (and every translated locale) rejects:
  - Internal release labels: `V1`, `V1.5`, `V2`, `MVP`, `alpha`, `beta`, `slice-N`, `phase-N`, `sprint-N`.
  - Ticket/epic IDs: `T-123`, `E03ui`, `JIRA-...`, `#1234` referring to issues.
  - Internal property/field names exposed as labels: camelCase tokens (`userName`, `firstName`), snake_case tokens (`first_name`), JSON-style fragments (`"key": value`), database column names.
  - Debug strings: `TODO`, `FIXME`, `XXX`, `console.log`, `print(`, `[DEBUG]`, stack-trace fragments.
  - Placeholder copy: `lorem ipsum`, `Untitled`, `New Item`, `Sample`, `Test`, `asdf`.
- **No string concatenation across locale boundaries.** A linter rule forbids `t("hello") + " " + userName` (breaks word order in other languages). The accepted form is parameterised interpolation: `t("greeting", { name: userName })`.
- **Pluralisation goes through the i18n plural API**, not `if (count === 1) "1 item" else count + " items"`.
- **Encoding and direction.** The locale file is UTF-8, normalisation NFC; RTL languages, if supported, are tagged.
- **Schema for locale files.** A JSON-schema (or equivalent) validates structure: every key is a string or a plural object; no nested debug metadata; no trailing commas.

## Subagent check

The `reviewer` and `verifier` look for what scanners cannot catch:

- **Internal vocabulary leaking through correct-looking copy.** A label like "Set primaryEmail" is technically a non-banned string, but `primaryEmail` is an internal field name. The user-facing word is "email" or "main email". Reviewer flags it.
- **JSON-shaped fragments in UI text.** `"status": "active"` rendered to a user means nothing. Replace with prose: "Account active".
- **Technical IDs surfaced to the user.** `Order 01HXYZABC` is acceptable for support, `Row 4821 in invoices_table` is not.
- **Stack traces / exception messages rendered as user copy.** Production paths surface a translated, friendly message; the technical detail goes to logs.
- **Untranslated strings hiding behind format functions.** `format("Hello, {name}", { name })` is still a hardcoded literal — it must be `t("greeting", { name })`.
- **Copy that describes future or speculative behaviour.** "Coming in V2" / "MVP feature" — describe what works today, in the user's words, or omit.
- **Inconsistent tone or terminology across screens.** A glossary lives in the i18n source; the reviewer checks that the same concept uses the same word everywhere (no "user" on one screen, "customer" on another, "account holder" on a third — pick one).
- **Accessibility labels go through i18n too.** A11y labels are user-facing; they obey the same rules.
- **Format strings preserve meaning in pluralisation and gender.** Reviewer checks that the chosen i18n format actually supports the languages the product ships in.

## Examples

### Good

```ts
// component
<Text>{t("payment.confirm.title")}</Text>
<Button label={t("payment.confirm.cta")} onPress={onConfirm} />
<Text>{t("payment.summary.total", { amount: formatMoney(total, locale) })}</Text>
<Text>{t("payment.items.count", { count: items.length })}</Text>
```

```json
// en.json (source of truth)
{
  "payment.confirm.title": "Confirm payment",
  "payment.confirm.cta": "Pay now",
  "payment.summary.total": "Total: {amount}",
  "payment.items.count": {
    "one": "{count} item",
    "other": "{count} items"
  }
}
```

### Bad

```ts
<Text>Confirm payment</Text>
<Button label={"Pay now"} onPress={onConfirm} />
<Text>{"Total: " + total + " EUR"}</Text>
<Text>{items.length === 1 ? "1 item" : items.length + " items"}</Text>
<Text>{"Set primaryEmail"}</Text>
<Text>{`{"status":"active"}`}</Text>
<Text>{`[DEBUG] order=${order.id}`}</Text>
<Text>Coming in V2</Text>
<Text>{error.stack}</Text>
```

Problems, in order: hardcoded strings; locale-broken concatenation; locale-broken pluralisation; internal field name exposed; JSON fragment in UI; debug string in production path; internal release label; raw stack trace as user copy.

## Anti-patterns

- Hardcoded user-facing strings in component / view / template files.
- Concatenation of translated fragments — breaks word order in other languages.
- `if (n === 1) "1 item" else n + " items"` — manual pluralisation.
- Internal property names (camelCase, snake_case) shown as labels.
- JSON-shaped fragments in UI text.
- Database column names, table names, internal service names visible to users.
- Technical IDs, ticket IDs, epic IDs in user-facing text.
- Internal release labels (`V1`, `V2`, `MVP`, `alpha`, `beta`, `slice-N`, `phase-N`).
- Debug markers (`TODO`, `FIXME`, `[DEBUG]`, `console.log` output, `print` output) reaching production UI.
- Raw stack traces or exception messages rendered to users.
- Placeholder copy (`lorem ipsum`, `Untitled`, `asdf`) shipped to users.
- Accessibility labels skipping the i18n layer.
- Inline format strings not routed through `t(...)`.
- Different terms for the same concept across screens.
- Locale files with orphan keys (referenced nowhere).
- Locale files missing keys referenced in code (renders as raw key to the user).

## Cross-refs

- `ui-components.md` — components receive already-translated text via props; they do not call `t(...)` from deep inside.
- `accessibility.md` — a11y labels go through the i18n layer with the same rules.
- `observability.md` — debug strings, internal IDs, and stack traces belong in logs, not in UI.
- `error-handling.md` — user-facing error messages are translated, friendly, and stable; technical detail is in logs and structured error codes.
- `documentation.md` — the glossary of approved user-facing terms lives next to the locale source of truth.
