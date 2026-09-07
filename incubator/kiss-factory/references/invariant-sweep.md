# Sweep an invariant before paying for verification

Most changes are local. Some change a promise that must remain true across several components. The
danger in those tasks is not one difficult edit; it is an affected path nobody classified.

Use this reference only for that second kind of work. The invariant comes from the issue and the
repository. Authorization, lifecycle, idempotency and transaction boundaries are examples, not a
closed list.

## Before implementation

State the invariant in one sentence. Then derive an impact map from the code and acceptance criteria:
every path that can observe or change the state governed by that invariant. Account for each path as
changed here, already protected, or outside the issue with a reason.

The map has no prescribed columns or catalogue of surfaces. Its form follows the system being
changed. What makes it complete is evidence from this repository and the absence of an unclassified
path, not resemblance to a previous task.

Run focused checks while the map or known findings are still changing. Pay for the full verification
suite after there are no known unclassified paths.

## During review

Reconstruct the affected paths independently from the issue, base and diff. Check the map's
completeness before checking how well each row was implemented. Complete the sweep before publishing
the review's single set of findings; finding one violation is a reason to widen the search, not to
end it.

## During repair

A missed path to an already-mapped invariant is a local repair. A second missed path is evidence that
the map was wrong. Stop patching paths one at a time, rebuild the whole map from the repository, and
batch the resulting repair before another full verification run.

This escalation is about repeated misses to the same invariant. An unrelated finding does not turn a
local change into a system-wide audit.
