---
name: clean-ai-text
description: Cleans up any text written by AI - documentation, notes, README files, agent instructions. Removes repetition, filler and contradictions, and makes the text understandable on its own. Use when the user wants text tidied, tightened, or made readable without losing meaning.
---

Follow `references/simple-talk.md` for how the cleaned text must sound.

# Input

The text or files the user names. If none is named, ask which text to clean.

# Analyse before editing

Read the whole text first. State what it is for and who reads it. Report what you found wrong before changing anything, and agree the direction with the user when the text is long or the problems are structural.

# Clean

1. Consistency - one term for one thing, one voice, one level of detail. Resolve statements that disagree with each other.
2. Repetition - say each thing once, in the place where it is needed.
3. Filler - remove words and sentences that carry no information. Keep a word only when removing it would change the meaning, the required action, or the outcome.
4. Conflicting instructions - when two rules cannot both be followed, keep the one the text needs and delete the other. If the choice belongs to the user, present both and ask.
5. Progressive disclosure - when the text is long, keep a short main document and move the detail into separate files it links to. This can repeat inside those files.
6. Standalone reading - the result must make sense to someone who reads it alone, with no other context. Remove references to earlier conversations, previous versions, problems that happened, and changes that were made.

Prefer deleting over rewriting. Change a sentence only when deleting part of it is not enough.

# Verify

Run a verification subagent that compares the original text with the cleaned one and lists anything that lost meaning: a rule, a constraint, a decision, an exact name, a path, or a format. Give the subagent both texts only - no other project files - so its judgement stays independent.

Fix everything it finds. Repeat until it finds nothing.

# Report

Tell the user what was removed, what was merged, what moved into separate files, and anything you chose to keep that looked redundant but was not.
