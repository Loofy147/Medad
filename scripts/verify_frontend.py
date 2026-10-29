#!/usr/bin/env python3
"""Static checks for the Arabic prototype and its evidence snapshot."""
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"

class AuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.script_parts: list[str] = []
        self.in_script = False
        self.ids: list[str] = []
        self.labels: list[str] = []
        self.external_links = 0
        self.errors: list[str] = []
        self.stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
        if tag not in void_tags:
            self.stack.append(tag)
        if data.get("id"):
            self.ids.append(str(data["id"]))
        if tag == "label" and data.get("for"):
            self.labels.append(str(data["for"]))
        if tag == "html" and (data.get("lang") != "ar" or data.get("dir") != "rtl"):
            self.errors.append("html element must declare lang=ar and dir=rtl")
        if tag == "a" and data.get("target") == "_blank":
            rel = set((data.get("rel") or "").split())
            if not {"noopener", "noreferrer"}.issubset(rel):
                self.errors.append("external target=_blank link must use rel=noopener noreferrer")
            self.external_links += 1
        if tag == "script":
            self.in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False
        if not self.stack:
            self.errors.append(f"unexpected closing tag: {tag}")
        elif self.stack[-1] != tag:
            self.errors.append(f"tag nesting mismatch: closing {tag}, expected {self.stack[-1]}")
        else:
            self.stack.pop()

    def handle_data(self, data):
        if self.in_script:
            self.script_parts.append(data)


def main() -> int:
    html = INDEX.read_text(encoding="utf-8")
    parser = AuditParser()
    parser.feed(html)
    parser.close()
    if parser.stack:
        parser.errors.append("unclosed tags: " + ", ".join(parser.stack[-10:]))
    if parser.errors:
        raise SystemExit("HTML checks failed: " + "; ".join(parser.errors))
    dupes = sorted({x for x in parser.ids if parser.ids.count(x) > 1})
    if dupes:
        raise SystemExit(f"duplicate element IDs: {dupes}")
    id_set = set(parser.ids)
    missing_labels = sorted(set(parser.labels) - id_set)
    if missing_labels:
        raise SystemExit(f"labels point to missing IDs: {missing_labels}")
    required_ids = {"v-overview", "v-products", "v-calculator", "v-proposals", "v-instant", "sourceurl", "sourcedate", "breakspend"}
    missing = sorted(required_ids - id_set)
    if missing:
        raise SystemExit(f"required UI sections/controls missing: {missing}")
    if parser.external_links < 4:
        raise SystemExit("expected sourced product links are missing")
    script = "\n".join(parser.script_parts)
    if "مرشح لاختبار محدود" in html or "نتيجة افتراضية فقط" not in html:
        raise SystemExit("client-side calculator must not promote an unverified positive model to test readiness")
    if "$('cost').value='';" not in script:
        raise SystemExit("clicking a product must clear unknown supplier cost before unit-economics calculation")
    if "Hnaya Source" not in html or "Kabagros" not in html or "SVC Corporation" not in html:
        raise SystemExit("supplier-discovery references are missing from product lab")
    if not script.strip():
        raise SystemExit("inline JavaScript not found")
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
        f.write(script)
        js_path = Path(f.name)
    try:
        subprocess.run(["node", "--check", str(js_path)], check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise SystemExit("Node.js is required for inline-JavaScript syntax verification") from exc
    finally:
        js_path.unlink(missing_ok=True)

    sys.path.insert(0, str(ROOT / "engine"))
    from opportunity import load_snapshot
    snapshot = load_snapshot(ROOT / "data" / "research_snapshot_2026-10-29.json")
    if len(snapshot.get("candidates", [])) != 4:
        raise SystemExit("expected four dated research candidates")
    if not all(x["stage"] == "RESEARCH_ONLY" for x in snapshot["readiness"]):
        raise SystemExit("the research snapshot must not promote candidates past research-only")
    print(f"PASS: HTML IDs/labels, {parser.external_links} external source links, JavaScript syntax, and {len(snapshot['candidates'])} evidence-gated candidates")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
