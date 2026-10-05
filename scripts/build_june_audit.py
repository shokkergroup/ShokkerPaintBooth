#!/usr/bin/env python3
"""Build the JUNE COMPLETE AUDIT living HTML pages.

Three living audits, one per finish family:
    SPB_JUNE_AUDIT_SPEC_OVERLAYS.html   (spec overlays  -> SPM9 score)
    SPB_JUNE_AUDIT_BASES.html           (bases          -> M7 composite)
    SPB_JUNE_AUDIT_PATTERNS.html        (regular patterns -> M7 composite)

Each card shows the ACTUAL render(s) embedded as base64 (self-contained — works
opened from a file:// or via the server), the CURRENT AI rating (1-100) with
tier, auto-derived OBJECTIONS from the weakest sub-metrics, an owner rating
slider (1-100, step 1), a row of OWNER REASON CHECKBOXES (what *you* think is
wrong — multi-select), four verdict buttons (KEEP / REBUILD / REPLACE / REMOVE)
and a notes box. SUBMIT POSTs {verdict, rating, ai_rating, reasons[], notes} to
``/api/june-audit/<category>`` and the card disappears. Already-decided finishes
stay hidden on reload.

Re-run any time to REBUILD after work is done:
    python scripts/build_june_audit.py                 # all three
    python scripts/build_june_audit.py spec_overlay    # just one
"""
from __future__ import annotations

import base64
import datetime
import html
import io
import json
import os
import re
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS = os.path.join(ROOT, "_workbook_metrics")
THUMBS = os.path.join(ROOT, "thumbnails")
JS_DATA = os.path.join(ROOT, "paint-booth-0-finish-data.js")

OUT = {
    "spec_overlay": "SPB_JUNE_AUDIT_SPEC_OVERLAYS.html",
    "base": "SPB_JUNE_AUDIT_BASES.html",
    "pattern": "SPB_JUNE_AUDIT_PATTERNS.html",
}
TITLE = {"spec_overlay": "SPEC OVERLAYS", "base": "BASES", "pattern": "PATTERNS"}

# Owner reason-checkboxes — what *you* think is wrong (multi-select, per family).
REASONS = {
    "spec_overlay": [
        "Too similar to another", "Too blobby / macro", "Too noisy / busy",
        "Too flat / boring", "Weak spec colors", "Not enough fine detail",
        "Broken / artifacts", "Doesn't tile / seams", "Wrong vibe for name",
        "Low effort / lazy",
    ],
    "base": [
        "Too similar to another", "Color off / muddy", "Too flat / boring",
        "Too noisy / busy", "Weak spec / light reaction", "Not enough flake/detail",
        "Broken / artifacts", "Smeared / blobby on car", "Wrong vibe for name",
        "Low effort / lazy",
    ],
    "pattern": [
        "Too similar to another", "Pattern too big / blobby", "Too noisy / busy",
        "Too flat / boring", "Weak / no spec interest", "Not enough fine detail",
        "Broken / artifacts", "Doesn't tile / seams", "Wrong vibe for name",
        "Low effort / lazy",
    ],
}


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def _load_json(name: str) -> dict:
    try:
        with open(os.path.join(METRICS, name), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_js_meta() -> dict:
    meta: dict[str, dict] = {}
    try:
        with open(JS_DATA, "r", encoding="utf-8") as f:
            txt = f.read()
    except OSError:
        return meta
    # Finish entries are one-per-line `{ id: "...", name: "...", ... }`. The old `\{[^{}]*?...\}`
    # regex BROKE on any entry containing a nested object (e.g. `defaults: {}`) — it stopped at the
    # inner `{`, so those entries got no name and the audit fell back to pretty(id). Parse per line
    # instead (robust to nested braces); the group-list arrays have bare strings (no `id:`) so they skip.
    id_re = re.compile(r"\bid\s*:\s*[\"']([^\"']+)[\"']")
    name_re = re.compile(r"\bname\s*:\s*[\"']([^\"']+)[\"']")
    for line in txt.splitlines():
        idm = id_re.search(line)
        if not idm:
            continue
        fid = idm.group(1)
        if fid in meta:
            continue
        nm = name_re.search(line)
        meta[fid] = {"name": nm.group(1) if nm else ""}
    return meta


def load_spec_pattern_picker_ids() -> set:
    """The spec overlays ACTUALLY shown in the app = the `SPEC_PATTERNS` picker array in
    paint-booth-0-finish-data.js. Anything scored in the metrics but NOT in this list is a
    phantom (already removed from the app / engine orphan) and MUST be scrubbed from the
    audit. Filtering here keeps the audit honest even if the metrics pipeline re-scores the
    full engine catalog. (2026-06-03 owner: 'remove from the audit what isn't in the app'.)"""
    try:
        with open(JS_DATA, "r", encoding="utf-8") as f:
            txt = f.read()
    except OSError:
        return set()
    m = re.search(r"const SPEC_PATTERNS\s*=\s*\[", txt)
    if not m:
        return set()
    start = m.end()
    depth = 1
    i = start
    while i < len(txt) and depth > 0:
        c = txt[i]
        depth += (c == "[") - (c == "]")
        i += 1
    block = txt[start:i]
    return set(re.findall(r"id\s*:\s*['\"]([^'\"]+)['\"]", block))


def pretty(fid: str) -> str:
    return re.sub(r"[_\-]+", " ", fid).strip().title()


# --------------------------------------------------------------------------- #
# Embed renders as base64 (self-contained)
# --------------------------------------------------------------------------- #
def _embed(rel_path: str, max_px: int = 184, quality: int = 72) -> str | None:
    path = os.path.join(THUMBS, rel_path)
    if not os.path.isfile(path):
        return None
    try:
        im = Image.open(path).convert("RGB")
        if max(im.size) > max_px:
            im.thumbnail((max_px, max_px))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=quality)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def embed_thumbs(cat: str, fid: str) -> list[tuple[str, str]]:
    sources = {
        "spec_overlay": [(f"spec_patterns_visual/{fid}_160.png", "pattern"),
                         (f"spec_patterns/{fid}.png", "spec M/R/CC")],
        "base": [(f"base/{fid}.png", "paint")],
        "pattern": [(f"pattern/{fid}.png", "paint")],
    }[cat]
    out = []
    for rel, lbl in sources:
        uri = _embed(rel)
        if uri:
            out.append((uri, lbl))
    return out


# --------------------------------------------------------------------------- #
# Objections (from weakest sub-metrics)
# --------------------------------------------------------------------------- #
def objections_m7(e: dict) -> list[str]:
    out = []
    c = e.get("components", {}) or {}
    m1, m2, m5, m6 = c.get("m1"), c.get("m2"), c.get("m5"), c.get("m6")
    if m6 is not None and m6 < 55:
        out.append(f"Misses its intended look (M6 {m6:.0f}/100)")
    if m1 is not None and m1 < 50:
        out.append(f"Clone / too close to siblings (M1 {m1:.0f})")
    if m5 is not None and m5 < 50:
        out.append(f"Spec ↔ paint mismatch (M5 {m5:.0f})")
    if m2 is not None and m2 < 40:
        out.append(f"ID / intent mismatch (M2 {m2:.0f})")
    if (e.get("cloneSize") or 1) > 1:
        out.append(f"In a clone group of {e['cloneSize']}")
    if e.get("tier") in ("critical", "fix") and not out:
        out.append(f"Scores in the '{e.get('tier')}' tier")
    return out


def objections_spm9(e: dict) -> list[str]:
    out = []
    g = lambda k: float(e[k]) if isinstance(e.get(k), (int, float)) else None
    unq, scd, wow, mp = g("UNQ"), g("SCD"), g("WOW"), g("MP")
    pfv, fsc, mfs, sim = g("PFV"), g("FSC"), g("MFS"), g("SIM")
    if unq is not None and unq < 50:
        nearest = e.get("_max_sim_to")
        ms = e.get("_max_sim")
        extra = f" — nearest: {nearest} ({ms:.2f})" if (nearest and isinstance(ms, (int, float))) else ""
        out.append(f"Too similar to the catalog (UNQ {unq:.0f}){extra}")
    if scd is not None and scd < 50:
        out.append(f"Weak spec color/shade variety (SCD {scd:.0f})")
    fine = [v for v in (pfv, fsc, mfs) if v is not None]
    if fine and sum(fine) / len(fine) < 45:
        out.append("Not enough fine detail at car scale")
    if mp is not None and mp > 0.5:
        out.append("Macro / blobby pollution")
    if wow is not None and wow < 40:
        out.append(f"Low wow factor (WOW {wow:.0f})")
    if e.get("tier") in ("critical", "fix") and not out:
        out.append(f"Scores in the '{e.get('tier')}' tier")
    return out


def collect(cat: str, m7: dict, spm9: dict, meta: dict) -> list[dict]:
    rows = []
    if cat == "spec_overlay":
        picker_ids = load_spec_pattern_picker_ids()
        skipped = 0
        for fid, e in spm9.get("by_finish", {}).items():
            if picker_ids and fid not in picker_ids:
                skipped += 1  # phantom: scored but NOT in the app picker — scrub from audit
                continue
            comp = e.get("composite")
            rows.append({"id": fid, "ai": int(round(comp)) if isinstance(comp, (int, float)) else 0,
                         "tier": e.get("tier", "?"), "objections": objections_spm9(e)})
        if skipped:
            print(f"  [spec_overlay] scrubbed {skipped} phantom(s) not in the app picker")
    else:
        bf = m7.get("byFinish", m7.get("by_finish", {}))
        prefix = "base:" if cat == "base" else "pattern:"
        for key, e in bf.items():
            if not key.startswith(prefix):
                continue
            fid = key[len(prefix):]
            comp = e.get("composite")
            rows.append({"id": fid, "ai": int(round(comp)) if isinstance(comp, (int, float)) else 0,
                         "tier": e.get("tier", "?"), "objections": objections_m7(e)})
    for r in rows:
        r["name"] = (meta.get(r["id"], {}).get("name") or pretty(r["id"]))
        r["thumbs"] = embed_thumbs(cat, r["id"])
    rows.sort(key=lambda r: (r["ai"], r["id"]))
    return rows


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #
def card_html(cat: str, r: dict) -> str:
    e = html.escape
    ai, tier = r["ai"], e(str(r["tier"]))
    if r["thumbs"]:
        thumbs = "".join(f'<figure><img src="{u}" alt="{e(lbl)}"><figcaption>{e(lbl)}</figcaption></figure>'
                         for u, lbl in r["thumbs"])
    else:
        thumbs = '<figure class="broken"><figcaption>no baked render</figcaption></figure>'
    objs = "".join(f"<li>{e(o)}</li>" for o in r["objections"]) or \
        "<li class='ok'>No automatic flags — judge by eye.</li>"
    checks = "".join(
        f'<label><input type="checkbox" data-reason="{e(rs)}">{e(rs)}</label>'
        for rs in REASONS[cat]
    )
    return f"""
  <article class="card" data-id="{e(r['id'])}" data-ai="{ai}" data-tier="{tier}" data-name="{e(r['name'].lower())}">
    <div class="thumbs">{thumbs}</div>
    <div class="meta">
      <h2 class="title">{e(r['name'])}</h2>
      <div class="id">{e(r['id'])}</div>
      <div class="airow">AI now: <b class="ai tier-{tier}">{ai}<small>/100</small></b>
        <span class="tierpill tier-{tier}">{tier}</span></div>
      <ul class="objections">{objs}</ul>
    </div>
    <div class="ctrl">
      <div class="rate"><label>YOUR rating: <b class="rateval">{ai}</b><small>/100</small></label>
        <input type="range" min="1" max="100" step="1" value="{ai}" class="slider"></div>
      <div class="reasons-box"><div class="reasons-title">What's wrong (check any):</div>{checks}</div>
      <div class="verdicts">
        <button data-v="keep">KEEP</button><button data-v="rebuild">REBUILD</button>
        <button data-v="replace">REPLACE</button><button data-v="remove">REMOVE</button></div>
      <textarea class="notes" rows="2" placeholder="Notes / what you want instead (REPLACE) or what to fix (REBUILD)..."></textarea>
      <button class="submit" disabled>SUBMIT &#10003;</button>
    </div>
  </article>"""


PAGE = r"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SPB June Audit — __TITLE__</title>
<style>
:root{--bg:#08090c;--panel:#11141a;--line:#222834;--text:#eef2f6;--muted:#93a0ad;
--keep:#22c76b;--rebuild:#f2b83b;--replace:#5aa9ff;--remove:#ef5757;--accent:#ff7a18;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,Segoe UI,Roboto,Arial,sans-serif}
header{position:sticky;top:0;z-index:30;background:#0b0d12f2;border-bottom:1px solid var(--line);padding:12px 18px;display:flex;flex-wrap:wrap;gap:12px;align-items:center}
h1{font-size:16px;margin:0;letter-spacing:.5px}h1 b{color:var(--accent)}
.stat{font-size:12px;color:var(--muted)}.stat b{color:var(--text)}.spacer{flex:1}
input[type=text],select{background:#0c0f15;border:1px solid var(--line);color:var(--text);border-radius:7px;padding:6px 9px;font-size:12px}
#save{font-size:12px;color:var(--muted)}#save.ok{color:var(--keep)}#save.fail{color:var(--remove)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px;padding:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px;display:flex;flex-direction:column;gap:9px;transition:opacity .4s,transform .4s}
.card.fading{opacity:0;transform:scale(.96)}
.thumbs{display:flex;gap:6px}.thumbs figure{margin:0;flex:1;text-align:center}
.thumbs img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:8px;background:#05060a;border:1px solid var(--line)}
.thumbs figcaption{font-size:9px;color:var(--muted);margin-top:2px;text-transform:uppercase;letter-spacing:.4px}
.thumbs figure.broken{display:flex;align-items:center;justify-content:center;aspect-ratio:1;border:1px dashed var(--line);border-radius:8px;color:var(--muted);font-size:10px}
.title{font-size:15px;margin:0}.id{font-size:11px;color:var(--muted);font-family:ui-monospace,Consolas,monospace}
.airow{font-size:12px;color:var(--muted);margin-top:5px;display:flex;align-items:center;gap:7px}
.ai{font-size:20px}.ai small{font-size:11px;color:var(--muted)}
.tierpill{font-size:10px;padding:1px 7px;border-radius:99px;border:1px solid var(--line);text-transform:uppercase}
.tier-masterpiece,.tier-keeper{color:var(--keep)}.tier-ok{color:#8fd0ff}.tier-watch{color:var(--rebuild)}.tier-fix,.tier-critical{color:var(--remove)}
.objections{margin:8px 0 0;padding-left:18px;font-size:12px;color:#ffd9b0}.objections li{margin:2px 0}
.objections li.ok{color:var(--muted);list-style:none;margin-left:-18px}
.ctrl{margin-top:auto;border-top:1px solid var(--line);padding-top:9px;display:flex;flex-direction:column;gap:8px}
.rate label{font-size:12px;color:var(--muted)}.rate .rateval{color:var(--accent);font-size:15px}
.slider{width:100%;accent-color:var(--accent)}
.reasons-box{font-size:11px}.reasons-title{color:var(--muted);font-size:9px;text-transform:uppercase;letter-spacing:.4px;margin-bottom:3px}
.reasons-box label{display:inline-flex;align-items:center;gap:3px;margin:1px 8px 2px 0;cursor:pointer;color:#cdd6df;font-size:11px}
.reasons-box input{accent-color:var(--accent);cursor:pointer}
.verdicts{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:5px}
.verdicts button{padding:7px 2px;font-size:11px;font-weight:700;border-radius:7px;cursor:pointer;border:1px solid var(--line);background:#0c0f15;color:var(--text)}
.verdicts button[data-v=keep].sel{background:var(--keep);color:#04140a}.verdicts button[data-v=rebuild].sel{background:var(--rebuild);color:#1a1304}
.verdicts button[data-v=replace].sel{background:var(--replace);color:#04121f}.verdicts button[data-v=remove].sel{background:var(--remove);color:#1f0606}
.notes{width:100%;background:#0c0f15;border:1px solid var(--line);color:var(--text);border-radius:7px;padding:6px 8px;font-size:12px;resize:vertical;font-family:inherit}
.submit{padding:9px;font-weight:800;border-radius:8px;border:none;cursor:pointer;background:var(--accent);color:#160a02;letter-spacing:.5px}
.submit:disabled{opacity:.4;cursor:not-allowed}
.rereview-banner{margin-top:7px;padding:6px 9px;border-radius:7px;background:rgba(242,184,59,.12);border:1px solid rgba(242,184,59,.45);color:#ffe1a6;font-size:11px;line-height:1.4}
.rereview-banner b{color:var(--rebuild)}
.card[data-rereview]{border-left:3px solid var(--rebuild)}
.card[data-rereview="replace"]{border-left-color:var(--replace)}
.card[data-rereview="replace"] .rereview-banner b{color:var(--replace)}
.card.saved-flash{outline:2px solid var(--keep);outline-offset:2px}
#empty{display:none;text-align:center;color:var(--muted);padding:60px}
</style></head><body>
<header>
  <h1>SHOKKER &mdash; JUNE AUDIT &mdash; <b>__TITLE__</b></h1>
  <span class="stat"><b id="remaining">0</b> to review &middot; <b id="done">0</b> submitted &middot; <b>__COUNT__</b> total</span>
  <span class="spacer"></span>
  <input type="text" id="search" placeholder="search id / name..." style="width:170px">
  <select id="tierfilter"><option value="">all tiers</option><option>critical</option><option>fix</option><option>watch</option><option>ok</option><option>keeper</option><option>masterpiece</option></select>
  <select id="sort"><option value="worst">worst first</option><option value="best">best first</option><option value="az">A &rarr; Z</option></select>
  <span id="save"></span>
</header>
<main class="grid" id="grid">
__CARDS__
</main>
<div id="empty">&#127881; Nothing left in this batch. Tell the dev to work the queue + rebuild the page.</div>
<script>
const CATEGORY="__CATEGORY__", API="/api/june-audit/"+CATEGORY, LKEY="june_audit_"+CATEGORY;
const grid=document.getElementById('grid');
const draft=JSON.parse(localStorage.getItem(LKEY)||'{}');
let retryTimer=null;
function setSave(t,cls){const s=document.getElementById('save');s.textContent=t;s.className=cls||'';}
function counts(){document.getElementById('remaining').textContent=[...grid.querySelectorAll('.card')].filter(c=>c.style.display!=='none').length;}
function localSave(){localStorage.setItem(LKEY,JSON.stringify(draft));}
async function pushOne(id,entry){
  draft[id]=entry; localSave();
  try{const r=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({entries:{[id]:entry}})});
    if(!r.ok)throw new Error(await r.text());const j=await r.json();
    document.getElementById('done').textContent=(j.total||0);setSave('✓ saved '+new Date().toLocaleTimeString(),'ok');
    if(retryTimer){clearInterval(retryTimer);retryTimer=null;}
  }catch(e){setSave('✗ server down — saved to browser, will retry','fail');if(!retryTimer)retryTimer=setInterval(flushDrafts,5000);}
}
async function flushDrafts(){try{const r=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({entries:draft})});if(r.ok){setSave('✓ synced','ok');if(retryTimer){clearInterval(retryTimer);retryTimer=null;}}}catch(e){}}
grid.addEventListener('input',e=>{if(e.target.classList.contains('slider'))e.target.closest('.card').querySelector('.rateval').textContent=e.target.value;});
grid.addEventListener('click',e=>{
  const vb=e.target.closest('.verdicts button');
  if(vb){const card=vb.closest('.card');card.querySelectorAll('.verdicts button').forEach(b=>b.classList.toggle('sel',b===vb));card.querySelector('.submit').disabled=false;return;}
  const sb=e.target.closest('.submit');if(sb)submitCard(sb.closest('.card'));
});
function markRereview(card,d){
  // REBUILD/REPLACE = "I need to re-rate this after it's reworked" -> the card STAYS in the audit
  // (owner directive 2026-06-03). Show the prior verdict/rating/reasons/note for context.
  card.dataset.rereview=d.verdict;
  let b=card.querySelector('.rereview-banner');
  if(!b){b=document.createElement('div');b.className='rereview-banner';const m=card.querySelector('.meta');if(m)m.appendChild(b);}
  const rs=(d.reasons&&d.reasons.length)?(' — '+d.reasons.join(', ')):'';
  const nt=d.notes?(' · “'+d.notes+'”'):'';
  b.innerHTML='↻ you marked <b>'+String(d.verdict).toUpperCase()+'</b> ('+(d.rating||'?')+'/100)'+rs+nt+' — re-rate the rework';
}
function submitCard(card){
  const v=card.querySelector('.verdicts button.sel');if(!v)return;
  const reasons=[...card.querySelectorAll('.reasons-box input:checked')].map(c=>c.dataset.reason);
  const entry={verdict:v.dataset.v,rating:parseInt(card.querySelector('.slider').value,10),
    ai_rating:parseInt(card.dataset.ai,10),reasons:reasons,notes:card.querySelector('.notes').value.trim(),ts:Date.now()};
  pushOne(card.dataset.id,entry);
  // Every submit acknowledges by fading the card out of THIS view (clear feedback). KEEP/REMOVE are
  // final and stay gone; REBUILD/REPLACE are restored on the NEXT page load (the load pass re-shows
  // them with their banner) so you can re-rate the rework — "show back up" = reappear on reopen.
  card.classList.add('fading');
  setTimeout(()=>{card.style.display='none';card.classList.remove('fading');counts();
    if([...grid.querySelectorAll('.card')].every(c=>c.style.display==='none'))document.getElementById('empty').style.display='block';},420);
}
function apply(){
  const q=(document.getElementById('search').value||'').toLowerCase();
  const tf=document.getElementById('tierfilter').value, sort=document.getElementById('sort').value;
  let cards=[...grid.querySelectorAll('.card')];
  cards.forEach(c=>{const done=c.dataset.done==='1';
    const match=(!q||c.dataset.id.includes(q)||c.dataset.name.includes(q))&&(!tf||c.dataset.tier===tf);
    c.style.display=(done||!match)?'none':'';});
  cards.sort((a,b)=>sort==='best'?b.dataset.ai-a.dataset.ai:sort==='az'?a.dataset.id.localeCompare(b.dataset.id):a.dataset.ai-b.dataset.ai);
  cards.forEach(c=>grid.appendChild(c));counts();
}
['search','tierfilter','sort'].forEach(id=>document.getElementById(id).addEventListener('input',apply));
(async()=>{let decided={};
  try{const r=await fetch(API);if(r.ok){const j=await r.json();decided=j.entries||{};document.getElementById('done').textContent=j.total||0;}}catch(e){}
  Object.assign(decided,draft);
  grid.querySelectorAll('.card').forEach(c=>{const d=decided[c.dataset.id];if(d&&d.verdict){if(d.verdict==='keep'||d.verdict==='remove'){c.dataset.done='1';}else{markRereview(c,d);}}});
  apply();
})();
</script></body></html>"""


def build(cat, m7, spm9, meta):
    rows = collect(cat, m7, spm9, meta)
    cards = "\n".join(card_html(cat, r) for r in rows)
    page = (PAGE.replace("__TITLE__", TITLE[cat]).replace("__CATEGORY__", cat)
                .replace("__COUNT__", str(len(rows))).replace("__CARDS__", cards))
    with open(os.path.join(ROOT, OUT[cat]), "w", encoding="utf-8") as f:
        f.write(page)
    embedded = sum(1 for r in rows if r["thumbs"])
    return f"{OUT[cat]}: {len(rows)} finishes, {embedded} with embedded renders (worst AI {rows[0]['ai'] if rows else '-'})"


def main(argv):
    cats = [a for a in argv[1:] if a in OUT] or list(OUT)
    m7, spm9, meta = _load_json("m7_composite.json"), _load_json("spm9_spec_pattern.json"), load_js_meta()
    print(f"[build_june_audit] {datetime.datetime.now():%Y-%m-%d %H:%M}  meta ids: {len(meta)}")
    for cat in cats:
        print("  " + build(cat, m7, spm9, meta))


if __name__ == "__main__":
    main(sys.argv)
