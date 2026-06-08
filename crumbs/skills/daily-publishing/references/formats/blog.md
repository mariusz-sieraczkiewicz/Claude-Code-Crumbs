# Format: blog

**Goal:** a standalone post a stranger can read end-to-end and walk away able to apply one thing. ~600–1200 words. → `blog.md`

## Shape

1. **Title** — concrete and searchable; name the problem or the result, not the topic. Good: "Cutting our cold-start from 4s to 400ms". Weak: "Thoughts on performance".
2. **Hook (1 short para)** — the specific moment or pain that started it. Drop the reader in the middle, not into background.
3. **Context (1 para)** — only what's needed to follow; assume a competent peer, not a beginner.
4. **Body** — the points from `subject.md` in logical order. Show the work: code blocks, the wrong turn before the right one, the actual command/diff. Each `##` section makes one point.
5. **Takeaway** — what to remember and when it applies (and when it doesn't).
6. **CTA** — one line; link from `identity`.

## Writing rules

- Front matter at top: `title`, `date`, `tags` (3–6, lowercase), `slug`.
- Short paragraphs (1–4 sentences). Headings every ~150–250 words.
- Prefer showing a code/diff/example over describing it.
- Define a term the first time it appears, before you rely on it — teach from first principles; don't assume the reader shares your project's context.
- **For a technical or system subject, the explanation turns on a concrete worked example** (the one agreed in Phase 5): state an example problem, show the actual artifacts with real content (not just their file names), and give a before/after that contrasts the result *with* vs *without* the idea — that contrast is what proves it. Show the artifact, don't merely name it.
- Honest about tradeoffs and what you'd do differently — that's what makes it trusted.

## Skeleton

```markdown
---
title: ""
date: "{date}"
tags: []
slug: "{slug}"
---

{hook}

## {context-or-first-point}
...

## Takeaway
...

— {identity.name} · {link}
```
