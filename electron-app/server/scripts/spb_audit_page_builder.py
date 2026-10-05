# -*- coding: utf-8 -*-
"""Shared SPB audit-page generator (docs/AUDIT_PAGE_SPEC.md).

Owner upgrades 2026-06-09 evening:
- PER-CARD SUBMIT (like the legacy june audits): each card has its own Submit
  that POSTs immediately and fades the card — Ricky can rate a few, tell
  Claude to act on what's submitted, and keep going. Bulk "Submit all decided"
  stays in the bottom bar.
- EXPANDED multi-select reason chips (legacy taxonomy + per-kind extras) and
  the standing "Render time too long" chip.
- Render-time badge per card (measured at REAL size; owner doctrine ~1s, >3s fail).

Loop rule: keep/remove/rename stay hidden on reload (server GET hides rated);
when Claude REBUILDS/REPLACES an item it clears that id from
electron-app/server/_audit/june_<cat>_audit.json so the redone item reappears.
"""
import base64, json, os

COMMON_CHIPS = [
    "Too similar to another", "Too blobby / macro", "Too noisy / busy",
    "Too flat / boring", "Not enough fine detail", "Broken / artifacts",
    "Wrong vibe for name", "Low effort / lazy", "Colors muddy",
    "Clips / blown out", "Too dark on car", "Too bright / washed out",
    "Render time too long", "Other (see notes)",
]
KIND_EXTRA = {
    "finish": ["Weak spec colors", "Spec wrong for paint", "No depth"],
    "pattern": ["Doesn't tile / seams", "Wrong scale", "Too sparse"],
    "spec_overlay": ["Weak spec colors", "Channels correlated / single-hue",
                     "No angle reveal", "Too subtle on car", "Too harsh", "Dead/flat zone"],
}
KIND_LABEL = {"spec_overlay": "SPEC OVERLAYS", "pattern": "PATTERNS", "finish": "FINISHES"}


def chips_for(kind):
    return KIND_EXTRA.get(kind, []) + COMMON_CHIPS


def _esc(s):
    return str(s).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def build_page(category, title_html, sub_html, meta, thumbs_dir, outfile, accent="#e8c050"):
    import cv2
    sections = {}
    for m in meta:
        sections.setdefault(m.get("kind", "finish"), []).append(m)

    # [2026-06-12 owner bug: ghostlab page showed "all items have verdicts"]
    # Unknown kinds (e.g. "experiment", "blend mode") were silently DROPPED by
    # the fixed kind loop below -> zero cards -> done-banner. Fold any unknown
    # kind into "finish" so every meta entry always renders.
    for k in list(sections.keys()):
        if k not in ("spec_overlay", "pattern", "finish"):
            sections.setdefault("finish", []).extend(sections.pop(k))

    blocks = []
    multi = len(sections) > 1
    for kind in ("spec_overlay", "pattern", "finish"):
        items = sections.get(kind)
        if not items:
            continue
        cards = []
        for m in items:
            png = os.path.join(thumbs_dir, m["id"] + ".png")
            ok, jpg = cv2.imencode(".jpg", cv2.imread(png), [cv2.IMWRITE_JPEG_QUALITY, 87])
            assert ok, png
            b64 = base64.b64encode(jpg.tobytes()).decode("ascii")
            chips = "".join('<button class="chip" data-chip="%s">%s</button>' % (_esc(c), _esc(c))
                            for c in chips_for(kind))
            rt = m.get("render_s")
            rt_badge = ""
            if rt is not None:
                cls = "rt-bad" if rt > 3.0 else ("rt-warn" if rt > 1.5 else "rt-ok")
                rt_badge = '<span class="rt %s" title="measured full-size render (paint+spec)">⏱ %.1fs</span>' % (cls, rt)
            mip_badge = ('<span class="mip" title="detail retention at 1/4 view — >=0.45 healthy">MIP %s</span>'
                         % m["mip"]) if m.get("mip") is not None else ""
            tech = (" · " + _esc(m["technique"])) if m.get("technique") else ""
            cards.append('''
<div class="card" data-id="{id}" data-kind="{kind}" data-ai="{ai}">
  <img class="swatch" src="data:image/jpeg;base64,{b64}" alt="{id}" loading="lazy">
  <div class="body">
    <div class="titlerow"><span class="name">{name}</span><span class="badges"><span class="ai" title="structure meter (not a quality judgment)">AI {ai}</span>{mip}{rt}</span></div>
    <div class="iid">{id}{tech}</div>
    <div class="desc">{desc}</div>
    <div class="verdicts">
      <button class="v keep" data-v="keep">Keep</button>
      <button class="v" data-v="replace">Replace</button>
      <button class="v" data-v="rebuild">Rebuild</button>
      <button class="v" data-v="rename">Rename</button>
      <button class="v remove" data-v="remove">Remove</button>
    </div>
    <div class="raterow"><label>Rating <output>50</output></label><input type="range" min="1" max="100" value="50" step="1" class="rate"></div>
    <div class="chips-title">WHAT'S WRONG (check any):</div>
    <div class="chips">{chips}</div>
    <textarea class="notes" placeholder="Notes (what would make it right?)"></textarea>
    <button class="cardsubmit" disabled>SUBMIT THIS ONE</button>
  </div>
</div>'''.format(id=m["id"], kind=kind, ai=m.get("ai_rating", ""), b64=b64, name=_esc(m["name"]),
                 desc=_esc(m["desc"]), chips=chips, mip=mip_badge, rt=rt_badge, tech=tech))
        head = ('<h2 class="section">%s <span class="seccount" data-kind="%s"></span></h2>\n'
                % (KIND_LABEL.get(kind, kind.upper()), kind)) if multi else ""
        blocks.append(head + '<div class="grid">%s\n</div>' % "\n".join(cards))

    html = _TEMPLATE.replace("__TITLE__", title_html).replace("__SUB__", sub_html)
    html = html.replace("__CARDS__", "\n".join(blocks)).replace("__CAT__", category)
    html = html.replace("__ACCENT__", accent)
    open(outfile, "w", encoding="utf-8", newline="\n").write(html)
    print("WROTE %s (%.1f MB, %d cards)" % (outfile, os.path.getsize(outfile) / 1048576.0, len(meta)))


_TEMPLATE = '''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SPB Audit — __CAT__</title>
<style>
  :root { --bg:#0d0f14; --panel:#161a22; --line:#262c3a; --txt:#e8eaf0; --dim:#9aa3b5;
          --gold:__ACCENT__; --red:#c23b4a; --blue:#4a6ed0; --green:#3dbb6e; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--txt); font:14px/1.45 "Segoe UI", system-ui, sans-serif; padding-bottom:90px; }
  header { padding:22px 26px 10px; }
  h1 { margin:0 0 4px; font-size:22px; letter-spacing:.5px; }
  h1 .flag { color:var(--gold); }
  .sub { color:var(--dim); font-size:13px; max-width:920px; }
  .section { margin:26px 26px 10px; font-size:15px; letter-spacing:2px; color:var(--gold); border-bottom:1px solid var(--line); padding-bottom:6px; }
  .seccount { color:var(--dim); font-weight:400; letter-spacing:0; font-size:12px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(480px, 1fr)); gap:18px; padding:18px 26px 0; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:10px; overflow:hidden; display:flex; flex-direction:column; }
  .card.decided { outline:2px solid var(--green); }
  .card.decided.rem { outline-color:var(--red); }
  .swatch { width:100%; display:block; background:#000; }
  .body { padding:12px 14px 14px; display:flex; flex-direction:column; gap:8px; }
  .titlerow { display:flex; justify-content:space-between; align-items:center; gap:8px; }
  .name { font-weight:600; font-size:16px; }
  .badges { display:flex; gap:6px; flex-wrap:wrap; }
  .ai, .mip, .rt { background:#222a3a; color:var(--dim); border-radius:10px; padding:2px 9px; font-size:12px; white-space:nowrap; }
  .rt-ok { color:#7fd49a; } .rt-warn { color:#e8c050; } .rt-bad { color:#ff7b8a; font-weight:700; }
  .iid { color:var(--dim); font-size:11px; font-family:Consolas, monospace; }
  .desc { color:#c3c9d6; font-size:12.5px; }
  .verdicts { display:flex; gap:6px; flex-wrap:wrap; }
  .v { flex:1; min-width:70px; padding:7px 0; border-radius:7px; border:1px solid var(--line); background:#1c212d; color:var(--txt); cursor:pointer; font-size:13px; }
  .v:hover { border-color:var(--gold); }
  .v.active { background:var(--blue); border-color:var(--blue); font-weight:600; }
  .v.keep.active { background:var(--green); border-color:var(--green); }
  .v.remove { flex:0 0 auto; min-width:64px; opacity:.65; }
  .v.remove.active { background:var(--red); border-color:var(--red); opacity:1; }
  .raterow { display:flex; align-items:center; gap:10px; font-size:12px; color:var(--dim); }
  .raterow output { color:var(--gold); font-weight:600; width:26px; display:inline-block; }
  .rate { flex:1; accent-color:var(--gold); }
  .chips-title { color:var(--dim); font-size:10px; letter-spacing:.6px; }
  .chips { display:flex; flex-wrap:wrap; gap:5px; }
  .chip { background:#1c212d; border:1px solid var(--line); color:var(--dim); border-radius:12px; padding:3px 10px; font-size:11.5px; cursor:pointer; }
  .chip.on { background:#3a2f4a; border-color:#8a6dd0; color:#d9ccf5; }
  .notes { background:#11141b; border:1px solid var(--line); color:var(--txt); border-radius:7px; min-height:40px; padding:7px 9px; font:12.5px "Segoe UI", sans-serif; resize:vertical; }
  .cardsubmit { padding:9px; font-weight:800; border-radius:8px; border:none; cursor:pointer; background:var(--gold); color:#10131a; letter-spacing:.5px; }
  .cardsubmit:disabled { opacity:.35; cursor:default; }
  .bar { position:fixed; left:0; right:0; bottom:0; background:#10131add; backdrop-filter:blur(8px); border-top:1px solid var(--line); display:flex; align-items:center; gap:18px; padding:12px 26px; z-index:50; }
  .counts { display:flex; gap:14px; font-size:13px; color:var(--dim); flex-wrap:wrap; }
  .counts b { color:var(--txt); }
  #submitall { margin-left:auto; background:#1c212d; color:var(--txt); border:1px solid var(--line); font-weight:700; border-radius:8px; padding:11px 24px; font-size:13px; cursor:pointer; }
  #submitall:hover { border-color:var(--gold); }
  #submitall:disabled { opacity:.4; cursor:default; }
  #msg { font-size:12.5px; color:var(--green); }
  .done-banner { margin:60px auto; text-align:center; color:var(--dim); font-size:16px; display:none; }
</style></head>
<body>
<header>
  <h1>__TITLE__</h1>
  <div class="sub">__SUB__</div>
</header>
__CARDS__
<div class="done-banner" id="doneBanner">All items have verdicts — nothing left to rate. Tell Claude to “look through the __CAT__ audit.”</div>
<div class="bar">
  <div class="counts" id="counts"></div>
  <span id="msg"></span>
  <button id="submitall">Submit ALL decided</button>
</div>
<script>
(function () {
  var CAT = '__CAT__';
  // API origin resolution (2026-06-13 fix for "offline — saved locally only"):
  // when this page is opened over http(s) it talks to its own origin (the SPB
  // server that served it). When opened from disk via file:// (double-clicked
  // in Explorer) a root-relative fetch resolves to file:///api/... and ALWAYS
  // fails -> the old code showed "kept locally". We instead probe the known SPB
  // local ports so a double-clicked page still reaches the running app server.
  var API_PATH = '/api/june-audit/' + CAT;
  var SERVED = (location.protocol === 'http:' || location.protocol === 'https:');
  // Candidate origins to try, in order. Same-origin first when served; then the
  // default SPB ports (server_bootstrap: 59876 preferred, 59877 fallback).
  var ORIGINS = [];
  if (SERVED) ORIGINS.push('');                       // '' => same-origin relative
  ORIGINS.push('http://localhost:59876', 'http://localhost:59877',
               'http://127.0.0.1:59876', 'http://127.0.0.1:59877');
  var apiBase = ORIGINS[0];                            // resolved on first reachable GET
  function apiUrl(base) { return (base || '') + API_PATH; }
  var serverReachable = false;

  var LS = 'spb_audit___CAT___draft_v2';
  var draft = {};
  try { draft = JSON.parse(localStorage.getItem(LS) || '{}') || {}; } catch (e) { draft = {}; }
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card'));

  function entryOf(id) {
    if (!draft[id]) draft[id] = { verdict: null, rating: null, reasons: [], notes: '' };
    return draft[id];
  }
  function persist() { try { localStorage.setItem(LS, JSON.stringify(draft)); } catch (e) {} updateBar(); }
  function payload(card) {
    var id = card.getAttribute('data-id');
    var e = draft[id];
    if (!e || !e.verdict) return null;
    return { verdict: e.verdict, rating: e.rating || null,
             ai_rating: parseInt(card.getAttribute('data-ai'), 10) || null,
             reasons: e.reasons || [], notes: e.notes || '', ts: Date.now() };
  }
  function post(entries) {
    if (!serverReachable) {
      return Promise.reject(new Error(
        'audit server not reachable — open this page through the SPB app (it auto-starts the local server), then submit again'));
    }
    return fetch(apiUrl(apiBase), { method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ entries: entries }) })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
  }
  function fadeOut(id) {
    var card = document.querySelector('.card[data-id="' + id + '"]');
    if (card) { card.style.transition = 'opacity .5s'; card.style.opacity = '0';
      setTimeout(function () { card.style.display = 'none'; updateBar(); }, 520); }
    delete draft[id];
  }
  function flash(text, bad) {
    var el = document.getElementById('msg');
    el.style.color = bad ? '#c23b4a' : '#3dbb6e';
    el.textContent = text;
    setTimeout(function () { el.textContent = ''; }, 4000);
  }
  function updateBar() {
    var c = { keep: 0, replace: 0, rebuild: 0, rename: 0, remove: 0, undecided: 0 };
    var visible = cards.filter(function (k) { return k.style.display !== 'none'; });
    visible.forEach(function (k) {
      var e = draft[k.getAttribute('data-id')];
      if (e && e.verdict) c[e.verdict]++; else c.undecided++;
    });
    document.getElementById('counts').innerHTML =
      '<span>Keep <b>' + c.keep + '</b></span><span>Replace <b>' + c.replace + '</b></span>' +
      '<span>Rebuild <b>' + c.rebuild + '</b></span><span>Rename <b>' + c.rename + '</b></span>' +
      '<span>Remove <b>' + c.remove + '</b></span><span>· Undecided <b>' + c.undecided + '</b></span>';
    document.getElementById('submitall').disabled =
      (c.keep + c.replace + c.rebuild + c.rename + c.remove) === 0;
    ['spec_overlay', 'pattern', 'finish'].forEach(function (kind) {
      var el = document.querySelector('.seccount[data-kind="' + kind + '"]');
      if (!el) return;
      var n = visible.filter(function (k) { return k.getAttribute('data-kind') === kind; }).length;
      el.textContent = n ? '— ' + n + ' to rate' : '— done ✓';
    });
    if (!visible.length) document.getElementById('doneBanner').style.display = 'block';
  }

  cards.forEach(function (card) {
    var id = card.getAttribute('data-id');
    var e = entryOf(id);
    var submitBtn = card.querySelector('.cardsubmit');
    function refreshCard() {
      card.classList.toggle('decided', !!e.verdict);
      card.classList.toggle('rem', e.verdict === 'remove');
      submitBtn.disabled = !e.verdict;
    }
    var vbtns = card.querySelectorAll('.v');
    Array.prototype.forEach.call(vbtns, function (b) {
      if (e.verdict === b.getAttribute('data-v')) b.classList.add('active');
      b.addEventListener('click', function () {
        var on = b.classList.contains('active');
        Array.prototype.forEach.call(vbtns, function (x) { x.classList.remove('active'); });
        e.verdict = on ? null : b.getAttribute('data-v');
        if (!on) b.classList.add('active');
        refreshCard(); persist();
      });
    });
    var slider = card.querySelector('.rate'), out = card.querySelector('.raterow output');
    if (e.rating) { slider.value = e.rating; out.textContent = e.rating; }
    slider.addEventListener('input', function () { out.textContent = slider.value; e.rating = parseInt(slider.value, 10); persist(); });
    Array.prototype.forEach.call(card.querySelectorAll('.chip'), function (ch) {
      var tag = ch.getAttribute('data-chip');
      if (e.reasons && e.reasons.indexOf(tag) >= 0) ch.classList.add('on');
      ch.addEventListener('click', function () {
        ch.classList.toggle('on');
        e.reasons = e.reasons || [];
        var i = e.reasons.indexOf(tag);
        if (i >= 0) e.reasons.splice(i, 1); else e.reasons.push(tag);
        persist();
      });
    });
    var notes = card.querySelector('.notes');
    if (e.notes) notes.value = e.notes;
    notes.addEventListener('input', function () { e.notes = notes.value.slice(0, 4000); persist(); });
    submitBtn.addEventListener('click', function () {
      var p = payload(card);
      if (!p) return;
      submitBtn.disabled = true;
      var one = {}; one[id] = p;
      post(one).then(function () { fadeOut(id); persist(); flash('Saved ' + id + ' ✓'); })
        .catch(function (err) { submitBtn.disabled = false; flash('Save failed: ' + err.message + ' (kept locally)', true); });
    });
    refreshCard();
  });

  // Probe candidate origins in order; the first that answers the GET is the live
  // SPB server. Hides already-rated cards (read back from the server) and unlocks
  // submitting. If none answer, the page stays usable as a local draft and tells
  // the owner exactly how to make submits persist.
  function tryLoad(i) {
    if (i >= ORIGINS.length) { onNoServer(); return; }
    var base = ORIGINS[i];
    fetch(apiUrl(base), { method: 'GET' })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (data) {
        apiBase = base; serverReachable = true;
        var entries = (data && data.entries) || {};
        cards.forEach(function (card) {
          var id = card.getAttribute('data-id');
          if (entries[id] && entries[id].verdict) { card.style.display = 'none'; delete draft[id]; }
        });
        persist();
      })
      .catch(function () { tryLoad(i + 1); });
  }
  function onNoServer() {
    serverReachable = false;
    var el = document.getElementById('msg');
    if (el) { el.style.color = '#e8c050';
      el.textContent = 'Offline — verdicts are saved in this browser only. Open this page through the SPB app to save them to the audit file.'; }
    updateBar();
  }
  tryLoad(0);

  document.getElementById('submitall').addEventListener('click', function () {
    var entries = {};
    cards.forEach(function (card) {
      if (card.style.display === 'none') return;
      var p = payload(card);
      if (p) entries[card.getAttribute('data-id')] = p;
    });
    if (!Object.keys(entries).length) return;
    var btn = this; btn.disabled = true;
    post(entries).then(function () {
      Object.keys(entries).forEach(fadeOut); persist();
      flash(Object.keys(entries).length + ' verdict(s) saved ✓');
    }).catch(function (err) { flash('Save failed: ' + err.message + ' (kept locally)', true); })
      .then(function () { btn.disabled = false; updateBar(); });
  });
  updateBar();
})();
</script>
</body></html>'''
