/* ============================================================================
 * SHOKKER PAINT BOOTH — One-Click "Report a Problem" Builder (spb-diag-report.js)
 * ----------------------------------------------------------------------------
 * Purpose: turn the in-memory diagnostics captured by spb-diag-recorder.js
 * (window.__SPB_DIAG) PLUS a redacted server snapshot (GET /api/diagnostics)
 * into ONE clean, copy-pasteable PLAIN-TEXT report a NON-technical user can hand
 * to Shokker support. The real driver: SHOKK THE WORLD per-variant 500s happen
 * on the user's machine where the owner can never see them — this surfaces them.
 *
 * Public API (all installed on window):
 *   window.spbBuildDiagnosticReport()  -> Promise<string>  (the full report text)
 *   window.spbReportAProblem(opts)     -> Promise<void>    (build + copy + toast)
 *   window.spbSaveDiagnosticReport()    -> Promise<void>   (build + download .txt)
 *   window.spbInstallReportButton(opts) -> HTMLElement|null (manual button inject)
 *
 * AUTO-WIRING (on DOMContentLoaded / immediately if DOM ready):
 *   - Any element with [data-spb-report-problem] becomes a working trigger.
 *   - Any container with [data-spb-report-slot] gets a styled button injected.
 *   - If neither exists on the page, a small floating "Report a problem"
 *     affordance is added bottom-right so the feature is always reachable.
 *   Opt out of the floating fallback with <body data-spb-report-no-float>.
 *
 * HARD PRIVACY RULES honored here:
 *   - License is surfaced ONLY as a boolean status. We never read or print the
 *     license key, AES key, license secret, or password hashes, and we never
 *     touch spb-license-secrets.json.
 *   - Everything gathered from the page (paths, localStorage, breadcrumbs, log
 *     tails from the server) is run through a redactor that masks secret-looking
 *     values as [REDACTED] before it lands in the report.
 *
 * BULLETPROOF: this file never throws into the app. The report builder always
 * resolves to a string (degrading sections to "(unavailable)" notes on error),
 * and the server fetch failing just adds a graceful note.
 * ========================================================================== */
(function () {
  'use strict';

  // Idempotent: never install twice.
  try {
    if (window.__SPB_DIAG_REPORT && window.__SPB_DIAG_REPORT.__installed) { return; }
  } catch (_e) { return; }

  var REPORT_VERSION = '1.0.0';
  var MAX_REPORT_BYTES = 100 * 1024;     // ~100 KB hard cap on the whole report
  var LOG_TAIL_KEEP_HEAD = 120;          // lines kept from the top of a long tail
  var LOG_TAIL_KEEP_TAIL = 120;          // lines kept from the bottom of a long tail
  var DIAG_FETCH_TIMEOUT_MS = 6000;      // don't hang the report on a dead server

  // localStorage keys worth surfacing in SETTINGS (safe, non-secret prefs only).
  var SETTINGS_KEYS = [
    'spb_picker_mode',
    'shokker_ui_mode',
    'shokker_ui_scale',
    'shokker_autosave',
    'spb_swatch_cache_version'
  ];

  // ----------------------------------------------------------------------
  // Redaction — mirror the recorder's intent so anything WE gather (paths,
  // localStorage, server log tails) is also scrubbed of secret-looking values.
  // ----------------------------------------------------------------------
  // Bearer FIRST (so "Authorization: Bearer <token>" masks the token, not just the
  // word), then labeled key:value secrets, then SHOKKER license keys, then an
  // unlabeled high-entropy blob pass (raw AES/API keys with no preceding keyword) —
  // mirrors the server-side redactor so the copy-pasted report is the last safe net.
  var _bearerRe = /(bearer\s+)([A-Za-z0-9._\-]{8,})/gi;
  var _kvSecretRe = /(["']?(?:license[_-]?key|licensekey|aes[_-]?key|secret|license[_-]?secret|password|passwd|pwd|pass[_-]?hash|password[_-]?hash|token|api[_-]?key|apikey|authorization|auth[_-]?token|bearer|private[_-]?key|credential|salt)["']?\s*[:=]\s*)(["']?)([^"'\s,;&}{]{3,})\2/gi;
  var _licenseKeyRe = /\bSHOKKER-[A-Z0-9]{2,}(?:-[A-Z0-9]{2,}){2,}\b/gi;
  var _blobRe = /[A-Za-z0-9+=_\-]{32,}/g;
  function _redactBlob(m) {
    if ((/[A-Za-z]/.test(m) && /[0-9]/.test(m)) || /^[0-9a-fA-F]{32,}$/.test(m)) { return '[REDACTED]'; }
    return m;
  }

  function _redact(s) {
    if (typeof s !== 'string' || !s) { return s; }
    var out = s;
    try {
      out = out.replace(_bearerRe, function (m, p1) { return p1 + '[REDACTED]'; });
      out = out.replace(_kvSecretRe, function (m, p1, p2) { return p1 + (p2 || '') + '[REDACTED]' + (p2 || ''); });
      out = out.replace(_licenseKeyRe, '[REDACTED]');
      out = out.replace(_blobRe, _redactBlob);
    } catch (_e) {
      // Blunt fallback so a redaction bug can never leak a raw secret.
      try { out = s.replace(/[A-Za-z0-9._\-]{24,}/g, '[REDACTED]'); } catch (_e2) { out = '[REDACTED]'; }
    }
    return out;
  }

  // ----------------------------------------------------------------------
  // Small helpers (all defensive; never throw).
  // ----------------------------------------------------------------------
  function _safe(fn, fallback) {
    try { var v = fn(); return (v === undefined || v === null) ? fallback : v; }
    catch (_e) { return fallback; }
  }
  function _str(v) {
    try {
      if (v === undefined) { return ''; }
      if (v === null) { return ''; }
      if (typeof v === 'string') { return v; }
      return String(v);
    } catch (_e) { return ''; }
  }
  function _trunc(s, max) {
    s = _str(s);
    if (s.length > max) { return s.slice(0, max) + '…[+' + (s.length - max) + ' chars]'; }
    return s;
  }
  function _pad2(n) { return (n < 10 ? '0' : '') + n; }
  function _localStamp(d) {
    try {
      d = d || new Date();
      return d.getFullYear() + '-' + _pad2(d.getMonth() + 1) + '-' + _pad2(d.getDate()) +
        ' ' + _pad2(d.getHours()) + ':' + _pad2(d.getMinutes()) + ':' + _pad2(d.getSeconds());
    } catch (_e) { return ''; }
  }
  function _fileStamp(d) {
    try {
      d = d || new Date();
      return d.getFullYear() + _pad2(d.getMonth() + 1) + _pad2(d.getDate()) + '-' +
        _pad2(d.getHours()) + _pad2(d.getMinutes()) + _pad2(d.getSeconds());
    } catch (_e) { return 'now'; }
  }
  function _hr() { return '----------------------------------------------------------------------'; }
  function _section(title) { return '\n=== ' + title + ' ' + '='.repeat(Math.max(0, 66 - title.length)) + '\n'; }

  // ----------------------------------------------------------------------
  // Section builders. Each returns a string and NEVER throws.
  // ----------------------------------------------------------------------
  function _buildSystem(info) {
    var L = [];
    try {
      var nav = _safe(function () { return navigator; }, {});
      var scr = _safe(function () { return screen; }, {});
      L.push('Page          : ' + _safe(function () { return info.page || location.pathname; }, ''));
      L.push('URL           : ' + _redact(_safe(function () { return info.href || location.href; }, '')));
      L.push('User-Agent    : ' + _str(_safe(function () { return nav.userAgent; }, '')));
      L.push('Platform      : ' + _str(_safe(function () { return nav.platform; }, '')));
      L.push('Language      : ' + _str(_safe(function () { return nav.language; }, '')));
      L.push('Online        : ' + _str(_safe(function () { return nav.onLine; }, '')));
      L.push('CPU cores     : ' + _str(_safe(function () { return nav.hardwareConcurrency; }, 'unknown')));
      L.push('Device memory : ' + _str(_safe(function () { return nav.deviceMemory; }, 'unknown')) + ' GB');
      L.push('Screen        : ' + _str(_safe(function () { return scr.width + ' x ' + scr.height; }, '')) +
        ' @ ' + _str(_safe(function () { return window.devicePixelRatio; }, 1)) + 'x DPR');
      L.push('Window        : ' + _str(_safe(function () { return window.innerWidth + ' x ' + window.innerHeight; }, '')));
      L.push('WebGL GPU     : ' + _str(_webglRenderer()));
      L.push('Recorder      : v' + _str(_safe(function () { return info.version; }, '?')) +
        ' (cap ' + _str(_safe(function () { return info.capacity; }, '?')) + ', started ' +
        _str(_safe(function () { return info.startedAtIso; }, '')) + ')');
    } catch (_e) {
      L.push('(system details unavailable)');
    }
    return L.join('\n');
  }

  function _webglRenderer() {
    try {
      var c = document.createElement('canvas');
      var gl = c.getContext('webgl') || c.getContext('experimental-webgl');
      if (!gl) { return 'no WebGL'; }
      var dbg = gl.getExtension('WEBGL_debug_renderer_info');
      if (dbg) {
        var r = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL);
        var v = gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL);
        return _str(v ? (v + ' — ') : '') + _str(r || 'unknown');
      }
      return _str(gl.getParameter(gl.RENDERER) || 'unknown');
    } catch (_e) { return 'unavailable'; }
  }

  function _buildSettings() {
    var L = [];
    try {
      for (var i = 0; i < SETTINGS_KEYS.length; i++) {
        var k = SETTINGS_KEYS[i];
        var v = _safe(function () { return localStorage.getItem(k); }, null);
        if (v !== null && v !== undefined) {
          L.push(_padKey(k) + ': ' + _redact(_trunc(v, 200)));
        }
      }
      // Body classes reveal the active look/mode (e.g. picker-live).
      var bodyCls = _safe(function () { return document.body && document.body.className; }, '');
      if (bodyCls) { L.push(_padKey('body.class') + ': ' + _trunc(_str(bodyCls).replace(/\s+/g, ' ').trim(), 240)); }
    } catch (_e) { /* ignore */ }
    if (!L.length) { return '(no relevant saved settings found)'; }
    return L.join('\n');
  }
  function _padKey(k) {
    k = _str(k);
    while (k.length < 24) { k += ' '; }
    return k;
  }

  function _buildContext(info) {
    var L = [];
    try {
      L.push('Current page  : ' + _str(_safe(function () { return info.page || location.pathname; }, '')));
      L.push('Current URL   : ' + _redact(_str(_safe(function () { return info.href || location.href; }, ''))));

      // Source paint path (#paintFile in the main app) — redact just in case.
      var paint = _firstFieldValue(['paintFile', 'sourcePath', 'sourceFile']);
      if (paint !== null) { L.push('Source paint  : ' + _redact(_trunc(paint, 400)) || '(empty)'); }

      // iRacing output folder (#outputDir in the main app).
      var outDir = _firstFieldValue(['outputDir', 'outputFolder', 'iracingFolder']);
      if (outDir !== null) { L.push('iRacing folder: ' + (_redact(_trunc(outDir, 400)) || '(empty)')); }

      // Zones: count + short summary (main app keeps a global `zones` array).
      var zoneSummary = _zoneSummary();
      if (zoneSummary) { L.push('Zones         : ' + zoneSummary.count + ' active'); L.push('Zone summary  : ' + zoneSummary.text); }

      // A couple of well-known status lines, if present on the page.
      var statusEl = _safe(function () { return document.getElementById('status'); }, null);
      if (statusEl && statusEl.textContent) { L.push('Page status   : ' + _trunc(_str(statusEl.textContent).replace(/\s+/g, ' ').trim(), 160)); }
      var connPill = _safe(function () { return document.getElementById('connPill'); }, null);
      if (connPill && connPill.textContent) { L.push('Server pill   : ' + _trunc(_str(connPill.textContent).replace(/\s+/g, ' ').trim(), 80)); }
    } catch (_e) {
      L.push('(context details unavailable)');
    }
    if (!L.length) { return '(no page context available)'; }
    return L.join('\n');
  }

  function _firstFieldValue(ids) {
    for (var i = 0; i < ids.length; i++) {
      var el = _safe((function (id) { return function () { return document.getElementById(id); }; })(ids[i]), null);
      if (el && typeof el.value === 'string') { return el.value.trim(); }
      if (el && typeof el.textContent === 'string' && el.tagName !== 'INPUT') { return el.textContent.trim(); }
    }
    return null;
  }

  function _zoneSummary() {
    try {
      var z = (typeof window.zones !== 'undefined') ? window.zones : (typeof zones !== 'undefined' ? zones : null); // eslint-disable-line no-undef
      if (!z || !z.length) { return null; }
      var parts = [];
      for (var i = 0; i < z.length && i < 12; i++) {
        var zone = z[i] || {};
        var name = _str(zone.name || zone.label || zone.id || ('zone ' + (i + 1)));
        var finish = _str(zone.finish || zone.finishName || zone.base || (zone.material && zone.material.name) || '');
        parts.push(finish ? (name + '→' + finish) : name);
      }
      if (z.length > 12) { parts.push('…+' + (z.length - 12) + ' more'); }
      return { count: z.length, text: _trunc(_redact(parts.join(', ')), 600) };
    } catch (_e) { return null; }
  }

  function _formatEntryTime(e) {
    var ts = _str(_safe(function () { return e.ts; }, ''));
    var t = _safe(function () { return e.t; }, null);
    var rel = (t === null) ? '' : ('+' + (Math.round(t) / 1000).toFixed(2) + 's');
    return (ts ? ts : '') + (rel ? (' (' + rel + ')') : '');
  }

  function _buildRecentErrors() {
    var entries = _safe(function () { return window.__SPB_DIAG.getErrors(); }, []);
    if (!entries || !entries.length) { return '(no errors or failed requests captured in this session — nice!)'; }
    var L = [];
    // Newest LAST per spec — getErrors is already chronological (oldest->newest).
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i] || {};
      var head = '[' + (i + 1) + '] ' + _formatEntryTime(e) + '  ' + _str(e.type).toUpperCase();
      L.push(head);
      try {
        if (e.type === 'fetch') {
          L.push('    ' + _str(e.method || 'GET') + ' ' + _redact(_str(e.url)));
          L.push('    status=' + _str(e.status === null ? 'FAILED' : e.status) +
            ' ok=' + _str(e.ok) + ' ms=' + _str(e.ms) + (e.failed ? ' (network/throw)' : ''));
          if (e.error) { L.push('    error: ' + _redact(_trunc(e.error, 1000))); }
          if (e.snippet) { L.push('    body: ' + _indent(_redact(_trunc(e.snippet, 1200)))); }
        } else if (e.type === 'error') {
          L.push('    ' + _redact(_trunc(e.message, 1000)));
          if (e.source) { L.push('    at ' + _redact(_str(e.source)) + (e.line ? (':' + e.line + (e.col ? (':' + e.col) : '')) : '')); }
          if (e.stack) { L.push('    stack: ' + _indent(_redact(_trunc(e.stack, 1500)))); }
        } else if (e.type === 'rejection') {
          L.push('    reason: ' + _redact(_trunc(e.reason, 1000)));
          if (e.stack) { L.push('    stack: ' + _indent(_redact(_trunc(e.stack, 1500)))); }
        } else if (e.type === 'console') {
          L.push('    ' + _redact(_trunc(e.text, 1200)));
        } else {
          L.push('    ' + _redact(_trunc(JSON.stringify(e), 1000)));
        }
      } catch (_e) {
        L.push('    (could not format this entry)');
      }
      L.push('');
    }
    return L.join('\n').replace(/\n+$/, '');
  }
  function _indent(s) {
    return _str(s).split('\n').map(function (line, idx) { return idx === 0 ? line : ('        ' + line); }).join('\n');
  }

  function _buildBreadcrumbs() {
    var crumbs = _safe(function () { return window.__SPB_DIAG.getBreadcrumbs(); }, []);
    if (!crumbs || !crumbs.length) { return '(no recent actions recorded)'; }
    var L = [];
    // Keep this readable: only the most recent ~40 actions.
    var start = Math.max(0, crumbs.length - 40);
    for (var i = start; i < crumbs.length; i++) {
      var c = crumbs[i] || {};
      var when = _formatEntryTime(c);
      var kind = _str(c.kind || 'manual');
      L.push('• ' + when + '  [' + kind + '] ' + _redact(_trunc(c.text, 160)));
    }
    if (start > 0) { L.unshift('(' + start + ' earlier action(s) trimmed)'); }
    return L.join('\n');
  }

  // ----------------------------------------------------------------------
  // SERVER section — await GET /api/diagnostics; degrade gracefully.
  // ----------------------------------------------------------------------
  function _fetchDiagnostics() {
    return new Promise(function (resolve) {
      var done = false;
      function finish(val) { if (!done) { done = true; resolve(val); } }
      var ctrl = null;
      try { if (typeof AbortController === 'function') { ctrl = new AbortController(); } } catch (_e) { ctrl = null; }
      var timer = null;
      try { timer = setTimeout(function () { try { if (ctrl) { ctrl.abort(); } } catch (_e) {} finish({ error: 'timed out after ' + DIAG_FETCH_TIMEOUT_MS + 'ms' }); }, DIAG_FETCH_TIMEOUT_MS); } catch (_e) {}
      try {
        var opts = { method: 'GET', cache: 'no-store', credentials: 'same-origin' };
        if (ctrl) { opts.signal = ctrl.signal; }
        window.fetch('/api/diagnostics', opts).then(function (res) {
          var status = _safe(function () { return res.status; }, null);
          return res.text().then(function (body) {
            if (timer) { try { clearTimeout(timer); } catch (_e) {} }
            var data = null;
            try { data = JSON.parse(body); } catch (_e) { data = null; }
            if (data) { finish({ status: status, data: data }); }
            else { finish({ status: status, error: 'non-JSON response', raw: _trunc(body, 400) }); }
          }, function (e) {
            if (timer) { try { clearTimeout(timer); } catch (_e2) {} }
            finish({ status: status, error: 'read failed: ' + _str(e) });
          });
        }, function (e) {
          if (timer) { try { clearTimeout(timer); } catch (_e) {} }
          finish({ error: 'request failed: ' + _str(e && e.message ? e.message : e) });
        });
      } catch (e) {
        if (timer) { try { clearTimeout(timer); } catch (_e) {} }
        finish({ error: 'could not start request: ' + _str(e) });
      }
    });
  }

  function _middleTruncateLines(lines, keepHead, keepTail) {
    if (!lines || lines.length <= (keepHead + keepTail)) { return lines || []; }
    var dropped = lines.length - keepHead - keepTail;
    var out = lines.slice(0, keepHead);
    out.push('··· [' + dropped + ' middle line(s) trimmed to keep report small] ···');
    out = out.concat(lines.slice(lines.length - keepTail));
    return out;
  }

  function _buildServer(result) {
    var L = [];
    if (!result || result.error) {
      L.push('Could not reach the local server diagnostics endpoint (/api/diagnostics).');
      L.push('Note: ' + _str(result && result.error ? result.error : 'unknown reason'));
      L.push('This often means the Paint Booth server is not running, or crashed.');
      L.push('That itself may be the bug — please mention what you were doing when it happened.');
      return L.join('\n');
    }
    var d = result.data || {};
    try {
      L.push('Endpoint OK   : ' + _str(d.ok) + '   (HTTP ' + _str(result.status) + ')');
      L.push('App version   : ' + _str(d.app_version));
      L.push('Engine version: ' + _str(d.engine_version));
      L.push('Build id      : ' + _str(d.build_id));
      L.push('Python        : ' + _str(d.python_version));
      var os = d.os || {};
      L.push('Server OS     : ' + _str(os.platform || (_str(os.system) + ' ' + _str(os.release))));
      L.push('PID           : ' + _str(d.pid));
      L.push('Server start  : ' + _str(d.server_start_time));
      L.push('Uptime        : ' + _str(d.uptime_seconds) + ' s');
      L.push('Routes        : ' + _str(d.registered_routes));
      L.push('Licensed      : ' + _str(d.licensed) + '   (status only — key never included)');
      if (d.gpu) { L.push('Server GPU    : ' + _redact(_trunc(_jsonish(d.gpu), 300))); }
      if (d.catalog) { L.push('Catalog       : ' + _trunc(_jsonish(d.catalog), 300)); }
      var lp = d.log_paths || {};
      if (lp.server_log) { L.push('Server log    : ' + _redact(_str(lp.server_log))); }
      if (lp.crash_log) { L.push('Crash log     : ' + _redact(_str(lp.crash_log))); }

      // recent_errors (server-side, already redacted server-side; redact again).
      if (d.recent_errors && d.recent_errors.length) {
        L.push('');
        L.push('Server recent errors (' + d.recent_errors.length + '):');
        for (var i = 0; i < d.recent_errors.length && i < 20; i++) {
          L.push('  • ' + _redact(_trunc(_jsonish(d.recent_errors[i]), 500)));
        }
      }

      // Server endpoint's OWN errors list (partial-failure diagnostics).
      if (d.errors && d.errors.length) {
        L.push('');
        L.push('Diagnostics endpoint partial-failure notes (' + d.errors.length + '):');
        for (var j = 0; j < d.errors.length; j++) { L.push('  • ' + _redact(_trunc(_str(d.errors[j]), 300))); }
      }

      // Log tails — middle-truncated, redact each line again defensively.
      L.push('');
      L.push('--- server_log.txt (tail) ' + _hr().slice(0, 28));
      L.push(_renderLogTail(d.server_log_tail));
      L.push('');
      L.push('--- server_crashes.log (tail) ' + _hr().slice(0, 24));
      L.push(_renderLogTail(d.crash_log_tail));
    } catch (_e) {
      L.push('(server section partly unavailable: ' + _str(_e) + ')');
    }
    return L.join('\n');
  }

  function _renderLogTail(tail) {
    if (!tail || !tail.length) { return '(empty or unavailable)'; }
    var lines;
    try { lines = tail.map(function (ln) { return _redact(_str(ln)); }); }
    catch (_e) { return '(could not render log tail)'; }
    lines = _middleTruncateLines(lines, LOG_TAIL_KEEP_HEAD, LOG_TAIL_KEEP_TAIL);
    return lines.join('\n');
  }

  function _jsonish(v) {
    try {
      if (typeof v === 'string') { return v; }
      return JSON.stringify(v);
    } catch (_e) { return _str(v); }
  }

  // ----------------------------------------------------------------------
  // MAIN: assemble the whole report.
  // ----------------------------------------------------------------------
  function spbBuildDiagnosticReport() {
    return new Promise(function (resolve) {
      var info = _safe(function () { return window.__SPB_DIAG.info; }, {}) || {};
      // Drop a breadcrumb so the report records that it was built.
      try { if (window.__SPB_DIAG && window.__SPB_DIAG.breadcrumb) { window.__SPB_DIAG.breadcrumb('built diagnostic report'); } } catch (_e) {}

      _fetchDiagnostics().then(function (serverResult) {
        var now = new Date();
        var appVersion = _safe(function () {
          return (serverResult && serverResult.data && serverResult.data.app_version) || '';
        }, '');

        var parts = [];
        parts.push('SHOKKER PAINT BOOTH — DIAGNOSTIC REPORT');
        parts.push(_hr());
        parts.push('App version   : ' + (appVersion || '(unknown — server unreachable)'));
        parts.push('Generated     : ' + _localStamp(now) + ' (your local time)');
        parts.push('Report format : v' + REPORT_VERSION);
        parts.push('');
        parts.push('WHAT TO DO: Copy ALL of this text and paste it to Shokker support');
        parts.push('(Discord or email). It contains everything needed to debug your issue.');
        parts.push('It does NOT contain your license key or any password — those are never');
        parts.push('included (license shows only as a true/false status).');

        parts.push(_section('SYSTEM'));
        parts.push(_buildSystem(info));

        parts.push(_section('SETTINGS'));
        parts.push(_buildSettings());

        parts.push(_section('CONTEXT'));
        parts.push(_buildContext(info));

        parts.push(_section('RECENT ERRORS (newest last)'));
        parts.push(_buildRecentErrors());

        parts.push(_section('BREADCRUMBS (recent actions)'));
        parts.push(_buildBreadcrumbs());

        parts.push(_section('SERVER'));
        parts.push(_buildServer(serverResult));

        parts.push('');
        parts.push(_hr());
        parts.push('END OF REPORT — paste everything above to Shokker support. Thank you!');

        var text = parts.join('\n');

        // Final hard size cap (~100 KB). Trim from the MIDDLE so the header and
        // the closing instruction always survive.
        try {
          if (text.length > MAX_REPORT_BYTES) {
            var head = text.slice(0, Math.floor(MAX_REPORT_BYTES * 0.6));
            var tail = text.slice(text.length - Math.floor(MAX_REPORT_BYTES * 0.3));
            text = head + '\n\n··· [report truncated to keep it under ~100 KB] ···\n\n' + tail;
          }
        } catch (_e) { /* leave as-is */ }

        resolve(text);
      }, function () {
        // _fetchDiagnostics never rejects, but be safe.
        resolve('SHOKKER PAINT BOOTH — DIAGNOSTIC REPORT\n' + _hr() +
          '\nGenerated: ' + _localStamp(new Date()) +
          '\n\n(Report builder hit an unexpected error gathering data. Please tell Shokker' +
          '\nsupport what you were doing when the problem happened.)');
      });
    });
  }

  // ----------------------------------------------------------------------
  // Clipboard + toast + download.
  // ----------------------------------------------------------------------
  function _copyToClipboard(text) {
    return new Promise(function (resolve) {
      // Preferred: async clipboard API.
      try {
        if (navigator && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
          navigator.clipboard.writeText(text).then(function () { resolve(true); }, function () { resolve(_execCopyFallback(text)); });
          return;
        }
      } catch (_e) { /* fall through */ }
      resolve(_execCopyFallback(text));
    });
  }
  function _execCopyFallback(text) {
    try {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.top = '-1000px';
      ta.style.left = '-1000px';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try { ta.setSelectionRange(0, ta.value.length); } catch (_e) {}
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (_e) { ok = false; }
      try { document.body.removeChild(ta); } catch (_e) {}
      return !!ok;
    } catch (_e) { return false; }
  }

  // Self-contained toast so the report works identically on EVERY page. We do
  // NOT delegate to the host page's showToast: its second-arg contract differs
  // by page (boolean isError in the main app vs a CSS-class kind string on
  // shokk-drop), so using our own toast keeps styling/behavior consistent and
  // guarantees the toast appears even on pages with no toast system at all.
  function _toast(message, kind) {
    try {
      var host = document.getElementById('__spbDiagToastHost');
      if (!host) {
        host = document.createElement('div');
        host.id = '__spbDiagToastHost';
        host.setAttribute('aria-live', 'polite');
        host.style.cssText = 'position:fixed;z-index:2147483600;bottom:18px;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;gap:8px;pointer-events:none;max-width:92vw;';
        document.body.appendChild(host);
      }
      var t = document.createElement('div');
      var bg = kind === 'error' ? '#3a1414' : (kind === 'warn' ? '#3a2e14' : '#0f2a18');
      var bd = kind === 'error' ? '#6b2a2a' : (kind === 'warn' ? '#6b5a2a' : '#2a6b3a');
      var fg = kind === 'error' ? '#f0b8b8' : (kind === 'warn' ? '#f0e0b8' : '#bff0cf');
      t.style.cssText = 'pointer-events:auto;font:600 13px/1.4 system-ui,Segoe UI,sans-serif;padding:11px 16px;border-radius:9px;box-shadow:0 8px 28px rgba(0,0,0,.45);border:1px solid ' + bd + ';background:' + bg + ';color:' + fg + ';opacity:0;transition:opacity .18s ease;';
      t.textContent = message;
      host.appendChild(t);
      // Force reflow then fade in.
      void t.offsetWidth;
      t.style.opacity = '1';
      setTimeout(function () {
        t.style.opacity = '0';
        setTimeout(function () { try { host.removeChild(t); } catch (_e) {} }, 250);
      }, 4200);
    } catch (_e) { /* a toast failure must never break the flow */ }
  }

  function spbReportAProblem(opts) {
    opts = opts || {};
    return spbBuildDiagnosticReport().then(function (text) {
      return _copyToClipboard(text).then(function (copied) {
        if (copied) {
          _toast('Diagnostics copied — paste it to Shokker support', 'success');
        } else {
          _toast('Could not auto-copy. Use "Save .txt" and send that file to Shokker support.', 'warn');
        }
        // Stash the latest report so a Save button (or console) can reuse it.
        try { window.__SPB_DIAG_REPORT.lastReport = text; } catch (_e) {}
        if (opts.alsoSave) { _downloadReport(text); }
        return text;
      });
    }, function () {
      _toast('Could not build the diagnostics report. Please try again.', 'error');
    });
  }

  function _downloadReport(text) {
    try {
      var name = 'spb-diagnostics-' + _fileStamp(new Date()) + '.txt';
      var blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = name;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      setTimeout(function () {
        try { document.body.removeChild(a); } catch (_e) {}
        try { URL.revokeObjectURL(url); } catch (_e) {}
      }, 1500);
      return true;
    } catch (_e) {
      _toast('Could not save the .txt file.', 'error');
      return false;
    }
  }

  function spbSaveDiagnosticReport() {
    return spbBuildDiagnosticReport().then(function (text) {
      try { window.__SPB_DIAG_REPORT.lastReport = text; } catch (_e) {}
      _downloadReport(text);
      _toast('Saved diagnostics .txt — attach it for Shokker support', 'success');
      return text;
    });
  }

  // ----------------------------------------------------------------------
  // Button UI. A compact "Report a Problem" control (copy) + a "Save .txt".
  // ----------------------------------------------------------------------
  function _makeButtonGroup(opts) {
    opts = opts || {};
    var wrap = document.createElement('span');
    wrap.className = 'spb-report-problem-group';
    wrap.style.cssText = 'display:inline-flex;gap:6px;align-items:center;vertical-align:middle;';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'spb-report-problem-btn' + (opts.btnClass ? (' ' + opts.btnClass) : '');
    btn.textContent = opts.label || 'Report a Problem';
    btn.title = 'Copies "Diagnostics for Support" — a plain-text report you paste to Shokker support so they can fix your issue.';
    btn.setAttribute('aria-label', 'Report a problem — copy diagnostics for Shokker support');
    if (!opts.btnClass) {
      btn.style.cssText = 'display:inline-flex;align-items:center;gap:6px;min-height:30px;padding:0 12px;border-radius:7px;border:1px solid #6b5a2a;background:#241d0c;color:#f0c040;font:700 12px/1 system-ui,Segoe UI,sans-serif;cursor:pointer;';
    }
    btn.addEventListener('click', function () {
      btn.disabled = true;
      var prev = btn.textContent;
      btn.textContent = 'Building…';
      spbReportAProblem().then(function () {
        btn.disabled = false; btn.textContent = prev;
      }, function () {
        btn.disabled = false; btn.textContent = prev;
      });
    });

    var save = document.createElement('button');
    save.type = 'button';
    save.className = 'spb-report-save-btn' + (opts.btnClass ? (' ' + opts.btnClass) : '');
    save.textContent = 'Save .txt';
    save.title = 'Save the diagnostics as a .txt file you can attach in an email or Discord.';
    save.setAttribute('aria-label', 'Save diagnostics as a text file');
    if (!opts.btnClass) {
      save.style.cssText = 'display:inline-flex;align-items:center;min-height:30px;padding:0 10px;border-radius:7px;border:1px solid #2b3645;background:#111925;color:#cdd7e3;font:600 11px/1 system-ui,Segoe UI,sans-serif;cursor:pointer;';
    }
    save.addEventListener('click', function () {
      save.disabled = true;
      var prev = save.textContent;
      save.textContent = 'Saving…';
      spbSaveDiagnosticReport().then(function () {
        save.disabled = false; save.textContent = prev;
      }, function () {
        save.disabled = false; save.textContent = prev;
      });
    });

    wrap.appendChild(btn);
    if (!opts.noSave) { wrap.appendChild(save); }
    return wrap;
  }

  function spbInstallReportButton(opts) {
    opts = opts || {};
    try {
      var target = opts.target;
      if (typeof target === 'string') { target = document.querySelector(target); }
      if (!target) { return null; }
      var group = _makeButtonGroup(opts);
      if (opts.prepend && target.firstChild) { target.insertBefore(group, target.firstChild); }
      else { target.appendChild(group); }
      return group;
    } catch (_e) { return null; }
  }

  function _installFloating() {
    try {
      if (document.getElementById('__spbReportFloat')) { return; }
      var float = document.createElement('div');
      float.id = '__spbReportFloat';
      float.style.cssText = 'position:fixed;z-index:2147483500;right:14px;bottom:14px;';
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = 'Report a problem';
      btn.title = 'Copies "Diagnostics for Support" you can paste to Shokker support.';
      btn.setAttribute('aria-label', 'Report a problem — copy diagnostics for Shokker support');
      btn.style.cssText = 'display:inline-flex;align-items:center;gap:6px;min-height:32px;padding:0 12px;border-radius:18px;border:1px solid #6b5a2a;background:rgba(36,29,12,.92);color:#f0c040;font:700 12px/1 system-ui,Segoe UI,sans-serif;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.4);';
      btn.addEventListener('click', function () {
        btn.disabled = true; var prev = btn.textContent; btn.textContent = 'Building…';
        spbReportAProblem().then(function () { btn.disabled = false; btn.textContent = prev; }, function () { btn.disabled = false; btn.textContent = prev; });
      });
      float.appendChild(btn);
      document.body.appendChild(float);
    } catch (_e) { /* ignore */ }
  }

  // ----------------------------------------------------------------------
  // Auto-wire on DOM ready.
  // ----------------------------------------------------------------------
  function _autoWire() {
    var wiredSomething = false;
    try {
      // 1) Explicit triggers: any [data-spb-report-problem] element.
      var triggers = document.querySelectorAll('[data-spb-report-problem]');
      for (var i = 0; i < triggers.length; i++) {
        (function (el) {
          if (el.__spbReportWired) { return; }
          el.__spbReportWired = true;
          wiredSomething = true;
          el.addEventListener('click', function (ev) {
            try { ev.preventDefault(); } catch (_e) {}
            var save = el.getAttribute('data-spb-report-problem') === 'save';
            if (save) { spbSaveDiagnosticReport(); } else { spbReportAProblem(); }
          });
        })(triggers[i]);
      }
      // 2) Slots: any [data-spb-report-slot] container gets a styled button group.
      var slots = document.querySelectorAll('[data-spb-report-slot]');
      for (var j = 0; j < slots.length; j++) {
        if (slots[j].__spbReportSlotFilled) { continue; }
        slots[j].__spbReportSlotFilled = true;
        var label = slots[j].getAttribute('data-spb-report-label') || 'Report a Problem';
        var btnClass = slots[j].getAttribute('data-spb-report-btn-class') || '';
        spbInstallReportButton({ target: slots[j], label: label, btnClass: btnClass });
        wiredSomething = true;
      }
    } catch (_e) { /* ignore */ }

    // 3) Floating fallback so the feature is ALWAYS reachable, unless the page
    //    already wired a trigger/slot or explicitly opted out.
    try {
      var noFloat = document.body && document.body.hasAttribute('data-spb-report-no-float');
      if (!wiredSomething && !noFloat) { _installFloating(); }
    } catch (_e) { /* ignore */ }
  }

  function _onReady(fn) {
    try {
      if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(fn, 0);
      } else {
        document.addEventListener('DOMContentLoaded', fn, { once: true });
      }
    } catch (_e) { try { setTimeout(fn, 0); } catch (_e2) {} }
  }

  // ----------------------------------------------------------------------
  // Install public API + auto-wire.
  // ----------------------------------------------------------------------
  try {
    window.spbBuildDiagnosticReport = spbBuildDiagnosticReport;
    window.spbReportAProblem = spbReportAProblem;
    window.spbSaveDiagnosticReport = spbSaveDiagnosticReport;
    window.spbInstallReportButton = spbInstallReportButton;
    window.__SPB_DIAG_REPORT = {
      __installed: true,
      version: REPORT_VERSION,
      build: spbBuildDiagnosticReport,
      report: spbReportAProblem,
      save: spbSaveDiagnosticReport,
      install: spbInstallReportButton,
      lastReport: null
    };
  } catch (_e) { /* ignore */ }

  _onReady(_autoWire);
})();
