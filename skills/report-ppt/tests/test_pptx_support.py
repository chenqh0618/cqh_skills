"""Invariant tests using synthetic images and decks, never scientific outputs."""

from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from pptx import Presentation
from pptx.util import Inches

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from pptx_support import (  # noqa: E402
    add_picture_fit, check_pptx, new_presentation, render_pptx, set_font, set_notes,
)


class PptxSupportTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="pptx-support-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.prs = new_presentation()
        self.slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.title = self.slide.shapes.add_textbox(Inches(.5), Inches(.3), Inches(12), Inches(.7))
        self.title.name = "report-title"
        self.title.text = "合成测试：当前证据不足以判断"
        set_font(self.title.text_frame, size=30)
        set_notes(self.slide, "这是用于验证版式的合成测试。", ["../tables/synthetic.tsv：测试列"])
        self.deck = self.root / "中文 deck.pptx"

    def save_and_check(self, **kwargs):
        self.prs.save(self.deck)
        return check_pptx(self.deck, **kwargs)

    def image(self, size=(800, 400), dpi=(96, 96), name="图 example.png"):
        path = self.root / name
        Image.new("RGB", size, "#236b8e").save(path, dpi=dpi)
        return path

    def test_picture_fit_preserves_pixels_and_handles_unequal_dpi(self):
        for size, dpi in [((800, 400), (96, 96)), ((300, 900), (96, 96)), ((800, 400), (72, 144))]:
            with self.subTest(size=size, dpi=dpi):
                path = self.image(size, dpi)
                before = hashlib.sha256(path.read_bytes()).hexdigest()
                shape = add_picture_fit(self.slide, path, Inches(1), Inches(1.5), Inches(5), Inches(4))
                self.assertAlmostEqual(shape.width / shape.height, size[0] / size[1], places=5)
                self.assertLessEqual(shape.width, Inches(5))
                self.assertLessEqual(shape.height, Inches(4))
                self.assertAlmostEqual(shape.left + shape.width / 2, Inches(3.5), delta=1)
                self.assertAlmostEqual(shape.top + shape.height / 2, Inches(3.5), delta=1)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
        self.assertEqual(self.save_and_check()["errors"], [])

    def test_missing_picture_and_invalid_box_fail_without_adding_shapes(self):
        count = len(self.slide.shapes)
        with self.assertRaises(FileNotFoundError):
            add_picture_fit(self.slide, self.root / "missing.png", 0, 0, 100, 100)
        for width in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                add_picture_fit(self.slide, self.image(), 0, 0, width, 100)
        self.assertEqual(len(self.slide.shapes), count)

    def test_font_and_source_notes_survive_save_and_reopen(self):
        self.prs.save(self.deck)
        restored = Presentation(self.deck).slides[0]
        self.assertIn("证据来源：", restored.notes_slide.notes_text_frame.text)
        self.assertIn("../tables/synthetic.tsv", restored.notes_slide.notes_text_frame.text)
        font = restored.shapes[0].text_frame.paragraphs[0].runs[0].font
        self.assertEqual(font.name, "Noto Sans CJK SC")
        self.assertEqual(font.size.pt, 30)
        self.assertEqual(font._element.find("a:ea", font._element.nsmap).get("typeface"), "Noto Sans CJK SC")

    def test_native_table_chinese_font_and_values_round_trip(self):
        table = self.slide.shapes.add_table(2, 2, Inches(1), Inches(2), Inches(10), Inches(2)).table
        for row, values in zip(table.rows, [("独立样本", "观测数量"), ("6", "1200")]):
            for cell, text in zip(row.cells, values):
                cell.text = text
                set_font(cell.text_frame, size=20)
        self.assertEqual(self.save_and_check()["errors"], [])
        restored = Presentation(self.deck).slides[0].shapes[1].table
        self.assertEqual(restored.cell(1, 0).text, "6")
        self.assertEqual(restored.cell(1, 1).text, "1200")

    def test_notes_require_narration_and_source_list(self):
        with self.assertRaises(ValueError):
            set_notes(self.slide, "  ")
        with self.assertRaises(TypeError):
            set_notes(self.slide, "讲稿", "one string is not a source list")
        with self.assertRaises(ValueError):
            set_notes(self.slide, "讲稿", [""])

    def test_checker_detects_missing_title_and_notes(self):
        self.title.text = ""
        self.slide.notes_slide.notes_text_frame.text = ""
        errors = self.save_and_check()["errors"]
        self.assertTrue(any("missing title" in message for message in errors))
        self.assertTrue(any("missing speaker notes" in message for message in errors))

    def test_notes_template_without_body_is_explicitly_reported(self):
        body_shape = self.slide.notes_slide.notes_text_frame._txBody.getparent()
        body_shape.getparent().remove(body_shape)
        with self.assertRaisesRegex(ValueError, "no body placeholder"):
            set_notes(self.slide, "讲稿")
        self.assertTrue(any("missing speaker notes" in message for message in self.save_and_check()["errors"]))

    def test_checker_detects_stretched_picture_and_out_of_bounds(self):
        self.slide.shapes.add_picture(str(self.image()), Inches(12), Inches(6), Inches(3), Inches(3))
        errors = self.save_and_check()["errors"]
        self.assertTrue(any("aspect ratio is distorted" in message for message in errors))
        self.assertTrue(any("beyond page bounds" in message for message in errors))

    def test_checker_accounts_for_rotated_bounds(self):
        shape = self.slide.shapes.add_textbox(Inches(9), Inches(0), Inches(4), Inches(.5))
        shape.rotation = 45
        self.assertTrue(any("beyond page bounds" in message for message in self.save_and_check()["errors"]))

    def test_cropped_images_and_groups_require_visual_review(self):
        shape = self.slide.shapes.add_picture(str(self.image()), Inches(1), Inches(2), Inches(4), Inches(4))
        shape.crop_left = .25
        shape.crop_right = .25
        group = self.slide.shapes.add_group_shape()
        group.shapes.add_textbox(Inches(6), Inches(2), Inches(2), Inches(1))
        result = self.save_and_check()
        self.assertEqual(result["errors"], [])
        self.assertTrue(any("cropped image" in message for message in result["warnings"]))
        self.assertTrue(any("group contents" in message for message in result["warnings"]))

    def test_expected_page_ratio_can_follow_user_template(self):
        self.assertTrue(self.save_and_check(aspect="4:3")["errors"])
        self.assertEqual(check_pptx(self.deck, aspect="any")["errors"], [])
        with self.assertRaises(ValueError):
            check_pptx(self.deck, aspect="16:0")

    def test_corrupt_file_and_empty_deck_are_reported(self):
        self.deck.write_text("not a pptx")
        self.assertTrue(check_pptx(self.deck)["errors"])
        new_presentation().save(self.deck)
        self.assertTrue(any("no slides" in message for message in check_pptx(self.deck)["errors"]))

    def test_render_preserves_existing_outputs(self):
        self.prs.save(self.deck)
        output = self.root / "preview"
        output.mkdir()
        marker = output / "existing.txt"
        marker.write_text("keep")
        with self.assertRaises(ValueError):
            render_pptx(self.deck, output)
        self.assertEqual(marker.read_text(), "keep")

    def test_unavailable_renderer_or_failed_conversion_is_explicit(self):
        self.prs.save(self.deck)
        before = self.deck.read_bytes()
        output = self.root / "new-preview"
        with patch("pptx_support.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "requires"):
                render_pptx(self.deck, output)
        with patch("pptx_support.shutil.which", return_value="/test/renderer"), patch(
            "pptx_support.subprocess.run", return_value=subprocess.CompletedProcess([], 1, "", "conversion failed")
        ):
            with self.assertRaisesRegex(RuntimeError, "conversion failed"):
                render_pptx(self.deck, output)
        self.assertEqual(self.deck.read_bytes(), before)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
