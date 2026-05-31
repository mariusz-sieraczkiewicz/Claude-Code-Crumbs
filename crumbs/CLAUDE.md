# Coding Principles

Bias toward caution over speed. For trivial tasks, use judgment.

1. **Think first** — State assumptions. Multiple interpretations → present them. Simpler approach → say so. Unclear → stop and ask.
2. **Simplicity** — Minimum code that solves the problem. No speculative features, no single-use abstractions, no impossible-scenario handling. 200 lines → 50.
3. **Surgical changes** — Touch only what you must. Match existing style. Don't improve adjacent code or delete pre-existing dead code. Every changed line traces to the request.
4. **Goal-driven** — Transform tasks into verifiable goals. Multi-step → state plan with checks. Weak criteria → ask first.

## Mandatory Rules

- **One question at a time.** Never batch questions. Wait for answer before asking the next. Applies everywhere: elicitation, clarification, sub-agents.
- **Fix all verification issues.** Every issue found by verifiers gets fixed — pre-existing, regression, or new. Never dismiss as "not my change." Leave the codebase cleaner than you found it.

## Research & Tools

Never answer technical questions from memory. Verify first:
- Libraries, APIs, frameworks, K8s, Helm, GitLab CI → context7 MCP
- Everything else → WebSearch

**When WebSearch fails (no results or errors), use tavily MCP instead.**

Current year: 2026. Use when searching for latest information.
