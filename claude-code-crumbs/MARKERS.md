# FREEZE markers — developer spec

Markers are HTML comments embedded in plugin command/agent markdown files. They are inert when rendered by Claude Code (HTML comments are invisible). At freeze time (`/freeze` → `scripts/freeze.sh`), the resolver evaluates each marker against the project's configuration and emits a frozen copy under `.claude/commands/` or `.claude/agents/` with **only the selected branches** present — markers are stripped.

## Syntax

### Conditional block

```
<!-- FREEZE:IF <expr> -->
content if expr true
<!-- FREEZE:ELIF <expr> -->
content for else-if (zero or more)
<!-- FREEZE:ELSE -->
fallback (optional)
<!-- FREEZE:ENDIF -->
```

Each marker must sit on its own line. Whitespace around the marker is permitted; trailing content on the marker line is not. Blocks nest arbitrarily deep.

### Inline value substitution

```
<!-- FREEZE:VAL <key> -->fallback-literal<!-- FREEZE:ENDVAL -->
```

Resolves to the dictionary value of `<key>` if non-empty and truthy; otherwise emits the fallback literal. Useful for templated branch names, PR title patterns, etc. Both markers must appear on the same logical text run — they do not span multiple paragraphs.

### File-level opt-out

```
<!-- FREEZE:SKIP -->
```

Anywhere in the file (typically the first line after frontmatter). Tells `freeze.sh` to exclude this file entirely — no project-local copy is written. Used for one-time bootstrap commands like `/000-prd-refine`, which must always be the plugin source (so a botched freeze doesn't lock you out of re-onboarding).

## Expression grammar (v1)

```
expr   := <key>                  # truthy check
        | "!" <key>              # falsy
        | <key> "==" <literal>   # equality
        | <key> "!=" <literal>   # inequality
key    := [A-Za-z_][A-Za-z0-9_]*
literal := "true" | "false" | INTEGER | QUOTED-STRING | BAREWORD
```

- `QUOTED-STRING` is `"..."` or `'...'` (no escaping; pick the delimiter that doesn't appear in the value).
- `BAREWORD` is any non-whitespace token; treated as a quoted string. Use barewords for short identifiers like `enterprise` or `small-team`. Quote anything that looks ambiguous.
- **No AND/OR/parens.** Compound conditions: use nested IFs or an ELIF chain. This is deliberate — keep the grammar trivial; complexity goes in the resolver dictionary, not the expression language.

### Truthiness

A value is **falsy** if it is exactly one of: empty string, `false`, `False`, `FALSE`, `0`, `null`, `~`. Everything else is truthy. List-valued keys are truthy iff the list is non-empty.

## Resolver dictionary

Keys are populated from these sources, in this precedence order (later overrides earlier):

| Key | Source | Type | Notes |
|---|---|---|---|
| `preset` | `.claude/stack.yaml` → `team_preset` | string | `solo` \| `small-team` \| `oss` \| `enterprise` |
| `pr_required` | `git-workflow.md` YAML block | bool | |
| `allow_commit_to_main` | `git-workflow.md` | bool | |
| `require_signed_commits` | `git-workflow.md` | bool | |
| `require_dco_signoff` | `git-workflow.md` | bool | |
| `require_codeowners_review` | `git-workflow.md` | bool | |
| `require_ticket_reference` | `git-workflow.md` | bool | |
| `tag_task_commits` | `git-workflow.md` | bool | |
| `auto_invoke_review` | `git-workflow.md` | bool | |
| `auto_invoke_verify` | `git-workflow.md` / `deployment.md` | bool | |
| `squash_merge` | `git-workflow.md` | bool | |
| `allow_force_push_to_main` | `git-workflow.md` | bool | |
| `delete_branch_on_merge` | `git-workflow.md` | bool | |
| `require_pre_flight` | `deployment.md` | bool | |
| `require_reviewers` | `git-workflow.md` | int | |
| `require_approvers_for_promote` | `deployment.md` | int | |
| `branch_name_pattern` | `git-workflow.md` | string | template literal |
| `pr_title_pattern` | `git-workflow.md` | string | |
| `pr_body_template` | `git-workflow.md` | string | multi-line YAML literal (`|`) |
| `ticket_prefixes` | `git-workflow.md` | list | truthy iff non-empty |

The YAML block is the first ` ```yaml ... ``` ` fenced block in the file. Subsequent blocks are ignored. Top-level keys only — nested mappings are not exposed to expressions.

## Examples

### 1 — boolean toggle

```
<!-- FREEZE:IF pr_required -->
Run `/006-merge` to open a PR before promotion.
<!-- FREEZE:ELSE -->
Solo preset: `/006-merge` only tags the commit; no PR is opened.
<!-- FREEZE:ENDIF -->
```

### 2 — string compare with ELIF chain

```
<!-- FREEZE:IF preset == "enterprise" -->
Branch naming: `task/{ticket_id}/{task_id}-{slug}` — ticket id is mandatory.
<!-- FREEZE:ELIF preset == "small-team" -->
Branch naming: `task/{task_id}-{slug}`.
<!-- FREEZE:ELIF preset == "oss" -->
Branch naming: `feat/{slug}` or `fix/{slug}`.
<!-- FREEZE:ELSE -->
Branch naming: optional; commits go straight to `main`.
<!-- FREEZE:ENDIF -->
```

### 3 — integer compare

```
<!-- FREEZE:IF require_reviewers != 0 -->
At least <!-- FREEZE:VAL require_reviewers -->1<!-- FREEZE:ENDVAL --> reviewer approval required before merge.
<!-- FREEZE:ENDIF -->
```

### 4 — inline VAL with negation

```
Default branch pattern: `<!-- FREEZE:VAL branch_name_pattern -->task/{task_id}-{slug}<!-- FREEZE:ENDVAL -->`.

<!-- FREEZE:IF !allow_commit_to_main -->
Direct commits to `main` are blocked at the platform level.
<!-- FREEZE:ENDIF -->
```

## One-way-ticket rationale

Freezing trades **flexibility** for **predictability**. Once `.claude/commands/*.md` exist, Claude Code reads them in preference to the plugin source — so the project's command behaviour stops drifting when the plugin updates, and toggle resolution stops re-running on every invocation. The cost: `/freeze --reset` is destructive of any post-freeze hand-edits. The cure: commit the frozen tree to git before customising. The discipline matches the broader plugin philosophy — small explicit steps, no hidden state, no surprise behaviour changes between two `/002-implement` runs on the same task.
