#!/usr/bin/env bash
# Lists comment blocks this branch ADDS to production source, for a human or an agent to judge.
# Usage: added-comments.sh <base-ref> [head-ref]
# Exits 0 always. A listed block is a candidate, not a violation.
set -uo pipefail

base="${1:?usage: added-comments.sh <base-ref> [head-ref]}"
head="${2:-HEAD}"

paths=(
  ':(glob)src/main/java/**/*.java'
  ':(glob)frontend/src/**/*.ts'
  ':(glob)frontend/src/**/*.tsx'
  ':(exclude,glob)**/*.test.ts'
  ':(exclude,glob)**/*.test.tsx'
  ':(exclude,glob)src/test/**'
)

# Every comment shape, including documentation on public types: the rule makes no
# exception for it, and the surrounding code being full of it is how it got that way.
comment='^[[:space:]]*(//|/\*|\*)'

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# Via files, not variables: on a large repository the base's comments run to
# megabytes, and an environment that size is rejected outright.
git diff -M "$base...$head" --unified=0 -- "${paths[@]}" > "$work/added"
git grep -I -n -E "$comment" "$base" -- "${paths[@]}" > "$work/existing" 2>/dev/null

ADDED="$work/added" EXISTING="$work/existing" python3 <<'PY'
import os, re, sys
from collections import defaultdict

MARKER = re.compile(r'^(//+|/\*+|\*+/?)')
IS_COMMENT = re.compile(r'^(//|/\*|\*)')
# Allowed by the rule: these change behaviour rather than explain it.
DIRECTIVE = re.compile(r'^//+\s*('
                       r'eslint-|@ts-|prettier-|noinspection|NOSONAR|CHECKSTYLE|'
                       r'biome-|oxlint-|c8 |v8 |istanbul )', re.I)

def norm(text):
    """Comment text with the marker, indentation and line breaks taken out, so the
    same sentence compares equal however it happens to be wrapped."""
    return re.sub(r'\s+', ' ', MARKER.sub('', text.strip())).strip()

# Every comment already on the base, joined per file into one unbroken string.
# Joining is the point: a sentence rewrapped across different lines is still a
# substring of the file it came from, and cannot match across a file boundary.
base_text = defaultdict(list)
for row in open(os.environ['EXISTING'], encoding='utf-8', errors='replace'):
    parts = row.rstrip('\n').split(':', 3)
    if len(parts) == 4:
        base_text[parts[1]].append(norm(parts[3]))
haystacks = [' '.join(v) for v in base_text.values()]

def already_on_base(text):
    return any(text in h for h in haystacks)

# Comment lines this branch adds, minus the ones whose text is already on the base.
# Judged one line at a time: a block can mix a sentence that was only rewrapped with
# one that was rewritten, and dropping or keeping the whole block gets one of them wrong.
new_lines, path, lineno = [], None, 0
for row in open(os.environ['ADDED'], encoding='utf-8', errors='replace'):
    row = row.rstrip('\n')
    if row.startswith('+++ b/'):
        path = row[6:]
    elif row.startswith('@@'):
        m = re.search(r'\+(\d+)', row)
        lineno = int(m.group(1)) if m else 0
    elif row.startswith('+'):
        text = row[1:].strip()
        if IS_COMMENT.match(text) and not DIRECTIVE.match(text):
            t = norm(text)
            if t and not already_on_base(t):
                new_lines.append((path, lineno, t))
        lineno += 1

# Print consecutive survivors together, so a candidate is read as the thought it is.
prev_path, prev_line = None, None
for path, lineno, text in new_lines:
    if path != prev_path or lineno != prev_line + 1:
        print(f"{path}:{lineno}")
    print(f"    {text}")
    prev_path, prev_line = path, lineno
PY
