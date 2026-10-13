#!/usr/bin/env python3
"""Read-only PDF structure and first-page identity checks; no network or writes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unicodedata
from urllib.parse import unquote


def normalize_doi(value):
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "",
                   value.strip(), flags=re.I)
    value = unquote(value).lower()
    if not re.fullmatch(r"10\.\d{4,9}/\S+", value):
        raise ValueError("Invalid DOI; supply one DOI or its doi.org URL")
    return value


def title_key(value):
    return "".join(c for c in unicodedata.normalize("NFKC", value).casefold()
                   if c.isalnum())


def doi_on_first_page(doi, text):
    # Allow PDF line breaks inside DOI; reject a target that is only a prefix.
    body = r"\s*".join(re.escape(c) for c in doi)
    return bool(re.search(r"(?<![\w/])" + body + r"(?![\w/])", text, re.I))


def run_pdf_tool(args):
    result = subprocess.run(args, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=60,
                            env={**os.environ, "LC_ALL": "C"})
    if result.returncode:
        raise ValueError(f"{Path(args[0]).name} could not parse the PDF")
    return result.stdout


def verify(pdf, doi, title):
    doi = normalize_doi(doi)
    if not title_key(title):
        raise ValueError("A nonempty expected article title is required")
    pdf = Path(pdf).expanduser().resolve(strict=True)
    with pdf.open("rb") as handle:
        if not handle.read(1024).lstrip().startswith(b"%PDF-"):
            raise ValueError("File is not a PDF (possibly a download/login page)")
    for tool in ("pdfinfo", "pdftotext"):
        if not shutil.which(tool):
            raise ValueError(f"Missing {tool}; install Poppler or inspect manually")
    info = run_pdf_tool(["pdfinfo", str(pdf)])
    fields = dict(re.findall(r"^([^:\n]+):[ \t]*(.*)$", info, re.M))
    pages = int(fields.get("Pages", "0"))
    if pages <= 0 or fields.get("Encrypted", "").startswith("yes"):
        raise ValueError("PDF has no readable pages or is encrypted")
    text = run_pdf_tool(["pdftotext", "-layout", str(pdf), "-"])
    first = text.split("\f", 1)[0]
    doi_match = doi_on_first_page(doi, first)
    title_match = title_key(title) in title_key(first)
    metadata_title_match = title_key(title) == title_key(fields.get("Title", ""))
    with pdf.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    return {"ok": doi_match and title_match, "pdf": str(pdf), "doi": doi,
            "title": title, "pages": pages, "bytes": pdf.stat().st_size,
            "sha256": digest, "doi_on_first_page": doi_match,
            "title_on_first_page": title_match,
            "metadata_title_matches": metadata_title_match,
            "text_pages": sum(bool(p.strip()) for p in text.split("\f")),
            "note": "Identity precheck only; inspect article type and completeness before acceptance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--doi", required=True)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()
    try:
        report = verify(args.pdf, args.doi, args.title)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        report = {"ok": False, "error": str(exc)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
