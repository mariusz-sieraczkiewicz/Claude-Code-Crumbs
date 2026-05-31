---
name: learn-from-conversation
description: Mine session history for struggles, user corrections, and workflow patterns. Present findings and save chosen ones to persistent learnings.
argument-hint: "[number-of-sessions] [--user]"
---

# Learn From Conversation

Storage target: `{project-root}/.claude/rules/learnings.md` (default) or `~/.claude/rules/learnings.md` (with `--user` flag). Never modify CLAUDE.md or MEMORY.md.

## Step 1: Locate Session Data

Session directory: `~/.claude/projects/{encoded-project-path}/` (path with `/` → `-`, prefixed with `-`). List `.jsonl` files sorted by modification time (newest first).

Default: analyze the **last 5 sessions**. User can override with a number argument (e.g., `/learn-from-conversation 10`). If fewer sessions exist than requested, analyze all.

If no session data: tell user.

## Step 2: Parallel Analysis

Spawn **one `learn-from-conversation-analyzer` per session file**, all in parallel. For large session files (>500KB), spawn multiple analyzers splitting the file into chunks.

Each analyzer receives: its session file path(s), CWD, paths to both learnings files (project + user level).

Analyzer instructions:
1. Read compaction summaries first, then scan messages
2. Scan for user corrections ("no", "wrong", "don't", "stop", "always", "never", "I said", "I meant")
3. Scan for struggle patterns (repeated tool calls, error-retry sequences)
4. Scan for workflow preferences and confirmed approaches
5. Write findings to `/tmp/learn-from-conversation-{session-id}.yaml`

Launch all analyzers in a single message for true parallelism.

## Step 3: Unify and Deduplicate

Read all analyzer outputs. Merge findings:
1. Group by theme/topic across all sessions
2. Deduplicate — same lesson from multiple sessions → single entry noting frequency ("seen in 3/5 sessions")
3. Deduplicate against existing learnings files (both project and user level)
4. Rank by: frequency (recurring > one-off), severity (user frustration > mild preference), actionability
5. For existing learnings that recur: prepare strengthened versions instead of new entries

## Step 4: Present Findings

Present unified findings grouped by category:

```
{N}. [{CATEGORY}] {summary} (seen in {count} session(s))
   Detail: {detail}
   Would remember: "{memory_entry}"
   {if existing: "Already in memory — would strengthen to: {strengthened}"}
```

Tell user: "Analyzed {N} of {total} sessions." If not all sessions were analyzed, ask: "Want me to analyze more sessions?"

## Step 5: User Selection

`AskUserQuestion` with `multiSelect: true`. Options: each finding by number + summary, "All" option. User can also type custom text.

## Step 6: Save

For each selected finding:
- **New**: append under a `##` header, explain WHY not just WHAT
- **Existing**: replace with strengthened version (more specific, more context, examples)

Keep entries concise — the file is auto-loaded into every conversation. Create the file with `# Learnings from Session History` header if it doesn't exist.

## Step 7: Confirm

Show user what was saved. If no findings: report sessions went smoothly.
