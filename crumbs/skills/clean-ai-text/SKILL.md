---
name: clean-ai-text
description: Cleans up any text written by AI - documentation, notes, README files, and instruction sets such as skills, commands, prompts and agent role files. Removes repetition, filler and contradictions, splits long text into files read on demand, and makes the result understandable on its own without dropping a single rule. Use when the user wants text tidied, tightened, restructured, or made readable without losing meaning.
---

Follow `references/simple-talk.md` for how the cleaned text must sound.

# Input

The text or files the user names. If none is named, ask which text to clean. When a named file links to others that carry its rules, the whole set is the input.

# Do not change what the text requires

Every rule, permission, prohibition, threshold, exact name, path, command and output format that held before must still hold after. Fewer words, same meaning.

# Analyse before editing

Read the whole text first, including the files it links to. State what it is for and who reads it.

Write down every rule it states and where each one is stated. That list is what the verification at the end checks against; without it, deleting is guesswork.

Report what you found wrong before changing anything, and agree the direction with the user when the text is long or the problems are structural. Ask one question at a time.

# Clean

1. Consistency - one term for one thing, one voice, one level of detail. Resolve statements that disagree with each other. A term used before it is explained is a defect.
2. Repetition - say each thing once, in the place where it is enforced, and link to it from anywhere else that needs it. Two copies of a rule drift apart, and then the reader cannot tell which one is current.
3. Filler - remove words and sentences that carry no information. Keep a word only when removing it would change the meaning, the required action, or the outcome.
4. Conflicting instructions - when two rules cannot both be followed, keep the one the text needs and delete the other. If the choice belongs to the user, present both and ask.
5. Progressive disclosure - when the text is long, keep a short main document and move the detail into separate files it links to, saying which file a reader must open and when. This can repeat inside those files.
6. Standalone reading - the result must make sense to someone who reads it alone, with no other context. Remove references to earlier conversations, previous versions, problems that happened, and changes that were made. Explain an abbreviation the first time it appears, or drop it.
7. Authority - when the text describes several people or agents, state each one's permissions and prohibitions once, in that actor's own section, without overlapping another's.

Prefer deleting over rewriting. Change a sentence only when deleting part of it is not enough.

Copy exact names, paths, commands, labels, formats and numbers character for character. Never add a rule that was not already there.

# Verify

Run a verification subagent that compares the original text with the cleaned one and lists anything that lost meaning: a rule, a constraint, a permission, a decision, an exact name, a path, a format or a threshold. Give the subagent both texts only - no other project files - so its judgement stays independent.

Fix everything it finds. Repeat until it finds nothing.

# Report

Tell the user what was removed, what was merged, what moved into separate files, and anything you chose to keep that looked redundant but was not.
