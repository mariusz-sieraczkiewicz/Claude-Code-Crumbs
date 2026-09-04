---
name: sec
description: Rewrite your most recent answer to be shorter and plainer, explained through short code fragments. Use when the user invokes /sec (optionally with a number like "/sec 600"), or asks for a shorter explanation backed by small code excerpts. Default limit is 1200 characters. Keeps the conversation language of the previous messages — never switches to English on its own.
---

# Sec

Rewrite your previous answer so someone unfamiliar with the details can read it fast, using short code fragments as the anchor of the explanation. This reworks the **last substantive response** — it is not a new task.

## What to do

1. **Target the last answer.** Rewrite your most recent substantive reply. If the user points at something else, rewrite that instead.
2. **Respect the limit.** Default is max **1200 characters**. If the user gives a number (e.g. "/sec 600", "max 300 chars"), obey it exactly. Count characters including spaces and stay under. Code fragments do not count toward the limit — prose does.
3. **Keep the language.** Write in the language used in the previous messages of this conversation. Do not switch to English unless the conversation is already in English.
4. **Explain with short code fragments.** Show 1-5 line excerpts of the real code, and around each one say in plain words what it does in the flow. Never paste a long block. Never leave a fragment without an explanation.
5. **Plain language.** Short sentences, everyday words. No preamble, no filler, no hedging.

## Don't assume the reader knows the details

- **No bare references.** Don't cite line numbers, step or record IDs, or `file:line` anchors as if the reader remembers them. Say what the thing *is* in plain words.
- **Acronyms:** expand on first use in plain words, or drop them.
- **Files:** name one only when necessary, and describe its role in a short clause.

## Keep the substance

- Preserve the conclusion, the key facts, and any decision the reader still has to make.
- Cut repetition, background they already have, and caveats that don't change the answer.
- If it truly can't fit without losing something essential, keep the essential part and note in a final short clause what you left out.

## Output

Just the rewritten text with its code fragments — no meta-commentary, no label.
