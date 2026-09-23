"""Regression tests for the analyze-run timeline renderer.

Run from the plugin root: python3 -m unittest discover -s tests -v
"""

import copy
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the plugin root
SKILL = ROOT / "skills/analyze-run"
SCRIPT = SKILL / "scripts/render_timeline.py"
SPEC = importlib.util.spec_from_file_location("render_timeline", SCRIPT)
renderer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = renderer  # dataclasses resolve annotations through sys.modules
SPEC.loader.exec_module(renderer)


def schema_example():
    text = (SKILL / "references/timeline-schema.md").read_text(encoding="utf-8")
    block = text.split("## Minimal example", 1)[1]
    return json.loads(re.search(r"```json\n(.*?)\n```", block, re.S).group(1))


def page_payload(page):
    raw = re.search(r'<script type="application/json" id="timeline-data">(.*?)</script>', page, re.S).group(1)
    return json.loads(raw)


def run_doc():
    return {
        "schema": "analyze-run-timeline/1",
        "title": "#7 — <b>cancel</b> an order",
        "timezone": "UTC",
        "agents": [
            {"id": "user", "label": "User", "runtime": "human"},
            {"id": "analyst", "label": "Analyst", "runtime": "claude-code", "role": "analyst"},
            {"id": "dev", "label": "Developer", "runtime": "codex", "role": "developer"},
            {"id": "rev", "label": "Spec reviewer", "runtime": "claude-code", "parent": "analyst"},
        ],
        "phases": [
            {"id": "p3", "label": "3 Implement", "start": "2026-09-20T08:00:00Z", "end": "2026-09-20T09:00:00Z"},
            {"id": "p4", "label": "4 Review", "start": "2026-09-20T09:00:00Z", "end": "2026-09-20T13:30:00Z"},
        ],
        "skills": [
            {"agent": "dev", "name": "delivery:implement", "start": "2026-09-20T08:00:00Z", "end": "2026-09-20T09:00:00Z"},
            {"agent": "dev", "name": "delivery:tdd", "start": "2026-09-20T08:05:00Z", "end": "2026-09-20T08:40:00Z"},
            {"agent": "analyst", "name": "delivery:code-review", "start": "2026-09-20T09:00:00Z", "end": "2026-09-20T09:20:00Z"},
        ],
        "skill_catalog": {
            "delivery:implement": {"label": "implement", "description": "Implement and verify slices.",
                                            "url": "https://github.com/example/delivery-plugin/blob/main/skills/implement/SKILL.md"},
        },
        "spans": [
            {"agent": "dev", "start": "2026-09-20T08:00:00Z", "end": "2026-09-20T08:40:00Z", "kind": "work",
             "items": [{"at": "2026-09-20T08:10:00Z", "text": "Edit OrderService.java"}, "plan written"]},
            {"agent": "dev", "start": "2026-09-20T08:40:00Z", "end": "2026-09-20T09:00:00Z", "kind": "check",
             "label": "gradlew test"},
            {"agent": "analyst", "start": "2026-09-20T08:30:00Z", "end": "2026-09-20T09:00:00Z", "kind": "work"},
            {"agent": "rev", "start": "2026-09-20T09:00:00Z", "end": "2026-09-20T09:20:00Z", "kind": "review",
             "skill": "delivery:code-review"},
            {"agent": "analyst", "start": "2026-09-20T09:20:00Z", "end": "2026-09-20T13:00:00Z", "kind": "wait-user"},
            {"agent": "analyst", "start": "2026-09-20T13:00:00Z", "end": "2026-09-20T13:30:00Z", "kind": "work"},
        ],
        "events": [
            {"type": "message", "at": "2026-09-20T08:30:00Z", "agent": "analyst", "to": "dev", "title": "handoff"},
            {"type": "milestone", "at": "2026-09-20T09:00:00Z", "agent": "dev", "title": "PR opened"},
            {"type": "pivot", "id": "P1", "at": "2026-09-20T08:40:00Z", "end": "2026-09-20T09:00:00Z", "agent": "dev",
             "severity": "medium", "category": "long-running", "title": "Full suite took 20 min", "impact_min": 15,
             "occurrences": ["2026-09-20T08:40:00Z", "2026-09-20T08:50:00Z"]},
            {"type": "pivot", "id": "P2", "at": "2026-09-20T09:20:00Z", "end": "2026-09-20T13:00:00Z",
             "agent": "analyst", "severity": "high", "category": "waiting", "title": "Gate waited over lunch"},
        ],
        "analysis": {
            "verdict": "friction", "summary": "One slow suite.",
            "recommendations": [{"title": "Run focused tests first", "evidence": ["P1"], "saving": "~15 min"}],
            "observations": ["P2: the user was away."],
        },
    }


class LoadTests(unittest.TestCase):
    def errors(self, doc):
        with self.assertRaises(renderer.TimelineError) as caught:
            renderer.load(doc)
        return str(caught.exception)

    def test_schema_reference_example_is_valid(self):
        doc = renderer.load(schema_example())
        self.assertIn("timeline-data", renderer.render_html(doc))

    def test_reports_every_problem_at_once(self):
        doc = run_doc()
        doc["spans"][0]["agent"] = "ghost"
        doc["spans"][1]["kind"] = "coffee"
        del doc["events"][2]["severity"]
        doc["analysis"]["recommendations"][0]["evidence"] = ["P9"]
        doc["skills"][0]["agent"] = "nobody"
        message = self.errors(doc)
        for expected in ("unknown agent 'ghost'", "kind must be one of", "severity must be one of",
                         "'P9' is not a pivot id", "skills[0]: unknown agent 'nobody'"):
            self.assertIn(expected, message)

    def test_rejects_timestamps_without_offset(self):
        doc = run_doc()
        doc["spans"][0]["start"] = "2026-09-20T08:00:00"
        self.assertIn("needs a UTC offset", self.errors(doc))

    def test_rejects_message_without_known_recipient(self):
        doc = run_doc()
        doc["events"][0]["to"] = "nobody"
        self.assertIn("message needs a known 'to' agent", self.errors(doc))

    def test_rejects_unknown_parent(self):
        doc = run_doc()
        doc["agents"][3]["parent"] = "missing"
        self.assertIn("unknown parent", self.errors(doc))

    def test_rejects_skill_links_that_are_not_web_or_file_urls(self):
        doc = run_doc()
        doc["skill_catalog"]["delivery:implement"]["url"] = "javascript:alert(1)"
        self.assertIn("url must start with one of", self.errors(doc))

    def test_items_keep_times_and_are_capped(self):
        doc = run_doc()
        doc["spans"][0]["items"] = [{"at": "2026-09-20T08:10:00Z", "text": "x" * 500}] + ["y"] * 300
        span = renderer.load(doc)["spans"][0]
        self.assertEqual(len(span.items), renderer.MAX_ITEMS)
        self.assertEqual(len(span.items[0].text), renderer.MAX_TEXT)
        self.assertIsNotNone(span.items[0].at)
        self.assertIsNone(span.items[1].at)


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.doc = renderer.load(run_doc())

    def test_nested_skill_gets_its_own_row(self):
        rows = {k.name: k.row for k in self.doc["skills"]}
        self.assertEqual(rows["delivery:implement"], 0)
        self.assertEqual(rows["delivery:tdd"], 1)

    def test_span_takes_the_innermost_skill_unless_it_names_one(self):
        spans = self.doc["spans"]
        self.assertEqual(renderer.span_skill(self.doc, spans[0]), "delivery:tdd")
        self.assertEqual(renderer.span_skill(self.doc, spans[1]), "delivery:implement")
        self.assertEqual(renderer.span_skill(self.doc, spans[3]), "delivery:code-review")
        self.assertIsNone(renderer.span_skill(self.doc, spans[2]))

    def test_subagent_work_counts_towards_the_skill_its_parent_is_running(self):
        doc = run_doc()
        doc["skills"].append({"agent": "analyst", "name": "delivery:orchestrate",
                              "start": "2026-09-20T08:30:00Z", "end": "2026-09-20T13:30:00Z"})
        del doc["spans"][3]["skill"]
        loaded = renderer.load(doc)
        self.assertEqual(renderer.span_skill(loaded, loaded["spans"][3]), "delivery:code-review")
        loaded["skills"] = [k for k in loaded["skills"] if k.name != "delivery:code-review"]
        self.assertEqual(renderer.span_skill(loaded, loaded["spans"][3]), "delivery:orchestrate")

    def test_time_by_skill_puts_unattributed_time_last(self):
        table = renderer.kind_minutes_by(self.doc, "skill")
        self.assertEqual(list(table)[-1], renderer.NO_SKILL)
        self.assertAlmostEqual(table["delivery:tdd"]["work"], 40.0)
        self.assertAlmostEqual(table["delivery:implement"]["check"], 20.0)


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.doc = renderer.load(run_doc())

    def test_stats_exclude_waiting_from_agent_activity(self):
        stats = renderer.compute_stats(self.doc)
        self.assertAlmostEqual(stats["active"], 110.0)       # 08:00–09:20 and 13:00–13:30
        self.assertAlmostEqual(stats["wait_user"], 220.0)
        self.assertAlmostEqual(stats["agent_sum"], 140.0)    # parallel analyst + developer

    def test_long_user_wait_is_collapsed_even_when_a_pivot_spans_it(self):
        data = page_payload(renderer.render_html(self.doc))
        self.assertEqual(len(data["gaps"]), 1)
        start, end = data["gaps"][0]
        self.assertEqual((end - start) / 60000, 220)

    def test_page_data_carries_lanes_skills_and_actions(self):
        data = page_payload(renderer.render_html(self.doc))
        self.assertEqual([a["id"] for a in data["agents"]], ["user", "analyst", "rev", "dev"])
        self.assertEqual(data["agents"][2]["depth"], 1)
        first = data["spans"][0]
        self.assertEqual(first["sk"], "delivery:tdd")
        self.assertEqual(first["it"][0][1], "Edit OrderService.java")
        self.assertEqual(data["catalog"]["delivery:implement"]["label"], "implement")

    def test_page_shows_assessment_pivots_and_skill_table(self):
        page = renderer.render_html(self.doc)
        for text in ('id="pivot-P1"', "Some friction", "Run focused tests first", "Observations (no action proposed)",
                     "2 occurrences", "Where the time went — by skill"):
            self.assertTrue(text in page, text)

    def test_page_escapes_input_text(self):
        doc = run_doc()
        doc["spans"][0]["items"][0]["text"] = "echo '</script><b>x</b>'"
        page = renderer.render_html(renderer.load(doc))
        self.assertNotIn("<b>cancel</b>", page)
        self.assertIn("&lt;b&gt;cancel&lt;/b&gt;", page)
        self.assertEqual(page_payload(page)["spans"][0]["it"][0][1], "echo '</script><b>x</b>'")

    def test_template_tokens_inside_input_text_stay_literal(self):
        doc = run_doc()
        doc["title"] = "__DATA__ and __TILES__"
        page = renderer.render_html(renderer.load(doc))
        self.assertIn("<title>__DATA__ and __TILES__</title>", page)
        self.assertEqual(page_payload(page)["agents"][0]["id"], "user")

    def test_markdown_summary_lists_verdict_pivots_and_skills(self):
        md = renderer.render_markdown(self.doc)
        self.assertIn("**P1 · Full suite took 20 min**", md)
        self.assertIn("Some friction", md)
        self.assertIn("| 4 Review |", md)
        self.assertIn("| delivery:tdd | 40m |", md)

    def test_checks_tile_appears_only_when_there_were_checks_or_remote_jobs(self):
        self.assertIn("Checks &amp; remote jobs", renderer.render_html(self.doc))
        doc = run_doc()
        doc["spans"][1]["kind"] = "tool"
        page = renderer.render_html(renderer.load(doc))
        self.assertNotIn("Checks &amp; remote jobs", page)
        self.assertNotIn("Checks & remote jobs", renderer.render_markdown(renderer.load(doc)))

    def test_skill_definitions_can_be_local_command_files(self):
        doc = run_doc()
        doc["skill_catalog"]["write-report"] = {"label": "write-report",
                                                "url": "file:///home/me/.claude/commands/write-report.md"}
        data = page_payload(renderer.render_html(renderer.load(doc)))
        self.assertEqual(data["catalog"]["write-report"]["url"], "file:///home/me/.claude/commands/write-report.md")

    def test_runs_without_phases_skills_or_analysis(self):
        doc = run_doc()
        for key in ("phases", "analysis", "skills", "skill_catalog"):
            doc.pop(key)
        doc["spans"][3].pop("skill")
        page = renderer.render_html(renderer.load(doc))
        self.assertNotIn("Assessment", page)
        self.assertNotIn("by skill", page)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_page_script_is_valid_javascript(self):
        page = renderer.render_html(self.doc)
        script = page.rsplit("<script>", 1)[1].split("</script>", 1)[0]
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(script)
        try:
            result = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
        finally:
            Path(f.name).unlink()
        self.assertEqual(result.returncode, 0, result.stderr)


class CliTests(unittest.TestCase):
    def run_cli(self, doc):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "timeline.json"
            src.write_text(json.dumps(doc))
            result = subprocess.run([sys.executable, str(SCRIPT), str(src), "-o", str(Path(tmp) / "t.html"),
                                     "--md", str(Path(tmp) / "t.md")], capture_output=True, text=True)
            outputs = [p.name for p in Path(tmp).iterdir()]
        return result, outputs

    def test_writes_html_and_markdown(self):
        result, outputs = self.run_cli(run_doc())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("t.html", outputs)
        self.assertIn("t.md", outputs)

    def test_invalid_input_exits_2_without_output(self):
        doc = copy.deepcopy(run_doc())
        doc["schema"] = "other"
        result, outputs = self.run_cli(doc)
        self.assertEqual(result.returncode, 2)
        self.assertIn("schema must be", result.stderr)
        self.assertNotIn("t.html", outputs)


if __name__ == "__main__":
    unittest.main()
