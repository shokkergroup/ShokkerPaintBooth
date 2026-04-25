"""
Shokker Engine v4.0 PRO - Local Server
=======================================
Runs locally alongside Paint Booth UI. No cloud, no uploads.

TABLE OF CONTENTS - Use these line numbers to jump to sections:
================================================================
  SECTION 1: SETUP & STATIC SERVING (L25-L95)
    Flask app, CORS, static file serving, 404 handler
    /thumbnails/<path> static route (immutable cache, pre-baked PNGs)

  SECTION 2: CONFIG, STATUS & LICENSE (L96-L316)
    /status, /config, /license, /build-check, thumbnail logging

  SECTION 3: FINISH DATA API (L317-L710)
    /finish-groups, /api/finish-data, /api/thumbnail-status,
    /api/clear-cache, /api/thumb-regen/<type>/<id>,
    /api/pattern-layer, apply_paint_recolor,
    _build_finish_data_payload, _id_to_display_name

  SECTION 4: SWATCH RENDERING (L711-L1535)
    /api/swatch/<type>/<key>, /swatch/*, _render_swatch_bytes,
    _apply_fallback_gradient, _swatch_placeholder_png,
    _render_pattern_swatch_from_image_path, _prebake_swatches,
    _prebake_spec_patterns, _generate_spec_preview_image,
    _generate_spec_metal_image, _queue_thumbnail_regen,
    _load_thumbnail_manifest, _save_thumbnail_manifest, _get_fn_hash

  SECTION 5: RENDER PIPELINE (L1536-L2230)
    /preview-render, /render, preview_tga, /preview/<job_id>,
    /download/<job_id>, /reset-backup

  SECTION 6: SWATCH ROUTE ALIASES (L2231-L2470)
    /swatch/<base>/<pattern>, /swatch/pattern/<id>,
    /swatch/mono/<id>, /upload-composited-paint

  SECTION 7: FILE & DEPLOY (L2470-L2930)
    /upload-spec-map, /check-file, /browse-files,
    /iracing-cars, /deploy-to-iracing, /config GET/POST

  SECTION 8: CLEANUP & JOBS (L2930-3010)
    /cleanup, auto_cleanup_old_jobs

  SECTION 9: .SHOKK FILE MANAGEMENT (L3010-L3250)
    /api/shokk/* (library-path, list, save, open, delete, preview)

  SECTION 10: EXPORT & UTILITIES (L3250-L3480)
    /export-psd-layers (Photoshop layer ZIP export #21)
    /api/export-spec-channels, /api/blank-canvas, log_message
================================================================
"""

from flask import Flask, request, jsonify, send_file, g
from flask_cors import CORS
import os
import time
import json
import shutil
import logging
import sys
import traceback
import io
import base64
import threading
import hashlib
import re
import uuid
import platform
import gc
from datetime import datetime
from urllib.parse import urlparse
from collections import deque, OrderedDict
from functools import wraps, lru_cache

# Server startup timestamp for uptime tracking
_server_start_time = time.time()

# Server version constants — kept in one place, exposed via headers + endpoints.
# DO NOT change the version strings without updating the build/CHANGELOG.
SPB_VERSION = "6.2.0-alpha"            # Public/UI-facing version
SPB_ENGINE_VERSION = "v6.2 PRO"        # Engine identifier shown in headers
SPB_BUILD_ID = "Gold-to-Platinum"      # Build family marker

# ----------------------------------------------------------------
# NAMED CONSTANTS — replace bare magic numbers throughout the file.
# Documented so future devs know WHY each value was chosen.
# ----------------------------------------------------------------

# Maximum allowed request body size (16 MB). Prevents OOM from
# malicious or accidental multi-gigabyte POSTs.  Base64-encoded
# 2048x2048 RGBA paint images are ~22 MB raw but compress to ~8 MB,
# so 16 MB covers normal use while rejecting absurd payloads.
MAX_CONTENT_LENGTH_BYTES = 16 * 1024 * 1024

# --- Zone parameter bounds ---
# Intensity: 0 = invisible, 100 = full strength (UI slider range)
INTENSITY_MIN = 0
INTENSITY_MAX = 100
INTENSITY_DEFAULT = 100  # Full strength unless user dials it back

# Scale: pattern tile scale. 0.01 = 100x zoom in, 10.0 = very tiled
SCALE_MIN = 0.01
SCALE_MAX = 10.0
SCALE_DEFAULT = 1.0  # 1:1 pattern mapping, no scaling

# Rotation: degrees. 0-360 wraps, but engine accepts any float and
# does modular arithmetic internally, so we clamp loosely.
ROTATION_MIN = -3600.0
ROTATION_MAX = 3600.0
ROTATION_DEFAULT = 0.0

# Pattern opacity: 0.0 = pattern invisible, 1.0 = fully opaque
OPACITY_MIN = 0.0
OPACITY_MAX = 1.0
OPACITY_DEFAULT = 1.0

# Preview scale: fraction of full resolution for live preview.
# 0.0625 = 1/16 (tiny), 1.0 = full res (slow but pixel-perfect)
PREVIEW_SCALE_MIN = 0.0625
PREVIEW_SCALE_MAX = 1.0
PREVIEW_SCALE_DEFAULT = 0.25  # Quarter-res is the sweet spot

# Wear level: 0 = pristine, 100 = maximum damage/patina
WEAR_LEVEL_MIN = 0
WEAR_LEVEL_MAX = 100
WEAR_LEVEL_DEFAULT = 0

# Swatch thumbnail size range
SWATCH_SIZE_MIN = 32
SWATCH_SIZE_MAX = 256
SWATCH_SIZE_DEFAULT = 64

# Night boost: multiplier for spec highlights in dark conditions
NIGHT_BOOST_DEFAULT = 0.7

# Seed: noise seed, any non-negative integer; 51 is the app default
SEED_DEFAULT = 51

# ----------------------------------------------------------------
# VALIDATION HELPERS — reusable bounds-checking for route handlers
# ----------------------------------------------------------------

def _clamp(value, lo, hi, default=None):
    """Clamp a numeric value to [lo, hi]. Return default if value is None."""
    if value is None:
        return default if default is not None else lo
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default if default is not None else lo
    return max(lo, min(hi, v))


def _safe_int(value, default=0):
    """Convert value to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    """Convert value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _validate_zone_required_fields(zone, index):
    """Check that a zone dict has the minimum required fields.
    Returns (ok, error_message) tuple."""
    if not isinstance(zone, dict):
        return False, f"Zone {index}: expected dict, got {type(zone).__name__}"
    if not zone.get("color") and zone.get("color") != 0:
        # color can be a string like "blue" or "everything", or an RGB list
        pass  # color is optional if region_mask is set
    if not zone.get("base") and not zone.get("finish"):
        return False, f"Zone {index} ('{zone.get('name', 'unnamed')}'): must have 'base' or 'finish'"
    return True, ""


def _sanitize_path(raw_path, allowed_roots=None):
    """Normalise a file path and optionally verify it falls under an allowed root.
    Returns (safe_path, error) — error is None on success."""
    if not raw_path or not isinstance(raw_path, str):
        return None, "Empty or non-string path"
    normed = os.path.normpath(os.path.abspath(raw_path))
    # Block path traversal: no .. components after normalisation
    if ".." in normed.split(os.sep):
        return None, "Path traversal detected"
    if allowed_roots:
        real = os.path.realpath(normed)
        if not any(real.startswith(os.path.realpath(r) + os.sep) or real == os.path.realpath(r)
                   for r in allowed_roots):
            return None, "Path outside allowed directories"
    return normed, None


def _is_local_ui_url(raw_url):
    try:
        parsed = urlparse(raw_url or "")
    except Exception:
        return False
    host = (parsed.hostname or "").lower()
    return host in {"127.0.0.1", "localhost"}


def _require_spb_internal_request():
    """Require the local SPB UI marker header for sensitive PSD routes.

    We still allow the user to open arbitrary local iRacing/template PSDs from
    disk, but browser pages on other origins should not be able to poke these
    loopback endpoints and read back PSD composites/layers.
    """
    if request.headers.get("X-Shokker-Internal") != "1":
        return False, "Blocked: missing SPB internal request header"
    for hdr in ("Origin", "Referer"):
        raw = request.headers.get(hdr)
        if raw and not _is_local_ui_url(raw):
            return False, f"Blocked non-local {hdr.lower()}"
    return True, None

# ----------------------------------------------------------------
# HARDENING: extra validators, rate limiter, request log ring,
# memoised registry helpers. All purely additive — existing
# routes can opt-in by calling these helpers explicitly.
# ----------------------------------------------------------------

# Hard ceiling on zone arrays — anything past this is almost
# certainly a runaway script or malicious payload.
MAX_ZONES_PER_REQUEST = 50

# Request body hard limit (separate from Flask's MAX_CONTENT_LENGTH;
# this one is checked manually by routes that need a tighter cap).
MAX_REQUEST_BYTES_HARD = 32 * 1024 * 1024  # 32 MB

# Minimum / maximum iRacing customer IDs we'll accept.
IRACING_ID_MIN_DIGITS = 4
IRACING_ID_MAX_DIGITS = 7

# Per-endpoint rate limit: { (endpoint, ip): deque[timestamps] }
_rate_limit_buckets = {}
_rate_limit_lock = threading.Lock()

# Recent-render ring buffer (most recent first).  Bounded to avoid leaks.
_recent_renders = deque(maxlen=64)
_recent_renders_lock = threading.Lock()

# Recent-error ring buffer for diagnostics endpoint.
_recent_errors = deque(maxlen=32)
_recent_errors_lock = threading.Lock()

# Total request counter — incremented in before_request hook.
_request_counter = 0
_request_counter_lock = threading.Lock()


def _new_request_id():
    """Short unique correlation ID used in logs and error responses."""
    return uuid.uuid4().hex[:12]


def _record_recent_error(rid, path, status, message):
    """Append an error entry to the recent-errors ring (used by /api/diagnostics)."""
    try:
        with _recent_errors_lock:
            _recent_errors.append({
                "rid": rid,
                "path": path,
                "status": status,
                "message": (message or "")[:500],
                "at": time.time(),
            })
    except Exception:
        pass


def _record_recent_render(kind, paint_file, elapsed_ms, success=True):
    """Append a render entry to the recent-renders ring (used by /api/recent-renders)."""
    try:
        with _recent_renders_lock:
            _recent_renders.appendleft({
                "kind": kind,                  # "preview" or "full"
                "paint_file": (paint_file or "")[:512],
                "elapsed_ms": int(elapsed_ms or 0),
                "success": bool(success),
                "at": time.time(),
            })
    except Exception:
        pass


def _validate_color_array(arr):
    """Strictly validate an [r, g, b] (or [r, g, b, a]) colour list.
    Returns (ok, normalized_list_or_None, error_message)."""
    if arr is None:
        return False, None, "color is None"
    if not isinstance(arr, (list, tuple)):
        return False, None, f"color must be list/tuple, got {type(arr).__name__}"
    if len(arr) not in (3, 4):
        return False, None, f"color must have 3 or 4 elements, got {len(arr)}"
    out = []
    for i, v in enumerate(arr):
        try:
            iv = int(v)
        except (TypeError, ValueError):
            return False, None, f"color[{i}] not an integer ({v!r})"
        if iv < 0 or iv > 255:
            return False, None, f"color[{i}]={iv} out of range 0-255"
        out.append(iv)
    return True, out, ""


def _validate_zone_dict(z):
    """Comprehensive zone validation. Returns (ok, error_message).
    Looser than _validate_zone_required_fields — checks types/bounds for
    every recognised field but lets unknown keys through."""
    if not isinstance(z, dict):
        return False, f"zone must be dict, got {type(z).__name__}"
    # Numeric fields with bounds
    bounded = {
        "intensity":         (INTENSITY_MIN, INTENSITY_MAX),
        "pattern_intensity": (INTENSITY_MIN, INTENSITY_MAX),
        "scale":             (SCALE_MIN,     SCALE_MAX),
        "rotation":          (ROTATION_MIN,  ROTATION_MAX),
        "pattern_opacity":   (OPACITY_MIN,   OPACITY_MAX),
        "wear_level":        (WEAR_LEVEL_MIN, WEAR_LEVEL_MAX),
        "pattern_offset_x":  (0.0, 1.0),
        "pattern_offset_y":  (0.0, 1.0),
    }
    for k, (lo, hi) in bounded.items():
        if k not in z or z[k] is None:
            continue
        try:
            v = float(z[k])
        except (TypeError, ValueError):
            return False, f"zone.{k} not numeric ({z[k]!r})"
        if v < lo - 1e-6 or v > hi + 1e-6:
            return False, f"zone.{k}={v} outside [{lo}, {hi}]"
    # base/finish presence — same rule as the legacy helper but explicit.
    if not z.get("base") and not z.get("finish") and not z.get("region_mask"):
        return False, f"zone needs one of: base, finish, region_mask"
    return True, ""


def _validate_path_safe(raw_path):
    """Reject obviously dangerous paths (traversal, NULs, weird URI schemes)
    BEFORE we hand them to os.path.exists or send_file.
    Returns (ok, normalized_path_or_None, error_message)."""
    if not raw_path or not isinstance(raw_path, str):
        return False, None, "path must be non-empty string"
    if "\x00" in raw_path:
        return False, None, "path contains NUL byte"
    if raw_path.lower().startswith(("file://", "http://", "https://", "ftp://")):
        return False, None, "URI schemes not allowed in path"
    # Resolve and re-check for traversal attempts.
    try:
        normed = os.path.normpath(os.path.abspath(raw_path))
    except (ValueError, OSError) as e:
        return False, None, f"path normalisation failed: {e}"
    if ".." in normed.split(os.sep):
        return False, None, "path traversal detected"
    return True, normed, ""


def _validate_iracing_id(raw_id):
    """Validate iRacing customer ID — must be all digits, 4-7 long.
    Returns (ok, normalized_string, error_message)."""
    if raw_id is None:
        return False, None, "iracing_id is required"
    s = str(raw_id).strip()
    if not s.isdigit():
        return False, None, "iracing_id must be all digits"
    if len(s) < IRACING_ID_MIN_DIGITS or len(s) > IRACING_ID_MAX_DIGITS:
        return False, None, (
            f"iracing_id must be {IRACING_ID_MIN_DIGITS}-{IRACING_ID_MAX_DIGITS} digits "
            f"(got {len(s)})"
        )
    return True, s, ""


def _rate_limit(endpoint_key, max_per_second=10):
    """Lightweight per-endpoint rate limit keyed by remote IP.
    Returns True if the request is within the budget, False if it should be rejected."""
    try:
        ip = (request.remote_addr or "?")
    except Exception:
        ip = "?"
    bucket_key = (endpoint_key, ip)
    now = time.time()
    with _rate_limit_lock:
        bucket = _rate_limit_buckets.get(bucket_key)
        if bucket is None:
            bucket = deque()
            _rate_limit_buckets[bucket_key] = bucket
        # Drop timestamps older than 1s
        while bucket and bucket[0] < now - 1.0:
            bucket.popleft()
        if len(bucket) >= max_per_second:
            return False
        bucket.append(now)
        return True


def _safe_jsonify_error(message, status, rid=None, **extra):
    """Build a consistent error response with request ID + timestamp."""
    payload = {
        "error": message,
        "status": status,
        "rid": rid or getattr(g, "_rid", None) or _new_request_id(),
        "at": time.time(),
    }
    payload.update(extra or {})
    return jsonify(payload), status


def _api_route(*args, **kwargs):
    """Decorator wrapper for Flask routes that adds:
       - request ID injection
       - blanket try/except → consistent JSON error
       - logging of unhandled exceptions
    Existing routes are NOT migrated automatically — opt-in only."""
    def deco(fn):
        @wraps(fn)
        def wrapped(*a, **kw):
            rid = getattr(g, "_rid", None) or _new_request_id()
            try:
                g._rid = rid
            except Exception:
                pass
            try:
                return fn(*a, **kw)
            except FileNotFoundError as e:
                _record_recent_error(rid, request.path, 404, str(e))
                return _safe_jsonify_error(str(e), 404, rid)
            except (ValueError, TypeError) as e:
                _record_recent_error(rid, request.path, 400, str(e))
                return _safe_jsonify_error(str(e), 400, rid)
            except Exception as e:
                tb = traceback.format_exc()
                logger.error(f"[rid={rid}] Unhandled in {fn.__name__}: {e}\n{tb}")
                _record_recent_error(rid, request.path, 500, str(e))
                return _safe_jsonify_error("internal_server_error", 500, rid,
                                           detail=str(e)[:200])
        return app.route(*args, **kwargs)(wrapped)
    return deco


# ----------------------------------------------------------------
# JS→Python key conversion: JS sends camelCase, engine expects snake_case.
# Applied to zone dicts before processing in /preview-render and /render.
# ----------------------------------------------------------------
def _camel_to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def _convert_zone_keys(zone_dict):
    """Recursively convert camelCase keys to snake_case in a zone dict."""
    if not isinstance(zone_dict, dict):
        return zone_dict
    return {_camel_to_snake(k): _convert_zone_keys(v) if isinstance(v, dict) else v
            for k, v in zone_dict.items()}

# ----------------------------------------------------------------
# Preview render serialisation — prevents CPU thrashing when the
# UI fires multiple /preview-render requests before the previous
# one finishes (e.g. slider dragging, zone switching).
#
# _preview_abort  — set this Event to tell an in-flight render it
#                   should give up (currently used as a signal; the
#                   actual check is the lock timeout below).
# _preview_render_lock — only one preview renders at a time.
#                   Acquiring it with a short timeout means stale
#                   requests return 429 instead of stacking up.
# ----------------------------------------------------------------
_preview_render_lock = threading.Lock()
_preview_abort = threading.Event()

# ----------------------------------------------------------------
# Incremental preview cache metadata (actual zone-result caching
# lives inside build_multi_zone._zone_cache in shokker_engine_v2).
# These track the last paint file + mtime seen by the preview
# endpoint so the engine cache can be invalidated when the file
# changes or the preview scale changes.
# ----------------------------------------------------------------
_preview_cache_paint_key = None  # "<paint_file_path>|<mtime>|<scale>"

# ----------------------------------------------------------------
# Spec delta cache (#12): stores the last spec map (uint8 ndarray)
# returned by /preview-render so subsequent previews can send a
# compressed delta instead of the full base64 PNG.
# ----------------------------------------------------------------
_prev_spec_cache = None  # numpy uint8 array or None

# ----------------------------------------------------------------
# Render statistics — accumulated during the server session.
# Exposed via GET /api/render-stats for the UI dashboard.
# ----------------------------------------------------------------
_render_stats = {
    "total_renders": 0,
    "total_render_time": 0.0,
    "zone_times": {},       # zone_name -> [list of elapsed times]
    "cache_hits": 0,
    "cache_misses": 0,
    "session_start": None,  # set on first render
}

# ----------------------------------------------------------------
# Render progress — tracks zone-by-zone progress for full renders.
# Polled by the UI via GET /api/render-progress.
# ----------------------------------------------------------------
_render_progress = {
    "active": False,
    "job_id": None,
    "total_zones": 0,
    "current_zone": 0,
    "current_zone_name": "",
    "phase": "idle",  # idle, preparing, rendering, encoding, done
    "started_at": 0,
    "elapsed_ms": 0,
}
_render_stats_lock = threading.Lock()

# --- Fix OSError [Errno 22] on print() when stdout/stderr pipes break (Electron) ---
class _SafeStream:
    """Wraps a stream so write() silently catches broken-pipe / invalid-argument errors."""
    def __init__(self, stream):
        self._stream = stream
    def write(self, data):
        try:
            self._stream.write(data)
        except (OSError, ValueError):
            pass
    def flush(self):
        try:
            self._stream.flush()
        except (OSError, ValueError):
            pass
    def __getattr__(self, name):
        return getattr(self._stream, name)

sys.stdout = _SafeStream(sys.stdout)
sys.stderr = _SafeStream(sys.stderr)

# Import the engine package (V5) and config
try:
    import engine
    from config import CFG
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import engine
    from config import CFG
# engine package provides V5 registries (BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY) via __getattr__

# GPU acceleration detection
try:
    from engine.gpu import gpu_info
except ImportError:
    def gpu_info(): return {'backend': 'cpu', 'name': 'CPU', 'vram_mb': 0, 'accelerated': False, 'icon': 'CPU'}

# Setup Flask
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH_BYTES  # Reject oversized POSTs (improvement #5)
# Enable JSON pretty-print only in dev — saves bytes in prod responses.
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
# Track app start for /api/health & /api/stats (mirrors _server_start_time).
app._start_time = _server_start_time
CORS(app)

# Shared cache-control header dicts (avoids typos and inconsistency)
_no_cache_headers = {'Cache-Control': 'no-store, no-cache, must-revalidate', 'Pragma': 'no-cache'}
_immutable_cache_headers = {'Cache-Control': 'public, max-age=31536000, immutable'}
# Short-lived cache for finish data, swatches that change rarely (5 minutes).
_short_cache_headers = {'Cache-Control': 'public, max-age=300'}


# ----------------------------------------------------------------
# REQUEST MIDDLEWARE — adds correlation IDs, timing headers,
# version headers, and structured access logs. Runs for every
# request without changing existing route handlers.
# ----------------------------------------------------------------
@app.before_request
def _spb_before_request():
    """Stamp request with start time + correlation ID."""
    try:
        g._t0 = time.perf_counter()
        g._rid = request.headers.get("X-Request-ID") or _new_request_id()
        global _request_counter
        with _request_counter_lock:
            _request_counter += 1
    except Exception:
        pass


@app.after_request
def _spb_after_request(resp):
    """Add timing + version headers to every response and log access line."""
    try:
        t0 = getattr(g, "_t0", None)
        elapsed_ms = int((time.perf_counter() - t0) * 1000) if t0 else 0
        rid = getattr(g, "_rid", "-")
        resp.headers['X-SPB-Version'] = SPB_VERSION
        resp.headers['X-SPB-Engine']  = SPB_ENGINE_VERSION
        resp.headers['X-Render-Time-Ms'] = str(elapsed_ms)
        resp.headers['X-Request-ID'] = rid
        # Optional gzip for large JSON responses when client accepts it.
        # Skips small bodies (<2KB) and already-compressed types.
        try:
            ae = (request.headers.get('Accept-Encoding') or '').lower()
            ctype = (resp.headers.get('Content-Type') or '').lower()
            if ('gzip' in ae and 'gzip' not in (resp.headers.get('Content-Encoding') or '')
                    and ctype.startswith('application/json')
                    and resp.content_length and resp.content_length > 2048):
                import gzip as _gzip
                gz = _gzip.compress(resp.get_data(), compresslevel=4)
                resp.set_data(gz)
                resp.headers['Content-Encoding'] = 'gzip'
                resp.headers['Content-Length'] = str(len(gz))
                resp.headers.add('Vary', 'Accept-Encoding')
        except Exception:
            # Compression must NEVER break a response.
            pass
        # Quiet down spammy polling endpoints — only log slow / non-200 hits.
        # 2026-04-21 perf fix: added /build-check (polled every 5s by the UI) to
        # the silenced set — every build-check was hitting logger.info and
        # Windows stdout, adding GIL pressure during active renders.
        path = request.path or ""
        spammy = path in ("/api/render-status", "/api/render-progress",
                          "/health", "/api/health", "/api/ping",
                          "/build-check")
        if (not spammy) or resp.status_code >= 400 or elapsed_ms > 250:
            logger.info(
                f"access rid={rid} {request.method} {path} -> {resp.status_code} "
                f"in {elapsed_ms}ms ip={request.remote_addr or '-'}"
            )
    except Exception:
        pass
    return resp

@app.errorhandler(404)
def _handle_404(e):
    rid = getattr(g, "_rid", None) or "-"
    _record_recent_error(rid, request.path, 404, "not_found")
    return jsonify({"error": "not_found", "path": request.path, "rid": rid}), 404

@app.errorhandler(413)
def _handle_413(e):
    """Request entity too large — MAX_CONTENT_LENGTH exceeded."""
    rid = getattr(g, "_rid", None) or "-"
    logger.warning(f"[rid={rid}] Request too large on {request.path} "
                   f"(limit: {MAX_CONTENT_LENGTH_BYTES // (1024*1024)}MB)")
    _record_recent_error(rid, request.path, 413, "payload_too_large")
    return jsonify({"error": "Request body too large",
                    "max_mb": MAX_CONTENT_LENGTH_BYTES // (1024 * 1024),
                    "rid": rid}), 413

@app.errorhandler(400)
def _handle_400(e):
    """Bad request — catches malformed JSON, missing fields, etc."""
    rid = getattr(g, "_rid", None) or "-"
    # 400 errors are user-facing: log message only, NOT full traceback.
    msg = getattr(e, 'description', None) or str(e)
    logger.info(f"[rid={rid}] 400 on {request.path}: {msg}")
    _record_recent_error(rid, request.path, 400, msg)
    return jsonify({"error": "bad_request", "message": msg, "rid": rid}), 400

@app.errorhandler(429)
def _handle_429(e):
    """Too many requests — typically from rate limiter."""
    rid = getattr(g, "_rid", None) or "-"
    return jsonify({"error": "too_many_requests",
                    "message": "Rate limit exceeded — slow down and retry.",
                    "rid": rid}), 429

@app.errorhandler(500)
def _handle_500(e):
    """Internal server error — log traceback and return safe message."""
    rid = getattr(g, "_rid", None) or "-"
    # Full traceback ONLY for 500s — 400/404 keep the log clean.
    logger.error(f"[rid={rid}] Unhandled 500 on {request.path}: {e}\n{traceback.format_exc()}")
    _record_recent_error(rid, request.path, 500, str(e))
    return jsonify({"error": "internal_server_error",
                    "message": "An unexpected error occurred. Check server logs for details.",
                    "rid": rid}), 500

@app.errorhandler(503)
def _handle_503(e):
    """Service unavailable — engine not loaded, GPU busy, etc."""
    rid = getattr(g, "_rid", None) or "-"
    return jsonify({"error": "service_unavailable",
                    "message": getattr(e, 'description', 'Service temporarily unavailable.'),
                    "rid": rid,
                    "retry_after_s": 5}), 503

@app.errorhandler(405)
def _handle_405(e):
    """Method not allowed — wrong HTTP verb on a known route."""
    rid = getattr(g, "_rid", None) or "-"
    return jsonify({"error": "method_not_allowed",
                    "method": request.method,
                    "path": request.path,
                    "rid": rid}), 405

@app.route('/favicon.ico')
def favicon():
    return '', 204  # No content — stops the 404 without needing an actual icon file

@app.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    """Serve pre-baked thumbnails directly as static files — no generation, maximum speed.
    Uses conditional=True so browsers get proper 304 Not Modified responses
    based on If-Modified-Since / ETag, saving bandwidth on repeat loads."""
    # Block path traversal: filename can contain subdirs but never ..
    if ".." in filename.replace("\\", "/").split("/"):
        return jsonify({"error": "invalid_path"}), 400
    thumb_path = os.path.join(THUMBNAIL_DIR, filename)
    if os.path.exists(thumb_path):
        resp = send_file(thumb_path, mimetype='image/png', conditional=True)
        # Long cache: thumbnails only change when content changes (hash-managed)
        resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return resp
    # If thumbnail doesn't exist yet, return 404 so JS onerror can fall back to API
    return jsonify({"error": "thumbnail_not_found", "path": filename}), 404


@app.route('/<path:filename>')
def serve_static_assets(filename):
    """Serve JS/CSS assets from the server directory."""
    if filename.endswith(('.js', '.css', '.png', '.svg', '.ico')):
        for candidate_dir in [SERVER_DIR, BUNDLE_DIR]:
            fpath = os.path.join(candidate_dir, filename)
            if os.path.exists(fpath):
                resp = send_file(fpath)
                if filename.endswith(('.js', '.css')):
                    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
                    resp.headers.pop('ETag', None)
                    resp.headers.pop('Last-Modified', None)
                return resp
    return jsonify({"error": "not_found", "path": request.path}), 404

# Folders - handle PyInstaller bundle vs normal Python
# When frozen (PyInstaller), __file__ is in a temp dir. Use exe location instead.
if getattr(sys, 'frozen', False):
    # For --onefile PyInstaller/Nuitka builds, sys.executable is in a temp extraction dir.
    # The REAL exe location (where HTML and config live) is the original path the user ran.
    # sys.argv[0] or the parent process's working dir won't help either.
    # Solution: check for SHOKKER_EXE_DIR env var (set by Electron), fall back to sys.executable dir.
    SERVER_DIR = os.environ.get('SHOKKER_EXE_DIR', os.path.dirname(sys.executable))
    BUNDLE_DIR = getattr(sys, '_MEIPASS', SERVER_DIR)  # Where bundled data files live
else:
    SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = SERVER_DIR
OUTPUT_FOLDER = os.path.join(SERVER_DIR, 'output')
CONFIG_FILE = os.path.join(SERVER_DIR, 'shokker_config.json')
# Pre-rendered thumbnails: env override > config > next to server. Ensures accurate thumbnails on every load when folder exists.
THUMBNAIL_DIR = os.environ.get('SHOKKER_THUMBNAIL_DIR') or getattr(CFG, 'THUMBNAIL_DIR', None) or os.path.join(SERVER_DIR, 'thumbnails')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- Auto-invalidate swatch disk cache when engine code changes ---
def _engine_files_fingerprint():
    """Hash of modification times of all engine .py files. Changes when ANY engine code is edited."""
    import hashlib
    mtimes = []
    for root, dirs, files in os.walk(os.path.join(SERVER_DIR, 'engine')):
        for f in sorted(files):
            if f.endswith('.py'):
                try:
                    mtimes.append(f"{f}:{os.path.getmtime(os.path.join(root, f)):.0f}")
                except OSError:
                    pass
    # Also include main engine files
    for f in ['shokker_engine_v2.py', 'server.py']:
        fp = os.path.join(SERVER_DIR, f)
        if os.path.isfile(fp):
            try:
                mtimes.append(f"{f}:{os.path.getmtime(fp):.0f}")
            except OSError:
                pass
    return hashlib.md5('|'.join(mtimes).encode()).hexdigest()[:12]

def _check_swatch_cache_freshness():
    """If engine code changed since last swatch cache build, wipe the disk cache."""
    cache_dir = os.path.join(THUMBNAIL_DIR, 'swatch_cache')
    fp_file = os.path.join(cache_dir, '_fingerprint.txt')
    current_fp = _engine_files_fingerprint()
    if os.path.isdir(cache_dir) and os.path.isfile(fp_file):
        try:
            with open(fp_file, 'r') as f:
                stored_fp = f.read().strip()
            if stored_fp == current_fp:
                return  # Cache is fresh
        except Exception:
            pass
    # Cache is stale or doesn't exist — wipe and rebuild
    if os.path.isdir(cache_dir):
        import shutil
        try:
            shutil.rmtree(cache_dir)
            logging.getLogger('shokker.startup').info(f"Swatch disk cache invalidated (engine code changed)")
        except Exception:
            pass
    os.makedirs(cache_dir, exist_ok=True)
    try:
        with open(fp_file, 'w') as f:
            f.write(current_fp)
    except Exception:
        pass

_check_swatch_cache_freshness()

_SWATCH_CACHE_TOKEN = None
_SWATCH_CACHE_TOKEN_TS = 0.0

def _swatch_cache_token():
    """Short-lived engine fingerprint for swatch cache keys.

    The startup wipe catches normal restarts. This token also prevents a running
    dev server from serving forever-old PNGs after engine files are edited.
    """
    global _SWATCH_CACHE_TOKEN, _SWATCH_CACHE_TOKEN_TS
    now = time.time()
    if _SWATCH_CACHE_TOKEN is None or (now - _SWATCH_CACHE_TOKEN_TS) > 10.0:
        _SWATCH_CACHE_TOKEN = _engine_files_fingerprint()
        _SWATCH_CACHE_TOKEN_TS = now
    return _SWATCH_CACHE_TOKEN

# Startup log
logger_startup = logging.getLogger('shokker.startup')

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('shokker')

# 2026-04-21 perf fix: werkzeug's built-in request-access logger prints every
# request at INFO level. During a live render the UI polls
# /api/render-status every 2s and /build-check every 5s — that's 7-13 stdout
# writes per zone render, each one a GIL-held `sys.stdout.write`. On Windows
# Defender-protected terminals the write itself can take 50-200ms. Measured
# impact: zone renders taking 20s+ when isolated benchmark is 1s.
#
# Silence werkzeug access-log spam for poll endpoints. Still logs warnings
# / errors / slow (>250ms) requests via the Flask access-log middleware
# below.
class _SilencePollEndpoints(logging.Filter):
    """Drop werkzeug access-log records for spammy poll endpoints so they
    don't steal GIL / stdout time during long renders."""
    _SPAMMY = (
        '/api/render-status', '/api/render-progress',
        '/health', '/api/health', '/api/ping',
        '/build-check',
    )
    def filter(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return True
        return not any(p in msg for p in self._SPAMMY)

logging.getLogger('werkzeug').addFilter(_SilencePollEndpoints())

# Log thumbnail dir and warn if missing/empty so user knows to run rebuild_thumbnails.py
def _log_thumbnail_dir():
    if not os.path.isdir(THUMBNAIL_DIR):
        logger_startup.warning(f"Thumbnail dir missing: {THUMBNAIL_DIR} - run: python rebuild_thumbnails.py")
        return
    count = 0
    for sub in ('base', 'pattern', 'monolithic'):
        d = os.path.join(THUMBNAIL_DIR, sub)
        if os.path.isdir(d):
            count += sum(1 for f in os.listdir(d) if f.endswith('.png'))
    expected = len(getattr(engine, 'BASE_REGISTRY', {})) + len(getattr(engine, 'PATTERN_REGISTRY', {})) + len(getattr(engine, 'MONOLITHIC_REGISTRY', {}))
    if count == 0:
        logger_startup.warning(f"Thumbnail dir empty: {THUMBNAIL_DIR} - run: python rebuild_thumbnails.py")
    else:
        msg = f"Thumbnails: {THUMBNAIL_DIR} ({count} pre-rendered PNGs)"
        if expected and count < expected:
            msg += f" - expected {expected}, {expected - count} missing (run: python rebuild_thumbnails.py)"
        logger_startup.info(msg)
_log_thumbnail_dir()

# ===== LICENSING & ACTIVATION =====
LICENSE_FILE = os.path.join(SERVER_DIR, 'shokker_license.json')
VALID_LICENSE_PREFIX = "SHOKKER-"  # Valid keys: SHOKKER-XXXX-XXXX-XXXX

def load_license():
    """Load saved license from disk."""
    try:
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('license_key', ''), data.get('activated', False)
    except Exception:
        pass
    return '', False

def save_license(key, activated):
    """Save license to disk."""
    try:
        with open(LICENSE_FILE, 'w') as f:
            json.dump({'license_key': key, 'activated': activated, 'timestamp': time.time()}, f)
    except Exception:
        pass

def validate_license_key(key):
    """Validate license key format: SHOKKER-XXXX-XXXX-XXXX (alphanumeric)."""
    if not key or not isinstance(key, str):
        return False
    key = key.strip().upper()
    if not key.startswith(VALID_LICENSE_PREFIX):
        return False
    parts = key.split('-')
    if len(parts) != 4:
        return False
    # Each part after SHOKKER should be 4 alphanumeric chars
    for part in parts[1:]:
        if len(part) != 4 or not part.isalnum():
            return False
    return True

# Load license on startup
_license_key, _license_active = load_license()


# ===== SERVE PAINT BOOTH HTML =====
@app.route('/')
def serve_paint_booth():
    """Serve the Paint Booth UI at the root URL for easy access."""
    # Check next to exe first, then in bundle dir, then in app/ subdir
    for candidate in [
        os.path.join(SERVER_DIR, 'paint-booth-v2.html'),
        os.path.join(BUNDLE_DIR, 'paint-booth-v2.html'),
        os.path.join(SERVER_DIR, '..', 'app', 'paint-booth-v2.html'),
    ]:
        if os.path.exists(candidate):
            # BUILD 23: Inject proof marker so we can verify Flask served the page (not cache)
            try:
                with open(os.path.abspath(candidate), 'r', encoding='utf-8') as hf:
                    html_content = hf.read()
                html_content = html_content.replace('</head>', f'<!-- FLASK-SERVED-BUILD-27 PID={os.getpid()} TIME={time.strftime("%H:%M:%S")} -->\n</head>', 1)
                from flask import Response
                return Response(html_content, mimetype='text/html')
            except Exception as _e:
                # Fallback to send_file if injection fails
                return send_file(os.path.abspath(candidate), mimetype='text/html')
    return "Paint Booth HTML not found", 404


# ================================================================
# CONFIG - persistent user settings (iRacing ID, car paths, etc.)
# ================================================================

def load_config():
    """Load saved config from shokker_config.json."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "iracing_id": "23371",
        "car_paths": {},
        "live_link_enabled": False,
        "active_car": None,
        "use_custom_number": True,
    }


def save_config(cfg):
    """Save config to shokker_config.json."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)


# ================================================================
# ENDPOINTS
# ================================================================

# 2026-04-21 perf fix: /build-check is polled by the UI every ~5s.
# The pre-fix handler did 3 filesystem `isfile` checks + one `open` +
# `json.loads` on EVERY call. On Windows with Defender real-time
# scanning, each file probe can take 50-200ms and holds the GIL — so
# during an active render the poll thread was stealing 150-600ms per
# poll from the CPU-bound render thread. At 5-6 polls per zone that
# adds 1-4 seconds of stall time per zone. Painter's log showed a
# 22-second render on a zone that benchmarks at ~1 s in isolation.
#
# Cache the package.json lookup across calls. Re-resolve only if the
# SERVER_DIR changes (never, in practice) or the session starts fresh.
_build_check_cache = {
    "pkg_version": None,
    "pkg_path_searched": False,
}

def _resolve_pkg_version():
    """Resolve the Electron package.json version once, then cache."""
    if _build_check_cache["pkg_path_searched"]:
        return _build_check_cache["pkg_version"] or "5.9.2"
    _build_check_cache["pkg_path_searched"] = True
    try:
        import json as _json
        for _pkg_path in [
            os.path.join(SERVER_DIR, 'electron-app', 'package.json'),
            os.path.join(os.path.dirname(SERVER_DIR), 'package.json'),
            os.path.join(SERVER_DIR, '..', 'package.json'),
        ]:
            if os.path.isfile(_pkg_path):
                with open(_pkg_path, 'r') as _f:
                    _build_check_cache["pkg_version"] = _json.load(_f).get('version', '5.9.2')
                break
    except Exception:
        pass
    return _build_check_cache["pkg_version"] or "5.9.2"


@app.route('/build-check', methods=['GET'])
def build_check():
    """Diagnostic endpoint - returns server status and configuration.
    Cached version lookup; this handler is polled every ~5s by the UI
    and must stay cheap enough to not stall concurrent renders."""
    # Downgrade log level so poll-spam doesn't contend with render stdout.
    logger.debug("[build-check] Health check requested")
    return jsonify({
        "build": "V5",
        "version": _resolve_pkg_version(),
        "status": "running",
        "debug": False,
        "engine": "Shokker Engine V5 - Modular Architecture",
        "pid": os.getpid(),
        "port": int(os.environ.get('SHOKKER_PORT', 59876)),
        "server_dir": SERVER_DIR,
        "gpu": gpu_info(),
    })

@app.route('/health', methods=['GET'])
def health():
    """Lightweight health check — no heavy computation, just confirms server is alive."""
    return jsonify({"ok": True, "version": "6.2.0-alpha", "uptime_s": int(time.time() - _server_start_time)})


@app.route('/status', methods=['GET'])
def status():
    """Server heartbeat + engine capabilities."""
    logger.debug("[status] Heartbeat requested")
    cfg = load_config()
    return jsonify({
        "status": "online",
        "version": "6.2.0-alpha",
        "engine": "Shokker Engine v6.0 PRO - 24K Arsenal",
        "capabilities": {
            "bases": list(engine.BASE_REGISTRY.keys()),
            "patterns": list(engine.PATTERN_REGISTRY.keys()),
            "monolithics": list(engine.MONOLITHIC_REGISTRY.keys()),
            "legacy_finishes": list(engine.FINISH_REGISTRY.keys()),
            "base_count": len(engine.BASE_REGISTRY),
            "pattern_count": len(engine.PATTERN_REGISTRY),
            "monolithic_count": len(engine.MONOLITHIC_REGISTRY),
            "combination_count": len(engine.BASE_REGISTRY) * len(engine.PATTERN_REGISTRY),
            "features": {
                "helmet_spec": True,
                "suit_spec": True,
                "wear_slider": True,
                "export_zip": True,
                "matching_set": True,
                "dual_spec": True,
                "live_link": True,
                "swatch_highres_mono": True,  # Color Shift Duo etc. render at 256px then downscale
            },
        },
        "config": {
            "iracing_id": cfg.get("iracing_id", ""),
            "live_link_enabled": cfg.get("live_link_enabled", False),
            "active_car": cfg.get("active_car"),
            "car_paths": cfg.get("car_paths", {}),
        },
        "license": {
            "active": _license_active,
            "key_masked": (_license_key[:12] + "****") if _license_key else "",
        },
        "gpu": gpu_info(),
    })


@app.route('/license', methods=['GET', 'POST'])
def license_endpoint():
    """Check or activate license."""
    global _license_key, _license_active
    logger.info(f"[license] {request.method} request")

    if request.method == 'GET':
        return jsonify({
            "active": _license_active,
            "key_masked": (_license_key[:12] + "****") if _license_key else "",
        })

    # POST - activate a key
    data = request.get_json() or {}
    key = (data.get('key', '') or '').strip().upper()

    if not key:
        return jsonify({"error": "No license key provided"}), 400

    if not validate_license_key(key):
        return jsonify({"error": "Invalid license key format. Expected: SHOKKER-XXXX-XXXX-XXXX"}), 400

    # Key format is valid - activate it
    # In production this would phone home to a license server.
    # For Alpha, valid format = activated.
    _license_key = key
    _license_active = True
    save_license(key, True)
    logger.info(f"License activated: {key[:12]}****")

    return jsonify({
        "active": True,
        "key_masked": key[:12] + "****",
        "message": "License activated successfully!"
    })


@app.route('/license/deactivate', methods=['POST'])
def license_deactivate():
    """Deactivate the current license."""
    global _license_key, _license_active
    _license_key = ''
    _license_active = False
    save_license('', False)
    logger.info("License deactivated")
    return jsonify({"active": False, "message": "License deactivated."})


@app.route('/finish-groups', methods=['GET'])
def finish_groups():
    """Return group metadata for UI organization of 24K Arsenal finishes."""
    logger.info("[finish-groups] Requested")
    try:
        import shokker_24k_expansion as _exp24k
        groups = _exp24k.get_expansion_group_map()
        counts = _exp24k.get_expansion_counts()
        # Merge PARADIGM groups if available
        try:
            import shokker_paradigm_expansion as _paradigm
            paradigm_groups = _paradigm.get_paradigm_group_map()
            for key in ("bases", "patterns", "specials"):
                if key in paradigm_groups:
                    groups.setdefault(key, {}).update(paradigm_groups[key])
        except Exception:
            pass
        # Merge FUSIONS groups if available
        try:
            import shokker_fusions_expansion as _fusions
            fusion_groups = _fusions.get_fusion_group_map()
            if "fusions" in fusion_groups:
                # Add fusions as specials (they render via MONOLITHIC_REGISTRY)
                groups.setdefault("specials", {}).update(fusion_groups["fusions"])
        except Exception:
            pass
        return jsonify({
            "status": "ok",
            "groups": groups,
            "expansion_counts": counts,
            "total_bases": len(engine.BASE_REGISTRY),
            "total_patterns": len(engine.PATTERN_REGISTRY),
            "total_specials": len(engine.MONOLITHIC_REGISTRY),
            "total_fusions": len(getattr(engine, 'FUSION_REGISTRY', {})),
            "total_combinations": len(engine.BASE_REGISTRY) * len(engine.PATTERN_REGISTRY) + len(engine.MONOLITHIC_REGISTRY),
        })
    except ImportError:
        return jsonify({"status": "ok", "groups": {"bases": {}, "patterns": {}, "specials": {}},
                        "expansion_counts": {"bases": 0, "patterns": 0, "specials": 0, "total": 0}})


# ================================================================
# /api/finish-data - Single source of truth for all finish lists
# Replaces the 10,000-line hardcoded JS arrays in paint-booth-v2.html
# Called once on page load; UI builds all dropdowns from this response.
# ================================================================

def _id_to_display_name(finish_id):
    """Convert snake_case finish ID to Title Case display name."""
    return finish_id.replace('_', ' ').title()


def _build_finish_data_payload():
    """Build the full finish catalogue from live Python registries.

    Returns a dict with:
      bases    - list of {id, name, category, swatch}
      patterns - list of {id, name, category, swatch}
      specials - list of {id, name, category, swatch}
      groups   - {bases: {cat: [id,...]}, patterns: {...}, specials: {...}}
      counts   - {bases: N, patterns: N, specials: N, total: N}
    """
    import shokker_24k_expansion as _exp24k

    # Pull the live group maps so we know every finish's category
    groups = _exp24k.get_expansion_group_map()

    # Merge PARADIGM groups
    try:
        import shokker_paradigm_expansion as _paradigm
        for key in ("bases", "patterns", "specials"):
            paradigm_g = _paradigm.get_paradigm_group_map().get(key, {})
            groups.setdefault(key, {}).update(paradigm_g)
    except Exception:
        pass

    # Merge FUSIONS groups (fusions render as specials)
    try:
        import shokker_fusions_expansion as _fusions
        fusion_g = _fusions.get_fusion_group_map().get("fusions", {})
        groups.setdefault("specials", {}).update(fusion_g)
    except Exception:
        pass

    # Invert: id → category for fast lookup
    id_to_cat = {"bases": {}, "patterns": {}, "specials": {}}
    for reg_key in ("bases", "patterns", "specials"):
        for cat_name, id_list in groups.get(reg_key, {}).items():
            for fid in id_list:
                id_to_cat[reg_key][fid] = cat_name

    # Default swatch colours per registry type (overridden per-finish if we have special data)
    _BASE_SWATCH   = "#888888"
    _PAT_SWATCH    = "#555577"
    _SPEC_SWATCH   = "#446688"

    def _make_entries(registry_keys, reg_type, default_swatch, swatch_type):
        """swatch_type: 'base' | 'pattern' | 'monolithic' - used by client for /api/swatch/<type>/<id>."""
        out = []
        seen = set()
        for fid in registry_keys:
            if fid in seen:
                continue
            seen.add(fid)
            out.append({
                "id":       fid,
                "name":     _id_to_display_name(fid),
                "category": id_to_cat[reg_type].get(fid, "Other"),
                "swatch":   default_swatch,
                "type":     swatch_type,
            })
        # Sort by category then name for stable UI ordering
        out.sort(key=lambda x: (x["category"], x["name"]))
        return out

    bases    = _make_entries(engine.BASE_REGISTRY.keys(),       "bases",    _BASE_SWATCH, "base")
    patterns = _make_entries(engine.PATTERN_REGISTRY.keys(),    "patterns", _PAT_SWATCH, "pattern")
    specials = _make_entries(engine.MONOLITHIC_REGISTRY.keys(), "specials", _SPEC_SWATCH, "monolithic")

    total = len(bases) + len(patterns) + len(specials)
    return {
        "bases":    bases,
        "patterns": patterns,
        "specials": specials,
        "groups":   groups,
        "counts": {
            "bases":    len(bases),
            "patterns": len(patterns),
            "specials": len(specials),
            "total":    total,
        },
    }


# Module-level cache - built once, never rebuilt (server restart resets it)
_FINISH_DATA_CACHE = None


def _safe_thumb_key(key):
    if not key:
        return "none"
    return str(key).replace("/", "_").replace("\\", "_").replace(":", "_").strip() or "none"


def _load_canonical_finish_ids():
    """Load finish_ids_canonical.json (from 1-data via scripts/export_finish_ids.py) if present."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "finish_ids_canonical.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


@app.route('/api/thumbnail-status', methods=['GET'])
def api_thumbnail_status():
    """Return thumbnail dir, PNG count, expected count (canonical list or registries), and list of missing keys."""
    logger.info("[thumbnail-status] Status check requested")
    exists = os.path.isdir(THUMBNAIL_DIR)
    count = 0
    if exists:
        for sub in ('base', 'pattern', 'monolithic'):
            d = os.path.join(THUMBNAIL_DIR, sub)
            if os.path.isdir(d):
                count += sum(1 for f in os.listdir(d) if f.endswith('.png'))
    canon = _load_canonical_finish_ids()
    if canon:
        expected_bases = len(canon.get("bases", []))
        expected_patterns = len(canon.get("patterns", []))
        expected_monolithics = len(canon.get("specials", []))
    else:
        expected_bases = len(getattr(engine, 'BASE_REGISTRY', {}))
        expected_patterns = len(getattr(engine, 'PATTERN_REGISTRY', {}))
        expected_monolithics = len(getattr(engine, 'MONOLITHIC_REGISTRY', {}))
    expected_total = expected_bases + expected_patterns + expected_monolithics
    missing = []
    if exists:
        if canon:
            for finish_type, keys in [("base", canon.get("bases", [])), ("pattern", canon.get("patterns", [])), ("monolithic", canon.get("specials", []))]:
                subdir = os.path.join(THUMBNAIL_DIR, finish_type)
                for key in keys:
                    if finish_type == "pattern" and (not key or key == "none"):
                        continue
                    path = os.path.join(subdir, _safe_thumb_key(key) + ".png")
                    if not os.path.isfile(path):
                        missing.append(f"{finish_type}/{key}")
        else:
            for finish_type, reg in [("base", engine.BASE_REGISTRY), ("pattern", engine.PATTERN_REGISTRY), ("monolithic", engine.MONOLITHIC_REGISTRY)]:
                if not reg:
                    continue
                subdir = os.path.join(THUMBNAIL_DIR, finish_type)
                for key in reg:
                    if finish_type == "pattern" and (not key or key == "none"):
                        continue
                    path = os.path.join(subdir, _safe_thumb_key(key) + ".png")
                    if not os.path.isfile(path):
                        missing.append(f"{finish_type}/{key}")
    return jsonify({
        "thumbnail_dir": os.path.abspath(THUMBNAIL_DIR),
        "exists": exists,
        "png_count": count,
        "expected": {
            "bases": expected_bases,
            "patterns": expected_patterns,
            "specials": expected_monolithics,
            "total": expected_total,
        },
        "missing_count": len(missing),
        "missing_sample": missing[:50],
        "canonical_used": canon is not None,
        "hint": "Run from V5 folder: python rebuild_thumbnails.py. Regenerate canonical list: python scripts/export_finish_ids.py" if (not exists or count == 0) else None,
    })


@app.route('/api/clear-cache', methods=['GET', 'POST'])
def api_clear_cache():
    """Clear in-memory + disk swatch caches. Use after code changes or for hard reset."""
    logger.info("[clear-cache] Cache clear requested")
    global _FINISH_DATA_CACHE
    with _SWATCH_CACHE_LOCK:
        _SWATCH_CACHE.clear()
    _FINISH_DATA_CACHE = None
    # Also clear disk swatch cache
    _swatch_disk_dir = os.path.join(THUMBNAIL_DIR, 'swatch_cache')
    cleared_disk = 0
    if os.path.isdir(_swatch_disk_dir):
        import shutil
        try:
            shutil.rmtree(_swatch_disk_dir)
            cleared_disk = 1
        except Exception:
            pass
    return jsonify({"status": "ok", "message": f"Caches cleared (memory + disk={cleared_disk})."})


@app.route('/api/thumb-regen/<finish_type>/<finish_id>', methods=['POST'])
def regen_thumbnail(finish_type, finish_id):
    """Force regeneration of a specific thumbnail. Useful for dev / after hot-adding a finish.
    finish_type: spec_patterns | bases | patterns | monolithics
    """
    logger.info(f"[thumb-regen] Queuing regen: {finish_type}/{finish_id}")
    if finish_type not in ('spec_patterns', 'bases', 'patterns', 'monolithics', 'base', 'pattern', 'monolithic'):
        return jsonify({"error": f"Invalid finish_type: {finish_type}"}), 400
    _queue_thumbnail_regen(finish_type, finish_id)
    return jsonify({"status": "queued", "finish_type": finish_type, "id": finish_id})


@app.route('/api/spec-pattern-preview/<pattern_id>')
def spec_pattern_preview(pattern_id):
    """Generate a 192x64 3-panel M/R/CC split preview thumbnail for a spec pattern.
    Layout: [M grayscale | R grayscale | CC inverted grayscale] each 64x64, labeled.
    Uses _generate_spec_preview_image() — same function as the pre-baker (DRY).
    Kept as fallback for JS onerror handlers when static thumbnail not yet baked."""
    # Support cache-bust via ?v= query param
    bust = request.args.get('v', '')

    # Check disk cache first (skip if cache-bust param provided)
    cache_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f'{pattern_id}.png')

    if os.path.exists(cache_path) and not bust:
        return send_file(cache_path, mimetype='image/png')

    # Generate using shared function
    img = _generate_spec_preview_image(pattern_id)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    # Save to disk for future static serving
    try:
        img.save(cache_path, 'PNG')
    except Exception:
        pass
    return send_file(buf, mimetype='image/png')


@app.route('/api/spec-pattern-preview-metal/<pattern_id>')
def spec_pattern_preview_metal(pattern_id):
    """Render spec pattern as if applied to a chrome/metallic surface simulation. 128x128.
    Uses _generate_spec_metal_image() — same function as the pre-baker (DRY).
    Kept as fallback for JS onerror handlers when static thumbnail not yet baked."""
    bust = request.args.get('v', '')

    cache_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns_metal')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f'{pattern_id}.png')

    if os.path.exists(cache_path) and not bust:
        return send_file(cache_path, mimetype='image/png')

    img = _generate_spec_metal_image(pattern_id)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    try:
        img.save(cache_path, 'PNG')
    except Exception:
        pass
    return send_file(buf, mimetype='image/png')


@app.route('/api/spec-preview-composite', methods=['POST'])
def spec_preview_composite():
    """Render a 256x128 composite preview of spec pattern stack over a base finish.
    Body: { zone_spec_stack: [...], base_finish: 'chrome'|'matte'|'brushed'|'carbon' }
    """
    logger.info("[spec-preview-composite] Composite preview requested")
    from engine.spec_patterns import PATTERN_CATALOG
    import numpy as np
    from PIL import Image as _PILImage, ImageDraw as _ImageDraw

    data = request.get_json(force=True, silent=True) or {}
    spec_stack = data.get('zone_spec_stack', [])
    base_finish = data.get('base_finish', 'chrome')

    W, H = 256, 128

    # Render base finish gradient background
    yy, xx = np.mgrid[0:H, 0:W]
    norm_x = xx / W
    norm_y = yy / H

    if base_finish == 'chrome':
        # Mirror-like gradient: bright top-center, dark edges
        dist = np.sqrt((norm_x - 0.5) ** 2 * 0.5 + (norm_y - 0.3) ** 2)
        lum = np.clip(1.0 - dist * 1.2, 0.15, 1.0)
        base_r = np.clip(lum * 0.90 + 0.08, 0, 1)
        base_g = np.clip(lum * 0.94 + 0.05, 0, 1)
        base_b = np.clip(lum * 1.05 + 0.03, 0, 1)
    elif base_finish == 'matte':
        # Flat dark matte, very subtle gradient
        lum = np.clip(0.15 + norm_x * 0.05 + (1 - norm_y) * 0.05, 0, 1)
        base_r = lum * 0.85
        base_g = lum * 0.85
        base_b = lum * 0.85
    elif base_finish == 'brushed':
        # Brushed metal: horizontal streaks
        streak = (np.sin(norm_y * H * 0.8) * 0.08 + 0.72)
        lum = np.clip(streak + (1 - norm_x) * 0.1, 0.3, 0.95)
        base_r = lum * 0.88
        base_g = lum * 0.91
        base_b = lum * 0.98
    elif base_finish == 'carbon':
        # Carbon fiber pattern: dark with weave highlights
        weave_x = (np.sin(norm_x * W * 0.5) * 0.5 + 0.5)
        weave_y = (np.sin(norm_y * H * 0.5) * 0.5 + 0.5)
        weave = weave_x * weave_y
        lum = np.clip(weave * 0.3 + 0.05, 0, 0.4)
        base_r = lum * 0.9
        base_g = lum * 0.95
        base_b = lum
    else:
        lum = np.ones((H, W), dtype=np.float32) * 0.6
        base_r = base_g = base_b = lum

    # Composite spec stack: blend each layer's pattern as a luminance modulation
    composite_mod = np.ones((H, W), dtype=np.float32)
    for layer in spec_stack[:5]:
        pid = layer.get('pattern', '')
        opacity = (layer.get('opacity', 50)) / 100.0
        fn = PATTERN_CATALOG.get(pid)
        if fn is None:
            continue
        try:
            pat = fn((H, W), 42, 1.0)
            pat = np.clip(pat, 0, 1).astype(np.float32)
            # Normal blend: scale by opacity
            composite_mod = composite_mod * (1.0 - opacity) + pat * opacity
        except Exception as ex:
            logger.warning(f"spec-preview-composite layer error {pid}: {ex}")

    # Apply composite mod to base channels
    final_r = np.clip(base_r * composite_mod, 0, 1)
    final_g = np.clip(base_g * composite_mod, 0, 1)
    final_b = np.clip(base_b * composite_mod, 0, 1)

    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[:, :, 0] = (final_r * 255).astype(np.uint8)
    rgba[:, :, 1] = (final_g * 255).astype(np.uint8)
    rgba[:, :, 2] = (final_b * 255).astype(np.uint8)
    rgba[:, :, 3] = 255

    img = _PILImage.fromarray(rgba, 'RGBA')

    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


@app.route('/api/psd-import', methods=['POST'])
def api_psd_import():
    """Import a PSD file and return its complete layer tree with rasterized thumbnails.

    Body: { "psd_path": "E:/path/to/file.psd", "thumbnail_size": 256 }
    Returns: {
        "success": true,
        "width": 2048, "height": 2048,
        "layers": [
            {
                "name": "Paintable Area", "kind": "group", "visible": true, "opacity": 255,
                "bbox": [0, 0, 2048, 2048],
                "children": [
                    { "name": "Base Paint", "kind": "pixel", "visible": true, "opacity": 255,
                      "bbox": [0, 0, 2048, 2048],
                      "thumbnail": "data:image/png;base64,...",
                      "full_image": "data:image/png;base64,..." }
                ]
            }
        ],
        "composite": "data:image/png;base64,..."  // Full flattened composite
    }
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        psd_path = data.get('psd_path', '')
        thumb_size = int(data.get('thumbnail_size', 256))
        ok, _req_err = _require_spb_internal_request()
        if not ok:
            return jsonify({"error": _req_err}), 403

        # BUG #70 (Bigelow, HIGH): pre-fix, this route accepted any path
        # and only checked os.path.exists(). Attacker on the same host (or
        # a misconfigured CORS/loopback setup) could read any PSD on the
        # server user's disk and receive a base64 composite of it.
        # Sanitize + restrict extension before touching the filesystem.
        psd_path, _err = _sanitize_path(psd_path)
        if _err:
            return jsonify({"error": _err}), 400
        if not psd_path.lower().endswith('.psd'):
            return jsonify({"error": "Only .psd files are allowed"}), 400
        if not os.path.exists(psd_path):
            return jsonify({"error": "PSD file not found"}), 404

        try:
            from psd_tools import PSDImage
        except ImportError:
            return jsonify({"error": "psd-tools not installed. Run: pip install psd-tools"}), 500

        psd = _get_cached_psd(psd_path)
        logger.info(f"[PSD Import] Opened {psd_path}: {psd.width}x{psd.height}, {len(psd)} top layers")

        import numpy as np
        from PIL import Image as PILImage

        def layer_to_dict(layer, include_full=True):
            """Convert a PSD layer to a serializable dict with optional rasterized image."""
            entry = {
                "name": layer.name,
                "kind": layer.kind,
                "visible": layer.visible,
                "opacity": layer.opacity,
                "bbox": list(layer.bbox) if hasattr(layer, 'bbox') else [0, 0, psd.width, psd.height],
            }

            # Blend mode
            if hasattr(layer, 'blend_mode'):
                entry["blend_mode"] = str(layer.blend_mode).replace('BlendMode.', '')

            # Group: recurse into children
            if layer.kind == 'group' or hasattr(layer, '__iter__'):
                entry["children"] = []
                try:
                    for child in layer:
                        entry["children"].append(layer_to_dict(child, include_full))
                except Exception:
                    pass
                return entry

            # Skip heavy per-layer rasterization on initial import (5+ seconds each)
            # Layers are rasterized on demand via /api/psd-layer endpoint
            entry["has_pixels"] = True

            return entry

        # Build layer tree
        layers = []
        for layer in psd:
            layers.append(layer_to_dict(layer))

        # Full composite
        composite_b64 = None
        try:
            composite = psd.composite()
            buf = io.BytesIO()
            composite.save(buf, 'PNG')
            composite_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('ascii')
        except Exception as comp_err:
            logger.warning(f"[PSD Import] Composite failed: {comp_err}")

        logger.info(f"[PSD Import] Success: {len(layers)} top layers extracted")
        return jsonify({
            "success": True,
            "width": psd.width,
            "height": psd.height,
            "layers": layers,
            "composite": composite_b64,
            "psd_path": psd_path,
        })

    except Exception as e:
        logger.error(f"/api/psd-import failed: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


_psd_cache = {}  # { path: (mtime, PSDImage) }

def _get_cached_psd(psd_path):
    """Get a PSD file from cache, or open and cache it."""
    from psd_tools import PSDImage
    mtime = os.path.getmtime(psd_path)
    if psd_path in _psd_cache and _psd_cache[psd_path][0] == mtime:
        return _psd_cache[psd_path][1]
    psd = PSDImage.open(psd_path)
    _psd_cache[psd_path] = (mtime, psd)
    # Keep cache small — only 3 PSDs max
    if len(_psd_cache) > 3:
        oldest = next(iter(_psd_cache))
        del _psd_cache[oldest]
    return psd


@app.route('/api/psd-rasterize-all', methods=['POST'])
def api_psd_rasterize_all():
    """Rasterize ALL pixel layers from a PSD, returning them as base64 images.
    This is the heavy operation — may take 30-60 seconds for large PSDs.
    Results are cached on the server.

    Body: { "psd_path": "..." }
    Returns: { "success": true, "layers": { "path/to/layer": { "image": "data:...", "bbox": [...], "size": [...] } } }
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        psd_path = data.get('psd_path', '')
        ok, _req_err = _require_spb_internal_request()
        if not ok:
            return jsonify({"error": _req_err}), 403
        # BUG #70: same path-traversal surface as /api/psd-import. Sanitize.
        psd_path, _err = _sanitize_path(psd_path)
        if _err:
            return jsonify({"error": _err}), 400
        if not psd_path.lower().endswith('.psd'):
            return jsonify({"error": "Only .psd files are allowed"}), 400
        if not os.path.exists(psd_path):
            return jsonify({"error": "PSD not found"}), 404

        psd = _get_cached_psd(psd_path)
        result_layers = {}

        def rasterize_tree(layer, path_prefix=""):
            """Recursively rasterize all pixel layers."""
            for child in layer:
                full_path = f"{path_prefix}/{child.name}" if path_prefix else child.name
                if child.kind == 'group' or hasattr(child, '__iter__'):
                    try:
                        rasterize_tree(child, full_path)
                    except Exception:
                        pass
                else:
                    # Pixel/type/shape layer — rasterize
                    try:
                        # Force-rasterize even hidden layers by temporarily setting visible
                        was_visible = child.visible
                        if not was_visible:
                            child.visible = True
                        img = child.composite(force=True)
                        if not was_visible:
                            child.visible = False
                        if img is None or img.size[0] == 0:
                            continue
                        buf = io.BytesIO()
                        img.save(buf, 'PNG')
                        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
                        result_layers[full_path] = {
                            "image": f"data:image/png;base64,{b64}",
                            "bbox": list(child.bbox),
                            "size": [img.width, img.height],
                            "visible": child.visible,
                            "opacity": child.opacity,
                        }
                        logger.info(f"[PSD Rasterize] {full_path}: {img.size}")
                    except Exception as layer_err:
                        logger.warning(f"[PSD Rasterize] Skip {full_path}: {layer_err}")

        t0 = time.time()
        rasterize_tree(psd)
        elapsed = time.time() - t0
        logger.info(f"[PSD Rasterize] Done: {len(result_layers)} layers in {elapsed:.1f}s")

        return jsonify({
            "success": True,
            "layers": result_layers,
            "count": len(result_layers),
            "elapsed_ms": round(elapsed * 1000),
        })
    except Exception as e:
        logger.error(f"/api/psd-rasterize-all failed: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/psd-layer', methods=['POST'])
def api_psd_layer():
    """Rasterize a specific layer from a PSD file on demand.

    Body: { "psd_path": "...", "layer_path": ["Paintable Area", "Base Paint"] }
    Returns: { "success": true, "image": "data:image/png;base64,..." }
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        psd_path = data.get('psd_path', '')
        layer_path = data.get('layer_path', [])
        ok, _req_err = _require_spb_internal_request()
        if not ok:
            return jsonify({"error": _req_err}), 403

        # BUG #70: same path-traversal surface as /api/psd-import. Sanitize.
        psd_path, _err = _sanitize_path(psd_path)
        if _err:
            return jsonify({"error": _err}), 400
        if not psd_path.lower().endswith('.psd'):
            return jsonify({"error": "Only .psd files are allowed"}), 400
        if not os.path.exists(psd_path):
            return jsonify({"error": "PSD not found"}), 404

        psd = _get_cached_psd(psd_path)

        # Navigate to the requested layer by path
        current = psd
        for name in layer_path:
            found = None
            for child in current:
                if child.name == name:
                    found = child
                    break
            if found is None:
                return jsonify({"error": f"Layer '{name}' not found"}), 404
            current = found

        # Rasterize
        img = current.composite()
        if img is None:
            return jsonify({"error": "Layer could not be rasterized"}), 500

        buf = io.BytesIO()
        img.save(buf, 'PNG')
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')

        return jsonify({
            "success": True,
            "image": f"data:image/png;base64,{b64}",
            "size": [img.width, img.height],
            "bbox": list(current.bbox) if hasattr(current, 'bbox') else [0, 0, img.width, img.height],
        })
    except Exception as e:
        logger.error(f"/api/psd-layer failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/dual-shift-preview', methods=['POST'])
def api_dual_shift_preview():
    """Generate a quick swatch preview of a custom dual color shift.

    Body: {
        "color_a": [R, G, B],      // 0-255 integers or 0.0-1.0 floats
        "color_b": [R, G, B],
        "shift_intensity": 0.8,     // 0.0-1.0, default 1.0
        "size": 256                 // preview px, default 256
    }
    Returns: base64 PNG of the shift swatch (paint + spec side-by-side).
    """
    import numpy as np
    try:
        data = request.get_json(force=True, silent=True) or {}
        raw_a = data.get('color_a', [255, 50, 140])
        raw_b = data.get('color_b', [255, 230, 25])
        intensity = float(data.get('shift_intensity', 1.0))
        sz = int(data.get('size', 256))
        sz = max(64, min(512, sz))

        # Normalize colors to 0-1
        def _norm(c):
            c = [float(x) for x in c]
            if any(x > 1.0 for x in c):
                c = [x / 255.0 for x in c]
            return tuple(np.clip(c, 0, 1))

        ca = _norm(raw_a)
        cb = _norm(raw_b)

        from engine.dual_color_shift import (
            spec_dual_shift, paint_dual_shift, _dual_shift_field
        )

        shape = (sz, sz)
        mask = np.ones(shape, dtype=np.float32)
        seed = 42

        # Generate spec map swatch
        spec = spec_dual_shift(shape, mask, seed, 1.0,
                               color_a=ca, color_b=cb,
                               shift_intensity=intensity)

        # Generate paint swatch — start with mid-grey canvas
        paint = np.full((sz, sz, 3), 0.5, dtype=np.float32)
        bb = np.zeros(shape, dtype=np.float32)
        paint = paint_dual_shift(paint, shape, mask, seed, 1.0, bb,
                                 color_a=ca, color_b=cb,
                                 shift_intensity=intensity)

        # Build side-by-side: paint | spec
        paint_u8 = (np.clip(paint[:, :, :3], 0, 1) * 255).astype(np.uint8)
        spec_vis = np.zeros((sz, sz, 3), dtype=np.uint8)
        spec_vis[:, :, 0] = spec[:, :, 0]  # M → red
        spec_vis[:, :, 1] = spec[:, :, 1]  # R → green
        spec_vis[:, :, 2] = spec[:, :, 2]  # CC → blue

        combined = np.concatenate([paint_u8, spec_vis], axis=1)

        from PIL import Image as PILImage
        img = PILImage.fromarray(combined, 'RGB')
        buf = io.BytesIO()
        img.save(buf, 'PNG', optimize=True)
        buf.seek(0)
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')

        return jsonify({
            "success": True,
            "preview": f"data:image/png;base64,{b64}",
            "color_a": list(ca),
            "color_b": list(cb),
            "intensity": intensity,
        })
    except Exception as e:
        logger.error(f"/api/dual-shift-preview failed: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/dual-shift-register', methods=['POST'])
def api_dual_shift_register():
    """Register a custom dual shift as a temporary monolithic finish.

    Body: {
        "color_a": [R, G, B],
        "color_b": [R, G, B],
        "shift_intensity": 1.0,
        "name": "My Custom Shift"   // optional display name
    }
    Returns: { "finish_id": "dualshift_custom_XXXXXX" }

    The registered finish can then be used as zone.finish in /preview-render and /render.
    """
    import numpy as np
    try:
        data = request.get_json(force=True, silent=True) or {}
        raw_a = data.get('color_a', [255, 50, 140])
        raw_b = data.get('color_b', [255, 230, 25])
        intensity = float(data.get('shift_intensity', 1.0))
        name = data.get('name', 'Custom Dual Shift')

        def _norm(c):
            c = [float(x) for x in c]
            if any(x > 1.0 for x in c):
                c = [x / 255.0 for x in c]
            return tuple(np.clip(c, 0, 1))

        ca = _norm(raw_a)
        cb = _norm(raw_b)

        from engine.dual_color_shift import spec_dual_shift, paint_dual_shift
        import shokker_engine_v2 as eng

        # Create a unique ID from the color values
        _hash = hash((ca, cb, intensity)) & 0xFFFFFF
        finish_id = f"dualshift_custom_{_hash:06x}"

        # Build spec and paint functions for this color pair
        def _spec(shape, mask, seed, sm, _ca=ca, _cb=cb, _int=intensity):
            return spec_dual_shift(shape, mask, seed, sm,
                                   color_a=_ca, color_b=_cb,
                                   shift_intensity=_int)

        def _paint(paint, shape, mask, seed, pm, bb, _ca=ca, _cb=cb, _int=intensity):
            return paint_dual_shift(paint, shape, mask, seed, pm, bb,
                                    color_a=_ca, color_b=_cb,
                                    shift_intensity=_int)

        # Register into the engine's monolithic registry
        if hasattr(eng, 'MONOLITHIC_REGISTRY'):
            eng.MONOLITHIC_REGISTRY[finish_id] = (_spec, _paint)
            logger.info(f"Registered custom dual shift: {finish_id} ({name}) "
                        f"A={ca} B={cb} int={intensity}")
        else:
            return jsonify({"error": "Engine registry not available"}), 500

        return jsonify({
            "success": True,
            "finish_id": finish_id,
            "name": name,
            "color_a": list(ca),
            "color_b": list(cb),
            "intensity": intensity,
        })
    except Exception as e:
        logger.error(f"/api/dual-shift-register failed: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/finish-registry-status', methods=['GET'])
def api_finish_registry_status():
    """Return which finish IDs are registered in the engine vs. unregistered.
    Used by the UI to show warning badges on placeholder finishes."""
    try:
        from shokker_engine_v2 import MONOLITHIC_REGISTRY, BASE_REGISTRY, PATTERN_REGISTRY
        registered = set()
        registered.update(MONOLITHIC_REGISTRY.keys())
        registered.update(BASE_REGISTRY.keys())
        registered.update(PATTERN_REGISTRY.keys())
        return jsonify({
            "registered": sorted(registered),
            "count": len(registered),
            "mono": len(MONOLITHIC_REGISTRY),
            "base": len(BASE_REGISTRY),
            "pattern": len(PATTERN_REGISTRY),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/finish-data', methods=['GET'])
def api_finish_data():
    """Serve the full finish catalogue as JSON.

    The HTML fetches this once at startup and uses it to build:
      - Base dropdown (BASES array)
      - Pattern dropdown (PATTERNS array)
      - Special/Monolithic picker (SPECIALS array)
      - Category group map for UI organisation

    Query params:
      ?nocache=1   - force rebuild even if cached (dev use only)
      ?type=bases  - return only one registry type
    """
    global _FINISH_DATA_CACHE
    logger.info(f"[finish-data] Requested (nocache={request.args.get('nocache')}, type={request.args.get('type')})")
    try:
        force = request.args.get("nocache") == "1"
        if _FINISH_DATA_CACHE is None or force:
            logger.debug("[finish-data] Building payload from registries")
            _FINISH_DATA_CACHE = _build_finish_data_payload()
        payload = _FINISH_DATA_CACHE

        # Optional filter by type
        filter_type = request.args.get("type")
        if filter_type and filter_type in payload:
            resp = jsonify({"status": "ok", filter_type: payload[filter_type],
                            "count": len(payload[filter_type])})
        else:
            resp = jsonify({"status": "ok", **payload})

        # Cache for 5 minutes — registries are stable per server lifetime,
        # but a short cache lets clients get updates after /api/reload-engine.
        for k, v in _short_cache_headers.items():
            resp.headers[k] = v
        return resp
    except Exception as e:
        logger.error(f"/api/finish-data failed: {e}\n{traceback.format_exc()}")
        return jsonify({"status": "error", "error": str(e)}), 500


def apply_paint_recolor(paint_file, rules, job_dir, mask_rle=None, mask_has_include=False):
    """Apply recolor rules to a paint file, saving a recolored copy.

    Each rule: {"source_rgb": [R,G,B], "target_rgb": [R,G,B], "tolerance": 40, "hue_shift": true}
    Uses HSV hue-shift to preserve shading (dark red → dark green, etc.)
    Optional mask_rle: RLE-encoded spatial mask (0=unset, 1=include, 2=exclude).
    Returns path to the recolored file.
    """
    import numpy as np
    from PIL import Image as PILImage
    import colorsys

    img = PILImage.open(paint_file).convert('RGB')
    pixels = np.array(img, dtype=np.float32)
    original = pixels.copy()
    h, w = pixels.shape[:2]

    # Decode spatial mask if provided
    # Format from client: {width, height, runs: [[value, count], ...]}
    spatial_mask = None
    if mask_rle and isinstance(mask_rle, dict) and "runs" in mask_rle:
        try:
            runs = mask_rle["runs"]
            spatial_mask = np.zeros(w * h, dtype=np.uint8)
            idx = 0
            for run in runs:
                val = int(run[0])
                count = int(run[1])
                end = min(idx + count, len(spatial_mask))
                spatial_mask[idx:end] = val
                idx = end
            spatial_mask = spatial_mask.reshape(h, w)
        except Exception as e:
            logger.warning(f"Recolor mask decode failed: {e}")
            spatial_mask = None

    for rule in rules:
        src = np.array(rule["source_rgb"], dtype=np.float32)
        tgt = np.array(rule["target_rgb"], dtype=np.float32)
        tol = float(rule.get("tolerance", 40))
        use_hue_shift = rule.get("hue_shift", True)

        # Build color mask: Euclidean RGB distance (same scaling as client-side)
        diff = original - src[np.newaxis, np.newaxis, :]
        dist_sq = np.sum(diff ** 2, axis=-1)
        mask = dist_sq <= (tol * tol * 3)

        # Apply spatial mask if present
        if spatial_mask is not None:
            # Exclude pixels marked as 2
            mask = mask & (spatial_mask != 2)
            # If include mode active, restrict to included pixels only
            if mask_has_include:
                mask = mask & (spatial_mask == 1)

        if not np.any(mask):
            continue

        if use_hue_shift:
            # Compute HSV deltas
            src_hsv = colorsys.rgb_to_hsv(src[0] / 255, src[1] / 255, src[2] / 255)
            tgt_hsv = colorsys.rgb_to_hsv(tgt[0] / 255, tgt[1] / 255, tgt[2] / 255)
            h_delta = tgt_hsv[0] - src_hsv[0]  # 0-1 range
            s_delta = tgt_hsv[1] - src_hsv[1]
            v_delta = tgt_hsv[2] - src_hsv[2]

            # Vectorized HSV shift on matched pixels
            matched = original[mask] / 255.0
            r_ch, g_ch, b_ch = matched[:, 0], matched[:, 1], matched[:, 2]
            maxc = np.maximum(np.maximum(r_ch, g_ch), b_ch)
            minc = np.minimum(np.minimum(r_ch, g_ch), b_ch)
            delta_c = maxc - minc

            # RGB → H
            hue = np.zeros_like(r_ch)
            nonzero = delta_c > 1e-6
            m_r = (maxc == r_ch) & nonzero
            m_g = (maxc == g_ch) & nonzero & ~m_r
            m_b = nonzero & ~m_r & ~m_g
            hue[m_r] = (((g_ch[m_r] - b_ch[m_r]) / delta_c[m_r]) % 6) / 6.0
            hue[m_g] = (((b_ch[m_g] - r_ch[m_g]) / delta_c[m_g]) + 2) / 6.0
            hue[m_b] = (((r_ch[m_b] - g_ch[m_b]) / delta_c[m_b]) + 4) / 6.0

            sat = np.where(maxc > 0, delta_c / maxc, 0)
            val = maxc

            # Apply shifts
            new_h = (hue + h_delta) % 1.0
            new_s = np.clip(sat + s_delta, 0, 1)
            new_v = np.clip(val + v_delta, 0, 1)

            # HSV → RGB using engine's vectorized function
            new_r, new_g, new_b = engine.hsv_to_rgb_vec(new_h, new_s, new_v)
            pixels[mask, 0] = new_r * 255
            pixels[mask, 1] = new_g * 255
            pixels[mask, 2] = new_b * 255
        else:
            pixels[mask] = tgt

    recolored = np.clip(pixels, 0, 255).astype(np.uint8)
    recolored_path = os.path.join(job_dir, "recolored_paint.tga")
    engine.write_tga_24bit(recolored_path, recolored)
    return recolored_path


def numpy_to_base64_png(arr):
    """Convert a numpy uint8 array to a base64-encoded PNG data URI.
    Uses cv2 with fast compression (level 1) instead of PIL default (level 6).
    ~3-5x faster encoding for preview images with negligible size increase."""
    import cv2 as _cv2
    import numpy as _np
    a = _np.asarray(arr)
    # cv2.imencode expects BGR(A), but our arrays are RGB(A) -- convert
    if a.ndim == 3:
        if a.shape[2] == 4:
            a = _cv2.cvtColor(a, _cv2.COLOR_RGBA2BGRA)
        elif a.shape[2] == 3:
            a = _cv2.cvtColor(a, _cv2.COLOR_RGB2BGR)
    # PNG compression level 1 (fast) -- level 0 is no compression (huge),
    # level 9 is max compression (slow). Level 1 is ~4x faster than default 3.
    ok, png_bytes = _cv2.imencode('.png', a, [_cv2.IMWRITE_PNG_COMPRESSION, 1])
    if not ok:
        # Fallback to PIL if cv2 fails
        from PIL import Image as PILImage
        img = PILImage.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        png_bytes = buf.getvalue()
    else:
        png_bytes = png_bytes.tobytes()
    b64 = base64.b64encode(png_bytes).decode('ascii')
    return f"data:image/png;base64,{b64}"


def _spec_array_to_rgba_uint8(arr):
    """Normalize spec array to (H, W, 4) uint8 for PNG encoding. Handles float, 3-chan, shape issues.
    Optimized: pre-allocates output array instead of concatenating/stacking."""
    import numpy as _np
    if arr is None or not hasattr(arr, 'shape') or arr.size == 0:
        return None
    a = _np.asarray(arr)
    if a.ndim == 2:
        # Grayscale -> RGBA: pre-allocate and fill channels (avoids 4 temp arrays from stack)
        h, w = a.shape
        out = _np.empty((h, w, 4), dtype=_np.uint8)
        if a.dtype != _np.uint8:
            gray = _np.clip(a, 0, 255).astype(_np.uint8)
        else:
            gray = a
        out[:, :, 0] = gray
        out[:, :, 1] = gray
        out[:, :, 2] = gray
        out[:, :, 3] = 255
        return out
    elif a.ndim == 3 and a.shape[-1] == 3:
        # RGB -> RGBA: pre-allocate with alpha=255 (avoids concatenate temp array)
        h, w = a.shape[:2]
        out = _np.empty((h, w, 4), dtype=_np.uint8)
        if a.dtype != _np.uint8:
            out[:, :, :3] = _np.clip(a, 0, 255).astype(_np.uint8)
        else:
            out[:, :, :3] = a
        out[:, :, 3] = 255
        return out
    if a.dtype != _np.uint8:
        a = _np.clip(a, 0, 255).astype(_np.uint8)
    if a.shape[-1] != 4:
        return None
    return a


# ================================================================
# PATTERN LAYER - pattern-only image for Photoshop-style overlay
# ================================================================
@app.route('/api/pattern-layer', methods=['GET'])
def api_pattern_layer():
    """Return the pattern texture as PNG for client overlay (place-on-map).
    Query: pattern=<id>, w=<int>, h=<int>, scale=<float>, rotation=<float>, seed=<int>
    Pattern is rendered at neutral offset (0.5,0.5); client applies position via transform."""
    from flask import Response as FlaskResponse
    import numpy as np
    from PIL import Image as PILImage
    try:
        pattern_id = (request.args.get('pattern') or '').strip() or None
        if not pattern_id or pattern_id.lower() == 'none':
            return jsonify({"error": "pattern required"}), 400
        w = max(64, min(4096, int(request.args.get('w', 2048))))
        h = max(64, min(4096, int(request.args.get('h', 2048))))
        scale = max(0.1, min(10.0, float(request.args.get('scale', 1.0))))
        rotation = float(request.args.get('rotation', 0))
        seed = int(request.args.get('seed', 42))
    except (TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid query: {e}"}), 400
    try:
        from engine.compose import _get_pattern_mask
        shape = (int(h), int(w))
        mask = np.ones(shape, dtype=np.float32)
        pv = _get_pattern_mask(
            pattern_id, shape, mask, seed=seed, sm=1.0,
            scale=scale, rotation=rotation, opacity=1.0, strength=1.0,
            offset_x=0.5, offset_y=0.5
        )
        if pv is None:
            return jsonify({"error": "pattern not found or failed to generate"}), 404
        arr = (np.clip(pv, 0, 1) * 255).astype(np.uint8)
        rgba = np.stack([arr, arr, arr, np.full_like(arr, 255)], axis=-1)
        buf = io.BytesIO()
        PILImage.fromarray(rgba).save(buf, format='PNG')
        buf.seek(0)
        return FlaskResponse(buf.getvalue(), mimetype='image/png', headers={'Cache-Control': 'no-store'})
    except Exception as e:
        logger.warning(f"/api/pattern-layer failed: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


# ================================================================
# SWATCH THUMBNAILS - engine-accurate per-finish rendered patches
# ================================================================

# In-memory swatch cache: cache_key → raw PNG bytes
_SWATCH_CACHE = {}
_SWATCH_CACHE_LOCK = __import__('threading').Lock()

# Distinct saturated hues so default-neutral swatches don't all look silver/gray
_SWATCH_HUE_PALETTE = (
    'cc2244', '2288cc', '44aa44', 'cc8822', '8844aa', '22aacc', 'aa4422', '4488aa',
    '66cc22', 'cc44aa', '228844', 'aa8822', '6644cc', '44cc88', 'cc6644', '88aa44',
)


def _swatch_display_color(finish_type, finish_key, color_hex):
    """When the requested color is the default neutral, return a deterministic per-finish
    hue so thumbnails look distinct instead of all silver/gray."""
    neutral = (color_hex or '').lower().replace('#', '').strip()
    if neutral in ('888888', '555577', '446688'):
        idx = hash((finish_type, finish_key)) % len(_SWATCH_HUE_PALETTE)
        return _SWATCH_HUE_PALETTE[idx]
    return color_hex


def _render_swatch_bytes(finish_type, finish_key, color_hex, size, seed):
    """Render a single swatch patch using the actual engine. Returns raw PNG bytes.

    finish_type: 'base' | 'pattern' | 'monolithic'
    finish_key:  key in the relevant registry
    color_hex:   6-char hex string (no #), e.g. '888888'
    size:        pixel dimension (square), 32-256
    seed:        noise seed

    Registry formats:
      BASE_REGISTRY entry     - dict with M, R, CC (0-255 ints), paint_fn
      PATTERN_REGISTRY entry  - dict with texture_fn, paint_fn
      MONOLITHIC_REGISTRY     - tuple (spec_fn, paint_fn) OR dict
    """
    import numpy as np

    # Use per-finish display color when default neutral so thumbnails look distinct
    color_hex = _swatch_display_color(finish_type, finish_key, color_hex)

    # Parse the hint color
    try:
        r = int(color_hex[0:2], 16) / 255.0
        g = int(color_hex[2:4], 16) / 255.0
        b = int(color_hex[4:6], 16) / 255.0
    except Exception:
        r, g, b = 0.533, 0.533, 0.533

    # Monolithic multi-color (Color Shift Duo, Chameleon, FUSIONS): noise/gradient needs resolution
    # At 48px the structural noise is ~1 sample → single flat color. ALWAYS render at 256 then downscale.
    mono_reg = getattr(engine, 'MONOLITHIC_REGISTRY', {})
    base_reg = getattr(engine, 'BASE_REGISTRY', {})
    is_base_but_mono = finish_type == 'base' and finish_key not in base_reg and (finish_key and finish_key in mono_reg)
    internal_size = size
    # Audited Color Shift + Effect & Visual: always use 256px for swatch so thumbnail and render match
    _SWATCH_256_FINISHES = frozenset([
        "cs_split", "cs_triadic", "cs_chrome_shift", "cs_earth", "cs_monochrome",
        "cs_neon_shift", "cs_ocean_shift", "cs_prism_shift", "cs_vivid",
        "cel_shade", "depth_map", "double_exposure", "glitch", "infrared", "phantom", "polarized", "x_ray",
        "chromatic_aberration", "crt_scanline", "datamosh", "embossed", "film_burn", "fish_eye",
        "halftone", "long_exposure", "negative", "parallax", "refraction", "solarization",
    ])
    if size < 256 and finish_key and finish_key in _SWATCH_256_FINISHES:
        internal_size = 256
        logger.debug(f"Swatch 256px (audited): {finish_key} (requested size={size})")
    elif size <= 96 and (finish_type == 'monolithic' or is_base_but_mono):
        internal_size = 256
        logger.debug(f"Swatch monolithic at 256px then downscale: {finish_type}/{finish_key} (requested size={size})")

    shape = (internal_size, internal_size)
    mask  = np.ones(shape, dtype=np.float32)

    # Build base paint canvas (RGBA float32, 0-1)
    paint = np.zeros((*shape, 4), dtype=np.float32)
    paint[:, :, 0] = r
    paint[:, :, 1] = g
    paint[:, :, 2] = b
    paint[:, :, 3] = 1.0

    # ── Spec-map visualisation helper ──────────────────────────────────────
    # Converts iRacing spec map values (M=metallic 0-255, R=roughness 0-255,
    # CC 0-255 where 16=max gloss) into visible brightness/texture so that
    # similar-looking metallic/matte/chrome bases are clearly distinguishable.
    def _apply_spec_visual(paint_arr, M_val, R_val, CC_val):
        M = np.clip(M_val / 255.0, 0, 1)   # 0=dielectric, 1=full metal
        R = np.clip(R_val / 255.0, 0, 1)   # 0=mirror, 1=fully matte
        # CC: 16=max gloss, 0=fully metallised, >16=progressively degraded
        CC_norm = 1.0 - np.clip((max(CC_val, 16) - 16) / 239.0, 0, 1)  # 1=gloss, 0=degraded

        # Metallic: light desaturate so base color still reads (was 0.55 → too gray)
        if M > 0.3:
            grey = paint_arr[:, :, :3].mean(axis=2, keepdims=True)
            desat = M * 0.26
            paint_arr[:, :, :3] = paint_arr[:, :, :3] * (1 - desat) + grey * desat
            # Bright highlight sweeping across top (simulates environment map)
            yy = np.linspace(1.0, 0.0, size, dtype=np.float32)[:, np.newaxis]
            highlight = np.clip(yy * M * 0.50, 0, 0.40)
            paint_arr[:, :, :3] = np.clip(
                paint_arr[:, :, :3] + highlight[:, :, np.newaxis], 0, 1)

        # Roughness: darken + add micro-grain for matte/rough surfaces
        if R > 0.35:
            matte_factor = (R - 0.35) / 0.65 * 0.38
            paint_arr[:, :, :3] = np.clip(paint_arr[:, :, :3] - matte_factor, 0, 1)
            if R > 0.65:
                rng_g = np.random.RandomState(seed + 7)
                grain_strength = (R - 0.65) / 0.35 * 0.07
                grain = rng_g.uniform(-grain_strength, grain_strength,
                                      (*shape, 1)).astype(np.float32)
                paint_arr[:, :, :3] = np.clip(paint_arr[:, :, :3] + grain, 0, 1)

        # Clearcoat degradation: dull the surface when CC is beyond 16 (max gloss)
        if CC_norm < 0.75:
            dull = (0.75 - CC_norm) / 0.75 * 0.28
            paint_arr[:, :, :3] = np.clip(paint_arr[:, :, :3] - dull, 0, 1)

        return paint_arr

    # ── Helper: extract fns from monolithic tuple or dict ──────────────────
    def _get_mono_fns(entry):
        if isinstance(entry, (tuple, list)) and len(entry) >= 2:
            return entry[0], entry[1]
        if isinstance(entry, dict):
            return entry.get('spec_fn'), entry.get('paint_fn')
        if callable(entry):
            return None, entry
        return None, None

    def _mono_opt(entry, key, default=None):
        """Get optional field from monolithic entry only if it's a dict (avoids tuple.get)."""
        return entry.get(key, default) if isinstance(entry, dict) else default

    def _try_generic_finish_swatch(fk, p, shp, msk, sd, hex_val, rr, gg, bb):
        """Try render_generic_finish for monolithic swatch. Modifies p in place. Returns True if successful."""
        if not fk:
            return False
        try:
            fc = None
            try:
                from finish_colors_lookup import get_finish_colors
                fc = get_finish_colors(fk)
            except Exception:
                pass
            if not fc:
                color_with_hash = '#' + (hex_val if len(hex_val) >= 6 else '888888')
                darker = np.clip(np.array([rr, gg, bb], dtype=np.float32) * 0.35, 0, 1)
                darker_hex = ''.join(format(int(round(x * 255)), '02x') for x in darker)
                fc = {"c1": color_with_hash, "c2": '#' + darker_hex}
                if fk.startswith('grad3_'):
                    mid = np.clip(np.array([rr, gg, bb], dtype=np.float32) * 0.7, 0, 1)
                    fc["c3"] = '#' + ''.join(format(int(round(x * 255)), '02x') for x in mid)
            zone_fake = {"finish": fk, "finish_colors": fc}
            spec_out, paint_out = engine.render_generic_finish(
                fk, zone_fake, p, shp, msk, sd, 1.0, 1.0, 0.0
            )
            if paint_out is not None and hasattr(paint_out, 'shape'):
                if paint_out.ndim == 3 and paint_out.shape[2] >= 3:
                    p[:, :, :3] = np.clip(paint_out[:, :, :3], 0, 1)
                elif paint_out.ndim == 2:
                    p[:, :, 0] = p[:, :, 1] = p[:, :, 2] = np.clip(paint_out, 0, 1)
                return True
        except Exception as gen_err:
            logger.debug(f"Generic finish swatch [{fk}]: {gen_err}")
        return False

    def _apply_fallback_gradient(p_arr, shp, rr, gg, bb):
        """Simple vertical gradient fallback when render_generic_finish fails."""
        h, w = shp
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, np.newaxis]
        darker = np.clip(np.array([rr, gg, bb], dtype=np.float32) * 0.4, 0, 1)
        p_arr[:, :, 0] = rr * (1 - yy) + darker[0] * yy
        p_arr[:, :, 1] = gg * (1 - yy) + darker[1] * yy
        p_arr[:, :, 2] = bb * (1 - yy) + darker[2] * yy

    # If client sent "base" but this key is only in MONOLITHIC (e.g. Chameleon Classic), render as monolithic
    if finish_type == 'base' and finish_key not in engine.BASE_REGISTRY and finish_key in engine.MONOLITHIC_REGISTRY:
        finish_type = 'monolithic'

    try:
        # ── BASE: dict with M, R, CC, paint_fn, optional base_spec_fn ───────
        # NOTE: BASE_REGISTRY does NOT have spec_fn - spec is built from M/R/CC
        # Carbon & Composite bases use base_spec_fn for weave/chunk pattern - show it in swatch
        if finish_type == 'base' and finish_key in engine.BASE_REGISTRY:
            entry = engine.BASE_REGISTRY[finish_key]
            if isinstance(entry, dict):
                M_val    = entry.get('M',  100)
                R_val    = entry.get('R',  100)
                CC_val   = entry.get('CC', 16)
                paint_fn = entry.get('paint_fn')
                base_spec_fn = entry.get('base_spec_fn')
                # Apply the paint modulation function (flake, grain, shimmer etc.)
                if paint_fn and callable(paint_fn):
                    try:
                        paint = paint_fn(paint, shape, mask, seed, 1.0, 0.0)
                    except Exception:
                        pass
                # Carbon & Composite: run base_spec_fn to get spatial M/R pattern and show weave on swatch
                if base_spec_fn and callable(base_spec_fn):
                    try:
                        spec_result = base_spec_fn(shape, seed + abs(hash(finish_key)) % 10000, 1.0, M_val, R_val)
                        R_arr = np.asarray(spec_result[1], dtype=np.float32)
                        if R_arr.ndim == 2:
                            r_min, r_max = float(R_arr.min()), float(R_arr.max())
                            pat = 1.0 - np.clip((R_arr - r_min) / (r_max - r_min + 1e-8), 0, 1)
                            # Stronger modulation (0.35–1.0) so weave/chunks are clearly visible
                            fac = np.clip(0.35 + 0.65 * pat[:, :, np.newaxis], 0, 1)
                            m3 = mask[:, :, np.newaxis]
                            paint[:, :, :3] = np.clip(paint[:, :, :3] * fac * m3 + paint[:, :, :3] * (1.0 - m3), 0, 1)
                    except Exception as _bs_err:
                        logger.debug(f"Base base_spec_fn swatch [{finish_key}]: {_bs_err}")
                # Overlay spec-map visual so chrome vs matte vs metallic are distinct
                paint = _apply_spec_visual(paint, M_val, R_val, CC_val)

        # ── PATTERN: dict with texture_fn + paint_fn, or image_path ─────────
        # texture_fn generates the spec-layer pattern structure (the actual visual)
        # image_path: load grayscale PNG for image-based patterns (Music Inspired, etc.)
        elif finish_type == 'pattern' and finish_key in engine.PATTERN_REGISTRY:
            entry      = engine.PATTERN_REGISTRY[finish_key]
            texture_fn = entry.get('texture_fn') if isinstance(entry, dict) else None
            paint_fn   = entry.get('paint_fn')   if isinstance(entry, dict) else None
            image_path = entry.get('image_path') if isinstance(entry, dict) else None

            # Use a mid-metallic-gray base so pattern structure is clearly visible
            paint = _apply_spec_visual(paint, 160, 35, 16)

            # image_path: load PNG and use as pattern_val (white=peaks, black=valleys)
            if image_path and not texture_fn:
                try:
                    from engine.render import _load_image_pattern
                    pv = _load_image_pattern(image_path, shape, scale=1.0, rotation=0.0)
                    if pv is not None:
                        pat = np.clip(pv, 0, 1)
                        bright = pat * 0.55
                        dark   = (1.0 - pat) * 0.32
                        paint[:, :, :3] = np.clip(
                            paint[:, :, :3]
                            + bright[:, :, np.newaxis]
                            - dark[:, :, np.newaxis], 0, 1)
                except Exception as img_err:
                    logger.debug(f"Pattern image_path swatch [{finish_key}]: {img_err}")

            # texture_fn is the primary visual - renders the actual spec pattern
            elif texture_fn and callable(texture_fn):
                try:
                    tex = texture_fn(shape, mask, seed, 1.0)
                    if isinstance(tex, dict):
                        pv    = tex.get('pattern_val')
                        M_pat = tex.get('M_pattern', pv)
                        R_pat = tex.get('R_pattern', pv)
                        M_range = tex.get('M_range', 60)

                        if pv is not None:
                            pat = np.clip(pv, 0, 1)
                            # Pattern peaks → bright; valleys → dark for clear structure
                            bright = pat * 0.55
                            dark   = (1.0 - pat) * 0.32
                            paint[:, :, :3] = np.clip(
                                paint[:, :, :3]
                                + bright[:, :, np.newaxis]
                                - dark[:, :, np.newaxis], 0, 1)

                            # Large M_range = metallic pattern → add chrome sheen to peaks
                            if abs(M_range) > 30 and M_pat is not None:
                                shine = np.clip(M_pat, 0, 1) * 0.28
                                paint[:, :, :3] = np.clip(
                                    paint[:, :, :3] + shine[:, :, np.newaxis], 0, 1)

                        elif isinstance(tex, np.ndarray):
                            # Raw array fallback
                            pv = np.clip(tex, 0, 1)
                            paint[:, :, :3] = np.clip(
                                paint[:, :, :3] * (0.5 + pv[:, :, np.newaxis] * 0.5), 0, 1)
                except Exception as tex_err:
                    logger.debug(f"Pattern texture_fn error [{finish_key}]: {tex_err}")

            # Paint modulation on top (colour tinting in grooves)
            if paint_fn and callable(paint_fn):
                try:
                    paint = paint_fn(paint, shape, mask, seed, 0.65, 0.0)
                except Exception:
                    pass

        # ── MONOLITHIC: grad/ghost/cs_duo/clr/mc - prefer render_generic_finish ──
        # Use finish_colors from JSON so thumbnails match real finish (fixes Ghost Gradient,
        # Gradient 3-Color, Gradient Mirror, etc.). Run BEFORE registry path for these prefixes.
        elif (finish_type == 'monolithic' and finish_key and
              any(finish_key.startswith(p) for p in ('grad_', 'grad3_', 'gradm_', 'ghostg_', 'clr_', 'cs_duo_', 'mc_'))):
            if not _try_generic_finish_swatch(finish_key, paint, shape, mask, seed, color_hex, r, g, b):
                _apply_fallback_gradient(paint, shape, r, g, b)

        # ── MONOLITHIC: tuple (spec_fn, paint_fn) from registry ──────────────
        elif finish_type == 'monolithic' and finish_key in engine.MONOLITHIC_REGISTRY:
            entry = engine.MONOLITHIC_REGISTRY[finish_key]
            spec_fn, paint_fn = _get_mono_fns(entry)

            # Handle dict-format monolithics (e.g. some fusions/expansions)
            baked_color = _mono_opt(entry, 'paint_color')
            if baked_color and len(baked_color) >= 3:
                bc = [float(v) for v in baked_color[:3]]
                if max(bc) > 1.0:
                    bc = [v / 255.0 for v in bc]  # normalise 0-255 → 0-1
                paint[:, :, 0] = bc[0]
                paint[:, :, 1] = bc[1]
                paint[:, :, 2] = bc[2]

            # Run spec_fn first (we need it for FUSIONS pattern and for optional spec_visual)
            spec_arr = None
            M_mean, R_mean, CC_mean = 128.0, 80.0, 16.0
            if spec_fn and callable(spec_fn):
                try:
                    spec_result = spec_fn(shape, mask, seed, 1.0)
                    spec_arr = _normalize_spec_result_to_rgba(spec_result, shape)
                    if spec_arr is not None:
                        M_mean  = float(spec_arr[:, :, 0].mean())
                        R_mean  = float(spec_arr[:, :, 1].mean())
                        CC_mean = float(spec_arr[:, :, 2].mean())
                except Exception as spec_err:
                    logger.debug(f"Monolithic spec_fn error [{finish_key}]: {spec_err}")

            # Run paint_fn on raw paint so Color Shift Duos and Chameleons get full-color output
            if paint_fn and callable(paint_fn):
                try:
                    paint = paint_fn(paint, shape, mask, seed, 1.0, 0.0)
                except Exception as pf_err:
                    logger.debug(f"Monolithic paint_fn error [{finish_key}]: {pf_err}")

            # FUSIONS only: use spec spatial variation so the fusion "pattern" is visible in the swatch.
            # Do NOT apply to Color Shift Duo / Chameleons - they are already two-tone; this would dim them.
            fusion_reg = getattr(engine, 'FUSION_REGISTRY', {})
            if finish_key in fusion_reg and spec_arr is not None and spec_arr.shape[:2] == shape:
                # Pattern from M and R channels (0-1) so structure shows as light/dark
                m_n = np.clip(spec_arr[:, :, 0] / 255.0, 0, 1)
                r_n = np.clip(spec_arr[:, :, 1] / 255.0, 0, 1)
                pat = np.clip(0.5 * (1.0 - r_n) + 0.5 * m_n, 0, 1)  # rough=dark, metal=bright
                pat = (pat - pat.min()) / (pat.max() - pat.min() + 1e-8)
                fac = np.clip(0.5 + 0.5 * pat[:, :, np.newaxis], 0, 1)  # stronger 0.5-1.0 so fusions pop
                m3 = mask[:, :, np.newaxis]
                paint[:, :, :3] = np.clip(paint[:, :, :3] * fac * m3 + paint[:, :, :3] * (1.0 - m3), 0, 1)
            # Any monolithic with spec but very flat paint (e.g. minimal paint_fn): add spec-based variation for thumbnails
            if spec_arr is not None and spec_arr.shape[:2] == shape:
                p_std = float(np.std(paint[:, :, :3]))
                if p_std < 0.08:
                    m_n = np.clip(spec_arr[:, :, 0] / 255.0, 0, 1)
                    r_n = np.clip(spec_arr[:, :, 1] / 255.0, 0, 1)
                    pat = np.clip(0.5 * (1.0 - r_n) + 0.5 * m_n, 0, 1)
                    pat = (pat - pat.min()) / (pat.max() - pat.min() + 1e-8)
                    fac = np.clip(0.7 + 0.3 * pat[:, :, np.newaxis], 0, 1)
                    m3 = mask[:, :, np.newaxis]
                    paint[:, :, :3] = np.clip(paint[:, :, :3] * fac * m3 + paint[:, :, :3] * (1.0 - m3), 0, 1)

            # Do NOT call _apply_spec_visual for monolithics - it desaturates and would wash out
            # Color Shift Duos, Chameleons, and gradients. Their paint_fn output is the thumbnail.

        # ── MONOLITHIC NOT IN REGISTRY ──
        # Use engine.render_generic_finish when possible; fallback to simple gradient.
        elif finish_type == 'monolithic':
            if not _try_generic_finish_swatch(finish_key, paint, shape, mask, seed, color_hex, r, g, b):
                _apply_fallback_gradient(paint, shape, r, g, b)

    except Exception as e:
        logger.warning(f"Swatch render error [{finish_type}/{finish_key}]: {e}")
        paint[:, :, :3] = 0.12  # Very dark grey - clearly not a normal swatch

    # Color identity blend for BASES and PATTERNS only - keeps a single hue visible so they
    # don't all read as silver/gray. Skip for MONOLITHICS: chameleon, gradients, color-shift,
    # fusions, etc. paint_fn outputs multi-color; blending with one tint would wash them out.
    if finish_type != 'monolithic':
        tint_strength = 0.38
        tint_rgb = np.array([r, g, b], dtype=np.float32).reshape(1, 1, 3)
        paint[:, :, :3] = np.clip(
            paint[:, :, :3] * (1.0 - tint_strength) + tint_rgb * tint_strength, 0, 1)

    # Downscale if we rendered monolithic at 256 for multi-color visibility
    if paint.shape[0] != size or paint.shape[1] != size:
        from PIL import Image as PILImage
        paint_rgb = np.nan_to_num(paint[:, :, :3], nan=0.0, posinf=1.0, neginf=0.0)
        rgb = np.clip(paint_rgb * 255, 0, 255).astype(np.uint8)
        img = PILImage.fromarray(rgb)
        img = img.resize((size, size), PILImage.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=True)
        return buf.getvalue()

    # Convert float32 RGBA → uint8 RGB, save as PNG (guard against NaNs from some finishes)
    paint_rgb = np.nan_to_num(paint[:, :, :3], nan=0.0, posinf=1.0, neginf=0.0)
    rgb = np.clip(paint_rgb * 255, 0, 255).astype(np.uint8)
    from PIL import Image as PILImage
    img = PILImage.fromarray(rgb)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _swatch_placeholder_png(size, split_mode=False):
    """Return a placeholder PNG (dark gray) when swatch render fails. Avoids 500 → broken image in UI."""
    from PIL import Image as PILImage
    w = (size * 2) if split_mode else size
    h = size
    # Dark gray so it's obvious it's a fallback but not bright
    img = PILImage.new('RGB', (w, h), (0x2a, 0x2a, 0x2a))
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _render_pattern_swatch_from_image_path(image_path, color_hex, size, seed):
    """Render a pattern swatch from an image path (same pipeline as PATTERN_REGISTRY image_path).
    image_path: path relative to V5 root (e.g. assets/patterns/for_review/foo.png).
    Returns PNG bytes. Used by /api/swatch/review so 'For Review' shows engine-accurate swatches.
    """
    import numpy as np
    try:
        r = int(color_hex[0:2], 16) / 255.0
        g = int(color_hex[2:4], 16) / 255.0
        b = int(color_hex[4:6], 16) / 255.0
    except Exception:
        r, g, b = 0.533, 0.533, 0.533
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.zeros((*shape, 4), dtype=np.float32)
    paint[:, :, 0] = r
    paint[:, :, 1] = g
    paint[:, :, 2] = b
    paint[:, :, 3] = 1.0
    # Same spec visual as pattern swatch (mid-metallic so structure is visible)
    M_val, R_val, CC_val = 160, 35, 16
    M = np.clip(M_val / 255.0, 0, 1)
    R = np.clip(R_val / 255.0, 0, 1)
    if M > 0.3:
        grey = paint[:, :, :3].mean(axis=2, keepdims=True)
        desat = M * 0.26
        paint[:, :, :3] = paint[:, :, :3] * (1 - desat) + grey * desat
        yy = np.linspace(1.0, 0.0, size, dtype=np.float32)[:, np.newaxis]
        highlight = np.clip(yy * M * 0.50, 0, 0.40)
        paint[:, :, :3] = np.clip(paint[:, :, :3] + highlight[:, :, np.newaxis], 0, 1)
    if R > 0.35:
        matte_factor = (R - 0.35) / 0.65 * 0.38
        paint[:, :, :3] = np.clip(paint[:, :, :3] - matte_factor, 0, 1)
        if R > 0.65:
            rng_g = np.random.RandomState(seed + 7)
            grain = rng_g.uniform(-0.07, 0.07, (*shape, 1)).astype(np.float32)
            paint[:, :, :3] = np.clip(paint[:, :, :3] + grain, 0, 1)
    # Load image pattern and apply peaks/valleys (same as pattern image_path in _render_swatch_bytes)
    try:
        from engine.render import _load_image_pattern
        pv = _load_image_pattern(image_path, shape, scale=1.0, rotation=0.0)
        if pv is not None:
            pat = np.clip(pv, 0, 1)
            bright = pat * 0.55
            dark = (1.0 - pat) * 0.32
            paint[:, :, :3] = np.clip(
                paint[:, :, :3] + bright[:, :, np.newaxis] - dark[:, :, np.newaxis], 0, 1)
    except Exception as img_err:
        logger.debug(f"Review swatch image_path [{image_path}]: {img_err}")
    # Color identity blend (same as bases/patterns in _render_swatch_bytes)
    tint_strength = 0.38
    tint_rgb = np.array([r, g, b], dtype=np.float32).reshape(1, 1, 3)
    paint[:, :, :3] = np.clip(
        paint[:, :, :3] * (1.0 - tint_strength) + tint_rgb * tint_strength, 0, 1)
    paint_rgb = np.nan_to_num(paint[:, :, :3], nan=0.0, posinf=1.0, neginf=0.0)
    rgb = np.clip(paint_rgb * 255, 0, 255).astype(np.uint8)
    from PIL import Image as PILImage
    img = PILImage.fromarray(rgb)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


@app.route('/api/for-review/list', methods=['GET'])
def api_for_review_list():
    """List pattern images in the For Review folder. Used by the app to show candidate patterns
    with engine-rendered swatches before adding them to PATTERNS and registry."""
    try:
        review_dir = getattr(CFG, 'PATTERN_FOR_REVIEW_DIR', None)
        if not review_dir or not os.path.isdir(review_dir):
            return jsonify({"items": [], "path": review_dir or ""})
        allowed = ('.png', '.jpg', '.jpeg')
        items = []
        for name in sorted(os.listdir(review_dir)):
            if name.startswith('.'):
                continue
            if os.path.splitext(name)[1].lower() in allowed:
                items.append({"id": os.path.splitext(name)[0], "filename": name})
        return jsonify({"items": items, "path": review_dir})
    except Exception as e:
        logger.warning(f"For-review list error: {e}")
        return jsonify({"items": [], "error": str(e)}), 500


@app.route('/api/swatch/review', methods=['GET'])
def api_swatch_review():
    """Render a pattern swatch using an image from the For Review folder (same pipeline as app).
    Params: image=<filename> (required), color=RRGGBB, size=64, seed=42."""
    from flask import Response as FlaskResponse
    filename = request.args.get('image', '').strip()
    if not filename:
        return jsonify({"error": "missing image parameter"}), 400
    # Only allow basename to prevent path traversal
    if os.path.basename(filename) != filename:
        return jsonify({"error": "invalid image parameter"}), 400
    review_dir = getattr(CFG, 'PATTERN_FOR_REVIEW_DIR', None)
    if not review_dir:
        return jsonify({"error": "For Review not configured"}), 500
    abs_path = os.path.join(review_dir, filename)
    if not os.path.isfile(abs_path):
        return jsonify({"error": "file not found", "image": filename}), 404
    # Path relative to V5 root for engine (same as PATTERN_REGISTRY image_path)
    rel_path = os.path.join("assets", "patterns", "for_review", filename).replace("\\", "/")
    color_hex = request.args.get('color', '888888').lstrip('#').ljust(6, '0')[:6]
    size = max(32, min(256, int(request.args.get('size', 64))))
    seed = int(request.args.get('seed', 42))
    try:
        png_bytes = _render_pattern_swatch_from_image_path(rel_path, color_hex, size, seed)
        return FlaskResponse(
            png_bytes,
            mimetype='image/png',
            headers={'Cache-Control': 'no-store, no-cache, must-revalidate', 'Pragma': 'no-cache'}
        )
    except Exception as e:
        logger.warning(f"Review swatch error [{filename}]: {e}")
        return FlaskResponse(
            _swatch_placeholder_png(size),
            mimetype='image/png',
            status=200
        )


@app.route('/api/swatch/<finish_type>/<finish_key>', methods=['GET'])
def api_swatch(finish_type, finish_key):
    """Return an engine-accurate swatch thumbnail as a PNG image.

    Params:
      ?color=RRGGBB   Hint color for bases/patterns (hex, no #). Default: 888888
      ?size=64        Square pixel size, clamped 32-256. Default: 64
      ?seed=42        Noise seed. Default: 42
      ?nocache=1      Bypass cache (dev use)
      ?mode=split     Returns 2x-wide image: left=neutral/dark (structure or base), right=with color.
                      Patterns: left=spec structure on dark gray, right=with user color.
                      Monolithics (FUSIONS, etc.): left=neutral 444444, right=user color (shows pattern + color).
                      Bases: left=neutral 444444, right=user color. Use for picker consistency.
    """
    from flask import Response as FlaskResponse
    color_hex = request.args.get('color', '888888').lstrip('#').ljust(6, '0')[:6]
    size      = max(32, min(256, int(request.args.get('size', 64))))
    seed      = int(request.args.get('seed', 42))
    nocache   = request.args.get('nocache') == '1'
    mode      = request.args.get('mode', '')
    cache_token = _swatch_cache_token()

    cache_key = f"{cache_token}:{finish_type}:{finish_key}:{color_hex}:{size}:{mode}"
    prefer = (request.args.get('prefer') or '').lower()
    # Correctness first: live engine swatches are the default. Static/prebuilt
    # thumbnails can hide rebuilt finish math behind old PNGs.
    prefer_live = prefer != 'static' and prefer != 'prerender'
    allow_prerender = not prefer_live

    # Permanent disk cache + browser cache. Swatches are tiny (2-5KB each).
    # Once rendered, saved to disk forever. Browser caches for 24h. ?v= busts on restart.
    _cache_headers = {'Cache-Control': 'public, max-age=86400, immutable'}

    # Disk cache path: thumbnails/swatch_cache/{type}_{key}_{color}_{size}_{mode}.png
    _swatch_cache_dir = os.path.join(THUMBNAIL_DIR, 'swatch_cache')
    _safe = (f"{cache_token}_{finish_type}_{finish_key}_{color_hex}_{size}_{mode}").replace('/', '_').replace('\\', '_').replace(':', '_')
    _disk_path = os.path.join(_swatch_cache_dir, _safe + '.png')

    # Check disk cache first (survives server restarts)
    if not nocache and os.path.isfile(_disk_path):
        try:
            with open(_disk_path, 'rb') as _df:
                return FlaskResponse(_df.read(), mimetype='image/png', headers=_cache_headers)
        except Exception:
            pass

    # Pre-rendered thumbnail (from rebuild_thumbnails.py)
    def _pre_path_for_key(key):
        safe = (key or '').replace('/', '_').replace('\\', '_').replace(':', '_').replace('-', '_').strip() or 'none'
        return os.path.join(THUMBNAIL_DIR, finish_type, safe + '.png')
    _pre_path = None
    if allow_prerender and mode != 'split' and finish_type in ('base', 'pattern', 'monolithic'):
        _safe_key = (finish_key or '').replace('/', '_').replace('\\', '_').replace(':', '_').strip() or 'none'
        _pre_path = os.path.join(THUMBNAIL_DIR, finish_type, _safe_key + '.png')
        if not os.path.isfile(_pre_path):
            alt_path = _pre_path_for_key(finish_key)
            if os.path.isfile(alt_path):
                _pre_path = alt_path

    if _pre_path is None or not os.path.isfile(_pre_path):
        # No pre-rendered file: use in-memory cache
        with _SWATCH_CACHE_LOCK:
            if not nocache and cache_key in _SWATCH_CACHE:
                return FlaskResponse(
                    _SWATCH_CACHE[cache_key],
                    mimetype='image/png',
                    headers=_cache_headers
                )

    # Pre-rendered thumbnail: serve when present; cache key includes file mtime so rebuild = fresh
    if allow_prerender and mode != 'split' and finish_type in ('base', 'pattern', 'monolithic'):
        if os.path.isfile(_pre_path):
            try:
                _mtime = int(os.path.getmtime(_pre_path))
                _prerender_cache_key = f"prerender:{finish_type}:{finish_key}:{size}:{_mtime}"
                with _SWATCH_CACHE_LOCK:
                    if _prerender_cache_key in _SWATCH_CACHE:
                        return FlaskResponse(
                            _SWATCH_CACHE[_prerender_cache_key],
                            mimetype='image/png',
                            headers=_no_cache_headers
                        )
                from PIL import Image as _PILImage
                with open(_pre_path, 'rb') as _f:
                    _img = _PILImage.open(_f).convert('RGB')
                if _img.size != (size, size):
                    _img = _img.resize((size, size), _PILImage.LANCZOS)
                _buf = io.BytesIO()
                _img.save(_buf, format='PNG', optimize=True)
                png_bytes = _buf.getvalue()
                with _SWATCH_CACHE_LOCK:
                    _SWATCH_CACHE[_prerender_cache_key] = png_bytes
                return FlaskResponse(
                    png_bytes,
                    mimetype='image/png',
                    headers=_no_cache_headers
                )
            except Exception as _e:
                logger.debug(f"Pre-rendered thumbnail failed [{finish_type}/{finish_key}]: {_e}")

    try:
        if mode == 'split' and finish_type in ('pattern', 'monolithic', 'base'):
            # Pre-rendered thumbnail (from rebuild_thumbnails.py): use when present so thumbnails actually show
            png_left = png_right = None
            _split_pre = _pre_path if _pre_path and os.path.isfile(_pre_path) else _pre_path_for_key(finish_key) if os.path.isfile(_pre_path_for_key(finish_key)) else None
            if _split_pre and allow_prerender:
                try:
                    from PIL import Image as _PILImg
                    with open(_split_pre, 'rb') as _f:
                        _img = _PILImg.open(_f).convert('RGB')
                    if _img.size != (size, size):
                        _img = _img.resize((size, size), _PILImg.LANCZOS)
                    _buf = io.BytesIO()
                    _img.save(_buf, format='PNG', optimize=True)
                    _bytes = _buf.getvalue()
                    png_left = _bytes
                    if finish_type == 'monolithic':
                        png_right = _bytes
                    # For base/pattern, right panel = live with user color (below)
                except Exception as _e:
                    logger.debug(f"Pre-rendered split failed [{finish_type}/{finish_key}]: {_e}")
            if png_left is None:
                # Left panel: neutral dark gray (shows structure / base behavior)
                png_left = _render_swatch_bytes(finish_type, finish_key, '444444', size, seed)
            if png_right is None:
                # Right panel: with user hint color; use pre-rendered for both if live fails
                try:
                    png_right = _render_swatch_bytes(finish_type, finish_key, color_hex, size, seed)
                except Exception as _e:
                    logger.warning(f"Swatch right panel failed [{finish_type}/{finish_key}]: {_e}")
                    png_right = png_left  # fallback so at least something shows
            # Stitch into 2:1 wide image with a thin divider
            import io as _io
            import numpy as _np
            from PIL import Image as PILImage
            img_l = PILImage.open(_io.BytesIO(png_left)).convert('RGB')
            img_r = PILImage.open(_io.BytesIO(png_right)).convert('RGB')
            combined = PILImage.new('RGB', (size * 2, size))
            combined.paste(img_l, (0, 0))
            combined.paste(img_r, (size, 0))
            arr = _np.array(combined)
            arr[:, size - 1, :] = [20, 20, 20]
            arr[:, size,     :] = [20, 20, 20]
            buf = _io.BytesIO()
            PILImage.fromarray(arr).save(buf, format='PNG', optimize=True)
            png_bytes = buf.getvalue()
        else:
            png_bytes = _render_swatch_bytes(finish_type, finish_key, color_hex, size, seed)
    except Exception as e:
        logger.warning(f"/api/swatch failed [{finish_type}/{finish_key}]: {e}")
        logger.debug(f"Swatch traceback: {traceback.format_exc()}")
        # Return 200 with placeholder PNG so the UI doesn't show broken image (gray div from onerror).
        # When split was requested, always return 2x-wide so the client doesn't stretch a single panel.
        png_bytes = _swatch_placeholder_png(size, split_mode=(mode == 'split'))

    with _SWATCH_CACHE_LOCK:
        _SWATCH_CACHE[cache_key] = png_bytes

    # Save to disk cache (permanent, survives restarts, ~3KB per swatch)
    try:
        os.makedirs(_swatch_cache_dir, exist_ok=True)
        with open(_disk_path, 'wb') as _df:
            _df.write(png_bytes)
    except Exception:
        pass  # Non-critical: in-memory cache still works

    return FlaskResponse(
        png_bytes,
        mimetype='image/png',
        headers=_cache_headers
    )


def _api_swatch_test_impl(finish_key):
    """Render ONE monolithic at 256x256 and return PNG. Used by both swatch-test and swatch_test routes."""
    from flask import Response as FlaskResponse
    size = 256
    if finish_key not in getattr(engine, 'MONOLITHIC_REGISTRY', {}):
        return jsonify({"error": f"Unknown monolithic: {finish_key}"}), 404
    try:
        png_bytes = _render_swatch_bytes('monolithic', finish_key, '888888', size, 42)
        return FlaskResponse(png_bytes, mimetype='image/png', headers={'Cache-Control': 'no-store'})
    except Exception as e:
        logger.exception(f"swatch-test {finish_key}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/swatch-test/<finish_key>', methods=['GET'])
def api_swatch_test(finish_key):
    """Render ONE monolithic at 256x256 and return PNG. Verify Color Shift Duo pipeline.
    Open: http://localhost:59876/api/swatch-test/cs_fire_ice (hyphen) or .../api/swatch_test/cs_fire_ice (underscore)"""
    return _api_swatch_test_impl(finish_key)


@app.route('/api/swatch_test/<finish_key>', methods=['GET'])
def api_swatch_test_underscore(finish_key):
    """Same as swatch-test; underscore URL for compatibility."""
    return _api_swatch_test_impl(finish_key)


# Curated base IDs for priority prebake at 48px (picker size). So you can verify:
# FOUNDATION, CERAMIC & GLASS, CARBON & COMPOSITE show correct swatches.
PREBAKE_PRIORITY_BASE_IDS = [
    # FOUNDATION
    "clear_matte", "eggshell", "flat_black", "gloss", "matte", "primer",
    "satin", "semi_gloss", "silk", "wet_look",
    # CERAMIC & GLASS
    "ceramic", "ceramic_matte", "crystal_clear", "enamel", "obsidian",
    "piano_black", "porcelain", "tempered_glass",
    # CARBON & COMPOSITE (pattern is in the base - base_spec_fn)
    "aramid", "carbon_base", "carbon_ceramic", "fiberglass", "forged_composite",
    "graphene", "hybrid_weave", "kevlar_base",
]


# ----------------------------------------------------------------
# Thumbnail manifest system — hash-based invalidation
# Thread-safe lock for manifest read/write
# ----------------------------------------------------------------
_THUMBNAIL_MANIFEST_LOCK = threading.Lock()


def _load_thumbnail_manifest():
    """Load or create the thumbnail hash manifest."""
    manifest_path = os.path.join(THUMBNAIL_DIR, '_manifest.json')
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"version": 2, "spec_patterns": {}, "bases": {}, "patterns": {}, "monolithics": {}}


def _save_thumbnail_manifest(manifest):
    """Save the thumbnail hash manifest (call under _THUMBNAIL_MANIFEST_LOCK)."""
    manifest_path = os.path.join(THUMBNAIL_DIR, '_manifest.json')
    os.makedirs(THUMBNAIL_DIR, exist_ok=True)
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)


def _get_fn_hash(fn):
    """Get a short hash of a function's source code for change detection."""
    try:
        import inspect
        src = inspect.getsource(fn)
        return hashlib.md5(src.encode()).hexdigest()[:12]
    except Exception:
        return "unknown"


def _generate_spec_preview_image(pattern_id):
    """Generate 194x64 3-panel M/R/CC split preview for a spec pattern. Returns PIL Image."""
    from engine.spec_patterns import PATTERN_CATALOG
    import numpy as np
    from PIL import Image as _PILImage, ImageDraw as _ImageDraw

    fn = PATTERN_CATALOG.get(pattern_id)
    if not fn:
        return _PILImage.new('RGBA', (194, 64), (40, 40, 40, 255))

    shape = (64, 64)
    seed = 42
    sm = 1.0
    try:
        arr = fn(shape, seed, sm)
    except Exception as e:
        logger.warning(f"Spec preview gen error for {pattern_id}: {e}")
        return _PILImage.new('RGBA', (194, 64), (40, 40, 40, 255))

    arr = np.clip(arr, 0, 1).astype(np.float32)
    if arr.ndim == 3:
        arr = arr.mean(axis=2)
    m_gray = (arr * 255).astype(np.uint8)
    r_gray = (arr * 255).astype(np.uint8)
    cc_gray = (255 - arr * 255).astype(np.uint8)

    # Canvas is 194px wide: 3 panels of 64px each + 2 single-pixel dividers (cols 64, 129)
    out = np.zeros((64, 194, 4), dtype=np.uint8)
    out[:, 0:64, 0] = m_gray
    out[:, 0:64, 1] = m_gray
    out[:, 0:64, 2] = m_gray
    out[:, 0:64, 3] = 255
    out[:, 64, :] = [30, 30, 30, 255]
    out[:, 65:129, 0] = r_gray
    out[:, 65:129, 1] = r_gray
    out[:, 65:129, 2] = r_gray
    out[:, 65:129, 3] = 255
    out[:, 129, :] = [30, 30, 30, 255]
    out[:, 130:194, 0] = cc_gray
    out[:, 130:194, 1] = cc_gray
    out[:, 130:194, 2] = cc_gray
    out[:, 130:194, 3] = 255

    img = _PILImage.fromarray(out, 'RGBA')
    draw = _ImageDraw.Draw(img)
    for label, x in [('M', 2), ('R', 67), ('CC', 132)]:
        draw.text((x + 1, 54), label, fill=(0, 0, 0, 200))
        draw.text((x, 53), label, fill=(255, 255, 255, 220))
    return img


def _generate_spec_metal_image(pattern_id):
    """Generate 128x128 metallic surface simulation for a spec pattern. Returns PIL Image."""
    from engine.spec_patterns import PATTERN_CATALOG
    import numpy as np
    from PIL import Image as _PILImage

    fn = PATTERN_CATALOG.get(pattern_id)
    if not fn:
        return _PILImage.new('RGBA', (128, 128), (60, 60, 60, 255))

    shape = (128, 128)
    seed = 42
    sm = 1.0
    try:
        arr = fn(shape, seed, sm)
    except Exception as e:
        logger.warning(f"Spec metal gen error for {pattern_id}: {e}")
        return _PILImage.new('RGBA', (128, 128), (60, 60, 60, 255))

    arr = np.clip(arr, 0, 1).astype(np.float32)
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    base_lighting = 1.0 - (xx / w * 0.4 + yy / h * 0.3)
    base_lighting = np.clip(base_lighting, 0.2, 1.0)
    metallic_factor = arr
    roughness = arr
    specular_sharpness = 1.0 - roughness * 0.8
    ambient = 0.25
    final_lum = base_lighting * metallic_factor * specular_sharpness + ambient * (1.0 - metallic_factor)
    final_lum = np.clip(final_lum, 0, 1)
    r_ch = np.clip(final_lum * 0.88 + 0.06, 0, 1)
    g_ch = np.clip(final_lum * 0.92 + 0.04, 0, 1)
    b_ch = np.clip(final_lum * 1.05 + 0.02, 0, 1)

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 0] = (r_ch * 255).astype(np.uint8)
    rgba[:, :, 1] = (g_ch * 255).astype(np.uint8)
    rgba[:, :, 2] = (b_ch * 255).astype(np.uint8)
    rgba[:, :, 3] = 255
    return _PILImage.fromarray(rgba, 'RGBA')


def _prebake_spec_patterns():
    """Pre-bake all spec pattern thumbnails that are missing or stale. Runs in background thread."""
    try:
        from engine.spec_patterns import PATTERN_CATALOG
    except Exception as e:
        logger.warning(f"Spec pattern prebake: could not import PATTERN_CATALOG: {e}")
        return

    spec_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns')
    spec_metal_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns_metal')
    os.makedirs(spec_dir, exist_ok=True)
    os.makedirs(spec_metal_dir, exist_ok=True)

    with _THUMBNAIL_MANIFEST_LOCK:
        manifest = _load_thumbnail_manifest()
    sp_manifest = manifest.get('spec_patterns', {})
    changed = False
    generated = 0
    skipped = 0
    errors = 0

    pattern_items = list(PATTERN_CATALOG.items())
    for pattern_id, fn in pattern_items:
        thumb_path = os.path.join(spec_dir, f"{pattern_id}.png")
        metal_path = os.path.join(spec_metal_dir, f"{pattern_id}.png")
        current_hash = _get_fn_hash(fn)
        cached_entry = sp_manifest.get(pattern_id, {})

        # Skip if both thumbnails exist AND hash matches (function unchanged)
        if (os.path.exists(thumb_path) and os.path.exists(metal_path)
                and cached_entry.get('hash') == current_hash):
            skipped += 1
            continue

        try:
            img = _generate_spec_preview_image(pattern_id)
            img.save(thumb_path)
            metal_img = _generate_spec_metal_image(pattern_id)
            metal_img.save(metal_path)

            sp_manifest[pattern_id] = {
                'hash': current_hash,
                'generated': datetime.utcnow().isoformat()
            }
            changed = True
            generated += 1
        except Exception as e:
            errors += 1
            logger.warning(f"Spec thumb bake failed for {pattern_id}: {e}")

        # Yield to active renders — don't compete for CPU
        while not _preview_render_lock.acquire(blocking=False):
            time.sleep(0.1)
        _preview_render_lock.release()
        # Small delay between bakes to avoid CPU saturation
        if len(pattern_items) > 50:
            time.sleep(0.02)

    if changed:
        manifest['spec_patterns'] = sp_manifest
        with _THUMBNAIL_MANIFEST_LOCK:
            _save_thumbnail_manifest(manifest)

    logger.info(f"Spec pattern thumbnails: {generated} generated, {skipped} cached, {errors} errors")


def _queue_thumbnail_regen(finish_type, finish_id, fn=None):
    """Queue a thumbnail for regeneration (e.g. after a new finish is added at runtime).
    finish_type: 'spec_patterns' | 'bases' | 'patterns' | 'monolithics'
    finish_id: the ID string
    fn: the function (for hash computation), or None to force regen
    """
    def _regen():
        time.sleep(0.5)
        try:
            if finish_type == 'spec_patterns':
                from engine.spec_patterns import PATTERN_CATALOG
                fn_to_use = fn or PATTERN_CATALOG.get(finish_id)
                if fn_to_use:
                    spec_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns')
                    spec_metal_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns_metal')
                    os.makedirs(spec_dir, exist_ok=True)
                    os.makedirs(spec_metal_dir, exist_ok=True)
                    thumb_path = os.path.join(spec_dir, f"{finish_id}.png")
                    metal_path = os.path.join(spec_metal_dir, f"{finish_id}.png")
                    img = _generate_spec_preview_image(finish_id)
                    img.save(thumb_path)
                    metal_img = _generate_spec_metal_image(finish_id)
                    metal_img.save(metal_path)
                    with _THUMBNAIL_MANIFEST_LOCK:
                        manifest = _load_thumbnail_manifest()
                        manifest.setdefault('spec_patterns', {})[finish_id] = {
                            'hash': _get_fn_hash(fn_to_use),
                            'generated': datetime.utcnow().isoformat()
                        }
                        _save_thumbnail_manifest(manifest)
                    logger.info(f"Thumbnail regen complete: spec_patterns/{finish_id}")
        except Exception as e:
            logger.warning(f"Thumbnail regen failed for {finish_type}/{finish_id}: {e}")

    threading.Thread(target=_regen, daemon=True).start()


def _prebake_swatches():
    """Pre-render base, pattern, priority bases at 48px, and some monolithics at startup.

    Phase 1: all bases + patterns at 64px. Phase 2: priority bases (FOUNDATION,
    CERAMIC & GLASS, CARBON & COMPOSITE) at 48px for picker. Phase 3: first 80
    monolithics at 48px. Runs in a background daemon thread.
    """
    neutral = '888888'
    seed    = 42
    count   = 0
    errors  = 0
    base_reg = set(engine.BASE_REGISTRY.keys())
    # Phase 1: bases + patterns at 64px
    size = 64
    items = (
        [('base', k) for k in engine.BASE_REGISTRY.keys()] +
        [('pattern', k) for k in engine.PATTERN_REGISTRY.keys()]
    )
    import time as _bake_time
    def _yield_to_render():
        """If a real render is active, pause pre-bake until it finishes."""
        while not _preview_render_lock.acquire(blocking=False):
            _bake_time.sleep(0.1)  # Wait 100ms and retry
        _preview_render_lock.release()

    for finish_type, finish_key in items:
        _yield_to_render()  # Don't compete with active renders
        cache_key = f"{_swatch_cache_token()}:{finish_type}:{finish_key}:{neutral}:{size}:"
        try:
            png_bytes = _render_swatch_bytes(finish_type, finish_key, neutral, size, seed)
            with _SWATCH_CACHE_LOCK:
                _SWATCH_CACHE[cache_key] = png_bytes
            count += 1
        except Exception as e:
            logger.debug(f"Pre-bake skip [{finish_type}/{finish_key}]: {e}")
            errors += 1
    # Phase 2: priority bases at 48px (picker)
    size = 48
    for finish_key in PREBAKE_PRIORITY_BASE_IDS:
        if finish_key not in base_reg:
            continue
        _yield_to_render()
        cache_key = f"{_swatch_cache_token()}:base:{finish_key}:{neutral}:{size}:"
        try:
            png_bytes = _render_swatch_bytes('base', finish_key, neutral, size, seed)
            with _SWATCH_CACHE_LOCK:
                _SWATCH_CACHE[cache_key] = png_bytes
            count += 1
        except Exception as e:
            logger.debug(f"Pre-bake skip [base/{finish_key}]: {e}")
            errors += 1
    # Phase 3: first 80 monolithics at 48px
    mono_keys = list(engine.MONOLITHIC_REGISTRY.keys())[:80]
    for finish_key in mono_keys:
        _yield_to_render()
        cache_key = f"{_swatch_cache_token()}:monolithic:{finish_key}:{neutral}:{size}:"
        try:
            png_bytes = _render_swatch_bytes('monolithic', finish_key, neutral, size, seed)
            with _SWATCH_CACHE_LOCK:
                _SWATCH_CACHE[cache_key] = png_bytes
            count += 1
        except Exception as e:
            logger.debug(f"Pre-bake skip [monolithic/{finish_key}]: {e}")
            errors += 1
    logger.info(f"Swatch pre-bake complete: {count} OK, {errors} skipped")


# Kick off swatch pre-bake at startup (non-blocking, daemon thread)
import threading as _threading
_threading.Thread(target=_prebake_swatches, daemon=True, name='swatch-prebake').start()
# Kick off spec pattern thumbnail pre-bake (lower priority, runs after swatches)
_threading.Thread(target=_prebake_spec_patterns, daemon=True, name='spec-thumb-prebake').start()


@app.route('/debug-rotation-log', methods=['GET'])
def debug_rotation_log():
    """Return the rotation debug log file contents (deprecated - kept for compat)."""
    return "Debug rotation logging removed in build 29", 200, {'Content-Type': 'text/plain'}


@app.route('/preview-render', methods=['POST'])
def preview_render_endpoint():
    """Low-res live preview - returns base64 PNGs inline (no job directory).

    JSON body:
    {
        "paint_file": "E:/path/to/car_num_23371.tga",
        "zones": [...],
        "seed": 51,
        "preview_scale": 0.25,
        "recolor_rules": []
    }

    Response:
    {
        "success": true,
        "elapsed_ms": 180,
        "paint_preview": "data:image/png;base64,...",
        "spec_preview": "data:image/png;base64,...",
        "resolution": [512, 512]
    }
    """
    # Per-IP rate limit: protect the engine from runaway slider drags.
    # 10 previews/sec/IP is generous — the UI debounces at ~3/sec.
    if not _rate_limit("preview-render", max_per_second=10):
        return jsonify({"error": "rate_limited",
                        "message": "Too many preview requests — slow down."}), 429

    # Signal any in-flight preview to abort, then wait for the lock.
    # If the previous render is still finishing after 2 s, reject this
    # request with 429 so the UI can retry rather than pile up renders.
    _preview_abort.set()
    acquired = _preview_render_lock.acquire(timeout=2.0)
    if not acquired:
        return jsonify({"error": "Preview busy — previous render still finishing"}), 429
    _preview_abort.clear()
    _preview_t0 = time.time()
    try:
        import numpy as np  # Must be at function scope — conditional np imports below shadow this
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        paint_file = data.get("paint_file")
        paint_image_base64_early = data.get("paint_image_base64")
        if not paint_image_base64_early and (not paint_file or not os.path.exists(paint_file)):
            return jsonify({"error": f"Paint file not found: {paint_file}"}), 404

        zones = [_convert_zone_keys(z) for z in data.get("zones", [])]
        import_spec_map_early = data.get("import_spec_map")
        if not zones and not import_spec_map_early:
            return jsonify({"error": "No zones provided"}), 400
        # Reject runaway zone arrays before we spend any CPU on them.
        if len(zones) > MAX_ZONES_PER_REQUEST:
            return jsonify({
                "error": "too_many_zones",
                "message": f"Zone count {len(zones)} exceeds limit {MAX_ZONES_PER_REQUEST}.",
                "limit": MAX_ZONES_PER_REQUEST,
            }), 400

        # Validate zone data has required fields
        for zi, z in enumerate(zones):
            ok, err = _validate_zone_required_fields(z, zi + 1)
            if not ok:
                logger.warning(f"[preview-render] Zone validation: {err}")
                # Don't reject — just log. Some zones may be incomplete during editing.

        seed = _safe_int(data.get("seed"), SEED_DEFAULT)
        preview_scale = _clamp(data.get("preview_scale"), PREVIEW_SCALE_MIN,
                               PREVIEW_SCALE_MAX, PREVIEW_SCALE_DEFAULT)

        # Incremental rendering hints from client
        changed_zone = _safe_int(data.get("changed_zone"), -1)
        zone_hashes = data.get("zone_hashes", [])

        # Invalidate engine zone cache when paint file or preview scale changes.
        # The engine cache (build_multi_zone._zone_cache) keys on zone settings only;
        # if the underlying paint file or resolution changes we must flush it so
        # cached spec/paint arrays from a different canvas size don't get reused.
        global _preview_cache_paint_key
        try:
            _paint_mtime = os.path.getmtime(paint_file)
        except OSError:
            _paint_mtime = 0
        _new_paint_key = f"{paint_file}|{_paint_mtime}"
        if _new_paint_key != _preview_cache_paint_key:
            _preview_cache_paint_key = _new_paint_key
            # Clear the engine-level zone cache when the PAINT FILE changes.
            # Scale changes should NOT flush the cache — the engine includes
            # canvas dimensions in its per-zone cache key so different scales
            # naturally produce different cache entries without flushing.
            try:
                import shokker_engine_v2 as _eng
                if hasattr(_eng.build_multi_zone, '_zone_cache'):
                    _eng.build_multi_zone._zone_cache.clear()
                    logger.info(f"[preview-cache] Invalidated zone cache (paint file changed)")
                # Also clear spec delta cache so first render after change sends full PNG
                global _prev_spec_cache
                _prev_spec_cache = None
            except Exception:
                pass
        if changed_zone >= 0 or zone_hashes:
            logger.info(f"[preview-cache] changed_zone={changed_zone}, {len(zone_hashes)} zone hashes received")

        # Decal spec finishes (list of {specFinish: "gloss"} for non-"none" decals)
        decal_spec_finishes = data.get("decal_spec_finishes", [])
        decal_mask_base64 = data.get("decal_mask_base64")  # separate decal-only alpha mask
        decal_paint_path_preview = None  # set below if paint_image_base64 is decoded

        # If client sent a composited paint (paint + baked-in decals), decode and use it
        paint_image_base64 = data.get("paint_image_base64")
        actual_paint_file = paint_file
        if paint_image_base64:
            try:
                import base64 as _b64, tempfile
                raw = paint_image_base64
                if raw.startswith("data:"):
                    raw = raw.split(",", 1)[-1]
                buf = _b64.b64decode(raw)
                tmp_decal_dir = tempfile.mkdtemp(prefix="shokker_preview_decal_")
                decal_paint_path_preview = os.path.join(tmp_decal_dir, "paint_with_decals.png")
                with open(decal_paint_path_preview, "wb") as f:
                    f.write(buf)
                actual_paint_file = decal_paint_path_preview
                logger.info(f"Preview: using composited paint (decals) from client, {len(decal_spec_finishes)} decal spec finish(es)")
            except Exception as e:
                logger.warning(f"Preview: failed to decode paint_image_base64: {e}")
                decal_paint_path_preview = None
                actual_paint_file = paint_file

        # Apply paint recoloring if rules provided (at preview res this is fast)
        # Note: recoloring runs on actual_paint_file so decal composite is preserved
        recolor_rules = data.get("recolor_rules", [])
        if recolor_rules:
            try:
                import tempfile
                tmp_dir = tempfile.mkdtemp(prefix="shokker_preview_")
                actual_paint_file = apply_paint_recolor(actual_paint_file, recolor_rules, tmp_dir)
            except Exception:
                pass  # Fall back to current actual_paint_file

        # Build server zones (same format conversion as /render)

        server_zones = []
        for z in zones:
            zone_obj = {
                "name": z.get("name", "Zone"),
                "color": z.get("color", "everything"),
                "intensity": str(_clamp(z.get("intensity"), INTENSITY_MIN, INTENSITY_MAX, INTENSITY_DEFAULT)),
            }
            # Base vs Pattern Intensity: when set, pattern uses pattern_intensity so lowering base doesn't kill pattern
            if z.get("pattern_intensity") is not None:
                zone_obj["pattern_intensity"] = str(_clamp(z.get("pattern_intensity"),
                                                           INTENSITY_MIN, INTENSITY_MAX, INTENSITY_DEFAULT))
            # Compositing mode
            if z.get("base"):
                zone_obj["base"] = z["base"]
                zone_obj["pattern"] = z.get("pattern", "none")
                if z.get("scale") and _safe_float(z.get("scale"), SCALE_DEFAULT) != SCALE_DEFAULT:
                    zone_obj["scale"] = _clamp(z["scale"], SCALE_MIN, SCALE_MAX, SCALE_DEFAULT)
                if z.get("rotation") and _safe_float(z.get("rotation"), ROTATION_DEFAULT) != ROTATION_DEFAULT:
                    zone_obj["rotation"] = _clamp(z["rotation"], ROTATION_MIN, ROTATION_MAX, ROTATION_DEFAULT)
                zone_obj["pattern_opacity"] = _clamp(z.get("pattern_opacity"),
                                                     OPACITY_MIN, OPACITY_MAX, OPACITY_DEFAULT)
                if z.get("pattern_stack"):
                    zone_obj["pattern_stack"] = z["pattern_stack"]
            # Monolithic/legacy mode
            elif z.get("finish"):
                zone_obj["finish"] = z["finish"]
                # Pass client color data for fallback rendering
                if z.get("finish_colors"):
                    zone_obj["finish_colors"] = z["finish_colors"]
                # Pass rotation for gradient direction control
                if z.get("rotation") and _safe_float(z.get("rotation"), ROTATION_DEFAULT) != ROTATION_DEFAULT:
                    zone_obj["rotation"] = _clamp(z["rotation"], ROTATION_MIN, ROTATION_MAX, ROTATION_DEFAULT)
                # BUG FIX: Pass pattern data for monolithic zones too - engine supports
                # pattern overlay on monolithics via overlay_pattern_on_spec/overlay_pattern_paint
                if z.get("pattern") and z.get("pattern") != "none":
                    zone_obj["pattern"] = z["pattern"]
                if z.get("scale") and _safe_float(z.get("scale"), SCALE_DEFAULT) != SCALE_DEFAULT:
                    zone_obj["scale"] = _clamp(z["scale"], SCALE_MIN, SCALE_MAX, SCALE_DEFAULT)
                zone_obj["pattern_opacity"] = _clamp(z.get("pattern_opacity"),
                                                     OPACITY_MIN, OPACITY_MAX, OPACITY_DEFAULT)
                if z.get("pattern_stack"):
                    zone_obj["pattern_stack"] = z["pattern_stack"]

            # --- PARAMETER PASSTHROUGH: fields from JS buildServerZonesForRender ---
            # Pattern position offsets (0.0-1.0, default 0.5 = centered)
            if z.get("pattern_offset_x") is not None:
                zone_obj["pattern_offset_x"] = _clamp(z["pattern_offset_x"], 0.0, 1.0, 0.5)
            if z.get("pattern_offset_y") is not None:
                zone_obj["pattern_offset_y"] = _clamp(z["pattern_offset_y"], 0.0, 1.0, 0.5)
            # Pattern flip (boolean toggles)
            if z.get("pattern_flip_h"):
                zone_obj["pattern_flip_h"] = bool(z["pattern_flip_h"])
            if z.get("pattern_flip_v"):
                zone_obj["pattern_flip_v"] = bool(z["pattern_flip_v"])
            # Pattern placement modes
            if z.get("pattern_fit_zone"):
                zone_obj["pattern_fit_zone"] = True
            if z.get("hard_edge"):
                zone_obj["hard_edge"] = True
            if z.get("pattern_manual"):
                zone_obj["pattern_manual"] = True

            # Pattern spec multiplier (controls spec map punch independently)
            if z.get("pattern_spec_mult") is not None:
                zone_obj["pattern_spec_mult"] = _safe_float(z["pattern_spec_mult"], 1.0)

            # Pattern strength map (per-pixel strength modulation)
            if z.get("pattern_strength_map"):
                try:
                    import numpy as np
                    psm_rle = z["pattern_strength_map"]
                    if isinstance(psm_rle, str):
                        psm_rle = json.loads(psm_rle)
                    psm_w = psm_rle.get("width", 0)
                    psm_h = psm_rle.get("height", 0)
                    psm_runs = psm_rle.get("runs", [])
                    psm_flat = np.zeros(psm_w * psm_h, dtype=np.float32)
                    psm_pos = 0
                    for run_val, run_len in psm_runs:
                        psm_flat[psm_pos:psm_pos + run_len] = float(run_val) / 255.0
                        psm_pos += run_len
                    zone_obj["pattern_strength_map"] = psm_flat.reshape((psm_h, psm_w))
                except Exception as _psm_err:
                    logger.warning(f"Failed to decode pattern_strength_map: {_psm_err}")

            # Custom intensity
            if z.get("custom_intensity"):
                zone_obj["custom_intensity"] = z["custom_intensity"]

            # Wear
            if z.get("wear_level"):
                zone_obj["wear_level"] = z["wear_level"]

            # v6.0 advanced finish params - must pass through for engine to use
            if z.get("cc_quality") is not None:
                zone_obj["cc_quality"] = _safe_float(z["cc_quality"], 1.0)
            if z.get("blend_base"):
                zone_obj["blend_base"] = z["blend_base"]
                zone_obj["blend_dir"] = z.get("blend_dir", "horizontal")
                zone_obj["blend_amount"] = _clamp(z.get("blend_amount"), 0.0, 1.0, 0.5)
            if z.get("paint_color"):
                zone_obj["paint_color"] = z["paint_color"]
            if z.get("base_scale") and _safe_float(z.get("base_scale"), SCALE_DEFAULT) != SCALE_DEFAULT:
                zone_obj["base_scale"] = _clamp(z["base_scale"], SCALE_MIN, SCALE_MAX, SCALE_DEFAULT)
            if z.get("base_strength") is not None:
                zone_obj["base_strength"] = _safe_float(z["base_strength"], 1.0)
            if z.get("base_spec_strength") is not None:
                zone_obj["base_spec_strength"] = _safe_float(z.get("base_spec_strength"), 1.0)
            # Base spec blend mode (normal, multiply, screen, etc.) — passthrough from JS
            if z.get("base_spec_blend_mode") and z["base_spec_blend_mode"] != "normal":
                zone_obj["base_spec_blend_mode"] = z["base_spec_blend_mode"]
            if z.get("base_color_mode") is not None:
                zone_obj["base_color_mode"] = z.get("base_color_mode", "source")
            if z.get("base_color") is not None:
                zone_obj["base_color"] = z.get("base_color", [1.0, 1.0, 1.0])
            if z.get("base_color_source") is not None:
                zone_obj["base_color_source"] = z.get("base_color_source")
            # Gradient color mode — must pass stops and direction for preview parity with full render
            if z.get("gradient_stops"):
                zone_obj["gradient_stops"] = z["gradient_stops"]
            if z.get("gradient_direction"):
                zone_obj["gradient_direction"] = z["gradient_direction"]
            if z.get("base_color_strength") is not None:
                zone_obj["base_color_strength"] = _clamp(z.get("base_color_strength"), 0.0, 1.0, 1.0)
            if z.get("base_color_fit_zone"):
                zone_obj["base_color_fit_zone"] = True
            if z.get("base_hue_offset") is not None:
                zone_obj["base_hue_offset"] = _safe_float(z.get("base_hue_offset"), 0.0)
            if z.get("base_saturation_adjust") is not None:
                zone_obj["base_saturation_adjust"] = _safe_float(z.get("base_saturation_adjust"), 0.0)
            if z.get("base_brightness_adjust") is not None:
                zone_obj["base_brightness_adjust"] = _safe_float(z.get("base_brightness_adjust"), 0.0)

            # Spec pattern overlay stack
            if z.get("spec_pattern_stack"):
                zone_obj["spec_pattern_stack"] = z.get("spec_pattern_stack", [])
            if z.get("overlay_spec_pattern_stack"):
                zone_obj["overlay_spec_pattern_stack"] = z.get("overlay_spec_pattern_stack", [])

            # Base Overlay Layers (2nd–5th). Trigger on EITHER base OR color_source so specials-only overlays work.
            for _pfx, _guard in [
                ("second_base", True),
                ("third_base", getattr(CFG, "ENABLE_THIRD_BASE_OVERLAY", False)),
                ("fourth_base", getattr(CFG, "ENABLE_THIRD_BASE_OVERLAY", False)),
                ("fifth_base", getattr(CFG, "ENABLE_THIRD_BASE_OVERLAY", False)),
            ]:
                if not _guard:
                    continue
                _has_base = z.get(_pfx)
                _has_src  = z.get(f"{_pfx}_color_source")
                if not _has_base and not _has_src:
                    continue
                logger.info(f"[PREVIEW OVERLAY] {_pfx}: base={_has_base}, src={_has_src}, str={z.get(f'{_pfx}_strength')}, blend={z.get(f'{_pfx}_blend_mode')}, color={z.get(f'{_pfx}_color')}")
                if _has_base:
                    zone_obj[_pfx] = _has_base
                zone_obj[f"{_pfx}_color"]        = z.get(f"{_pfx}_color", [1.0, 1.0, 1.0])
                zone_obj[f"{_pfx}_color_source"] = _has_src
                zone_obj[f"{_pfx}_strength"]     = float(z.get(f"{_pfx}_strength", 0.0))
                zone_obj[f"{_pfx}_blend_mode"]   = z.get(f"{_pfx}_blend_mode", "noise")
                zone_obj[f"{_pfx}_noise_scale"]  = int(z.get(f"{_pfx}_noise_scale", 24))
                zone_obj[f"{_pfx}_scale"]        = max(0.01, min(5.0, float(z.get(f"{_pfx}_scale", 1.0))))
                zone_obj[f"{_pfx}_pattern"]      = z.get(f"{_pfx}_pattern")
                # Preview must pass the same base-overlay tuning fields as the
                # full render payload; otherwise sliders look dead until export.
                for _k in (f"{_pfx}_spec_strength",
                           f"{_pfx}_hue_shift", f"{_pfx}_saturation", f"{_pfx}_brightness",
                           f"{_pfx}_pattern_hue_shift", f"{_pfx}_pattern_saturation", f"{_pfx}_pattern_brightness",
                           f"{_pfx}_pattern_opacity", f"{_pfx}_pattern_scale",
                           f"{_pfx}_pattern_rotation", f"{_pfx}_pattern_strength",
                           f"{_pfx}_pattern_offset_x", f"{_pfx}_pattern_offset_y"):
                    if z.get(_k) is not None:
                        zone_obj[_k] = float(z[_k])
                for _bk in (f"{_pfx}_pattern_invert", f"{_pfx}_pattern_harden",
                            f"{_pfx}_pattern_flip_h", f"{_pfx}_pattern_flip_v",
                            f"{_pfx}_fit_zone"):
                    if z.get(_bk) is not None:
                        zone_obj[_bk] = bool(z[_bk])

            # Region mask (base64 RLE from UI)
            if z.get("region_mask"):
                try:
                    import numpy as np
                    from PIL import Image as PILImage
                    rle = z["region_mask"]
                    if isinstance(rle, str):
                        rle = json.loads(rle)
                    rw = rle.get("width", 0)
                    rh = rle.get("height", 0)
                    runs = rle.get("runs", [])
                    flat = np.zeros(rw * rh, dtype=np.float32)
                    pos = 0
                    for run_val, run_len in runs:
                        # Client sends binary 0/1; engine expects float 0.0 or 1.0 (not 0/255)
                        flat[pos:pos + run_len] = float(run_val) / 255.0 if run_val else 0.0
                        pos += run_len
                    zone_obj["region_mask"] = flat.reshape((rh, rw))
                except Exception:
                    pass  # Skip broken masks

            # Source layer mask (PSD layer alpha — restricts zone to layer pixels)
            if z.get("source_layer_mask"):
                try:
                    import numpy as np
                    rle = z["source_layer_mask"]
                    if isinstance(rle, str):
                        rle = json.loads(rle)
                    rw = rle.get("width", 0)
                    rh = rle.get("height", 0)
                    runs = rle.get("runs", [])
                    flat = np.zeros(rw * rh, dtype=np.float32)
                    pos = 0
                    for run_val, run_len in runs:
                        flat[pos:pos + run_len] = float(run_val) / 255.0 if run_val else 0.0
                        pos += run_len
                    zone_obj["source_layer_mask"] = flat.reshape((rh, rw))
                    logger.info(f"[PSD] Zone '{zone_obj.get('name','')}' restricted to layer mask ({rw}x{rh})")
                except Exception as _slm_err:
                    logger.warning(f"[PSD] source_layer_mask decode failed: {_slm_err}")

            # Photoshop-correct layer-local color matching: decode the layer's
            # own RGB image so the engine can color-match against the layer's
            # unblended pixels instead of the composite. See Codex finding.
            if z.get("source_layer_rgb_png"):
                try:
                    import base64 as _b64lr, io as _iolr, numpy as np
                    from PIL import Image as _PILlr
                    _raw = z["source_layer_rgb_png"]
                    if _raw.startswith("data:"):
                        _raw = _raw.split(",", 1)[-1]
                    _img = _PILlr.open(_iolr.BytesIO(_b64lr.b64decode(_raw))).convert("RGBA")
                    zone_obj["source_layer_rgb"] = np.asarray(_img, dtype=np.uint8)
                    logger.info(f"[PSD] Zone '{zone_obj.get('name','')}' will color-match against layer RGB ({_img.size[0]}x{_img.size[1]})")
                except Exception as _slr_err:
                    logger.warning(f"[PSD] source_layer_rgb decode failed: {_slr_err}")

            # Spatial mask - include/exclude refinement for color-based zones
            # Values: 0=unset, 1=include (green), 2=exclude (red)
            if z.get("spatial_mask"):
                try:
                    import numpy as np
                    rle = z["spatial_mask"]
                    if isinstance(rle, str):
                        rle = json.loads(rle)
                    rw = rle.get("width", 0)
                    rh = rle.get("height", 0)
                    runs = rle.get("runs", [])
                    flat = np.zeros(rw * rh, dtype=np.uint8)
                    pos = 0
                    for run_val, run_len in runs:
                        flat[pos:pos + run_len] = int(run_val)
                        pos += run_len
                    zone_obj["spatial_mask"] = flat.reshape((rh, rw))
                except Exception:
                    pass
                # Engine uses region_mask first and skips color+spatial; so when spatial is set, drop region_mask
                if "region_mask" in zone_obj:
                    del zone_obj["region_mask"]
            if z.get("priority_override") is not None:
                zone_obj["priority_override"] = bool(z.get("priority_override"))

            server_zones.append(zone_obj)

        # Import spec map (merge mode)
        import_spec_map = data.get("import_spec_map")
        if import_spec_map and not os.path.exists(import_spec_map):
            import_spec_map = None  # Silently skip if file missing

        # Diagnostic: log zone scale values for debugging
        for zi, sz in enumerate(server_zones):
            parts = [f"Zone {zi+1}"]
            if sz.get("base"): parts.append(f"base={sz['base']}")
            if sz.get("pattern"): parts.append(f"pat={sz['pattern']}")
            if sz.get("scale"): parts.append(f"scale={sz['scale']}")
            if sz.get("pattern_stack"):
                for li, layer in enumerate(sz["pattern_stack"]):
                    parts.append(f"stack[{li}]={layer.get('id','?')}@scale={layer.get('scale',1.0)}")
            logger.info("  ".join(parts))

        # Run the preview render (pass abort_event so build_multi_zone can bail between zones)
        paint_rgb, spec_rgba, elapsed_ms = engine.preview_render(
            actual_paint_file, server_zones, seed=seed, preview_scale=preview_scale,
            import_spec_map=import_spec_map,
            decal_spec_finishes=decal_spec_finishes if decal_spec_finishes else None,
            decal_paint_path=decal_paint_path_preview,
            decal_mask_base64=decal_mask_base64 or None,
            abort_event=_preview_abort,
        )

        # Convert paint to base64 PNG (main preview)
        paint_b64 = numpy_to_base64_png(paint_rgb)

        # Convert spec to base64 PNG (bottom-right inset). Normalize and catch failures so
        # the main paint preview still works; show clear message if spec (bottom right) fails.
        spec_b64 = None
        spec_warning = None
        spec_normalized = _spec_array_to_rgba_uint8(spec_rgba)
        if spec_normalized is not None:
            try:
                spec_b64 = numpy_to_base64_png(spec_normalized)
            except Exception as spec_err:
                logger.warning(f"Spec map (bottom-right) encode failed: {spec_err}\n{traceback.format_exc()}")
                spec_warning = "Could not render spec map (bottom right corner). Check server logs for details."
        else:
            spec_warning = "Spec map invalid (wrong shape/dtype). Check server logs for details."

        # If spec failed, use a 1x1 transparent PNG so the UI doesn't break; client can hide or show message
        if spec_b64 is None:
            spec_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="  # 1x1 transparent

        # Cleanup temp dirs created during preview
        if decal_paint_path_preview:
            try:
                shutil.rmtree(os.path.dirname(decal_paint_path_preview), ignore_errors=True)
            except Exception:
                pass
        if recolor_rules and actual_paint_file != paint_file and actual_paint_file != decal_paint_path_preview:
            try:
                shutil.rmtree(os.path.dirname(actual_paint_file), ignore_errors=True)
            except Exception:
                pass

        # ---- Spec delta encoding (#12) ----
        # If we have a cached previous spec and shapes match, compute a
        # compressed delta.  Send it instead of the full PNG when smaller.
        spec_delta_b64 = None
        if spec_normalized is not None and _prev_spec_cache is not None:
            try:
                if _prev_spec_cache.shape == spec_normalized.shape:
                    from engine.compose import compress_spec_delta
                    delta_bytes = compress_spec_delta(spec_normalized, _prev_spec_cache)
                    # Only use delta if it is smaller than the full PNG
                    spec_png_bytes = base64.b64decode(spec_b64.split(",", 1)[-1]) if spec_b64 and spec_b64.startswith("data:") else b""
                    if len(delta_bytes) < len(spec_png_bytes) * 0.9:
                        spec_delta_b64 = base64.b64encode(delta_bytes).decode("ascii")
                        logger.info(f"[preview-delta] delta={len(delta_bytes)}B vs png={len(spec_png_bytes)}B  ({len(delta_bytes)/max(1,len(spec_png_bytes))*100:.0f}%)")
            except Exception as _de:
                logger.debug(f"Spec delta encoding skipped: {_de}")

        # Update the cached spec for next delta computation
        # Use np.array with copy=True instead of .copy() -- same result but
        # ensures contiguous memory layout for faster delta comparisons next time.
        if spec_normalized is not None:
            _prev_spec_cache = np.ascontiguousarray(spec_normalized)

        payload = {
            "success": True,
            "elapsed_ms": round(elapsed_ms, 1),
            "paint_preview": paint_b64,
            "spec_preview": spec_b64,
            "resolution": [paint_rgb.shape[1], paint_rgb.shape[0]],
        }
        if spec_delta_b64:
            payload["spec_delta"] = spec_delta_b64
        if spec_warning:
            payload["spec_warning"] = spec_warning
        # Record successful preview render in the recent-renders ring.
        try:
            _record_recent_render("preview", paint_file,
                                  int((time.time() - _preview_t0) * 1000), success=True)
        except Exception:
            pass
        return jsonify(payload)

    except Exception as e:
        err_msg = str(e)
        # Provide friendlier error messages for common issues
        if 'numpy' in err_msg.lower() or 'np' in err_msg:
            err_msg = f"Engine computation error: {err_msg}. Try re-rendering."
        elif 'FileNotFoundError' in type(e).__name__ or 'not found' in err_msg.lower():
            err_msg = f"File not found: {err_msg}. Check that the paint file path is correct."
        elif 'MemoryError' in type(e).__name__:
            err_msg = "Out of memory — try reducing preview scale or number of zones."
        logger.error(f"Preview render failed: {e}\n{traceback.format_exc()}")
        try:
            _record_recent_render("preview", paint_file if 'paint_file' in dir() else None,
                                  int((time.time() - _preview_t0) * 1000), success=False)
        except Exception:
            pass
        return jsonify({"error": err_msg, "rid": getattr(g, "_rid", "-")}), 500
    finally:
        # Always release the preview render lock so the next request can proceed.
        try:
            _preview_render_lock.release()
        except RuntimeError:
            pass  # Lock was already released (e.g. early-return path above)


@app.route('/render', methods=['POST'])
def render():
    """
    Run the engine on local files. No upload needed - everything is local.

    JSON body:
    {
        "paint_file": "E:/path/to/car_num_23371.tga",
        "iracing_id": "23371",
        "seed": 51,
        "zones": [
            {
                "name": "Body",
                "color": "blue",
                "base": "chrome",
                "pattern": "carbon_fiber",
                "intensity": "100"
            }
        ],
        "live_link": true,              // optional: copy to iRacing folder
        "helmet_paint_file": "...",     // optional: helmet paint TGA path
        "suit_paint_file": "...",       // optional: suit paint TGA path
        "wear_level": 0,               // optional: 0-100 wear/age amount
        "export_zip": false             // optional: bundle into ZIP
    }
    """
    # ===== LICENSE GATE (disabled for Alpha testing) =====
    # if not _license_active:
    #     return jsonify({
    #         "error": "License required",
    #         "message": "A valid Shokker Engine license is required for full renders. "
    #                    "Preview mode is always free. Enter your license key in Settings.",
    #         "license_required": True
    #     }), 403

    # Cancel any in-flight preview render so it doesn't compete for CPU
    _preview_abort.set()
    # Acquire render lock to prevent preview and full render from running simultaneously
    acquired = _preview_render_lock.acquire(timeout=5.0)
    if not acquired:
        logger.warning("Full render waiting for preview lock — forcing acquisition")
        # Force it — full renders take priority
        try:
            _preview_render_lock.release()
        except RuntimeError:
            pass
        _preview_render_lock.acquire(timeout=1.0)

    try:
        import numpy as np  # Must be at function scope — conditional np imports below shadow this
        data = request.get_json()
        if not data:
            _preview_render_lock.release()
            return jsonify({"error": "No JSON body provided"}), 400

        paint_file = data.get("paint_file")
        paint_image_base64 = data.get("paint_image_base64")
        if not paint_file and not paint_image_base64:
            return jsonify({"error": "Missing 'paint_file' path or 'paint_image_base64'"}), 400
        if paint_file and not paint_image_base64 and not os.path.exists(paint_file):
            return jsonify({"error": f"Paint file not found: {paint_file}"}), 404

        zones = [_convert_zone_keys(z) for z in data.get("zones", [])]
        import_spec_map_early = data.get("import_spec_map")
        if not zones and not import_spec_map_early:
            return jsonify({"error": "No zones provided"}), 400
        # Reject runaway zone arrays before we spend any CPU on them.
        if len(zones) > MAX_ZONES_PER_REQUEST:
            return jsonify({
                "error": "too_many_zones",
                "message": f"Zone count {len(zones)} exceeds limit {MAX_ZONES_PER_REQUEST}.",
                "limit": MAX_ZONES_PER_REQUEST,
            }), 400

        iracing_id = data.get("iracing_id", "00000")
        seed = _safe_int(data.get("seed"), SEED_DEFAULT)
        use_live_link = data.get("live_link", False)
        output_dir_user = data.get("output_dir", "")  # UI-specified iRacing paint folder
        # Car file naming: car_num_ (custom numbers) vs car_ (no custom numbers)
        use_custom_number = data.get("use_custom_number", None)
        if use_custom_number is None:
            # Fall back to saved config
            _cfg_tmp = load_config()
            use_custom_number = _cfg_tmp.get("use_custom_number", True)
        car_prefix = "car_num" if use_custom_number else "car"
        helmet_paint = data.get("helmet_paint_file")
        suit_paint = data.get("suit_paint_file")
        wear_level = int(_clamp(data.get("wear_level"), WEAR_LEVEL_MIN, WEAR_LEVEL_MAX, WEAR_LEVEL_DEFAULT))
        export_zip = data.get("export_zip", False)
        dual_spec = data.get("dual_spec", False)
        night_boost = _safe_float(data.get("night_boost"), NIGHT_BOOST_DEFAULT)
        import_spec_map = data.get("import_spec_map")
        if import_spec_map and not os.path.exists(import_spec_map):
            logger.warning(f"Import spec map not found: {import_spec_map}")
            import_spec_map = None

        # Spec stamp overlay
        stamp_spec_finish = data.get("stamp_spec_finish", "gloss")
        stamp_image_path = None

        # Decal spec finishes (list of {specFinish: "gloss"} for non-"none" decals)
        decal_spec_finishes = data.get("decal_spec_finishes", [])
        decal_mask_base64 = data.get("decal_mask_base64")  # separate decal-only alpha mask
        decal_paint_path = None  # set below if paint_image_base64 is decoded

        # Validate optional files
        if helmet_paint and not os.path.exists(helmet_paint):
            helmet_paint = None
        if suit_paint and not os.path.exists(suit_paint):
            suit_paint = None

        # Create job output dir
        job_id = f"{int(time.time())}_{iracing_id}"
        job_dir = os.path.join(OUTPUT_FOLDER, f"job_{job_id}")
        os.makedirs(job_dir, exist_ok=True)

        # When client sends composited paint (e.g. paint + decals), decode and write to job dir
        if paint_image_base64:
            try:
                import base64
                raw = paint_image_base64
                if raw.startswith("data:"):
                    raw = raw.split(",", 1)[-1]
                buf = base64.b64decode(raw)
                decal_paint_path = os.path.join(job_dir, "paint_with_decals.png")
                with open(decal_paint_path, "wb") as f:
                    f.write(buf)
                paint_file = decal_paint_path
                logger.info(f"Job {job_id}: Using composited paint (decals) from client")
                if decal_spec_finishes:
                    logger.info(f"Job {job_id}: {len(decal_spec_finishes)} decal spec finish(es) will be applied")
            except Exception as e:
                logger.warning(f"Job {job_id}: Failed to decode paint_image_base64: {e}")
                decal_paint_path = None
                if not paint_file or not os.path.exists(paint_file):
                    return jsonify({"error": "Invalid paint_image_base64 and no valid paint_file"}), 400

        # Decode stamp image if provided
        stamp_image_base64 = data.get("stamp_image_base64")
        if stamp_image_base64:
            try:
                import base64
                raw = stamp_image_base64
                if raw.startswith("data:"):
                    raw = raw.split(",", 1)[-1]
                buf = base64.b64decode(raw)
                stamp_image_path = os.path.join(job_dir, "stamp_overlay.png")
                with open(stamp_image_path, "wb") as f:
                    f.write(buf)
                logger.info(f"Job {job_id}: Stamp overlay saved ({stamp_spec_finish})")
            except Exception as e:
                logger.warning(f"Job {job_id}: Failed to decode stamp_image_base64: {e}")
                stamp_image_path = None

        # AUTO-PURGE: keep only most recent 2 job dirs (server-side temp output). This does NOT
        # touch the user's output_dir or any "Shokker Paint Booth" subfolder (manual saves).
        try:
            job_dirs = sorted(
                [d for d in os.listdir(OUTPUT_FOLDER) if d.startswith('job_') and os.path.isdir(os.path.join(OUTPUT_FOLDER, d))],
                key=lambda d: os.path.getmtime(os.path.join(OUTPUT_FOLDER, d)),
                reverse=True
            )
            for old_dir in job_dirs[2:]:  # Keep 2 most recent, delete rest
                old_path = os.path.join(OUTPUT_FOLDER, old_dir)
                try:
                    shutil.rmtree(old_path)
                except Exception:
                    pass
        except Exception:
            pass

        recolor_rules = data.get("recolor_rules", [])
        recolor_mask_rle = data.get("recolor_mask", None)
        recolor_mask_has_include = data.get("recolor_mask_has_include", False)

        logger.info(f"Job {job_id}: {len(zones)} zones, paint={os.path.basename(paint_file)}"
                     f", helmet={'yes' if helmet_paint else 'default'}"
                     f", suit={'yes' if suit_paint else 'default'}"
                     f", wear={wear_level}"
                     f"{f', recolor={len(recolor_rules)} rules' if recolor_rules else ''}"
                     f"{', +mask' if recolor_mask_rle else ''}")
        # Log each zone's render path for diagnostics
        for i, z in enumerate(zones):
            # Log overlay data if present
            if z.get('second_base') or z.get('second_base_color_source'):
                logger.info(f"  Zone {i+1} OVERLAY: 2nd_base={z.get('second_base')}, color_src={z.get('second_base_color_source')}, strength={z.get('second_base_strength')}, blend={z.get('second_base_blend_mode')}, color={z.get('second_base_color')}")
            # Determine which render path this zone will take
            if z.get('base'):
                path_label = f"base={z['base']} pattern={z.get('pattern','none')}"
            elif z.get('finish'):
                path_label = f"finish={z['finish']}"
                if z.get('pattern') and z.get('pattern') != 'none':
                    path_label += f" +overlay={z['pattern']}"
            else:
                path_label = "fallback (no base or finish)"
            logger.info(f"  Zone {i+1}: {path_label} "
                        f"color={str(z.get('color','?'))[:40]} intensity={z.get('intensity','?')} "
                        f"wear={z.get('wear_level',0)} stack={len(z.get('pattern_stack',[])) if z.get('pattern_stack') else 0}")
        start = time.time()

        # Apply paint recoloring if any rules are provided
        actual_paint_file = paint_file
        if recolor_rules:
            try:
                actual_paint_file = apply_paint_recolor(paint_file, recolor_rules, job_dir,
                                                         recolor_mask_rle, recolor_mask_has_include)
                logger.info(f"Job {job_id}: Applied {len(recolor_rules)} recolor rules -> {os.path.basename(actual_paint_file)}")
            except Exception as e:
                logger.warning(f"Job {job_id}: Recolor failed ({e}), using original paint")
                actual_paint_file = paint_file

        # Determine car folder name for export
        cfg = load_config()
        car_folder_name = cfg.get("active_car", "unknown")

        # Run the full pipeline (car + helmet + suit + wear + optional zip)
        # Decode spatial_mask RLE for each zone before engine call
        for z in zones:
            # Decode region_mask RLE (same as preview-render)
            if z.get("region_mask") and isinstance(z["region_mask"], (dict, str)):
                try:
                    import numpy as np
                    rle = z["region_mask"]
                    if isinstance(rle, str):
                        rle = json.loads(rle)
                    rw = rle.get("width", 0)
                    rh = rle.get("height", 0)
                    runs = rle.get("runs", [])
                    flat = np.zeros(rw * rh, dtype=np.float32)
                    pos = 0
                    for run_val, run_len in runs:
                        # Client sends binary 0/1; engine expects float 0.0 or 1.0 (not 0/255)
                        flat[pos:pos + run_len] = float(run_val) / 255.0 if run_val else 0.0
                        pos += run_len
                    z["region_mask"] = flat.reshape((rh, rw))
                except Exception:
                    z.pop("region_mask", None)

            # Decode source_layer_mask RLE (same as preview-render)
            if z.get("source_layer_mask") and isinstance(z["source_layer_mask"], (dict, str)):
                try:
                    import numpy as np
                    rle = z["source_layer_mask"]
                    if isinstance(rle, str):
                        rle = json.loads(rle)
                    rw = rle.get("width", 0)
                    rh = rle.get("height", 0)
                    runs = rle.get("runs", [])
                    flat = np.zeros(rw * rh, dtype=np.float32)
                    pos = 0
                    for run_val, run_len in runs:
                        flat[pos:pos + run_len] = float(run_val) / 255.0 if run_val else 0.0
                        pos += run_len
                    z["source_layer_mask"] = flat.reshape((rh, rw))
                except Exception:
                    z.pop("source_layer_mask", None)

            # Decode source_layer_rgb_png so the engine can color-match against
            # the layer's unblended pixels (Photoshop-correct behavior).
            if z.get("source_layer_rgb_png"):
                try:
                    import base64 as _b64lr, io as _iolr, numpy as np
                    from PIL import Image as _PILlr
                    _raw = z["source_layer_rgb_png"]
                    if _raw.startswith("data:"):
                        _raw = _raw.split(",", 1)[-1]
                    _img = _PILlr.open(_iolr.BytesIO(_b64lr.b64decode(_raw))).convert("RGBA")
                    z["source_layer_rgb"] = np.asarray(_img, dtype=np.uint8)
                except Exception as _slr_err_r:
                    z.pop("source_layer_rgb", None)

            # Decode spatial_mask RLE
            if z.get("spatial_mask") and isinstance(z["spatial_mask"], (dict, str)):
                try:
                    import numpy as np
                    rle = z["spatial_mask"]
                    if isinstance(rle, str):
                        rle = json.loads(rle)
                    rw = rle.get("width", 0)
                    rh = rle.get("height", 0)
                    runs = rle.get("runs", [])
                    flat = np.zeros(rw * rh, dtype=np.uint8)
                    pos = 0
                    for run_val, run_len in runs:
                        flat[pos:pos + run_len] = int(run_val)
                        pos += run_len
                    z["spatial_mask"] = flat.reshape((rh, rw))
                    # Engine uses region_mask first and skips color+spatial; when spatial is set, drop region_mask
                    z.pop("region_mask", None)
                except Exception:
                    z.pop("spatial_mask", None)

            # Decode pattern_strength_map RLE
            if z.get("pattern_strength_map") and isinstance(z["pattern_strength_map"], (dict, str)):
                try:
                    import numpy as np
                    psm_rle = z["pattern_strength_map"]
                    if isinstance(psm_rle, str):
                        psm_rle = json.loads(psm_rle)
                    psm_w = psm_rle.get("width", 0)
                    psm_h = psm_rle.get("height", 0)
                    psm_runs = psm_rle.get("runs", [])
                    psm_flat = np.zeros(psm_w * psm_h, dtype=np.float32)
                    psm_pos = 0
                    for run_val, run_len in psm_runs:
                        psm_flat[psm_pos:psm_pos + run_len] = float(run_val) / 255.0
                        psm_pos += run_len
                    z["pattern_strength_map"] = psm_flat.reshape((psm_h, psm_w))
                except Exception:
                    z.pop("pattern_strength_map", None)

        # Update render progress for UI polling
        _render_progress["active"] = True
        _render_progress["job_id"] = job_id
        _render_progress["total_zones"] = len(zones)
        _render_progress["current_zone"] = 0
        _render_progress["phase"] = "rendering"
        _render_progress["started_at"] = time.time()

        # Progress callback: updates _render_progress so the UI can poll per-zone status
        def _progress_cb(zone_num, total, zone_name):
            _render_progress["current_zone"] = zone_num
            _render_progress["current_zone_name"] = zone_name
            _render_progress["elapsed_ms"] = int((time.time() - _render_progress["started_at"]) * 1000)

        results = engine.full_render_pipeline(
            car_paint_file=actual_paint_file,
            output_dir=job_dir,
            zones=zones,
            iracing_id=iracing_id,
            seed=seed,
            helmet_paint_file=helmet_paint,
            suit_paint_file=suit_paint,
            wear_level=wear_level,
            car_folder_name=car_folder_name,
            export_zip=export_zip,
            dual_spec=dual_spec,
            night_boost=night_boost,
            import_spec_map=import_spec_map,
            car_prefix=car_prefix,
            stamp_image=stamp_image_path,
            stamp_spec_finish=stamp_spec_finish,
            decal_spec_finishes=decal_spec_finishes if decal_spec_finishes else None,
            decal_paint_path=decal_paint_path,
            decal_mask_base64=decal_mask_base64 or None,
            progress_callback=_progress_cb,
        )

        _render_progress["phase"] = "encoding"
        _render_progress["current_zone"] = len(zones)

        elapsed = time.time() - start
        _render_progress["elapsed_ms"] = int(elapsed * 1000)
        _render_progress["phase"] = "done"
        _render_progress["active"] = False
        logger.info(f"Job {job_id}: completed in {elapsed:.1f}s")
        try:
            _render_paint_src = os.path.join(job_dir, f"{car_prefix}_{iracing_id}.tga")
            _render_paint_png = os.path.join(job_dir, "RENDER_paint.png")
            if os.path.exists(_render_paint_src):
                from PIL import Image as PILImage
                PILImage.open(_render_paint_src).save(_render_paint_png)
        except Exception as _paint_png_err:
            logger.warning(f"Job {job_id}: failed to generate RENDER_paint.png: {_paint_png_err}")

        # ── Track render statistics ──
        with _render_stats_lock:
            if _render_stats["session_start"] is None:
                _render_stats["session_start"] = time.time()
            _render_stats["total_renders"] += 1
            _render_stats["total_render_time"] += elapsed
            for z in zones:
                zname = z.get("name", "unnamed")
                if zname not in _render_stats["zone_times"]:
                    _render_stats["zone_times"][zname] = []
                _render_stats["zone_times"][zname].append(elapsed / max(1, len(zones)))

        # ── PERSIST latest render outputs so SHOKK save always has access ──
        # These survive auto-purge (they live in OUTPUT_FOLDER root, not job_*)
        try:
            _latest_dir = os.path.join(OUTPUT_FOLDER, "_latest_render")
            os.makedirs(_latest_dir, exist_ok=True)
            _spec_src = os.path.join(job_dir, f"car_spec_{iracing_id}.tga")
            _paint_src = os.path.join(job_dir, f"{car_prefix}_{iracing_id}.tga")
            _preview_src = os.path.join(job_dir, "RENDER_paint.png")
            if not os.path.exists(_preview_src):
                _preview_src = os.path.join(job_dir, "PREVIEW_paint.png")
            if os.path.exists(_spec_src):
                shutil.copy2(_spec_src, os.path.join(_latest_dir, "spec.tga"))
            if os.path.exists(_paint_src):
                shutil.copy2(_paint_src, os.path.join(_latest_dir, "paint.tga"))
            if os.path.exists(_preview_src):
                shutil.copy2(_preview_src, os.path.join(_latest_dir, "preview.png"))
            # Also save a spec PNG for quick loading
            _spec_png_src = os.path.join(job_dir, "RENDER_spec.png")
            if not os.path.exists(_spec_png_src):
                _spec_png_src = os.path.join(job_dir, "spec.png")
            if os.path.exists(_spec_png_src):
                shutil.copy2(_spec_png_src, os.path.join(_latest_dir, "spec.png"))
            elif os.path.exists(_spec_src):
                # Convert TGA to PNG for SHOKK embedding
                try:
                    from PIL import Image as PILImage
                    PILImage.open(_spec_src).save(os.path.join(_latest_dir, "spec.png"))
                except Exception:
                    pass
            logger.info(f"Job {job_id}: persisted latest render to _latest_render/")
        except Exception as _lr_e:
            logger.warning(f"Job {job_id}: failed to persist latest render: {_lr_e}")

        # Build preview URLs (scan job dir for all PNGs)
        preview_urls = {}
        for fname in os.listdir(job_dir):
            if fname.endswith('.png'):
                preview_urls[fname] = f"/preview/{job_id}/{fname}"

        # Build download URLs for all TGA files
        download_urls = {}
        for fname in os.listdir(job_dir):
            if fname.endswith('.tga'):
                key = fname.replace('.tga', '')
                download_urls[key] = f"/download/{job_id}/{fname}"

        # ZIP download URL
        zip_url = None
        if export_zip and "export_zip" in results:
            zip_name = os.path.basename(results["export_zip"])
            zip_url = f"/download/{job_id}/{zip_name}"

        # Build list of TGA files to push to the output folder
        # car_prefix is "car_num" (custom numbers) or "car" (no custom numbers)
        # spec is ALWAYS "car_spec" regardless
        files_to_push = [
            (f"{car_prefix}_{iracing_id}.tga", f"{car_prefix}_{iracing_id}.tga"),
            (f"car_spec_{iracing_id}.tga", f"car_spec_{iracing_id}.tga"),
        ]
        # PSD-style channel breakdown: car file + spec file + R,G,B,A channel TGAs for PSD import
        spec_tga = os.path.join(job_dir, f"car_spec_{iracing_id}.tga")
        if os.path.exists(spec_tga):
            try:
                import numpy as np
                from PIL import Image as PILImage
                img = PILImage.open(spec_tga).convert("RGBA")
                arr = np.array(img)
                for fname, ch_idx in [
                    ("spec_metallic.tga", 0),
                    ("spec_roughness.tga", 1),
                    ("spec_clearcoat.tga", 2),
                    ("spec_mask.tga", 3),
                ]:
                    ch = arr[:, :, ch_idx]
                    rgb = np.stack([ch, ch, ch], axis=-1)
                    engine.write_tga_24bit(os.path.join(job_dir, fname), rgb)
                    files_to_push.append((fname, fname))
            except Exception as e:
                logger.warning(f"Channel TGA export failed: {e}")
        paint_tga = os.path.join(job_dir, f"{car_prefix}_{iracing_id}.tga")
        if os.path.exists(paint_tga):
            try:
                shutil.copy2(paint_tga, os.path.join(job_dir, "paint_base.tga"))
                files_to_push.append(("paint_base.tga", "paint_base.tga"))
            except Exception as e:
                logger.warning(f"paint_base.tga copy failed: {e}")

        if "helmet_spec" in results:
            files_to_push.append(
                (f"helmet_spec_{iracing_id}.tga", f"helmet_spec_{iracing_id}.tga"))
        if "helmet_paint" in results:
            files_to_push.append(
                (f"helmet_{iracing_id}.tga", f"helmet_{iracing_id}.tga"))
        if "suit_spec" in results:
            files_to_push.append(
                (f"suit_spec_{iracing_id}.tga", f"suit_spec_{iracing_id}.tga"))
        if "suit_paint" in results:
            files_to_push.append(
                (f"suit_{iracing_id}.tga", f"suit_{iracing_id}.tga"))

        def _push_files_to_dir(target_dir, label="output"):
            """Copy rendered TGAs to a target directory with backup of originals."""
            pushed = []
            for src_name, dst_name in files_to_push:
                src = os.path.join(job_dir, src_name)
                dst = os.path.join(target_dir, dst_name)
                if os.path.exists(src):
                    # Back up originals (first time only)
                    backup = os.path.join(target_dir, f"ORIGINAL_{dst_name}")
                    if os.path.exists(dst) and not os.path.exists(backup):
                        try:
                            shutil.copyfile(dst, backup)
                        except Exception as e:
                            logger.warning(f"Could not backup {dst}: {e}")
                    
                    # Copy new file over. iRacing locking the file metadata 
                    # causes standard copy2 to throw [Errno 22] Invalid argument.
                    # copyfile only copies data and avoids metadata updates.
                    retries = 3
                    for attempt in range(retries):
                        try:
                            shutil.copyfile(src, dst)
                            pushed.append(dst_name)
                            break
                        except OSError as e:
                            if attempt < retries - 1:
                                time.sleep(0.2) # Wait for iRacing to finish reading
                            else:
                                raise Exception(f"Failed to push {dst_name} after {retries} attempts: {str(e)}")
            logger.info(f"{label}: pushed {len(pushed)} files to {target_dir}")
            return pushed

        # PRIMARY: Copy output TGAs to the user-specified output folder
        output_dir_status = None
        if output_dir_user and output_dir_user.strip():
            target = os.path.normpath(output_dir_user.strip())
            if os.path.isdir(target):
                try:
                    pushed = _push_files_to_dir(target, "Output Dir")
                    output_dir_status = {
                        "success": True,
                        "path": target,
                        "pushed_files": pushed,
                        "message": f"Saved {len(pushed)} files to {target}"
                    }
                except Exception as e:
                    output_dir_status = {"success": False, "path": target, "error": str(e)}
                    logger.error(f"Output Dir error: {e}")
            else:
                output_dir_status = {
                    "success": False,
                    "path": target,
                    "error": f"iRacing folder not found: {target}"
                }

        # SECONDARY: iRacing Live Link (config-based, if user also has it enabled)
        live_link_status = None
        if use_live_link:
            active_car = cfg.get("active_car")
            car_path = cfg.get("car_paths", {}).get(active_car) if active_car else None
            # Use output_dir as live link target if no config car path
            if not car_path and output_dir_user:
                car_path = os.path.normpath(output_dir_user.strip())
                active_car = os.path.basename(car_path)

            if car_path and os.path.isdir(car_path):
                try:
                    pushed = _push_files_to_dir(car_path, "Live Link")
                    live_link_status = {
                        "success": True,
                        "car": active_car,
                        "path": car_path,
                        "pushed_files": pushed,
                        "message": f"Pushed {len(pushed)} files to iRacing! Alt+Tab and Ctrl+R."
                    }
                except Exception as e:
                    live_link_status = {"success": False, "error": str(e)}
                    logger.error(f"Live Link error: {e}")
            else:
                live_link_status = {
                    "success": False,
                    "error": "No active car configured. Set up iRacing Live Link in settings."
                }

        result = {
            "success": True,
            "job_id": job_id,
            "elapsed_seconds": round(elapsed, 2),
            "zone_count": len(zones),
            "wear_level": wear_level,
            "preview_urls": preview_urls,
            "download_urls": download_urls,
            "includes": {
                "car": True,
                "helmet": "helmet_spec" in results,
                "suit": "suit_spec" in results,
                "wear": wear_level > 0,
            },
        }
        if zip_url:
            result["export_zip_url"] = zip_url
        if output_dir_status:
            result["output_dir"] = output_dir_status
        if live_link_status:
            result["live_link"] = live_link_status

        # Cleanup: delete TGA files from job dir (already pushed to output/iRacing).
        # Keep only preview PNGs so the browser can still fetch them.
        try:
            for fname in os.listdir(job_dir):
                if fname.endswith('.tga'):
                    try:
                        os.remove(os.path.join(job_dir, fname))
                    except Exception:
                        pass
        except Exception:
            pass

        return jsonify(result)

    except Exception as e:
        logger.error(f"Render error: {traceback.format_exc()}")
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
    finally:
        # Release render lock so previews can resume
        try:
            _preview_render_lock.release()
        except RuntimeError:
            pass  # Already released


def _photoshop_exchange_root():
    """Default folder for Photoshop round-trip: Documents/ShokkerPaintBooth/PhotoshopExchange."""
    return os.path.join(os.path.expanduser("~"), "Documents", "ShokkerPaintBooth", "PhotoshopExchange")


@app.route('/api/export-to-photoshop', methods=['POST'])
def export_to_photoshop():
    """
    Export current zones as a named "car file" for Photoshop: paint.tga, spec.tga, channel TGAs
    (spec_metallic, spec_roughness, spec_clearcoat, spec_mask, paint_base), and manifest.json
    in exchange_folder/car_file_name/. No iRacing output; for round-trip workflow.
    Body: paint_file (or paint_image_base64), zones, car_file_name, exchange_folder (optional).
    """
    try:
        data = request.get_json() or {}
        paint_file = data.get("paint_file")
        paint_image_base64 = data.get("paint_image_base64")
        if not paint_file and not paint_image_base64:
            return jsonify({"error": "Missing 'paint_file' or 'paint_image_base64'"}), 400
        if paint_file and not paint_image_base64 and not os.path.exists(paint_file):
            return jsonify({"error": f"Paint file not found: {paint_file}"}), 404

        zones = [_convert_zone_keys(z) for z in data.get("zones", [])]
        import_spec_map_early = data.get("import_spec_map")
        if not zones and not import_spec_map_early:
            return jsonify({"error": "No zones provided"}), 400
        # Reject runaway zone arrays before we spend any CPU on them.
        if len(zones) > MAX_ZONES_PER_REQUEST:
            return jsonify({
                "error": "too_many_zones",
                "message": f"Zone count {len(zones)} exceeds limit {MAX_ZONES_PER_REQUEST}.",
                "limit": MAX_ZONES_PER_REQUEST,
            }), 400

        car_file_name = (data.get("car_file_name") or "shokker_export").strip()
        if not car_file_name:
            car_file_name = "shokker_export"
        # Sanitize for filesystem
        car_file_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in car_file_name).strip() or "shokker_export"

        exchange_root = (data.get("exchange_folder") or "").strip() or _photoshop_exchange_root()
        exchange_root = os.path.normpath(exchange_root)
        exchange_dir = os.path.join(exchange_root, car_file_name)
        os.makedirs(exchange_dir, exist_ok=True)

        iracing_id = "00000"
        seed = int(data.get("seed", 51))
        job_id = f"{int(time.time())}_{iracing_id}"
        job_dir = os.path.join(OUTPUT_FOLDER, f"job_{job_id}")
        os.makedirs(job_dir, exist_ok=True)

        if paint_image_base64:
            try:
                raw = paint_image_base64
                if raw.startswith("data:"):
                    raw = raw.split(",", 1)[-1]
                buf = base64.b64decode(raw)
                decal_paint_path = os.path.join(job_dir, "paint_with_decals.png")
                with open(decal_paint_path, "wb") as f:
                    f.write(buf)
                paint_file = decal_paint_path
            except Exception as e:
                return jsonify({"error": f"Invalid paint_image_base64: {e}"}), 400

        actual_paint_file = paint_file
        recolor_rules = data.get("recolor_rules", [])
        recolor_mask_rle = data.get("recolor_mask", None)
        recolor_mask_has_include = data.get("recolor_mask_has_include", False)
        if recolor_rules:
            try:
                actual_paint_file = apply_paint_recolor(
                    paint_file, recolor_rules, job_dir, recolor_mask_rle, recolor_mask_has_include
                )
            except Exception:
                actual_paint_file = paint_file

        for z in zones:
            if z.get("region_mask") and isinstance(z["region_mask"], (dict, str)):
                try:
                    import numpy as np
                    rle = z["region_mask"]
                    if isinstance(rle, str):
                        rle = json.loads(rle)
                    rw, rh = rle.get("width", 0), rle.get("height", 0)
                    runs = rle.get("runs", [])
                    flat = np.zeros(rw * rh, dtype=np.float32)
                    pos = 0
                    for run_val, run_len in runs:
                        flat[pos:pos + run_len] = float(run_val) / 255.0 if run_val else 0.0
                        pos += run_len
                    z["region_mask"] = flat.reshape((rh, rw))
                except Exception:
                    z.pop("region_mask", None)
            if z.get("source_layer_mask") and isinstance(z["source_layer_mask"], (dict, str)):
                try:
                    import numpy as np
                    rle = z["source_layer_mask"]
                    if isinstance(rle, str):
                        rle = json.loads(rle)
                    rw, rh = rle.get("width", 0), rle.get("height", 0)
                    runs = rle.get("runs", [])
                    flat = np.zeros(rw * rh, dtype=np.float32)
                    pos = 0
                    for run_val, run_len in runs:
                        flat[pos:pos + run_len] = float(run_val) / 255.0 if run_val else 0.0
                        pos += run_len
                    z["source_layer_mask"] = flat.reshape((rh, rw))
                except Exception:
                    z.pop("source_layer_mask", None)
            # PARITY FIX: export-to-photoshop must also decode layer-local RGB
            # so color matching is Photoshop-correct (matches /render and
            # /preview-render semantics exactly).
            if z.get("source_layer_rgb_png"):
                try:
                    import base64 as _b64lr, io as _iolr, numpy as np
                    from PIL import Image as _PILlr
                    _raw = z["source_layer_rgb_png"]
                    if _raw.startswith("data:"):
                        _raw = _raw.split(",", 1)[-1]
                    _img = _PILlr.open(_iolr.BytesIO(_b64lr.b64decode(_raw))).convert("RGBA")
                    z["source_layer_rgb"] = np.asarray(_img, dtype=np.uint8)
                except Exception:
                    z.pop("source_layer_rgb", None)
            if z.get("spatial_mask") and isinstance(z["spatial_mask"], (dict, str)):
                try:
                    import numpy as np
                    rle = z["spatial_mask"]
                    if isinstance(rle, str):
                        rle = json.loads(rle)
                    rw, rh = rle.get("width", 0), rle.get("height", 0)
                    runs = rle.get("runs", [])
                    flat = np.zeros(rw * rh, dtype=np.uint8)
                    pos = 0
                    for run_val, run_len in runs:
                        flat[pos:pos + run_len] = int(run_val)
                        pos += run_len
                    z["spatial_mask"] = flat.reshape((rh, rw))
                    z.pop("region_mask", None)
                except Exception:
                    z.pop("spatial_mask", None)
            # Decode pattern_strength_map RLE
            if z.get("pattern_strength_map") and isinstance(z["pattern_strength_map"], (dict, str)):
                try:
                    import numpy as np
                    psm_rle = z["pattern_strength_map"]
                    if isinstance(psm_rle, str):
                        psm_rle = json.loads(psm_rle)
                    psm_w = psm_rle.get("width", 0)
                    psm_h = psm_rle.get("height", 0)
                    psm_runs = psm_rle.get("runs", [])
                    psm_flat = np.zeros(psm_w * psm_h, dtype=np.float32)
                    psm_pos = 0
                    for run_val, run_len in psm_runs:
                        psm_flat[psm_pos:psm_pos + run_len] = float(run_val) / 255.0
                        psm_pos += run_len
                    z["pattern_strength_map"] = psm_flat.reshape((psm_h, psm_w))
                except Exception:
                    z.pop("pattern_strength_map", None)

        _imp = data.get("import_spec_map")
        _import_spec_map = _imp if (_imp and os.path.exists(_imp)) else None
        results = engine.full_render_pipeline(
            car_paint_file=actual_paint_file,
            output_dir=job_dir,
            zones=zones,
            iracing_id=iracing_id,
            seed=seed,
            helmet_paint_file=None,
            suit_paint_file=None,
            wear_level=0,
            car_folder_name=car_file_name,
            export_zip=False,
            dual_spec=False,
            night_boost=0.7,
            import_spec_map=_import_spec_map,
            car_prefix="car_num",
        )

        # Generate channel TGAs in job_dir (same as main render path) so we can copy base + spec + channels
        spec_tga = os.path.join(job_dir, f"car_spec_{iracing_id}.tga")
        if os.path.exists(spec_tga):
            try:
                import numpy as np
                from PIL import Image as PILImage
                img = PILImage.open(spec_tga).convert("RGBA")
                arr = np.array(img)
                for fname, ch_idx in [
                    ("spec_metallic.tga", 0),
                    ("spec_roughness.tga", 1),
                    ("spec_clearcoat.tga", 2),
                    ("spec_mask.tga", 3),
                ]:
                    ch = arr[:, :, ch_idx]
                    rgb = np.stack([ch, ch, ch], axis=-1)
                    engine.write_tga_24bit(os.path.join(job_dir, fname), rgb)
            except Exception as e:
                logger.warning(f"Export to Photoshop: channel TGA export failed: {e}")
        paint_tga = os.path.join(job_dir, f"car_num_{iracing_id}.tga")
        if os.path.exists(paint_tga):
            try:
                shutil.copy2(paint_tga, os.path.join(job_dir, "paint_base.tga"))
            except Exception as e:
                logger.warning(f"Export to Photoshop: paint_base.tga copy failed: {e}")

        # Copy to exchange dir with named files: {car_file_name}.tga, {car_file_name} Spec.tga, etc.
        base_name = car_file_name
        paint_src = os.path.join(job_dir, f"car_num_{iracing_id}.tga")
        spec_src = os.path.join(job_dir, f"car_spec_{iracing_id}.tga")
        paint_dst = os.path.join(exchange_dir, f"{base_name}.tga")
        spec_dst = os.path.join(exchange_dir, f"{base_name} Spec.tga")
        if os.path.exists(paint_src):
            shutil.copy2(paint_src, paint_dst)
        if os.path.exists(spec_src):
            shutil.copy2(spec_src, spec_dst)

        channel_map = [
            ("spec_metallic.tga", f"{base_name} spec_metallic.tga"),
            ("spec_roughness.tga", f"{base_name} spec_roughness.tga"),
            ("spec_clearcoat.tga", f"{base_name} spec_clearcoat.tga"),
            ("spec_mask.tga", f"{base_name} spec_mask.tga"),
            ("paint_base.tga", f"{base_name} paint_base.tga"),
        ]
        for src_fname, dst_fname in channel_map:
            src = os.path.join(job_dir, src_fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(exchange_dir, dst_fname))

        channel_files = [dst_f for _, dst_f in channel_map if os.path.exists(os.path.join(exchange_dir, dst_f))]
        manifest = {
            "name": car_file_name,
            "paint_path": paint_dst,
            "spec_path": spec_dst,
            "channel_files": channel_files,
            "timestamp": int(time.time()),
            "exchange_dir": exchange_dir,
        }
        manifest_path = os.path.join(exchange_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        # Write last_export.json in exchange root so Photoshop script can find "latest"
        last_export = {"car_file_name": car_file_name, "exchange_dir": exchange_dir, "timestamp": manifest["timestamp"]}
        with open(os.path.join(exchange_root, "last_export.json"), "w") as f:
            json.dump(last_export, f)

        logger.info(f"Export to Photoshop: {car_file_name} -> {exchange_dir}")
        return jsonify({
            "success": True,
            "car_file_name": car_file_name,
            "exchange_dir": exchange_dir,
            "manifest_path": manifest_path,
        })
    except Exception as e:
        logger.exception("export-to-photoshop")
        return jsonify({"error": str(e)}), 500


def _photoshop_safe_join(root, subpath):
    """Join root with subpath; ensure result is under root (no .. escape). Return None if invalid."""
    if ".." in subpath or subpath.startswith("/"):
        return None
    root = os.path.normpath(root)
    full = os.path.normpath(os.path.join(root, subpath))
    try:
        real_root = os.path.realpath(root)
        real_full = os.path.realpath(full)
        if real_full != real_root and not real_full.startswith(real_root + os.sep):
            return None
    except OSError:
        return None
    return full


@app.route('/api/photoshop-import-list', methods=['GET'])
def photoshop_import_list():
    """
    List subfolders and .tga files in exchange_folder (optionally under subpath).
    Query: exchange_folder (optional), subpath (optional, e.g. "" or "CosmicDLM").
    Returns: {"subfolders": ["name1", ...], "files": ["a.tga", ...]}.
    """
    exchange_root = (request.args.get("exchange_folder") or "").strip() or _photoshop_exchange_root()
    exchange_root = os.path.normpath(exchange_root)
    if not os.path.isdir(exchange_root):
        return jsonify({"error": "Exchange folder not found."}), 404
    subpath = (request.args.get("subpath") or "").strip().replace("\\", "/").strip("/")
    list_dir = exchange_root if not subpath else _photoshop_safe_join(exchange_root, subpath)
    if list_dir is None or not os.path.isdir(list_dir):
        return jsonify({"subfolders": [], "files": []})
    subfolders = []
    files = []
    for name in sorted(os.listdir(list_dir)):
        full = os.path.join(list_dir, name)
        if os.path.isdir(full):
            subfolders.append(name)
        elif name.lower().endswith(".tga"):
            files.append(name)
    return jsonify({"subfolders": subfolders, "files": files})


@app.route('/api/photoshop-import-file', methods=['GET'])
def photoshop_import_file():
    """
    Serve a TGA file by path relative to exchange_folder.
    Query: exchange_folder (optional), path (required, e.g. "CosmicDLM/paint.tga" or "CosmicDLM/DLM438-base-001.tga").
    """
    exchange_root = (request.args.get("exchange_folder") or "").strip() or _photoshop_exchange_root()
    exchange_root = os.path.normpath(exchange_root)
    if not os.path.isdir(exchange_root):
        return jsonify({"error": "Exchange folder not found."}), 404
    path_arg = (request.args.get("path") or "").strip().replace("\\", "/").lstrip("/")
    if not path_arg:
        return jsonify({"error": "Missing path."}), 400
    full_path = _photoshop_safe_join(exchange_root, path_arg)
    if full_path is None or not os.path.isfile(full_path):
        return jsonify({"error": "File not found or path invalid."}), 404
    return send_file(full_path, mimetype="image/x-tga", as_attachment=False)


@app.route('/api/photoshop-import-paint', methods=['GET'])
def photoshop_import_paint():
    """
    Serve paint file. If path= is given, serve that file under exchange_folder; else import_for_shokker/paint.tga.
    Query: exchange_folder (optional), path (optional, e.g. "CosmicDLM/DLM438-base-001.tga").
    """
    exchange_root = (request.args.get("exchange_folder") or "").strip() or _photoshop_exchange_root()
    exchange_root = os.path.normpath(exchange_root)
    if not os.path.isdir(exchange_root):
        return jsonify({"error": "Exchange folder not found."}), 404
    path_arg = (request.args.get("path") or "").strip().replace("\\", "/").lstrip("/")
    if path_arg:
        full_path = _photoshop_safe_join(exchange_root, path_arg)
        if full_path is None or not os.path.isfile(full_path):
            return jsonify({"error": "Paint file not found."}), 404
        return send_file(full_path, mimetype="image/x-tga", as_attachment=False)
    import_dir = os.path.join(exchange_root, "import_for_shokker")
    paint_path = os.path.join(import_dir, "paint.tga")
    if not os.path.isfile(paint_path):
        return jsonify({"error": "No paint file in import folder. Put paint.tga in import_for_shokker or pick a file."}), 404
    return send_file(paint_path, mimetype="image/x-tga", as_attachment=False)


@app.route('/api/photoshop-import-spec', methods=['GET'])
def photoshop_import_spec():
    """
    Serve spec map from exchange_folder/import_for_shokker/spec.tga.
    Query: exchange_folder (optional).
    """
    exchange_root = (request.args.get("exchange_folder") or "").strip() or _photoshop_exchange_root()
    exchange_root = os.path.normpath(exchange_root)
    if not os.path.isdir(exchange_root):
        return jsonify({"error": "Exchange folder not found."}), 404
    import_dir = os.path.join(exchange_root, "import_for_shokker")
    spec_path = os.path.join(import_dir, "spec.tga")
    if not os.path.isfile(spec_path):
        return jsonify({"error": "No spec file in import folder. Put spec.tga in import_for_shokker."}), 404
    return send_file(spec_path, mimetype="image/x-tga", as_attachment=False)


@app.route('/api/photoshop-import-spec-from-last-export', methods=['POST'])
def photoshop_import_spec_from_last_export():
    """
    One-click: find the spec TGA from the most recent 'Export to Photoshop',
    copy to temp, return path so client can set importedSpecMapPath.
    Looks at last_export.json → exchange_dir → finds the *Spec.tga or spec.tga.
    """
    try:
        data = request.get_json() or {}
        exchange_root = (data.get("exchange_folder") or "").strip() or _photoshop_exchange_root()
        exchange_root = os.path.normpath(exchange_root)

        spec_src = None

        # Try last_export.json to find the most recent car folder
        last_export_path = os.path.join(exchange_root, "last_export.json")
        if os.path.isfile(last_export_path):
            try:
                with open(last_export_path) as f:
                    last = json.load(f)
                car_dir = last.get("exchange_dir", "")
                if car_dir and os.path.isdir(car_dir):
                    # Look for any *Spec.tga or spec.tga in that folder
                    for fname in os.listdir(car_dir):
                        if fname.lower().endswith(".tga") and ("spec" in fname.lower()) and ("metallic" not in fname.lower()) and ("roughness" not in fname.lower()) and ("clearcoat" not in fname.lower()) and ("mask" not in fname.lower()):
                            spec_src = os.path.join(car_dir, fname)
                            break
            except Exception:
                pass

        # Fallback: scan exchange_root for any subfolder with a spec TGA
        if not spec_src and os.path.isdir(exchange_root):
            for name in sorted(os.listdir(exchange_root), reverse=True):
                sub = os.path.join(exchange_root, name)
                if os.path.isdir(sub):
                    for fname in os.listdir(sub):
                        if fname.lower().endswith(".tga") and ("spec" in fname.lower()) and ("metallic" not in fname.lower()) and ("roughness" not in fname.lower()) and ("clearcoat" not in fname.lower()) and ("mask" not in fname.lower()):
                            spec_src = os.path.join(sub, fname)
                            break
                    if spec_src:
                        break

        if not spec_src or not os.path.isfile(spec_src):
            return jsonify({"error": "No spec map found from a previous export. Export to Photoshop first."}), 404

        from PIL import Image as PILImage
        temp_dir = os.path.join(OUTPUT_FOLDER, 'temp_spec_imports')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f'imported_spec_ps_{int(time.time())}.tga')
        shutil.copy2(spec_src, temp_path)
        img = PILImage.open(temp_path)
        spec_name = os.path.basename(spec_src)
        return jsonify({
            "success": True,
            "temp_path": temp_path.replace("\\", "/"),
            "resolution": [img.width, img.height],
            "source_file": spec_name,
        })
    except Exception as e:
        logger.exception("photoshop-import-spec-from-last-export")
        return jsonify({"error": str(e)}), 500


@app.route('/api/photoshop-exchange-root', methods=['GET'])
def photoshop_exchange_root():
    """Return the default Photoshop exchange folder path for UI."""
    return jsonify({"path": _photoshop_exchange_root()})


@app.route('/save-render-to-keep', methods=['POST'])
def save_render_to_keep():
    """Copy the current render files from the output folder into a 'Shokker Paint Booth' subfolder
    with timestamped names, so they are kept and never overwritten by the next render.
    Body: {"output_dir": "C:/path/to/iRacing/paint/carname", "iracing_id": "23371"}.
    """
    try:
        data = request.get_json() or {}
        output_dir = (data.get("output_dir") or "").strip()
        if not output_dir:
            return jsonify({"success": False, "error": "Missing output_dir"}), 400
        target_dir = os.path.normpath(output_dir)
        if not os.path.isdir(target_dir):
            return jsonify({"success": False, "error": f"Output folder not found: {target_dir}"}), 400
        # Subfolder where manual saves go (never auto-overwritten)
        keep_subfolder = "Shokker Paint Booth"
        keep_dir = os.path.join(target_dir, keep_subfolder)
        os.makedirs(keep_dir, exist_ok=True)
        # Timestamp for unique filenames
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        saved = []
        # Channel breakdown for PSD import (same names as render push)
        channel_tgas = ("paint_base.tga", "spec_metallic.tga", "spec_roughness.tga", "spec_clearcoat.tga", "spec_mask.tga")
        for fname in os.listdir(target_dir):
            if not fname.endswith(".tga"):
                continue
            # Copy render output TGAs + PSD channel breakdown (car_num_, car_spec_, paint_base, spec_metallic, etc.)
            if fname in channel_tgas:
                pass  # include
            elif not (fname.startswith("car_num_") or fname.startswith("car_spec_") or
                      (fname.startswith("car_") and not fname.startswith("car_spec_")) or
                      fname.startswith("helmet_") or fname.startswith("suit_")):
                continue
            src = os.path.join(target_dir, fname)
            if not os.path.isfile(src):
                continue
            base, ext = os.path.splitext(fname)
            dest_name = f"{base}_{ts}{ext}"
            dest = os.path.join(keep_dir, dest_name)
            try:
                shutil.copy2(src, dest)
                saved.append(dest_name)
            except Exception as e:
                logger.warning(f"save-render-to-keep: could not copy {fname}: {e}")
        if not saved:
            return jsonify({
                "success": False,
                "error": "No render TGA files found in the output folder. Render first, then click Save to keep."
            }), 400
        return jsonify({
            "success": True,
            "path": keep_dir,
            "saved_files": saved,
            "message": f"Saved {len(saved)} file(s) to {keep_subfolder}/"
        })
    except Exception as e:
        logger.exception("save-render-to-keep")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/preview/<job_id>/<filename>', methods=['GET'])
def get_preview(job_id, filename):
    """Serve preview PNGs to the browser."""
    safe_job = os.path.basename(job_id)
    safe_file = os.path.basename(filename)
    path = os.path.join(OUTPUT_FOLDER, f"job_{safe_job}", safe_file)
    if os.path.exists(path):
        return send_file(path, mimetype='image/png')
    return jsonify({"error": "File not found"}), 404


@app.route('/download/<job_id>/<filename>', methods=['GET'])
def download_file(job_id, filename):
    """Download output TGA files."""
    safe_job = os.path.basename(job_id)
    safe_file = os.path.basename(filename)
    path = os.path.join(OUTPUT_FOLDER, f"job_{safe_job}", safe_file)
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name=safe_file)
    return jsonify({"error": "File not found"}), 404


@app.route('/reset-backup', methods=['POST'])
def reset_backup():
    """Delete the ORIGINAL_ backup so next render creates a fresh one.
    Use this if the backup was accidentally created from an already-rendered file.
    Body: {"paint_file": "E:/path/to/car_num_23371.tga"}
    """
    try:
        data = request.get_json() or {}
        paint_file = data.get("paint_file", "")
        if not paint_file:
            return jsonify({"error": "Missing paint_file"}), 400
        paint_file = os.path.normpath(os.path.abspath(paint_file))
        source_dir = os.path.dirname(paint_file)
        basename = os.path.basename(paint_file)
        backup_path = os.path.join(source_dir, f"ORIGINAL_{basename}")
        deleted = []
        if os.path.exists(backup_path):
            os.remove(backup_path)
            deleted.append(backup_path)
            logger.info(f"Reset backup: deleted {backup_path}")
        # Also check the output folder for any ORIGINAL_ copies
        output_backup = os.path.join(source_dir, f"ORIGINAL_car_spec_{data.get('iracing_id', '00000')}.tga")
        if os.path.exists(output_backup):
            os.remove(output_backup)
            deleted.append(output_backup)
        return jsonify({"success": True, "deleted": deleted,
                        "message": f"Cleared {len(deleted)} backup(s). Next render will use the current source file."})
    except Exception as e:
        logger.error(f"Reset backup error: {e}")
        return jsonify({"error": str(e)}), 500


# LRU cache for TGA→PNG previews (keyed by path + mtime, max 8 entries)
_tga_preview_cache = {}  # {key: (mtime, png_bytes)}
_TGA_CACHE_MAX = 8

@app.route('/preview-tga', methods=['POST'])
def preview_tga():
    """Convert a local TGA file to PNG and serve it for browser display.
    Body: {"path": "E:/path/to/car_num_23371.tga"}
    Caches up to 8 recent results so switching cars is instant on revisit.
    """
    logger.debug("[preview-tga] TGA preview requested")
    try:
        from PIL import Image as PILImage
        import io
        data = request.get_json() or {}
        tga_path = data.get('path', '')
        if not tga_path or not os.path.isfile(tga_path):
            return jsonify({"error": "File not found"}), 404

        # Check cache — hit if same path + same modification time
        try:
            mtime = os.path.getmtime(tga_path)
        except OSError:
            mtime = 0
        cache_key = f"{tga_path}|{mtime}"
        if cache_key in _tga_preview_cache:
            logger.debug(f"[preview-tga] Cache hit: {os.path.basename(tga_path)}")
            buf = io.BytesIO(_tga_preview_cache[cache_key])
            buf.seek(0)
            return send_file(buf, mimetype='image/png')

        img = PILImage.open(tga_path)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        png_bytes = buf.getvalue()

        # Store in cache (evict oldest if full)
        if len(_tga_preview_cache) >= _TGA_CACHE_MAX:
            oldest_key = next(iter(_tga_preview_cache))
            del _tga_preview_cache[oldest_key]
        _tga_preview_cache[cache_key] = png_bytes
        logger.debug(f"[preview-tga] Cached: {os.path.basename(tga_path)} ({len(png_bytes)//1024}KB)")

        buf.seek(0)
        return send_file(io.BytesIO(png_bytes), mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


### ===== SWATCH GENERATION =====
SWATCH_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swatches')
os.makedirs(SWATCH_FOLDER, exist_ok=True)

# Clear swatch cache on startup so rebuilt finishes get fresh thumbnails
_swatch_files = [f for f in os.listdir(SWATCH_FOLDER) if f.endswith('.png')]
if _swatch_files:
    for f in _swatch_files:
        try:
            os.remove(os.path.join(SWATCH_FOLDER, f))
        except OSError:
            pass
    logger.info(f"Cleared {len(_swatch_files)} cached swatches for fresh regeneration")

@app.route('/swatch/<base_id>/<pattern_id>')
def get_swatch(base_id, pattern_id):
    """Generate a 64x64 swatch thumbnail for a base+pattern finish combination.
    Cached to disk for instant repeat loads."""
    try:
        from PIL import Image as PILImage
        import io
        import numpy as np

        cache_file = os.path.join(SWATCH_FOLDER, f"{base_id}_{pattern_id}.png")
        if os.path.exists(cache_file):
            return send_file(cache_file, mimetype='image/png')

        # Validate IDs
        if base_id not in engine.BASE_REGISTRY:
            return jsonify({"error": f"Unknown base: {base_id}"}), 404
        if pattern_id != "none" and pattern_id not in engine.PATTERN_REGISTRY:
            return jsonify({"error": f"Unknown pattern: {pattern_id}"}), 404

        # Generate at 128x128 for better pattern visibility, downscale to 64x64
        render_shape = (128, 128)
        output_size = (64, 64)
        mask = np.ones(render_shape, dtype=np.float32)
        spec = engine.compose_finish(base_id, pattern_id, render_shape, mask, 51, 1.0)

        # Visualize spec as visible color:
        # Metallic -> brightness, Roughness -> darkness, Clearcoat -> blue tint
        metallic = spec[:,:,0].astype(np.float32) / 255.0
        roughness = spec[:,:,1].astype(np.float32) / 255.0
        clearcoat = np.clip(1.0 - spec[:,:,2].astype(np.float32) / 64.0, 0, 1)

        # Base gray shifted by metallic (bright = more metallic)
        r = np.clip(0.3 + metallic * 0.5 - roughness * 0.15 + clearcoat * 0.1, 0, 1)
        g = np.clip(0.3 + metallic * 0.45 - roughness * 0.15 + clearcoat * 0.15, 0, 1)
        b = np.clip(0.35 + metallic * 0.4 - roughness * 0.1 + clearcoat * 0.2, 0, 1)

        rgb = np.stack([r, g, b], axis=2)
        rgb_uint8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)

        img = PILImage.fromarray(rgb_uint8, 'RGB')
        img = img.resize(output_size, PILImage.LANCZOS)
        img.save(cache_file, 'PNG')
        return send_file(cache_file, mimetype='image/png')

    except Exception as e:
        logger.error(f"Swatch error {base_id}/{pattern_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/swatch/pattern/<pattern_id>')
def get_pattern_swatch(pattern_id):
    """Generate a 64x64 swatch showing the actual pattern texture.
    Renders the texture function at 256x256 and visualizes the pattern_val
    (plus M/R channels if available) as a tinted grayscale image.
    Cached to disk for instant repeat loads."""
    try:
        from PIL import Image as PILImage
        import io
        import numpy as np

        cache_file = os.path.join(SWATCH_FOLDER, f"pat_{pattern_id}.png")
        if os.path.exists(cache_file):
            return send_file(cache_file, mimetype='image/png')

        if pattern_id not in engine.PATTERN_REGISTRY:
            return jsonify({"error": f"Unknown pattern: {pattern_id}"}), 404

        registry = engine.PATTERN_REGISTRY[pattern_id]
        tex_fn = registry.get("texture_fn")
        if tex_fn is None:
            # No texture - return a dark gray placeholder
            img = PILImage.new('RGB', (64, 64), (40, 40, 50))
            img.save(cache_file, 'PNG')
            return send_file(cache_file, mimetype='image/png')

        # Render texture at 256x256 for good detail
        render_shape = (256, 256)
        output_size = (64, 64)
        mask = np.ones(render_shape, dtype=np.float32)

        # Call texture function (handle both 3-arg and 4-arg signatures)
        import inspect
        sig = inspect.signature(tex_fn)
        n_params = len(sig.parameters)
        if n_params >= 4:
            tex = tex_fn(render_shape, mask, 42, 1.0)
        elif n_params >= 2:
            tex = tex_fn(render_shape, 42)
        else:
            tex = tex_fn(render_shape)

        # Extract pattern channels
        if isinstance(tex, dict):
            pv = tex.get("pattern_val", np.zeros(render_shape, dtype=np.float32))
            M_pat = tex.get("M_pattern")
            R_pat = tex.get("R_pattern")
        else:
            pv = tex if isinstance(tex, np.ndarray) else np.zeros(render_shape, dtype=np.float32)
            M_pat = None
            R_pat = None

        # Ensure correct shape
        if pv.shape != render_shape:
            from PIL import Image as _Img
            pv_img = _Img.fromarray((np.clip(pv, 0, 1) * 255).astype(np.uint8))
            pv_img = pv_img.resize(render_shape, _Img.LANCZOS)
            pv = np.array(pv_img, dtype=np.float32) / 255.0

        # Get the swatch tint color from the PATTERNS array (from the HTML)
        # Use a neutral teal/blue tint for the pattern
        swatch_color = registry.get("_swatch_rgb")
        if swatch_color is None:
            # Default: cool slate blue tint for spec-map patterns
            tint_r, tint_g, tint_b = 0.55, 0.65, 0.85

        if M_pat is not None and R_pat is not None:
            # Independent channels: visualize M as brightness, R as inverse darkness
            # M_pat high = bright/chrome, R_pat high = dark/rough
            M_p = np.clip(M_pat, 0, 1) if M_pat.shape == render_shape else np.clip(pv, 0, 1)
            R_p = np.clip(R_pat, 0, 1) if R_pat.shape == render_shape else np.clip(1.0 - pv, 0, 1)
            # Create RGB visualization: M → brightness, 1-R → smoothness highlight
            brightness = M_p * 0.6 + (1.0 - R_p) * 0.4
            r = np.clip(brightness * tint_r + 0.1, 0, 1)
            g = np.clip(brightness * tint_g + 0.08, 0, 1)
            b = np.clip(brightness * tint_b + 0.12, 0, 1)
        else:
            # Simple pattern: use pattern_val as luminance with tint
            pv_n = np.clip(pv, 0, 1)
            r = np.clip(pv_n * tint_r * 0.8 + 0.12, 0, 1)
            g = np.clip(pv_n * tint_g * 0.8 + 0.10, 0, 1)
            b = np.clip(pv_n * tint_b * 0.8 + 0.14, 0, 1)

        # Stack and convert to image
        rgb = np.stack([r, g, b], axis=2)
        rgb_uint8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)

        img = PILImage.fromarray(rgb_uint8, 'RGB')
        img = img.resize(output_size, PILImage.LANCZOS)
        img.save(cache_file, 'PNG')
        return send_file(cache_file, mimetype='image/png')

    except Exception as e:
        logger.error(f"Pattern swatch error {pattern_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/swatch/mono/<finish_id>')
def get_mono_swatch(finish_id):
    """Generate a swatch for a monolithic finish.
    Renders at 256x256 for gradient/noise finishes, then downscales to 64x64.
    This fixes Prizm, Chameleon, Multi, and SHOKK thumbnails that need
    higher resolution to show their effects properly."""
    try:
        from PIL import Image as PILImage
        import io
        import numpy as np

        cache_file = os.path.join(SWATCH_FOLDER, f"{_swatch_cache_token()}_mono_{finish_id}.png")
        if os.path.exists(cache_file):
            return send_file(cache_file, mimetype='image/png')

        if finish_id not in engine.MONOLITHIC_REGISTRY:
            return jsonify({"error": f"Unknown monolithic: {finish_id}"}), 404

        # Render at 256x256 for proper gradient/noise visibility, then downscale
        render_size = (256, 256)
        output_size = (64, 64)
        shape = render_size
        mask = np.ones(shape, dtype=np.float32)
        spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[finish_id]

        spec = _normalize_spec_result_to_rgba(spec_fn(shape, mask, 51, 1.0), shape)
        if spec is None:
            spec = np.zeros((shape[0], shape[1], 4), dtype=np.float32)
            spec[:, :, 0] = 5
            spec[:, :, 1] = 100
            spec[:, :, 2] = 16
            spec[:, :, 3] = 255

        # Create a neutral gray paint for the monolithic to modify
        neutral = np.ones((render_size[0], render_size[1], 3), dtype=np.float32) * 0.5
        painted = paint_fn(neutral, shape, mask, 51, 1.0, 0.10)

        # Blend spec visualization with paint color
        metallic = spec[:,:,0].astype(np.float32) / 255.0
        roughness = spec[:,:,1].astype(np.float32) / 255.0

        # Use paint color tinted by spec properties
        paint_rgb = np.clip(painted, 0, 1)
        brightness = 0.6 + metallic * 0.4 - roughness * 0.2
        result = paint_rgb * brightness[:,:,np.newaxis]

        rgb_uint8 = (np.clip(result, 0, 1) * 255).astype(np.uint8)

        img = PILImage.fromarray(rgb_uint8, 'RGB')
        # Downscale from render_size to output_size for clean thumbnail
        if render_size != output_size:
            img = img.resize(output_size, PILImage.LANCZOS)
        img.save(cache_file, 'PNG')
        return send_file(cache_file, mimetype='image/png')

    except Exception as e:
        logger.error(f"Mono swatch error {finish_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/upload-composited-paint', methods=['POST'])
def upload_composited_paint():
    """Receive a composited paint PNG (with decals baked in) and save as temp TGA.
    Body: {"paint_data": "data:image/png;base64,...", "iracing_id": "23371"}
    Returns: {"temp_path": "E:/path/to/temp_composited.tga"}
    """
    try:
        from PIL import Image as PILImage
        import numpy as np

        data = request.get_json() or {}
        paint_data = data.get('paint_data', '')
        iracing_id = data.get('iracing_id', '00000')

        if not paint_data or not paint_data.startswith('data:image'):
            return jsonify({"error": "Missing or invalid paint_data"}), 400

        # Decode base64 PNG
        b64_start = paint_data.index(',') + 1
        img_bytes = base64.b64decode(paint_data[b64_start:])
        img = PILImage.open(io.BytesIO(img_bytes)).convert('RGB')

        # Save as TGA (24-bit, top-left origin matching iRacing format)
        temp_dir = os.path.join(OUTPUT_FOLDER, 'temp_composites')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f'composited_{iracing_id}_{int(time.time())}.tga')

        # PIL can save TGA directly
        img.save(temp_path, 'TGA')

        return jsonify({
            "success": True,
            "temp_path": temp_path.replace("\\", "/"),
            "resolution": [img.width, img.height]
        })

    except Exception as e:
        logger.error(f"Composited paint upload error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/upload-paint-file', methods=['POST'])
def api_upload_paint_file():
    """Accept a paint TGA (or image) file upload; save to server and return path for use as Source Paint.
    Used when user picks a TGA from LOAD SHOKK → Spec Map + New TGA so render uses that file, not the header path.
    """
    try:
        if 'file' not in request.files and 'paint_file' not in request.files:
            return jsonify({"error": "No file in request. Send multipart with 'file' or 'paint_file'."}), 400
        f = request.files.get('file') or request.files.get('paint_file')
        if not f or not f.filename:
            return jsonify({"error": "No file selected"}), 400
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in f.filename)
        upload_dir = os.path.join(OUTPUT_FOLDER, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        path = os.path.join(upload_dir, f"paint_{int(time.time())}_{safe_name}")
        f.save(path)
        path_abs = os.path.abspath(path).replace("\\", "/")
        return jsonify({"ok": True, "path": path_abs})
    except Exception as e:
        logger.error(f"Upload paint file error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/serve-local-file', methods=['POST'])
def api_serve_local_file():
    """Verify a local file path exists and return a URL the client can fetch it from.
    Used by SHOKK load fallback when paint wasn't baked into the SHOKK file.
    Body: { path: "C:/path/to/paint.tga" }
    Returns: { ok: true, url: "/api/serve-local-file/download?p=..." }
    """
    try:
        data = request.get_json() or {}
        file_path = data.get("path", "").strip()
        if not file_path:
            return jsonify({"error": "No path provided"}), 400
        # Normalize path
        file_path = os.path.abspath(file_path)
        if not os.path.isfile(file_path):
            return jsonify({"ok": False, "error": f"File not found: {file_path}"}), 404
        # URL-encode the path for safe transport
        import urllib.parse
        encoded = urllib.parse.quote(file_path, safe='')
        return jsonify({"ok": True, "url": f"/api/serve-local-file/download?p={encoded}"})
    except Exception as e:
        logger.error(f"serve-local-file error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/serve-local-file/download', methods=['GET'])
def api_serve_local_file_download():
    """Serve a local file to the client (for SHOKK paint fallback loading).
    Only serves image files (TGA/PNG/JPG) to prevent arbitrary file access."""
    import urllib.parse
    file_path = urllib.parse.unquote(request.args.get('p', ''))
    if not file_path:
        return jsonify({"error": "No path"}), 400
    file_path = os.path.abspath(file_path)
    # Path traversal protection: block .. components
    if ".." in file_path.split(os.sep):
        logger.warning(f"[serve-local-file] Path traversal attempt blocked: {file_path}")
        return jsonify({"error": "Invalid path"}), 400
    if not os.path.isfile(file_path):
        return jsonify({"error": "File not found"}), 404
    # Only serve image file types — prevents serving arbitrary system files
    ext = os.path.splitext(file_path)[1].lower()
    allowed_types = {'.tga': 'image/tga', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
    mimetype = allowed_types.get(ext)
    if not mimetype:
        logger.warning(f"[serve-local-file] Rejected non-image file type: {ext}")
        return jsonify({"error": f"File type '{ext}' not allowed. Only TGA/PNG/JPG permitted."}), 400
    logger.debug(f"[serve-local-file] Serving: {os.path.basename(file_path)}")
    return send_file(file_path, mimetype=mimetype, as_attachment=False)


@app.route('/upload-spec-map', methods=['POST'])
def upload_spec_map():
    """Receive a spec map TGA/PNG (base64) for import & merge mode.
    Body: {"spec_data": "data:image/...;base64,..."}
      OR: {"spec_path": "E:/path/to/existing_spec.tga"}
    Returns: {"temp_path": "E:/path/to/imported_spec.tga", "resolution": [w, h]}
    """
    logger.info("[upload-spec-map] Spec map upload requested")
    try:
        from PIL import Image as PILImage
        import numpy as np

        data = request.get_json() or {}
        spec_data = data.get('spec_data', '')
        spec_path = data.get('spec_path', '')

        temp_dir = os.path.join(OUTPUT_FOLDER, 'temp_spec_imports')
        os.makedirs(temp_dir, exist_ok=True)

        if spec_path and os.path.isfile(spec_path):
            # Direct file path - just validate and return
            img = PILImage.open(spec_path)
            return jsonify({
                "success": True,
                "temp_path": spec_path.replace("\\", "/"),
                "resolution": [img.width, img.height],
                "mode": img.mode,
            })

        if not spec_data or not spec_data.startswith('data:image'):
            return jsonify({"error": "Missing spec_data or spec_path"}), 400

        # Decode base64 image
        b64_start = spec_data.index(',') + 1
        img_bytes = base64.b64decode(spec_data[b64_start:])
        img = PILImage.open(io.BytesIO(img_bytes))

        # Preserve RGBA if present (spec maps are 32-bit RGBA)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        temp_path = os.path.join(temp_dir, f'imported_spec_{int(time.time())}.tga')
        img.save(temp_path, 'TGA')

        logger.info(f"Spec map imported: {img.width}x{img.height} {img.mode} -> {temp_path}")
        return jsonify({
            "success": True,
            "temp_path": temp_path.replace("\\", "/"),
            "resolution": [img.width, img.height],
            "mode": "RGBA",
        })

    except Exception as e:
        logger.error(f"Spec map upload error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/upload-tga-decal', methods=['POST'])
def upload_tga_decal():
    """Convert an uploaded TGA file to PNG for use as a decal.
    Accepts multipart form POST with a 'file' field containing a .tga file.
    Returns: {"success": true, "png_base64": "data:image/png;base64,...", "width": N, "height": N}
    """
    try:
        from PIL import Image as PILImage
        import tempfile, uuid

        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        f = request.files['file']
        if not f.filename.lower().endswith('.tga'):
            return jsonify({"error": "File must be a TGA"}), 400

        # Save TGA temporarily
        temp_tga = os.path.join(tempfile.gettempdir(), f"decal_{uuid.uuid4().hex}.tga")
        f.save(temp_tga)

        # Convert to RGBA PNG
        img = PILImage.open(temp_tga).convert('RGBA')
        temp_png = temp_tga.replace('.tga', '.png')
        img.save(temp_png, 'PNG')

        # Clean up TGA
        try:
            os.remove(temp_tga)
        except Exception:
            pass

        # Read PNG as base64
        with open(temp_png, 'rb') as pf:
            png_b64 = base64.b64encode(pf.read()).decode('utf-8')

        try:
            os.remove(temp_png)
        except Exception:
            pass

        logger.info(f"TGA decal uploaded: {f.filename} -> {img.width}x{img.height} PNG")
        return jsonify({
            "success": True,
            "png_base64": f"data:image/png;base64,{png_b64}",
            "width": img.width,
            "height": img.height,
        })
    except Exception as e:
        logger.error(f"TGA decal upload error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/check-file', methods=['POST'])
def check_file():
    """Check if a file path exists on disk. Used by UI to validate Source Paint paths."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid or missing JSON body"}), 400
        if 'path' not in data:
            return jsonify({"error": "Missing 'path' field in request"}), 400
        path = data['path']
        logger.debug(f"[check-file] Checking: {path}")
        exists = os.path.exists(path)
        is_file = os.path.isfile(path) if exists else False
        size = os.path.getsize(path) if is_file else 0
        return jsonify({
            "path": path,
            "exists": exists,
            "is_file": is_file,
            "size": size,
            "size_human": f"{size / 1024:.0f} KB" if size > 0 else "0",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/browse-files', methods=['POST'])
def browse_files():
    """Browse filesystem directories. Returns folders and files for the UI file picker.
    Body: {"path": "E:/some/dir", "filter": ".tga"}  (filter is optional)
    Single-pass scandir - detects large dirs dynamically and switches to folders-only.
    """
    try:
        data = request.get_json(silent=True) or {}
        logger.debug(f"[browse-files] path={data.get('path', '(root)')}")
        browse_path = data.get('path', '')
        file_filter = data.get('filter', '').lower()

        # Default starting locations if no path given
        if not browse_path:
            drives = []
            for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                drive = f"{letter}:/"
                if os.path.exists(drive):
                    drives.append({"name": f"{letter}:", "path": drive, "type": "drive"})
            user_home = os.path.expanduser("~")
            quick_navs = []
            iracing_paint = os.path.join(user_home, "Documents", "iRacing", "paint")
            if os.path.isdir(iracing_paint):
                quick_navs.append({"name": "iRacing Paint Folder", "path": iracing_paint.replace("\\", "/"), "type": "shortcut"})
            cfg = load_config()
            for car_name, car_path in cfg.get("car_paths", {}).items():
                if os.path.isdir(car_path):
                    quick_navs.append({"name": f"Live Link: {car_name}", "path": car_path.replace("\\", "/"), "type": "shortcut"})
            return jsonify({"path": "", "drives": drives, "quick_navs": quick_navs, "items": []})

        browse_path = os.path.normpath(browse_path)
        if not os.path.isdir(browse_path):
            return jsonify({"error": f"Not a directory: {browse_path}"}), 400

        import subprocess as _sp

        MAX_FILES = 200
        LARGE_DIR_THRESHOLD = 300
        folders = []
        files = []
        total_files = 0
        entry_count = 0
        large_dir = False

        # --- FAST PATH: use Windows dir /b /ad to get ONLY folder names ---
        # This avoids Python touching every file entry (which triggers Defender scans).
        # We first try the fast path; if it finds many entries we skip the slow scandir.
        fast_folders = None
        try:
            r = _sp.run(
                ['cmd', '/c', 'dir', '/b', '/ad', browse_path],
                capture_output=True, text=True, timeout=8
            )
            if r.returncode == 0 and r.stdout.strip():
                raw_names = [n.strip() for n in r.stdout.splitlines() if n.strip()]
                fast_folders = []
                for nm in raw_names:
                    if nm.startswith('.'):
                        continue
                    fp = os.path.join(browse_path, nm).replace("\\", "/")
                    fast_folders.append({"name": nm, "path": fp, "type": "folder"})
        except Exception:
            fast_folders = None  # fall back to scandir

        # Decide: if dir /b /ad returned results, use a quick entry count to decide fast vs slow
        if fast_folders is not None:
            # Quick count: how many total entries?
            # Use dir /b WITHOUT pipe (pipe+shell=True hangs on Python 3.13/Windows)
            try:
                r2 = _sp.run(
                    ['cmd', '/c', 'dir', '/b', browse_path],
                    capture_output=True, text=True, timeout=8
                )
                entry_count = len(r2.stdout.strip().splitlines()) if r2.returncode == 0 and r2.stdout.strip() else 0
            except Exception:
                entry_count = len(fast_folders) + 500  # assume large if count fails

            if entry_count > LARGE_DIR_THRESHOLD:
                # Large directory - use ONLY the folder names from dir /b /ad
                large_dir = True
                folders = fast_folders
                folders.sort(key=lambda x: x["name"].lower())
                items = folders

                parent = os.path.dirname(browse_path)
                parent_path = parent.replace("\\", "/") if parent != browse_path else ""

                return jsonify({
                    "path": browse_path.replace("\\", "/"),
                    "parent": parent_path,
                    "items": items,
                    "total_folders": len(folders),
                    "total_files": 0,
                    "hidden_files": -1,
                    "large_dir": True,
                    "entry_count": entry_count,
                })

        # --- SLOW PATH: small directory, use scandir for full file listing ---
        try:
            with os.scandir(browse_path) as scanner:
                for entry in scanner:
                    if entry.name.startswith('.'):
                        continue
                    entry_count += 1
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            folders.append({"name": entry.name, "path": entry.path.replace("\\", "/"), "type": "folder"})
                        else:
                            if file_filter and not entry.name.lower().endswith(file_filter):
                                continue
                            total_files += 1
                            if len(files) < MAX_FILES:
                                try:
                                    size = entry.stat(follow_symlinks=False).st_size
                                except OSError:
                                    size = 0
                                files.append({
                                    "name": entry.name,
                                    "path": entry.path.replace("\\", "/"),
                                    "type": "file",
                                    "size": size,
                                    "size_human": f"{size / 1024:.0f} KB" if size > 0 else "0",
                                })
                    except OSError:
                        continue
        except PermissionError:
            return jsonify({"error": "Permission denied", "path": browse_path}), 403

        hidden_files = total_files - len(files)
        folders.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())
        items = folders + files

        parent = os.path.dirname(browse_path)
        parent_path = parent.replace("\\", "/") if parent != browse_path else ""

        return jsonify({
            "path": browse_path.replace("\\", "/"),
            "parent": parent_path,
            "items": items,
            "total_folders": len(folders),
            "total_files": total_files,
            "hidden_files": hidden_files,
            "large_dir": False,
            "entry_count": entry_count,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/iracing-cars', methods=['GET'])
def list_iracing_cars():
    """Discover car folders in the iRacing paint directory.
    Returns list of car folder names that exist in ~/Documents/iRacing/paint/
    """
    logger.info("[iracing-cars] Car discovery requested")
    try:
        user_home = os.path.expanduser("~")
        iracing_paint = os.path.join(user_home, "Documents", "iRacing", "paint")
        if not os.path.isdir(iracing_paint):
            return jsonify({"cars": [], "paint_dir": "", "error": "iRacing paint folder not found"})

        cars = []
        for entry in sorted(os.listdir(iracing_paint)):
            car_path = os.path.join(iracing_paint, entry)
            if os.path.isdir(car_path):
                # Check for existing paint files
                tga_count = len([f for f in os.listdir(car_path) if f.endswith('.tga')])
                cars.append({
                    "name": entry,
                    "path": car_path.replace("\\", "/"),
                    "tga_count": tga_count
                })

        return jsonify({
            "cars": cars,
            "paint_dir": iracing_paint.replace("\\", "/"),
            "count": len(cars)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/deploy-to-iracing', methods=['POST'])
def deploy_to_iracing():
    """One-click deploy: copy rendered TGAs from a job to an iRacing car folder.
    Body: {"job_id": "...", "car_folder": "dallaraarca", "iracing_id": "23371"}
    """
    try:
        data = request.get_json(silent=True) or {}
        logger.info(f"[deploy] Deploy requested: car={data.get('car_folder')}, job={data.get('job_id')}")
        job_id = data.get("job_id", "")
        car_folder = data.get("car_folder", "")
        iracing_id = data.get("iracing_id", "00000")

        if not job_id:
            return jsonify({"error": "Missing job_id"}), 400
        if not car_folder:
            return jsonify({"error": "Missing car_folder"}), 400
        # Validate iracing_id format using shared helper.
        ok_id, _norm_id, id_err = _validate_iracing_id(iracing_id)
        if not ok_id:
            return jsonify({"error": id_err}), 400
        iracing_id = _norm_id
        # Block path traversal in car_folder.
        if "/" in car_folder or "\\" in car_folder or ".." in car_folder:
            return jsonify({"error": "invalid car_folder name"}), 400

        user_home = os.path.expanduser("~")
        iracing_paint = os.path.join(user_home, "Documents", "iRacing", "paint")
        target_dir = os.path.join(iracing_paint, car_folder)

        # Create car folder if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)

        job_dir = os.path.join(OUTPUT_FOLDER, f"job_{job_id}")
        if not os.path.isdir(job_dir):
            return jsonify({"error": f"Job not found: {job_id}"}), 404

        # Deploy all TGA files
        deployed = []
        for fname in os.listdir(job_dir):
            if fname.endswith('.tga'):
                src = os.path.join(job_dir, fname)
                dst = os.path.join(target_dir, fname)
                # Backup original if exists
                backup = os.path.join(target_dir, f"ORIGINAL_{fname}")
                if os.path.exists(dst) and not os.path.exists(backup):
                    shutil.copy2(dst, backup)
                shutil.copy2(src, dst)
                deployed.append(fname)
                logger.info(f"Deploy: {fname} -> {target_dir}")

        return jsonify({
            "success": True,
            "deployed": deployed,
            "target": target_dir.replace("\\", "/"),
            "message": f"Deployed {len(deployed)} files to {car_folder}. Alt+Tab to iRacing and press Ctrl+R!"
        })

    except Exception as e:
        logger.error(f"Deploy error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/config', methods=['GET'])
def get_config():
    """Return current config."""
    logger.debug("[config] GET config requested")
    return jsonify(load_config())


@app.route('/config', methods=['POST'])
def set_config():
    """
    Update config. Merges with existing config.

    JSON body (all fields optional):
    {
        "iracing_id": "23371",
        "live_link_enabled": true,
        "active_car": "dallaraarca",
        "car_paths": {
            "dallaraarca": "C:/Users/You/Documents/iRacing/paint/dallaraarca",
            "stockcar_camaro": "C:/Users/You/Documents/iRacing/paint/stockcar_camaro"
        }
    }
    """
    try:
        updates = request.get_json(silent=True)
        if not updates:
            return jsonify({"error": "No JSON body. Send a JSON object with config fields to update."}), 400

        logger.info(f"[config] POST update: keys={list(updates.keys())}")
        cfg = load_config()

        # Merge updates
        if "iracing_id" in updates:
            cfg["iracing_id"] = str(updates["iracing_id"])
        if "live_link_enabled" in updates:
            cfg["live_link_enabled"] = bool(updates["live_link_enabled"])
        if "active_car" in updates:
            cfg["active_car"] = updates["active_car"]
        if "use_custom_number" in updates:
            cfg["use_custom_number"] = bool(updates["use_custom_number"])
        if "car_paths" in updates:
            cfg.setdefault("car_paths", {}).update(updates["car_paths"])
        if "imported_spec_path" in updates:
            v = updates["imported_spec_path"]
            cfg["imported_spec_path"] = str(v).strip() if v else None

        # Validate car paths exist
        warnings = []
        for car, path in cfg.get("car_paths", {}).items():
            if not os.path.isdir(path):
                warnings.append(f"Path for '{car}' not found: {path}")

        save_config(cfg)
        result = {"success": True, "config": cfg}
        if warnings:
            result["warnings"] = warnings
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Legacy endpoint (backward compat with old UI code)
@app.route('/apply-finish', methods=['POST'])
def apply_finish_legacy():
    """Legacy endpoint - redirects to /render format."""
    try:
        if 'paint_file' not in request.files:
            return jsonify({"error": "No paint file provided. Use /render with JSON instead."}), 400

        file = request.files['paint_file']
        filename = f"upload_{int(time.time())}_{file.filename}"
        upload_path = os.path.join(OUTPUT_FOLDER, 'uploads', filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)

        zones_str = request.form.get('zones', '[]')
        zones = json.loads(zones_str)
        iracing_id = request.form.get('iracing_id', '00000')
        req_id = request.form.get('request_id', str(int(time.time())))
        # Car prefix for legacy endpoint - read from config
        _legacy_cfg = load_config()
        _legacy_prefix = "car_num" if _legacy_cfg.get("use_custom_number", True) else "car"

        job_dir = os.path.join(OUTPUT_FOLDER, f"job_{req_id}")
        os.makedirs(job_dir, exist_ok=True)

        paint_rgb, combined_spec, masks = engine.build_multi_zone(
            paint_file=upload_path,
            output_dir=job_dir,
            zones=zones,
            iracing_id=iracing_id,
            car_prefix=_legacy_prefix,
        )

        return jsonify({
            "success": True,
            "job_id": req_id,
            "files": {
                "paint_tga": os.path.join(job_dir, f"{_legacy_prefix}_{iracing_id}.tga"),
                "spec_tga": os.path.join(job_dir, f"car_spec_{iracing_id}.tga"),
                "preview_paint": f"/preview/{req_id}/PREVIEW_paint.png",
                "preview_spec": f"/preview/{req_id}/PREVIEW_spec.png",
            }
        })

    except Exception as e:
        logger.error(f"Legacy endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


# ================================================================
# CLEANUP OLD RENDER JOBS
# ================================================================

@app.route('/cleanup', methods=['POST'])
def cleanup_jobs():
    """Delete old render job folders to free disk space.
    Body (optional): {"max_age_hours": 24}   (default: delete all jobs)
    """
    try:
        data = request.get_json(silent=True) or {}
        logger.info(f"[cleanup] Cleanup requested (max_age_hours={data.get('max_age_hours', 0)})")
        max_age_hours = data.get("max_age_hours", 0)  # 0 = delete all

        deleted = 0
        freed_bytes = 0
        kept = 0
        now = time.time()

        if not os.path.exists(OUTPUT_FOLDER):
            return jsonify({"success": True, "deleted": 0, "kept": 0, "freed_mb": 0})

        for entry in os.listdir(OUTPUT_FOLDER):
            if not entry.startswith("job_"):
                continue
            job_path = os.path.join(OUTPUT_FOLDER, entry)
            if not os.path.isdir(job_path):
                continue

            # Check age if max_age_hours > 0
            if max_age_hours > 0:
                age_hours = (now - os.path.getmtime(job_path)) / 3600
                if age_hours < max_age_hours:
                    kept += 1
                    continue

            # Calculate size before deleting
            for root, dirs, files in os.walk(job_path):
                for f in files:
                    try:
                        freed_bytes += os.path.getsize(os.path.join(root, f))
                    except:
                        pass

            shutil.rmtree(job_path, ignore_errors=True)
            deleted += 1

        freed_mb = round(freed_bytes / (1024 * 1024), 1)
        logger.info(f"Cleanup: deleted {deleted} jobs, freed {freed_mb}MB, kept {kept}")
        return jsonify({
            "success": True,
            "deleted": deleted,
            "kept": kept,
            "freed_mb": freed_mb,
            "message": f"Cleaned {deleted} render jobs, freed {freed_mb}MB"
        })
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        return jsonify({"error": str(e)}), 500


# ================================================================
# SHOKK FILE SYSTEM - .shokk paint recipe files
# ================================================================

def _get_shokk_manager():
    """Lazy-init the SHOKK manager (avoids import at module level)."""
    try:
        from shokk_manager import ShokkManager
        lib_dir = getattr(CFG, 'SHOKK_LIBRARY_DIR',
                          ShokkManager.get_default_library_path())
        factory_dir = getattr(CFG, 'SHOKK_FACTORY_DIR',
                              os.path.join(SERVER_DIR, 'shokk_factory'))
        return ShokkManager(lib_dir, factory_dir)
    except Exception as e:
        logger.error(f"ShokkManager init failed: {e}")
        return None


@app.route('/api/shokk/library-path', methods=['GET'])
def api_shokk_library_path():
    """Return the SHOKK Library folder path (for Open Folder button)."""
    mgr = _get_shokk_manager()
    if not mgr:
        return jsonify({"error": "SHOKK manager unavailable"}), 500
    return jsonify({"path": mgr.library_dir, "ok": True})


@app.route('/api/shokk/list', methods=['GET'])
def api_shokk_list():
    """List all .shokk files in the library + factory dirs."""
    logger.info("[shokk/list] Listing SHOKK library")
    mgr = _get_shokk_manager()
    if not mgr:
        return jsonify({"error": "SHOKK manager unavailable"}), 500
    try:
        entries = mgr.list_library()
        return jsonify({"ok": True, "shokks": entries, "count": len(entries)})
    except Exception as e:
        logger.error(f"/api/shokk/list error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/shokk/save', methods=['POST'])
def api_shokk_save():
    """
    Package and save current session as a .shokk file to the library.
    Body: { name, author, description, tags[], session_json{}, include_paint: bool }
    Uses the latest RENDER_spec.png and RENDER_paint.png from the most recent job.
    """
    logger.info("[shokk/save] Save requested")
    mgr = _get_shokk_manager()
    if not mgr:
        return jsonify({"error": "SHOKK manager unavailable"}), 500
    try:
        data = request.get_json() or {}
        name = data.get("name", "Untitled SHOKK").strip() or "Untitled SHOKK"
        author = data.get("author", "").strip()
        description = data.get("description", "").strip()
        tags = data.get("tags") or []
        session_json = data.get("session_json") or {}
        include_paint = data.get("include_paint", True)

        # Find the render job's spec and paint files
        spec_path = None
        def _find_job_files(job_dir):
            """Find spec, paint, and preview files in a job directory.
            Supports both legacy names (RENDER_spec.png, output.tga) and
            current names (car_spec_XXXXX.tga, car_num_XXXXX.tga, PREVIEW_paint.png)."""
            import glob
            _spec = None
            _paint = None
            _preview = None
            
            # Spec: try exact names first, then glob car_spec_*.tga
            for name in ("RENDER_spec.png", "spec.png"):
                p = os.path.join(job_dir, name)
                if os.path.exists(p):
                    _spec = p
                    break
            if not _spec:
                matches = glob.glob(os.path.join(job_dir, "car_spec_*.tga"))
                if matches:
                    _spec = matches[0]
            
            # Paint: try exact names first, then glob car_num_*.tga then car_*.tga
            for name in ("RENDER_paint.tga", "output.tga"):
                p = os.path.join(job_dir, name)
                if os.path.exists(p):
                    _paint = p
                    break
            if not _paint:
                # car_num_XXXXX.tga (custom numbers) or car_XXXXX.tga (standard)
                for pattern in ("car_num_*.tga", "car_*.tga"):
                    matches = glob.glob(os.path.join(job_dir, pattern))
                    # Exclude spec TGAs
                    matches = [m for m in matches if "spec" not in os.path.basename(m)]
                    if matches:
                        _paint = matches[0]
                        break
            
            # Preview: PREVIEW_paint.png takes priority
            for name in ("PREVIEW_paint.png", "preview.png", "preview.jpg"):
                p = os.path.join(job_dir, name)
                if os.path.exists(p):
                    _preview = p
                    break
            
            return _spec, _paint, _preview

        # If the frontend sent a specific job_id, use that FIRST
        target_job_id = data.get("job_id", "").strip()
        if target_job_id:
            target_job_dir = os.path.join(OUTPUT_FOLDER, f"job_{target_job_id}")
            if os.path.isdir(target_job_dir):
                spec_path, paint_path, preview_path = _find_job_files(target_job_dir)
                logger.info(f"SHOKK save: Using specific job_id={target_job_id} spec={spec_path is not None} paint={paint_path is not None}")

        # Fallback A: check _latest_render/ persistent copy (survives auto-purge)
        if not spec_path:
            _latest_dir = os.path.join(OUTPUT_FOLDER, "_latest_render")
            if os.path.isdir(_latest_dir):
                _ls, _lp, _lpr = None, None, None
                for sname in ("spec.png", "spec.tga"):
                    p = os.path.join(_latest_dir, sname)
                    if os.path.exists(p):
                        _ls = p
                        break
                for pname in ("paint.tga",):
                    p = os.path.join(_latest_dir, pname)
                    if os.path.exists(p):
                        _lp = p
                        break
                for prname in ("preview.png",):
                    p = os.path.join(_latest_dir, prname)
                    if os.path.exists(p):
                        _lpr = p
                        break
                if _ls:
                    spec_path = _ls
                    if not paint_path: paint_path = _lp
                    if not preview_path: preview_path = _lpr
                    logger.info(f"SHOKK save: Using _latest_render/ spec={spec_path is not None}")

        # Fallback B: scan for the most recent job if still not found
        if not spec_path:
            jobs = sorted(
                [d for d in os.listdir(OUTPUT_FOLDER) if d.startswith("job_")],
                key=lambda d: os.path.getmtime(os.path.join(OUTPUT_FOLDER, d)),
                reverse=True
            )

            for job in jobs:
                job_dir = os.path.join(OUTPUT_FOLDER, job)
                _s, _p, _pr = _find_job_files(job_dir)
                if _s:
                    spec_path = _s
                    if not paint_path: paint_path = _p
                    if not preview_path: preview_path = _pr
                    break

        out_path = mgr.save(
            name=name,
            author=author,
            description=description,
            tags=tags,
            session_json=session_json,
            spec_path=spec_path,
            paint_path=paint_path if include_paint else None,
            preview_path=preview_path,
            include_paint=include_paint,
            spb_version=getattr(CFG, 'VERSION', '5.0.0'),
        )

        import os.path as _op
        return jsonify({
            "ok": True,
            "path": out_path,
            "filename": _op.basename(out_path),
            "has_spec": spec_path is not None,
            "has_paint": include_paint and paint_path is not None,
        })
    except Exception as e:
        logger.error(f"/api/shokk/save error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/shokk/open', methods=['POST'])
def api_shokk_open():
    """
    Extract a .shokk file and return its contents.
    Body: { path: "/absolute/path/to/file.shokk" }
    Returns: { manifest, session_json, spec_path, paint_path }
    """
    logger.info("[shokk/open] Open requested")
    mgr = _get_shokk_manager()
    if not mgr:
        return jsonify({"error": "SHOKK manager unavailable"}), 500
    try:
        data = request.get_json() or {}
        shokk_path = data.get("path", "").strip()
        if not shokk_path or not os.path.exists(shokk_path):
            return jsonify({"error": f"File not found: {shokk_path}"}), 404

        # Extract to a temp dir inside the output folder (so server can serve files)
        import tempfile
        extract_dir = tempfile.mkdtemp(dir=OUTPUT_FOLDER, prefix="shokk_open_")
        result = mgr.open(shokk_path, extract_dir=extract_dir)

        # Client-fetchable URL for paint (so loadPaintImageFromPath can fetch it)
        paint_url = None
        if result.get("paint_path"):
            ext_basename = os.path.basename(extract_dir)
            paint_basename = os.path.basename(result["paint_path"])
            if ext_basename.startswith("shokk_open_") and paint_basename:
                paint_url = f"/api/shokk/extracted/{ext_basename}/{paint_basename}"

        return jsonify({
            "ok": True,
            "manifest": result["manifest"],
            "session_json": result["session_json"],
            "spec_path": result["spec_path"],
            "paint_path": result["paint_path"],
            "paint_url": paint_url,
            "extract_dir": extract_dir,
        })
    except Exception as e:
        logger.error(f"/api/shokk/open error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/shokk/extracted/<extract_basename>/<filename>', methods=['GET'])
def api_shokk_extracted_file(extract_basename, filename):
    """Serve a file from an extracted SHOKK dir (so client can load paint)."""
    safe_extract = os.path.basename(extract_basename)
    safe_file = os.path.basename(filename)
    if not safe_extract.startswith("shokk_open_") or not safe_file:
        return jsonify({"error": "Invalid path"}), 400
    path = os.path.join(OUTPUT_FOLDER, safe_extract, safe_file)
    path = os.path.abspath(path)
    out_abs = os.path.abspath(OUTPUT_FOLDER)
    if not path.startswith(out_abs + os.sep) and path != out_abs:
        return jsonify({"error": "Invalid path"}), 400
    if not os.path.isfile(path):
        return jsonify({"error": "File not found"}), 404
    mimetype = "image/tga" if safe_file.lower().endswith(".tga") else None
    return send_file(path, mimetype=mimetype, as_attachment=False)


@app.route('/api/shokk/preview/<filename>', methods=['GET'])
def api_shokk_preview(filename):
    """Serve the preview.jpg from inside a .shokk file in the library or factory dir."""
    mgr = _get_shokk_manager()
    if not mgr:
        return jsonify({"error": "SHOKK manager unavailable"}), 500
    try:
        # Search library + factory
        for search_dir in [mgr.library_dir, mgr.factory_dir]:
            if not search_dir:
                continue
            fpath = os.path.join(search_dir, filename)
            if os.path.exists(fpath):
                preview_bytes = mgr.get_preview_bytes(fpath)
                if preview_bytes:
                    from flask import Response as FlaskResponse
                    return FlaskResponse(preview_bytes, mimetype='image/jpeg',
                                        headers={'Cache-Control': 'max-age=3600'})
        # No preview found - return a placeholder
        return jsonify({"error": "No preview in this SHOKK file"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/shokk/delete', methods=['POST'])
def api_shokk_delete():
    """Delete a .shokk from the user library (never factory). Body: { filename }"""
    mgr = _get_shokk_manager()
    if not mgr:
        return jsonify({"error": "SHOKK manager unavailable"}), 500
    try:
        data = request.get_json() or {}
        filename = data.get("filename", "").strip()
        if not filename.endswith(".shokk"):
            return jsonify({"error": "Invalid filename"}), 400
        ok = mgr.delete(filename)
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/shokk/rename', methods=['POST'])
def api_shokk_rename():
    """Rename a .shokk in the user library (never factory). Body: { old_name, new_name }"""
    mgr = _get_shokk_manager()
    if not mgr:
        return jsonify({"error": "SHOKK manager unavailable"}), 500
    try:
        data = request.get_json() or {}
        old_name = data.get("old_name", "").strip()
        new_name = data.get("new_name", "").strip()
        if not old_name.endswith(".shokk") or not new_name.endswith(".shokk"):
            return jsonify({"error": "Invalid filename — must end in .shokk"}), 400
        # Sanitize new name: allow alphanumeric, spaces, dashes, underscores, dots
        safe_new = "".join(c if c.isalnum() or c in " ._-" else "_" for c in new_name)
        if not safe_new or safe_new == ".shokk":
            return jsonify({"error": "Invalid new name"}), 400
        old_path = os.path.join(mgr.library_dir, old_name)
        new_path = os.path.join(mgr.library_dir, safe_new)
        if not os.path.exists(old_path):
            return jsonify({"error": "File not found"}), 404
        if os.path.exists(new_path):
            return jsonify({"error": f'A file named "{safe_new}" already exists'}), 409
        os.rename(old_path, new_path)
        return jsonify({"ok": True, "new_name": safe_new})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================================================================
# PHOTOSHOP LAYER EXPORT (#21)
# ================================================================
@app.route('/export-psd-layers', methods=['POST'])
def export_psd_layers():
    """Export per-zone spec + paint images as a ZIP for Photoshop layer import.

    JSON body: same as /render (paint_file, zones, seed, etc.)
    plus optional: output_name (default: "shokker_layers")

    Returns a ZIP containing:
      per_zone_1_spec.png, per_zone_1_paint.png, ...
      combined_spec.png, combined_paint.png
      layers.json (zone metadata: names, blend modes, order)
    """
    logger.info("[export-psd-layers] PSD layer export requested")
    import zipfile
    import tempfile
    import numpy as np
    from PIL import Image as PILImage

    try:
        data = request.get_json() or {}
        paint_file = data.get("paint_file")
        paint_image_base64 = data.get("paint_image_base64")
        if not paint_file and not paint_image_base64:
            return jsonify({"error": "Missing 'paint_file' or 'paint_image_base64'"}), 400
        if paint_file and not paint_image_base64 and not os.path.exists(paint_file):
            return jsonify({"error": f"Paint file not found: {paint_file}"}), 404

        zones = [_convert_zone_keys(z) for z in data.get("zones", [])]
        if not zones:
            return jsonify({"error": "No zones provided"}), 400

        seed = int(data.get("seed", 51))
        output_name = (data.get("output_name") or "shokker_layers").strip()
        output_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in output_name).strip() or "shokker_layers"

        # Create a temp job directory for the render
        job_id = f"{int(time.time())}_layers"
        job_dir = os.path.join(OUTPUT_FOLDER, f"job_{job_id}")
        os.makedirs(job_dir, exist_ok=True)

        # Decode base64 paint if provided
        if paint_image_base64:
            try:
                raw = paint_image_base64
                if raw.startswith("data:"):
                    raw = raw.split(",", 1)[-1]
                buf = base64.b64decode(raw)
                decal_paint_path = os.path.join(job_dir, "paint_with_decals.png")
                with open(decal_paint_path, "wb") as f:
                    f.write(buf)
                paint_file = decal_paint_path
            except Exception as e:
                return jsonify({"error": f"Invalid paint_image_base64: {e}"}), 400

        # Apply recolor if provided
        actual_paint_file = paint_file
        recolor_rules = data.get("recolor_rules", [])
        if recolor_rules:
            try:
                actual_paint_file = apply_paint_recolor(paint_file, recolor_rules, job_dir)
            except Exception:
                actual_paint_file = paint_file

        # Decode region_mask RLE for each zone (same as /render)
        for z in zones:
            if z.get("region_mask") and isinstance(z["region_mask"], (dict, str)):
                try:
                    rle = z["region_mask"]
                    if isinstance(rle, str):
                        rle = json.loads(rle)
                    rw, rh = rle.get("width", 0), rle.get("height", 0)
                    runs = rle.get("runs", [])
                    flat = np.zeros(rw * rh, dtype=np.float32)
                    pos = 0
                    for run_val, run_len in runs:
                        flat[pos:pos + run_len] = float(run_val) / 255.0 if run_val else 0.0
                        pos += run_len
                    z["region_mask"] = flat.reshape((rh, rw))
                except Exception:
                    z.pop("region_mask", None)
            if z.get("source_layer_mask") and isinstance(z["source_layer_mask"], (dict, str)):
                try:
                    rle = z["source_layer_mask"]
                    if isinstance(rle, str):
                        rle = json.loads(rle)
                    rw, rh = rle.get("width", 0), rle.get("height", 0)
                    runs = rle.get("runs", [])
                    flat = np.zeros(rw * rh, dtype=np.float32)
                    pos = 0
                    for run_val, run_len in runs:
                        flat[pos:pos + run_len] = float(run_val) / 255.0 if run_val else 0.0
                        pos += run_len
                    z["source_layer_mask"] = flat.reshape((rh, rw))
                except Exception:
                    z.pop("source_layer_mask", None)

        # Decode pattern_strength_map RLE for each zone
        for z in zones:
            if z.get("pattern_strength_map") and isinstance(z["pattern_strength_map"], (dict, str)):
                try:
                    psm_rle = z["pattern_strength_map"]
                    if isinstance(psm_rle, str):
                        psm_rle = json.loads(psm_rle)
                    psm_w = psm_rle.get("width", 0)
                    psm_h = psm_rle.get("height", 0)
                    psm_runs = psm_rle.get("runs", [])
                    psm_flat = np.zeros(psm_w * psm_h, dtype=np.float32)
                    psm_pos = 0
                    for run_val, run_len in psm_runs:
                        psm_flat[psm_pos:psm_pos + run_len] = float(run_val) / 255.0
                        psm_pos += run_len
                    z["pattern_strength_map"] = psm_flat.reshape((psm_h, psm_w))
                except Exception:
                    z.pop("pattern_strength_map", None)

        # Build server_zones (simplified zone conversion)
        server_zones = []
        for z in zones:
            zone_obj = {
                "name": z.get("name", "Zone"),
                "color": z.get("color", "everything"),
                "intensity": z.get("intensity", "100"),
            }
            if z.get("base"):
                zone_obj["base"] = z["base"]
                zone_obj["pattern"] = z.get("pattern", "none")
                if z.get("scale"): zone_obj["scale"] = float(z["scale"])
                if z.get("rotation"): zone_obj["rotation"] = float(z["rotation"])
                if z.get("pattern_opacity"): zone_obj["pattern_opacity"] = float(z["pattern_opacity"])
                if z.get("pattern_stack"): zone_obj["pattern_stack"] = z["pattern_stack"]
            elif z.get("finish"):
                zone_obj["finish"] = z["finish"]
                if z.get("finish_colors"): zone_obj["finish_colors"] = z["finish_colors"]
                if z.get("pattern") and z["pattern"] != "none":
                    zone_obj["pattern"] = z["pattern"]
                if z.get("scale"): zone_obj["scale"] = float(z["scale"])
                if z.get("pattern_opacity"): zone_obj["pattern_opacity"] = float(z["pattern_opacity"])
            if z.get("region_mask") is not None and isinstance(z["region_mask"], np.ndarray):
                zone_obj["region_mask"] = z["region_mask"]
            if z.get("priority_override") is not None:
                zone_obj["priority_override"] = bool(z.get("priority_override"))
            if z.get("pattern_spec_mult") is not None:
                zone_obj["pattern_spec_mult"] = float(z["pattern_spec_mult"])
            if z.get("pattern_strength_map") is not None and isinstance(z["pattern_strength_map"], np.ndarray):
                zone_obj["pattern_strength_map"] = z["pattern_strength_map"]
            if z.get("custom_intensity"): zone_obj["custom_intensity"] = z["custom_intensity"]
            if z.get("wear_level"): zone_obj["wear_level"] = z["wear_level"]
            # v6 params
            if z.get("paint_color"): zone_obj["paint_color"] = z["paint_color"]
            if z.get("blend_base"):
                zone_obj["blend_base"] = z["blend_base"]
                zone_obj["blend_dir"] = z.get("blend_dir", "horizontal")
                zone_obj["blend_amount"] = float(z.get("blend_amount", 0.5))
            server_zones.append(zone_obj)

        import_spec_map = data.get("import_spec_map")
        if import_spec_map and not os.path.exists(import_spec_map):
            import_spec_map = None

        # Run the engine with export_layers=True
        import shokker_engine_v2 as _eng
        result = _eng.build_multi_zone(
            actual_paint_file, job_dir, server_zones,
            seed=seed, export_layers=True,
            import_spec_map=import_spec_map,
        )

        # Unpack result: (paint_rgb, combined_spec_u8, zone_masks, zone_layers)
        if len(result) == 4:
            paint_rgb, combined_spec_u8, zone_masks, zone_layers = result
        else:
            # Fallback if export_layers somehow returned 3-tuple
            paint_rgb, combined_spec_u8, zone_masks = result[:3]
            zone_layers = []

        # Build the ZIP
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Per-zone images
            layers_meta = []
            for layer in zone_layers:
                idx = layer["zone_index"] + 1
                zname = layer["zone_name"]
                safe_name = "".join(c if c.isalnum() or c in "_- " else "_" for c in zname).strip() or f"zone_{idx}"

                # Spec PNG
                spec_arr = layer["spec"]
                spec_img = PILImage.fromarray(spec_arr)
                spec_buf = io.BytesIO()
                spec_img.save(spec_buf, format="PNG")
                zf.writestr(f"per_zone_{idx}_spec.png", spec_buf.getvalue())

                # Paint PNG
                paint_arr = layer["paint"]
                paint_img = PILImage.fromarray(paint_arr)
                paint_buf = io.BytesIO()
                paint_img.save(paint_buf, format="PNG")
                zf.writestr(f"per_zone_{idx}_paint.png", paint_buf.getvalue())

                layers_meta.append({
                    "index": idx,
                    "name": zname,
                    "safe_name": safe_name,
                    "spec_file": f"per_zone_{idx}_spec.png",
                    "paint_file": f"per_zone_{idx}_paint.png",
                    "blend_mode": "normal",
                })

            # Combined images
            combined_paint_img = PILImage.fromarray(paint_rgb)
            cp_buf = io.BytesIO()
            combined_paint_img.save(cp_buf, format="PNG")
            zf.writestr("combined_paint.png", cp_buf.getvalue())

            combined_spec_img = PILImage.fromarray(combined_spec_u8)
            cs_buf = io.BytesIO()
            combined_spec_img.save(cs_buf, format="PNG")
            zf.writestr("combined_spec.png", cs_buf.getvalue())

            # Layers manifest
            manifest = {
                "version": 1,
                "layers": layers_meta,
                "combined_paint": "combined_paint.png",
                "combined_spec": "combined_spec.png",
                "resolution": [int(paint_rgb.shape[1]), int(paint_rgb.shape[0])],
                "seed": seed,
            }
            zf.writestr("layers.json", json.dumps(manifest, indent=2))

        zip_buf.seek(0)
        zip_bytes = zip_buf.getvalue()

        # Also save to disk for later retrieval
        zip_path = os.path.join(job_dir, f"{output_name}.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)

        logger.info(f"PSD layer export: {len(zone_layers)} zones, ZIP={len(zip_bytes)} bytes -> {zip_path}")

        return send_file(
            io.BytesIO(zip_bytes),
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{output_name}.zip",
        )

    except Exception as e:
        logger.error(f"PSD layer export failed: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/export-spec-channels', methods=['POST'])
def api_export_spec_channels():
    """
    Split a spec map into 4 separate channel PNGs + include the paint file as a 5th PNG.
    Supports both current render jobs and extracting from a .shokk file.
    Body (optional): { shokk_path, spec_path, output_dir, include_paint }
    Returns paths to: paint.png, spec_metallic.png, spec_roughness.png, spec_clearcoat.png, spec_mask.png
    """
    try:
        import numpy as np
        from PIL import Image as PILImage

        data = request.get_json() or {}
        shokk_path = data.get("shokk_path", "").strip()
        include_paint = data.get("include_paint", True)
        spec_path = data.get("spec_path")
        paint_path = None

        # === Source 1: Extract from a .shokk file ===
        if shokk_path and os.path.exists(shokk_path):
            mgr = _get_shokk_manager()
            if not mgr:
                return jsonify({"error": "SHOKK manager unavailable"}), 500
            import tempfile
            extract_dir = tempfile.mkdtemp(dir=OUTPUT_FOLDER, prefix="shokk_export_")
            result = mgr.open(shokk_path, extract_dir=extract_dir)
            spec_path = result.get("spec_path")
            paint_path = result.get("paint_path")
            logger.info(f"PS Export from SHOKK: {shokk_path}")

        # === Source 2: Check _latest_render/ persistent copy ===
        if not spec_path or not os.path.exists(spec_path):
            _latest_dir = os.path.join(OUTPUT_FOLDER, "_latest_render")
            if os.path.isdir(_latest_dir):
                for sname in ("spec.png", "spec.tga"):
                    p = os.path.join(_latest_dir, sname)
                    if os.path.exists(p):
                        spec_path = p
                        break
                if not paint_path:
                    p = os.path.join(_latest_dir, "paint.tga")
                    if os.path.exists(p):
                        paint_path = p

        # === Source 3: Find from latest render job ===
        if not spec_path or not os.path.exists(spec_path):
            import glob as _glob
            jobs = sorted(
                [d for d in os.listdir(OUTPUT_FOLDER) if d.startswith("job_")],
                key=lambda d: os.path.getmtime(os.path.join(OUTPUT_FOLDER, d)),
                reverse=True
            )
            for job in jobs:
                job_dir = os.path.join(OUTPUT_FOLDER, job)
                # Spec: try exact names, then glob car_spec_*.tga
                if not spec_path:
                    for spec_name in ("RENDER_spec.png", "spec.png", "PREVIEW_spec.png"):
                        p = os.path.join(job_dir, spec_name)
                        if os.path.exists(p):
                            spec_path = p
                            break
                    if not spec_path:
                        m = _glob.glob(os.path.join(job_dir, "car_spec_*.tga"))
                        if m: spec_path = m[0]
                # Paint: try exact names, then glob car_num_*.tga / car_*.tga
                if not paint_path:
                    for paint_name in ("PREVIEW_paint.png", "RENDER_paint.tga", "output.tga"):
                        p = os.path.join(job_dir, paint_name)
                        if os.path.exists(p):
                            paint_path = p
                            break
                    if not paint_path:
                        for pat in ("car_num_*.tga", "car_*.tga"):
                            m = _glob.glob(os.path.join(job_dir, pat))
                            m = [x for x in m if "spec" not in os.path.basename(x)]
                            if m:
                                paint_path = m[0]
                                break
                if spec_path:
                    break

        if not spec_path or not os.path.exists(spec_path):
            return jsonify({"error": "No spec map found. Render first, or select a SHOKK file with spec data."}), 404

        img = PILImage.open(spec_path).convert("RGBA")
        arr = np.array(img)

        # PS Export output: use user-specified dir, or a dedicated PS_Exports folder
        # NEVER save into a job_* folder (those get auto-purged)
        _user_out = data.get("output_dir", "").strip()
        logger.info(f"PS Export: output_dir from request = '{_user_out}' (len={len(_user_out) if _user_out else 0})")
        # Resolve relative paths to absolute — browser folder pickers return relative paths
        if _user_out and not os.path.isabs(_user_out):
            logger.warning(f"PS Export: relative path detected '{_user_out}', resolving to absolute")
            # Try resolving relative to the output folder first, then fall back to default
            _resolved = os.path.join(OUTPUT_FOLDER, "PS_Exports", _user_out)
            _user_out = _resolved
            logger.info(f"PS Export: resolved to '{_user_out}'")
        if _user_out:
            # Create directory if it doesn't exist — user explicitly chose this path
            try:
                os.makedirs(_user_out, exist_ok=True)
                out_dir = _user_out
                logger.info(f"PS Export: using user-specified output dir: {_user_out}")
            except Exception as _dir_err:
                logger.warning(f"PS Export: could not create output dir '{_user_out}': {_dir_err}, using default")
                out_dir = os.path.join(OUTPUT_FOLDER, "PS_Exports")
        else:
            # Dedicated PS_Exports folder that auto-purge NEVER touches
            out_dir = os.path.join(OUTPUT_FOLDER, "PS_Exports")

        os.makedirs(out_dir, exist_ok=True)

        paths = {}

        # === Save the FULL spec TGA as a backup (never lose your work) ===
        try:
            spec_backup = os.path.join(out_dir, "spec_full.png")
            img.save(spec_backup)
            paths["Spec (Full RGBA)"] = spec_backup
            logger.info(f"PS Export: spec_full.png backup saved")
        except Exception as sbe:
            logger.warning(f"PS Export: could not save spec backup: {sbe}")

        # === Export paint file as PNG ===
        if include_paint and paint_path and os.path.exists(paint_path):
            try:
                paint_img = PILImage.open(paint_path).convert("RGB")
                paint_out = os.path.join(out_dir, "paint_base.png")
                paint_img.save(paint_out)
                paths["Paint (Base)"] = paint_out
                logger.info(f"PS Export: paint_base.png saved")
            except Exception as pe:
                logger.warning(f"PS Export: could not export paint: {pe}")

        # === Export 4 spec channels ===
        channel_defs = [
            ("spec_metallic.png",   arr[:, :, 0], "R (Metallic)"),
            ("spec_roughness.png",  arr[:, :, 1], "G (Roughness)"),
            ("spec_clearcoat.png",  arr[:, :, 2], "B (Clearcoat)"),
            ("spec_mask.png",       arr[:, :, 3], "A (Spec Mask)"),
        ]

        for fname, channel, label in channel_defs:
            channel_img = PILImage.fromarray(channel, mode="L")
            out_path = os.path.join(out_dir, fname)
            channel_img.save(out_path)
            paths[label] = out_path

        return jsonify({"ok": True, "paths": paths, "spec_source": spec_path})
    except Exception as e:
        logger.error(f"/api/export-spec-channels error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/blank-canvas', methods=['GET'])
def api_blank_canvas():
    """
    Return a flat white TGA suitable as a blank starting canvas.
    Query params: width=2048, height=2048, color=ffffff
    """
    try:
        import numpy as np
        w = max(64, min(4096, int(request.args.get('width', 2048))))
        h = max(64, min(4096, int(request.args.get('height', 2048))))
        color_hex = request.args.get('color', 'ffffff').lstrip('#')
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)

        # Build white canvas TGA
        canvas = np.full((h, w, 3), [r, g, b], dtype=np.uint8)
        tga_path = os.path.join(OUTPUT_FOLDER, "blank_canvas.tga")
        engine.write_tga_24bit(tga_path, canvas)
        return send_file(tga_path, mimetype='image/tga',
                         download_name='blank_canvas.tga', as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================================================================
# MAIN
# ================================================================

def auto_cleanup_old_jobs(max_age_hours=24):
    """Remove job directories older than max_age_hours to prevent disk bloat."""
    if not os.path.exists(OUTPUT_FOLDER):
        return
    cutoff = time.time() - (max_age_hours * 3600)
    cleaned = 0
    for name in os.listdir(OUTPUT_FOLDER):
        job_path = os.path.join(OUTPUT_FOLDER, name)
        if os.path.isdir(job_path) and name.startswith("job_"):
            try:
                mtime = os.path.getmtime(job_path)
                if mtime < cutoff:
                    shutil.rmtree(job_path, ignore_errors=True)
                    cleaned += 1
            except Exception:
                pass
    if cleaned:
        logger.info(f"Auto-cleanup: removed {cleaned} job dirs older than {max_age_hours}h")


# ================================================================
# RENDER STATUS / PROGRESS ENDPOINTS
# ================================================================

@app.route('/api/render-status', methods=['GET'])
def api_render_status():
    """Return render progress in the format the JS poller expects.
    Polled by paint-booth-5-api-render.js during full renders."""
    pct = 0
    if _render_progress["active"] and _render_progress["total_zones"] > 0:
        pct = int((_render_progress["current_zone"] / _render_progress["total_zones"]) * 100)
    return jsonify({
        "active": _render_progress["active"],
        "total_zones": _render_progress["total_zones"],
        "current_zone": _render_progress["current_zone"],
        "zone_name": _render_progress["current_zone_name"],
        "phase": _render_progress["phase"],
        "percent": max(5, min(95, pct)) if _render_progress["active"] else 0,
        "elapsed_ms": int((time.time() - _render_progress["started_at"]) * 1000) if _render_progress["active"] else _render_progress["elapsed_ms"],
    })


# ================================================================
# RENDER STATISTICS ENDPOINT
# ================================================================

@app.route('/api/render-progress', methods=['GET'])
def api_render_progress():
    """Return current render progress for the UI progress bar.
    Polled by the client during full renders."""
    return jsonify(_render_progress)


@app.route('/api/render-stats', methods=['GET'])
def api_render_stats():
    """Return render statistics for the current session."""
    logger.debug("[render-stats] Stats requested")
    with _render_stats_lock:
        total = _render_stats["total_renders"]
        total_time = _render_stats["total_render_time"]
        avg_time = total_time / total if total > 0 else 0.0
        zone_avgs = {}
        for zname, times in _render_stats["zone_times"].items():
            zone_avgs[zname] = round(sum(times) / len(times), 2) if times else 0.0
        hits = _render_stats["cache_hits"]
        misses = _render_stats["cache_misses"]
        cache_total = hits + misses
        cache_rate = round(hits / cache_total * 100, 1) if cache_total > 0 else 0.0
        uptime = 0.0
        if _render_stats["session_start"]:
            uptime = round(time.time() - _render_stats["session_start"], 1)

    return jsonify({
        "total_renders": total,
        "average_render_time": round(avg_time, 2),
        "total_render_time": round(total_time, 2),
        "per_zone_avg_times": zone_avgs,
        "cache_hit_rate": cache_rate,
        "cache_hits": hits,
        "cache_misses": misses,
        "gpu": gpu_info(),
        "session_uptime_seconds": uptime,
    })


# ================================================================
# FINISH MIXER ENDPOINTS
# ================================================================

_CUSTOM_FINISHES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if not getattr(sys, 'frozen', False) else SERVER_DIR,
    'custom_finishes.json'
)


def _load_custom_finishes():
    """Load custom finishes from JSON file. Returns list of dicts."""
    if os.path.exists(_CUSTOM_FINISHES_PATH):
        try:
            with open(_CUSTOM_FINISHES_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_custom_finishes(finishes):
    """Save custom finishes list to JSON file."""
    with open(_CUSTOM_FINISHES_PATH, 'w', encoding='utf-8') as f:
        json.dump(finishes, f, indent=2, ensure_ascii=False)


@app.route('/api/mix-preview', methods=['POST'])
def api_mix_preview():
    """Generate a 256x256 preview of blended finishes.

    POST JSON: { "finish_ids": [...], "weights": [...], "seed": 51 }
    Returns: { "image": "data:image/png;base64,..." }
    """
    logger.info("[mix-preview] Mix preview requested")
    try:
        data = request.get_json(force=True)
        finish_ids = data.get('finish_ids', [])
        weights = data.get('weights', [])
        seed = int(data.get('seed', 51))

        if len(finish_ids) < 2 or len(finish_ids) > 3:
            return jsonify({"error": "Need 2-3 finish_ids"}), 400
        if len(finish_ids) != len(weights):
            return jsonify({"error": "finish_ids and weights must match in length"}), 400

        from engine.compose import mix_finishes
        import numpy as np
        from PIL import Image

        shape = (256, 256)
        mask = np.ones(shape, dtype=np.float32)
        sm = 1.0

        spec = mix_finishes(shape, mask, seed, sm, finish_ids, weights,
                            monolithic_registry=engine.MONOLITHIC_REGISTRY)

        # Convert spec to a visible preview image:
        # Map M channel to blue, R to green, CC to red for visual distinction
        preview = np.zeros((256, 256, 3), dtype=np.uint8)
        preview[:, :, 0] = spec[:, :, 2]  # CC -> Red
        preview[:, :, 1] = spec[:, :, 1]  # R -> Green
        preview[:, :, 2] = spec[:, :, 0]  # M -> Blue

        img = Image.fromarray(preview, 'RGB')
        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')

        return jsonify({"image": f"data:image/png;base64,{b64}"})
    except Exception as e:
        logger.error(f"[mix-preview] Error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/save-custom-finish', methods=['POST'])
def api_save_custom_finish():
    """Save a custom mixed finish recipe.

    POST JSON: { "name": "My Mix", "finish_ids": [...], "weights": [...] }
    Returns: { "id": "custom_001", "name": "My Mix", ... }
    """
    logger.info("[save-custom-finish] Save custom finish requested")
    try:
        data = request.get_json(force=True)
        name = data.get('name', '').strip()
        finish_ids = data.get('finish_ids', [])
        weights = data.get('weights', [])

        if not name:
            return jsonify({"error": "Name is required"}), 400
        if len(finish_ids) < 2 or len(finish_ids) > 3:
            return jsonify({"error": "Need 2-3 finish_ids"}), 400
        if len(finish_ids) != len(weights):
            return jsonify({"error": "finish_ids and weights must match in length"}), 400

        # Normalize weights
        w_sum = sum(weights)
        if w_sum > 0:
            weights = [round(w / w_sum, 4) for w in weights]
        else:
            weights = [round(1.0 / len(weights), 4)] * len(weights)

        finishes = _load_custom_finishes()

        # Generate next ID
        existing_nums = []
        for cf in finishes:
            cid = cf.get('id', '')
            if cid.startswith('custom_'):
                try:
                    existing_nums.append(int(cid.split('_')[1]))
                except (IndexError, ValueError):
                    pass
        next_num = max(existing_nums, default=0) + 1
        new_id = f"custom_{next_num:03d}"

        mix_mode = data.get('mix_mode', 'both')  # 'both', 'color', 'spec'
        entry = {
            "id": new_id,
            "name": name,
            "finish_ids": finish_ids,
            "weights": weights,
            "mix_mode": mix_mode,
            "created": datetime.now().isoformat(),
        }
        finishes.append(entry)
        _save_custom_finishes(finishes)

        logger.info(f"[mixer] Saved custom finish: {new_id} = {name}")
        return jsonify(entry)
    except Exception as e:
        logger.error(f"[save-custom-finish] Error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/custom-finishes', methods=['GET'])
def api_custom_finishes():
    """Return the list of saved custom mixed finishes."""
    try:
        finishes = _load_custom_finishes()
        return jsonify(finishes)
    except Exception as e:
        logger.error(f"[custom-finishes] Error: {e}")
        return jsonify([])


@app.route('/api/health', methods=['GET'])
def api_health():
    """Server health check endpoint."""
    try:
        import time as _t
        uptime = _t.time() - getattr(app, '_start_time', _t.time())
        base_count = len(getattr(engine, 'BASE_REGISTRY', {})) if engine else 0
        pattern_count = len(getattr(engine, 'PATTERN_REGISTRY', {})) if engine else 0
        mono_count = len(getattr(engine, 'MONOLITHIC_REGISTRY', {})) if engine else 0
        return jsonify({"status": "ok", "uptime_seconds": round(uptime, 1),
                        "registries": {"bases": base_count, "patterns": pattern_count, "monolithics": mono_count},
                        "version": "6.2.0"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/delete-custom-finish', methods=['POST'])
def api_delete_custom_finish():
    """Delete a saved custom finish by ID."""
    try:
        data = request.get_json(force=True)
        delete_id = data.get('id', '').strip()
        if not delete_id:
            return jsonify({"error": "id is required"}), 400
        finishes = _load_custom_finishes()
        original_count = len(finishes)
        finishes = [f for f in finishes if f.get('id') != delete_id]
        if len(finishes) == original_count:
            return jsonify({"error": f"Custom finish '{delete_id}' not found"}), 404
        _save_custom_finishes(finishes)
        return jsonify({"success": True, "deleted": delete_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/mix-paint-preview', methods=['POST'])
def api_mix_paint_preview():
    """Generate a SPLIT preview: paint (left) + spec (right), like the main render output.
    Detects base vs monolithic per component. Uses actual swatch colors."""
    try:
        data = request.get_json(force=True)
        finish_ids = data.get('finish_ids', [])
        weights = data.get('weights', [])
        seed = int(data.get('seed', 51))
        color_hex = str(data.get('color', '888888')).replace('#', '').strip()
        # Validate hex color — must be 6 hex chars
        import re
        if not re.match(r'^[0-9a-fA-F]{6}$', color_hex):
            logger.warning(f"[mix-preview] Invalid color_hex '{color_hex}', defaulting to 888888")
            color_hex = '888888'
        if len(finish_ids) < 2 or len(finish_ids) != len(weights):
            return jsonify({"error": "Need 2-3 matching finish_ids and weights"}), 400

        import numpy as np
        from PIL import Image

        size = 128
        w_sum = sum(weights)
        if w_sum > 0:
            weights = [w / w_sum for w in weights]
        else:
            weights = [1.0 / len(weights)] * len(weights)

        # Determine type per component: base or monolithic
        _base_reg = getattr(engine, 'BASE_REGISTRY', {})
        _mono_reg = getattr(engine, 'MONOLITHIC_REGISTRY', {})

        # --- PAINT SIDE: blend swatch images ---
        paint_blend = np.zeros((size, size, 3), dtype=np.float32)
        for fid, wt in zip(finish_ids, weights):
            swatch_bytes = None
            # Try monolithic first (these have colors), then base
            if fid in _mono_reg:
                try:
                    swatch_bytes = _render_swatch_bytes('monolithic', fid, color_hex, size, seed)
                except Exception:
                    pass
            if not swatch_bytes and fid in _base_reg:
                try:
                    swatch_bytes = _render_swatch_bytes('base', fid, color_hex, size, seed)
                except Exception:
                    pass
            if not swatch_bytes:
                # Last resort: try both types
                for stype in ['monolithic', 'base']:
                    try:
                        swatch_bytes = _render_swatch_bytes(stype, fid, color_hex, size, seed)
                        if swatch_bytes:
                            break
                    except Exception:
                        pass
            if swatch_bytes:
                try:
                    swatch_img = Image.open(io.BytesIO(swatch_bytes)).convert('RGB')
                    swatch_arr = np.array(swatch_img).astype(np.float32) / 255.0
                    paint_blend += swatch_arr * wt
                except Exception:
                    paint_blend += 0.5 * wt
            else:
                paint_blend += 0.5 * wt

        paint_u8 = np.clip(paint_blend * 255, 0, 255).astype(np.uint8)

        # --- SPEC SIDE: blend spec values and visualize ---
        from engine.compose import mix_finishes
        spec_shape = (size, size)
        mask = np.ones(spec_shape, dtype=np.float32)
        try:
            spec = mix_finishes(spec_shape, mask, seed, 1.0, finish_ids, weights,
                                monolithic_registry=_mono_reg)
            # Visualize spec: R=Metallic(red), G=Roughness(green), B=Clearcoat(blue)
            spec_vis = np.zeros((size, size, 3), dtype=np.uint8)
            spec_vis[:, :, 0] = spec[:, :, 0]  # M → Red
            spec_vis[:, :, 1] = spec[:, :, 1]  # R → Green
            spec_vis[:, :, 2] = spec[:, :, 2]  # CC → Blue
            spec_info = {"M_avg": round(float(np.mean(spec[:,:,0])), 1),
                         "R_avg": round(float(np.mean(spec[:,:,1])), 1),
                         "CC_avg": round(float(np.mean(spec[:,:,2])), 1)}
        except Exception as e:
            logger.warning(f"[mix-preview] spec blend failed: {e}")
            spec_vis = np.full((size, size, 3), 40, dtype=np.uint8)
            spec_info = {"M_avg": 0, "R_avg": 0, "CC_avg": 0}

        # --- COMBINE: paint (left) | spec (right) side by side ---
        combined = np.zeros((size, size * 2 + 4, 3), dtype=np.uint8)
        combined[:, :size, :] = paint_u8
        combined[:, size:size+4, :] = 60  # divider line
        combined[:, size+4:, :] = spec_vis

        img = Image.fromarray(combined, 'RGB')
        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')

        return jsonify({"image": f"data:image/png;base64,{b64}", "spec_summary": spec_info})
    except Exception as e:
        logger.error(f"[mix-paint-preview] Error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


# ================================================================
# HARDENED UTILITY ENDPOINTS — added in v6.2 hardening pass.
# Read-only diagnostics + safe maintenance. Prefixed /api/ so they
# do not collide with any UI / static routes.
# ================================================================

@lru_cache(maxsize=4096)
def _memo_finish_meta(finish_id):
    """Memoised lookup: returns (kind, name, category) for a finish ID.
    Cleared by /api/reload-engine to pick up hot-added finishes."""
    if not isinstance(finish_id, str) or not finish_id:
        return None
    base_reg = getattr(engine, 'BASE_REGISTRY', {}) or {}
    pat_reg  = getattr(engine, 'PATTERN_REGISTRY', {}) or {}
    mono_reg = getattr(engine, 'MONOLITHIC_REGISTRY', {}) or {}
    fus_reg  = getattr(engine, 'FUSION_REGISTRY', {}) or {}
    if finish_id in base_reg:
        return ("base", _id_to_display_name(finish_id), "base")
    if finish_id in pat_reg:
        return ("pattern", _id_to_display_name(finish_id), "pattern")
    if finish_id in mono_reg:
        return ("monolithic", _id_to_display_name(finish_id), "monolithic")
    if finish_id in fus_reg:
        return ("fusion", _id_to_display_name(finish_id), "fusion")
    return None


def _normalize_spec_result_to_rgba(spec_result, shape, default_m=5, default_r=100, default_cc=16):
    """Normalize spec outputs from all engine contracts to HxWx4 float32.

    Monolithic/spec helpers are not perfectly consistent: some return RGBA,
    some return RGB, and several pattern-driven finishes return an (M, R, CC)
    tuple. The render and swatch routes must not treat tuple specs as failures.
    """
    import numpy as _np

    h, w = shape[:2]

    def _plane(value, fallback):
        if value is None:
            return _np.full((h, w), float(fallback), dtype=_np.float32)
        arr = _np.asarray(value, dtype=_np.float32)
        if arr.ndim == 0:
            return _np.full((h, w), float(arr), dtype=_np.float32)
        if arr.shape != (h, w):
            try:
                arr = _np.resize(arr, (h, w)).astype(_np.float32)
            except Exception:
                return _np.full((h, w), float(fallback), dtype=_np.float32)
        return arr

    if isinstance(spec_result, dict):
        for key in ("spec", "rgba", "result"):
            if key in spec_result:
                return _normalize_spec_result_to_rgba(
                    spec_result[key], shape, default_m, default_r, default_cc
                )
        if any(k in spec_result for k in ("M", "R", "CC")):
            m = _plane(spec_result.get("M"), default_m)
            r = _plane(spec_result.get("R"), default_r)
            cc = _plane(spec_result.get("CC"), default_cc)
            out = _np.empty((h, w, 4), dtype=_np.float32)
            out[:, :, 0] = _np.clip(m, 0, 255)
            out[:, :, 1] = _np.clip(r, 0, 255)
            out[:, :, 2] = _np.clip(cc, 0, 255)
            out[:, :, 3] = 255
            return out
        return None

    if isinstance(spec_result, (tuple, list)) and len(spec_result) >= 2:
        m = _plane(spec_result[0], default_m)
        r = _plane(spec_result[1], default_r)
        cc = _plane(spec_result[2] if len(spec_result) >= 3 else None, default_cc)
        out = _np.empty((h, w, 4), dtype=_np.float32)
        out[:, :, 0] = _np.clip(m, 0, 255)
        out[:, :, 1] = _np.clip(r, 0, 255)
        out[:, :, 2] = _np.clip(cc, 0, 255)
        out[:, :, 3] = 255
        return out

    if spec_result is None:
        return None

    arr = _np.asarray(spec_result, dtype=_np.float32)
    if arr.ndim == 3 and arr.shape[0] in (3, 4) and arr.shape[1:3] == (h, w):
        arr = _np.moveaxis(arr, 0, -1)
    if arr.ndim == 2:
        out = _np.empty((h, w, 4), dtype=_np.float32)
        out[:, :, 0] = _np.clip(_plane(arr, default_m), 0, 255)
        out[:, :, 1] = default_r
        out[:, :, 2] = default_cc
        out[:, :, 3] = 255
        return out
    if arr.ndim == 3 and arr.shape[:2] == (h, w):
        out = _np.empty((h, w, 4), dtype=_np.float32)
        chans = arr.shape[2]
        out[:, :, 0] = _np.clip(arr[:, :, 0], 0, 255)
        out[:, :, 1] = _np.clip(arr[:, :, 1] if chans > 1 else default_r, 0, 255)
        out[:, :, 2] = _np.clip(arr[:, :, 2] if chans > 2 else default_cc, 0, 255)
        out[:, :, 3] = _np.clip(arr[:, :, 3] if chans > 3 else 255, 0, 255)
        return out
    return None


@app.route('/api/finish-by-id/<finish_id>', methods=['GET'])
def api_finish_by_id(finish_id):
    """Return single-finish metadata: id, kind, display name, category, swatch URL."""
    rid = getattr(g, '_rid', '-')
    try:
        meta = _memo_finish_meta(finish_id)
        if not meta:
            return jsonify({"error": "finish_not_found", "finish_id": finish_id, "rid": rid}), 404
        kind, name, category = meta
        return jsonify({
            "id": finish_id,
            "kind": kind,
            "name": name,
            "category": category,
            "swatch_url": f"/api/swatch/{kind}/{finish_id}",
            "rid": rid,
        })
    except Exception as e:
        logger.error(f"[finish-by-id rid={rid}] {e}")
        return jsonify({"error": str(e), "rid": rid}), 500


@app.route('/api/validate-paint-file', methods=['POST'])
def api_validate_paint_file():
    """Validate a paint file path: existence, readability, dimensions.
    Body: {"path": "E:/.../car_num_23371.tga", "expect_size": [2048, 2048]}"""
    rid = getattr(g, '_rid', '-')
    try:
        data = request.get_json(silent=True) or {}
        raw_path = data.get('path', '')
        expect = data.get('expect_size')  # optional [W, H]
        ok, normed, err = _validate_path_safe(raw_path)
        if not ok:
            return jsonify({"valid": False, "reason": err, "rid": rid}), 400
        if not os.path.exists(normed):
            return jsonify({"valid": False, "reason": "file_not_found",
                            "path": normed, "rid": rid}), 404
        if not os.path.isfile(normed):
            return jsonify({"valid": False, "reason": "not_a_regular_file",
                            "path": normed, "rid": rid}), 400
        try:
            size_bytes = os.path.getsize(normed)
        except OSError as e:
            return jsonify({"valid": False, "reason": f"stat_failed: {e}",
                            "rid": rid}), 500
        readable = os.access(normed, os.R_OK)
        # Try to open with PIL to extract dimensions (cheap)
        dims = None
        try:
            from PIL import Image as _PIL
            with _PIL.open(normed) as img:
                dims = [img.width, img.height]
        except Exception as e:
            return jsonify({"valid": False, "reason": f"unreadable_image: {e}",
                            "path": normed, "rid": rid}), 400
        ok_dims = True
        if expect and isinstance(expect, list) and len(expect) == 2:
            ok_dims = (dims and dims[0] == int(expect[0]) and dims[1] == int(expect[1]))
        return jsonify({
            "valid": readable and ok_dims,
            "path": normed,
            "size_bytes": size_bytes,
            "dimensions": dims,
            "readable": readable,
            "matches_expected_size": ok_dims,
            "rid": rid,
        })
    except Exception as e:
        logger.error(f"[validate-paint-file rid={rid}] {e}")
        return jsonify({"valid": False, "reason": str(e), "rid": rid}), 500


@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Comprehensive server stats: uptime, render count, cache hits, memory."""
    rid = getattr(g, '_rid', '-')
    try:
        # Memory snapshot — best-effort, falls back to gc counts.
        mem_mb = None
        try:
            import resource as _res  # POSIX only
            mem_mb = round(_res.getrusage(_res.RUSAGE_SELF).ru_maxrss / 1024, 1)
        except Exception:
            try:
                import psutil as _ps  # type: ignore
                mem_mb = round(_ps.Process(os.getpid()).memory_info().rss / (1024 * 1024), 1)
            except Exception:
                pass

        with _render_stats_lock:
            renders = dict(_render_stats)
        with _request_counter_lock:
            req_count = _request_counter
        with _recent_renders_lock:
            recent_count = len(_recent_renders)
        with _recent_errors_lock:
            err_count = len(_recent_errors)

        return jsonify({
            "version": SPB_VERSION,
            "engine": SPB_ENGINE_VERSION,
            "build": SPB_BUILD_ID,
            "uptime_s": int(time.time() - _server_start_time),
            "request_count": req_count,
            "total_renders": renders.get("total_renders", 0),
            "total_render_time_s": round(renders.get("total_render_time", 0.0), 2),
            "cache_hits": renders.get("cache_hits", 0),
            "cache_misses": renders.get("cache_misses", 0),
            "recent_renders_logged": recent_count,
            "recent_errors_logged": err_count,
            "memory_rss_mb": mem_mb,
            "gc_objects": len(gc.get_objects()),
            "registries": {
                "bases": len(getattr(engine, 'BASE_REGISTRY', {})),
                "patterns": len(getattr(engine, 'PATTERN_REGISTRY', {})),
                "monolithics": len(getattr(engine, 'MONOLITHIC_REGISTRY', {})),
                "fusions": len(getattr(engine, 'FUSION_REGISTRY', {})),
            },
            "gpu": gpu_info(),
            "rid": rid,
        })
    except Exception as e:
        logger.error(f"[stats rid={rid}] {e}")
        return jsonify({"error": str(e), "rid": rid}), 500


@app.route('/api/reload-engine', methods=['POST'])
def api_reload_engine():
    """Soft-reload the engine module — clears finish-meta cache + zone cache.
    Use during dev when registries change at runtime. Does NOT re-import .py files."""
    rid = getattr(g, '_rid', '-')
    try:
        global _FINISH_DATA_CACHE
        _FINISH_DATA_CACHE = None
        _memo_finish_meta.cache_clear()
        cleared_zones = 0
        try:
            import shokker_engine_v2 as _eng
            if hasattr(_eng.build_multi_zone, '_zone_cache'):
                cleared_zones = len(_eng.build_multi_zone._zone_cache)
                _eng.build_multi_zone._zone_cache.clear()
        except Exception:
            pass
        with _SWATCH_CACHE_LOCK:
            sw_count = len(_SWATCH_CACHE)
            _SWATCH_CACHE.clear()
        logger.info(f"[reload-engine rid={rid}] cleared {sw_count} swatches, {cleared_zones} zone cache entries")
        return jsonify({
            "ok": True,
            "cleared": {"swatches": sw_count, "zones": cleared_zones,
                        "finish_meta": True, "finish_data_cache": True},
            "rid": rid,
        })
    except Exception as e:
        logger.error(f"[reload-engine rid={rid}] {e}")
        return jsonify({"error": str(e), "rid": rid}), 500


@app.route('/api/recent-renders', methods=['GET'])
def api_recent_renders():
    """Return the last N renders (preview + full) with timestamps + elapsed.
    Optional ?limit=N to cap response size (default 25, max 64)."""
    rid = getattr(g, '_rid', '-')
    limit = max(1, min(64, _safe_int(request.args.get('limit'), 25)))
    with _recent_renders_lock:
        items = list(_recent_renders)[:limit]
    return jsonify({"count": len(items), "items": items, "rid": rid})


@app.route('/api/clear-cache/<cache_name>', methods=['POST'])
def api_clear_cache_named(cache_name):
    """Granular cache clearing.  cache_name in:
       swatch | finish_data | zone | spec_delta | psd | finish_meta | all"""
    rid = getattr(g, '_rid', '-')
    cleared = {}
    try:
        global _FINISH_DATA_CACHE, _prev_spec_cache
        name = (cache_name or "").lower().strip()
        if name in ("swatch", "swatches", "all"):
            with _SWATCH_CACHE_LOCK:
                cleared["swatch"] = len(_SWATCH_CACHE)
                _SWATCH_CACHE.clear()
        if name in ("finish_data", "finish-data", "all"):
            cleared["finish_data"] = 1 if _FINISH_DATA_CACHE else 0
            _FINISH_DATA_CACHE = None
        if name in ("zone", "zones", "all"):
            try:
                import shokker_engine_v2 as _eng
                if hasattr(_eng.build_multi_zone, '_zone_cache'):
                    cleared["zone"] = len(_eng.build_multi_zone._zone_cache)
                    _eng.build_multi_zone._zone_cache.clear()
            except Exception:
                cleared["zone"] = 0
        if name in ("spec_delta", "spec-delta", "all"):
            cleared["spec_delta"] = 1 if _prev_spec_cache is not None else 0
            _prev_spec_cache = None
        if name in ("psd", "all"):
            cleared["psd"] = len(_psd_cache)
            _psd_cache.clear()
        if name in ("finish_meta", "finish-meta", "all"):
            _memo_finish_meta.cache_clear()
            cleared["finish_meta"] = 1
        if not cleared:
            return jsonify({"error": f"Unknown cache: {cache_name}",
                            "valid": ["swatch", "finish_data", "zone",
                                      "spec_delta", "psd", "finish_meta", "all"],
                            "rid": rid}), 400
        return jsonify({"ok": True, "cleared": cleared, "rid": rid})
    except Exception as e:
        logger.error(f"[clear-cache rid={rid}] {e}")
        return jsonify({"error": str(e), "rid": rid}), 500


@app.route('/api/zone-coverage-estimate', methods=['POST'])
def api_zone_coverage_estimate():
    """Estimate pixel coverage % for a zone config against a paint file.
    Body: {"paint_file": "...", "zones": [...] }
    Returns: {"coverage": [{"zone": "name", "pct": 12.5}, ...], "total_zones": N}"""
    rid = getattr(g, '_rid', '-')
    try:
        data = request.get_json(silent=True) or {}
        paint_file = data.get('paint_file', '')
        zones = data.get('zones', [])
        if not zones:
            return jsonify({"error": "no_zones", "rid": rid}), 400
        if len(zones) > MAX_ZONES_PER_REQUEST:
            return jsonify({"error": "too_many_zones",
                            "limit": MAX_ZONES_PER_REQUEST,
                            "got": len(zones), "rid": rid}), 400
        ok, normed, err = _validate_path_safe(paint_file)
        if not ok or not os.path.exists(normed):
            return jsonify({"error": err or "paint_file_missing", "rid": rid}), 404
        try:
            from PIL import Image as _PIL
            import numpy as _np
            with _PIL.open(normed) as img:
                arr = _np.array(img.convert('RGBA'))
        except Exception as e:
            return jsonify({"error": f"image_open_failed: {e}", "rid": rid}), 400
        total_px = arr.shape[0] * arr.shape[1]
        # Quick estimate by colour-channel matching for "blue|red|green|black|white" zones.
        # Region masks are ignored (they need engine rasterisation, too heavy).
        result = []
        for z in zones[:MAX_ZONES_PER_REQUEST]:
            color = (z.get('color') or '').lower()
            name = z.get('name') or color or 'unnamed'
            pct = 0.0
            if color == 'everything':
                pct = 100.0
            else:
                # Threshold-based rough match.  Not exact — that's the point.
                r, gch, b = arr[..., 0], arr[..., 1], arr[..., 2]
                if color == 'red':
                    m = (r > 150) & (gch < 100) & (b < 100)
                elif color == 'green':
                    m = (gch > 150) & (r < 100) & (b < 100)
                elif color == 'blue':
                    m = (b > 150) & (r < 100) & (gch < 100)
                elif color == 'black':
                    m = (r < 32) & (gch < 32) & (b < 32)
                elif color == 'white':
                    m = (r > 220) & (gch > 220) & (b > 220)
                elif color == 'yellow':
                    m = (r > 200) & (gch > 200) & (b < 100)
                else:
                    m = None
                if m is not None:
                    pct = round(100.0 * float(m.sum()) / total_px, 2)
            result.append({"zone": name, "color": color, "pct": pct})
        return jsonify({
            "coverage": result,
            "total_zones": len(zones),
            "image_dims": [int(arr.shape[1]), int(arr.shape[0])],
            "rid": rid,
        })
    except Exception as e:
        logger.error(f"[zone-coverage rid={rid}] {e}")
        return jsonify({"error": str(e), "rid": rid}), 500


@app.route('/api/diagnostics', methods=['GET'])
def api_diagnostics():
    """Big diagnostics payload — Python version, packages, GPU, registries,
    recent error log, available endpoints. Used for bug reports."""
    rid = getattr(g, '_rid', '-')
    pkg_versions = {}
    for pkg in ("numpy", "Pillow", "flask", "flask_cors", "psd_tools"):
        try:
            mod = __import__(pkg if pkg != "Pillow" else "PIL")
            pkg_versions[pkg] = getattr(mod, "__version__", "unknown")
        except Exception:
            pkg_versions[pkg] = None
    endpoints = []
    try:
        for rule in app.url_map.iter_rules():
            endpoints.append({
                "rule": str(rule),
                "methods": sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS")),
            })
    except Exception:
        pass
    with _recent_errors_lock:
        recent_errs = list(_recent_errors)
    return jsonify({
        "version": SPB_VERSION,
        "engine_version": SPB_ENGINE_VERSION,
        "build_id": SPB_BUILD_ID,
        "python": {
            "version": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "packages": pkg_versions,
        "gpu": gpu_info(),
        "registries": {
            "bases": len(getattr(engine, 'BASE_REGISTRY', {})),
            "patterns": len(getattr(engine, 'PATTERN_REGISTRY', {})),
            "monolithics": len(getattr(engine, 'MONOLITHIC_REGISTRY', {})),
            "fusions": len(getattr(engine, 'FUSION_REGISTRY', {})),
        },
        "endpoints_count": len(endpoints),
        "endpoints": endpoints,
        "recent_errors": recent_errs,
        "uptime_s": int(time.time() - _server_start_time),
        "rid": rid,
    })


@app.route('/api/server-info', methods=['GET'])
def api_server_info():
    """Lightweight server info — version, port, paths. Cheaper than /status."""
    rid = getattr(g, '_rid', '-')
    return jsonify({
        "version": SPB_VERSION,
        "engine": SPB_ENGINE_VERSION,
        "build": SPB_BUILD_ID,
        "pid": os.getpid(),
        "port": int(os.environ.get('SHOKKER_PORT', 59876)),
        "server_dir": SERVER_DIR,
        "thumbnail_dir": THUMBNAIL_DIR,
        "uptime_s": int(time.time() - _server_start_time),
        "rid": rid,
    })


@app.route('/api/ping', methods=['GET'])
def api_ping():
    """Tiny health probe — returns plaintext 'pong' for fastest possible check."""
    from flask import Response as _Resp
    return _Resp("pong", mimetype='text/plain')


@app.route('/api/echo', methods=['POST'])
def api_echo():
    """Debug echo — returns the JSON body and request headers verbatim.
    Useful for client-side debugging of camelCase→snake_case conversion."""
    rid = getattr(g, '_rid', '-')
    try:
        body = request.get_json(silent=True) or {}
    except Exception:
        body = {}
    return jsonify({
        "body": body,
        "headers": dict(request.headers),
        "method": request.method,
        "remote_addr": request.remote_addr,
        "rid": rid,
    })


# ----------------------------------------------------------------
# BACKGROUND CLEANUP THREAD — runs every hour, deletes stale tmp
# files and old job directories. Daemon thread so it dies with the
# server process. Logs counts to the standard logger.
# ----------------------------------------------------------------
def _spb_background_janitor():
    """Periodic cleanup of tmp files + old job dirs + memory stats log."""
    interval_s = 60 * 60  # 1 hour
    log = logging.getLogger('shokker.janitor')
    while True:
        try:
            time.sleep(interval_s)
        except Exception:
            return
        # 1) Old job dirs (>24h)
        try:
            now = time.time()
            cleaned_jobs = 0
            if os.path.isdir(OUTPUT_FOLDER):
                for entry in os.listdir(OUTPUT_FOLDER):
                    if not entry.startswith("job_"):
                        continue
                    p = os.path.join(OUTPUT_FOLDER, entry)
                    try:
                        if os.path.isdir(p) and (now - os.path.getmtime(p)) / 3600 > 24:
                            shutil.rmtree(p, ignore_errors=True)
                            cleaned_jobs += 1
                    except OSError:
                        pass
            if cleaned_jobs:
                log.info(f"janitor: removed {cleaned_jobs} stale job dirs")
        except Exception as e:
            log.warning(f"janitor job-cleanup failed: {e}")
        # 2) Tmp files in OS temp matching shokker_* prefixes (>1 day old)
        try:
            import tempfile as _tf
            tmp_root = _tf.gettempdir()
            cleaned_tmp = 0
            now = time.time()
            for entry in os.listdir(tmp_root):
                if not entry.startswith(("shokker_preview_", "shokker_render_", "shokker_decal_")):
                    continue
                p = os.path.join(tmp_root, entry)
                try:
                    if (now - os.path.getmtime(p)) > 86400:
                        if os.path.isdir(p):
                            shutil.rmtree(p, ignore_errors=True)
                        else:
                            os.remove(p)
                        cleaned_tmp += 1
                except OSError:
                    pass
            if cleaned_tmp:
                log.info(f"janitor: removed {cleaned_tmp} stale tmp files")
        except Exception as e:
            log.warning(f"janitor tmp-cleanup failed: {e}")
        # 3) Periodic memory stats — dropped at INFO so they show up in log review.
        try:
            obj_count = len(gc.get_objects())
            with _render_stats_lock:
                renders = _render_stats.get("total_renders", 0)
            log.info(f"janitor stats: gc_objects={obj_count} total_renders={renders}")
            # Auto-restart hint after 1000 renders (memory drift mitigation)
            if renders > 0 and renders % 1000 == 0:
                log.warning(f"janitor: {renders} renders served — consider restarting "
                            f"the server to reclaim memory.")
        except Exception:
            pass

# Kick off the janitor — daemon so it never blocks shutdown.
threading.Thread(target=_spb_background_janitor, daemon=True, name='spb-janitor').start()


if __name__ == '__main__':
    import socket

    # Auto-cleanup old renders on startup
    auto_cleanup_old_jobs(max_age_hours=24)

    cfg = load_config()
    bases = len(engine.BASE_REGISTRY)
    patterns = len(engine.PATTERN_REGISTRY)
    monos = len(engine.MONOLITHIC_REGISTRY)
    combos = bases * patterns
    has_expansion = bases > 60  # Original engine has ~55 bases

    # BUILD 27: HARDCODED PORT 59876 - eliminates any port-squatting possibility
    # No env var, no scanning, no SO_REUSEADDR ambiguity
    port = 59876

    # Write chosen port for external discovery
    port_file = os.path.join(SERVER_DIR, '.server_port')
    with open(port_file, 'w') as f:
        f.write(str(port))

    # ----------------------------------------------------------------
    # Pre-flight: warn about missing optional dependencies BEFORE we
    # bind the socket — easier for users to spot in the console log.
    # ----------------------------------------------------------------
    _missing_deps = []
    for _dep, _hint in (("psd_tools", "PSD import will be disabled"),
                        ("psutil",    "memory stats fall back to gc")):
        try:
            __import__(_dep)
        except ImportError:
            _missing_deps.append((_dep, _hint))

    # GPU + diagnostics one-liner (caches the call so banner == /api/stats)
    _gpu = gpu_info()
    _gpu_label = f"{_gpu.get('icon', '?')} {_gpu.get('name', 'CPU')}"
    if _gpu.get('vram_mb'):
        _gpu_label += f" ({_gpu.get('vram_mb')} MB)"

    print("=" * 60)
    print(f"  SHOKKER PAINT BOOTH — {SPB_VERSION}")
    print(f"  Engine: {SPB_ENGINE_VERSION}  |  Build: {SPB_BUILD_ID}")
    print(f"  GPU: {_gpu_label}  |  Accelerated: {_gpu.get('accelerated', False)}")
    if has_expansion:
        print(f"  24K Arsenal LOADED - {bases} bases / {patterns} patterns / {monos} monolithics")
    else:
        print(f"  WARNING: 24K Arsenal NOT loaded - only {bases} bases / {patterns} patterns")
    print(f"  {combos}+ finish combinations ready")
    print(f"  iRacing ID: {cfg.get('iracing_id', 'not set')}")
    if cfg.get("live_link_enabled") and cfg.get("active_car"):
        car_path = cfg.get("car_paths", {}).get(cfg["active_car"], "???")
        print(f"  Live Link: {cfg['active_car']} => {car_path}")
    else:
        print("  Live Link: not configured")
    if _missing_deps:
        print("  Optional deps missing:")
        for _dep, _hint in _missing_deps:
            print(f"    - {_dep}: {_hint}")
    print(f"  Listening on http://localhost:{port}")
    print(f"  Open this URL in your browser:  http://localhost:{port}/")
    print("=" * 60)
    # Pre-warm the finish-data cache so the very first /api/finish-data
    # request doesn't pay the build cost. Wrapped to stay non-fatal.
    try:
        _FINISH_DATA_CACHE = _build_finish_data_payload()
        logger.info(f"Pre-warmed finish-data cache: {_FINISH_DATA_CACHE['counts']['total']} entries")
    except Exception as _e:
        logger.warning(f"Pre-warm failed (non-fatal): {_e}")


    # Threaded WSGI server (handles concurrent requests)
    import socketserver
    from wsgiref.simple_server import WSGIServer, WSGIRequestHandler

    class ThreadedWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
        daemon_threads = True
        allow_reuse_address = False  # Will FAIL fast if port already taken

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format, *args):
            # Route HTTP logs through standard logger instead of stderr
            logger.info(format % args)

    try:
        server = ThreadedWSGIServer(('127.0.0.1', port), QuietHandler)
        server.set_app(app)
        logger.info(f"Server bound to port {port} - serving")
        server.serve_forever()
    except OSError as e:
        logger.error(f"Port {port} already in use: {e}")
        # Try fallback port
        alt_port = 59877
        try:
            server = ThreadedWSGIServer(('127.0.0.1', alt_port), QuietHandler)
            server.set_app(app)
            logger.info(f"Fallback: bound to port {alt_port}")
            server.serve_forever()
        except Exception as e2:
            logger.error(f"Fallback port {alt_port} also failed: {e2}")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        logger.error(traceback.format_exc())
