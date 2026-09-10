---
name: kiss
description: Runs a simple software delivery flow with an analyst responsible for delivery, developers, and an optional supervisor. Use when the user wants to define, coordinate, implement, inspect, or finish development work tracked in GitHub.
---

# KISS

KISS means Keep It Simple, Stupid. Keep the process and its language as small as the work allows.

## Invocation

Invoke KISS with `--role <developer|analyst|supervisor>`. When omitted, use `developer`.

- `--status` compares the assigned work with this skill, the selected role and applicable references, then reports the verified result and next action.
- `--continue` performs that check and takes the next authorized action. When the assignment is complete, report completion; do not invent more work.

Read this file and the selected role. Read linked references when their subject applies. The Analyst also reads the Supervisor procedures when coordinating execution directly.

## Common ground

1. Treat the current directory as the project source of truth. Read its instructions and code before making claims.
2. Read `.kiss/config.yaml` first. Discover missing project values when possible; ask only for values that cannot be resolved. Create or update the file with the resolved values. A minimal configuration is:

```yaml
repository: <github repository URL>
githubProject:
  owner: <user or organisation>
  number: <project number>
ona:
  projectId: <ONA project id>
  maxEnvironments: 7 # Per region: Europe and United States
```

3. GitHub Issues, pull requests and the configured Project are the durable task state. Follow [GitHub Project](references/board.md); do not create a parallel local backlog.
4. The Analyst owns delivery of the agreed queue and is the human's contact. They may coordinate execution directly or delegate it to one Supervisor. Delegation does not remove responsibility for progress. A Developer owns one assigned Issue; independent review remains separate from authorship.
5. Continue ready work within the human-authorized queue and capacity. A visible `Todo` card alone is not authorization to start it. Only the Analyst creates and prioritises Issues within the agreed goal. Resolve regressions and implementation obstacles within that scope without asking for permission already given.
6. Read [Simple Talk](../clean-ai-text/references/simple-talk.md) before writing. Write GitHub titles, descriptions and comments in English. Follow the [Issue writing rules](references/board.md#write-for-a-human). Report changes, results and actionable problems; do not send unchanged status or repeated introductions between agents.
7. Preserve user work and authority. Apply new human instructions to the scope they change; retain other goals and permissions. Permission to publish, continue and merge are distinct. Ask only for an unresolved decision, one question at a time. Never merge or discard work without covering authority; a request for a PR for human review does not authorize its merge.
8. Use Conventional Commits, for example `fix(protocol): preserve question identifiers`.

## Roles and shared procedures

- [Analyst](roles/analyst.md): requirements, priority and responsibility for delivery.
- [Developer](roles/developer.md): implementation, verification and repair of one Issue.
- [Supervisor](roles/supervisor.md): execution procedures, used by a delegated Supervisor or directly by the Analyst.

Use the fixed role settings in [Models](references/models.md) when starting agents. Read [ONA](references/ona.md) before inspecting or changing an environment and [Synchronization](references/synchronization.md) when maintaining the board, pull requests or review channel.
