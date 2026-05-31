#!/usr/bin/env bash
set -euo pipefail

# verify-gate-artifacts.sh
# Hard gate: verifies that /003 and /004 artifacts exist with status: ok
# before allowing a command to report success.
#
# Usage:
#   ./verify-gate-artifacts.sh --epic <epic-id>
#   ./verify-gate-artifacts.sh --epic <epic-id> --feedback-round <round-id>
#
# Exit codes:
#   0 = all artifacts present and ok
#   1 = missing or failed artifact (prints which one)
#   2 = usage error

EPIC_ID=""
FEEDBACK_ROUND=""
MODE="epic"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --epic) EPIC_ID="$2"; shift 2 ;;
    --feedback-round) FEEDBACK_ROUND="$2"; MODE="feedback"; shift 2 ;;
    *) echo "Usage: verify-gate-artifacts.sh --epic <epic-id> [--feedback-round <round-id>]" >&2; exit 2 ;;
  esac
done

if [[ -z "$EPIC_ID" ]]; then
  echo "Error: --epic is required." >&2
  exit 2
fi

RUNS_DIR=".claude/runs/${EPIC_ID}"

if [[ ! -d "$RUNS_DIR" ]]; then
  echo "GATE FAIL: Runs directory not found: $RUNS_DIR" >&2
  exit 1
fi

check_artifact() {
  local path="$1"
  local label="$2"

  if [[ ! -f "$path" ]]; then
    echo "GATE FAIL: $label artifact not found at: $path" >&2
    echo "Run the corresponding gate command before reporting success." >&2
    return 1
  fi

  local status
  status=$(jq -r '.status // empty' "$path" 2>/dev/null)
  if [[ "$status" != "ok" ]]; then
    echo "GATE FAIL: $label artifact has status '$status' (expected 'ok') at: $path" >&2
    return 1
  fi

  echo "GATE OK: $label — status: ok ($path)"
  return 0
}

FAILED=0

if [[ "$MODE" == "feedback" ]]; then
  # Feedback round mode: check 05c-verify.json and 05d-review.json
  ROUND_DIR="${RUNS_DIR}/_feedback/${FEEDBACK_ROUND}"

  if [[ ! -d "$ROUND_DIR" ]]; then
    echo "GATE FAIL: Feedback round directory not found: $ROUND_DIR" >&2
    exit 1
  fi

  check_artifact "${ROUND_DIR}/05c-verify.json" "/003-verify-dod (feedback round)" || FAILED=1
  check_artifact "${ROUND_DIR}/05d-review.json" "/004-code-review (feedback round)" || FAILED=1

else
  # Epic mode: check 03-verify-epic.json and 04-review-epic.json
  check_artifact "${RUNS_DIR}/03-verify-epic.json" "/003-verify-dod (epic)" || FAILED=1
  check_artifact "${RUNS_DIR}/04-review-epic.json" "/004-code-review (epic)" || FAILED=1
fi

if [[ "$FAILED" -eq 1 ]]; then
  echo "" >&2
  echo "Cannot report success — gate artifacts are missing or failed." >&2
  echo "Run /003-verify-dod and /004-code-review, then retry." >&2
  exit 1
fi

echo ""
echo "All gate artifacts verified. Safe to report success."
exit 0
