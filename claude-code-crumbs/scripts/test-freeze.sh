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

# -----------------------------------------------------------------------------
# Test 8: flow list with `#` inside quoted value survives comment-strip.
# -----------------------------------------------------------------------------
mv "$WORK/proj/.claude/ruleset/git-workflow.md" "$WORK/proj/.claude/ruleset/git-workflow.md.bak"
cat > "$WORK/proj/.claude/ruleset/git-workflow.md" <<'EOF'
# Git Workflow

```yaml
pr_required: true
ticket_prefixes: ["CHG", "dev #tag", "JIRA"]
allow_commit_to_main: false
```
EOF
# Add a marker that emits ticket_prefixes via VAL.
cat > "$WORK/plugin/commands/flowlist.md" <<'EOF'
prefixes: <!-- FREEZE:VAL ticket_prefixes -->none<!-- FREEZE:ENDVAL -->
EOF
"$FREEZE" --reset --force > /dev/null 2>&1 || true
"$FREEZE" --force --plugin-root="$WORK/plugin" > "$WORK/flowlist.log" 2>&1 \
    || fail "freeze with flow-list-comment-value failed"
if ! grep -q 'dev #tag' "$WORK/proj/.claude/commands/flowlist.md"; then
    echo "FAIL: flow list with '#' inside quoted value got truncated"
    cat "$WORK/proj/.claude/commands/flowlist.md"
    exit 1
fi
mv "$WORK/proj/.claude/ruleset/git-workflow.md.bak" "$WORK/proj/.claude/ruleset/git-workflow.md"
rm -f "$WORK/plugin/commands/flowlist.md"

# -----------------------------------------------------------------------------
# Test 9: symlink in plugin tree refused.
# -----------------------------------------------------------------------------
"$FREEZE" --reset --force > /dev/null 2>&1 || true
echo "secret" > "$WORK/secret.txt"
ln -s "$WORK/secret.txt" "$WORK/plugin/commands/symlinked.md"
set +e
"$FREEZE" --force --plugin-root="$WORK/plugin" > "$WORK/symlink.log" 2>&1
rc=$?
set -e
rm -f "$WORK/plugin/commands/symlinked.md" "$WORK/secret.txt"
if [ "$rc" -eq 0 ]; then
    fail "freeze followed symlink in plugin tree (rc=$rc)"
fi
grep -q "refusing symlink" "$WORK/symlink.log" || fail "missing 'refusing symlink' in stderr"

# -----------------------------------------------------------------------------
# Test 10: BOM directly before team_preset on line 1 resolves correctly.
# (Worst case — BOM strip only fires on NR==1.)
# -----------------------------------------------------------------------------
"$FREEZE" --reset --force > /dev/null 2>&1 || true
mv "$WORK/proj/.claude/stack.yaml" "$WORK/proj/.claude/stack.yaml.bak"
printf '\xef\xbb\xbfteam_preset: enterprise\nstack:\n  name: bomtest\n' > "$WORK/proj/.claude/stack.yaml"
"$FREEZE" --force --plugin-root="$WORK/plugin" > "$WORK/bom.log" 2>&1 \
    || { cat "$WORK/bom.log"; fail "freeze failed on BOM-prefixed stack.yaml"; }
grep -q "preset=enterprise" "$WORK/bom.log" || fail "preset not detected past BOM"
mv "$WORK/proj/.claude/stack.yaml.bak" "$WORK/proj/.claude/stack.yaml"

# -----------------------------------------------------------------------------
# Test 11: reserved key `preset` in ruleset YAML is ignored.
# -----------------------------------------------------------------------------
"$FREEZE" --reset --force > /dev/null 2>&1 || true
mv "$WORK/proj/.claude/ruleset/git-workflow.md" "$WORK/proj/.claude/ruleset/git-workflow.md.bak"
cat > "$WORK/proj/.claude/ruleset/git-workflow.md" <<'EOF'
# Git Workflow

```yaml
preset: hijacked
pr_required: true
allow_commit_to_main: false
```
EOF
"$FREEZE" --force --plugin-root="$WORK/plugin" > "$WORK/shadow.log" 2>&1 \
    || fail "freeze failed after preset-shadow attempt"
# Validated preset must still be 'enterprise' (from stack.yaml), not 'hijacked'.
grep -q "preset=enterprise" "$WORK/shadow.log" || fail "ruleset shadowed validated preset"
mv "$WORK/proj/.claude/ruleset/git-workflow.md.bak" "$WORK/proj/.claude/ruleset/git-workflow.md"

# -----------------------------------------------------------------------------
# Test 12: --reset is surgical via manifest — preserves user-authored files.
# -----------------------------------------------------------------------------
"$FREEZE" --reset --force > /dev/null 2>&1 || true
"$FREEZE" --force --plugin-root="$WORK/plugin" > /dev/null 2>&1 \
    || fail "pre-manifest freeze failed"
# Drop a user file alongside the frozen ones.
echo "user-authored" > "$WORK/proj/.claude/commands/my-custom.md"
"$FREEZE" --reset --force > "$WORK/manifreset.log" 2>&1 \
    || fail "manifest-based reset failed"
if [ ! -f "$WORK/proj/.claude/commands/my-custom.md" ]; then
    fail "manifest-based reset deleted user-authored file"
fi
[ -f "$WORK/proj/.claude/commands/sample.md" ] && fail "frozen sample.md not removed"
[ -f "$WORK/proj/.claude/.freeze-manifest" ] && fail "manifest not removed after reset"
rm -f "$WORK/proj/.claude/commands/my-custom.md"
rmdir "$WORK/proj/.claude/commands" 2>/dev/null || true

# -----------------------------------------------------------------------------
# Test 13a: manifest path traversal refused.
# -----------------------------------------------------------------------------
"$FREEZE" --reset --force > /dev/null 2>&1 || true
"$FREEZE" --force --plugin-root="$WORK/plugin" > /dev/null 2>&1 \
    || fail "freeze before traversal test failed"
EVIDENCE="$WORK/traversal-evidence.txt"
echo "must-survive" > "$EVIDENCE"
# Tamper with manifest: inject path traversal targeting the evidence file.
# Compute manifest-relative path from $WORK/proj/.claude/.freeze-manifest to $EVIDENCE.
printf '../../../%s\n' "$(basename "$EVIDENCE")" >> "$WORK/proj/.claude/.freeze-manifest"
"$FREEZE" --reset --force > "$WORK/traversal.log" 2>&1 || true
if [ ! -f "$EVIDENCE" ]; then
    fail "SECURITY: --reset deleted file outside project via manifest traversal"
fi
grep -q "unsafe path" "$WORK/traversal.log" || fail "missing 'unsafe path' warning"
rm -f "$EVIDENCE"

# -----------------------------------------------------------------------------
# Test 13b: symlinked manifest refused.
# -----------------------------------------------------------------------------
mkdir -p "$WORK/proj/.claude"
echo "victim-content" > "$WORK/victim.txt"
ln -sf "$WORK/victim.txt" "$WORK/proj/.claude/.freeze-manifest"
set +e
"$FREEZE" --reset --force > "$WORK/symlink-manifest.log" 2>&1
rc=$?
set -e
rm -f "$WORK/proj/.claude/.freeze-manifest"
[ -f "$WORK/victim.txt" ] || fail "SECURITY: symlinked manifest let freeze delete target"
if [ "$rc" -ne 4 ]; then
    fail "expected exit 4 for symlinked manifest, got $rc"
fi
grep -q "manifest is a symlink" "$WORK/symlink-manifest.log" \
    || fail "missing 'manifest is a symlink' in stderr"
rm -f "$WORK/victim.txt"

# -----------------------------------------------------------------------------
# Test 13c: flow list with trailing comma drops phantom empty item.
# -----------------------------------------------------------------------------
"$FREEZE" --reset --force > /dev/null 2>&1 || true
mv "$WORK/proj/.claude/ruleset/git-workflow.md" "$WORK/proj/.claude/ruleset/git-workflow.md.bak"
cat > "$WORK/proj/.claude/ruleset/git-workflow.md" <<'EOF'
# Git Workflow

```yaml
pr_required: true
ticket_prefixes: ["CHG", "JIRA", ]
allow_commit_to_main: false
```
EOF
cat > "$WORK/plugin/commands/flowcomma.md" <<'EOF'
prefixes: <!-- FREEZE:VAL ticket_prefixes -->none<!-- FREEZE:ENDVAL -->
EOF
"$FREEZE" --force --plugin-root="$WORK/plugin" > "$WORK/flowcomma.log" 2>&1 \
    || fail "freeze with trailing-comma flow list failed"
# Must emit "CHG,JIRA" (NO trailing comma, no phantom empty).
if ! grep -Eq '^prefixes: CHG,JIRA$' "$WORK/proj/.claude/commands/flowcomma.md"; then
    echo "FAIL: trailing-comma flow list produced phantom empty item"
    cat "$WORK/proj/.claude/commands/flowcomma.md"
    exit 1
fi
mv "$WORK/proj/.claude/ruleset/git-workflow.md.bak" "$WORK/proj/.claude/ruleset/git-workflow.md"
rm -f "$WORK/plugin/commands/flowcomma.md"

# -----------------------------------------------------------------------------
# Test 13: concurrent freeze lock.
# -----------------------------------------------------------------------------
"$FREEZE" --reset --force > /dev/null 2>&1 || true
# Manually plant lock dir, then attempt freeze.
mkdir -p "$WORK/proj/.claude/.freeze.lock"
set +e
"$FREEZE" --force --plugin-root="$WORK/plugin" > "$WORK/lock.log" 2>&1
rc=$?
set -e
rmdir "$WORK/proj/.claude/.freeze.lock"
if [ "$rc" -ne 4 ]; then
    fail "expected exit 4 for concurrent lock, got $rc"
fi
grep -q "another freeze" "$WORK/lock.log" || fail "missing 'another freeze' in stderr"

# -----------------------------------------------------------------------------
# Tests 17-19: real-command FREEZE toggle pairs introduced by T-003 / T-004.
#
# Drive the actual /003-verify-dod.md and /004-code-review.md command files
# (under crumbs commands/) through freeze with the new self-heal toggles set
# both ways, and assert the frozen output picks the right branch.
#
# These tests cover the toggles `auto_fix_on_verify_fail` (003) and
# `auto_fix_on_review_fail` (004) added by the epic-restore-flow rewrites.
# -----------------------------------------------------------------------------

REAL_CMD_DIR="$SCRIPT_DIR/../commands"
[ -f "$REAL_CMD_DIR/003-verify-dod.md" ] || fail "real 003-verify-dod.md not found at $REAL_CMD_DIR"
[ -f "$REAL_CMD_DIR/004-code-review.md" ] || fail "real 004-code-review.md not found at $REAL_CMD_DIR"

# Helper: rewrite the toggle block in git-workflow.md, copy a real command
# into the plugin tree, run freeze, and return path to the frozen file.
#
# $1 = real command basename (e.g. 003-verify-dod.md)
# $2 = path to a tmp git-workflow.md body (full file, will replace ruleset copy)
# $3 = output log path
run_real_freeze() {
    local cmd_base="$1" gw_body="$2" logf="$3"
    "$FREEZE" --reset --force > /dev/null 2>&1 || true
    rm -f "$WORK/plugin/commands"/*.md
    cp "$REAL_CMD_DIR/$cmd_base" "$WORK/plugin/commands/$cmd_base"
    cp "$gw_body" "$WORK/proj/.claude/ruleset/git-workflow.md"
    "$FREEZE" --force --plugin-root="$WORK/plugin" > "$logf" 2>&1 \
        || { cat "$logf"; fail "freeze failed for $cmd_base"; }
}

# Stash current plugin commands so we can restore at the end (rest of the
# suite already passed; tests below rebuild from scratch).
STASH_DIR="$WORK/stash"
mkdir -p "$STASH_DIR"
cp "$WORK/plugin/commands"/*.md "$STASH_DIR/" 2>/dev/null || true

# Stash original git-workflow.md so we can restore.
cp "$WORK/proj/.claude/ruleset/git-workflow.md" "$WORK/proj/.claude/ruleset/git-workflow.md.case17bak"

# -----------------------------------------------------------------------------
# Test 17: /003-verify-dod.md with auto_fix_on_verify_fail: true
#   → frozen output MUST include the self-heal Phase 2 dispatch text.
#   → frozen output MUST NOT include the read-only Phase 2 text.
# -----------------------------------------------------------------------------
cat > "$WORK/gw-fix-on.md" <<'EOF'
# Git Workflow

```yaml
pr_required: true
allow_commit_to_main: false
auto_invoke_review: true
auto_fix_on_verify_fail: true
auto_fix_on_review_fail: true
```
EOF
run_real_freeze "003-verify-dod.md" "$WORK/gw-fix-on.md" "$WORK/case17.log"
OUT17="$WORK/proj/.claude/commands/003-verify-dod.md"
[ -f "$OUT17" ] || fail "case 17: frozen 003-verify-dod.md not written"
if ! grep -q 'Phase 2 — Dispatch feedback-implementer' "$OUT17"; then
    echo "FAIL: case 17 — missing self-heal Phase 2 heading in frozen 003"
    grep -n 'Phase 2' "$OUT17" || true
    exit 1
fi
if grep -q 'Phase 2 — Read result (read-only)' "$OUT17"; then
    echo "FAIL: case 17 — read-only Phase 2 heading leaked into self-heal-on frozen 003"
    exit 1
fi
if grep -q 'FREEZE:' "$OUT17"; then
    fail "case 17: frozen 003 still contains FREEZE markers"
fi

# -----------------------------------------------------------------------------
# Test 18: /003-verify-dod.md with auto_fix_on_verify_fail: false
#   → frozen output MUST include the read-only Phase 2 text.
#   → frozen output MUST NOT include the self-heal Phase 2 dispatch text.
# -----------------------------------------------------------------------------
cat > "$WORK/gw-fix-off.md" <<'EOF'
# Git Workflow

```yaml
pr_required: true
allow_commit_to_main: false
auto_invoke_review: true
auto_fix_on_verify_fail: false
auto_fix_on_review_fail: false
```
EOF
run_real_freeze "003-verify-dod.md" "$WORK/gw-fix-off.md" "$WORK/case18.log"
OUT18="$WORK/proj/.claude/commands/003-verify-dod.md"
[ -f "$OUT18" ] || fail "case 18: frozen 003-verify-dod.md not written"
if ! grep -q 'Phase 2 — Read result (read-only)' "$OUT18"; then
    echo "FAIL: case 18 — missing read-only Phase 2 heading in frozen 003"
    grep -n 'Phase 2' "$OUT18" || true
    exit 1
fi
if grep -q 'Phase 2 — Dispatch feedback-implementer' "$OUT18"; then
    echo "FAIL: case 18 — self-heal Phase 2 dispatch leaked into read-only frozen 003"
    exit 1
fi
if grep -q 'FREEZE:' "$OUT18"; then
    fail "case 18: frozen 003 still contains FREEZE markers"
fi

# -----------------------------------------------------------------------------
# Test 19: /004-code-review.md exercising auto_fix_on_review_fail in both
# directions in a single case-pair (parallels 17/18 for the reviewer command).
# -----------------------------------------------------------------------------
# 19a: auto_fix_on_review_fail: true → self-heal Phase 2 heading present.
run_real_freeze "004-code-review.md" "$WORK/gw-fix-on.md" "$WORK/case19a.log"
OUT19A="$WORK/proj/.claude/commands/004-code-review.md"
[ -f "$OUT19A" ] || fail "case 19a: frozen 004-code-review.md not written"
if ! grep -q 'Phase 2 — Apply Fixes' "$OUT19A"; then
    echo "FAIL: case 19a — missing 'Phase 2 — Apply Fixes' heading in frozen 004"
    grep -n 'Phase 2' "$OUT19A" || true
    exit 1
fi
if grep -q 'Phase 2 — Read result (read-only mode)' "$OUT19A"; then
    echo "FAIL: case 19a — read-only Phase 2 heading leaked into self-heal-on frozen 004"
    exit 1
fi
if grep -q 'FREEZE:' "$OUT19A"; then
    fail "case 19a: frozen 004 still contains FREEZE markers"
fi

# 19b: auto_fix_on_review_fail: false → read-only Phase 2 heading present.
run_real_freeze "004-code-review.md" "$WORK/gw-fix-off.md" "$WORK/case19b.log"
OUT19B="$WORK/proj/.claude/commands/004-code-review.md"
[ -f "$OUT19B" ] || fail "case 19b: frozen 004-code-review.md not written"
if ! grep -q 'Phase 2 — Read result (read-only mode)' "$OUT19B"; then
    echo "FAIL: case 19b — missing read-only Phase 2 heading in frozen 004"
    grep -n 'Phase 2' "$OUT19B" || true
    exit 1
fi
if grep -q 'Phase 2 — Apply Fixes' "$OUT19B"; then
    echo "FAIL: case 19b — self-heal 'Apply Fixes' leaked into read-only frozen 004"
    exit 1
fi
if grep -q 'FREEZE:' "$OUT19B"; then
    fail "case 19b: frozen 004 still contains FREEZE markers"
fi

# Restore stashed plugin commands + ruleset so any subsequent additions to
# this test file start from the original baseline.
"$FREEZE" --reset --force > /dev/null 2>&1 || true
rm -f "$WORK/plugin/commands"/*.md
cp "$STASH_DIR"/*.md "$WORK/plugin/commands/" 2>/dev/null || true
mv "$WORK/proj/.claude/ruleset/git-workflow.md.case17bak" "$WORK/proj/.claude/ruleset/git-workflow.md"

echo "PASS: all freeze.sh self-tests"
exit 0
