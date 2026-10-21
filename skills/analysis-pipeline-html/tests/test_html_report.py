import base64
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from html_report import Document, ReportError, check_html, pack


PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")


def page(content, style=""):
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<title>测试报告</title><style>' + style + '</style></head><body>'
            + content + '</body></html>')


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.figure = self.root / "有空格 figure.png"
        self.figure.write_bytes(PNG)
        self.table = self.root / "result.tsv"
        self.table.write_text("group\tvalue\nA\t1\n", encoding="utf-8")
        self.draft = self.work / "draft.html"
        self.output = self.root / "report.html"

    def draft_html(self, content=None, style=""):
        if content is None:
            content = ('<h1 id="result">结果</h1><img src="../有空格%20figure.png" alt="测试图">'
                       '<a href="#result">结果</a><a href="../result.tsv">原表</a>')
        self.draft.write_text(page(content, style), encoding="utf-8")

    def test_pack_preserves_figure_bytes_and_rebases_evidence(self):
        self.draft_html()
        before = self.draft.read_bytes()
        result = pack(self.draft, self.output)
        doc = Document(self.output.read_text())
        image = next(e.values for e in doc.elements if e.tag == "img")
        self.assertEqual(base64.b64decode(image["src"].split(",", 1)[1]), PNG)
        self.assertEqual(image["alt"], "测试图")
        self.assertEqual(unquote(image["data-source"]), self.figure.name)
        self.assertIn("result.tsv", [e.values.get("href") for e in doc.elements])
        self.assertEqual(self.draft.read_bytes(), before)
        self.assertTrue(result["validation"]["ok"])

    def test_copied_report_is_readable_without_project_assets(self):
        self.draft_html()
        pack(self.draft, self.output)
        moved_dir = self.root / "share"
        moved_dir.mkdir()
        moved = moved_dir / "report.html"
        shutil.copy2(self.output, moved)
        self.figure.unlink()
        result = check_html(moved.read_text(), moved, portable=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["embedded_images"], 1)
        self.assertTrue(result["warnings"])
        self.assertFalse(check_html(moved.read_text(), moved)["ok"])

    def test_versions_preserve_existing_and_explicit_replace_updates(self):
        self.output.write_text("previous report")
        self.draft_html()
        first = pack(self.draft, self.output)
        second = pack(self.draft, self.output)
        self.assertEqual(Path(first["output"]).name, "report_v02.html")
        self.assertEqual(Path(second["output"]).name, "report_v03.html")
        self.assertEqual(self.output.read_text(), "previous report")
        updated = pack(self.draft, self.output, replace=True)
        self.assertEqual(Path(updated["output"]), self.output)
        self.assertTrue(updated["validation"]["ok"])

    def test_missing_evidence_fails_before_writing(self):
        self.draft_html('<a href="absent.tsv">不存在的证据</a>')
        with self.assertRaises(ReportError):
            pack(self.draft, self.output)
        self.assertFalse(self.output.exists())

    def test_invalid_draft_does_not_replace_existing_report(self):
        self.output.write_text("keep me")
        self.draft_html('<img src="missing.png" alt="缺图">')
        with self.assertRaises(ReportError):
            pack(self.draft, self.output, replace=True)
        self.assertEqual(self.output.read_text(), "keep me")

    def test_external_resources_are_rejected_but_source_urls_are_allowed(self):
        cases = ['<script src="https://example.org/app.js"></script>',
                 '<link rel="stylesheet" href="style.css">',
                 '<img src="https://example.org/pic.png" alt="图">',
                 '<iframe src="figure.pdf"></iframe>',
                 '<img data-dynamic-image="true" alt="图" srcset="pic.png 2x">']
        for content in cases:
            with self.subTest(content=content):
                self.draft_html(content)
                with self.assertRaises(ReportError):
                    pack(self.draft, self.output)
        self.draft_html('<a href="https://example.org/source">外部来源</a>')
        result = pack(self.draft, self.output)
        self.assertEqual(result["validation"]["external_links_not_fetched"], 1)

    def test_css_rendering_dependencies_are_rejected(self):
        for css in ['body{background:url(../figure.png)}',
                    '@font-face{src:url("https://example.org/font.woff2")}',
                    '@import "style.css";']:
            with self.subTest(css=css):
                self.draft_html('<p>正文</p>', css)
                with self.assertRaises(ReportError):
                    pack(self.draft, self.output)

    def test_svg_with_external_image_is_rejected(self):
        svg = self.root / "chart.svg"
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="figure.png"/></svg>')
        self.draft_html('<img src="../chart.svg" alt="SVG图">')
        with self.assertRaisesRegex(ReportError, "external rendering dependency"):
            pack(self.draft, self.output)

    def test_self_contained_svg_and_internal_references_pack(self):
        svg = self.root / "chart.svg"
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
                       '<defs><linearGradient id="g"><stop stop-color="red"/></linearGradient></defs>'
                       '<rect width="20" height="20" fill="url(#g)"/></svg>')
        self.draft_html('<img src="../chart.svg" alt="SVG图">')
        result = pack(self.draft, self.output)
        self.assertEqual(result["validation"]["embedded_images"], 1)

    def test_duplicate_and_missing_anchors_fail(self):
        for content in ['<p id="x">甲</p><p id="x">乙</p>', '<a href="#absent">跳转</a>']:
            with self.subTest(content=content):
                self.draft_html(content)
                with self.assertRaises(ReportError):
                    pack(self.draft, self.output)

    def test_template_fields_and_malformed_images_fail(self):
        for content in ['<p>{{STEPS}}</p>', '<img src="data:image/png;base64,broken!" alt="图">', '<img alt="缺图">']:
            with self.subTest(content=content):
                self.draft_html(content)
                with self.assertRaises(ReportError):
                    pack(self.draft, self.output)

    def test_format_mismatch_is_not_silently_embedded(self):
        self.figure.write_text("not an image")
        self.draft_html()
        with self.assertRaisesRegex(ReportError, "signature"):
            pack(self.draft, self.output)

    def test_dynamic_viewer_slot_has_no_initial_rendering_dependency(self):
        self.draft_html('<img id="viewer" data-dynamic-image="true" alt="放大图">')
        self.assertTrue(pack(self.draft, self.output)["validation"]["ok"])

    def test_replacing_input_or_symlink_is_rejected(self):
        self.draft_html()
        self.output.symlink_to(self.table)
        for path in [self.output, self.draft]:
            with self.subTest(path=path):
                with self.assertRaises(ReportError):
                    pack(self.draft, path, replace=True)
        self.assertIn("group", self.table.read_text())

    def test_utf8_paths_and_draft_self_links_are_rebased(self):
        self.draft_html('<h1 id="结论">标题</h1><a href="draft.html#%E7%BB%93%E8%AE%BA">结论</a>'
                        '<a href="../有空格%20figure.png">图源</a>')
        pack(self.draft, self.output)
        doc = Document(self.output.read_text())
        hrefs = [e.values.get("href") for e in doc.elements if e.tag == "a"]
        self.assertIn("#%E7%BB%93%E8%AE%BA", hrefs)
        self.assertIn(self.figure.name, [unquote(x) for x in hrefs])


if __name__ == "__main__":
    unittest.main()
