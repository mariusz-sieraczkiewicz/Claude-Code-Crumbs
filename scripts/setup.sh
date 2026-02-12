#!/bin/bash
set -e

export NODE_USE_SYSTEM_CA=1

echo "Installing Python..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-certifi ca-certificates

echo "Installing uv/uvx..."
curl -LsSf https://astral.sh/uv/install.sh | sh

echo "Installing pip-system-certs..."
pip3 install --break-system-packages pip-system-certs

echo "Creating .mcp.json..."
cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "globaljira": {
      "command": "uvx",
      "args": [
        "mcp-atlassian"
      ],
      "env": {
        "JIRA_URL": "https://globaljira.roche.com",
        "JIRA_PERSONAL_TOKEN": "${JIRA_PERSONAL_TOKEN}",
        "JIRA_SSL_VERIFY": "false",
        "JIRA_READ_ONLY": "true"
      }
    },
    "tavily": {
      "command": "npx",
      "args": [
        "-y",
        "tavily-mcp@latest"
      ],
      "env": {
        "TAVILY_API_KEY": "${TAVILY_API_KEY}"
      }
    }
  }
}
EOF

echo "Creating .claude/commands/create-command.md..."
mkdir -p .claude/commands
cat > .claude/commands/create-command.md << 'CMDEOF'
---
description: 'Create a new Claude Code custom slash command with best practices'
argument-hint: [command-name] [brief-description]
---

# Create Custom Claude Code Slash Command

You are creating a new custom slash command for Claude Code. The command name is: **$1**
The brief description/purpose is: **$2**

If no arguments provided, ask the user for:

1. Command name (lowercase with hyphens, e.g., "code-review", "deploy-staging")
2. Brief description of what the command should do

## Command File Location

Create the command file at: `.claude/commands/$1.md`

For namespaced commands (e.g., "workflow/dev-story"), create at: `.claude/commands/workflow/dev-story.md`

## Required Format

Use this structure with YAML frontmatter:

```yaml
---
description: 'Brief explanation displayed in /help'
argument-hint: [arg1] [arg2]  # Optional - shows expected arguments
---

Your prompt content here.
Use $ARGUMENTS for all args or $1, $2, etc. for positional.
```

## Frontmatter Fields Reference

| Field                      | Required    | Purpose                                   |
| -------------------------- | ----------- | ----------------------------------------- |
| `description`              | Recommended | Shows in `/help` command listing          |
| `argument-hint`            | Optional    | Shows expected args during autocompletion |
| `disable-model-invocation` | Optional    | Prevents programmatic invocation          |

## Argument Handling

### All Arguments: `$ARGUMENTS`

```markdown
Fix the issue described: $ARGUMENTS
```

Usage: `/fix-issue Login button not working on mobile`

### Positional Arguments: `$1`, `$2`, `$3`

```markdown
Review PR #$1 with priority: $2
Assign to: $3
```

Usage: `/review-pr 456 high @alice`

## Best Practices to Follow

### 1. Description (CRITICAL for discoverability)

- Keep it concise but informative
- Describe the ACTION the command performs
- Will appear in `/help` output

Good: `'Perform comprehensive security audit on specified directory'`
Bad: `'Security stuff'`

### 2. Be Specific in Prompts

Instead of:

```markdown
Review the code
```

Write:

```markdown
Review the code in $ARGUMENTS focusing on:

1. Security vulnerabilities (SQL injection, XSS, CSRF)
2. Performance bottlenecks
3. Error handling completeness
4. Test coverage gaps

For each issue found, provide:

- Severity (Critical/High/Medium/Low)
- Location (file:line)
- Description
- Suggested fix with code example
```

### 3. Use Emphasis for Critical Instructions

```markdown
IMPORTANT: Always run tests before committing.

YOU MUST follow these steps in order:

1. First step
2. Second step

CRITICAL: Never expose API keys in responses.
```

### 4. Tool Restrictions

Only restrict when necessary:

- `allowed-tools: Read, Grep` - Read-only analysis
- `allowed-tools: Bash(git:*)` - Only git commands
- Omit for full tool access

### 5. File References with `@`

```markdown
Review the following files:
@src/lib/components/Button.svelte
@src/lib/utils/helpers.ts

Check for consistency with:
@docs/coding-standards.md
```

### 6. Bash Output Inclusion

If allowed-tools includes Bash, you can use the exclamation mark followed by a command in backticks to embed live shell output into your prompt. For example, showing the current git branch or recent commits. The syntax is: exclamation mark, then backtick, then command, then backtick.

### 7. Structured Output Requests

```markdown
Generate output in this format:

## Summary

[1-2 sentence overview]

## Changes

- [ ] Change 1
- [ ] Change 2

## Risks

| Risk | Severity | Mitigation |
| ---- | -------- | ---------- |
```

## Command Template Patterns

### Analysis Command

```yaml
---
description: 'Analyze code for [specific purpose]'
allowed-tools: Read, Grep, Glob
argument-hint: [file-or-directory]
---

Analyze $ARGUMENTS for:
1. [Analysis point 1]
2. [Analysis point 2]
3. [Analysis point 3]

Output format:
## Findings
[Structured findings]

## Recommendations
[Actionable recommendations]
```

### Creation Command

```yaml
---
description: 'Create new [thing] with tests'
argument-hint: [name]
---

Create a new [thing] named $ARGUMENTS:

1. Create main file at [path]/$ARGUMENTS.[ext]
2. Create test file at [path]/$ARGUMENTS.test.[ext]
3. Update exports in [index file]

Follow these patterns:
- [Pattern 1]
- [Pattern 2]

Include:
- [Required element 1]
- [Required element 2]
```

### Workflow Command

```yaml
---
description: 'Execute [workflow name] workflow'
argument-hint: [context]
---

Execute the [workflow] workflow for: $ARGUMENTS

## Steps

1. **Preparation**
   - [Prep step 1]
   - [Prep step 2]

2. **Execution**
   - [Exec step 1]
   - [Exec step 2]

3. **Verification**
   - [Verify step 1]
   - [Verify step 2]

## Success Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
```

### Review Command

```yaml
---
description: 'Review [thing] against standards'
allowed-tools: Read, Grep
argument-hint: [target]
---

Review $ARGUMENTS against project standards:

## Checklist
- [ ] Follows coding conventions
- [ ] Has adequate test coverage
- [ ] Documentation is complete
- [ ] No security vulnerabilities
- [ ] Performance is acceptable

## Output
For each issue:
1. Location
2. Severity
3. Description
4. Suggested fix
```

## Your Task

Now create the command file for **$1** with purpose: **$2**

1. Determine if tool restrictions are needed
2. Define appropriate arguments
3. Write a clear, specific prompt
4. Include output format expectations
5. Save to `.claude/commands/$1.md`

After creating, remind the user to:

- Test with `/help` to verify the command appears
- Run the command to test behavior
- Iterate on the prompt based on results
- Consider adding to version control for team sharing
CMDEOF

echo ""
echo "Installation complete!"
echo "Python: $(python3 --version)"
echo "pip: $(pip3 --version)"
echo "uv: $($HOME/.local/bin/uv --version)"
echo "uvx: $($HOME/.local/bin/uvx --version)"