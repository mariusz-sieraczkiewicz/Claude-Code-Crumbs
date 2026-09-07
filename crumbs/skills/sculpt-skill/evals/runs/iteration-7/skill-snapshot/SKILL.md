---
name: sculp-skill
description: Sculpting skill means remove everething and leave only essence in which removing anything will break the skill outcome. Use when user wants make skill crystal clean.
---
# Important
Don't use skill-creator skill together with sculp-skill - it may be counterproductive.

# Ground rules
1. Always work on skill copy - suffix them with the next version <skill-name>-v1, -v2 ...

2. Split work into subagents when possible to make work more performant and not to clutter the context window.

3. The aim is to have skill that:
* is minimalistic - means you cannot remove anything there without changing what the skill produces or way of reasoning. In practice it means you must remove repetitions, reassurances and things the model already knows.
* easy to understand for the human - no jargon, empathetically take into account that human may not know what you know
* is final snapshot - does not have reference to previous version, mentioning modification strategies, refering to any discussion or thinking process
* declarative - don't try do describe things in details, especially when llm model quite likely has all needed knowledge. Describe rules when they are very specific to the described problem, not being known facts

4. Make changes surgical - when possible prefer minimal changes or removing sentences or parts of sentences to rewriting or rephrasing.

5. Apply progressive disclosure for more complex skills - instead of having one big skill, create a skeleton in main file and reference steps as separate reference files. This rules may apply recursively.

# Writing rules

More specifically: write the human skill in this order and follow these patterns.

## Frontmatter

```yaml
---
name: review-proposal
description: Reviews a proposal against project requirements. Use when a proposal must be accepted, revised, or escalated.
metadata:
  workspace: ./.review-proposals/<timestamp-id>
---

Read first and follow rules defined in `references/runtime.md` file. They define context and definitions for implicit assumptions in the skill.
```

Rules:

- `description` states **what the skill does** and **when to use it**.
- Saving the result to a file requires a `workspace`.
- Define types in `./scripts/contracts.py`; do not describe fields in the skill body.
- Copy `runtime.md` file to target `references/runtime.md` skill file - it describes conventions and implicit rules.
- The example shows syntax, not a checklist. Eg. workspace is an optional declaration which original skill should have declared in metadata or mentioned in text to have defaults redefined in sculpted skill.


## Beginning (input data) and end (output data)

### Input
Declare input typed data at the beginning of the skill file.
Input (→ `ReviewContext`) 
or for more inputs
Input (request → `ReviewContext`, policy → ReviewPolicy(`policy.yaml`))

### Output
Declare output typed data at the end of the skill file.
Output (→ ReviewResult(`review-result.yaml`))

## Prefer semantic compression

Express each responsibility with the smallest concept that preserves its effect.

Remove details that require no distinct treatment. Split content only when its
parts lead to different decisions, actions, or results.

Do not split one responsibility into artificial micro-steps.

Do not enumerate examples of possible actions or consequences that imposed.

Name the concept that governs the rule especially when llm model quite likely know it from internal knowledge.

## Declare the stage result at the end

```markdown
(→ `ReviewContext`)
```

Do not describe how the result is serialized, stored, or transferred.

## A subagent needs a role, task, data, and result

```markdown
Subagent: Evidence Reviewer (→ `EvidenceReview`)

Using the review context, check whether every proposal claim is supported by
available evidence. Identify unsupported claims and missing evidence.
```

“Review the proposal” is insufficient. State what the reviewer must verify and identify.

## Declare parallel work before the subagents

```markdown
Review the proposal using these two subagents in parallel:

Subagent: Evidence Reviewer (→ `EvidenceReview`)

Check whether every material claim is supported.

Subagent: Policy Reviewer (→ `PolicyReview`)

Check whether the proposal satisfies every applicable policy requirement.
```

Do not encode parallelism through nested lists or special syntax.

## Every **domain** decision needs complete branches

```markdown
Decide from the evidence and policy reviews:

- If every applicable requirement is satisfied, accept the proposal.
- If identified issues can be corrected without participant judgment, revise it.
- If two materially different valid outcomes remain, present both outcomes and ask the participant to choose.
- If a required source is unavailable, report it and stop without producing the official result.
```

For every branch, specify:

- the condition,
- the permitted action,
- whether the workflow continues,
- whether the official result is produced.

## A question to a person must identify the exact decision

```markdown
Present the conflicting requirements, the evidence supporting each option, and
the consequence of each choice.
```

Do not merely write “ask the user for clarification.”

## A loop needs a limit and exit conditions

```markdown
Run at most 3 revision–review iterations.

After each review:

- If all requirements are satisfied, produce the final result.
- If iteration 3 is complete, record every unresolved issue and finish.
- Otherwise, revise the proposal and review it again.
```

## For sources, define availability and coverage

```markdown
Review every enabled required source and account for each source in the review.

If a required source is unavailable, report which source is unavailable and
stop without producing a result.

If an optional source is unavailable, record the missing coverage and reduce
the confidence of the assessment.
```

## Exact operations and interpretive work must sound different

A deterministic operation:

```markdown
Read `policy.yaml`.
```

Work requiring judgment:

```markdown
Inspect the available policies and determine which one governs the request.
```

The first instruction specifies the exact operation and target. The second requires interpretation by an agent.

## Do not ever directly refer to contract type fields

Its meaning, role and usage should be natural consequence of type definition. Add Pydantic description if needed to describe things not derivebale from the name of the field.

Instead of field references use human language counterparts.

# Report

Generate report what was shortened, deleted, modified (rephrased) oraz saved in typed contract in yaml file.

# Verification
At the end run Verification subagent to check if new version of skill conforms # Ground rules and # Writing rules. During the verification use original skill contents. But instruct subagent not to look to other files eg. in project dir to retain objectivity in context window. Update modification report.


Run Fixer subagent if issues found. Repeat until no issues.