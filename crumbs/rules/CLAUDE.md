## Tools

Never answer technical questions from memory. Verify first:
- Python/JS/TS libraries, APIs, versions, frameworks → context MCP
- Kubernetes, Helm, kubectl → context MCP
- GitLab CI/CD → context MCP
- Otherwise → WebSearch (fallback: tavily MCP if WebSearch fails)

Use `rg` for exact strings/imports. Use `ast-grep` for structural patterns (class defs, function signatures).

Current year: 2026. Use this when searching for latest information.

## Behavioral Guidelines

Bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

State assumptions explicitly. Multiple interpretations → present them. Simpler approach exists → say so. Unclear → stop and ask.

### 2. Simplicity First

Minimum code that solves the problem. No speculative features, no single-use abstractions, no error handling for impossible scenarios. 200 lines that could be 50 → rewrite.

### 3. Surgical Changes

Touch only what you must. Match existing style. Don't improve adjacent code, don't refactor what isn't broken, don't delete pre-existing dead code (mention it instead). Remove only orphans YOUR changes created. Test: every changed line traces to the user's request.

### 4. Goal-Driven Execution

Transform tasks into verifiable goals ("Add validation" → "Write tests for invalid inputs, make them pass"). For multi-step tasks, state plan with verification checks. Strong criteria → independent looping. Weak criteria → ask for clarification first.

## Asking Questions (MANDATORY)

ONE question at a time. Never batch. Wait for answer before next question. Applies everywhere: elicitation, clarification, sub-agents.

## Fix ALL Issues During Verification (MANDATORY)

Fix EVERY issue found by verifiers — pre-existing, regression, or new. Never dismiss as "not caused by this change." Leave the codebase cleaner than you found it: documentation gaps, naming inconsistencies, orphaned references, stale paths.

## globaljira MCP

If `globaljira` returns `Unexpected return value type` errors or `curl` gets a 302 from Cloudflare → user is off VPN. Tell them to connect; don't debug the MCP package.
