#!/usr/bin/env python3
"""Build a single-file biomedical evidence report. Standard library only; no network.

Usage: python build_report.py report.json report.html --assets-root ./assets
Input is an explicitly prepared analysis, not raw paper text. See examples/.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
STAGES = [
    ("context", "① 背景与承接"), ("question", "② 目的与假设"),
    ("design", "③ 实验或分析设计"), ("panels", "④ 子图证据"),
    ("results", "⑤ 结果怎样解读"), ("inference", "⑥ 证据如何支持结论"),
    ("limitations", "⑦ 边界与未解决问题"), ("bridge", "⑧ 本图小结与下一图"),
]
MATH_TAGS = set("math mrow mi mn mo mtext mspace ms mfrac msqrt mroot msub msup msubsup munder mover munderover mtable mtr mtd semantics annotation".split())
MATH_ATTRS = set("display mathvariant stretchy fence separator accent accentunder columnalign rowalign columnspacing rowspacing xmlns encoding".split())


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def text(value: Any) -> str:
    return esc(value).replace("\n", "<br>")


def safe_url(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"Only public http(s) citation URLs are accepted: {value!r}")
    return esc(value)


def mathml(value: str) -> str:
    if "<!" in value:
        raise ValueError("MathML declarations are not permitted")
    root = ET.fromstring(value)
    if root.tag.split("}")[-1] != "math":
        raise ValueError("MathML must have a math root")
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag not in MATH_TAGS:
            raise ValueError(f"Unsupported MathML tag: {tag}")
        node.tag = tag
        if any(k not in MATH_ATTRS for k in node.attrib):
            raise ValueError("Unsupported MathML attribute")
    root.set("xmlns", "http://www.w3.org/1998/Math/MathML")
    return ET.tostring(root, encoding="unicode")


def image_uri(path: str, base: Path) -> str:
    target = (base / path).resolve()
    if not target.is_relative_to(base.resolve()):
        raise ValueError("Image paths must stay inside --assets-root")
    if not target.is_file():
        raise ValueError(f"Image file not found: {target}")
    raw = target.read_bytes()
    if len(raw) > 20_000_000:
        raise ValueError("An individual image exceeds 20 MB; resize it before embedding")
    ext = target.suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml"}.get(ext)
    if not mime:
        raise ValueError(f"Unsupported image format: {ext}")
    if ext == ".svg":
        source = raw.decode("utf-8")
        if "<!DOCTYPE" in source.upper() or "<!ENTITY" in source.upper():
            raise ValueError("SVG declarations are not permitted")
        root = ET.fromstring(source)
        if root.tag.split("}")[-1] != "svg":
            raise ValueError("Invalid SVG root")
        for node in root.iter():
            tag = node.tag.split("}")[-1].lower()
            if tag in {"script", "foreignobject", "iframe", "object", "embed", "animate", "animatemotion", "animatetransform", "set"}:
                raise ValueError("Active SVG content is not permitted")
            for key, value in node.attrib.items():
                key = key.split("}")[-1].lower()
                if key.startswith("on") or (key == "href" and not value.startswith("#")):
                    raise ValueError("External SVG references or events are not permitted")
            css = " ".join(node.attrib.values()) + (node.text or "")
            if "@import" in css.lower() or re.search(r"url\s*\(\s*['\"]?\s*(?!#)[^\s]", css, re.I):
                raise ValueError("SVG must not contain external CSS references")
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


class AnchorCheck(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
        if values.get("href", "").startswith("#"):
            self.links.append(str(values["href"])[1:])

    def validate(self) -> None:
        duplicate = [key for key, n in Counter(self.ids).items() if n > 1]
        missing = sorted(set(self.links) - set(self.ids))
        if duplicate or missing:
            raise ValueError(f"Broken HTML anchors: duplicates={duplicate}; missing={missing}")


class Renderer:
    def __init__(self, report: dict[str, Any], base: Path) -> None:
        self.report = report
        self.base = base
        self.sources = report.get("sources", [])
        self.ref_index = {source["id"]: n for n, source in enumerate(self.sources, 1)}
        if len(self.ref_index) != len(self.sources):
            raise ValueError("Duplicate source IDs")
        self.validate()

    def validate(self) -> None:
        r = self.report
        m = r["metadata"]
        if m.get("status") not in {"template", "partial", "complete"}:
            raise ValueError("metadata.status must be template, partial or complete")
        for key in ("title", "paper_citation", "report_date", "version", "article_type"):
            if not m.get(key):
                raise ValueError(f"Missing metadata.{key}")
        figures = r.get("figures", [])
        expected = r.get("expected_main_figures", [])
        actual = [f["label"] for f in figures]
        if not expected or expected != actual or len(set(actual)) != len(actual):
            raise ValueError("Main figure inventory does not match report order")
        for f in figures:
            for key, _ in STAGES:
                if not f.get(key):
                    raise ValueError(f"Missing {f['label']}.{key}")
            covered = [label for p in f["panels"] for label in p["labels"]]
            if sorted(covered) != sorted(f.get("expected_panels", [])) or len(covered) != len(set(covered)):
                raise ValueError(f"Missing or repeated panel coverage: {f['label']}")
            if m["status"] == "complete" and f.get("visual_status") != "inspected":
                raise ValueError("Complete reports require visually inspected main figures")
        if m["status"] == "complete":
            coverage = r.get("source_coverage", [])
            if not coverage or any(x.get("status") != "已读" for x in coverage if x.get("required", True)):
                raise ValueError("Complete reports require all essential materials to be read")
            if not self.sources:
                raise ValueError("Complete reports require traceable sources")
        if not r.get("overview") or not r.get("synthesis"):
            raise ValueError("Overview and synthesis are required")
        for s in self.sources:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", s["id"]):
                raise ValueError("Source IDs must be URL-fragment-safe ASCII identifiers")
            safe_url(s.get("url", ""))
        # Validate every citation, including nested paragraph/table metadata.
        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for ref in value.get("refs", []):
                    if ref not in self.ref_index:
                        raise ValueError(f"Unknown reference ID: {ref}")
                for nested in value.values():
                    walk(nested)
            elif isinstance(value, list):
                for nested in value:
                    walk(nested)
        walk(r)

    def citations(self, b: dict[str, Any]) -> str:
        refs = "".join(f'<a href="#ref-{esc(ref)}" aria-label="参考来源 {self.ref_index[ref]}">[{self.ref_index[ref]}]</a>' for ref in b.get("refs", []))
        out = f'<span class="refs">{refs}</span>' if refs else ""
        if b.get("locator"):
            out += f'<span class="locator">{text(b["locator"])}</span>'
        return out

    def table(self, headers: list[str], rows: list[list[Any]], caption: str = "", raw: bool = False) -> str:
        if any(len(row) != len(headers) for row in rows):
            raise ValueError("Table row width does not match headers")
        fmt = str if raw else text
        cap = f"<caption>{text(caption)}</caption>" if caption else ""
        head = "".join(f'<th scope="col">{text(h)}</th>' for h in headers)
        body = "".join("<tr>" + "".join(f"<td>{fmt(c)}</td>" for c in row) + "</tr>" for row in rows)
        return f'<div class="table-wrap"><table>{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'

    def image(self, b: dict[str, Any]) -> str:
        uri = image_uri(b["path"], self.base)
        cap = text(b.get("caption", ""))
        if b.get("source"):
            cap += "<br>来源：" + text(b["source"])
        return f'<figure class="figure-image"><img src="{uri}" alt="{esc(b.get("alt", b.get("caption", "论文图像")))}"><figcaption>{cap}{self.citations(b)}</figcaption></figure>'

    def blocks(self, values: list[Any]) -> str:
        return "".join(self.block(b) for b in values)

    def block(self, b: Any) -> str:
        if isinstance(b, str):
            return f"<p>{text(b)}</p>"
        kind = b.get("type", "p")
        if kind == "p":
            return f'<p>{text(b["text"])}{self.citations(b)}</p>'
        if kind == "callout":
            tone = " warn" if b.get("tone") == "warn" else ""
            return f'<div class="callout{tone}"><strong>{text(b["title"])}</strong><p>{text(b["text"])}{self.citations(b)}</p></div>'
        if kind == "table":
            return self.table(b["headers"], b["rows"], b.get("caption", "")) + self.citations(b)
        if kind == "flow":
            items = "".join(f'<li><span class="step">{n:02d}</span><span class="node-text">{text(node)}</span></li>' for n, node in enumerate(b["nodes"], 1))
            return f'<ol class="flow">{items}</ol><p class="caption">{text(b.get("caption", ""))}{self.citations(b)}</p>'
        if kind == "math":
            result = f'<div class="math-block">{mathml(b["mathml"])}</div>'
            if b.get("source"):
                result += f'<details><summary>查看公式源码</summary><pre><code>{esc(b["source"])}</code></pre></details>'
            return result + self.citations(b)
        if kind == "image":
            return self.image(b)
        if kind == "code":
            return f'<details><summary>{text(b.get("title", "查看源码"))}</summary><pre><code>{esc(b["text"])}</code></pre></details>'
        raise ValueError(f"Unsupported block type: {kind}")

    def section(self, ident: str, title: str, body: str, kicker: str = "") -> str:
        label = f'<div class="kicker">{text(kicker)}</div>' if kicker else ""
        return f'<section class="section" id="{esc(ident)}">{label}<h2>{text(title)}</h2>{body}<a class="jump" href="#top">返回页首 ↑</a></section>'

    def render(self) -> str:
        r, m = self.report, self.report["metadata"]
        status = {"template": "结构演示 · 非真实论文解读", "partial": "部分解读 · 存在材料或核验缺口", "complete": "论文解读 · 详见材料覆盖范围"}[m["status"]]
        warn = " warn" if m["status"] != "complete" else ""
        hero = f'<header class="hero"><span class="badge{warn}">{text(status)}</span><div class="eyebrow">BIOMEDICAL RESEARCH · EVIDENCE & LOGIC</div><h1>{text(m["title"])}</h1><p>{text(m.get("subtitle", ""))}</p><p class="paper-title">{text(m["paper_citation"])}</p><div class="meta-line">研究类型：{text(m["article_type"])}<br>论文版本：{text(m["version"])}　｜　报告日期：{text(m["report_date"])}</div></header>'
        parts: list[str] = []
        toc: list[tuple[str, str]] = []
        def add(ident: str, title: str, body: str, kicker: str = "") -> None:
            toc.append((ident, title))
            parts.append(self.section(ident, title, body, kicker))
        coverage = [[x["label"], x["status"], x.get("detail", "")] for x in r.get("source_coverage", [])]
        body = self.table(["材料", "阅读状态", "覆盖说明"], coverage) if coverage else "<p>未提供材料覆盖记录。</p>"
        if m.get("scope_note"):
            body += self.block({"type": "callout", "tone": "warn" if warn else "", "title": "阅读范围与限制", "text": m["scope_note"]})
        add("coverage", "材料覆盖与核验范围", body, "READING SCOPE")
        for n, section in enumerate(r["overview"], 1):
            add(f"overview-{n}", section["title"], self.blocks(section["blocks"]), f"OVERVIEW / {n:02d}")
        figure_map = r.get("figure_map", [])
        if figure_map:
            rows = []
            for n, row in enumerate(figure_map, 1):
                if n > len(r["figures"]):
                    raise ValueError("Figure navigation contains unknown figures")
                rows.append([f'<a href="#figure-{n}">{text(row["figure"])}</a>', text(row["question"]), text(row["approach"]), text(row["role"])])
            add("figure-map", "主图路线：每幅图解决什么问题", self.table(["主图", "科学问题", "实验/数据", "在证据链中的作用"], rows, raw=True), "FIGURE ROUTE")
        for n, f in enumerate(r["figures"], 1):
            visual = {"inspected": "原图已核验", "not_available": "原图未获取", "template": "演示条目"}.get(f.get("visual_status", ""), "原图尚未核验")
            body = f'<p class="lead">{text(f.get("role", ""))}</p><span class="badge{warn}">{text(visual)}</span>'
            for im in f.get("images", []):
                body += self.image(im)
            for key, title in STAGES:
                body += f"<h3>{text(title)}</h3>"
                if key == "panels":
                    observations, interpretation = [], []
                    for p in f["panels"]:
                        labels = text(" / ".join(p["labels"]))
                        observations.append([labels, text(p.get("method", "")), text(p.get("comparison", "")), text(p.get("observation", ""))])
                        interpretation.append([labels, text(p.get("interpretation", "")), text(p.get("limit", "")), text(p.get("source", "")) + self.citations(p)])
                    body += self.table(["子图", "方法/测量", "关键比较", "直接观察"], observations, raw=True)
                    body += self.table(["子图", "可以支持", "不能据此推出", "证据定位"], interpretation, raw=True)
                else:
                    body += self.blocks(f[key])
            add(f"figure-{n}", f'{f["label"]}｜{f["title"]}', body, f'MAIN FIGURE / {n:02d}')
        for n, section in enumerate(r["synthesis"], 1):
            add(f"synthesis-{n}", section["title"], self.blocks(section["blocks"]), "SYNTHESIS")
        for n, section in enumerate(r.get("appendices", []), 1):
            add(f"appendix-{n}", section["title"], self.blocks(section["blocks"]), "APPENDIX")
        if self.sources:
            entries = []
            for source in self.sources:
                link = f'<a href="{safe_url(source["url"])}" target="_blank" rel="noopener noreferrer">打开原始来源</a>' if source.get("url") else "本地/用户提供材料"
                detail = " · ".join(str(source[k]) for k in ("kind", "locator", "accessed") if source.get(k))
                entries.append(f'<li id="ref-{esc(source["id"])}">{text(source["citation"])}<br>{link}<div class="source-meta">{text(detail)}</div></li>')
            source_body = '<ol class="source-list">' + "".join(entries) + "</ol>"
        else:
            source_body = "<p>此页面为结构演示，未使用真实论文结论。真实报告须填写原始来源及图号定位。</p>"
        add("references", "参考来源与定位", source_body, "SOURCES")
        quality = r.get("quality", {})
        checked = "".join(f"<li>{text(item)}</li>" for item in quality.get("checked", []))
        open_items = "".join(f"<li>{text(item)}</li>" for item in quality.get("open", []))
        q = f'<h3>已完成的检查</h3><ul class="checks">{checked}</ul><h3>仍需说明的事项</h3><ul class="checks">{open_items}</ul>'
        add("quality", "交付检查与限制", q, "QUALITY & LIMITS")
        template = (ROOT / "assets" / "report-template.html").read_text(encoding="utf-8")
        values = {"TITLE": esc(m["title"]), "TOC": "".join(f'<a href="#{ident}">{text(title)}</a>' for ident, title in toc), "HERO": hero, "CONTENT": "".join(parts)}
        # Single substitution pass: text in the report cannot masquerade as a template token.
        document = re.sub(r"\{\{(TITLE|TOC|HERO|CONTENT)\}\}", lambda match: values[match.group(1)], template)
        anchors = AnchorCheck()
        anchors.feed(document)
        anchors.validate()
        return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Prepared JSON analysis")
    parser.add_argument("output", type=Path, help="Output .html file")
    parser.add_argument("--assets-root", type=Path, help="Allowed root directory for image inputs")
    args = parser.parse_args()
    try:
        if args.output.suffix.lower() != ".html":
            raise ValueError("Output must have an .html suffix")
        if args.input.resolve() == args.output.resolve():
            raise ValueError("Input and output cannot be the same file")
        report = json.loads(args.input.read_text(encoding="utf-8"))
        result = Renderer(report, args.assets_root or args.input.parent).render()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
        print(json.dumps({"output": str(args.output.resolve()), "bytes": args.output.stat().st_size, "figures": len(report["figures"]), "status": report["metadata"]["status"]}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as error:
        print(f"Report build failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
