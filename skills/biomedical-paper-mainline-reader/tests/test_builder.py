"""Synthetic structure/security tests; these do not validate scientific reasoning."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_report", ROOT / "scripts" / "build_report.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestBuilder(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "examples" / "preview.json").read_text(encoding="utf-8"))

    def actual(self):
        d = copy.deepcopy(self.data)
        d["metadata"].update(status="mainline", figure_status="inspected")
        d["sources"] = [{"id": "paper", "citation": "Synthetic source for renderer testing only", "url": "https://example.org/paper"}]
        for i, node in enumerate(d["mainline"], 1):
            node["paragraphs"][0] = {"text": "Synthetic narrative, not a research result.", "refs": ["paper"], "locator": f"Figure {i} (test fixture)"}
        for insight in d["insights"]:
            insight["origin"] = {"text": "Synthetic transfer trigger.", "refs": ["paper"], "locator": "Methods (test fixture)"}
        return d

    def render(self, data=None):
        return module.Report(self.data if data is None else data).render()

    def test_template(self):
        out = self.render()
        self.assertIn("不是真实论文解读", out)
        self.assertIn("<html lang=\"zh-CN\">", out)

    def test_cited_report(self):
        out = self.render(self.actual())
        self.assertIn('href="#source-paper"', out)
        self.assertIn('id="source-paper"', out)

    def test_does_not_require_all_figures(self):
        d = self.actual()
        self.assertNotIn("expected_main_figures", d)
        d["mainline"] = d["mainline"][:1]
        self.assertIn('id="node-1"', self.render(d))

    def test_partial_status(self):
        d = self.actual()
        d["metadata"].update(status="partial", figure_status="unverified")
        self.assertIn("材料有限：", self.render(d))

    def test_unverified_mainline_rejected(self):
        d = self.actual()
        d["metadata"]["figure_status"] = "unverified"
        with self.assertRaises(ValueError):
            self.render(d)

    def test_source_required(self):
        d = self.actual()
        d["sources"] = []
        with self.assertRaises(ValueError):
            self.render(d)

    def test_duplicate_source_rejected(self):
        d = self.actual()
        d["sources"].append(d["sources"][0].copy())
        with self.assertRaises(ValueError):
            self.render(d)

    def test_unknown_citation_rejected(self):
        d = self.actual()
        d["mainline"][0]["paragraphs"][0]["refs"] = ["missing"]
        with self.assertRaises(ValueError):
            self.render(d)

    def test_evidence_locator_required(self):
        d = self.actual()
        d["mainline"][0]["paragraphs"][0].pop("locator")
        with self.assertRaises(ValueError):
            self.render(d)

    def test_transfer_trigger_required(self):
        d = self.actual()
        d["insights"][0]["origin"] = "No source"
        with self.assertRaises(ValueError):
            self.render(d)

    def test_zero_insights_is_allowed(self):
        d = self.actual()
        d["insights"] = []
        d["no_transfer_reason"] = "This synthetic case has no defensible transfer."
        self.assertIn(d["no_transfer_reason"], self.render(d))

    def test_zero_insights_requires_reason(self):
        self.data["insights"] = []
        with self.assertRaises(ValueError):
            self.render()

    def test_javascript_link_rejected(self):
        d = self.actual()
        d["sources"][0]["url"] = "javascript:alert(1)"
        with self.assertRaises(ValueError):
            self.render(d)

    def test_url_credentials_rejected(self):
        d = self.actual()
        d["sources"][0]["url"] = "https://user:secret@example.org/paper"
        with self.assertRaises(ValueError):
            self.render(d)

    def test_url_control_character_rejected(self):
        with self.assertRaises(ValueError):
            module.safe_url("https://example.org/\nunsafe")

    def test_html_is_escaped(self):
        self.data["thesis"] = '<script>alert("x")</script><img src=x onerror=alert(1)>'
        out = self.render()
        self.assertNotIn("<script>", out)
        self.assertNotIn("<img ", out)
        self.assertIn("&lt;script&gt;", out)

    def test_chat_citation_token_rejected(self):
        self.data["thesis"] = "Unsupported citation citeturn0search0"
        with self.assertRaises(ValueError):
            self.render()

    def test_invalid_date_rejected(self):
        self.data["metadata"]["report_date"] = "2026-02-30"
        with self.assertRaises(ValueError):
            self.render()

    def test_bad_source_id_rejected(self):
        d = self.actual()
        d["sources"][0]["id"] = 'paper" onclick="bad'
        with self.assertRaises(ValueError):
            self.render(d)

    def test_bad_reference_type_rejected(self):
        d = self.actual()
        d["mainline"][0]["paragraphs"][0]["refs"] = "paper"
        with self.assertRaises(ValueError):
            self.render(d)

    def test_bad_stage_rejected(self):
        self.data["insights"][0]["stage"] = "已经证明"
        with self.assertRaises(ValueError):
            self.render()

    def test_missing_priority_rejected(self):
        self.data.pop("priority")
        with self.assertRaises(ValueError):
            self.render()

    def test_anchor_audit(self):
        audit = module.HTMLAudit()
        audit.feed('<a href="#missing">bad link</a>')
        with self.assertRaises(ValueError):
            audit.check()

    def test_no_external_runtime(self):
        out = self.render()
        self.assertNotIn("<script", out)
        self.assertNotIn("<link", out)
        self.assertIn("default-src 'none'", out)


if __name__ == "__main__":
    unittest.main()
