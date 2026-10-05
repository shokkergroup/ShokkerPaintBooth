'use strict';

/*
 * SHOKKER-IZE (MEGA FEATURE 2) — "⚡ Shokker-ize this paint".
 *
 * One click sends the CURRENTLY LOADED paint to POST /api/shokkerize, which
 * auto-generates an angle-reactive color-shift spec map from the art's OWN
 * geometry (winner physics: M~252 / clearcoat flat 255 / gloss-floor + lanes).
 * The returned spec is applied best-effort as the global Layer-0 spec map and a
 * preview render is triggered.
 *
 * CURRENT-PAINT SOURCING (the fix):
 *   The paintable image is NOT always a .tga on disk. When a PSD is loaded the
 *   paint is a composited/flattened RASTER held in the live canvas — there is no
 *   sibling .tga, so deriving one from the PSD filename produced a bogus path
 *   ("... PSD.tga not found"). We now mirror the MAIN RENDER FLOW
 *   (paint-booth-5-api-render.js doRender): grab the live composite canvas via
 *   window.buildLivePaintCompositeCanvas() (falls back to #paintCanvas) and POST
 *   the actual pixels as base64. The server already accepts JSON {image:<dataURI>}.
 *   Only when there is a genuine on-disk paint path AND no live-canvas source do
 *   we fall back to sending {paint_file:<path>} so the server can read it fresh.
 *
 * ENTRY POINT: this feature is opened from a TOOLBAR DROPDOWN (not the Settings/
 * Options menu, and not a floating FAB). It mutates no page chrome on load; the
 * dropdown item calls window.SPBShokkerize.open() (alias: shokkerizeCurrentPaint).
 *
 * Flag guard: set window.SPB_SHOKKERIZE_DISABLE = true before load to no-op.
 */

(function () {
  if (window.__spbShokkerizeInit) return;
  window.__spbShokkerizeInit = true;
  if (window.SPB_SHOKKERIZE_DISABLE) return;

  function toast(msg, isError) {
    if (typeof window.showToast === 'function') {
      try { window.showToast(msg, !!isError); return; } catch (e) {}
    }
    // last-resort visibility
    try { console[isError ? 'error' : 'log']('[shokkerize] ' + msg); } catch (e) {}
  }

  // The Source Paint path in the header bar. May point at a PSD/PNG/etc. (which
  // has NO sibling .tga) — we only trust it as a server-readable source when it
  // is a real on-disk path AND there is no live-canvas raster to prefer.
  function currentPaintPath() {
    var el = document.getElementById('paintFile');
    var v = (el && el.value ? el.value : '').trim().replace(/^"+|"+$/g, '');
    return v;
  }

  function looksLikeDiskPath(p) {
    return !!p && (p.indexOf('/') !== -1 || p.indexOf('\\') !== -1 || /^[a-zA-Z]:/.test(p));
  }

  // The visible/working paint raster — exactly what the live preview and the
  // main render flow use. For PSD loads this is the flattened composite; for
  // flat loads it is the canvas; it also includes user edits. Returns a canvas
  // or null.
  function liveCompositeCanvas() {
    try {
      if (typeof window !== 'undefined' && typeof window.buildLivePaintCompositeCanvas === 'function') {
        var c = window.buildLivePaintCompositeCanvas();
        if (c && c.width > 0 && c.height > 0) return c;
      }
    } catch (e) {}
    var pc = document.getElementById('paintCanvas');
    if (pc && pc.width > 0 && pc.height > 0) return pc;
    return null;
  }

  // Convert a canvas to a base64 PNG data URI. Prefer the app's async helper
  // (toBlob, faster + no main-thread stall); fall back to toDataURL.
  function canvasToDataUri(canvas) {
    if (typeof window !== 'undefined' && typeof window.canvasToBase64Async === 'function') {
      try { return window.canvasToBase64Async(canvas); } catch (e) {}
    }
    if (typeof canvasToBase64Async === 'function') {
      try { return canvasToBase64Async(canvas); } catch (e) {}
    }
    return new Promise(function (resolve, reject) {
      try { resolve(canvas.toDataURL('image/png')); } catch (e) { reject(e); }
    });
  }

  // Build the POST body that points the server at the REAL current paint.
  // Returns a Promise<object|null>. null => nothing usable is loaded.
  function buildPaintBody(preset) {
    var intensity = getIntensity();
    preset = preset || _activePreset || 'balanced';

    // 1) PREFERRED: the live composite raster (PSD composite / flat canvas /
    //    edited pixels). This is the source of truth the renderer itself uses
    //    and is correct whether or not a .tga exists on disk.
    var canvas = liveCompositeCanvas();
    if (canvas) {
      return Promise.resolve(canvasToDataUri(canvas)).then(function (dataUri) {
        if (dataUri) return { image: dataUri, intensity: intensity, preset: preset };
        // canvas existed but encoding failed — fall through to disk path below.
        var p = currentPaintPath();
        if (looksLikeDiskPath(p)) return { paint_file: p, intensity: intensity, preset: preset };
        return null;
      });
    }

    // 2) FALLBACK: a genuine on-disk paint path (e.g. a .tga the user typed in
    //    before any canvas exists). Never a guessed .tga next to a PSD.
    var path = currentPaintPath();
    if (looksLikeDiskPath(path)) {
      return Promise.resolve({ paint_file: path, intensity: intensity, preset: preset });
    }
    return Promise.resolve(null);
  }

  function getIntensity() {
    var el = document.getElementById('shokkerizeIntensity');
    if (el && el.value !== '' && el.value != null) {
      var f = parseFloat(el.value);
      if (!isNaN(f)) return Math.max(0, Math.min(1, f));
    }
    return 1.0;
  }

  // The currently-selected LOOK preset (one of the one-click buttons). Defaults
  // to the proven winner. Set by the preset panel; backward-compatible runs
  // (no panel open) just use this default.
  var _activePreset = 'balanced';

  // Hard-coded fallback so the panel renders even if the presets endpoint is
  // unreachable; the server is the source of truth and overwrites this on load.
  var _PRESET_FALLBACK = [
    { id: 'subtle',   label: 'Subtle Sheen', blurb: 'Gentle satin flash — fine even pearl.' },
    { id: 'balanced', label: 'Balanced',     blurb: 'The crowd-pleaser — winner lanes + lively flake.' },
    { id: 'inferno',  label: 'Inferno',      blurb: 'MAX color-shift — hottest, deepest flake.' },
    { id: 'chrome',   label: 'Chrome Flake', blurb: 'Liquid-chrome mirror — brushed sweeps.' },
    { id: 'ghost',    label: 'Ghost',        blurb: 'Dark phantom — sparse hard pins ignite on movement.' }
  ];

  function fetchPresets() {
    return fetch('/api/shokkerize/presets', { method: 'GET' })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j && j.success && Array.isArray(j.presets) && j.presets.length) return j.presets;
        return _PRESET_FALLBACK;
      })
      .catch(function () { return _PRESET_FALLBACK; });
  }

  // Best-effort: apply the returned spec as the global spec map and re-render.
  function applySpec(data) {
    var applied = false;
    // 1) data-URI hook if the app exposes one (future-proof, no edit needed)
    if (typeof window.setGlobalSpecMapDataUri === 'function') {
      try { window.setGlobalSpecMapDataUri(data.spec_png, 'Shokker-ize', [data.width, data.height]); applied = true; } catch (e) {}
    }
    // 2) fall back to the documented global the renderer reads
    if (!applied) {
      try {
        window.importedSpecMapPath = data.spec_png; // data:image/png;base64,...
        applied = true;
      } catch (e) {}
    }
    if (typeof window.triggerPreviewRender === 'function') {
      try { window.triggerPreviewRender(); } catch (e) {}
    }
    return applied;
  }

  // Always give the owner the result visually, even if auto-apply can't reach
  // the renderer in this build: pop the generated spec in a lightweight viewer.
  function showResultPreview(data) {
    var existing = document.getElementById('shokkerizeResult');
    if (existing) existing.remove();
    var wrap = document.createElement('div');
    wrap.id = 'shokkerizeResult';
    wrap.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:99999;'
      + 'background:#14161a;border:1px solid #2a2f37;border-radius:10px;padding:10px;'
      + 'box-shadow:0 8px 28px rgba(0,0,0,.5);max-width:280px;font:12px/1.4 system-ui,sans-serif;color:#dfe3ea;';
    var s = data.stats || {};
    wrap.innerHTML =
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        + '<b style="color:#7fe1a0;">&#9889; Shokker-ized spec</b>'
        + '<span style="cursor:pointer;color:#8a93a0;" id="shokkerizeClose">&times;</span></div>'
      + '<img src="' + data.spec_png + '" alt="spec" style="width:100%;border-radius:6px;display:block;">'
      + '<div style="margin-top:6px;color:#9aa3b0;">M ' + (s.M_mean != null ? s.M_mean : '?')
        + ' &middot; B ' + (s.B_mean != null ? s.B_mean : '?')
        + ' &middot; lanes ' + (s.G_lane_cov != null ? Math.round(s.G_lane_cov * 100) + '%' : '?')
        + '</div>';
    document.body.appendChild(wrap);
    var c = document.getElementById('shokkerizeClose');
    if (c) c.onclick = function () { wrap.remove(); };
  }

  // Run Shokker-ize with an explicit preset (or the active one). Backward
  // compatible: run() with no arg uses the currently-selected look.
  function run(preset) {
    if (preset) _activePreset = preset;
    return buildPaintBody(preset).then(function (body) {
      if (!body) {
        toast('Load a paint first, then Shokker-ize it.', true);
        return;
      }
      return fetch('/api/shokkerize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: (typeof AbortSignal !== 'undefined' && AbortSignal.timeout) ? AbortSignal.timeout(60000) : undefined,
      })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          if (!res.ok || !res.j || !res.j.success) {
            toast('Shokker-ize failed: ' + ((res.j && res.j.error) || 'unknown'), true);
            return;
          }
          var data = res.j;
          showResultPreview(data);
          var applied = applySpec(data);
          var look = (data.preset || _activePreset || 'balanced');
          toast(applied ? ('⚡ Shokker-ized [' + look + '] — angle-reactive spec applied (Layer 0).')
                        : ('⚡ Spec generated [' + look + '] (see preview, bottom-right).'));
          return data;
        })
        .catch(function (err) { toast('Shokker-ize error: ' + err, true); });
    });
  }

  // ---- VIRAL one-click LOOK panel ---------------------------------------
  // A lightweight floating panel of preset buttons. Click a look -> the live
  // paint is instantly re-shokker-ized with that recipe and re-rendered. This
  // is the "drop any paint, one click, it comes ALIVE" surface.
  function openPanel() {
    var existing = document.getElementById('shokkerizePanel');
    if (existing) { existing.remove(); return; }  // toggle

    var wrap = document.createElement('div');
    wrap.id = 'shokkerizePanel';
    wrap.style.cssText = 'position:fixed;right:16px;top:64px;z-index:99999;'
      + 'background:#14161a;border:1px solid #2a2f37;border-radius:12px;padding:14px;'
      + 'box-shadow:0 10px 34px rgba(0,0,0,.55);width:248px;'
      + 'font:13px/1.45 system-ui,sans-serif;color:#dfe3ea;';
    wrap.innerHTML =
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        + '<b style="color:#7fe1a0;font-size:14px;">&#9889; Shokker-ize</b>'
        + '<span style="cursor:pointer;color:#8a93a0;font-size:18px;line-height:1;" id="shokkerizePanelClose">&times;</span></div>'
      + '<div style="color:#9aa3b0;margin-bottom:10px;">Drop any paint &mdash; one click, it comes alive. Pick a look:</div>'
      + '<div id="shokkerizePresetBtns" style="display:flex;flex-direction:column;gap:7px;"></div>'
      + '<div style="margin-top:10px;display:flex;align-items:center;gap:8px;">'
        + '<label style="color:#9aa3b0;">Intensity</label>'
        + '<input type="range" id="shokkerizeIntensity" min="0" max="1" step="0.05" value="1" style="flex:1;">'
      + '</div>';
    document.body.appendChild(wrap);

    var closeEl = document.getElementById('shokkerizePanelClose');
    if (closeEl) closeEl.onclick = function () { wrap.remove(); };

    var btnHost = document.getElementById('shokkerizePresetBtns');
    fetchPresets().then(function (presets) {
      if (!btnHost) return;
      btnHost.innerHTML = '';
      presets.forEach(function (p) {
        var b = document.createElement('button');
        b.type = 'button';
        b.setAttribute('data-preset', p.id);
        var isActive = (p.id === _activePreset);
        b.style.cssText = 'text-align:left;cursor:pointer;border-radius:9px;padding:8px 10px;'
          + 'border:1px solid ' + (isActive ? '#7fe1a0' : '#2a2f37') + ';'
          + 'background:' + (isActive ? 'rgba(127,225,160,.12)' : '#1b1e24') + ';'
          + 'color:#e7ebf2;transition:border-color .12s,background .12s;';
        b.innerHTML = '<div style="font-weight:600;color:#e7ebf2;">' + p.label + '</div>'
          + '<div style="color:#9aa3b0;font-size:11.5px;margin-top:1px;">' + (p.blurb || '') + '</div>';
        b.onmouseenter = function () { if (p.id !== _activePreset) b.style.borderColor = '#3a4250'; };
        b.onmouseleave = function () { if (p.id !== _activePreset) b.style.borderColor = '#2a2f37'; };
        b.onclick = function () {
          _activePreset = p.id;
          // repaint active state
          Array.prototype.forEach.call(btnHost.children, function (c) {
            var act = c.getAttribute('data-preset') === _activePreset;
            c.style.borderColor = act ? '#7fe1a0' : '#2a2f37';
            c.style.background = act ? 'rgba(127,225,160,.12)' : '#1b1e24';
          });
          b.disabled = true;
          b.style.opacity = '.6';
          Promise.resolve(run(p.id)).then(function () { b.disabled = false; b.style.opacity = '1'; })
            .catch(function () { b.disabled = false; b.style.opacity = '1'; });
        };
        btnHost.appendChild(b);
      });
    });
  }

  // Public entry point — invoked from the toolbar dropdown item.
  // open() now shows the one-click LOOK panel (the viral surface). The bare
  // run() is kept for backward-compat callers that want a one-shot.
  window.shokkerizeCurrentPaint = run;
  window.SPBShokkerize = window.SPBShokkerize || {};
  window.SPBShokkerize.open = openPanel;
  window.SPBShokkerize.panel = openPanel;
  window.SPBShokkerize.run = run;
})();
