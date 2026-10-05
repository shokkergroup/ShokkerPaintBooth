# -*- coding: utf-8 -*-
"""Build SPB_AUDIT_tool_audit.html from the toolbar-tool-audit workflow result JSON.
Self-contained; served via the /SPB_AUDIT_<name>.html route (must live in electron-app/server)."""
import os, sys, json, html, time

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
OUT = os.path.join(ROOT, "SPB_AUDIT_tool_audit.html")
# the workflow result JSON (passed as argv[1], else default temp path)
src = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\RICKY'~1\AppData\Local\Temp\claude\C--Users-Ricky-s-PC\f8a557e2-6dd0-4a08-905a-fe9ae2f524c4\tasks\whwc1ppeb.output"
data = json.load(open(src, encoding="utf-8"))
rep = data["result"]["report"]
stats = data["result"]["stats"]

def esc(s): return html.escape(str(s or ""))
SEVC = {"critical": "#ff3b3b", "high": "#ff7a2f", "medium": "#e0a13a", "low": "#5fb0ff", "none": "#38d39f"}

# fix-status: list of {contains, status} — a bug is marked if a substring matches its problem text.
_sf = os.path.join(ROOT, "_reworks_2026", "tool_fix_status.json")
STATUS_RULES = json.load(open(_sf)) if os.path.exists(_sf) else []
def _status_for(problem):
    for r in STATUS_RULES:
        if r.get("contains", "") and r["contains"] in problem:
            return r.get("status", "")
    return ""

bug_rows = ""
for i, b in enumerate(rep["confirmedBugs"]):
    sev = b["severity"]; col = SEVC.get(sev, "#888")
    st = _status_for(b["problem"])
    badge = f'<span class="fixed">✓ FIXED</span>' if st == "fixed" else (f'<span class="wip">in progress</span>' if st == "wip" else '<span class="todo">queued</span>')
    bug_rows += f"""<tr>
      <td><span class="sev" style="background:{col}">{esc(sev)}</span></td>
      <td class="nm">{esc(b['tool'])}<br><span class="ctx">{esc(b['context'])}</span></td>
      <td>{esc(b['problem'])}</td>
      <td class="fix">{esc(b['fix'])}</td>
      <td class="ev"><code>{esc(b['evidence'])}</code></td>
      <td>{badge}</td>
    </tr>"""

works = "".join(f"<li>{esc(w)}</li>" for w in rep["worksAsIntended"])
imps = ""
for im in rep["improvements"]:
    ic = {"high": "#38d39f", "medium": "#e0a13a", "low": "#5fb0ff"}.get(im["impact"], "#888")
    imps += f"""<div class="imp"><div class="imp-h"><b>{esc(im['idea'])}</b>
      <span class="tag" style="border-color:{ic};color:{ic}">{esc(im['impact'])} impact · {esc(im['effort'])}</span></div>
      <div class="imp-r">{esc(im['rationale'])}</div></div>"""
recs = "".join(f"<li>{esc(r)}</li>" for r in rep["topRecommendations"])

HTMLDOC = f"""<!doctype html><html><head><meta charset="utf-8"><title>SPB Toolbar Tool Audit</title>
<style>
body{{background:#0d0e12;color:#e8e8ee;font:15px/1.55 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:0 0 80px}}
.wrap{{max-width:1240px;margin:0 auto;padding:24px}}
h1{{font-size:29px;margin:.2em 0}} h2{{font-size:21px;border-bottom:2px solid #2a2b34;padding-bottom:6px;margin-top:40px}}
.lead{{color:#b9b9c6;font-size:16px}}
.kpis{{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}}
.kpi{{background:#16171d;border:1px solid #24252e;border-radius:10px;padding:13px 18px;flex:1;min-width:130px}}
.kpi b{{display:block;font-size:25px;color:#fff}} .kpi span{{color:#8a8a99;font-size:12px}}
.box{{background:#14151b;border:1px solid #24252e;border-radius:10px;padding:16px 20px;margin:16px 0}}
.box.accent{{border-left:4px solid #ff7a2f}}
table{{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #20212a;vertical-align:top}}
th{{color:#8a8a99}} td.nm{{font-weight:600;color:#fff;white-space:nowrap}} .ctx{{font-size:11px;color:#6da8ff;font-weight:400}}
.sev{{display:inline-block;padding:2px 8px;border-radius:10px;color:#0d0e12;font-weight:700;font-size:11px;text-transform:uppercase}}
td.fix{{color:#bfe3cf}} td.ev code{{font-size:11px;color:#7f8aa0;word-break:break-word}}
.fixed{{color:#38d39f;font-weight:700}} .wip{{color:#e0a13a;font-weight:700}} .todo{{color:#8a8a99}}
ul{{color:#c5c5d2}} li{{margin:5px 0}}
.imp{{background:#16171d;border:1px solid #24252e;border-radius:8px;padding:12px 16px;margin:8px 0}}
.imp-h{{display:flex;justify-content:space-between;gap:10px;align-items:center}} .imp-r{{color:#9b9baa;font-size:13px;margin-top:5px}}
.tag{{font-size:11px;border:1px solid;border-radius:10px;padding:1px 9px;white-space:nowrap}}
code{{background:#1c1d25;padding:1px 5px;border-radius:4px}}
</style></head><body><div class="wrap">
<h1>Shokker Paint Booth — Toolbar Tool Audit</h1>
<p class="lead">Deep functional audit of every Zone &amp; Layer tool: do they work exactly as intended? Plus a roadmap to use the toolbar to its full potential. Generated {time.strftime('%Y-%m-%d %H:%M')} via a {esc(data.get('agentCount','?'))}-agent workflow.</p>
<div class="kpis">
  <div class="kpi"><b>{stats['totalFindings']}</b><span>total findings</span></div>
  <div class="kpi"><b>{stats['claimedDefects']}</b><span>claimed defects</span></div>
  <div class="kpi"><b>{stats['confirmedDefects']}</b><span>confirmed real (adversarially verified)</span></div>
  <div class="kpi"><b>{len(rep['worksAsIntended'])}</b><span>tools verified working</span></div>
  <div class="kpi"><b>{len(rep['improvements'])}</b><span>improvement ideas</span></div>
</div>
<div class="box accent"><b>Bottom line.</b> {esc(rep['summary'])}</div>

<h2>🔝 Top recommendations (in order)</h2>
<div class="box"><ol>{recs}</ol></div>

<h2>🐛 Confirmed bugs ({len(rep['confirmedBugs'])}) — verified against the code</h2>
<table>
  <tr><th>Sev</th><th>Tool</th><th>Problem</th><th>Fix</th><th>Evidence</th><th>Status</th></tr>
  {bug_rows}
</table>

<h2>🚀 Improvement roadmap — use the toolbar to its full potential</h2>
{imps}

<h2>✅ Verified working as intended</h2>
<div class="box"><ul>{works}</ul></div>

<p class="lead" style="margin-top:28px">Fixes are being applied surgically and synced to both trees; the Status column updates as each lands. None of these are crashes — every tool produces correct output for normal use; the work is making the promises true and closing zone/layer parity gaps.</p>
</div></body></html>"""

open(OUT, "w", encoding="utf-8").write(HTMLDOC)
print("WROTE", OUT, round(len(HTMLDOC)/1024), "KB")
