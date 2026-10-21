#!/usr/bin/env python3
"""Pack verified report figures into HTML and check static reading dependencies.

Python 3.10+, standard library only. Does not fetch URLs, execute analysis,
validate scientific claims, or detect arbitrary network calls in JavaScript.
"""
from __future__ import annotations

import argparse
import base64
import binascii
from collections import Counter
from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import quote, unquote, unquote_to_bytes, urlsplit, urlunsplit
import xml.etree.ElementTree as ET


IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml"}
CSS_URL = re.compile(r"url\(\s*(?:\"([^\"]*)\"|'([^']*)'|([^)]*))\s*\)", re.I)
PLACEHOLDER = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")


class ReportError(ValueError):
    pass


@dataclass
class Element:
    tag: str
    attrs: list[tuple[str, str | None]]
    start: int
    end: int
    line: int
    self_closing: bool = False

    @property
    def values(self) -> dict[str, str | None]:
        return dict(self.attrs)


class Document(HTMLParser):
    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.offsets = [0] + [m.end() for m in re.finditer("\n", text)]
        self.elements: list[Element] = []
        self.styles: list[str] = []
        self.title = ""
        self.in_style = False
        self.in_title = False
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        line, col = self.getpos()
        start = self.offsets[line - 1] + col
        raw = self.get_starttag_text()
        self.elements.append(Element(tag, attrs, start, start + len(raw), line))
        if tag == "style":
            self.in_style = True
        if tag == "title":
            self.in_title = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.elements[-1].self_closing = True
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_style:
            self.styles.append(data)
        if self.in_title:
            self.title += data


def css_errors(css: str) -> list[str]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    errors = []
    if re.search(r"@import\b", css, re.I):
        errors.append("CSS @import must be inlined")
    for match in CSS_URL.finditer(css):
        value = next(v for v in match.groups() if v is not None).strip()
        if not value.lower().startswith("data:") and not value.startswith("#"):
            errors.append(f"CSS resource must be embedded: {value}")
    return errors


def verify_svg(data: bytes, depth: int = 0) -> None:
    if depth > 8:
        raise ReportError("SVG image nesting is too deep; export a flat display image")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ReportError(f"Invalid SVG: {exc}") from exc
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ReportError("Image declared as SVG has no svg root")
    if b"<?xml-stylesheet" in data:
        raise ReportError("SVG references an external stylesheet; export a self-contained image")
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag in {"script", "foreignObject"}:
            raise ReportError(f"SVG {tag} is unsupported; export a static PNG")
        for attr, value in node.attrib.items():
            key = attr.rsplit("}", 1)[-1]
            if key == "style":
                failures = css_errors(value)
                if failures:
                    raise ReportError("SVG " + "; ".join(failures))
            if key in {"href", "src"} and tag != "a":
                if value.startswith("#"):
                    continue
                if value.lower().startswith("data:image/"):
                    verify_data_image(value, depth + 1)
                else:
                    raise ReportError(f"SVG has an external rendering dependency: {value}")
            if "url(" in value.lower():
                failures = css_errors(value)
                if failures:
                    raise ReportError("SVG " + "; ".join(failures))
        if tag == "style":
            failures = css_errors("".join(node.itertext()))
            if failures:
                raise ReportError("SVG " + "; ".join(failures))


def verify_image(data: bytes, mime: str, depth: int = 0) -> None:
    signatures = {
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/gif": data.startswith((b"GIF87a", b"GIF89a")),
        "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    }
    if mime == "image/svg+xml":
        verify_svg(data, depth)
    elif mime not in signatures or not signatures[mime]:
        raise ReportError(f"Unsupported or mismatched image signature: {mime}")


def verify_data_image(value: str, depth: int = 0) -> None:
    try:
        header, payload = value.split(",", 1)
        mime = header[5:].split(";", 1)[0].lower()
        data = (base64.b64decode(payload, validate=True) if header.lower().endswith(";base64")
                else unquote_to_bytes(payload))
    except (ValueError, binascii.Error) as exc:
        raise ReportError("Malformed embedded image") from exc
    verify_image(data, mime, depth)


def local_path(value: str, base: Path) -> Path | None:
    url = urlsplit(value)
    if url.scheme and url.scheme != "file":
        return None
    if url.netloc and not (url.scheme == "file" and url.netloc == "localhost"):
        return None
    if not url.path:
        return None
    path = Path(unquote(url.path))
    return (path if path.is_absolute() else base / path).resolve()


def check_html(text: str, path: Path, portable: bool = False) -> dict:
    doc = Document(text)
    errors, warnings = [], []
    ids = [e.values["id"] for e in doc.elements if "id" in e.values]
    duplicates = [str(k) for k, n in Counter(ids).items() if n > 1]
    if duplicates:
        errors.append("Duplicate IDs: " + ", ".join(duplicates))
    content = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    unfinished = sorted(set(PLACEHOLDER.findall(content)))
    if unfinished:
        errors.append("Unfilled template fields: " + ", ".join(unfinished))
    if not doc.title.strip():
        errors.append("Page title is empty or absent")
    if not any(e.tag == "meta" and str(e.values.get("charset", "")).lower() == "utf-8"
               for e in doc.elements):
        errors.append("Explicit UTF-8 charset is required")
    sources = []
    external_links = 0
    image_count = 0
    for e in doc.elements:
        a = e.values
        at = f"line {e.line}"
        if e.tag == "base":
            errors.append(f"{at}: base URLs are unsupported; use paths relative to the HTML")
        if "srcset" in a:
            errors.append(f"{at}: srcset must be replaced by one embedded display image")
        if "style" in a:
            errors.extend(f"{at}: {s}" for s in css_errors(a["style"] or ""))
        if e.tag == "img":
            if not (a.get("alt") or "").strip():
                errors.append(f"{at}: image needs a descriptive alt")
            src = a.get("src") or ""
            if not src and a.get("data-dynamic-image") == "true":
                continue  # Template's viewer slot is filled from an existing figure.
            if not src.lower().startswith("data:image/"):
                errors.append(f"{at}: display image is not embedded: {src}")
            else:
                try:
                    verify_data_image(src)
                    image_count += 1
                except ReportError as exc:
                    errors.append(f"{at}: {exc}")
        elif e.tag == "script" and a.get("src"):
            errors.append(f"{at}: script must be inline")
        elif e.tag == "link" and a.get("href"):
            errors.append(f"{at}: linked styles/fonts/icons must be inline or embedded")
        elif e.tag in {"iframe", "object", "embed", "audio", "video", "source", "track"}:
            errors.append(f"{at}: {e.tag} is unsupported; use a static embedded figure")
        elif e.tag in {"image", "use", "feimage"}:
            href = a.get("href") or a.get("xlink:href") or ""
            if href and not (href.startswith("#") or href.lower().startswith("data:image/")):
                errors.append(f"{at}: SVG resource is not embedded: {href}")
            elif href.lower().startswith("data:image/"):
                try:
                    verify_data_image(href)
                except ReportError as exc:
                    errors.append(f"{at}: {exc}")
        if e.tag == "a" and a.get("href"):
            href = a["href"]
            url = urlsplit(href)
            if not url.scheme and not url.netloc and not url.path:
                if url.fragment and unquote(url.fragment) not in ids:
                    errors.append(f"{at}: broken same-page anchor: {href}")
            else:
                source = local_path(href, path.parent)
                if source is not None:
                    exists = source.exists()
                    sources.append({"href": href, "exists": exists})
                    if not exists:
                        message = f"{at}: source link unavailable: {href}"
                        (warnings if portable else errors).append(message)
                elif url.scheme in {"http", "https", "mailto", "tel"} or url.netloc:
                    external_links += 1
                elif not href.lower().startswith("data:image/"):
                    errors.append(f"{at}: unsupported evidence link: {url.scheme}")
    errors.extend(css_errors("\n".join(doc.styles)))
    return {"ok": not errors, "errors": list(dict.fromkeys(errors)),
            "warnings": list(dict.fromkeys(warnings)), "embedded_images": image_count,
            "local_source_links": sources, "external_links_not_fetched": external_links}


def tag_html(element: Element, updates: dict[str, str]) -> str:
    attrs = [(key, updates.get(key, value)) for key, value in element.attrs]
    attrs.extend((key, value) for key, value in updates.items() if key not in element.values)
    rendered = "".join(" " + key if value is None else f' {key}="{escape(value, quote=True)}"'
                       for key, value in attrs)
    return f"<{element.tag}{rendered}{' /' if element.self_closing else ''}>"


def unused_path(requested: Path) -> Path:
    if not requested.exists() and not requested.is_symlink():
        return requested
    stem = re.sub(r"_v\d+$", "", requested.stem)
    version = 2
    while True:
        candidate = requested.with_name(f"{stem}_v{version:02d}{requested.suffix}")
        if not candidate.exists() and not candidate.is_symlink():
            return candidate
        version += 1


def pack(draft: Path, requested: Path, replace: bool = False) -> dict:
    draft = draft.resolve()
    # Keep an output symlink visible so replacing a report cannot overwrite its target.
    requested = Path(os.path.abspath(requested))
    if requested.suffix.lower() != ".html":
        raise ReportError("Output must have an .html suffix")
    output = requested if replace else unused_path(requested)
    if output.is_symlink():
        raise ReportError("Refusing to replace an output symlink; specify a regular HTML file")
    if output.resolve() == draft:
        raise ReportError("Use a separate draft; packing does not modify the input file")
    text = draft.read_text(encoding="utf-8")
    doc = Document(text)
    if any(e.tag == "base" for e in doc.elements):
        raise ReportError("Remove base URLs and resolve paths relative to the draft")
    replacements = []
    images: dict[Path, str] = {}
    for element in doc.elements:
        a = element.values
        updates = {}
        if element.tag == "img" and a.get("src"):
            src = a["src"]
            if not src.lower().startswith("data:"):
                source = local_path(src, draft.parent)
                if source is None:
                    raise ReportError(f"Images must be local verified files, not fetched URLs: {src}")
                if urlsplit(src).query or urlsplit(src).fragment:
                    raise ReportError(f"Image URL query/fragment is unsupported; export the selected view: {src}")
                if not source.is_file():
                    raise ReportError(f"Missing figure: {source}")
                mime = IMAGE_MIME.get(source.suffix.lower())
                if mime is None:
                    raise ReportError(f"Unsupported figure format; export PNG/JPEG/SVG: {source}")
                if source not in images:
                    data = source.read_bytes()
                    verify_image(data, mime)
                    images[source] = "data:" + mime + ";base64," + base64.b64encode(data).decode("ascii")
                updates["src"] = images[source]
                if not a.get("data-source"):
                    updates["data-source"] = os.path.relpath(source, output.parent)
        if element.tag == "a" and a.get("href"):
            href = a["href"]
            source = local_path(href, draft.parent)
            if source is not None:
                url = urlsplit(href)
                if source == draft:
                    updates["href"] = "#" + url.fragment
                else:
                    rel = quote(Path(os.path.relpath(source, output.parent)).as_posix(), safe="/")
                    updates["href"] = urlunsplit(("", "", rel, url.query, url.fragment))
        if updates:
            replacements.append((element.start, element.end, tag_html(element, updates)))
    chunks = []
    position = 0
    for start, end, replacement in replacements:
        chunks.extend((text[position:start], replacement))
        position = end
    chunks.append(text[position:])
    text = "".join(chunks)
    validation = check_html(text, output)
    if not validation["ok"]:
        raise ReportError("Report validation failed:\n" + "\n".join(validation["errors"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    if replace:
        fd, temporary = tempfile.mkstemp(prefix=".html-report-", suffix=".tmp", dir=output.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
            os.replace(temporary, output)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    else:
        with output.open("x", encoding="utf-8") as handle:
            handle.write(text)
    return {"output": str(output), "bytes": output.stat().st_size,
            "newly_embedded_files": [str(p) for p in images], "validation": validation}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    packing = commands.add_parser("pack", help="Embed local figures and rebase evidence links")
    packing.add_argument("draft", type=Path)
    packing.add_argument("--output", required=True, type=Path)
    packing.add_argument("--replace", action="store_true", help="Replace an explicitly requested existing report")
    checking = commands.add_parser("check", help="Check static assets, anchors and evidence links")
    checking.add_argument("report", type=Path)
    checking.add_argument("--portable", action="store_true", help="Report missing source links as warnings after moving")
    args = parser.parse_args()
    try:
        if args.command == "pack":
            result = pack(args.draft, args.output, args.replace)
            code = 0
        else:
            path = args.report.resolve()
            result = check_html(path.read_text(encoding="utf-8"), path, args.portable)
            result["report"] = str(path)
            code = 0 if result["ok"] else 1
    except (ReportError, OSError, UnicodeError, ValueError) as exc:
        result = {"ok": False, "error": str(exc)}
        code = 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
