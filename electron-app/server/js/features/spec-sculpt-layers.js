/* ============================================================================
 * SPEC SCULPT — Auto-build layers + CAR DETECTION showcase (2026-06-27)
 * ---------------------------------------------------------------------------
 * Owner ask: the 4-LAYER auto-build + car detection that lives in the regular
 * app's right-side Layers column (js/features/smart-separate.js → S.layers)
 * should ALSO be on the Spec Sculpt page. Here it's a SHOWCASE: detect which
 * iRacing car the loaded livery is, then preview the numbers / sponsors /
 * template / paint split — no zone-creation required on this page.
 *
 * Self-contained IIFE, NO page-wide MutationObserver. Renders into a card
 * (#ssLayersCard) that is injected once after the Auto-Separate card. Pulls the
 * currently-loaded source paint straight off Spec Sculpt's own #imgPaintSrc
 * preview (the server already decodes TGA → a browser-decodable JPEG into it),
 * with the in-memory File (window.SpecSculptState?.file) as a fallback. POSTs a
 * PNG blob to /api/auto-layers (multipart, no internal-request gating). If that
 * route 404s the whole card hides itself — graceful degrade.
 * ========================================================================== */
(function () {
  'use strict';
  if (window.SpecSculptLayers && window.SpecSculptLayers.__installed) return;

  var SL = window.SpecSculptLayers = window.SpecSculptLayers || {};
  SL.__installed = true;
  SL.busy = false;
  SL.result = null;
  SL.status = '';
  SL.available = null;      // null=unknown, true/false once probed
  var _gen = 0;             // drop stale responses

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]; }); }
  function pct(x) { return Math.round((Number(x) || 0) * 100); }
  function $(id) { return document.getElementById(id); }

  // ---- where to mount: after the Auto-Separate card, else after the source-paint card ----
  function _host() {
    var card = $('ssLayersCard');
    if (card) return card;
    card = document.createElement('div');
    card.className = 'card';
    card.id = 'ssLayersCard';
    card.style.display = 'none';   // shown once we confirm the route exists
    var anchor = $('autoSepCard') || $('paintPreviewCard');
    if (anchor && anchor.parentNode) {
      anchor.parentNode.insertBefore(card, anchor.nextSibling);
    } else {
      (document.querySelector('main') || document.body).appendChild(card);
    }
    return card;
  }

  // ---- grab the loaded source paint as a PNG blob ----------------------------
  // Spec Sculpt's #imgPaintSrc is the single source of truth the engine samples:
  // a blob/object-URL for browser-decodable uploads, OR the server-decoded JPEG
  // data-URL for TGA paths. Drawing it to a canvas normalizes all of those to a
  // clean PNG blob. Same-origin / data / blob URLs => canvas is NOT tainted.
  function sourceBlob() {
    return new Promise(function (resolve, reject) {
      var img = $('imgPaintSrc');
      if (img && img.getAttribute('src') && img.complete && img.naturalWidth) {
        try {
          var c = document.createElement('canvas');
          c.width = img.naturalWidth; c.height = img.naturalHeight;
          c.getContext('2d').drawImage(img, 0, 0);
          c.toBlob(function (b) {
            if (b) { resolve(b); return; }
            _fallbackFile(resolve, reject);
          }, 'image/png');
          return;
        } catch (e) { /* tainted / read failure — fall through to the File */ }
      }
      _fallbackFile(resolve, reject);
    });
  }
  function _fallbackFile(resolve, reject) {
    // Spec Sculpt keeps the raw uploaded File around; use it directly (the server
    // route decodes TGA itself). Look it up defensively across the names it may use.
    var f = null;
    try {
      var st = window.SpecSculptState || window.state || null;
      if (st && st.file) f = st.file;
    } catch (e) {}
    if (!f) {
      try {
        var fi = $('fileInput');
        if (fi && fi.files && fi.files[0]) f = fi.files[0];
      } catch (e) {}
    }
    if (f) { resolve(f); return; }
    reject(new Error('Load a source paint first.'));
  }

  // ---- one-time probe so a missing route hides the card instead of erroring ---
  SL.probe = function probe() {
    if (SL.available !== null) { SL.render(); return; }
    // HEAD/OPTIONS-style cheap probe: a tiny GET. The route is POST-only, so a 405
    // means "exists"; 404 means "missing". Either way no OCR runs.
    fetch('/api/auto-layers', { method: 'GET' }).then(function (r) {
      SL.available = (r.status !== 404);
    }).catch(function () {
      // network error — assume present (Electron localhost); the run will surface real failures
      SL.available = true;
    }).then(function () { SL.render(); });
  };

  // ---- run the detection + 4-layer split ------------------------------------
  SL.run = function run() {
    if (SL.busy) return;
    var myGen = ++_gen;
    SL.busy = true; SL.status = 'Reading livery… (~15s)'; SL.result = null; SL.render();
    sourceBlob().then(function (blob) {
      var fd = new FormData();
      var nm = (blob && blob.name) || 'livery.png';
      fd.append('image', blob, nm);
      fd.append('preview_size', '1024');
      return fetch('/api/auto-layers', { method: 'POST', body: fd });
    }).then(function (r) {
      if (r.status === 404) { SL.available = false; throw new Error('route unavailable'); }
      return r.json();
    }).then(function (j) {
      if (myGen !== _gen) return;
      SL.busy = false;
      if (!j || !j.success) { SL.result = null; SL.status = 'Failed: ' + ((j && j.error) || 'unknown'); SL.render(); return; }
      SL.result = j; SL.status = '';
      SL.render();
    }).catch(function (e) {
      if (myGen !== _gen) return;
      SL.busy = false; SL.result = null;
      SL.status = (SL.available === false) ? '' : ('Failed: ' + (e.message || e));
      SL.render();
    });
  };

  // ---- render the showcase card ----------------------------------------------
  SL.render = function render() {
    var card = _host();
    if (SL.available === false) { card.style.display = 'none'; return; }
    card.style.display = 'block';

    var line = 'var(--line,#2b3645)';
    var muted = 'var(--muted,#9ba8b8)';
    var good = 'var(--good,#78e39b)';
    var danger = 'var(--danger,#ff5967)';

    var h = '';
    h += '<h3 style="margin-top:0;">🧩 Auto-build layers — detect car';
    h += '<span class="hint" id="ssLayersStatus" style="margin-left:auto;font-weight:400;">' +
         (SL.status ? '<span style="color:' + (SL.status.indexOf('Failed') === 0 ? danger : muted) + ';">' + esc(SL.status) + '</span>' : '') +
         '</span></h3>';
    h += '<p class="hint">Reads the loaded livery, identifies <strong>which iRacing car</strong> it is, ' +
         'and previews the split into <span style="color:#ff8a8a;">numbers</span>, ' +
         '<span style="color:#8ab8ff;">sponsors</span>, <span style="color:#9affb0;">template</span> &amp; ' +
         '<span style="color:var(--text,#eaf0f8);">base paint</span>. <em>(Flat images only — ~15s, OCR reads the numbers.)</em></p>';

    h += '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px;">' +
         '<button type="button" class="btn primary" id="ssLayersRun" style="min-height:38px;"' + (SL.busy ? ' disabled' : '') + '>' +
         (SL.busy ? '⏳ Reading livery…' : '🧩 Auto-build layers (detect car)') + '</button></div>';

    var r = SL.result;
    if (r && r.success) {
      // --- detected car badge ---
      var car = (r.car && r.car[0]) || null;
      if (car) {
        var label = car.family || car.slug || '?';
        h += '<div style="margin:2px 0 10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">' +
             '<span style="font-size:12px;color:' + good + ';font-weight:800;">Detected car: ' + esc(label) + '</span>' +
             '<span class="pill ok" style="font-size:10px;">score ' + esc(String(car.score)) + '</span>' +
             '</div>';
        // runner-up matches, if any
        if (r.car && r.car.length > 1) {
          var rest = r.car.slice(1, 3).map(function (c) { return esc(c.family || c.slug || '?') + ' (' + esc(String(c.score)) + ')'; }).join(' · ');
          if (rest) h += '<p class="hint" style="margin:-6px 0 10px;">also like: ' + rest + '</p>';
        }
      }

      // --- 4 fraction chips ---
      var f = r.fractions || {};
      h += '<div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px;">' +
           '<span style="background:rgba(255,90,90,0.14);color:#ff8a8a;border:1px solid rgba(255,90,90,0.35);border-radius:999px;padding:3px 10px;font-size:11px;">Numbers ' + pct(f.numbers) + '%</span>' +
           '<span style="background:rgba(90,140,255,0.14);color:#8ab8ff;border:1px solid rgba(90,140,255,0.35);border-radius:999px;padding:3px 10px;font-size:11px;">Sponsors ' + pct(f.sponsors) + '%</span>' +
           '<span style="background:rgba(90,255,150,0.12);color:#9affb0;border:1px solid rgba(90,255,150,0.30);border-radius:999px;padding:3px 10px;font-size:11px;">Template ' + pct(f.template) + '%</span>' +
           ((f.brand_graphics > 0) ? '<span style="background:rgba(255,160,30,0.14);color:#ffb14d;border:1px solid rgba(255,160,30,0.35);border-radius:999px;padding:3px 10px;font-size:11px;">Brand graphics ' + pct(f.brand_graphics) + '%</span>' : '') +
           '<span style="background:rgba(255,255,255,0.06);color:var(--text,#eaf0f8);border:1px solid ' + line + ';border-radius:999px;padding:3px 10px;font-size:11px;">Paint ' + pct(f.paint) + '%</span>' +
           '</div>';

      // --- overlay showcase image (numbers=red, sponsors=blue, template=green) ---
      if (r.overlay) {
        h += '<img src="' + r.overlay + '" alt="detected layer overlay" ' +
             'style="display:block;width:100%;max-width:480px;border-radius:8px;border:1px solid ' + line + ';">';
      }

      // --- optional per-layer mask thumbs (the route returns them) ---
      if (r.layers) {
        h += '<div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;">';
        [['numbers', 'Numbers', '#ff8a8a'], ['sponsors', 'Sponsors', '#8ab8ff'], ['template', 'Template', '#9affb0'],
         (f.brand_graphics > 0 ? ['brand_graphics', 'Brand graphics', '#ffb14d'] : null), ['paint', 'Paint', '#cfd6e6']].filter(Boolean).forEach(function (m) {
          if (!r.layers[m[0]]) return;
          h += '<div style="text-align:center;flex:0 0 auto;">' +
               '<div class="hint" style="color:' + m[2] + ';margin:0 0 3px;">' + m[1] + '</div>' +
               '<img src="' + r.layers[m[0]] + '" alt="" style="width:104px;border-radius:6px;border:1px solid ' + line + ';background:#05070a;display:block;"></div>';
        });
        h += '</div>';
      }

      // brand-graphics 3-way merge toggle (owner 2026-06-27)
      if (f.brand_graphics > 0) {
        var bm = SL.brandMerge || 'separate';
        var bb = function (v, lbl, id) {
          var on = (bm === v);
          return '<button type="button" id="' + id + '" style="cursor:pointer;flex:1;border:1px solid ' + (on ? '#ffb14d' : line) + ';background:' + (on ? 'rgba(255,160,30,0.14)' : 'transparent') + ';color:' + (on ? '#ffb14d' : 'var(--dim,#9aa6b8)') + ';border-radius:6px;padding:6px 0;font-size:11px;font-weight:600;">' + lbl + '</button>';
        };
        h += '<div class="hint" style="margin-top:10px;">Brand graphics (m&amp;m, Monster, Bass Pro…):</div>' +
             '<div style="margin-top:4px;display:flex;gap:6px;">' + bb('separate', 'Own layer', 'ssBrandSep') + bb('paint', 'Into paint', 'ssBrandPaint') + bb('sponsors', 'Into sponsors', 'ssBrandSpon') + '</div>';
      }
      // --- optional: hand the split to Spec Sculpt's zone/region path if present ---
      if (typeof window.shokkTraceImportZones === 'function' && typeof window.encodeRegionMaskRLE === 'function') {
        h += '<button type="button" class="btn" id="ssLayersApply" style="margin-top:10px;">🧩 Apply as regions</button>';
      }
    }

    card.innerHTML = h;

    // wire (re-wired each render; no observers)
    var btn = $('ssLayersRun'); if (btn) btn.onclick = function () { SL.run(); };
    var ap = $('ssLayersApply'); if (ap) ap.onclick = function () { SL.applyRegions(); };
    var _bs = $('ssBrandSep'); if (_bs) _bs.onclick = function () { SL.brandMerge = 'separate'; SL.render(); };
    var _bp = $('ssBrandPaint'); if (_bp) _bp.onclick = function () { SL.brandMerge = 'paint'; SL.render(); };
    var _bn = $('ssBrandSpon'); if (_bn) _bn.onclick = function () { SL.brandMerge = 'sponsors'; SL.render(); };
  };

  // ---- OPTIONAL: turn the masks into regions, only if Spec Sculpt exposes the path ----
  SL.brandMerge = 'separate';                // 'separate' | 'paint' | 'sponsors'
  SL.applyRegions = function applyRegions() {
    var r = SL.result;
    if (!r || !r.layers) return;
    if (typeof window.shokkTraceImportZones !== 'function' || typeof window.encodeRegionMaskRLE !== 'function') return;
    SL.status = 'Building regions…'; SL.render();
    var spec = [
      { key: 'paint', name: 'Paint' },
      { key: 'numbers', name: 'Numbers' },
      { key: 'sponsors', name: 'Sponsors' },
      { key: 'template', name: 'Template' },
      { key: 'brand_graphics', name: 'Brand Graphics' }
    ];
    Promise.all(spec.map(function (s) { return r.layers[s.key] ? _decodeMaskPNG(r.layers[s.key]) : Promise.resolve(null); })).then(function (decoded) {
      var bm = SL.brandMerge || 'separate', bgd = decoded[4];
      if (bgd && bgd.any && bm !== 'separate') {
        var tgt = decoded[(bm === 'sponsors') ? 2 : 0];
        if (tgt && tgt.data) { for (var q = 0; q < bgd.data.length; q++) { if (bgd.data[q]) tgt.data[q] = 255; } tgt.any = true; }
        decoded[4] = null;
      }
      var W = 0, H = 0, zones = [];
      spec.forEach(function (s, i) {
        var d = decoded[i];
        if (!d || !d.any) return;
        if (!W) { W = d.width; H = d.height; }
        var rle = window.encodeRegionMaskRLE(d.data, d.width, d.height);
        if (rle) zones.push({ name: s.name, rle: rle });
      });
      if (!zones.length) { SL.status = 'No non-empty layers.'; SL.render(); return; }
      try {
        var n = window.shokkTraceImportZones({ width: W, height: H, zones: zones });
        SL.status = '✓ created ' + (n || zones.length) + ' regions'; SL.render();
      } catch (e) { SL.status = 'Failed: ' + (e.message || e); SL.render(); }
    }).catch(function (e) { SL.status = 'Failed: ' + (e.message || e); SL.render(); });
  };

  function _decodeMaskPNG(dataUrl) {
    return new Promise(function (resolve) {
      if (!dataUrl) { resolve(null); return; }
      var im = new Image();
      im.onload = function () {
        try {
          var w = im.naturalWidth, hh = im.naturalHeight;
          if (!w || !hh) { resolve(null); return; }
          var cv = document.createElement('canvas'); cv.width = w; cv.height = hh;
          var ctx = cv.getContext('2d'); ctx.drawImage(im, 0, 0, w, hh);
          var px = ctx.getImageData(0, 0, w, hh).data;
          var out = new Uint8Array(w * hh), any = false;
          for (var i = 0, p = 0; i < out.length; i++, p += 4) {
            if (px[p] > 127) { out[i] = 255; any = true; }
          }
          resolve({ data: out, width: w, height: hh, any: any });
        } catch (e) { resolve(null); }
      };
      im.onerror = function () { resolve(null); };
      im.src = dataUrl;
    });
  }

  // ---- boot: probe once after DOM is ready, mount the card ----
  function boot() { try { SL.probe(); } catch (e) {} }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
