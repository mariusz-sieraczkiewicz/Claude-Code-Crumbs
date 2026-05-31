---
name: learn-from-conversation
description: Mine session history for struggles, user corrections, and workflow patterns. Present findings and save chosen ones to persistent learnings.
---

# Learn From Conversation

Storage target: `{project-root}/.claude/rules/learnings.md` (default) or `~/.claude/rules/learnings.md` (with `--user` flag). Never modify CLAUDE.md or MEMORY.md.

## Step 1: Locate Session Data

Session directory: `~/.claude/projects/{encoded-project-path}/` (path with `/` → `-`, prefixed with `-`). List `.jsonl` files sorted by size (largest first).

If no session data: tell user. If only one small session: analyze directly without subagent.

## Step 2: Analyze

Spawn `learn-from-conversation-analyzer` with: session directory, file list, CWD, paths to both learnings files (project + user level).

Analyzer instructions:
1. Read compaction summaries from largest sessions first
2. Scan for user corrections ("no", "wrong", "don't", "stop", "always", "never", "I said", "I meant")
3. Scan for struggle patterns (repeated tool calls, error-retry sequences)
4. Check existing learnings for duplicates
5. Write top 5-15 findings to `/tmp/learn-from-conversation-findings.yaml`

## Step 3: Present Findings

Read analyzer output. Present grouped by category:

```
{N}. [{CATEGORY}] {summary}
   Detail: {detail}
   Would remember: "{memory_entry}"
   {if duplicate: "Already in memory — would strengthen to: {strengthened}"}
```

## Step 4: User Selection

`AskUserQuestion` with `multiSelect: true`. Options: each finding by number + summary, "All" option. User can also type custom text.

## Step 5: Save

For each selected finding:
- **New**: append under a `##` header, explain WHY not just WHAT
- **Existing**: replace with strengthened version (more specific, more context, examples)

Keep entries concise — the file is auto-loaded into every conversation. Create the file with `# Learnings from Session History` header if it doesn't exist.

## Step 6: Confirm

Show user what was saved. If no findings: report session went smoothly.
