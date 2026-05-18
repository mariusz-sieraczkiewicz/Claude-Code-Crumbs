#!/usr/bin/env bash
# test-freeze.sh — self-test for scripts/freeze.sh.
#
# Creates a temp workspace with:
#   - .claude/stack.yaml (preset=enterprise)
#   - .claude/ruleset/git-workflow.md (with YAML toggle block)
#   - .claude/ruleset/deployment.md   (with YAML toggle block)
#   - synthetic plugin tree with one command exercising every marker form
#
# Runs freeze.sh, diffs against expected output, prints PASS/FAIL.
#
# Exit 0 on pass, non-zero on any mismatch.

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FREEZE="$SCRIPT_DIR/freeze.sh"

if [ ! -x "$FREEZE" ]; then
    echo "test-freeze: $FREEZE not executable" >&2
    exit 1
fi

WORK="$(mktemp -d -t freeze-test.XXXXXX)" || { echo "mktemp failed" >&2; exit 1; }
trap 'rm -rf "$WORK"' EXIT

# -----------------------------------------------------------------------------
# Build fake project.
# -----------------------------------------------------------------------------
mkdir -p "$WORK/proj/.claude/ruleset"
mkdir -p "$WORK/plugin/commands"
mkdir -p "$WORK/plugin/agents"

cat > "$WORK/proj/.claude/stack.yaml" <<'EOF'
stack:
  name: testproj
team_preset: enterprise
EOF

cat > "$WORK/proj/.claude/ruleset/git-workflow.md" <<'EOF'
---
description: test
---

# Git Workflow

> **Preset: enterprise**

## Auto-invoke toggles

```yaml
auto_invoke_review: true
require_reviewers: 2
pr_required: true
allow_commit_to_main: false
require_signed_commits: true
squash_merge: true
ticket_prefixes: ["CHG", "JIRA"]
branch_name_pattern: "task/{ticket_id}/{task_id}-{slug}"
pr_body_template: |
  ## Summary
  <one para>

  ## Change-management
  - Ticket: {ticket_id}
```

End.
EOF

cat > "$WORK/proj/.claude/ruleset/deployment.md" <<'EOF'
---
description: test
---

# Deployment

```yaml
require_pre_flight: true
require_approvers_for_promote: 2
auto_deploy_prod: false
```
EOF

# Synthetic command file with every marker form.
cat > "$WORK/plugin/commands/sample.md" <<'EOF'
---
description: sample
---

# Sample

<!-- FREEZE:IF preset == "enterprise" -->
ENTERPRISE_LINE_1
<!-- FREEZE:ELIF preset == "small-team" -->
SMALL_TEAM_LINE
<!-- FREEZE:ELSE -->
FALLBACK_LINE
<!-- FREEZE:ENDIF -->

<!-- FREEZE:IF pr_required -->
PR_REQUIRED_TRUE
<!-- FREEZE:ELSE -->
PR_REQUIRED_FALSE
<!-- FREEZE:ENDIF -->

<!-- FREEZE:IF !allow_commit_to_main -->
COMMIT_TO_MAIN_BLOCKED
<!-- FREEZE:ENDIF -->

<!-- FREEZE:IF require_reviewers != 0 -->
REVIEWERS_NEEDED
<!-- FREEZE:ENDIF -->

Branch pattern: <!-- FREEZE:VAL branch_name_pattern -->task/{task_id}-{slug}<!-- FREEZE:ENDVAL -->

Missing key: <!-- FREEZE:VAL nonexistent_key -->fallback-text<!-- FREEZE:ENDVAL -->

<!-- FREEZE:IF ticket_prefixes -->
HAS_TICKET_PREFIXES
<!-- FREEZE:ENDIF -->

PR body literal headers: <!-- FREEZE:VAL pr_body_template -->no-template<!-- FREEZE:ENDVAL -->
EOF

# Synthetic agent file without markers — should be copied verbatim.
cat > "$WORK/plugin/agents/plain.md" <<'EOF'
---
description: plain
---

# Plain Agent

No markers here. Should appear verbatim.
EOF

# -----------------------------------------------------------------------------
# Run freeze (from inside the proj dir).
# -----------------------------------------------------------------------------
cd "$WORK/proj"

if ! "$FREEZE" --force --plugin-root="$WORK/plugin" > "$WORK/run.log" 2>&1; then
    echo "FAIL: freeze.sh exited non-zero"
    cat "$WORK/run.log"
    exit 1
fi

# -----------------------------------------------------------------------------
# Verify outputs.
# -----------------------------------------------------------------------------
fail() { echo "FAIL: $*"; cat "$WORK/run.log" 2>/dev/null; exit 1; }

OUT_CMD="$WORK/proj/.claude/commands/sample.md"
OUT_AG="$WORK/proj/.claude/agents/plain.md"

[ -f "$OUT_CMD" ] || fail "sample.md not written"
[ -f "$OUT_AG" ]  || fail "plain.md not written"

# Expected content for sample.md.
EXPECTED_SAMPLE="$WORK/expected.sample.md"
cat > "$EXPECTED_SAMPLE" <<'EOF'
---
description: sample
---

# Sample

ENTERPRISE_LINE_1

PR_REQUIRED_TRUE

COMMIT_TO_MAIN_BLOCKED

REVIEWERS_NEEDED

Branch pattern: task/{ticket_id}/{task_id}-{slug}

Missing key: fallback-text

HAS_TICKET_PREFIXES

PR body literal headers: ## Summary\n<one para>\n\n## Change-management\n- Ticket: {ticket_id}
EOF

if ! diff -u "$EXPECTED_SAMPLE" "$OUT_CMD" > "$WORK/diff.out"; then
    echo "FAIL: sample.md content mismatch"
    cat "$WORK/diff.out"
    exit 1
fi

# Verify plain.md is identical to source.
if ! diff -u "$WORK/plugin/agents/plain.md" "$OUT_AG" > "$WORK/diff2.out"; then
    echo "FAIL: plain.md should be verbatim copy"
    cat "$WORK/diff2.out"
    exit 1
fi

# Verify no FREEZE markers remain in frozen output.
if grep -q 'FREEZE:' "$OUT_CMD"; then
    fail "frozen sample.md still contains FREEZE markers"
fi

# Verify pr_body_template literal preserved markdown headers (regression: awk
# stripped `#`-lines inside YAML literal blocks).
if ! grep -q '## Summary' "$OUT_CMD"; then
    echo "FAIL: pr_body_template lost '## Summary' header (literal-block # stripped)"
    cat "$OUT_CMD"
    exit 1
fi
if ! grep -q '## Change-management' "$OUT_CMD"; then
    echo "FAIL: pr_body_template lost '## Change-management' header"
    cat "$OUT_CMD"
    exit 1
fi

# -----------------------------------------------------------------------------
# Test 2: --dry-run does not write.
# -----------------------------------------------------------------------------
rm -rf "$WORK/proj/.claude/commands" "$WORK/proj/.claude/agents"
if ! "$FREEZE" --dry-run --plugin-root="$WORK/plugin" > "$WORK/dry.log" 2>&1; then
    fail "dry-run exited non-zero"
fi
if [ -d "$WORK/proj/.claude/commands" ] || [ -d "$WORK/proj/.claude/agents" ]; then
    fail "dry-run created output directories"
fi
grep -q 'DRY-RUN' "$WORK/dry.log" || fail "dry-run output missing DRY-RUN line"

# -----------------------------------------------------------------------------
# Test 3: already-frozen guard.
# -----------------------------------------------------------------------------
"$FREEZE" --force --plugin-root="$WORK/plugin" > /dev/null 2>&1 || fail "second freeze --force failed"
# Now without --force, should exit 5.
set +e
"$FREEZE" --plugin-root="$WORK/plugin" > "$WORK/locked.log" 2>&1
rc=$?
set -e
if [ "$rc" -ne 5 ]; then
    fail "expected exit 5 for already-frozen, got $rc"
fi

# -----------------------------------------------------------------------------
# Test 4: --reset --force clears outputs.
# -----------------------------------------------------------------------------
"$FREEZE" --reset --force > /dev/null 2>&1 || fail "reset failed"
if [ -d "$WORK/proj/.claude/commands" ] || [ -d "$WORK/proj/.claude/agents" ]; then
    fail "reset did not remove output dirs"
fi

# -----------------------------------------------------------------------------
# Test 5: missing stack.yaml -> exit 1.
# -----------------------------------------------------------------------------
mv "$WORK/proj/.claude/stack.yaml" "$WORK/proj/.claude/stack.yaml.bak"
set +e
"$FREEZE" --force --plugin-root="$WORK/plugin" > "$WORK/miss.log" 2>&1
rc=$?
set -e
mv "$WORK/proj/.claude/stack.yaml.bak" "$WORK/proj/.claude/stack.yaml"
if [ "$rc" -ne 1 ]; then
    fail "expected exit 1 for missing stack.yaml, got $rc"
fi

# -----------------------------------------------------------------------------
# Test 6: unknown team_preset -> exit 1 with clear message.
# -----------------------------------------------------------------------------
mv "$WORK/proj/.claude/stack.yaml" "$WORK/proj/.claude/stack.yaml.bak"
cat > "$WORK/proj/.claude/stack.yaml" <<'EOF'
stack:
  name: testproj
team_preset: weird-thing
EOF
set +e
"$FREEZE" --force --plugin-root="$WORK/plugin" > "$WORK/unknown.log" 2>&1
rc=$?
set -e
mv "$WORK/proj/.claude/stack.yaml.bak" "$WORK/proj/.claude/stack.yaml"
if [ "$rc" -ne 1 ]; then
    fail "expected exit 1 for unknown preset, got $rc"
fi
grep -q "unknown team_preset" "$WORK/unknown.log" || fail "missing 'unknown team_preset' in stderr"

# -----------------------------------------------------------------------------
# Test 7: unterminated yaml fence in ruleset -> exit 2.
# -----------------------------------------------------------------------------
mv "$WORK/proj/.claude/ruleset/git-workflow.md" "$WORK/proj/.claude/ruleset/git-workflow.md.bak"
cat > "$WORK/proj/.claude/ruleset/git-workflow.md" <<'EOF'
# Git Workflow

```yaml
pr_required: true
allow_commit_to_main: false
EOF
set +e
"$FREEZE" --force --plugin-root="$WORK/plugin" > "$WORK/unterm.log" 2>&1
rc=$?
set -e
mv "$WORK/proj/.claude/ruleset/git-workflow.md.bak" "$WORK/proj/.claude/ruleset/git-workflow.md"
if [ "$rc" -ne 2 ]; then
    fail "expected exit 2 for unterminated yaml fence, got $rc"
fi
grep -q "unterminated" "$WORK/unterm.log" || fail "missing 'unterminated' in stderr"

echo "PASS: all freeze.sh self-tests"
exit 0
