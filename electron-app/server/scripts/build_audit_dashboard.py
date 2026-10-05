# -*- coding: utf-8 -*-
"""Build a self-contained, visual HTML dashboard from the overnight audit.

Reads _overnight_audit/{findings.json, catalog_audit.json, MORNING_REPORT.md} and emits
_overnight_audit/audit_dashboard.html — open it in Chrome (file://, no server needed).

Thumbnails are embedded as base64 from the baked picker cache
(thumbnails/picker_split/{type}/{id}.png; spec patterns from spec_patterns_combined),
so the page is fully portable. Sections: summary cards, the FIXED finishes, and every
finding category with thumbnails (DEAD / WEAK_SPEC / CASE_DUP / top DUP_SPEC pairs) plus
sortable tables, and the narrative report rendered from markdown.
"""
import os, sys, json, base64, html, re

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
OUT = os.path.join(ROOT, "_overnight_audit")
TH = os.path.join(ROOT, "thumbnails")
findings = json.load(open(os.path.join(OUT, "findings.json"), encoding="utf-8"))
audit = json.load(open(os.path.join(OUT, "catalog_audit.json"), encoding="utf-8"))

_b64_cache = {}
_PLACEHOLDER = ("data:image/svg+xml;base64," + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><rect width="80" height="80" '
    b'fill="#222"/><text x="40" y="44" fill="#666" font-size="10" text-anchor="middle">n/a</text></svg>'
).decode())


def thumb(ftype, fid):
    key = (ftype, fid)
    if key in _b64_cache:
        return _b64_cache[key]
    paths = []
    if ftype in ("base", "pattern", "monolithic"):
        paths.append(os.path.join(TH, "picker_split", ftype, fid + ".png"))
    if ftype == "spec_pattern":
        paths.append(os.path.join(TH, "spec_patterns_combined", fid + "_160.png"))
        paths.append(os.path.join(TH, "spec_patterns_visual", fid + "_160.png"))
    uri = _PLACEHOLDER
    for p in paths:
        if os.path.exists(p):
            try:
                uri = "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
                break
            except Exception:
                pass
    _b64_cache[key] = uri
    return uri


def card(ftype, fid, note):
    return ('<figure class="card"><img loading="lazy" src="%s"><figcaption>'
            '<b>%s</b><span class="t">%s</span><span class="n">%s</span></figcaption></figure>'
            % (thumb(ftype, fid), html.escape(fid), ftype, html.escape(note)))


def pair_card(ftype, a, b, note):
    return ('<figure class="card pair"><div class="duo"><img loading="lazy" src="%s"><img loading="lazy" src="%s"></div>'
            '<figcaption><b>%s</b><span class="t">vs</span><b>%s</b><span class="n">%s · %s</span></figcaption></figure>'
            % (thumb(ftype, a), thumb(ftype, b), html.escape(a), html.escape(b), ftype, html.escape(note)))


def md_to_html(md):
    out, in_ul = [], False
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if in_ul:
                out.append("</ul>"); in_ul = False
            continue
        line_e = html.escape(line)
        line_e = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line_e)
        line_e = re.sub(r"`(.+?)`", r"<code>\1</code>", line_e)
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            if in_ul:
                out.append("</ul>"); in_ul = False
            lvl = len(m.group(1))
            txt = re.sub(r"`(.+?)`", r"<code>\1</code>", re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(m.group(2))))
            out.append("<h%d>%s</h%d>" % (lvl + 1, txt, lvl + 1))
        elif re.match(r"^\s*[-*]\s+", line):
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append("<li>" + re.sub(r"^\s*[-*]\s+", "", line_e) + "</li>")
        else:
            if in_ul:
                out.append("</ul>"); in_ul = False
            out.append("<p>" + line_e + "</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


# ---- build finding rows with stats from catalog_audit ----
def stat_for(ftype, fid):
    if ftype == "spec_pattern":
        e = audit.get("spec_pattern", {}).get(fid, {})
        s = e.get("160") or e.get("64") or {}
        return s.get("std"), None
    e = audit.get("paint", {}).get(ftype, {}).get(fid, {})
    spec = e.get("spec") or {}
    paint = (e.get("paint", {}) or {})
    p = paint.get("160") or paint.get("64") or {}
    return (spec.get("std") if isinstance(spec, dict) else None), (p.get("ms") if isinstance(p, dict) else None)


SECTIONS = []


def grid_section(key, title, blurb, items, kind="card", limit=None):
    if not items:
        return
    n = len(items)
    shown = items[:limit] if limit else items
    cards = []
    for it in shown:
        if kind == "pair":
            ftype, ab, note = it
            a, b = ab.split(" ~= ")
            cards.append(pair_card(ftype, a.strip(), b.strip(), note))
        else:
            ftype, fid, note = it
            cards.append(card(ftype, fid, note))
    more = ("<p class='more'>+%d more — see the table / findings.json</p>" % (n - len(shown))) if limit and n > len(shown) else ""
    SECTIONS.append((key, title, n,
        "<p class='blurb'>%s</p><div class='grid'>%s</div>%s" % (html.escape(blurb), "".join(cards), more)))


def table_section(key, title, blurb, rows, headers):
    if not rows:
        return
    head = "".join("<th>%s</th>" % html.escape(h) for h in headers)
    body = ""
    for r in rows:
        body += "<tr>" + "".join("<td>%s</td>" % html.escape(str(c)) for c in r) + "</tr>"
    SECTIONS.append((key, title, len(rows),
        "<p class='blurb'>%s</p><table class='sortable'><thead><tr>%s</tr></thead><tbody>%s</tbody></table>"
        % (html.escape(blurb), head, body)))


# FIXED (manual list — the bugs I repaired)
FIXED = [("base", "nebula", "spec-fn arity + stacked-array — FIXED"),
         ("base", "infinite_finish", "spec-fn arity + stacked-array — FIXED"),
         ("monolithic", "exotic_anti_metal", "RGB/RGBA broadcast — FIXED"),
         ("spec_pattern", "pearl_micro", "256-floor shape bug — FIXED")]
grid_section("fixed", "✅ Fixed (auto-repaired objective bugs)",
             "These threw render errors and are now repaired + verified. Thumbnails are the live, working renders.",
             FIXED)

grid_section("dead", "Dead output", "Renders completely flat (std≈0) — the finish does nothing visible.",
             findings.get("DEAD", []))
grid_section("weak", "Weak spec maps", "Spec channel spread below the quality floor — mostly gloss/clear bases (flat by nature).",
             findings.get("WEAK_SPEC", []))
# case-dup: render the two casings side by side
casepairs = []
for ftype, ids, note in findings.get("CASE_DUP", []):
    parts = [p.strip() for p in ids.split(" / ")]
    if len(parts) >= 2:
        casepairs.append((ftype, "%s ~= %s" % (parts[0], parts[1]), "case-collision (same file on disk)"))
grid_section("case", "Case-collision IDs", "Two IDs differing only by case → their cache PNGs overwrite each other on Windows.",
             casepairs, kind="pair")
# dup-spec: top tightest pairs visual + full table
dup = findings.get("DUP_SPEC", [])
def dup_dist(it):
    m = re.search(r"dist=([0-9.]+)", it[2]); return float(m.group(1)) if m else 1.0
dup_sorted = sorted(dup, key=dup_dist)
grid_section("dup", "Near-duplicate spec maps (tightest)", "Sibling finishes with near-identical spec maps — your 'all specs unique' targets. Showing the 36 closest pairs.",
             dup_sorted[:36], kind="pair")
table_section("dupall", "All near-duplicate pairs", "Full list, sorted tightest-first. The big clusters are the enh_/f_ gloss-base families.",
              [(it[0], it[1], it[2].replace("fam=", "").replace("dist=", "")) for it in dup_sorted],
              ["type", "pair", "family / distance"])
# slow: table
slow_rows = []
for ftype, fid, note in findings.get("SLOW", []):
    _, ms = stat_for(ftype, fid)
    slow_rows.append((ftype, fid, note.replace("paint@", "@")))
table_section("slow", "Slow renderers", "Over the 800ms/64px-thumbnail budget — entirely the Mortal Shokk (ms_*) family.",
              slow_rows, ["type", "finish", "timing"])

# ---- summary ----
order = [("fixed", "Fixed", len(FIXED)), ("dead", "Dead", len(findings.get("DEAD", []))),
         ("weak", "Weak spec", len(findings.get("WEAK_SPEC", []))),
         ("slow", "Slow", len(findings.get("SLOW", []))),
         ("dup", "Dup specs", len(dup)), ("case", "Case-dup", len(findings.get("CASE_DUP", [])))]
cards_html = "".join(
    "<a class='sc' href='#%s'><span class='num'>%d</span><span class='lbl'>%s</span></a>" % (k, n, t)
    for k, t, n in order)
counts = audit.get("meta", {}).get("counts", {})
nav = "".join("<a href='#%s'>%s</a>" % (k, t) for k, t, *_ in SECTIONS) + "<a href='#narrative'>Full report</a>"

body = "<header><h1>SPB Catalog Audit</h1><p class='sub'>Rendered %s bases · %s patterns · %s monolithics · %s spec patterns &mdash; %ss</p><div class='summary'>%s</div></header>" % (
    counts.get("base"), counts.get("pattern"), counts.get("monolithic"), counts.get("spec_pattern"),
    audit.get("meta", {}).get("elapsed_s"), cards_html)
body += "<nav>%s</nav>" % nav
for key, title, n, content in SECTIONS:
    body += "<section id='%s'><h2>%s <span class='cnt'>%d</span></h2>%s</section>" % (key, html.escape(title), n, content)

narrative = ""
mp = os.path.join(OUT, "MORNING_REPORT.md")
if os.path.exists(mp):
    narrative = md_to_html(open(mp, encoding="utf-8").read())
body += "<section id='narrative' class='narrative'><h2>Full overnight report</h2>%s</section>" % narrative

CSS = """
:root{--bg:#0e0f13;--panel:#171922;--ink:#e6e8ee;--mut:#8a90a2;--acc:#22c55e;--warn:#f5a623;--line:#262a36}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
a{color:#7ab8ff;text-decoration:none}h1{margin:0 0 4px;font-size:26px}h2{font-size:20px;border-bottom:1px solid var(--line);padding-bottom:8px;margin-top:0}
header{padding:28px 28px 8px}.sub{color:var(--mut);margin:0 0 16px}
.summary{display:flex;gap:12px;flex-wrap:wrap}.sc{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 18px;min-width:96px;display:flex;flex-direction:column;align-items:center}
.sc .num{font-size:26px;font-weight:800}.sc .lbl{color:var(--mut);font-size:12px}
nav{position:sticky;top:0;z-index:5;background:rgba(14,15,19,.92);backdrop-filter:blur(6px);border-bottom:1px solid var(--line);padding:10px 28px;display:flex;gap:18px;flex-wrap:wrap;font-size:13px}
section{padding:22px 28px;border-bottom:1px solid var(--line)}.cnt{color:var(--mut);font-weight:400;font-size:14px}
.blurb{color:var(--mut);margin:0 0 14px}.more{color:var(--mut);margin-top:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px}
.card{margin:0;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.card img{width:100%;display:block;aspect-ratio:1/1;object-fit:cover;background:#000}
.card .duo{display:flex}.card .duo img{width:50%}
figcaption{padding:8px 10px;display:flex;flex-direction:column;gap:1px}figcaption b{font-size:12px;word-break:break-all}
figcaption .t{color:var(--mut);font-size:11px}figcaption .n{color:var(--warn);font-size:11px}
.pair figcaption{flex-flow:row wrap;align-items:baseline;gap:6px}.pair .n{width:100%}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line)}
th{cursor:pointer;color:var(--mut);user-select:none;position:sticky;top:46px;background:var(--bg)}th:hover{color:var(--ink)}
td:nth-child(2){font-family:ui-monospace,Consolas,monospace;color:#cfe0ff}
.narrative{max-width:900px}.narrative code{background:#0a0b0f;padding:1px 5px;border-radius:4px;color:#9fe0b0;font-size:12px}
.narrative h3{margin-top:22px}.narrative li{margin:3px 0}
"""
JS = """
document.querySelectorAll('table.sortable').forEach(function(t){
 t.querySelectorAll('th').forEach(function(th,i){th.addEventListener('click',function(){
  var rows=[].slice.call(t.tBodies[0].rows);var asc=th._asc=!th._asc;
  rows.sort(function(a,b){var x=a.cells[i].innerText,y=b.cells[i].innerText;
   var nx=parseFloat(x),ny=parseFloat(y);
   if(!isNaN(nx)&&!isNaN(ny)){return asc?nx-ny:ny-nx;}
   return asc?x.localeCompare(y):y.localeCompare(x);});
  rows.forEach(function(r){t.tBodies[0].appendChild(r);});});});});
"""
doc = "<!doctype html><html><head><meta charset='utf-8'><title>SPB Catalog Audit</title><style>%s</style></head><body>%s<script>%s</script></body></html>" % (CSS, body, JS)
outp = os.path.join(OUT, "audit_dashboard.html")
open(outp, "w", encoding="utf-8").write(doc)
print("wrote %s (%.1f MB)" % (outp, len(doc) / 1024 / 1024))
