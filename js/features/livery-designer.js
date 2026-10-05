/*
 * PROMPT-TO-LIVERY — MEGA FEATURE 1 (frontend panel)
 * --------------------------------------------------
 * A small "✨ Design It" panel: type a vibe ("menacing matte black with
 * toxic-green fracture and a carbon hood"), POST it to /api/design-from-prompt,
 * then show 1–3 complete looks as clickable OPTION CARDS (each with its own
 * palette + finishes). The first auto-applies so "it just works"; the painter
 * can flip between the alternates with one click — the viral "type a vibe ->
 * 3 stunning options -> click" flow.
 *
 * ADDITIVE + non-destructive: this file only RUNS when explicitly included from
 * paint-booth-v2.html. It mutates nothing on load. It builds its own panel and
 * applies zones through the app's existing in-scope path when that global
 * exists (window.spbApplyZones).
 *
 * Open the panel: via the EXPERIMENTAL FEATURES toolbar dropdown, or call
 * window.SPBLiveryDesigner.open() from the console / a menu item.
 */
(function () {
  'use strict';
  if (window.__SPB_LIVERY_DESIGNER_LOADED) return;
  window.__SPB_LIVERY_DESIGNER_LOADED = true;

  var PANEL_ID = 'spbLiveryDesignerPanel';

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === 'style') n.style.cssText = attrs[k];
      else if (k === 'text') n.textContent = attrs[k];
      else if (k === 'html') n.innerHTML = attrs[k];
      else if (k === 'class') n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }

  function toast(msg) {
    try { if (typeof window.showToast === 'function') { window.showToast(msg); return; } } catch (e) {}
    console.log('[LiveryDesigner]', msg);
  }

  function titleize(s) {
    s = String(s || '').replace(/[_-]+/g, ' ').trim();
    return s.replace(/\b\w/g, function (m) { return m.toUpperCase(); });
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  /* ---- Apply the returned zones through the app's canonical path. ----
   *
   * WHY THE OLD CODE DID NOTHING: the live editor keeps its zones in a
   * top-level `let zones` inside paint-booth-2-state-zones.js. A top-level
   * `let` is a LEXICAL binding, NOT a property of `window`, and it cannot be
   * reassigned from a separate <script> (this IIFE). The old path called a
   * nonexistent `window.setZones`, then "fell back" to creating a brand-new
   * `window.zones` array that NO renderer ever reads — so the real `zones`
   * binding was never replaced and renderZones() just repainted the unchanged
   * list. Result: "(N zones — applying…)" logged, editor frozen.
   *
   * THE FIX: go through the same in-scope entry point the recipe-restore path
   * uses. `window.spbApplyZones` (added in paint-booth-5-api-render.js, which
   * shares the bundle scope) runs `zones = _recipeSnapshotToZones(...);
   * selectedZoneIndex = 0; renderZones(); triggerPreviewRender(); autoSave();`
   * — the EXACT sequence of restoreRecipeFromRecent(). If that helper is
   * absent (older bundle), report failure honestly so the toast tells the
   * painter to update — far better than a silent half-apply.
   */
  function applyZones(zones) {
    if (!Array.isArray(zones) || !zones.length) return false;
    try {
      if (typeof window.spbApplyZones === 'function') {
        return window.spbApplyZones(zones) !== false;
      }
    } catch (e) { console.warn('[LiveryDesigner] spbApplyZones failed', e); }
    console.warn('[LiveryDesigner] window.spbApplyZones missing — cannot install zones in this build.');
    return false;
  }

  /* ---- Grab the LOADED paint so the server can map the design onto the car's
   * REAL regions (the make-or-break coverage fix). This MIRRORS Shokker-ize:
   * the live composite canvas (PSD composite / flat canvas / edited pixels) is
   * the SAME raster the renderer uses. We send it as a base64 PNG; the server
   * extracts the dominant colors and uses them as the zone selectors so the
   * design's finishes actually cover the car. Falls back to the on-disk paint
   * path, and finally to nothing (legacy palette-selector design). Returns a
   * Promise<object> of extra POST fields (possibly empty). NEVER rejects. */
  function currentPaintPath() {
    var elp = document.getElementById('paintFile');
    var v = (elp && elp.value ? elp.value : '').trim().replace(/^"+|"+$/g, '');
    return v;
  }
  function looksLikeDiskPath(p) {
    return !!p && (p.indexOf('/') !== -1 || p.indexOf('\\') !== -1 || /^[a-zA-Z]:/.test(p));
  }
  function liveCompositeCanvas() {
    try {
      if (typeof window.buildLivePaintCompositeCanvas === 'function') {
        var c = window.buildLivePaintCompositeCanvas();
        if (c && c.width > 0 && c.height > 0) return c;
      }
    } catch (e) {}
    var pc = document.getElementById('paintCanvas');
    if (pc && pc.width > 0 && pc.height > 0) return pc;
    return null;
  }
  function canvasToDataUri(canvas) {
    if (typeof window.canvasToBase64Async === 'function') {
      try { return window.canvasToBase64Async(canvas); } catch (e) {}
    }
    return new Promise(function (resolve) {
      try { resolve(canvas.toDataURL('image/png')); } catch (e) { resolve(null); }
    });
  }
  function loadedPaintBody() {
    var canvas = liveCompositeCanvas();
    if (canvas) {
      return Promise.resolve(canvasToDataUri(canvas)).then(function (dataUri) {
        if (dataUri) return { image: dataUri };
        var p = currentPaintPath();
        return looksLikeDiskPath(p) ? { paint_file: p } : {};
      }).catch(function () {
        var p = currentPaintPath();
        return looksLikeDiskPath(p) ? { paint_file: p } : {};
      });
    }
    var path = currentPaintPath();
    return Promise.resolve(looksLikeDiskPath(path) ? { paint_file: path } : {});
  }

  /* ---- Turn the API payload into 1–3 complete LOOK options. ----
   * Option 0 is the primary design (data.zones + meta.theme/palette/mood).
   * Options 1–2 are the engine's variations (meta.variations[] — each a full
   * alternate design with its own zones + palette). Backward compatible: if the
   * engine/route predates variations, we still show the single primary look. */
  function optionsFromData(data) {
    var meta = data.meta || {};
    var opts = [];
    opts.push({
      name: meta.theme || data.prompt || 'Design',
      palette: meta.palette || [],
      zones: data.zones || [],
      zone_count: data.zone_count || (data.zones || []).length,
      mood: meta.mood || '',
      explanation: data.explanation || '',
      primary: true
    });
    (meta.variations || []).forEach(function (v) {
      if (!v || !Array.isArray(v.zones) || !v.zones.length) return;
      opts.push({
        name: v.name || 'Alternate',
        palette: v.palette || [],
        zones: v.zones,
        zone_count: v.zones.length,
        mood: v.mood || '',
        explanation: v.explanation || '',
        primary: false
      });
    });
    return opts;
  }

  function selectOption(opt, card, cards) {
    var ok = applyZones(opt.zones);
    cards.forEach(function (c) {
      var sel = c.card === card;
      c.card.classList.toggle('spb-ld-opt--sel', sel);
      c.btn.textContent = sel ? (ok ? 'Applied ✓' : 'Apply') : 'Apply';
    });
    toast(ok ? (titleize(opt.name) + ' applied — ' + opt.zone_count + ' zones')
             : 'Generated (see console) — auto-apply path not found in this build');
  }

  function renderOptions(data) {
    var out = document.getElementById('spbLDOutput');
    if (!out) return;
    var opts = optionsFromData(data);
    out.innerHTML = '';
    if (!opts.length) { out.textContent = 'No design produced.'; return; }

    out.appendChild(el('div', { class: 'spb-ld-hdr',
      text: opts.length > 1 ? ('Pick a look — ' + opts.length + ' options:') : 'Your look:' }));

    var cards = [];
    opts.forEach(function (opt, i) {
      var card = el('div', { class: 'spb-ld-opt' + (opt.primary ? ' spb-ld-opt--primary' : '') });
      var sw = el('div', { class: 'spb-ld-sw' });
      (opt.palette || []).slice(0, 6).forEach(function (hex) {
        sw.appendChild(el('span', { class: 'spb-ld-chip', style: 'background:' + hex }));
      });
      var lab = el('div', { class: 'spb-ld-lab' }, [
        el('div', { class: 'spb-ld-name', text: titleize(opt.name) + (opt.primary ? '  ★' : '') }),
        el('div', { class: 'spb-ld-meta',
          text: opt.zone_count + ' zones' + (opt.mood ? ' · ' + opt.mood : '') })
      ]);
      var applyBtn = el('button', { class: 'spb-ld-apply', text: 'Apply' });
      card.appendChild(sw); card.appendChild(lab); card.appendChild(applyBtn);
      card.addEventListener('click', function () { selectOption(opt, card, cards); });
      out.appendChild(card);
      cards.push({ card: card, btn: applyBtn, opt: opt });
    });

    // Auto-apply the first (primary) so "load car -> click -> beautiful" just works,
    // and mark it as the selected card. The painter flips looks with one click.
    selectOption(opts[0], cards[0].card, cards);
  }

  function design() {
    var input = document.getElementById('spbLDPrompt');
    var out = document.getElementById('spbLDOutput');
    var btn = document.getElementById('spbLDGo');
    var prompt = (input && input.value || '').trim();
    if (!prompt) { toast('Type a vibe first.'); return; }
    if (btn) { btn.disabled = true; btn.textContent = 'Designing…'; }
    if (out) out.innerHTML = '<div class="spb-ld-loading">Designing looks…</div>';
    loadedPaintBody().then(function (paintFields) {
      var body = { prompt: prompt };
      if (paintFields) Object.keys(paintFields).forEach(function (k) { body[k] = paintFields[k]; });
      return fetch('/api/design-from-prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (btn) { btn.disabled = false; btn.textContent = '✨ Design It'; }
        if (!data || !data.ok) {
          var err = (data && data.error) || 'Design failed';
          if (out) out.innerHTML = '<div class="spb-ld-err">⚠ ' + escapeHtml(err) + '</div>';
          toast('Design failed: ' + err);
          return;
        }
        console.log('[LiveryDesigner] zones:', data.zones, 'meta:', data.meta);
        renderOptions(data);
      }).catch(function (e) {
        if (btn) { btn.disabled = false; btn.textContent = '✨ Design It'; }
        if (out) out.innerHTML = '<div class="spb-ld-err">⚠ ' + escapeHtml('' + e) + '</div>';
        toast('Design request error: ' + e);
      });
    });
  }

  function ensureStyles() {
    if (document.getElementById('spbLDStyles')) return;
    var css = '' +
      '#spbLiveryDesignerPanel .spb-ld-hdr{font-size:12px;color:#9aa3b2;margin:10px 0 7px;font-weight:600;}' +
      '#spbLiveryDesignerPanel .spb-ld-opt{display:flex;align-items:center;gap:10px;padding:8px;' +
        'border:1px solid #23262e;border-radius:10px;background:#0e1014;margin-bottom:7px;cursor:pointer;' +
        'transition:border-color .15s,transform .12s,box-shadow .15s;}' +
      '#spbLiveryDesignerPanel .spb-ld-opt:hover{border-color:#3a3f4d;transform:translateY(-1px);}' +
      '#spbLiveryDesignerPanel .spb-ld-opt--sel{border-color:#8a5cff;' +
        'box-shadow:0 0 0 1px rgba(138,92,255,.33),0 6px 18px rgba(124,76,255,.18);}' +
      '#spbLiveryDesignerPanel .spb-ld-sw{display:flex;gap:0;border-radius:6px;overflow:hidden;flex:0 0 auto;' +
        'box-shadow:inset 0 0 0 1px rgba(255,255,255,.06);}' +
      '#spbLiveryDesignerPanel .spb-ld-chip{width:16px;height:30px;display:block;}' +
      '#spbLiveryDesignerPanel .spb-ld-lab{flex:1 1 auto;min-width:0;}' +
      '#spbLiveryDesignerPanel .spb-ld-name{font-weight:700;font-size:13px;color:#eef0f5;' +
        'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}' +
      '#spbLiveryDesignerPanel .spb-ld-meta{font-size:11px;color:#8b93a3;margin-top:1px;}' +
      '#spbLiveryDesignerPanel .spb-ld-apply{flex:0 0 auto;border:none;border-radius:7px;padding:6px 11px;' +
        'font-size:11px;font-weight:700;cursor:pointer;background:#21242e;color:#cdd3df;}' +
      '#spbLiveryDesignerPanel .spb-ld-opt--sel .spb-ld-apply{background:linear-gradient(90deg,#6c4cff,#b14bff);color:#fff;}' +
      '#spbLiveryDesignerPanel .spb-ld-loading,#spbLiveryDesignerPanel .spb-ld-err{color:#b8c0cc;font-size:12px;padding:6px 2px;}' +
      '#spbLiveryDesignerPanel .spb-ld-err{color:#ff9b9b;}';
    var st = el('style', { id: 'spbLDStyles' });
    st.textContent = css;
    document.head.appendChild(st);
  }

  function buildPanel() {
    if (document.getElementById(PANEL_ID)) return document.getElementById(PANEL_ID);
    ensureStyles();
    var panel = el('div', {
      id: PANEL_ID,
      style: 'position:fixed;right:18px;bottom:74px;width:340px;z-index:99999;' +
             'background:#15171c;color:#e8e8ec;border:1px solid #2c2f38;border-radius:12px;' +
             'box-shadow:0 10px 40px rgba(0,0,0,.55);padding:14px;font:13px/1.4 system-ui,Segoe UI,sans-serif;display:none;'
    });
    var head = el('div', { style: 'display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;' }, [
      el('div', { text: '✨ Prompt-to-Livery', style: 'font-weight:700;font-size:14px;' }),
      el('button', { id: 'spbLDClose', title: 'Close', text: '✕',
        style: 'background:none;border:none;color:#9aa;cursor:pointer;font-size:16px;' })
    ]);
    var ta = el('textarea', {
      id: 'spbLDPrompt', rows: '3',
      placeholder: 'e.g. menacing matte black with toxic-green fracture and a carbon hood',
      style: 'width:100%;box-sizing:border-box;background:#0e1014;color:#e8e8ec;border:1px solid #2c2f38;' +
             'border-radius:8px;padding:8px;resize:vertical;font:13px/1.4 inherit;'
    });
    var go = el('button', { id: 'spbLDGo', text: '✨ Design It',
      style: 'margin-top:8px;width:100%;padding:9px;border:none;border-radius:8px;cursor:pointer;' +
             'background:linear-gradient(90deg,#6c4cff,#b14bff);color:#fff;font-weight:700;font-size:13px;' });
    var out = el('div', { id: 'spbLDOutput',
      style: 'margin-top:10px;max-height:300px;overflow:auto;font-size:12px;min-height:18px;' });
    panel.appendChild(head); panel.appendChild(ta); panel.appendChild(go); panel.appendChild(out);
    document.body.appendChild(panel);

    go.addEventListener('click', design);
    ta.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); design(); }
    });
    document.getElementById('spbLDClose').addEventListener('click', function () { panel.style.display = 'none'; });
    return panel;
  }

  function open() {
    var p = buildPanel();
    p.style.display = 'block';
    var ta = document.getElementById('spbLDPrompt');
    if (ta) ta.focus();
  }
  function close() { var p = document.getElementById(PANEL_ID); if (p) p.style.display = 'none'; }
  function toggle() { var p = document.getElementById(PANEL_ID); if (p && p.style.display === 'block') close(); else open(); }

  // NOTE (2026-06-13): the floating bottom-right "✨ Design It" FAB has been
  // removed. The launchers live in the EXPERIMENTAL FEATURES toolbar dropdown,
  // so this module no longer self-injects a fixed-position button on load.
  // Open the panel via the public API instead:
  //   window.SPBLiveryDesigner.open()  /  .toggle()  /  .close()
  // The panel itself is still built lazily on first open() — nothing is
  // injected into the page until the user (or the toolbar item) asks for it.

  window.SPBLiveryDesigner = { open: open, close: close, toggle: toggle, design: design, applyZones: applyZones };
})();
