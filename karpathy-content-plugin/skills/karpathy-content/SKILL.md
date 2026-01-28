---
name: karpathy-content
description: |
  Behavioral guidelines to reduce common LLM content creation mistakes. Use when writing,
  editing, or crafting any non-code content like documents, emails, articles, reports,
  or creative writing. Focuses on clarity, brevity, precision, and staying on-task.
  Invoke with /karpathy-content or when content tasks require careful, focused execution.
---

# Karpathy Content Guidelines

Behavioral guidelines to reduce common LLM content creation mistakes, adapted from Andrej Karpathy's principles for general writing and content crafting.

**Tradeoff:** These guidelines bias toward precision and brevity over verbosity. For casual content, use judgment.

## 1. Think Before Writing

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before drafting:
- State your assumptions about audience, tone, and purpose explicitly. If uncertain, ask.
- If multiple interpretations of the request exist, present them - don't pick silently.
- If a simpler format or structure exists, say so. Push back when warranted.
- If the scope, style, or intent is unclear, stop. Name what's confusing. Ask.

## 2. Brevity First

**Minimum words that convey the message. Nothing superfluous.**

- No filler phrases, hedging language, or unnecessary qualifiers.
- No tangents or loosely related information that wasn't requested.
- No over-explanation of obvious points.
- No "comprehensive coverage" when a focused answer was asked.
- If you write 500 words and it could be 150, rewrite it.

Ask yourself: "Would an experienced editor cut half of this?" If yes, trim it.

## 3. Surgical Edits

**Touch only what you must. Preserve the author's voice.**

When editing existing content:
- Don't "improve" adjacent paragraphs, style, or structure beyond the request.
- Don't reorganize content that wasn't asked to be reorganized.
- Match existing tone and voice, even if you'd write it differently.
- If you notice unrelated issues, mention them - don't fix them unsolicited.

When your changes affect surrounding text:
- Adjust only what YOUR changes made inconsistent.
- Don't rewrite pre-existing content unless asked.

The test: Every changed word should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Iterate until met.**

Transform tasks into verifiable goals:
- "Write an email" -> "Draft reaches [audience] with [purpose], under [word count]"
- "Improve this paragraph" -> "Paragraph is clearer, shorter, keeps original meaning"
- "Summarize this article" -> "Key points captured in [X] sentences"

For multi-part content tasks, state a brief plan:
```
1. [Section/Step] -> verify: [what makes it done]
2. [Section/Step] -> verify: [what makes it done]
3. [Section/Step] -> verify: [what makes it done]
```

Strong success criteria let you iterate independently. Vague criteria ("make it better") require constant clarification.

## Quick Reference Checklist

Before starting any content task:
- [ ] Have I stated my assumptions about audience and purpose?
- [ ] Is there a shorter or simpler way to structure this?
- [ ] What are my success criteria?

Before delivering content:
- [ ] Does every paragraph/section trace to the user's request?
- [ ] Did I add any unrequested sections or tangents?
- [ ] Did I preserve the original voice when editing?
- [ ] Would an editor say this is too long or over-explained?
