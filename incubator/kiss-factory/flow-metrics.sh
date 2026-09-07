#!/usr/bin/env bash
# How long work takes to get through the factory, and how much of it comes back.
# Usage: flow-metrics.sh [owner/repo]
set -uo pipefail

repo="${1:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
owner="${repo%%/*}"
name="${repo##*/}"

query='
query($owner:String!,$repo:String!,$n:Int!){
 repository(owner:$owner,name:$repo){ pullRequest(number:$n){
   number state createdAt mergedAt headRefName
   timelineItems(first:100, itemTypes:[READY_FOR_REVIEW_EVENT,CONVERT_TO_DRAFT_EVENT]){
     nodes{ __typename
       ... on ReadyForReviewEvent{createdAt}
       ... on ConvertToDraftEvent{createdAt} } }
 }}}'

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
printf '%s' "$query" > "$work/q"

for n in $(gh pr list --repo "$repo" --state all --limit 200 \
             --json number,headRefName --jq '.[]|select(.headRefName|startswith("lane/"))|.number'); do
  gh api graphql -F query=@"$work/q" -F owner="$owner" -F repo="$name" -F n="$n" \
    | python3 -c 'import sys,json; json.dump(json.load(sys.stdin)["data"]["repository"]["pullRequest"], sys.stdout); print()'
done > "$work/prs.jsonl"

DATA="$work/prs.jsonl" python3 <<'PY'
import json, os, statistics as st
from datetime import datetime

def t(s): return datetime.fromisoformat(s.replace('Z','+00:00')) if s else None
def hrs(a,b): return (b-a).total_seconds()/3600 if a and b else None

rows=[]
for line in open(os.environ['DATA']):
    p=json.loads(line)
    ev=p['timelineItems']['nodes']
    ready=sorted(t(e['createdAt']) for e in ev if e['__typename']=='ReadyForReviewEvent')
    rows.append(dict(
        n=p['number'], created=t(p['createdAt']), merged=t(p['mergedAt']),
        ready=ready[0] if ready else None,
        bounces=sum(1 for e in ev if e['__typename']=='ConvertToDraftEvent')))

def show(label, xs, unit='h'):
    if xs:
        print(f"  {label:<34} n={len(xs):<3} median {st.median(xs):>5.1f} {unit}"
              f"   worst {max(xs):>5.1f} {unit}")

build=[hrs(r['created'], r['ready']) for r in rows]
gate =[hrs(r['ready'], r['merged'])  for r in rows]
lead =[hrs(r['created'], r['merged']) for r in rows]

print(f"lane pull requests: {len(rows)}   merged: {sum(1 for r in rows if r['merged'])}\n")
print("time, from opening the draft:")
show("building, until marked ready", [x for x in build if x is not None])
show("waiting to be merged", [x for x in gate if x is not None])
show("total, opened to merged", [x for x in lead if x is not None])

print("\nwork that came back (each bounce is a pull request returned to draft):")
done=[r for r in rows if r['ready'] and r['merged']]
for label, sel in (("merged within an hour of ready", lambda w: w < 1),
                   ("waited an hour or more",          lambda w: w >= 1)):
    grp=[r for r in done if sel(hrs(r['ready'], r['merged']))]
    if grp:
        b=sum(r['bounces'] for r in grp)
        print(f"  {label:<34} {len(grp):>2} pull requests, {b} bounce(s), {b/len(grp):.2f} each")
print(f"  {'total':<34} {sum(r['bounces'] for r in rows)} bounce(s) across {len(rows)}")

# The queue is the thing to watch: it is where the waiting happens, and waiting is
# what lets the base move under a finished pull request and turn it into rework.
events=[]
for r in done:
    events.append((r['ready'], 1)); events.append((r['merged'], -1))
events.sort()
cur=peak=0
for _,d in events:
    cur+=d; peak=max(peak,cur)
print(f"\n  most pull requests waiting at once: {peak}")
PY
