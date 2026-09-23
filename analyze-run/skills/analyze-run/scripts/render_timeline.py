#!/usr/bin/env python3
"""Render an agent run timeline (schema analyze-run-timeline/1) as a self-contained HTML page.

Usage:
  python3 render_timeline.py timeline.json -o timeline.html [--md summary.md] [--gap-minutes 30]

The input format is described in ../references/timeline-schema.md. The script needs only the
Python 3.9+ standard library. It validates the input, computes the summary tables and writes one
HTML file; the timeline itself is drawn in the page by inline JavaScript so it can zoom.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

SCHEMA = "analyze-run-timeline/1"

# Order matters: the page colours these kinds with a colour-blind-safe palette validated in this order.
SPAN_KINDS = {
    "work": "Agent work",
    "check": "Checks (tests, validators)",
    "tool": "Long tool calls",
    "remote": "Remote jobs (CI, cloud)",
    "review": "Review",
    "wait-agent": "Waiting for another agent",
    "wait-user": "Waiting for the user",
    "blocked": "Blocked (environment / access)",
}
PASSIVE_KINDS = {"wait-user"}          # compressible: nothing runs while the user is away
WAIT_KINDS = {"wait-user", "wait-agent"}
EVENT_TYPES = {"pivot", "milestone", "message"}
SEVERITIES = {"high": "High", "medium": "Medium", "low": "Low"}
VERDICTS = {
    "healthy": "Healthy run — no material changes recommended",
    "friction": "Some friction — targeted changes recommended",
    "waste": "Significant avoidable time — changes recommended",
}
MAX_ITEMS = 200
MAX_TEXT = 300
MAX_SKILL_ROWS = 3
LINK_PREFIXES = ("https://", "http://", "file://")
NO_SKILL = "(no skill recorded)"


class TimelineError(Exception):
    pass


# ---------------------------------------------------------------------------- parsing

def parse_ts(value, where: str) -> datetime:
    if not isinstance(value, str):
        raise TimelineError(f"{where}: timestamp must be an ISO-8601 string, got {value!r}")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        ts = datetime.fromisoformat(text)
    except ValueError:
        raise TimelineError(f"{where}: not an ISO-8601 timestamp: {value!r}") from None
    if ts.tzinfo is None:
        raise TimelineError(f"{where}: timestamp needs a UTC offset or Z: {value!r}")
    return ts.astimezone(timezone.utc)


@dataclass
class Item:
    at: datetime | None
    text: str


@dataclass
class Span:
    agent: str
    start: datetime
    end: datetime
    kind: str
    label: str
    detail: str
    skill: str | None
    items: list


@dataclass
class SkillRun:
    agent: str
    name: str
    start: datetime
    end: datetime
    detail: str
    row: int = 0


@dataclass
class Event:
    id: str
    type: str
    at: datetime
    end: datetime | None
    agent: str
    to: str | None
    title: str
    detail: str
    category: str
    severity: str
    impact_min: float | None
    evidence: list
    occurrences: list


def parse_items(raw, where: str, problems: list) -> list:
    if raw is None:
        return []
    if not isinstance(raw, list):
        problems.append(f"{where}: items must be a list")
        return []
    items = []
    for j, it in enumerate(raw[:MAX_ITEMS]):
        if isinstance(it, str):
            items.append(Item(None, it[:MAX_TEXT]))
            continue
        if not isinstance(it, dict) or not isinstance(it.get("text"), str):
            problems.append(f"{where}.items[{j}]: needs a text")
            continue
        at = None
        if it.get("at"):
            try:
                at = parse_ts(it["at"], f"{where}.items[{j}].at")
            except TimelineError as e:
                problems.append(str(e))
                continue
        items.append(Item(at, it["text"][:MAX_TEXT]))
    return items


def load(data: dict) -> dict:
    """Validate the document and return normalised structures. Raises TimelineError listing every problem."""
    problems: list[str] = []

    def need(cond, msg):
        if not cond:
            problems.append(msg)

    need(data.get("schema") == SCHEMA, f"schema must be {SCHEMA!r}")
    need(isinstance(data.get("title"), str) and data["title"].strip(), "title is required")
    agents = data.get("agents")
    need(isinstance(agents, list) and agents, "agents must be a non-empty list")
    agents = agents if isinstance(agents, list) else []
    ids = [a.get("id") for a in agents if isinstance(a, dict)]
    need(len(ids) == len(agents), "every agent must be an object")
    need(len(set(ids)) == len(ids), f"agent ids must be unique: {ids}")
    for a in agents:
        if isinstance(a, dict):
            need(isinstance(a.get("id"), str) and a["id"], f"agent without id: {a}")
            need(isinstance(a.get("label"), str) and a["label"], f"agent {a.get('id')}: label is required")
            if a.get("parent") is not None:
                need(a["parent"] in ids, f"agent {a.get('id')}: unknown parent {a.get('parent')!r}")
    idset = set(ids)

    spans: list[Span] = []
    for i, s in enumerate(data.get("spans") or []):
        w = f"spans[{i}]"
        try:
            start, end = parse_ts(s.get("start"), w + ".start"), parse_ts(s.get("end"), w + ".end")
        except TimelineError as e:
            problems.append(str(e))
            continue
        need(end >= start, f"{w}: end is before start")
        need(s.get("agent") in idset, f"{w}: unknown agent {s.get('agent')!r}")
        need(s.get("kind") in SPAN_KINDS, f"{w}: kind must be one of {list(SPAN_KINDS)}, got {s.get('kind')!r}")
        need(s.get("skill") is None or isinstance(s.get("skill"), str), f"{w}: skill must be a skill name")
        spans.append(Span(s.get("agent"), start, max(start, end), s.get("kind"), str(s.get("label") or ""),
                          str(s.get("detail") or ""), s.get("skill") or None, parse_items(s.get("items"), w, problems)))

    skills: list[SkillRun] = []
    for i, k in enumerate(data.get("skills") or []):
        w = f"skills[{i}]"
        try:
            start, end = parse_ts(k.get("start"), w + ".start"), parse_ts(k.get("end"), w + ".end")
        except TimelineError as e:
            problems.append(str(e))
            continue
        need(end >= start, f"{w}: end is before start")
        need(k.get("agent") in idset, f"{w}: unknown agent {k.get('agent')!r}")
        need(isinstance(k.get("name"), str) and k["name"], f"{w}: name is required")
        skills.append(SkillRun(k.get("agent"), str(k.get("name") or ""), start, max(start, end), str(k.get("detail") or "")))

    catalog = {}
    raw_catalog = data.get("skill_catalog") or {}
    need(isinstance(raw_catalog, dict), "skill_catalog must be an object keyed by skill name")
    for name, entry in (raw_catalog.items() if isinstance(raw_catalog, dict) else []):
        entry = entry if isinstance(entry, dict) else {}
        url = entry.get("url")
        if url is not None:
            need(isinstance(url, str) and url.startswith(LINK_PREFIXES),
                 f"skill_catalog[{name!r}].url must start with one of {list(LINK_PREFIXES)}")
        catalog[name] = {k: str(entry[k]) for k in ("label", "description", "url") if entry.get(k)}

    events: list[Event] = []
    seen_ids: set[str] = set()
    for i, e in enumerate(data.get("events") or []):
        w = f"events[{i}]"
        try:
            at = parse_ts(e.get("at"), w + ".at")
            end = parse_ts(e["end"], w + ".end") if e.get("end") else None
            occurrences = [parse_ts(o, f"{w}.occurrences[{j}]") for j, o in enumerate(e.get("occurrences") or [])]
        except TimelineError as err:
            problems.append(str(err))
            continue
        etype = e.get("type")
        need(etype in EVENT_TYPES, f"{w}: type must be one of {sorted(EVENT_TYPES)}, got {etype!r}")
        need(e.get("agent") in idset, f"{w}: unknown agent {e.get('agent')!r}")
        need(isinstance(e.get("title"), str) and e["title"], f"{w}: title is required")
        if etype == "message":
            need(e.get("to") in idset, f"{w}: message needs a known 'to' agent, got {e.get('to')!r}")
        eid = str(e.get("id") or "")
        if etype == "pivot":
            need(bool(eid), f"{w}: a pivot needs an id such as 'P1'")
            need(e.get("severity") in SEVERITIES, f"{w}: severity must be one of {list(SEVERITIES)}")
        if eid:
            need(eid not in seen_ids, f"{w}: duplicate event id {eid!r}")
            seen_ids.add(eid)
        if end is not None:
            need(end >= at, f"{w}: end is before at")
        impact = e.get("impact_min")
        need(impact is None or isinstance(impact, (int, float)), f"{w}: impact_min must be a number")
        ev = e.get("evidence") or []
        events.append(Event(eid, etype, at, end, e.get("agent"), e.get("to"), str(e.get("title") or ""),
                            str(e.get("detail") or ""), str(e.get("category") or ""),
                            e.get("severity") or "low", impact, ev if isinstance(ev, list) else [str(ev)],
                            sorted(occurrences)))

    need(spans or events, "the timeline needs at least one span or event")

    phases = []
    for i, p in enumerate(data.get("phases") or []):
        w = f"phases[{i}]"
        try:
            start, end = parse_ts(p.get("start"), w + ".start"), parse_ts(p.get("end"), w + ".end")
        except TimelineError as e:
            problems.append(str(e))
            continue
        need(end >= start, f"{w}: end is before start")
        need(isinstance(p.get("label"), str) and p["label"], f"{w}: label is required")
        phases.append({"id": str(p.get("id") or p.get("label")), "label": str(p.get("label") or ""),
                       "start": start, "end": max(start, end)})

    analysis = data.get("analysis") or {}
    verdict = analysis.get("verdict")
    if verdict is not None:
        need(verdict in VERDICTS, f"analysis.verdict must be one of {list(VERDICTS)}")
    pivot_ids = {e.id for e in events if e.type == "pivot"}
    for i, r in enumerate(analysis.get("recommendations") or []):
        need(isinstance(r.get("title"), str) and r["title"], f"analysis.recommendations[{i}]: title is required")
        for ref in r.get("evidence") or []:
            need(ref in pivot_ids, f"analysis.recommendations[{i}]: evidence {ref!r} is not a pivot id")

    tzname = data.get("timezone")
    tz = None
    if tzname:
        if ZoneInfo is None:
            problems.append("timezone given but zoneinfo is unavailable (needs Python 3.9+)")
        else:
            try:
                tz = ZoneInfo(tzname)
            except Exception:
                problems.append(f"unknown timezone {tzname!r}")
    if problems:
        raise TimelineError("\n".join(problems))

    stack_skills(skills)
    return {
        "title": data["title"], "subject": data.get("subject") or {}, "tz": tz or datetime.now().astimezone().tzinfo,
        "tzname": tzname or "local", "tz_iana": tzname, "agents": agents, "spans": spans, "skills": skills,
        "catalog": catalog, "events": events, "phases": phases, "analysis": analysis,
        "sources": data.get("sources") or [], "notes": data.get("notes") or [],
    }


# ---------------------------------------------------------------------------- time maths

def merge(intervals):
    out = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def total_minutes(intervals) -> float:
    return sum((e - s).total_seconds() for s, e in merge(intervals)) / 60.0


def overlap_minutes(a0, a1, b0, b1) -> float:
    return max(0.0, (min(a1, b1) - max(a0, b0)).total_seconds() / 60.0)


def fmt_dur(minutes: float | None) -> str:
    if minutes is None:
        return "—"
    if minutes < 1:
        return f"{max(0, round(minutes * 60))}s"
    m = int(round(minutes))
    if m < 60:
        return f"{m}m"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}h {m:02d}m"
    d, h = divmod(h, 24)
    return f"{d}d {h}h"


def find_gaps(t0, t1, busy, gap_minutes: float):
    """Stretches longer than gap_minutes with no busy interval; the page collapses them."""
    busy = merge([(max(s, t0), min(e, t1)) for s, e in busy if e >= t0 and s <= t1])
    gaps, cursor = [], t0
    for s, e in busy:
        if (s - cursor).total_seconds() / 60 > gap_minutes:
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if (t1 - cursor).total_seconds() / 60 > gap_minutes:
        gaps.append((cursor, t1))
    return gaps


def stack_skills(skills):
    """Give nested or overlapping skill runs of one agent separate rows (outermost first)."""
    by_agent: dict = {}
    for k in sorted(skills, key=lambda k: (k.start, -(k.end - k.start).total_seconds())):
        rows = by_agent.setdefault(k.agent, [])
        for r, row_end in enumerate(rows):
            if k.start >= row_end:
                k.row = r
                rows[r] = k.end
                break
        else:
            k.row = min(len(rows), MAX_SKILL_ROWS - 1)
            if len(rows) < MAX_SKILL_ROWS:
                rows.append(k.end)
            else:
                rows[k.row] = max(rows[k.row], k.end)


def span_skill(doc, span) -> str | None:
    """The span's own skill, else the innermost (shortest) skill running at its midpoint in its lane, or in
    the nearest ancestor lane: a subagent or background job works for the skill its parent is running."""
    if span.skill:
        return span.skill
    parents = {a["id"]: a.get("parent") for a in doc["agents"]}
    mid = span.start + (span.end - span.start) / 2
    agent, seen = span.agent, set()
    while agent and agent not in seen:
        seen.add(agent)
        covering = [k for k in doc["skills"] if k.agent == agent and k.start <= mid <= k.end]
        if covering:
            return min(covering, key=lambda k: k.end - k.start).name
        agent = parents.get(agent)
    return None


def compute_stats(doc):
    spans = doc["spans"]
    events = doc["events"]
    times = [s.start for s in spans] + [s.end for s in spans] + [e.at for e in events] + \
            [e.end for e in events if e.end] + [p["start"] for p in doc["phases"]] + \
            [p["end"] for p in doc["phases"]] + [k.start for k in doc["skills"]] + [k.end for k in doc["skills"]]
    t0, t1 = min(times), max(times)
    active = [(s.start, s.end) for s in spans if s.kind not in WAIT_KINDS]
    per_agent = {}
    for a in doc["agents"]:
        mine = [(s.start, s.end) for s in spans if s.agent == a["id"] and s.kind not in WAIT_KINDS]
        per_agent[a["id"]] = total_minutes(mine)
    pivots = [e for e in events if e.type == "pivot"]
    return {
        "t0": t0, "t1": t1,
        "wall": (t1 - t0).total_seconds() / 60,
        "active": total_minutes(active),
        "agent_sum": sum(per_agent.values()),
        "wait_user": total_minutes([(s.start, s.end) for s in spans if s.kind == "wait-user"]),
        "checks_remote": total_minutes([(s.start, s.end) for s in spans if s.kind in ("check", "remote")]),
        "blocked": total_minutes([(s.start, s.end) for s in spans if s.kind == "blocked"]),
        "pivots": pivots,
        "impact": sum(p.impact_min or 0 for p in pivots),
        "per_agent": per_agent,
        "skills": sorted({k.name for k in doc["skills"]} | {s.skill for s in spans if s.skill}),
    }


def kind_minutes_by(doc, key):
    """Minutes per kind for each phase, agent or skill. Spans are clipped to phase windows; a span counts
    towards the skill that was active at its midpoint."""
    table: dict = {}
    if key == "agent":
        for s in doc["spans"]:
            row = table.setdefault(s.agent, {})
            row[s.kind] = row.get(s.kind, 0) + (s.end - s.start).total_seconds() / 60
        return table
    if key == "skill":
        for s in doc["spans"]:
            row = table.setdefault(span_skill(doc, s) or NO_SKILL, {})
            row[s.kind] = row.get(s.kind, 0) + (s.end - s.start).total_seconds() / 60
        return dict(sorted(table.items(), key=lambda kv: (kv[0] == NO_SKILL, -sum(kv[1].values()))))
    for p in doc["phases"]:
        row = table.setdefault(p["id"], {})
        for s in doc["spans"]:
            m = overlap_minutes(s.start, s.end, p["start"], p["end"])
            if m:
                row[s.kind] = row.get(s.kind, 0) + m
    return table


# ---------------------------------------------------------------------------- page

def esc(text) -> str:
    return html.escape(str(text), quote=True)


def local(ts: datetime, tz) -> datetime:
    return ts.astimezone(tz)


def agent_rows(agents):
    """Order agents so each child lane sits directly under its parent; return (agent, depth) pairs."""
    by_parent: dict = {}
    for a in agents:
        by_parent.setdefault(a.get("parent"), []).append(a)
    out = []

    def walk(parent, depth):
        for a in by_parent.get(parent, []):
            out.append((a, depth))
            walk(a["id"], depth + 1)
    walk(None, 0)
    return out


def ms(ts: datetime) -> int:
    return int(ts.timestamp() * 1000)


def page_data(doc, stats, gap_minutes: float) -> dict:
    """Everything the in-page timeline needs, with times as epoch milliseconds."""
    busy = [(s.start, s.end) for s in doc["spans"] if s.kind not in PASSIVE_KINDS]
    busy += [(e.at, e.at) for e in doc["events"]]  # an event's extent is not activity (a wait can span a night)
    gaps = find_gaps(stats["t0"], stats["t1"], busy, gap_minutes)
    agents = []
    for a, depth in agent_rows(doc["agents"]):
        active = stats["per_agent"].get(a["id"], 0)
        meta = " · ".join(x for x in (a.get("runtime"), a.get("role"), fmt_dur(active) if active else "") if x)
        agents.append({"id": a["id"], "label": a["label"], "meta": meta, "depth": depth,
                       "session": a.get("session") or "", "human": a.get("runtime") == "human"})
    return {
        "t0": ms(stats["t0"]), "t1": ms(stats["t1"]), "tz": doc["tz_iana"],
        "gaps": [[ms(s), ms(e)] for s, e in gaps],
        "kinds": SPAN_KINDS, "severities": SEVERITIES,
        "agents": agents,
        "phases": [{"l": p["label"], "s": ms(p["start"]), "e": ms(p["end"])} for p in doc["phases"]],
        "spans": [{"a": s.agent, "s": ms(s.start), "e": ms(s.end), "k": s.kind, "l": s.label, "d": s.detail,
                   "sk": span_skill(doc, s), "it": [[ms(i.at) if i.at else None, i.text] for i in s.items]}
                  for s in sorted(doc["spans"], key=lambda s: (s.start, s.end))],
        "skills": [{"a": k.agent, "n": k.name, "s": ms(k.start), "e": ms(k.end), "r": k.row, "d": k.detail}
                   for k in doc["skills"]],
        "catalog": doc["catalog"],
        "events": [{"ty": e.type, "id": e.id, "a": e.agent, "to": e.to, "at": ms(e.at),
                    "end": ms(e.end) if e.end else None, "ti": e.title, "d": e.detail, "c": e.category,
                    "sev": e.severity, "imp": e.impact_min, "occ": [ms(o) for o in e.occurrences],
                    "ev": [str(x) for x in e.evidence]} for e in doc["events"]],
    }


def stacked_table(title, rows, labels, caption):
    kinds = [k for k in SPAN_KINDS if any(r.get(k) for r in rows.values())]
    if not kinds:
        return ""
    maxtotal = max((sum(r.values()) for r in rows.values()), default=0) or 1
    head = "".join(f"<th>{esc(SPAN_KINDS[k])}</th>" for k in kinds)
    body = []
    for rid, row in rows.items():
        total = sum(row.values())
        bar = "".join(
            f'<span class="seg k-{k}" style="width:{row.get(k, 0) / maxtotal * 100:.2f}%" '
            f'title="{esc(SPAN_KINDS[k] + " · " + fmt_dur(row.get(k, 0)))}"></span>'
            for k in kinds if row.get(k))
        cells = "".join(f"<td>{fmt_dur(row.get(k)) if row.get(k) else ''}</td>" for k in kinds)
        body.append(f'<tr><th scope="row">{esc(labels.get(rid, rid))}</th><td class="barcell"><div class="bar">{bar}</div></td>'
                    f'<td class="num">{fmt_dur(total)}</td>{cells}</tr>')
    return (f'<section><h2>{esc(title)}</h2><p class="caption">{esc(caption)}</p><div class="table-wrap"><table>'
            f'<thead><tr><th></th><th class="barcell">Share</th><th>Total</th>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div></section>')


def render_html(doc, gap_minutes: float = 30.0) -> str:
    stats = compute_stats(doc)
    tz = doc["tz"]
    labels = {a["id"]: a["label"] for a in doc["agents"]}
    data = page_data(doc, stats, gap_minutes)

    subject_bits = " · ".join(esc(f"{k}: {v}") for k, v in doc["subject"].items() if v)
    window = f"{local(stats['t0'], tz):%a %d %b %H:%M} → {local(stats['t1'], tz):%a %d %b %H:%M} ({esc(doc['tzname'])})"
    parallel = stats["agent_sum"] / stats["active"] if stats["active"] else 0
    sev_counts = {k: sum(1 for p in stats["pivots"] if p.severity == k) for k in SEVERITIES}
    tiles = [
        ("Wall clock", fmt_dur(stats["wall"]), "first to last recorded activity"),
        ("Agent activity", fmt_dur(stats["active"]),
         f"{fmt_dur(stats['agent_sum'])} summed over agents" + (f" · ×{parallel:.1f} parallel" if parallel >= 1.05 else "")),
        ("Waiting for the user", fmt_dur(stats["wait_user"]), "gates, questions, answers"),
    ]
    if stats["checks_remote"]:
        tiles.append(("Checks & remote jobs", fmt_dur(stats["checks_remote"]), "tests, validators, CI and other remote jobs"))
    tiles += [
        ("Pivot events", str(len(stats["pivots"])),
         " · ".join(f"{n} {SEVERITIES[k].lower()}" for k, n in sev_counts.items() if n) or "none"),
    ]
    if stats["impact"]:
        tiles.append(("Estimated impact", "~" + fmt_dur(stats["impact"]), "time the pivots cost (estimate)"))
    tiles_html = "".join(f'<div class="tile"><div class="tile-label">{esc(a)}</div><div class="tile-value">{esc(b)}</div>'
                         f'<div class="tile-sub">{esc(c)}</div></div>' for a, b, c in tiles)

    legend = "".join(f'<span class="key"><span class="sw k-{k}"></span>{esc(v)}</span>'
                     for k, v in SPAN_KINDS.items() if any(s.kind == k for s in doc["spans"]))
    if doc["skills"]:
        legend += '<span class="key"><span class="sw-skill">skill</span>Skill in use</span>'
    legend += ('<span class="key"><span class="sw-pivot sev-high">1</span>Pivot event (colour = severity)</span>'
               '<span class="key"><span class="sw-ms"></span>Milestone</span>')
    if any(e.type == "message" for e in doc["events"]):
        legend += '<span class="key"><span class="sw-msg"></span>Message</span>'
    if data["gaps"]:
        legend += '<span class="key"><span class="sw-gap"></span>Collapsed idle gap</span>'

    pivots_html = []
    for p in sorted(stats["pivots"], key=lambda e: e.at):
        ev = "".join(f"<li><code>{esc(x)}</code></li>" for x in p.evidence)
        lasted = f" · lasted {fmt_dur((p.end - p.at).total_seconds() / 60)}" if p.end else ""
        if len(p.occurrences) > 1:
            lasted += (f" · {len(p.occurrences)} occurrences, {local(p.occurrences[0], tz):%H:%M}–"
                       f"{local(p.occurrences[-1], tz):%H:%M}")
        impact = f" · impact ~{fmt_dur(p.impact_min)}" if p.impact_min else ""
        pivots_html.append(
            f'<li class="pivot-card sev-{p.severity}" id="pivot-{esc(p.id)}">'
            f'<div class="pc-head"><span class="badge sev-{p.severity}">{esc(p.id)}</span>'
            f'<span class="sev-label">{esc(SEVERITIES[p.severity])}</span>'
            f'<strong>{esc(p.title)}</strong></div>'
            f'<div class="pc-meta">{local(p.at, tz):%a %H:%M} · {esc(labels.get(p.agent, p.agent))}'
            f'{" · " + esc(p.category) if p.category else ""}{lasted}{impact}</div>'
            f'{"<p>" + esc(p.detail) + "</p>" if p.detail else ""}'
            f'{"<ul class=evidence>" + ev + "</ul>" if ev else ""}</li>')
    pivots_section = (f'<section><h2>Pivot events</h2><ol class="pivots">{"".join(pivots_html)}</ol></section>'
                      if pivots_html else
                      '<section><h2>Pivot events</h2><p class="caption">None recorded.</p></section>')

    analysis = doc["analysis"]
    rec_html = ""
    if analysis:
        verdict = analysis.get("verdict")
        items = []
        for i, r in enumerate(analysis.get("recommendations") or [], 1):
            refs = " ".join(f'<a class="badge-link" href="#pivot-{esc(x)}">{esc(x)}</a>' for x in r.get("evidence") or [])
            facts = [("Change", r.get("change")), ("Where", r.get("target")), ("Expected saving", r.get("saving")),
                     ("Cost / risk", r.get("cost")), ("Confidence", r.get("confidence"))]
            dl = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in facts if v)
            items.append(f'<li class="rec"><h3>{i}. {esc(r["title"])}</h3>'
                         f'{"<p>" + esc(r.get("why")) + "</p>" if r.get("why") else ""}'
                         f'{"<p class=refs>Evidence: " + refs + "</p>" if refs else ""}<dl>{dl}</dl></li>')
        obs = "".join(f"<li>{esc(o)}</li>" for o in analysis.get("observations") or [])
        rec_html = (f'<section><h2>Assessment</h2>'
                    + (f'<div class="verdict v-{esc(verdict)}"><strong>{esc(VERDICTS[verdict])}</strong>'
                       f'{"<p>" + esc(analysis.get("summary")) + "</p>" if analysis.get("summary") else ""}</div>'
                       if verdict else "")
                    + (f'<h3 class="sub">Recommendations</h3><ol class="recs">{"".join(items)}</ol>' if items else "")
                    + (f'<h3 class="sub">Observations (no action proposed)</h3><ul class="obs">{obs}</ul>' if obs else "")
                    + '</section>')

    phase_labels = {p["id"]: p["label"] for p in doc["phases"]}
    tables = ""
    if doc["phases"]:
        tables += stacked_table("Where the time went — by phase", kind_minutes_by(doc, "phase"), phase_labels,
                                "Span time clipped to each phase. Parallel agents add up, so a phase can exceed its wall-clock length.")
    if stats["skills"]:
        tables += stacked_table("Where the time went — by skill", kind_minutes_by(doc, "skill"), {},
                                "Each span counts towards the skill that was active in its lane at that moment.")
    tables += stacked_table("Where the time went — by agent", kind_minutes_by(doc, "agent"), labels,
                            "Raw span time per agent, including waits.")

    notes = "".join(f"<li>{esc(n)}</li>" for n in doc["notes"])
    sources = "".join(
        f'<li><code>{esc(s.get("path") or s.get("ref") or "")}</code> {esc(" · ".join(str(s.get(k)) for k in ("runtime", "role", "note") if s.get(k)))}</li>'
        for s in doc["sources"])
    method = (f'<section><h2>Sources and caveats</h2>'
              + (f'<ul class="notes">{notes}</ul>' if notes else "")
              + (f'<details><summary>{len(doc["sources"])} source(s)</summary><ul class="sources">{sources}</ul></details>' if sources else "")
              + f'<p class="caption">Idle stretches longer than {gap_minutes:g} minutes with no agent activity are collapsed on the timeline; '
                f'durations everywhere are real. Times shown in {esc(doc["tzname"])}.</p></section>')

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    parts = {
        "__TITLE__": esc(doc["title"]), "__SUBJECT__": subject_bits, "__WINDOW__": window, "__TILES__": tiles_html,
        "__LEGEND__": legend, "__RECS__": rec_html, "__PIVOTS__": pivots_section, "__TABLES__": tables,
        "__METHOD__": method,
    }
    # One pass, so text coming from the timeline is never scanned for tokens again.
    page = re.sub(r"__(TITLE|SUBJECT|WINDOW|TILES|LEGEND|RECS|PIVOTS|TABLES|METHOD)__",
                  lambda m: parts[m.group(0)], HTML_TEMPLATE)
    marker = 'id="timeline-data">__DATA__<'
    return page.replace(marker, marker.replace("__DATA__", payload), 1)


def render_markdown(doc) -> str:
    stats = compute_stats(doc)
    tz = doc["tz"]
    labels = {a["id"]: a["label"] for a in doc["agents"]}
    out = [f"# {doc['title']}", ""]
    if doc["subject"]:
        out += [" · ".join(f"{k}: {v}" for k, v in doc["subject"].items() if v), ""]
    out += [f"- Wall clock: {fmt_dur(stats['wall'])} ({local(stats['t0'], tz):%Y-%m-%d %H:%M} → {local(stats['t1'], tz):%Y-%m-%d %H:%M}, {doc['tzname']})",
            f"- Agent activity: {fmt_dur(stats['active'])} (summed over agents {fmt_dur(stats['agent_sum'])})",
            f"- Waiting for the user: {fmt_dur(stats['wait_user'])}"]
    if stats["checks_remote"]:
        out.append(f"- Checks & remote jobs: {fmt_dur(stats['checks_remote'])}")
    out += [f"- Pivot events: {len(stats['pivots'])}" + (f", estimated impact ~{fmt_dur(stats['impact'])}" if stats["impact"] else ""),
            ""]
    if doc["phases"]:
        out += ["| Phase | Start | Length |", "|---|---|---|"]
        out += [f"| {p['label']} | {local(p['start'], tz):%a %H:%M} | {fmt_dur((p['end'] - p['start']).total_seconds() / 60)} |"
                for p in doc["phases"]]
        out.append("")
    if stats["skills"]:
        table = kind_minutes_by(doc, "skill")
        kinds = [k for k in SPAN_KINDS if any(r.get(k) for r in table.values())]
        out += ["| Skill | Time | " + " | ".join(SPAN_KINDS[k] for k in kinds) + " |",
                "|---|---|" + "---|" * len(kinds)]
        for name, row in table.items():
            out.append(f"| {name} | {fmt_dur(sum(row.values()))} | "
                       + " | ".join(fmt_dur(row[k]) if row.get(k) else "" for k in kinds) + " |")
        out.append("")
    if stats["pivots"]:
        out += ["## Pivot events", ""]
        for p in sorted(stats["pivots"], key=lambda e: e.at):
            impact = f", impact ~{fmt_dur(p.impact_min)}" if p.impact_min else ""
            if len(p.occurrences) > 1:
                impact = f", {len(p.occurrences)} occurrences" + impact
            out.append(f"- **{p.id} · {p.title}** — {local(p.at, tz):%a %H:%M}, {labels.get(p.agent, p.agent)}, "
                       f"{SEVERITIES[p.severity].lower()}{impact}. {p.detail}".rstrip())
        out.append("")
    analysis = doc["analysis"]
    if analysis:
        out += ["## Assessment", ""]
        if analysis.get("verdict"):
            out += [f"**{VERDICTS[analysis['verdict']]}.** {analysis.get('summary') or ''}".rstrip(), ""]
        for i, r in enumerate(analysis.get("recommendations") or [], 1):
            out.append(f"{i}. **{r['title']}**" + (f" — {r['why']}" if r.get("why") else ""))
            for k, label in (("change", "Change"), ("target", "Where"), ("saving", "Expected saving"),
                             ("cost", "Cost / risk"), ("confidence", "Confidence")):
                if r.get(k):
                    out.append(f"   - {label}: {r[k]}")
            if r.get("evidence"):
                out.append(f"   - Evidence: {', '.join(r['evidence'])}")
        if analysis.get("observations"):
            out += ["", "Observations (no action proposed):"] + [f"- {o}" for o in analysis["observations"]]
        out.append("")
    if doc["notes"]:
        out += ["## Caveats", ""] + [f"- {n}" for n in doc["notes"]] + [""]
    return "\n".join(out)


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>__TITLE__</title>
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --surface-2: #f0efec;
  --text: #0b0b0b; --text-2: #52514e; --text-muted: #6f6e69;
  --grid: #e1e0d9; --axis: #c3c2b7; --ring: rgba(11,11,11,0.10);
  --k-work: #2a78d6; --k-check: #eb6834; --k-tool: #1baf7a; --k-remote: #eda100; --k-review: #e87ba4; --k-wait-agent: #4a3aa7;
  --wait-fill: #f0efec; --wait-ink: #c3c2b7; --blocked-fill: #fbe9e1;
  --status-good: #0ca30c; --status-warning: #fab219; --status-serious: #ec835a; --status-critical: #d03b3b;
  --phase-fill: #ecebe6; --phase-band: rgba(11,11,11,0.025);
  --skill-fill: #e7e5df; --skill-ink: #b3b1a8; --brush: rgba(42,120,214,0.14);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --surface-2: #232321;
    --text: #ffffff; --text-2: #c3c2b7; --text-muted: #9a9890;
    --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10);
    --k-work: #3987e5; --k-check: #d95926; --k-tool: #199e70; --k-remote: #c98500; --k-review: #d55181; --k-wait-agent: #9085e9;
    --wait-fill: #232321; --wait-ink: #45443f; --blocked-fill: #3a2219;
    --phase-fill: #2a2a27; --phase-band: rgba(255,255,255,0.03);
    --skill-fill: #2f2e2b; --skill-ink: #4a4944; --brush: rgba(57,135,229,0.22);
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --surface-2: #232321;
  --text: #ffffff; --text-2: #c3c2b7; --text-muted: #9a9890;
  --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10);
  --k-work: #3987e5; --k-check: #d95926; --k-tool: #199e70; --k-remote: #c98500; --k-review: #d55181; --k-wait-agent: #9085e9;
  --wait-fill: #232321; --wait-ink: #45443f; --blocked-fill: #3a2219;
  --phase-fill: #2a2a27; --phase-band: rgba(255,255,255,0.03);
  --skill-fill: #2f2e2b; --skill-ink: #4a4944; --brush: rgba(57,135,229,0.22);
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--text);
  font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1280px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 22px; margin: 0 0 4px; }
h2 { font-size: 16px; margin: 32px 0 8px; }
h3.sub { font-size: 14px; margin: 20px 0 8px; color: var(--text-2); }
.subject, .window, .caption { color: var(--text-2); margin: 2px 0; }
.caption { font-size: 12px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 20px 0; }
.tile { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; padding: 12px 14px; }
.tile-label { font-size: 12px; color: var(--text-2); }
.tile-value { font-size: 24px; font-weight: 600; margin: 2px 0; }
.tile-sub { font-size: 12px; color: var(--text-muted); }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 12px; color: var(--text-2); margin: 8px 0 10px; }
.key { display: inline-flex; align-items: center; gap: 6px; }
.sw { width: 18px; height: 10px; border-radius: 3px; display: inline-block; flex: none; }
.sw-skill { font-size: 9px; font-weight: 600; padding: 0 5px; border-radius: 2px; background: var(--skill-fill);
  border: 1px solid var(--skill-ink); color: var(--text-2); line-height: 12px; }
.sw-pivot { width: 16px; height: 16px; border-radius: 50%; color: #fff; font-size: 10px; font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center; }
.sw-ms { width: 9px; height: 9px; transform: rotate(45deg); background: var(--text-2); display: inline-block; }
.sw-msg { width: 18px; height: 0; border-top: 1.5px solid var(--text-muted); display: inline-block; }
.sw-gap { width: 14px; height: 12px; border-left: 1.5px solid var(--axis); border-right: 1.5px solid var(--axis);
  background: var(--surface-2); display: inline-block; }
.tl-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; margin: 4px 0 8px; font-size: 12px; }
.zoom { display: inline-flex; border: 1px solid var(--ring); border-radius: 8px; overflow: hidden; background: var(--surface); }
.zoom button { font: inherit; color: var(--text); background: none; border: 0; padding: 5px 11px; cursor: pointer; }
.zoom button + button { border-left: 1px solid var(--ring); }
.zoom button:hover { background: var(--surface-2); }
.zoom button:focus-visible { outline: 2px solid var(--k-work); outline-offset: -2px; }
.tl-status { color: var(--text); font-variant-numeric: tabular-nums; }
.tl-hint { color: var(--text-muted); }
.overview { background: var(--surface); border: 1px solid var(--ring); border-radius: 8px; margin-bottom: 8px;
  cursor: pointer; touch-action: none; }
.overview svg { display: block; }
.ov-view { fill: var(--brush); stroke: var(--k-work); stroke-width: 1.5; }
.timeline { display: grid; grid-template-columns: 200px minmax(0, 1fr); background: var(--surface);
  border: 1px solid var(--ring); border-radius: 10px; overflow: hidden; }
.labels { border-right: 1px solid var(--grid); }
.lane-label { display: flex; flex-direction: column; justify-content: center; padding: 0 10px;
  border-bottom: 1px solid var(--grid); overflow: hidden; }
.lane-label .name { font-weight: 600; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lane-label .meta { font-size: 11px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lane-label.d1, .lane-label.d2, .lane-label.d3 { padding-left: 22px; }
.lane-label.d1 .name, .lane-label.d2 .name, .lane-label.d3 .name { font-weight: 500; font-size: 12px; }
.scroller { overflow-x: auto; outline: none; }
svg.track { display: block; user-select: none; -webkit-user-select: none; }
.phase { fill: var(--phase-fill); cursor: pointer; }
.phase-bg { fill: var(--phase-band); }
.phase-label { font-size: 11px; font-weight: 600; fill: var(--text-2); pointer-events: none; }
.lane-line { stroke: var(--grid); stroke-width: 1; }
.grid { stroke: var(--grid); stroke-width: 1; }
.tick { font-size: 11px; fill: var(--text-muted); text-anchor: middle; font-variant-numeric: tabular-nums; pointer-events: none; }
.tick.day { font-weight: 600; fill: var(--text-2); text-anchor: start; }
.axis-hit { fill: transparent; cursor: col-resize; }
.brush { fill: var(--brush); stroke: var(--k-work); stroke-width: 1; pointer-events: none; }
.gap { fill: var(--surface-2); opacity: 0.92; }
.gap-edge { stroke: var(--axis); stroke-width: 1.5; fill: none; pointer-events: none; }
.gap-label { font-style: italic; }
.skill { fill: var(--skill-fill); stroke: var(--skill-ink); stroke-width: 1; cursor: pointer; }
.skill:hover { stroke: var(--text-2); }
.skill-label { font-size: 9px; font-weight: 600; fill: var(--text-2); pointer-events: none; }
.span { stroke: var(--surface); stroke-width: 1; cursor: pointer; }
.span:hover { stroke: var(--text); }
.k-work { fill: var(--k-work); background: var(--k-work); }
.k-check { fill: var(--k-check); background: var(--k-check); }
.k-tool { fill: var(--k-tool); background: var(--k-tool); }
.k-remote { fill: var(--k-remote); background: var(--k-remote); }
.k-review { fill: var(--k-review); background: var(--k-review); }
.k-wait-agent { fill: var(--k-wait-agent); background: var(--k-wait-agent); opacity: 0.55; }
.k-wait-user { fill: url(#hatch-wait); background: repeating-linear-gradient(45deg, var(--wait-ink) 0 2px, var(--wait-fill) 2px 6px); }
.k-blocked { fill: url(#hatch-blocked); background: repeating-linear-gradient(45deg, var(--status-serious) 0 2px, var(--blocked-fill) 2px 6px); }
.item-ticks { stroke: var(--surface); stroke-width: 1; opacity: 0.8; pointer-events: none; }
.span-label { font-size: 10px; fill: var(--text-2); pointer-events: none; }
.msg { stroke: var(--text-muted); stroke-width: 1.2; pointer-events: none; }
.msg-dot { fill: var(--surface); stroke: var(--text-muted); stroke-width: 1.5; cursor: pointer; }
.milestone { fill: var(--text-2); stroke: var(--surface); stroke-width: 1.5; cursor: pointer; }
.pivot { cursor: pointer; }
.pivot circle { stroke: var(--surface); stroke-width: 2; }
.pivot text { font-size: 10px; font-weight: 700; text-anchor: middle; fill: #fff; pointer-events: none; }
.pivot.sev-high circle, .sw-pivot.sev-high, .badge.sev-high, .pivot-extent.sev-high { fill: var(--status-critical); background: var(--status-critical); }
.pivot.sev-medium circle, .badge.sev-medium, .pivot-extent.sev-medium { fill: var(--status-serious); background: var(--status-serious); }
.pivot.sev-low circle, .badge.sev-low, .pivot-extent.sev-low { fill: var(--text-muted); background: var(--text-muted); }
.pivot.sev-medium text { fill: #1a1a19; }
.pivot-extent { pointer-events: none; }
.pivot-rule { stroke: var(--status-critical); stroke-width: 1; opacity: 0.35; pointer-events: none; }
.pivot:focus { outline: none; }
.pivot:focus circle, .pivot:hover circle { stroke: var(--text); }
#tip { position: fixed; z-index: 20; max-width: 360px; background: var(--text); color: var(--surface);
  padding: 6px 9px; border-radius: 7px; font-size: 12px; white-space: pre-line; pointer-events: none;
  box-shadow: 0 4px 16px rgba(0,0,0,0.2); display: none; }
#pop { position: fixed; z-index: 30; width: min(440px, calc(100vw - 16px)); max-height: min(70vh, 560px); overflow: auto;
  background: var(--surface); color: var(--text); border: 1px solid var(--ring); border-radius: 12px; padding: 12px 14px 14px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.25); font-size: 13px; }
#pop[hidden] { display: none; }
.pop-close { position: sticky; top: 0; float: right; font: inherit; font-size: 16px; line-height: 1; border: 0;
  background: none; color: var(--text-muted); cursor: pointer; padding: 2px 4px; }
.pop-head { display: flex; align-items: center; gap: 8px; padding-right: 20px; }
.pop-head strong { font-size: 14px; }
.pop-meta { color: var(--text-muted); font-size: 12px; margin: 2px 0 8px; font-variant-numeric: tabular-nums; }
.pop-row { display: grid; grid-template-columns: 64px 1fr; gap: 8px; font-size: 12px; margin: 3px 0; }
.pop-row > span:first-child { color: var(--text-muted); }
.pop-skill { background: var(--surface-2); border-radius: 8px; padding: 8px 10px; margin: 6px 0 8px; }
.pop-tag { font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }
.pop-desc { color: var(--text-2); font-size: 12px; margin: 2px 0 4px; }
.pop-skill a, #pop a { color: var(--k-work); font-size: 12px; }
.pop-sub { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; margin: 10px 0 4px; }
.pop-items { list-style: none; padding: 0; margin: 0; font-size: 12px; }
.pop-items li { display: grid; grid-template-columns: 62px 1fr; gap: 8px; padding: 3px 0; border-top: 1px solid var(--grid); }
.pop-items time { color: var(--text-muted); font-variant-numeric: tabular-nums; }
.pop-items span { overflow-wrap: anywhere; }
.pop-actions { margin-top: 10px; display: flex; gap: 8px; }
.pop-actions button { font: inherit; font-size: 12px; border: 1px solid var(--ring); background: var(--surface-2);
  color: var(--text); border-radius: 6px; padding: 4px 10px; cursor: pointer; }
ol.pivots, ol.recs { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }
.pivot-card, .rec, .verdict { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; padding: 12px 14px; }
.pivot-card { border-left: 4px solid var(--text-muted); }
.pivot-card.sev-high { border-left-color: var(--status-critical); }
.pivot-card.sev-medium { border-left-color: var(--status-serious); }
.pivot-card:target { box-shadow: 0 0 0 2px var(--text-2); }
.pc-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.badge { color: #fff; font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: 10px; }
.badge.sev-medium { color: #1a1a19; }
.sev-label { font-size: 11px; color: var(--text-2); text-transform: uppercase; letter-spacing: 0.04em; }
.pc-meta { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.pivot-card p, .rec p { margin: 6px 0 0; }
ul.evidence { margin: 6px 0 0; padding-left: 18px; font-size: 11px; color: var(--text-2); }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px; overflow-wrap: anywhere; }
.verdict { border-left: 4px solid var(--status-good); }
.verdict.v-friction { border-left-color: var(--status-warning); }
.verdict.v-waste { border-left-color: var(--status-critical); }
.verdict p { margin: 6px 0 0; color: var(--text-2); }
.rec h3 { font-size: 14px; margin: 0; }
.rec dl { display: grid; grid-template-columns: max-content 1fr; gap: 2px 12px; margin: 8px 0 0; font-size: 13px; }
.rec dt { color: var(--text-muted); }
.rec dd { margin: 0; }
.refs { font-size: 12px; color: var(--text-2); }
.badge-link { color: var(--text); font-weight: 600; }
.obs { color: var(--text-2); }
.table-wrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; }
table { border-collapse: collapse; width: 100%; font-size: 12px; }
th, td { padding: 6px 10px; text-align: left; border-bottom: 1px solid var(--grid); white-space: nowrap; }
thead th { color: var(--text-muted); font-weight: 500; }
td { font-variant-numeric: tabular-nums; color: var(--text-2); }
td.num { color: var(--text); font-weight: 600; }
.barcell { width: 38%; min-width: 160px; }
.bar { display: flex; gap: 2px; height: 10px; }
.seg { display: block; height: 10px; border-radius: 2px; min-width: 2px; }
.notes, .sources { color: var(--text-2); }
details summary { cursor: pointer; color: var(--text-2); }
@media (max-width: 640px) {
  .timeline { grid-template-columns: 116px minmax(0, 1fr); }
  .lane-label .meta { display: none; }
  .tile-value { font-size: 20px; }
  .tl-hint { display: none; }
}
</style>
</head>
<body>
<main>
<h1>__TITLE__</h1>
<p class="subject">__SUBJECT__</p>
<p class="window">__WINDOW__</p>
<div class="tiles">__TILES__</div>
<div class="legend">__LEGEND__</div>
<div class="tl-toolbar">
  <div class="zoom" role="group" aria-label="Zoom">
    <button type="button" data-z="out" aria-label="Zoom out">−</button>
    <button type="button" data-z="in" aria-label="Zoom in">+</button>
    <button type="button" data-z="fit">Fit</button>
    <button type="button" data-z="60">1 h</button>
    <button type="button" data-z="15">15 min</button>
  </div>
  <span class="tl-status" id="tl-status"></span>
  <span class="tl-hint">Drag along the time axis to zoom into a range · Ctrl/⌘ + scroll zooms · click a bar for what happened</span>
</div>
<div class="overview" id="tl-overview-box" title="Overview: click or drag to move the view"><svg id="tl-overview"></svg></div>
<div class="timeline">
  <div class="labels" id="tl-labels"></div>
  <div class="scroller" id="tl-scroller" tabindex="0" aria-label="Timeline; + and − zoom, 0 fits"><div id="tl-track"></div></div>
</div>
<noscript><p class="caption">The interactive timeline needs JavaScript; the tables below carry the same totals.</p></noscript>
__RECS__
__PIVOTS__
__TABLES__
__METHOD__
</main>
<div id="tip" role="tooltip"></div>
<div id="pop" role="dialog" aria-label="Details" hidden></div>
<script type="application/json" id="timeline-data">__DATA__</script>
<script>
(function () {
  'use strict';
  var D = JSON.parse(document.getElementById('timeline-data').textContent);
  var ROW = 38, SUB = 30, SKROW = 12, HEAD = 30, AXIS = 36, GAP = 28, PAD = 28;
  var MIN_PPM = 0.2, MAX_PPM = 300, START_PPM = 4;
  var STEPS = [1, 2, 5, 10, 15, 30, 60, 120, 180, 360, 720, 1440];

  function mkFmt(opts) {
    var o = {hourCycle: 'h23'}; for (var k in opts) o[k] = opts[k];
    if (D.tz) o.timeZone = D.tz;
    try { return new Intl.DateTimeFormat('en-GB', o); } catch (e) { delete o.timeZone; return new Intl.DateTimeFormat('en-GB', o); }
  }
  var fHM = mkFmt({hour: '2-digit', minute: '2-digit'});
  var fHMS = mkFmt({hour: '2-digit', minute: '2-digit', second: '2-digit'});
  var fDay = mkFmt({weekday: 'short', day: '2-digit', month: 'short'});
  var fParts = mkFmt({year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'});
  function offsetMin(t) {
    var p = {}; fParts.formatToParts(new Date(t)).forEach(function (x) { p[x.type] = x.value; });
    var wall = Date.UTC(+p.year, +p.month - 1, +p.day, (+p.hour) % 24, +p.minute);
    return Math.round((wall - Math.floor(t / 60000) * 60000) / 60000);
  }
  function hm(t) { return fHM.format(new Date(t)); }
  function hms(t) { return fHMS.format(new Date(t)); }
  function dur(msv) {
    var m = msv / 60000; if (m < 1) return Math.max(0, Math.round(m * 60)) + 's';
    m = Math.round(m); if (m < 60) return m + 'm';
    var h = Math.floor(m / 60); m = m % 60;
    if (h < 24) return h + 'h ' + (m < 10 ? '0' : '') + m + 'm';
    return Math.floor(h / 24) + 'd ' + (h % 24) + 'h';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function f1(v) { return v.toFixed(1); }

  // ---- time axis with collapsed gaps
  var segs = [];
  (function () {
    var cur = D.t0;
    D.gaps.forEach(function (g) { if (g[0] > cur) segs.push({s: cur, e: g[0], gap: false}); segs.push({s: g[0], e: g[1], gap: true}); cur = g[1]; });
    if (D.t1 > cur || !segs.length) segs.push({s: cur, e: D.t1, gap: false});
  })();
  function liveMs(a, b) {
    var sum = 0;
    segs.forEach(function (s) { if (!s.gap) sum += Math.max(0, Math.min(b, s.e) - Math.max(a, s.s)); });
    return sum;
  }
  function gapsWithin(a, b) { return segs.filter(function (s) { return s.gap && s.s >= a && s.e <= b; }).length; }
  function inGap(t) { return segs.some(function (s) { return s.gap && t > s.s && t < s.e; }); }
  function makeScale(ppm, pad) {
    var pos = [], x = pad;
    segs.forEach(function (s) { var w = s.gap ? GAP : (s.e - s.s) / 60000 * ppm; pos.push([x, x + w]); x += w; });
    var end = x;
    return {
      ppm: ppm, width: end + pad,
      x: function (t) {
        if (t <= D.t0) return pad;
        for (var i = 0; i < segs.length; i++) {
          var s = segs[i];
          if (t <= s.e) { var p = pos[i]; if (t < s.s) return p[0]; return s.e > s.s ? p[0] + (p[1] - p[0]) * (t - s.s) / (s.e - s.s) : p[0]; }
        }
        return end;
      },
      t: function (xv) {
        if (xv <= pad) return D.t0;
        for (var i = 0; i < segs.length; i++) {
          var p = pos[i];
          if (xv <= p[1]) { var s = segs[i]; return p[1] > p[0] ? s.s + (s.e - s.s) * (xv - p[0]) / (p[1] - p[0]) : s.s; }
        }
        return D.t1;
      }
    };
  }

  // ---- lanes
  var lanes = D.agents.map(function (a) {
    var rows = 0;
    D.skills.forEach(function (k) { if (k.a === a.id) rows = Math.max(rows, k.r + 1); });
    var base = a.depth ? SUB : ROW;
    return {a: a, rows: rows, base: base, h: base + rows * SKROW};
  });
  var laneOf = {}, yy = HEAD;
  lanes.forEach(function (l) { l.y = yy; yy += l.h; laneOf[l.a.id] = l; });
  var lanesBottom = yy, H = yy + AXIS;
  function barY(l) { return l.y + 4 + l.rows * SKROW; }
  function barH(l) { return l.base - (l.a.depth ? 14 : 20); }
  function agentLabel(id) { return laneOf[id] ? laneOf[id].a.label : id; }
  function skillLabel(n) { var c = D.catalog[n]; return (c && c.label) || n.replace(/^[^:]+:/, ''); }
  function phaseAt(t) { for (var i = 0; i < D.phases.length; i++) { var p = D.phases[i]; if (t >= p.s && t <= p.e) return p; } return null; }

  var scroller = document.getElementById('tl-scroller'), track = document.getElementById('tl-track');
  var labelsEl = document.getElementById('tl-labels'), statusEl = document.getElementById('tl-status');
  var ovBox = document.getElementById('tl-overview-box');
  var tip = document.getElementById('tip'), pop = document.getElementById('pop');
  var S = null, O = null;

  function viewWidth() { return scroller.clientWidth || 800; }
  function fitPpm() {
    var live = Math.max(liveMs(D.t0, D.t1) / 60000, 1);
    return clamp((viewWidth() - 2 * PAD - GAP * D.gaps.length) / live, MIN_PPM, MAX_PPM);
  }

  function drawLabels() {
    var h = '<div style="height:' + HEAD + 'px"></div>';
    lanes.forEach(function (l) {
      h += '<div class="lane-label d' + Math.min(l.a.depth, 3) + '" style="height:' + l.h + 'px" title="' + esc(l.a.session) + '">' +
        '<span class="name">' + (l.a.depth ? '↳ ' : '') + esc(l.a.label) + '</span><span class="meta">' + esc(l.a.meta) + '</span></div>';
    });
    labelsEl.innerHTML = h + '<div style="height:' + AXIS + 'px"></div>';
  }

  var DEFS = '<defs>' +
    '<pattern id="hatch-wait" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
    '<rect width="6" height="6" fill="var(--wait-fill)"/><line x1="0" y1="0" x2="0" y2="6" stroke="var(--wait-ink)" stroke-width="2"/></pattern>' +
    '<pattern id="hatch-blocked" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">' +
    '<rect width="6" height="6" fill="var(--blocked-fill)"/><line x1="0" y1="0" x2="0" y2="6" stroke="var(--status-serious)" stroke-width="2.5"/></pattern>' +
    '<marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">' +
    '<path d="M0,0 L8,4 L0,8 z" fill="var(--text-muted)"/></marker></defs>';

  function sticky(cls, x0, x1, y, cw, text) {
    return '<text class="' + cls + ' sticky" x="' + f1(x0 + 3) + '" y="' + y + '" data-x0="' + f1(x0) + '" data-x1="' + f1(x1) +
      '" data-cw="' + cw + '" data-full="' + esc(text) + '"></text>';
  }
  function stick() {
    var left = scroller.scrollLeft;
    track.querySelectorAll('text.sticky').forEach(function (el) {
      var x0 = +el.getAttribute('data-x0'), x1 = +el.getAttribute('data-x1'), cw = +el.getAttribute('data-cw');
      var full = el.getAttribute('data-full'), start = Math.max(x0 + 3, left + 6), maxc = Math.floor((x1 - start - 3) / cw);
      if (maxc < 3) { el.textContent = ''; return; }
      el.setAttribute('x', f1(start));
      el.textContent = full.length > maxc ? full.slice(0, maxc - 1) + '…' : full;
    });
  }

  function draw() {
    var p = [], W = S.width;
    p.push('<svg class="track" width="' + Math.ceil(W) + '" height="' + H + '" role="img" aria-label="Timeline of agent activity">', DEFS);
    D.phases.forEach(function (ph, i) {
      var x0 = S.x(ph.s), x1 = S.x(ph.e);
      if (i % 2 === 0) p.push('<rect class="phase-bg" x="' + f1(x0) + '" y="' + HEAD + '" width="' + f1(Math.max(x1 - x0, 1)) + '" height="' + (lanesBottom - HEAD) + '"/>');
      p.push('<rect class="phase" data-i="p' + i + '" x="' + f1(x0) + '" y="4" width="' + f1(Math.max(x1 - x0 - 2, 1)) + '" height="' + (HEAD - 8) + '" rx="4"/>');
      p.push(sticky('phase-label', x0 + 2, x1, HEAD / 2 + 4, 6.4, ph.l));
    });
    lanes.forEach(function (l) { p.push('<line class="lane-line" x1="0" x2="' + Math.ceil(W) + '" y1="' + (l.y + l.h) + '" y2="' + (l.y + l.h) + '"/>'); });

    var step = STEPS[STEPS.length - 1];
    for (var si = 0; si < STEPS.length; si++) if (STEPS[si] * S.ppm >= 64) { step = STEPS[si]; break; }
    var stepMs = step * 60000, off = offsetMin(D.t0) * 60000;
    var t = Math.ceil((D.t0 + off) / stepMs) * stepMs - off, lastDay = null, guard = 0;
    for (; t <= D.t1 && guard < 20000; t += stepMs, guard++) {
      if (inGap(t)) continue;
      var tx = f1(S.x(t)), day = fDay.format(new Date(t));
      p.push('<line class="grid" x1="' + tx + '" x2="' + tx + '" y1="' + HEAD + '" y2="' + lanesBottom + '"/>',
             '<text class="tick" x="' + tx + '" y="' + (lanesBottom + 14) + '">' + hm(t) + '</text>');
      if (day !== lastDay) { p.push('<text class="tick day" x="' + f1(Math.max(4, S.x(t) - 14)) + '" y="' + (lanesBottom + 29) + '">' + esc(day) + '</text>'); lastDay = day; }
    }

    D.skills.forEach(function (k, i) {
      var l = laneOf[k.a], x0 = S.x(k.s), w = Math.max(S.x(k.e) - x0, 2), y = l.y + 3 + k.r * SKROW;
      p.push('<rect class="skill" data-i="k' + i + '" x="' + f1(x0) + '" y="' + y + '" width="' + f1(w) + '" height="' + (SKROW - 2) + '" rx="2"/>');
      p.push(sticky('skill-label', x0, x0 + w, y + SKROW - 4.5, 5.4, skillLabel(k.n)));
    });

    var labelEnd = {};
    D.spans.forEach(function (s, i) {
      var l = laneOf[s.a], x0 = S.x(s.s), w = Math.max(S.x(s.e) - x0, 1.5), by = barY(l), bh = barH(l);
      p.push('<rect class="span k-' + s.k + '" data-i="s' + i + '" x="' + f1(x0) + '" y="' + by + '" width="' + f1(w) + '" height="' + bh + '" rx="3"/>');
      if (S.ppm >= 6 && w > 8 && s.it.length) {
        var d = '';
        s.it.forEach(function (it) { if (it[0] != null) { var xx = S.x(it[0]); if (xx > x0 + 1 && xx < x0 + w - 1) d += 'M' + f1(xx) + ',' + (by + bh - 5) + 'v4'; } });
        if (d) p.push('<path class="item-ticks" d="' + d + '"/>');
      }
      if (s.l && !l.a.depth) {
        var tw = s.l.length * 6;
        if (w >= Math.min(tw, 90) && x0 >= (labelEnd[s.a] || -1)) {
          var room = Math.max(w, 90), shown = tw <= room ? s.l : s.l.slice(0, Math.floor(room / 6) - 1) + '…';
          p.push('<text class="span-label" x="' + f1(x0 + 1) + '" y="' + (by + bh + 11) + '">' + esc(shown) + '</text>');
          labelEnd[s.a] = x0 + shown.length * 6 + 8;
        }
      }
    });

    segs.forEach(function (sg, i) {
      if (!sg.gap) return;
      var x0 = S.x(sg.s);
      p.push('<rect class="gap" data-i="g' + i + '" x="' + f1(x0 + 3) + '" y="' + HEAD + '" width="' + (GAP - 6) + '" height="' + (lanesBottom - HEAD) + '"/>',
             '<path class="gap-edge" d="M' + f1(x0 + 3) + ',' + HEAD + ' l4,6 l-4,6 l4,6 M' + f1(x0 + GAP - 3) + ',' + HEAD + ' l-4,6 l4,6 l-4,6"/>',
             '<text class="tick gap-label" x="' + f1(x0 + GAP / 2) + '" y="' + (lanesBottom + 14) + '">' + dur(sg.e - sg.s) + '</text>');
    });

    D.events.forEach(function (e, i) {
      if (e.ty !== 'message') return;
      var x = f1(S.x(e.at)), fl = laneOf[e.a], tl = laneOf[e.to];
      var y1 = fl.y + fl.h / 2, y2 = tl.y + tl.h / 2 + (tl.y > fl.y ? -8 : 8);
      p.push('<line class="msg" x1="' + x + '" y1="' + f1(y1) + '" x2="' + x + '" y2="' + f1(y2) + '" marker-end="url(#arrow)"/>',
             '<circle class="msg-dot" data-i="e' + i + '" cx="' + x + '" cy="' + f1(y1) + '" r="4.5"/>');
    });
    D.events.forEach(function (e, i) {
      if (e.ty !== 'milestone') return;
      var x = S.x(e.at), l = laneOf[e.a], cy = barY(l) + barH(l) / 2;
      p.push('<path class="milestone" data-i="e' + i + '" d="M' + f1(x) + ',' + f1(cy - 6) + ' l5,6 l-5,6 l-5,-6 z"/>');
    });
    D.events.forEach(function (e, i) {
      if (e.ty !== 'pivot') return;
      var x = S.x(e.at), l = laneOf[e.a], cy = barY(l) + barH(l) / 2, bottom = l.y + l.h;
      if (e.sev === 'high') p.push('<line class="pivot-rule" x1="' + f1(x) + '" x2="' + f1(x) + '" y1="' + HEAD + '" y2="' + lanesBottom + '"/>');
      if (e.end != null) p.push('<rect class="pivot-extent sev-' + e.sev + '" x="' + f1(x) + '" y="' + (bottom - 6) + '" width="' + f1(Math.max(S.x(e.end) - x, 2)) + '" height="3" rx="1.5"/>');
      e.occ.forEach(function (o) { p.push('<rect class="pivot-extent sev-' + e.sev + '" x="' + f1(S.x(o) - 1) + '" y="' + (bottom - 9) + '" width="2" height="7" rx="1"/>'); });
      p.push('<g class="pivot sev-' + e.sev + '" data-i="e' + i + '" tabindex="0"><circle cx="' + f1(x) + '" cy="' + f1(cy) + '" r="10"/>' +
             '<text x="' + f1(x) + '" y="' + f1(cy + 4) + '">' + esc(e.id.replace(/^P/, '') || '!') + '</text></g>');
    });

    p.push('<rect class="axis-hit" x="0" y="' + lanesBottom + '" width="' + Math.ceil(W) + '" height="' + AXIS + '"/>',
           '<rect id="tl-brush" class="brush" x="0" y="' + HEAD + '" width="0" height="' + (lanesBottom - HEAD) + '"/>', '</svg>');
    track.innerHTML = p.join('');
  }

  function drawOverview() {
    var W = ovBox.clientWidth; if (!W) return;
    var rows = lanes.filter(function (l) { return !l.a.human; }), rh = 4, h = 10 + rows.length * rh + 4;
    var live = Math.max(liveMs(D.t0, D.t1) / 60000, 1);
    O = makeScale(Math.max((W - 16 - GAP * D.gaps.length) / live, 0.0001), 8);
    var p = ['<svg width="' + W + '" height="' + h + '">'];
    rows.forEach(function (l, r) {
      var y = 6 + r * rh;
      D.spans.forEach(function (s) {
        if (s.a !== l.a.id || s.k === 'wait-user') return;
        var x0 = O.x(s.s);
        p.push('<rect class="k-' + s.k + '" x="' + f1(x0) + '" y="' + y + '" width="' + f1(Math.max(O.x(s.e) - x0, 0.8)) + '" height="3"/>');
      });
    });
    segs.forEach(function (sg) { if (sg.gap) p.push('<rect class="gap" x="' + f1(O.x(sg.s) + 3) + '" y="2" width="' + (GAP - 6) + '" height="' + (h - 4) + '"/>'); });
    D.events.forEach(function (e) { if (e.ty === 'pivot') p.push('<circle class="pivot-extent sev-' + e.sev + '" cx="' + f1(O.x(e.at)) + '" cy="3" r="2.5"/>'); });
    var a = O.x(S.t(scroller.scrollLeft)), b = O.x(S.t(scroller.scrollLeft + viewWidth()));
    p.push('<rect class="ov-view" x="' + f1(a) + '" y="1" width="' + f1(Math.max(b - a, 3)) + '" height="' + (h - 2) + '" rx="3"/></svg>');
    ovBox.innerHTML = p.join('');
  }

  function status() {
    var a = S.t(scroller.scrollLeft), b = S.t(scroller.scrollLeft + viewWidth());
    var per = S.ppm >= 1 ? '1 min ≈ ' + Math.round(S.ppm) + ' px' : '1 h ≈ ' + Math.round(S.ppm * 60) + ' px';
    statusEl.textContent = 'Showing ' + hm(a) + '–' + hm(b) + ' · ' + per;
  }
  function refresh() { drawOverview(); status(); stick(); }
  var rafPending = false;
  scroller.addEventListener('scroll', function () {
    if (rafPending) return; rafPending = true;
    requestAnimationFrame(function () { rafPending = false; refresh(); });
  });

  function setPpm(ppm, anchorT, anchorPx) {
    if (anchorT == null) { anchorPx = viewWidth() / 2; anchorT = S.t(scroller.scrollLeft + anchorPx); }
    S = makeScale(clamp(ppm, MIN_PPM, MAX_PPM), PAD); draw();
    scroller.scrollLeft = Math.max(0, S.x(anchorT) - anchorPx);
    refresh();
  }
  function zoomRange(a, b) {
    var live = Math.max(liveMs(a, b), 60000) / 60000;
    S = makeScale(clamp((viewWidth() - 48 - gapsWithin(a, b) * GAP) / live, MIN_PPM, MAX_PPM), PAD); draw();
    scroller.scrollLeft = Math.max(0, S.x(a) - 24);
    refresh();
  }

  document.querySelectorAll('[data-z]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var z = btn.getAttribute('data-z');
      if (z === 'in') setPpm(S.ppm * 1.6);
      else if (z === 'out') setPpm(S.ppm / 1.6);
      else if (z === 'fit') setPpm(fitPpm(), D.t0, PAD);
      else setPpm((viewWidth() - 2 * PAD) / +z);
    });
  });
  scroller.addEventListener('wheel', function (ev) {
    if (!(ev.ctrlKey || ev.metaKey)) return;
    ev.preventDefault();
    var r = scroller.getBoundingClientRect(), px = ev.clientX - r.left;
    setPpm(S.ppm * Math.exp(-ev.deltaY * 0.0025), S.t(scroller.scrollLeft + px), px);
  }, {passive: false});
  scroller.addEventListener('keydown', function (ev) {
    if (ev.key === '+' || ev.key === '=') setPpm(S.ppm * 1.6);
    else if (ev.key === '-' || ev.key === '_') setPpm(S.ppm / 1.6);
    else if (ev.key === '0') setPpm(fitPpm(), D.t0, PAD);
    else if (ev.key === 'Enter') {
      var el = document.activeElement, id = el && el.getAttribute && el.getAttribute('data-i');
      if (id) { var r = el.getBoundingClientRect(); openPop(id, r.left + r.width / 2, r.bottom); }
    }
  });

  // brush: drag along the phase header or the time axis
  var drag = null, suppressClick = false;
  track.addEventListener('mousedown', function (ev) {
    var svg = track.firstChild; if (!svg || ev.button !== 0) return;
    var r = svg.getBoundingClientRect(), y = ev.clientY - r.top;
    if (y > HEAD && y < lanesBottom) return;
    drag = {x0: ev.clientX - r.left, x1: ev.clientX - r.left, left: r.left};
    ev.preventDefault();
  });
  window.addEventListener('mousemove', function (ev) {
    if (!drag) return;
    drag.x1 = ev.clientX - drag.left;
    var b = document.getElementById('tl-brush');
    if (b) { b.setAttribute('x', Math.min(drag.x0, drag.x1)); b.setAttribute('width', Math.abs(drag.x1 - drag.x0)); }
  });
  window.addEventListener('mouseup', function () {
    if (!drag) return;
    var d = drag; drag = null;
    if (Math.abs(d.x1 - d.x0) > 8) { suppressClick = true; hideTip(); zoomRange(S.t(Math.min(d.x0, d.x1)), S.t(Math.max(d.x0, d.x1))); }
    else { var b = document.getElementById('tl-brush'); if (b) b.setAttribute('width', 0); }
  });

  // overview: click or drag to move the view
  var ovDrag = false;
  function ovMove(ev) {
    var r = ovBox.getBoundingClientRect();
    scroller.scrollLeft = Math.max(0, S.x(O.t(ev.clientX - r.left)) - viewWidth() / 2);
  }
  ovBox.addEventListener('pointerdown', function (ev) { ovDrag = true; ovBox.setPointerCapture(ev.pointerId); ovMove(ev); });
  ovBox.addEventListener('pointermove', function (ev) { if (ovDrag) ovMove(ev); });
  ovBox.addEventListener('pointerup', function () { ovDrag = false; });

  // ---- tooltip and details
  function kindBreakdown(agent, a, b) {
    var sums = {};
    D.spans.forEach(function (s) {
      if (s.a !== agent) return;
      var m = Math.max(0, Math.min(b, s.e) - Math.max(a, s.s)); if (m) sums[s.k] = (sums[s.k] || 0) + m;
    });
    return Object.keys(D.kinds).filter(function (k) { return sums[k]; }).map(function (k) { return D.kinds[k] + ' ' + dur(sums[k]); }).join(' · ');
  }
  function lookup(id) {
    var n = +id.slice(1);
    return {p: D.phases, k: D.skills, s: D.spans, e: D.events, g: segs}[id[0]][n];
  }
  function tipText(id) {
    var o = lookup(id), c = id[0];
    if (!o) return '';
    if (c === 's') return (o.l || D.kinds[o.k]) + '\n' + D.kinds[o.k] + ' · ' + dur(o.e - o.s) + ' · ' + hm(o.s) + '–' + hm(o.e) +
      (o.sk ? '\nSkill: ' + skillLabel(o.sk) : '') + (o.it.length ? '\n' + o.it.length + ' action' + (o.it.length > 1 ? 's' : '') + ' — click for details' : '');
    if (c === 'k') return 'Skill: ' + o.n + '\n' + dur(o.e - o.s) + ' · ' + hm(o.s) + '–' + hm(o.e) + '\nclick for details';
    if (c === 'p') return o.l + '\n' + dur(o.e - o.s) + ' · ' + hm(o.s) + '–' + hm(o.e);
    if (c === 'g') return 'Collapsed gap: ' + dur(o.e - o.s) + '\nno agent activity, only waiting';
    if (o.ty === 'pivot') return o.id + ' · ' + o.ti + '\n' + hm(o.at) + (o.occ.length > 1 ? ' · ' + o.occ.length + '×' : '') + (o.imp ? ' · impact ~' + dur(o.imp * 60000) : '');
    return o.ti + '\n' + hm(o.at) + (o.ty === 'message' ? ' · ' + agentLabel(o.a) + ' → ' + agentLabel(o.to) : ' · milestone');
  }
  function showTip(el, x, y) {
    var text = tipText(el.getAttribute('data-i')); if (!text) return hideTip();
    var lines = text.split('\n'); tip.textContent = '';
    var b = document.createElement('b'); b.textContent = lines.shift(); b.style.display = 'block'; tip.appendChild(b);
    if (lines.length) tip.appendChild(document.createTextNode(lines.join('\n')));
    tip.style.display = 'block';
    var w = tip.offsetWidth, h = tip.offsetHeight, top = y + 16;
    if (top + h > window.innerHeight - 8) top = y - h - 12;
    tip.style.left = Math.max(8, Math.min(x + 14, window.innerWidth - w - 8)) + 'px'; tip.style.top = Math.max(8, top) + 'px';
  }
  function hideTip() { tip.style.display = 'none'; }
  track.addEventListener('mousemove', function (ev) {
    if (drag) return;
    var el = ev.target.closest && ev.target.closest('[data-i]');
    if (el && pop.hidden) showTip(el, ev.clientX, ev.clientY); else hideTip();
  });
  track.addEventListener('mouseleave', hideTip);

  function skillBlock(n) {
    var c = D.catalog[n] || {};
    return '<div class="pop-skill"><div><span class="pop-tag">Skill</span> <strong>' + esc(n) + '</strong></div>' +
      (c.description ? '<div class="pop-desc">' + esc(c.description) + '</div>' : '') +
      (c.url ? '<a href="' + esc(c.url) + '" target="_blank" rel="noopener">Open definition</a>' : '') + '</div>';
  }
  function row(k, v) { return v ? '<div class="pop-row"><span>' + esc(k) + '</span><span>' + v + '</span></div>' : ''; }
  function zoomBtn(a, b, extra) {
    return '<div class="pop-actions">' + (extra || '') + '<button type="button" data-act="zoom" data-a="' + a + '" data-b="' + b + '">Zoom to this</button></div>';
  }
  function popHtml(id) {
    var o = lookup(id), c = id[0], h = '<button type="button" class="pop-close" aria-label="Close">×</button>';
    if (c === 's') {
      var ph = phaseAt((o.s + o.e) / 2), extra = '';
      h += '<div class="pop-head"><span class="sw k-' + o.k + '"></span><strong>' + esc(o.l || D.kinds[o.k]) + '</strong></div>' +
        '<div class="pop-meta">' + esc(agentLabel(o.a)) + ' · ' + esc(D.kinds[o.k]) + ' · ' + hms(o.s) + '–' + hms(o.e) + ' · ' + dur(o.e - o.s) + '</div>' +
        (o.sk ? skillBlock(o.sk) : '') + row('Phase', ph ? esc(ph.l) : '') + (o.d ? '<p>' + esc(o.d) + '</p>' : '');
      if (o.it.length) {
        var va = S.t(scroller.scrollLeft), vb = S.t(scroller.scrollLeft + viewWidth());
        var shown = popAll ? o.it : o.it.filter(function (it) { return it[0] == null || (it[0] >= va && it[0] <= vb); });
        if (!shown.length) shown = o.it;
        var partial = shown.length < o.it.length;
        h += '<div class="pop-sub">What happened · ' + (partial ? shown.length + ' of ' + o.it.length + ' actions, in view ' + hm(va) + '–' + hm(vb)
          : o.it.length + ' action' + (o.it.length > 1 ? 's' : '')) + '</div><ol class="pop-items">';
        shown.forEach(function (it) { h += '<li><time>' + (it[0] != null ? hms(it[0]) : '') + '</time><span>' + esc(it[1]) + '</span></li>'; });
        h += '</ol>';
        if (partial) extra = '<button type="button" data-act="all" data-id="' + id + '">Show all ' + o.it.length + '</button>';
      } else if (!o.d) h += '<p class="pop-desc">No action details were recorded for this span.</p>';
      return h + zoomBtn(o.s, o.e, extra);
    }
    if (c === 'k') {
      return h + skillBlock(o.n) + '<div class="pop-meta">' + esc(agentLabel(o.a)) + ' · ' + hms(o.s) + '–' + hms(o.e) + ' · ' + dur(o.e - o.s) + '</div>' +
        row('Time', esc(kindBreakdown(o.a, o.s, o.e))) + (o.d ? '<p>' + esc(o.d) + '</p>' : '') + zoomBtn(o.s, o.e);
    }
    if (c === 'p') return h + '<div class="pop-head"><strong>' + esc(o.l) + '</strong></div><div class="pop-meta">' + hms(o.s) + '–' + hms(o.e) + ' · ' + dur(o.e - o.s) + '</div>' + zoomBtn(o.s, o.e);
    if (c === 'g') return h + '<div class="pop-head"><strong>Collapsed gap · ' + dur(o.e - o.s) + '</strong></div><div class="pop-meta">' + hms(o.s) + '–' + hms(o.e) + '</div><p class="pop-desc">No agent was active; lanes only waited.</p>';
    if (o.ty === 'pivot') {
      h += '<div class="pop-head"><span class="badge sev-' + o.sev + '">' + esc(o.id) + '</span><strong>' + esc(o.ti) + '</strong></div>' +
        '<div class="pop-meta">' + esc(D.severities[o.sev]) + ' · ' + esc(agentLabel(o.a)) + ' · ' + hms(o.at) + (o.c ? ' · ' + esc(o.c) : '') + '</div>' +
        row('Lasted', o.end != null ? dur(o.end - o.at) : '') + row('Repeats', o.occ.length > 1 ? o.occ.length + '×, ' + hm(o.occ[0]) + '–' + hm(o.occ[o.occ.length - 1]) : '') +
        row('Impact', o.imp ? '~' + dur(o.imp * 60000) : '') + (o.d ? '<p>' + esc(o.d) + '</p>' : '');
      if (o.ev.length) h += '<div class="pop-sub">Evidence</div><ul class="pop-items">' + o.ev.map(function (x) { return '<li><time></time><span><code>' + esc(x) + '</code></span></li>'; }).join('') + '</ul>';
      return h + '<div class="pop-actions"><button type="button" data-act="card" data-id="' + esc(o.id) + '">Show in the list</button></div>';
    }
    return h + '<div class="pop-head"><strong>' + esc(o.ti) + '</strong></div><div class="pop-meta">' + hms(o.at) + ' · ' +
      (o.ty === 'message' ? esc(agentLabel(o.a)) + ' → ' + esc(agentLabel(o.to)) : esc(agentLabel(o.a)) + ' · milestone') + '</div>' +
      (o.d ? '<p>' + esc(o.d) + '</p>' : '');
  }
  var popAll = false;
  function openPop(id, x, y, all) {
    popAll = !!all; hideTip(); pop.innerHTML = popHtml(id); pop.hidden = false;
    var w = pop.offsetWidth, h = pop.offsetHeight, top = y + 14;
    if (top + h > window.innerHeight - 8) top = Math.max(8, y - h - 14);
    pop.style.left = Math.max(8, Math.min(x + 12, window.innerWidth - w - 8)) + 'px'; pop.style.top = top + 'px';
  }
  function closePop() { pop.hidden = true; }
  track.addEventListener('click', function (ev) {
    if (suppressClick) { suppressClick = false; return; }
    var el = ev.target.closest && ev.target.closest('[data-i]');
    if (!el) return;
    ev.stopPropagation(); openPop(el.getAttribute('data-i'), ev.clientX, ev.clientY);
  });
  pop.addEventListener('click', function (ev) {
    ev.stopPropagation();
    var b = ev.target.closest('button'); if (!b) return;
    if (b.classList.contains('pop-close')) return closePop();
    var act = b.getAttribute('data-act');
    if (act === 'zoom') { closePop(); var a = +b.getAttribute('data-a'), z = +b.getAttribute('data-b'), m = Math.max((z - a) * 0.08, 30000); zoomRange(a - m, z + m); }
    if (act === 'card') { closePop(); location.hash = 'pivot-' + b.getAttribute('data-id'); }
    if (act === 'all') { var r = pop.getBoundingClientRect(); openPop(b.getAttribute('data-id'), r.left - 12, r.top - 14, true); }
  });
  document.addEventListener('click', function (ev) { if (!pop.hidden && !pop.contains(ev.target)) closePop(); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') { closePop(); hideTip(); } });
  window.addEventListener('resize', function () { if (S) refresh(); });

  drawLabels();
  S = makeScale(Math.max(fitPpm(), START_PPM), PAD);
  draw();
  refresh();
})();
</script>
</body>
</html>
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("timeline", help="timeline JSON (schema analyze-run-timeline/1)")
    ap.add_argument("-o", "--output", required=True, help="HTML file to write")
    ap.add_argument("--md", help="also write a Markdown summary to this path")
    ap.add_argument("--gap-minutes", type=float, default=30.0,
                    help="collapse stretches with no agent activity longer than this (default 30)")
    args = ap.parse_args(argv)
    try:
        data = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: cannot read {args.timeline}: {e}", file=sys.stderr)
        return 2
    try:
        doc = load(data)
    except TimelineError as e:
        print("error: invalid timeline:\n" + "\n".join("  - " + line for line in str(e).splitlines()), file=sys.stderr)
        return 2
    Path(args.output).write_text(render_html(doc, args.gap_minutes), encoding="utf-8")
    print(f"wrote {args.output}")
    if args.md:
        Path(args.md).write_text(render_markdown(doc), encoding="utf-8")
        print(f"wrote {args.md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
