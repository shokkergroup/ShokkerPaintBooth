/* ============================================================================
 * SMART SEPARATE STUDIO — pop-out guided workspace (2026-06-26)
 * ---------------------------------------------------------------------------
 * Owner ask: a flat livery (TGA/PNG/JPEG) has no PSD layer tree. Smart Separate
 * (right Layers column) splits it into NUMBERS / SPONSORS / PAINT. This Studio
 * is the *guided* workspace: a full-screen pop-out where the painter sees the
 * livery, paints quick marks ("this is a number", "this is a sponsor"), refines
 * include/exclude regions, watches the segmentation update live, then either
 * PROTECTS the decals on render or builds editable ZONES (a Paint zone they can
 * finish while numbers/sponsors stay protected — the selling feature for a
 * PSD-less buyer).
 *
 * Self-contained vanilla JS. Injected modal (#ssStudioModal) appended to body,
 * shown/hidden via display — same shell pattern as paint-booth-8-autoseparate.js.
 * NO page-wide MutationObserver (that broke live preview before). It reuses the
 * existing SmartSep state/methods (run, canvasBlob, applyProtect, redraw) and the
 * app's window.shokkTraceImportZones / encodeRegionMaskRLE for zone creation, and
 * a trimmed private copy of _paintRegionCircleAt for brush dabs.
 * ========================================================================== */
(function () {
  'use strict';
  if (window.SmartSepStudio && window.SmartSepStudio.__installed) return;

  var ST = window.SmartSepStudio = window.SmartSepStudio || {};
  ST.__installed = true;

  var STUDIO_W = 768, STUDIO_H = 768;
  var N = STUDIO_W * STUDIO_H;

  // --- live state ----------------------------------------------------------
  ST.mode = 'auto';            // auto | numbers | sponsors | include | exclude
  ST.brush = 36;               // brush radius-ish size 3..300
  ST.hardness = 0.7;           // 0..1
  ST.sens = 1.0;               // mirrors SmartSep.sens
  ST.numSize = 1.0;            // mirrors SmartSep.numSize
  ST.live = false;             // live-refine on stroke
  ST.erase = false;            // global erase toggle (right-click also erases)
  ST.activeLayer = null;       // include/exclude target: numbers|sponsors|paint
  ST.makeDecalZones = false;   // "make decal zones too" checkbox

  // mask buffers (Uint8Array, 0..255 at 768²)
  ST.numbers_hint = null;
  ST.sponsors_hint = null;
  ST.include = null;
  ST.exclude = null;
  ST.seg = null;               // {numbers,sponsors,paint} Uint8Array each

  // internals
  var _built = false;
  var _gen = 0;                // drop-stale-response counter (mirrors SmartSep.run)
  var _refineTimer = null;
  var _undo = [];
  var _redo = [];
  var _lastAutoSeg = null;     // snapshot of seg after last Auto Sort (for Reset)
  var _drawing = false;
  var _lastPt = null;
  var _keyHandler = null;

  function $(id) { return document.getElementById(id); }
  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
  function pct(x) { return Math.round((Number(x) || 0) * 100); }
  function newMask() { return new Uint8Array(N); }

  // ---------------------------------------------------------------------------
  // BRUSH — trimmed private copy of _paintRegionCircleAt (paint-booth-3-canvas.js
  // ~1580). Round, soft falloff via gaussian sigma; union (max) for paint,
  // subtractive for erase. Operates on a 768² Uint8Array.
  // ---------------------------------------------------------------------------
  function _paintCircle(mask, x, y, radius, value, opacity, hardness) {
    x = x | 0; y = y | 0; radius = Math.max(1, radius | 0);
    var r2 = radius * radius;
    var sigma = radius * (1.0 - hardness) * 0.5;
    var sigma2x2 = 2.0 * sigma * sigma;
    var hard = (hardness >= 0.99 && opacity >= 0.99);
    var w = STUDIO_W, h = STUDIO_H;
    for (var dy = -radius; dy <= radius; dy++) {
      var py = y + dy; if (py < 0 || py >= h) continue;
      for (var dx = -radius; dx <= radius; dx++) {
        var dist2 = dx * dx + dy * dy;
        if (dist2 > r2) continue;
        var px = x + dx; if (px < 0 || px >= w) continue;
        var idx = py * w + px;
        if (hard) {
          mask[idx] = value ? 255 : 0;
        } else if (value === 0) {
          var dist0 = Math.sqrt(dist2);
          var fall0 = sigma > 0.5 ? Math.exp(-(dist0 * dist0) / sigma2x2) : (dist0 <= radius ? 1.0 : 0.0);
          var cur = mask[idx] / 255.0;
          mask[idx] = Math.round(Math.max(0, cur - fall0 * opacity) * 255);
        } else {
          var dist = Math.sqrt(dist2);
          var fall = sigma > 0.5 ? Math.exp(-(dist * dist) / sigma2x2) : (dist <= radius ? 1.0 : 0.0);
          mask[idx] = Math.max(mask[idx], Math.round(fall * opacity * 255));
        }
      }
    }
  }

  // ---------------------------------------------------------------------------
  // MASK <-> DATAURL helpers (white-on-black PNG, 768²). Pattern from the
  // lightbox tint loop (getImageData -> per-pixel -> putImageData / toDataURL).
  // ---------------------------------------------------------------------------
  function maskToDataURL(u8, w, h) {
    w = w || STUDIO_W; h = h || STUDIO_H;
    var cv = document.createElement('canvas'); cv.width = w; cv.height = h;
    var ctx = cv.getContext('2d', { willReadFrequently: true });
    var img = ctx.createImageData(w, h);
    var d = img.data;
    for (var i = 0, j = 0; i < u8.length; i++, j += 4) {
      var v = u8[i];
      d[j] = v; d[j + 1] = v; d[j + 2] = v; d[j + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    return cv.toDataURL('image/png');
  }

  // Decode an image dataURL into a 768² Uint8Array (threshold on luminance).
  function imgToMask(dataURL, cb) {
    var im = new Image();
    im.onload = function () {
      try {
        var cv = document.createElement('canvas'); cv.width = STUDIO_W; cv.height = STUDIO_H;
        var ctx = cv.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(im, 0, 0, STUDIO_W, STUDIO_H);
        var d = ctx.getImageData(0, 0, STUDIO_W, STUDIO_H).data;
        var out = newMask();
        for (var i = 0, j = 0; i < out.length; i++, j += 4) {
          out[i] = d[j] > 110 ? 255 : 0;   // white-on-black PNG -> binary
        }
        cb(out);
      } catch (e) { cb(newMask()); }
    };
    im.onerror = function () { cb(newMask()); };
    im.src = dataURL;
  }

  // Threshold a soft mask to a hard 0/255 copy.
  function thresholded(u8, thr) {
    thr = thr == null ? 110 : thr;
    var out = newMask();
    for (var i = 0; i < u8.length; i++) out[i] = u8[i] > thr ? 255 : 0;
    return out;
  }

  // ---------------------------------------------------------------------------
  // OVERLAY — rebuild #ssOverlayCanvas from ST.seg: numbers->(255,60,60),
  // sponsors->(60,120,255), paint->transparent. Cheap at 768².
  // ---------------------------------------------------------------------------
  function rebuildOverlay() {
    var cv = $('ssOverlayCanvas'); if (!cv || !ST.seg) return;
    var ctx = cv.getContext('2d', { willReadFrequently: true });
    var img = ctx.createImageData(STUDIO_W, STUDIO_H);
    var d = img.data;
    var nums = ST.seg.numbers, spons = ST.seg.sponsors;
    for (var i = 0, j = 0; i < N; i++, j += 4) {
      if (nums && nums[i] > 110) { d[j] = 255; d[j + 1] = 60; d[j + 2] = 60; d[j + 3] = 190; }
      else if (spons && spons[i] > 110) { d[j] = 60; d[j + 1] = 120; d[j + 2] = 255; d[j + 3] = 190; }
      else { d[j + 3] = 0; }
    }
    ctx.putImageData(img, 0, 0);
  }

  function updateChips() {
    var total = N, n = 0, s = 0, p = 0;
    if (ST.seg) {
      var nums = ST.seg.numbers, spons = ST.seg.sponsors;
      for (var i = 0; i < total; i++) {
        if (nums && nums[i] > 110) n++;
        else if (spons && spons[i] > 110) s++;
        else p++;
      }
    }
    var el = $('ssChips');
    if (el) {
      el.innerHTML =
        '<span style="background:#2a1414;color:#ff7a7a;border-radius:999px;padding:3px 11px;">Numbers ' + pct(n / total) + '%</span>' +
        '<span style="background:#141e2a;color:#8ab8ff;border-radius:999px;padding:3px 11px;">Sponsors ' + pct(s / total) + '%</span>' +
        '<span style="background:#102014;color:#9affb0;border-radius:999px;padding:3px 11px;">Paint ' + pct(p / total) + '%</span>';
    }
  }

  // ---------------------------------------------------------------------------
  // UNDO / REDO — snapshot {seg + 4 hint buffers}. Cap ~20.
  // ---------------------------------------------------------------------------
  function snapshot() {
    return {
      seg: ST.seg ? { numbers: ST.seg.numbers.slice(), sponsors: ST.seg.sponsors.slice(), paint: ST.seg.paint.slice() } : null,
      numbers_hint: ST.numbers_hint.slice(),
      sponsors_hint: ST.sponsors_hint.slice(),
      include: ST.include.slice(),
      exclude: ST.exclude.slice()
    };
  }
  function pushUndo() {
    _undo.push(snapshot());
    if (_undo.length > 20) _undo.shift();
    _redo.length = 0;
    refreshUndoButtons();
  }
  function restore(snap) {
    if (!snap) return;
    ST.seg = snap.seg ? { numbers: snap.seg.numbers.slice(), sponsors: snap.seg.sponsors.slice(), paint: snap.seg.paint.slice() } : ST.seg;
    ST.numbers_hint = snap.numbers_hint.slice();
    ST.sponsors_hint = snap.sponsors_hint.slice();
    ST.include = snap.include.slice();
    ST.exclude = snap.exclude.slice();
    rebuildOverlay(); updateChips();
  }
  ST.undo = function () {
    if (!_undo.length) return;
    _redo.push(snapshot());
    restore(_undo.pop());
    refreshUndoButtons();
  };
  ST.redo = function () {
    if (!_redo.length) return;
    _undo.push(snapshot());
    restore(_redo.pop());
    refreshUndoButtons();
  };
  function refreshUndoButtons() {
    var u = $('ssUndo'), r = $('ssRedo');
    if (u) u.disabled = !_undo.length;
    if (r) r.disabled = !_redo.length;
  }

  // ---------------------------------------------------------------------------
  // SEED seg from SmartSep.result.masks (decode PNGs -> 768 -> threshold).
  // If no result, leave nulls and trigger an Auto Sort.
  // ---------------------------------------------------------------------------
  function seedSegFromResult(done) {
    var R = window.SmartSep && window.SmartSep.result;
    if (!R || !R.detected || !R.masks) { done(false); return; }
    var seg = { numbers: newMask(), sponsors: newMask(), paint: newMask() };
    var pending = 3;
    function fin() { if (--pending === 0) { ST.seg = seg; recomputePaint(); done(true); } }
    imgToMask(R.masks.numbers, function (m) { seg.numbers = m; fin(); });
    imgToMask(R.masks.sponsors, function (m) { seg.sponsors = m; fin(); });
    imgToMask(R.masks.paint, function (m) { seg.paint = m; fin(); });
  }

  // paint = everything NOT numbers and NOT sponsors (kept consistent locally).
  function recomputePaint() {
    if (!ST.seg) return;
    var nums = ST.seg.numbers, spons = ST.seg.sponsors, paint = ST.seg.paint;
    for (var i = 0; i < N; i++) {
      paint[i] = (nums[i] > 110 || spons[i] > 110) ? 0 : 255;
    }
  }

  function segFromMasks(masks, done) {
    var seg = { numbers: newMask(), sponsors: newMask(), paint: newMask() };
    var pending = 3;
    function fin() { if (--pending === 0) { recomputePaintInto(seg); done(seg); } }
    imgToMask(masks.numbers, function (m) { seg.numbers = m; fin(); });
    imgToMask(masks.sponsors, function (m) { seg.sponsors = m; fin(); });
    imgToMask(masks.paint, function (m) { seg.paint = m; fin(); });
  }
  function recomputePaintInto(seg) {
    for (var i = 0; i < N; i++) seg.paint[i] = (seg.numbers[i] > 110 || seg.sponsors[i] > 110) ? 0 : 255;
  }

  // ---------------------------------------------------------------------------
  // AUTO SORT — full pass via SmartSep.run (which posts the canvas blob to
  // /api/auto-separate-livery). We sync sens/numSize first, then re-seed seg.
  // ---------------------------------------------------------------------------
  ST.autoSort = function () {
    if (!window.SmartSep) return;
    window.SmartSep.sens = ST.sens;
    window.SmartSep.numSize = ST.numSize;
    setStatus('Auto-sorting…');
    // SmartSep.run is async + calls redraw on the host panel; poll its result.
    var myGen = ++_gen;
    var before = window.SmartSep.result;
    try { window.SmartSep.run(); } catch (e) { setStatus('Auto sort failed'); return; }
    var tries = 0;
    var poll = setInterval(function () {
      if (myGen !== _gen) { clearInterval(poll); return; }
      var R = window.SmartSep.result;
      if (R !== before || (R && R.detected) || window.SmartSep.status.indexOf('Failed') === 0) {
        if (window.SmartSep.busy) { if (++tries > 60) clearInterval(poll); return; }
        clearInterval(poll);
        if (!R || !R.detected) { setStatus(window.SmartSep.status || 'Nothing separated — raise Sensitivity.'); return; }
        seedSegFromResult(function (ok) {
          if (!ok) { setStatus('Auto sort: could not read masks'); return; }
          // clear hints after a fresh auto pass
          ST.numbers_hint = newMask(); ST.sponsors_hint = newMask();
          ST.include = newMask(); ST.exclude = newMask();
          _lastAutoSeg = { numbers: ST.seg.numbers.slice(), sponsors: ST.seg.sponsors.slice(), paint: ST.seg.paint.slice() };
          _undo.length = 0; _redo.length = 0; refreshUndoButtons();
          rebuildOverlay(); updateChips();
          setStatus('✓ auto-sorted');
        });
      } else if (++tries > 80) { clearInterval(poll); setStatus('Auto sort timed out'); }
    }, 120);
  };

  // ---------------------------------------------------------------------------
  // REFINE — POST the current marks to /api/smart-separate/refine. Drops stale
  // responses via the generation counter. On 404/fail it keeps the local overlay
  // and never throws (offline-preview behaviour).
  // ---------------------------------------------------------------------------
  function _refine() {
    if (ST.mode === 'auto') return;
    var src = $('ssSourceCanvas'); if (!src) return;
    var myGen = ++_gen;
    setStatus('Refining…');
    var payload = {
      image: src.toDataURL('image/png'),
      preview_size: 768,
      sensitivity: ST.sens,
      number_size: ST.numSize,
      active_layer: ST.activeLayer || null,
      number_hint: maskToDataURL(ST.numbers_hint),
      sponsor_hint: maskToDataURL(ST.sponsors_hint),
      include_mask: maskToDataURL(ST.include),
      exclude_mask: maskToDataURL(ST.exclude),
      base_masks: {
        numbers: maskToDataURL(ST.seg ? ST.seg.numbers : newMask()),
        sponsors: maskToDataURL(ST.seg ? ST.seg.sponsors : newMask()),
        paint: maskToDataURL(ST.seg ? ST.seg.paint : newMask())
      }
    };
    fetch('/api/smart-separate/refine', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (r) {
      if (!r.ok) throw new Error('http ' + r.status);
      return r.json();
    }).then(function (j) {
      if (myGen !== _gen) return;                  // superseded
      if (!j || !j.success || !j.masks) throw new Error((j && j.error) || 'refine failed');
      segFromMasks(j.masks, function (seg) {
        if (myGen !== _gen) return;
        pushUndo();
        ST.seg = seg;
        // write the refined result back so the launcher summary + protect path see it
        if (window.SmartSep) {
          window.SmartSep.result = {
            detected: !!j.detected,
            overlay: j.overlay || (window.SmartSep.result && window.SmartSep.result.overlay) || null,
            masks: j.masks,
            fractions: j.fractions || null
          };
        }
        rebuildOverlay(); updateChips();
        setStatus('✓ refined');
      });
    }).catch(function () {
      if (myGen !== _gen) return;
      // offline / route missing — keep the local (mark-driven) overlay
      setStatus('offline preview — Auto Sort to commit');
    });
  }

  function refineMaybe(force) {
    if (ST.mode === 'auto') return;
    clearTimeout(_refineTimer);
    if (ST.live && !force) {
      _refineTimer = setTimeout(_refine, 350);
    } else if (force) {
      _refine();
    }
  }

  // ---------------------------------------------------------------------------
  // POINTER / STROKE handling on #ssStageWrap. Maps CSS px -> studio px via the
  // stage rect, interpolates dabs between points, routes to the active buffer.
  // ---------------------------------------------------------------------------
  function stagePoint(ev) {
    var wrap = $('ssStageWrap'); if (!wrap) return null;
    var rect = wrap.getBoundingClientRect();
    var sx = STUDIO_W / rect.width, sy = STUDIO_H / rect.height;
    return {
      x: clamp(Math.round((ev.clientX - rect.left) * sx), 0, STUDIO_W - 1),
      y: clamp(Math.round((ev.clientY - rect.top) * sy), 0, STUDIO_H - 1)
    };
  }

  function activeBuffers() {
    // returns {buf, mirror} — mirror is the seg layer to OR into for instant feedback
    switch (ST.mode) {
      case 'numbers': return { buf: ST.numbers_hint, mirror: ST.seg && ST.seg.numbers };
      case 'sponsors': return { buf: ST.sponsors_hint, mirror: ST.seg && ST.seg.sponsors };
      case 'include': return { buf: ST.include, mirror: null };
      case 'exclude': return { buf: ST.exclude, mirror: null };
      default: return null;
    }
  }

  function dabAt(x, y, erasing) {
    var ab = activeBuffers(); if (!ab) return;
    var radius = Math.round(ST.brush / 2);
    var val = erasing ? 0 : 255;
    _paintCircle(ab.buf, x, y, radius, val, 0.95, ST.hardness);
    if (ab.mirror) _paintCircle(ab.mirror, x, y, radius, val, 0.95, ST.hardness);
    // Mark-mode strokes also clear the other seg layer + paint for clean feedback
    if (!erasing && ST.seg && (ST.mode === 'numbers' || ST.mode === 'sponsors')) {
      var other = ST.mode === 'numbers' ? ST.seg.sponsors : ST.seg.numbers;
      _paintCircle(other, x, y, radius, 0, 0.95, ST.hardness);
      _paintCircle(ST.seg.paint, x, y, radius, 0, 0.95, ST.hardness);
      ST.activeLayer = ST.mode;
    }
  }

  function strokeBetween(a, b, erasing) {
    if (!a) { dabAt(b.x, b.y, erasing); return; }
    var dist = Math.hypot(b.x - a.x, b.y - a.y);
    var step = Math.max(1, Math.round(ST.brush / 4));
    var n = Math.max(1, Math.ceil(dist / step));
    for (var i = 1; i <= n; i++) {
      var t = i / n;
      dabAt(Math.round(a.x + (b.x - a.x) * t), Math.round(a.y + (b.y - a.y) * t), erasing);
    }
  }

  function onDown(ev) {
    if (ST.mode === 'auto') return;
    ev.preventDefault();
    var p = stagePoint(ev); if (!p) return;
    pushUndo();
    _drawing = true;
    var erasing = ST.erase || ev.button === 2;
    _lastPt = null;
    strokeBetween(_lastPt, p, erasing);
    _lastPt = p;
    rebuildOverlay();
    drawCursor(p.x, p.y);
  }
  // OWNER 2026-06-28: drawing felt "jinky" because rebuildOverlay() (a full 768²
  // ImageData pass) ran on EVERY pointermove. Coalesce overlay repaints to one per
  // animation frame so the stroke stays smooth at 60fps.
  var _ovPending = false;
  function scheduleOverlay() {
    if (_ovPending) return;
    _ovPending = true;
    (window.requestAnimationFrame || function (f) { return setTimeout(f, 16); })(function () {
      _ovPending = false; rebuildOverlay();
    });
  }
  function onMove(ev) {
    var p = stagePoint(ev); if (!p) return;
    drawCursor(p.x, p.y);
    if (!_drawing) return;
    var erasing = ST.erase || ev.buttons === 2;
    strokeBetween(_lastPt, p, erasing);
    _lastPt = p;
    scheduleOverlay();
  }
  var _livePvTimer = null;
  function onUp() {
    if (!_drawing) return;
    _drawing = false; _lastPt = null;
    updateChips();
    // commit a refine pass (immediate unless Live, which debounced during stroke)
    refineMaybe(!ST.live);
    // OWNER 2026-06-28: drawing should change the LIVE PREVIEW. Debounced push of the
    // current marks through the proven protect->preview path so the main preview reflects
    // what you just drew (numbers/sponsors kept) without any extra click.
    clearTimeout(_livePvTimer);
    _livePvTimer = setTimeout(function () { try { if (ST.seg && typeof ST.protect === 'function') ST.protect(); } catch (e) {} }, 400);
  }
  function onLeave() { clearCursor(); }

  function drawCursor(x, y) {
    var cv = $('ssBrushCanvas'); if (!cv) return;
    var ctx = cv.getContext('2d');
    ctx.clearRect(0, 0, STUDIO_W, STUDIO_H);
    if (ST.mode === 'auto') return;
    var radius = Math.round(ST.brush / 2);
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = (ST.erase) ? 'rgba(255,51,102,0.9)'
      : ST.mode === 'numbers' ? 'rgba(255,80,80,0.95)'
        : ST.mode === 'sponsors' ? 'rgba(90,150,255,0.95)'
          : ST.mode === 'include' ? 'rgba(0,229,255,0.95)' : 'rgba(255,170,0,0.95)';
    ctx.stroke();
  }
  function clearCursor() {
    var cv = $('ssBrushCanvas'); if (cv) cv.getContext('2d').clearRect(0, 0, STUDIO_W, STUDIO_H);
  }

  function setStatus(t) { var el = $('ssStatus'); if (el) el.textContent = t || ''; ST.status = t || ''; }

  // ---------------------------------------------------------------------------
  // MODE / TOOL setters (wired from inline handlers built in the markup).
  // ---------------------------------------------------------------------------
  ST.setMode = function (m) {
    ST.mode = m;
    if (m === 'numbers' || m === 'sponsors') ST.activeLayer = m;
    var tabs = document.querySelectorAll('[data-ssmode]');
    for (var i = 0; i < tabs.length; i++) {
      var on = tabs[i].getAttribute('data-ssmode') === m;
      tabs[i].style.background = on ? 'linear-gradient(135deg,#00e5ff,#7c4dff)' : '#161a26';
      tabs[i].style.color = on ? '#04121a' : '#9aa3b2';
      tabs[i].style.fontWeight = on ? '800' : '600';
    }
    clearCursor();
  };
  ST.setBrush = function (v) { ST.brush = clamp(parseInt(v, 10) || 36, 3, 300); var l = $('ssBrushV'); if (l) l.textContent = ST.brush + 'px'; };
  ST.setHardness = function (v) { ST.hardness = clamp((parseInt(v, 10) || 70) / 100, 0, 1); var l = $('ssHardV'); if (l) l.textContent = Math.round(ST.hardness * 100) + '%'; };
  ST.setSens = function (v) { ST.sens = clamp((parseInt(v, 10) || 100) / 100, 0.3, 2.0); var l = $('ssSensV'); if (l) l.textContent = ST.sens.toFixed(1) + '×'; if (ST.live) refineMaybe(); };
  ST.setNumSize = function (v) { ST.numSize = clamp((parseInt(v, 10) || 100) / 100, 0.4, 2.5); var l = $('ssNumV'); if (l) l.textContent = ST.numSize.toFixed(1) + '×'; if (ST.live) refineMaybe(); };
  ST.setLive = function (on) { ST.live = !!on; };
  ST.setErase = function (on) { ST.erase = !!on; var b = $('ssErase'); if (b) { b.style.background = on ? '#2a0f18' : '#161a26'; b.style.color = on ? '#ff3366' : '#9aa3b2'; } };
  ST.setMakeDecalZones = function (on) { ST.makeDecalZones = !!on; };
  ST.setOverlayOpacity = function (v) { var cv = $('ssOverlayCanvas'); if (cv) cv.style.opacity = String(clamp((parseInt(v, 10) || 100) / 100, 0, 1)); };
  ST.toggleSecondary = function () {
    var box = $('ssSecondary'); if (!box) return;
    var open = box.style.display !== 'none';
    box.style.display = open ? 'none' : 'block';
    var car = $('ssSecCaret'); if (car) car.textContent = open ? '▸' : '▾';
  };

  ST.reSort = function () { ST.autoSort(); }; // re-run incorporates synced sliders; marks still drive _refine

  ST.reset = function () {
    pushUndo();
    ST.numbers_hint = newMask(); ST.sponsors_hint = newMask();
    ST.include = newMask(); ST.exclude = newMask();
    if (_lastAutoSeg) {
      ST.seg = { numbers: _lastAutoSeg.numbers.slice(), sponsors: _lastAutoSeg.sponsors.slice(), paint: _lastAutoSeg.paint.slice() };
    }
    rebuildOverlay(); updateChips();
    setStatus('reset to last auto');
  };

  // ---------------------------------------------------------------------------
  // OUTPUT: PROTECT — upscale seg to the SOURCE resolution, hand white-on-black
  // PNG masks to SmartSep.result, applyProtect() (unions numbers+sponsors), then
  // kick the live preview.
  // ---------------------------------------------------------------------------
  function upscaledMaskDataURL(u8, dstW, dstH) {
    // nearest-neighbour upscale 768² mask -> dstW x dstH white-on-black PNG
    var cv = document.createElement('canvas'); cv.width = dstW; cv.height = dstH;
    var ctx = cv.getContext('2d', { willReadFrequently: true });
    var img = ctx.createImageData(dstW, dstH);
    var d = img.data;
    for (var y = 0; y < dstH; y++) {
      var sy = Math.min(STUDIO_H - 1, (y * STUDIO_H / dstH) | 0);
      for (var x = 0; x < dstW; x++) {
        var sx = Math.min(STUDIO_W - 1, (x * STUDIO_W / dstW) | 0);
        var v = u8[sy * STUDIO_W + sx] > 110 ? 255 : 0;
        var j = (y * dstW + x) * 4;
        d[j] = v; d[j + 1] = v; d[j + 2] = v; d[j + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    return cv.toDataURL('image/png');
  }

  ST.protect = function () {
    if (!ST.seg || !window.SmartSep) { setStatus('Auto Sort first.'); return; }
    var src = $('paintCanvas');
    var dstW = (src && src.width) ? src.width : 2048;
    var dstH = (src && src.height) ? src.height : 2048;
    setStatus('Building protect mask…');
    var masks = {
      numbers: upscaledMaskDataURL(ST.seg.numbers, dstW, dstH),
      sponsors: upscaledMaskDataURL(ST.seg.sponsors, dstW, dstH),
      paint: upscaledMaskDataURL(ST.seg.paint, dstW, dstH)
    };
    // ensure SmartSep treats this as a detected result, then run its proven union
    window.SmartSep.result = {
      detected: true,
      overlay: (window.SmartSep.result && window.SmartSep.result.overlay) || null,
      masks: masks,
      fractions: (window.SmartSep.result && window.SmartSep.result.fractions) || null
    };
    try { window.SmartSep.applyProtect(); } catch (e) {}
    try { if (typeof triggerPreviewRender === 'function') triggerPreviewRender(); else if (typeof window.spbKickLivePreview === 'function') window.spbKickLivePreview(); } catch (e) {}
    setStatus('🛡 protected — finishes will keep numbers & sponsors');
  };

  // ---------------------------------------------------------------------------
  // OUTPUT: MAKE ZONES — build a shokkTraceImportZones payload at 768² (Paint
  // always; Numbers/Sponsors when "make decal zones too" is checked). Then close.
  // ---------------------------------------------------------------------------
  ST.makeZones = function () {
    if (!ST.seg) { setStatus('Auto Sort first.'); return; }
    if (typeof window.shokkTraceImportZones !== 'function' || typeof window.encodeRegionMaskRLE !== 'function') {
      setStatus('Zone import not available in this build.'); return;
    }
    var paintT = thresholded(ST.seg.paint);
    var zones = [{ name: 'Paint', base_color: '#ffffff', rle: window.encodeRegionMaskRLE(paintT, STUDIO_W, STUDIO_H) }];
    if (ST.makeDecalZones) {
      var numsT = thresholded(ST.seg.numbers);
      var sponsT = thresholded(ST.seg.sponsors);
      zones.push({ name: 'Numbers', base_color: '#111111', rle: window.encodeRegionMaskRLE(numsT, STUDIO_W, STUDIO_H) });
      zones.push({ name: 'Sponsors', base_color: '#111111', rle: window.encodeRegionMaskRLE(sponsT, STUDIO_W, STUDIO_H) });
    }
    var payload = { width: STUDIO_W, height: STUDIO_H, zones: zones };
    try { window.shokkTraceImportZones(payload); } catch (e) { setStatus('Zone import failed: ' + (e.message || e)); return; }
    ST.close();
  };

  // ---------------------------------------------------------------------------
  // MODAL build / open / close
  // ---------------------------------------------------------------------------
  function modeTab(label, m) {
    return '<button data-ssmode="' + m + '" onclick="SmartSepStudio.setMode(\'' + m + '\')" ' +
      'style="cursor:pointer;border:1px solid #2a2f3a;border-radius:8px;padding:7px 4px;font-size:10px;background:#161a26;color:#9aa3b2;font-weight:600;">' + label + '</button>';
  }
  function actionBtn(label, fn, style) {
    return '<button onclick="' + fn + '" style="cursor:pointer;border:1px solid #2a2f3a;border-radius:8px;padding:8px 6px;font-size:10px;font-weight:700;background:#161a26;color:#cfd5e3;' + (style || '') + '">' + label + '</button>';
  }

  function buildModal() {
    if (_built) return;
    _built = true;
    var m = document.createElement('div');
    m.id = 'ssStudioModal';
    m.style.cssText = 'position:fixed;inset:0;z-index:100000;display:none;background:rgba(4,6,16,0.86);' +
      'backdrop-filter:blur(5px);align-items:center;justify-content:center;font-family:Segoe UI,Arial,sans-serif;';

    var h = '';
    h += '<div style="background:#080818;border:1px solid #2a2f3a;border-radius:16px;width:96%;max-width:1240px;max-height:96vh;' +
      'overflow:hidden;display:flex;flex-direction:column;box-shadow:0 30px 90px rgba(0,0,0,.75);color:#e8eaf0;">';

    // header
    h += '<div style="display:flex;align-items:center;gap:12px;padding:14px 18px;border-bottom:1px solid #1c2130;">' +
      '<strong style="font-size:15px;color:#ffaa00;letter-spacing:.4px;">🪓 Smart Separate Studio</strong>' +
      '<span style="font-size:11px;color:#7080a0;">flat livery → numbers · sponsors · paint</span>' +
      '<span id="ssStatus" style="margin-left:auto;font-size:11px;color:#7080a0;"></span>' +
      '<button onclick="SmartSepStudio.close()" style="background:#161a26;border:1px solid #2a2f3a;color:#cfd5e3;border-radius:8px;padding:6px 13px;cursor:pointer;font-size:12px;">Done ✕</button>' +
      '</div>';

    // body: 2-column
    h += '<div style="display:flex;gap:0;flex:1;min-height:0;">';

    // ---- LEFT: stage ----
    h += '<div style="flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:10px;padding:16px;overflow:auto;background:radial-gradient(ellipse at center,#0c0c20,#060610);">';
    h += '<div id="ssChips" style="display:flex;gap:8px;font-size:10px;"></div>';
    h += '<div id="ssStageWrap" oncontextmenu="return false;" style="position:relative;width:min(72vh,640px);aspect-ratio:1/1;border-radius:12px;overflow:hidden;border:1px solid #2a2f3a;background:#05070a;touch-action:none;cursor:crosshair;">' +
      '<canvas id="ssSourceCanvas" width="768" height="768" style="position:absolute;inset:0;width:100%;height:100%;display:block;"></canvas>' +
      '<canvas id="ssOverlayCanvas" width="768" height="768" style="position:absolute;inset:0;width:100%;height:100%;display:block;opacity:0.7;pointer-events:none;"></canvas>' +
      '<canvas id="ssBrushCanvas" width="768" height="768" style="position:absolute;inset:0;width:100%;height:100%;display:block;pointer-events:none;"></canvas>' +
      '</div>';
    h += '<label style="display:flex;align-items:center;gap:8px;font-size:10px;color:#7080a0;width:min(72vh,640px);">Overlay' +
      '<input type="range" min="0" max="100" value="70" oninput="SmartSepStudio.setOverlayOpacity(this.value)" style="flex:1;accent-color:#00e5ff;"></label>';
    h += '</div>';

    // ---- RIGHT: tools rail ----
    h += '<div style="width:300px;flex:0 0 300px;border-left:1px solid #1c2130;padding:14px 14px 16px;overflow:auto;background:#0a0a18;">';

    // mode tabs
    h += '<div style="font-size:9px;color:#7080a0;letter-spacing:.5px;margin-bottom:6px;">MODE</div>';
    h += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">' +
      modeTab('Auto', 'auto') + modeTab('Mark Numbers', 'numbers') +
      modeTab('Mark Sponsors', 'sponsors') + modeTab('Refine Include', 'include') +
      '</div>';
    h += '<div style="display:grid;grid-template-columns:1fr;gap:6px;margin-top:6px;">' + modeTab('Refine Exclude', 'exclude') + '</div>';

    // brush controls
    h += '<div style="font-size:9px;color:#7080a0;letter-spacing:.5px;margin:14px 0 6px;">BRUSH</div>';
    h += '<label style="display:flex;align-items:center;gap:8px;font-size:10px;color:#7080a0;">Size' +
      '<input type="range" min="3" max="300" value="36" oninput="SmartSepStudio.setBrush(this.value)" style="flex:1;accent-color:#00e5ff;">' +
      '<span id="ssBrushV" style="width:38px;text-align:right;color:#cfd5e3;">36px</span></label>';
    h += '<label style="display:flex;align-items:center;gap:8px;font-size:10px;color:#7080a0;margin-top:6px;">Hardness' +
      '<input type="range" min="0" max="100" value="70" oninput="SmartSepStudio.setHardness(this.value)" style="flex:1;accent-color:#00e5ff;">' +
      '<span id="ssHardV" style="width:38px;text-align:right;color:#cfd5e3;">70%</span></label>';
    h += '<button id="ssErase" onclick="SmartSepStudio.setErase(!SmartSepStudio.erase)" style="cursor:pointer;width:100%;margin-top:8px;border:1px solid #2a2f3a;border-radius:8px;padding:7px 0;font-size:10px;font-weight:700;background:#161a26;color:#9aa3b2;">🩹 Erase (or right-click)</button>';

    // secondary collapsible
    h += '<div onclick="SmartSepStudio.toggleSecondary()" style="cursor:pointer;font-size:9px;color:#7080a0;letter-spacing:.5px;margin:14px 0 6px;user-select:none;"><span id="ssSecCaret">▸</span> ADVANCED (sensitivity / number size)</div>';
    h += '<div id="ssSecondary" style="display:none;">';
    h += '<label style="display:flex;align-items:center;gap:8px;font-size:10px;color:#7080a0;">Sensitivity' +
      '<input type="range" min="30" max="200" value="100" oninput="SmartSepStudio.setSens(this.value)" style="flex:1;accent-color:#7c4dff;">' +
      '<span id="ssSensV" style="width:38px;text-align:right;color:#cfd5e3;">1.0×</span></label>';
    h += '<label style="display:flex;align-items:center;gap:8px;font-size:10px;color:#7080a0;margin-top:6px;">Number size' +
      '<input type="range" min="40" max="250" value="100" oninput="SmartSepStudio.setNumSize(this.value)" style="flex:1;accent-color:#3a7bd5;">' +
      '<span id="ssNumV" style="width:38px;text-align:right;color:#cfd5e3;">1.0×</span></label>';
    h += '<label style="display:flex;align-items:center;gap:6px;font-size:10px;color:#7080a0;margin-top:8px;cursor:pointer;"><input type="checkbox" onchange="SmartSepStudio.setLive(this.checked)"> Live refine on stroke</label>';
    h += '</div>';

    // actions
    h += '<div style="font-size:9px;color:#7080a0;letter-spacing:.5px;margin:14px 0 6px;">ACTIONS</div>';
    h += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">' +
      actionBtn('🪓 Auto Sort', 'SmartSepStudio.autoSort()', 'color:#00e5ff;') +
      actionBtn('↻ Re-sort marks', 'SmartSepStudio.reSort()') +
      actionBtn('⟲ Reset', 'SmartSepStudio.reset()') +
      '<button id="ssUndo" onclick="SmartSepStudio.undo()" disabled style="cursor:pointer;border:1px solid #2a2f3a;border-radius:8px;padding:8px 6px;font-size:10px;font-weight:700;background:#161a26;color:#cfd5e3;">↶ Undo</button>' +
      '</div>';
    h += '<div style="display:grid;grid-template-columns:1fr;gap:6px;margin-top:6px;">' +
      '<button id="ssRedo" onclick="SmartSepStudio.redo()" disabled style="cursor:pointer;border:1px solid #2a2f3a;border-radius:8px;padding:8px 6px;font-size:10px;font-weight:700;background:#161a26;color:#cfd5e3;">↷ Redo</button>' +
      '</div>';

    // output
    h += '<div style="font-size:9px;color:#7080a0;letter-spacing:.5px;margin:16px 0 6px;">OUTPUT</div>';
    h += '<button onclick="SmartSepStudio.protect()" style="cursor:pointer;width:100%;border:1px solid #1a3a26;border-radius:9px;padding:9px 0;font-size:11px;font-weight:800;color:#9affb0;background:#10261a;">🛡 Protect numbers &amp; sponsors</button>';
    h += '<label style="display:flex;align-items:center;gap:6px;font-size:10px;color:#7080a0;margin:10px 0 4px;cursor:pointer;"><input type="checkbox" onchange="SmartSepStudio.setMakeDecalZones(this.checked)"> make decal zones too</label>';
    h += '<button onclick="SmartSepStudio.makeZones()" style="cursor:pointer;width:100%;border:none;border-radius:9px;padding:10px 0;font-size:11px;font-weight:800;color:#04121a;background:linear-gradient(135deg,#00e5ff,#7c4dff);box-shadow:0 4px 14px rgba(0,229,255,.18);">🧩 Make Zones from this</button>';
    h += '<button onclick="SmartSepStudio.close()" style="cursor:pointer;width:100%;margin-top:8px;border:1px solid #2a2f3a;border-radius:9px;padding:8px 0;font-size:11px;font-weight:700;color:#cfd5e3;background:#161a26;">Done</button>';
    h += '<p style="font-size:9px;color:#5a6480;line-height:1.55;margin:12px 0 0;">Tip: <b>Mark</b> a few numbers &amp; sponsors, then <b>Auto Sort</b> or refine — then <b>Make Zones</b> gives you a Paint zone to finish while the decals stay protected.</p>';

    h += '</div>'; // tools rail
    h += '</div>'; // body row
    h += '</div>'; // modal card

    m.innerHTML = h;
    document.body.appendChild(m);

    // background-click closes (only on the dim backdrop, not the card)
    m.addEventListener('click', function (e) { if (e.target === m) ST.close(); });

    // pointer events on the stage wrap
    var wrap = $('ssStageWrap');
    wrap.addEventListener('pointerdown', onDown);
    wrap.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    wrap.addEventListener('pointerleave', onLeave);
  }

  function drawSourceFromPaintCanvas() {
    var src = $('paintCanvas'), dst = $('ssSourceCanvas');
    if (!dst) return;
    var ctx = dst.getContext('2d', { willReadFrequently: true });
    ctx.clearRect(0, 0, STUDIO_W, STUDIO_H);
    if (src && src.width) {
      try { ctx.drawImage(src, 0, 0, STUDIO_W, STUDIO_H); } catch (e) {}
    }
  }

  ST.open = function () {
    buildModal();

    // seed sliders/state from SmartSep
    if (window.SmartSep) {
      ST.sens = window.SmartSep.sens || 1.0;
      ST.numSize = window.SmartSep.numSize || 1.0;
    }
    // init buffers
    ST.numbers_hint = newMask(); ST.sponsors_hint = newMask();
    ST.include = newMask(); ST.exclude = newMask();
    ST.seg = null; _undo.length = 0; _redo.length = 0; _lastAutoSeg = null;

    // draw the livery once
    drawSourceFromPaintCanvas();

    // reflect slider state into the UI
    var sB = $('ssBrushV'); if (sB) sB.textContent = ST.brush + 'px';
    var sH = $('ssHardV'); if (sH) sH.textContent = Math.round(ST.hardness * 100) + '%';
    var sS = $('ssSensV'); if (sS) sS.textContent = ST.sens.toFixed(1) + '×';
    var sN = $('ssNumV'); if (sN) sN.textContent = ST.numSize.toFixed(1) + '×';
    var allRanges = document.querySelectorAll('#ssSecondary input[type=range]');
    if (allRanges[0]) allRanges[0].value = Math.round(ST.sens * 100);
    if (allRanges[1]) allRanges[1].value = Math.round(ST.numSize * 100);

    ST.setMode('auto');
    setStatus('');

    // show
    $('ssStudioModal').style.display = 'flex';

    // attach key handlers
    _keyHandler = function (e) {
      if (e.key === 'Escape' || e.key === 'Esc') { e.preventDefault(); ST.close(); return; }
      var meta = e.ctrlKey || e.metaKey;
      if (meta && (e.key === 'z' || e.key === 'Z')) {
        e.preventDefault();
        if (e.shiftKey) ST.redo(); else ST.undo();
      } else if (meta && (e.key === 'y' || e.key === 'Y')) {
        e.preventDefault(); ST.redo();
      }
    };
    document.addEventListener('keydown', _keyHandler);

    // seed from an existing result, else auto-sort
    seedSegFromResult(function (ok) {
      if (ok) {
        _lastAutoSeg = { numbers: ST.seg.numbers.slice(), sponsors: ST.seg.sponsors.slice(), paint: ST.seg.paint.slice() };
        rebuildOverlay(); updateChips(); refreshUndoButtons();
        setStatus('loaded last separation');
      } else {
        // give the painter an empty stage first, then run a pass
        ST.seg = { numbers: newMask(), sponsors: newMask(), paint: newMask() };
        recomputePaint(); rebuildOverlay(); updateChips();
        ST.autoSort();
      }
    });
  };

  ST.close = function () {
    // write summary back to SmartSep so the launcher reflects the latest state
    if (window.SmartSep) {
      window.SmartSep.sens = ST.sens;
      window.SmartSep.numSize = ST.numSize;
    }
    var m = $('ssStudioModal'); if (m) m.style.display = 'none';
    if (_keyHandler) { document.removeEventListener('keydown', _keyHandler); _keyHandler = null; }
    clearTimeout(_refineTimer);
    _drawing = false; _lastPt = null;
    try { if (window.SmartSep && typeof window.SmartSep.redraw === 'function') window.SmartSep.redraw(); } catch (e) {}
  };
})();
