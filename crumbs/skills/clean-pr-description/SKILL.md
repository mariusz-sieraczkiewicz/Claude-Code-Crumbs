---
name: clean-pr-description
description: Rewrite a pull request description around its intended outcome and, when relevant, the confirmed problem or root cause, in at most 10 sentences. Use when the user asks to clean, shorten or correct a PR description, or replace an implementation report with a clear explanation of purpose.
---

# Read

Identify the pull request from the user's request or the current branch. If the target is ambiguous, ask which PR to edit.

Read its full description and diff. Consult linked issues when needed to establish the intended outcome or root cause. Do not present an inferred cause or an unimplemented change as fact.

# Rewrite

Write for a reviewer who has not followed the discussion:

- Lead with what the PR aims to achieve and why it matters.
- Include the identified problem or confirmed root cause when relevant and supported by evidence; omit it when unknown.
- Mention scope, behavior changes or compatibility limits only when needed to describe the outcome accurately.
- Use plain language and at most 10 sentences. Prefer fewer; do not pad the text to reach eight.
- Remove repetition, filler, implementation walkthroughs, test reports, CI logs and work history. The description explains purpose, not the delivery process.
- Preserve issue-closing references such as `Closes #404` and any repository-required fields. Keep those fields concise.

# Publish

Check the draft against the diff, sentence limit and preserved references. If the user requested only a draft, return it without publishing. Otherwise, update only the PR description and read it back to verify the saved text.

Do not change code or other PR metadata. Updating a PR description does not require a git commit or push.
