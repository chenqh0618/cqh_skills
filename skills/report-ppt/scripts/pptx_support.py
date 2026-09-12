"""Small PPTX helpers; content, evidence checking, and layout remain task-specific."""

import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt


DEFAULT_FONT = "Noto Sans CJK SC"
TITLE_NAME = "report-title"


def new_presentation():
    """Create an empty 16:9 deck. Existing templates can be loaded directly."""
    prs = Presentation()
    prs.slide_width = Inches(13.333333)
    prs.slide_height = Inches(7.5)
    return prs


def set_font(text_frame, name=DEFAULT_FONT, size=None):
    """Set existing paragraph/run fonts, including the East Asian typeface.

    Call after assigning text; size is in points. Font installation is the
    caller's responsibility. For a table, call on each cell's text_frame.
    """
    for paragraph in text_frame.paragraphs:
        for font in [paragraph.font, *(run.font for run in paragraph.runs)]:
            font.name = name
            if size is not None:
                font.size = Pt(size)
            for tag in ("a:ea", "a:cs"):
                element = font._element.find(tag, font._element.nsmap)
                if element is None:
                    element = OxmlElement(tag)
                    font._element.append(element)
                element.set("typeface", name)


def set_notes(slide, narration, sources=()):
    """Write narration followed by separately labelled source references."""
    if not isinstance(narration, str) or not narration.strip():
        raise ValueError("Speaker narration must be nonempty.")
    if isinstance(sources, str):
        raise TypeError("sources must be a sequence of source strings, not one string.")
    refs = list(sources)
    if any(not isinstance(source, str) or not source.strip() for source in refs):
        raise ValueError("Each source reference must be a nonempty string.")
    notes = narration.strip()
    if refs:
        notes += "\n\n证据来源：\n" + "\n".join(f"- {source.strip()}" for source in refs)
    frame = slide.notes_slide.notes_text_frame
    if frame is None:
        raise ValueError("This notes template has no body placeholder; use a compatible notes layout.")
    frame.text = notes


def add_picture_fit(slide, path, left, top, width, height):
    """Contain and center an uncropped image in a box; all dimensions are EMU.

    Both output dimensions are derived from pixel proportions. This also
    handles images whose horizontal and vertical DPI metadata differ.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")
    if not all(math.isfinite(v) for v in (left, top, width, height)):
        raise ValueError("Image box coordinates must be finite.")
    if min(left, top) < 0 or min(width, height) < 1:
        raise ValueError("Image box must have nonnegative origin and positive dimensions.")
    with Image.open(path) as img:
        pixel_w, pixel_h = img.size
    scale = min(width / pixel_w, height / pixel_h)
    fitted_w = max(1, round(pixel_w * scale))
    fitted_h = max(1, round(pixel_h * scale))
    return slide.shapes.add_picture(
        str(path), round(left + (width - fitted_w) / 2),
        round(top + (height - fitted_h) / 2),
        width=fitted_w, height=fitted_h,
    )


def check_pptx(path, aspect="16:9"):
    """Check saved slide geometry and required text, without modifying the file.

    A title is a title placeholder or a textbox named 'report-title'. Group
    contents are not inspected; their presence is explicitly reported.
    """
    result = {"file": str(Path(path).resolve()), "slides": 0, "errors": [], "warnings": []}
    errors, warnings = result["errors"], result["warnings"]
    try:
        prs = Presentation(str(path))
    except Exception as exc:
        errors.append(f"Cannot open PPTX: {exc}")
        return result
    result["slides"] = len(prs.slides)
    if not prs.slides:
        errors.append("Deck contains no slides.")
    if aspect != "any":
        try:
            a, b = [float(part) for part in aspect.split(":")]
            if not all(math.isfinite(v) and v > 0 for v in (a, b)):
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("aspect must be a positive ratio such as '16:9', or 'any'.") from None
        if not math.isclose(prs.slide_width / prs.slide_height, a / b, rel_tol=0.001):
            errors.append(f"Page aspect ratio does not match {aspect}.")
    for number, slide in enumerate(prs.slides, 1):
        prefix = f"Slide {number}"
        title = slide.shapes.title
        titles = ([title] if title is not None else []) + [
            shape for shape in slide.shapes if shape.name == TITLE_NAME
        ]
        if not any(shape.has_text_frame and shape.text.strip() for shape in titles):
            errors.append(f"{prefix}: missing title placeholder or '{TITLE_NAME}' text.")
        notes = slide.notes_slide.notes_text_frame if slide.has_notes_slide else None
        if notes is None or not notes.text.strip():
            errors.append(f"{prefix}: missing speaker notes.")
        for shape in slide.shapes:
            label = f"{prefix}, {shape.name}"
            # Rotate the bounding box around its center for page-edge checking.
            angle = math.radians(shape.rotation)
            bound_w = abs(shape.width * math.cos(angle)) + abs(shape.height * math.sin(angle))
            bound_h = abs(shape.width * math.sin(angle)) + abs(shape.height * math.cos(angle))
            cx, cy = shape.left + shape.width / 2, shape.top + shape.height / 2
            tolerance = 127  # 0.01 pt: tolerate integer-rounding noise only.
            if (cx - bound_w / 2 < -tolerance or cy - bound_h / 2 < -tolerance
                    or cx + bound_w / 2 > prs.slide_width + tolerance
                    or cy + bound_h / 2 > prs.slide_height + tolerance):
                errors.append(f"{label}: shape extends beyond page bounds.")
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                warnings.append(f"{label}: group contents require visual inspection.")
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                try:
                    pixel_w, pixel_h = shape.image.size
                    crops = (shape.crop_left, shape.crop_right, shape.crop_top, shape.crop_bottom)
                    visible_w = pixel_w * (1 - crops[0] - crops[1])
                    visible_h = pixel_h * (1 - crops[2] - crops[3])
                    if min(visible_w, visible_h, shape.width, shape.height) <= 0:
                        errors.append(f"{label}: invalid image dimensions or crop.")
                    elif not math.isclose(shape.width / shape.height, visible_w / visible_h, rel_tol=0.01):
                        errors.append(f"{label}: image aspect ratio is distorted.")
                    if any(abs(value) > 0.00001 for value in crops):
                        warnings.append(f"{label}: cropped image; verify axes and legend remain visible.")
                except Exception as exc:
                    errors.append(f"{label}: cannot inspect image: {exc}")
    warnings.append("Text overflow, overlap, plot readability, source accuracy, and scientific claims require manual review.")
    return result


def render_pptx(path, out_dir, dpi=110, timeout=60):
    """Render into a new/empty directory using an isolated LibreOffice profile.

    Rendering takes place in a temporary directory. No stale PDF is accepted
    and no existing preview files are overwritten.
    """
    path, out_dir = Path(path).resolve(), Path(out_dir).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"PPTX not found: {path}")
    if out_dir.exists() and (not out_dir.is_dir() or any(out_dir.iterdir())):
        raise ValueError(f"Render output must be a new or empty directory: {out_dir}")
    if dpi <= 0 or timeout <= 0:
        raise ValueError("dpi and timeout must be positive.")
    office = shutil.which("libreoffice") or shutil.which("soffice")
    rasterizer = shutil.which("pdftoppm")
    if not office or not rasterizer:
        raise RuntimeError("Rendering requires LibreOffice/soffice and pdftoppm; PPTX is unchanged.")
    with tempfile.TemporaryDirectory(prefix="report-ppt-render-") as temporary:
        work = Path(temporary)
        converted = work / "converted"
        converted.mkdir()
        # A fixed staging name avoids option-like or unusual source basenames.
        staged = work / "deck.pptx"
        shutil.copyfile(path, staged)
        commands = [
            [office, f"-env:UserInstallation={(work / 'profile').as_uri()}",
             "--headless", "--convert-to", "pdf", "--outdir", str(converted), str(staged)],
            [rasterizer, "-png", "-r", str(dpi), str(converted / "deck.pdf"), str(converted / "page")],
        ]
        for command in commands:
            try:
                completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f"Rendering timed out after {timeout}s: {Path(command[0]).name}") from exc
            if completed.returncode != 0:
                raise RuntimeError(f"Rendering failed: {completed.stderr.strip() or completed.stdout.strip()}")
            if not (converted / "deck.pdf").is_file():
                raise RuntimeError(f"LibreOffice produced no PDF: {completed.stdout.strip()}")
        pages = sorted(converted.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
        if not pages:
            raise RuntimeError("Rendering produced no page images.")
        if out_dir.exists() and any(out_dir.iterdir()):
            raise ValueError(f"Render output became nonempty: {out_dir}")
        out_dir.mkdir(parents=True, exist_ok=True)
        for source in [converted / "deck.pdf", *pages]:
            # Exclusive creation also protects against a concurrent writer.
            with source.open("rb") as src, (out_dir / source.name).open("xb") as dst:
                shutil.copyfileobj(src, dst)
    return {"pdf": str(out_dir / "deck.pdf"), "pages": [str(out_dir / page.name) for page in pages]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Check a saved PPTX; does not write files.")
    check.add_argument("pptx")
    check.add_argument("--aspect", default="16:9", help="Expected ratio, e.g. 4:3; 'any' skips ratio check.")
    render = sub.add_parser("render", help="Render PPTX into a new or empty directory.")
    render.add_argument("pptx")
    render.add_argument("--out-dir", required=True)
    render.add_argument("--dpi", type=int, default=110)
    render.add_argument("--timeout", type=int, default=60, help="Timeout per external process, in seconds.")
    args = parser.parse_args()
    try:
        if args.command == "check":
            result = check_pptx(args.pptx, args.aspect)
        else:
            result = render_pptx(args.pptx, args.out_dir, args.dpi, args.timeout)
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
