/*
 * PHOTO-TO-LIVERY — bonus MEGA FEATURE (frontend panel)
 * -----------------------------------------------------
 * A small "📷 Photo → Livery" panel: pick ANY reference image (a sunset photo, a
 * real race car, an album cover), POST it to /api/design-from-image, preview the
 * extracted palette, then APPLY the returned multi-zone config to the live editor.
 *
 * ADDITIVE + non-destructive: this file only RUNS when explicitly included from
 * paint-booth-v2.html. It mutates nothing on load. It floats its own button +
 * panel, applies zones through the app's existing setZones/renderZones path when
 * those globals exist (falling back to window.zones + renderZones()), and no-ops
 * gracefully if anything it needs is absent.
 *
 * Open the panel: click the floating "📷 Photo → Livery" button (bottom-right,
 * just above the ✨ Design It button), or call window.SPBPhotoLivery.open() from
 * the console / a menu item.
 */
(function () {
  'use strict';
  if (window.__SPB_PHOTO_LIVERY_LOADED) return;
  window.__SPB_PHOTO_LIVERY_LOADED = true;

  var PANEL_ID = 'spbPhotoLiveryPanel';
  var _lastFile = null;

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === 'style') n.style.cssText = attrs[k];
      else if (k === 'text') n.textContent = attrs[k];
      else if (k === 'html') n.innerHTML = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }

  function toast(msg) {
    try { if (typeof window.showToast === 'function') { window.showToast(msg); return; } } catch (e) {}
    console.log('[PhotoLivery]', msg);
  }

  /* ---- Apply the returned zones through the app's canonical path. ----
   *
   * Photo→Livery delegates to the Prompt-to-Livery applier so there is ONE
   * zone-install code path (see js/features/livery-designer.js for the full
   * root-cause writeup). The canonical installer is window.spbApplyZones
   * (added in paint-booth-5-api-render.js, in-bundle-scope), which is the only
   * thing that can actually replace the editor's lexical `let zones` binding.
   */
  function applyZones(zones) {
    // Single source of truth: reuse the Prompt-to-Livery applier when present.
    try {
      if (window.SPBLiveryDesigner && typeof window.SPBLiveryDesigner.applyZones === 'function') {
        return window.SPBLiveryDesigner.applyZones(zones) !== false;
      }
    } catch (e) { console.warn('[PhotoLivery] delegate to SPBLiveryDesigner failed', e); }

    if (!Array.isArray(zones) || !zones.length) return false;

    // Direct canonical path if the designer module wasn't loaded.
    try {
      if (typeof window.spbApplyZones === 'function') {
        return window.spbApplyZones(zones) !== false;
      }
    } catch (e) { console.warn('[PhotoLivery] spbApplyZones failed', e); }

    // Older bundle without the canonical installer: do NOT mutate state (the
    // editor's `zones` is a lexical `let` we can't reassign from here, and
    // appending blank zones via window.addZone would corrupt the editor).
    console.warn('[PhotoLivery] window.spbApplyZones missing — cannot install zones in this build.');
    return false;
  }

  function renderPalette(palette) {
    var box = document.getElementById('spbPLPalette');
    if (!box) return;
    box.innerHTML = '';
    // Role badge so the "it understood my photo" intelligence is visible: which
    // extracted color became the body vs the hero feature vs the accent.
    var roleGlyph = { body: '●', feature: '◆', accent: '▲' };
    (palette || []).forEach(function (p) {
      var pct = Math.round((p.weight || 0) * 100);
      var role = p.role || '';
      var sw = el('div', {
        title: (p.name || '') + '  ' + p.hex + '  (' + pct + '%' +
               (role ? '  · ' + role : '') + ')',
        style: 'position:relative;flex:' + Math.max(1, pct) +
               ';height:30px;background:' + p.hex + ';border-radius:5px;min-width:16px;' +
               (role ? 'box-shadow:0 0 0 2px rgba(255,255,255,.25) inset;' : '')
      });
      if (role && roleGlyph[role]) {
        // contrast glyph against the swatch
        var hex = (p.hex || '#888').replace('#', '');
        var lum = (parseInt(hex.substr(0, 2), 16) * 0.299 +
                   parseInt(hex.substr(2, 2), 16) * 0.587 +
                   parseInt(hex.substr(4, 2), 16) * 0.114);
        sw.appendChild(el('span', {
          text: roleGlyph[role],
          style: 'position:absolute;left:0;right:0;top:50%;transform:translateY(-50%);' +
                 'text-align:center;font-size:11px;line-height:1;' +
                 'color:' + (lum > 140 ? 'rgba(0,0,0,.55)' : 'rgba(255,255,255,.7)') + ';'
        }));
      }
      box.appendChild(sw);
    });
  }

  /* Show the matched art direction (theme) + mood so the user SEES the engine
   * reasoning about their photo — the viral "it gets it" moment. */
  function renderVibe(data) {
    var box = document.getElementById('spbPLVibe');
    if (!box) return;
    var meta = data.meta || {};
    var theme = meta.theme || '';
    var mood = (meta.mood_words || []).slice(0, 4).join(' · ');
    if (!theme && !mood) { box.style.display = 'none'; return; }
    box.style.display = 'block';
    box.innerHTML = '';
    if (theme) {
      box.appendChild(el('div', {
        html: 'Art direction: <b style="color:#54e8cf">' + theme + '</b>' +
              (meta.theme_mood ? ' <span style="color:#7e8794">— ' + meta.theme_mood + '</span>' : ''),
        style: 'font-size:12px;margin-bottom:2px;'
      }));
    }
    if (mood) {
      box.appendChild(el('div', {
        text: 'Mood read: ' + mood,
        style: 'font-size:11px;color:#9aa3b0;'
      }));
    }
  }

  function summarize(data) {
    var lines = [];
    (data.zones || []).forEach(function (z) {
      var fin = z.finish || z.base;
      if (!fin) return;
      var col = Array.isArray(z.color) && z.color[0] ? z.color[0].hex
              : (typeof z.color === 'string' ? z.color : '');
      lines.push('• ' + z.name + ' → ' + fin + (col ? '  ' + col : ''));
    });
    return lines.join('\n');
  }

  /* ---- The LOADED car paint (so the server maps the photo's finishes onto the
   * car's REAL regions = full coverage). MIRRORS Shokker-ize / Prompt-to-Livery:
   * the live composite canvas is the same raster the renderer uses. Returns a
   * Promise<{paint_image|paint_file}|null>; NEVER rejects. */
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
  function loadedCarPaint() {
    var canvas = liveCompositeCanvas();
    if (canvas) {
      return Promise.resolve(canvasToDataUri(canvas)).then(function (dataUri) {
        if (dataUri) return { paint_image: dataUri };
        var p = currentPaintPath();
        return looksLikeDiskPath(p) ? { paint_file: p } : null;
      }).catch(function () {
        var p = currentPaintPath();
        return looksLikeDiskPath(p) ? { paint_file: p } : null;
      });
    }
    var path = currentPaintPath();
    return Promise.resolve(looksLikeDiskPath(path) ? { paint_file: path } : null);
  }

  function postFile(file) {
    var out = document.getElementById('spbPLOutput');
    var btn = document.getElementById('spbPLGo');
    if (!file) { toast('Pick an image first.'); return; }
    if (btn) { btn.disabled = true; btn.textContent = 'Analyzing…'; }
    if (out) out.textContent = 'Analyzing image…';

    loadedCarPaint().then(function (carFields) {
      var fd = new FormData();
      fd.append('image', file, file.name || 'image.png');
      fd.append('seed', '51');
      if (carFields) {
        // The loaded car paint -> server extracts its dominant colors so the
        // photo's finishes cover the car's real regions.
        if (carFields.paint_image) fd.append('paint_image', carFields.paint_image);
        if (carFields.paint_file) fd.append('paint_file', carFields.paint_file);
      }
      return fetch('/api/design-from-image', { method: 'POST', body: fd })
        .then(function (r) { return r.json(); })
        .then(function (data) { handleResult(data, out, btn); });
    }).catch(function (e) {
      if (btn) { btn.disabled = false; btn.textContent = '📷 Build Livery'; }
      if (out) out.textContent = '⚠ ' + e;
      toast('Photo request error: ' + e);
    });
  }

  function handleResult(data, out, btn) {
    if (btn) { btn.disabled = false; btn.textContent = '📷 Build Livery'; }
    if (!data || !data.ok) {
      var err = (data && data.error) || 'Design failed';
      if (out) out.textContent = '⚠ ' + err;
      toast('Photo → Livery failed: ' + err);
      return;
    }
    console.log('[PhotoLivery] palette:', data.palette, 'zones:', data.zones, 'meta:', data.meta);
    renderVibe(data);
    renderPalette(data.palette);
    if (out) {
      out.textContent = (data.explanation || '') + '\n\n' + summarize(data) +
        '\n\n(' + (data.zone_count || 0) + ' zones — applying…)';
    }
    var ok = applyZones(data.zones);
    toast(ok ? ('Livery applied: ' + (data.zone_count || 0) + ' zones')
             : 'Zones generated (see console) — auto-apply path not found in this build');
  }

  function onPick(ev) {
    var f = ev.target && ev.target.files && ev.target.files[0];
    if (!f) return;
    _lastFile = f;
    var nm = document.getElementById('spbPLFileName');
    if (nm) nm.textContent = f.name;
    // Preview thumbnail.
    try {
      var img = document.getElementById('spbPLThumb');
      if (img) { img.src = URL.createObjectURL(f); img.style.display = 'block'; }
    } catch (e) {}
  }

  function buildPanel() {
    if (document.getElementById(PANEL_ID)) return document.getElementById(PANEL_ID);
    var panel = el('div', {
      id: PANEL_ID,
      style: 'position:fixed;right:18px;bottom:128px;width:340px;z-index:99999;' +
             'background:#15171c;color:#e8e8ec;border:1px solid #2c2f38;border-radius:12px;' +
             'box-shadow:0 10px 40px rgba(0,0,0,.55);padding:14px;font:13px/1.4 system-ui,Segoe UI,sans-serif;display:none;'
    });
    var head = el('div', { style: 'display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;' }, [
      el('div', { text: '📷 Photo → Livery', style: 'font-weight:700;font-size:14px;' }),
      el('button', { id: 'spbPLClose', title: 'Close', text: '✕',
        style: 'background:none;border:none;color:#9aa;cursor:pointer;font-size:16px;' })
    ]);

    var fileInput = el('input', { id: 'spbPLFile', type: 'file', accept: 'image/*', style: 'display:none;' });
    var pickBtn = el('button', { id: 'spbPLPick', text: 'Choose image…',
      style: 'width:100%;padding:9px;border:1px dashed #3a3f4a;border-radius:8px;cursor:pointer;' +
             'background:#0e1014;color:#cdd3dc;font-weight:600;font-size:13px;' });
    var fname = el('div', { id: 'spbPLFileName', text: 'No image selected',
      style: 'margin-top:6px;color:#7e8794;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;' });
    var thumb = el('img', { id: 'spbPLThumb',
      style: 'display:none;margin-top:8px;max-width:100%;max-height:120px;border-radius:8px;border:1px solid #23262e;' });
    var vibe = el('div', { id: 'spbPLVibe',
      style: 'display:none;margin-top:9px;padding:8px 10px;border-radius:8px;' +
             'background:#10141a;border:1px solid #23303a;' });
    var palette = el('div', { id: 'spbPLPalette',
      style: 'display:flex;gap:3px;margin-top:8px;min-height:6px;' });
    var go = el('button', { id: 'spbPLGo', text: '📷 Build Livery',
      style: 'margin-top:10px;width:100%;padding:9px;border:none;border-radius:8px;cursor:pointer;' +
             'background:linear-gradient(90deg,#0f9b8e,#1ec8b0);color:#04201c;font-weight:800;font-size:13px;' });
    var out = el('pre', { id: 'spbPLOutput',
      style: 'margin-top:10px;white-space:pre-wrap;max-height:200px;overflow:auto;background:#0e1014;' +
             'border:1px solid #23262e;border-radius:8px;padding:8px;color:#b8c0cc;font-size:12px;min-height:18px;' });

    panel.appendChild(head);
    panel.appendChild(fileInput);
    panel.appendChild(pickBtn);
    panel.appendChild(fname);
    panel.appendChild(thumb);
    panel.appendChild(vibe);
    panel.appendChild(palette);
    panel.appendChild(go);
    panel.appendChild(out);
    document.body.appendChild(panel);

    pickBtn.addEventListener('click', function () { fileInput.click(); });
    fileInput.addEventListener('change', onPick);
    go.addEventListener('click', function () { postFile(_lastFile); });
    document.getElementById('spbPLClose').addEventListener('click', function () { panel.style.display = 'none'; });
    return panel;
  }

  function open() {
    var p = buildPanel();
    p.style.display = 'block';
  }
  function close() { var p = document.getElementById(PANEL_ID); if (p) p.style.display = 'none'; }
  function toggle() { var p = document.getElementById(PANEL_ID); if (p && p.style.display === 'block') close(); else open(); }

  // NOTE (2026-06-13): the floating bottom-right "📷 Photo → Livery" FAB has
  // been removed. The owner is moving these MEGA-FEATURE launchers into a
  // toolbar dropdown, so this module no longer self-injects a fixed-position
  // button on load. Open the panel via the public API instead:
  //   window.SPBPhotoLivery.open()  /  .toggle()  /  .close()
  // The panel is still built lazily on first open(); nothing is injected into
  // the page until the user (or the toolbar item) asks for it.

  window.SPBPhotoLivery = { open: open, close: close, toggle: toggle, applyZones: applyZones };
})();
