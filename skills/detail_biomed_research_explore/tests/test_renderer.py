"""Functional tests on synthetic report data; these do not validate real papers."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_report", ROOT / "scripts" / "build_report.py")
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((ROOT / "examples" / "template-report.json").read_text(encoding="utf-8"))

    def render(self):
        return module.Renderer(self.report, ROOT / "examples").render()

    def test_template_builds(self):
        output = self.render()
        self.assertIn('lang="zh-CN"', output)
        self.assertIn('结构演示 · 非真实论文解读', output)
        self.assertIn('id="figure-2"', output)
        self.assertNotIn('<script', output)
        self.assertNotIn('{{CONTENT}}', output)

    def test_missing_panel_rejected(self):
        self.report['figures'][0]['expected_panels'].append('e')
        with self.assertRaises(ValueError): self.render()

    def test_duplicate_panel_rejected(self):
        self.report['figures'][0]['panels'][1]['labels'].append('a')
        with self.assertRaises(ValueError): self.render()

    def test_missing_figure_rejected(self):
        self.report['figures'].pop()
        with self.assertRaises(ValueError): self.render()

    def test_false_complete_rejected(self):
        self.report['metadata']['status'] = 'complete'
        with self.assertRaises(ValueError): self.render()

    def test_missing_section_rejected(self):
        self.report['figures'][0]['inference'] = []
        with self.assertRaises(ValueError): self.render()

    def test_unknown_citation_rejected(self):
        self.report['overview'][0]['blocks'].append({'type':'p','text':'合成测试','refs':['missing']})
        with self.assertRaises(ValueError): self.render()

    def test_citation_anchor_generated(self):
        self.report['sources'] = [{'id':'local','citation':'合成测试来源；非真实论文','kind':'测试','locator':'仅用于功能测试'}]
        self.report['overview'][0]['blocks'].append({'text':'合成测试','refs':['local'],'locator':'演示位置'})
        output = self.render()
        self.assertIn('href="#ref-local"', output)
        self.assertIn('id="ref-local"', output)

    def test_script_url_rejected(self):
        self.report['sources'] = [{'id':'x','citation':'测试','url':'javascript:alert(1)'}]
        with self.assertRaises(ValueError): self.render()

    def test_text_html_escaped(self):
        self.report['overview'][0]['blocks'].append('<script>alert(1)</script>')
        output = self.render()
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', output)
        self.assertNotIn('<script>', output)

    def test_mathml_renders(self):
        output = self.render()
        self.assertIn('<math display="block"', output)
        self.assertIn('<mfrac>', output)

    def test_unsafe_mathml_rejected(self):
        with self.assertRaises(ValueError):
            module.mathml('<math><script>alert(1)</script></math>')

    def test_image_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)/'safe'; base.mkdir()
            with self.assertRaises(ValueError):
                module.image_uri('../outside.png',base)

    def test_external_svg_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'bad.svg'
            p.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.org/x.png" /></svg>')
            with self.assertRaises(ValueError):
                module.image_uri('bad.svg',Path(t))

    def test_passive_svg_embeds(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'safe.svg'
            p.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10" /></svg>')
            self.assertTrue(module.image_uri('safe.svg',Path(t)).startswith('data:image/svg+xml;base64,'))

    def test_duplicate_anchor_rejected(self):
        parser = module.AnchorCheck()
        parser.feed('<h1 id="same">A</h1><h2 id="same">B</h2>')
        with self.assertRaises(ValueError): parser.validate()

    def test_missing_anchor_rejected(self):
        parser = module.AnchorCheck()
        parser.feed('<a href="#absent">x</a>')
        with self.assertRaises(ValueError): parser.validate()

    def test_table_shape_rejected(self):
        r = module.Renderer(self.report,ROOT)
        with self.assertRaises(ValueError): r.table(['a','b'],[['a']])

    def test_text_cannot_replace_template_tokens(self):
        self.report['metadata']['title']='{{CONTENT}}'
        self.assertIn('<title>{{CONTENT}}</title>',self.render())


if __name__ == '__main__':
    unittest.main()
