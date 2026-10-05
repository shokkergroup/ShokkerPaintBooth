"""Encyclopedia v2 lane D - shared helpers for the figure scripts.

* a tiny SVG builder (dark theme = the app's tokens, text wrapping, overflow warnings)
* src(): turns "file + regex" into a verified "file:line" source string, so no number
  in a figure can cite a line that does not exist
* a manifest writer that MERGES into data/encyclopedia/figures.json by id (the SVG
  script owns g01..g20, the render script owns r01..r14; neither clobbers the other)

No engine import here - diagrams are cheap and never boot the engine.
"""
import json
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape as _esc

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "encyclopedia" / "figures"
MANIFEST = ROOT / "data" / "encyclopedia" / "figures.json"

# The app's own tokens (css/look-theme-prelude.css :root, css/spb-look-gallery-20260728.css :585 pro-orange)
C = dict(
    bg="#0b0e17", panel="#111524", raised="#171c2e", inset="#080a12", line="#2a3150",
    text="#c3ccdd", hi="#eef2f9", dim="#8794ad", faint="#5b667e",
    orange="#f5761a", orange_hi="#ff9a4d", cyan="#00e5ff", pink="#ff3366", blue="#3366ff",
    green="#33ff66", gold="#ffaa00", good="#4cc38a", bad="#ff2e63",
    # spec channel colours (matches the app's R METAL / G ROUGH / B COAT strip)
    R="#ff5d6c", G="#43d68a", B="#5b8cff", A="#c3ccdd",
)
FONT = "'Segoe UI', Inter, -apple-system, Roboto, Arial, sans-serif"
MONO = "Consolas, 'Courier New', monospace"

_file_cache = {}


def src(path, pattern, start=1, flags=0):
    """Return 'relative/path:line' for the first line >= start matching regex `pattern`."""
    p = ROOT / path
    if path not in _file_cache:
        _file_cache[path] = p.read_text(encoding="utf8", errors="replace").splitlines()
    rx = re.compile(pattern, flags)
    for i, ln in enumerate(_file_cache[path], 1):
        if i >= start and rx.search(ln):
            return f"{path}:{i}"
    raise RuntimeError(f"source not found: {path} /{pattern}/")


def reg(fid):
    """(M, R, CC, 'file:line') of a base finish straight from engine/base_registry_data.py."""
    path = "engine/base_registry_data.py"
    s = src(path, r'^\s*"%s"\s*:\s*\{' % re.escape(fid))
    line = _file_cache[path][int(s.rsplit(":", 1)[1]) - 1]
    m = re.search(r'"M":\s*(\d+).*?"R":\s*(\d+).*?"CC":\s*(\d+)', line)
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), s


def esc(s):
    return _esc(str(s), {'"': "&quot;"})


def tw(s, size, bold=False):
    """Estimated rendered width of a string (conservative)."""
    return len(s) * size * (0.57 if bold else 0.51)


def wrap(s, maxw, size, bold=False):
    words, lines, cur = str(s).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if tw(t, size, bold) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class Svg:
    def __init__(self, w=640, name=""):
        self.w, self.name = w, name
        self.p, self.d, self.maxy, self.warn = [], [], 0, []
        self._gid = 0

    def gid(self, pfx="g"):
        self._gid += 1
        return f"{pfx}{self._gid}"

    def _y(self, y):
        self.maxy = max(self.maxy, y)

    def defs(self, s):
        self.d.append(s)

    def raw(self, s, ymax=None):
        self.p.append(s)
        if ymax:
            self._y(ymax)

    def rect(self, x, y, w, h, fill="none", stroke=None, sw=1, r=0, extra=""):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.p.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}"{st} {extra}/>')
        self._y(y + h)

    def line(self, x1, y1, x2, y2, stroke=None, sw=1.5, dash=None, extra=""):
        stroke = stroke or C["line"]
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{da} {extra}/>')
        self._y(max(y1, y2))

    def circle(self, cx, cy, r, fill="none", stroke=None, sw=1, extra=""):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}"{st} {extra}/>')
        self._y(cy + r)

    def path(self, d, fill="none", stroke=None, sw=1.5, extra=""):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.p.append(f'<path d="{d}" fill="{fill}"{st} {extra}/>')

    def arrow(self, x1, y1, x2, y2, stroke=None, sw=2):
        """Line with an arrowhead at (x2,y2)."""
        import math
        stroke = stroke or C["dim"]
        self.line(x1, y1, x2, y2, stroke, sw)
        a = math.atan2(y2 - y1, x2 - x1)
        L = 9
        pts = [(x2, y2), (x2 - L * math.cos(a - 0.45), y2 - L * math.sin(a - 0.45)), (x2 - L * math.cos(a + 0.45), y2 - L * math.sin(a + 0.45))]
        self.p.append('<polygon points="%s" fill="%s"/>' % (" ".join(f"{a_:.1f},{b_:.1f}" for a_, b_ in pts), stroke))
        self._y(max(y1, y2))

    def text(self, x, y, s, size=14, fill=None, anchor="start", bold=False, italic=False, mono=False, extra=""):
        fill = fill or C["text"]
        fam = MONO if mono else FONT
        wt = ' font-weight="700"' if bold else ""
        it = ' font-style="italic"' if italic else ""
        if size < 13:
            self.warn.append(f"font {size} < 13: {s[:30]}")
        w = tw(s, size, bold)
        if anchor == "start" and x + w > self.w - 4:
            self.warn.append(f"overflow right ({x + w:.0f}>{self.w}): {s[:40]}")
        if anchor == "middle" and (x - w / 2 < 2 or x + w / 2 > self.w - 2):
            self.warn.append(f"overflow mid ({x - w / 2:.0f}..{x + w / 2:.0f}): {s[:40]}")
        if anchor == "end" and x - w < 2:
            self.warn.append(f"overflow left ({x - w:.0f}): {s[:40]}")
        self.p.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{wt}{it} {extra}>{esc(s)}</text>')
        self._y(y + size * 0.3)

    def para(self, x, y, s, maxw, size=14, fill=None, lh=1.38, anchor="start", bold=False):
        """Wrapped text; (x,y) is the first baseline; returns the next free baseline y."""
        for ln in wrap(s, maxw, size, bold):
            xx = x + (maxw / 2 if anchor == "middle" else 0)
            self.text(xx, y, ln, size, fill, anchor, bold)
            y += size * lh
        return y

    def pill(self, x, y, label, size=13, fill=None, color=None, padx=8, h=22, stroke=None):
        color = color or C["hi"]
        fill = fill or C["raised"]
        w = tw(label, size, True) + padx * 2
        self.rect(x, y, w, h, fill, stroke, 1.2, r=h / 2)
        self.text(x + w / 2, y + h / 2 + size * 0.34, label, size, color, "middle", True)
        return w

    def card(self, x, y, w, h, title=None, accent=None, fill=None):
        self.rect(x, y, w, h, fill or C["panel"], C["line"], 1.2, r=10)
        if accent:
            self.rect(x, y + 8, 4, h - 16, accent, r=2)
        if title:
            self.text(x + 16, y + 26, title, 16, C["hi"], bold=True)

    def render(self, title, desc, pad=18):
        h = int(self.maxy + pad)
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {h}" width="{self.w}" height="{h}" '
                f'role="img" aria-labelledby="t d"><title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>')
        defs = f"<defs>{''.join(self.d)}</defs>" if self.d else ""
        bg = f'<rect width="{self.w}" height="{h}" fill="{C["bg"]}"/>'
        return head + defs + bg + "".join(self.p) + "</svg>\n"


# ---------------------------------------------------------------- diagram registry
DIAGRAMS = {}


def diagram(fid):
    def deco(fn):
        DIAGRAMS[fid] = fn
        return fn
    return deco


def title(s, text, sub=None):
    s.text(16, 30, text, 20, C["hi"], bold=True)
    y = 30
    if sub:
        y = s.para(16, 52, sub, s.w - 32, 14, C["dim"]) - 8
    return y + 14


def lin(s, gid, c0, c1, horiz=True):
    s.defs(f'<linearGradient id="{gid}" x1="0" y1="0" x2="{1 if horiz else 0}" y2="{0 if horiz else 1}">'
           f'<stop offset="0" stop-color="{c0}"/><stop offset="1" stop-color="{c1}"/></linearGradient>')


# ---------------------------------------------------------------- manifest
FIGS = []


def figure(fid, title, caption, sources, alt, kind="svg", file=None, meta=None):
    ent = dict(id=fid, title=title, caption=caption, file=file or f"figures/{fid}.svg", kind=kind,
               sources=sorted(set(sources)), alt=alt)
    if meta:
        ent["meta"] = meta
    FIGS.append(ent)
    return ent


def write_manifest(owned_prefix):
    """Merge FIGS into figures.json (replace same ids, keep other lanes' entries), atomic."""
    cur = []
    if MANIFEST.exists():
        try:
            cur = json.loads(MANIFEST.read_text(encoding="utf8"))
        except Exception:
            cur = []
    byid = {e["id"]: e for e in cur}
    for e in FIGS:
        byid[e["id"]] = e
    out = [byid[k] for k in sorted(byid)]
    tmp = str(MANIFEST) + ".tmp"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(tmp, MANIFEST)
    return len(out)


def save_svg(fid, svg_text):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{fid}.svg"
    tmp = str(p) + ".tmp"
    with open(tmp, "w", encoding="utf8") as f:
        f.write(svg_text)
    os.replace(tmp, p)
    return p
