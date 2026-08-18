---
name: shorten
description: Rewrite your most recent answer to be shorter and plainer for a non-expert reader. Use when the user says "shorten", "shorter please", "make it shorter", "simpler", "plain language", "TL;DR", or gives a length limit (e.g. "max 500 chars"), or invokes /shorten (optionally with a number like "/shorten 500"). Cuts length and jargon only — keeps the conclusion and key facts. Never assumes the reader knows file names, line numbers (L10), record/step IDs (S3), or internal references, and spells out or drops acronyms.
---

# Shorten

Rewrite your previous answer so someone unfamiliar with the details can read it fast. This reworks the **last substantive response** — it is not a new task.

## What to do

1. **Target the last answer.** Rewrite your most recent substantive reply. If the user points at something else, rewrite that instead.
2. **Respect the limit.** Default is max **800 characters**. If the user gives a number (e.g. "/shorten 500", "max 300 chars", "in 2 lines"), obey it exactly. Count characters including spaces and stay under.
3. **Plain language.** Short sentences, everyday words. No preamble ("Here's a shorter version"), no filler, no hedging.

## Don't assume the reader knows the details

- **No bare references.** Don't cite line numbers (like L10), step or record IDs (like S3), or `file:line` anchors as if the reader remembers them. Say what the thing *is* in plain words.
- **Acronyms:** expand on first use in plain words, or drop them.
- **Files:** name one only when necessary, and describe its role in a short clause — never point at a file expecting the reader to recall its contents.

## Keep the substance

- Preserve the conclusion, the key facts, and any decision the reader still has to make.
- Cut repetition, background they already have, proof-style citations, and caveats that don't change the answer.
- If it truly can't fit without losing something essential, keep the essential part and note in a final short clause what you left out.

## Output

Just the rewritten text — no meta-commentary, no "Shortened:" label.
