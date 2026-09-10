# Synchronize delivery state

GitHub, the Project, worker state and the review channel describe different facts. Keep them consistent through one named synchronization owner for the queue. The coordinator owns this responsibility until they explicitly hand it to an available process or executor. This owner writes phases, labels, native links and Slack messages/reactions. Issue requirements and decisions remain authored by the Analyst, while implementation evidence remains authored by the Developer. Other agents supply changed evidence rather than independently writing the projected state.

## Collect once, react to changes

Use a script or API integration for deterministic copying and comparisons when available. Prefer GitHub events and CI completion watches, with a full reconciliation at startup, takeover and at a configured interval no longer than 15 minutes. Consume changed records between those checks. A quiet scheduled read does not require a model turn. Wake the coordinator for a discrepancy, failed action, due follow-up or newly executable task. When the queue has no executable step, register an event wait or host wakeup no later than 15 minutes; stay quiet while nothing changes.

This skill defines the procedure; it does not install a webhook listener or scheduler. Verify that the chosen mechanism exists and runs. If none is available, the named coordinator performs reconciliation with available tools and registers a host wakeup. If the host cannot schedule a wakeup, report the limitation and establish a reachable coordinator; do not claim unattended monitoring exists. Do not have Analyst, Supervisor and Developer each poll the same unchanged CI run.

A configured model may help classify an ambiguous description. It must not decide acceptance, infer missing approval or invent dependency links. Route such questions to the delivery owner with the source evidence.

## Reconcile facts

1. Resolve the configured repository and Project, including all pages. Read current native Issue–PR links, PR head/base, draft state, reviews, required checks, merge state and worker evidence. Do not infer active implementation from a label, recent comment or the existence of a PR.
2. Link a PR natively through GitHub Development when its scope implements the Issue. Record real blocking relationships natively as well. Verify the actual relation after writing; a URL in an Issue body is not equivalent. A PR that provides only a foundation does not complete the broader Issue.
3. Compute the phase using [board rules](board.md#status), the execution record and current evidence. Preserve an unresolved human decision or a valid Waiting condition; a PR event alone must not overwrite them. Review approval, successful CI, merge and deployment are separate facts. Unknown or unavailable checks remain unknown.
4. Update stale status and apply the [label rules](board.md#labels) through the one writer. Read them back and check for GitHub automation side effects. Recompute from current evidence if another actor changed the item; never blindly restore a stale snapshot over newer work.
5. Close an Issue only when its own acceptance criteria are complete, accounting for authorized deferrals and, for grouping Issues, relevant children. A foundation PR or one child merge is not proof. Remove stale status text, update completed phases and retain detailed verification in the PR.

Before adding or reordering board options, preserve existing option IDs and item values. If the host API cannot do this safely, keep task data intact and report the exact configuration action needed; do not replace the entire option list speculatively.

## Review channel

Use only a channel and posting authority established by the human or project configuration. If no channel is configured, continue GitHub reconciliation and report the missing review-channel setting. Do not guess a similarly named channel or send direct messages without authorization.

Before posting, verify the [Code review entry condition](board.md#code-review-entry-condition) against the current PR revision. Publish only non-draft PRs with all required CI/CD checks green. A review request or a card already in `Code review` is not proof of readiness. If the entry condition stops holding after publication, correct the existing message to show that readiness was withdrawn; do not post another review request until the condition passes again.

Post each eligible PR as its own message, with a short human-readable purpose and link. Search for an existing message for that exact repository and PR before posting. Keep its channel/message ID mapping in integration metadata. PR descriptions should explain the problem, resulting behaviour and verification in at most ten sentences unless a repository template or essential requirement needs more.

Use the channel's established emoji for approval and merge. Verify the convention from existing messages; if ambiguous, report it rather than assigning a new meaning. Reconcile reactions against current GitHub state, including dismissed approvals and reopened work. Remove only stale reactions owned by the integration; preserve human reactions. For an older message containing several PRs, use an aggregate reaction only if it is true for every linked PR, and flag ambiguous existing markings.

## Safe retries and ownership

Store processed event IDs or equivalent deduplication keys and the last verified source revision. Re-read current state for delayed or out-of-order events. Repeating a sync must not duplicate messages, links or comments.

Transfer write ownership and the message mapping explicitly. Before retrying an uncertain write, read its result; for Slack, look for the exact message before reposting. On rate limits or transient errors, use the provider's retry guidance and retain the pending action. Do not run a tight retry loop or ask a large model to restate the unchanged failure.

Record the affected item, attempted operation and next retry when synchronization fails. A synchronization failure does not by itself block unrelated implementation or prove that a PR's checks failed. The coordinator repairs synchronization and verifies the actual state before reporting success.
