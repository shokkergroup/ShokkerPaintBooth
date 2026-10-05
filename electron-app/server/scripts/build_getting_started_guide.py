# -*- coding: utf-8 -*-
"""Build SPB_GETTING_STARTED_GUIDE.pdf — interactive PDF with bookmarks + internal links.

Usage:
  python -B scripts/build_getting_started_guide.py
  python -B scripts/build_getting_started_guide.py --out docs/custom.pdf

Output: docs/SPB_GETTING_STARTED_GUIDE.pdf
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from getting_started_content import TOC, build_all

VERSION = "6.3.0-alpha"
CODENAME = "Spring Catalogue"
BUILD_DATE = date.today().isoformat()
OUTPUT_DEFAULT = os.path.join(ROOT, "docs", "SPB_GETTING_STARTED_GUIDE.pdf")

ACCENT = colors.HexColor("#0077aa")
ACCENT2 = colors.HexColor("#6b21a8")
INK = colors.HexColor("#1a2332")
MUT = colors.HexColor("#4a5568")
LINE = colors.HexColor("#cbd5e1")
PANEL = colors.HexColor("#f1f5f9")
WARN_C = colors.HexColor("#b45309")
GOOD = colors.HexColor("#047857")


class GuideDoc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        super().__init__(filename, **kw)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        self.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=self._on_page)])

    def _on_page(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUT)
        canvas.drawString(
            self.leftMargin, 0.45 * inch,
            f"Shokker Paint Booth — Getting Started Guide  ·  v{VERSION}  ·  {BUILD_DATE}",
        )
        canvas.drawRightString(self.pagesize[0] - self.rightMargin, 0.45 * inch, f"Page {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and getattr(flowable, "_bm_name", None):
            self.canv.bookmarkPage(flowable._bm_name)
            self.canv.addOutlineEntry(
                flowable._bm_title, flowable._bm_name,
                level=getattr(flowable, "_bm_level", 0),
            )


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "GuideTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=26, textColor=INK, spaceAfter=6, alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "GuideSubtitle", parent=base["Normal"], fontSize=12,
            textColor=MUT, alignment=TA_CENTER, spaceAfter=16,
        ),
        "part": ParagraphStyle(
            "GuidePart", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=22, textColor=ACCENT2, spaceBefore=6, spaceAfter=4, alignment=TA_CENTER,
        ),
        "part_sub": ParagraphStyle(
            "GuidePartSub", parent=base["Normal"], fontSize=11,
            textColor=MUT, alignment=TA_CENTER, spaceAfter=20,
        ),
        "h1": ParagraphStyle(
            "GuideH1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=16, textColor=ACCENT, spaceBefore=14, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "GuideH2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=12, textColor=ACCENT2, spaceBefore=10, spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "GuideH3", parent=base["Heading3"], fontName="Helvetica-Bold",
            fontSize=10.5, textColor=INK, spaceBefore=8, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "GuideBody", parent=base["Normal"], fontSize=9.5, leading=13,
            textColor=INK, alignment=TA_JUSTIFY, spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "GuideBullet", parent=base["Normal"], fontSize=9.5, leading=12.5,
            leftIndent=12, textColor=INK, spaceAfter=2,
        ),
        "tip": ParagraphStyle(
            "GuideTip", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=9, leading=12, textColor=GOOD, backColor=PANEL,
            borderPadding=6, spaceBefore=3, spaceAfter=6,
        ),
        "warn": ParagraphStyle(
            "GuideWarn", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=WARN_C, spaceBefore=3, spaceAfter=6,
        ),
        "toc": ParagraphStyle(
            "GuideToc", parent=base["Normal"], fontSize=9.5, leading=14, textColor=ACCENT,
        ),
        "toc_part": ParagraphStyle(
            "GuideTocPart", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=10, leading=16, textColor=ACCENT2, spaceBefore=4,
        ),
        "toc_sub": ParagraphStyle(
            "GuideTocSub", parent=base["Normal"], fontSize=9, leading=13,
            textColor=INK, leftIndent=14,
        ),
    }


def _link(anchor, label):
    return f'<link href="#{anchor}" color="#0077aa">{label}</link>'


def _make_ctx(st):
    story = []

    def _p(text, style_key, *, bm_name=None, bm_title=None, bm_level=0):
        para = Paragraph(text, st[style_key])
        if bm_name:
            para._bm_name = bm_name
            para._bm_title = bm_title or bm_name
            para._bm_level = bm_level
        story.append(para)

    def _table(_s, data, col_widths=None):
        t = Table(data, colWidths=col_widths, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PANEL),
            ("TEXTCOLOR", (0, 0), (-1, 0), INK),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 5))

    def part(s, anchor, title, subtitle=""):
        s.append(PageBreak())
        _p(f'<a name="{anchor}"/>{title}', "part", bm_name=anchor, bm_title=title, bm_level=0)
        if subtitle:
            _p(subtitle, "part_sub")

    def h1(s, anchor, title, body_text=""):
        _p(f'<a name="{anchor}"/>{title}', "h1", bm_name=anchor, bm_title=title, bm_level=1)
        if body_text:
            _p(body_text, "body")

    def h2(s, title):
        _p(title, "h2")

    def h3(s, title):
        _p(title, "h3")

    def body(s, text):
        _p(text, "body")

    def tip(s, text):
        _p(f"Tip: {text}", "tip")

    def warn(s, text):
        _p(f"⚠ {text}", "warn")

    def bullets(s, items):
        for item in items:
            story.append(Paragraph(f"• {item}", st["bullet"]))

    return {
        "story": story,
        "st": st,
        "p": _p,
        "part": part,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "body": body,
        "tip": tip,
        "warn": warn,
        "bullets": bullets,
        "table": _table,
    }


def _build_cover(st):
    s = []
    s.append(Spacer(1, 0.9 * inch))
    s.append(Paragraph("SHOKKER PAINT BOOTH", st["title"]))
    s.append(Paragraph("Getting Started Guide", st["title"]))
    s.append(Spacer(1, 0.12 * inch))
    s.append(Paragraph(
        f'Comprehensive user reference · v{VERSION} "{CODENAME}"<br/>Paint the paint. Not the pixel.',
        st["subtitle"],
    ))
    s.append(Spacer(1, 0.2 * inch))
    s.append(Paragraph(
        "A true onboarding guide for the main Paint Booth and companion labs: "
        "<b>Finish Viewer</b>, <b>Spec Sculpt</b>, and <b>Shokk Drop</b>. "
        "Use the PDF <b>Bookmarks</b> panel (left sidebar in Adobe Reader / Edge) or the "
        "clickable Table of Contents to jump between parts.",
        st["body"],
    ))
    s.append(Spacer(1, 0.15 * inch))
    s.append(Paragraph("<b>How this guide is organized</b>", st["h2"]))
    parts = [
        "Part 0 — Start Here (first 15 minutes, mental model)",
        "Part I — Header setup, load paint, settings",
        "Part II — Interface: zones, popout, layers (not right-panel finishes)",
        "Part III — Core workflow: colors → popout Base swatch → render",
        "Parts IV–V — Popout reference & finish types",
        "Parts VI–VIII — Spec maps, tools, render & deploy",
        "Part IX — Save & share (.shokk, recipes)",
        "Parts X–XII — Finish Viewer, Spec Sculpt, Shokk Drop",
        "Part XIII — Workflows · Reference",
    ]
    for line in parts:
        s.append(Paragraph(f"• {line}", st["bullet"]))
    s.append(PageBreak())
    return s


def _build_toc(st):
    s = []
    s.append(Paragraph('<a name="toc"/>Table of Contents', st["h1"]))
    p = s.append
    for anchor, bm_title, display, level in TOC:
        label = display or bm_title
        if level == 0:
            p(Spacer(1, 3))
            p(Paragraph(_link(anchor, label), st["toc_part"]))
        elif level == 1:
            p(Paragraph(_link(anchor, label), st["toc_sub"]))
    s.append(PageBreak())
    return s


def build_story(st):
    s = _build_cover(st)
    s.extend(_build_toc(st))
    ctx = _make_ctx(st)
    build_all(ctx)
    s.extend(ctx["story"])
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_DEFAULT)
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    st = _styles()
    doc = GuideDoc(
        out, pagesize=letter,
        rightMargin=0.7 * inch, leftMargin=0.7 * inch,
        topMargin=0.8 * inch, bottomMargin=0.7 * inch,
        title="Shokker Paint Booth — Getting Started Guide",
        author="Shokker Group",
    )
    doc.build(build_story(st))
    print(f"Wrote {out} ({os.path.getsize(out):,} bytes)")


if __name__ == "__main__":
    main()
