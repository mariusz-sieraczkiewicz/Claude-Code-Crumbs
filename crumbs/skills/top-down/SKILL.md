---
name: top-down
description: Rewrite the answer top-down — a lead that stands alone, then fixed sections for questions, what was done, what was not, and follow-ups. Use when reporting finished work, findings, an investigation, or a decision the human has to make.
---

# top-down

Write the answer in two layers. A reader who stops after the first sentence still has the point.
A reader who reads the sections has everything.

Then stop. There is no third layer. Whatever did not fit belongs in a section or does not belong in
the answer.

## Language

Write the answer in the language the conversation is already using, unless the user has explicitly
asked for another one. This covers everything you emit: the lead, the section headings, and every
line under them. Translate the four headings into that language rather than leaving them in English.

Within that language, keep technical and domain terms in their original English form instead of
translating them.

How to word every line — plainness, empathy for a reader who was not there, never compressing exact
names or paths, stating decisions and who owns them — is governed by `references/simple-talk.md`.
Read it and apply it to the lead and to every section line. Where it sets a length limit, the
structure here wins: the sections stay, and the wording inside them gets shorter.

## Layer 1 — the lead

One or two sentences. The main message and its effect. Not what you did, what is now true. Write it
last, from everything you know, then delete every word that survives deletion.

When the crux of the answer is a decision only the human can make, **the question belongs in the
lead**. A reader who stops at the first sentence must still know they are being asked something.
That question then appears nowhere else — see below.

## Layer 2 — up to four sections

Never a section outside these four, never in another order, headings translated as described above.
But **every one of them is optional.** Most answers use one or two.

```
* questions
- <one question per line>

* not done
- <one sentence per item, saying why>

* follow-up tasks
- <one short sentence per task>

* done
- <one sentence per non-obvious result, verb first, max 15 words>
```

What is open comes before what is finished. The reader needs the parts that still need them; the
completed work is the part they can skim.

### A section earns its place or it is not written

The four headings are a menu, not a form. Write a section only when this answer genuinely produced
something for it. A heading kept because the shape has four of them is noise, and worse, it pulls
filler in underneath: the reader cannot tell the line that mattered from the line that was there to
stop a heading looking bare.

Two tests, both of which a section must pass:

- **Did this answer produce it?** The content has to come from the work this answer reports, not
  from the conversation around it. A leftover from an earlier task, a caveat the reader already
  accepted, an open item that has been open for days — none of those became true here, so none of
  them belong. Dragging them along makes the answer look like it made less progress than it did.
- **Would leaving it out cost the reader something?** If they would act no differently for having
  read it, it is decoration.

The common failures, each a section that should have been dropped:

- `follow-up tasks` restating a backlog item that already existed before this answer.
- `not done` listing something that was never in scope, so it was never going to be done.
- `questions` repeating the question already asked in the lead, or asking something you can settle
  yourself by reading one file.
- `done` on an answer that decided or explained something rather than changing anything.

A lead alone is a complete answer when nothing is open and nothing was produced.

**questions** — only things you genuinely cannot decide yourself. One question per line, never two
in one line.

**Never write the same question twice.** Each question lives in exactly one place: the one that is
the essence of the answer goes in the lead and is not repeated here; every additional question goes
here and stays out of the lead. If the only question was the essential one, this section is gone.

**not done** — anything in scope that you skipped, could not finish, or did not verify. The reason
is the whole point of the line; a bare "not done" is worthless.

**follow-up tasks** — work that falls out of this but is not part of it. One short sentence each,
enough that someone could pick it up cold.

**done** — the hardest section to write, because most of what you did does not belong in it.

Each line starts with a verb and states a result. Fifteen words is the ceiling, not the target.
**Three or four lines is the ceiling too** — if you have more, you are listing the job rather than
the results, so go back and cut.

The test for every candidate line: **could a competent reader have predicted this from the task
itself?** If yes, delete it. That removes, by default:

- routine verification that went as expected — the test suite passing, the build being green, the
  page still loading;
- mechanical steps implied by the approach you already described — the rename that follows from the
  decision, the import that follows from the move;
- restatements of the same result at a different zoom level.

What survives is what the reader could not have guessed: a judgement call and why you made it, a
deviation from the obvious approach, a durable artifact that did not exist before, something that
turned out other than expected.

Verification is assumed, not reported. Mention it only when it failed, when it surprised you, or
when producing it was the deliverable.

## The extraction test

Apply to every line: **would this still mean something if it were lifted out of this conversation
and shown to someone else?**

If not, the line leans on context that exists only between you and this thread. The failure modes
below are the recurring ways that happens.

The word limits never excuse a naked label or a bare count. If a line does not fit with its context
intact, cut the line or split it — never cut the context.

## Failure modes

Each has a mechanical test and a fix. Run them before sending.

### Count without content
A quantifier standing in for the items: "three tasks", "several problems", "a few files".

- **Test:** delete the number. If nothing is lost, the number was standing in for content.
- **Fix:** name the items. The count is free once the items are there.

### Label without gloss
Any identifier assumed known: a ticket id, file name, class, function, flag, branch, acronym,
product, tool, or person.

- **Test:** would a reader meeting this label for the first time know what it refers to?
- **Fix:** one clause, immediately, saying what it is or does. Not a definition — a role.

### Characterisation without the artifact
Describing the shape of output instead of showing it: "the error was misleading", "the log says
something else", "the output looked odd".

- **Test:** am I making a claim about text, data, or a value that I never display?
- **Fix:** show the smallest excerpt that carries the claim — usually one line.

### Conversational anchoring
Words that resolve only inside this thread: "as I said above", "that file", "the earlier fix",
"this approach", and bare "it" or "there" across a break.

- **Test:** does resolving this word require having read an earlier message?
- **Fix:** restate the referent. Repetition is cheaper than a dangling pointer.

### Verdict without an observable
A judgement with nothing a reader could check: "it works now", "all green", "fixed".

- **Test:** what did I see that made me believe this, and is it in the text?
- **Fix:** give the observable — the count, the status, the response, the before and after. If you
  did not verify it, the line belongs in the not-done section, not the done section.
- **But:** the cure is usually to delete the claim, not to evidence it. "It works" is exactly the
  predictable line the done section excludes. Keep the observable only when the claim survives that
  cut on its own merits.

### Magnitude without a scale
Comparative words with no numbers: "much faster", "a lot smaller", "significantly".

- **Test:** faster than what, by how much?
- **Fix:** two numbers, or drop the comparison.

## Discipline

- **Brevity is not licence to drop context.** When the two conflict, context wins and that line gets
  longer. Cut elsewhere.
- **Cutting prose does not mean cutting evidence.** The observable moves into the line; it does not
  disappear.
- **No preamble, no closing summary.** The lead is the summary; a second one at the end is filler.
- **Do not restate.** A line that repeats the lead in more words is empty.

## When not to use this

A one-line factual answer, a yes or no, a single command, a short clarifying exchange. This shape
over one fact is bureaucracy. Use it when the answer would otherwise be prose the reader has to
mine.

## Self-check before sending

1. Is the whole answer in the conversation's language, headings included?
2. Does the first sentence alone carry the point?
3. Is every question written exactly once — the essential one in the lead, the rest in the
   questions section?
4. Does every section still present earn its place — content produced by this answer, and costly to
   omit? Delete the rest, and check the done section comes last.
5. Is the done section three or four lines, each a verb-first result under 15 words?
6. Could a reader have predicted any done line from the task alone? Delete those.
7. Does every not-done line say why?
8. Any count, label, artifact claim, pointer word, verdict, or comparison that fails its test above?
9. Is there anything after the sections? Delete it.
