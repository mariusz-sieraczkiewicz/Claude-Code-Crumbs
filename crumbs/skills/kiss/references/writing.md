# Write Issues for a human

Apply [Simple Talk](../../clean-ai-text/references/simple-talk.md) to every Issue title, body and comment. Keep the task's terminology. The reader knows neither the agent conversation nor the implementation details.

- **Title:** name the change and its effect in plain words, preferably 5–8 words. Preserve required project prefixes, identifiers and suffixes. Avoid vague titles such as "Refactor engine" and titles built from class names or unexplained abbreviations.
- **Body:** start with a short paragraph explaining the problem and intended behaviour. Follow with observable acceptance criteria, usually 3–5 bullets. Aim for 1,500 characters or fewer; use more only when needed to preserve agreed requirements, authority or essential constraints. Omit empty sections and repeated summaries.
- **Technical context:** keep only details that change what a correct solution must do. Link to the relevant source instead of copying architecture, workflow rules, file lists or logs. Describe what a link or identifier refers to; a section number or path alone is not an explanation. Keep exact names when they are necessary.
- **Comments:** usually use 2–4 sentences for a question, answer or durable decision: what, why and its effect on the task. Keep progress and verification in the places defined by [board content](board.md#content).
- **Updates:** keep one coherent current description, not successive addenda or duplicated requirements. Preserve agreed scope and criteria when shortening; follow the Analyst's rules for changes after work starts.

For example, prefer **"Keep user edits when AI finishes"** to **"Implement draftVersion guard in result hydration"**. Explain that a late AI result must not overwrite text edited after generation started; use the exact technical name only if the implementation needs it.

Before saving, reread the title and text as a new reader: can they tell what changes, why, and when it is done? Remove repetition and unnecessary detail, not requirements. Check that the final Markdown has real paragraphs and lists rather than escaped newlines.

