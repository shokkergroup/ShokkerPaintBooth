/* ============================================================================
 * SHOKKER PAINT BOOTH — Finish Packs Downloader (finish-packs.js)
 * ----------------------------------------------------------------------------
 * Purpose: let a buyer one-click download the premium Finish Packs that did NOT
 * ship inside the installer (they are too large). The Python backend is live:
 *
 *   GET  /api/finish-packs
 *        -> {"status":"ok","packs":[{id,label,sizeMB,installed,enables,url}, ...]}
 *   POST /api/finish-packs/install   body {"id":"<pack id>"}
 *        -> {"status":"ok","id","files","installed":true}            on success
 *        -> {"status":"error","reason":"..."}                        on failure
 *        (downloads ~18MB-1.2GB from GitHub + extracts; can take minutes)
 *
 * Public API (installed on window):
 *   window.openFinishPacksModal()   -> open the modal (builds it on first call)
 *   window.closeFinishPacksModal()  -> hide the modal
 *
 * Conventions matched from the rest of the app:
 *   - API base: ShokkerAPI.baseUrl (which is window.location.origin in Electron);
 *     we fall back to window.location.origin if ShokkerAPI is not ready yet.
 *   - Toasts: window.showToast(msg, isError).
 *   - Styling: reuses the existing .btn / .btn-sm classes plus a small scoped
 *     stylesheet so the panel matches the dark Shokker chrome without touching
 *     any existing ids/classes.
 *
 * BULLETPROOF: this file never throws into the app. Everything is wrapped; a
 * dead server just shows an inline error + a Retry button.
 * ========================================================================== */
(function () {
  'use strict';

  // Idempotent: never install twice.
  try {
    if (window.__SPB_FINISH_PACKS && window.__SPB_FINISH_PACKS.__installed) { return; }
  } catch (_e) { return; }

  var MODAL_ID = 'finishPacksModal';
  var LIST_ID = 'finishPacksList';
  var STYLE_ID = 'finishPacksStyle';
  var BANNER_ID = 'finishPacksBanner';
  // Session flag so the auto-prompt banner shows at most once per app session.
  var BANNER_SEEN_KEY = 'spb_finish_packs_prompted';

  // ----------------------------------------------------------------------
  // Small helpers
  // ----------------------------------------------------------------------

  /** Resolve the API base the same way the rest of the app does. */
  function apiBase() {
    try {
      if (window.ShokkerAPI && typeof window.ShokkerAPI.baseUrl === 'string' && window.ShokkerAPI.baseUrl) {
        return window.ShokkerAPI.baseUrl;
      }
    } catch (_e) { /* fall through */ }
    try { return window.location.origin || ''; } catch (_e2) { return ''; }
  }

  function toast(msg, isError) {
    try { if (typeof window.showToast === 'function') { window.showToast(msg, !!isError); } } catch (_e) { /* ignore */ }
  }

  /** Is a real in-app restart bridge available (Electron)? (7.0.7-restart) */
  function hasRestartBridge() {
    try {
      if (typeof window.spbRestartApp === 'function') { return true; }
      if (window.electronAPI && typeof window.electronAPI.restartApp === 'function') { return true; }
    } catch (_e) { /* ignore */ }
    return false;
  }

  /** Trigger the real app restart (kills Python server + relaunches). */
  function triggerRestart() {
    try {
      if (typeof window.spbRestartApp === 'function') { window.spbRestartApp(); return; }
      if (window.electronAPI && typeof window.electronAPI.restartApp === 'function') { window.electronAPI.restartApp(); return; }
    } catch (_e) { /* ignore */ }
    // Last-ditch fallback for non-Electron contexts: a hard reload won't restart
    // the server, but it's better than nothing.
    try { window.location.reload(); } catch (_e2) { /* ignore */ }
  }

  /** Escape a string for safe insertion as element text content. */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  /** Human-friendly size label from a sizeMB number. */
  function sizeLabel(sizeMB) {
    var n = Number(sizeMB);
    if (!isFinite(n) || n <= 0) { return ''; }
    if (n >= 1024) { return (n / 1024).toFixed(1).replace(/\.0$/, '') + ' GB'; }
    return Math.round(n) + ' MB';
  }

  // ----------------------------------------------------------------------
  // Styles (scoped; injected once)
  // ----------------------------------------------------------------------

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) { return; }
    var css = ''
      + '#' + MODAL_ID + '{position:fixed;inset:0;z-index:13000;display:none;'
      + 'align-items:center;justify-content:center;background:rgba(0,0,0,0.82);}'
      + '#' + MODAL_ID + '.fp-open{display:flex;}'
      + '#' + MODAL_ID + ' .fp-card{width:min(640px,94vw);max-height:88vh;display:flex;flex-direction:column;'
      + 'background:#0d0f18;border:1px solid rgba(0,229,255,0.18);border-radius:14px;overflow:hidden;'
      + 'box-shadow:0 24px 80px rgba(0,0,0,0.6);}'
      + '#' + MODAL_ID + ' .fp-head{display:flex;align-items:center;gap:10px;padding:16px 20px;flex-shrink:0;'
      + 'background:linear-gradient(180deg,#11141f 0%,#0d0f18 100%);border-bottom:1px solid rgba(0,229,255,0.12);}'
      + '#' + MODAL_ID + ' .fp-title{font-size:16px;font-weight:900;letter-spacing:1px;flex:1;'
      + 'background:linear-gradient(90deg,#00e5ff,#ffd166);-webkit-background-clip:text;background-clip:text;'
      + '-webkit-text-fill-color:transparent;}'
      + '#' + MODAL_ID + ' .fp-x{background:transparent;border:none;color:#9fb0c4;font-size:22px;line-height:1;'
      + 'cursor:pointer;padding:2px 8px;border-radius:6px;}'
      + '#' + MODAL_ID + ' .fp-x:hover{color:#fff;background:rgba(255,255,255,0.08);}'
      + '#' + MODAL_ID + ' .fp-sub{padding:10px 20px 0;font-size:11px;color:#8a99ad;flex-shrink:0;}'
      + '#' + MODAL_ID + ' .fp-list{padding:12px 20px 20px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;}'
      + '#' + MODAL_ID + ' .fp-row{display:flex;align-items:center;gap:12px;padding:12px 14px;'
      + 'background:#11141f;border:1px solid rgba(255,255,255,0.06);border-radius:10px;}'
      + '#' + MODAL_ID + ' .fp-info{flex:1;min-width:0;}'
      + '#' + MODAL_ID + ' .fp-label{font-size:13px;font-weight:700;color:#e8eef6;}'
      + '#' + MODAL_ID + ' .fp-meta{font-size:11px;color:#8a99ad;margin-top:2px;}'
      + '#' + MODAL_ID + ' .fp-action{flex-shrink:0;display:flex;flex-direction:column;align-items:flex-end;gap:4px;}'
      + '#' + MODAL_ID + ' .fp-installed{font-size:12px;font-weight:800;color:#33dd88;white-space:nowrap;}'
      // ---- Restart-now success CTA (7.0.7-restart) ----
      + '#' + MODAL_ID + ' .fp-restart-wrap{display:flex;flex-direction:column;align-items:flex-end;gap:6px;max-width:230px;}'
      + '#' + MODAL_ID + ' .fp-restart-note{font-size:11px;color:#33dd88;font-weight:800;text-align:right;line-height:1.3;white-space:normal;}'
      + '#' + MODAL_ID + ' .fp-restart-sub{font-size:10px;color:#ffb84d;text-align:right;line-height:1.3;white-space:normal;}'
      + '#' + MODAL_ID + ' .fp-restart-btn{background:linear-gradient(180deg,#00e5ff,#00a6c4);color:#04121a;'
      + 'border:none;border-radius:8px;font-weight:900;font-size:13px;padding:9px 16px;cursor:pointer;white-space:nowrap;}'
      + '#' + MODAL_ID + ' .fp-restart-btn:hover{filter:brightness(1.08);}'
      + '#' + MODAL_ID + ' .fp-status{font-size:10px;color:#8a99ad;text-align:right;max-width:200px;}'
      + '#' + MODAL_ID + ' .fp-status.fp-err{color:#ff6b6b;}'
      + '#' + MODAL_ID + ' .fp-spin{display:inline-block;width:12px;height:12px;margin-right:6px;vertical-align:-1px;'
      + 'border:2px solid rgba(0,229,255,0.25);border-top-color:#00e5ff;border-radius:50%;animation:fpSpin 0.8s linear infinite;}'
      + '@keyframes fpSpin{to{transform:rotate(360deg);}}'
      + '#' + MODAL_ID + ' .fp-busy{opacity:0.75;cursor:progress;}'
      + '#' + MODAL_ID + ' .fp-empty{padding:24px;text-align:center;color:#8a99ad;font-size:13px;}'
      // ---- First-open auto-prompt banner (7.0.5-uxfix) ----
      + '#' + BANNER_ID + '{position:fixed;left:50%;bottom:22px;transform:translateX(-50%) translateY(20px);'
      + 'z-index:13050;max-width:560px;width:calc(100vw - 40px);opacity:0;pointer-events:none;'
      + 'transition:opacity .3s ease,transform .3s ease;'
      + 'display:flex;align-items:center;gap:14px;padding:14px 16px;'
      + 'background:linear-gradient(180deg,#15233a 0%,#0e1626 100%);'
      + 'border:1px solid rgba(0,229,255,0.35);border-radius:12px;'
      + 'box-shadow:0 18px 48px rgba(0,0,0,0.55),0 0 0 1px rgba(0,0,0,0.4) inset;}'
      + '#' + BANNER_ID + '.fp-banner-show{opacity:1;pointer-events:auto;transform:translateX(-50%) translateY(0);}'
      + '#' + BANNER_ID + ' .fp-banner-ico{font-size:24px;line-height:1;flex-shrink:0;}'
      + '#' + BANNER_ID + ' .fp-banner-body{flex:1;min-width:0;}'
      + '#' + BANNER_ID + ' .fp-banner-title{font-size:13.5px;font-weight:800;color:#eaf2fb;}'
      + '#' + BANNER_ID + ' .fp-banner-sub{font-size:11.5px;color:#9fb4cc;margin-top:3px;line-height:1.35;}'
      + '#' + BANNER_ID + ' .fp-banner-btns{display:flex;align-items:center;gap:8px;flex-shrink:0;}'
      + '#' + BANNER_ID + ' .fp-banner-go{background:linear-gradient(180deg,#00e5ff,#00a6c4);color:#04121a;'
      + 'border:none;border-radius:8px;font-weight:800;font-size:12.5px;padding:9px 14px;cursor:pointer;white-space:nowrap;}'
      + '#' + BANNER_ID + ' .fp-banner-go:hover{filter:brightness(1.08);}'
      + '#' + BANNER_ID + ' .fp-banner-x{background:transparent;border:none;color:#8aa0ba;font-size:20px;'
      + 'line-height:1;cursor:pointer;padding:2px 8px;border-radius:6px;flex-shrink:0;}'
      + '#' + BANNER_ID + ' .fp-banner-x:hover{color:#fff;background:rgba(255,255,255,0.08);}';
    var el = document.createElement('style');
    el.id = STYLE_ID;
    el.textContent = css;
    (document.head || document.documentElement).appendChild(el);
  }

  // ----------------------------------------------------------------------
  // Modal shell (built once)
  // ----------------------------------------------------------------------

  function ensureModal() {
    var existing = document.getElementById(MODAL_ID);
    if (existing) { return existing; }
    ensureStyle();

    var modal = document.createElement('div');
    modal.id = MODAL_ID;
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-label', 'Finish Packs downloader');
    modal.innerHTML = ''
      + '<div class="fp-card">'
      + '  <div class="fp-head">'
      + '    <span class="fp-title">FINISH PACKS</span>'
      + '    <button type="button" class="fp-x" aria-label="Close" data-fp-close>&times;</button>'
      + '  </div>'
      + '  <div class="fp-sub">Premium finish packs are downloaded on demand to keep the installer small. '
      + 'Pick a pack and click Download &mdash; the app fetches it from GitHub and installs it. '
      + 'Restart the app afterward to load new packs.</div>'
      + '  <div class="fp-list" id="' + LIST_ID + '"></div>'
      + '</div>';

    // Close on backdrop click (but not when clicking inside the card).
    modal.addEventListener('click', function (ev) {
      if (ev.target === modal) { closeModal(); }
    });
    // Close button.
    modal.addEventListener('click', function (ev) {
      var t = ev.target;
      if (t && t.closest && t.closest('[data-fp-close]')) { closeModal(); }
    });

    (document.body || document.documentElement).appendChild(modal);
    return modal;
  }

  // ----------------------------------------------------------------------
  // List rendering + install flow
  // ----------------------------------------------------------------------

  function renderLoading() {
    var list = document.getElementById(LIST_ID);
    if (!list) { return; }
    list.innerHTML = '<div class="fp-empty"><span class="fp-spin"></span>Loading finish packs&hellip;</div>';
  }

  function renderError(reason, retryFn) {
    var list = document.getElementById(LIST_ID);
    if (!list) { return; }
    list.innerHTML = '';
    var box = document.createElement('div');
    box.className = 'fp-empty';
    var msg = document.createElement('div');
    msg.style.color = '#ff6b6b';
    msg.style.marginBottom = '10px';
    msg.textContent = 'Could not load finish packs: ' + String(reason || 'unknown error');
    var retry = document.createElement('button');
    retry.type = 'button';
    retry.className = 'btn btn-sm';
    retry.textContent = 'Retry';
    retry.addEventListener('click', retryFn);
    box.appendChild(msg);
    box.appendChild(retry);
    list.appendChild(box);
  }

  /** Build one pack row. */
  function buildRow(pack) {
    var row = document.createElement('div');
    row.className = 'fp-row';
    row.setAttribute('data-fp-id', pack.id);

    var info = document.createElement('div');
    info.className = 'fp-info';
    var label = document.createElement('div');
    label.className = 'fp-label';
    label.textContent = String(pack.label || pack.id || 'Finish Pack');
    var meta = document.createElement('div');
    meta.className = 'fp-meta';
    var sz = sizeLabel(pack.sizeMB);
    meta.textContent = sz ? ('Download size: ' + sz) : 'Downloadable pack';
    info.appendChild(label);
    info.appendChild(meta);

    var action = document.createElement('div');
    action.className = 'fp-action';

    if (pack.installed === true) {
      var badge = document.createElement('div');
      badge.className = 'fp-installed';
      badge.textContent = 'Installed ✓';
      action.appendChild(badge);
    } else {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-sm';
      btn.textContent = 'Download';
      var status = document.createElement('div');
      status.className = 'fp-status';
      status.style.display = 'none';
      btn.addEventListener('click', function () { installPack(pack, row, btn, status); });
      action.appendChild(btn);
      action.appendChild(status);
    }

    row.appendChild(info);
    row.appendChild(action);
    return row;
  }

  function installPack(pack, row, btn, status) {
    if (!pack || !pack.id) { return; }
    // Obvious, non-frozen in-progress state: spinner inside the button itself,
    // a dimmed/disabled look, plus a status line under it. (7.0.5-uxfix)
    btn.disabled = true;
    btn.classList.add('fp-busy');
    btn.innerHTML = '<span class="fp-spin"></span>Downloading…';
    status.className = 'fp-status';
    status.style.display = 'block';
    var szTxt = sizeLabel(pack.sizeMB);
    status.innerHTML = '<span class="fp-spin"></span>Downloading ' + esc(String(pack.label || pack.id))
      + (szTxt ? ' (' + esc(szTxt) + ')' : '') + '&hellip; this can take a few minutes. Keep the app open.';

    var url = apiBase() + '/api/finish-packs/install';
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: pack.id })
    })
      .then(function (res) { return res.json().catch(function () { return { status: 'error', reason: 'bad response from server (HTTP ' + res.status + ')' }; }); })
      .then(function (data) {
        data = data || {};
        if (data.status === 'ok') {
          // Swap the row to a prominent "Restart now" CTA. A plain Ctrl+R page
          // reload does NOT restart the Python server, so the freshly downloaded
          // finishes never register — only a full app restart loads them.
          // (7.0.7-restart)
          var action = row.querySelector('.fp-action');
          if (action) {
            action.innerHTML = '';
            var wrap = document.createElement('div');
            wrap.className = 'fp-restart-wrap';

            var note = document.createElement('div');
            note.className = 'fp-restart-note';
            note.textContent = 'Installed ✓';
            wrap.appendChild(note);

            if (hasRestartBridge()) {
              var sub = document.createElement('div');
              sub.className = 'fp-restart-sub';
              sub.textContent = 'Click Restart now to load these finishes (a page refresh won’t load them).';
              wrap.appendChild(sub);

              var rbtn = document.createElement('button');
              rbtn.type = 'button';
              rbtn.className = 'fp-restart-btn';
              rbtn.textContent = 'Restart now';
              rbtn.addEventListener('click', function () {
                rbtn.disabled = true;
                rbtn.textContent = 'Restarting…';
                triggerRestart();
              });
              wrap.appendChild(rbtn);
            } else {
              // Non-Electron / no bridge fallback: tell them to fully restart.
              var fb = document.createElement('div');
              fb.className = 'fp-restart-sub';
              fb.textContent = 'Fully restart the app to load these finishes (a page refresh won’t load them).';
              wrap.appendChild(fb);
            }
            action.appendChild(wrap);
          }
          toast('Finish pack installed: ' + (pack.label || pack.id) + '. Restart the app to load it.', false);
        } else {
          showRowError(pack, row, btn, status, data.reason || 'install failed');
        }
      })
      .catch(function (err) {
        showRowError(pack, row, btn, status, (err && err.message) ? err.message : 'network error');
      });
  }

  function showRowError(pack, row, btn, status, reason) {
    // Re-enable as a Retry button.
    btn.disabled = false;
    btn.classList.remove('fp-busy');
    btn.innerHTML = '';
    btn.textContent = 'Retry';
    status.className = 'fp-status fp-err';
    status.style.display = 'block';
    status.textContent = String(reason || 'install failed');
    toast('Finish pack failed: ' + (pack.label || pack.id) + ' — ' + String(reason || ''), true);
  }

  function loadPacks() {
    renderLoading();
    var url = apiBase() + '/api/finish-packs';
    fetch(url, { method: 'GET' })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var list = document.getElementById(LIST_ID);
        if (!list) { return; }
        if (!data || data.status !== 'ok' || !Array.isArray(data.packs)) {
          renderError((data && data.error) || 'server returned no packs', loadPacks);
          return;
        }
        if (data.packs.length === 0) {
          list.innerHTML = '<div class="fp-empty">No finish packs are available.</div>';
          return;
        }
        list.innerHTML = '';
        data.packs.forEach(function (pack) {
          try { list.appendChild(buildRow(pack)); } catch (_e) { /* skip a malformed entry */ }
        });
      })
      .catch(function (err) {
        renderError((err && err.message) ? err.message : 'network error', loadPacks);
      });
  }

  // ----------------------------------------------------------------------
  // Open / close
  // ----------------------------------------------------------------------

  function openModal() {
    try {
      var modal = ensureModal();
      modal.classList.add('fp-open');
      // Close the settings dropdown if it is open so the modal is not behind it.
      try {
        var dd = document.getElementById('settingsDropdown');
        if (dd) { dd.style.display = 'none'; }
      } catch (_e) { /* ignore */ }
      loadPacks();
    } catch (e) {
      toast('Could not open Finish Packs: ' + ((e && e.message) || e), true);
    }
  }

  function closeModal() {
    var modal = document.getElementById(MODAL_ID);
    if (modal) { modal.classList.remove('fp-open'); }
  }

  // Esc closes the modal.
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') {
      var modal = document.getElementById(MODAL_ID);
      if (modal && modal.classList.contains('fp-open')) { closeModal(); }
    }
  });

  // ----------------------------------------------------------------------
  // First-open auto-prompt banner
  // ----------------------------------------------------------------------
  // Buyers were seeing EMPTY premium finish categories (Mortal Shokk, etc.) and
  // assuming the app was broken, because the download lived buried in the gear
  // menu. On first paint-booth open we check the manifest and, if ANY pack is
  // missing, surface a prominent, friendly, dismissible banner that opens the
  // existing Finish Packs modal. Shown at most once per session, never if all
  // packs are already installed. (7.0.5-uxfix)

  function dismissBanner() {
    var b = document.getElementById(BANNER_ID);
    if (b) {
      b.classList.remove('fp-banner-show');
      // Remove from the DOM after the fade so it never intercepts clicks.
      setTimeout(function () { try { if (b && b.parentNode) { b.parentNode.removeChild(b); } } catch (_e) {} }, 320);
    }
  }

  function showBanner(missing) {
    if (document.getElementById(BANNER_ID)) { return; }
    ensureStyle();

    // Build a short, friendly name list (first 3 + "& N more").
    var names = missing.map(function (p) { return String(p.label || p.id || '').trim(); })
      .filter(function (n) { return n; });
    var shown = names.slice(0, 3).join(', ');
    var extra = names.length - 3;
    var nameStr = shown + (extra > 0 ? ', & ' + extra + ' more' : '');

    var banner = document.createElement('div');
    banner.id = BANNER_ID;
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Download premium finish packs');
    banner.innerHTML = ''
      + '<div class="fp-banner-ico" aria-hidden="true">📦</div>'
      + '<div class="fp-banner-body">'
      + '  <div class="fp-banner-title">Some premium finish packs aren’t downloaded yet</div>'
      + '  <div class="fp-banner-sub">' + esc(nameStr) + (names.length ? ' ' : '')
      + 'are installed on demand to keep the app small, so those categories look empty until you grab them. Download them now?</div>'
      + '</div>'
      + '<div class="fp-banner-btns">'
      + '  <button type="button" class="fp-banner-go" data-fp-banner-go>Download packs</button>'
      + '  <button type="button" class="fp-banner-x" aria-label="Dismiss" data-fp-banner-x>&times;</button>'
      + '</div>';

    banner.addEventListener('click', function (ev) {
      var t = ev.target;
      if (!t || !t.closest) { return; }
      if (t.closest('[data-fp-banner-go]')) {
        dismissBanner();
        try { openModal(); } catch (_e) { /* ignore */ }
      } else if (t.closest('[data-fp-banner-x]')) {
        dismissBanner();
      }
    });

    (document.body || document.documentElement).appendChild(banner);
    // Force a reflow then add the show class so the slide/fade-in transition runs.
    void banner.offsetWidth;
    banner.classList.add('fp-banner-show');
  }

  /** Check the manifest once per session; prompt if any pack is missing. */
  function maybePromptForPacks() {
    try {
      if (sessionStorage.getItem(BANNER_SEEN_KEY)) { return; }
    } catch (_e) { /* sessionStorage unavailable — fall through, prompt once */ }

    var url = apiBase() + '/api/finish-packs';
    fetch(url, { method: 'GET' })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (!data || data.status !== 'ok' || !Array.isArray(data.packs)) { return; }
        var missing = data.packs.filter(function (p) { return p && p.installed === false; });
        if (missing.length === 0) { return; }  // all installed — stay quiet
        // Mark as prompted so we never nag again this session, even on re-render.
        try { sessionStorage.setItem(BANNER_SEEN_KEY, '1'); } catch (_e) { /* ignore */ }
        showBanner(missing);
      })
      .catch(function () { /* server not ready / offline — silently skip */ });
  }

  function scheduleAutoPrompt() {
    var run = function () { setTimeout(maybePromptForPacks, 1500); };
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', run, { once: true });
    } else {
      run();
    }
  }

  // ----------------------------------------------------------------------
  // Public API
  // ----------------------------------------------------------------------

  window.openFinishPacksModal = openModal;
  window.closeFinishPacksModal = closeModal;
  window.__SPB_FINISH_PACKS = {
    __installed: true,
    open: openModal,
    close: closeModal,
    reload: loadPacks,
    prompt: maybePromptForPacks
  };

  // Kick the one-shot, once-per-session auto-prompt.
  try { scheduleAutoPrompt(); } catch (_e) { /* never let this break the app */ }
})();
