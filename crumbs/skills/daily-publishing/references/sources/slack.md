# Source: slack

Processes already-collected Slack activity for the day. Output contract: see `README.md`.

## Locate

`sources.slack` in `config.yaml`: `access` (`codex` | `mcp` | `export` | `api`), `export_dir`, `channels` (empty = all the user participates in). Setup → `../integration.md`.

## Collect

With `access: codex`, fetch the day's messages by shelling out to the Codex CLI (Slack is read through its `slack@openai-curated` plugin — no token or MCP server in this config):

```bash
codex exec --skip-git-repo-check "Using your Slack tools only, strictly read-only (do not post, draft, react, or schedule anything): collect every message I sent on {date} and every thread I replied in that day, across <channels from config, or: all channels and DMs I participate in>. Output one line per message: 'HH:MM | <permalink or #channel> | <text>'. Include thread replies with their parent context. If you cannot access Slack, output exactly: SLACK_ACCESS_FAILED." < /dev/null
```

The `< /dev/null` is required: `codex exec` also reads extra prompt input from stdin, so with stdin left open (e.g. backgrounded runs) it hangs on "Reading additional input from stdin...".

The transcript echoes tool calls and prints the final answer twice — parse the message lines, ignore the noise. If the output contains `SLACK_ACCESS_FAILED` or no Slack tool calls ran, treat the source as `skipped (not configured)`. If the day spans many channels, split into one `codex exec` call per channel group to stay under its context and Slack rate limits.

Then, whatever the access method:

1. Gather messages the user **sent** plus threads they actively replied in, across configured channels/DMs, for the target day.
2. Drop pure reactions, +1s, logistics ("on my way"), and bot noise.
3. Keep: explanations the user wrote, problems debated, decisions, links shared with commentary, questions answered.

## Emit

- Provenance ref: permalink when available, else `slack#<channel>`.
- Collapse a thread into one item summarizing the exchange + the user's contribution.

→ `raw/{date}/slack.md`
