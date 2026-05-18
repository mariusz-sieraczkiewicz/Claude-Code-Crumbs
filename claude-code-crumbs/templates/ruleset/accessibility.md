# Accessibility

**Principle:** Every interactive element is reachable by keyboard, exposed with a stable a11y identifier, and meets WCAG 2.1 AA — accessibility is part of the component contract, not a release-eve audit.

## Mechanical enforcement

The categories below are the contract; pick the concrete tools that fit the stack:

- **Static a11y linting in the source files.** Tool examples: `eslint-plugin-jsx-a11y`, `axe-linter`, `stylelint-a11y`, Android Lint a11y checks, SwiftLint custom rules. The lint step rejects:
  - `<img>` / image components without alternative text.
  - Interactive elements rendered with non-interactive roles (`<div onClick>` instead of a button).
  - Form fields without an associated label.
  - Elements with `aria-*` attributes that are invalid or mismatched with the role.
  - Heading-level skips (`h1` followed by `h3`).
- **Runtime a11y scanning** during component preview / story rendering and during E2E runs. Tool examples: `axe-core`, `pa11y`, `Lighthouse a11y`, XCUITest accessibility audits, Android Accessibility Scanner. Violations at the "serious" / "critical" severity fail the build.
- **Required a11y identifiers on every interactive element.** A custom check (lint rule or reviewer step) asserts every `Button`, text input, toggle, switch, picker, stepper, link, and tappable cell carries a stable identifier:
  - Web: `data-testid="<screen>.<element>[.<modifier>]"` (or `id`, depending on the test selector convention).
  - iOS / SwiftUI: `.accessibilityIdentifier("<screen>.<element>")`.
  - Android / Compose: `Modifier.testTag("<screen>.<element>")`.
  - The naming convention is project-wide and documented in `testing.md` (ATDD selectors depend on it).
- **Contrast ratio check.** Design tokens are validated against WCAG 2.1 AA contrast minimums (4.5:1 for body text, 3:1 for large text and UI components). Tool examples: token-pipeline contrast check, `axe-core` colour-contrast rule.
- **Focus-visible.** Linter / runtime check that focusable elements have a visible focus ring (no global `outline: none` without a replacement).
- **Keyboard navigation smoke tests** in E2E: every screen must be reachable and operable using `Tab` / `Shift+Tab` / `Enter` / `Space` / `Esc` / arrow keys, with no keyboard trap.
- **Motion and animation.** Respect `prefers-reduced-motion` (or platform equivalent); enforce via a linter rule that forbids forced animation loops without a reduced-motion branch.

## Subagent check

The `reviewer` and `verifier` catch what scanners miss:

- **Identifier stability.** The identifier must not contain volatile data (no UUIDs, no timestamps, no localised strings). It must survive a copy change. Reviewer rejects `data-testid="confirm-payment-2026-05"`.
- **Identifier scope.** Identifiers are unique within a screen. Reviewer flags two elements on the same screen sharing an identifier.
- **Role semantics.** A button that opens a menu has `role="button"` and `aria-haspopup="menu"`; a tab in a tab bar has `role="tab"` and `aria-selected`. Linters catch invalid combinations; the reviewer catches missing context.
- **Announcement quality.** Screen-reader text is meaningful prose, not a duplicated visual label, not a debug string, not an internal field name. ("Submit payment of 12.99 EUR", not "btn", not "Submit primaryAction").
- **Keyboard equivalence for every gesture.** Long press, swipe, drag, pinch — every gesture has a keyboard or assistive-control alternative.
- **Touch target size.** Minimum target is 44x44 pt / 48x48 dp / WCAG 2.5.5 (target 24×24 CSS px minimum, 44×44 strongly recommended). Reviewer flags inline 20px icons used as tap targets.
- **Live regions used correctly.** Status messages use `aria-live="polite"`; errors that must interrupt use `assertive`. Overuse causes screen-reader spam.
- **Forms.** Every input has a programmatic label (not just a visual placeholder). Error messages are associated via `aria-describedby` and announced on validation failure.
- **Disabled vs. unavailable.** A disabled button is announced as disabled; a hidden button is not announced. Reviewer rejects "fake-disabled" styling without the actual disabled state.
- **Modals and overlays.** Focus moves into the modal on open, is trapped inside, and returns to the trigger on close.

## Examples

### Good

```tsx
<Button
  testID="payment.confirm.button"
  accessibilityRole="button"
  accessibilityLabel={t("payment.confirm.a11y")}
  onPress={onConfirm}
  disabled={isLoading}
>
  {t("payment.confirm.cta")}
</Button>

<TextField
  testID="payment.amount.input"
  label={t("payment.amount.label")}
  value={amount}
  onChange={setAmount}
  errorText={errors.amount && t("payment.amount.error.required")}
  aria-describedby="payment.amount.error"
/>
```

SwiftUI equivalent:

```swift
Button(action: onConfirm) {
    Text(LocalizedStringKey("payment.confirm.cta"))
}
.accessibilityIdentifier("payment.confirm.button")
.accessibilityLabel(Text(LocalizedStringKey("payment.confirm.a11y")))
.disabled(isLoading)
```

Tokens module enforces contrast:

```ts
// tokens.ts — verified at build time
export const tokens = {
  color: {
    textOnSurface:   "#1a1a1a", // contrast 16.1:1 on surface  — AAA
    textOnPrimary:   "#ffffff", // contrast  5.2:1 on primary  — AA
    surface:         "#fafafa",
    primary:         "#0a66c2",
    danger:          "#b3261e",
  },
};
```

### Bad

```tsx
<div onClick={onConfirm} style={{ background: "#0a84ff", color: "#a0c8ff" }}>
  Confirm
</div>

<input type="text" placeholder="Amount" />

<span onClick={openMenu}>...</span>
```

Problems: not a button (no role, no keyboard activation, no focus ring); colour contrast fails AA; placeholder is not a label; the menu trigger has no role, no name, and no a11y identifier.

## Anti-patterns

- `<div onClick>` / `View` with a tap gesture instead of a proper button — invisible to screen readers, not keyboard operable.
- Missing `accessibilityIdentifier` / `data-testid` / `testTag` on interactive elements — ATDD specs cannot select them.
- Identifiers that contain volatile data (UUIDs, timestamps, localised text).
- Placeholder used as the only label for a form field.
- Icon-only buttons with no `accessibilityLabel`.
- `outline: none` (or platform equivalent) without a visible focus replacement.
- Colour as the only signal (red text for error, no icon or prose).
- Contrast below 4.5:1 for body text, 3:1 for large text / UI components.
- Touch targets under 24 CSS px (24×24 absolute minimum; 44×44 strongly preferred).
- Modal that does not trap focus or return focus to the trigger on close.
- Gesture-only interactions (swipe to delete) with no keyboard / assistive alternative.
- `aria-live="assertive"` for non-urgent status — screen-reader spam.
- Animations and parallax effects with no `prefers-reduced-motion` branch.
- Disabled buttons styled grey but still focusable and activatable.
- A11y labels containing internal field names, IDs, or debug strings (see `copy-and-i18n.md`).
- Heading levels skipped or used for visual sizing instead of structure.

## Cross-refs

- `ui-components.md` — interactive components expose a11y identifier and role as part of their contract; consumers receive labels via props.
- `testing.md` — ATDD selectors are the a11y identifiers defined here; the naming convention (`<screen>.<element>[.<modifier>]`) is shared.
- `copy-and-i18n.md` — a11y labels are user-facing copy and go through the i18n layer; no internal labels.
- `ui-components.md` / `code-style.md` — design tokens encode contrast-checked colour pairs; magic colours are forbidden.
- `documentation.md` — the a11y identifier naming convention and the screen-reader label glossary live in the docs source of truth.
