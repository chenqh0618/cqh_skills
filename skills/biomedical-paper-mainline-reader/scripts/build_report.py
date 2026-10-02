#!/usr/bin/env python3
"""Render an already-written mainline analysis as standalone HTML (stdlib only).

No network, AI calls, installation actions or raw HTML input. This checks document
structure and references, not the truth or completeness of scientific claims.
Usage: python scripts/build_report.py input.json output.html
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"template": "结构演示", "mainline": "主线精读", "partial": "材料有限"}
FIGURE_STATUSES = {
    "template": "未提供真实论文",
    "inspected": "关键原图已核对",
    "partially_inspected": "仅部分关键原图已核对",
    "unverified": "关键原图尚未核对",
    "not_applicable": "所选主张无需图像核验",
}
STAGES = {"现有数据可初步评估", "需补充实验/数据", "长期关注", "资源待确认"}


def nonempty(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location} must be a nonempty string")
    return value


def text(value: str) -> str:
    return escape(value, quote=True).replace("\n", "<br>")


def paragraph(value: Any, location: str) -> dict[str, Any]:
    if isinstance(value, str):
        return {"text": nonempty(value, location)}
    if not isinstance(value, dict):
        raise ValueError(f"{location} must be text or a paragraph object")
    nonempty(value.get("text"), f"{location}.text")
    refs = value.get("refs", [])
    if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs):
        raise ValueError(f"{location}.refs must be an array of source IDs")
    if "locator" in value and not isinstance(value["locator"], str):
        raise ValueError(f"{location}.locator must be a string")
    return value


def safe_url(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Source URL must be a string")
    if not value:
        return ""
    u = urlsplit(value)
    if (u.scheme not in {"http", "https"} or not u.hostname or u.username or
            u.password or any(c.isspace() or ord(c) < 32 for c in value)):
        raise ValueError("Source links must be HTTP(S) URLs without credentials")
    return escape(value, quote=True)


class HTMLAudit(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.anchors: list[str] = []
        self.problems: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
        if values.get("href", "").startswith("#"):
            self.anchors.append(str(values["href"])[1:])
        if tag in {"script", "iframe", "object", "embed", "form", "link"}:
            self.problems.append(f"Unexpected active or external element: {tag}")
        if any(k.lower().startswith("on") for k in values):
            self.problems.append("Unexpected event handler")
        if "src" in values and not str(values["src"]).startswith("data:"):
            self.problems.append("External asset detected")

    def check(self) -> None:
        repeated = [i for i, count in Counter(self.ids).items() if count > 1]
        missing = sorted(set(self.anchors) - set(self.ids))
        if repeated or missing or self.problems:
            raise ValueError(f"HTML validation failed: duplicate={repeated}, "
                             f"missing={missing}, problems={self.problems}")


class Report:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.sources: dict[str, int] = {}
        self.validate()

    def validate(self) -> None:
        d = self.data
        if not isinstance(d, dict) or not isinstance(d.get("metadata"), dict):
            raise ValueError("Report and metadata must be objects")
        m = d["metadata"]
        for k in ("title", "paper_citation", "paper_version", "report_date", "scope_note"):
            nonempty(m.get(k), f"metadata.{k}")
        date.fromisoformat(m["report_date"])
        if m.get("status") not in STATUSES:
            raise ValueError("metadata.status must be template, mainline or partial")
        if m.get("figure_status") not in FIGURE_STATUSES:
            raise ValueError("Unknown metadata.figure_status")
        if m["status"] != "template" and m["figure_status"] == "template":
            raise ValueError("Real reports cannot use a template figure status")
        if m["status"] == "mainline" and m["figure_status"] not in {"inspected", "not_applicable"}:
            raise ValueError("Unverified key images require partial report status")
        sources = d.get("sources", [])
        if not isinstance(sources, list):
            raise ValueError("sources must be an array")
        for n, source in enumerate(sources, 1):
            if not isinstance(source, dict):
                raise ValueError("Each source must be an object")
            sid = nonempty(source.get("id"), "source.id")
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", sid):
                raise ValueError("Source IDs must be short ASCII identifiers")
            if sid in self.sources:
                raise ValueError(f"Duplicate source ID: {sid}")
            self.sources[sid] = n
            nonempty(source.get("citation"), "source.citation")
            safe_url(source.get("url", ""))
        if m["status"] != "template" and not sources:
            raise ValueError("Real reports require traceable sources")
        paragraph(d.get("thesis"), "thesis")
        overview = d.get("overview")
        if not isinstance(overview, list) or not overview:
            raise ValueError("overview must contain paragraphs")
        for p in overview:
            paragraph(p, "overview[]")
        route = d.get("route", [])
        if not isinstance(route, list) or not route or any(not isinstance(x, str) or not x.strip() for x in route):
            raise ValueError("route must contain nonempty text labels")
        nodes = d.get("mainline")
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("mainline requires at least one evidence node")
        for node in nodes:
            if not isinstance(node, dict):
                raise ValueError("Each mainline node must be an object")
            nonempty(node.get("title"), "mainline.title")
            ps = node.get("paragraphs")
            if not isinstance(ps, list) or not ps:
                raise ValueError("Every mainline node requires narrative paragraphs")
            checked = [paragraph(p, "mainline.paragraphs[]") for p in ps]
            if m["status"] != "template" and not any(p.get("refs") and p.get("locator") for p in checked):
                raise ValueError("Each mainline node requires a cited, located source")
            if node.get("takeaway"):
                paragraph(node["takeaway"], "mainline.takeaway")
        nonempty(d.get("research_context"), "research_context")
        insights = d.get("insights")
        if not isinstance(insights, list):
            raise ValueError("insights must be an array (may be empty)")
        if not insights:
            nonempty(d.get("no_transfer_reason"), "no_transfer_reason")
        for insight in insights:
            if not isinstance(insight, dict):
                raise ValueError("Each insight must be an object")
            nonempty(insight.get("title"), "insight.title")
            if insight.get("stage") not in STAGES:
                raise ValueError(f"Insight stage must be one of {sorted(STAGES)}")
            for key in ("origin", "application", "boundary"):
                paragraph(insight.get(key), f"insight.{key}")
            origin = paragraph(insight["origin"], "insight.origin")
            if m["status"] != "template" and not (origin.get("refs") and origin.get("locator")):
                raise ValueError("Each insight must identify its cited paper trigger")
        priority = d.get("priority")
        if not isinstance(priority, dict):
            raise ValueError("priority must be an object")
        nonempty(priority.get("title"), "priority.title")
        paragraph(priority.get("text"), "priority.text")

        def walk(v: Any) -> None:
            if isinstance(v, str) and ("" in v or "" in v):
                raise ValueError("Replace chat citation tokens with HTML source references")
            if isinstance(v, dict):
                for ref in v.get("refs", []):
                    if ref not in self.sources:
                        raise ValueError(f"Unknown source ID: {ref}")
                for sub in v.values():
                    walk(sub)
            elif isinstance(v, list):
                for sub in v:
                    walk(sub)
        walk(d)

    def p(self, value: Any, cls: str = "") -> str:
        p = paragraph(value, "paragraph")
        refs = "".join(f'<a href="#source-{escape(r)}" aria-label="来源 {self.sources[r]}">'
                       f'[{self.sources[r]}]</a>' for r in dict.fromkeys(p.get("refs", [])))
        cite = f'<span class="refs">{refs}</span>' if refs else ""
        locator = f'<span class="locator">{text(p["locator"])}</span>' if p.get("locator") else ""
        attr = f' class="{cls}"' if cls else ""
        return f'<p{attr}>{text(p["text"])}{cite}{locator}</p>'

    def render(self) -> str:
        d = self.data
        m = d["metadata"]
        parts = ['<section id="question" aria-labelledby="question-title">',
                 '<div class="section-heading"><span class="section-number">01</span>'
                 '<h2 id="question-title">这篇论文究竟在解决什么</h2></div>',
                 '<div class="thesis"><span class="eyebrow">一句话主线</span>',
                 self.p(d["thesis"]), '</div>']
        parts.extend(self.p(p) for p in d["overview"])
        parts.append('<ol class="route" aria-label="研究主线">')
        for label in d["route"]:
            parts.append(f'<li>{text(label)}</li>')
        parts.extend(['</ol></section>',
                      '<section id="mainline" aria-labelledby="mainline-title">',
                      '<div class="section-heading"><span class="section-number">02</span>'
                      '<h2 id="mainline-title">沿主线读懂关键证据</h2></div>'])
        for n, node in enumerate(d["mainline"], 1):
            parts.append(f'<article class="evidence-node" id="node-{n}">'
                         f'<div class="node-title"><span class="node-number">{n:02d}</span>'
                         f'<h3>{text(node["title"])}</h3></div>')
            parts.extend(self.p(p) for p in node["paragraphs"])
            if node.get("takeaway"):
                parts.append(self.p(node["takeaway"], "takeaway"))
            parts.append('</article>')
        parts.extend(['</section>', '<section id="transfer" aria-labelledby="transfer-title">',
                      '<div class="section-heading"><span class="section-number">03</span>'
                      '<h2 id="transfer-title">对我的肺损伤修复研究有什么用</h2></div>',
                      '<div class="research-context"><span class="eyebrow">课题视角</span>',
                      f'<p>{text(d["research_context"])}</p></div>',
                      '<p class="transfer-note">本节是面向用户课题的研究推演；不等于原论文已在肺损伤修复中完成验证。</p>'])
        if not d["insights"]:
            parts.append(self.p(d["no_transfer_reason"]))
        for n, insight in enumerate(d["insights"], 1):
            parts.extend([f'<article class="insight" id="insight-{n}">',
                          f'<span class="stage">{text(insight["stage"])}</span>',
                          f'<h3>{text(insight["title"])}</h3>',
                          '<div class="insight-row"><span class="row-label">本文触发点</span>',
                          self.p(insight["origin"]), '</div>',
                          '<div class="insight-row"><span class="row-label">如何迁移</span>',
                          self.p(insight["application"]), '</div>',
                          '<div class="insight-row boundary"><span class="row-label">价值与边界</span>',
                          self.p(insight["boundary"]), '</div></article>'])
        parts.extend(['</section>', '<section class="priority" id="priority">',
                      '<span class="eyebrow">最值得带走的一个点</span>',
                      f'<h2>{text(d["priority"]["title"])}</h2>',
                      self.p(d["priority"]["text"]), '</section>',
                      '<section class="sources" id="sources"><h2>来源与材料范围</h2>',
                      f'<p>{text(m["scope_note"])}</p>'])
        if d.get("sources"):
            parts.append('<ol>')
            for source in d["sources"]:
                url = safe_url(source.get("url", ""))
                link = f' <a href="{url}" target="_blank" rel="noopener noreferrer">原文入口 ↗</a>' if url else ""
                note = f'<span class="locator">{text(source["note"])}</span>' if source.get("note") else ""
                parts.append(f'<li id="source-{escape(source["id"])}">{text(source["citation"])}{link}{note}</li>')
            parts.append('</ol>')
        else:
            parts.append('<p>尚未提供真实论文。本演示不包含文献结论，也不提供虚构文献或图号。</p>')
        parts.append('</section>')
        if m["status"] == "template":
            notice = "结构与样式演示，不是真实论文解读。下文说明正式报告的取舍与写法；没有虚构实验或发现。"
        elif m["status"] == "partial":
            notice = "材料有限：结论仅限已取得和核验的证据；未获取或未核对的内容不能视为已经验证。"
        else:
            notice = "本报告围绕核心问题精选证据，不提供全部主图或子图的逐项概括。"
        values = {
            "TITLE": text(m["title"]),
            "SUBTITLE": text(m.get("subtitle", "抓住论文主线，把有价值的启发带回自己的课题。")),
            "STATUS": text(STATUSES[m["status"]]),
            "PAPER": text(m["paper_citation"]),
            "VERSION": text(m["paper_version"]),
            "DATE": text(m["report_date"]),
            "FIGURE_STATUS": text(FIGURE_STATUSES[m["figure_status"]]),
            "NOTICE": text(notice),
            "CONTENT": "\n".join(parts),
        }
        template = (ROOT / "assets" / "report-template.html").read_text(encoding="utf-8")
        tokens = set(re.findall(r"\{\{([A-Z_]+)\}\}", template))
        if tokens != set(values):
            raise ValueError(f"Template token mismatch: {tokens ^ set(values)}")
        output = re.sub(r"\{\{([A-Z_]+)\}\}", lambda match: values[match.group(1)], template)
        audit = HTMLAudit()
        audit.feed(output)
        audit.check()
        return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        report = Report(data).render()
        if args.output.suffix.lower() not in {".html", ".htm"}:
            raise ValueError("Output filename must end in .html or .htm")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.exit(2, f"Cannot build report: {exc}\n")
    print(f"Created {args.output.resolve()} ({len(report.encode('utf-8')):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
