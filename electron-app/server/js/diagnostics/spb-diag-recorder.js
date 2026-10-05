/* ============================================================================
 * SHOKKER PAINT BOOTH — Frontend Diagnostics Recorder (spb-diag-recorder.js)
 * ----------------------------------------------------------------------------
 * Purpose: capture everything a non-technical user needs to report a bug, into
 * a capped in-memory ring buffer, WITHOUT changing any app behavior. This is the
 * data source for the one-click "Report a Problem" report builder.
 *
 * It MUST be the FIRST <script> in <head> on every main page so it catches the
 * earliest console output, errors, rejections, and fetches.
 *
 * Hard rules honored here:
 *   - 100% transparent: never swallow console output, never alter fetch
 *     responses / errors / streaming, never break the app.
 *   - Bulletproof: every hook wrapped in try/catch, never throws.
 *   - Idempotent: safe no-op if loaded twice (guarded by window.__SPB_DIAG).
 *   - Privacy: this recorder NEVER reads or stores the license key, AES key,
 *     license secret, or password hashes. Fetch bodies are only captured as a
 *     short, length-capped snippet, and obvious secret-looking values are
 *     redacted from any captured text (see _redact()). The report builder is
 *     responsible for the same redaction on anything else it gathers.
 *
 * Public API (window.__SPB_DIAG):
 *   .getEntries()      -> Array<Entry>   (chronological copy of the ring buffer)
 *   .getErrors()       -> Array<Entry>   (subset: console.error + error + rejection + fetch>=400/fail)
 *   .getBreadcrumbs()  -> Array<Entry>   (subset: clicks + manual breadcrumbs)
 *   .breadcrumb(msg)   -> void           (record a manual breadcrumb)
 *   .info              -> { version, page, href, startedAt, startedAtIso, userAgent, capacity }
 *
 * Also exposed: window.spbDiagBreadcrumb(msg) (same as .breadcrumb).
 *
 * Entry shape (all entries):
 *   {
 *     t:    Number,   // ms since startedAt (monotonic-ish; perf.now based when available)
 *     ts:   String,   // ISO timestamp (wall clock) of capture
 *     type: String,   // 'console' | 'error' | 'rejection' | 'fetch' | 'breadcrumb'
 *     ...type-specific fields (see below)
 *   }
 *
 *   console:    { level:'log'|'info'|'warn'|'error', text:String }
 *   error:      { message, source, line, col, stack }
 *   rejection:  { reason, stack }
 *   fetch:      { url, method, status (Number|null), ok:Boolean, ms:Number,
 *                 failed:Boolean, error:String|null, snippet:String|null }
 *   breadcrumb: { kind:'click'|'manual', text:String }
 * ========================================================================== */
(function () {
  'use strict';

  // ---- Idempotency guard: safe no-op if loaded twice. --------------------
  try {
    if (window.__SPB_DIAG && window.__SPB_DIAG.__installed) {
      return;
    }
  } catch (_e) {
    // If we can't even read window, there's nothing safe to do.
    return;
  }

  var VERSION = '1.0.0';
  var CAPACITY = 600;            // ring buffer cap (drop oldest)
  var SNIPPET_MAX = 600;         // max chars of a captured fetch body snippet
  var TEXT_MAX = 2000;           // max chars for a captured console/error text
  var BREADCRUMB_TEXT_MAX = 120; // max chars for breadcrumb text

  // ---- Time helpers ------------------------------------------------------
  var _hasPerf = false;
  try { _hasPerf = !!(window.performance && typeof window.performance.now === 'function'); } catch (_e) { _hasPerf = false; }
  var START_PERF = _hasPerf ? window.performance.now() : 0;
  var START_WALL = Date.now();

  function _now() {
    try { return _hasPerf ? window.performance.now() : (Date.now() - START_WALL); }
    catch (_e) { return 0; }
  }
  function _rel() {
    try { return Math.round((_now() - START_PERF) * 1000) / 1000; }
    catch (_e) { return 0; }
  }
  function _iso() {
    try { return new Date().toISOString(); }
    catch (_e) { return ''; }
  }

  // ---- Safe string coercion ---------------------------------------------
  function _safeStr(v, max) {
    var s;
    try {
      if (v == null) { s = String(v); }
      else if (typeof v === 'string') { s = v; }
      else if (v instanceof Error) { s = (v.name ? v.name + ': ' : '') + (v.message || ''); }
      else if (typeof v === 'object') {
        try { s = JSON.stringify(v); } catch (_e1) { s = Object.prototype.toString.call(v); }
        if (s == null) { s = String(v); }
      } else { s = String(v); }
    } catch (_e) {
      try { s = Object.prototype.toString.call(v); } catch (_e2) { s = '[unstringifiable]'; }
    }
    if (typeof s !== 'string') { s = ''; }
    var lim = (typeof max === 'number' && max > 0) ? max : TEXT_MAX;
    if (s.length > lim) { s = s.slice(0, lim) + '…[+' + (s.length - lim) + ' chars]'; }
    return s;
  }

  // ---- Privacy redaction -------------------------------------------------
  // Redact secret-looking values from any captured text. This protects against
  // a license key / AES key / secret / password-hash accidentally riding along
  // in a log line, error message, or response body snippet.
  // Ordered redaction rules, applied in sequence. Each rule is its OWN
  // {regex, replacement} so callbacks can't be mismatched across patterns.
  // Bearer runs FIRST: "Authorization: Bearer <token>" must mask the TOKEN
  // (the key:value rule would otherwise consume the word "Bearer" and leave the
  // token exposed). The final high-entropy blob rule catches UNLABELED secrets
  // (raw AES/API keys) that no keyword precedes.
  function _redactBlob(m) {
    // Redact a 32+ char run only if it's mixed alnum (API keys / base64) or
    // pure-hex (AES keys); leave plain words, numbers, and path-ish tokens.
    if ((/[A-Za-z]/.test(m) && /[0-9]/.test(m)) || /^[0-9a-fA-F]{32,}$/.test(m)) { return '[REDACTED]'; }
    return m;
  }
  var _redactRules = [
    // 1. Authorization / Bearer <token>
    { re: /(bearer\s+)([A-Za-z0-9._\-]{8,})/gi, rep: function (m, p1) { return p1 + '[REDACTED]'; } },
    // 2. key:value / key=value for sensitive key names (JSON or query-ish)
    { re: /(["']?(?:license[_-]?key|licensekey|aes[_-]?key|secret|license[_-]?secret|password|passwd|pwd|pass[_-]?hash|password[_-]?hash|token|api[_-]?key|authorization|auth[_-]?token|bearer)["']?\s*[:=]\s*)(["']?)([^"'\s,&}]{4,})\2/gi, rep: function (m, p1, q) { return p1 + (q || '') + '[REDACTED]' + (q || ''); } },
    // 3. SHOKKER-XXXX-XXXX-XXXX license keys
    { re: /\bSHOKKER-[A-Z0-9]{2,}(?:-[A-Z0-9]{2,}){2,}\b/gi, rep: '[REDACTED]' },
    // 4. Unlabeled high-entropy blob (no slashes/dots, so file paths break apart)
    { re: /[A-Za-z0-9+=_\-]{32,}/g, rep: _redactBlob }
  ];
  function _redact(s) {
    if (typeof s !== 'string' || !s) { return s; }
    var out = s;
    try {
      for (var i = 0; i < _redactRules.length; i++) {
        out = out.replace(_redactRules[i].re, _redactRules[i].rep);
      }
    } catch (_e) { /* if redaction blows up, fall back to a blunt scrub */
      try { out = s.replace(/[A-Za-z0-9._\-]{24,}/g, '[REDACTED]'); } catch (_e2) { out = s; }
    }
    return out;
  }

  // ---- Ring buffer -------------------------------------------------------
  var _buf = [];     // array of entries (chronological)
  function _push(entry) {
    try {
      if (!entry || typeof entry !== 'object') { return; }
      entry.t = _rel();
      entry.ts = _iso();
      _buf.push(entry);
      if (_buf.length > CAPACITY) {
        // drop oldest; splice keeps it simple and correct
        _buf.splice(0, _buf.length - CAPACITY);
      }
    } catch (_e) { /* never throw from the recorder */ }
  }

  // ======================================================================
  // 1. CONSOLE WRAPPING (always call original; never swallow).
  // ======================================================================
  (function wrapConsole() {
    try {
      if (!window.console) { return; }
      var levels = ['log', 'info', 'warn', 'error'];
      for (var i = 0; i < levels.length; i++) {
        (function (level) {
          try {
            var orig = window.console[level];
            // Only wrap real functions; keep a reference for original call.
            if (typeof orig !== 'function') { return; }
            var bound = orig;
            window.console[level] = function () {
              // Record first (best-effort), but NEVER let recording break logging.
              try {
                var parts = [];
                for (var a = 0; a < arguments.length; a++) {
                  parts.push(_safeStr(arguments[a], 500));
                }
                _push({
                  type: 'console',
                  level: level,
                  text: _redact(_safeStr(parts.join(' '), TEXT_MAX))
                });
              } catch (_eRec) { /* ignore recording failure */ }
              // ALWAYS call the original, with original args + this.
              try { return bound.apply(this, arguments); }
              catch (_eCall) {
                // As an absolute fallback, try calling without `this`.
                try { return bound.apply(window.console, arguments); } catch (_e2) { return undefined; }
              }
            };
            // Mark so we don't double-wrap if some other layer re-runs.
            try { window.console[level].__spbWrapped = true; } catch (_e) {}
          } catch (_eLevel) { /* skip this level */ }
        })(levels[i]);
      }
    } catch (_e) { /* console wrap failed; app still works */ }
  })();

  // ======================================================================
  // 2. WINDOW 'error' EVENTS.
  // ======================================================================
  (function wrapWindowError() {
    try {
      window.addEventListener('error', function (ev) {
        try {
          // Resource load errors (img/script) have no ev.message; still useful.
          var msg = (ev && ev.message) ? ev.message : 'error event';
          var src = (ev && ev.filename) ? ev.filename : (ev && ev.target && ev.target.src) || null;
          var line = (ev && typeof ev.lineno === 'number') ? ev.lineno : null;
          var col = (ev && typeof ev.colno === 'number') ? ev.colno : null;
          var stack = null;
          try { if (ev && ev.error && ev.error.stack) { stack = String(ev.error.stack); } } catch (_e) {}
          _push({
            type: 'error',
            message: _redact(_safeStr(msg, TEXT_MAX)),
            source: src ? _safeStr(src, 500) : null,
            line: line,
            col: col,
            stack: stack ? _redact(_safeStr(stack, TEXT_MAX)) : null
          });
        } catch (_eRec) { /* ignore */ }
      }, true); // capture phase so resource errors are seen
    } catch (_e) { /* ignore */ }
  })();

  // ======================================================================
  // 3. WINDOW 'unhandledrejection'.
  // ======================================================================
  (function wrapRejection() {
    try {
      window.addEventListener('unhandledrejection', function (ev) {
        try {
          var reason = ev ? ev.reason : undefined;
          var stack = null;
          try { if (reason && reason.stack) { stack = String(reason.stack); } } catch (_e) {}
          _push({
            type: 'rejection',
            reason: _redact(_safeStr(reason, TEXT_MAX)),
            stack: stack ? _redact(_safeStr(stack, TEXT_MAX)) : null
          });
        } catch (_eRec) { /* ignore */ }
      });
    } catch (_e) { /* ignore */ }
  })();

  // ======================================================================
  // 4. FETCH WRAPPING — fully transparent.
  //    Records failures (thrown) and responses with status>=400.
  //    Never alters the response, never breaks streaming, clones before
  //    reading any body snippet, preserves error propagation exactly.
  // ======================================================================
  (function wrapFetch() {
    try {
      if (typeof window.fetch !== 'function') { return; }
      var origFetch = window.fetch;

      function _methodOf(input, init) {
        try {
          if (init && init.method) { return String(init.method).toUpperCase(); }
          if (input && typeof input === 'object' && input.method) { return String(input.method).toUpperCase(); }
        } catch (_e) {}
        return 'GET';
      }
      function _urlOf(input) {
        try {
          if (typeof input === 'string') { return input; }
          if (input && typeof input === 'object') {
            if (typeof input.url === 'string') { return input.url; }    // Request
          }
          return String(input);
        } catch (_e) { return '[unknown-url]'; }
      }
      function _recordFetch(rec) {
        try {
          rec.type = 'fetch';
          if (rec.url) { rec.url = _redact(_safeStr(rec.url, 600)); }
          if (rec.snippet) { rec.snippet = _redact(_safeStr(rec.snippet, SNIPPET_MAX)); }
          if (rec.error) { rec.error = _redact(_safeStr(rec.error, TEXT_MAX)); }
          _push(rec);
        } catch (_e) {}
      }

      window.fetch = function (input, init) {
        var startedAt = _now();
        var method, url;
        try { method = _methodOf(input, init); } catch (_e) { method = 'GET'; }
        try { url = _urlOf(input); } catch (_e) { url = '[unknown-url]'; }

        var p;
        try {
          p = origFetch.apply(this, arguments);
        } catch (_eSync) {
          // Some polyfills could throw synchronously; record then rethrow EXACTLY.
          try {
            _recordFetch({
              url: url, method: method, status: null, ok: false,
              ms: Math.round((_now() - startedAt) * 100) / 100,
              failed: true, error: _safeStr(_eSync, TEXT_MAX), snippet: null
            });
          } catch (_e) {}
          throw _eSync;
        }

        // If the original didn't return a thenable, return it untouched.
        if (!p || typeof p.then !== 'function') { return p; }

        // Attach observation WITHOUT consuming the real response/promise:
        // we return the ORIGINAL promise `p`, and observe via a detached chain.
        try {
          p.then(function (res) {
            try {
              var ms = Math.round((_now() - startedAt) * 100) / 100;
              var status = null, ok = false;
              try { status = (res && typeof res.status === 'number') ? res.status : null; } catch (_e) {}
              try { ok = !!(res && res.ok); } catch (_e) {}

              // Only bother capturing for failures (status >= 400) to keep the
              // buffer signal-rich and avoid touching every success body.
              if (status != null && status >= 400) {
                var snippet = null;
                // Clone BEFORE reading so the app's own res.text()/.json()/stream
                // is never disturbed. If clone/read fails, record without snippet.
                try {
                  if (res && typeof res.clone === 'function') {
                    var c = res.clone();
                    if (c && typeof c.text === 'function') {
                      c.text().then(function (body) {
                        try {
                          _recordFetch({
                            url: url, method: method, status: status, ok: ok, ms: ms,
                            failed: false, error: null,
                            snippet: _safeStr(body, SNIPPET_MAX)
                          });
                        } catch (_e) {}
                      }, function () {
                        // body read failed; record without snippet
                        try {
                          _recordFetch({ url: url, method: method, status: status, ok: ok, ms: ms, failed: false, error: null, snippet: null });
                        } catch (_e) {}
                      });
                      return; // recording happens in the .text() callbacks
                    }
                  }
                } catch (_eClone) { /* fall through to record without snippet */ }
                _recordFetch({ url: url, method: method, status: status, ok: ok, ms: ms, failed: false, error: null, snippet: snippet });
              }
            } catch (_eThen) { /* ignore observation errors */ }
          }, function (err) {
            // Network/thrown error path.
            try {
              var ms2 = Math.round((_now() - startedAt) * 100) / 100;
              _recordFetch({
                url: url, method: method, status: null, ok: false, ms: ms2,
                failed: true, error: _safeStr(err, TEXT_MAX), snippet: null
              });
            } catch (_e) {}
          });
          // (Rejection from our DETACHED observation chain is already handled by
          // the onRejected arg passed to .then above — no extra catch is needed and
          // we never create a second "unhandledrejection". The original `p` is untouched.)
        } catch (_eObserve) { /* observation setup failed; ignore */ }

        // Return the ORIGINAL promise untouched — caller sees identical behavior.
        return p;
      };
      try { window.fetch.__spbWrapped = true; } catch (_e) {}
    } catch (_e) { /* fetch wrap failed; app still works */ }
  })();

  // ======================================================================
  // 5. BREADCRUMBS — clicks + public manual API.
  // ======================================================================
  function _recordBreadcrumb(kind, text) {
    try {
      _push({
        type: 'breadcrumb',
        kind: kind === 'click' ? 'click' : 'manual',
        text: _redact(_safeStr(text, BREADCRUMB_TEXT_MAX))
      });
    } catch (_e) {}
  }

  (function wrapClicks() {
    try {
      document.addEventListener('click', function (ev) {
        try {
          var el = ev && ev.target;
          if (!el || typeof el.closest !== 'function') { return; }
          var hit = el.closest('button, [role="button"], .btn');
          if (!hit) { return; }
          var label = '';
          try {
            label = (hit.getAttribute && (hit.getAttribute('aria-label') || hit.getAttribute('title'))) || '';
            if (!label) { label = hit.textContent || ''; }
            label = String(label).replace(/\s+/g, ' ').trim();
          } catch (_e) { label = ''; }
          if (!label) {
            try { label = '#' + (hit.id || hit.className || hit.tagName || 'button'); } catch (_e) { label = 'button'; }
          }
          _recordBreadcrumb('click', label);
        } catch (_eRec) { /* ignore */ }
      }, true); // capture so we see clicks even if app stops propagation
    } catch (_e) { /* ignore */ }
  })();

  // ======================================================================
  // PUBLIC API
  // ======================================================================
  function _copyMatching(pred) {
    var out = [];
    try {
      for (var i = 0; i < _buf.length; i++) {
        var e = _buf[i];
        if (!e) { continue; }
        if (!pred || pred(e)) {
          // shallow clone so callers can't mutate the buffer
          try { out.push(_shallow(e)); } catch (_eC) { out.push(e); }
        }
      }
    } catch (_e) {}
    return out;
  }
  function _shallow(o) {
    var c = {};
    for (var k in o) { if (Object.prototype.hasOwnProperty.call(o, k)) { c[k] = o[k]; } }
    return c;
  }

  var api = {
    __installed: true,
    info: {
      version: VERSION,
      page: (function () { try { return (location.pathname || '').split('/').pop() || location.pathname || ''; } catch (_e) { return ''; } })(),
      href: (function () { try { return location.href || ''; } catch (_e) { return ''; } })(),
      startedAt: START_WALL,
      startedAtIso: (function () { try { return new Date(START_WALL).toISOString(); } catch (_e) { return ''; } })(),
      userAgent: (function () { try { return (navigator && navigator.userAgent) || ''; } catch (_e) { return ''; } })(),
      capacity: CAPACITY
    },
    getEntries: function () { return _copyMatching(null); },
    getErrors: function () {
      return _copyMatching(function (e) {
        if (e.type === 'error' || e.type === 'rejection') { return true; }
        if (e.type === 'console' && e.level === 'error') { return true; }
        if (e.type === 'fetch' && (e.failed === true || (typeof e.status === 'number' && e.status >= 400))) { return true; }
        return false;
      });
    },
    getBreadcrumbs: function () {
      return _copyMatching(function (e) { return e.type === 'breadcrumb'; });
    },
    breadcrumb: function (msg) { _recordBreadcrumb('manual', msg); },
    // Internal escape hatch for the report builder (not part of the contract):
    _clear: function () { try { _buf.length = 0; } catch (_e) {} }
  };

  // Install on window. Wrap in try/catch; never throw.
  try { window.__SPB_DIAG = api; } catch (_e) {}
  try {
    window.spbDiagBreadcrumb = function (msg) {
      try { api.breadcrumb(msg); } catch (_e2) {}
    };
  } catch (_e) {}

  // First breadcrumb: recorder online.
  try { _recordBreadcrumb('manual', 'diag recorder online v' + VERSION); } catch (_e) {}
})();
