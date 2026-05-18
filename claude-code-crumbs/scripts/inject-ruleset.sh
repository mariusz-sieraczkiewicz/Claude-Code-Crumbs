#!/bin/sh
set -eu

# inject-ruleset.sh
# Concatenate <ruleset>/*.md into a single string for subagent injection.
# Each file is prefixed with: --- <filename without extension> ---
# Usage: ./inject-ruleset.sh   (no args)
#
# Ruleset directory resolution order:
#   1. .claude/stack.yaml -> paths.ruleset (if present)
#   2. .claude/ruleset (default fallback)

DEFAULT_RULESET_DIR=".claude/ruleset"
STACK_YAML=".claude/stack.yaml"

RULESET_DIR=""

# Minimal POSIX YAML extraction: find `paths:` block, then a `ruleset:` sub-key.
# We accept either flow style under paths or block style indented sub-keys.
if [ -f "$STACK_YAML" ]; then
    RULESET_DIR="$(
        awk '
            BEGIN { in_paths = 0; paths_indent = -1 }
            # Strip CR for CRLF files.
            { sub(/\r$/, "") }
            # Skip full-line comments.
            /^[[:space:]]*#/ { next }

            # Inline flow form: paths: { ruleset: "x", ... }
            /^[[:space:]]*paths:[[:space:]]*\{.*ruleset:/ {
                line = $0
                sub(/.*ruleset:[[:space:]]*/, "", line)
                # Trim trailing , or } and anything after.
                sub(/[,}].*$/, "", line)
                # Trim spaces first so quote-strip can match end-of-string quote.
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
                # Strip surrounding quotes.
                gsub(/^["'\'']|["'\'']$/, "", line)
                # Trim again in case quotes had internal padding.
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
                print line
                exit
            }

            # Block form: detect `paths:` on its own (value empty or trailing comment).
            /^[[:space:]]*paths:[[:space:]]*(#.*)?$/ {
                in_paths = 1
                match($0, /^[[:space:]]*/)
                paths_indent = RLENGTH
                next
            }

            in_paths == 1 {
                # Compute indent of current line.
                match($0, /^[[:space:]]*/)
                cur_indent = RLENGTH
                # Empty line: continue scanning within block.
                if ($0 ~ /^[[:space:]]*$/) { next }
                # Left the paths block when indent <= paths_indent.
                if (cur_indent <= paths_indent) { in_paths = 0; next }
                # Look for `ruleset: <value>` inside the block.
                if ($0 ~ /^[[:space:]]*ruleset:/) {
                    line = $0
                    sub(/^[[:space:]]*ruleset:[[:space:]]*/, "", line)
                    # Strip trailing inline comment.
                    sub(/[[:space:]]+#.*$/, "", line)
                    # Strip quotes.
                    gsub(/^["'\'']|["'\'']$/, "", line)
                    # Trim spaces.
                    gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
                    print line
                    exit
                }
            }
        ' "$STACK_YAML"
    )"
fi

# Strip trailing slashes (portable).
while :; do
    case "$RULESET_DIR" in
        */) RULESET_DIR="${RULESET_DIR%/}" ;;
        *)  break ;;
    esac
done

if [ -z "$RULESET_DIR" ]; then
    RULESET_DIR="$DEFAULT_RULESET_DIR"
fi

if [ ! -d "$RULESET_DIR" ]; then
    echo "No ruleset found at ${RULESET_DIR}. Run /000-prd-refine first." >&2
    exit 2
fi

# Count *.md files (alphabetical order via shell glob).
# Use a portable approach to detect empty directory without bash arrays.
COUNT=0
for f in "$RULESET_DIR"/*.md; do
    [ -e "$f" ] || continue
    COUNT=$((COUNT + 1))
done

if [ "$COUNT" -eq 0 ]; then
    echo "No ruleset found at ${RULESET_DIR}. Run /000-prd-refine first." >&2
    exit 2
fi

for f in "$RULESET_DIR"/*.md; do
    [ -e "$f" ] || continue
    base="$(basename "$f" .md)"
    printf -- '--- %s ---\n' "$base"
    cat -- "$f"
    printf '\n'
done
