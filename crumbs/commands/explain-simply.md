---
description: 'Explain what happened in plain language — context first, problem by problem, honest about what is and is not solved. No jargon.'
argument-hint: <what to explain (optional — defaults to the most recent work/findings in this conversation)>
---

# Explain Simply

Give a plain-language explanation of **$ARGUMENTS** — or, if that is empty, of the most recent work, findings, decision, or situation in this conversation.

Assume the reader does **not** know this system, codebase, or domain by heart. They do not want jargon, acronym soup, raw metric dumps, or bare file references. They want to actually **understand** what happened and what it means — especially the problems hit along the way, whether each was solved, and what is still open.

## How to explain

1. **Context first.** Before any detail, set the scene for someone seeing this fresh: what is this thing, what is it for, and why does it matter? A few plain sentences. Never assume the reader remembers what a file, function, metric, component, or term does — explain it by *what happens / the flow*, not by its name.

2. **Organize around the PROBLEMS, not internal labels.** Do NOT structure the explanation by ticket IDs, acceptance-criteria numbers, phase names, task codes, or file names. Structure it by the actual problems that came up, in human terms. For each problem:
   - **What it was** — in plain language, with a concrete everyday analogy when it helps (a broken measuring tape, a safety net nobody fell into, a placebo fix, a stopwatch started too late).
   - **Was it solved?** — yes / partly / no, said plainly.
   - **How** — the actual fix, in terms a non-expert can grasp.
   - **What it cost or revealed** — any honest catch, surprise, or trade-off.

3. **Be honest, not impressive.** The goal is the reader's understanding, not showing off. If a result is weaker than it sounds, if a "fix" only partly works, if something was almost wrong and got caught, or if a number is flattering for a boring reason — say so. End with a clear **"What is still NOT solved"** section listing the real gaps, limitations, and deferred decisions.

4. **Anchors are allowed; bare citations are not.** You MAY point at a specific file, section, line, number, or short excerpt — but always wrapped in a plain explanation of what it is and where it fits in the flow. A path or metric on its own, with no surrounding explanation, is exactly what to avoid.

5. **Plain prose, light structure.** Short paragraphs, everyday words, an optional simple table or problem-by-problem headings. Expand any acronym on first use. Match the user's language.

Make it as long as it needs to be to be genuinely clear — but every sentence must add understanding, not noise. If you are unsure what the reader most wants explained, ask one focused question before diving in.
