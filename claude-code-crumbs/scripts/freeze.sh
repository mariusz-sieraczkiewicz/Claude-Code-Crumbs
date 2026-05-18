#!/usr/bin/env bash
# freeze.sh
# Freeze preset-driven configuration into project-local commands and agents.
#
# Reads:
#   - .claude/stack.yaml                  (team_preset)
#   - .claude/ruleset/git-workflow.md     (YAML toggle block, ```yaml ... ```)
#   - .claude/ruleset/deployment.md       (YAML toggle block)
#
# For each plugin command/agent (commands/*.md, agents/*.md):
#   - Parse <!-- FREEZE:IF/ELIF/ELSE/ENDIF --> blocks
#   - Parse <!-- FREEZE:VAL <key> -->fallback<!-- FREEZE:ENDVAL --> inline subs
#   - Evaluate expressions against the resolver dictionary
#   - Write frozen output to .claude/commands/<name>.md and .claude/agents/<name>.md
#
# Files without any FREEZE markers are copied verbatim (creates a project-local override).
#
# Exit codes:
#   0  success
#   1  missing config
#   2  marker parse error
#   3  expression eval error
#   4  IO error
#   5  already-frozen-without-force

set -u
set -o pipefail

# -----------------------------------------------------------------------------
# Default plugin root. Override with --plugin-root=<path>.
# -----------------------------------------------------------------------------
DEFAULT_PLUGIN_ROOT="${HOME}/.claude/plugins/claude-code-crumbs"
PLUGIN_ROOT=""
DRY_RUN=0
FORCE=0
RESET=0

STACK_YAML=".claude/stack.yaml"
GIT_RULES=".claude/ruleset/git-workflow.md"
DEPLOY_RULES=".claude/ruleset/deployment.md"

OUT_COMMANDS=".claude/commands"
OUT_AGENTS=".claude/agents"

# -----------------------------------------------------------------------------
# Logging helpers.
# -----------------------------------------------------------------------------
err() { printf 'freeze: %s\n' "$*" >&2; }
info() { printf 'freeze: %s\n' "$*"; }

# -----------------------------------------------------------------------------
# Argument parsing.
# -----------------------------------------------------------------------------
parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --dry-run) DRY_RUN=1 ;;
            --force) FORCE=1 ;;
            --reset) RESET=1 ;;
            --plugin-root=*) PLUGIN_ROOT="${1#--plugin-root=}" ;;
            -h|--help)
                cat <<'EOF'
Usage: freeze.sh [--dry-run] [--force] [--reset] [--plugin-root=<path>]

  --dry-run         Print summary without writing.
  --force           Skip confirmation prompts (re-freeze, reset).
  --reset           Remove .claude/commands/ and .claude/agents/ and exit.
  --plugin-root=P   Override plugin source dir.
                    Default: ~/.claude/plugins/claude-code-crumbs

Scope is preset-driven: freeze resolves keys from .claude/ruleset/git-workflow.md
and .claude/ruleset/deployment.md (the active team_preset). Other dynamics
(extras, stack-level toggles) remain runtime.
EOF
                exit 0
                ;;
            *)
                err "unrecognised argument: $1"
                exit 2
                ;;
        esac
        shift
    done

    if [ -z "$PLUGIN_ROOT" ]; then
        PLUGIN_ROOT="$DEFAULT_PLUGIN_ROOT"
    fi
}

# -----------------------------------------------------------------------------
# Reset handler.
# -----------------------------------------------------------------------------
do_reset() {
    if [ ! -d "$OUT_COMMANDS" ] && [ ! -d "$OUT_AGENTS" ]; then
        info "nothing to reset (no $OUT_COMMANDS or $OUT_AGENTS)"
        exit 0
    fi
    if [ "$FORCE" -ne 1 ]; then
        printf 'freeze: remove %s and %s? [y/N] ' "$OUT_COMMANDS" "$OUT_AGENTS"
        read -r reply || reply=""
        case "$reply" in
            y|Y|yes|YES) : ;;
            *) info "aborted"; exit 0 ;;
        esac
    fi
    rm -rf "$OUT_COMMANDS" "$OUT_AGENTS" || { err "failed to remove frozen dirs"; exit 4; }
    info "reset: removed $OUT_COMMANDS and $OUT_AGENTS"
    exit 0
}

# -----------------------------------------------------------------------------
# YAML parsing.
#   parse_stack_preset <stack.yaml>  -> prints team_preset value (or empty).
#   parse_yaml_block <file>          -> prints `key=value` lines from the
#                                       first ```yaml ... ``` fenced block.
# -----------------------------------------------------------------------------
parse_stack_preset() {
    local f="$1"
    [ -f "$f" ] || return 0
    awk '
        { sub(/\r$/, "") }
        /^[[:space:]]*#/ { next }
        /^[[:space:]]*team_preset:[[:space:]]*/ {
            line = $0
            sub(/^[[:space:]]*team_preset:[[:space:]]*/, "", line)
            sub(/[[:space:]]+#.*$/, "", line)
            gsub(/^["'\'']|["'\'']$/, "", line)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
            print line
            exit
        }
    ' "$f"
}

check_yaml_fence_balanced() {
    # Returns 0 if the FIRST ```yaml fence has a matching closing ```.
    # Returns 1 if unterminated. Caller is responsible for exiting.
    local f="$1"
    [ -f "$f" ] || return 0
    local result
    result="$(awk '
        BEGIN { in_block = 0; closed = 0 }
        { sub(/\r$/, "") }
        in_block == 0 && /^[[:space:]]*```[[:space:]]*yaml[[:space:]]*$/ { in_block = 1; next }
        in_block == 1 && /^[[:space:]]*```[[:space:]]*$/ { closed = 1; exit }
        END { if (in_block == 1 && closed == 0) print "UNTERMINATED" }
    ' "$f")"
    [ "$result" != "UNTERMINATED" ]
}

parse_yaml_block() {
    # Extract the FIRST fenced ```yaml ... ``` block, then emit key=value pairs.
    # Lists are joined with commas. Multi-line literal scalars (|) are joined
    # with literal "\n" markers so the resolver can detect non-empty multilines.
    # NOTE: fence-balance pre-check happens in build_resolver — $(...) swallows
    # exit codes, so the check must run in the parent shell.
    local f="$1"
    [ -f "$f" ] || return 0
    awk '
        BEGIN { in_block = 0; pending_key = ""; pending_indent = -1; pending_buf = "" }
        { sub(/\r$/, "") }
        # Find first ```yaml fence.
        in_block == 0 && /^[[:space:]]*```[[:space:]]*yaml[[:space:]]*$/ {
            in_block = 1
            next
        }
        in_block == 1 && /^[[:space:]]*```[[:space:]]*$/ {
            if (pending_key != "") {
                print pending_key "=" pending_buf
                pending_key = ""; pending_buf = ""; pending_indent = -1
            }
            in_block = 0
            exit
        }
        in_block != 1 { next }
        # Skip comments only OUTSIDE a multi-line literal block. Inside a literal,
        # markdown headers (`## Summary`) are content, not comments.
        pending_key == "" && /^[[:space:]]*#/ { next }
        /^[[:space:]]*$/ {
            # Blank line: inside a literal block, preserve as an empty line in
            # pending_buf. Outside a literal, skip.
            if (pending_key != "") {
                if (pending_buf == "") pending_buf = ""
                else pending_buf = pending_buf "\\n"
            }
            next
        }

        {
            # Compute indent.
            match($0, /^[[:space:]]*/)
            cur_indent = RLENGTH

            # If we are collecting a multi-line literal block, keep until indent <= start.
            if (pending_key != "") {
                if (cur_indent > pending_indent) {
                    s = $0
                    sub(/^[[:space:]]+/, "", s)
                    if (pending_buf == "") pending_buf = s
                    else pending_buf = pending_buf "\\n" s
                    next
                } else {
                    print pending_key "=" pending_buf
                    pending_key = ""; pending_buf = ""; pending_indent = -1
                    # Fall through and process current line as a fresh key.
                }
            }

            # Match "key: value" (only top-level toggles; nested keys not extracted).
            if (match($0, /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*:[[:space:]]*/)) {
                kv = $0
                key_match = $0
                # Extract key.
                sub(/[[:space:]]*$/, "", key_match)
                # Take up to the first colon.
                idx = index(key_match, ":")
                key = substr(key_match, 1, idx - 1)
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
                # Extract value.
                val = substr($0, idx + 1)
                sub(/^[[:space:]]+/, "", val)
                # Strip trailing inline comment (best effort: " #...").
                sub(/[[:space:]]+#.*$/, "", val)
                # Strip trailing spaces.
                sub(/[[:space:]]+$/, "", val)

                # Multi-line literal indicator.
                if (val == "|" || val == "|-" || val == "|+" || val == ">" || val == ">-" || val == ">+") {
                    pending_key = key
                    pending_indent = cur_indent
                    pending_buf = ""
                    next
                }

                # Flow list: [a, b, c].
                if (val ~ /^\[.*\]$/) {
                    inner = val
                    sub(/^\[/, "", inner)
                    sub(/\]$/, "", inner)
                    # Strip quotes around individual items, normalise spaces.
                    n = split(inner, parts, ",")
                    out = ""
                    for (i = 1; i <= n; i++) {
                        item = parts[i]
                        gsub(/^[[:space:]]+|[[:space:]]+$/, "", item)
                        gsub(/^["'\'']|["'\'']$/, "", item)
                        if (out == "") out = item
                        else out = out "," item
                    }
                    print key "=" out
                    next
                }

                # Strip surrounding quotes from scalar.
                gsub(/^["'\'']|["'\'']$/, "", val)

                print key "=" val
                next
            }
        }
        END {
            if (pending_key != "") {
                print pending_key "=" pending_buf
            }
        }
    ' "$f"
}

# -----------------------------------------------------------------------------
# Resolver dictionary. Stored as RES_<KEY>=<value> shell vars (uppercased key).
# -----------------------------------------------------------------------------
resolver_set() {
    # $1=key $2=value
    local k v
    k="$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')"
    v="$2"
    eval "RES_${k}=\$v"
    eval "RES_${k}_SET=1"
}

resolver_get() {
    local k val
    k="$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')"
    eval "val=\${RES_${k}-}"
    printf '%s' "$val"
}

resolver_has() {
    local k set
    k="$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')"
    eval "set=\${RES_${k}_SET-0}"
    [ "$set" = "1" ]
}

build_resolver() {
    # Load from stack.yaml + ruleset files into the resolver dict.
    local preset
    if [ ! -f "$STACK_YAML" ]; then
        err "missing $STACK_YAML"
        exit 1
    fi
    preset="$(parse_stack_preset "$STACK_YAML")"
    if [ -z "$preset" ]; then
        err "team_preset not found in $STACK_YAML"
        exit 1
    fi
    case "$preset" in
        solo|small-team|oss|enterprise) : ;;
        *)
            err "unknown team_preset: '$preset' (expected one of: solo, small-team, oss, enterprise)"
            exit 1
            ;;
    esac
    resolver_set preset "$preset"

    if [ ! -f "$GIT_RULES" ]; then
        err "missing $GIT_RULES"
        exit 1
    fi
    if [ ! -f "$DEPLOY_RULES" ]; then
        err "missing $DEPLOY_RULES"
        exit 1
    fi

    if ! check_yaml_fence_balanced "$GIT_RULES"; then
        err "unterminated \`\`\`yaml fence in $GIT_RULES"
        exit 2
    fi
    if ! check_yaml_fence_balanced "$DEPLOY_RULES"; then
        err "unterminated \`\`\`yaml fence in $DEPLOY_RULES"
        exit 2
    fi

    # Merge YAML blocks. Later writes override earlier ones (deployment > git).
    local line key val
    while IFS= read -r line; do
        [ -n "$line" ] || continue
        key="${line%%=*}"
        val="${line#*=}"
        resolver_set "$key" "$val"
    done <<EOF
$(parse_yaml_block "$GIT_RULES")
EOF

    while IFS= read -r line; do
        [ -n "$line" ] || continue
        key="${line%%=*}"
        val="${line#*=}"
        resolver_set "$key" "$val"
    done <<EOF
$(parse_yaml_block "$DEPLOY_RULES")
EOF
}

# -----------------------------------------------------------------------------
# Expression evaluator.
#   Forms:
#     <key> == <literal>
#     <key> != <literal>
#     <key>             (truthy: true | nonzero | nonempty)
#     !<key>            (falsy)
#   Literals: true, false, integers, "double" or 'single' quoted, barewords.
# Returns: 0 (true), 1 (false), 3 (parse error -> caller exits 3).
# -----------------------------------------------------------------------------
eval_expr() {
    local expr="$1"
    # Trim.
    expr="${expr#"${expr%%[![:space:]]*}"}"
    expr="${expr%"${expr##*[![:space:]]}"}"

    if [ -z "$expr" ]; then
        err "empty expression"
        return 3
    fi

    # Detect operator presence.
    case "$expr" in
        *"=="*) _eval_cmp "$expr" "==" ;;
        *"!="*) _eval_cmp "$expr" "!=" ;;
        "!"*)
            local k="${expr#!}"
            k="${k#"${k%%[![:space:]]*}"}"
            k="${k%"${k##*[![:space:]]}"}"
            if _is_truthy "$(resolver_get "$k")"; then return 1; else return 0; fi
            ;;
        *)
            if _is_truthy "$(resolver_get "$expr")"; then return 0; else return 1; fi
            ;;
    esac
}

_eval_cmp() {
    local expr="$1" op="$2" lhs rhs lhs_v rhs_v
    lhs="${expr%%${op}*}"
    rhs="${expr#*${op}}"
    lhs="${lhs#"${lhs%%[![:space:]]*}"}"
    lhs="${lhs%"${lhs##*[![:space:]]}"}"
    rhs="${rhs#"${rhs%%[![:space:]]*}"}"
    rhs="${rhs%"${rhs##*[![:space:]]}"}"

    lhs_v="$(resolver_get "$lhs")"
    rhs_v="$(_unquote "$rhs")"

    if [ "$op" = "==" ]; then
        [ "$lhs_v" = "$rhs_v" ]
        return $?
    else
        [ "$lhs_v" != "$rhs_v" ]
        return $?
    fi
}

_unquote() {
    local s="$1"
    case "$s" in
        \"*\") s="${s#\"}"; s="${s%\"}" ;;
        \'*\') s="${s#\'}"; s="${s%\'}" ;;
    esac
    printf '%s' "$s"
}

_is_truthy() {
    local v="$1"
    case "$v" in
        ""|"false"|"False"|"FALSE"|"0"|"null"|"~") return 1 ;;
        *) return 0 ;;
    esac
}

# -----------------------------------------------------------------------------
# Marker processor.
#
# Two passes:
#   1. Line-based block processing for IF/ELIF/ELSE/ENDIF.
#   2. Inline VAL/ENDVAL substitution.
#
# Updates BRANCH_TAKEN / BRANCH_PRUNED counters (for dry-run summary).
# -----------------------------------------------------------------------------
BRANCH_TAKEN=0
BRANCH_PRUNED=0
VAL_RESOLVED=0
VAL_FALLBACK=0
COUNT_FILE=""

process_file() {
    local src="$1" dst="$2"
    local content
    if ! content="$(cat -- "$src")"; then
        err "cannot read $src"
        return 4
    fi

    # FREEZE:SKIP — file is excluded from freezing entirely (e.g. one-time
    # bootstrap commands like /000-prd-refine). Return success without writing.
    if printf '%s' "$content" | grep -q '<!--[[:space:]]*FREEZE:SKIP[[:space:]]*-->'; then
        if [ "$DRY_RUN" -eq 1 ]; then
            printf '  %s  SKIP\n' "$(basename "$src")"
        fi
        return 10   # special "skipped" indicator handled by caller
    fi

    # Counts emitted by the awk subprocess via this file (since pipelines run
    # the function in a subshell and lose variable updates).
    COUNT_FILE="$(mktemp -t freeze.count.XXXXXX)" || { err "mktemp failed"; return 4; }
    : > "$COUNT_FILE"

    local body rc
    body="$(printf '%s' "$content" | _process_blocks)"
    rc=$?
    if [ "$rc" -ne 0 ]; then rm -f "$COUNT_FILE"; return "$rc"; fi
    body="$(printf '%s' "$body" | _process_vals)"
    rc=$?
    if [ "$rc" -ne 0 ]; then rm -f "$COUNT_FILE"; return "$rc"; fi

    # Read counts.
    if [ -s "$COUNT_FILE" ]; then
        local t p
        t="$(awk -F= '$1=="taken"{print $2}' "$COUNT_FILE")"
        p="$(awk -F= '$1=="pruned"{print $2}' "$COUNT_FILE")"
        [ -n "$t" ] && BRANCH_TAKEN=$((BRANCH_TAKEN + t))
        [ -n "$p" ] && BRANCH_PRUNED=$((BRANCH_PRUNED + p))
    fi
    rm -f "$COUNT_FILE"

    if [ "$DRY_RUN" -eq 1 ]; then
        return 0
    fi

    local dst_dir
    dst_dir="$(dirname -- "$dst")"
    mkdir -p -- "$dst_dir" || { err "mkdir $dst_dir failed"; return 4; }
    # Preserve trailing newline from source (always emit one — markdown
    # convention; source files end with newline).
    printf '%s\n' "$body" > "$dst" || { err "write $dst failed"; return 4; }
    return 0
}

# Block processor reads stdin, emits to stdout. Communicates errors via exit code.
_process_blocks() {
    local input
    input="$(cat)"

    # Use awk to walk lines and emit only selected branches.
    # Stack-based to support nesting. State per level:
    #   ACTIVE   — currently emitting lines in this branch
    #   MATCHED  — a branch has matched in this IF chain (don't emit any more)
    #   PARENT   — inherited active state from parent level
    #
    # Counts emitted via stderr lines "T n" / "P n" then we read them.
    local tmp_err
    tmp_err="$(mktemp -t freeze.err.XXXXXX)" || { err "mktemp failed"; return 4; }

    # Export resolver values into env for awk subprocess via a serialised dict.
    local dict_file
    dict_file="$(mktemp -t freeze.dict.XXXXXX)" || { err "mktemp failed"; rm -f "$tmp_err"; return 4; }
    _dump_resolver > "$dict_file"

    local out rc
    out="$(printf '%s' "$input" | awk -v DICT="$dict_file" -v ERRF="$tmp_err" '
        function trim(s) {
            sub(/^[[:space:]]+/, "", s)
            sub(/[[:space:]]+$/, "", s)
            return s
        }
        function unquote(s) {
            if (length(s) >= 2) {
                first = substr(s, 1, 1)
                last  = substr(s, length(s), 1)
                if ((first == "\"" && last == "\"") || (first == "'\''" && last == "'\''")) {
                    return substr(s, 2, length(s) - 2)
                }
            }
            return s
        }
        function is_truthy(v) {
            if (v == "" || v == "false" || v == "False" || v == "FALSE" || v == "0" || v == "null" || v == "~") return 0
            return 1
        }
        function lookup(k,    K) {
            K = toupper(k)
            gsub(/-/, "_", K)
            return DICT_VALS[K]
        }
        function eval_expr(e,    op_pos, lhs, rhs, k, neg) {
            e = trim(e)
            if (e == "") { errmsg = "empty expression"; return -1 }
            if ((op_pos = index(e, "==")) > 0) {
                lhs = trim(substr(e, 1, op_pos - 1))
                rhs = trim(substr(e, op_pos + 2))
                return (lookup(lhs) == unquote(rhs)) ? 1 : 0
            }
            if ((op_pos = index(e, "!=")) > 0) {
                lhs = trim(substr(e, 1, op_pos - 1))
                rhs = trim(substr(e, op_pos + 2))
                return (lookup(lhs) != unquote(rhs)) ? 1 : 0
            }
            neg = 0
            if (substr(e, 1, 1) == "!") {
                neg = 1
                e = trim(substr(e, 2))
            }
            k = e
            if (k !~ /^[A-Za-z_][A-Za-z0-9_]*$/) { errmsg = "bad key: " e; return -1 }
            v = lookup(k)
            if (neg) return is_truthy(v) ? 0 : 1
            return is_truthy(v) ? 1 : 0
        }
        BEGIN {
            # Load dict.
            while ((getline line < DICT) > 0) {
                eqp = index(line, "=")
                if (eqp <= 0) continue
                k = substr(line, 1, eqp - 1)
                v = substr(line, eqp + 1)
                DICT_VALS[k] = v
            }
            close(DICT)
            depth = 0
            # Stack of states.
            STK_ACTIVE[0] = 1   # root is always active
            STK_MATCHED[0] = 1  # root is "matched" (no else triggers)
            taken = 0; pruned = 0
        }
        {
            line = $0
            # IF
            if (match(line, /^[[:space:]]*<!--[[:space:]]*FREEZE:IF[[:space:]]+/)) {
                expr = line
                sub(/^[[:space:]]*<!--[[:space:]]*FREEZE:IF[[:space:]]+/, "", expr)
                sub(/[[:space:]]*-->[[:space:]]*$/, "", expr)
                depth++
                parent_active = STK_ACTIVE[depth - 1]
                if (parent_active) {
                    r = eval_expr(expr)
                    if (r < 0) { print "EVAL_ERROR: " errmsg > ERRF; exit 3 }
                    if (r == 1) { STK_ACTIVE[depth] = 1; STK_MATCHED[depth] = 1; taken++ }
                    else        { STK_ACTIVE[depth] = 0; STK_MATCHED[depth] = 0; pruned++ }
                } else {
                    STK_ACTIVE[depth] = 0
                    STK_MATCHED[depth] = 1   # suppress all branches
                }
                next
            }
            # ELIF
            if (match(line, /^[[:space:]]*<!--[[:space:]]*FREEZE:ELIF[[:space:]]+/)) {
                if (depth < 1) { print "PARSE_ERROR: ELIF without IF" > ERRF; exit 2 }
                expr = line
                sub(/^[[:space:]]*<!--[[:space:]]*FREEZE:ELIF[[:space:]]+/, "", expr)
                sub(/[[:space:]]*-->[[:space:]]*$/, "", expr)
                parent_active = STK_ACTIVE[depth - 1]
                if (parent_active && !STK_MATCHED[depth]) {
                    r = eval_expr(expr)
                    if (r < 0) { print "EVAL_ERROR: " errmsg > ERRF; exit 3 }
                    if (r == 1) { STK_ACTIVE[depth] = 1; STK_MATCHED[depth] = 1; taken++ }
                    else        { STK_ACTIVE[depth] = 0; pruned++ }
                } else {
                    if (STK_ACTIVE[depth] == 1) { STK_ACTIVE[depth] = 0 }
                    # already matched somewhere: prune this branch
                    if (parent_active) pruned++
                }
                next
            }
            # ELSE
            if (match(line, /^[[:space:]]*<!--[[:space:]]*FREEZE:ELSE[[:space:]]*-->[[:space:]]*$/)) {
                if (depth < 1) { print "PARSE_ERROR: ELSE without IF" > ERRF; exit 2 }
                parent_active = STK_ACTIVE[depth - 1]
                if (parent_active && !STK_MATCHED[depth]) {
                    STK_ACTIVE[depth] = 1; STK_MATCHED[depth] = 1; taken++
                } else {
                    if (STK_ACTIVE[depth] == 1) STK_ACTIVE[depth] = 0
                    if (parent_active) pruned++
                }
                next
            }
            # ENDIF
            if (match(line, /^[[:space:]]*<!--[[:space:]]*FREEZE:ENDIF[[:space:]]*-->[[:space:]]*$/)) {
                if (depth < 1) { print "PARSE_ERROR: ENDIF without IF" > ERRF; exit 2 }
                delete STK_ACTIVE[depth]
                delete STK_MATCHED[depth]
                depth--
                next
            }
            # Regular line: emit if active.
            if (STK_ACTIVE[depth]) print line
        }
        END {
            if (depth != 0) { print "PARSE_ERROR: unterminated IF (depth=" depth ")" > ERRF; exit 2 }
            print "COUNT " taken " " pruned > ERRF
        }
    ')"
    rc=$?

    # Read counters / errors from tmp_err.
    if [ "$rc" -ne 0 ]; then
        if [ -s "$tmp_err" ]; then
            local errline
            errline="$(grep -E '^(PARSE_ERROR|EVAL_ERROR)' "$tmp_err" | head -1)"
            err "$errline"
        fi
        rm -f "$tmp_err" "$dict_file"
        return "$rc"
    fi

    # Persist counts to COUNT_FILE so the parent shell can read them
    # (this function runs in a subshell via pipeline).
    local count_line t p
    count_line="$(grep '^COUNT ' "$tmp_err" | tail -1)"
    if [ -n "$count_line" ] && [ -n "${COUNT_FILE:-}" ]; then
        t="$(printf '%s' "$count_line" | awk '{print $2}')"
        p="$(printf '%s' "$count_line" | awk '{print $3}')"
        printf 'taken=%s\npruned=%s\n' "${t:-0}" "${p:-0}" > "$COUNT_FILE"
    fi
    rm -f "$tmp_err" "$dict_file"

    printf '%s' "$out"
    return 0
}

# Inline VAL/ENDVAL substitution.
#   <!-- FREEZE:VAL <key> -->fallback<!-- FREEZE:ENDVAL -->
# Replaces with dict[key] if non-empty truthy, else fallback literal.
_process_vals() {
    local input
    input="$(cat)"
    local dict_file
    dict_file="$(mktemp -t freeze.valdict.XXXXXX)" || { err "mktemp failed"; return 4; }
    _dump_resolver > "$dict_file"

    local out
    out="$(printf '%s' "$input" | awk -v DICT="$dict_file" '
        function lookup(k,    K) {
            K = toupper(k)
            gsub(/-/, "_", K)
            return DICT_VALS[K]
        }
        BEGIN {
            while ((getline line < DICT) > 0) {
                eqp = index(line, "=")
                if (eqp <= 0) continue
                k = substr(line, 1, eqp - 1)
                v = substr(line, eqp + 1)
                DICT_VALS[k] = v
            }
            close(DICT)
            buf = ""
        }
        {
            if (NR == 1) buf = $0
            else buf = buf "\n" $0
        }
        END {
            data = buf
            out = ""
            # Walk through scanning for the start marker.
            while ((sp = match(data, /<!--[[:space:]]*FREEZE:VAL[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]*-->/)) > 0) {
                head = substr(data, 1, sp - 1)
                marker = substr(data, sp, RLENGTH)
                rest = substr(data, sp + RLENGTH)
                # Extract key from marker.
                key = marker
                sub(/^<!--[[:space:]]*FREEZE:VAL[[:space:]]+/, "", key)
                sub(/[[:space:]]*-->$/, "", key)
                # Find matching ENDVAL.
                ep = match(rest, /<!--[[:space:]]*FREEZE:ENDVAL[[:space:]]*-->/)
                if (ep <= 0) {
                    # No closing tag — emit head and the marker as-is, continue from rest.
                    out = out head marker
                    data = rest
                    continue
                }
                fallback = substr(rest, 1, ep - 1)
                end_marker_len = RLENGTH
                after = substr(rest, ep + end_marker_len)
                v = lookup(key)
                if (v != "" && v != "false" && v != "False" && v != "FALSE" && v != "0" && v != "null") {
                    chosen = v
                } else {
                    chosen = fallback
                }
                out = out head chosen
                data = after
            }
            out = out data
            printf "%s", out
        }
    ')"
    rm -f "$dict_file"
    printf '%s' "$out"
    return 0
}

_dump_resolver() {
    # Dump RES_* vars as KEY=VALUE for awk subprocess.
    # Use `set` and grep prefix RES_.
    set | grep '^RES_' | grep -v '_SET=' | while IFS= read -r kv; do
        # kv like RES_PRESET='solo' OR RES_PRESET=solo
        local k v
        k="${kv%%=*}"
        v="${kv#*=}"
        k="${k#RES_}"
        # Strip outer quoting that `set` may add.
        case "$v" in
            \'*\') v="${v#\'}"; v="${v%\'}" ;;
        esac
        printf '%s=%s\n' "$k" "$v"
    done
}

# -----------------------------------------------------------------------------
# Main freeze loop.
# -----------------------------------------------------------------------------
do_freeze() {
    if [ ! -d "$PLUGIN_ROOT" ]; then
        err "plugin root not found: $PLUGIN_ROOT"
        exit 1
    fi
    if [ ! -d "$PLUGIN_ROOT/commands" ] && [ ! -d "$PLUGIN_ROOT/agents" ]; then
        err "no commands/ or agents/ in $PLUGIN_ROOT"
        exit 1
    fi

    # Already-frozen check.
    if [ "$DRY_RUN" -ne 1 ] && [ "$FORCE" -ne 1 ]; then
        if [ -d "$OUT_COMMANDS" ] && [ "$(ls -A "$OUT_COMMANDS" 2>/dev/null)" ]; then
            err "$OUT_COMMANDS already populated — re-run with --force to overwrite, or --reset first"
            exit 5
        fi
        if [ -d "$OUT_AGENTS" ] && [ "$(ls -A "$OUT_AGENTS" 2>/dev/null)" ]; then
            err "$OUT_AGENTS already populated — re-run with --force to overwrite, or --reset first"
            exit 5
        fi
    fi

    build_resolver

    info "preset=$(resolver_get preset) plugin_root=$PLUGIN_ROOT"

    local total_files=0
    local SKIPPED_FILES=0
    local rc

    # Commands.
    if [ -d "$PLUGIN_ROOT/commands" ]; then
        for src in "$PLUGIN_ROOT"/commands/*.md; do
            [ -e "$src" ] || continue
            local base dst
            base="$(basename "$src")"
            dst="$OUT_COMMANDS/$base"
            local pre_t=$BRANCH_TAKEN pre_p=$BRANCH_PRUNED
            process_file "$src" "$dst"
            rc=$?
            if [ "$rc" -eq 10 ]; then
                # FREEZE:SKIP file — counted separately, not in total_files.
                SKIPPED_FILES=$((SKIPPED_FILES + 1))
                continue
            fi
            if [ "$rc" -ne 0 ]; then
                err "failed processing $src"
                exit "$rc"
            fi
            total_files=$((total_files + 1))
            if [ "$DRY_RUN" -eq 1 ]; then
                printf '  %s  +%d/-%d branches\n' \
                    "$base" \
                    $((BRANCH_TAKEN - pre_t)) \
                    $((BRANCH_PRUNED - pre_p))
            fi
        done
    fi

    # Agents.
    if [ -d "$PLUGIN_ROOT/agents" ]; then
        for src in "$PLUGIN_ROOT"/agents/*.md; do
            [ -e "$src" ] || continue
            local base dst
            base="$(basename "$src")"
            dst="$OUT_AGENTS/$base"
            local pre_t=$BRANCH_TAKEN pre_p=$BRANCH_PRUNED
            process_file "$src" "$dst"
            rc=$?
            if [ "$rc" -eq 10 ]; then
                # FREEZE:SKIP file — counted separately, not in total_files.
                SKIPPED_FILES=$((SKIPPED_FILES + 1))
                continue
            fi
            if [ "$rc" -ne 0 ]; then
                err "failed processing $src"
                exit "$rc"
            fi
            total_files=$((total_files + 1))
            if [ "$DRY_RUN" -eq 1 ]; then
                printf '  %s  +%d/-%d branches\n' \
                    "$base" \
                    $((BRANCH_TAKEN - pre_t)) \
                    $((BRANCH_PRUNED - pre_p))
            fi
        done
    fi

    if [ "$DRY_RUN" -eq 1 ]; then
        info "DRY-RUN: $total_files files, $BRANCH_TAKEN branches taken, $BRANCH_PRUNED pruned, $SKIPPED_FILES skipped"
    else
        info "froze $total_files files ($BRANCH_TAKEN branches taken, $BRANCH_PRUNED pruned, $SKIPPED_FILES skipped)"
        info "output: $OUT_COMMANDS/  $OUT_AGENTS/"
    fi
}

# -----------------------------------------------------------------------------
# Entry point.
# -----------------------------------------------------------------------------
main() {
    parse_args "$@"
    if [ "$RESET" -eq 1 ]; then
        do_reset
    fi
    do_freeze
}

# Allow sourcing without auto-run (for self-test).
if [ "${FREEZE_SH_LIB:-0}" != "1" ]; then
    main "$@"
fi
