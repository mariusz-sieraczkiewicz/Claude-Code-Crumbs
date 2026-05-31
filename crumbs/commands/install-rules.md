---
description: Install coding rules from the crumbs plugin into the current project with stack-appropriate file filters.
argument-hint: "[ruleset-name ...]"
---

# /install-rules

Copies selected rulesets from the plugin into the project's `.claude/rules/` directory, adding frontmatter `globs` filters so rules apply selectively based on the project's stack.

## Available Rulesets

| Ruleset | File | Applies to |
|---------|------|------------|
| error-handling | unified-error-handling.md | All code |
| logging | unified-logging.md | All code |
| testing | unified-testing.md | Test files |
| test-execution | unified-test-execution.md | All (behavioral) |
| validation | unified-validation.md | All code |

## Process

### Step 1: Present available rulesets

Show the user the table above. If arguments were provided (e.g., `/install-rules logging testing`), pre-select those. Otherwise ask which rulesets to install using `AskUserQuestion` with `multiSelect: true`.

### Step 2: Propose file filters

For each selected ruleset, propose a `globs` frontmatter filter based on what makes sense:

- **error-handling**: `**/*.{ts,js,py,java,kt,go}` (all source code)
- **logging**: `**/*.{ts,js,py,java,kt,go}` (all source code)
- **testing**: `**/*.{test,spec}.{ts,js,py}`, `**/test_*.py`, `**/tests/**`
- **test-execution**: no globs (behavioral rule, applies always)
- **validation**: `**/*.{ts,js,py,java,kt,go}` (all source code)

Present the proposed filters to the user and ask them to confirm or adjust. Show as a list:
```
error-handling → globs: **/*.{ts,js,py}
logging        → globs: **/*.{ts,js,py}
testing        → globs: **/*.test.{ts,js}, **/test_*.py
```

### Step 3: Install

For each confirmed ruleset:

1. Read the source file from `${CLAUDE_PLUGIN_ROOT}/ruleset/{filename}`
2. Prepend the `globs` frontmatter:
   ```
   ---
   globs: <confirmed-glob-pattern>
   ---
   ```
3. Write to `.claude/rules/{ruleset-name}.md` in the project root
4. If the file already exists, ask user: overwrite or skip?

### Step 4: Confirm

Show summary of what was installed:
```
Installed rules:
  .claude/rules/error-handling.md  (globs: **/*.{ts,js,py})
  .claude/rules/logging.md         (globs: **/*.{ts,js,py})
  .claude/rules/testing.md         (globs: **/*.test.{ts,js})
```
