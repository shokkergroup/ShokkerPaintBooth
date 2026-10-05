# -*- coding: utf-8 -*-
"""Render the pre-Alpha readiness report (workflow JSON) into a styled HTML dashboard.

Reads the workflow task-output JSON (result.{alpha_blockers, should_fix, post_alpha,
owner_only_decisions, whats_already_solid, recommended_order_of_attack, honest_caveats})
and writes _overnight_audit/alpha_readiness.html — open in Chrome. Severity-colored,
effort + owner-only badges, with a live "fixed since" override list.
"""
import os, sys, json, html

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_overnight_audit", "alpha_readiness.json")
OUT = os.path.join(ROOT, "_overnight_audit", "alpha_readiness.html")

data = json.load(open(SRC, encoding="utf-8"))
r = data.get("result", data)


def jget(key):
    v = r.get(key)
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


blockers = jget("alpha_blockers") or []
should = jget("should_fix") or []
post = jget("post_alpha") or []
owner = jget("owner_only_decisions") or []
solid = jget("whats_already_solid") or []
order = jget("recommended_order_of_attack") or []
caveats = jget("honest_caveats") or []

# Items already resolved this session (live override on top of the report's snapshot).
FIXED = {"B1"}  # MC_DEFS catalog brick — fixed + verified after the report was generated.

EFFORT = {"S": "#22c55e", "M": "#f5a623", "L": "#ef4444"}


def esc(s):
    return html.escape(str(s))


def badge(txt, color, title=""):
    return '<span class="b" style="background:%s" title="%s">%s</span>' % (color, esc(title), esc(txt))


def block_card(it):
    bid = it.get("id", "")
    fixed = bid in FIXED
    ev = "#2b6b3a" if fixed else ("#3a2326" if not it.get("owner_only") else "#3a2e16")
    badges = badge(it.get("effort", "?"), EFFORT.get(it.get("effort"), "#666"), "effort")
    if it.get("owner_only"):
        badges += badge("OWNER", "#a855f7", "owner-only decision")
    if fixed:
        badges += badge("✓ FIXED THIS SESSION", "#22c55e")
    return ('<div class="card%s" style="border-left-color:%s">'
            '<div class="ch"><span class="bid">%s</span><span class="bt">%s</span><span class="bb">%s</span></div>'
            '<p class="prob">%s</p>'
            '<p class="fix"><b>Fix:</b> %s</p>'
            '<p class="ev">%s</p></div>') % (
        " fixed" if fixed else "", "#22c55e" if fixed else ("#a855f7" if it.get("owner_only") else "#ef4444"),
        esc(bid), esc(it.get("title", "")), badges,
        esc(it.get("problem", "")), esc(it.get("fix", "")),
        esc("evidence: " + it.get("evidence", "")) if it.get("evidence") else "")


def simple_card(it, accent):
    bid = it.get("id", "")
    badges = badge(it.get("effort", "?"), EFFORT.get(it.get("effort"), "#666"), "effort")
    if it.get("owner_only"):
        badges += badge("OWNER", "#a855f7", "owner-only")
    return ('<div class="card" style="border-left-color:%s">'
            '<div class="ch"><span class="bid">%s</span><span class="bt">%s</span><span class="bb">%s</span></div>'
            '<p class="prob">%s</p>%s</div>') % (
        accent, esc(bid), esc(it.get("title", "")), badges,
        esc(it.get("problem", it.get("detail", ""))),
        ('<p class="fix"><b>Fix:</b> %s</p>' % esc(it["fix"])) if it.get("fix") else "")


n_block = len(blockers)
n_fixed = sum(1 for b in blockers if b.get("id") in FIXED)
n_owner = sum(1 for b in blockers if b.get("owner_only"))
body = []
body.append("<header><h1>Shokker Paint Booth — Pre-Alpha Readiness</h1>"
            "<p class='sub'>%s</p>"
            "<div class='cards'>%s%s%s%s</div></header>" % (
                esc(r.get("generated", "")),
                "<a class='sc' href='#blockers'><span class='num'>%d</span><span>Blockers</span></a>" % n_block,
                "<a class='sc' style='--c:#22c55e' href='#blockers'><span class='num'>%d</span><span>Fixed this session</span></a>" % n_fixed,
                "<a class='sc' style='--c:#a855f7' href='#owner'><span class='num'>%d</span><span>Owner-only blockers</span></a>" % n_owner,
                "<a class='sc' href='#should'><span class='num'>%d</span><span>Should-fix</span></a>" % len(should)))
body.append("<nav><a href='#summary'>Summary</a><a href='#order'>Order of attack</a><a href='#blockers'>🔴 Blockers</a><a href='#should'>🟡 Should-fix</a><a href='#post'>🟢 Post-Alpha</a><a href='#owner'>Owner-only</a><a href='#solid'>What's solid</a></nav>")
body.append("<section id='summary'><h2>Summary</h2><p>%s</p></section>" % esc(r.get("summary", "")))
if order:
    body.append("<section id='order'><h2>Recommended order of attack</h2><ol>%s</ol></section>"
                % "".join("<li>%s</li>" % esc(o) for o in order))
body.append("<section id='blockers'><h2>🔴 Alpha Blockers <span class='cnt'>%d</span></h2>%s</section>"
            % (n_block, "".join(block_card(b) for b in blockers)))
body.append("<section id='should'><h2>🟡 Should-Fix <span class='cnt'>%d</span></h2>%s</section>"
            % (len(should), "".join(simple_card(s, "#f5a623") for s in should)))
body.append("<section id='post'><h2>🟢 Post-Alpha <span class='cnt'>%d</span></h2>%s</section>"
            % (len(post), "".join(simple_card(p, "#22c55e") for p in post)))
if owner:
    body.append("<section id='owner'><h2>Owner-only decisions</h2><ul>%s</ul></section>"
                % "".join("<li>%s</li>" % esc(o) for o in owner))
if solid:
    body.append("<section id='solid'><h2>✅ What's already solid</h2><ul>%s</ul></section>"
                % "".join("<li>%s</li>" % esc(s) for s in solid))
if caveats:
    body.append("<section id='caveats'><h2>Honest caveats</h2><ul>%s</ul></section>"
                % "".join("<li>%s</li>" % esc(c) for c in caveats))

CSS = """
:root{--bg:#0e0f13;--panel:#171922;--ink:#e6e8ee;--mut:#8a90a2;--line:#262a36}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14.5px/1.6 -apple-system,Segoe UI,Roboto,sans-serif}
header{padding:30px 30px 12px}h1{margin:0 0 4px;font-size:27px}.sub{color:var(--mut);margin:0 0 16px}
.cards{display:flex;gap:12px;flex-wrap:wrap}.sc{--c:#ef4444;background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--c);border-radius:10px;padding:12px 18px;display:flex;flex-direction:column;min-width:120px}
.sc .num{font-size:26px;font-weight:800;color:var(--c)}.sc span:last-child{color:var(--mut);font-size:12px}
nav{position:sticky;top:0;z-index:5;background:rgba(14,15,19,.93);backdrop-filter:blur(6px);border-bottom:1px solid var(--line);padding:11px 30px;display:flex;gap:18px;flex-wrap:wrap;font-size:13px}a{color:#7ab8ff;text-decoration:none}
section{padding:22px 30px;border-bottom:1px solid var(--line)}h2{font-size:21px;border-bottom:1px solid var(--line);padding-bottom:8px}.cnt{color:var(--mut);font-weight:400;font-size:15px}
.card{background:var(--panel);border:1px solid var(--line);border-left:4px solid #ef4444;border-radius:9px;padding:12px 16px;margin:12px 0}
.card.fixed{opacity:.72}.ch{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.bid{font-weight:800;color:var(--mut);font-family:ui-monospace,Consolas,monospace}.bt{font-weight:700;font-size:15px}
.bb{margin-left:auto;display:flex;gap:6px}.b{font-size:10.5px;font-weight:800;color:#000;padding:2px 8px;border-radius:20px}
.prob{color:#d3d7e0;margin:8px 0 6px}.fix{color:#9fe0b0;margin:6px 0}.fix b{color:#cfe0ff}
.ev{color:var(--mut);font-size:12px;font-family:ui-monospace,Consolas,monospace;margin:4px 0 0;word-break:break-word}
ul li,ol li{margin:6px 0}ol{padding-left:22px}
"""
doc = "<!doctype html><html><head><meta charset='utf-8'><title>SPB Pre-Alpha Readiness</title><style>%s</style></head><body>%s</body></html>" % (CSS, "".join(body))
open(OUT, "w", encoding="utf-8").write(doc)
print("wrote %s (%.0f KB)" % (OUT, len(doc) / 1024))
