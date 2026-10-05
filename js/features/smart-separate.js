/* ============================================================================
 * SMART SEPARATE — right-side Layer-column panel for FLAT images (2026-06-26)
 * ---------------------------------------------------------------------------
 * Owner ask (repeated): a flat TGA/PNG/JPEG has no PSD layer tree, so the right
 * "Layers" column normally just says "NO LAYERS — TGA LOADED". Put the SMART
 * tools THERE instead — split the flat livery into NUMBERS / SPONSOR LOGOS /
 * PAINT, with tolerance sliders, an obvious ON/OFF toggle (default OFF), and a
 * one-click "Protect numbers & sponsors" so finishes stop painting over them.
 *
 * PURELY ADDITIVE + self-contained: it exposes window.SmartSep and is called
 * from renderLayerPanel() (paint-booth-3-canvas.js) via a 2-line hook. NO
 * page-wide MutationObserver (that earlier broke the live preview). If the
 * /api/auto-separate-livery route is missing it degrades to the old message.
 * ========================================================================== */
(function () {
  'use strict';
  if (window.SmartSep && window.SmartSep.__installed) return;

  var S = window.SmartSep = window.SmartSep || {};
  S.__installed = true;
  S.enabled = false;          // master toggle — DEFAULT OFF
  S.sens = 1.0;               // sensitivity 0.3..2.0
  S.numSize = 1.0;            // number-size 0.4..2.5
  S.live = false;            // live re-run on slider move
  S.result = null;            // last API result {overlay, masks, fractions, detected}
  S.status = '';              // status line text
  S.busy = false;
  S.protect = false;          // "protect numbers & sponsors on render" flag
  S.protectMask = null;       // combined numbers+sponsors mask (data URL) for the render
  var _gen = 0;               // generation counter to drop stale responses
  var _liveTimer = null;
  var SMART_TGA_BUILD_PREFIX = 'smart-tga-cycle';

  // --- 4-LAYER auto-separation state (numbers/sponsors/template/paint -> real zones) ---
  S.layers = S.layers || { busy: false, creating: false, status: '', result: null };
  var _lgen = 0;              // generation counter for the layers run

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]; }); }
  function pct(x) { return Math.round((Number(x) || 0) * 100); }

  // --- redraw the host panel (re-enters renderLayerPanel -> renderInto) ---
  function redraw() {
    try { if (typeof window.renderLayerPanel === 'function') { window.renderLayerPanel(); return; } } catch (e) {}
    var c = document.getElementById('layerPanelContent');
    if (c) S.renderInto(c);
  }
  S.redraw = redraw;

  // --- grab the current flat livery as a PNG blob from the paint canvas ---
  function canvasBlob() {
    return new Promise(function (resolve, reject) {
      var c = document.getElementById('paintCanvas');
      if (!c || !c.width) { reject(new Error('Load a flat image first')); return; }
      try { c.toBlob(function (b) { b ? resolve(b) : reject(new Error('canvas read failed')); }, 'image/png'); }
      catch (e) { reject(e); }
    });
  }

  function currentSourcePaintPath() {
    try {
      var v = (document.getElementById('paintFile') || {}).value || localStorage.getItem('spb_last_paint_file') || '';
      return String(v || '').trim();
    } catch (_) {
      return '';
    }
  }

  function currentIracingCarFolderHint() {
    try {
      var v = (document.getElementById('outputDir') || {}).value || '';
      return String(v || '').trim();
    } catch (_) {
      return '';
    }
  }

  function currentAutoLayerCarHint(sourcePath) {
    var folder = currentIracingCarFolderHint();
    return folder || sourcePath || '';
  }

  function isFullTgaPath(path) {
    var p = String(path || '').trim();
    if (!/\.tga$/i.test(p.split(/[?#]/, 1)[0])) return false;
    return /^[A-Za-z]:[\\/]/.test(p) || /^\\\\/.test(p) || /^\//.test(p);
  }

  function shouldUseDiskTgaForAutoLayers(path) {
    // Smart TGA Auto-build must classify the original flat TGA, not whatever
    // the visible layer stack currently recomposes after a previous sort.
    return isFullTgaPath(path);
  }

  function requireSmartTgaHandshake(j) {
    var build = j && j.smart_tga && j.smart_tga.build;
    if (typeof build === 'string' && build.indexOf(SMART_TGA_BUILD_PREFIX) === 0) return j;
    throw new Error('stale Smart TGA server response: restart/reload the SPB server so Auto-build uses the current separator');
  }

  function autoLayersUploadJson(hint) {
    return canvasBlob().then(function (blob) {
      var fd = new FormData();
      fd.append('image', blob, 'livery.png');
      fd.append('preview_size', '1024');
      fd.append('brand_graphics_merge', Lyr.brandMerge || 'sponsors');
      if (hint) fd.append('paint_file_hint', hint);
      var carHint = currentAutoLayerCarHint(hint);
      if (carHint) fd.append('car_hint_path', carHint);
      return fetch('/api/auto-layers', { method: 'POST', body: fd });
    }).then(function (r) { return r.json(); }).then(requireSmartTgaHandshake);
  }

  function autoLayersRequestJson() {
    var hint = currentSourcePaintPath();
    var carHint = currentAutoLayerCarHint(hint);
    if (shouldUseDiskTgaForAutoLayers(hint)) {
      return fetch('/api/auto-layers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Shokker-Internal': '1' },
        body: JSON.stringify({
          paint_file: hint,
          paint_file_hint: hint,
          car_hint_path: carHint,
          preview_size: 1024,
          brand_graphics_merge: Lyr.brandMerge || 'sponsors'
        })
      }).then(function (r) {
        return r.json().then(function (j) {
          if (r.ok && j && j.success) return requireSmartTgaHandshake(j);
          var msg = (j && j.error) || ('HTTP ' + r.status);
          throw new Error('source path route failed: ' + msg);
        });
      }).catch(function (e) {
        try { console.warn('[Smart TGA] source path auto-layers failed; falling back to canvas upload', e); } catch (_) {}
        return autoLayersUploadJson(hint);
      });
    }
    return autoLayersUploadJson(hint);
  }

  // --- run the separation against the backend route ---
  S.run = function run() {
    var myGen = ++_gen;
    S.busy = true; S.status = 'Separating…'; redraw();
    canvasBlob().then(function (blob) {
      var fd = new FormData();
      fd.append('image', blob, 'livery.png');
      fd.append('sensitivity', String(S.sens));
      fd.append('number_size', String(S.numSize));
      return fetch('/api/auto-separate-livery', { method: 'POST', body: fd });
    }).then(function (r) { return r.json(); }).then(function (j) {
      if (myGen !== _gen) return;            // a newer run superseded this one
      S.busy = false;
      if (!j || !j.success) { S.result = null; S.status = 'Failed: ' + ((j && j.error) || 'unknown'); redraw(); return; }
      if (!j.detected) { S.result = j; S.status = j.message || 'Nothing confidently separated — raise Sensitivity.'; redraw(); return; }
      S.result = j; S.status = '✓ separated';
      // keep an existing protect choice in sync with the freshest masks
      if (S.protect && j.masks) S.protectMask = j.masks; // store the full mask set
      redraw();
    }).catch(function (e) {
      if (myGen !== _gen) return;
      S.busy = false; S.result = null; S.status = 'Failed: ' + (e.message || e); redraw();
    });
  };

  function liveMaybe() { if (S.live) { clearTimeout(_liveTimer); _liveTimer = setTimeout(S.run, 350); } }

  // --- toggle / slider handlers (called from inline oninput/onclick) ---
  S.toggle = function () {
    S.enabled = !S.enabled;
    if (!S.enabled) { S.status = ''; }       // collapse but keep last result cached
    redraw();
  };
  S.setSens = function (v) { S.sens = Math.max(0.3, Math.min(2.0, (parseInt(v, 10) || 100) / 100)); _updLabels(); liveMaybe(); };
  S.setNum = function (v) { S.numSize = Math.max(0.4, Math.min(2.5, (parseInt(v, 10) || 100) / 100)); _updLabels(); liveMaybe(); };
  S.setLive = function (on) { S.live = !!on; if (on) S.run(); };
  // Re-run only if Live is on (used by the Studio when it writes state back).
  S.liveMaybe = liveMaybe;
  // Union the numbers + sponsors grayscale masks into ONE protect mask (data URL).
  // The render path feeds this to the engine as decal_mask_base64, which restores the
  // ORIGINAL composite RGB (decals) into those pixels AFTER finishes — so numbers and
  // sponsor logos survive whatever finish covers the body.
  function combineMasks(masks) {
    return new Promise(function (resolve) {
      var imgs = ['numbers', 'sponsors'].map(function (k) { return masks[k]; }).filter(Boolean);
      if (!imgs.length) { resolve(null); return; }
      var loaded = 0, els = [], done = false;
      function build() {
        try {
          var w = els[0].naturalWidth, hh = els[0].naturalHeight;
          var cv = document.createElement('canvas'); cv.width = w; cv.height = hh;
          var ctx = cv.getContext('2d');
          ctx.fillStyle = '#000'; ctx.fillRect(0, 0, w, hh);
          ctx.globalCompositeOperation = 'lighter';   // union of the two white masks
          els.forEach(function (e) { try { ctx.drawImage(e, 0, 0, w, hh); } catch (_) {} });
          resolve(cv.toDataURL('image/png'));
        } catch (e) { resolve(null); }
      }
      els = imgs.map(function (src) {
        var im = new Image();
        im.onload = function () { if (++loaded === imgs.length && !done) { done = true; build(); } };
        im.onerror = function () { if (++loaded === imgs.length && !done) { done = true; build(); } };
        im.src = src; return im;
      });
    });
  }

  S.applyProtect = function () {
    if (!S.result || !S.result.detected || !S.result.masks) { S.status = 'Run Separate first.'; redraw(); return; }
    S.status = 'Building protect mask…'; redraw();
    combineMasks(S.result.masks).then(function (url) {
      S.protect = true; S.protectMask = S.result.masks; S.protectMaskUrl = url || null;
      S.status = url ? '🛡 Protecting numbers & sponsors on render' : 'Protect mask build failed';
      try { if (typeof window.requestLivePreview === 'function') window.requestLivePreview(); else if (typeof window.triggerLivePreview === 'function') window.triggerLivePreview(); } catch (e) {}
      redraw();
    });
  };
  S.clearProtect = function () {
    S.protect = false; S.protectMask = null; S.protectMaskUrl = null; S.status = 'Protection off';
    try { if (typeof window.requestLivePreview === 'function') window.requestLivePreview(); else if (typeof window.triggerLivePreview === 'function') window.triggerLivePreview(); } catch (e) {}
    redraw();
  };

  function _updLabels() {
    var a = document.getElementById('ssSensV'); if (a) a.textContent = S.sens.toFixed(1) + '×';
    var b = document.getElementById('ssNumV'); if (b) b.textContent = S.numSize.toFixed(1) + '×';
  }

  // --- COMPACT LAUNCHER, rendered into #layerPanelContent ---
  // The full guided workspace now lives in SmartSepStudio (smart-separate-studio.js).
  // This panel is just the ON/OFF toggle + protect status + a button into the Studio,
  // plus a small summary of the last result so the painter sees state at a glance.
  S.renderInto = function renderInto(container) {
    if (!container) return;
    var gold = 'var(--accent-gold,#e8b13a)', cyan = 'var(--accent-cyan,#46c8ff)', dim = 'var(--text-dim,#8a93a6)';
    var bd = '1px solid var(--border,#2a2f3a)';
    var on = S.enabled;
    var L = S.layers;
    var sw = '<button data-testid="smart-tga-toggle" onclick="SmartSep.toggle()" title="Turn the smart split on/off" style="cursor:pointer;border:' + bd +
      ';border-radius:999px;width:42px;height:22px;position:relative;background:' + (on ? 'linear-gradient(90deg,#3a7bd5,#7c4dff)' : '#222732') +
      ';flex:0 0 auto;transition:background .15s;">' +
      '<span style="position:absolute;top:1px;left:' + (on ? '21px' : '1px') + ';width:18px;height:18px;border-radius:50%;background:#fff;transition:left .15s;"></span></button>';
    var autoBuildClick = on ? 'SmartSep.layers.run()' : 'SmartSep.enabled=true;SmartSep.layers.run()';
    var autoBuildButton = '<button type="button" data-testid="smart-tga-auto-build" onclick="' + autoBuildClick + '" ' + (L.busy ? 'disabled ' : '') +
         'style="cursor:' + (L.busy ? 'default' : 'pointer') + ';width:100%;margin-top:8px;border:' + bd +
         ';border-radius:9px;padding:9px 0;font-weight:800;font-size:11px;letter-spacing:.3px;color:#dfe9ff;background:linear-gradient(135deg,#14324f,#3a1f5c);">Auto-build layers' +
         (L.busy ? ' ...' : '') + '</button>';

    var h = '';
    h += '<div style="padding:10px 9px 6px;">';
    h += '<div style="display:flex;align-items:center;gap:8px;">' +
         '<strong style="color:' + gold + ';font-size:11px;letter-spacing:.4px;">🪓 SMART SEPARATE</strong>' +
         '<span style="margin-left:auto;"></span>' + sw + '</div>';
    h += '<div style="font-size:9px;color:' + dim + ';margin-top:4px;line-height:1.5;">Flat image — no PSD layers. Split it into ' +
         '<span style="color:#ff7a7a;">numbers</span>, <span style="color:#8ab8ff;">sponsors</span> &amp; ' +
         '<span style="color:#9affb0;">paint</span> so finishes skip the decals.</div>';

    if (!on) {
      h += autoBuildButton;
      if (L.status) h += '<div style="margin-top:7px;font-size:9px;color:' + (L.status.indexOf('Failed') === 0 ? '#ff7a7a' : (L.busy ? cyan : dim)) + ';">' + esc(L.status) + '</div>';
      h += '<div style="font-size:9px;color:' + dim + ';margin-top:8px;line-height:1.5;">Toggle on to open the guided Studio — paint over what should be a number vs a sponsor and protect the decals.</div>';
      if (S.protect) h += '<div style="margin-top:8px;font-size:9px;color:#9affb0;">🛡 Protection is ON (numbers &amp; sponsors kept on render). <a href="#" onclick="SmartSep.clearProtect();return false;" style="color:' + cyan + ';">turn off</a></div>';
      h += '</div>';
      container.innerHTML = h;
      return;
    }

    // --- ENABLED: big launcher button into the Studio ---
    h += '<button onclick="if(window.SmartSepStudio)SmartSepStudio.open();" style="cursor:pointer;width:100%;margin-top:11px;border:none;border-radius:9px;padding:10px 0;font-weight:800;font-size:11px;letter-spacing:.3px;color:#ffffff;text-shadow:0 1px 2px rgba(0,0,0,.55);background:linear-gradient(135deg,#00e5ff,#7c4dff);box-shadow:0 4px 14px rgba(0,229,255,.18);">🪓 Open Smart Separate Studio →</button>';

    // --- 4-LAYER auto-separation launcher (numbers/sponsors/template/paint as real zones) ---
    var L = S.layers;
    h += '<button onclick="SmartSep.layers.run()" ' + (L.busy ? 'disabled ' : '') +
         'style="cursor:' + (L.busy ? 'default' : 'pointer') + ';width:100%;margin-top:8px;border:' + bd +
         ';border-radius:9px;padding:9px 0;font-weight:800;font-size:11px;letter-spacing:.3px;color:#dfe9ff;background:linear-gradient(135deg,#14324f,#3a1f5c);">🧩 Auto-build layers' +
         (L.busy ? ' …' : '') + '</button>';
    if (L.status) h += '<div style="margin-top:7px;font-size:9px;color:' + (L.status.indexOf('Failed') === 0 ? '#ff7a7a' : (L.busy ? cyan : dim)) + ';">' + esc(L.status) + '</div>';
    if (L.result && L.result.success) {
      var car = (L.result.car && L.result.car[0]) || null;
      if (car) {
        var carScore = Number(car.score);
        var lowCarConf = isFinite(carScore) && carScore > 0 && carScore < 0.20;
        var carColor = lowCarConf ? '#ffb14d' : '#9affb0';
        var carName = lowCarConf ? (car.slug || car.family || '?') : (car.family || car.slug || '?');
        var carWarn = lowCarConf ? ' <strong style="color:#ffb14d;">low confidence</strong>' : '';
        h += '<div style="margin-top:7px;font-size:9px;color:' + carColor + ';">Detected: <strong>' + esc(carName) + '</strong> <span style="color:' + dim + ';">(' + esc(String(car.score)) + ')</span>' + carWarn + '</div>';
      }
      var lf = L.result.fractions || {};
      if (L.result.engine) {
        var gc = L.result.gpu_cache || null;
        var cacheText = '';
        if (gc && gc.cache) {
          var cc = gc.cache === 'hit' ? '#9affb0' : (gc.cache === 'miss' ? '#ffb14d' : dim);
          cacheText = ' <span style="color:' + dim + ';">Cache:</span> <strong style="color:' + cc + ';">' + esc(gc.cache) + '</strong>';
          if (gc.reason) {
            cacheText += ' <span style="color:' + dim + ';">Reason:</span> <strong style="color:#ffb14d;">' + esc(gc.reason) + '</strong>';
          }
        }
        h += '<div style="margin-top:5px;font-size:9px;color:' + dim + ';">Engine: <strong style="color:' + (L.result.engine === 'gpu_hybrid' ? '#ffb14d' : cyan) + ';">' + esc(L.result.engine) + '</strong>' + cacheText + '</div>';
      }
      if (L.result.smart_tga && L.result.smart_tga.build) {
        h += '<div style="margin-top:4px;font-size:9px;color:' + dim + ';">Smart TGA: <strong style="color:#9affb0;">' + esc(L.result.smart_tga.build) + '</strong></div>';
      }
      if (L.result.source && L.result.source.mode) {
        var src = L.result.source;
        var srcMode = src.mode === 'paint_file' ? 'path' : src.mode;
        var srcBytes = Number(src.bytes || 0);
        var srcSize = srcBytes > 0 ? (' · ' + (srcBytes >= 1048576 ? (srcBytes / 1048576).toFixed(1) + ' MB' : Math.round(srcBytes / 1024) + ' KB')) : '';
        h += '<div style="margin-top:4px;font-size:9px;color:' + dim + ';">Source: <strong style="color:' + (src.mode === 'paint_file' ? '#9affb0' : cyan) + ';">' + esc(srcMode) + '</strong>' + (src.label ? ' <span style="color:' + dim + ';">' + esc(src.label) + '</span>' : '') + srcSize + '</div>';
      }
      var tg = L.result.template_guard || null;
      if (tg && (tg.status === 'blocked' || tg.reason === 'area_rejected')) {
        var tgText = tg.status || 'skipped';
        if (tg.reason) tgText += ' (' + tg.reason + ')';
        if (tg.matched_slug) tgText += ' ' + tg.matched_slug;
        h += '<div style="margin-top:4px;font-size:9px;color:' + dim + ';">Template: <strong style="color:#ffb14d;">' + esc(tgText) + '</strong></div>';
      }
      var cn = L.result.companion_numbers || null;
      if (cn && cn.status) {
        var notableSkip = cn.reason && ['delta_area_rejected', 'source_mismatch', 'component_shape_rejected', 'whole_canvas_bbox', 'disabled', 'error'].indexOf(cn.reason) >= 0;
        if (cn.status === 'applied' || notableSkip) {
          var compColor = cn.status === 'applied' ? '#9affb0' : '#ffb14d';
          var compText = cn.status;
          if (cn.status === 'applied' && cn.delta_frac != null) compText += ' +' + pct(cn.delta_frac) + '%';
          if (cn.reason) compText += ' (' + cn.reason + ')';
          h += '<div style="margin-top:4px;font-size:9px;color:' + dim + ';">Companion #s: <strong style="color:' + compColor + ';">' + esc(compText) + '</strong></div>';
        }
      }
      var cd = L.result.companion_decals || null;
      if (cd && cd.status) {
        var decalSkip = cd.reason && ['alpha_area_rejected', 'source_mismatch', 'component_shape_rejected', 'whole_canvas_bbox', 'disabled', 'error'].indexOf(cd.reason) >= 0;
        if (cd.status === 'applied' || decalSkip) {
          var decalColor = cd.status === 'applied' ? '#9affb0' : '#ffb14d';
          var decalText = cd.status;
          if (cd.status === 'applied' && cd.alpha_frac != null) decalText += ' +' + pct(cd.alpha_frac) + '%';
          if (cd.reason) decalText += ' (' + cd.reason + ')';
          h += '<div style="margin-top:4px;font-size:9px;color:' + dim + ';">Companion decals: <strong style="color:' + decalColor + ';">' + esc(decalText) + '</strong></div>';
        }
      }
      if (L.layerCheck) {
        var lc = L.layerCheck;
        var roundtripWarn = (lc.roundtripDiffFrac || 0) > 0.002 || (lc.roundtripGapFrac || 0) > 0.002;
        var ok = lc.restrictReady && !lc.mismatch && !lc.overlapPixels && !roundtripWarn;
        var lcColor = ok ? '#9affb0' : '#ffb14d';
        var lcText = ok ? 'restrict-ready' : 'check needed';
        lcText += ' · ' + (lc.layerCount || 0) + ' layers';
        if (lc.coverageFrac != null) lcText += ' · ' + pct(lc.coverageFrac) + '% covered';
        if (lc.roundtripDiffFrac != null && (lc.roundtripDiffFrac > 0 || lc.roundtripGapFrac > 0)) lcText += ' · roundtrip ' + pct(lc.roundtripDiffFrac) + '% diff';
        if (lc.overlapPixels) lcText += ' · overlap ' + pct(lc.overlapFrac) + '%';
        if (lc.roundtripGapFrac) lcText += ' · gap ' + pct(lc.roundtripGapFrac) + '%';
        if (lc.mismatch) lcText += ' · mask size mismatch';
        h += '<div style="margin-top:4px;font-size:9px;color:' + dim + ';">Real layers: <strong style="color:' + lcColor + ';">' + esc(lcText) + '</strong></div>';
      }
      if (L.layerCheck && L.undoAutoBuildReady) {
        h += '<button onclick="SmartSep.layers.undoAutoBuild()" style="cursor:pointer;width:100%;margin-top:7px;border:1px solid #4a2a2a;border-radius:8px;padding:7px 0;font-size:10px;font-weight:800;color:#ffb3b3;background:#241111;">Undo Auto-build layers</button>';
      }
      h += '<div style="margin-top:7px;font-size:9px;display:flex;gap:6px;flex-wrap:wrap;">' +
           '<span style="background:#2a1414;color:#ff7a7a;border-radius:999px;padding:2px 7px;">Numbers ' + pct(lf.numbers) + '%</span>' +
           '<span style="background:#141e2a;color:#8ab8ff;border-radius:999px;padding:2px 7px;">Sponsors ' + pct(lf.sponsors) + '%</span>' +
           '<span style="background:#102014;color:#9affb0;border-radius:999px;padding:2px 7px;">Template ' + pct(lf.template) + '%</span>' +
           ((lf.brand_graphics > 0) ? '<span style="background:#241a0e;color:#ffb14d;border-radius:999px;padding:2px 7px;">Brand graphics ' + pct(lf.brand_graphics) + '%</span>' : '') +
           '<span style="background:#1a1a22;color:#cfd6e6;border-radius:999px;padding:2px 7px;">Paint ' + pct(lf.paint) + '%</span></div>';
      if (L.result.overlay) h += '<img src="' + L.result.overlay + '" alt="layer overlay" style="width:100%;margin-top:8px;border-radius:7px;border:' + bd + ';display:block;">';
      if (lf.brand_graphics > 0) {
        var bm = L.brandMerge || 'separate';
        var bopt = function (v, lbl) {
          var on = (bm === v);
          return '<button onclick="SmartSep.layers.setBrand(\'' + v + '\')" style="cursor:pointer;flex:1;border:1px solid ' + (on ? '#ffb14d' : '#2a2f3a') + ';background:' + (on ? '#241a0e' : 'transparent') + ';color:' + (on ? '#ffb14d' : dim) + ';border-radius:6px;padding:5px 0;font-size:9px;font-weight:700;">' + lbl + '</button>';
        };
        h += '<div style="margin-top:8px;font-size:9px;color:' + dim + ';">Brand graphics (m&amp;m, Monster, Bass Pro…) — these can be:</div>' +
             '<div style="margin-top:4px;display:flex;gap:5px;">' + bopt('separate', 'Own layer') + bopt('paint', 'Into paint') + bopt('sponsors', 'Into sponsors') + '</div>';
      }
      h += '<button onclick="SmartSep.layers.createZones()" ' + (L.creating ? 'disabled ' : '') +
           'style="cursor:' + (L.creating ? 'default' : 'pointer') + ';width:100%;margin-top:8px;border:none;border-radius:8px;padding:8px 0;font-size:10px;font-weight:800;color:#04121a;background:linear-gradient(135deg,#9affb0,#46c8ff);">🧩 Create these layers as zones' + (L.creating ? ' …' : '') + '</button>';
    }

    // --- status ---
    if (S.status) h += '<div style="margin-top:8px;font-size:9px;color:' + (S.status.indexOf('Failed') === 0 ? '#ff7a7a' : dim) + ';">' + esc(S.status) + '</div>';

    // --- compact result summary (chips + small overlay + 3 mask thumbs) ---
    var r = S.result;
    if (r && r.detected) {
      var f = r.fractions || {};
      h += '<div style="margin-top:10px;font-size:9px;display:flex;gap:7px;flex-wrap:wrap;">' +
           '<span style="background:#2a1414;color:#ff7a7a;border-radius:999px;padding:2px 8px;">Numbers ' + pct(f.numbers) + '%</span>' +
           '<span style="background:#141e2a;color:#8ab8ff;border-radius:999px;padding:2px 8px;">Sponsors ' + pct(f.sponsors) + '%</span>' +
           '<span style="background:#102014;color:#9affb0;border-radius:999px;padding:2px 8px;">Paint ' + pct(f.paint) + '%</span></div>';
      if (r.overlay) h += '<img src="' + r.overlay + '" alt="separation overlay" style="width:100%;margin-top:8px;border-radius:7px;border:' + bd + ';display:block;">';
      if (r.masks) {
        h += '<div style="margin-top:6px;display:flex;gap:5px;">';
        h += '<div style="flex:1;text-align:center;"><div style="font-size:8px;color:#ff7a7a;margin-bottom:2px;">Numbers</div><img src="' + r.masks.numbers + '" style="width:100%;border-radius:5px;border:' + bd + ';background:#05070a;display:block;"></div>';
        h += '<div style="flex:1;text-align:center;"><div style="font-size:8px;color:#8ab8ff;margin-bottom:2px;">Sponsors</div><img src="' + r.masks.sponsors + '" style="width:100%;border-radius:5px;border:' + bd + ';background:#05070a;display:block;"></div>';
        h += '<div style="flex:1;text-align:center;"><div style="font-size:8px;color:#9affb0;margin-bottom:2px;">Paint</div><img src="' + r.masks.paint + '" style="width:100%;border-radius:5px;border:' + bd + ';background:#05070a;display:block;"></div>';
        h += '</div>';
      }
      // --- protect status / apply ---
      if (S.protect) {
        h += '<div style="margin-top:9px;font-size:9px;color:#9affb0;">🛡 Numbers &amp; sponsors will be kept on render. <a href="#" onclick="SmartSep.clearProtect();return false;" style="color:' + cyan + ';">turn off</a></div>';
      } else {
        h += '<button onclick="SmartSep.applyProtect()" style="cursor:pointer;width:100%;margin-top:9px;border:' + bd + ';border-radius:8px;padding:7px 0;font-size:10px;font-weight:700;color:#9affb0;background:#10261a;">🛡 Protect numbers &amp; sponsors</button>';
      }
      h += '<div style="margin-top:7px;font-size:8px;color:' + dim + ';line-height:1.5;">Open the Studio to paint marks, refine the split, build zones, or fine-tune sensitivity.</div>';
    } else if (r && !r.detected && r.overlay) {
      h += '<img src="' + r.overlay + '" alt="livery" style="width:100%;margin-top:8px;border-radius:7px;border:' + bd + ';display:block;">';
    }

    h += '</div>';
    container.innerHTML = h;
    _updLabels();
  };

  // Render-path contribution: when protection is on, hand the combined numbers+sponsors
  // mask to the engine via the proven decal_mask_base64 channel (restores original decal
  // RGB after finishes). Returns null when off so it's a strict no-op.
  S.renderPayload = function () {
    if (S.protect && S.protectMaskUrl) return { decal_mask_base64: S.protectMaskUrl };
    return null;
  };

  // ==========================================================================
  // 4-LAYER AUTO-SEPARATION (numbers / sponsors / template / paint -> zones)
  // Self-contained. Hits /api/auto-layers (car_layers.separate_into_layers, OCR
  // driven ~15s), then turns each non-empty PNG mask into an RLE zone and feeds
  // window.shokkTraceImportZones. No MutationObserver.
  // ==========================================================================

  // Load a PNG data URL into an offscreen canvas, threshold to a binary Uint8Array
  // (>127 -> 255 else 0). Resolves {data:Uint8Array, width, height} at the PNG's
  // NATIVE size. Resolves null on failure / empty source.
  function decodeMaskPNG(dataUrl) {
    return new Promise(function (resolve) {
      if (!dataUrl) { resolve(null); return; }
      var im = new Image();
      im.onload = function () {
        try {
          var w = im.naturalWidth, hh = im.naturalHeight;
          if (!w || !hh) { resolve(null); return; }
          var cv = document.createElement('canvas'); cv.width = w; cv.height = hh;
          var ctx = cv.getContext('2d');
          ctx.drawImage(im, 0, 0, w, hh);
          var px = ctx.getImageData(0, 0, w, hh).data;
          var out = new Uint8Array(w * hh);
          var any = false;
          for (var i = 0, p = 0; i < out.length; i++, p += 4) {
            // mask PNGs are white-on-black; use the red channel as luma
            if (px[p] > 127) { out[i] = 255; any = true; }
          }
          resolve({ data: out, width: w, height: hh, any: any });
        } catch (e) { resolve(null); }
      };
      im.onerror = function () { resolve(null); };
      im.src = dataUrl;
    });
  }

  var Lyr = S.layers;
  if (typeof Lyr.undoAutoBuildReady !== 'boolean') Lyr.undoAutoBuildReady = false;

  Lyr.run = function run() {
    var myGen = ++_lgen;
    Lyr.busy = true; Lyr.undoAutoBuildReady = false; Lyr.layerCheck = null; Lyr.status = 'Reading livery... Smart TGA deep pass can take 60-90s'; Lyr.result = null; redraw();
    autoLayersRequestJson().then(function (j) {
      if (myGen !== _lgen) return;
      Lyr.busy = false;
      if (!j || !j.success) { Lyr.result = null; Lyr.status = 'Failed: ' + ((j && j.error) || 'unknown'); redraw(); return; }
      Lyr.result = j; Lyr.status = 'Stacking layers…';
      // OWNER 2026-06-28: Auto-build must produce REAL stacked LAYERS in the right panel
      // (Numbers/Sponsors/Car Template/Paint), not just an overlay — build them now.
      Lyr.buildLayers();
    }).catch(function (e) {
      if (myGen !== _lgen) return;
      Lyr.busy = false; Lyr.result = null; Lyr.status = 'Failed: ' + (e.message || e); redraw();
    });
  };

  Lyr.brandMerge = 'sponsors';                 // 'separate' | 'paint' | 'sponsors'
  Lyr.setBrand = function setBrand(v) { Lyr.brandMerge = v; redraw(); };

  Lyr.undoAutoBuild = function undoAutoBuild() {
    if (typeof window.undoSmartTgaAutoBuildLayers !== 'function') {
      Lyr.status = 'Auto-build undo unavailable.';
    } else if (window.undoSmartTgaAutoBuildLayers()) {
      Lyr.undoAutoBuildReady = false;
      Lyr.layerCheck = null;
      Lyr.status = 'Undid Smart TGA auto-build layers.';
    } else {
      Lyr.undoAutoBuildReady = false;
      Lyr.status = 'Auto-build undo is no longer the latest layer action.';
    }
    redraw();
  };

  Lyr.createZones = function createZones() {
    var r = Lyr.result;
    if (!r || !r.success || !r.layers) { Lyr.status = 'Run Auto-build layers first.'; redraw(); return; }
    if (typeof window.shokkTraceImportZones !== 'function') { Lyr.status = 'Zone importer unavailable.'; redraw(); return; }
    Lyr.creating = true; Lyr.status = 'Building zones…'; redraw();
    // Paint FIRST, then numbers/sponsors/template/brand-graphics (priority order for the painter).
    var spec = [
      { key: 'paint', name: 'Paint', base_color: '#cccccc' },
      { key: 'numbers', name: 'Numbers', base_color: '#111111' },
      { key: 'sponsors', name: 'Sponsors', base_color: '#222222' },
      { key: 'template', name: 'Template', base_color: '#0a0a0a' },
      { key: 'brand_graphics', name: 'Brand Graphics', base_color: '#181818' }
    ];
    Promise.all(spec.map(function (s) {
      return r.layers[s.key] ? decodeMaskPNG(r.layers[s.key]) : Promise.resolve(null);
    })).then(function (decoded) {
      // BRAND-GRAPHICS 3-way merge (owner 2026-06-27): the ambiguous graphic logos (m&m, Bass Pro,
      // Monster) can be their own layer, folded into PAINT, or folded into SPONSORS — user's choice.
      var bm = Lyr.brandMerge || 'sponsors', bg = decoded[4];
      if (bg && bg.any && bm !== 'separate') {
        var tgt = decoded[(bm === 'sponsors') ? 2 : 0];   // sponsors, else paint
        if (tgt && tgt.data) {
          for (var q = 0; q < bg.data.length; q++) { if (bg.data[q]) tgt.data[q] = 255; }
          tgt.any = true;
        }
        decoded[4] = null;                          // no separate Brand Graphics zone
      }
      var W = 0, Hh = 0, zones = [];
      spec.forEach(function (s, i) {
        var d = decoded[i];
        if (!d || !d.any) return;                 // skip empty masks
        if (!W) { W = d.width; Hh = d.height; }
        var rle = (typeof window.encodeRegionMaskRLE === 'function')
          ? window.encodeRegionMaskRLE(d.data, d.width, d.height) : null;
        if (!rle) return;
        zones.push({ name: s.name, base_color: s.base_color, rle: rle });
      });
      if (!zones.length) { Lyr.creating = false; Lyr.status = 'No non-empty layers to create.'; redraw(); return; }
      try {
        var n = window.shokkTraceImportZones({ width: W, height: Hh, zones: zones });
        Lyr.creating = false; Lyr.status = '✓ created ' + (n || zones.length) + ' zones'; redraw();
      } catch (e) {
        Lyr.creating = false; Lyr.status = 'Failed: ' + (e.message || e); redraw();
      }
    }).catch(function (e) {
      Lyr.creating = false; Lyr.status = 'Failed: ' + (e.message || e); redraw();
    });
  };

  // ==========================================================================
  // 4-LAYER STACK (owner 2026-06-28): turn the auto-separation masks into REAL
  // stacked LAYERS (Numbers / Sponsors / Car Template / Paint [+ Brand Graphics])
  // in the right-side Layers panel, by reusing the PSD-layer machinery. Because
  // the masks PARTITION the car (paint = complement of the rest), a layer whose
  // img = the livery pixels masked to its region reconstructs the IDENTICAL
  // livery via recompositeFromLayers() — display unchanged, now layer-backed, so
  // the ZONE POPOUT "Restrict to layer" dropdown + the render path work on them
  // exactly like PSD layers (both _psdLayers-driven, no other code to touch).
  // ==========================================================================

  // One layer canvas at paint-canvas resolution: livery RGB only where the mask is
  // set (alpha 0 elsewhere). Nearest-samples the (smaller) mask up to W×Hh.
  function buildMaskedLayerCanvas(livery, decoded, W, Hh) {
    var cv = document.createElement('canvas'); cv.width = W; cv.height = Hh;
    var ctx = cv.getContext('2d');
    var out = ctx.createImageData(W, Hh);
    var od = out.data, ld = livery.data, md = decoded.data, mw = decoded.width, mh = decoded.height;
    for (var y = 0; y < Hh; y++) {
      var my = (y * mh / Hh) | 0, mrow = my * mw, row = y * W;
      for (var x = 0; x < W; x++) {
        var mx = (x * mw / W) | 0;
        if (md[mrow + mx]) {
          var p = (row + x) * 4;
          od[p] = ld[p]; od[p + 1] = ld[p + 1]; od[p + 2] = ld[p + 2]; od[p + 3] = 255;
        }
      }
    }
    ctx.putImageData(out, 0, 0);
    return cv;
  }

  function summarizeDecodedAutoLayers(decoded, spec) {
    var base = null, mismatch = false;
    for (var i = 0; i < decoded.length; i++) {
      if (!decoded[i] || !decoded[i].data) continue;
      if (!base) base = { width: decoded[i].width, height: decoded[i].height };
      else if (decoded[i].width !== base.width || decoded[i].height !== base.height) mismatch = true;
    }
    var total = base ? base.width * base.height : 0;
    var seen = total ? new Uint8Array(total) : null;
    var layerCount = 0, covered = 0, overlap = 0, layerPixels = [];
    if (seen) {
      decoded.forEach(function (d, idx) {
        if (!d || !d.data || !d.any || d.width !== base.width || d.height !== base.height) return;
        layerCount++;
        var px = 0;
        for (var p = 0; p < d.data.length; p++) {
          if (!d.data[p]) continue;
          px++;
          if (seen[p]) overlap++;
          else { seen[p] = 1; covered++; }
        }
        layerPixels.push({ key: spec[idx].key, name: spec[idx].name, pixels: px, frac: total ? px / total : 0 });
      });
    }
    return {
      layerCount: layerCount,
      width: base ? base.width : 0,
      height: base ? base.height : 0,
      coverageFrac: total ? covered / total : 0,
      overlapPixels: overlap,
      overlapFrac: total ? overlap / total : 0,
      mismatch: mismatch,
      layerPixels: layerPixels,
      restrictReady: false
    };
  }

  function summarizeLayerRoundtrip(layers, livery, W, Hh) {
    var total = W * Hh;
    if (!total || !layers.length) return { roundtripDiffFrac: 1, roundtripGapFrac: 1, roundtripSamples: 0, roundtripMaxDiff: 255 };
    var stride = total > 600000 ? Math.ceil(Math.sqrt(total / 600000)) : 1;
    var layerData = [];
    for (var i = 0; i < layers.length; i++) {
      try {
        layerData.push(layers[i].img.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, W, Hh).data);
      } catch (_) {
        return { roundtripDiffFrac: 1, roundtripGapFrac: 1, roundtripSamples: 0, roundtripMaxDiff: 255 };
      }
    }
    var src = livery.data, samples = 0, diff = 0, gap = 0, maxDiff = 0;
    for (var y = 0; y < Hh; y += stride) {
      for (var x = 0; x < W; x += stride) {
        var p = (y * W + x) * 4;
        var ar = 0, ag = 0, ab = 0, aa = 0;
        for (var li = 0; li < layerData.length; li++) {
          var ld = layerData[li];
          if (ld[p + 3]) { ar = ld[p]; ag = ld[p + 1]; ab = ld[p + 2]; aa = ld[p + 3]; }
        }
        samples++;
        if (!aa) { gap++; continue; }
        var d = Math.max(Math.abs(ar - src[p]), Math.abs(ag - src[p + 1]), Math.abs(ab - src[p + 2]));
        if (d > maxDiff) maxDiff = d;
        if (d > 2) diff++;
      }
    }
    return {
      roundtripDiffFrac: samples ? diff / samples : 1,
      roundtripGapFrac: samples ? gap / samples : 1,
      roundtripSamples: samples,
      roundtripStride: stride,
      roundtripMaxDiff: maxDiff
    };
  }

  Lyr.buildLayers = function buildLayers() {
    var r = Lyr.result;
    if (!r || !r.success || !r.layers) { Lyr.status = 'Run Auto-build layers first.'; redraw(); return; }
    Lyr.layerCheck = null;
    var pc = document.getElementById('paintCanvas');
    if (!pc || !pc.width) { Lyr.status = 'Load a flat image first.'; redraw(); return; }
    var W = pc.width, Hh = pc.height, livery;
    try { livery = pc.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, W, Hh); }
    catch (e) { Lyr.status = 'Canvas read blocked.'; redraw(); return; }
    Lyr.creating = true; redraw();
    // bottom -> top: paint at the base, decals above it
    var spec = [
      { key: 'paint', name: 'Paint' },
      { key: 'template', name: 'Car Template' },
      { key: 'sponsors', name: 'Sponsors' },
      { key: 'brand_graphics', name: 'Brand Graphics' },
      { key: 'numbers', name: 'Numbers' }
    ];
    Promise.all(spec.map(function (s) { return r.layers[s.key] ? decodeMaskPNG(r.layers[s.key]) : Promise.resolve(null); }))
      .then(function (dec) {
        // BRAND-GRAPHICS 3-way merge (own layer / into paint / into sponsors)
        var bm = Lyr.brandMerge || 'sponsors', bi = 3, bg = dec[bi];
        if (bg && bg.any && bm !== 'separate') {
          var tgt = dec[(bm === 'sponsors') ? 2 : 0];
          if (tgt && tgt.data && tgt.width === bg.width && tgt.height === bg.height) {
            for (var q = 0; q < bg.data.length; q++) { if (bg.data[q]) tgt.data[q] = 255; }
            tgt.any = true; dec[bi] = null;
          }
        }
        var layerCheck = summarizeDecodedAutoLayers(dec, spec);
        var layers = [];
        spec.forEach(function (s, i) {
          var d = dec[i]; if (!d || !d.any) return;
          layers.push({
            id: 'autolayer_' + s.key, name: s.name, path: s.name,
            img: buildMaskedLayerCanvas(livery, d, W, Hh),
            bbox: [0, 0, W, Hh], visible: true, opacity: 255, locked: false,
            groupName: 'Auto-Separated', blendMode: 'source-over', effects: {}, virtual: true
          });
        });
        if (!layers.length) { Lyr.creating = false; Lyr.status = 'No layers to build.'; redraw(); return; }
        var roundtripCheck = summarizeLayerRoundtrip(layers, livery, W, Hh);
        try {
          if (typeof window._captureSmartTgaAutoBuildRestorePoint === 'function') window._captureSmartTgaAutoBuildRestorePoint('Smart TGA auto-build layers');
          if (typeof window._pushLayerStackUndo === 'function') window._pushLayerStackUndo('Smart TGA auto-build layers');
          window._psdLayers = layers;
          window._psdLayersLoaded = true;
          window._selectedLayerId = layers[layers.length - 1].id;
          if (typeof invalidateLayerVisibleContributionCache === 'function') invalidateLayerVisibleContributionCache();
          if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
          Lyr.creating = false; Lyr.status = '';
          Lyr.undoAutoBuildReady = true;
          for (var rcKey in roundtripCheck) { if (Object.prototype.hasOwnProperty.call(roundtripCheck, rcKey)) layerCheck[rcKey] = roundtripCheck[rcKey]; }
          layerCheck.restrictReady = Array.isArray(window._psdLayers) && window._psdLayers.length === layers.length && layers.every(function (layer) { return !!layer.img; });
          Lyr.layerCheck = layerCheck;
          Lyr.status = 'Built ' + layers.length + ' real layers' + (layerCheck.restrictReady ? ' — restrict-ready' : '');
          if (typeof renderLayerPanel === 'function') renderLayerPanel();
          else redraw();
          if (typeof showToast === 'function') showToast('Built ' + layers.length + ' layers — restrict any zone to them in the zone popout');
        } catch (e) { Lyr.creating = false; Lyr.status = 'Failed: ' + (e.message || e); redraw(); }
      }).catch(function (e) { Lyr.creating = false; Lyr.status = 'Failed: ' + (e.message || e); redraw(); });
  };
})();
