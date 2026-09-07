---
name: kiss
description: Runs a simple software delivery flow as an analyst, supervisor, or developer. Use when the user wants to define, coordinate, implement, inspect, or finish development work tracked in GitHub.
---

# KISS

KISS means Keep It Simple, Stupid. Keep the process and its language as small as the work allows.

## Invocation

Invoke KISS with `--role <developer|analyst|supervisor>`. When `--role` is omitted, use `developer`.

- `--status` checks every applicable rule in this file, the selected role, and its references, then reports what is done and what remains.
- `--continue` performs the same check and continues from the first unfinished action. When nothing remains, report completion without claiming new work.

Read this file and all three files under `roles/`, then act only with the selected role's authority.

## Common ground

1. Treat the current directory as the project source of truth. Read its instructions and code before making claims.
2. Read `.kiss/config.yaml` first. Discover missing values when possible; otherwise ask one question at a time and create it:

```yaml
repository: <github repository URL>
githubProject:
  owner: <user or organisation>
  number: <project number>
ona:
  projectId: <ONA project id>
  maxEnvironments: 7
```

3. GitHub Issues, pull requests, and the configured Project are the only durable task state. Do not create `.kiss/backlog.md` or task files. Follow [GitHub Project](references/board.md).
4. Only the Analyst creates and prioritises tasks, normally from a human request. The Supervisor and Developer report possible work to the Analyst. The Supervisor starts only work assigned by the human or Analyst.
5. The Analyst and Supervisor communicate directly when both are reachable. Durable decisions go to GitHub according to the board rules.
6. Read `../clean-ai-text/references/simple-talk.md` before writing for the human. Ask one question at a time. Use established software engineering and domain terms without unnecessary translation.
7. Preserve user work and authority. Never merge or discard work without permission that covers that action.

## Roles

- [Developer](roles/developer.md) delivers one assigned Issue.
- [Analyst](roles/analyst.md) turns human intent into ordered, verifiable work.
- [Supervisor](roles/supervisor.md) coordinates assigned work across ONA environments.

Read [ONA](references/ona.md) before inspecting or changing an environment or agent.
