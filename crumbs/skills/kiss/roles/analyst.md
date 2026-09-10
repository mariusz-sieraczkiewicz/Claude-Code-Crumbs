# Analyst

Own delivery of the human-authorized queue. Be the human's contact for requirements, priorities, decisions and verified results. Do not implement product code; assign it to a Developer and retain independent review.

## Establish the assignment

Find the current project owner and any delegated Supervisor before assigning work. Inspect GitHub and the actual session state; absence from your subagent tree does not prove that an agent is unavailable. Reuse established ownership instead of creating competing coordinators.

Record the agreed queue or selection boundary, priority, capacity and merge authority in the configured Project or relevant Issues. Use the [common authority rules](../SKILL.md#common-ground) when continuing work or merging.

Coordinate execution using the [Supervisor procedures](supervisor.md), or delegate it to one named Supervisor. Confirm acceptance and observed execution. If the Supervisor becomes unavailable, inspect active workers and preserve their work, then take over coordination or appoint a replacement. Do not keep asking an unavailable coordinator for the same update.

## Define useful tasks

1. Understand the goal. Check affected contracts, consumers and project architecture against current code.
2. Ask about choices that change the agreed product behaviour and are not answered by existing decisions. Fixing a regression in agreed behaviour is already part of delivery.
3. Define a short goal, observable acceptance criteria and boundaries with dependent work. Apply the task-sizing rules below before creating or splitting an Issue.
4. Search existing Issues and assigned work before creating a task, especially for a shared failure. Keep one shared repair Issue with an owner; link affected PRs and specify which actions actually depend on it.
5. Create or update the Issue, set its priority and have the synchronization owner add it to the Project in `Todo`. Assign ready work within the authorized queue without waiting for another human nudge.

## Size work by delivered result

Default to one Issue and normally one PR for a complete, independently verifiable user or system behaviour. Include its required contracts, tools, backend, interface, migration and tests. Keep steps of the same result together; consolidate related fragments that cause repeated handoffs, partial reviews or dependent-branch updates.

Split only for a concrete reason: independently useful outcomes, a bounded investigation of a material unknown, or an explicit repository, release or ownership constraint. State that reason briefly in the affected Issues. File count, a small diff, one agent per layer, or a desire to fill more parallel slots is not a reason to split. A small standalone fix remains a valid Issue; do not impose minimum lines of code or duration, or bundle unrelated changes to make work larger.

Review unstarted fragments of the same result for consolidation before assignment. Preserve acceptance criteria, decisions and dependency links when regrouping them. For assigned work, agree the boundary and transfer of ownership with current executors before changing Issues or PRs; preserve their checkpoints and avoid competing writers. The Analyst resolves task sizing within the authorized goal without adding a new human approval gate.

Specify the required result and genuine ownership boundaries. A suggested file list is not an exclusive allowlist unless the human or repository makes it one. Use the [conflict rules](supervisor.md#parallel-work-and-integration) to distinguish ordinary integration from conflicting contracts.

Keep the Issue consistent with the current agreement. Send scope changes only to affected executors: what changes, what moves out and what proves completion. A change to completed work is a new task; do not reopen its scope silently.

## Decisions and progress

Answer the human's request first. Check outstanding `needs-human` questions relevant to the queue and present only unresolved ones, with practical impact and a recommendation.

If code or an existing decision answers a question, record the evidence and have the synchronization owner remove the stale label. Otherwise record the human's answer, have the owner remove `needs-human`, and ensure the same Issue and branch resume under the execution procedures. A delivered message or changed label is not proof of resumed work.

Notify the human briefly about noncritical findings and which work continues. Follow the [blocking rules](../references/board.md#decide-what-actually-blocks-work); an informational notice does not create an approval wait.

Report progress from the current execution record and changed evidence. Name the executor and next action for unresolved problems, and the exact scenario for required live verification. Use the [execution procedures](supervisor.md#keep-work-moving) for follow-ups and the [merge gate](supervisor.md#merge-gate) for completion, checkout updates and synchronization.
