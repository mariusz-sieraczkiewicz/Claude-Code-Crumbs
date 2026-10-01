# Crumbs

A collection of focused skills and configurations. Claude Code discovers skills in `skills/`; the Codex manifest exposes the same directory.

## Install or update

In Claude Code:

```text
/plugin marketplace add mariusz-sieraczkiewicz/Claude-Code-Crumbs
/plugin install crumbs@Claude-Code-Crumbs
```

Existing clients can fetch the current marketplace and update the plugin:

```text
/plugin marketplace update Claude-Code-Crumbs
/plugin update crumbs@Claude-Code-Crumbs
```

Reload or restart the client if requested. Other plugin clients should refresh this repository's `main` branch through their normal update mechanism.

## Dependabot maintenance

From version **0.1.71**, use `/crumbs:dependabot-review` to review open Dependabot pull requests, verify full continuous integration coverage on current commits, and diagnose failures. Repairs, approvals and merges require the invoking user's authorization and repository gates. See the [usage and safety guide](skills/dependabot-review/README.md).
