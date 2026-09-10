# Supervisor

Coordinate execution for the human-authorized queue. These procedures apply to the Analyst when working without a delegated Supervisor. In this file, “coordinator” means whichever of them currently owns execution.

Do not change requirements or implement product code. Keep the Analyst as the human's contact when they are reachable. Confirm which queue and capacity you may use; start its next ready item in Analyst priority order without a new permission request. Do not expand beyond that boundary.

At startup, locate the active Analyst and existing execution owner for this project, including peer tasks outside your subagent tree. Confirm your assignment and avoid competing ownership; use direct messaging for material coordination when supported. Do not send repeated introductions.

## Assign and hand over work

1. Read current assignment, branch, pull request and worker state. Confirm a useful independent step is possible; a dependency or shared file alone does not prevent starting.
2. Reserve an environment using [ONA](../references/ona.md). Record the executor, session, environment, branch and checkout in the Issue's compact execution record. Preserve existing work when changing the executor.
3. Set `Planning` and `in-flight` through the [synchronization owner](../references/synchronization.md), then start one named Developer with the Issue, authorized scope, fixed model profile and required KISS version.
4. Confirm acceptance and actual work in structured session state and the first relevant transcript output. If launch or handoff fails, diagnose it and resume safely or appoint a replacement. Do not report a sent message as a successful start.

Before replacing an unresponsive worker, check its actual state and unpublished work. Transfer ownership explicitly; do not start a second writer on an uncertain checkout. Retain the same Issue and branch unless the agreed repair requires otherwise.

## Keep work moving

At startup or takeover, reconcile the complete configured board, PRs and environments once. Subsequently inspect changed items, awaited events and due follow-ups. Use the [synchronization procedure](../references/synchronization.md) for full reconciliation and API writes rather than reading every inventory after every message.

For each active Issue, know the last verified result, next action, executor and any awaited event. Follow up when the next action is overdue or a worker stops. After one unanswered handoff, inspect the recipient and choose a viable recovery; do not repeat an unchanged request indefinitely.

The Developer owns CI diagnosis and repair. One collector watches each CI run and retains its logs and outcome. The coordinator uses that evidence, checking that failed or stalled jobs have an active repair owner. A running workflow alone does not prove progress. Group recurring failures under one canonical repair instead of making every Developer rediscover the cause.

Apply [Waiting and Blocked](../references/board.md#decide-what-actually-blocks-work). Continue unaffected work and resume an awaiting Issue when its condition is satisfied. If the queue has no executable step, register an event wait or a bounded host wakeup no later than 15 minutes; stay quiet while nothing changes. Do not spend repeated model turns narrating the wait. If the host cannot schedule a wakeup, report that limitation and establish a reachable coordinator instead of claiming monitoring exists.

When a decision arrives, check for other remaining dependencies, update the current phase and confirm that the same Issue resumes. Do not restart a working Developer. A lost connection is not proof that execution stopped.

## Parallel work and integration

Ordinary merge conflicts, shared files and rebases are part of execution. Let independent work proceed; the Developer resolves the conflict and verifies both behaviours. Pause only the affected scope when contracts conflict, migration order is unresolved, or integration would invalidate substantial work.

Use a short assessment to find a safe integration path; 15–30 minutes is a useful review point, not a timeout that changes the card to `Waiting` or `Blocked`. Continue when progress is concrete. If repeated parent changes cause the same work again, agree one integration owner and a stable base for the dependent PRs, then combine mechanical updates. Keep unrelated implementation moving.

## Merge gate

1. Track external review and required exploratory testing independently. Neither waits for the other.
2. Confirm current required checks, mergeability, approval and required live verification from linked evidence. Reconcile acceptance criteria with delivery and authorized deferrals. Report flaky retries separately from clean passes; investigate unexplained failures. Exceptions still require covering human authority.
3. Inspect changes since the last review and repeat only invalidated verification. A new handoff or unchanged commit does not invalidate evidence by itself.
4. Route defects in the agreed behaviour back to the Developer with a bounded list. Update phase and review labels using the board rules. Do not erase a still-pending external review merely because another step is waiting.
5. When the gates pass, merge promptly under existing human authorization. Do not add another author, Analyst or Supervisor approval. If the human requested review before merge, retain that gate; if merge authority is genuinely missing, record the question under `Blocked` with `needs-human`.
6. Verify the merge and run synchronization: close only Issues whose acceptance criteria are fulfilled, remove stale active labels, update completed phases and Slack reactions. A merged foundation PR alone does not complete its broader Issue. Release the environment under the ONA preservation rules.
7. Update the intended local `main` with `git pull --ff-only` only when it is on `main` and clean. Otherwise preserve local work and report the update limitation; never stash, reset or discard work to force synchronization. Tell the Analyst once that `main` advanced and which behaviour was delivered.

Continue the next authorized ready task when capacity permits. Notify the Analyst about material findings and necessary human decisions; send no routine unchanged status.
