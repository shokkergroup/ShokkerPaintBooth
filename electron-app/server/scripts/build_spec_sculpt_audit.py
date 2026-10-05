"""Build the Spec Sculpt PRESET AUDIT page.

Renders a composite spec thumbnail for every Spec Sculpt preset on a reference
paint, embeds them as base64 (so the page works even opened straight off disk),
and writes a self-contained interactive ``spec-sculpt-audit.html`` at repo root.

The page lets the owner mark each preset KEEP / REBUILD / RENAME / BUILD NEW,
give a 1-10 rating, tick why-it-failed reasons, suggest a name, and leave notes.
It auto-saves to localStorage and pushes to ``POST /api/spec-sculpt/audit`` (which
writes ``_audit/spec_sculpt_audit.json`` for the agent to read).

Usage:
  python scripts/build_spec_sculpt_audit.py \
      [--paint docs/hardmode_proof/dualshift_sunset_paint.png] [--size 256]
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.spec_sculpt.core import load_paint_rgb_float01  # noqa: E402
from engine.spec_sculpt.generate import scratch_spec_from_any_paint  # noqa: E402
from engine.spec_sculpt.presets import (  # noqa: E402
    PRESET_CATALOG_BY_ID,
    SPEC_SCULPT_PRESETS,
    normalize_preset_stack,
)


def _jpeg_b64(rgb_u8: np.ndarray, quality: int = 82) -> str:
    img = Image.fromarray(np.clip(rgb_u8, 0, 255).astype(np.uint8), mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _render_preset(tex, pid, seed, size):
    ps = normalize_preset_stack([[pid, 1.0]])
    spec = scratch_spec_from_any_paint(tex, seed=seed, chromatic_shift=True, preset_stack=ps)
    comp = np.stack([spec[:, :, 0], spec[:, :, 1], spec[:, :, 2]], axis=2)
    if comp.shape[0] != size:
        comp = np.asarray(Image.fromarray(comp).resize((size, size), Image.BILINEAR))
    return comp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paint", default="docs/hardmode_proof/dualshift_sunset_paint.png")
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--seed", type=int, default=9101)
    ap.add_argument("--out", default="spec-sculpt-audit.html")
    args = ap.parse_args()

    paint_path = os.path.join(ROOT, args.paint) if not os.path.isabs(args.paint) else args.paint
    tex, _, _ = load_paint_rgb_float01(paint_path, target_size=args.size)
    print(f"reference paint: {os.path.basename(paint_path)} @ {args.size}px")

    presets = []
    for i, p in enumerate(SPEC_SCULPT_PRESETS):
        pid = str(p["id"])
        finishes = ", ".join(fid for fid, _ in PRESET_CATALOG_BY_ID.get(pid, []))
        comp = _render_preset(tex, pid, args.seed + i * 17, args.size)
        presets.append({
            "id": pid,
            "label": str(p.get("label", pid)),
            "category": str(p.get("category", "")),
            "desc": str(p.get("description", "")),
            "texture": finishes,  # real finish id(s) this preset maps to
            "thumb": _jpeg_b64(comp),
        })
        if (i + 1) % 20 == 0:
            print(f"  rendered {i + 1}/{len(SPEC_SCULPT_PRESETS)}")
    print(f"rendered {len(presets)} presets")

    html = _PAGE_TEMPLATE.replace("/*__PRESETS__*/", json.dumps(presets))
    html = html.replace(
        "/*__META__*/",
        json.dumps({"paint": os.path.basename(paint_path), "size": args.size, "count": len(presets)}),
    )
    out_path = os.path.join(ROOT, args.out) if not os.path.isabs(args.out) else args.out
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    kb = os.path.getsize(out_path) // 1024
    print(f"wrote {out_path}  ({kb} KB)")


# ===========================================================================
# Page template — {PRESETS} JSON is injected into the marked slot.
# ===========================================================================
_PAGE_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spec Sculpt — Preset Audit</title>
<style>
  :root {
    --bg:#0c0e13; --panel:#13161f; --card:#161a24; --ink:#e8edf5; --muted:#8b95a7;
    --line:#242c3a; --accent:#5fb0ff; --keep:#10b981; --rebuild:#ef4444;
    --rename:#f59e0b; --new:#a855f7;
  }
  * { box-sizing:border-box; }
  html,body { margin:0; background:var(--bg); color:var(--ink);
    font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif; }
  a { color:var(--accent); }
  header { position:sticky; top:0; z-index:20; background:rgba(15,18,26,.96);
    backdrop-filter:blur(8px); border-bottom:1px solid var(--line); padding:12px 18px; }
  .htop { display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
  h1 { margin:0; font-size:17px; letter-spacing:.3px; }
  h1 .sub { color:var(--muted); font-size:12px; font-weight:400; margin-left:6px; }
  .grow { flex:1; }
  .counter { font-size:12px; color:var(--muted); font-variant-numeric:tabular-nums; }
  .bar { height:6px; border-radius:4px; background:#0a0d13; overflow:hidden; width:180px; border:1px solid var(--line); }
  .bar > i { display:block; height:100%; background:linear-gradient(90deg,var(--accent),var(--new)); width:0%; }
  button { font:inherit; padding:7px 13px; border-radius:7px; cursor:pointer;
    border:1px solid var(--line); background:#1b2130; color:var(--ink); }
  button:hover { filter:brightness(1.15); }
  button.primary { background:var(--accent); color:#06121f; font-weight:700; border:0; }
  button.ghost { background:transparent; }
  .filters { display:flex; gap:7px; flex-wrap:wrap; align-items:center; margin-top:10px; }
  .filters .chip { padding:4px 11px; border:1px solid var(--line); border-radius:20px; font-size:12px;
    background:transparent; color:var(--muted); cursor:pointer; }
  .filters .chip.active { color:var(--ink); border-color:var(--accent); background:rgba(95,176,255,.12); }
  input[type=text],select,textarea { background:#0a0d13; color:var(--ink);
    border:1px solid var(--line); border-radius:6px; padding:7px 9px; font:inherit; }
  input[type=text].search { width:200px; }
  .status { font-size:12px; color:var(--muted); }
  .status.ok { color:var(--keep); } .status.err { color:var(--rebuild); }
  main { padding:18px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:16px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:11px; overflow:hidden;
    display:flex; flex-direction:column; border-left:4px solid var(--line); }
  .card.v-keep { border-left-color:var(--keep); }
  .card.v-rebuild { border-left-color:var(--rebuild); }
  .card.v-rename { border-left-color:var(--rename); }
  .card.v-new { border-left-color:var(--new); }
  .thumb { width:100%; aspect-ratio:1/1; object-fit:cover; display:block; background:#000; cursor:zoom-in; }
  .cbody { padding:11px 13px 13px; display:flex; flex-direction:column; gap:9px; }
  .ctitle { display:flex; align-items:baseline; gap:8px; }
  .ctitle b { font-size:15px; }
  .ctitle .cat { color:var(--muted); font-size:11px; margin-left:auto; white-space:nowrap; }
  .cid { font-size:11px; color:var(--muted); font-family:ui-monospace,Menlo,monospace; }
  .cdesc { font-size:12px; color:#aeb6c4; min-height:18px; }
  .verdicts { display:grid; grid-template-columns:repeat(4,1fr); gap:5px; }
  .verdicts label { text-align:center; font-size:11.5px; font-weight:600; padding:6px 2px; border-radius:6px;
    border:1px solid var(--line); cursor:pointer; color:var(--muted); user-select:none; }
  .verdicts input { display:none; }
  .verdicts label.keep.on { background:rgba(16,185,129,.16); border-color:var(--keep); color:#7ff0c8; }
  .verdicts label.rebuild.on { background:rgba(239,68,68,.16); border-color:var(--rebuild); color:#ffb4b4; }
  .verdicts label.rename.on { background:rgba(245,158,11,.16); border-color:var(--rename); color:#ffd790; }
  .verdicts label.new.on { background:rgba(168,85,247,.16); border-color:var(--new); color:#dcb6ff; }
  .rowlabel { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.6px; }
  .rating { display:flex; gap:3px; flex-wrap:wrap; }
  .rating .n { width:24px; height:24px; border-radius:5px; border:1px solid var(--line); background:#0a0d13;
    font-size:12px; cursor:pointer; color:var(--muted); display:flex; align-items:center; justify-content:center; }
  .rating .n.on { background:var(--accent); color:#06121f; font-weight:700; border:0; }
  .reasons { display:flex; flex-wrap:wrap; gap:5px; }
  .reasons label { font-size:11px; padding:3px 8px; border:1px solid var(--line); border-radius:14px;
    color:var(--muted); cursor:pointer; }
  .reasons label:has(input:checked) { background:rgba(239,68,68,.12); border-color:var(--rebuild); color:#ffc9c9; }
  .reasons input { display:none; }
  textarea { width:100%; min-height:46px; resize:vertical; }
  .nameRow { display:none; }
  .card.show-name .nameRow { display:block; }
  .saved-dot { font-size:11px; color:var(--muted); }
  .saved-dot.dirty { color:var(--rename); }
  .cfoot { display:flex; align-items:center; gap:8px; margin-top:2px; }
  .cfoot .saved-dot { flex:1; }
  .submitBtn { background:var(--keep); color:#06231a; font-weight:700; border:0;
    padding:7px 13px; border-radius:7px; cursor:pointer; white-space:nowrap; }
  .submitBtn:hover { filter:brightness(1.1); }
  .submitBtn.needs { background:#1b2130; color:var(--muted); font-weight:600; }
  .card.removing { transition:opacity .26s ease, transform .26s ease; opacity:0; transform:scale(.95); pointer-events:none; }
  .chip.submitted-chip.active { color:#7ff0c8; border-color:var(--keep); background:rgba(16,185,129,.12); }
  .lightbox { position:fixed; inset:0; background:rgba(0,0,0,.86); display:none; z-index:50;
    align-items:center; justify-content:center; flex-direction:column; gap:10px; cursor:zoom-out; }
  .lightbox img { max-width:88vw; max-height:80vh; image-rendering:auto; border:1px solid var(--line); border-radius:8px; }
  .lightbox .lbl { color:var(--ink); font-size:14px; }
  .empty { color:var(--muted); padding:40px; text-align:center; }
</style>
</head>
<body>
<header>
  <div class="htop">
    <h1>🪄 Spec Sculpt — Preset Audit <span class="sub" id="metaSub"></span></h1>
    <div class="grow"></div>
    <div class="counter" id="counter">0 / 0 rated</div>
    <div class="bar"><i id="barFill"></i></div>
    <button class="primary" id="saveServer">💾 Save to server</button>
    <button id="exportBtn" class="ghost">⬇ Export JSON</button>
    <span class="status" id="statusMsg"></span>
  </div>
  <div class="filters" id="filters">
    <span class="chip active" data-f="all">All</span>
    <span class="chip" data-f="unrated">Unrated</span>
    <span class="chip" data-f="keep">Keep</span>
    <span class="chip" data-f="rebuild">Rebuild</span>
    <span class="chip" data-f="rename">Rename</span>
    <span class="chip" data-f="new">Build new</span>
    <span class="chip submitted-chip" data-f="submitted">✓ Submitted</span>
    <select id="catFilter"><option value="">All categories</option></select>
    <input type="text" class="search" id="search" placeholder="search id / name / notes…">
    <span class="grow"></span>
    <button id="collapseRated" class="ghost">Hide rated</button>
  </div>
</header>

<main>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" style="display:none;">No presets match this filter.</div>
</main>

<div class="lightbox" id="lightbox"><img id="lbImg" alt=""><div class="lbl" id="lbLbl"></div></div>

<script>
const PRESETS = /*__PRESETS__*/;
const META = /*__META__*/;
const REASONS = [
  ["dup","Too similar to another"],
  ["name","Name doesn't fit"],
  ["big","Pattern too large"],
  ["small","Too small / busy"],
  ["noisy","Too noisy / grainy"],
  ["flat","Too flat / lifeless"],
  ["material","Wrong material read"],
  ["color","Color / chroma off"],
  ["unreal","Not iRacing-believable"],
  ["artifact","Visible artifact"],
];
const VERDICTS = [["keep","KEEP"],["rebuild","REBUILD"],["rename","RENAME"],["new","BUILD NEW"]];
const LS_KEY = "spec_sculpt_audit_v1";
const API = "/api/spec-sculpt/audit";

let audit = {};            // pid -> {verdict, rating, reasons:[], name, notes, ts}
let filter = "all";
let catFilter = "";
let search = "";
let hideRated = false;

const $ = (id) => document.getElementById(id);

function loadLocal() {
  try { audit = JSON.parse(localStorage.getItem(LS_KEY) || "{}") || {}; }
  catch (e) { audit = {}; }
}
function saveLocal() {
  try { localStorage.setItem(LS_KEY, JSON.stringify(audit)); } catch (e) {}
}
function entry(pid) { return audit[pid] || (audit[pid] = { reasons: [] }); }

async function loadServer() {
  try {
    const r = await fetch(API, { method: "GET" });
    if (!r.ok) return;
    const j = await r.json();
    const srv = (j && j.entries) || {};
    // Merge: keep whichever entry has the newer ts; default to local on tie.
    Object.keys(srv).forEach(pid => {
      const s = srv[pid], l = audit[pid];
      if (!l || (s.ts || 0) > (l.ts || 0)) audit[pid] = s;
    });
    saveLocal();
    renderAll();
    setStatus(`Loaded ${Object.keys(srv).length} saved from server.`, "ok");
  } catch (e) { /* server not running — localStorage still works */ }
}

function setStatus(msg, cls) {
  const el = $("statusMsg"); el.textContent = msg || ""; el.className = "status " + (cls || "");
}

function countRated() { return PRESETS.filter(p => audit[p.id] && audit[p.id].verdict).length; }
function countSubmitted() { return PRESETS.filter(p => audit[p.id] && audit[p.id].submitted).length; }
function updateCounter() {
  const n = countRated(), s = countSubmitted(), t = PRESETS.length;
  $("counter").textContent = `${s} submitted · ${n} rated · ${t - s} left`;
  $("barFill").style.width = (t ? (100 * s / t) : 0) + "%";
}

let saveTimer = null;
function touch(pid) {
  const e = entry(pid); e.ts = Date.now();
  saveLocal(); updateCounter();
  const card = document.querySelector(`[data-card="${pid}"]`);
  if (card) { card.className = "card" + verdictClass(e.verdict) + (e.verdict === "rename" || e.verdict === "new" ? " show-name" : ""); }
  const dot = card && card.querySelector(".saved-dot");
  if (dot) { dot.textContent = "● unsaved"; dot.classList.add("dirty"); }
  const sb = card && card.querySelector(".submitBtn");
  if (sb) sb.classList.toggle("needs", !e.verdict && !e.rating);
}

function verdictClass(v) {
  return v ? " v-" + v : "";
}

function buildCard(p) {
  const e = entry(p.id);
  const card = document.createElement("div");
  card.className = "card" + verdictClass(e.verdict) + ((e.verdict === "rename" || e.verdict === "new") ? " show-name" : "");
  card.dataset.card = p.id;
  card.dataset.cat = p.category;

  const img = document.createElement("img");
  img.className = "thumb"; img.loading = "lazy"; img.src = p.thumb; img.alt = p.label;
  img.addEventListener("click", () => openLightbox(p));
  card.appendChild(img);

  const body = document.createElement("div");
  body.className = "cbody";

  body.innerHTML = `
    <div class="ctitle"><b>${esc(p.label)}</b><span class="cat">${esc(p.category)}</span></div>
    <div class="cid">${esc(p.id)}${p.texture ? " &middot; finish: " + esc(p.texture) : ""}</div>
    <div class="cdesc">${esc(p.desc)}</div>
    <div class="verdicts">${VERDICTS.map(([v, lbl]) =>
      `<label class="${v}${e.verdict === v ? " on" : ""}"><input type="radio" name="v-${p.id}" value="${v}"${e.verdict === v ? " checked" : ""}>${lbl}</label>`
    ).join("")}</div>
    <div><div class="rowlabel">Rating</div><div class="rating">${
      Array.from({length: 10}, (_, i) => i + 1).map(n =>
        `<div class="n${e.rating === n ? " on" : ""}" data-n="${n}">${n}</div>`).join("")
    }</div></div>
    <div><div class="rowlabel">Why it doesn't work</div><div class="reasons">${
      REASONS.map(([k, lbl]) =>
        `<label><input type="checkbox" value="${k}"${(e.reasons || []).includes(k) ? " checked" : ""}>${lbl}</label>`).join("")
    }</div></div>
    <div class="nameRow"><div class="rowlabel">Suggested name</div>
      <input type="text" class="nameInput" placeholder="your name idea" value="${esc(e.name || "")}"></div>
    <div><div class="rowlabel">Notes</div>
      <textarea class="notesInput" placeholder="rename idea, how to build it, what's wrong…">${esc(e.notes || "")}</textarea></div>
    <div class="cfoot">
      <span class="saved-dot">${e.verdict ? "saved locally" : ""}</span>
      <button class="submitBtn${e.verdict ? "" : " needs"}" title="Save this verdict to the server and clear it from the list">✓ Submit &amp; remove</button>
    </div>
  `;

  // verdict radios
  body.querySelectorAll(`input[name="v-${p.id}"]`).forEach(r => {
    r.addEventListener("change", () => {
      entry(p.id).verdict = r.value;
      body.querySelectorAll(".verdicts label").forEach(l => l.classList.remove("on"));
      r.closest("label").classList.add("on");
      touch(p.id);
    });
  });
  // rating
  body.querySelectorAll(".rating .n").forEach(n => {
    n.addEventListener("click", () => {
      const val = parseInt(n.dataset.n, 10);
      const cur = entry(p.id).rating;
      entry(p.id).rating = (cur === val ? null : val);
      body.querySelectorAll(".rating .n").forEach(x => x.classList.remove("on"));
      if (entry(p.id).rating) n.classList.add("on");
      touch(p.id);
    });
  });
  // reasons
  body.querySelectorAll(".reasons input").forEach(c => {
    c.addEventListener("change", () => {
      const set = new Set(entry(p.id).reasons || []);
      if (c.checked) set.add(c.value); else set.delete(c.value);
      entry(p.id).reasons = [...set];
      touch(p.id);
    });
  });
  // name + notes
  const nameEl = body.querySelector(".nameInput");
  nameEl.addEventListener("input", () => { entry(p.id).name = nameEl.value; touch(p.id); });
  const notesEl = body.querySelector(".notesInput");
  notesEl.addEventListener("input", () => { entry(p.id).notes = notesEl.value; touch(p.id); });
  // submit this card -> server, then remove it from the list (declutter)
  const submitBtn = body.querySelector(".submitBtn");
  if (submitBtn) submitBtn.addEventListener("click", () => submitOne(p.id));

  card.appendChild(body);
  return card;
}

function matches(p) {
  const e = audit[p.id] || {};
  if (catFilter && p.category !== catFilter) return false;
  if (filter === "submitted") return !!e.submitted;   // dedicated view of already-submitted
  if (e.submitted) return false;                       // submitted cards leave the working list
  if (hideRated && e.verdict) return false;
  if (filter === "unrated" && e.verdict) return false;
  if (["keep","rebuild","rename","new"].includes(filter) && e.verdict !== filter) return false;
  if (search) {
    const hay = (p.id + " " + p.label + " " + p.category + " " + (e.notes || "") + " " + (e.name || "")).toLowerCase();
    if (!hay.includes(search)) return false;
  }
  return true;
}

function renderAll() {
  const grid = $("grid"); grid.innerHTML = "";
  let shown = 0;
  PRESETS.forEach(p => { if (matches(p)) { grid.appendChild(buildCard(p)); shown++; } });
  $("empty").style.display = shown ? "none" : "block";
  updateCounter();
}

function openLightbox(p) {
  $("lbImg").src = p.thumb; $("lbLbl").textContent = p.label + "  ·  " + p.id;
  $("lightbox").style.display = "flex";
}

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;" }[c]));
}

async function saveToServer() {
  setStatus("Saving…", "");
  try {
    const r = await fetch(API, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entries: audit }),
    });
    const j = await r.json();
    if (r.ok && j.ok) {
      setStatus(`Saved ${j.total} entries to server.`, "ok");
      document.querySelectorAll(".saved-dot").forEach(d => { d.textContent = "saved"; d.classList.remove("dirty"); });
    } else {
      setStatus("Error: " + (j.error || r.statusText), "err");
    }
  } catch (e) {
    setStatus("Save failed (is the server running?). Your work is still saved locally — use Export JSON.", "err");
  }
}

async function submitOne(pid) {
  const e = entry(pid);
  if (!e.verdict && !e.rating) { setStatus("Pick a verdict (or a rating) before submitting.", "err"); return; }
  e.ts = Date.now();
  const wasSubmitted = e.submitted;
  e.submitted = true;
  saveLocal();
  setStatus("Submitting…", "");
  try {
    const r = await fetch(API, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entries: { [pid]: e } }),
    });
    const j = await r.json();
    if (r.ok && j.ok) {
      updateCounter();
      const card = document.querySelector(`[data-card="${pid}"]`);
      if (card) {
        card.classList.add("removing");
        const drop = () => { card.remove(); if (!$("grid").children.length) $("empty").style.display = "block"; };
        card.addEventListener("transitionend", drop, { once: true });
        setTimeout(drop, 380);
      }
      setStatus(`Submitted “${pid}”. ${countSubmitted()} / ${PRESETS.length} done — it's saved server-side.`, "ok");
    } else {
      e.submitted = wasSubmitted; saveLocal(); updateCounter();
      setStatus("Submit failed: " + (j.error || r.statusText) + " (still saved locally).", "err");
    }
  } catch (err) {
    e.submitted = wasSubmitted; saveLocal(); updateCounter();
    setStatus("Submit failed — server not reachable. Saved locally; open via the running server to submit.", "err");
  }
}

function exportJson() {
  const blob = new Blob([JSON.stringify({ meta: META, entries: audit }, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "spec_sculpt_audit.json";
  a.click();
}

function initCategories() {
  const cats = [...new Set(PRESETS.map(p => p.category))].sort();
  const sel = $("catFilter");
  cats.forEach(c => { const o = document.createElement("option"); o.value = c; o.textContent = c; sel.appendChild(o); });
}

function wire() {
  $("metaSub").textContent = `— ${META.count} presets on “${META.paint}”. Mark each, then Save to server.`;
  $("filters").querySelectorAll(".chip").forEach(ch => {
    ch.addEventListener("click", () => {
      $("filters").querySelectorAll(".chip").forEach(x => x.classList.remove("active"));
      ch.classList.add("active"); filter = ch.dataset.f; renderAll();
    });
  });
  $("catFilter").addEventListener("change", e => { catFilter = e.target.value; renderAll(); });
  $("search").addEventListener("input", e => { search = e.target.value.toLowerCase().trim(); renderAll(); });
  $("collapseRated").addEventListener("click", () => {
    hideRated = !hideRated; $("collapseRated").textContent = hideRated ? "Show rated" : "Hide rated"; renderAll();
  });
  $("saveServer").addEventListener("click", saveToServer);
  $("exportBtn").addEventListener("click", exportJson);
  $("lightbox").addEventListener("click", () => { $("lightbox").style.display = "none"; });
  window.addEventListener("keydown", e => {
    if (e.key === "Escape") $("lightbox").style.display = "none";
    if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); saveToServer(); }
  });
}

initCategories();
loadLocal();
wire();
renderAll();
loadServer();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
