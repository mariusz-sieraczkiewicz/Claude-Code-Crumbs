#!/usr/bin/env bash
set -euo pipefail

# archive-epic-runs.sh
# Move .claude/runs/<epic-id>/ -> .claude/runs-archive/<epic-id>-<UTC-timestamp>-<hex4>.tar.gz
# Usage: ./archive-epic-runs.sh <epic-id>   (e.g. E-001)

usage() {
    cat >&2 <<EOF
Usage: $(basename "$0") <epic-id>

  <epic-id>   Epic identifier matching ^E-[0-9]{3}$ (e.g. E-001).

Archives .claude/runs/<epic-id>/ to .claude/runs-archive/<epic-id>-<UTC>-<hex4>.tar.gz
EOF
}

if [ "$#" -ne 1 ]; then
    usage
    exit 2
fi

EPIC_ID="$1"

# Validate epic id format
if ! printf '%s' "$EPIC_ID" | grep -Eq '^E-[0-9]{3}$'; then
    echo "Error: epic-id '$EPIC_ID' does not match ^E-[0-9]{3}\$" >&2
    usage
    exit 2
fi

SRC_DIR=".claude/runs/${EPIC_ID}"
ARCHIVE_DIR=".claude/runs-archive"

# If source does not exist, nothing to archive — surface as an error so callers
# don't silently believe the archive succeeded.
if [ ! -d "$SRC_DIR" ]; then
    echo "Error: nothing to archive — ${SRC_DIR}/ does not exist." >&2
    exit 1
fi

mkdir -p "$ARCHIVE_DIR"

# Acquire POSIX-atomic lock via mkdir.
LOCK_DIR="${ARCHIVE_DIR}/.lock.${EPIC_ID}"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "Another archive in progress for ${EPIC_ID}. Wait or remove ${LOCK_DIR}." >&2
    exit 3
fi

# Ensure lock is removed on any exit.
cleanup() {
    rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Source-stable checksum helper. Lists files sorted then hashes concatenated content.
compute_checksum() {
    # shellcheck disable=SC2016
    ( cd "$1" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 cat 2>/dev/null | shasum -a 256 | awk '{print $1}' )
}

CHECKSUM_BEFORE="$(compute_checksum "$SRC_DIR")"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
HEX4="$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n' | cut -c1-4)"
ARCHIVE_PATH="${ARCHIVE_DIR}/${EPIC_ID}-${TIMESTAMP}-${HEX4}.tar.gz"

# Create archive (BSD + GNU tar compatible). -C avoids leading path components.
tar -czf "$ARCHIVE_PATH" -C ".claude/runs" "$EPIC_ID"

# Verify archive integrity before deleting source.
if ! tar -tzf "$ARCHIVE_PATH" >/dev/null 2>&1; then
    echo "Error: archive integrity check failed for $ARCHIVE_PATH" >&2
    rm -f "$ARCHIVE_PATH"
    exit 1
fi

# Re-check source stability — abort if anything changed under SRC_DIR while archiving.
CHECKSUM_AFTER="$(compute_checksum "$SRC_DIR")"
if [ "$CHECKSUM_BEFORE" != "$CHECKSUM_AFTER" ]; then
    echo "Error: source ${SRC_DIR} changed during archive (checksum mismatch). Source preserved." >&2
    echo "  before: ${CHECKSUM_BEFORE}" >&2
    echo "  after:  ${CHECKSUM_AFTER}" >&2
    rm -f "$ARCHIVE_PATH"
    exit 4
fi

rm -rf "$SRC_DIR"

if [ -d "$SRC_DIR" ]; then
    echo "Error: failed to remove ${SRC_DIR} after archive. Archive at ${ARCHIVE_PATH} is intact." >&2
    exit 3
fi

echo "Archived ${EPIC_ID} -> ${ARCHIVE_PATH}"
