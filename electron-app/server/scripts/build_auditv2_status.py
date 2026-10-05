# -*- coding: utf-8 -*-
"""Build a self-contained AUDIT-V2 STATUS page for the owner's review from the 89-agent audit
workflow output + the implementer's fix tracking. Writes SPB_AUDIT_auditv2_status.html to BOTH trees
so it serves at localhost:59876/SPB_AUDIT_auditv2_status.html. Read-only reporting; no app changes.
"""
import json, os, html

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
SRV = os.path.join(ROOT, "electron-app", "server")
SRC = r"C:\Users\RICKY'~1\AppData\Local\Temp\claude\C--Users-Ricky-s-PC\f8a557e2-6dd0-4a08-905a-fe9ae2f524c4\tasks\wwx2yhtoi.output"

bugs = json.load(open(SRC, encoding="utf-8"))["result"]["confirmed_bugs"]

# classify each confirmed bug by title-substring → (status, note). Mirrors TOOL_AUDIT_PROGRESS.md.
def classify(t):
    F = ("FIXED", "")
    rules = [
        ("Color Brush ignores zone", ("FIXED", "clips to active zone selection")),
        ("Pattern brush also ignores", ("FIXED", "clips to active zone selection")),
        ("Pencil tool ignores zone", ("FIXED", "clips to active zone selection")),
        ("paints across entire canvas", ("FIXED", "blur/sharpen now clip to zone selection")),
        ("Eraser flow behavior contradicts", ("FIXED", "erase honors flow; false warning removed")),
        ("Clone Stamp does not copy source alpha", ("FIXED", "alpha channel now blended")),
        ("Operator Precedence", ("FIXED", "parenthesized the pivot-commit condition")),
        ("Lasso and Pen blocked in Layer Mode", ("FIXED", "layer-mode hints corrected to match reality")),
        ("Brush and Eraser tools missing usage hints", ("FIXED", "added to tool-hint map")),
        ("Missing tooltip hints for text and shape", ("FIXED", "added to tool-hint map")),
        ("Missing modifier hints for pick-item", ("FIXED", "added to tool-hint map")),
        ("wandContiguous control hidden", ("FIXED", "Contiguous checkbox now shown in Fill mode")),
        ("Layer-mode brush/erase mousedown lacks pressure", ("FIXED", "first dab honors pressure+flow")),
        ("Gradient tool pushes undo before validating", ("FIXED", "undo moved to mouseup after length check")),
        ("Zone Transform Arrow Key", ("FIXED", "toast corrected: arrows move, Alt+Arrow rotates")),
        ("Spatial-erase context hint", ("FIXED", "added the missing context hint")),
        ("Zone-pick uses hardcoded", ("FIXED", "inits from element's real offset/scale/rotation")),
        ("Text tool missing toolbar mode guard", ("FIXED", "wrapper now guards layer-only Text")),
        ("Shape tool missing toolbar mode guard", ("FIXED", "wrapper now guards layer-only Shape")),
        ("featherZoneSelection calls wrong undo", ("REJECTED", "FALSE POSITIVE — pushZoneUndo is undefined; pushUndo is already correct")),
        ("Spatial mask painter ignores opacity", ("DEFERRED", "spatial mask is categorical 0/1/2 — opacity falloff is wrong for it")),
        ("grow/shrink use different algorithm", ("DEFERRED", "suggested fix may mutate the wrong (zone vs layer) data structure")),
        ("smooth and layer-mode smooth", ("DEFERRED", "same zone-vs-layer data-model risk")),
        ("Fill bucket layer mode ignores selection", ("DEFERRED", "'subtract = don't fill' semantics are odd; low value")),
        ("brushFlow slider is ignored", ("BY DESIGN", "blur/sharpen are intentionally opacity-only (code comment); the Ignores-Flow warning already informs the user")),
        ("Pencil ignores brushFlow", ("BY DESIGN", "pencil is a binary hard-edge stamp; flow does not apply")),
        ("Auto-feather slider shown but no visual", ("DEFERRED", "live-preview overlay is a feature build; the slider itself works")),
        ("Advanced mask operations", ("DEFERRED", "layer-mode equivalents are a feature build")),
        ("THREE different feather implementations", ("NOTED", "informational; the three paths all work")),
        ("Smudge buffer lock comment", ("NOTED", "informational; not a defect")),
        ("Text tool textarea fontsize", ("DEFERRED", "minor high-zoom edit-box sizing; low value")),
        ("Shape tool does not warn", ("WON'T FIX", "padding keeps the box >=4px, so tiny shapes draw rather than silently fail; premise shaky")),
        ("Ambiguous Toast Messaging", ("DEFERRED", "minor wording; low value")),
    ]
    for key, val in rules:
        if key in t:
            return val
    return ("TODO", "")

ORDER = {"FIXED": 0, "REJECTED": 1, "BY DESIGN": 2, "DEFERRED": 3, "WON'T FIX": 4, "NOTED": 5, "TODO": 6}
COLOR = {"FIXED": "#3ee37d", "REJECTED": "#ff7a6a", "BY DESIGN": "#9DC4FF", "DEFERRED": "#ffd24a",
         "WON'T FIX": "#c0a0ff", "NOTED": "#8a93a3", "TODO": "#ff7a6a"}

rows = []
counts = {}
for b in bugs:
    st, note = classify(b.get("title", ""))
    counts[st] = counts.get(st, 0) + 1
    rows.append((ORDER.get(st, 9), st, note, b))
rows.sort(key=lambda r: (r[0], {"high": 0, "medium": 1, "low": 2}.get(r[3].get("severity", "low"), 3)))

TOOLS = [
    ("🌅 Sun Sweep", "relight a flat finish under a moving sun + export a hero GIF (route+UI, needs a booth restart)"),
    ("🍬 Candy Depth Sculptor", "paint lacquer depth; flakes read through wet candy (route+UI, needs restart)"),
    ("🗺️ Flash Map", "heat overlay of where the livery POPS on track vs reads dead matte — in-booth toggle, no restart"),
    ("🤖 Material Map", "per-region 'what material should this panel be' overlay — in-booth toggle, no restart"),
    ("🔬 Zone Spec-Channel Analyzer", "per-zone Metallic/Roughness/Clearcoat stats + honest labels — in-booth toggle, no restart"),
    ("🧩 Fill Unset Zones", "stamp one template zone's style onto every unconfigured zone — ⧉ button in the zone-actions row, one Undo"),
    ("🛟 Keybind collision detector", "offline regression guard for shortcut conflicts (scripts/keybind_collision_report.py)"),
]

def esc(s): return html.escape(s or "")

parts = []
parts.append("""<!doctype html><html><head><meta charset="utf-8"><title>SPB Audit v2 — Status</title>
<style>
body{background:#0b0d18;color:#e8eef7;font-family:Segoe UI,system-ui,Arial,sans-serif;margin:0;padding:28px;line-height:1.5;}
h1{font-size:22px;margin:0 0 4px;} .sub{color:#8a93a3;margin-bottom:18px;}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 22px;}
.chip{padding:5px 11px;border-radius:999px;font-weight:700;font-size:13px;background:rgba(255,255,255,.06);}
.tools{background:rgba(124,160,255,.07);border:1px solid rgba(124,160,255,.25);border-radius:10px;padding:14px 18px;margin-bottom:24px;}
.tools h2{font-size:15px;margin:0 0 8px;color:#9DC4FF;}
.tools li{margin:3px 0;}
table{border-collapse:collapse;width:100%;font-size:13px;}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid rgba(255,255,255,.08);vertical-align:top;}
th{color:#9DC4FF;position:sticky;top:0;background:#0b0d18;}
.st{font-weight:800;white-space:nowrap;} .sev{font-size:11px;opacity:.7;text-transform:uppercase;}
.note{color:#aeb6c2;} .ev{color:#6b7787;font-family:Consolas,monospace;font-size:11px;}
</style></head><body>""")
parts.append("<h1>SPB Toolbar Audit v2 — Status</h1>")
parts.append('<div class="sub">89-agent re-audit (zone + layer, adversarially verified) → 35 confirmed bugs. '
             'Generated 2026-06-20 during the self-improve run. Implementer verified every finding against real code before merging.</div>')
parts.append('<div class="chips">')
for st in sorted(counts, key=lambda s: ORDER.get(s, 9)):
    parts.append(f'<span class="chip" style="color:{COLOR.get(st,"#fff")}">{esc(st)}: {counts[st]}</span>')
parts.append('</div>')
parts.append('<div class="tools"><h2>New SPB-specific tools shipped this run</h2><ul>')
for name, desc in TOOLS:
    parts.append(f"<li><b>{esc(name)}</b> — {esc(desc)}</li>")
parts.append("</ul></div>")
parts.append("<table><tr><th>Status</th><th>Sev</th><th>Tool</th><th>Issue</th><th>Resolution</th></tr>")
for _, st, note, b in rows:
    parts.append("<tr>"
        f'<td class="st" style="color:{COLOR.get(st,"#fff")}">{esc(st)}</td>'
        f'<td class="sev">{esc(b.get("severity",""))}</td>'
        f'<td>{esc((b.get("tool","") or "")[:22])}<div class="sev">{esc(b.get("context",""))}</div></td>'
        f'<td>{esc(b.get("title",""))}<div class="ev">{esc((b.get("evidence","") or "")[:160])}</div></td>'
        f'<td class="note">{esc(note)}</td>'
        "</tr>")
parts.append("</table></body></html>")
doc = "".join(parts)

for d in (ROOT, SRV):
    with open(os.path.join(d, "SPB_AUDIT_auditv2_status.html"), "w", encoding="utf-8") as fh:
        fh.write(doc)
print("WROTE SPB_AUDIT_auditv2_status.html to both trees;", len(doc), "bytes")
print("status counts:", counts)
