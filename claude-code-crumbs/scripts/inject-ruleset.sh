#!/bin/sh
set -eu

# inject-ruleset.sh
# Concatenate <ruleset>/*.md into a single string for subagent injection.
# Each file is prefixed with: --- <filename without extension> ---
#
# Usage:
#   ./inject-ruleset.sh                              # inject ALL rule files (default)
#   ./inject-ruleset.sh --rules <slug,slug,...>      # inject SUBSET of rule files
#
# Subset selection (`--rules`):
#   - <slug,slug,...> is a comma-separated list of rule basenames (no `.md`).
#   - Only rule files whose basename appears in the list are emitted, PLUS the
#     mandatory core set: architecture, testing, code-style, git-workflow.
#   - The mandatory core is ALWAYS included regardless of what `--rules` lists.
#   - Unknown slugs are silently ignored (the matching loop simply skips them).
#   - Omit `--rules` (or pass an empty value) to fall back to the original
#     "inject all" behaviour.
#
# Ruleset directory resolution order:
#   1. .claude/stack.yaml -> paths.ruleset (if present)
#   2. .claude/ruleset (default fallback)

DEFAULT_RULESET_DIR=".claude/ruleset"
STACK_YAML=".claude/stack.yaml"

# Mandatory core rules — always injected, regardless of `--rules` value.
# These rules are load-bearing for every implementation task:
#   - architecture:  layering / vertical-slice boundaries
#   - testing:       Step library, Worlds, TDD entry-point
#   - code-style:    formatting / lint baseline
#   - git-workflow:  branch, commit, and signing policy
MANDATORY_CORE="architecture,testing,code-style,git-workflow"

RULES_FILTER=""

# Parse args.
while [ $# -gt 0 ]; do
    case "$1" in
        --rules)
            shift
            if [ $# -eq 0 ]; then
                echo "Error: --rules requires a comma-separated slug list" >&2
                exit 2
            fi
            RULES_FILTER="$1"
            shift
            ;;
        --rules=*)
            RULES_FILTER="${1#--rules=}"
            shift
            ;;
        *)
            echo "Error: unrecognised argument: $1" >&2
            echo "Usage: $0 [--rules slug1,slug2,...]" >&2
            exit 2
            ;;
    esac
done

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

# Reject path traversal and absolute paths that escape project root.
case "$RULESET_DIR" in
    *..*)
        echo "Error: paths.ruleset must not contain '..' (got: $RULESET_DIR)" >&2
        exit 2
        ;;
    /*)
        echo "Error: paths.ruleset must be project-relative, not absolute (got: $RULESET_DIR)" >&2
        exit 2
        ;;
esac

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

# Build the effective allow-list when `--rules` was given.
# Format: leading + trailing commas so we can substring-match `,<slug>,` safely.
ALLOW_LIST=""
if [ -n "$RULES_FILTER" ]; then
    # Merge user-supplied slugs with the mandatory core.
    COMBINED="${RULES_FILTER},${MANDATORY_CORE}"
    # Sentinel commas at both ends to make `,<slug>,` matches unambiguous.
    ALLOW_LIST=",${COMBINED},"
fi

for f in "$RULESET_DIR"/*.md; do
    [ -e "$f" ] || continue
    case "$(basename "$f")" in
        -*)
            echo "Warning: skipping ruleset file with leading dash: $f" >&2
            continue
            ;;
    esac
    base="$(basename "$f" .md)"

    # If a filter is active, skip files whose basename is not in the allow-list.
    if [ -n "$ALLOW_LIST" ]; then
        case "$ALLOW_LIST" in
            *",${base},"*) : ;;  # included, fall through and emit
            *) continue ;;
        esac
    fi

    printf -- '--- %s ---\n' "$base"
    cat -- "$f"
    printf '\n'
done
