"""[SPB-PERF1 2026-10-09] PERF-BOOT lane: load-path speed-ups that cannot change any render, finish or engine output.

ONE kill switch (server side): env SPB_PERF1_OFF=1 restores the exact old behaviour (no URL stamps, no long cache,
every request logged). The client half of the same switch is window.SPB_PERF1_OFF / localStorage SPB_PERF1_OFF='1'.

Why (measured on the owner's machine class, 2026-10-09, warm cache, 199 scripts + 46 stylesheets):
  * Every JS/CSS file was served `Cache-Control: no-cache`, so each boot made ~250 conditional requests. The Werkzeug dev
    server answers one every ~20 ms (new TCP connection each, requests effectively serial) = ~4.2 s of the 6.6 s boot.
  * Each of those requests also wrote 2 log lines (stderr + the rotating server log).
Fix (1): paint-booth-v2.html is served with a content stamp on every local .js/.css URL (`&_p=<mtime>-<size>`). A stamped URL
changes whenever the file changes, so it can be cached for a year (`immutable`) and an edit can never be served stale: the HTML
itself stays `no-store`, so the next page load carries the new stamp. Un-stamped URLs (lazy loaders, tools) keep `no-cache`.
Fix (2): successful (2xx/3xx) GETs of static assets are no longer written to the request log (errors and slow hits still are).
"""
import logging
import os
import re

PERF1_OFF = os.environ.get('SPB_PERF1_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on')

# src="..." / href="..." pointing at a local .js/.css (no scheme, no leading //, no data:)
_ASSET_RE = re.compile(r'''(\b(?:src|href)=")([^"?#:\s]+\.(?:js|css))(\?[^"#]*)?(")''')
_LONG_CACHE = 'public, max-age=31536000, immutable'
_STATIC_EXT = ('.js', '.css', '.png', '.svg', '.ico', '.webp', '.jpg', '.jpeg', '.gif', '.woff', '.woff2', '.map')


def _stamp_for(rel, dirs):
    rel = rel.lstrip('/')
    if '..' in rel.replace('\\', '/').split('/'):
        return None
    for d in dirs:
        try:
            st = os.stat(os.path.join(d, rel))
        except OSError:
            continue
        return '%x-%x' % (st.st_mtime_ns // 1000000, st.st_size)
    return None


def stamp_html(html, dirs):
    """Append `_p=<mtime>-<size>` to every local script/stylesheet URL in the served HTML. No-op when the switch is off."""
    if PERF1_OFF or not html:
        return html
    cache = {}

    def sub(m):
        rel = m.group(2)
        if rel not in cache:
            cache[rel] = _stamp_for(rel, dirs)
        st = cache[rel]
        if not st:
            return m.group(0)
        q = m.group(3) or ''
        q = (q + '&' if q else '?') + '_p=' + st
        return m.group(1) + rel + q + m.group(4)

    try:
        return _ASSET_RE.sub(sub, html)
    except Exception:
        return html          # never break the page over an optimisation


def long_cache_header(filename, args):
    """Cache-Control value for a stamped .js/.css request, or None (caller keeps its old header)."""
    if PERF1_OFF or not filename.endswith(('.js', '.css')):
        return None
    try:
        p = args.get('_p')
    except Exception:
        return None
    if p and re.fullmatch(r'[0-9a-f]+-[0-9a-f]+', p):
        return _LONG_CACHE
    return None


class _QuietStaticAccess(logging.Filter):
    """Drop werkzeug's per-request line for successful static-asset GETs (a boot is ~250 of them; each is 2 log writes)."""
    # werkzeug colours the request line: "\x1b[36mGET /js/x.js?v=1 HTTP/1.1\x1b[0m" 304 -
    _RX = re.compile(r'"(?:\x1b\[[0-9;]*m)?GET /[^" ?]*\.(?:js|css|png|svg|ico|webp|jpg|jpeg|gif|woff2?|map)(?:\?[^" ]*)? HTTP/[0-9.]+(?:\x1b\[[0-9;]*m)?" [23]\d\d\b')

    def filter(self, record):
        try:
            return not self._RX.search(record.getMessage())
        except Exception:
            return True


_installed = False


def install_quiet_static_log():
    global _installed
    if PERF1_OFF or _installed:
        return False
    _installed = True
    logging.getLogger('werkzeug').addFilter(_QuietStaticAccess())
    return True
