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
    finish_catalog_routes.id_to_display_name

  SECTION 4: SWATCH RENDERING (L711-L1535)
    /api/swatch/<type>/<key>, /swatch/*, _render_swatch_bytes,
    _apply_fallback_gradient, _swatch_placeholder_png,
    _render_pattern_swatch_from_image_path, save_picker_split_snapshot,
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
import tempfile
import subprocess
from datetime import datetime
from urllib.parse import quote
from collections import deque, OrderedDict
from functools import wraps, lru_cache

from server_routes.iracing_pair_deploy import PairDeploymentError, deploy_iracing_tga_pair
from server_routes.preview_source_cache import PreviewSourceError, preview_source_cache
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows

# Config owns release identity. Import it before defining any server/header
# constants so diagnostics, build-info, and response headers cannot drift.
try:
    from config import CFG
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import CFG

from server_routes.request_security import (
    install_spb_origin_guard,
    is_same_spb_origin_url,
)
from server_routes.write_security import external_write_denial

# Server startup timestamp for uptime tracking
_server_start_time = time.time()

# Server version constants ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â exposed via headers + endpoints.
SPB_VERSION = str(CFG.VERSION)          # Single source: config._Config.VERSION
SPB_ENGINE_VERSION = "v6.2 PRO"        # Engine identifier shown in headers
SPB_BUILD_ID = str(CFG.BUILD_TAG)       # Single source: config._Config.BUILD_TAG
SPB_SMART_TGA_BUILD_ID = "smart-tga-cycle637-conflict-safe-evidence-canary-20260710"

# ----------------------------------------------------------------
# NAMED CONSTANTS ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â replace bare magic numbers throughout the file.
# Documented so future devs know WHY each value was chosen.
# ----------------------------------------------------------------

# Default maximum request body size (16 MB). Prevents OOM from malicious
# or accidental multi-gigabyte POSTs. Spec Sculpt receives a route-scoped
# allowance below because real layered 2048 iRacing PSDs routinely exceed it.
MAX_CONTENT_LENGTH_BYTES = 16 * 1024 * 1024
SPEC_SCULPT_MAX_CONTENT_LENGTH_BYTES = 256 * 1024 * 1024

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
# VALIDATION HELPERS ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â reusable bounds-checking for route handlers
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
    if not zone.get("base") and not zone.get("finish") and not zone.get("material_stack"):
        return False, f"Zone {index} ('{zone.get('name', 'unnamed')}'): must have 'base', 'finish', or 'material_stack'"
    return True, ""


def _sanitize_path(raw_path, allowed_roots=None):
    """Normalise a file path and optionally verify it falls under an allowed root.
    Returns (safe_path, error) ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â error is None on success."""
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


def _is_same_spb_origin_url(raw_url):
    """Accept loopback UI URLs only when they target this exact server port."""
    return is_same_spb_origin_url(raw_url, request.host_url)


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
        if raw and not _is_same_spb_origin_url(raw):
            return False, f"Blocked non-local {hdr.lower()}"
    return True, None


def _decode_rle_mask_payload(payload, label, *, expected_shape=None, max_shape=None):
    """Decode a UI RLE mask and reject malformed payloads explicitly."""
    import math
    import numpy as np

    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ValueError(f"{label}: expected RLE dict, got {type(payload).__name__}")

    rw = int(payload.get("width", 0))
    rh = int(payload.get("height", 0))
    if rw <= 0 or rh <= 0:
        raise ValueError(f"{label}: invalid RLE dimensions {rw}x{rh}")
    # [ULTRACODE 2026-08-22 M2] hard cap: canvas is 2048; an unbounded
    # width*height allocation was a memory bomb (100000x100000 -> 40GB).
    if rw > 4096 or rh > 4096:
        raise ValueError(f"{label}: RLE dimensions too large {rw}x{rh}")
    if expected_shape is not None and (rh, rw) != tuple(expected_shape):
        raise ValueError(
            f"{label}: RLE dimensions {rw}x{rh} do not match source "
            f"{int(expected_shape[1])}x{int(expected_shape[0])}"
        )
    if max_shape is not None and (rh > int(max_shape[0]) or rw > int(max_shape[1])):
        raise ValueError(
            f"{label}: RLE dimensions {rw}x{rh} exceed field limit "
            f"{int(max_shape[1])}x{int(max_shape[0])}"
        )

    runs = payload.get("runs", [])
    if not isinstance(runs, list):
        raise ValueError(f"{label}: expected RLE runs list")

    total = rw * rh
    if len(runs) > min(total, 4 * 1024 * 1024):
        raise ValueError(f"{label}: too many RLE runs ({len(runs)})")
    # A per-mask dimension cap is not sufficient when a request carries many
    # masks. Charge every allocation against one request-wide decoded-byte cap.
    try:
        from flask import current_app, g, has_request_context
        if has_request_context():
            requested_bytes = total * np.dtype(np.float32).itemsize
            limit = int(current_app.config.get("SPB_RLE_DECODE_BUDGET_BYTES", 1024 * 1024 * 1024))
            used = int(getattr(g, "_spb_rle_decoded_bytes", 0))
            if requested_bytes > max(0, limit - used):
                raise ValueError(
                    f"{label}: aggregate RLE decode budget exceeded "
                    f"({used >> 20} MiB decoded + {requested_bytes >> 20} MiB > {limit >> 20} MiB)"
                )
            g._spb_rle_decoded_bytes = used + requested_bytes
    except RuntimeError as _spb_ex:
        _spb_swallow('_decode_rle_mask_payload@L290', _spb_ex)
    flat = np.zeros(total, dtype=np.float32)
    pos = 0
    for run in runs:
        if not isinstance(run, (list, tuple)) or len(run) != 2:
            raise ValueError(f"{label}: invalid RLE run {run!r}")
        run_val, run_len = run
        run_value = float(run_val)
        if not math.isfinite(run_value) or run_value < 0.0 or run_value > 255.0:
            raise ValueError(f"{label}: invalid mask value {run_val!r}")
        run_len = int(run_len)
        if run_len <= 0 or pos + run_len > total:
            raise ValueError(f"{label}: RLE run exceeds mask size")
        flat[pos:pos + run_len] = run_value / 255.0 if run_value else 0.0
        pos += run_len

    if pos != total:
        raise ValueError(f"{label}: RLE runs cover {pos} of {total} pixels")
    return flat.reshape((rh, rw))


def _decode_spatial_mask_payload(payload, label, *, expected_shape=None):
    """Decode include/exclude spatial mask RLE without dropping malformed masks."""
    import numpy as np

    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ValueError(f"{label}: expected RLE dict, got {type(payload).__name__}")

    rw = int(payload.get("width", 0))
    rh = int(payload.get("height", 0))
    if rw <= 0 or rh <= 0:
        raise ValueError(f"{label}: invalid RLE dimensions {rw}x{rh}")
    # [ULTRACODE 2026-08-22 M2] hard cap: canvas is 2048; an unbounded
    # width*height allocation was a memory bomb (100000x100000 -> 40GB).
    if rw > 4096 or rh > 4096:
        raise ValueError(f"{label}: RLE dimensions too large {rw}x{rh}")
    if expected_shape is not None and (rh, rw) != tuple(expected_shape):
        raise ValueError(
            f"{label}: RLE dimensions {rw}x{rh} do not match source "
            f"{int(expected_shape[1])}x{int(expected_shape[0])}"
        )

    runs = payload.get("runs", [])
    if not isinstance(runs, list):
        raise ValueError(f"{label}: expected RLE runs list")

    total = rw * rh
    if len(runs) > min(total, 4 * 1024 * 1024):
        raise ValueError(f"{label}: too many RLE runs ({len(runs)})")
    try:
        from flask import current_app, g, has_request_context
        if has_request_context():
            requested_bytes = total * np.dtype(np.uint8).itemsize
            limit = int(current_app.config.get("SPB_RLE_DECODE_BUDGET_BYTES", 1024 * 1024 * 1024))
            used = int(getattr(g, "_spb_rle_decoded_bytes", 0))
            if requested_bytes > max(0, limit - used):
                raise ValueError(
                    f"{label}: aggregate RLE decode budget exceeded "
                    f"({used >> 20} MiB decoded + {requested_bytes >> 20} MiB > {limit >> 20} MiB)"
                )
            g._spb_rle_decoded_bytes = used + requested_bytes
    except RuntimeError as _spb_ex:
        _spb_swallow('_decode_spatial_mask_payload@L351', _spb_ex)
    flat = np.zeros(total, dtype=np.uint8)
    pos = 0
    for run in runs:
        if not isinstance(run, (list, tuple)) or len(run) != 2:
            raise ValueError(f"{label}: invalid RLE run {run!r}")
        run_val, run_len = run
        run_val = int(run_val)
        run_len = int(run_len)
        if run_val not in (0, 1, 2):
            raise ValueError(f"{label}: invalid spatial mask value {run_val}")
        if run_len <= 0 or pos + run_len > total:
            raise ValueError(f"{label}: RLE run exceeds mask size")
        flat[pos:pos + run_len] = run_val
        pos += run_len

    if pos != total:
        raise ValueError(f"{label}: RLE runs cover {pos} of {total} pixels")
    return flat.reshape((rh, rw))


def _image_rle_shape(image_path, label):
    """Return a bounded (height, width) contract for source-sized UI masks."""
    from PIL import Image as _PILImage

    try:
        with _PILImage.open(image_path) as image:
            width, height = image.size
    except Exception as exc:
        raise ValueError(f"{label}: unable to read source dimensions ({exc})") from exc
    if width <= 0 or height <= 0 or width > 4096 or height > 4096:
        raise ValueError(f"{label}: unsupported source dimensions {width}x{height}")
    return (height, width)


def _decode_source_layer_rgb_payload(payload, label, *, expected_shape=None):
    """Decode layer-local RGB PNG data and reject malformed payloads explicitly."""
    import numpy as np
    from PIL import Image as _PILImage

    if not isinstance(payload, str) or not payload:
        raise ValueError(f"{label}: expected base64 PNG string")
    raw = payload.split(",", 1)[-1] if payload.startswith("data:") else payload
    try:
        source = _PILImage.open(io.BytesIO(base64.b64decode(raw, validate=True)))
    except Exception as exc:
        raise ValueError(f"{label}: invalid layer RGB PNG ({exc})") from exc
    width, height = source.size
    if width <= 0 or height <= 0 or width > 4096 or height > 4096:
        source.close()
        raise ValueError(f"{label}: unsupported layer RGB dimensions {width}x{height}")
    if expected_shape is not None and (height, width) != tuple(expected_shape):
        source.close()
        raise ValueError(
            f"{label}: layer RGB dimensions {width}x{height} do not match source "
            f"{int(expected_shape[1])}x{int(expected_shape[0])}"
        )
    try:
        from flask import current_app, g, has_request_context
        if has_request_context():
            requested_bytes = width * height * 4
            limit = int(current_app.config.get("SPB_RLE_DECODE_BUDGET_BYTES", 1024 * 1024 * 1024))
            used = int(getattr(g, "_spb_rle_decoded_bytes", 0))
            if requested_bytes > max(0, limit - used):
                source.close()
                raise ValueError(
                    f"{label}: aggregate decoded payload budget exceeded "
                    f"({used >> 20} MiB decoded + {requested_bytes >> 20} MiB > {limit >> 20} MiB)"
                )
            g._spb_rle_decoded_bytes = used + requested_bytes
    except RuntimeError as _spb_ex:
        _spb_swallow('_decode_source_layer_rgb_payload@L419', _spb_ex)
    img = source.convert("RGBA")
    source.close()
    return np.asarray(img, dtype=np.uint8)


# [RENDER-BUDGET 2026-10-04] was 8: a design with 9+ unique layer sets (20-zone test:
# 9) walked the LRU cyclically, so EVERY preview missed EVERY entry and re-decoded +
# re-charged all of them. 16 entries x 16 MiB per cache; only designs that really use
# that many layer sets fill it.
_SOURCE_LAYER_PAYLOAD_CACHE_LIMIT = 16
_source_layer_mask_decode_cache = OrderedDict()
_source_layer_rgb_decode_cache = OrderedDict()


def _payload_sha1(payload):
    raw = payload.split(",", 1)[-1] if isinstance(payload, str) and payload.startswith("data:") else payload
    if isinstance(raw, str):
        data = raw.encode("utf-8", "surrogatepass")
    else:
        data = json.dumps(raw, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(data).hexdigest()


def _source_layer_payload_key(zone, payload, field_name):
    source_id = zone.get("source_layer_id") or zone.get("source_layer")
    revision = zone.get("source_layer_revision")
    if source_id is not None and revision is not None:
        size = zone.get("source_layer_size") or []
        bbox = zone.get("source_layer_bbox") or []
        if isinstance(payload, dict):
            payload_shape = (
                int(payload.get("width", 0) or 0),
                int(payload.get("height", 0) or 0),
                len(payload.get("runs", []) or []),
            )
        elif isinstance(payload, str):
            # [ULTRACODE 2026-08-22 synthesis #5a] length is not identity —
            # same-length different-content data-URLs collided on the fast
            # path. Hash the content.
            payload_shape = (len(payload), _payload_sha1(payload))
        else:
            payload_shape = ()
        # [ULTRACODE 2026-08-22, cache-integrity lane] the id+revision fast
        # path had NO content signal — the client's revision counter resets to
        # 0 on every reload, so after a reload (no server restart) this key
        # could replay a STALE decoded mask for changed content. Fold a cheap
        # content digest of the runs in: same id/revision + different pixels
        # now miss instead of silently replaying yesterday's ownership.
        # [SPB-PREVIEW-SPEED 2026-08-24] this used to hash EVERY run in a Python
        # loop with two int->bytes conversions per run: ~36 ms per mask per
        # request on a real 120k-run livery mask, paid on every preview for
        # every zone. Sampled signature instead — total run count, total covered
        # length (catches any structural change), 512 strided runs plus both
        # ends: ~3.6 ms, 10x cheaper, and still a genuine content signal. Belt
        # and braces anyway now that _layerCompositeRevision is seeded from
        # wall-clock (a reload can no longer reuse a stale revision).
        _content_sig = ""
        try:
            if isinstance(payload, dict):
                _runs = payload.get("runs", []) or []
                _step = max(1, len(_runs) // 512)
                _sig = (
                    len(_runs),
                    sum(_r[1] for _r in _runs),
                    tuple(map(tuple, _runs[::_step][:512])),
                    tuple(map(tuple, _runs[:8])),
                    tuple(map(tuple, _runs[-8:])),
                )
                _content_sig = hashlib.blake2b(repr(_sig).encode(), digest_size=8).hexdigest()
        except Exception:
            _content_sig = "err"
        return (field_name, str(source_id), str(revision), tuple(size), tuple(bbox), payload_shape, _content_sig)
    return (field_name, _payload_sha1(payload))


def _cache_get(cache, key):
    try:
        value = cache.get(key)
        if value is not None:
            cache.move_to_end(key)
        return value
    except Exception:
        return None


def _cache_put(cache, key, value, limit):
    try:
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > limit:
            cache.popitem(last=False)
    except Exception as _spb_ex:
        _spb_swallow('_cache_put@L508', _spb_ex)
    return value


def _request_source_layer_memo():
    """[RENDER-BUDGET 2026-10-04] per-request {payload_key: decoded array}.

    Zones restricted to the same layer set send byte-identical layer payloads (the AI's
    per-part splits, Spray Can left/right/hood). The process LRU used to be the only
    dedupe, so once a request held more unique sets than the LRU an identical payload was
    decoded (and charged, and held in RAM) twice. Within one request it is now decoded
    exactly once, whatever the LRU size. Same arrays the LRU would hand out: no pixel change."""
    try:
        from flask import g, has_request_context
        if has_request_context():
            memo = getattr(g, "_spb_source_layer_request_memo", None)
            if memo is None:
                memo = {}
                g._spb_source_layer_request_memo = memo
            return memo
    except Exception as _spb_ex:
        _spb_swallow('_request_source_layer_memo', _spb_ex)
    return None


def _decode_cached_source_layer_mask(zone, label, *, expected_shape=None):
    """Cache layer-visible masks across preview/full renders without changing pixels."""
    payload = zone.get("source_layer_mask")
    payload_key = _source_layer_payload_key(zone, payload, "source_layer_mask")
    zone["_source_layer_mask_cache_key"] = payload_key
    _memo = _request_source_layer_memo()
    cached = _memo.get(payload_key) if _memo is not None else None
    if cached is None:
        cached = _cache_get(_source_layer_mask_decode_cache, payload_key)
    if cached is not None:
        if expected_shape is not None and tuple(cached.shape) != tuple(expected_shape):
            raise ValueError(
                f"{label}: cached mask dimensions {cached.shape[1]}x{cached.shape[0]} "
                f"do not match source {expected_shape[1]}x{expected_shape[0]}"
            )
        if _memo is not None:
            _memo[payload_key] = cached
        return cached
    decoded = _decode_rle_mask_payload(payload, label, expected_shape=expected_shape)
    if _memo is not None:
        _memo[payload_key] = decoded
    return _cache_put(_source_layer_mask_decode_cache, payload_key, decoded, _SOURCE_LAYER_PAYLOAD_CACHE_LIMIT)


def _decode_cached_source_layer_rgb(zone, label, *, expected_shape=None):
    """Cache layer-local RGB PNG decode and hand the engine a stable mask-cache key."""
    payload = zone.get("source_layer_rgb_png")
    payload_key = _source_layer_payload_key(zone, payload, "source_layer_rgb")
    zone["_source_layer_rgb_cache_key"] = payload_key
    _memo = _request_source_layer_memo()
    cached = _memo.get(payload_key) if _memo is not None else None
    if cached is None:
        cached = _cache_get(_source_layer_rgb_decode_cache, payload_key)
    if cached is not None:
        if expected_shape is not None and tuple(cached.shape[:2]) != tuple(expected_shape):
            raise ValueError(
                f"{label}: cached layer RGB dimensions {cached.shape[1]}x{cached.shape[0]} "
                f"do not match source {expected_shape[1]}x{expected_shape[0]}"
            )
        if _memo is not None:
            _memo[payload_key] = cached
        return cached
    decoded = _decode_source_layer_rgb_payload(payload, label, expected_shape=expected_shape)
    if _memo is not None:
        _memo[payload_key] = decoded
    return _cache_put(_source_layer_rgb_decode_cache, payload_key, decoded, _SOURCE_LAYER_PAYLOAD_CACHE_LIMIT)

# ----------------------------------------------------------------
# HARDENING: extra validators, rate limiter, request log ring,
# memoised registry helpers. All purely additive ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â existing
# routes can opt-in by calling these helpers explicitly.
# ----------------------------------------------------------------

# Hard ceiling on zone arrays ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â anything past this is almost
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

# Total request counter ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â incremented in before_request hook.
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
    except Exception as _spb_ex:
        _spb_swallow('_record_recent_error@L597', _spb_ex)


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
    except Exception as _spb_ex:
        _spb_swallow('_record_recent_render@L612', _spb_ex)


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
    Looser than _validate_zone_required_fields ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â checks types/bounds for
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
    # base/finish presence ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â same rule as the legacy helper but explicit.
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
    """Validate iRacing customer ID ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â must be all digits, 4-7 long.
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
       - blanket try/except ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ consistent JSON error
       - logging of unhandled exceptions
    Existing routes are NOT migrated automatically ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â opt-in only."""
    def deco(fn):
        @wraps(fn)
        def wrapped(*a, **kw):
            rid = getattr(g, "_rid", None) or _new_request_id()
            try:
                g._rid = rid
            except Exception as _spb_ex:
                _spb_swallow('wrapped@L752', _spb_ex)
            try:
                return fn(*a, **kw)
            except FileNotFoundError as e:
                _record_recent_error(rid, request.path, 404, str(e))
                return _safe_jsonify_error(str(e), 404, rid)
            except (ValueError, TypeError) as e:
                _record_recent_error(rid, request.path, 400, str(e))
                return _safe_jsonify_error(str(e), 400, rid)
            except (ConnectionError, BrokenPipeError) as e:
                # S3 (2026-06-03): the client closed the socket mid-response — common when the
                # swatch picker cancels in-flight loads or the window navigates away. It is not a
                # server fault and there is nothing left to send, so log quietly (INFO, no
                # traceback) instead of ERROR. 499 = "client closed request" (nginx convention).
                logger.info(f"[rid={rid}] client disconnected on {request.path}: {type(e).__name__}")
                return ("", 499)
            except Exception as e:
                tb = traceback.format_exc()
                logger.error(f"[rid={rid}] Unhandled in {fn.__name__}: {e}\n{tb}")
                _record_recent_error(rid, request.path, 500, str(e))
                return _safe_jsonify_error("internal_server_error", 500, rid,
                                           detail=str(e)[:200])
        return app.route(*args, **kwargs)(wrapped)
    return deco


# ----------------------------------------------------------------
# JSÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢Python key conversion: JS sends camelCase, engine expects snake_case.
# Applied to zone dicts before processing in /preview-render and /render.
# ----------------------------------------------------------------
def _camel_to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def _convert_zone_keys(zone_dict):
    """Recursively convert camelCase keys to snake_case in a zone dict."""
    if not isinstance(zone_dict, dict):
        return zone_dict
    converted = {_camel_to_snake(k): _convert_zone_keys(v) if isinstance(v, dict) else v
                 for k, v in zone_dict.items()}
    # SPB base-mode hotfix 2026-09-09: an app/API payload naming a color mode
    # is authoritative, including old clients/saves without the auxiliary flag.
    # This shared boundary covers preview, Render and Photoshop exports. Legacy
    # engine-only calls still retain their original inherited-default behavior.
    if converted.get("base_color_mode") in ("source", "finish", "own", "solid", "special", "gradient"):
        converted["base_color_explicit"] = True
    return converted


_BASE_OVERLAY_PATTERN_BLEND_MODES = {
    "pattern",
    "pattern_reactive",
    "pattern_vivid",
    "pattern_pop",
    "pattern_edges",
    "pattern_peaks",
    "pattern_contour",
    "pattern_screen",
    "pattern_stream",
    "pattern_threshold",
}


def _normalize_overlay_blend_mode_token(value):
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _overlay_blend_mode_requires_pattern(value):
    return _normalize_overlay_blend_mode_token(value) in _BASE_OVERLAY_PATTERN_BLEND_MODES


def _is_blank_overlay_pattern_value(value):
    if value is None:
        return True
    normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    return normalized in (
        "",
        "none",
        "_none_",
        "__none__",
        "none_(base_only)",
        "none_(independent)",
        "base_only",
    )


def _overlay_number_missing_or_default(zone, key, default_value, tolerance=1e-6):
    if key not in zone or zone.get(key) is None:
        return True
    try:
        return abs(float(zone.get(key)) - float(default_value)) <= tolerance
    except (TypeError, ValueError):
        return True


def _overlay_number_missing_default_or_zero(zone, key, default_value, tolerance=1e-6):
    if _overlay_number_missing_or_default(zone, key, default_value, tolerance):
        return True
    try:
        return float(zone.get(key)) <= tolerance
    except (TypeError, ValueError):
        return True


def _repair_base_overlay_pattern_reactive_payload(zone):
    """Make stale overlay payloads inherit the zone pattern for Pattern Pop modes.

    Older UI state can keep 2nd-5th overlay react-pattern as "__none__" even
    while the visible control means "use the zone's primary pattern". Pattern
    modes should therefore inherit the primary pattern and transform at the
    server boundary. Tint is intentionally excluded so uniform tint behavior
    remains unchanged.
    """
    if not isinstance(zone, dict):
        return zone
    primary_pattern = zone.get("pattern")
    if not primary_pattern or str(primary_pattern).strip().lower() in ("", "none", "__none__"):
        return zone

    for prefix in ("second_base", "third_base", "fourth_base", "fifth_base"):
        if not _overlay_blend_mode_requires_pattern(zone.get(f"{prefix}_blend_mode")):
            continue
        has_overlay = bool(
            zone.get(prefix)
            or zone.get(f"{prefix}_color_source")
            or _safe_float(zone.get(f"{prefix}_strength"), 0.0) > 0.001
        )
        if not has_overlay:
            continue
        if not _is_blank_overlay_pattern_value(zone.get(f"{prefix}_pattern")):
            continue

        zone[f"{prefix}_pattern"] = ""
        if "scale" in zone and _overlay_number_missing_or_default(zone, f"{prefix}_pattern_scale", 1.0):
            zone[f"{prefix}_pattern_scale"] = zone.get("scale")
        if "rotation" in zone and _overlay_number_missing_or_default(zone, f"{prefix}_pattern_rotation", 0.0):
            zone[f"{prefix}_pattern_rotation"] = zone.get("rotation")
        if _overlay_number_missing_default_or_zero(zone, f"{prefix}_pattern_opacity", 1.0):
            zone[f"{prefix}_pattern_opacity"] = zone.get("pattern_opacity", 1.0)
        if _overlay_number_missing_default_or_zero(zone, f"{prefix}_pattern_strength", 1.0):
            zone[f"{prefix}_pattern_strength"] = 1.0
        if "pattern_offset_x" in zone and _overlay_number_missing_or_default(zone, f"{prefix}_pattern_offset_x", 0.5):
            zone[f"{prefix}_pattern_offset_x"] = zone.get("pattern_offset_x")
        if "pattern_offset_y" in zone and _overlay_number_missing_or_default(zone, f"{prefix}_pattern_offset_y", 0.5):
            zone[f"{prefix}_pattern_offset_y"] = zone.get("pattern_offset_y")
        if zone.get("pattern_flip_h") and zone.get(f"{prefix}_pattern_flip_h") is None:
            zone[f"{prefix}_pattern_flip_h"] = True
        if zone.get("pattern_flip_v") and zone.get(f"{prefix}_pattern_flip_v") is None:
            zone[f"{prefix}_pattern_flip_v"] = True

    return zone

# ----------------------------------------------------------------
# Preview render serialisation ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â prevents CPU thrashing when the
# UI fires multiple /preview-render requests before the previous
# one finishes (e.g. slider dragging, zone switching).
#
# _preview_abort  ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â set this Event to tell an in-flight render it
#                   should give up (currently used as a signal; the
#                   actual check is the lock timeout below).
# _preview_render_lock ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â only one preview renders at a time.
#                   Acquiring it with a short timeout means stale
#                   requests return 429 instead of stacking up.
# ----------------------------------------------------------------
_preview_render_lock = threading.Lock()

# [2026-06-12 preview-deadlock fix] cross-process "painter is active" signal.
# The boot swatch warm runs as a DETACHED subprocess; after engine changes it
# re-bakes ~1700 swatches (~18 min) and the CPU contention made live previews
# miss their timeouts (UI marked the server offline -> dead preview). The
# preview/render routes touch this file; the warm loop pauses while it's fresh.
_USER_ACTIVE_HEARTBEAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_spb_user_active.heartbeat")


def _touch_user_active_heartbeat():
    try:
        if _external_write_denial(_USER_ACTIVE_HEARTBEAT, "user-active-heartbeat"):
            return
        with open(_USER_ACTIVE_HEARTBEAT, "w") as _hb:
            _hb.write(str(time.time()))
    except Exception as _spb_ex:
        _spb_swallow('_touch_user_active_heartbeat@L926', _spb_ex)
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


def _get_prev_spec_cache():
    return _prev_spec_cache


def _set_prev_spec_cache(value):
    global _prev_spec_cache
    _prev_spec_cache = value

# ----------------------------------------------------------------
# Render statistics ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â accumulated during the server session.
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
# Render progress ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â tracks zone-by-zone progress for full renders.
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
        except (OSError, ValueError) as _spb_ex:
            _spb_swallow('write@L992', _spb_ex)
    def flush(self):
        try:
            self._stream.flush()
        except (OSError, ValueError) as _spb_ex:
            _spb_swallow('flush@L997', _spb_ex)
    def __getattr__(self, name):
        return getattr(self._stream, name)

sys.stdout = _SafeStream(sys.stdout)
sys.stderr = _SafeStream(sys.stderr)

# Import the engine package (V5) and config
try:
    import engine
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import engine
# engine package provides V5 registries (BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY) via __getattr__

# GPU acceleration detection
try:
    from engine.gpu import gpu_info
except ImportError:
    def gpu_info(): return {'backend': 'cpu', 'name': 'CPU', 'vram_mb': 0, 'accelerated': False, 'icon': 'CPU'}

# Setup Flask
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH_BYTES  # Reject oversized POSTs (improvement #5)
# [RENDER-BUDGET 2026-10-04] request-wide decoded-payload budget: the anti-OOM ceiling for
# hostile / runaway payloads (every decoded mask / layer image of one request is charged).
# Was 256 MiB = 16 planes of 2048x2048 float32. A layer-limited zone costs 2 planes (float32
# layer mask + RGBA layer image) per UNIQUE layer set and a part-limited zone 1 more (float32
# region mask), so 256 MiB ran out at ~8 zones: the owner's ARCA design after one AI turn =
# 5 unique layer sets x 32 MiB + 7 region masks x 16 MiB = 272 MiB on a cold cache, and the
# first preview failed ("my change didn't happen"). 1 GiB = 64 planes = ~20 zones that each
# have their own layer set AND a part limit; still a hard ceiling (a hostile 50-zone payload
# of four full-canvas masks per zone would decode ~2.6 GiB). Measurements:
# docs/handoff_reports/RENDER_BUDGET.md. The decoders keep the same number as their
# no-config fallback (they are exec'd standalone by tests, so it is a literal there).
app.config['SPB_RLE_DECODE_BUDGET_BYTES'] = 1024 * 1024 * 1024
# Enable JSON pretty-print only in dev ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â saves bytes in prod responses.
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
# Track app start for /api/health & /api/stats (mirrors _server_start_time).
app._start_time = _server_start_time
CORS(app)


# The shared exact-loopback-origin policy is installed after logging is ready.


# Shared cache-control header dicts (avoids typos and inconsistency)
_no_cache_headers = {'Cache-Control': 'no-store, no-cache, must-revalidate', 'Pragma': 'no-cache'}
_immutable_cache_headers = {'Cache-Control': 'public, max-age=31536000, immutable'}
# Short-lived cache for finish data, swatches that change rarely (5 minutes).
_short_cache_headers = {'Cache-Control': 'public, max-age=300'}


def _coerce_output_dir(raw):
    """Resolve the iRacing output field to an existing directory.

    Accept an existing directory or an existing file path, or an explicit .tga path (existing or
    not-yet-created) whose parent already exists. Do not reinterpret a missing
    folder as its parent: that silently redirects exports to the wrong place.
    """
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    # The UI accepts pasted paths wrapped in a matching single/double quote.
    # Peel balanced wrapper pairs only; malformed/unbalanced quoting is invalid.
    while len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1].strip()
    if not value or value[0] in ('"', "'") or value[-1] in ('"', "'"):
        return None
    path = os.path.normpath(value)
    if os.path.isdir(path):
        return path
    parent = os.path.dirname(path) or os.curdir
    if not os.path.isdir(parent):
        return None
    if os.path.isfile(path):
        return parent
    leaf = os.path.basename(path)
    if os.path.splitext(leaf)[1].lower() == ".tga":
        return parent
    return None


# ----------------------------------------------------------------
# REQUEST MIDDLEWARE ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â adds correlation IDs, timing headers,
# version headers, and structured access logs. Runs for every
# request without changing existing route handlers.
# ----------------------------------------------------------------
@app.before_request
def _spb_before_request():
    """Stamp request with start time + correlation ID."""
    try:
        # Flask 3.1 supports a per-request upload cap. Keep the conservative
        # app-wide ceiling, while allowing the local PSD/material workflows to
        # accept real layered 2048 templates instead of failing at 16 MB.
        if request.path == "/api/psd-import" or request.path.startswith("/api/spec-sculpt/"):
            request.max_content_length = SPEC_SCULPT_MAX_CONTENT_LENGTH_BYTES
        g._t0 = time.perf_counter()
        g._rid = request.headers.get("X-Request-ID") or _new_request_id()
        global _request_counter
        with _request_counter_lock:
            _request_counter += 1
    except Exception as _spb_ex:
        _spb_swallow('_spb_before_request@L1081', _spb_ex)


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
        except Exception as _spb_ex:
            # Compression must NEVER break a response.
            _spb_swallow('_spb_after_request@L1110', _spb_ex)
        # Quiet down spammy polling endpoints ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â only log slow / non-200 hits.
        # 2026-04-21 perf fix: added /build-check (polled every 5s by the UI) to
        # the silenced set ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â every build-check was hitting logger.info and
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
    except Exception as _spb_ex:
        _spb_swallow('_spb_after_request@L1126', _spb_ex)
    return resp

@app.errorhandler(404)
def _handle_404(e):
    rid = getattr(g, "_rid", None) or "-"
    _record_recent_error(rid, request.path, 404, "not_found")
    return jsonify({"error": "not_found", "path": request.path, "rid": rid}), 404

@app.errorhandler(413)
def _handle_413(e):
    """Request entity too large ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â MAX_CONTENT_LENGTH exceeded."""
    rid = getattr(g, "_rid", None) or "-"
    active_limit = int(request.max_content_length or MAX_CONTENT_LENGTH_BYTES)
    logger.warning(f"[rid={rid}] Request too large on {request.path} "
                   f"(limit: {active_limit // (1024*1024)}MB)")
    _record_recent_error(rid, request.path, 413, "payload_too_large")
    return jsonify({"error": "Request body too large",
                    "max_mb": active_limit // (1024 * 1024),
                    "rid": rid}), 413

@app.errorhandler(400)
def _handle_400(e):
    """Bad request ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â catches malformed JSON, missing fields, etc."""
    rid = getattr(g, "_rid", None) or "-"
    # 400 errors are user-facing: log message only, NOT full traceback.
    msg = getattr(e, 'description', None) or str(e)
    logger.info(f"[rid={rid}] 400 on {request.path}: {msg}")
    _record_recent_error(rid, request.path, 400, msg)
    return jsonify({"error": "bad_request", "message": msg, "rid": rid}), 400

@app.errorhandler(429)
def _handle_429(e):
    """Too many requests ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â typically from rate limiter."""
    rid = getattr(g, "_rid", None) or "-"
    return jsonify({"error": "too_many_requests",
                    "message": "Rate limit exceeded ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â slow down and retry.",
                    "rid": rid}), 429

@app.errorhandler(500)
def _handle_500(e):
    """Internal server error ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â log traceback and return safe message."""
    rid = getattr(g, "_rid", None) or "-"
    # Full traceback ONLY for 500s ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 400/404 keep the log clean.
    logger.error(f"[rid={rid}] Unhandled 500 on {request.path}: {e}\n{traceback.format_exc()}")
    _record_recent_error(rid, request.path, 500, str(e))
    return jsonify({"error": "internal_server_error",
                    "message": "An unexpected error occurred. Check server logs for details.",
                    "rid": rid}), 500

@app.errorhandler(503)
def _handle_503(e):
    """Service unavailable ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â engine not loaded, GPU busy, etc."""
    rid = getattr(g, "_rid", None) or "-"
    return jsonify({"error": "service_unavailable",
                    "message": getattr(e, 'description', 'Service temporarily unavailable.'),
                    "rid": rid,
                    "retry_after_s": 5}), 503

@app.errorhandler(405)
def _handle_405(e):
    """Method not allowed ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â wrong HTTP verb on a known route."""
    rid = getattr(g, "_rid", None) or "-"
    return jsonify({"error": "method_not_allowed",
                    "method": request.method,
                    "path": request.path,
                    "rid": rid}), 405

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
OUTPUT_FOLDER = os.path.realpath(os.path.abspath(CFG.OUTPUT_DIR))


def _external_write_denial(target_path, operation):
    """Deny writes outside SPB-owned output while verification mode is active."""
    return external_write_denial(
        target_path,
        operation,
        owned_root=OUTPUT_FOLDER,
        # A few startup cache checks run before the main logger is assigned.
        logger=globals().get("logger"),
    )


# Spec Sculpt jobs only ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â isolated from main render jobs; capped retention below.
SPEC_SCULPT_JOBS_DIR = os.path.join(OUTPUT_FOLDER, 'shokker_spec_sculpt')
SPEC_SCULPT_JOBS_RETENTION = 12
CONFIG_FILE = os.path.join(SERVER_DIR, 'shokker_config.json')
DEFAULT_ASSET_FILENAMES = {
    # [SPB 2026-06-02 owner] First-launch default source paint = the Chevy truck
    # starter PSD that ships at the project root.
    "starter_psd": "SPB Chevy Truck Starting Example PSD.psd",
    "blank_canvas_tga": "blank_canvas_2048_white.tga",
}


def _default_asset_path(filename: str) -> str:
    """Find a bundled default asset in dev, Electron, or frozen runtime."""
    seen = set()
    for base in (SERVER_DIR, BUNDLE_DIR):
        if not base or base in seen:
            continue
        seen.add(base)
        candidate = os.path.abspath(os.path.join(base, "assets", "defaults", filename))
        if os.path.isfile(candidate):
            return candidate
        # [SPB 2026-06-02 owner] Also accept a starter asset sitting directly next to
        # the server — dev runs from the project root, where the example PSD lives.
        root_candidate = os.path.abspath(os.path.join(base, filename))
        if os.path.isfile(root_candidate):
            return root_candidate
    return ""

# Pre-rendered thumbnails: env override > config > next to server. Ensures accurate thumbnails on every load when folder exists.
THUMBNAIL_DIR = os.environ.get('SHOKKER_THUMBNAIL_DIR') or getattr(CFG, 'THUMBNAIL_DIR', None) or os.path.join(SERVER_DIR, 'thumbnails')

from server_routes.asset_routes import register_asset_routes
register_asset_routes(
    app,
    server_dir=SERVER_DIR,
    bundle_dir=BUNDLE_DIR,
    thumbnail_dir=THUMBNAIL_DIR,
)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(SPEC_SCULPT_JOBS_DIR, exist_ok=True)
SPB_TEMP_FOLDER = os.path.join(OUTPUT_FOLDER, "temp")
os.makedirs(SPB_TEMP_FOLDER, exist_ok=True)

# Static HTML pages ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â must run after SERVER_DIR / BUNDLE_DIR exist (SPB boot fix 2026-05-17).
from server_routes.static_pages import register_static_page_routes
register_static_page_routes(app, server_dir=SERVER_DIR, bundle_dir=BUNDLE_DIR)
from server_routes.spec_overlay_routes import register_spec_overlay_routes
register_spec_overlay_routes(app)

# Windows temp can become unavailable under sandboxing, permissions changes, or
# stale short-path env values. Keep all SPB scratch files under the app output
# folder so live preview/decal handling never depends on OS temp health.
tempfile.tempdir = SPB_TEMP_FOLDER


def _purge_spec_sculpt_jobs(keep: int | None = None):
    """Keep only the newest ``keep`` Spec Sculpt job folders under ``shokker_spec_sculpt``."""
    k = SPEC_SCULPT_JOBS_RETENTION if keep is None else int(keep)
    try:
        if not os.path.isdir(SPEC_SCULPT_JOBS_DIR):
            return
        job_dirs = sorted(
            [
                d
                for d in os.listdir(SPEC_SCULPT_JOBS_DIR)
                if d.startswith("job_") and os.path.isdir(os.path.join(SPEC_SCULPT_JOBS_DIR, d))
            ],
            key=lambda d: os.path.getmtime(os.path.join(SPEC_SCULPT_JOBS_DIR, d)),
            reverse=True,
        )
        for old in job_dirs[k:]:
            shutil.rmtree(os.path.join(SPEC_SCULPT_JOBS_DIR, old), ignore_errors=True)
    except Exception as _spb_ex:
        _spb_swallow('_purge_spec_sculpt_jobs@L1292', _spb_ex)


def _schedule_spec_sculpt_purge():
    """Run retention after the response so Save never waits on old 30 MB jobs."""
    # SPB-BETA-2026-07-20 live timing: at the 12-job cap, synchronous deletion
    # added several seconds to an otherwise ~3 s guided render. A short daemon
    # delay keeps the exact retention policy but removes cleanup from click time.
    timer = threading.Timer(1.5, _purge_spec_sculpt_jobs)
    timer.daemon = True
    timer.start()


def _resolve_output_job_dir(safe_job_id: str) -> str | None:
    """Locate an owned render job without crossing product namespaces."""
    safe_job_id = str(safe_job_id or "")
    if safe_job_id.startswith("render_"):
        bases = (OUTPUT_FOLDER,)
    elif safe_job_id.startswith("sculpt_"):
        bases = (SPEC_SCULPT_JOBS_DIR,)
    else:
        # Read-only compatibility for jobs created before namespaced IDs.
        bases = (OUTPUT_FOLDER, SPEC_SCULPT_JOBS_DIR)
    for base in bases:
        p = os.path.join(base, f"job_{safe_job_id}")
        if os.path.isdir(p):
            return p
    return None


def _spb_mkdtemp(prefix="shokker_"):
    os.makedirs(SPB_TEMP_FOLDER, exist_ok=True)
    # tempfile.mkdtemp can create Windows ACLs that are unreadable inside the
    # sandboxed desktop runner. Inheriting the app temp folder ACL keeps live
    # canvas preview/decal scratch files writable by the same process.
    for _ in range(100):
        path = os.path.join(SPB_TEMP_FOLDER, f"{prefix}{uuid.uuid4().hex}")
        try:
            os.makedirs(path, exist_ok=False)
            return path
        except FileExistsError as _spb_ex:
            _spb_swallow('_spb_mkdtemp@L1333', _spb_ex); continue
    return tempfile.mkdtemp(prefix=prefix, dir=SPB_TEMP_FOLDER)


def _spb_temp_file_path(filename):
    os.makedirs(SPB_TEMP_FOLDER, exist_ok=True)
    return os.path.join(SPB_TEMP_FOLDER, filename)

# --- Auto-invalidate swatch disk cache when engine code changes ---
def _engine_files_fingerprint():
    """Stable hash of renderer source files.

    Use file contents instead of mtimes so packaged installs and app restarts do
    not invalidate swatch thumbnails unless the renderer code actually changed.
    """
    import hashlib
    digest = hashlib.md5()
    for root, dirs, files in os.walk(os.path.join(SERVER_DIR, 'engine')):
        for f in sorted(files):
            if f.endswith('.py'):
                fp = os.path.join(root, f)
                try:
                    rel = os.path.relpath(fp, SERVER_DIR).replace('\\', '/')
                    digest.update(rel.encode('utf-8', 'ignore'))
                    with open(fp, 'rb') as src:
                        digest.update(src.read())
                except OSError:
                    pass
    # Also include main engine files
    for f in ['shokker_engine_v2.py', 'server.py']:
        fp = os.path.join(SERVER_DIR, f)
        if os.path.isfile(fp):
            try:
                digest.update(f.encode('utf-8', 'ignore'))
                with open(fp, 'rb') as src:
                    digest.update(src.read())
            except OSError as _spb_ex:
                _spb_swallow('_engine_files_fingerprint@L1370', _spb_ex)
    return digest.hexdigest()[:12]

def _check_swatch_cache_freshness():
    """If engine code changed since last swatch cache build, wipe the disk cache."""
    cache_dir = os.path.join(THUMBNAIL_DIR, 'swatch_cache')
    if _external_write_denial(cache_dir, "swatch-cache-startup"):
        return
    fp_file = os.path.join(cache_dir, '_fingerprint.txt')
    current_fp = _engine_files_fingerprint()
    if os.path.isdir(cache_dir) and os.path.isfile(fp_file):
        try:
            with open(fp_file, 'r') as f:
                stored_fp = f.read().strip()
            if stored_fp == current_fp:
                return  # Cache is fresh
        except Exception as _spb_ex:
            _spb_swallow('_check_swatch_cache_freshness@L1387', _spb_ex)
    # Cache is stale or doesn't exist ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â wipe and rebuild
    if os.path.isdir(cache_dir):
        import shutil
        try:
            # Owner 2026-09-18: full-detail thumbnails are permanent content-
            # addressed bakes. Their per-finish fingerprint already changes when
            # that renderer changes; unrelated engine edits must not erase them.
            # Retire only the legacy globally keyed cache, within this directory.
            cache_root = os.path.realpath(cache_dir)
            for name in os.listdir(cache_root):
                if name == 'faithful_split_v1':
                    continue
                target = os.path.realpath(os.path.join(cache_root, name))
                if os.path.commonpath([cache_root, target]) != cache_root:
                    continue
                if os.path.isdir(target) and not os.path.islink(os.path.join(cache_root, name)):
                    shutil.rmtree(target)
                else:
                    os.unlink(os.path.join(cache_root, name))
            logging.getLogger('shokker.startup').info("Legacy swatch cache invalidated; persistent faithful bakes retained")
        except Exception as _spb_ex:
            _spb_swallow('_check_swatch_cache_freshness@L1395', _spb_ex)
    os.makedirs(cache_dir, exist_ok=True)
    try:
        with open(fp_file, 'w') as f:
            f.write(current_fp)
    except Exception as _spb_ex:
        _spb_swallow('_check_swatch_cache_freshness@L1401', _spb_ex)

_check_swatch_cache_freshness()

_SWATCH_CACHE_TOKEN = None
_SWATCH_CACHE_TOKEN_TS = 0.0
_SWATCH_CACHE = {}
_SWATCH_CACHE_LOCK = threading.Lock()

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

# [ULTRACODE 2026-08-22 M3] server_v5.py creates a distinct Flask app, so every
# entry point installs this helper rather than expecting inherited view
# functions to carry Flask hooks.
install_spb_origin_guard(app, logger=logger)

# Observability (audit "No observability" gap): global sys.excepthook -> local
# rotating crash log + a catch-all Flask errorhandler(Exception) returning a
# clean JSON 500. Additive + opt-out-safe (SHOKKER_OBSERVABILITY=0 disables;
# default on; local-only). Never raises -- wrapped so a wiring failure can't
# block server startup.
try:
    from server_routes.observability import install_observability, log_startup as _spb_log_startup
    install_observability(app, logger=logger, server_dir=SERVER_DIR)
    _spb_log_startup(
        logger,
        name="server.py",
        version=SPB_VERSION,
        engine_version=SPB_ENGINE_VERSION,
        extra={"build": SPB_BUILD_ID},
    )
except Exception as _obs_e:  # pragma: no cover - defensive
    logger.warning(f"Observability hooks not installed: {_obs_e}")

# June Complete Audit — verdict logging + page serving for the living
# spec-overlay / base / pattern audits (logger + SERVER_DIR are both ready here).
try:
    from server_routes.june_audit_routes import register_june_audit_routes
    register_june_audit_routes(
        app,
        server_dir=SERVER_DIR,
        logger=logger,
        external_write_guard=lambda path, operation: _external_write_denial(path, operation),
    )
except Exception as _june_e:  # pragma: no cover - defensive
    logger.warning(f"June audit routes not installed: {_june_e}")

# SPB Workbench — persistent owner work-management tool (dev/owner-only, additive).
# Catalog/ratings/bugs/worklog APIs + SPB_WORKBENCH.html. Defensive: never blocks boot.
try:
    from server_routes.workbench_routes import register_workbench_routes
    register_workbench_routes(
        app,
        server_dir=SERVER_DIR,
        logger=logger,
        external_write_guard=lambda path, operation: _external_write_denial(path, operation),
    )
except Exception as _wb_e:  # pragma: no cover - defensive
    logger.warning(f"Workbench routes not installed: {_wb_e}")

# [E28 2026-08-08] Easy Mode "SHOW ME WHERE": the real per-material routing map
# for a Whole Car mix, straight from the engine that renders it. Defensive.
try:
    from server_routes.material_map_routes import register_material_map_routes
    register_material_map_routes(app, server_dir=SERVER_DIR, logger=logger)
except Exception as _mm_e:  # pragma: no cover - defensive
    logger.warning(f"Material map route not installed: {_mm_e}")

# ── MEGA FEATURES (2026-06-13 overnight run) — all additive + flag-guarded.
#    New routes only; each in its own defensive try/except so a failure can
#    NEVER block boot (owner mandate: nothing breaks what already works).
try:
    from server_routes.livery_designer_routes import register_livery_designer_routes
    register_livery_designer_routes(app, logger=logger)
except Exception as _ld_e:  # pragma: no cover - defensive
    logger.warning(f"Livery Designer routes not installed: {_ld_e}")
try:
    from server_routes.shokkerize_routes import register_shokkerize_routes
    register_shokkerize_routes(app, logger=logger)
except Exception as _shk_e:  # pragma: no cover - defensive
    logger.warning(f"Shokkerize routes not installed: {_shk_e}")
try:
    from server_routes.photo_livery_routes import register_photo_livery_routes
    register_photo_livery_routes(app, logger=logger)
except Exception as _pl_e:  # pragma: no cover - defensive
    logger.warning(f"Photo Livery routes not installed: {_pl_e}")

# Diagnostics routes need logger + SERVER_DIR + THUMBNAIL_DIR (SPB boot fix 2026-05-17).
from server_routes.diagnostics import register_diagnostics_routes


def _spb_request_count_snapshot():
    with _request_counter_lock:
        return _request_counter


register_diagnostics_routes(
    app,
    engine_getter=lambda: engine,
    version=SPB_VERSION,
    engine_version=SPB_ENGINE_VERSION,
    build_id=SPB_BUILD_ID,
    server_start_time_getter=lambda: _server_start_time,
    gpu_info_func=gpu_info,
    logger=logger,
    render_stats=_render_stats,
    render_stats_lock=_render_stats_lock,
    request_count_getter=_spb_request_count_snapshot,
    recent_renders=_recent_renders,
    recent_renders_lock=_recent_renders_lock,
    recent_errors=_recent_errors,
    recent_errors_lock=_recent_errors_lock,
    server_dir_getter=lambda: SERVER_DIR,
    thumbnail_dir_getter=lambda: THUMBNAIL_DIR,
)

# One-click "Report a Problem" support payload — owns /api/diagnostics and adds
# REDACTED log tails (server_log.txt + server_crashes.log), catalog counts and a
# privacy-safe license boolean. Surfaces the SHOKK THE WORLD per-variant 500 the
# owner can't see (it lives only in the user's local log). The license KEY is
# never read here — only license_status_getter's boolean is surfaced.
from server_routes.diagnostics_report_routes import register_diagnostics_report_routes
register_diagnostics_report_routes(
    app,
    app_root_getter=lambda: SERVER_DIR,
    version=CFG.VERSION,
    engine_version=SPB_ENGINE_VERSION,
    build_id=SPB_BUILD_ID,
    engine_getter=lambda: engine,
    gpu_info_func=gpu_info,
    license_status_getter=lambda: _license_active,
    server_start_time_getter=lambda: _server_start_time,
    server_log_path_getter=lambda: os.path.join(SERVER_DIR, 'server_log.txt'),
    crash_log_path_getter=lambda: os.environ.get('SHOKKER_CRASH_LOG') or os.path.join(SERVER_DIR, 'server_crashes.log'),
    recent_errors_getter=lambda: list(_recent_errors),
    logger=logger,
)
from server_routes.render_monitoring import register_render_monitoring_routes
register_render_monitoring_routes(
    app,
    render_progress=_render_progress,
    render_stats=_render_stats,
    render_stats_lock=_render_stats_lock,
    recent_renders=_recent_renders,
    recent_renders_lock=_recent_renders_lock,
    safe_int=_safe_int,
    gpu_info_func=gpu_info,
    logger=logger,
)

# 2026-04-21 perf fix: werkzeug's built-in request-access logger prints every
# request at INFO level. During a live render the UI polls
# /api/render-status every 2s and /build-check every 5s ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â that's 7-13 stdout
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
        '/spb-prof',
    )
    def filter(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return True
        return not any(p in msg for p in self._SPAMMY)

logging.getLogger('werkzeug').addFilter(_SilencePollEndpoints())


@app.route('/spb-prof', methods=['GET'])
def _spb_profiler_beacon_sink():
    """Acknowledge the temporary UI profiler beacon without a false 404."""
    return ('', 204)

# Log thumbnail dir and warn if missing/empty so user knows to run rebuild_thumbnails.py
def _log_thumbnail_dir():
    if not os.path.isdir(THUMBNAIL_DIR):
        logger_startup.warning(f"Thumbnail dir missing: {THUMBNAIL_DIR} - run: python rebuild_thumbnails.py")
        return
    from server_routes.thumbnail_status import build_thumbnail_inventory
    inventory = build_thumbnail_inventory(THUMBNAIL_DIR, engine)
    if inventory['png_count'] == 0:
        logger_startup.warning(f"Thumbnail dir empty: {THUMBNAIL_DIR} - run: python rebuild_thumbnails.py")
    else:
        logger_startup.info(
            "Thumbnails: %s (%s/%s active catalog PNGs cached; %s use live "
            "fallback; %s legacy extras retained; exact per-category status: "
            "/api/thumbnail-status)",
            THUMBNAIL_DIR,
            inventory['present_total'],
            inventory['expected_total'],
            inventory['missing_count'],
            inventory['stale_count'],
        )
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
    except Exception as _spb_ex:
        _spb_swallow('load_license@L1637', _spb_ex)
    return '', False

def save_license(key, activated):
    """Save license to disk (atomic: temp + os.replace; a crash mid-save cannot truncate it).

    [2026-09-05 codebase-health S3] was a plain open('w') + silent `except: pass`."""
    try:
        from engine.atomic_io import atomic_write_json, file_lock
        with file_lock(LICENSE_FILE):
            atomic_write_json(LICENSE_FILE, {'license_key': key, 'activated': activated, 'timestamp': time.time()}, indent=None)
    except Exception as _ex:
        logger.warning("[license] save failed: %s", _ex)

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
# ================================================================
# CONFIG - persistent user settings (iRacing ID, car paths, etc.)
# ================================================================

_CONFIG_DEFAULTS = {
    "iracing_id": "23371",
    "car_paths": {},
    "live_link_enabled": False,
    "active_car": None,
    "use_custom_number": True,
}


def load_config():
    """Load saved config from shokker_config.json.

    [2026-09-05 codebase-health S3] A corrupt/truncated file is now moved aside as
    shokker_config.json.corrupt-<ts> with a WARNING instead of being silently replaced by
    the defaults on the next save (which used to erase the owner's car_paths)."""
    from engine.atomic_io import load_json_guarded
    data = load_json_guarded(CONFIG_FILE, default=lambda: None, logger=logger, what="shokker_config.json")
    if isinstance(data, dict):
        return data
    return dict(_CONFIG_DEFAULTS, car_paths={})


def save_config(cfg):
    """Save config to shokker_config.json (atomic: temp + os.replace)."""
    from engine.atomic_io import atomic_write_json, file_lock
    with file_lock(CONFIG_FILE):
        atomic_write_json(CONFIG_FILE, cfg, indent=2)

from server_routes.config_routes import register_config_routes
register_config_routes(
    app,
    load_config=load_config,
    save_config=save_config,
    logger=logger,
    config_path=CONFIG_FILE,
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
)


from server_routes.system_status import register_system_status_routes
register_system_status_routes(
    app,
    engine_getter=lambda: engine,
    load_config=load_config,
    license_getter=lambda: (_license_key, _license_active),
    version=SPB_VERSION,
    build_id=SPB_BUILD_ID,
    server_dir_getter=lambda: SERVER_DIR,
    server_start_time_getter=lambda: _server_start_time,
    gpu_info_func=gpu_info,
    logger=logger,
)


def _set_license_state(key, active):
    global _license_key, _license_active
    _license_key = key
    _license_active = active


from server_routes.license_routes import register_license_routes
register_license_routes(
    app,
    license_getter=lambda: (_license_key, _license_active),
    license_setter=_set_license_state,
    validate_license_key=validate_license_key,
    save_license=save_license,
    logger=logger,
    license_path=LICENSE_FILE,
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
)


from server_routes.finish_catalog_routes import id_to_display_name, register_finish_catalog_routes
_finish_catalog_cache = register_finish_catalog_routes(
    app,
    engine_getter=lambda: engine,
    cache_headers=_short_cache_headers,
    logger=logger,
)


from server_routes.thumbnail_status import register_thumbnail_status_routes
register_thumbnail_status_routes(
    app,
    engine_getter=lambda: engine,
    thumbnail_dir_getter=lambda: THUMBNAIL_DIR,
    server_dir_getter=lambda: os.path.dirname(os.path.abspath(__file__)),
    logger=logger,
)


from server_routes.cache_admin_routes import register_cache_admin_routes
register_cache_admin_routes(
    app,
    swatch_cache=_SWATCH_CACHE,
    swatch_cache_lock=_SWATCH_CACHE_LOCK,
    finish_catalog_cache_clear=_finish_catalog_cache['clear'],
    finish_meta_cache_clear=lambda: _finish_meta_cache_clear(),
    psd_cache_getter=lambda: _psd_cache,
    prev_spec_cache_getter=_get_prev_spec_cache,
    prev_spec_cache_setter=_set_prev_spec_cache,
    thumbnail_dir_getter=lambda: THUMBNAIL_DIR,
    validate_thumbnail_regen_request=lambda finish_type, finish_id: _validate_thumbnail_regen_request(finish_type, finish_id),
    queue_thumbnail_regen=lambda finish_type, finish_id: _queue_thumbnail_regen(finish_type, finish_id),
    logger=logger,
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
)


@app.route('/api/spec-pattern-preview/<pattern_id>')
def spec_pattern_preview(pattern_id):
    """Generate a 192x64 3-panel M/R/CC split preview thumbnail for a spec pattern.
    Layout: [M grayscale | R grayscale | CC inverted grayscale] each 64x64, labeled.
    Uses _generate_spec_preview_image() ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â same function as the pre-baker (DRY).
    Kept as fallback for JS onerror handlers when static thumbnail not yet baked."""
    # Support cache-bust via ?v= query param
    bust = request.args.get('v', '')

    try:
        _validate_spec_pattern_preview_request(pattern_id)
    except Exception as e:
        status_code = 404 if isinstance(e, ValueError) and str(e).startswith("Unknown spec pattern") else 500
        logger.warning(f"/api/spec-pattern-preview rejected [{pattern_id}]: {e}")
        return jsonify({
            "error": "spec_pattern_preview_failed",
            "pattern": pattern_id,
            "message": str(e),
        }), status_code

    # Check disk cache first (skip if cache-bust param provided)
    cache_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns')
    cache_path = os.path.join(cache_dir, f'{pattern_id}.png')
    cache_write_denied = _external_write_denial(cache_path, "spec-pattern-preview-cache")
    if not cache_write_denied:
        os.makedirs(cache_dir, exist_ok=True)

    if not bust and _spec_preview_cache_is_current(pattern_id, cache_path):
        return send_file(cache_path, mimetype='image/png')

    # Generate using shared function
    try:
        img = _generate_spec_preview_image(pattern_id)
    except Exception as e:
        logger.warning(f"/api/spec-pattern-preview failed [{pattern_id}]: {e}")
        return jsonify({
            "error": "spec_pattern_preview_failed",
            "pattern": pattern_id,
            "message": str(e),
        }), 500
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    # Save to disk for future static serving
    if not cache_write_denied:
        try:
            img.save(cache_path, 'PNG')
            _mark_spec_preview_cache_current(pattern_id)
        except Exception as _spb_ex:
            _spb_swallow('spec_pattern_preview@L1835', _spb_ex)
    return send_file(buf, mimetype='image/png')


@app.route('/api/spec-pattern-preview-metal/<pattern_id>')
def spec_pattern_preview_metal(pattern_id):
    """Render spec pattern as if applied to a chrome/metallic surface simulation. 128x128.
    Uses _generate_spec_metal_image() ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â same function as the pre-baker (DRY).
    Kept as fallback for JS onerror handlers when static thumbnail not yet baked."""
    bust = request.args.get('v', '')

    try:
        _validate_spec_pattern_preview_request(pattern_id)
    except Exception as e:
        status_code = 404 if isinstance(e, ValueError) and str(e).startswith("Unknown spec pattern") else 500
        logger.warning(f"/api/spec-pattern-preview-metal rejected [{pattern_id}]: {e}")
        return jsonify({
            "error": "spec_pattern_preview_failed",
            "pattern": pattern_id,
            "message": str(e),
        }), status_code

    cache_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns_metal')
    cache_path = os.path.join(cache_dir, f'{pattern_id}.png')
    cache_write_denied = _external_write_denial(cache_path, "spec-pattern-metal-cache")
    if not cache_write_denied:
        os.makedirs(cache_dir, exist_ok=True)

    if not bust and _spec_preview_cache_is_current(pattern_id, cache_path, 'metal'):
        return send_file(cache_path, mimetype='image/png')

    try:
        img = _generate_spec_metal_image(pattern_id)
    except Exception as e:
        logger.warning(f"/api/spec-pattern-preview-metal failed [{pattern_id}]: {e}")
        return jsonify({
            "error": "spec_pattern_preview_failed",
            "pattern": pattern_id,
            "message": str(e),
        }), 500
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    if not cache_write_denied:
        try:
            img.save(cache_path, 'PNG')
            _mark_spec_preview_cache_current(pattern_id, 'metal')
        except Exception as _spb_ex:
            _spb_swallow('spec_pattern_preview_metal@L1883', _spb_ex)
    return send_file(buf, mimetype='image/png')


@app.route('/api/spec-pattern-visual-preview/<pattern_id>')
def spec_pattern_visual_preview(pattern_id):
    """Render a square visual thumbnail for spec-pattern browsing.

    This is intentionally different from /api/spec-pattern-preview/<id>, which
    is a compact M/R/CC diagnostic split. The picker needs the actual pattern
    field shape so painters can recognize Light Leak, Velvet Sheen, etc.
    """
    size = int(_clamp(request.args.get('size', 160), 64, 512))
    bust = request.args.get('v', '')

    try:
        _validate_spec_pattern_preview_request(pattern_id)
    except Exception as e:
        status_code = 404 if isinstance(e, ValueError) and str(e).startswith("Unknown spec pattern") else 500
        logger.warning(f"/api/spec-pattern-visual-preview rejected [{pattern_id}]: {e}")
        return jsonify({
            "error": "spec_pattern_visual_preview_failed",
            "pattern": pattern_id,
            "message": str(e),
        }), status_code

    cache_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns_visual')
    cache_path = os.path.join(cache_dir, f'{pattern_id}_{size}.png')
    cache_write_denied = _external_write_denial(cache_path, "spec-pattern-visual-cache")
    if not cache_write_denied:
        os.makedirs(cache_dir, exist_ok=True)

    # 2026-06-03: was immutable max-age=86400 — that pinned STALE previews in the browser for 24h
    # after a re-bake (honest-preview generator change + pattern rebuilds). no-cache lets the browser
    # revalidate against the content ETag (send_file), so re-baked previews show up immediately (304 when
    # unchanged, 200 when the pattern/generator changed) with no per-change URL versioning.
    _spec_cache_headers = {'Cache-Control': 'no-cache'}
    if not bust and _spec_visual_cache_is_current(pattern_id, size, cache_path):
        resp = send_file(cache_path, mimetype='image/png')
        resp.headers.update(_spec_cache_headers)
        return resp

    try:
        img = _generate_spec_visual_image(pattern_id, size=size)
    except Exception as e:
        logger.warning(f"/api/spec-pattern-visual-preview failed [{pattern_id}]: {e}")
        return jsonify({
            "error": "spec_pattern_visual_preview_failed",
            "pattern": pattern_id,
            "message": str(e),
        }), 500

    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    if not cache_write_denied:
        try:
            img.save(cache_path, 'PNG')
            _mark_spec_visual_cache_current(pattern_id, size)
        except Exception as _spb_ex:
            _spb_swallow('spec_pattern_visual_preview@L1943', _spb_ex)
    resp = send_file(buf, mimetype='image/png')
    resp.headers.update(_spec_cache_headers)
    return resp


@app.route('/api/spec-pattern-combined/<pattern_id>')
def spec_pattern_combined(pattern_id):
    """Render the REAL combined 3-channel spec map for a spec pattern.

    R=Metallic, G=Roughness, B=Clearcoat — the actual on-car material spec the
    engine produces (modern patterns stack [M, R, CC]), NOT a synthetic
    single-field recolor. Used as the RIGHT half of the Spec Overlay split cards
    so painters see the true material colors (red=metallic, etc.).
    """
    size = int(_clamp(request.args.get('size', 160), 64, 512))
    bust = request.args.get('v', '')

    try:
        _validate_spec_pattern_preview_request(pattern_id)
    except Exception as e:
        status_code = 404 if isinstance(e, ValueError) and str(e).startswith("Unknown spec pattern") else 500
        logger.warning(f"/api/spec-pattern-combined rejected [{pattern_id}]: {e}")
        return jsonify({
            "error": "spec_pattern_combined_failed",
            "pattern": pattern_id,
            "message": str(e),
        }), status_code

    cache_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns_combined')
    cache_path = os.path.join(cache_dir, f'{pattern_id}_{size}.png')
    cache_write_denied = _external_write_denial(cache_path, "spec-pattern-combined-cache")
    if not cache_write_denied:
        os.makedirs(cache_dir, exist_ok=True)

    # 2026-06-03: was immutable max-age=86400 — that pinned STALE previews in the browser for 24h
    # after a re-bake (honest-preview generator change + pattern rebuilds). no-cache lets the browser
    # revalidate against the content ETag (send_file), so re-baked previews show up immediately (304 when
    # unchanged, 200 when the pattern/generator changed) with no per-change URL versioning.
    _spec_cache_headers = {'Cache-Control': 'no-cache'}
    if not bust and _spec_combined_cache_is_current(pattern_id, size, cache_path):
        resp = send_file(cache_path, mimetype='image/png')
        resp.headers.update(_spec_cache_headers)
        return resp

    try:
        img = _generate_spec_combined_image(pattern_id, size=size)
    except Exception as e:
        logger.warning(f"/api/spec-pattern-combined failed [{pattern_id}]: {e}")
        return jsonify({
            "error": "spec_pattern_combined_failed",
            "pattern": pattern_id,
            "message": str(e),
        }), 500

    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    if not cache_write_denied:
        try:
            img.save(cache_path, 'PNG')
            _mark_spec_combined_cache_current(pattern_id, size)
        except Exception as _spb_ex:
            _spb_swallow('spec_pattern_combined@L2006', _spb_ex)
    resp = send_file(buf, mimetype='image/png')
    resp.headers.update(_spec_cache_headers)
    return resp


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
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request body"}), 400
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
    for layer_index, layer in enumerate(spec_stack[:5], start=1):
        if not isinstance(layer, dict):
            message = f"Spec preview composite layer {layer_index} must be an object"
            logger.warning(f"/api/spec-preview-composite rejected: {message}")
            return jsonify({
                "error": "spec_preview_composite_failed",
                "layer": layer_index,
                "message": message,
            }), 400
        pid = str(layer.get('pattern', '') or '').strip()
        if not pid:
            continue
        opacity = (layer.get('opacity', 50)) / 100.0
        fn = PATTERN_CATALOG.get(pid)
        if fn is None:
            message = f"Unknown spec pattern in composite preview layer {layer_index}: {pid}"
            logger.warning(f"/api/spec-preview-composite rejected [{pid}]: {message}")
            return jsonify({
                "error": "spec_preview_composite_failed",
                "layer": layer_index,
                "pattern": pid,
                "message": message,
            }), 404
        try:
            pat = fn((H, W), 42, 1.0)
            pat = np.clip(pat, 0, 1).astype(np.float32)
            # 2026-05-26 fix: modern spec patterns return 3-channel (H, W, 3).
            # composite_mod is 2D — collapse pat to 2D (mean over channels)
            # so the blend math works.
            if pat.ndim == 3:
                pat = pat.mean(axis=2)
            # Normal blend: scale by opacity
            composite_mod = composite_mod * (1.0 - opacity) + pat * opacity
        except Exception as ex:
            message = f"Spec preview composite renderer failed in layer {layer_index} [{pid}]: {ex}"
            logger.warning(f"/api/spec-preview-composite failed [{pid}]: {ex}")
            return jsonify({
                "error": "spec_preview_composite_failed",
                "layer": layer_index,
                "pattern": pid,
                "message": message,
            }), 500

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


_psd_cache = {}  # { path: (mtime, PSDImage) }

def _get_cached_psd(psd_path):
    """Get a layered file (PSD or OpenRaster .ora) from cache, or open and cache it.

    [2026-07-04 owner] GIMP/Krita users import via OpenRaster: .ora parses into a
    psd_tools-compatible facade (server_routes/ora_import.py), so every PSD route
    and the booth layer system work identically for both formats.
    """
    mtime = os.path.getmtime(psd_path)
    if psd_path in _psd_cache and _psd_cache[psd_path][0] == mtime:
        return _psd_cache[psd_path][1]
    if psd_path.lower().endswith('.ora'):
        from server_routes.ora_import import OraImage
        psd = OraImage.open(psd_path)
    elif psd_path.lower().endswith('.xcf'):
        # GIMP native format — needs the optional gimpformats package; raises a
        # user-facing XcfSupportMissing message when absent (never a crash).
        from server_routes.xcf_import import XcfImage
        psd = XcfImage.open(psd_path)
    else:
        from psd_tools import PSDImage
        psd = PSDImage.open(psd_path)
    _psd_cache[psd_path] = (mtime, psd)
    # Keep cache small ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â only 3 PSDs max
    if len(_psd_cache) > 3:
        oldest = next(iter(_psd_cache))
        del _psd_cache[oldest]
    return psd


from server_routes.psd_import_routes import register_psd_import_routes
register_psd_import_routes(
    app,
    require_internal_request=_require_spb_internal_request,
    sanitize_path=_sanitize_path,
    get_cached_psd=_get_cached_psd,
    logger=logger,
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
)

# SHOKK FORGE app integration (2026-07-16): keep HTTP/job concerns in small
# modules; geometry and reconstruction remain in versioned _forge_* libraries.
from forge_service import AdapterRegistry, ForgeJobStore, ForgePipeline
from server_routes.forge_routes import register_forge_routes
_forge_adapters = AdapterRegistry(SERVER_DIR)
_forge_jobs_root = os.environ.get('SPB_FORGE_JOBS_ROOT') or os.path.join(OUTPUT_FOLDER, 'forge_jobs')
_forge_job_store = ForgeJobStore(_forge_jobs_root, _forge_adapters)
_forge_pipeline = ForgePipeline(_forge_job_store, _forge_adapters)
register_forge_routes(
    app,
    adapters=_forge_adapters,
    job_store=_forge_job_store,
    pipeline=_forge_pipeline,
    require_internal_request=_require_spb_internal_request,
)

from server_routes.dual_shift_routes import register_dual_shift_routes
register_dual_shift_routes(app, logger=logger)

from server_routes.paint_recolor_support import apply_paint_recolor_impl


def apply_paint_recolor(paint_file, rules, job_dir, mask_rle=None, mask_has_include=False):
    """Apply recolor rules to a paint file, saving a recolored copy.

    Each rule: {"source_rgb": [R,G,B], "target_rgb": [R,G,B], "tolerance": 40, "hue_shift": true}
    Uses HSV hue-shift to preserve shading (dark red -> dark green, etc.)
    Optional mask_rle: RLE-encoded spatial mask (0=unset, 1=include, 2=exclude).
    Returns path to the recolored file.
    """
    return apply_paint_recolor_impl(
        paint_file,
        rules,
        job_dir,
        engine=engine,
        logger=logger,
        decode_spatial_mask_payload=_decode_spatial_mask_payload,
        mask_rle=mask_rle,
        mask_has_include=mask_has_include,
    )

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


from server_routes.pattern_layer_routes import register_pattern_layer_routes
from engine.render import _load_image_pattern
register_pattern_layer_routes(
    app,
    pattern_registry_getter=lambda: engine.PATTERN_REGISTRY,
    load_image_pattern=_load_image_pattern,
    logger=logger,
)


# ================================================================
# SWATCH THUMBNAILS - engine-accurate per-finish rendered patches
# ================================================================

# In-memory swatch cache: cache_key ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ raw PNG bytes
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
        # STABLE per-finish hue (2026-06-27): Python's builtin hash() is SALTED per process
        # (PYTHONHASHSEED), so hash((type,key)) picked a DIFFERENT palette index every launch ->
        # this swatch color changed every run -> picker_split_needs_rebuild saw a color mismatch and
        # RE-BAKED ~741 color-shift/gradient thumbnails on EVERY app start (the "thumbnails bake every
        # launch" bug). hashlib.md5 is process-stable, so the hue (and the cache key) is now fixed.
        import hashlib
        idx = int(hashlib.md5(('%s:%s' % (finish_type, finish_key)).encode()).hexdigest(), 16) % len(_SWATCH_HUE_PALETTE)
        return _SWATCH_HUE_PALETTE[idx]
    return color_hex


# Picker split thumbs: offline snapshots in thumbnails/picker_split/ (see rebuild_picker_swatches.py).
# Runtime serves those small PNGs; on miss uses a fast 64px stitch ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â no launch bake, no swatch_cache bloat.
PICKER_SPLIT_SUBDIR = 'picker_split'
PICKER_SNAPSHOT_SIZE = 48
PICKER_SNAPSHOT_SEED = 42
PICKER_SNAPSHOT_SOURCE_CANVAS = 2048
# [2026-08-01 SPB thumbnail-accuracy fix - owner: "thumbnails must be EXACT REPLICA
# minis of the 2048 canvas"] 0.25 (512px) rendered scale-VARIANT generators with
# features ~4x too big relative to the car. Measured vs full-2048 ground truth
# (_thumb_audit/audit_results.jsonl): sequin_silver SPEC half @512 = SSIM 0.47 /
# MAD 28.4 (nothing like the car); @1024 = SSIM 0.996 / MAD 2.2. ns_indigo_inferno
# paint SSIM 0.971->0.997, spec 0.972->0.995. Per-swatch bake cost 0.3-1.0s ->
# 0.95-1.4s (full 2048 = 2.8-3.8s, over budget). 0.5 = near-identical thumbs.
# NOTE: this constant is hashed into _picker_finish_renderer_hash, so changing it
# auto-invalidates every warm-cache filename, the picker_split manifest hash, and
# every JS ?v= token (full rebake: python rebuild_picker_swatches.py --force).
PICKER_SNAPSHOT_RENDER_SCALE = 0.5  # 1024px - scale-faithful for 48px thumbs (see audit above)

_CATALOG_SWATCH_COLORS = None


def _v5_project_root():
    return os.environ.get('SHOKKER_V5_ROOT') or os.path.dirname(os.path.abspath(__file__))


def _load_catalog_swatch_colors():
    """Parse paint-booth-1-data.js once for per-finish catalog swatch tints."""
    global _CATALOG_SWATCH_COLORS
    if _CATALOG_SWATCH_COLORS is not None:
        return _CATALOG_SWATCH_COLORS
    colors = {}
    import re
    for name in ('paint-booth-1-data.js', 'paint-booth-0-finish-data.js'):
        path = os.path.join(_v5_project_root(), name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
            for m in re.finditer(
                r'\{\s*id\s*:\s*["\']([a-z][a-z0-9_]*)["\'][^}]*?swatch\s*:\s*["\']#?([0-9a-fA-F]{3,8})["\']',
                text,
                re.IGNORECASE | re.DOTALL,
            ):
                fid = m.group(1)
                sw = m.group(2).strip()
                if len(sw) == 3:
                    sw = ''.join(c * 2 for c in sw)
                colors[fid] = sw[:6].lower()
        except Exception as e:
            logger.debug(f"Catalog swatch color parse failed ({path}): {e}")
    _CATALOG_SWATCH_COLORS = colors
    return colors


def _catalog_color_for_picker_swatch(finish_type, finish_key):
    """Catalog tint when known; else deterministic palette / neutral."""
    cat = _load_catalog_swatch_colors()
    if finish_key and finish_key in cat:
        return cat[finish_key]
    return _swatch_display_color(finish_type, finish_key, '888888').replace('#', '')[:6]


def _picker_swatch_catalog_items():
    """All registry finishes shown in the finish picker."""
    items = []
    items.extend(('base', k) for k in engine.BASE_REGISTRY.keys())
    items.extend(('pattern', k) for k in engine.PATTERN_REGISTRY.keys())
    items.extend(('monolithic', k) for k in engine.MONOLITHIC_REGISTRY.keys())
    return items


def _picker_split_safe_key(finish_key):
    return (finish_key or '').replace('/', '_').replace('\\', '_').replace(':', '_').strip() or 'none'


def _picker_split_static_path(finish_type, finish_key):
    """Stable path for a shipped/offline picker snapshot (one PNG per finish)."""
    sub = os.path.join(THUMBNAIL_DIR, PICKER_SPLIT_SUBDIR, finish_type)
    return os.path.join(sub, _picker_split_safe_key(finish_key) + '.png')


def _read_picker_split_png_bytes(static_path, output_size):
    """Load a picker_split snapshot; resize to requested picker width if needed.

    [2026-08-06 owner: "even in the blown up preview you see NO GRIDS"] The
    stored static snapshot is a small PNG (PICKER_SNAPSHOT_SIZE per side).
    Serving it UPSCALED for a big request (hover popout asked for 480 and this
    clamped to 256 then LANCZOS-stretched a 48px file) is how fine detail —
    Synthwave's glowing grid — vanished from the enlarged view. Upscales beyond
    1.5x now REFUSE (raise) so the route falls through to a true live render at
    the requested size (the internal snapshot render is 1024px — real detail).
    """
    import io
    from PIL import Image as PILImage
    out_sz = max(32, min(512, int(output_size)))
    with open(static_path, 'rb') as f:
        raw = f.read()
    if out_sz == PICKER_SNAPSHOT_SIZE:
        return raw
    img = PILImage.open(io.BytesIO(raw)).convert('RGB')
    if img.size[1] * 1.5 < out_sz:
        raise ValueError(
            f"static snapshot {img.size[1]}px cannot honestly serve {out_sz}px request")
    if img.size != (out_sz * 2, out_sz):
        img = img.resize((out_sz * 2, out_sz), PILImage.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _make_temp_catalog_paint_path(r, g, b, size=PICKER_SNAPSHOT_SOURCE_CANVAS):
    """Solid RGB plate for catalog swatch preview (matches zone tint)."""
    from PIL import Image as PILImage
    import tempfile
    def _ch(x):
        return max(0, min(255, int(round(float(x) * 255.0))))

    rgb = (_ch(r), _ch(g), _ch(b))
    img = PILImage.new('RGB', (int(size), int(size)), rgb)
    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    tmp_path = tmp.name
    tmp.close()
    img.save(tmp_path)
    return tmp_path


def _catalog_swatch_zone_for_preview(finish_type, finish_key, r, g, b, canvas_size):  # noqa: E501
    """Single full-canvas zone for picker thumbnails -- mirrors live UI defaults.

    Earlier versions of this builder shipped only ~7 keys, leaving v6 fields
    (overlay bases, gradient stops, spec pattern stacks, blend modes, hue/sat
    adjustments, base color modes, cc_quality) to fall back to engine implicit
    defaults. The live preview always sends ~50 keys, so even the real-engine
    bake path could drift from the live preview for finishes whose default
    state in the UI populates any of those fields. We now seed the zone with
    the same defaults addZone() uses in paint-booth-2-state-zones.js so a
    freshly-picked finish bakes to the same pixels the live preview produces
    on first paint.
    """
    return _catalog_swatch_zone_for_preview_v2(finish_type, finish_key, r, g, b, canvas_size)


def _catalog_swatch_zone_for_preview_legacy(finish_type, finish_key, r, g, b, canvas_size):
    """Single full-canvas zone for picker thumbnails ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â same fields as live preview."""
    import numpy as np
    mono_reg = getattr(engine, 'MONOLITHIC_REGISTRY', {})
    base_reg = getattr(engine, 'BASE_REGISTRY', {})
    zone = {
        "name": "CatalogSwatch",
        "color": [float(r), float(g), float(b)],
        "intensity": 100,
        "base_spec_strength": 1.0,
        "region_mask": np.ones((int(canvas_size), int(canvas_size)), dtype=np.float32),
    }
    if finish_type == 'monolithic':
        zone["finish"] = finish_key
        try:
            from finish_colors_lookup import get_finish_colors
            fc = get_finish_colors(finish_key)
            if fc:
                zone["finish_colors"] = fc
        except Exception as _spb_ex:
            _spb_swallow('_catalog_swatch_zone_for_preview_legacy@L2481', _spb_ex)
    elif finish_type == 'base':
        if finish_key in mono_reg and finish_key not in base_reg:
            zone["finish"] = finish_key
        else:
            zone["base"] = finish_key
            zone["pattern"] = "none"
    elif finish_type == 'pattern':
        zone["base"] = "chrome"
        zone["pattern"] = finish_key
        zone["pattern_scale"] = 1.0
        zone["pattern_strength"] = 1.0
    return zone


def _catalog_swatch_zone_for_preview_v2(finish_type, finish_key, r, g, b, canvas_size):
    """Bake zone that mirrors paint-booth-2-state-zones.js addZone() defaults.

    Explicit > implicit: the engine falls back to these same values when keys
    are missing, but listing them here documents the contract and protects
    against future engine default drift. Closes Divergence 2 from
    THUMBNAIL_BUG_DIAGNOSTIC.md.
    """
    import numpy as np
    mono_reg = getattr(engine, 'MONOLITHIC_REGISTRY', {})
    base_reg = getattr(engine, 'BASE_REGISTRY', {})
    zone = {
        "name": "CatalogSwatch",
        "color": [float(r), float(g), float(b)],
        "intensity": 100,
        # Base-channel defaults (mirrors addZone)
        "base_strength": 1.0,
        "base_spec_strength": 1.0,
        "base_color_mode": "source",
        "base_color": [1.0, 1.0, 1.0],
        "base_color_strength": 1.0,
        "base_color_scale": 1.0,
        "base_color_rotation": 0,
        "base_color_fit_zone": False,
        "base_offset_x": 0.5,
        "base_offset_y": 0.5,
        "base_rotation": 0,
        "base_flip_h": False,
        "base_flip_v": False,
        "base_hue_offset": 0,
        "base_saturation_adjust": 0,
        "base_brightness_adjust": 0,
        # Pattern-channel defaults
        "pattern_opacity": 1.0,
        "pattern_offset_x": 0.5,
        "pattern_offset_y": 0.5,
        "pattern_flip_h": False,
        "pattern_flip_v": False,
        # Spec / overlay stacks default to empty (engine treats missing same way)
        "spec_pattern_stack": [],
        "overlay_spec_pattern_stack": [],
        "third_overlay_spec_pattern_stack": [],
        "fourth_overlay_spec_pattern_stack": [],
        "fifth_overlay_spec_pattern_stack": [],
        # Render hygiene: omit cc_quality so engine uses its own default
        # (live UI only sends cc_quality when user has changed it from 100%).
        "region_mask": np.ones((int(canvas_size), int(canvas_size)), dtype=np.float32),
        # Bake plate is flat gray, so the engine's zone-color match (which treats
        # color=[r,g,b] as a list of color selectors) finds 0 matching pixels and
        # skips the zone. Tell it to use the region_mask shape directly.
        "apply_area_shape_only": True,
    }
    if finish_type == 'monolithic':
        zone["finish"] = finish_key
        # [2026-08-16 owner: "MANY of the finishes... have NO DETAILS" in the click-to-enlarge]
        # Same disease the BASE branch was cured of on 2026-08-06, one branch over: this bake
        # zone defaults base_color_mode='source', and since the SOURCE-MODE PARITY fix
        # (shokker_engine_v2, 2026-08-15) monolithics HONOR source mode — paint reverts to the
        # flat catalog plate, so every monolithic's live-rendered big preview (the >=512px
        # fallback when the baked snapshot can't honestly serve the size) showed a gray slab
        # beside a correct spec. The card must advertise the finish's AUTHORED paint: the same
        # sentinel dodges the source lock (paint_fn runs) and no-ops in
        # _apply_base_color_override (unknown mode -> paint untouched).
        zone["base_color_mode"] = "authored_swatch"
        try:
            from finish_colors_lookup import get_finish_colors
            fc = get_finish_colors(finish_key)
            if fc:
                zone["finish_colors"] = fc
        except Exception as _spb_ex:
            _spb_swallow('_catalog_swatch_zone_for_preview_v2@L2566', _spb_ex)
    elif finish_type == 'base':
        if finish_key in mono_reg and finish_key not in base_reg:
            zone["finish"] = finish_key
            # [2026-08-16] mono-registered id arriving as type 'base' — same sentinel as above.
            zone["base_color_mode"] = "authored_swatch"
        else:
            zone["base"] = finish_key
            zone["pattern"] = "none"
            # [2026-08-06 owner: thumbnails "do not always accurately represent
            # the paints. AT ALL" — MARPAT flat olive, all of Groovy Vibes flat]
            # The 2026-07-08 source-mode law (compose.py _source_paint_lock)
            # correctly skips the base paint pass on the CAR when
            # base_color_mode='source' — but this bake zone mirrors that
            # default, so every authored-paint base (camo, tie-dye, lava lamp)
            # thumbnailed as a flat tint plate. The card must advertise the
            # finish's AUTHORED look: use a sentinel mode that fails the lock's
            # membership test (paint_fn runs) and no-ops in
            # _apply_base_color_override (unknown mode -> paint returned
            # untouched). Bases with a noop paint_fn keep 'source' — their
            # honest look IS the tinted plate + spec.
            try:
                _b_entry = base_reg.get(finish_key) or {}
                _b_paint_fn = _b_entry.get('paint_fn') if isinstance(_b_entry, dict) else None
                if _b_paint_fn is not None and not engine._base_paint_fn_is_noop(_b_paint_fn):
                    zone["base_color_mode"] = "authored_swatch"
            except Exception as _spb_ex:
                _spb_swallow('_catalog_swatch_zone_for_preview_v2@L2593', _spb_ex)
    elif finish_type == 'pattern':
        zone["base"] = "chrome"
        zone["pattern"] = finish_key
        zone["pattern_scale"] = 1.0
        zone["pattern_strength"] = 1.0
        zone["pattern_rotation"] = 0
    return zone


def _render_fast_split_swatch_bytes(finish_type, finish_key, color_hex, output_size, seed):
    """Fast runtime fallback when no offline picker_split snapshot exists (~64px stitch)."""
    import io as _io
    import numpy as _np
    from PIL import Image as PILImage
    size = max(32, min(256, int(output_size)))
    png_left = _render_swatch_bytes(finish_type, finish_key, color_hex, size, seed)
    png_right = _render_spec_swatch_bytes(finish_type, finish_key, size, seed)
    img_l = PILImage.open(_io.BytesIO(png_left)).convert('RGB')
    img_r = PILImage.open(_io.BytesIO(png_right)).convert('RGB')
    combined = PILImage.new('RGB', (size * 2, size))
    combined.paste(img_l, (0, 0))
    combined.paste(img_r, (size, 0))
    arr = _np.array(combined)
    arr[:, size - 1, :] = [20, 20, 20]
    arr[:, size, :] = [20, 20, 20]
    buf = _io.BytesIO()
    PILImage.fromarray(arr).save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _pattern_picker_override_tile(finish_key, w, h):
    """The authored RGB artwork shared by the picker and Overlay/Blend paint modes.

    SPB-105 color routing tick3 (2026-09-07): the old picker-only art route
    promised color that the paint renderer discarded. Both now resolve the
    same source; existing artwork and spec callbacks are unchanged.
    """
    try:
        import numpy as _np
        from PIL import Image as _PImg
        from engine.pattern_artwork import picker_pattern_artwork
        path = picker_pattern_artwork(finish_key)
        if not path:
            from engine.registry import PATTERN_REGISTRY
            from engine.pattern_paint_placement import composite_pattern_layer
            entry = PATTERN_REGISTRY.get(finish_key, {})
            authored = entry.get('_spb_authored_paint_fn')
            if callable(authored):
                source = _np.full((int(h), int(w), 3), .5, _np.float32)
                paint = composite_pattern_layer(authored, source, (int(h), int(w)),
                    _np.ones((int(h), int(w)), _np.float32), 42,
                    texture_fn=entry.get('_spb_authored_texture_fn'))
                return _np.uint8(_np.clip(paint, 0, 1) * 255)
            return None
        im = _PImg.open(path).convert('RGB').resize((int(w), int(h)), _PImg.LANCZOS)
        return _np.asarray(im)
    except Exception:
        return None


def _render_picker_split_snapshot_bytes(finish_type, finish_key, color_hex, output_size, seed):
    """Offline snapshot bake only (rebuild_picker_swatches.py): preview_render then downscale."""
    import io
    import numpy as np
    from PIL import Image as PILImage

    # [SPB-PATTERN-PICKER fix 2026-06-06] The picker grid requests color=888888 for EVERY
    # pattern; texture_fn patterns that lack a baked override tile then render gray-on-gray
    # (the original bug: ~200 of 410 texture patterns showed on gray). Map neutral
    # (888888/555577/446688) -> deterministic saturated per-finish hue, exactly like the
    # non-split render_swatch_bytes path already does, so the pattern art is visible.
    # No-op for any explicit user color and for catalog tints (e.g. pf_ 888899) -> safe,
    # picker-swatch-only (never affects in-car render). Override-covered patterns still get
    # their tile painted over the left half afterward, so they are unaffected.
    color_hex = _swatch_display_color(finish_type, finish_key, color_hex)
    try:
        hx = (color_hex or '888888').lstrip('#').ljust(6, '0')[:6]
        r = int(hx[0:2], 16) / 255.0
        g = int(hx[2:4], 16) / 255.0
        b = int(hx[4:6], 16) / 255.0
    except Exception:
        r, g, b = 0.533, 0.533, 0.533

    canvas = PICKER_SNAPSHOT_SOURCE_CANVAS
    paint_path = _make_temp_catalog_paint_path(r, g, b, canvas)
    zone = _catalog_swatch_zone_for_preview(finish_type, finish_key, r, g, b, canvas)
    try:
        paint_rgb, spec_rgba, _elapsed = engine.preview_render(
            paint_path, [zone], seed=int(seed),
            preview_scale=PICKER_SNAPSHOT_RENDER_SCALE,
        )
    finally:
        try:
            os.unlink(paint_path)
        except Exception as _spb_ex:
            _spb_swallow('_render_picker_split_snapshot_bytes@L2690', _spb_ex)

    if paint_rgb is None or not hasattr(paint_rgb, 'size') or paint_rgb.size == 0:
        raise RuntimeError(f"Faithful swatch produced empty paint [{finish_type}/{finish_key}]")

    if paint_rgb.dtype != np.uint8:
        paint_rgb = np.clip(paint_rgb, 0, 255).astype(np.uint8)
    if paint_rgb.ndim == 2:
        paint_rgb = np.stack([paint_rgb] * 3, axis=-1)
    elif paint_rgb.shape[-1] > 3:
        paint_rgb = paint_rgb[:, :, :3]

    spec_norm = _spec_array_to_rgba_uint8(spec_rgba)
    h, w = int(paint_rgb.shape[0]), int(paint_rgb.shape[1])
    # SPB-105 color routing tick3: the paint half and actual Overlay/Blend layer
    # share authored artwork (or the retained authored procedural color callback).
    if finish_type == 'pattern':
        _ov_tile = _pattern_picker_override_tile(finish_key, w, h)
        if _ov_tile is not None:
            paint_rgb = _ov_tile
    if spec_norm is not None and (spec_norm.shape[0] != h or spec_norm.shape[1] != w):
        from PIL import Image as _PILImage
        spec_img = _PILImage.fromarray(spec_norm[:, :, :3])
        spec_img = spec_img.resize((w, h), _PILImage.LANCZOS)
        right = np.array(spec_img)
    elif spec_norm is not None:
        right = spec_norm[:, :, :3]
    else:
        right = np.zeros((h, w, 3), dtype=np.uint8)

    # [SPB-SWATCH-TRUTH 2026-08-06 — owner: "the SPEC side is LYING ... many of them
    # are just dead wrong"] The right half is LABELLED "SPEC" in the picker, so it must
    # ALWAYS be the compiled spec (RGB = M / Roughness / Cc). Nothing else may be drawn
    # there.
    #
    # What went wrong: the 2026-08-03 OPALFIRE ramp pass replaced the spec half with a
    # 2x zoom crop OF THE PAINT whenever the spec was uniform (per-channel std < 3),
    # reasoning that a flat half-square "carries zero information". But FLAT SPEC IS
    # EXACTLY WHAT A FOUNDATION BASE IS — gloss/matte/satin/flat_black have constant
    # M/R/Cc by definition — so the entire Foundation category silently showed
    # paint-on-both-sides under a SPEC label. Measured on the live route before this
    # fix: gloss/matte/flat_black/satin had left half == right half exactly, while
    # chrome (245.6, 5.2, 16.0 — its true R255/G0/B16) and brushed_metal_fine kept a
    # genuine split, which is why only "many" and not all of them looked wrong.
    #
    # A uniform spec square is not information-free: its colour IS the finish's
    # M/R/Cc triple, which is the single most useful thing to know about a foundation
    # base. Truthfulness beats visual density here — the owner set that rule directly.
    combined = PILImage.new('RGB', (w * 2, h))
    combined.paste(PILImage.fromarray(paint_rgb), (0, 0))
    combined.paste(PILImage.fromarray(right), (w, 0))
    arr = np.array(combined)
    arr[:, w - 1, :] = [20, 20, 20]
    arr[:, w, :] = [20, 20, 20]
    # [2026-08-06] 512 ceiling (was 256): the big click-to-enlarge preview asks
    # for 512/side, which is the render's native 1024px halved — true detail.
    out_sz = max(32, min(512, int(output_size)))
    if arr.shape[0] != out_sz or arr.shape[1] != out_sz * 2:
        # [2026-08-01 SPB thumbnail-accuracy fix] cv2.INTER_AREA (box average) for the
        # final shrink: at ~21:1 (1024 -> 48) it integrates high-frequency spec/flake
        # energy honestly; LANCZOS ringing exaggerated sparkle contrast on fine specs.
        import cv2 as _cv2
        interp = _cv2.INTER_AREA if out_sz < arr.shape[0] else _cv2.INTER_LANCZOS4
        arr = _cv2.resize(arr, (out_sz * 2, out_sz), interpolation=interp)
    combined = PILImage.fromarray(arr)
    buf = io.BytesIO()
    combined.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _picker_split_manifest_path():
    return os.path.join(THUMBNAIL_DIR, PICKER_SPLIT_SUBDIR, '_manifest.json')


def _load_picker_split_manifest():
    path = _picker_split_manifest_path()
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as _spb_ex:
            _spb_swallow('_load_picker_split_manifest@L2772', _spb_ex)
    return {
        'version': 2,
        'render_scale': PICKER_SNAPSHOT_RENDER_SCALE,
        'output_size': PICKER_SNAPSHOT_SIZE,
        'finishes': {},
    }


def _save_picker_split_manifest(manifest):
    path = _picker_split_manifest_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # ATOMIC write (2026-06-27): the picker manifest is the record of which thumbnails are already
    # baked. The old plain open('w')+dump TRUNCATES the file the instant it opens — so a baker killed
    # mid-write (app closed during the 25s boot-warm) or two bakers racing left a truncated/empty
    # manifest. _load_picker_split_manifest then returns finishes:{} -> EVERY finish "needs rebuild"
    # -> the whole catalog re-bakes on the next start ("thumbnails bake every launch"). Write to a
    # temp file in the same dir, then os.replace() — an atomic rename, so the live manifest is only
    # ever the previous-complete or the new-complete file, never a half-written one.
    tmp = "%s.tmp.%d" % (path, os.getpid())
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception as _spb_ex:
            _spb_swallow('_save_picker_split_manifest@L2801', _spb_ex)


# [2026-06-12 thumbnail-cache fix] per-request bytecode hashing was repeated
# for every swatch request (hundreds per picker open). Memoized on the
# REGISTRY ENTRY IDENTITY so rework hooks that swap an entry invalidate the
# memo naturally; engine code can't change within a process otherwise.
_PICKER_RENDERER_HASH_MEMO = {}
_PICKER_ENGINE_READY = False

# SPB-WILDS tick 3 buyer-facing cache regression (2026-08-23), owner verdict:
# "Must be VERY UNIQUE." A shared-kit mutation changed Bloom paint/spec byte
# hashes while the picker renderer hash stayed e0ad94ce3f5a -> e0ad94ce3f5a,
# allowing prefer=live to serve an old exact/static card before live rendering.
# Shared renderer factories can keep the same returned wrapper source while a
# helper elsewhere in their module changes every generated pixel. Keep this
# list deliberately narrow: module digests are correct for genuinely shared
# renderer kits, but would make unrelated edits invalidate broad picker groups.
_PICKER_RENDERER_SHARED_DEPENDENCY_MODULES = frozenset({
    'engine.expansions.fractured_wilds_microkit_2026',
    'engine.expansions.fractured_wilds_signatures_2026',
    # SPB-GRADIENT-OVERHAUL-2026-08-23 / G-6: all 166 recipes close over
    # factory wrappers in this module. Bytecode-only hashing missed helper and
    # palette changes, leaving 11 showcase + 10 material buyer cards stale.
    'engine.expansions.gradient_overhaul_2026',
})
_PICKER_RENDERER_MODULE_HASH_MEMO = {}
# 2026-09-02 owner: "I don't think the DARK CITY is rebaking thumbnails."
# These shelves are DATA-DRIVEN: every finish's paint_fn/spec_fn is the same
# `_mk(fid)` closure, so its source hash never changes; the finish itself lives
# in design tables, deck tables and shared kits. Fold those files' on-disk
# hashes into the picker key so an edit to any of them re-bakes the thumbnail.
_SPB_SPEC_STACK = ('engine.paint_v2.spec_story', 'engine.paint_v2.spec_cards',
                   'engine.expansions.nightshift_forms_2026', 'engine.paint_v2.era_kit_2026')
_PICKER_RENDERER_MODULE_DEPS = {
    'engine.expansions.gradient_overhaul_2026': ('engine.expansions.gradient_designs_2026',),
    'engine.expansions.dark_city_2026': ('engine.expansions.dark_city_2026',
                                         'engine.expansions.fractured_flames_kit_2026') + _SPB_SPEC_STACK,
    'engine.expansions.paradigm_2026': ('engine.expansions.paradigm_2026', 'engine.expansions.paradigm_design_2026',
                                        'engine.expansions.paradigm_decks_2026') + _SPB_SPEC_STACK,
    'engine.expansions.world_of_color_2026': ('engine.expansions.world_of_color_2026', 'engine.expansions.woc_design_2026',
                                              'engine.expansions.woc_decks_2026',
                                              'engine.expansions.world_of_color_kit_2026') + _SPB_SPEC_STACK,
    'engine.expansions.fractured_flames_2026': ('engine.expansions.fractured_flames_2026', 'engine.expansions.flames_design_2026',
                                                'engine.expansions.flames_decks_2026',
                                                'engine.expansions.fractured_flames_kit_2026') + _SPB_SPEC_STACK,
    'engine.expansions.fable_2026': ('engine.expansions.fable_2026',
                                     'engine.expansions.fractured_flames_kit_2026') + _SPB_SPEC_STACK,
    'engine.expansions.fractured_nightshift_2026': ('engine.expansions.fractured_nightshift_2026',
                                                    'engine.expansions.nightshift_design_2026') + _SPB_SPEC_STACK,
    'engine.expansions.fractured_elements_2026': ('engine.expansions.fractured_elements_2026',
                                                  'engine.expansions.elements_design_2026') + _SPB_SPEC_STACK,
    'engine.paint_v2.era_base_2026': ('engine.paint_v2.era_base_2026', 'engine.paint_v2.era_authored_decks_2026',
                                      'engine.paint_v2.era_1990s_2026', 'engine.paint_v2.era_1980s_2026',
                                      'engine.paint_v2.era_1970s_2026', 'engine.paint_v2.cyberpunk_2026',
                                      'engine.paint_v2.tactical_2026') + _SPB_SPEC_STACK,
}


def _picker_renderer_module_hash(module_name):
    """Fingerprint an allowlisted shared renderer module's on-disk source."""
    hit = _PICKER_RENDERER_MODULE_HASH_MEMO.get(module_name)
    if hit is not None:
        return hit
    try:
        module = sys.modules.get(module_name) or __import__(module_name, fromlist=['*'])
        path = getattr(module, '__file__', None)
        if not path:
            return None
        with open(path, 'rb') as source_file:
            result = hashlib.md5(source_file.read()).hexdigest()[:12]
        _PICKER_RENDERER_MODULE_HASH_MEMO[module_name] = result
        return result
    except Exception:
        return None


def _append_picker_renderer_fn_hash(parts, fn):
    parts.append(_get_fn_hash(fn))
    module_name = getattr(fn, '__module__', '')
    if module_name in _PICKER_RENDERER_SHARED_DEPENDENCY_MODULES:
        dependency_hash = _picker_renderer_module_hash(module_name)
        if dependency_hash:
            parts.append(f'module:{module_name}:{dependency_hash}')
    for dependency_module_name in _PICKER_RENDERER_MODULE_DEPS.get(module_name, ()):
        dependency_hash = _picker_renderer_module_hash(dependency_module_name)
        if dependency_hash:
            parts.append(f'module:{dependency_module_name}:{dependency_hash}')
    # SPB-GRADIENT-MATH-2026-08-23 / GM-2: factory wrappers can depend on
    # transitive renderer modules whose edits must invalidate picker caches.
    for dependency_module_name in getattr(fn, '_spb_picker_dependency_modules', ()):
        dependency_hash = _picker_renderer_module_hash(dependency_module_name)
        if dependency_hash:
            parts.append(f'module:{dependency_module_name}:{dependency_hash}')


def _picker_finish_renderer_hash(finish_type, finish_key):
    """Fingerprint finish renderer code + bake settings for incremental rebuilds."""
    import hashlib
    # Lazy first-render wiring replaces base callbacks. Finalize that wiring
    # BEFORE fingerprinting, without rendering an image. Offline/live agree.
    global _PICKER_ENGINE_READY
    if not _PICKER_ENGINE_READY:
        ensure = getattr(engine, '_ensure_expansions_loaded', None)
        if callable(ensure):
            ensure()
        getattr(engine, 'preview_render', None)
        _PICKER_ENGINE_READY = True
    _reg_for_memo = {
        'monolithic': getattr(engine, 'MONOLITHIC_REGISTRY', {}),
        'base': getattr(engine, 'BASE_REGISTRY', {}),
        'pattern': getattr(engine, 'PATTERN_REGISTRY', {}),
    }.get(finish_type, {})
    _entry_for_memo = _reg_for_memo.get(finish_key)
    # Owner 2026-10-02: final registry wiring can replace callbacks/material
    # values IN PLACE. Dict identity alone then serves the pre-wiring hash.
    if isinstance(_entry_for_memo, dict):
        _memo_state = tuple(id(_entry_for_memo.get(k)) for k in
                            ('paint_fn', 'base_spec_fn', 'spec_fn', 'texture_fn')) + tuple(
            str(_entry_for_memo.get(k)) for k in ('M', 'R', 'CC', 'image_path'))
    elif isinstance(_entry_for_memo, (tuple, list)):
        _memo_state = tuple(id(fn) for fn in _entry_for_memo[:2])
    else:
        _memo_state = ()
    _memo_key = (finish_type, finish_key, id(_entry_for_memo), _memo_state)
    _hit = _PICKER_RENDERER_HASH_MEMO.get(_memo_key)
    if _hit is not None:
        return _hit
    parts = [
        str(PICKER_SNAPSHOT_RENDER_SCALE),
        str(PICKER_SNAPSHOT_SOURCE_CANVAS),
        str(PICKER_SNAPSHOT_SIZE),
        # [2026-08-06] bake-zone version salt: the zone builder now renders
        # authored base paint (see _catalog_swatch_zone_for_preview_v2).
        # Bumping this invalidates every cached split swatch so the flat
        # pre-fix thumbnails cannot keep serving from disk.
        'bakezone-authoredpaint-1',
        # [SPB-SWATCH-TRUTH 2026-08-06] the SPEC half is now ALWAYS the compiled
        # spec — the uniform-spec branch used to substitute a paint zoom, which
        # made every flat Foundation base (gloss/matte/satin/flat_black) show
        # paint on both sides under a SPEC label. Salt bumped so the lying
        # thumbnails cannot keep serving from disk.
        'spechalf-truth-1',
    ]
    mono_reg = getattr(engine, 'MONOLITHIC_REGISTRY', {})
    base_reg = getattr(engine, 'BASE_REGISTRY', {})
    pattern_reg = getattr(engine, 'PATTERN_REGISTRY', {})

    if finish_type == 'monolithic' and finish_key in mono_reg:
        entry = mono_reg[finish_key]
        if isinstance(entry, (tuple, list)):
            for fn in entry[:2]:
                if callable(fn):
                    _append_picker_renderer_fn_hash(parts, fn)
        elif isinstance(entry, dict):
            for key in ('spec_fn', 'paint_fn'):
                fn = entry.get(key)
                if callable(fn):
                    _append_picker_renderer_fn_hash(parts, fn)
    elif finish_type == 'base' and finish_key in base_reg:
        entry = base_reg[finish_key]
        if isinstance(entry, dict):
            for key in ('paint_fn', 'base_spec_fn'):
                fn = entry.get(key)
                if callable(fn):
                    _append_picker_renderer_fn_hash(parts, fn)
            parts.append(f"M{entry.get('M')}R{entry.get('R')}CC{entry.get('CC')}")
    elif finish_type == 'pattern' and finish_key in pattern_reg:
        entry = pattern_reg[finish_key]
        if isinstance(entry, dict):
            for key in ('texture_fn', 'paint_fn'):
                fn = entry.get(key)
                if callable(fn):
                    _append_picker_renderer_fn_hash(parts, fn)
            parts.append(str(entry.get('image_path') or ''))
            # Match the picker color registry even before expansion initialization.
            from engine.registry import PATTERN_REGISTRY as _authored_pattern_registry
            authored = _authored_pattern_registry.get(finish_key, {}).get('_spb_authored_paint_fn')
            if callable(authored) and not getattr(engine, '_SPB_REGULAR_IMAGE_OVERRIDES', {}).get(finish_key):
                parts.append('pattern-authored-color-20260907')
                _append_picker_renderer_fn_hash(parts, authored)

    try:
        from finish_colors_lookup import get_finish_colors
        fc = get_finish_colors(finish_key)
        if fc:
            parts.append(hashlib.md5(
                json.dumps(fc, sort_keys=True, default=str).encode()
            ).hexdigest()[:12])
    except Exception as _spb_ex:
        _spb_swallow('_picker_finish_renderer_hash@L2965', _spb_ex)

    _result = hashlib.md5('|'.join(parts).encode()).hexdigest()[:12]
    if len(_PICKER_RENDERER_HASH_MEMO) > 8000:
        _PICKER_RENDERER_HASH_MEMO.clear()
    _PICKER_RENDERER_HASH_MEMO[_memo_key] = _result
    return _result


def picker_split_needs_rebuild(finish_type, finish_key, force=False):
    """True when snapshot missing or finish renderer / catalog tint changed."""
    if force:
        return True
    if not os.path.isfile(_picker_split_static_path(finish_type, finish_key)):
        return True
    manifest = _load_picker_split_manifest()
    entry = manifest.get('finishes', {}).get(f'{finish_type}:{finish_key}', {})
    color_hex = _catalog_color_for_picker_swatch(finish_type, finish_key)
    if entry.get('color_hex') != color_hex:
        return True
    if entry.get('hash') != _picker_finish_renderer_hash(finish_type, finish_key):
        return True
    if entry.get('render_scale') != PICKER_SNAPSHOT_RENDER_SCALE:
        return True
    return False


def _require_wilds_picker_write_quality(items, manifest_path=None):
    """Central fail-closed guard shared by CLI, API, and background writers."""
    # SPB-105 / owner Wilds rebuild, 2026-08-26: the owner explicitly requested
    # usable picker previews for the independently M7/collision/distinctness-
    # gated experimental overrides while the separate 110/110 visual-review
    # manifest is deliberately still incomplete.  Permit only a one-shot CLI
    # bake when every selected Wilds ID is in the provenance-audited independent
    # override ledger.  This never opens the legacy fallback IDs, API writes, or
    # the all-110 release path; unset env retains the original fail-closed guard.
    if os.environ.get("SPB_ALLOW_EXPERIMENTAL_WILDS_THUMBNAILS") == "1":
        try:
            from scripts.spb_wilds_110_provenance_audit import INDEPENDENT_OVERRIDES
            _lanes, _wilds_ids = __import__(
                "scripts.spb_wilds_release_gate", fromlist=["declared_wilds_110"]
            ).declared_wilds_110()
            _wilds_set = set(_wilds_ids)
            _targeted = {
                key for finish_type, key in items
                if finish_type == "monolithic" and key in _wilds_set
            }
            if _targeted and _targeted.issubset(INDEPENDENT_OVERRIDES):
                return {"experimental_override_picker_bake": sorted(_targeted)}
        except Exception as _spb_ex:
            # Any inability to prove the ledger falls through to the original lock.
            _spb_swallow('_require_wilds_picker_write_quality@L3015', _spb_ex)
    from scripts.spb_wilds_release_gate import require_wilds_quality_release_for_items

    return require_wilds_quality_release_for_items(
        items,
        manifest_path=manifest_path,
        registry=engine.MONOLITHIC_REGISTRY,
    )


def _save_picker_split_snapshot_unchecked(finish_type, finish_key, color_hex=None, output_size=PICKER_SNAPSHOT_SIZE, seed=PICKER_SNAPSHOT_SEED):
    """Internal writer; callers must have passed the central Wilds guard."""
    color_hex = (color_hex or _catalog_color_for_picker_swatch(finish_type, finish_key)).replace('#', '')[:6]
    png = _render_picker_split_snapshot_bytes(finish_type, finish_key, color_hex, output_size, seed)
    path = _picker_split_static_path(finish_type, finish_key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as df:
        df.write(png)
    manifest = _load_picker_split_manifest()
    manifest.setdefault('finishes', {})[f'{finish_type}:{finish_key}'] = {
        'hash': _picker_finish_renderer_hash(finish_type, finish_key),
        'color_hex': color_hex,
        'generated': datetime.utcnow().isoformat(),
        'render_scale': PICKER_SNAPSHOT_RENDER_SCALE,
    }
    manifest['render_scale'] = PICKER_SNAPSHOT_RENDER_SCALE
    manifest['output_size'] = output_size
    manifest['updated'] = datetime.utcnow().isoformat()
    _save_picker_split_manifest(manifest)
    return path


def save_picker_split_snapshot(finish_type, finish_key, color_hex=None, output_size=PICKER_SNAPSHOT_SIZE, seed=PICKER_SNAPSHOT_SEED):
    """Write a picker snapshot only after the central Wilds quality guard."""
    _require_wilds_picker_write_quality([(finish_type, finish_key)])
    return _save_picker_split_snapshot_unchecked(
        finish_type, finish_key, color_hex, output_size, seed,
    )


def bake_picker_split_batch(
    items, force=False, on_progress=None, wilds_quality_manifest=None,
):
    """Bake many picker snapshots; skips up-to-date entries unless force=True."""
    _require_wilds_picker_write_quality(items, manifest_path=wilds_quality_manifest)
    baked = skipped = errors = 0
    total = len(items)
    for i, (finish_type, finish_key) in enumerate(items):
        if not picker_split_needs_rebuild(finish_type, finish_key, force=force):
            skipped += 1
            if on_progress:
                on_progress(finish_type, finish_key, 'skip', i + 1, total)
            continue
        try:
            path = _save_picker_split_snapshot_unchecked(finish_type, finish_key)
            baked += 1
            if on_progress:
                on_progress(finish_type, finish_key, 'ok', i + 1, total, path)
        except Exception as e:
            errors += 1
            logger.debug(f"Picker snapshot bake failed [{finish_type}/{finish_key}]: {e}")
            if on_progress:
                on_progress(finish_type, finish_key, 'fail', i + 1, total, str(e))
    return baked, skipped, errors


def _swatch_split_cache_safe_key(*parts):
    """Mirror swatch_routes._safe_swatch_key so warmed files match the live route."""
    return "_".join(str(part or "") for part in parts).replace('/', '_').replace('\\', '_').replace(':', '_')


def _picker_split_warm_cache_path(finish_type, finish_key, color_hex, size, split_hash):
    """Exact disk path the prefer=live split route reads/writes (swatch_routes.py).

    The picker/library request /api/swatch/<type>/<key>?...&mode=split&prefer=live,
    which makes the route SKIP the static thumbnails/picker_split/ PNGs and instead
    hit thumbnails/swatch_cache/picker_split/{type}_{key}_{color}_{size}_{hash}.png.
    Pre-writing that exact file turns every picker thumbnail into a guaranteed cache
    HIT (instant), with byte-identical pixels to the live render (same render fn).
    """
    split_cache_dir = os.path.join(THUMBNAIL_DIR, 'swatch_cache', 'picker_split')
    name = _swatch_split_cache_safe_key(finish_type, finish_key, color_hex, size, split_hash) + '.png'
    return os.path.join(split_cache_dir, name)


def warm_picker_split_swatch_cache(items_with_color, size=PICKER_SNAPSHOT_SIZE,
                                   seed=PICKER_SNAPSHOT_SEED, force=False, on_progress=None,
                                   wilds_quality_manifest=None):
    """Pre-render the exact per-color split PNGs the prefer=live picker route serves.

    items_with_color: iterable of (finish_type, finish_key, color_hex) where color_hex
    is the SAME tint the JS picker sends (the finish's item.swatch, lowercased 6-hex).
    Writes thumbnails/swatch_cache/picker_split/{type}_{key}_{color}_{size}_{hash}.png so
    the first open of the picker / finish library is a cold-cache-free instant hit.
    """
    baked = skipped = errors = 0
    items_with_color = list(items_with_color)
    _require_wilds_picker_write_quality(
        [
            (finish_type, finish_key)
            for finish_type, finish_key, _color_hex in items_with_color
        ],
        manifest_path=wilds_quality_manifest,
    )
    total = len(items_with_color)
    mono_reg = getattr(engine, 'MONOLITHIC_REGISTRY', {})
    base_reg = getattr(engine, 'BASE_REGISTRY', {})
    pattern_reg = getattr(engine, 'PATTERN_REGISTRY', {})
    for i, (finish_type, finish_key, color_hex) in enumerate(items_with_color):
        # [2026-06-12 preview-deadlock fix] NEVER fight the painter: while the
        # booth is actively previewing/rendering (heartbeat fresher than 20s),
        # pause the bake loop entirely. Works cross-process (boot warm is a
        # detached subprocess) via the heartbeat file's mtime.
        try:
            while (os.path.isfile(_USER_ACTIVE_HEARTBEAT)
                   and (time.time() - os.path.getmtime(_USER_ACTIVE_HEARTBEAT)) < 20.0):
                time.sleep(2.0)
        except Exception as _spb_ex:
            _spb_swallow('warm_picker_split_swatch_cache@L3134', _spb_ex)
        # Mirror the route's request-color normalization (no lowercasing there; the JS
        # always sends lowercase, so we lowercase defensively to match its output).
        col = (color_hex or '888888').lstrip('#').lower().ljust(6, '0')[:6]
        # Skip ids the route would 404 on so we never poison the cache with errors.
        valid = (
            (finish_type == 'base' and (finish_key in base_reg or finish_key in mono_reg)) or
            (finish_type == 'pattern' and finish_key in pattern_reg) or
            (finish_type == 'monolithic' and finish_key in mono_reg)
        )
        if not valid:
            skipped += 1
            if on_progress:
                on_progress(finish_type, finish_key, 'skip', i + 1, total)
            continue
        try:
            split_hash = _picker_finish_renderer_hash(finish_type, finish_key) or ''
        except Exception:
            split_hash = ''
        if not split_hash:
            errors += 1
            if on_progress:
                on_progress(finish_type, finish_key, 'fail', i + 1, total, 'no renderer hash')
            continue
        path = _picker_split_warm_cache_path(finish_type, finish_key, col, size, split_hash)
        if (not force) and os.path.isfile(path):
            skipped += 1
            if on_progress:
                on_progress(finish_type, finish_key, 'skip', i + 1, total)
            continue
        try:
            png = _render_picker_split_snapshot_bytes(finish_type, finish_key, col, size, seed)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as df:
                df.write(png)
            baked += 1
            if on_progress:
                on_progress(finish_type, finish_key, 'ok', i + 1, total, path)
        except Exception as e:
            errors += 1
            logger.debug(f"Picker split warm-cache bake failed [{finish_type}/{finish_key}]: {e}")
            if on_progress:
                on_progress(finish_type, finish_key, 'fail', i + 1, total, str(e))
    return baked, skipped, errors


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

    # SPB-105 AT-R2: owner "bake the new thumbnails"; the legacy square path
    # flattened image-authored bases. Use the same compiled paint as the picker.
    # Evidence: standard duplicate score 1.0 before; R2_LIVE_REPORT records after.
    if finish_type == 'base' and (getattr(engine, 'BASE_REGISTRY', {}).get(finish_key, {}).get('all_that_revision') or getattr(engine, 'BASE_REGISTRY', {}).get(finish_key, {}).get('era_image_revision')):
        from PIL import Image as _Image
        raw = _render_picker_split_snapshot_bytes(finish_type, finish_key, color_hex, max(512, size), seed)
        with _Image.open(io.BytesIO(raw)) as pair:
            paint_half = pair.crop((0, 0, pair.width // 2, pair.height))
            if paint_half.size != (size, size):
                paint_half = paint_half.resize((size, size), _Image.Resampling.BOX)
            result = io.BytesIO()
            paint_half.save(result, 'PNG')
            return result.getvalue()

    # Per-finish hue when default neutral helps most bases read distinct in grids.
    # PRISM FORGE (pf_*) procedural paint is tuned against true neutral gray ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â do not
    # substitute the palette hue or catalog thumbnails / previews diverge from in-sim.
    requested_sw_hex = (color_hex or '').lower().replace('#', '').strip()
    color_hex = _swatch_display_color(finish_type, finish_key, color_hex)
    if finish_key and str(finish_key).startswith('pf_') and requested_sw_hex in ('888888', '555577', '446688'):
        color_hex = requested_sw_hex

    # Parse the hint color
    try:
        r = int(color_hex[0:2], 16) / 255.0
        g = int(color_hex[2:4], 16) / 255.0
        b = int(color_hex[4:6], 16) / 255.0
    except Exception:
        r, g, b = 0.533, 0.533, 0.533

    # Monolithic multi-color (Color Shift Duo, Chameleon, FUSIONS): noise/gradient needs resolution
    # At 48px the structural noise is ~1 sample ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ single flat color. ALWAYS render at 256 then downscale.
    mono_reg = getattr(engine, 'MONOLITHIC_REGISTRY', {})
    base_reg = getattr(engine, 'BASE_REGISTRY', {})
    pattern_reg = getattr(engine, 'PATTERN_REGISTRY', {})
    is_base_but_mono = finish_type == 'base' and finish_key not in base_reg and (finish_key and finish_key in mono_reg)
    dynamic_mono_prefixes = ('grad_', 'grad3_', 'gradm_', 'ghostg_', 'clr_', 'cs_duo_', 'mc_')
    is_dynamic_mono = bool(finish_key and any(finish_key.startswith(p) for p in dynamic_mono_prefixes))
    has_dynamic_colors = False
    if is_dynamic_mono:
        try:
            from finish_colors_lookup import get_finish_colors
            has_dynamic_colors = bool(get_finish_colors(finish_key))
        except Exception:
            has_dynamic_colors = False
    if finish_type not in ('base', 'pattern', 'monolithic'):
        raise ValueError(f"Unknown swatch type: {finish_type}")
    if finish_type == 'base' and finish_key not in base_reg and finish_key not in mono_reg:
        raise ValueError(f"Unknown swatch base: {finish_key}")
    if finish_type == 'pattern' and finish_key not in pattern_reg:
        raise ValueError(f"Unknown swatch pattern: {finish_key}")
    if finish_type == 'monolithic' and finish_key not in mono_reg and not has_dynamic_colors:
        raise ValueError(f"Unknown swatch monolithic: {finish_key}")
    # [2026-08-01 SPB thumbnail-accuracy fix] Default floor 512: rendering bases/
    # patterns at the requested size (48px zone dots!) let per-pixel-noise generators
    # draw features ~10x too big relative to the 2048 canvas (sequin_silver rendered
    # at 48 direct vs 256-rendered-then-downscaled: MAD 33.1 / SSIM 0.27). Render at
    # >=512 then downscale with INTER_AREA. The audited carve-outs below deliberately
    # KEEP their 256 render (owner-verified at that resolution; do not bump blindly).
    internal_size = size if size >= 512 else 512
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
    elif size < 256 and finish_key and str(finish_key).startswith('pf_'):
        internal_size = 256
        logger.debug(f"Swatch 256px (PRISM FORGE): {finish_key} (requested size={size})")

    shape = (internal_size, internal_size)
    mask  = np.ones(shape, dtype=np.float32)

    # Build base paint canvas (RGBA float32, 0-1)
    paint = np.zeros((*shape, 4), dtype=np.float32)
    paint[:, :, 0] = r
    paint[:, :, 1] = g
    paint[:, :, 2] = b
    paint[:, :, 3] = 1.0

    # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Spec-map visualisation helper ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
    # Converts iRacing spec map values (M=metallic 0-255, R=roughness 0-255,
    # CC 0-255 where 16=max gloss) into visible brightness/texture so that
    # similar-looking metallic/matte/chrome bases are clearly distinguishable.
    def _apply_spec_visual(paint_arr, M_val, R_val, CC_val):
        M = np.clip(M_val / 255.0, 0, 1)   # 0=dielectric, 1=full metal
        R = np.clip(R_val / 255.0, 0, 1)   # 0=mirror, 1=fully matte
        # CC: 16=max gloss, 0=fully metallised, >16=progressively degraded
        CC_norm = 1.0 - np.clip((max(CC_val, 16) - 16) / 239.0, 0, 1)  # 1=gloss, 0=degraded

        # Metallic: light desaturate so base color still reads (was 0.55 ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ too gray)
        if M > 0.3:
            grey = paint_arr[:, :, :3].mean(axis=2, keepdims=True)
            desat = M * 0.26
            paint_arr[:, :, :3] = paint_arr[:, :, :3] * (1 - desat) + grey * desat
            # Bright highlight sweeping across top (simulates environment map)
            _h = int(paint_arr.shape[0])
            yy = np.linspace(1.0, 0.0, _h, dtype=np.float32)[:, np.newaxis]
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
                _gh, _gw = int(paint_arr.shape[0]), int(paint_arr.shape[1])
                grain = rng_g.uniform(-grain_strength, grain_strength,
                                      (_gh, _gw, 1)).astype(np.float32)
                paint_arr[:, :, :3] = np.clip(paint_arr[:, :, :3] + grain, 0, 1)

        # Clearcoat degradation: dull the surface when CC is beyond 16 (max gloss)
        if CC_norm < 0.75:
            dull = (0.75 - CC_norm) / 0.75 * 0.28
            paint_arr[:, :, :3] = np.clip(paint_arr[:, :, :3] - dull, 0, 1)

        return paint_arr

    def _apply_spec_visual_spatial(paint_arr, M_map, R_map, CC_map, seed, shp):
        """Per-pixel spec visualization for bases with spatial base_spec_fn (e.g. PRISM FORGE).

        Mirrors the scalar _apply_spec_visual logic but uses full M/R/CC maps so swatches
        match full-render spec detail. Adds a light paint-edge trace (cf. paint-aware spec
        pipelines) so micro relief reads in thumbnails.
        """
        h, w = int(shp[0]), int(shp[1])
        M = np.clip(np.asarray(M_map, dtype=np.float32) / 255.0, 0.0, 1.0)
        R = np.clip(np.asarray(R_map, dtype=np.float32) / 255.0, 0.0, 1.0)
        CCv = np.asarray(CC_map, dtype=np.float32)
        if M.shape != (h, w) or R.shape != (h, w) or CCv.shape != (h, w):
            return paint_arr
        CC_norm = 1.0 - np.clip((np.maximum(CCv, 16.0) - 16.0) / 239.0, 0.0, 1.0)
        rgb = paint_arr[:, :, :3].astype(np.float32, copy=False)
        grey = rgb.mean(axis=2, keepdims=True)
        desat = np.clip(M * 0.26, 0.0, 0.26)[:, :, np.newaxis]
        rgb = rgb * (1.0 - desat) + grey * desat
        yy = np.linspace(1.0, 0.0, h, dtype=np.float32)[:, np.newaxis]
        highlight = np.clip(yy * M * 0.50, 0.0, 0.40)
        rgb = np.clip(rgb + highlight[:, :, np.newaxis], 0.0, 1.0)
        matte_factor = np.where(R > 0.35, (R - 0.35) / 0.65 * 0.38, 0.0).astype(np.float32)
        rgb = np.clip(rgb - matte_factor[:, :, np.newaxis], 0.0, 1.0)
        rough_hi = np.clip((R - 0.65) / 0.35, 0.0, 1.0)
        grain_strength = rough_hi * 0.07
        rng_g = np.random.RandomState(int(seed) + 7)
        grain = rng_g.uniform(-1.0, 1.0, (h, w, 1)).astype(np.float32) * grain_strength[:, :, np.newaxis]
        rgb = np.clip(rgb + grain, 0.0, 1.0)
        dull = np.where(CC_norm < 0.75, (0.75 - CC_norm) / 0.75 * 0.28, 0.0).astype(np.float32)
        rgb = np.clip(rgb - dull[:, :, np.newaxis], 0.0, 1.0)
        lum = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]).astype(np.float64)
        gy, gx = np.gradient(lum)
        edge = np.sqrt(gx * gx + gy * gy).astype(np.float32)
        p99 = float(np.percentile(edge, 99.0)) + 1e-6
        edge_n = np.clip(edge / p99, 0.0, 1.0)
        flash = edge_n * np.power(M, 0.85) * 0.14
        rgb = np.clip(rgb + flash[:, :, np.newaxis], 0.0, 1.0)
        paint_arr[:, :, :3] = rgb
        return paint_arr

    # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Helper: extract fns from monolithic tuple or dict ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
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
            try:
                from finish_colors_lookup import get_finish_colors
                fc = get_finish_colors(fk)
            except Exception:
                fc = None
            if not fc:
                raise ValueError(f"Unknown dynamic monolithic swatch colors: {fk}")
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
        except ValueError:
            raise
        except Exception as gen_err:
            raise RuntimeError(f"Generic finish swatch renderer failed [{fk}]: {gen_err}") from gen_err
        raise RuntimeError(f"Generic finish swatch renderer returned no paint [{fk}]")

    # If client sent "base" but this key is only in MONOLITHIC (e.g. Chameleon Classic), render as monolithic
    if finish_type == 'base' and finish_key not in engine.BASE_REGISTRY and finish_key in engine.MONOLITHIC_REGISTRY:
        finish_type = 'monolithic'

    try:
        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ BASE: dict with M, R, CC, paint_fn, optional base_spec_fn ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
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
                _is_prism_forge = bool(finish_key and str(finish_key).startswith('pf_'))
                # Apply the paint modulation function (flake, grain, shimmer etc.)
                if paint_fn and callable(paint_fn):
                    try:
                        paint_out = paint_fn(paint, shape, mask, seed, 1.0, 0.0)
                        if paint_out is not None:
                            po = np.asarray(paint_out, dtype=np.float32)
                            if po.ndim == 3 and po.shape[2] >= 3:
                                if paint.shape[2] >= 4 and po.shape[2] == 3:
                                    paint[:, :, :3] = np.clip(po[:, :, :3], 0, 1)
                                else:
                                    paint = po
                            elif po.ndim == 2:
                                paint[:, :, 0] = paint[:, :, 1] = paint[:, :, 2] = np.clip(po, 0, 1)
                    except Exception as paint_err:
                        raise RuntimeError(f"Base swatch paint_fn failed [{finish_key}]: {paint_err}") from paint_err
                _used_spatial_spec = False
                # Carbon & Composite: run base_spec_fn to get spatial M/R pattern and show weave on swatch
                if base_spec_fn and callable(base_spec_fn):
                    try:
                        spec_seed = seed + abs(hash(finish_key)) % 10000
                        spec_result = _invoke_base_spec_fn(base_spec_fn, shape, spec_seed, 1.0, M_val, R_val)
                        if _is_prism_forge and isinstance(spec_result, (tuple, list)) and len(spec_result) >= 3:
                            M_arr = np.asarray(spec_result[0], dtype=np.float32)
                            R_arr = np.asarray(spec_result[1], dtype=np.float32)
                            CC_arr = np.asarray(spec_result[2], dtype=np.float32)
                            if M_arr.ndim == 2 and R_arr.ndim == 2 and CC_arr.ndim == 2:
                                paint = _apply_spec_visual_spatial(
                                    paint, M_arr, R_arr, CC_arr, seed + 101, shape)
                                _used_spatial_spec = True
                        if not _used_spatial_spec:
                            # spec_result is either a (M, R, CC) tuple/list of 2D arrays
                            # OR a stacked (h, w, 3) array (paradigm_v3-style spec fns, e.g.
                            # nebula / infinite_finish). Extract the R channel for both so the
                            # paint-swatch spec-visual modulation doesn't broadcast-crash.
                            if isinstance(spec_result, (tuple, list)):
                                R_arr = np.asarray(spec_result[1], dtype=np.float32)
                            else:
                                _sr = np.asarray(spec_result, dtype=np.float32)
                                R_arr = _sr[:, :, 1] if (_sr.ndim == 3 and _sr.shape[2] >= 2) else _sr
                            if R_arr.ndim == 2:
                                r_min, r_max = float(R_arr.min()), float(R_arr.max())
                                pat = 1.0 - np.clip((R_arr - r_min) / (r_max - r_min + 1e-8), 0, 1)
                                # Stronger modulation (0.35ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“1.0) so weave/chunks are clearly visible
                                fac = np.clip(0.35 + 0.65 * pat[:, :, np.newaxis], 0, 1)
                                m3 = mask[:, :, np.newaxis]
                                paint[:, :, :3] = np.clip(paint[:, :, :3] * fac * m3 + paint[:, :, :3] * (1.0 - m3), 0, 1)
                    except Exception as _bs_err:
                        raise RuntimeError(f"Base swatch base_spec_fn failed [{finish_key}]: {_bs_err}") from _bs_err
                # Overlay spec-map visual so chrome vs matte vs metallic are distinct
                if not _used_spatial_spec:
                    paint = _apply_spec_visual(paint, M_val, R_val, CC_val)

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ PATTERN: dict with texture_fn + paint_fn, or image_path ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
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
                    raise RuntimeError(f"Pattern image swatch failed [{finish_key}]: {img_err}") from img_err

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
                            # Pattern peaks ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ bright; valleys ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ dark for clear structure
                            bright = pat * 0.55
                            dark   = (1.0 - pat) * 0.32
                            paint[:, :, :3] = np.clip(
                                paint[:, :, :3]
                                + bright[:, :, np.newaxis]
                                - dark[:, :, np.newaxis], 0, 1)

                            # Large M_range = metallic pattern ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ add chrome sheen to peaks
                            if abs(M_range) > 30 and M_pat is not None:
                                shine = np.clip(M_pat, 0, 1) * 0.28
                                paint[:, :, :3] = np.clip(
                                    paint[:, :, :3] + shine[:, :, np.newaxis], 0, 1)

                        else:
                            raise RuntimeError(
                                f"Pattern swatch texture_fn returned no pattern data [{finish_key}]"
                            )
                    elif isinstance(tex, np.ndarray):
                        pv = np.clip(tex, 0, 1)
                        if pv.ndim != 2:
                            raise RuntimeError(
                                f"Pattern swatch texture_fn returned invalid array shape [{finish_key}]: {pv.shape}"
                            )
                        paint[:, :, :3] = np.clip(
                            paint[:, :, :3] * (0.5 + pv[:, :, np.newaxis] * 0.5), 0, 1)
                    else:
                        raise RuntimeError(
                            f"Pattern swatch texture_fn returned unsupported result [{finish_key}]: {type(tex).__name__}"
                        )
                except Exception as tex_err:
                    raise RuntimeError(f"Pattern swatch texture_fn failed [{finish_key}]: {tex_err}") from tex_err

            # Paint modulation on top (colour tinting in grooves)
            if paint_fn and callable(paint_fn):
                try:
                    paint = paint_fn(paint, shape, mask, seed, 0.65, 0.0)
                    # B8 (2026-06-03): some pattern paint_fns operate in 0-255 space and return
                    # 0-255 values (the shimmer_* micro-shimmer family via _paint_micro_shimmer).
                    # This swatch pipeline is 0-1, so an un-normalised 0-255 return clips to pure
                    # white — shimmer_void_dust rendered 255/255/255. Detect the 0-255 scale and
                    # bring it back to 0-1 (mirrors the baked_color normalise in the mono branch).
                    paint = np.asarray(paint, dtype=np.float32)
                    if paint.size and float(np.nanmax(paint)) > 1.5:
                        paint = paint / 255.0
                    paint = np.clip(paint, 0.0, 1.0)
                except Exception as paint_err:
                    raise RuntimeError(f"Pattern swatch paint_fn failed [{finish_key}]: {paint_err}") from paint_err

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ MONOLITHIC: grad/ghost/cs_duo/clr/mc - prefer render_generic_finish ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        # Use finish_colors from JSON so thumbnails match real finish (fixes Ghost Gradient,
        # Gradient 3-Color, Gradient Mirror, etc.). Run BEFORE registry path for these prefixes.
        elif (finish_type == 'monolithic' and finish_key and
              is_dynamic_mono and finish_key not in engine.MONOLITHIC_REGISTRY):
            # SPB-GRADIENT-OVERHAUL-2026-08-23 G-15: registered gradients are
            # authored renderer products, including the enlarged modal swatch.
            # The former dynamic-prefix-first branch flattened every grad_* to
            # JSON endpoint colors even after the picker card used v3. Keep the
            # generic route only for truly unregistered/custom dynamic IDs.
            try:
                _try_generic_finish_swatch(finish_key, paint, shape, mask, seed, color_hex, r, g, b)
            except (ValueError, RuntimeError) as _dm_err:
                # S6 (2026-06-03): a dynamic-mono swatch (gradient / duo / clr / mc) whose colors
                # can't be resolved (stale or not-yet-configured id) is a "swatch not available",
                # not a server crash. Surface a clean 404 instead of a 500+traceback — the picker
                # already hides 404 tiles. We deliberately do NOT fake a gradient here; that would
                # hide a catalog wiring problem, per the dynamic-mono design note below.
                raise FileNotFoundError(f"swatch unavailable (no colors): {finish_key}") from _dm_err

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ MONOLITHIC: tuple (spec_fn, paint_fn) from registry ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        elif finish_type == 'monolithic' and finish_key in engine.MONOLITHIC_REGISTRY:
            entry = engine.MONOLITHIC_REGISTRY[finish_key]
            spec_fn, paint_fn = _get_mono_fns(entry)

            # Handle dict-format monolithics (e.g. some fusions/expansions)
            baked_color = _mono_opt(entry, 'paint_color')
            if baked_color and len(baked_color) >= 3:
                bc = [float(v) for v in baked_color[:3]]
                if max(bc) > 1.0:
                    bc = [v / 255.0 for v in bc]  # normalise 0-255 ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ 0-1
                paint[:, :, 0] = bc[0]
                paint[:, :, 1] = bc[1]
                paint[:, :, 2] = bc[2]

            # Run spec_fn first (we need it for FUSIONS pattern and for optional spec_visual)
            spec_arr = None
            M_mean, R_mean, CC_mean = 128.0, 80.0, 16.0
            if spec_fn and callable(spec_fn):
                try:
                    spec_result = _invoke_monolithic_spec_fn(
                        spec_fn, shape, mask, seed, 1.0, reg_entry=entry
                    )
                    spec_arr = _normalize_spec_result_to_rgba(
                        spec_result, shape, strict_shapes=True
                    )
                    if spec_arr is not None:
                        M_mean  = float(spec_arr[:, :, 0].mean())
                        R_mean  = float(spec_arr[:, :, 1].mean())
                        CC_mean = float(spec_arr[:, :, 2].mean())
                except Exception as spec_err:
                    raise RuntimeError(f"Monolithic swatch spec_fn failed [{finish_key}]: {spec_err}") from spec_err

            # Run paint_fn on raw paint so Color Shift Duos and Chameleons get full-color output
            if paint_fn and callable(paint_fn):
                try:
                    paint = paint_fn(paint, shape, mask, seed, 1.0, 0.0)
                except Exception as pf_err:
                    raise RuntimeError(f"Monolithic swatch paint_fn failed [{finish_key}]: {pf_err}") from pf_err

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

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ DYNAMIC MONOLITHIC NOT IN REGISTRY ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
        # Procedural color finishes must resolve through finish_colors_lookup.
        # Misspelled/stale prefixed IDs should fail instead of inventing a
        # plausible gradient that hides a catalog wiring problem.
        elif finish_type == 'monolithic':
            try:
                _try_generic_finish_swatch(finish_key, paint, shape, mask, seed, color_hex, r, g, b)
            except (ValueError, RuntimeError) as _dm_err:
                # S6 (2026-06-03): a dynamic-mono swatch (gradient / duo / clr / mc) whose colors
                # can't be resolved (stale or not-yet-configured id) is a "swatch not available",
                # not a server crash. Surface a clean 404 instead of a 500+traceback — the picker
                # already hides 404 tiles. We deliberately do NOT fake a gradient here; that would
                # hide a catalog wiring problem, per the dynamic-mono design note below.
                raise FileNotFoundError(f"swatch unavailable (no colors): {finish_key}") from _dm_err

    except Exception as e:
        logger.warning(f"Swatch render error [{finish_type}/{finish_key}]: {e}")
        raise

    # Color identity blend for BASES and PATTERNS only - keeps a single hue visible so they
    # don't all read as silver/gray. Skip for MONOLITHICS: chameleon, gradients, color-shift,
    # fusions, etc. paint_fn outputs multi-color; blending with one tint would wash them out.
    if finish_type != 'monolithic':
        tint_strength = 0.38
        tint_rgb = np.array([r, g, b], dtype=np.float32).reshape(1, 1, 3)
        paint[:, :, :3] = np.clip(
            paint[:, :, :3] * (1.0 - tint_strength) + tint_rgb * tint_strength, 0, 1)

    # Downscale from the internal render size to the requested thumb size.
    # [2026-08-01 SPB thumbnail-accuracy fix] cv2.INTER_AREA: box-average shrink keeps
    # fine flake/grain density honest (LANCZOS ringing overstated sparkle at 10:1+).
    if paint.shape[0] != size or paint.shape[1] != size:
        from PIL import Image as PILImage
        import cv2 as _cv2
        paint_rgb = np.nan_to_num(paint[:, :, :3], nan=0.0, posinf=1.0, neginf=0.0)
        rgb = np.clip(paint_rgb * 255, 0, 255).astype(np.uint8)
        interp = _cv2.INTER_AREA if size < paint.shape[0] else _cv2.INTER_LANCZOS4
        rgb = _cv2.resize(rgb, (size, size), interpolation=interp)
        img = PILImage.fromarray(rgb)
        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=True)
        return buf.getvalue()

    # Convert float32 RGBA ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ uint8 RGB, save as PNG (guard against NaNs from some finishes)
    paint_rgb = np.nan_to_num(paint[:, :, :3], nan=0.0, posinf=1.0, neginf=0.0)
    rgb = np.clip(paint_rgb * 255, 0, 255).astype(np.uint8)
    from PIL import Image as PILImage
    img = PILImage.fromarray(rgb)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _invoke_monolithic_spec_fn(spec_fn, shape, mask, seed, sm, reg_entry=None):
    """Call monolithic ``spec_fn`` whether it is (shape, mask, seed, sm) or
    base-style (shape, seed, sm, base_m, base_r). Wrong arity used to feed the
    mask array into ``seed``, producing garbage spec thumbnails for many specials.
    """
    m_fb, r_fb = 128, 80
    if isinstance(reg_entry, dict):
        m_fb = int(reg_entry.get("M", m_fb))
        r_fb = int(reg_entry.get("R", r_fb))
    try:
        return spec_fn(shape, mask, int(seed), float(sm))
    except TypeError:
        return spec_fn(shape, int(seed), float(sm), m_fb, r_fb)


def _invoke_base_spec_fn(spec_fn, shape, seed, sm, m_val, r_val):
    """Call a base ``base_spec_fn`` whether it is base-style (shape, seed, sm, M, R)
    or a monolithic-style (shape, mask, seed, sm) fn that got registered onto a base.

    2026-06-03 fix: the concurrent rebuild wired paradigm_v3's spec_nebula /
    spec_infinite_finish (both ``(shape, mask, seed, sm)``) onto the ``nebula`` and
    ``infinite_finish`` BASES, but the base render path calls with 5 args -> the fn
    raised "takes 4 positional arguments but 5 were given" and the swatch failed.
    Try the base signature first; on a TypeError fall back to the monolithic one
    with a full-coverage mask (preserves the rebuild's intended spec for the base).
    """
    try:
        return spec_fn(shape, int(seed), float(sm), m_val, r_val)
    except TypeError:
        import numpy as np
        mask = np.ones(shape, dtype=np.float32)
        return spec_fn(shape, mask, int(seed), float(sm))


def _render_spec_swatch_bytes(finish_type, finish_key, size, seed):
    """Render the right half of picker split swatches from the engine spec map.

    Encodes **M / Roughness / Cc** directly into RGB (same layout as viewing a
    compiled spec TGA: red = metallic, green = roughness, blue = clearcoat
    scaled for visibility). Avoids false-color \"material tint\" blends that
    made unrelated finishes look like the same brown plate.
    """
    import numpy as np
    from PIL import Image as PILImage

    mono_reg = getattr(engine, 'MONOLITHIC_REGISTRY', {})
    base_reg = getattr(engine, 'BASE_REGISTRY', {})
    pattern_reg = getattr(engine, 'PATTERN_REGISTRY', {})
    dynamic_mono_prefixes = ('grad_', 'grad3_', 'gradm_', 'ghostg_', 'clr_', 'cs_duo_', 'mc_')
    is_dynamic_mono = bool(finish_key and any(finish_key.startswith(p) for p in dynamic_mono_prefixes))
    if finish_type == 'base' and finish_key not in base_reg and finish_key in mono_reg:
        finish_type = 'monolithic'

    # [2026-08-01 SPB thumbnail-accuracy fix] Floor 512 (was 256-for-small): spec
    # generators that compute noise per-pixel of the output size draw features too
    # big relative to the 2048 canvas at small renders (see _thumb_audit evidence:
    # sequin_silver spec @512-scale vs 2048 = SSIM 0.47). 512 + INTER_AREA shrink.
    internal_size = size if size >= 512 else 512
    shape = (internal_size, internal_size)
    mask = np.ones(shape, dtype=np.float32)
    spec_arr = None

    def _constant_spec(m_val, r_val, cc_val):
        out = np.empty((shape[0], shape[1], 4), dtype=np.float32)
        out[:, :, 0] = np.asarray(m_val, dtype=np.float32) if np.ndim(m_val) else float(m_val)
        out[:, :, 1] = np.asarray(r_val, dtype=np.float32) if np.ndim(r_val) else float(r_val)
        out[:, :, 2] = np.asarray(cc_val, dtype=np.float32) if np.ndim(cc_val) else float(cc_val)
        out[:, :, 3] = 255.0
        return out

    if finish_type == 'base' and finish_key in base_reg:
        entry = base_reg[finish_key]
        m_val = entry.get('M', 100) if isinstance(entry, dict) else 100
        r_val = entry.get('R', 100) if isinstance(entry, dict) else 100
        cc_val = entry.get('CC', 16) if isinstance(entry, dict) else 16
        base_spec_fn = entry.get('base_spec_fn') if isinstance(entry, dict) else None
        if callable(base_spec_fn):
            try:
                result = _invoke_base_spec_fn(base_spec_fn, shape, seed + abs(hash(finish_key)) % 10000, 1.0, m_val, r_val)
                spec_arr = _normalize_spec_result_to_rgba(result, shape, default_m=m_val, default_r=r_val, default_cc=cc_val)
            except Exception as spec_err:
                raise RuntimeError(f"Base spec swatch renderer failed [{finish_key}]: {spec_err}") from spec_err
        if spec_arr is None:
            spec_arr = _constant_spec(m_val, r_val, cc_val)

    elif finish_type == 'pattern' and finish_key in pattern_reg:
        entry = pattern_reg[finish_key]
        texture_fn = entry.get('texture_fn') if isinstance(entry, dict) else None
        image_path = entry.get('image_path') if isinstance(entry, dict) else None
        if image_path and not texture_fn:
            from engine.render import _load_image_pattern
            pv = _load_image_pattern(image_path, shape, scale=1.0, rotation=0.0)
            if pv is None:
                raise RuntimeError(f"Pattern spec swatch image returned no pattern [{finish_key}]")
            pat = np.clip(pv, 0, 1)
            spec_arr = _constant_spec(80 + pat * 145, 120 - pat * 80, 16 + pat * 58)
        elif callable(texture_fn):
            tex = texture_fn(shape, mask, seed, 1.0)
            if isinstance(tex, dict):
                pv = tex.get('pattern_val')
                m_pat = tex.get('M_pattern', pv)
                r_pat = tex.get('R_pattern', pv)
                if pv is None:
                    raise RuntimeError(f"Pattern spec swatch texture returned no pattern [{finish_key}]")
                m = 70 + np.clip(m_pat if m_pat is not None else pv, 0, 1) * 165
                r = 140 - np.clip(r_pat if r_pat is not None else pv, 0, 1) * 92
                cc = 16 + np.clip(pv, 0, 1) * 72
                spec_arr = _constant_spec(m, r, cc)
            elif isinstance(tex, np.ndarray):
                pv = np.clip(tex, 0, 1)
                spec_arr = _constant_spec(70 + pv * 150, 130 - pv * 80, 16 + pv * 64)
        if spec_arr is None:
            raise RuntimeError(f"Pattern spec swatch has no renderer [{finish_key}]")

    elif finish_type == 'monolithic' and is_dynamic_mono and finish_key not in mono_reg:
        try:
            from finish_colors_lookup import get_finish_colors
            fc = get_finish_colors(finish_key)
        except Exception:
            fc = None
        if not fc:
            raise ValueError(f"Unknown dynamic monolithic spec swatch colors: {finish_key}")
        paint = np.ones((shape[0], shape[1], 4), dtype=np.float32) * 0.5
        paint[:, :, 3] = 1.0
        spec_result, _paint_result = engine.render_generic_finish(
            finish_key, {"finish": finish_key, "finish_colors": fc}, paint, shape, mask, seed, 1.0, 1.0, 0.0
        )
        spec_arr = _normalize_spec_result_to_rgba(spec_result, shape, strict_shapes=False)

    elif finish_type == 'monolithic' and finish_key in mono_reg:
        entry = mono_reg[finish_key]
        if isinstance(entry, (tuple, list)) and len(entry) >= 1:
            spec_fn = entry[0]
        elif isinstance(entry, dict):
            spec_fn = entry.get('spec_fn')
        else:
            spec_fn = None
        if callable(spec_fn):
            spec_arr = _normalize_spec_result_to_rgba(
                _invoke_monolithic_spec_fn(spec_fn, shape, mask, seed, 1.0, reg_entry=entry),
                shape,
                strict_shapes=True,
            )
        if spec_arr is None:
            spec_arr = _constant_spec(128, 80, 16)

    else:
        raise ValueError(f"Unknown spec swatch: {finish_type}/{finish_key}")

    spec = np.nan_to_num(spec_arr[:, :, :3].astype(np.float32), nan=0.0, posinf=255.0, neginf=0.0)
    m_ch = np.clip(spec[:, :, 0], 0, 255)
    r_ch = np.clip(spec[:, :, 1], 0, 255)
    cc_ch = np.clip(spec[:, :, 2], 0, 255)
    # Linear Cc visibility: engine uses 16ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“255 inverted clearcoat; stretch to full blue range.
    cc_vis = np.clip((cc_ch - 16.0) * (255.0 / 239.0), 0.0, 255.0)
    rgb = np.stack([m_ch, r_ch, cc_vis], axis=2).astype(np.uint8)
    # [2026-08-01 SPB thumbnail-accuracy fix] INTER_AREA box-average shrink — honest
    # integration of fine spec detail at large downscale ratios (see audit comment
    # on internal_size above).
    if rgb.shape[0] != size or rgb.shape[1] != size:
        import cv2 as _cv2
        interp = _cv2.INTER_AREA if size < rgb.shape[0] else _cv2.INTER_LANCZOS4
        rgb = _cv2.resize(rgb, (size, size), interpolation=interp)
    img = PILImage.fromarray(rgb, 'RGB')
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _swatch_placeholder_png(size, split_mode=False):
    """Return a placeholder PNG (dark gray) when swatch render fails. Avoids 500 ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ broken image in UI."""
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
        if pv is None:
            raise RuntimeError(f"Review pattern image did not decode [{image_path}]")
        pat = np.clip(pv, 0, 1)
        bright = pat * 0.55
        dark = (1.0 - pat) * 0.32
        paint[:, :, :3] = np.clip(
            paint[:, :, :3] + bright[:, :, np.newaxis] - dark[:, :, np.newaxis], 0, 1)
    except Exception as img_err:
        raise RuntimeError(f"Review swatch image renderer failed [{image_path}]: {img_err}") from img_err
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


from server_routes.swatch_review_routes import register_swatch_review_routes
register_swatch_review_routes(
    app,
    review_dir_getter=lambda: getattr(CFG, 'PATTERN_FOR_REVIEW_DIR', None),
    render_pattern_swatch_from_image_path=lambda image_path, color_hex, size, seed: _render_pattern_swatch_from_image_path(image_path, color_hex, size, seed),
    logger=logger,
)


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
# Thumbnail manifest system ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â hash-based invalidation
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
        except Exception as _spb_ex:
            _spb_swallow('_load_thumbnail_manifest@L3975', _spb_ex)
    return {"version": 2, "spec_patterns": {}, "bases": {}, "patterns": {}, "monolithics": {}}


def _save_thumbnail_manifest(manifest):
    """Save the thumbnail hash manifest (call under _THUMBNAIL_MANIFEST_LOCK).

    [2026-09-05 codebase-health S3] atomic (temp + os.replace): a crash mid-write used to
    truncate the manifest and force a full picker re-bake."""
    from engine.atomic_io import atomic_write_json
    manifest_path = os.path.join(THUMBNAIL_DIR, '_manifest.json')
    os.makedirs(THUMBNAIL_DIR, exist_ok=True)
    atomic_write_json(manifest_path, manifest, indent=2, ensure_ascii=True)


def _get_fn_hash(fn):
    """Short hash of a function's source for change detection.

    Wrapper closures (e.g. _spb_wrap_texture_quality_floor.<locals>._wrapped,
    _spb_make_rebuilt_pattern_paint.<locals>._paint) share identical wrapper
    source across hundreds of finishes, which made the picker renderer hash
    COLLIDE across finishes and DRIFT for all of them on any wrapper edit
    (root cause of the recurring thumbnail re-bake). Fold in qualname + the
    source of any inner functions/closure cells so the fingerprint tracks the
    real per-finish renderer, not the shared wrapper text. (2026-06-13)
    """
    try:
        import inspect
        parts = [getattr(fn, '__qualname__', getattr(fn, '__name__', '?'))]
        if 'spec_pattern' in getattr(fn, '__module__', '') or getattr(fn, '_spb_overlay_version', 1) >= 2:
            from engine.spec_overlay_v2.preview import dependency_fingerprint
            parts.append(dependency_fingerprint(fn))
        try:
            parts.append(inspect.getsource(fn))
        except Exception:
            parts.append('nosrc')
        # closure cells: capture the real inner texture_fn / pattern_id / etc.
        for cell in (getattr(fn, '__closure__', None) or ()):
            try:
                cv = cell.cell_contents
            except Exception as _spb_ex:
                _spb_swallow('_get_fn_hash@L4013', _spb_ex); continue
            if callable(cv):
                try:
                    parts.append(inspect.getsource(cv))
                except Exception:
                    parts.append(getattr(cv, '__qualname__', repr(cv)))
            elif isinstance(cv, (str, int, float, bool, type(None))):
                parts.append(repr(cv))
        return hashlib.md5('|'.join(parts).encode()).hexdigest()[:12]
    except Exception:
        return "unknown"


def _get_spec_pattern_preview_fn(pattern_id):
    from engine.spec_patterns import PATTERN_CATALOG

    fn = PATTERN_CATALOG.get(pattern_id)
    if not fn:
        # 2026-06-03 (B6): resolve legacy/renamed spec-pattern ids so old picker tiles still
        # preview (e.g. sparkle_shattered -> razor_wire_coil, brushed_sparkle -> nordic_rune_field).
        try:
            from engine.spec_pattern_aliases import SPEC_PATTERN_ALIASES
            alias = SPEC_PATTERN_ALIASES.get(pattern_id)
            if alias:
                fn = PATTERN_CATALOG.get(alias)
        except Exception as _spb_ex:
            _spb_swallow('_get_spec_pattern_preview_fn@L4039', _spb_ex)
    if not fn:
        raise ValueError(f"Unknown spec pattern: {pattern_id}")
    return fn


def _validate_spec_pattern_preview_request(pattern_id):
    _get_spec_pattern_preview_fn(pattern_id)


def _spec_preview_cache_is_current(pattern_id, cache_path, variant='channels'):
    """Return True only when the cached spec preview matches the renderer source hash."""
    if not os.path.exists(cache_path):
        return False
    fn = _get_spec_pattern_preview_fn(pattern_id)
    current_hash = _get_fn_hash(fn)
    with _THUMBNAIL_MANIFEST_LOCK:
        manifest = _load_thumbnail_manifest()
    cached_entry = manifest.get('spec_patterns_v2_previews', {}).get(f'{pattern_id}:{variant}', {})
    return cached_entry.get('hash') == current_hash


def _mark_spec_preview_cache_current(pattern_id, variant='channels'):
    fn = _get_spec_pattern_preview_fn(pattern_id)
    with _THUMBNAIL_MANIFEST_LOCK:
        manifest = _load_thumbnail_manifest()
        manifest.setdefault('spec_patterns_v2_previews', {})[f'{pattern_id}:{variant}'] = {
            'hash': _get_fn_hash(fn),
            'generated': datetime.utcnow().isoformat()
        }
        _save_thumbnail_manifest(manifest)


def _spec_visual_cache_is_current(pattern_id, size, cache_path):
    """Return True only when the cached visual spec thumbnail is current."""
    if not os.path.exists(cache_path):
        return False
    fn = _get_spec_pattern_preview_fn(pattern_id)
    current_hash = _get_fn_hash(fn)
    with _THUMBNAIL_MANIFEST_LOCK:
        manifest = _load_thumbnail_manifest()
    cached_entry = manifest.get('spec_pattern_visuals', {}).get(f'{pattern_id}:{size}', {})
    return cached_entry.get('hash') == current_hash


def _mark_spec_visual_cache_current(pattern_id, size):
    fn = _get_spec_pattern_preview_fn(pattern_id)
    with _THUMBNAIL_MANIFEST_LOCK:
        manifest = _load_thumbnail_manifest()
        manifest.setdefault('spec_pattern_visuals', {})[f'{pattern_id}:{size}'] = {
            'hash': _get_fn_hash(fn),
            'generated': datetime.utcnow().isoformat()
        }
        _save_thumbnail_manifest(manifest)


def _validate_thumbnail_regen_request(finish_type, finish_id):
    normalized = {
        "base": "base",
        "bases": "base",
        "pattern": "pattern",
        "patterns": "pattern",
        "monolithic": "monolithic",
        "monolithics": "monolithic",
        "spec_patterns": "spec_patterns",
    }.get(finish_type)
    if not normalized:
        raise ValueError(f"Invalid finish_type: {finish_type}")

    if normalized == "spec_patterns":
        _generate_spec_preview_image(finish_id)
    elif normalized == "base":
        if finish_id not in getattr(engine, "BASE_REGISTRY", {}):
            raise ValueError(f"Unknown thumbnail base: {finish_id}")
        _render_swatch_bytes("base", finish_id, "888888", 64, 42)
        save_picker_split_snapshot("base", finish_id)
    elif normalized == "pattern":
        if finish_id not in getattr(engine, "PATTERN_REGISTRY", {}):
            raise ValueError(f"Unknown thumbnail pattern: {finish_id}")
        _render_swatch_bytes("pattern", finish_id, "888888", 64, 42)
        save_picker_split_snapshot("pattern", finish_id)
    elif normalized == "monolithic":
        if finish_id not in getattr(engine, "MONOLITHIC_REGISTRY", {}):
            raise ValueError(f"Unknown thumbnail monolithic: {finish_id}")
        _require_wilds_picker_write_quality([("monolithic", finish_id)])
        _render_swatch_bytes("monolithic", finish_id, "888888", 64, 42)
        _save_picker_split_snapshot_unchecked("monolithic", finish_id)

    return normalized


def _generate_spec_preview_image(pattern_id):
    """SPB-105 v2 tick 3: applied canonical M/R/Cc preview; no averaged channels."""
    from engine.spec_overlay_v2.preview import image
    return image(pattern_id,kind='channels')


def _generate_spec_visual_image(pattern_id, size=160):
    """SPB-105 v2 tick 3: applied canonical M/R/Cc preview; no averaged channels."""
    from engine.spec_overlay_v2.preview import image
    return image(pattern_id,kind='visual',size=size)


def _generate_spec_combined_image(pattern_id, size=160):
    """SPB-105 v2 tick 3: applied canonical M/R/Cc preview; no averaged channels."""
    from engine.spec_overlay_v2.preview import image
    return image(pattern_id,kind='combined',size=size)


def _spec_combined_cache_is_current(pattern_id, size, cache_path):
    """Return True only when the cached combined-spec thumbnail is current."""
    if not os.path.exists(cache_path):
        return False
    fn = _get_spec_pattern_preview_fn(pattern_id)
    current_hash = _get_fn_hash(fn)
    with _THUMBNAIL_MANIFEST_LOCK:
        manifest = _load_thumbnail_manifest()
    cached_entry = manifest.get('spec_pattern_combined', {}).get(f'{pattern_id}:{size}', {})
    return cached_entry.get('hash') == current_hash


def _mark_spec_combined_cache_current(pattern_id, size):
    fn = _get_spec_pattern_preview_fn(pattern_id)
    with _THUMBNAIL_MANIFEST_LOCK:
        manifest = _load_thumbnail_manifest()
        manifest.setdefault('spec_pattern_combined', {})[f'{pattern_id}:{size}'] = {
            'hash': _get_fn_hash(fn),
            'generated': datetime.utcnow().isoformat()
        }
        _save_thumbnail_manifest(manifest)


def _generate_spec_metal_image(pattern_id):
    """SPB-105 v2: independent M/R/Cc lighting study, no channel averaging."""
    from engine.spec_overlay_v2.preview import image
    return image(pattern_id,kind='visual',size=128)


def _prebake_spec_patterns():
    """Pre-bake all spec pattern thumbnails that are missing or stale. Runs in background thread."""
    try:
        from engine.spec_patterns import PATTERN_CATALOG
    except Exception as e:
        logger.warning(f"Spec pattern prebake: could not import PATTERN_CATALOG: {e}")
        return

    spec_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns')
    spec_metal_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns_metal')
    # 2026-06-02 (owner Feature #3): also pre-bake the two halves of the Spec
    # Overlay split cards so the picker is instant on first load (no lazy
    # per-dropdown render) and only re-baked when a pattern's fn changes:
    #   spec_patterns_visual   = LEFT half (grayscale field, size 160)
    #   spec_patterns_combined = RIGHT half (REAL 3-channel M/R/CC, size 160)
    spec_visual_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns_visual')
    spec_combined_dir = os.path.join(THUMBNAIL_DIR, 'spec_patterns_combined')
    os.makedirs(spec_dir, exist_ok=True)
    os.makedirs(spec_metal_dir, exist_ok=True)
    os.makedirs(spec_visual_dir, exist_ok=True)
    os.makedirs(spec_combined_dir, exist_ok=True)
    PREVIEW_SIZE = 160

    with _THUMBNAIL_MANIFEST_LOCK:
        manifest = _load_thumbnail_manifest()
    sp_manifest = manifest.get('spec_patterns', {})
    sv_manifest = manifest.get('spec_pattern_visuals', {}) or {}
    sc_manifest = manifest.get('spec_pattern_combined', {}) or {}
    # SERVERCORE-4 fix: track only the entries THIS run baked so we can merge
    # them into a freshly re-read manifest at the end, instead of writing back
    # this stale snapshot wholesale (which would clobber concurrent writers,
    # e.g. _queue_thumbnail_regen updating bases/patterns/monolithics).
    baked_entries = {}
    baked_visual = {}
    baked_combined = {}
    changed = False
    generated = 0
    generated_aux = 0
    skipped = 0
    errors = 0

    pattern_items = list(PATTERN_CATALOG.items())
    for pattern_id, fn in pattern_items:
        thumb_path = os.path.join(spec_dir, f"{pattern_id}.png")
        metal_path = os.path.join(spec_metal_dir, f"{pattern_id}.png")
        visual_path = os.path.join(spec_visual_dir, f"{pattern_id}_{PREVIEW_SIZE}.png")
        combined_path = os.path.join(spec_combined_dir, f"{pattern_id}_{PREVIEW_SIZE}.png")
        skey = f"{pattern_id}:{PREVIEW_SIZE}"
        current_hash = _get_fn_hash(fn)
        cached_entry = sp_manifest.get(pattern_id, {})
        did_work = False

        # 1) M/R/CC strip + metal sim (hash-gated together)
        if not (os.path.exists(thumb_path) and os.path.exists(metal_path)
                and cached_entry.get('hash') == current_hash):
            try:
                img = _generate_spec_preview_image(pattern_id)
                img.save(thumb_path)
                metal_img = _generate_spec_metal_image(pattern_id)
                metal_img.save(metal_path)
                entry = {'hash': current_hash, 'generated': datetime.utcnow().isoformat()}
                sp_manifest[pattern_id] = entry
                baked_entries[pattern_id] = entry
                changed = True
                generated += 1
                did_work = True
            except Exception as e:
                errors += 1
                logger.warning(f"Spec thumb bake failed for {pattern_id}: {e}")

        # 2) LEFT half of the split card -- grayscale visual field (hash-gated)
        if not (os.path.exists(visual_path) and sv_manifest.get(skey, {}).get('hash') == current_hash):
            try:
                vimg = _generate_spec_visual_image(pattern_id, size=PREVIEW_SIZE)
                vimg.save(visual_path)
                baked_visual[skey] = {'hash': current_hash, 'generated': datetime.utcnow().isoformat()}
                changed = True
                generated_aux += 1
                did_work = True
            except Exception as e:
                errors += 1
                logger.warning(f"Spec visual bake failed for {pattern_id}: {e}")

        # 3) RIGHT half of the split card -- REAL combined 3-channel spec (hash-gated)
        if not (os.path.exists(combined_path) and sc_manifest.get(skey, {}).get('hash') == current_hash):
            try:
                cimg = _generate_spec_combined_image(pattern_id, size=PREVIEW_SIZE)
                cimg.save(combined_path)
                baked_combined[skey] = {'hash': current_hash, 'generated': datetime.utcnow().isoformat()}
                changed = True
                generated_aux += 1
                did_work = True
            except Exception as e:
                errors += 1
                logger.warning(f"Spec combined bake failed for {pattern_id}: {e}")

        if not did_work:
            skipped += 1
            continue

        # Yield to active renders ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â don't compete for CPU
        while not _preview_render_lock.acquire(blocking=False):
            time.sleep(0.1)
        _preview_render_lock.release()
        # Small delay between bakes to avoid CPU saturation
        if len(pattern_items) > 50:
            time.sleep(0.02)

    if changed:
        # SERVERCORE-4 fix: re-read the manifest under the lock and merge only
        # the entries we baked, so updates written by concurrent threads during
        # the (potentially long) bake loop are preserved instead of clobbered.
        with _THUMBNAIL_MANIFEST_LOCK:
            fresh = _load_thumbnail_manifest()
            fresh_sp = fresh.get('spec_patterns')
            if not isinstance(fresh_sp, dict):
                fresh_sp = {}
            fresh_sp.update(baked_entries)
            fresh['spec_patterns'] = fresh_sp
            # merge the split-card halves (LEFT visual + RIGHT real-combined) the
            # same safe way, under one lock at the end (no per-card manifest I/O).
            if baked_visual:
                fresh_sv = fresh.get('spec_pattern_visuals')
                if not isinstance(fresh_sv, dict):
                    fresh_sv = {}
                fresh_sv.update(baked_visual)
                fresh['spec_pattern_visuals'] = fresh_sv
            if baked_combined:
                fresh_sc = fresh.get('spec_pattern_combined')
                if not isinstance(fresh_sc, dict):
                    fresh_sc = {}
                fresh_sc.update(baked_combined)
                fresh['spec_pattern_combined'] = fresh_sc
            _save_thumbnail_manifest(fresh)

    logger.info(
        f"Spec pattern thumbnails: {generated} strip+metal, {generated_aux} split-card halves, "
        f"{skipped} cached, {errors} errors"
    )


def _thumb_regen_picker_type(finish_type):
    return {
        'base': 'base', 'bases': 'base',
        'pattern': 'pattern', 'patterns': 'pattern',
        'monolithic': 'monolithic', 'monolithics': 'monolithic',
    }.get(finish_type)


def _queue_thumbnail_regen(finish_type, finish_id, fn=None):
    """Queue a thumbnail for regeneration (e.g. after a new finish is added at runtime).
    finish_type: 'spec_patterns' | 'bases' | 'patterns' | 'monolithics'
    finish_id: the ID string
    fn: the function (for hash computation), or None to force regen
    """
    def _regen():
        time.sleep(0.5)
        try:
            picker_type = _thumb_regen_picker_type(finish_type)
            if picker_type:
                path = save_picker_split_snapshot(picker_type, finish_id)
                logger.info(f"Picker snapshot regen complete: {picker_type}/{finish_id} -> {path}")
                return
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


import threading as _threading


def _truthy_env(name):
    return str(os.environ.get(name, '')).strip().lower() in ('1', 'true', 'yes', 'on')


def _count_thumbnail_pngs(*subdirs):
    count = 0
    for subdir in subdirs:
        path = os.path.join(THUMBNAIL_DIR, subdir)
        if not os.path.isdir(path):
            continue
        try:
            count += sum(1 for name in os.listdir(path) if name.lower().endswith('.png'))
        except OSError as _spb_ex:
            _spb_swallow('_count_thumbnail_pngs@L4517', _spb_ex)
    return count


def _count_picker_split_snapshots():
    root = os.path.join(THUMBNAIL_DIR, PICKER_SPLIT_SUBDIR)
    if not os.path.isdir(root):
        return 0
    return sum(
        _count_thumbnail_pngs(f'{PICKER_SPLIT_SUBDIR}/{sub}')
        for sub in ('base', 'pattern', 'monolithic')
    )


def _start_thumbnail_background_jobs():
    """Spec-pattern thumbnail maintenance only. Picker thumbs are offline snapshots."""
    try:
        expected_picker = len(_picker_swatch_catalog_items())
        picker_cached = _count_picker_split_snapshots()
        if expected_picker and picker_cached < expected_picker * 0.5:
            logger_startup.info(
                f"Picker snapshots: {picker_cached}/{expected_picker} - "
                f"run: python rebuild_picker_swatches.py (optional, for accurate picker thumbs)"
            )
    except Exception as _spb_ex:
        _spb_swallow('_start_thumbnail_background_jobs@L4542', _spb_ex)

    # Kill-switch: set SHOKKER_SKIP_SPEC_PREBAKE=1 to disable the background
    # spec-thumbnail prebake entirely (e.g. on a slow network drive).
    if _truthy_env('SHOKKER_SKIP_SPEC_PREBAKE'):
        logger.info("Spec pattern thumbnail pre-bake disabled (SHOKKER_SKIP_SPEC_PREBAKE)")
        return
    if _external_write_denial(THUMBNAIL_DIR, "spec-thumbnail-prebake"):
        logger.info("Spec pattern thumbnail pre-bake disabled (SPB_NO_LIVE_LINK)")
        return

    try:
        from engine.spec_patterns import PATTERN_CATALOG
        expected = len(PATTERN_CATALOG)
    except Exception:
        expected = 0
    if not expected:
        logger.warning("Spec pattern thumbnail verification skipped: active catalog unavailable")
        return

    spec_count = _count_thumbnail_pngs('spec_patterns')
    metal_count = _count_thumbnail_pngs('spec_patterns_metal')
    # 2026-06-02 (Feature #3): also gate on the two split-card halves so the
    # Spec Overlay picker is fully cached on first load (no lazy per-dropdown
    # render) and re-baked only when a pattern changes.
    visual_count = _count_thumbnail_pngs('spec_patterns_visual')
    combined_count = _count_thumbnail_pngs('spec_patterns_combined')
    # Raw totals are not cache validity: historical extras can make every count
    # exceed ``expected`` while an active ID is absent or its renderer hash is
    # stale. The worker is intentionally cheap for current entries and performs
    # the authoritative per-ID existence + hash check before writing anything.
    logger.info(
        f"Spec pattern thumbnail verification queued; active={expected}, stored "
        f"strip={spec_count} metal={metal_count} visual={visual_count} "
        f"combined={combined_count} (legacy extras ignored; only missing/stale entries rebake)"
    )
    _threading.Thread(target=_prebake_spec_patterns, daemon=True, name='spec-thumb-prebake').start()


_start_thumbnail_background_jobs()


# ---------------------------------------------------------------------------
# Finish Pack-aware render error detection
# ---------------------------------------------------------------------------
# 99 catalog finishes depend on un-bundled reference_textures packs that buyers
# download in-app (engine/asset_packs.py). When a pack is not installed, the
# engine raises FileNotFoundError / RuntimeError / KeyError whose message or
# path reveals the missing pack. Previously these fell through to a misleading
# "Check that the paint file path is correct" message pointing at the buyer's
# iRacing file. _detect_missing_finish_pack maps such errors to the owning pack
# so the handler can return a structured error_code:'pack_missing' that the UI
# turns into a one-click Finish Packs download prompt.

# finish-id / base-id prefix -> pack id. Used for the spec-overlay KeyError
# ("Unknown reference spec overlay: <name>") which carries no filesystem path.
#
# 2026-06-08 mismap fix: there is intentionally NO bare ("msh", ...) catch-all
# here. Money Shokk (money_shokk.py, pack 'spec_overlays') and Mortal Shokk
# (cultural_mortal_shokk.py, pack 'mortal_shokk') BOTH register the same msh_*
# finish ids, so a bare 'msh' prefix CANNOT disambiguate them and used to
# wrongly tell a Money Shokk finish it needs the 'Mortal Shokk' pack. The Money
# Shokk spec-overlay KeyError is now resolved by error signature in
# _detect_missing_finish_pack (-> 'spec_overlays'); anything that still reaches
# this id-prefix fallback as a bare msh_* deliberately maps to nothing and gets
# the generic "needs a Finish Pack" message instead of a guessed (wrong) name.
# The mshx/mshc/msha entries are unambiguous (Money Shokk only) and stay.
_PACK_ID_PREFIXES = (
    ("fd_", "forbidden_dragon"),
    ("cx_", "colorshoxx"),
    ("pp_", "pattern_plates"),
    ("mshx", "spec_overlays"),   # Money Shokk Xtreme spec overlays
    ("mshc", "spec_overlays"),   # Money Shokk combined spec overlays
    ("msha", "spec_overlays"),   # Money Shokk animated spec overlays
)


def _pack_for_rel_substring(path_text):
    """Return the asset_packs manifest entry whose 'rel' subpath appears in the
    given (normalized, forward-slash) path text, or None. Longest 'rel' wins so
    'grunge_&_fun' is preferred over a hypothetical 'grunge' style prefix."""
    try:
        from engine import asset_packs
    except Exception:
        return None
    best = None
    best_len = -1
    for pack in asset_packs.PACKS:
        rel = str(pack.get("rel") or "").replace("\\", "/").strip("/")
        if rel and rel.lower() in path_text:
            if len(rel) > best_len:
                best = pack
                best_len = len(rel)
    return best


def _pack_for_finish_prefix(zones):
    """Fallback: inspect the zone finish/base/pattern ids and return the
    asset_packs manifest entry implied by a known pack prefix (fd_, cx_, pp_,
    msh*...). Used when the exception has no reference_textures path (the
    spec-overlay KeyError)."""
    try:
        from engine import asset_packs
    except Exception:
        return None
    candidates = []
    for z in (zones or []):
        if not isinstance(z, dict):
            continue
        for key in ("finish", "base", "monolithic", "pattern"):
            val = z.get(key)
            if isinstance(val, str) and val:
                candidates.append(val.strip().lower())
    for cid in candidates:
        for prefix, pack_id in _PACK_ID_PREFIXES:
            if cid.startswith(prefix):
                pack = asset_packs.get_pack(pack_id)
                if pack:
                    return pack
    return None


def _detect_missing_finish_pack(exc, zones=None):
    """If `exc` indicates a missing downloadable Finish Pack, return a dict
    {"error", "error_code":"pack_missing", "pack", "pack_label"} ready to
    jsonify; otherwise return None.

    Triggers on:
      - any error string / path containing 'reference_textures'
      - 'COLORSHOXX reference texture missing'
      - 'Unknown reference spec overlay' (spec_overlays / mortal_shokk KeyError)
    Pack is resolved by matching the manifest 'rel' subpath inside the error
    path, falling back to the zone finish/base id prefix.
    """
    try:
        err_text = str(exc) or ""
    except Exception:
        err_text = ""
    low = err_text.lower().replace("\\", "/")

    is_ref_missing = (
        "reference_textures" in low
        or "colorshoxx reference texture missing" in low
        or "unknown reference spec overlay" in low
    )
    if not is_ref_missing:
        return None

    pack = _pack_for_rel_substring(low)
    # 2026-06-08 mismap fix: Money Shokk (money_shokk.py) and Mortal Shokk
    # (cultural_mortal_shokk.py) BOTH register the same msh_* finish ids, so the
    # 'msh' prefix fallback below can't tell them apart and used to label a Money
    # Shokk finish as needing the 'Mortal Shokk' pack. Disambiguate by the error
    # signature itself: the path-less spec-overlay KeyError ("Unknown reference
    # spec overlay: ...") is ALWAYS raised by money_shokk.py and means the
    # 'spec_overlays' (Money Shokk) pack — never Mortal Shokk. Resolve it
    # directly, before the ambiguous id-prefix guess.
    if pack is None and "unknown reference spec overlay" in low:
        try:
            from engine import asset_packs as _ap
            pack = _ap.get_pack("spec_overlays")
        except Exception:
            pack = None
    if pack is None:
        pack = _pack_for_finish_prefix(zones)
    if pack is None:
        # Pack-related error but we could not map it to a specific pack. Still
        # steer the buyer to the downloader rather than their iRacing file.
        return {
            "error": ("This finish needs a Finish Pack that is not installed. "
                      "Open Finish Packs (gear menu) to download it, then restart."),
            "error_code": "pack_missing",
            "pack": None,
            "pack_label": None,
        }

    label = pack.get("label") or pack.get("id")
    return {
        "error": ("This finish needs the '%s' Finish Pack. "
                  "Open Finish Packs (gear menu) to download it, then restart."
                  % label),
        "error_code": "pack_missing",
        "pack": pack.get("id"),
        "pack_label": label,
    }


@app.route('/preview-render', methods=['POST'])
def preview_render_endpoint():
    """Native-resolution live preview; returns base64 PNGs inline (no job directory).

    JSON body:
    {
        "paint_file": "E:/path/to/car_num_23371.tga",
        "paint_image_base64": "data:image/png;base64,...",  # first live-canvas request
        "paint_source_token": "opaque-token",               # later unchanged-canvas requests
        "zones": [...],
        "seed": 51,
        "preview_scale": 1.0,
        "recolor_rules": []
    }

    Response:
    {
        "success": true,
        "elapsed_ms": 180,
        "paint_preview": "data:image/png;base64,...",
        "spec_preview": "data:image/png;base64,...",
        "paint_source_token": "opaque-token",
        "resolution": [2048, 2048]
    }
    """
    # Per-IP rate limit: protect the engine from runaway slider drags.
    # 10 previews/sec/IP is generous ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â the UI debounces at ~3/sec.
    if not _rate_limit("preview-render", max_per_second=10):
        return jsonify({"error": "rate_limited",
                        "message": "Too many preview requests ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â slow down."}), 429

    # Signal any in-flight preview to abort, then wait for the lock.
    # If the previous render is still finishing after 2 s, reject this
    # request with 429 so the UI can retry rather than pile up renders.
    _touch_user_active_heartbeat()
    _preview_abort.set()
    acquired = _preview_render_lock.acquire(timeout=2.0)
    if not acquired:
        return jsonify({"error": "Preview busy ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â previous render still finishing"}), 429
    _preview_abort.clear()
    _preview_t0 = time.time()
    _preview_temp_dirs = []
    try:
        import numpy as np  # Must be at function scope ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â conditional np imports below shadow this
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        paint_file = data.get("paint_file")
        paint_image_base64_early = data.get("paint_image_base64")
        paint_source_token_early = data.get("paint_source_token")
        preview_source_record = None
        preview_source_transport = "file"
        if paint_image_base64_early:
            # [SPB native-2048 latency 2026-08-23] Decode and hash an uploaded
            # canvas once, then return an opaque process-local token.  Repeated
            # finish/slider previews reuse the exact PNG bytes without resending
            # multi-megabyte JSON.  Bounded LRU + PNG validation live in the
            # dedicated route module; resolution and engine inputs are unchanged.
            try:
                preview_source_record = preview_source_cache.remember_data_url(
                    paint_image_base64_early
                )
                preview_source_transport = "inline"
            except PreviewSourceError as source_error:
                return jsonify({
                    "error": str(source_error),
                    "code": "invalid_preview_source",
                }), 400
        elif paint_source_token_early:
            preview_source_record = preview_source_cache.resolve(paint_source_token_early)
            if preview_source_record is None:
                # Fail closed after server restart/TTL/LRU eviction.  The client
                # clears its token and immediately retries its memoized full PNG.
                return jsonify({
                    "error": "Preview paint source expired; resend the canvas.",
                    "code": "preview_source_missing",
                }), 409
            preview_source_transport = "token"
        if preview_source_record is None and (not paint_file or not os.path.exists(paint_file)):
            return jsonify({"error": f"Paint file not found: {paint_file}"}), 404

        zones = [
            _repair_base_overlay_pattern_reactive_payload(_convert_zone_keys(z))
            for z in data.get("zones", [])
        ]
        # [gauntlet 2026-07-04] The 2026-06-26 TEMP payload dump ("Remove after
        # capture" — capture completed 2026-06-27) serialized the FULL zone payload
        # (region-mask RLE, spatial masks, layer RGB base64) to disk synchronously
        # on EVERY request tick — tens to hundreds of ms for PSD liveries. Now
        # opt-in via SPB_CAPTURE_PREVIEW_PAYLOAD=1 for render-replay captures.
        if os.environ.get("SPB_CAPTURE_PREVIEW_PAYLOAD"):
            try:
                import json as _json_dbg
                _payload_capture_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_LAST_PREVIEW_PAYLOAD.json")
                if _external_write_denial(_payload_capture_path, "preview-payload-capture"):
                    raise PermissionError("external_write_disabled")
                with open(_payload_capture_path, "w", encoding="utf-8") as _f_dbg:
                    _json_dbg.dump({"paint_file": paint_file, "seed": data.get("seed", 51),
                                    "preview_scale": data.get("preview_scale", 0.25),
                                    "zones": data.get("zones", [])}, _f_dbg, indent=1)
            except Exception as _spb_ex:
                _spb_swallow('preview_render_endpoint@L4831', _spb_ex)
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
                # Don't reject ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â just log. Some zones may be incomplete during editing.

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
        global _preview_cache_paint_key, _prev_spec_cache
        if data.get("force_refresh"):
            try:
                import shokker_engine_v2 as _eng
                if hasattr(_eng.build_multi_zone, '_zone_cache'):
                    _eng.build_multi_zone._zone_cache.clear()
                    logger.info("[preview-cache] Force refresh cleared zone cache")
                _prev_spec_cache = None
            except Exception as _spb_ex:
                _spb_swallow('preview_render_endpoint@L4871', _spb_ex)
        if preview_source_record is not None:
            # Use decoded-content identity even when the browser also sends its
            # PSD/TGA path.  The old `and not paint_file` branch could leave the
            # engine zone cache stale after live-canvas pixel edits.
            _new_paint_key = f"live_canvas|{preview_source_record.digest}"
        else:
            try:
                _paint_mtime = os.path.getmtime(paint_file)
            except (OSError, TypeError, ValueError):
                _paint_mtime = 0
            _new_paint_key = f"{paint_file}|{_paint_mtime}"
        if _new_paint_key != _preview_cache_paint_key:
            _preview_cache_paint_key = _new_paint_key
            # Clear the engine-level zone cache when the PAINT FILE changes.
            # Scale changes should NOT flush the cache ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â the engine includes
            # canvas dimensions in its per-zone cache key so different scales
            # naturally produce different cache entries without flushing.
            try:
                import shokker_engine_v2 as _eng
                if hasattr(_eng.build_multi_zone, '_zone_cache'):
                    _eng.build_multi_zone._zone_cache.clear()
                    logger.info(f"[preview-cache] Invalidated zone cache (paint file changed)")
                # Also clear spec delta cache so first render after change sends full PNG
                _prev_spec_cache = None
            except Exception as _spb_ex:
                _spb_swallow('preview_render_endpoint@L4897', _spb_ex)
        if changed_zone >= 0 or zone_hashes:
            logger.info(f"[preview-cache] changed_zone={changed_zone}, {len(zone_hashes)} zone hashes received")

        # Decal spec finishes (list of {specFinish: "gloss"} for non-"none" decals)
        decal_spec_finishes = data.get("decal_spec_finishes", [])
        decal_mask_base64 = data.get("decal_mask_base64")  # separate decal-only alpha mask
        decal_paint_path_preview = None  # set below if a live PNG source is materialized

        # If the client supplied/reused a composited paint, materialize the exact
        # cached PNG bytes for the unchanged engine file-path contract.
        actual_paint_file = paint_file
        if preview_source_record is not None:
            try:
                tmp_decal_dir = _spb_mkdtemp(prefix="shokker_preview_decal_")
                _preview_temp_dirs.append(tmp_decal_dir)
                decal_paint_path_preview = os.path.join(tmp_decal_dir, "paint_with_decals.png")
                with open(decal_paint_path_preview, "wb") as f:
                    f.write(preview_source_record.payload)
                actual_paint_file = decal_paint_path_preview
                logger.info(
                    "Preview: using composited paint source via %s (%d bytes), %d decal spec finish(es)",
                    preview_source_transport,
                    preview_source_record.byte_count,
                    len(decal_spec_finishes),
                )
            except Exception as e:
                logger.warning(f"Preview: failed to materialize live paint source: {e}")
                decal_paint_path_preview = None
                actual_paint_file = paint_file

        # Apply paint recoloring if rules provided (at preview res this is fast)
        # Note: recoloring runs on actual_paint_file so decal composite is preserved
        recolor_rules = data.get("recolor_rules", [])
        if recolor_rules:
            try:
                tmp_dir = _spb_mkdtemp(prefix="shokker_preview_")
                _preview_temp_dirs.append(tmp_dir)
                actual_paint_file = apply_paint_recolor(actual_paint_file, recolor_rules, tmp_dir)
            except Exception as _spb_ex:
                _spb_swallow('preview_render_endpoint@L4937', _spb_ex)  # Fall back to current actual_paint_file

        _rle_canvas_shape = None
        if any(z.get("region_mask") or z.get("source_layer_mask") or z.get("spatial_mask") for z in zones):
            _rle_canvas_shape = _image_rle_shape(actual_paint_file, "preview paint")

        # Build server zones (same format conversion as /render)

        server_zones = []
        for z in zones:
            zone_obj = {
                "name": z.get("name", "Zone"),
                "color": z.get("color", "everything"),
                "intensity": str(_clamp(z.get("intensity"), INTENSITY_MIN, INTENSITY_MAX, INTENSITY_DEFAULT)),
            }
            _render_seed_index = z.get("render_seed_index")
            if isinstance(_render_seed_index, int) and not isinstance(_render_seed_index, bool) and 0 <= _render_seed_index <= 0xFFFFFFFF:
                zone_obj["render_seed_index"] = _render_seed_index
            # SPB-EASY-WHOLE-MIX-20260721 (owner: "pick up to 4 max finishes"
            # with a slider for each): the browser already sends a validated,
            # typed material plan, but this preview-only compatibility bridge
            # used to rebuild zones field-by-field and silently discard it.
            # Preserve the exact four fields and let the engine's strict
            # validator reject malformed ids/types/weights. This changes no
            # finish renderer, so the per-finish M7 rebake gate is N/A.
            if z.get("material_stack") is not None:
                zone_obj["material_stack"] = z.get("material_stack")
                zone_obj["material_stack_mode"] = z.get("material_stack_mode", "auto_trace")
                zone_obj["material_stack_amount"] = z.get("material_stack_amount", 1.0)
                zone_obj["material_scale"] = z.get("material_scale", 1.0)
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
            # SPB-105 tick5: Blend and the new H/S/spec controls must survive
            # preview transport. Engine-only tests missed this field whitelist.
            from server_routes.pattern_controls import copy_pattern_controls
            copy_pattern_controls(zone_obj, z)

            # Pattern strength map (per-pixel strength modulation)
            if z.get("pattern_strength_map"):
                try:
                    # [ULTRACODE 2026-08-22 M2] reuse the validated decoder
                    # (run-shape checks + the 4096 dimension cap) instead of an
                    # inline unbounded np.zeros(w*h) alloc. Behavior-identical
                    # output: float32 mask /255.
                    psm_rle = z["pattern_strength_map"]
                    if isinstance(psm_rle, str):
                        psm_rle = json.loads(psm_rle)
                    zone_obj["pattern_strength_map"] = _decode_rle_mask_payload(
                        psm_rle, "pattern_strength_map", max_shape=(512, 512))
                except Exception as _psm_err:
                    raise ValueError(f"pattern_strength_map decode failed: {_psm_err}") from _psm_err

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
            if z.get("base_scale") is not None and _safe_float(z.get("base_scale"), SCALE_DEFAULT) != SCALE_DEFAULT:
                zone_obj["base_scale"] = _clamp(z["base_scale"], SCALE_MIN, SCALE_MAX, SCALE_DEFAULT)
            if z.get("base_offset_x") is not None:
                zone_obj["base_offset_x"] = _clamp(z["base_offset_x"], 0.0, 1.0, 0.5)
            if z.get("base_offset_y") is not None:
                zone_obj["base_offset_y"] = _clamp(z["base_offset_y"], 0.0, 1.0, 0.5)
            if z.get("base_rotation") is not None and _safe_float(z.get("base_rotation"), ROTATION_DEFAULT) != ROTATION_DEFAULT:
                zone_obj["base_rotation"] = _clamp(z["base_rotation"], ROTATION_MIN, ROTATION_MAX, ROTATION_DEFAULT)
            # [2026-08-06 owner: "Spec Scale ... NOT reflecting at all in the LIVE
            # PREVIEWS ... I can't see how the pattern looks unless I put it on the
            # car in the actual game"] This preview whitelist forwarded base_scale/
            # base_rotation but silently DROPPED spec_scale/spec_rotation, so the
            # engine never saw them here — while /render forwards them, making the
            # preview lie vs the export. Verified at wire level: spec_sig byte-
            # identical at spec_scale 1.0 vs 0.2 pre-fix. NOTE: spec_scale==1.0 must
            # still be forwarded — a MISSING spec_scale means "follow base_scale"
            # to the engine, so independent-at-1.0 is a real, distinct state (same
            # rule the client payload builders follow, paint-booth-5:653).
            if z.get("spec_scale") is not None:
                zone_obj["spec_scale"] = _clamp(z["spec_scale"], SCALE_MIN, SCALE_MAX, SCALE_DEFAULT)
            if z.get("spec_rotation") is not None and _safe_float(z.get("spec_rotation"), ROTATION_DEFAULT) != ROTATION_DEFAULT:
                zone_obj["spec_rotation"] = _clamp(z["spec_rotation"], ROTATION_MIN, ROTATION_MAX, ROTATION_DEFAULT)
            # [SPB-SPECSHIFT-PARITY 2026-08-24] THIRD instance of the same trap
            # (after spec_scale/spec_rotation above): the R/G/B spec-channel
            # sliders reached the engine on /render — which forwards the client
            # zone dicts in place — but this preview builder is an ALLOWLIST, so
            # a field nobody copies is silently dropped. Owner: "moving the SPEC
            # SLIDERS doesn't update the combined/metal/rough/coat previews."
            # It wasn't the thumbnails: the preview genuinely rendered without
            # the shift, so the spec came back byte-identical and the dock had
            # nothing new to draw — and the live pane disagreed with the export.
            # Engine consumes this at shokker_engine_v2.py (SPEC CHANNEL SLIDERS).
            _z_scs = z.get("spec_channel_shift")
            if isinstance(_z_scs, (list, tuple)) and len(_z_scs) == 3:
                zone_obj["spec_channel_shift"] = [
                    _clamp(_z_scs[0], -127, 127, 0),
                    _clamp(_z_scs[1], -127, 127, 0),
                    _clamp(_z_scs[2], -127, 127, 0),
                ]
            if z.get("base_flip_h") is not None:
                zone_obj["base_flip_h"] = bool(z["base_flip_h"])
            if z.get("base_flip_v") is not None:
                zone_obj["base_flip_v"] = bool(z["base_flip_v"])
            if z.get("base_strength") is not None:
                zone_obj["base_strength"] = _safe_float(z["base_strength"], 1.0)
            _bss_raw = z.get("base_spec_strength")
            if _bss_raw is None and z.get("baseSpecStrength") is not None:
                _bss_raw = z.get("baseSpecStrength")
            if _bss_raw is not None:
                zone_obj["base_spec_strength"] = _safe_float(_bss_raw, 1.0)
            # SPB-93 tick 30: preview rebuilds the canonical Zone payload
            # field-by-field, so carry the iRacing spec-alpha lighting control.
            if z.get("spec_lighting_mask") is not None:
                zone_obj["spec_lighting_mask"] = int(round(_clamp(
                    z.get("spec_lighting_mask"), 0.0, 255.0, 255.0
                )))
            _material_remap = z.get("spec_material_remap")
            if isinstance(_material_remap, dict):
                try:
                    _clean_remap = {}
                    for _channel in ("m", "r", "cc"):
                        _range = _material_remap.get(_channel)
                        if not isinstance(_range, dict):
                            raise ValueError("missing material range")
                        _low = int(round(_clamp(_range.get("low"), 0.0, 255.0, 0.0)))
                        _high = int(round(_clamp(_range.get("high"), 0.0, 255.0, 255.0)))
                        if _low > _high:
                            raise ValueError("material range low exceeds high")
                        _clean_remap[_channel] = {"low": _low, "high": _high}
                    zone_obj["spec_material_remap"] = _clean_remap
                except (TypeError, ValueError):
                    logger.warning("Ignoring invalid spec material remap for preview Zone %r", zone_obj.get("name"))
            _sampled_spec = z.get("spec_material_override")
            if isinstance(_sampled_spec, dict):
                try:
                    zone_obj["spec_material_override"] = {
                        key: int(round(_clamp(_sampled_spec.get(key), 0.0, 255.0, 255.0)))
                        for key in ("m", "r", "cc", "a")
                    }
                except (TypeError, ValueError):
                    logger.warning("Ignoring invalid sampled spec material for preview Zone %r", zone_obj.get("name"))
            # Base spec blend mode (normal, multiply, screen, etc.) ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â passthrough from JS
            if z.get("base_spec_blend_mode") and z["base_spec_blend_mode"] != "normal":
                zone_obj["base_spec_blend_mode"] = z["base_spec_blend_mode"]
            if z.get("base_color_mode") is not None:
                zone_obj["base_color_mode"] = z.get("base_color_mode", "source")
            # SPB base-mode hotfix 2026-09-09: preserve the UI's source/own choice.
            # Dropping this flag made source mode fall into the legacy finish-color default.
            if z.get("base_color_explicit") is not None:
                zone_obj["base_color_explicit"] = bool(z["base_color_explicit"])
            if z.get("base_color") is not None:
                zone_obj["base_color"] = z.get("base_color", [1.0, 1.0, 1.0])
            if z.get("base_color_source") is not None:
                zone_obj["base_color_source"] = z.get("base_color_source")
            # Gradient color mode ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â must pass stops and direction for preview parity with full render
            if z.get("gradient_stops"):
                zone_obj["gradient_stops"] = z["gradient_stops"]
            if z.get("gradient_direction"):
                zone_obj["gradient_direction"] = z["gradient_direction"]
            if z.get("base_color_strength") is not None:
                zone_obj["base_color_strength"] = _clamp(z.get("base_color_strength"), 0.0, 1.0, 1.0)
            # [SPB COLOR LAB 2026-08-27b] THIRD whitelist on the dial path (after the client
            # config-hash and the per-zone zone_hashes): this server-side zone_obj translation
            # silently stripped the new keys, so the engine always received depth=None and the
            # sliders read as dead. depth present switches the engine to the Lab pipeline.
            if z.get("base_color_depth") is not None:
                zone_obj["base_color_depth"] = _clamp(z.get("base_color_depth"), 0.0, 1.0, 0.65)
            if z.get("base_color_flip") is not None:
                zone_obj["base_color_flip"] = _clamp(z.get("base_color_flip"), 0.0, 355.0, 0.0)
            if z.get("base_color_underglow") is not None:
                zone_obj["base_color_underglow"] = _clamp(z.get("base_color_underglow"), 0.0, 1.0, 0.0)
            if z.get("base_color_fit_zone"):
                zone_obj["base_color_fit_zone"] = True
            if z.get("base_hue_offset") is not None:
                zone_obj["base_hue_offset"] = _safe_float(z.get("base_hue_offset"), 0.0)
            if z.get("base_saturation_adjust") is not None:
                zone_obj["base_saturation_adjust"] = _safe_float(z.get("base_saturation_adjust"), 0.0)
            if z.get("base_brightness_adjust") is not None:
                zone_obj["base_brightness_adjust"] = _safe_float(z.get("base_brightness_adjust"), 0.0)

            # Per-zone imported spec source: lets a zone start from a user TGA/PNG/JPG spec map.
            if z.get("zone_spec_map"):
                _zsm_path = z.get("zone_spec_map")
                if os.path.exists(_zsm_path):
                    zone_obj["zone_spec_map"] = _zsm_path
                    zone_obj["zone_spec_map_strength"] = _clamp(z.get("zone_spec_map_strength"), 0.0, 1.0, 1.0)
                else:
                    logger.warning(f"Zone spec map not found for preview zone '{zone_obj.get('name', 'Zone')}': {_zsm_path}")

            # Spec pattern overlay stack
            # SPB-93: preview must retain the same rendered-material records as full output.
            if isinstance(z.get("material_instances"), list):
                zone_obj["material_instances"] = z["material_instances"]
            if z.get("spec_pattern_stack"):
                zone_obj["spec_pattern_stack"] = z.get("spec_pattern_stack", [])
            if z.get("overlay_spec_pattern_stack"):
                zone_obj["overlay_spec_pattern_stack"] = z.get("overlay_spec_pattern_stack", [])
            if z.get("third_overlay_spec_pattern_stack"):
                zone_obj["third_overlay_spec_pattern_stack"] = z.get("third_overlay_spec_pattern_stack", [])
            if z.get("fourth_overlay_spec_pattern_stack"):
                zone_obj["fourth_overlay_spec_pattern_stack"] = z.get("fourth_overlay_spec_pattern_stack", [])
            if z.get("fifth_overlay_spec_pattern_stack"):
                zone_obj["fifth_overlay_spec_pattern_stack"] = z.get("fifth_overlay_spec_pattern_stack", [])

            # Base Overlay Layers (2ndÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“5th). Trigger on EITHER base OR color_source so specials-only overlays work.
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
                logger.info(
                    f"[PREVIEW OVERLAY] {_pfx}: base={_has_base}, src={_has_src}, "
                    f"str={z.get(f'{_pfx}_strength')}, blend={z.get(f'{_pfx}_blend_mode')}, "
                    f"color={z.get(f'{_pfx}_color')}, pattern={z.get(f'{_pfx}_pattern')!r}, "
                    f"pat_scale={z.get(f'{_pfx}_pattern_scale')}, "
                    f"pat_opacity={z.get(f'{_pfx}_pattern_opacity')}, "
                    f"pat_strength={z.get(f'{_pfx}_pattern_strength')}"
                )
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
                zone_obj[f"{_pfx}_spec_strength"] = float(z.get(f"{_pfx}_spec_strength", 1.0))
                zone_obj[f"{_pfx}_hue_shift"] = float(z.get(f"{_pfx}_hue_shift") or 0)
                zone_obj[f"{_pfx}_saturation"] = float(z.get(f"{_pfx}_saturation") or 0)
                zone_obj[f"{_pfx}_brightness"] = float(z.get(f"{_pfx}_brightness") or 0)
                zone_obj[f"{_pfx}_pattern_hue_shift"] = float(z.get(f"{_pfx}_pattern_hue_shift") or 0)
                zone_obj[f"{_pfx}_pattern_saturation"] = float(z.get(f"{_pfx}_pattern_saturation") or 0)
                zone_obj[f"{_pfx}_pattern_brightness"] = float(z.get(f"{_pfx}_pattern_brightness") or 0)
                for _k in (
                           f"{_pfx}_pattern_opacity", f"{_pfx}_pattern_scale",
                           f"{_pfx}_pattern_rotation", f"{_pfx}_pattern_strength",
                           f"{_pfx}_pattern_offset_x", f"{_pfx}_pattern_offset_y",
                           # [SPB-DEGRADE-HUNT 2026-08-22] parity with the full
                           # render: these five overlay params were silently
                           # dropped from previews only, so the live pane
                           # visibly diverged from ("re-degraded" vs) every
                           # completed full render on rotated/tinted overlays.
                           f"{_pfx}_rotation", f"{_pfx}_spec_rotation",
                           f"{_pfx}_color_strength", f"{_pfx}_color_scale",
                           f"{_pfx}_spec_scale"):
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
                    zone_obj["region_mask"] = _decode_rle_mask_payload(
                        z["region_mask"], "preview region_mask", expected_shape=_rle_canvas_shape
                    )
                except Exception as _rm_err:
                    raise ValueError(f"region_mask decode failed: {_rm_err}") from _rm_err

            # Source layer mask (PSD layer alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â restricts zone to layer pixels)
            if z.get("source_layer_mask"):
                try:
                    zone_obj["source_layer_mask"] = _decode_cached_source_layer_mask(
                        z, "preview source_layer_mask", expected_shape=_rle_canvas_shape
                    )
                    # [ULTRACODE 2026-08-22 synthesis #5c] forward the real
                    # content key — without it the engine's color-mask cache
                    # fell back to id(ndarray) (cross-request collisions).
                    zone_obj["_source_layer_mask_cache_key"] = z.get("_source_layer_mask_cache_key")
                    rh, rw = zone_obj["source_layer_mask"].shape
                    logger.info(f"[PSD] Zone '{zone_obj.get('name','')}' restricted to layer mask ({rw}x{rh})")
                except Exception as _slm_err:
                    raise ValueError(f"source_layer_mask decode failed: {_slm_err}") from _slm_err

            # Photoshop-correct layer-local color matching: decode the layer's
            # own RGB image so the engine can color-match against the layer's
            # unblended pixels instead of the composite. See Codex finding.
            if z.get("source_layer_rgb_png"):
                try:
                    zone_obj["source_layer_rgb"] = _decode_cached_source_layer_rgb(
                        z, "preview source_layer_rgb_png", expected_shape=_rle_canvas_shape
                    )
                    zone_obj["_source_layer_rgb_cache_key"] = z.get("_source_layer_rgb_cache_key")
                    _rh, _rw = zone_obj["source_layer_rgb"].shape[:2]
                    logger.info(f"[PSD] Zone '{zone_obj.get('name','')}' will color-match against layer RGB ({_rw}x{_rh})")
                except Exception as _slr_err:
                    raise ValueError(f"source_layer_rgb decode failed: {_slr_err}") from _slr_err

            # Spatial mask - include/exclude refinement for color-based zones
            # Values: 0=unset, 1=include (green), 2=exclude (red)
            if z.get("spatial_mask"):
                try:
                    zone_obj["spatial_mask"] = _decode_spatial_mask_payload(
                        z["spatial_mask"], "preview spatial_mask", expected_shape=_rle_canvas_shape
                    )
                except Exception as _spm_err:
                    raise ValueError(f"spatial_mask decode failed: {_spm_err}") from _spm_err
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

        # SPB-93: retain native material and current preview when unlinking.
        from server_routes.zone_material_capture import prepare_capture
        try:
            material_capture = prepare_capture(data.get('material_capture'), server_zones)
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400

        # Run the preview render (pass abort_event so build_multi_zone can bail between zones)
        paint_rgb, spec_rgba, elapsed_ms = engine.preview_render(
            actual_paint_file, server_zones, seed=seed, preview_scale=preview_scale,
            import_spec_map=import_spec_map,
            decal_spec_finishes=decal_spec_finishes if decal_spec_finishes else None,
            decal_paint_path=decal_paint_path_preview,
            decal_mask_base64=decal_mask_base64 or None,
            abort_event=_preview_abort,
        )

        if material_capture is not None:
            try:
                return jsonify(material_capture.finish(
                    (paint_rgb, spec_rgba, elapsed_ms), preview_scale, engine.preview_render,
                    actual_paint_file, seed=seed, import_spec_map=import_spec_map,
                    decal_spec_finishes=decal_spec_finishes if decal_spec_finishes else None,
                    decal_paint_path=decal_paint_path_preview,
                    decal_mask_base64=decal_mask_base64 or None, abort_event=_preview_abort))
            except ValueError as exc:
                return jsonify({'success': False, 'error': str(exc)}), 422

        # Convert paint to base64 PNG (main preview)
        # [SPB-QOL 2026-08-05 loop unit 6] Skip re-sending an IDENTICAL paint image.
        # MEASURED across realistic edits: the paint preview was byte-identical in
        # 5 of 6 (every intensity change AND every base swap gloss->matte->chrome)
        # because those are SPEC finishes — they change material properties, not
        # paint colours. 318 KB was encoded, base64'd, shipped and decoded every
        # time for nothing, while the round trip (182-468 ms) was often dominated
        # by that overhead rather than the engine (56-118 ms).
        #
        # The signature is taken on the RAW array, before encoding, so a hit skips
        # the PNG encode too — not just the transfer.
        #
        # Correctness: the client tells us what it is currently displaying
        # (client_paint_sig). We only omit the image when that matches what we
        # just rendered, so a fresh page, a second tab, or a reload always gets
        # real pixels. Never trust "the last thing WE sent" — that is what makes
        # this safe for more than one client.
        _paint_sig = None
        try:
            _paint_sig = hashlib.sha1(np.ascontiguousarray(paint_rgb).tobytes()).hexdigest()
        except Exception:
            _paint_sig = None
        _client_paint_sig = data.get("client_paint_sig")
        _paint_reused = bool(_paint_sig and _client_paint_sig and _client_paint_sig == _paint_sig)
        paint_b64 = None if _paint_reused else numpy_to_base64_png(paint_rgb)

        # Convert spec to base64 PNG (bottom-right inset). Normalize and catch failures so
        # the main paint preview still works; show clear message if spec (bottom right) fails.
        spec_b64 = None
        spec_warning = None
        spec_normalized = _spec_array_to_rgba_uint8(spec_rgba)
        # [SPB-QOL 2026-08-05] Same lossless signature skip as the paint image.
        # The spec PNG is the single biggest payload (up to ~626 KB, and one
        # observed render logged a 484 KB PNG for an essentially UNCHANGED spec).
        # Signed on the RAW array so a hit skips the PNG encode as well as the
        # transfer, and keyed on what the CLIENT currently holds so a reload or a
        # second tab always gets real pixels.
        _spec_sig = None
        if spec_normalized is not None:
            try:
                _spec_sig = hashlib.sha1(np.ascontiguousarray(spec_normalized).tobytes()).hexdigest()
            except Exception:
                _spec_sig = None
        _spec_reused = bool(_spec_sig and data.get("client_spec_sig") == _spec_sig)
        if spec_normalized is not None and _spec_reused:
            pass                       # client already has these exact pixels
        elif spec_normalized is not None:
            try:
                spec_b64 = numpy_to_base64_png(spec_normalized)
            except Exception as spec_err:
                logger.warning(f"Spec map (bottom-right) encode failed: {spec_err}\n{traceback.format_exc()}")
                spec_warning = "Could not render spec map (bottom right corner). Check server logs for details."
        else:
            spec_warning = "Spec map invalid (wrong shape/dtype). Check server logs for details."

        # If spec failed, use a 1x1 transparent PNG so the UI doesn't break; client can hide or show message
        if spec_b64 is None and not _spec_reused:
            spec_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="  # 1x1 transparent

        # ---- Spec delta encoding (#12) ----
        # If we have a cached previous spec and shapes match, compute a
        # compressed delta.  Send it instead of the full PNG when smaller.
        # [SPB-QOL 2026-08-05] DISABLED. This delta was computed and shipped on
        # every render and **no client has ever read it** (the only client-side
        # reference to spec_delta is a cache-clear route). It also cannot be
        # wired up as-is: compress_spec_delta stores clamp(delta + 128, 0, 255),
        # so any change beyond +/-127 is LOSSY — verified, a spec byte going
        # 0 -> 250 reconstructs as 127, which would show the painter a wrong
        # metallic/roughness/clearcoat value. Wrong is worse than slow. The
        # lossless signature skip above covers the case this was aiming at (an
        # unchanged spec: one logged render spent 484 KB on it). Left in place,
        # unused, so the encoder can be made lossless later if the bandwidth is
        # ever worth it.
        spec_delta_b64 = None
        if False and spec_normalized is not None and _prev_spec_cache is not None:
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
            "server_total_ms": round((time.time() - _preview_t0) * 1000, 1),
            "source_transport": preview_source_transport,
        }
        if preview_source_record is not None:
            payload["paint_source_token"] = preview_source_record.token
            payload["source_bytes"] = preview_source_record.byte_count
        # Always report the signature so the client can echo it next time.
        if _paint_sig:
            payload["paint_sig"] = _paint_sig
        if _paint_reused:
            payload["paint_unchanged"] = True
            payload.pop("paint_preview", None)
        if _spec_sig:
            payload["spec_sig"] = _spec_sig
        if _spec_reused:
            payload["spec_unchanged"] = True
            payload.pop("spec_preview", None)
        if spec_delta_b64:
            payload["spec_delta"] = spec_delta_b64
        if spec_warning:
            payload["spec_warning"] = spec_warning
        # Record successful preview render in the recent-renders ring.
        try:
            _record_recent_render("preview", paint_file,
                                  int((time.time() - _preview_t0) * 1000), success=True)
        except Exception as _spb_ex:
            _spb_swallow('preview_render_endpoint@L5457', _spb_ex)
        return jsonify(payload)

    except Exception as e:
        # Finish Pack-aware check FIRST: a missing reference_textures pack must
        # steer the buyer to the in-app downloader, NOT the misleading "check
        # your paint file path" branch below.
        _pack_err = _detect_missing_finish_pack(e, zones if 'zones' in dir() else None)
        if _pack_err is not None:
            logger.warning(f"Preview render blocked by missing Finish Pack "
                           f"(pack={_pack_err.get('pack')}): {e}")
            try:
                _record_recent_render("preview", paint_file if 'paint_file' in dir() else None,
                                      int((time.time() - _preview_t0) * 1000), success=False)
            except Exception as _spb_ex:
                _spb_swallow('preview_render_endpoint@L5472', _spb_ex)
            _pack_err["rid"] = getattr(g, "_rid", "-")
            return jsonify(_pack_err), 409
        err_msg = str(e)
        # Provide friendlier error messages for common issues
        if 'numpy' in err_msg.lower() or 'np' in err_msg:
            err_msg = f"Engine computation error: {err_msg}. Try re-rendering."
        elif 'FileNotFoundError' in type(e).__name__ or 'not found' in err_msg.lower():
            # Guard: a reference_textures path is a missing pack (handled above),
            # never the buyer's paint file. Only blame the paint path otherwise.
            if 'reference_textures' in err_msg.replace('\\', '/'):
                err_msg = ("This finish needs a Finish Pack that is not installed. "
                           "Open Finish Packs (gear menu) to download it, then restart.")
            else:
                err_msg = f"File not found: {err_msg}. Check that the paint file path is correct."
        elif 'MemoryError' in type(e).__name__:
            err_msg = "Out of memory - try reducing preview scale or number of zones."
        logger.error(f"Preview render failed: {e}\n{traceback.format_exc()}")
        try:
            _record_recent_render("preview", paint_file if 'paint_file' in dir() else None,
                                  int((time.time() - _preview_t0) * 1000), success=False)
        except Exception as _spb_ex:
            _spb_swallow('preview_render_endpoint@L5494', _spb_ex)
        return jsonify({"error": err_msg, "rid": getattr(g, "_rid", "-")}), 500
    finally:
        # Materialized token sources and recolor intermediates must disappear on
        # success, validation errors, engine exceptions, and aborted renders.
        # Keeping one explicit ownership list avoids the old success-only leak.
        for _preview_temp_dir in reversed(_preview_temp_dirs):
            try:
                shutil.rmtree(_preview_temp_dir, ignore_errors=True)
            except Exception as _spb_ex:
                _spb_swallow('preview_render_endpoint@L5504', _spb_ex)
        # Always release the preview render lock so the next request can proceed.
        try:
            _preview_render_lock.release()
        except RuntimeError as _spb_ex:
            _spb_swallow('preview_render_endpoint@L5509', _spb_ex)  # Lock was already released (e.g. early-return path above)


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
        "live_link": true,              // optional: copy car files to iRacing folder
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
    _touch_user_active_heartbeat()
    _preview_abort.set()
    # Acquire render lock to prevent preview and full render from running simultaneously
    # SERVERCORE-1 fix: track lock ownership; never force-release an unowned lock.
    have_lock = _preview_render_lock.acquire(timeout=5.0)
    if not have_lock:
        logger.warning("Render lock busy after 5s - returning 429 (no force-release)")
        return jsonify({"error": "render_busy"}), 429

    try:
        import numpy as np  # Must be at function scope ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â conditional np imports below shadow this
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        paint_file = data.get("paint_file")
        paint_image_base64 = data.get("paint_image_base64")
        if not paint_file and not paint_image_base64:
            return jsonify({"error": "Missing 'paint_file' path or 'paint_image_base64'"}), 400
        if paint_file and not paint_image_base64 and not os.path.exists(paint_file):
            return jsonify({"error": f"Paint file not found: {paint_file}"}), 404

        zones = [
            _repair_base_overlay_pattern_reactive_payload(_convert_zone_keys(z))
            for z in data.get("zones", [])
        ]
        # [gauntlet 2026-07-04] The 2026-06-26 TEMP payload dump ("Remove after
        # capture" — capture completed 2026-06-27) serialized the FULL zone payload
        # (region-mask RLE, spatial masks, layer RGB base64) to disk synchronously
        # on EVERY request tick — tens to hundreds of ms for PSD liveries. Now
        # opt-in via SPB_CAPTURE_PREVIEW_PAYLOAD=1 for render-replay captures.
        if os.environ.get("SPB_CAPTURE_PREVIEW_PAYLOAD"):
            try:
                import json as _json_dbg
                _payload_capture_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_LAST_PREVIEW_PAYLOAD.json")
                if _external_write_denial(_payload_capture_path, "render-payload-capture"):
                    raise PermissionError("external_write_disabled")
                with open(_payload_capture_path, "w", encoding="utf-8") as _f_dbg:
                    _json_dbg.dump({"paint_file": paint_file, "seed": data.get("seed", 51),
                                    "preview_scale": data.get("preview_scale", 0.25),
                                    "zones": data.get("zones", [])}, _f_dbg, indent=1)
            except Exception as _spb_ex:
                _spb_swallow('render@L5588', _spb_ex)
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
        if data.get("helmet_paint_file") or data.get("suit_paint_file"):
            logger.info("Ignoring retired helmet/suit render payload fields in car-only SPB build")
        helmet_paint = None
        suit_paint = None
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

        # Create job output dir
        job_id = f"render_{int(time.time())}_{iracing_id}_{uuid.uuid4().hex[:12]}"
        job_dir = os.path.join(OUTPUT_FOLDER, f"job_{job_id}")
        os.makedirs(job_dir, exist_ok=True)
        globals().setdefault("_SPB_OWN_JOB_DIRS", set()).add(f"job_{job_id}")  # HELPER_V2 fix pass 5 2026-10-05 (orchestrator): the auto-purge below only removes THIS process's own job dirs

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
                [d for d in os.listdir(OUTPUT_FOLDER) if d.startswith('job_') and d in globals().get('_SPB_OWN_JOB_DIRS', ()) and os.path.isdir(os.path.join(OUTPUT_FOLDER, d))],  # HELPER_V2 fix pass 5 2026-10-05 (orchestrator): output/ is SHARED by the live (59876) and test (59879) servers -- a render on one used to delete every other job dir, the owner's live render jobs included; dirs this process did not create are left to the 24 h janitor (server_routes/job_cleanup.py)
                key=lambda d: os.path.getmtime(os.path.join(OUTPUT_FOLDER, d)),
                reverse=True
            )
            for old_dir in job_dirs[2:]:  # Keep 2 most recent, delete rest
                old_path = os.path.join(OUTPUT_FOLDER, old_dir)
                try:
                    shutil.rmtree(old_path)
                except Exception as _spb_ex:
                    _spb_swallow('render@L5689', _spb_ex)
        except Exception as _spb_ex:
            _spb_swallow('render@L5691', _spb_ex)

        recolor_rules = data.get("recolor_rules", [])
        recolor_mask_rle = data.get("recolor_mask", None)
        recolor_mask_has_include = data.get("recolor_mask_has_include", False)

        logger.info(f"Job {job_id}: {len(zones)} zones, paint={os.path.basename(paint_file)}"
                     f", wear={wear_level}"
                     f"{f', recolor={len(recolor_rules)} rules' if recolor_rules else ''}"
                     f"{', +mask' if recolor_mask_rle else ''}")
        # Log each zone's render path for diagnostics
        for i, z in enumerate(zones):
            if z.get("zone_spec_map"):
                _zsm_path = z.get("zone_spec_map")
                if os.path.exists(_zsm_path):
                    z["zone_spec_map_strength"] = _clamp(z.get("zone_spec_map_strength"), 0.0, 1.0, 1.0)
                else:
                    logger.warning(f"Zone spec map not found for render zone '{z.get('name', 'Zone')}': {_zsm_path}")
                    z.pop("zone_spec_map", None)
                    z.pop("zone_spec_map_strength", None)
            # Log overlay data if present
            for _overlay_pfx, _overlay_label in (
                ("second_base", "2nd_base"),
                ("third_base", "3rd_base"),
                ("fourth_base", "4th_base"),
                ("fifth_base", "5th_base"),
            ):
                if z.get(_overlay_pfx) or z.get(f"{_overlay_pfx}_color_source"):
                    logger.info(
                        f"  Zone {i+1} OVERLAY: {_overlay_label}={z.get(_overlay_pfx)}, "
                        f"color_src={z.get(f'{_overlay_pfx}_color_source')}, "
                        f"strength={z.get(f'{_overlay_pfx}_strength')}, "
                        f"blend={z.get(f'{_overlay_pfx}_blend_mode')}, "
                        f"color={z.get(f'{_overlay_pfx}_color')}, "
                        f"pattern={z.get(f'{_overlay_pfx}_pattern')!r}, "
                        f"pat_scale={z.get(f'{_overlay_pfx}_pattern_scale')}, "
                        f"pat_opacity={z.get(f'{_overlay_pfx}_pattern_opacity')}, "
                        f"pat_strength={z.get(f'{_overlay_pfx}_pattern_strength')}"
                    )
            # Determine which render path this zone will take
            if z.get('base'):
                path_label = f"base={z['base']} pattern={z.get('pattern','none')}"
            elif z.get('finish'):
                path_label = f"finish={z['finish']}"
                if z.get('pattern') and z.get('pattern') != 'none':
                    path_label += f" +overlay={z['pattern']}"
            elif z.get('zone_spec_map'):
                path_label = f"zone spec source={os.path.basename(z['zone_spec_map'])}"
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
            except ValueError:
                raise
            except Exception as e:
                logger.warning(f"Job {job_id}: Recolor failed ({e}), using original paint")
                actual_paint_file = paint_file

        _rle_canvas_shape = None
        if any(z.get("region_mask") or z.get("source_layer_mask") or z.get("spatial_mask") for z in zones):
            _rle_canvas_shape = _image_rle_shape(actual_paint_file, "render paint")

        # Determine car folder name for export
        cfg = load_config()
        car_folder_name = cfg.get("active_car", "unknown")

        # Run the full pipeline (car + helmet + suit + wear + optional zip)
        # Decode spatial_mask RLE for each zone before engine call
        for z in zones:
            # Decode region_mask RLE (same as preview-render)
            if z.get("region_mask") and isinstance(z["region_mask"], (dict, str)):
                try:
                    z["region_mask"] = _decode_rle_mask_payload(
                        z["region_mask"], "render region_mask", expected_shape=_rle_canvas_shape
                    )
                except Exception as _rm_err_r:
                    raise ValueError(f"region_mask decode failed: {_rm_err_r}") from _rm_err_r

            # Decode source_layer_mask RLE (same as preview-render)
            if z.get("source_layer_mask") and isinstance(z["source_layer_mask"], (dict, str)):
                try:
                    z["source_layer_mask"] = _decode_cached_source_layer_mask(
                        z, "render source_layer_mask", expected_shape=_rle_canvas_shape
                    )
                except Exception as _slm_err:
                    raise ValueError(f"source_layer_mask decode failed: {_slm_err}") from _slm_err

            # Decode source_layer_rgb_png so the engine can color-match against
            # the layer's unblended pixels (Photoshop-correct behavior).
            if z.get("source_layer_rgb_png"):
                try:
                    z["source_layer_rgb"] = _decode_cached_source_layer_rgb(
                        z, "render source_layer_rgb_png", expected_shape=_rle_canvas_shape
                    )
                except Exception as _slr_err_r:
                    raise ValueError(f"source_layer_rgb decode failed: {_slr_err_r}") from _slr_err_r

            # Decode spatial_mask RLE
            if z.get("spatial_mask") and isinstance(z["spatial_mask"], (dict, str)):
                try:
                    z["spatial_mask"] = _decode_spatial_mask_payload(
                        z["spatial_mask"], "render spatial_mask", expected_shape=_rle_canvas_shape
                    )
                    # Engine uses region_mask first and skips color+spatial; when spatial is set, drop region_mask
                    z.pop("region_mask", None)
                except Exception as _spm_err_r:
                    raise ValueError(f"spatial_mask decode failed: {_spm_err_r}") from _spm_err_r

            # Decode pattern_strength_map RLE
            if z.get("pattern_strength_map") and isinstance(z["pattern_strength_map"], (dict, str)):
                try:
                    # [ULTRACODE 2026-08-22 M2] validated decoder (4096 cap).
                    psm_rle = z["pattern_strength_map"]
                    if isinstance(psm_rle, str):
                        psm_rle = json.loads(psm_rle)
                    z["pattern_strength_map"] = _decode_rle_mask_payload(
                        psm_rle, "render pattern_strength_map", max_shape=(512, 512))
                except Exception as _psm_err_r:
                    raise ValueError(f"pattern_strength_map decode failed: {_psm_err_r}") from _psm_err_r

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
                # [SPB-PERF 2026-08-06] compress_level=1. This PNG is a UI preview served
                # over localhost (an <img> src, plus the _latest_render copy) — nothing
                # reads its file size. PNG is lossless at every level, so the decoded
                # pixels are identical; level 6 -> 1 trades ~1MB of localhost transfer for
                # ~0.12s off the render request the user is waiting on.
                PILImage.open(_render_paint_src).save(_render_paint_png, compress_level=1)
        except Exception as _paint_png_err:
            logger.warning(f"Job {job_id}: failed to generate RENDER_paint.png: {_paint_png_err}")

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Track render statistics ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
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

        # ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ PERSIST latest render outputs so SHOKK save always has access ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
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
                except Exception as _spb_ex:
                    _spb_swallow('render@L5920', _spb_ex)
            logger.info(f"Job {job_id}: persisted latest render to _latest_render/")
        except Exception as _lr_e:
            logger.warning(f"Job {job_id}: failed to persist latest render: {_lr_e}")

        def _job_file_url(route_name, fname):
            return f"/{route_name}/{job_id}/{quote(fname, safe='')}"

        # Build preview URLs (scan job dir for all PNGs)
        preview_urls = {}
        for fname in os.listdir(job_dir):
            if fname.endswith('.png'):
                preview_urls[fname] = _job_file_url("preview", fname)

        # Build download URLs for all TGA files
        download_urls = {}
        for fname in os.listdir(job_dir):
            if fname.endswith('.tga'):
                key = fname.replace('.tga', '')
                download_urls[key] = _job_file_url("download", fname)
        advertised_download_files = {f"{key}.tga" for key in download_urls.keys()}

        # ZIP download URL
        zip_url = None
        if export_zip and "export_zip" in results:
            zip_name = os.path.basename(results["export_zip"])
            zip_url = _job_file_url("download", zip_name)

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
                # [SPB 2026-08-06 NOTE — do not "optimize" this by reading
                # results["car_spec"] instead of the file: that IS byte-identical
                # (write_tga_32bit -> PIL .convert("RGBA") round-trips all four channels
                # unchanged, verified), but it buys nothing, because THIS BLOCK IS NOT
                # PRODUCING FILES. Job dirs from before and after the attempt contain no
                # spec_metallic/roughness/clearcoat/mask.tga and no paint_base.tga, and no
                # "Channel TGA export failed" warning is logged — yet the route demonstrably
                # runs both before (RENDER_paint.png) and after (_latest_render persist) it.
                # Fix the reason it is dead before optimizing it.
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

        def _push_files_to_dir(target_dir, label="output"):
            """Copy rendered TGAs to a target directory with backup of originals."""
            denial = _external_write_denial(target_dir, f"render-{label.lower().replace(' ', '-')}")
            if denial:
                raise PermissionError(denial["error"])
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
                    retries = 8
                    for attempt in range(retries):
                        try:
                            shutil.copyfile(src, dst)
                            src_bytes = os.path.getsize(src)
                            dst_bytes = os.path.getsize(dst) if os.path.isfile(dst) else -1
                            def _render_copy_sha256(path):
                                digest = hashlib.sha256()
                                with open(path, "rb") as stream:
                                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                                        digest.update(chunk)
                                return digest.hexdigest()
                            src_sha256 = _render_copy_sha256(src)
                            dst_sha256 = _render_copy_sha256(dst) if os.path.isfile(dst) else ""
                            if src_bytes <= 0 or dst_bytes != src_bytes or dst_sha256 != src_sha256:
                                raise OSError(
                                    f"Copy verification failed for {dst_name}: source={src_bytes} bytes, "
                                    f"target={dst_bytes} bytes, exact_match={dst_sha256 == src_sha256}"
                                )
                            pushed.append(dst_name)
                            break
                        except OSError as e:
                            if attempt < retries - 1:
                                time.sleep(0.25 + attempt * 0.15) # Wait for iRacing/previewer to release the file
                            else:
                                hint = ""
                                if isinstance(e, PermissionError):
                                    hint = " Close iRacing preview/sim or any image viewer using the target TGA, then render again."
                                raise Exception(f"Failed to push {dst_name} after {retries} attempts: {str(e)}.{hint}")
            logger.info(f"{label}: pushed {len(pushed)} files to {target_dir}")
            return pushed

        # PRIMARY: Copy output TGAs to the user-specified output folder
        output_dir_status = None
        if output_dir_user and output_dir_user.strip():
            target = _coerce_output_dir(output_dir_user)
            if target:
                denial = _external_write_denial(target, "render-output-dir")
                if denial:
                    output_dir_status = {**denial, "suppressed": True}
                else:
                    try:
                        pushed = _push_files_to_dir(target, "Output Dir")
                        output_dir_status = {
                            "success": True,
                            "verified": True,
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
                    "path": os.path.normpath(output_dir_user.strip()),
                    "error": (f"iRacing output folder not found: {output_dir_user.strip()} — "
                              "set this to your iRacing car FOLDER (e.g. Documents\\iRacing\\paint\\<car>), not a file.")
                }

        # SECONDARY: iRacing Live Link. Prefer the visible output folder so
        # paint/spec always land in the same current car folder.
        live_link_status = None
        if use_live_link:
            car_path, active_car, live_link_error, live_link_source = _resolve_live_link_target(
                cfg, output_dir_user
            )

            if car_path:
                denial = _external_write_denial(car_path, "render-live-link")
                if denial:
                    live_link_status = {**denial, "suppressed": True, "source": live_link_source}
                else:
                    try:
                        pushed = _push_files_to_dir(car_path, "Live Link")
                        live_link_status = {
                            "success": True,
                            "verified": True,
                            "car": active_car,
                            "path": car_path,
                            "source": live_link_source,
                            "pushed_files": pushed,
                            "message": f"Pushed {len(pushed)} files to iRacing! Alt+Tab and Ctrl+R."
                        }
                    except Exception as e:
                        live_link_status = {
                            "success": False,
                            "car": active_car,
                            "path": car_path,
                            "source": live_link_source,
                            "error": str(e),
                        }
                        logger.error(f"Live Link error: {e}")
            else:
                live_link_status = {
                    "success": False,
                    "car": active_car,
                    "source": live_link_source,
                    "error": live_link_error,
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
                "helmet": False,
                "suit": False,
                "wear": wear_level > 0,
            },
        }
        if zip_url:
            result["export_zip_url"] = zip_url
        if output_dir_status:
            result["output_dir"] = output_dir_status
        if live_link_status:
            result["live_link"] = live_link_status

        # Cleanup: delete only unadvertised helper TGAs from the job dir.
        # Returned download_urls must remain valid until normal job cleanup.
        try:
            for fname in os.listdir(job_dir):
                if fname.endswith('.tga') and fname not in advertised_download_files:
                    try:
                        os.remove(os.path.join(job_dir, fname))
                    except Exception as _spb_ex:
                        _spb_swallow('render@L6145', _spb_ex)
        except Exception as _spb_ex:
            _spb_swallow('render@L6147', _spb_ex)

        return jsonify(result)

    except Exception as e:
        # Log the full traceback server-side only (never to the client - it
        # leaks absolute filesystem paths). The client gets a short, clean error.
        logger.error(f"Render error: {traceback.format_exc()}")
        # Finish Pack-aware check: a missing reference_textures pack must steer
        # the buyer to the in-app downloader, not surface a raw engine error.
        _pack_err = _detect_missing_finish_pack(e, zones if 'zones' in dir() else None)
        if _pack_err is not None:
            logger.warning(f"Render blocked by missing Finish Pack "
                           f"(pack={_pack_err.get('pack')}): {e}")
            return jsonify(_pack_err), 409
        return jsonify({"error": str(e)}), 500
    finally:
        # Release render lock so previews can resume. SERVERCORE-1 fix: only
        # release if THIS thread actually acquired it (have_lock), so we never
        # release a lock we don't own. The 429 timeout path returns before the
        # try block, so have_lock is guaranteed True whenever we reach here.
        if have_lock:
            try:
                _preview_render_lock.release()
            except RuntimeError as _spb_ex:
                _spb_swallow('render@L6172', _spb_ex)  # Already released (defensive)


def _photoshop_exchange_root():
    """Default folder for Photoshop round-trip: Documents/ShokkerPaintBooth/PhotoshopExchange."""
    return os.path.join(os.path.expanduser("~"), "Documents", "ShokkerPaintBooth", "PhotoshopExchange")


from server_routes.photoshop_export_routes import register_photoshop_export_routes
register_photoshop_export_routes(
    app,
    engine_getter=lambda: engine,
    output_folder_getter=lambda: OUTPUT_FOLDER,
    photoshop_exchange_root=_photoshop_exchange_root,
    repair_base_overlay_pattern_reactive_payload=lambda zone: _repair_base_overlay_pattern_reactive_payload(zone),
    convert_zone_keys=lambda zone: _convert_zone_keys(zone),
    max_zones_per_request=MAX_ZONES_PER_REQUEST,
    apply_paint_recolor=lambda paint_file, recolor_rules, job_dir, recolor_mask_rle=None, recolor_mask_has_include=False: apply_paint_recolor(
        paint_file, recolor_rules, job_dir, recolor_mask_rle, recolor_mask_has_include
    ),
    decode_rle_mask_payload=lambda payload, label, **kwargs: _decode_rle_mask_payload(payload, label, **kwargs),
    decode_source_layer_rgb_payload=lambda payload, label, **kwargs: _decode_source_layer_rgb_payload(payload, label, **kwargs),
    decode_spatial_mask_payload=lambda payload, label, **kwargs: _decode_spatial_mask_payload(payload, label, **kwargs),
    image_shape_getter=lambda path, label: _image_rle_shape(path, label),
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
    logger=logger,
)

from server_routes.photoshop_import_routes import register_photoshop_import_routes
register_photoshop_import_routes(
    app,
    exchange_root_getter=_photoshop_exchange_root,
    output_folder=OUTPUT_FOLDER,
    require_internal_request=_require_spb_internal_request,
    logger=logger,
)

from server_routes.render_file_routes import register_render_file_routes
# [SPB-RECENTS-001] rotating last-10 renders live under the writable output base.
RECENT_RENDERS_DIR = os.path.join(OUTPUT_FOLDER, 'recent_renders')
try:
    os.makedirs(RECENT_RENDERS_DIR, exist_ok=True)
except Exception as _spb_ex:
    _spb_swallow('<module>@L6215', _spb_ex)
register_render_file_routes(
    app,
    output_job_dir_resolver=_resolve_output_job_dir,
    logger=logger,
    recent_renders_dir=RECENT_RENDERS_DIR,
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
)

### ===== SWATCH GENERATION =====
SWATCH_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swatches')
_swatch_files = []
if not _external_write_denial(SWATCH_FOLDER, "swatch-cache-startup"):
    os.makedirs(SWATCH_FOLDER, exist_ok=True)
    # Clear swatch cache on startup so rebuilt finishes get fresh thumbnails.
    _swatch_files = [f for f in os.listdir(SWATCH_FOLDER) if f.endswith('.png')]
    if _swatch_files:
        for f in _swatch_files:
            try:
                os.remove(os.path.join(SWATCH_FOLDER, f))
            except OSError as _spb_ex:
                _spb_swallow('<module>@L6236', _spb_ex)
logger.info(f"Cleared {len(_swatch_files)} cached swatches for fresh regeneration")

from server_routes.swatch_routes import register_swatch_routes
register_swatch_routes(
    app,
    engine_getter=lambda: engine,
    thumbnail_dir_getter=lambda: THUMBNAIL_DIR,
    swatch_folder_getter=lambda: SWATCH_FOLDER,
    swatch_cache=_SWATCH_CACHE,
    swatch_cache_lock=_SWATCH_CACHE_LOCK,
    swatch_cache_token=_swatch_cache_token,
    render_swatch_bytes=lambda finish_type, finish_key, color_hex, size, seed: _render_swatch_bytes(finish_type, finish_key, color_hex, size, seed),
    render_fast_split_swatch_bytes=lambda finish_type, finish_key, color_hex, size, seed: _render_fast_split_swatch_bytes(finish_type, finish_key, color_hex, size, seed),
    render_picker_split_snapshot_bytes=lambda finish_type, finish_key, color_hex, size, seed: _render_picker_split_snapshot_bytes(finish_type, finish_key, color_hex, size, seed),
    picker_split_static_path=lambda finish_type, finish_key: _picker_split_static_path(finish_type, finish_key),
    read_picker_split_png_bytes=lambda static_path, output_size: _read_picker_split_png_bytes(static_path, output_size),
    truthy_env=_truthy_env,
    normalize_spec_result_to_rgba=lambda spec, shape, strict_shapes=False: _normalize_spec_result_to_rgba(spec, shape, strict_shapes=strict_shapes),
    invoke_monolithic_spec_fn=lambda spec_fn, shape, mask, seed, sm, reg_entry=None: _invoke_monolithic_spec_fn(spec_fn, shape, mask, seed, sm, reg_entry=reg_entry),
    logger=logger,
    picker_finish_renderer_hash=lambda finish_type, finish_key: _picker_finish_renderer_hash(finish_type, finish_key),
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
    quality_write_guard=lambda items: _require_wilds_picker_write_quality(items),
)


_FULL_DNA_EXPORT_JOB = {
    "process": None,
    "status_file": None,
    "started_at": None,
}


def _full_dna_status_path():
    return os.path.join(SERVER_DIR, "docs", "DNA_FINISH_EXPORTS", "_latest_status.json")


def _read_full_dna_status():
    path = _FULL_DNA_EXPORT_JOB.get("status_file") or _full_dna_status_path()
    payload = {
        "status": "idle",
        "running": False,
        "statusFile": path,
    }
    proc = _FULL_DNA_EXPORT_JOB.get("process")
    if proc is not None and proc.poll() is None:
        payload["status"] = "running"
        payload["running"] = True
    elif proc is not None:
        payload["exitCode"] = proc.returncode
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_payload = json.load(f)
            payload.update(file_payload)
            payload["running"] = bool(proc is not None and proc.poll() is None)
        except Exception as exc:
            payload["statusReadError"] = str(exc)
    return payload


from server_routes.finish_viewer_recent_routes import register_finish_viewer_latest_routes
register_finish_viewer_latest_routes(
    app,
    output_folder_getter=lambda: OUTPUT_FOLDER,
    full_dna_job=_FULL_DNA_EXPORT_JOB,
    full_dna_status_path_getter=_full_dna_status_path,
    full_dna_status_reader=_read_full_dna_status,
    rate_limit=_rate_limit,
    safe_int=_safe_int,
    server_dir=SERVER_DIR,
    sys_executable=sys.executable,
    logger=logger,
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
)


def _candidate_iracing_roots():
    candidates = []
    for value in (
        os.environ.get("IRACING_ROOT"),
        os.environ.get("IRACING_INSTALL"),
        r"C:\iRacing",
        r"D:\iRacing",
    ):
        if value:
            candidates.append(value)
    for drive in "EFGHI":
        candidates.append(f"{drive}:\\iRacing")

    seen = set()
    roots = []
    for path in candidates:
        norm = os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
        key = os.path.normcase(norm)
        if key not in seen:
            seen.add(key)
            roots.append(norm)
    return roots


def _windows_personal_documents_dir():
    """Return Windows' redirected Documents folder when Explorer defines one."""

    if os.name != "nt":
        return None
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            raw, _value_type = winreg.QueryValueEx(key, "Personal")
        resolved = os.path.abspath(os.path.expandvars(str(raw or "").strip()))
        return resolved or None
    except (OSError, ImportError, TypeError, ValueError):
        return None


def _iracing_documents_dir():
    """Find the real ``Documents/iRacing`` root, including redirected folders.

    ``~/Documents`` is common, but Windows can redirect Documents into OneDrive.
    Easy Spec Sculpt's verified install and car discovery must resolve the same
    root or a successful copy can land somewhere iRacing never reads.
    """

    candidates = [os.path.join(os.path.expanduser("~"), "Documents")]
    redirected = _windows_personal_documents_dir()
    if redirected:
        candidates.append(redirected)
    for env_name in ("OneDriveConsumer", "OneDriveCommercial", "OneDrive"):
        root = os.environ.get(env_name)
        if root:
            candidates.append(os.path.join(root, "Documents"))

    seen = set()
    for candidate in candidates:
        # Each candidate is already rooted. Avoid expanding it a second time;
        # besides being redundant, that makes test/home redirection shims turn
        # a complete ``.../Documents`` path back into the home directory.
        documents = os.path.abspath(os.path.expandvars(candidate))
        key = os.path.normcase(documents)
        if key in seen:
            continue
        seen.add(key)
        docs = os.path.join(documents, "iRacing")
        if os.path.isdir(docs):
            return docs
    return None


# SPB-SIMPLIFY-2026-07-18 (owner): sniff the standard iRacing paint folders so the
# header can auto-detect which car model the user paints. Most recently modified
# first == most likely the car they're working on right now.
@app.route('/api/iracing-paint-cars')
def api_iracing_paint_cars():
    cars = []
    docs = _iracing_documents_dir()
    paint_root = os.path.join(docs, "paint") if docs else None
    if paint_root and os.path.isdir(paint_root):
        try:
            with os.scandir(paint_root) as entries:
                for entry in entries:
                    if not entry.is_dir():
                        continue
                    try:
                        mtime = entry.stat().st_mtime
                    except OSError:
                        mtime = 0
                    cars.append({
                        "name": entry.name,
                        "path": entry.path,
                        "mtime": mtime,
                    })
        except OSError as _spb_ex:
            _spb_swallow('api_iracing_paint_cars@L6412', _spb_ex)
    cars.sort(key=lambda c: c["mtime"], reverse=True)
    return jsonify({"paint_root": paint_root, "cars": cars})


# SPB-SIMPLIFY-2026-07-20 (owner request): guess the user's iRacing customer ID from the
# filenames already sitting in their paint folders. iRacing's own convention encodes it:
#   car_<custid>.tga       -> sim-stamped-number scheme for that car
#   car_num_<custid>.tga   -> custom-number scheme for that car
# The ID that appears across the most car folders is almost certainly the user; whether
# car_num_ files dominate tells us if they run custom numbers. This is a HINT only — the
# client fills the header field just once, only when it's empty, and manual entry always wins.
@app.route('/api/iracing-id-detect')
def api_iracing_id_detect():
    import re as _re
    votes = {}          # id -> set of folder names it appears in
    custom_votes = {}   # id -> set of folder names with car_num_<id>
    folders_scanned = 0
    docs = _iracing_documents_dir()
    paint_root = os.path.join(docs, "paint") if docs else None
    pat = _re.compile(r"^car_(num_)?(\d{4,9})\.tga$", _re.IGNORECASE)
    if paint_root and os.path.isdir(paint_root):
        try:
            with os.scandir(paint_root) as entries:
                for entry in entries:
                    if not entry.is_dir():
                        continue
                    folders_scanned += 1
                    try:
                        for fname in os.listdir(entry.path):
                            m = pat.match(fname)
                            if not m:
                                continue
                            cust_id = m.group(2)
                            votes.setdefault(cust_id, set()).add(entry.name)
                            if m.group(1):
                                custom_votes.setdefault(cust_id, set()).add(entry.name)
                    except OSError as _spb_ex:
                        _spb_swallow('api_iracing_id_detect@L6450', _spb_ex); continue
        except OSError as _spb_ex:
            _spb_swallow('api_iracing_id_detect@L6452', _spb_ex)
    ranked = sorted(votes.items(), key=lambda kv: len(kv[1]), reverse=True)
    best_id, best_folders = (ranked[0][0], sorted(ranked[0][1])) if ranked else (None, [])
    runner_up_count = len(ranked[1][1]) if len(ranked) > 1 else 0
    custom_count = len(custom_votes.get(best_id, set())) if best_id else 0
    return jsonify({
        "paint_root": paint_root,
        "folders_scanned": folders_scanned,
        "best_id": best_id,
        "best_folder_count": len(best_folders),
        "best_folders": best_folders[:12],
        "runner_up_count": runner_up_count,
        # confident = clearly the dominant ID, not a tie with someone else's shared scheme
        "confident": bool(best_id) and len(best_folders) >= 1 and len(best_folders) >= 2 * max(1, runner_up_count) - 1,
        "custom_number_folders": custom_count,
        "runs_custom_numbers": bool(best_id) and custom_count * 2 >= len(best_folders),
    })


def _pe_export_names(dll_path):
    """Small PE export reader so we do not need dumpbin/extra tools."""
    import struct

    with open(dll_path, "rb") as fh:
        data = fh.read()
    if len(data) < 0x40 or data[:2] != b"MZ":
        return []
    peoff = struct.unpack_from("<I", data, 0x3C)[0]
    if data[peoff:peoff + 4] != b"PE\0\0":
        return []
    coff = peoff + 4
    _machine, sections_count, _ts, _sym, _sym_count, opt_size, _chars = struct.unpack_from("<HHIIIHH", data, coff)
    opt = coff + 20
    magic = struct.unpack_from("<H", data, opt)[0]
    data_dir = opt + (112 if magic == 0x20B else 96)
    export_rva, _export_size = struct.unpack_from("<II", data, data_dir)
    if not export_rva:
        return []

    sections = []
    section_off = opt + opt_size
    for i in range(sections_count):
        off = section_off + i * 40
        virtual_size, virtual_address, raw_size, raw_ptr = struct.unpack_from("<IIII", data, off + 8)
        sections.append((virtual_address, max(virtual_size, raw_size), raw_ptr))

    def rva_to_offset(rva):
        for virtual_address, size, raw_ptr in sections:
            if virtual_address <= rva < virtual_address + size:
                return raw_ptr + (rva - virtual_address)
        raise ValueError(f"RVA outside sections: {rva:x}")

    export_off = rva_to_offset(export_rva)
    _flags, _time, _major, _minor, _name_rva, _base, _num_funcs, names_count, _funcs_rva, names_rva, _ords_rva = struct.unpack_from("<IIHHIIIIIII", data, export_off)
    names_off = rva_to_offset(names_rva)
    exports = []
    for i in range(names_count):
        name_rva = struct.unpack_from("<I", data, names_off + i * 4)[0]
        name_off = rva_to_offset(name_rva)
        end = data.index(b"\0", name_off)
        try:
            exports.append(data[name_off:end].decode("ascii"))
        except UnicodeDecodeError as _spb_ex:
            _spb_swallow('_pe_export_names@L6515', _spb_ex)
    return sorted(exports)


def _asar_file_text(asar_path, archive_path, max_chars=120000):
    import struct

    with open(asar_path, "rb") as fh:
        blob = fh.read()
    if len(blob) < 16:
        return ""
    header_size = struct.unpack_from("<I", blob, 12)[0]
    header = json.loads(blob[16:16 + header_size].decode("utf-8"))
    node = header
    for part in archive_path.split("/"):
        node = node.get("files", {}).get(part)
        if not node:
            return ""
    offset = int(node.get("offset", 0))
    size = int(node.get("size", 0))
    data_start = 16 + header_size
    raw = blob[data_start + offset:data_start + offset + size]
    return raw[:max_chars].decode("utf-8", errors="replace")


def _iracing_ui_summary(root):
    ui_dir = os.path.join(root, "ui")
    dll_path = os.path.join(ui_dir, "iRacingViewer.dll")
    asar_path = os.path.join(ui_dir, "resources", "app.asar")
    exports = []
    package = {}
    preload_calls = []
    main_signals = []

    if os.path.isfile(dll_path):
        try:
            exports = _pe_export_names(dll_path)
        except Exception as exc:
            logger.warning(f"[iracing-viewer-info] DLL export read failed: {exc}")

    if os.path.isfile(asar_path):
        try:
            package_text = _asar_file_text(asar_path, "package.json", max_chars=20000)
            if package_text:
                package = json.loads(package_text)
            preload = _asar_file_text(asar_path, "compiled/preload.js", max_chars=20000)
            for call in (
                "viewerCreateView",
                "viewerLoadObject",
                "viewerPaintItem",
                "viewerResize",
                "viewerDeleteView",
                "viewerSetFrameWindowBGColor",
                "viewerSetPathDetails",
            ):
                if call in preload:
                    preload_calls.append(call)
            main = _asar_file_text(asar_path, "compiled/main.js", max_chars=120000)
            for signal in (
                "iRacingViewer.dll",
                "viewerSupportBegin",
                "viewerLoadBackgroundObject",
                "viewerLoadObject",
                "viewerPaintItem",
                "getCarWebImage",
                "paintChanged",
                "specMapChange",
            ):
                if signal in main:
                    main_signals.append(signal)
        except Exception as exc:
            logger.warning(f"[iracing-viewer-info] ASAR read failed: {exc}")

    viewer_exports = [name for name in exports if name.startswith("viewer")]
    return {
        "ui_dir": ui_dir,
        "viewer_dll": dll_path if os.path.isfile(dll_path) else None,
        "viewer_dll_export_count": len(exports),
        "viewer_exports": viewer_exports,
        "web_image_export": "getCarWebImage" in exports,
        "asar": asar_path if os.path.isfile(asar_path) else None,
        "electron_app": package.get("name"),
        "electron_version": package.get("version"),
        "preload_calls": preload_calls,
        "main_signals": main_signals,
    }


def _iracing_car_package_summary(root, limit=180):
    cars_dir = os.path.join(root, "cars")
    web_cars_dir = os.path.join(root, "httproot", "cars")
    docs_dir = _iracing_documents_dir()
    paint_dir = os.path.join(docs_dir, "paint") if docs_dir else None
    packages = []
    dat_count = 0
    total_bytes = 0
    web_dat_count = 0

    if os.path.isdir(cars_dir):
        for current, _dirs, files in os.walk(cars_dir):
            for name in files:
                if not name.lower().endswith(".dat"):
                    continue
                dat_count += 1
                path = os.path.join(current, name)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    size = 0
                total_bytes += size
                if len(packages) < limit:
                    rel = os.path.relpath(current, cars_dir).replace(os.sep, "\\")
                    car_key = rel if rel != "." else os.path.splitext(name)[0]
                    paint_key = car_key.replace("\\", " ")
                    packages.append({
                        "car_key": car_key,
                        "paint_folder": paint_key,
                        "dat": os.path.relpath(path, root).replace(os.sep, "\\"),
                        "dat_mb": round(size / (1024 * 1024), 2),
                        "paint_dir_exists": bool(paint_dir and os.path.isdir(os.path.join(paint_dir, paint_key))),
                    })

    if os.path.isdir(web_cars_dir):
        for _current, _dirs, files in os.walk(web_cars_dir):
            web_dat_count += sum(1 for name in files if name.lower().endswith(".dat"))

    return {
        "cars_dir": cars_dir if os.path.isdir(cars_dir) else None,
        "httproot_cars_dir": web_cars_dir if os.path.isdir(web_cars_dir) else None,
        "dat_count": dat_count,
        "web_dat_count": web_dat_count,
        "total_dat_gb": round(total_bytes / (1024 * 1024 * 1024), 2),
        "packages_sample": packages,
        "packages_sample_limit": limit,
    }


from server_routes.paint_upload_routes import register_paint_upload_routes
register_paint_upload_routes(
    app,
    output_folder=OUTPUT_FOLDER,
    temp_file_path=_spb_temp_file_path,
    logger=logger,
)


def _parse_bool_form(val):
    if val is None:
        return None
    s = str(val).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off", ""):
        return False
    return bool(val)


def _resolve_live_link_target(cfg, output_dir_user=""):
    """Choose the iRacing folder for Live Link pushes.

    The visible header output folder is the user's current car target. A stale
    saved active car must never override it, because that can put specs in a
    different car folder than the paint.
    """
    output_dir = str(output_dir_user or "").strip()
    if output_dir:
        # The visible field is USER-pasted; accept a folder OR a file path
        # (...\car_num_<id>.tga) and resolve to the containing folder so a
        # whole-path paste never produces "iRacing Car Folder not found".
        resolved = _coerce_output_dir(output_dir)
        if resolved:
            active_car = os.path.basename(resolved.rstrip("\\/"))
            return resolved, active_car, None, "output_dir"
        target = os.path.normpath(output_dir)
        active_car = os.path.basename(target.rstrip("\\/"))
        return (
            None,
            active_car,
            f"Visible iRacing Car Folder not found (point to a FOLDER, not a file): {target}",
            "output_dir",
        )

    active_car = cfg.get("active_car")
    car_path = cfg.get("car_paths", {}).get(active_car) if active_car else None
    if car_path:
        # car_path is config-derived but may have been saved from a pasted
        # file path; coerce file->folder leniently while keeping config logic.
        resolved = _coerce_output_dir(car_path)
        if resolved:
            return resolved, active_car, None, "saved_active_car"
        car_path = os.path.normpath(car_path)
        return (
            None,
            active_car,
            f"Saved Live Link folder not found for {active_car} (point to a FOLDER, not a file): {car_path}",
            "saved_active_car",
        )

    return (
        None,
        None,
        "No active car configured. Set the iRacing Car Folder in the header or Live Link settings.",
        "saved_active_car",
    )


def _push_standard_car_outputs_to_dir(job_dir, iracing_id, car_prefix, target_dir, label="output"):
    """Transactionally install the exact expected 2048 paint + spec pair."""
    denial = _external_write_denial(target_dir, f"spec-sculpt-{label.lower().replace(' ', '-')}")
    if denial:
        raise PermissionError(denial["error"])
    paint_path = os.path.join(job_dir, f"{car_prefix}_{iracing_id}.tga")
    spec_path = os.path.join(job_dir, f"car_spec_{iracing_id}.tga")
    try:
        result = deploy_iracing_tga_pair(
            paint_path,
            spec_path,
            target_dir,
            str(iracing_id),
            paint_prefix=car_prefix,
        )
    except PairDeploymentError as exc:
        hint = " Close iRacing preview/sim or any image viewer using the target TGA, then try again." if exc.code in {"staging_failed", "commit_failed_rolled_back"} else ""
        raise Exception(f"{label} exact paint + spec install failed ({exc.code}): {exc}.{hint}") from exc
    logger.info(f"{label}: transaction {result['transaction_id']} verified {len(result['deployed'])} files in {target_dir}")
    return result["deployed"]


def _deploy_job_dir_to_iracing_paint(job_dir, car_folder, iracing_id):
    """Copy every ``*.tga`` into the discovered iRacing paint car folder.

    Shared by ``POST /deploy-to-iracing`` and Spec Sculpt ``deploy_car_folder``.
    Returns dict with ``success`` bool; on failure includes ``error`` (HTTP layer maps codes).
    """
    if not job_dir or not os.path.isdir(job_dir):
        return {"success": False, "error": "invalid_job_dir"}
    ok_id, norm_id, id_err = _validate_iracing_id(iracing_id)
    if not ok_id:
        return {"success": False, "error": id_err}
    iracing_id = norm_id
    car_folder = str(car_folder or "").strip()
    if not car_folder:
        return {"success": False, "error": "Missing car_folder"}
    if "/" in car_folder or "\\" in car_folder or ".." in car_folder:
        return {"success": False, "error": "invalid car_folder name"}
    if _is_scrubbed_iracing_gear_folder(car_folder):
        return {
            "success": False,
            "error": "helmet/suit folders are not supported SPB car targets in this build",
        }
    documents_dir = _iracing_documents_dir()
    if not documents_dir:
        return {
            "success": False,
            "verified": False,
            "error": "iRacing Documents folder not found (checked standard and redirected Documents locations)",
        }
    iracing_paint = os.path.join(documents_dir, "paint")
    target_dir = os.path.join(iracing_paint, car_folder)
    denial = _external_write_denial(target_dir, "iracing-paint-deploy")
    if denial:
        return denial
    os.makedirs(target_dir, exist_ok=True)

    available = []
    for prefix in ("car_num", "car"):
        candidate = os.path.join(job_dir, f"{prefix}_{iracing_id}.tga")
        if os.path.isfile(candidate):
            available.append((prefix, candidate))
    spec_source = os.path.join(job_dir, f"car_spec_{iracing_id}.tga")
    if len(available) != 1 or not os.path.isfile(spec_source):
        return {
            "success": False,
            "verified": False,
            "error": (
                "Exact iRacing deployment requires one paint file "
                f"(car_{iracing_id}.tga or car_num_{iracing_id}.tga) plus car_spec_{iracing_id}.tga; "
                f"found {len(available)} paint candidate(s) and spec={os.path.isfile(spec_source)}"
            ),
            "target": target_dir.replace("\\", "/"),
        }
    paint_prefix, paint_source = available[0]
    try:
        result = deploy_iracing_tga_pair(
            paint_source,
            spec_source,
            target_dir,
            iracing_id,
            paint_prefix=paint_prefix,
        )
    except PairDeploymentError as exc:
        logger.error(f"[deploy-job-dir] exact pair failed ({exc.code}): {exc}")
        return {
            "success": False,
            "verified": False,
            "error": str(exc),
            "code": exc.code,
            "target": target_dir.replace("\\", "/"),
        }
    result["car_folder"] = car_folder
    # [2026-08-09 S22] iRacing compiles paint .tga files into .mip. SPB never
    # writes or reads .mip (zero references anywhere in this codebase), so a
    # .mip left over from an earlier load can be OLDER than the .tga we just
    # wrote. If iRacing prefers it, the painter sees "INSTALLED + LOCKED IN"
    # and then loads a car still wearing the previous spec. We do not delete
    # anything in the owner's paint folder on a guess - we report it, and the
    # UI tells them which file to move.
    stale_mips = []
    try:
        newest_write = 0.0
        for name in (f"{paint_prefix}_{iracing_id}.tga", f"car_spec_{iracing_id}.tga"):
            candidate = os.path.join(target_dir, name)
            if os.path.isfile(candidate):
                newest_write = max(newest_write, os.path.getmtime(candidate))
        for name in os.listdir(target_dir):
            if not name.lower().endswith(".mip"):
                continue
            if iracing_id not in name:
                continue
            full = os.path.join(target_dir, name)
            mtime = os.path.getmtime(full)
            if newest_write and mtime < newest_write - 1:
                stale_mips.append({"name": name, "age_seconds": int(newest_write - mtime)})
    except Exception as exc:  # never let a warning break a good deploy
        logger.warning(f"[deploy-job-dir] stale .mip scan skipped: {exc}")
    if stale_mips:
        result["stale_mips"] = stale_mips
        logger.warning(
            "[deploy-job-dir] %d stale .mip file(s) alongside the new .tga pair: %s"
            % (len(stale_mips), ", ".join(m["name"] for m in stale_mips))
        )
    result["message"] = f"Deployed and verified the paint + spec pair in {car_folder}. Alt+Tab to iRacing and press Ctrl+R!"
    logger.info(f"[deploy-job-dir] transaction {result['transaction_id']} -> {target_dir}")
    return result


def _spec_sculpt_paint_preview_data_url(pil_img, max_edge=480):
    """Downscale (bounded) JPEG data URL for browser preview of source paint."""
    from io import BytesIO
    import base64
    from PIL import Image as PILImage

    try:
        img = pil_img
        if getattr(img, "mode", None) == "RGBA":
            bg = PILImage.new("RGB", img.size, (26, 28, 34))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif getattr(img, "mode", None) != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > max_edge:
            r = max_edge / float(max(w, h))
            img = img.resize((max(1, int(w * r)), max(1, int(h * r))), PILImage.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=86, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


# SPB-BETA-2026-07-21: Easy Spec Sculpt's eyedropper must sample the native
# 2048 paint, never the lossy 480px JPEG used only for display. Path-backed
# sources receive a short-lived opaque capability from /analyze; raw path reads
# remain internal-only and constrained to the app/iRacing roots below.
SPEC_SCULPT_SOURCE_TOKEN_TTL_SECONDS = 12 * 60 * 60
SPEC_SCULPT_SOURCE_TOKEN_LIMIT = 48
_spec_sculpt_source_tokens = OrderedDict()
_spec_sculpt_source_tokens_lock = threading.Lock()


def _remember_spec_sculpt_source(path):
    """Return an opaque, process-local capability for an already-opened source."""
    real_path = os.path.realpath(os.path.abspath(path))
    stat = os.stat(real_path)
    now = time.time()
    token = uuid.uuid4().hex + uuid.uuid4().hex
    record = {
        "path": real_path,
        "size": int(stat.st_size),
        "mtime_ns": int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))),
        "expires": now + SPEC_SCULPT_SOURCE_TOKEN_TTL_SECONDS,
    }
    with _spec_sculpt_source_tokens_lock:
        expired = [
            key for key, value in _spec_sculpt_source_tokens.items()
            if float(value.get("expires", 0)) <= now
        ]
        for key in expired:
            _spec_sculpt_source_tokens.pop(key, None)
        _spec_sculpt_source_tokens[token] = record
        _spec_sculpt_source_tokens.move_to_end(token)
        while len(_spec_sculpt_source_tokens) > SPEC_SCULPT_SOURCE_TOKEN_LIMIT:
            _spec_sculpt_source_tokens.popitem(last=False)
    return token


def _resolve_spec_sculpt_source_token(token):
    """Resolve an opaque source capability and reject expired/changed files."""
    token = str(token or "").strip()
    if not token:
        return None, "Missing source_token"
    now = time.time()
    with _spec_sculpt_source_tokens_lock:
        record = _spec_sculpt_source_tokens.get(token)
        if record is None:
            return None, "Unknown source_token; analyze the paint again"
        if float(record.get("expires", 0)) <= now:
            _spec_sculpt_source_tokens.pop(token, None)
            return None, "Expired source_token; analyze the paint again"
        _spec_sculpt_source_tokens.move_to_end(token)
        record = dict(record)
    path = record["path"]
    try:
        stat = os.stat(path)
    except OSError:
        return None, "Source paint is no longer available"
    mtime_ns = int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)))
    if int(stat.st_size) != record["size"] or mtime_ns != record["mtime_ns"]:
        with _spec_sculpt_source_tokens_lock:
            _spec_sculpt_source_tokens.pop(token, None)
        return None, "Source paint changed; analyze it again before sampling"
    return path, None


def _spec_sculpt_sample_allowed_roots():
    """Directories a raw-path color-sample request may read from."""
    roots = [SERVER_DIR, OUTPUT_FOLDER, SPB_TEMP_FOLDER]
    home = os.path.expanduser("~")
    roots.append(os.path.join(home, "Documents", "ShokkerPaintBooth"))
    iracing_root = _iracing_documents_dir()
    if iracing_root:
        roots.extend([
            os.path.join(iracing_root, "paint"),
            os.path.join(iracing_root, "paints"),
        ])
    result = []
    for root in roots:
        if not root:
            continue
        real_root = os.path.realpath(os.path.abspath(root))
        key = os.path.normcase(real_root)
        if key not in {os.path.normcase(item) for item in result}:
            result.append(real_root)
    return result


def _resolve_spec_sculpt_sample_path(raw_path):
    """Resolve a raw path without permitting traversal or root-prefix tricks."""
    if not raw_path or not isinstance(raw_path, str):
        return None, "Missing paint_file"
    if ".." in raw_path.replace("\\", "/").split("/"):
        return None, "Path traversal detected"
    try:
        real_path = os.path.realpath(os.path.abspath(os.path.expanduser(raw_path)))
    except (OSError, TypeError, ValueError):
        return None, "Invalid paint_file path"
    real_key = os.path.normcase(real_path)
    for root in _spec_sculpt_sample_allowed_roots():
        root_key = os.path.normcase(root)
        try:
            if os.path.commonpath([real_key, root_key]) == root_key:
                return real_path, None
        except ValueError as _spb_ex:
            _spb_swallow('_resolve_spec_sculpt_sample_path@L6979', _spb_ex); continue
    return None, "Path outside allowed paint directories"


def _spec_sculpt_native_color_sample(pil_img, nx, ny, radius=2):
    """Sample one material color from the full-resolution source image.

    The selected color is always an actual source pixel. A 5x5 default window
    rejects isolated anti-alias/noise pixels, while a center-family occupying at
    least 20% of the window wins so a deliberate click on a fine stripe is not
    replaced by the surrounding body color.
    """
    import math
    from collections import defaultdict

    if not math.isfinite(float(nx)) or not math.isfinite(float(ny)):
        raise ValueError("x and y must be finite normalized coordinates")
    nx = float(nx)
    ny = float(ny)
    if nx < 0.0 or nx > 1.0 or ny < 0.0 or ny > 1.0:
        raise ValueError("x and y must each be between 0 and 1")
    radius = max(1, min(6, int(radius)))
    image = pil_img.convert("RGB")
    width, height = image.size
    px = min(width - 1, max(0, int(nx * width)))
    py = min(height - 1, max(0, int(ny * height)))
    left = max(0, px - radius)
    top = max(0, py - radius)
    right = min(width - 1, px + radius)
    bottom = min(height - 1, py + radius)
    center_rgb = tuple(int(value) for value in image.getpixel((px, py)))

    # Eight-level buckets preserve real authored shades while grouping tiny
    # encoder/anti-alias variations. Representatives below remain real pixels.
    buckets = defaultdict(list)
    for sy in range(top, bottom + 1):
        for sx in range(left, right + 1):
            rgb = tuple(int(value) for value in image.getpixel((sx, sy)))
            buckets[tuple(value // 8 for value in rgb)].append(rgb)

    def representative(values):
        means = [sum(pixel[channel] for pixel in values) / len(values) for channel in range(3)]
        return min(
            values,
            key=lambda pixel: sum((pixel[channel] - means[channel]) ** 2 for channel in range(3)),
        )

    center_bucket = tuple(value // 8 for value in center_rgb)
    total = sum(len(values) for values in buckets.values())
    ranked = sorted(
        (
            {
                "bucket": key,
                "rgb": representative(values),
                "count": len(values),
            }
            for key, values in buckets.items()
        ),
        key=lambda row: (
            -row["count"],
            sum((row["rgb"][channel] - center_rgb[channel]) ** 2 for channel in range(3)),
            row["rgb"],
        ),
    )
    center_row = next((row for row in ranked if row["bucket"] == center_bucket), None)
    selected = center_row if center_row and center_row["count"] / total >= 0.20 else ranked[0]

    def public_row(row):
        rgb = [int(value) for value in row["rgb"]]
        return {
            "rgb": rgb,
            "hex": "#{:02X}{:02X}{:02X}".format(*rgb),
            "count": int(row["count"]),
            "coverage": round(row["count"] / total, 4),
        }

    return {
        "rgb": [int(value) for value in selected["rgb"]],
        "hex": "#{:02X}{:02X}{:02X}".format(*selected["rgb"]),
        "center_rgb": [int(value) for value in center_rgb],
        "normalized": [nx, ny],
        "pixel": [px, py],
        "radius": radius,
        "bounds": [left, top, right, bottom],
        "resolution": [width, height],
        "method": "center-guided-local-mode",
        "confidence": round(selected["count"] / total, 4),
        "palette": [public_row(row) for row in ranked[:5]],
    }


@app.route('/api/spec-sculpt/presets', methods=['GET'])
def api_spec_sculpt_presets():
    """Catalog of blend-layer presets for the Spec Sculpt Lab UI."""
    try:
        from engine.spec_sculpt.presets import MAX_PRESET_STACK, SPEC_SCULPT_PRESETS

        presets_out = []
        for p in SPEC_SCULPT_PRESETS:
            presets_out.append({
                "id": p["id"],
                "label": p["label"],
                "description": p["description"],
                "category": p.get("category", "Blend layers"),
                "tags": list(p.get("tags") or []),
                "uses_chromatic": bool(p.get("uses_chromatic", True)),
            })
        return jsonify({
            "success": True,
            "max_selected": MAX_PRESET_STACK,
            "presets": presets_out,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# SHOKK THE WORLD (Spec Sculpt) — ~20 signature looks from one paint, at once.
# Each recipe is a small scratch-preset combo drawn from the 121-preset catalog
# (engine/spec_sculpt/presets.py). Preview-only + tiny size = fast batch; the
# chosen one is rendered full-res via the existing /api/spec-sculpt/generate.
# ---------------------------------------------------------------------------
SPEC_SCULPT_WORLD_RECIPES = [
    # 2026-06-01: now reference the curated real-finish presets (see engine/spec_sculpt/presets.py).
    {"label": "Mirror Chrome", "presets": [["mirror_chrome", 1.0]]},
    {"label": "Mercury Flow", "presets": [["mercury_flow", 1.0]]},
    {"label": "Radial Machined", "presets": [["radial_machined", 1.0]]},
    {"label": "Brushed Titanium", "presets": [["brushed_titanium", 1.0]]},
    {"label": "Obsidian Mirror", "presets": [["obsidian_mirror", 1.0]]},
    {"label": "Forged Carbon", "presets": [["forged_carbon", 1.0]]},
    {"label": "Carbon Fiber", "presets": [["carbon_fiber", 1.0]]},
    {"label": "Bakeneko Velvet", "presets": [["bakeneko_velvet", 1.0]]},
    {"label": "Matte Silk", "presets": [["matte_silk", 1.0]]},
    {"label": "Candy Poison", "presets": [["candy_poison", 1.0]]},
    {"label": "Cotton Candy", "presets": [["cotton_candy", 1.0]]},
    {"label": "Pearl Chaser", "presets": [["pearl_chaser", 1.0]]},
    {"label": "Ghost Scales", "presets": [["ghost_scales", 1.0]]},
    {"label": "Chaos Flake", "presets": [["chaos_flake", 1.0]]},
    {"label": "Hex Flake", "presets": [["hex_flake", 1.0]]},
    {"label": "Galaxy Sparkle", "presets": [["galaxy_sparkle", 1.0]]},
    {"label": "Metal Flake", "presets": [["metal_flake", 1.0]]},
    {"label": "Holographic", "presets": [["holographic", 1.0]]},
    {"label": "Arctic Chameleon", "presets": [["arctic_chameleon", 1.0]]},
    {"label": "Oil Slick Wave", "presets": [["oil_slick_wave", 1.0]]},
    {"label": "Spectral Rings", "presets": [["spectral_rings", 1.0]]},
    {"label": "Copper Flame", "presets": [["copper_flame", 1.0]]},
    {"label": "Marble Pearl", "presets": [["marble_pearl", 1.0]]},
    {"label": "Rose Gold", "presets": [["rose_gold", 1.0]]},
]


def _spec_sculpt_star_ids():
    """Finish ids the owner marked KEEP in the preset audit (boost them in the picker)."""
    try:
        from engine.spec_sculpt.presets import PRESET_CATALOG_BY_ID
        entries = _load_spec_sculpt_audit()
        stars = set()
        for pid, e in entries.items():
            if (e or {}).get("verdict") == "keep":
                for fid, _w in PRESET_CATALOG_BY_ID.get(pid, []):
                    stars.add(fid)
        return stars
    except Exception:
        return set()


def _spec_sculpt_world_variations(seed=9101, n=24):
    """Diverse Shokk-the-World recipes from the spec index; falls back to the curated list.

    Each recipe is ``{"label", "catalog": [[finish_id, 1.0]]}`` — the diversity picker
    chooses N maximally-different, above-quality finishes from the WHOLE library
    (engine/spec_sculpt/spec_index.py), weighting owner-KEEP finishes up.
    """
    try:
        from engine.spec_sculpt.spec_index import index_available, pick_diverse
        if index_available():
            picks = pick_diverse(n, seed=int(seed), star_ids=_spec_sculpt_star_ids())
            if picks:
                return [{"label": p["name"], "catalog": [[p["id"], 1.0]]} for p in picks]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[spec-sculpt] world picker fell back to curated list: {e}")
    return [{"label": r["label"], "presets": r["presets"]} for r in SPEC_SCULPT_WORLD_RECIPES]


@app.route('/api/spec-sculpt/world', methods=['GET'])
def api_spec_sculpt_world_recipes():
    """The 'Shokk the World' look list — diverse picks from the full spec library."""
    try:
        seed = _safe_int(request.args.get("seed"), 9101)
        n = max(6, min(40, _safe_int(request.args.get("n"), 24)))
        recipes = _spec_sculpt_world_variations(seed=seed, n=n)
        return jsonify({"success": True, "recipes": recipes, "count": len(recipes)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/spec-sculpt/batch', methods=['POST'])
def api_spec_sculpt_batch():
    """SHOKK THE WORLD for Spec Sculpt: render ~20 small spec PREVIEWS from one paint
    in a single request. No TGAs/jobs are written — the user picks one and the existing
    /api/spec-sculpt/generate builds the full 2048 job + deploy.

    Multipart: ``file`` / ``paint_file`` upload. JSON: ``{"paint_file": "/abs/path"}``.
    Optional ``variations`` (list of {label, presets|catalog|mode, [seed]}) overrides the curated set.
    Optional ``preview_size`` (default 320, clamped 160..512), ``seed`` (base), ``chromatic_shift``.
    ``fast_trace`` defaults on because this endpoint is a chooser, not a final export.
    ``tile_only`` returns one compact on-car image per choice instead of five proof images.
    """
    temp_created_path = None
    try:
        ct = (request.content_type or "").lower()
        json_body = request.get_json(silent=True) if ct.startswith("application/json") else None

        def gv(key, default=None):
            if json_body is not None:
                val = json_body.get(key)
                return default if val is None else val
            return request.form.get(key, default)

        base_seed = _safe_int(gv("seed"), 9101) & 0xFFFFFFFF
        chromatic = _parse_bool_form(gv("chromatic_shift"))
        if chromatic is None:
            chromatic = True
        preview_size = _safe_int(gv("preview_size"), 320)
        # SPB-BETA-2026-07-21: 160 is the authored-material chooser tier. The
        # on-car card is still relit/exported at 200px below, while heavyweight
        # catalog engines avoid their >=192 full-detail branch. Live full-library
        # sample: 12.1 s @240 (two 2.5 s tiles) -> sub-second material bakes @160.
        # The selected look remains a full 2048 render, so no export quality moves.
        preview_size = max(160, min(512, preview_size))
        fast_trace = _parse_bool_form(gv("fast_trace"))
        fast_trace = True if fast_trace is None else bool(fast_trace)
        tile_only = bool(_parse_bool_form(gv("tile_only")))

        # Resolve the variation list (client override or curated default).
        variations = None
        raw_var = gv("variations")
        if raw_var:
            if isinstance(raw_var, str):
                try:
                    variations = json.loads(raw_var)
                except Exception:
                    variations = None
            elif isinstance(raw_var, list):
                variations = raw_var
        if not variations:
            # Default = diverse picks from the full spec library (spec index).
            variations = _spec_sculpt_world_variations(seed=base_seed, n=24)
        variations = list(variations)[:24]  # hard cap

        # Resolve paint source (upload or path).
        paint_disk_path = None
        if json_body is not None:
            pf = str(gv("paint_file") or "").strip()
            if not pf:
                return jsonify({"success": False, "error": "JSON body requires paint_file (absolute path)"}), 400
            paint_disk_path = os.path.abspath(os.path.expanduser(pf))
        else:
            f = request.files.get('file') or request.files.get('paint_file')
            if f and f.filename:
                temp_created_path = _spb_temp_file_path(f"spec_sculpt_world_{uuid.uuid4().hex}_{f.filename}")
                f.save(temp_created_path)
                paint_disk_path = temp_created_path
            else:
                pf = str(gv("paint_file") or "").strip()
                if pf:
                    paint_disk_path = os.path.abspath(os.path.expanduser(pf))
        if not paint_disk_path or not os.path.isfile(paint_disk_path):
            return jsonify({"success": False, "error": f"paint_file not found: {paint_disk_path}"}), 400

        from engine.spec_sculpt.core import load_paint_rgb_float01
        from engine.spec_sculpt.generate import (
            scratch_spec_from_any_paint,
            fracture_spec_from_any_paint,
            candy_depth_spec_from_any_paint,
            zoned_auto_spec,
            apply_sculpt_mask,
            build_protect_mask,
            refine_sculpt_mask,
            auto_protect_mask_from_paint,
        )
        from engine.spec_sculpt.presets import normalize_preset_stack
        from engine.spec_sculpt.preview import spec_preview_png_data_urls

        # Load the paint ONCE at small size — reused for every variation.
        tex, orig_hw, final_hw = load_paint_rgb_float01(paint_disk_path, target_size=preview_size)

        # LAYER-AWARE SCULPT (2026-06-24): if a PSD + protected layer names came in, shield those
        # layers across EVERY look in the gallery too (built once, cached). Additive/guarded: no
        # PSD/names -> _protect_mask stays None and Shokk the World behaves exactly as before.
        _protect_mask = None
        try:
            _protect_raw = gv("protect_layers")
            if _protect_raw:
                if isinstance(_protect_raw, (list, tuple)):
                    _pnames = list(_protect_raw)
                else:
                    _s = str(_protect_raw).strip()
                    try:
                        _pnames = json.loads(_s)
                        if not isinstance(_pnames, list):
                            _pnames = [str(_pnames)]
                    except Exception:
                        _pnames = [x.strip() for x in _s.split(",") if x.strip()]
                _psd_src = str(gv("psd_path") or "").strip() or paint_disk_path
                _protect_mask = build_protect_mask(_psd_src, _pnames)
        except Exception:
            _protect_mask = None

        # #24 Mask refine: grow/contract protected region + boundary feather (shared across the gallery).
        try:
            _mask_grow = _safe_int(gv("mask_grow"), 0)
        except Exception:
            _mask_grow = 0
        try:
            _mf = gv("mask_feather")
            _mask_feather = max(0.0, min(12.0, float(_mf))) if _mf not in (None, "") else 2.0
        except (TypeError, ValueError):
            _mask_feather = 2.0
        # protected-decal finish (realism): default 'matte' keeps the legacy neutral (no behavior change).
        _PROTECT_MATS = {'matte': (0, 160, 0), 'satin': (105, 110, 140), 'gloss': (135, 45, 240), 'wet': (110, 35, 248), 'carbon': (70, 150, 55)}
        _protect_neutral = _PROTECT_MATS.get(str(gv("protect_material") or "matte").strip().lower(), (0, 160, 0))
        if _protect_mask is not None and _mask_grow:
            _protect_mask = refine_sculpt_mask(_protect_mask, _mask_grow)

        # auto-detect decals (no PSD): shield numbers/sponsors across the WHOLE gallery too, built once
        # from the shared tex and reused for every look. Guarded: returns None on a plain/busy car -> no-op.
        if _protect_mask is None and bool(_parse_bool_form(gv("auto_protect"))):
            try:
                _ap_str = max(0.3, min(2.0, float(gv("auto_protect_strength")))) if gv("auto_protect_strength") not in (None, "") else 1.0
            except (TypeError, ValueError):
                _ap_str = 1.0
            _protect_mask = auto_protect_mask_from_paint(tex, strength=_ap_str)
            if _protect_mask is not None and _mask_grow:
                _protect_mask = refine_sculpt_mask(_protect_mask, _mask_grow)

        from engine.spec_sculpt.catalog_blend import normalize_catalog_stack
        from engine.spec_sculpt.easy_material_layers import (
            apply_material_impact,
            apply_material_impact_to_report,
            composite_easy_color_layers,
            normalize_material_impact,
            normalize_material_scale,
            parse_easy_color_layers,
            pattern_tile_for_scale,
        )

        # [SPB-SPEC-SCULPT pick-a-look 2026-06-05] Realistic finish tiles for the "Pick a
        # look" grid: render each catalog pick on a CLEAN neutral swatch exactly like
        # regular SPB's picker swatches (vibrant + varied), so the grid leads with what the
        # finish actually looks like instead of only the warm red/green channel-viz. The
        # clearcoat-fixed spec map is still returned as previews.composite (secondary).
        from engine.registry import BASE_REGISTRY as _BR, MONOLITHIC_REGISTRY as _MR
        _base_reg = set(_BR.keys()); _mono_reg = set(_MR.keys())
        _swatch_canvas = max(192, min(320, preview_size))
        _swatch_png = None
        try:
            _swatch_png = _make_temp_catalog_paint_path(0.533, 0.533, 0.533, _swatch_canvas)
        except Exception as _se:
            logger.warning(f"[spec-sculpt/batch] clean-swatch setup failed: {_se}")

        def _paint_rgb_to_data_url(pr, *, compact_jpeg=False):
            import io as _io, base64 as _b64
            import numpy as _np
            from PIL import Image as _PImg
            a = _np.clip(pr, 0, 255).astype(_np.uint8)
            if a.ndim == 2:
                a = _np.stack([a] * 3, axis=-1)
            if a.shape[-1] > 3:
                a = a[:, :, :3]
            _b = _io.BytesIO()
            if compact_jpeg:
                _PImg.fromarray(a).save(_b, format='JPEG', quality=84, optimize=True, subsampling=1)
                _mime = 'image/jpeg'
            else:
                _PImg.fromarray(a).save(_b, format='PNG', optimize=True)
                _mime = 'image/png'
            return 'data:' + _mime + ';base64,' + _b64.b64encode(_b.getvalue()).decode('ascii')

        # ON-CAR preview: render each look on the USER'S loaded paint (relit with the finish's material)
        # so the grid shows how the finish reads on THEIR livery — not a grey swatch. (2026-06-26)
        import cv2 as _cv2
        import numpy as np
        try:
            from engine.spec_sculpt.sun_sweep import derive_micro_normal as _dmn, relight_frame as _relit
        except Exception:
            _dmn = _relit = None
        _car_px = max(200, min(360, preview_size))
        _tex_car = _cv2.resize(np.asarray(tex, np.float32), (_car_px, _car_px), interpolation=_cv2.INTER_AREA)

        def _on_car_render(spec_full, seed_):
            if _relit is None:
                return None
            sp = _cv2.resize(np.asarray(spec_full, np.uint8), (_car_px, _car_px), interpolation=_cv2.INTER_NEAREST)
            nrm = _dmn(_tex_car, sp, seed=int(seed_) & 0xFFFFFFFF)
            lit = np.asarray(_relit(_tex_car, sp, nrm, (0.34, 0.46, 0.82), ambient=0.22), np.float32)
            # keep the livery legible in a small tile even under dark materials (chrome/matte) by
            # screen-blending a little of the flat paint back in — the material lighting stays on top.
            # (the blend is stronger where the paint is DARK so black liveries don't read as a black box.)
            _pl = (0.34 + 0.20 * (1.0 - _tex_car))           # ~0.34 on white, ~0.54 on black
            out = np.clip(_tex_car * _pl + lit, 0.0, 1.0)
            return _paint_rgb_to_data_url(out * 255.0, compact_jpeg=tile_only)

        def _render_exact_named_look(kind, look_id, seed_, material_scale_, catalog_type_=None):
            """Render one named Easy material without gallery-only emphasis."""
            kind = str(kind or "").strip().lower()
            look_id = str(look_id or "").strip()
            seed_ = int(seed_) & 0xFFFFFFFF
            material_scale_ = normalize_material_scale(material_scale_, 1.0)
            if kind == "mode":
                if look_id == "zoned":
                    return zoned_auto_spec(tex, seed_, drama=1.0)
                if look_id == "fracture":
                    return fracture_spec_from_any_paint(tex)
                if look_id == "candy_depth":
                    return candy_depth_spec_from_any_paint(tex, seed=seed_)
                raise ValueError(f"Unknown Easy signature mode: {look_id}")
            if kind not in {"preset", "catalog"} or not look_id:
                raise ValueError("Easy material requires a named preset, catalog look, or mode")
            return scratch_spec_from_any_paint(
                tex,
                seed=seed_,
                chromatic_shift=chromatic,
                preset_stack=[(look_id, 1.0)] if kind == "preset" else None,
                catalog_stack=[{
                    "id": look_id,
                    "weight": 1.0,
                    "registry_type": catalog_type_,
                }] if kind == "catalog" else None,
                paint_emphasis=None,
                paint_emphasis_strength=0.0,
                pattern_tile=pattern_tile_for_scale(material_scale_),
                fast_trace=fast_trace,
            )

        results = []
        for i, var in enumerate(variations):
            if not isinstance(var, dict):
                continue
            label = str(var.get("label") or ("Look " + str(i + 1)))[:48]
            # A recipe may be a signature Easy engine, catalog-based (real finish
            # ids, from the diversity picker), or preset-based (curated presets /
            # More-like-this). The signature path lets the recommendation rail
            # show Smart Materials, FRACTURE, and Candy Depth on the user's actual
            # livery without adding a separate full-size generate request per tile.
            mode = str(var.get("mode") or "").strip().lower()
            if mode not in {"zoned", "fracture", "candy_depth"}:
                mode = ""
            cat = normalize_catalog_stack(var.get("catalog"))
            ps = normalize_preset_stack(var.get("presets"))
            if not mode and not cat and not ps:
                continue
            var_seed = (_safe_int(var.get("seed"), base_seed + i * 17)) & 0xFFFFFFFF
            # [SPB-SPEC-SCULPT fix#3+#13 2026-06-02] SHOKK THE WORLD paint-AWARE: emphasis modes +
            # engine/spec_sculpt/paint_trace.py (spatial envelope, scratch skeleton fuse, Viva
            # ridge/crest trace without grid-flash dots). Catalog-on-uniform-mask alone = wallpaper.
            _emph_mode = ("highlights", "saturated", "shadows", "highlights", "desaturated")[i % 5]
            _exact_plan = _parse_bool_form(var.get("exact")) is True
            _paint_emphasis = None if _exact_plan else _emph_mode
            _paint_emphasis_strength = 0.0 if _exact_plan else 0.5
            _pattern_tile = pattern_tile_for_scale(var.get("material_scale", 1.0))
            _material_impact = normalize_material_impact(var.get("material_impact"))
            _easy_base = var.get("easy_base")
            if isinstance(_easy_base, str):
                try:
                    _easy_base = json.loads(_easy_base)
                except Exception:
                    _easy_base = None
            _easy_layers = parse_easy_color_layers(var.get("easy_color_layers"))
            _easy_color_report = []
            try:
                if isinstance(_easy_base, dict) and _easy_layers:
                    _base_seed = _safe_int(_easy_base.get("seed"), base_seed) & 0xFFFFFFFF
                    _base_spec = _render_exact_named_look(
                        _easy_base.get("kind"),
                        _easy_base.get("look_id") or _easy_base.get("id"),
                        _base_seed,
                        _easy_base.get("material_scale", 1.0),
                        _easy_base.get("catalog_type") or _easy_base.get("registry_type"),
                    )

                    def _render_batch_color_layer(layer):
                        _layer_seed = int(layer.get("seed") if layer.get("seed") is not None else var_seed) & 0xFFFFFFFF
                        return _render_exact_named_look(
                            layer["kind"], layer["look_id"], _layer_seed, layer["material_scale"],
                            layer.get("catalog_type"),
                        )

                    spec_u8, _easy_color_report = composite_easy_color_layers(
                        _base_spec, tex, _easy_layers, _render_batch_color_layer,
                    )
                elif mode == "zoned":
                    spec_u8 = zoned_auto_spec(tex, var_seed, drama=1.0)
                elif mode == "fracture":
                    spec_u8 = fracture_spec_from_any_paint(tex)
                elif mode == "candy_depth":
                    spec_u8 = candy_depth_spec_from_any_paint(tex, seed=var_seed)
                elif cat:
                    spec_u8 = scratch_spec_from_any_paint(
                        tex, seed=var_seed, chromatic_shift=chromatic, catalog_stack=cat,
                        paint_emphasis=_paint_emphasis, paint_emphasis_strength=_paint_emphasis_strength,
                        pattern_tile=_pattern_tile, fast_trace=fast_trace)
                else:
                    spec_u8 = scratch_spec_from_any_paint(
                        tex, seed=var_seed, chromatic_shift=chromatic, preset_stack=ps,
                        paint_emphasis=_paint_emphasis, paint_emphasis_strength=_paint_emphasis_strength,
                        pattern_tile=_pattern_tile, fast_trace=fast_trace)
                spec_u8 = apply_material_impact(spec_u8, _material_impact)
                _easy_color_report = apply_material_impact_to_report(_easy_color_report, _material_impact)
                if _protect_mask is not None:
                    spec_u8 = apply_sculpt_mask(spec_u8, _protect_mask, feather=_mask_feather, neutral=_protect_neutral)
                # SPB-BETA-2026-07-20 · owner: keep all 20 looks but make the chooser
                # easy/fast. Live Chevy PSD audit was 35.7 s plus ~20 MB of base64 because
                # every tile encoded composite + R/G/B proofs. A tile chooser needs one
                # on-car image; the chosen look still gets the full 2048 proof suite.
                previews = {} if tile_only else spec_preview_png_data_urls(spec_u8)
                # ON-CAR render: the look on the USER'S livery (relit). This is the tile the grid leads
                # with — "how this finish reads on MY car" — for BOTH catalog and preset looks.
                try:
                    _ocr = _on_car_render(spec_u8, var_seed)
                    if _ocr:
                        previews["render"] = _ocr
                except Exception as _re:
                    logger.warning(f"[spec-sculpt/batch] on-car render tile {i} ({label}) failed: {_re}")
                if not previews:
                    # Safe fallback when relighting is unavailable: one material-map tile,
                    # never a blank card and never the four unused channel payloads.
                    previews["composite"] = _paint_rgb_to_data_url(spec_u8[:, :, :3], compact_jpeg=tile_only)
                entry = {"idx": i, "label": label, "seed": var_seed, "previews": previews}
                if _easy_color_report:
                    entry["easy_color_layers"] = _easy_color_report
                if mode:
                    entry["mode"] = mode
                elif cat:
                    entry["catalog"] = [[fid, round(float(w), 4)] for fid, w in cat]
                else:
                    entry["presets"] = [[pid, round(float(w), 4)] for pid, w in ps]
                results.append(entry)
            except Exception as ve:
                logger.warning(f"[spec-sculpt/batch] variation {i} ({label}) failed: {ve}")
                continue

        if _swatch_png:
            try:
                os.unlink(_swatch_png)
            except Exception as _spb_ex:
                _spb_swallow('api_spec_sculpt_batch@L7525', _spb_ex)

        if not results:
            return jsonify({"success": False, "error": "No variations rendered."}), 500

        return jsonify({
            "success": True,
            "count": len(results),
            "preview_size": preview_size,
            "fast_trace": fast_trace,
            "tile_only": tile_only,
            "original_resolution": [int(orig_hw[1]), int(orig_hw[0])],
            "paint_file": paint_disk_path,
            "variations": results,
        })
    except Exception as e:
        logger.error(f"/api/spec-sculpt/batch failed: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if temp_created_path:
            try:
                os.remove(temp_created_path)
            except Exception as _spb_ex:
                _spb_swallow('api_spec_sculpt_batch@L7548', _spb_ex)


# --- Spec Sculpt PRESET AUDIT (owner triage tool, mirrors SPB-89 rate-finish) -------
SPEC_SCULPT_AUDIT_DIR = os.path.join(SERVER_DIR, '_audit')
SPEC_SCULPT_AUDIT_JSON = os.path.join(SPEC_SCULPT_AUDIT_DIR, 'spec_sculpt_audit.json')
SPEC_SCULPT_AUDIT_HISTORY = os.path.join(SPEC_SCULPT_AUDIT_DIR, 'spec_sculpt_audit_history.jsonl')
_VALID_AUDIT_VERDICTS = {"keep", "rebuild", "rename", "new"}


def _load_spec_sculpt_audit():
    # [2026-09-05 codebase-health S3] corrupt file -> quarantined + WARNING, never silently {}
    from engine.atomic_io import load_json_guarded
    data = load_json_guarded(SPEC_SCULPT_AUDIT_JSON, default=dict, logger=logger, what="spec_sculpt_audit.json")
    return data.get("entries", {}) if isinstance(data, dict) else {}


def _audit_counts(entries):
    counts = {v: 0 for v in _VALID_AUDIT_VERDICTS}
    for e in entries.values():
        v = (e or {}).get("verdict")
        if v in counts:
            counts[v] += 1
    return counts


@app.route('/api/spec-sculpt/batch-folder', methods=['POST'])
def api_spec_sculpt_batch_folder():
    """#30 Batch sculpt — apply the CURRENT scratch/catalog look to every paint in a folder.

    JSON: ``{folder, out_dir?, preset_stack?, catalog_stack?, seed?, chromatic_shift?, max_files?, size?}``.
    Renders each paint's spec via ``scratch_spec_from_any_paint`` (the dominant scratch+catalog look path)
    and writes ``<name>_spec.tga`` into ``out_dir`` (default ``<folder>/_spec``). Internal-only (reads/writes
    the local FS). Bounded (max_files cap). Fusion/candy/fracture looks fall back to scratch — logged, never
    silent. Returns a per-file report."""
    ok_internal, err = _require_spb_internal_request()
    if not ok_internal:
        return jsonify({"success": False, "error": err}), 403
    import os as _os
    import time as _time
    import json as _json
    import traceback as _tb
    try:
        data = request.get_json(silent=True)
        src = data if isinstance(data, dict) else request.form

        def gv(k, d=None):
            try:
                v = src.get(k)
            except Exception:
                v = None
            return v if v is not None else d

        folder = str(gv("folder") or "").strip()
        if not folder or not _os.path.isdir(folder):
            return jsonify({"success": False, "error": "folder not found"}), 400
        out_dir = str(gv("out_dir") or "").strip() or _os.path.join(folder, "_spec")
        denial = _external_write_denial(out_dir, "spec-sculpt-batch-folder")
        if denial:
            return jsonify(denial), 403
        try:
            _os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            return jsonify({"success": False, "error": f"cannot create out_dir: {e}"}), 400
        try:
            max_files = max(1, min(64, int(gv("max_files") or 24)))
        except Exception:
            max_files = 24
        try:
            size = int(gv("size") or 2048)
        except Exception:
            size = 2048
        if size not in (512, 1024, 2048):
            size = 2048
        seed = _safe_int(gv("seed"), 9101)
        chromatic = bool(_parse_bool_form(gv("chromatic_shift")))

        ps_raw = gv("preset_stack")
        cs_raw = gv("catalog_stack")
        if isinstance(ps_raw, str):
            try:
                ps_raw = _json.loads(ps_raw)
            except Exception:
                ps_raw = None
        if isinstance(cs_raw, str):
            try:
                cs_raw = _json.loads(cs_raw)
            except Exception:
                cs_raw = None

        from engine.spec_sculpt.core import load_paint_rgb_float01
        from engine.spec_sculpt.generate import scratch_spec_from_any_paint, iron_fix
        from engine.spec_sculpt.presets import normalize_preset_stack
        from engine.spec_sculpt.catalog_blend import normalize_catalog_stack
        from PIL import Image as _Image

        preset_stack = normalize_preset_stack(ps_raw)
        catalog_stack = normalize_catalog_stack(cs_raw)

        exts = (".psd", ".png", ".tga", ".jpg", ".jpeg", ".bmp", ".webp")
        try:
            names = sorted(f for f in _os.listdir(folder)
                           if f.lower().endswith(exts) and _os.path.isfile(_os.path.join(folder, f)))
        except Exception as e:
            return jsonify({"success": False, "error": f"cannot list folder: {e}"}), 400
        truncated = len(names) > max_files
        names = names[:max_files]

        results = []
        for fn in names:
            spath = _os.path.join(folder, fn)
            t0 = _time.perf_counter()
            try:
                tex, _o, _f = load_paint_rgb_float01(spath, target_size=size)
                spec = scratch_spec_from_any_paint(
                    tex, seed=seed, chromatic_shift=chromatic,
                    preset_stack=preset_stack, catalog_stack=catalog_stack)
                spec = iron_fix(spec)
                rgb = spec[:, :, :3] if (getattr(spec, "ndim", 0) == 3 and spec.shape[2] >= 3) else spec
                out_path = _os.path.join(out_dir, _os.path.splitext(fn)[0] + "_spec.tga")
                _Image.fromarray(rgb.astype("uint8")).save(out_path)
                results.append({"file": fn, "status": "ok", "out": out_path,
                                "ms": int((_time.perf_counter() - t0) * 1000)})
            except Exception as e:
                results.append({"file": fn, "status": "failed", "error": str(e)[:140]})

        ok_n = sum(1 for r in results if r["status"] == "ok")
        return jsonify({"success": True, "out_dir": out_dir, "total": len(names),
                        "ok": ok_n, "truncated": truncated, "results": results})
    except Exception as e:
        logger.error(f"/api/spec-sculpt/batch-folder error: {e}\n{_tb.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/spec-sculpt/open-folder', methods=['POST'])
def api_spec_sculpt_open_folder():
    """#33 One-click open the deployed/iRacing folder in the OS file explorer. Internal-only.

    JSON: ``{path}``. If ``path`` is a file, opens its parent. Validates existence before opening."""
    ok_internal, err = _require_spb_internal_request()
    if not ok_internal:
        return jsonify({"success": False, "error": err}), 403
    import os as _os
    import sys as _sys
    import subprocess as _sp
    try:
        data = request.get_json(silent=True)
        src = data if isinstance(data, dict) else request.form
        try:
            path = str((src.get("path") if hasattr(src, "get") else "") or "").strip()
        except Exception:
            path = ""
        if not path:
            return jsonify({"success": False, "error": "no path given"}), 400
        path = _os.path.normpath(path)
        if _os.path.isfile(path):
            path = _os.path.dirname(path)
        if not _os.path.isdir(path):
            return jsonify({"success": False, "error": "folder not found: " + path}), 404
        try:
            if _sys.platform.startswith("win"):
                _os.startfile(path)  # noqa: B606,P204
            elif _sys.platform == "darwin":
                _sp.Popen(["open", path])
            else:
                _sp.Popen(["xdg-open", path])
        except Exception as e:
            return jsonify({"success": False, "error": f"could not open: {e}"}), 500
        return jsonify({"success": True, "path": path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/spec-sculpt/auto-protect-preview', methods=['POST'])
def api_spec_sculpt_auto_protect_preview():
    """Preview what the no-PSD decal auto-detector would PROTECT on a FLAT paint (trust + tuning UI).

    Body: paint_file (path) OR an uploaded file + optional strength (0.3..2.0). Returns a magenta-tinted
    preview of the detected decal regions + the protected fraction. Internal-only (reads local paths)."""
    ok_internal, err = _require_spb_internal_request()
    if not ok_internal:
        return jsonify({"success": False, "error": err}), 403
    import os
    import io
    import base64
    import uuid as _uuid
    temp_created = None
    try:
        from engine.spec_sculpt.core import load_paint_rgb_float01
        from engine.spec_sculpt.generate import auto_protect_mask_from_paint
        from PIL import Image
        import numpy as np

        ct = (request.content_type or "").lower()
        jb = request.get_json(silent=True) if ct.startswith("application/json") else None

        def gv(k, d=None):
            if jb is not None:
                v = jb.get(k)
                return d if v is None else v
            return request.form.get(k, d)

        uploaded = request.files.get('paint_file') or request.files.get('file')
        if uploaded is not None and uploaded.filename:
            temp_created = _spb_temp_file_path(f"spec_sculpt_ap_{_uuid.uuid4().hex}_{uploaded.filename}")
            uploaded.save(temp_created)
            paint_disk = temp_created
        else:
            pf = str(gv("paint_file") or "").strip()
            if not pf:
                return jsonify({"success": False, "error": "paint_file (path) or an uploaded file required"}), 400
            paint_disk = os.path.abspath(os.path.expanduser(pf))
            if not os.path.isfile(paint_disk):
                return jsonify({"success": False, "error": f"paint_file not found: {paint_disk}"}), 400
        try:
            strength = max(0.3, min(2.0, float(gv("strength")))) if gv("strength") not in (None, "") else 1.0
        except (TypeError, ValueError):
            strength = 1.0

        tex, _o, _f = load_paint_rgb_float01(paint_disk, target_size=768)
        if temp_created:
            try:
                os.remove(temp_created)
                temp_created = None
            except OSError as _spb_ex:
                _spb_swallow('api_spec_sculpt_auto_protect_preview@L7773', _spb_ex)

        mask = auto_protect_mask_from_paint(tex, strength=strength)  # 255 sculpt / 0 protect, or None
        arr = np.asarray(tex)
        rgb = arr[:, :, :3]
        if float(rgb.max() if rgb.size else 0.0) <= 1.5:
            rgb = rgb * 255.0
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)

        detected = mask is not None
        if detected:
            prot = (mask == 0)
            tint = np.array([255, 45, 180], np.float32)
            over_f = rgb.astype(np.float32)
            over_f[prot] = over_f[prot] * 0.35 + tint * 0.65
            over = np.clip(over_f, 0, 255).astype(np.uint8)
            protect_frac = float(prot.mean())
        else:
            over = rgb
            protect_frac = 0.0

        buf = io.BytesIO()
        Image.fromarray(over).save(buf, format='PNG')
        data_url = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')
        return jsonify({"success": True, "preview": data_url, "detected": bool(detected),
                        "protect_frac": round(protect_frac, 4), "strength": strength})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if temp_created:
            try:
                os.remove(temp_created)
            except Exception as _spb_ex:
                _spb_swallow('api_spec_sculpt_auto_protect_preview@L7806', _spb_ex)


@app.route('/api/auto-separate-livery', methods=['POST'])
def api_auto_separate_livery():
    """AUTO-SEPARATE a FLAT livery (TGA/PNG/JPEG — NOT a PSD) into NUMBERS / SPONSORS / PAINT.

    Brings Spec Sculpt's flat-image decal detection to the main app. Body: an uploaded file (or, internal
    requests only, a paint_file path) + sensitivity (0.3..2.0) + number_size (0.4..2.5). Returns a
    color-coded overlay (numbers=red, sponsors=blue) + the three masks as PNG data URLs + coverage."""
    import os, io, base64, re
    import uuid as _uuid
    from pathlib import Path
    temp_created = None
    try:
        from engine.spec_sculpt.core import load_paint_rgb_float01
        from engine.spec_sculpt.generate import separate_livery_layers
        from PIL import Image
        import numpy as np

        ct = (request.content_type or "").lower()
        jb = request.get_json(silent=True) if ct.startswith("application/json") else None

        def gv(k, d=None):
            if jb is not None:
                v = jb.get(k); return d if v is None else v
            return request.form.get(k, d)

        uploaded = request.files.get('paint_file') or request.files.get('file') or request.files.get('image')
        if uploaded is not None and uploaded.filename:
            temp_created = _spb_temp_file_path(f"autosep_{_uuid.uuid4().hex}_{uploaded.filename}")
            uploaded.save(temp_created); paint_disk = temp_created
        else:
            ok_internal, err = _require_spb_internal_request()
            if not ok_internal:
                return jsonify({"success": False, "error": "upload a file, or (internal only) pass paint_file: " + err}), 403
            pf = str(gv("paint_file") or "").strip()
            if not pf:
                return jsonify({"success": False, "error": "a file upload or paint_file path is required"}), 400
            paint_disk = os.path.abspath(os.path.expanduser(pf))
            if not os.path.isfile(paint_disk):
                return jsonify({"success": False, "error": f"paint_file not found: {paint_disk}"}), 404

        if paint_disk.lower().endswith(".psd"):
            return jsonify({"success": False, "error": "Auto-Separate is for FLAT images (TGA/PNG/JPEG) — a PSD already has its layers."}), 400

        def _f(k, lo, hi, dv):
            try:
                return max(lo, min(hi, float(gv(k)))) if gv(k) not in (None, "") else dv
            except (TypeError, ValueError):
                return dv
        sens = _f("sensitivity", 0.3, 2.0, 1.0)
        nsz = _f("number_size", 0.4, 2.5, 1.0)
        prev = int(_f("preview_size", 256, 1024, 768))

        tex, _o, _ff = load_paint_rgb_float01(paint_disk, target_size=prev)
        if temp_created:
            try:
                os.remove(temp_created); temp_created = None
            except OSError as _spb_ex:
                _spb_swallow('api_auto_separate_livery@L7866', _spb_ex)

        # SMART (OCR-driven) separation first — reads the livery so digits->NUMBERS, words->SPONSORS,
        # and the base paint stays clean (the classic contrast detector over-protected). Falls back to
        # the classic detector if EasyOCR is unavailable or finds nothing. (2026-06-26)
        res = None
        if str(gv("smart", "1")).strip().lower() not in ("0", "false", "no"):
            try:
                from engine.spec_sculpt.smart_separate import separate_livery_layers_smart
                res = separate_livery_layers_smart(tex)
                if res is not None and not (res["numbers"].any() or res["sponsors"].any()):
                    res = None  # OCR found no text -> let the classic detector try
            except Exception as _smart_err:
                res = None
        if res is None:
            res = separate_livery_layers(tex, sensitivity=sens, number_size=nsz)
        a = np.asarray(tex)
        rgb = np.clip(a[:, :, :3] * (255.0 if (a.size and a.max() <= 1.5) else 1.0), 0, 255).astype(np.uint8)

        def _png(arr):
            b = io.BytesIO(); Image.fromarray(arr).save(b, "PNG")
            return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode('ascii')

        if res is None:
            return jsonify({"success": True, "detected": False, "overlay": _png(rgb),
                            "fractions": {"numbers": 0.0, "sponsors": 0.0, "paint": 1.0},
                            "message": "Couldn't confidently separate (likely a busy all-over base). Try raising Sensitivity.",
                            "sensitivity": sens, "number_size": nsz})
        nm, sp, pt = res["numbers"], res["sponsors"], res["paint"]
        ov = rgb.astype(np.float32)
        ov[nm > 0] = ov[nm > 0] * 0.25 + np.array([255, 45, 45], np.float32) * 0.75
        ov[sp > 0] = ov[sp > 0] * 0.25 + np.array([55, 95, 255], np.float32) * 0.75
        ov = np.clip(ov, 0, 255).astype(np.uint8)
        return jsonify({"success": True, "detected": True, "overlay": _png(ov),
                        "masks": {"numbers": _png(np.stack([nm] * 3, -1)),
                                  "sponsors": _png(np.stack([sp] * 3, -1)),
                                  "paint": _png(np.stack([pt] * 3, -1))},
                        "fractions": {"numbers": round(float((nm > 0).mean()), 4),
                                      "sponsors": round(float((sp > 0).mean()), 4),
                                      "paint": round(float((pt > 0).mean()), 4)},
                        "sensitivity": sens, "number_size": nsz})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if temp_created:
            try:
                os.remove(temp_created)
            except Exception as _spb_ex:
                _spb_swallow('api_auto_separate_livery@L7914', _spb_ex)


@app.route('/api/auto-layers', methods=['POST'])
def api_auto_layers():
    """AUTO-BUILD the 4 self-separated LAYERS from a FLAT livery (TGA/PNG/JPEG — NOT a PSD).

    Sibling to /api/auto-separate-livery (same upload / internal paint_file plumbing + `_png` helper),
    but instead of NUMBERS/SPONSORS/PAINT it runs engine.spec_sculpt.car_layers.separate_into_layers,
    which ALSO identifies WHICH iRacing car it is and carves a TEMPLATE layer (glass/grill/lights/
    reserved bits) using learned per-car intel. ~13s because OCR reads the numbers/sponsors.

    Body: an uploaded file (paint_file / file / image) OR (internal only) a paint_file path, plus an
    optional preview_size (default 1024 — layers want decent res; clamped 256..2048).

    Returns JSON:
      {"success": True,
       "car": [{slug,family,score,template_frac}, ...]    # top car matches
       "layers": {"numbers","sponsors","template","paint"} # each a white-on-black PNG data URL mask
       "overlay": dataurl,                                 # numbers=red, sponsors=blue, template=green tint
       "size": [H, W]}
    On error -> {"success": False, "error": str} 500. Temp upload always cleaned up in finally."""
    import os, io, base64, re
    import uuid as _uuid
    from pathlib import Path
    temp_created = None
    try:
        from engine.spec_sculpt.core import load_paint_rgb_float01
        from engine.spec_sculpt.car_layers import (
            separate_into_layers, hint_from_path, folder_slug_from_path,
            _sponsor_fragment_supplement, _isolated_wordmark_supplement,
            _tiny_logotype_residual_supplement, _micro_logotype_residual_supplement,
            _colored_micro_logo_residual_supplement,
            _bright_panel_micro_logo_residual_supplement,
            _panel_text_residual_supplement,
            _stacked_front_clip_template_supplement,
            _horizontal_front_clip_template_supplement,
            _paired_rear_lamp_template_supplement,
            _number_template_false_positive_to_template,
            _template_contained_paint_trim_supplement,
            _neutral_body_watermark_template_to_paint,
            _faint_number_outline_supplement,
            _flat_livery_sponsor_to_paint,
            _warm_edge_livery_sponsor_to_paint,
            _vertical_livery_stripe_sponsor_to_paint,
            _solid_warm_livery_sponsor_to_paint,
            _bright_warm_body_color_sponsor_to_paint,
            _warm_tan_body_panel_sponsor_to_paint,
            _diagonal_warm_livery_slash_sponsor_to_paint,
            _decorative_livery_sponsor_to_paint,
            _large_red_livery_sponsor_to_paint,
            _smooth_red_body_panel_sponsor_to_paint,
            _small_flat_red_livery_sponsor_to_paint,
            _red_orange_livery_block_sponsor_to_paint,
            _warm_livery_arc_sponsor_to_paint,
            _geometric_livery_sponsor_to_paint,
            _pale_body_panel_sponsor_to_paint,
            _ornamental_neutral_livery_sponsor_to_paint,
            _dark_body_panel_sponsor_to_paint,
            _white_livery_sponsor_to_paint,
            _merge_demoted_layer_guard,
            _merge_white_livery_sponsor_guard,
            _tiny_dark_sponsor_speck_to_paint,
            _number_logo_false_positive_to_sponsor,
            _multicolor_logo_false_positive_to_sponsor,
            _green_white_logo_false_positive_to_sponsor,
            _large_green_logo_false_positive_to_sponsor,
            _white_livery_number_panel_to_paint,
            _small_sponsor_panel_false_positive_to_sponsor,
            _thin_textline_number_false_positive_to_sponsor,
            _red_single_digit_number_supplement,
            _red_two_digit_number_supplement,
            _apply_number_trim_supplement,
            _number_badge_graphic_supplement,
            _round_badge_number_supplement,
            _repeated_round_badge_number_supplement,
            _yellow_panel_number_supplement,
            _pale_sponsor_panel_number_supplement,
            _hot_pink_paint_number_supplement,
            _black_blue_paint_number_supplement,
            _white_purple_paint_number_supplement,
            _red_white_dark_paint_number_supplement,
            _round_number_badge_interior_to_paint,
            _round_number_badge_number_crumb_to_paint,
            _round_number_badge_sponsor_crumb_to_number,
            _large_stylized_number_sponsor_shell_to_number,
            _merge_panel_text_residual_guard,
            _enforce_smart_tga_layer_priority,
        )
        from PIL import Image
        import numpy as np
        import cv2

        ct = (request.content_type or "").lower()
        jb = request.get_json(silent=True) if ct.startswith("application/json") else None

        def gv(k, d=None):
            if jb is not None:
                v = jb.get(k); return d if v is None else v
            return request.form.get(k, d)

        uploaded = request.files.get('paint_file') or request.files.get('file') or request.files.get('image')
        if uploaded is not None and uploaded.filename:
            temp_created = _spb_temp_file_path(f"autolayers_{_uuid.uuid4().hex}_{uploaded.filename}")
            uploaded.save(temp_created); paint_disk = temp_created
            _source_mode = "upload"
            _source_label = uploaded.filename
        else:
            ok_internal, err = _require_spb_internal_request()
            if not ok_internal:
                return jsonify({"success": False, "error": "upload a file, or (internal only) pass paint_file: " + err}), 403
            pf = str(gv("paint_file") or "").strip()
            if not pf:
                return jsonify({"success": False, "error": "a file upload or paint_file path is required"}), 400
            paint_disk = os.path.abspath(os.path.expanduser(pf))
            if not os.path.isfile(paint_disk):
                return jsonify({"success": False, "error": f"paint_file not found: {paint_disk}"}), 404
            _source_mode = "paint_file"
            _source_label = os.path.basename(paint_disk)

        if paint_disk.lower().endswith(".psd"):
            return jsonify({"success": False, "error": "Auto-Layers is for FLAT images (TGA/PNG/JPEG) — a PSD already has its layers."}), 400

        def _f(k, lo, hi, dv):
            try:
                return max(lo, min(hi, float(gv(k)))) if gv(k) not in (None, "") else dv
            except (TypeError, ValueError):
                return dv
        prev = int(_f("preview_size", 256, 2048, 1024))

        tex, _o, _ff = load_paint_rgb_float01(paint_disk, target_size=prev)
        _merge = str(gv("brand_graphics_merge") or "sponsors").lower()
        _explicit_car_hint = str(
            gv("car_hint_path")
            or gv("car_folder_hint")
            or gv("iracing_car_folder")
            or gv("output_dir")
            or ""
        ).strip()
        _paint_hint = str(gv("paint_file_hint") or "").strip()
        _hint_path = _explicit_car_hint or _paint_hint
        _hint_slug, _hint_family = hint_from_path(_hint_path)
        _hint_source_slug = folder_slug_from_path(_hint_path)
        try:
            _source_bytes = int(os.path.getsize(paint_disk))
        except OSError:
            _source_bytes = None
        _gpu_layers = None
        _gpu_info = None
        try:
            from engine.spec_sculpt import smart_tga_gpu_bridge as _gpu_bridge
            _gpu_layers = _gpu_bridge.separate_file_if_available(paint_disk, target_shape=tex.shape[:2])
            _gpu_info = _gpu_bridge.last_info()
        except Exception as _gpu_exc:
            print(f"[SmartTGA GPU] fallback: {_gpu_exc}")
            _gpu_info = {"available": False, "cache": "error", "error": str(_gpu_exc)}

        if temp_created:
            try:
                os.remove(temp_created); temp_created = None
            except OSError as _spb_ex:
                _spb_swallow('api_auto_layers@L8075', _spb_ex)

        route_candidate_snapshot = None
        route_mask_evidence = []
        route_ocr_regions = []
        if _gpu_layers is not None:
            # Smart TGA hybrid (2026-06-28): the trained SAM+OCR+CLIP model finds numbers,
            # sponsor text, and graphic logos far better than the old OCR-only path. Keep the
            # existing learned template prior for headlights/grilles/windows, then rebuild the
            # partition so Restrict-to-layer works on real editable layers.
            r = separate_into_layers(tex, brand_graphics_merge=_merge, use_ocr=False,
                                     car_slug=_hint_slug, car_family_hint=_hint_family,
                                     source_slug_hint=_hint_source_slug,
                                     include_adjudicator_context=True)
            _adjudicator_context = r.pop("_adjudicator_context", {})
            route_candidate_snapshot = _adjudicator_context.get("candidate_snapshot")
            route_mask_evidence = list(_adjudicator_context.get("mask_evidence") or ())
            route_ocr_regions = list(_gpu_layers.get("_ocr_regions") or ())
            nm = _gpu_layers["numbers"].copy()
            sp = _gpu_layers["text"].copy()
            bg = _gpu_layers["logos"].copy()
            tm = r["layers"]["template"].copy()
            if route_candidate_snapshot is not None:
                try:
                    from engine.spec_sculpt.candidate_evidence import (
                        capture_candidate_snapshot,
                        merge_candidate_snapshots,
                    )
                    gpu_candidate_snapshot = capture_candidate_snapshot(
                        {"numbers": nm, "sponsors": sp, "brand_graphics": bg},
                        source_stage="gpu_model_raw",
                        source="smart_tga_gpu_hybrid",
                        reason="unrepaired_gpu_partition",
                    )
                    route_candidate_snapshot = merge_candidate_snapshots(
                        route_candidate_snapshot,
                        gpu_candidate_snapshot,
                    )
                except Exception as _spb_ex:
                    _spb_swallow('api_auto_layers@L8114', _spb_ex)
            # Priority for editable layers: numbers win first, then confirmed car-template prior,
            # then sponsors/logos. This prevents fixed headlights/grilles/badges from being erased
            # by OCR/CLIP when the vision model finds them logo-like.
            tm[nm > 0] = 0
            sp[(nm > 0) | (tm > 0)] = 0
            bg[(nm > 0) | (sp > 0) | (tm > 0)] = 0
            if _merge in ("sponsor", "sponsors"):
                sp = np.maximum(sp, bg); bg = np.zeros_like(bg)
            elif _merge == "paint":
                bg = np.zeros_like(bg)
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            r["layers"] = {"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt}
            r["sponsor_fragment_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["isolated_wordmark_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["tiny_logotype_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["micro_logotype_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["colored_micro_logo_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["bright_panel_micro_logo_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["panel_text_residual_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["stacked_front_clip_template_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["horizontal_front_clip_template_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["paired_rear_lamp_template_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["number_template_false_positive_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["template_contained_paint_trim_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["neutral_body_watermark_template_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["faint_number_outline_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["flat_livery_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["warm_edge_livery_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["vertical_livery_stripe_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["solid_warm_livery_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["bright_warm_body_color_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["warm_tan_body_panel_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["diagonal_warm_livery_slash_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["decorative_livery_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["large_red_livery_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["smooth_red_body_panel_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["small_flat_red_livery_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["red_orange_livery_block_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["warm_livery_arc_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["geometric_livery_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["pale_body_panel_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["ornamental_neutral_livery_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["dark_body_panel_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["white_livery_sponsor_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["tiny_dark_sponsor_speck_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["number_logo_false_positive_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["multicolor_logo_false_positive_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["green_white_logo_false_positive_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["large_green_logo_false_positive_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["white_livery_number_panel_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["small_sponsor_panel_false_positive_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["thin_textline_number_false_positive_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["red_single_digit_number_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["red_two_digit_number_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["number_trim_fragment_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["number_badge_graphic_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["round_badge_number_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["repeated_round_badge_number_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["yellow_panel_number_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["pale_sponsor_panel_number_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["hot_pink_paint_number_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["black_blue_paint_number_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["white_purple_paint_number_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["red_white_dark_paint_number_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["badge_interior_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["badge_number_crumb_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["badge_sponsor_crumb_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["large_stylized_number_shell_guard"] = {"status": "skipped", "reason": "gpu_rebuild_pending"}
            r["engine"] = "gpu_hybrid"
        else:
            r = separate_into_layers(tex, brand_graphics_merge=_merge,
                                     car_slug=_hint_slug, car_family_hint=_hint_family,
                                     source_slug_hint=_hint_source_slug,
                                     include_adjudicator_context=True)
            _adjudicator_context = r.pop("_adjudicator_context", {})
            route_candidate_snapshot = _adjudicator_context.get("candidate_snapshot")
            route_mask_evidence = list(_adjudicator_context.get("mask_evidence") or ())
            r["engine"] = "heuristic_ocr"
        layers = r["layers"]; H, W = r["size"]
        nm = layers["numbers"]; sp = layers["sponsors"]; tm = layers["template"]; pt = layers["paint"]
        bg = layers.get("brand_graphics")
        if bg is None:
            bg = np.zeros_like(nm)

        # Cycle 607: preserve the union of repeated legacy guard verdicts as
        # immutable evidence.  These ledgers are diagnostic-only; the existing
        # replay sequence still owns every production mask mutation.
        number_logo_false_positive_accum_mask = np.zeros_like(nm, dtype=np.uint8)
        large_stylized_number_shell_accum_mask = np.zeros_like(nm, dtype=np.uint8)

        a = np.asarray(tex)
        rgb = np.clip(a[:, :, :3] * (255.0 if (a.size and a.max() <= 1.5) else 1.0), 0, 255).astype(np.uint8)
        force_gpu_supplements = r.get("engine") == "gpu_hybrid"
        flat_livery_sponsor_guard = r.get("flat_livery_sponsor_guard") or {}
        if force_gpu_supplements or flat_livery_sponsor_guard.get("status") != "applied":
            flat_livery_sponsor_mask, flat_livery_sponsor_guard = _flat_livery_sponsor_to_paint(rgb, sp, nm, tm, bg)
            if flat_livery_sponsor_mask.any():
                sp[flat_livery_sponsor_mask > 0] = 0
                bg[flat_livery_sponsor_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["flat_livery_sponsor_guard"] = flat_livery_sponsor_guard

        warm_edge_livery_sponsor_guard = r.get("warm_edge_livery_sponsor_guard") or {}
        warm_edge_livery_sponsor_accum_mask = np.zeros_like(sp, dtype=np.uint8)
        if force_gpu_supplements or warm_edge_livery_sponsor_guard.get("status") != "applied":
            warm_edge_livery_sponsor_mask, warm_edge_livery_sponsor_guard = _warm_edge_livery_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if warm_edge_livery_sponsor_mask.any():
                sp[warm_edge_livery_sponsor_mask > 0] = 0
                bg[warm_edge_livery_sponsor_mask > 0] = 0
                warm_edge_livery_sponsor_accum_mask = np.maximum(
                    warm_edge_livery_sponsor_accum_mask,
                    warm_edge_livery_sponsor_mask,
                )
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["warm_edge_livery_sponsor_guard"] = warm_edge_livery_sponsor_guard

        pre_decorative_shell_guard = r.get("large_stylized_number_shell_guard") or {}
        if force_gpu_supplements or pre_decorative_shell_guard.get("status") != "applied":
            pre_decorative_shell_mask, pre_decorative_shell_guard = _large_stylized_number_sponsor_shell_to_number(
                rgb, nm, sp, tm, bg
            )
            large_stylized_number_shell_accum_mask = np.maximum(
                large_stylized_number_shell_accum_mask,
                pre_decorative_shell_mask,
            )
            if pre_decorative_shell_mask.any():
                nm = np.maximum(nm, pre_decorative_shell_mask)
                sp[pre_decorative_shell_mask > 0] = 0
                bg[pre_decorative_shell_mask > 0] = 0
                tm[pre_decorative_shell_mask > 0] = 0
                pre_decorative_shell_guard["phase"] = "pre_decorative_livery"
                pre_decorative_shell_guard["passes"] = ["pre_decorative_livery"]
                for component in pre_decorative_shell_guard.get("components", []):
                    component["phase"] = "pre_decorative_livery"
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["large_stylized_number_shell_guard"] = pre_decorative_shell_guard

        decorative_livery_sponsor_guard = r.get("decorative_livery_sponsor_guard") or {}
        decorative_livery_sponsor_accum_mask = np.zeros_like(sp, dtype=np.uint8)
        if force_gpu_supplements or decorative_livery_sponsor_guard.get("status") != "applied":
            decorative_livery_sponsor_mask, decorative_livery_sponsor_guard = _decorative_livery_sponsor_to_paint(rgb, sp, nm, tm, bg)
            if decorative_livery_sponsor_mask.any():
                sp[decorative_livery_sponsor_mask > 0] = 0
                bg[decorative_livery_sponsor_mask > 0] = 0
                decorative_livery_sponsor_accum_mask = np.maximum(
                    decorative_livery_sponsor_accum_mask,
                    decorative_livery_sponsor_mask,
                )
                decorative_livery_sponsor_guard["passes"] = ["pre_sponsor_fragment"]
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["decorative_livery_sponsor_guard"] = decorative_livery_sponsor_guard

        vertical_livery_stripe_sponsor_guard = r.get("vertical_livery_stripe_sponsor_guard") or {}
        if force_gpu_supplements or vertical_livery_stripe_sponsor_guard.get("status") != "applied":
            vertical_livery_stripe_sponsor_mask, vertical_livery_stripe_sponsor_guard = _vertical_livery_stripe_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if vertical_livery_stripe_sponsor_mask.any():
                sp[vertical_livery_stripe_sponsor_mask > 0] = 0
                bg[vertical_livery_stripe_sponsor_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["vertical_livery_stripe_sponsor_guard"] = vertical_livery_stripe_sponsor_guard

        solid_warm_livery_sponsor_guard = r.get("solid_warm_livery_sponsor_guard") or {}
        if force_gpu_supplements or solid_warm_livery_sponsor_guard.get("status") != "applied":
            solid_warm_livery_sponsor_mask, solid_warm_livery_sponsor_guard = _solid_warm_livery_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if solid_warm_livery_sponsor_mask.any():
                sp[solid_warm_livery_sponsor_mask > 0] = 0
                bg[solid_warm_livery_sponsor_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["solid_warm_livery_sponsor_guard"] = solid_warm_livery_sponsor_guard

        bright_warm_body_color_sponsor_guard = r.get("bright_warm_body_color_sponsor_guard") or {}
        if force_gpu_supplements or bright_warm_body_color_sponsor_guard.get("status") != "applied":
            bright_warm_body_color_sponsor_mask, bright_warm_body_color_sponsor_guard = _bright_warm_body_color_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if bright_warm_body_color_sponsor_mask.any():
                sp[bright_warm_body_color_sponsor_mask > 0] = 0
                bg[bright_warm_body_color_sponsor_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["bright_warm_body_color_sponsor_guard"] = bright_warm_body_color_sponsor_guard

        warm_tan_body_panel_sponsor_guard = r.get("warm_tan_body_panel_sponsor_guard") or {}
        if force_gpu_supplements or warm_tan_body_panel_sponsor_guard.get("status") != "applied":
            warm_tan_body_panel_sponsor_mask, warm_tan_body_panel_sponsor_guard = _warm_tan_body_panel_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if warm_tan_body_panel_sponsor_mask.any():
                sp[warm_tan_body_panel_sponsor_mask > 0] = 0
                bg[warm_tan_body_panel_sponsor_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["warm_tan_body_panel_sponsor_guard"] = warm_tan_body_panel_sponsor_guard

        diagonal_warm_livery_slash_sponsor_guard = r.get("diagonal_warm_livery_slash_sponsor_guard") or {}
        if force_gpu_supplements or diagonal_warm_livery_slash_sponsor_guard.get("status") != "applied":
            diagonal_warm_livery_slash_sponsor_mask, diagonal_warm_livery_slash_sponsor_guard = _diagonal_warm_livery_slash_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if diagonal_warm_livery_slash_sponsor_mask.any():
                sp[diagonal_warm_livery_slash_sponsor_mask > 0] = 0
                bg[diagonal_warm_livery_slash_sponsor_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["diagonal_warm_livery_slash_sponsor_guard"] = diagonal_warm_livery_slash_sponsor_guard

        large_red_livery_sponsor_guard = r.get("large_red_livery_sponsor_guard") or {}
        if force_gpu_supplements or large_red_livery_sponsor_guard.get("status") != "applied":
            large_red_livery_sponsor_mask, large_red_livery_sponsor_guard = _large_red_livery_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if large_red_livery_sponsor_mask.any():
                sp[large_red_livery_sponsor_mask > 0] = 0
                bg[large_red_livery_sponsor_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["large_red_livery_sponsor_guard"] = large_red_livery_sponsor_guard

        smooth_red_body_panel_sponsor_guard = r.get("smooth_red_body_panel_sponsor_guard") or {}
        smooth_red_body_panel_sponsor_accum_mask = np.zeros_like(sp, dtype=np.uint8)
        if force_gpu_supplements or smooth_red_body_panel_sponsor_guard.get("status") != "applied":
            smooth_red_body_panel_sponsor_mask, smooth_red_body_panel_sponsor_guard = _smooth_red_body_panel_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if smooth_red_body_panel_sponsor_mask.any():
                sp[smooth_red_body_panel_sponsor_mask > 0] = 0
                bg[smooth_red_body_panel_sponsor_mask > 0] = 0
                smooth_red_body_panel_sponsor_accum_mask = np.maximum(
                    smooth_red_body_panel_sponsor_accum_mask,
                    smooth_red_body_panel_sponsor_mask,
                )
                smooth_red_body_panel_sponsor_guard["passes"] = ["pre_sponsor_fragment"]
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["smooth_red_body_panel_sponsor_guard"] = smooth_red_body_panel_sponsor_guard

        small_flat_red_livery_sponsor_guard = r.get("small_flat_red_livery_sponsor_guard") or {}
        if force_gpu_supplements or small_flat_red_livery_sponsor_guard.get("status") != "applied":
            small_flat_red_livery_sponsor_mask, small_flat_red_livery_sponsor_guard = _small_flat_red_livery_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if small_flat_red_livery_sponsor_mask.any():
                sp[small_flat_red_livery_sponsor_mask > 0] = 0
                bg[small_flat_red_livery_sponsor_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["small_flat_red_livery_sponsor_guard"] = small_flat_red_livery_sponsor_guard

        red_orange_livery_block_sponsor_guard = r.get("red_orange_livery_block_sponsor_guard") or {}
        if force_gpu_supplements or red_orange_livery_block_sponsor_guard.get("status") != "applied":
            red_orange_livery_block_sponsor_mask, red_orange_livery_block_sponsor_guard = _red_orange_livery_block_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if red_orange_livery_block_sponsor_mask.any():
                sp[red_orange_livery_block_sponsor_mask > 0] = 0
                bg[red_orange_livery_block_sponsor_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["red_orange_livery_block_sponsor_guard"] = red_orange_livery_block_sponsor_guard

        warm_livery_arc_sponsor_guard = r.get("warm_livery_arc_sponsor_guard") or {}
        warm_livery_arc_sponsor_accum_mask = np.zeros_like(sp)
        if force_gpu_supplements or warm_livery_arc_sponsor_guard.get("status") != "applied":
            warm_livery_arc_sponsor_mask, warm_livery_arc_sponsor_guard = _warm_livery_arc_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if warm_livery_arc_sponsor_mask.any():
                sp[warm_livery_arc_sponsor_mask > 0] = 0
                bg[warm_livery_arc_sponsor_mask > 0] = 0
                warm_livery_arc_sponsor_accum_mask = np.maximum(
                    warm_livery_arc_sponsor_accum_mask,
                    warm_livery_arc_sponsor_mask,
                )
                warm_livery_arc_sponsor_guard["passes"] = ["pre_sponsor_fragment"]
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["warm_livery_arc_sponsor_guard"] = warm_livery_arc_sponsor_guard

        geometric_livery_sponsor_guard = r.get("geometric_livery_sponsor_guard") or {}
        if force_gpu_supplements or geometric_livery_sponsor_guard.get("status") != "applied":
            geometric_livery_sponsor_mask, geometric_livery_sponsor_guard = _geometric_livery_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if geometric_livery_sponsor_mask.any():
                sp[geometric_livery_sponsor_mask > 0] = 0
                bg[geometric_livery_sponsor_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["geometric_livery_sponsor_guard"] = geometric_livery_sponsor_guard

        pale_body_panel_sponsor_guard = r.get("pale_body_panel_sponsor_guard") or {}
        pale_body_panel_sponsor_accum_mask = np.zeros_like(sp)
        if force_gpu_supplements or pale_body_panel_sponsor_guard.get("status") != "applied":
            pale_body_panel_sponsor_mask, pale_body_panel_sponsor_guard = _pale_body_panel_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if pale_body_panel_sponsor_mask.any():
                sp[pale_body_panel_sponsor_mask > 0] = 0
                bg[pale_body_panel_sponsor_mask > 0] = 0
                pale_body_panel_sponsor_accum_mask = np.maximum(
                    pale_body_panel_sponsor_accum_mask,
                    pale_body_panel_sponsor_mask,
                )
                pale_body_panel_sponsor_guard["passes"] = ["pre_number_recovery"]
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["pale_body_panel_sponsor_guard"] = pale_body_panel_sponsor_guard

        dark_body_panel_sponsor_guard = r.get("dark_body_panel_sponsor_guard") or {}
        dark_body_panel_sponsor_accum_mask = np.zeros_like(sp)
        if force_gpu_supplements or dark_body_panel_sponsor_guard.get("status") != "applied":
            dark_body_panel_sponsor_mask, dark_body_panel_sponsor_guard = _dark_body_panel_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if dark_body_panel_sponsor_mask.any():
                sp[dark_body_panel_sponsor_mask > 0] = 0
                bg[dark_body_panel_sponsor_mask > 0] = 0
                dark_body_panel_sponsor_accum_mask = np.maximum(
                    dark_body_panel_sponsor_accum_mask,
                    dark_body_panel_sponsor_mask,
                )
                dark_body_panel_sponsor_guard["passes"] = ["pre_number_recovery"]
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["dark_body_panel_sponsor_guard"] = dark_body_panel_sponsor_guard

        white_livery_sponsor_guard = r.get("white_livery_sponsor_guard") or {}
        white_livery_sponsor_accum_mask = np.zeros_like(sp)
        if force_gpu_supplements or white_livery_sponsor_guard.get("status") != "applied":
            white_livery_sponsor_mask, white_livery_sponsor_guard = _white_livery_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if white_livery_sponsor_mask.any():
                sp[white_livery_sponsor_mask > 0] = 0
                bg[white_livery_sponsor_mask > 0] = 0
                white_livery_sponsor_accum_mask = np.maximum(
                    white_livery_sponsor_accum_mask,
                    white_livery_sponsor_mask,
                )
                white_livery_sponsor_guard["passes"] = ["pre_number_recovery"]
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["white_livery_sponsor_guard"] = white_livery_sponsor_guard

        ornamental_neutral_livery_sponsor_guard = r.get("ornamental_neutral_livery_sponsor_guard") or {}
        ornamental_neutral_livery_sponsor_accum_mask = np.zeros_like(sp)
        if force_gpu_supplements or ornamental_neutral_livery_sponsor_guard.get("status") != "applied":
            ornamental_neutral_livery_sponsor_mask, ornamental_neutral_livery_sponsor_guard = (
                _ornamental_neutral_livery_sponsor_to_paint(rgb, sp, nm, tm, bg)
            )
            if ornamental_neutral_livery_sponsor_mask.any():
                sp[ornamental_neutral_livery_sponsor_mask > 0] = 0
                bg[ornamental_neutral_livery_sponsor_mask > 0] = 0
                ornamental_neutral_livery_sponsor_accum_mask = np.maximum(
                    ornamental_neutral_livery_sponsor_accum_mask,
                    ornamental_neutral_livery_sponsor_mask,
                )
                ornamental_neutral_livery_sponsor_guard["passes"] = ["pre_number_recovery"]
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["ornamental_neutral_livery_sponsor_guard"] = ornamental_neutral_livery_sponsor_guard

        number_logo_false_positive_guard = r.get("number_logo_false_positive_guard") or {}
        if force_gpu_supplements or number_logo_false_positive_guard.get("status") != "applied":
            number_logo_false_positive_mask, number_logo_false_positive_guard = _number_logo_false_positive_to_sponsor(rgb, nm, sp, tm, bg)
            number_logo_false_positive_accum_mask = np.maximum(
                number_logo_false_positive_accum_mask,
                number_logo_false_positive_mask,
            )
            if number_logo_false_positive_mask.any():
                nm[number_logo_false_positive_mask > 0] = 0
                sp = np.maximum(sp, number_logo_false_positive_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["number_logo_false_positive_guard"] = number_logo_false_positive_guard

        multicolor_logo_false_positive_guard = r.get("multicolor_logo_false_positive_guard") or {}
        if force_gpu_supplements or multicolor_logo_false_positive_guard.get("status") != "applied":
            multicolor_logo_false_positive_mask, multicolor_logo_false_positive_guard = _multicolor_logo_false_positive_to_sponsor(
                rgb, nm, sp, tm, bg
            )
            if multicolor_logo_false_positive_mask.any():
                nm[multicolor_logo_false_positive_mask > 0] = 0
                sp = np.maximum(sp, multicolor_logo_false_positive_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["multicolor_logo_false_positive_guard"] = multicolor_logo_false_positive_guard

        green_white_logo_false_positive_guard = r.get("green_white_logo_false_positive_guard") or {}
        if force_gpu_supplements or green_white_logo_false_positive_guard.get("status") != "applied":
            green_white_logo_false_positive_mask, green_white_logo_false_positive_guard = _green_white_logo_false_positive_to_sponsor(
                rgb, nm, sp, tm, bg
            )
            if green_white_logo_false_positive_mask.any():
                nm[green_white_logo_false_positive_mask > 0] = 0
                sp = np.maximum(sp, green_white_logo_false_positive_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["green_white_logo_false_positive_guard"] = green_white_logo_false_positive_guard

        large_green_logo_false_positive_guard = r.get("large_green_logo_false_positive_guard") or {}
        if force_gpu_supplements or large_green_logo_false_positive_guard.get("status") != "applied":
            large_green_logo_false_positive_mask, large_green_logo_false_positive_guard = _large_green_logo_false_positive_to_sponsor(
                rgb, nm, sp, tm, bg
            )
            if large_green_logo_false_positive_mask.any():
                nm[large_green_logo_false_positive_mask > 0] = 0
                sp = np.maximum(sp, large_green_logo_false_positive_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["large_green_logo_false_positive_guard"] = large_green_logo_false_positive_guard

        white_livery_number_panel_guard = r.get("white_livery_number_panel_guard") or {}
        white_livery_number_panel_accum_mask = np.zeros_like(nm)
        if force_gpu_supplements or white_livery_number_panel_guard.get("status") != "applied":
            white_livery_number_panel_mask, white_livery_number_panel_guard = _white_livery_number_panel_to_paint(
                rgb, nm, sp, tm, bg
            )
            if white_livery_number_panel_mask.any():
                nm[white_livery_number_panel_mask > 0] = 0
                white_livery_number_panel_accum_mask = np.maximum(
                    white_livery_number_panel_accum_mask,
                    white_livery_number_panel_mask,
                )
                white_livery_number_panel_guard["passes"] = ["pre_number_recovery"]
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["white_livery_number_panel_guard"] = white_livery_number_panel_guard

        small_sponsor_panel_false_positive_guard = r.get("small_sponsor_panel_false_positive_guard") or {}
        if force_gpu_supplements or small_sponsor_panel_false_positive_guard.get("status") != "applied":
            small_sponsor_panel_false_positive_mask, small_sponsor_panel_false_positive_guard = _small_sponsor_panel_false_positive_to_sponsor(
                rgb, nm, sp, tm, bg
            )
            if small_sponsor_panel_false_positive_mask.any():
                nm[small_sponsor_panel_false_positive_mask > 0] = 0
                sp = np.maximum(sp, small_sponsor_panel_false_positive_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["small_sponsor_panel_false_positive_guard"] = small_sponsor_panel_false_positive_guard

        thin_textline_number_false_positive_guard = r.get("thin_textline_number_false_positive_guard") or {}
        if force_gpu_supplements or thin_textline_number_false_positive_guard.get("status") != "applied":
            thin_textline_number_false_positive_mask, thin_textline_number_false_positive_guard = _thin_textline_number_false_positive_to_sponsor(
                rgb, nm, sp, tm, bg
            )
            if thin_textline_number_false_positive_mask.any():
                nm[thin_textline_number_false_positive_mask > 0] = 0
                sp = np.maximum(sp, thin_textline_number_false_positive_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["thin_textline_number_false_positive_guard"] = thin_textline_number_false_positive_guard

        red_single_digit_number_guard = r.get("red_single_digit_number_guard") or {}
        if force_gpu_supplements or red_single_digit_number_guard.get("status") != "applied":
            red_single_digit_number_mask, red_single_digit_number_guard = _red_single_digit_number_supplement(rgb, nm, sp, tm, bg)
            if red_single_digit_number_mask.any():
                nm = np.maximum(nm, red_single_digit_number_mask)
                sp[red_single_digit_number_mask > 0] = 0
                bg[red_single_digit_number_mask > 0] = 0
                tm[red_single_digit_number_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["red_single_digit_number_guard"] = red_single_digit_number_guard

        red_two_digit_number_guard = r.get("red_two_digit_number_guard") or {}
        if force_gpu_supplements or red_two_digit_number_guard.get("status") != "applied":
            red_two_digit_number_mask, red_two_digit_number_guard = _red_two_digit_number_supplement(rgb, nm, sp, tm, bg)
            if red_two_digit_number_mask.any():
                nm = np.maximum(nm, red_two_digit_number_mask)
                sp[red_two_digit_number_mask > 0] = 0
                bg[red_two_digit_number_mask > 0] = 0
                tm[red_two_digit_number_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["red_two_digit_number_guard"] = red_two_digit_number_guard

        number_trim_fragment_guard = r.get("number_trim_fragment_guard") or {}
        number_trim_fragment_accum_mask = np.zeros_like(nm, dtype=np.uint8)
        hot_pink_paint_number_accum_mask = np.zeros_like(nm, dtype=np.uint8)
        if force_gpu_supplements or number_trim_fragment_guard.get("status") != "applied":
            number_trim_fragment_guard, number_trim_fragment_accum_mask, number_trim_fragment_applied = (
                _apply_number_trim_supplement(
                    rgb,
                    nm,
                    sp,
                    tm,
                    bg,
                    existing_guard=number_trim_fragment_guard,
                    accum_mask=number_trim_fragment_accum_mask,
                    phase="pre_number_recovery",
                )
            )
            if number_trim_fragment_applied:
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["number_trim_fragment_guard"] = number_trim_fragment_guard

        number_badge_graphic_guard = r.get("number_badge_graphic_guard") or {}
        if force_gpu_supplements or number_badge_graphic_guard.get("status") != "applied":
            number_badge_graphic_mask, number_badge_graphic_guard = _number_badge_graphic_supplement(
                rgb, nm, sp, tm, bg
            )
            if number_badge_graphic_mask.any():
                nm = np.maximum(nm, number_badge_graphic_mask)
                sp[number_badge_graphic_mask > 0] = 0
                bg[number_badge_graphic_mask > 0] = 0
                tm[number_badge_graphic_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["number_badge_graphic_guard"] = number_badge_graphic_guard

        round_badge_number_guard = r.get("round_badge_number_guard") or {}
        if force_gpu_supplements or round_badge_number_guard.get("status") != "applied":
            round_badge_number_mask, round_badge_number_guard = _round_badge_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if round_badge_number_mask.any():
                nm = np.maximum(nm, round_badge_number_mask)
                sp[round_badge_number_mask > 0] = 0
                bg[round_badge_number_mask > 0] = 0
                tm[round_badge_number_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["round_badge_number_guard"] = round_badge_number_guard

        repeated_round_badge_number_guard = r.get("repeated_round_badge_number_guard") or {}
        if (
            (force_gpu_supplements or repeated_round_badge_number_guard.get("status") != "applied")
            and round_badge_number_guard.get("status") != "applied"
        ):
            repeated_round_badge_number_mask, repeated_round_badge_number_guard = _repeated_round_badge_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if repeated_round_badge_number_mask.any():
                nm = np.maximum(nm, repeated_round_badge_number_mask)
                sp[repeated_round_badge_number_mask > 0] = 0
                bg[repeated_round_badge_number_mask > 0] = 0
                tm[repeated_round_badge_number_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["repeated_round_badge_number_guard"] = repeated_round_badge_number_guard

        yellow_panel_number_guard = r.get("yellow_panel_number_guard") or {}
        if force_gpu_supplements or yellow_panel_number_guard.get("status") != "applied":
            yellow_panel_number_mask, yellow_panel_number_guard = _yellow_panel_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if yellow_panel_number_mask.any():
                nm = np.maximum(nm, yellow_panel_number_mask)
                sp[yellow_panel_number_mask > 0] = 0
                bg[yellow_panel_number_mask > 0] = 0
                tm[yellow_panel_number_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["yellow_panel_number_guard"] = yellow_panel_number_guard

        pale_sponsor_panel_number_guard = r.get("pale_sponsor_panel_number_guard") or {}
        if force_gpu_supplements or pale_sponsor_panel_number_guard.get("status") != "applied":
            pale_sponsor_panel_number_mask, pale_sponsor_panel_number_guard = _pale_sponsor_panel_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if pale_sponsor_panel_number_mask.any():
                nm = np.maximum(nm, pale_sponsor_panel_number_mask)
                sp[pale_sponsor_panel_number_mask > 0] = 0
                bg[pale_sponsor_panel_number_mask > 0] = 0
                tm[pale_sponsor_panel_number_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["pale_sponsor_panel_number_guard"] = pale_sponsor_panel_number_guard

        hot_pink_paint_number_guard = r.get("hot_pink_paint_number_guard") or {}
        if force_gpu_supplements or hot_pink_paint_number_guard.get("status") != "applied":
            hot_pink_paint_number_mask, hot_pink_paint_number_guard = _hot_pink_paint_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if hot_pink_paint_number_mask.any():
                hot_pink_paint_number_accum_mask = np.maximum(
                    hot_pink_paint_number_accum_mask, hot_pink_paint_number_mask
                )
                nm = np.maximum(nm, hot_pink_paint_number_mask)
                sp[hot_pink_paint_number_mask > 0] = 0
                bg[hot_pink_paint_number_mask > 0] = 0
                tm[hot_pink_paint_number_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["hot_pink_paint_number_guard"] = hot_pink_paint_number_guard

        black_blue_paint_number_guard = r.get("black_blue_paint_number_guard") or {}
        if force_gpu_supplements or black_blue_paint_number_guard.get("status") != "applied":
            black_blue_paint_number_mask, black_blue_paint_number_guard = _black_blue_paint_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if black_blue_paint_number_mask.any():
                nm = np.maximum(nm, black_blue_paint_number_mask)
                sp[black_blue_paint_number_mask > 0] = 0
                bg[black_blue_paint_number_mask > 0] = 0
                tm[black_blue_paint_number_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["black_blue_paint_number_guard"] = black_blue_paint_number_guard

        white_purple_paint_number_guard = r.get("white_purple_paint_number_guard") or {}
        if force_gpu_supplements or white_purple_paint_number_guard.get("status") != "applied":
            white_purple_paint_number_mask, white_purple_paint_number_guard = _white_purple_paint_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if white_purple_paint_number_mask.any():
                nm = np.maximum(nm, white_purple_paint_number_mask)
                sp[white_purple_paint_number_mask > 0] = 0
                bg[white_purple_paint_number_mask > 0] = 0
                tm[white_purple_paint_number_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["white_purple_paint_number_guard"] = white_purple_paint_number_guard

        red_white_dark_paint_number_guard = r.get("red_white_dark_paint_number_guard") or {}
        if force_gpu_supplements or red_white_dark_paint_number_guard.get("status") != "applied":
            red_white_dark_paint_number_mask, red_white_dark_paint_number_guard = _red_white_dark_paint_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if red_white_dark_paint_number_mask.any():
                nm = np.maximum(nm, red_white_dark_paint_number_mask)
                sp[red_white_dark_paint_number_mask > 0] = 0
                bg[red_white_dark_paint_number_mask > 0] = 0
                tm[red_white_dark_paint_number_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["red_white_dark_paint_number_guard"] = red_white_dark_paint_number_guard

        if force_gpu_supplements:
            white_livery_sponsor_post_mask, white_livery_sponsor_post_guard = _white_livery_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if white_livery_sponsor_post_mask.any():
                sp[white_livery_sponsor_post_mask > 0] = 0
                bg[white_livery_sponsor_post_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                r["white_livery_sponsor_guard"] = _merge_white_livery_sponsor_guard(
                    r.get("white_livery_sponsor_guard"),
                    white_livery_sponsor_post_guard,
                    white_livery_sponsor_accum_mask,
                    white_livery_sponsor_post_mask,
                    "post_number_recovery",
                )
                white_livery_sponsor_accum_mask = np.maximum(
                    white_livery_sponsor_accum_mask,
                    white_livery_sponsor_post_mask,
                )

            pale_body_panel_sponsor_post_mask, pale_body_panel_sponsor_post_guard = _pale_body_panel_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if pale_body_panel_sponsor_post_mask.any():
                sp[pale_body_panel_sponsor_post_mask > 0] = 0
                bg[pale_body_panel_sponsor_post_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                r["pale_body_panel_sponsor_guard"] = _merge_demoted_layer_guard(
                    r.get("pale_body_panel_sponsor_guard"),
                    pale_body_panel_sponsor_post_guard,
                    pale_body_panel_sponsor_accum_mask,
                    pale_body_panel_sponsor_post_mask,
                    "post_number_recovery",
                    "pre_number_recovery",
                )
                pale_body_panel_sponsor_accum_mask = np.maximum(
                    pale_body_panel_sponsor_accum_mask,
                    pale_body_panel_sponsor_post_mask,
                )

            dark_body_panel_sponsor_post_mask, dark_body_panel_sponsor_post_guard = _dark_body_panel_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if dark_body_panel_sponsor_post_mask.any():
                sp[dark_body_panel_sponsor_post_mask > 0] = 0
                bg[dark_body_panel_sponsor_post_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                r["dark_body_panel_sponsor_guard"] = _merge_demoted_layer_guard(
                    r.get("dark_body_panel_sponsor_guard"),
                    dark_body_panel_sponsor_post_guard,
                    dark_body_panel_sponsor_accum_mask,
                    dark_body_panel_sponsor_post_mask,
                    "post_number_recovery",
                    "pre_number_recovery",
                )
                dark_body_panel_sponsor_accum_mask = np.maximum(
                    dark_body_panel_sponsor_accum_mask,
                    dark_body_panel_sponsor_post_mask,
                )

            ornamental_neutral_livery_sponsor_post_mask, ornamental_neutral_livery_sponsor_post_guard = (
                _ornamental_neutral_livery_sponsor_to_paint(rgb, sp, nm, tm, bg)
            )
            if ornamental_neutral_livery_sponsor_post_mask.any():
                sp[ornamental_neutral_livery_sponsor_post_mask > 0] = 0
                bg[ornamental_neutral_livery_sponsor_post_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                r["ornamental_neutral_livery_sponsor_guard"] = _merge_demoted_layer_guard(
                    r.get("ornamental_neutral_livery_sponsor_guard"),
                    ornamental_neutral_livery_sponsor_post_guard,
                    ornamental_neutral_livery_sponsor_accum_mask,
                    ornamental_neutral_livery_sponsor_post_mask,
                    "post_number_recovery",
                    "pre_number_recovery",
                )
                ornamental_neutral_livery_sponsor_accum_mask = np.maximum(
                    ornamental_neutral_livery_sponsor_accum_mask,
                    ornamental_neutral_livery_sponsor_post_mask,
                )

            white_livery_number_panel_post_mask, white_livery_number_panel_post_guard = _white_livery_number_panel_to_paint(
                rgb, nm, sp, tm, bg
            )
            if white_livery_number_panel_post_mask.any():
                nm[white_livery_number_panel_post_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                r["white_livery_number_panel_guard"] = _merge_demoted_layer_guard(
                    r.get("white_livery_number_panel_guard"),
                    white_livery_number_panel_post_guard,
                    white_livery_number_panel_accum_mask,
                    white_livery_number_panel_post_mask,
                    "post_number_recovery",
                    "pre_number_recovery",
                )
                white_livery_number_panel_accum_mask = np.maximum(
                    white_livery_number_panel_accum_mask,
                    white_livery_number_panel_post_mask,
                )

        faint_number_outline_guard = r.get("faint_number_outline_guard") or {}
        if force_gpu_supplements or faint_number_outline_guard.get("status") != "applied":
            faint_number_outline_mask, faint_number_outline_guard = _faint_number_outline_supplement(rgb, nm, sp, tm, bg)
            if faint_number_outline_mask.any():
                nm = np.maximum(nm, faint_number_outline_mask)
                sp[faint_number_outline_mask > 0] = 0
                bg[faint_number_outline_mask > 0] = 0
                tm[faint_number_outline_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["faint_number_outline_guard"] = faint_number_outline_guard

        if number_trim_fragment_guard.get("status") != "applied":
            number_trim_fragment_guard, number_trim_fragment_accum_mask, number_trim_fragment_applied = (
                _apply_number_trim_supplement(
                    rgb,
                    nm,
                    sp,
                    tm,
                    bg,
                    existing_guard=number_trim_fragment_guard,
                    accum_mask=number_trim_fragment_accum_mask,
                    phase="post_faint_number_outline",
                )
            )
            if number_trim_fragment_applied:
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["number_trim_fragment_guard"] = number_trim_fragment_guard

        isolated_wordmark_guard = r.get("isolated_wordmark_guard") or {}
        if force_gpu_supplements or isolated_wordmark_guard.get("status") != "applied":
            isolated_wordmark_mask, isolated_wordmark_guard = _isolated_wordmark_supplement(rgb, nm, sp, tm, bg)
            if isolated_wordmark_mask.any():
                sp = np.maximum(sp, isolated_wordmark_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["isolated_wordmark_guard"] = isolated_wordmark_guard

        sponsor_fragment_guard = r.get("sponsor_fragment_guard") or {}
        if force_gpu_supplements or sponsor_fragment_guard.get("status") != "applied":
            sponsor_fragment_mask, sponsor_fragment_guard = _sponsor_fragment_supplement(rgb, nm, sp, tm, bg)
            if sponsor_fragment_mask.any():
                sp = np.maximum(sp, sponsor_fragment_mask)
                warm_edge_livery_sponsor_post_mask, warm_edge_livery_sponsor_post_guard = _warm_edge_livery_sponsor_to_paint(
                    rgb, sp, nm, tm, bg
                )
                if warm_edge_livery_sponsor_post_mask.any():
                    sp[warm_edge_livery_sponsor_post_mask > 0] = 0
                    bg[warm_edge_livery_sponsor_post_mask > 0] = 0
                    warm_edge_livery_sponsor_guard = _merge_demoted_layer_guard(
                        warm_edge_livery_sponsor_guard,
                        warm_edge_livery_sponsor_post_guard,
                        warm_edge_livery_sponsor_accum_mask,
                        warm_edge_livery_sponsor_post_mask,
                        "post_sponsor_fragment",
                        "pre_sponsor_fragment",
                    )
                    warm_edge_livery_sponsor_accum_mask = np.maximum(
                        warm_edge_livery_sponsor_accum_mask,
                        warm_edge_livery_sponsor_post_mask,
                    )
                    r["warm_edge_livery_sponsor_guard"] = warm_edge_livery_sponsor_guard
                warm_livery_arc_sponsor_post_mask, warm_livery_arc_sponsor_post_guard = _warm_livery_arc_sponsor_to_paint(
                    rgb, sp, nm, tm, bg
                )
                if warm_livery_arc_sponsor_post_mask.any():
                    sp[warm_livery_arc_sponsor_post_mask > 0] = 0
                    bg[warm_livery_arc_sponsor_post_mask > 0] = 0
                    warm_livery_arc_sponsor_guard = _merge_demoted_layer_guard(
                        warm_livery_arc_sponsor_guard,
                        warm_livery_arc_sponsor_post_guard,
                        warm_livery_arc_sponsor_accum_mask,
                        warm_livery_arc_sponsor_post_mask,
                        "post_sponsor_fragment",
                        "pre_sponsor_fragment",
                    )
                    warm_livery_arc_sponsor_accum_mask = np.maximum(
                        warm_livery_arc_sponsor_accum_mask,
                        warm_livery_arc_sponsor_post_mask,
                    )
                    r["warm_livery_arc_sponsor_guard"] = warm_livery_arc_sponsor_guard
                smooth_red_body_panel_sponsor_post_mask, smooth_red_body_panel_sponsor_post_guard = _smooth_red_body_panel_sponsor_to_paint(
                    rgb, sp, nm, tm, bg
                )
                if smooth_red_body_panel_sponsor_post_mask.any():
                    sp[smooth_red_body_panel_sponsor_post_mask > 0] = 0
                    bg[smooth_red_body_panel_sponsor_post_mask > 0] = 0
                    smooth_red_body_panel_sponsor_guard = _merge_demoted_layer_guard(
                        smooth_red_body_panel_sponsor_guard,
                        smooth_red_body_panel_sponsor_post_guard,
                        smooth_red_body_panel_sponsor_accum_mask,
                        smooth_red_body_panel_sponsor_post_mask,
                        "post_sponsor_fragment",
                        "pre_sponsor_fragment",
                    )
                    smooth_red_body_panel_sponsor_accum_mask = np.maximum(
                        smooth_red_body_panel_sponsor_accum_mask,
                        smooth_red_body_panel_sponsor_post_mask,
                    )
                    r["smooth_red_body_panel_sponsor_guard"] = smooth_red_body_panel_sponsor_guard
                decorative_livery_sponsor_post_mask, decorative_livery_sponsor_post_guard = _decorative_livery_sponsor_to_paint(
                    rgb, sp, nm, tm, bg
                )
                if decorative_livery_sponsor_post_mask.any():
                    sp[decorative_livery_sponsor_post_mask > 0] = 0
                    bg[decorative_livery_sponsor_post_mask > 0] = 0
                    decorative_livery_sponsor_post_guard["phase"] = "post_sponsor_fragment"
                    for component in decorative_livery_sponsor_post_guard.get("components", []):
                        component["phase"] = "post_sponsor_fragment"
                    decorative_livery_sponsor_guard = _merge_demoted_layer_guard(
                        decorative_livery_sponsor_guard,
                        decorative_livery_sponsor_post_guard,
                        decorative_livery_sponsor_accum_mask,
                        decorative_livery_sponsor_post_mask,
                        "post_sponsor_fragment",
                        "pre_sponsor_fragment",
                    )
                    decorative_livery_sponsor_accum_mask = np.maximum(
                        decorative_livery_sponsor_accum_mask,
                        decorative_livery_sponsor_post_mask,
                    )
                    r["decorative_livery_sponsor_guard"] = decorative_livery_sponsor_guard
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["sponsor_fragment_guard"] = sponsor_fragment_guard

        tiny_logotype_guard = r.get("tiny_logotype_guard") or {}
        if force_gpu_supplements or tiny_logotype_guard.get("status") != "applied":
            tiny_logotype_mask, tiny_logotype_guard = _tiny_logotype_residual_supplement(rgb, nm, sp, tm, bg)
            if tiny_logotype_mask.any():
                sp = np.maximum(sp, tiny_logotype_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["tiny_logotype_guard"] = tiny_logotype_guard

        micro_logotype_guard = r.get("micro_logotype_guard") or {}
        if force_gpu_supplements or micro_logotype_guard.get("status") != "applied":
            micro_logotype_mask, micro_logotype_guard = _micro_logotype_residual_supplement(rgb, nm, sp, tm, bg)
            if micro_logotype_mask.any():
                sp = np.maximum(sp, micro_logotype_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["micro_logotype_guard"] = micro_logotype_guard

        colored_micro_logo_guard = r.get("colored_micro_logo_guard") or {}
        if force_gpu_supplements or colored_micro_logo_guard.get("status") != "applied":
            colored_micro_logo_mask, colored_micro_logo_guard = _colored_micro_logo_residual_supplement(rgb, nm, sp, tm, bg)
            if colored_micro_logo_mask.any():
                sp = np.maximum(sp, colored_micro_logo_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["colored_micro_logo_guard"] = colored_micro_logo_guard

        bright_panel_micro_logo_guard = r.get("bright_panel_micro_logo_guard") or {}
        if force_gpu_supplements or bright_panel_micro_logo_guard.get("status") != "applied":
            bright_panel_micro_logo_mask, bright_panel_micro_logo_guard = _bright_panel_micro_logo_residual_supplement(rgb, nm, sp, tm, bg)
            if bright_panel_micro_logo_mask.any():
                sp = np.maximum(sp, bright_panel_micro_logo_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["bright_panel_micro_logo_guard"] = bright_panel_micro_logo_guard

        panel_text_residual_guard = r.get("panel_text_residual_guard") or {}
        panel_text_residual_accum_mask = None
        if force_gpu_supplements or panel_text_residual_guard.get("status") != "applied":
            panel_text_residual_mask, panel_text_residual_guard = _panel_text_residual_supplement(rgb, nm, sp, tm, bg)
            panel_text_residual_accum_mask = panel_text_residual_mask.copy()
            if panel_text_residual_mask.any():
                sp = np.maximum(sp, panel_text_residual_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["panel_text_residual_guard"] = panel_text_residual_guard

        stacked_front_clip_template_guard = r.get("stacked_front_clip_template_guard") or {}
        if force_gpu_supplements or stacked_front_clip_template_guard.get("status") != "applied":
            stacked_front_clip_template_mask, stacked_front_clip_template_guard = _stacked_front_clip_template_supplement(
                rgb, nm, sp, tm, bg
            )
            if stacked_front_clip_template_mask.any():
                sp[stacked_front_clip_template_mask > 0] = 0
                bg[stacked_front_clip_template_mask > 0] = 0
                tm = np.maximum(tm, stacked_front_clip_template_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["stacked_front_clip_template_guard"] = stacked_front_clip_template_guard

        horizontal_front_clip_template_guard = r.get("horizontal_front_clip_template_guard") or {}
        if force_gpu_supplements or horizontal_front_clip_template_guard.get("status") != "applied":
            horizontal_front_clip_template_mask, horizontal_front_clip_template_guard = _horizontal_front_clip_template_supplement(
                rgb, nm, sp, tm, bg
            )
            if horizontal_front_clip_template_mask.any():
                sp[horizontal_front_clip_template_mask > 0] = 0
                bg[horizontal_front_clip_template_mask > 0] = 0
                tm = np.maximum(tm, horizontal_front_clip_template_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["horizontal_front_clip_template_guard"] = horizontal_front_clip_template_guard

        paired_rear_lamp_template_guard = r.get("paired_rear_lamp_template_guard") or {}
        if force_gpu_supplements or paired_rear_lamp_template_guard.get("status") != "applied":
            paired_rear_lamp_template_mask, paired_rear_lamp_template_guard = _paired_rear_lamp_template_supplement(
                rgb, nm, sp, tm, bg
            )
            if paired_rear_lamp_template_mask.any():
                sp[paired_rear_lamp_template_mask > 0] = 0
                bg[paired_rear_lamp_template_mask > 0] = 0
                tm = np.maximum(tm, paired_rear_lamp_template_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["paired_rear_lamp_template_guard"] = paired_rear_lamp_template_guard

        number_template_false_positive_guard = r.get("number_template_false_positive_guard") or {}
        if force_gpu_supplements or number_template_false_positive_guard.get("status") != "applied":
            number_template_false_positive_mask, number_template_false_positive_guard = _number_template_false_positive_to_template(
                rgb, nm, sp, tm, bg
            )
            if number_template_false_positive_mask.any():
                nm[number_template_false_positive_mask > 0] = 0
                tm = np.maximum(tm, number_template_false_positive_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["number_template_false_positive_guard"] = number_template_false_positive_guard

        template_contained_paint_trim_guard = r.get("template_contained_paint_trim_guard") or {}
        if force_gpu_supplements or template_contained_paint_trim_guard.get("status") != "applied":
            template_contained_paint_trim_mask, template_contained_paint_trim_guard = _template_contained_paint_trim_supplement(
                rgb, nm, sp, tm, bg
            )
            if template_contained_paint_trim_mask.any():
                tm = np.maximum(tm, template_contained_paint_trim_mask)
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["template_contained_paint_trim_guard"] = template_contained_paint_trim_guard

        badge_interior_guard = r.get("badge_interior_guard") or {}
        if force_gpu_supplements or badge_interior_guard.get("status") != "applied":
            badge_interior_mask, badge_interior_guard = _round_number_badge_interior_to_paint(nm, sp, tm, bg)
            if badge_interior_mask.any():
                sp[badge_interior_mask > 0] = 0
                bg[badge_interior_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["badge_interior_guard"] = badge_interior_guard

        badge_number_crumb_guard = r.get("badge_number_crumb_guard") or {}
        if force_gpu_supplements or badge_number_crumb_guard.get("status") != "applied":
            badge_number_crumb_mask, badge_number_crumb_guard = _round_number_badge_number_crumb_to_paint(nm)
            if badge_number_crumb_mask.any():
                nm[badge_number_crumb_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["badge_number_crumb_guard"] = badge_number_crumb_guard

        badge_sponsor_crumb_guard = r.get("badge_sponsor_crumb_guard") or {}
        if force_gpu_supplements or badge_sponsor_crumb_guard.get("status") != "applied":
            badge_sponsor_crumb_mask, badge_sponsor_crumb_guard = _round_number_badge_sponsor_crumb_to_number(nm, sp, tm, bg)
            if badge_sponsor_crumb_mask.any():
                nm = np.maximum(nm, badge_sponsor_crumb_mask)
                sp[badge_sponsor_crumb_mask > 0] = 0
                bg[badge_sponsor_crumb_mask > 0] = 0
                tm[badge_sponsor_crumb_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["badge_sponsor_crumb_guard"] = badge_sponsor_crumb_guard

        def _apply_large_stylized_number_shell(phase):
            nonlocal nm, sp, tm, bg, pt, number_trim_fragment_guard, number_trim_fragment_accum_mask
            nonlocal large_stylized_number_shell_accum_mask
            shell_mask, shell_guard = _large_stylized_number_sponsor_shell_to_number(
                rgb, nm, sp, tm, bg
            )
            large_stylized_number_shell_accum_mask = np.maximum(
                large_stylized_number_shell_accum_mask,
                shell_mask,
            )
            if not shell_mask.any():
                if phase == "pre_response_partition" and not r.get("large_stylized_number_shell_guard"):
                    r["large_stylized_number_shell_guard"] = shell_guard
                return False

            nm = np.maximum(nm, shell_mask)
            sp[shell_mask > 0] = 0
            bg[shell_mask > 0] = 0
            tm[shell_mask > 0] = 0
            shell_guard["phase"] = phase
            for component in shell_guard.get("components", []):
                component["phase"] = phase

            existing_shell_guard = r.get("large_stylized_number_shell_guard") or {}
            if existing_shell_guard.get("status") == "applied":
                existing_components = list(existing_shell_guard.get("components") or [])
                response_components = list(shell_guard.get("components") or [])
                passes = list(existing_shell_guard.get("passes") or ["pre_response_partition"])
                if phase not in passes:
                    passes.append(phase)
                prior_px = int(existing_shell_guard.get("added_px") or 0)
                response_px = int(shell_guard.get("added_px") or int((shell_mask > 0).sum()))
                canvas_px = max(1, int(H) * int(W))
                r["large_stylized_number_shell_guard"] = {
                    **existing_shell_guard,
                    "status": "applied",
                    "component_count": len(existing_components) + len(response_components),
                    "candidate_count": (
                        int(existing_shell_guard.get("candidate_count", 0) or 0)
                        + int(shell_guard.get("candidate_count", 0) or 0)
                    ),
                    "added_px": prior_px + response_px,
                    "added_frac": round(float(prior_px + response_px) / float(canvas_px), 6),
                    "capped": bool(existing_shell_guard.get("capped")) or bool(shell_guard.get("capped")),
                    "components": (existing_components + response_components)[:8],
                    "passes": passes,
                }
            else:
                shell_guard["passes"] = [phase]
                r["large_stylized_number_shell_guard"] = shell_guard

            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

            existing_trim_guard = r.get("number_trim_fragment_guard") or number_trim_fragment_guard or {}
            next_number_trim_fragment_guard, number_trim_fragment_accum_mask, number_trim_fragment_applied = (
                _apply_number_trim_supplement(
                    rgb,
                    nm,
                    sp,
                    tm,
                    bg,
                    existing_guard=existing_trim_guard,
                    accum_mask=number_trim_fragment_accum_mask,
                    phase=f"post_{phase}_large_stylized_number_shell",
                )
            )
            if number_trim_fragment_applied or existing_trim_guard.get("status") != "applied":
                number_trim_fragment_guard = next_number_trim_fragment_guard
            else:
                number_trim_fragment_guard = existing_trim_guard
            r["number_trim_fragment_guard"] = number_trim_fragment_guard
            if number_trim_fragment_applied:
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            return True

        large_stylized_number_shell_guard = r.get("large_stylized_number_shell_guard") or {}
        if force_gpu_supplements or large_stylized_number_shell_guard.get("status") != "applied":
            _apply_large_stylized_number_shell("pre_response_partition")

        def _companion_number_mask(hint_path, current_rgb):
            """Strictly use iRacing car_num_* only when it behaves like a sparse number overlay."""
            info = {"status": "skipped", "reason": "unavailable"}
            enabled = os.environ.get("SPB_SMART_TGA_COMPANION_NUMBERS", "1").strip().lower()
            if enabled in {"0", "false", "off", "no"}:
                info["reason"] = "disabled"; return None, info
            try:
                if not hint_path:
                    info["reason"] = "no_hint_path"; return None, info
                hp = Path(os.path.abspath(os.path.expanduser(hint_path)))
                m = re.fullmatch(r"car_(\d+)\.tga", hp.name.lower())
                num_m = re.fullmatch(r"car_num_(\d+)\.tga", hp.name.lower())
                team_m = re.fullmatch(r"car_team_(\d+)\.tga", hp.name.lower())
                if m:
                    base_path = hp
                    number_path = hp.with_name(f"car_num_{m.group(1)}.tga")
                    source_kind = "car"
                elif num_m:
                    base_path = hp.with_name(f"car_{num_m.group(1)}.tga")
                    number_path = hp
                    source_kind = "car_num"
                elif team_m:
                    base_path = hp
                    number_path = hp.with_name(f"car_num_team_{team_m.group(1)}.tga")
                    source_kind = "car_team"
                else:
                    info["reason"] = "hint_not_car_or_car_num_or_car_team_tga"; return None, info
                if not hp.is_file() or not base_path.is_file() or not number_path.is_file():
                    info["reason"] = "missing_companion"; return None, info

                h, w = current_rgb.shape[:2]
                def _load_rgb(path):
                    im = Image.open(path).convert("RGB")
                    arr = np.asarray(im, dtype=np.uint8)
                    if arr.shape[:2] != (h, w):
                        arr = cv2.resize(arr, (w, h), interpolation=cv2.INTER_LANCZOS4)
                    return arr

                source_rgb = _load_rgb(hp)
                base = _load_rgb(base_path)
                comp = _load_rgb(number_path)
                source_diff = np.max(np.abs(current_rgb.astype(np.int16) - source_rgb.astype(np.int16)), axis=2) > 18
                source_diff_frac = float(source_diff.mean())
                try:
                    source_limit = float(os.environ.get("SPB_SMART_TGA_COMPANION_SOURCE_MAX", "0.16"))
                except (TypeError, ValueError):
                    source_limit = 0.16
                source_limit = max(0.08, min(0.35, source_limit))
                if source_diff_frac > source_limit:
                    info.update({"reason": "source_mismatch", "source_diff": round(source_diff_frac, 5),
                                 "source_limit": round(source_limit, 5)})
                    return None, info
                source_match = "loose" if source_diff_frac > 0.08 else "strict"

                rgb_delta = np.max(np.abs(base.astype(np.int16) - comp.astype(np.int16)), axis=2)
                loose_frac = float((rgb_delta > 18).mean())
                mask = rgb_delta > 45
                frac = float(mask.mean())
                if frac < 0.002 or frac > 0.075 or loose_frac > 0.16:
                    info.update({"reason": "delta_area_rejected", "delta_frac": round(frac, 5),
                                 "loose_delta_frac": round(loose_frac, 5),
                                 "source_diff": round(source_diff_frac, 5),
                                 "source_match": source_match,
                                 "source_kind": source_kind})
                    return None, info

                clean = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
                n, _labels, stats, _cent = cv2.connectedComponentsWithStats(clean.astype(np.uint8), 8)
                comp_fracs = [float(stats[i, cv2.CC_STAT_AREA]) / float(h * w) for i in range(1, n)
                              if stats[i, cv2.CC_STAT_AREA] >= 80]
                if not comp_fracs or len(comp_fracs) > 48 or max(comp_fracs) > 0.035:
                    info.update({"reason": "component_shape_rejected", "components": len(comp_fracs),
                                 "largest_component": round(max(comp_fracs or [0.0]), 5),
                                 "source_diff": round(source_diff_frac, 5),
                                 "source_match": source_match,
                                 "source_kind": source_kind})
                    return None, info
                ys, xs = np.where(clean)
                if len(xs) == 0:
                    info["reason"] = "empty_after_cleanup"; return None, info
                bbox_w = (int(xs.max()) - int(xs.min()) + 1) / float(w)
                bbox_h = (int(ys.max()) - int(ys.min()) + 1) / float(h)
                if bbox_w > 0.92 and bbox_h > 0.92:
                    info.update({"reason": "whole_canvas_bbox", "bbox_w": round(bbox_w, 4),
                                 "bbox_h": round(bbox_h, 4),
                                 "source_kind": source_kind})
                    return None, info
                info.update({"status": "applied", "reason": None, "path": str(number_path),
                             "delta_frac": round(frac, 5), "source_diff": round(source_diff_frac, 5),
                             "source_match": source_match,
                             "source_kind": source_kind,
                             "components": len(comp_fracs), "largest_component": round(max(comp_fracs), 5)})
                return clean.astype(np.uint8) * 255, info
            except Exception as exc:
                info.update({"reason": "error", "error": str(exc)})
                return None, info

        def _companion_decal_mask(hint_path, current_rgb):
            """Use iRacing car_decal_* only when it is a sparse alpha decal/sponsor overlay."""
            info = {"status": "skipped", "reason": "unavailable"}
            enabled = os.environ.get("SPB_SMART_TGA_COMPANION_DECALS", "1").strip().lower()
            if enabled in {"0", "false", "off", "no"}:
                info["reason"] = "disabled"; return None, info
            try:
                if not hint_path:
                    info["reason"] = "no_hint_path"; return None, info
                hp = Path(os.path.abspath(os.path.expanduser(hint_path)))
                m = re.fullmatch(r"car(?:_num)?_(\d+)\.tga", hp.name.lower())
                if not m:
                    info["reason"] = "hint_not_car_or_car_num_tga"; return None, info
                companion = hp.with_name(f"car_decal_{m.group(1)}.tga")
                if not hp.is_file() or not companion.is_file():
                    info["reason"] = "missing_companion"; return None, info

                h, w = current_rgb.shape[:2]
                base = Image.open(hp).convert("RGB")
                if base.size != (w, h):
                    base = base.resize((w, h), Image.Resampling.BILINEAR)
                base_rgb = np.asarray(base, dtype=np.uint8)
                source_diff = np.max(np.abs(current_rgb.astype(np.int16) - base_rgb.astype(np.int16)), axis=2) > 18
                source_diff_frac = float(source_diff.mean())
                try:
                    source_limit = float(os.environ.get("SPB_SMART_TGA_COMPANION_DECAL_SOURCE_MAX", "0.16"))
                except (TypeError, ValueError):
                    source_limit = 0.16
                source_limit = max(0.08, min(0.35, source_limit))
                if source_diff_frac > source_limit:
                    info.update({"reason": "source_mismatch", "source_diff": round(source_diff_frac, 5),
                                 "source_limit": round(source_limit, 5)})
                    return None, info

                decal = Image.open(companion).convert("RGBA")
                if decal.size != (w, h):
                    decal = decal.resize((w, h), Image.Resampling.NEAREST)
                alpha = np.asarray(decal.getchannel("A"), dtype=np.uint8)
                mask = alpha > 8
                frac = float(mask.mean())
                try:
                    max_frac = float(os.environ.get("SPB_SMART_TGA_COMPANION_DECAL_MAX", "0.12"))
                except (TypeError, ValueError):
                    max_frac = 0.12
                try:
                    min_frac = float(os.environ.get("SPB_SMART_TGA_COMPANION_DECAL_MIN", "0.00025"))
                except (TypeError, ValueError):
                    min_frac = 0.00025
                min_frac = max(0.00005, min(0.005, min_frac))
                max_frac = max(0.02, min(0.25, max_frac))
                if frac < min_frac or frac > max_frac:
                    rgb_fallback = os.environ.get("SPB_SMART_TGA_COMPANION_DECAL_RGB_FALLBACK", "1").strip().lower()
                    if rgb_fallback not in {"0", "false", "off", "no"} and frac > 0.98:
                        rgb_decal = np.asarray(decal.convert("RGB"), dtype=np.uint8)
                        hsv = cv2.cvtColor(rgb_decal, cv2.COLOR_RGB2HSV)
                        sat = hsv[:, :, 1]
                        val = hsv[:, :, 2]
                        # Some iRacing decal TGAs ship fully opaque with a near-black/blank
                        # background. Use RGB only when the visible foreground is tiny.
                        bg_dark = (val < 12) & (sat < 45)
                        bg_white = (val > 245) & (sat < 20)
                        rgb_mask = (~(bg_dark | bg_white)) & ((sat > 35) | (val > 35))
                        rgb_clean = cv2.morphologyEx(
                            rgb_mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)
                        ) > 0
                        n_rgb, labels_rgb, stats_rgb, _cent_rgb = cv2.connectedComponentsWithStats(
                            rgb_clean.astype(np.uint8), 8
                        )
                        keep_rgb = [i for i in range(1, n_rgb) if stats_rgb[i, cv2.CC_STAT_AREA] >= 24]
                        rgb_comp_fracs = [
                            float(stats_rgb[i, cv2.CC_STAT_AREA]) / float(h * w) for i in keep_rgb
                        ]
                        rgb_frac = float(rgb_clean.mean())
                        rgb_largest = max(rgb_comp_fracs or [0.0])
                        rgb_mask_ok = (
                            0.001 <= rgb_frac <= 0.025
                            and 1 <= len(rgb_comp_fracs) <= 48
                            and rgb_largest <= 0.012
                        )
                        if rgb_mask_ok:
                            rgb_candidate = np.isin(labels_rgb, keep_rgb)
                            ys_rgb, xs_rgb = np.where(rgb_candidate)
                            if len(xs_rgb):
                                bbox_w_rgb = (int(xs_rgb.max()) - int(xs_rgb.min()) + 1) / float(w)
                                bbox_h_rgb = (int(ys_rgb.max()) - int(ys_rgb.min()) + 1) / float(h)
                                rgb_mask_ok = not (bbox_w_rgb > 0.92 and bbox_h_rgb > 0.92)
                                if rgb_mask_ok:
                                    mask = rgb_candidate
                                    frac = float(mask.mean())
                                    info.update({
                                        "mask_source": "rgb_opaque_fallback",
                                        "alpha_frac_raw": round(float((alpha > 8).mean()), 5),
                                        "rgb_frac": round(rgb_frac, 5),
                                        "rgb_components": len(rgb_comp_fracs),
                                        "rgb_largest_component": round(rgb_largest, 5),
                                    })
                        if not info.get("mask_source"):
                            info.update({"reason": "alpha_area_rejected", "alpha_frac": round(frac, 5),
                                         "alpha_min": round(min_frac, 5),
                                         "alpha_max": round(max_frac, 5),
                                         "source_diff": round(source_diff_frac, 5),
                                         "rgb_frac": round(float(rgb_clean.mean()), 5),
                                         "rgb_components": len(rgb_comp_fracs),
                                         "rgb_largest_component": round(max(rgb_comp_fracs or [0.0]), 5)})
                            return None, info
                    else:
                        info.update({"reason": "alpha_area_rejected", "alpha_frac": round(frac, 5),
                                     "alpha_min": round(min_frac, 5),
                                     "alpha_max": round(max_frac, 5),
                                     "source_diff": round(source_diff_frac, 5)})
                        return None, info
                if frac < min_frac or frac > max_frac:
                    info.update({"reason": "alpha_area_rejected", "alpha_frac": round(frac, 5),
                                 "alpha_min": round(min_frac, 5),
                                 "alpha_max": round(max_frac, 5),
                                 "source_diff": round(source_diff_frac, 5)})
                    return None, info

                n, labels, stats, _cent = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
                keep = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= 24]
                if not keep:
                    info.update({"reason": "empty_after_cleanup", "alpha_frac": round(frac, 5),
                                 "source_diff": round(source_diff_frac, 5)})
                    return None, info
                comp_fracs = [float(stats[i, cv2.CC_STAT_AREA]) / float(h * w) for i in keep]
                if len(comp_fracs) > 160 or max(comp_fracs) > 0.08:
                    info.update({"reason": "component_shape_rejected", "components": len(comp_fracs),
                                 "largest_component": round(max(comp_fracs or [0.0]), 5),
                                 "alpha_frac": round(frac, 5),
                                 "source_diff": round(source_diff_frac, 5)})
                    return None, info
                clean = np.isin(labels, keep)
                ys, xs = np.where(clean)
                if len(xs) == 0:
                    info["reason"] = "empty_after_cleanup"; return None, info
                bbox_w = (int(xs.max()) - int(xs.min()) + 1) / float(w)
                bbox_h = (int(ys.max()) - int(ys.min()) + 1) / float(h)
                if bbox_w > 0.92 and bbox_h > 0.92:
                    info.update({"reason": "whole_canvas_bbox", "bbox_w": round(bbox_w, 4),
                                 "bbox_h": round(bbox_h, 4), "alpha_frac": round(frac, 5)})
                    return None, info
                source_kind = "car_num" if hp.name.lower().startswith("car_num_") else "car"
                info.update({"status": "applied", "reason": None, "path": str(companion),
                             "source_kind": source_kind,
                             "alpha_frac": round(float(clean.mean()), 5),
                             "source_diff": round(source_diff_frac, 5),
                             "components": len(comp_fracs), "largest_component": round(max(comp_fracs), 5)})
                return clean.astype(np.uint8) * 255, info
            except Exception as exc:
                info.update({"reason": "error", "error": str(exc)})
                return None, info

        companion_numbers, companion_info = _companion_number_mask(_hint_path, rgb)
        if companion_numbers is not None:
            companion_number_mode = os.environ.get("SPB_SMART_TGA_COMPANION_NUMBERS_MODE", "replace").strip().lower()
            if companion_number_mode in {"union", "merge", "add"}:
                nm = np.maximum(nm, companion_numbers)
                companion_info["mode"] = "union"
            else:
                nm = companion_numbers.copy()
                companion_info["mode"] = "replace"
            number_pixels = nm > 0
            sp[number_pixels] = 0
            tm[number_pixels] = 0
            bg[number_pixels] = 0
            decals = number_pixels | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        companion_decals, companion_decal_info = _companion_decal_mask(_hint_path, rgb)
        if companion_decals is not None:
            decal_pixels = companion_decals > 0
            # Verified sparse iRacing car_decal_* companions are sponsor/contingency evidence.
            # Let them reclaim pixels from generated Number false positives so real tiny decals
            # are not hidden behind a mis-binned wordmark/panel in Smart TGA Auto-build.
            overridden_number_pixels = int((decal_pixels & (nm > 0)).sum())
            if overridden_number_pixels:
                nm[decal_pixels] = 0
                companion_decal_info["overrode_number_pixels"] = overridden_number_pixels
                companion_decal_info["number_priority"] = "decal_override"
            else:
                companion_decal_info["overrode_number_pixels"] = 0
                companion_decal_info["number_priority"] = "none"
            sp = np.maximum(sp, (decal_pixels.astype(np.uint8) * 255))
            tm[decal_pixels] = 0
            bg[decal_pixels] = 0
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        white_livery_sponsor_final_mask, white_livery_sponsor_final_guard = _white_livery_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if white_livery_sponsor_final_mask.any():
            sp[white_livery_sponsor_final_mask > 0] = 0
            bg[white_livery_sponsor_final_mask > 0] = 0
            r["white_livery_sponsor_guard"] = _merge_white_livery_sponsor_guard(
                r.get("white_livery_sponsor_guard"),
                white_livery_sponsor_final_guard,
                white_livery_sponsor_accum_mask,
                white_livery_sponsor_final_mask,
                "final_partition",
            )
            white_livery_sponsor_accum_mask = np.maximum(
                white_livery_sponsor_accum_mask,
                white_livery_sponsor_final_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        pale_body_panel_sponsor_final_mask, pale_body_panel_sponsor_final_guard = _pale_body_panel_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if pale_body_panel_sponsor_final_mask.any():
            sp[pale_body_panel_sponsor_final_mask > 0] = 0
            bg[pale_body_panel_sponsor_final_mask > 0] = 0
            r["pale_body_panel_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("pale_body_panel_sponsor_guard"),
                pale_body_panel_sponsor_final_guard,
                pale_body_panel_sponsor_accum_mask,
                pale_body_panel_sponsor_final_mask,
                "final_partition",
                "pre_number_recovery",
            )
            pale_body_panel_sponsor_accum_mask = np.maximum(
                pale_body_panel_sponsor_accum_mask,
                pale_body_panel_sponsor_final_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        dark_body_panel_sponsor_final_mask, dark_body_panel_sponsor_final_guard = _dark_body_panel_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if dark_body_panel_sponsor_final_mask.any():
            sp[dark_body_panel_sponsor_final_mask > 0] = 0
            bg[dark_body_panel_sponsor_final_mask > 0] = 0
            r["dark_body_panel_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("dark_body_panel_sponsor_guard"),
                dark_body_panel_sponsor_final_guard,
                dark_body_panel_sponsor_accum_mask,
                dark_body_panel_sponsor_final_mask,
                "final_partition",
                "pre_number_recovery",
            )
            dark_body_panel_sponsor_accum_mask = np.maximum(
                dark_body_panel_sponsor_accum_mask,
                dark_body_panel_sponsor_final_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        ornamental_neutral_livery_sponsor_final_mask, ornamental_neutral_livery_sponsor_final_guard = (
            _ornamental_neutral_livery_sponsor_to_paint(rgb, sp, nm, tm, bg)
        )
        if ornamental_neutral_livery_sponsor_final_mask.any():
            sp[ornamental_neutral_livery_sponsor_final_mask > 0] = 0
            bg[ornamental_neutral_livery_sponsor_final_mask > 0] = 0
            r["ornamental_neutral_livery_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("ornamental_neutral_livery_sponsor_guard"),
                ornamental_neutral_livery_sponsor_final_guard,
                ornamental_neutral_livery_sponsor_accum_mask,
                ornamental_neutral_livery_sponsor_final_mask,
                "final_partition",
                "pre_number_recovery",
            )
            ornamental_neutral_livery_sponsor_accum_mask = np.maximum(
                ornamental_neutral_livery_sponsor_accum_mask,
                ornamental_neutral_livery_sponsor_final_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        white_livery_number_panel_final_mask, white_livery_number_panel_final_guard = _white_livery_number_panel_to_paint(
            rgb, nm, sp, tm, bg
        )
        if white_livery_number_panel_final_mask.any():
            nm[white_livery_number_panel_final_mask > 0] = 0
            r["white_livery_number_panel_guard"] = _merge_demoted_layer_guard(
                r.get("white_livery_number_panel_guard"),
                white_livery_number_panel_final_guard,
                white_livery_number_panel_accum_mask,
                white_livery_number_panel_final_mask,
                "final_partition",
                "pre_number_recovery",
            )
            white_livery_number_panel_accum_mask = np.maximum(
                white_livery_number_panel_accum_mask,
                white_livery_number_panel_final_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        thin_textline_number_final_mask, thin_textline_number_final_guard = _thin_textline_number_false_positive_to_sponsor(
            rgb, nm, sp, tm, bg
        )
        if thin_textline_number_final_mask.any():
            nm[thin_textline_number_final_mask > 0] = 0
            sp = np.maximum(sp, thin_textline_number_final_mask)
            thin_textline_number_final_guard["pass"] = "final_partition"
            r["thin_textline_number_false_positive_guard"] = thin_textline_number_final_guard
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        tiny_dark_sponsor_speck_guard = r.get("tiny_dark_sponsor_speck_guard") or {}
        if force_gpu_supplements or tiny_dark_sponsor_speck_guard.get("status") != "applied":
            tiny_dark_sponsor_speck_mask, tiny_dark_sponsor_speck_guard = _tiny_dark_sponsor_speck_to_paint(
                rgb, sp, nm, tm, bg
            )
            if tiny_dark_sponsor_speck_mask.any():
                sp[tiny_dark_sponsor_speck_mask > 0] = 0
                bg[tiny_dark_sponsor_speck_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["tiny_dark_sponsor_speck_guard"] = tiny_dark_sponsor_speck_guard

        if number_trim_fragment_guard.get("status") != "applied":
            number_trim_fragment_guard, number_trim_fragment_accum_mask, number_trim_fragment_applied = (
                _apply_number_trim_supplement(
                    rgb,
                    nm,
                    sp,
                    tm,
                    bg,
                    existing_guard=number_trim_fragment_guard,
                    accum_mask=number_trim_fragment_accum_mask,
                    phase="final_partition",
                )
            )
            if number_trim_fragment_applied:
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["number_trim_fragment_guard"] = number_trim_fragment_guard

        number_badge_graphic_guard = r.get("number_badge_graphic_guard") or number_badge_graphic_guard
        if number_badge_graphic_guard.get("status") != "applied":
            number_badge_graphic_final_mask, number_badge_graphic_final_guard = _number_badge_graphic_supplement(
                rgb, nm, sp, tm, bg
            )
            if number_badge_graphic_final_mask.any():
                nm = np.maximum(nm, number_badge_graphic_final_mask)
                sp[number_badge_graphic_final_mask > 0] = 0
                bg[number_badge_graphic_final_mask > 0] = 0
                tm[number_badge_graphic_final_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                number_badge_graphic_final_guard["phase"] = "final_partition"
                for component in number_badge_graphic_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                number_badge_graphic_guard = number_badge_graphic_final_guard
                r["number_badge_graphic_guard"] = number_badge_graphic_guard

        round_badge_number_guard = r.get("round_badge_number_guard") or round_badge_number_guard
        if round_badge_number_guard.get("status") != "applied":
            round_badge_number_final_mask, round_badge_number_final_guard = _round_badge_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if round_badge_number_final_mask.any():
                nm = np.maximum(nm, round_badge_number_final_mask)
                sp[round_badge_number_final_mask > 0] = 0
                bg[round_badge_number_final_mask > 0] = 0
                tm[round_badge_number_final_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                round_badge_number_final_guard["phase"] = "final_partition"
                for component in round_badge_number_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                round_badge_number_guard = round_badge_number_final_guard
                r["round_badge_number_guard"] = round_badge_number_guard

        repeated_round_badge_number_guard = r.get("repeated_round_badge_number_guard") or repeated_round_badge_number_guard
        if (
            repeated_round_badge_number_guard.get("status") != "applied"
            and round_badge_number_guard.get("status") != "applied"
        ):
            repeated_round_badge_number_final_mask, repeated_round_badge_number_final_guard = _repeated_round_badge_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if repeated_round_badge_number_final_mask.any():
                nm = np.maximum(nm, repeated_round_badge_number_final_mask)
                sp[repeated_round_badge_number_final_mask > 0] = 0
                bg[repeated_round_badge_number_final_mask > 0] = 0
                tm[repeated_round_badge_number_final_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                repeated_round_badge_number_final_guard["phase"] = "final_partition"
                for component in repeated_round_badge_number_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                repeated_round_badge_number_guard = repeated_round_badge_number_final_guard
                r["repeated_round_badge_number_guard"] = repeated_round_badge_number_guard

        yellow_panel_number_guard = r.get("yellow_panel_number_guard") or yellow_panel_number_guard
        if yellow_panel_number_guard.get("status") != "applied":
            yellow_panel_number_final_mask, yellow_panel_number_final_guard = _yellow_panel_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if yellow_panel_number_final_mask.any():
                nm = np.maximum(nm, yellow_panel_number_final_mask)
                sp[yellow_panel_number_final_mask > 0] = 0
                bg[yellow_panel_number_final_mask > 0] = 0
                tm[yellow_panel_number_final_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                yellow_panel_number_final_guard["phase"] = "final_partition"
                for component in yellow_panel_number_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                yellow_panel_number_guard = yellow_panel_number_final_guard
                r["yellow_panel_number_guard"] = yellow_panel_number_guard

        pale_sponsor_panel_number_guard = r.get("pale_sponsor_panel_number_guard") or pale_sponsor_panel_number_guard
        if pale_sponsor_panel_number_guard.get("status") != "applied":
            pale_sponsor_panel_number_final_mask, pale_sponsor_panel_number_final_guard = _pale_sponsor_panel_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if pale_sponsor_panel_number_final_mask.any():
                nm = np.maximum(nm, pale_sponsor_panel_number_final_mask)
                sp[pale_sponsor_panel_number_final_mask > 0] = 0
                bg[pale_sponsor_panel_number_final_mask > 0] = 0
                tm[pale_sponsor_panel_number_final_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                pale_sponsor_panel_number_final_guard["phase"] = "final_partition"
                for component in pale_sponsor_panel_number_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                pale_sponsor_panel_number_guard = pale_sponsor_panel_number_final_guard
                r["pale_sponsor_panel_number_guard"] = pale_sponsor_panel_number_guard

        hot_pink_paint_number_guard = r.get("hot_pink_paint_number_guard") or hot_pink_paint_number_guard
        if hot_pink_paint_number_guard.get("status") != "applied":
            hot_pink_paint_number_final_mask, hot_pink_paint_number_final_guard = _hot_pink_paint_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if hot_pink_paint_number_final_mask.any():
                hot_pink_paint_number_accum_mask = np.maximum(
                    hot_pink_paint_number_accum_mask, hot_pink_paint_number_final_mask
                )
                nm = np.maximum(nm, hot_pink_paint_number_final_mask)
                sp[hot_pink_paint_number_final_mask > 0] = 0
                bg[hot_pink_paint_number_final_mask > 0] = 0
                tm[hot_pink_paint_number_final_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                hot_pink_paint_number_final_guard["phase"] = "final_partition"
                for component in hot_pink_paint_number_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                hot_pink_paint_number_guard = hot_pink_paint_number_final_guard
                r["hot_pink_paint_number_guard"] = hot_pink_paint_number_guard

        black_blue_paint_number_guard = r.get("black_blue_paint_number_guard") or black_blue_paint_number_guard
        if black_blue_paint_number_guard.get("status") != "applied":
            black_blue_paint_number_final_mask, black_blue_paint_number_final_guard = _black_blue_paint_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if black_blue_paint_number_final_mask.any():
                nm = np.maximum(nm, black_blue_paint_number_final_mask)
                sp[black_blue_paint_number_final_mask > 0] = 0
                bg[black_blue_paint_number_final_mask > 0] = 0
                tm[black_blue_paint_number_final_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                black_blue_paint_number_final_guard["phase"] = "final_partition"
                for component in black_blue_paint_number_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                black_blue_paint_number_guard = black_blue_paint_number_final_guard
                r["black_blue_paint_number_guard"] = black_blue_paint_number_guard

        white_purple_paint_number_guard = r.get("white_purple_paint_number_guard") or white_purple_paint_number_guard
        if white_purple_paint_number_guard.get("status") != "applied":
            white_purple_paint_number_final_mask, white_purple_paint_number_final_guard = _white_purple_paint_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if white_purple_paint_number_final_mask.any():
                nm = np.maximum(nm, white_purple_paint_number_final_mask)
                sp[white_purple_paint_number_final_mask > 0] = 0
                bg[white_purple_paint_number_final_mask > 0] = 0
                tm[white_purple_paint_number_final_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                white_purple_paint_number_final_guard["phase"] = "final_partition"
                for component in white_purple_paint_number_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                white_purple_paint_number_guard = white_purple_paint_number_final_guard
                r["white_purple_paint_number_guard"] = white_purple_paint_number_guard

        red_white_dark_paint_number_guard = r.get("red_white_dark_paint_number_guard") or red_white_dark_paint_number_guard
        if red_white_dark_paint_number_guard.get("status") != "applied":
            red_white_dark_paint_number_final_mask, red_white_dark_paint_number_final_guard = _red_white_dark_paint_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if red_white_dark_paint_number_final_mask.any():
                nm = np.maximum(nm, red_white_dark_paint_number_final_mask)
                sp[red_white_dark_paint_number_final_mask > 0] = 0
                bg[red_white_dark_paint_number_final_mask > 0] = 0
                tm[red_white_dark_paint_number_final_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                red_white_dark_paint_number_final_guard["phase"] = "final_partition"
                for component in red_white_dark_paint_number_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                red_white_dark_paint_number_guard = red_white_dark_paint_number_final_guard
                r["red_white_dark_paint_number_guard"] = red_white_dark_paint_number_guard

        vertical_livery_stripe_sponsor_guard = r.get("vertical_livery_stripe_sponsor_guard") or {}
        if vertical_livery_stripe_sponsor_guard.get("status") != "applied":
            vertical_livery_stripe_final_mask, vertical_livery_stripe_final_guard = _vertical_livery_stripe_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if vertical_livery_stripe_final_mask.any():
                sp[vertical_livery_stripe_final_mask > 0] = 0
                bg[vertical_livery_stripe_final_mask > 0] = 0
                vertical_livery_stripe_final_guard["phase"] = "final_partition"
                for component in vertical_livery_stripe_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["vertical_livery_stripe_sponsor_guard"] = vertical_livery_stripe_final_guard

        solid_warm_livery_sponsor_guard = r.get("solid_warm_livery_sponsor_guard") or {}
        if solid_warm_livery_sponsor_guard.get("status") != "applied":
            solid_warm_livery_final_mask, solid_warm_livery_final_guard = _solid_warm_livery_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if solid_warm_livery_final_mask.any():
                sp[solid_warm_livery_final_mask > 0] = 0
                bg[solid_warm_livery_final_mask > 0] = 0
                solid_warm_livery_final_guard["phase"] = "final_partition"
                for component in solid_warm_livery_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["solid_warm_livery_sponsor_guard"] = solid_warm_livery_final_guard

        bright_warm_body_color_sponsor_guard = r.get("bright_warm_body_color_sponsor_guard") or {}
        if bright_warm_body_color_sponsor_guard.get("status") != "applied":
            bright_warm_body_color_final_mask, bright_warm_body_color_final_guard = _bright_warm_body_color_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if bright_warm_body_color_final_mask.any():
                sp[bright_warm_body_color_final_mask > 0] = 0
                bg[bright_warm_body_color_final_mask > 0] = 0
                bright_warm_body_color_final_guard["phase"] = "final_partition"
                for component in bright_warm_body_color_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["bright_warm_body_color_sponsor_guard"] = bright_warm_body_color_final_guard

        warm_tan_body_panel_sponsor_guard = r.get("warm_tan_body_panel_sponsor_guard") or {}
        if warm_tan_body_panel_sponsor_guard.get("status") != "applied":
            warm_tan_body_panel_final_mask, warm_tan_body_panel_final_guard = _warm_tan_body_panel_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if warm_tan_body_panel_final_mask.any():
                sp[warm_tan_body_panel_final_mask > 0] = 0
                bg[warm_tan_body_panel_final_mask > 0] = 0
                warm_tan_body_panel_final_guard["phase"] = "final_partition"
                for component in warm_tan_body_panel_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["warm_tan_body_panel_sponsor_guard"] = warm_tan_body_panel_final_guard

        diagonal_warm_livery_slash_sponsor_guard = r.get("diagonal_warm_livery_slash_sponsor_guard") or {}
        if diagonal_warm_livery_slash_sponsor_guard.get("status") != "applied":
            diagonal_warm_livery_slash_final_mask, diagonal_warm_livery_slash_final_guard = _diagonal_warm_livery_slash_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if diagonal_warm_livery_slash_final_mask.any():
                sp[diagonal_warm_livery_slash_final_mask > 0] = 0
                bg[diagonal_warm_livery_slash_final_mask > 0] = 0
                diagonal_warm_livery_slash_final_guard["phase"] = "final_partition"
                for component in diagonal_warm_livery_slash_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["diagonal_warm_livery_slash_sponsor_guard"] = diagonal_warm_livery_slash_final_guard

        red_orange_livery_block_sponsor_guard = r.get("red_orange_livery_block_sponsor_guard") or {}
        if red_orange_livery_block_sponsor_guard.get("status") != "applied":
            red_orange_livery_block_final_mask, red_orange_livery_block_final_guard = _red_orange_livery_block_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if red_orange_livery_block_final_mask.any():
                sp[red_orange_livery_block_final_mask > 0] = 0
                bg[red_orange_livery_block_final_mask > 0] = 0
                red_orange_livery_block_final_guard["phase"] = "final_partition"
                for component in red_orange_livery_block_final_guard.get("components", []):
                    component["phase"] = "final_partition"
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["red_orange_livery_block_sponsor_guard"] = red_orange_livery_block_final_guard

        # Some dark mini-number ink only becomes unclaimed after final livery demotions.
        yellow_panel_number_guard = r.get("yellow_panel_number_guard") or yellow_panel_number_guard
        if yellow_panel_number_guard.get("status") != "applied":
            yellow_panel_number_late_mask, yellow_panel_number_late_guard = _yellow_panel_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if yellow_panel_number_late_mask.any():
                nm = np.maximum(nm, yellow_panel_number_late_mask)
                sp[yellow_panel_number_late_mask > 0] = 0
                bg[yellow_panel_number_late_mask > 0] = 0
                tm[yellow_panel_number_late_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                yellow_panel_number_late_guard["phase"] = "final_livery_partition"
                for component in yellow_panel_number_late_guard.get("components", []):
                    component["phase"] = "final_livery_partition"
                yellow_panel_number_guard = yellow_panel_number_late_guard
                r["yellow_panel_number_guard"] = yellow_panel_number_guard

        pale_sponsor_panel_number_guard = r.get("pale_sponsor_panel_number_guard") or pale_sponsor_panel_number_guard
        if pale_sponsor_panel_number_guard.get("status") != "applied":
            pale_sponsor_panel_number_late_mask, pale_sponsor_panel_number_late_guard = _pale_sponsor_panel_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if pale_sponsor_panel_number_late_mask.any():
                nm = np.maximum(nm, pale_sponsor_panel_number_late_mask)
                sp[pale_sponsor_panel_number_late_mask > 0] = 0
                bg[pale_sponsor_panel_number_late_mask > 0] = 0
                tm[pale_sponsor_panel_number_late_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                pale_sponsor_panel_number_late_guard["phase"] = "final_livery_partition"
                for component in pale_sponsor_panel_number_late_guard.get("components", []):
                    component["phase"] = "final_livery_partition"
                pale_sponsor_panel_number_guard = pale_sponsor_panel_number_late_guard
                r["pale_sponsor_panel_number_guard"] = pale_sponsor_panel_number_guard

        hot_pink_paint_number_guard = r.get("hot_pink_paint_number_guard") or hot_pink_paint_number_guard
        if hot_pink_paint_number_guard.get("status") != "applied":
            hot_pink_paint_number_late_mask, hot_pink_paint_number_late_guard = _hot_pink_paint_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if hot_pink_paint_number_late_mask.any():
                hot_pink_paint_number_accum_mask = np.maximum(
                    hot_pink_paint_number_accum_mask, hot_pink_paint_number_late_mask
                )
                nm = np.maximum(nm, hot_pink_paint_number_late_mask)
                sp[hot_pink_paint_number_late_mask > 0] = 0
                bg[hot_pink_paint_number_late_mask > 0] = 0
                tm[hot_pink_paint_number_late_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                hot_pink_paint_number_late_guard["phase"] = "final_livery_partition"
                for component in hot_pink_paint_number_late_guard.get("components", []):
                    component["phase"] = "final_livery_partition"
                hot_pink_paint_number_guard = hot_pink_paint_number_late_guard
                r["hot_pink_paint_number_guard"] = hot_pink_paint_number_guard

        black_blue_paint_number_guard = r.get("black_blue_paint_number_guard") or black_blue_paint_number_guard
        if black_blue_paint_number_guard.get("status") != "applied":
            black_blue_paint_number_late_mask, black_blue_paint_number_late_guard = _black_blue_paint_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if black_blue_paint_number_late_mask.any():
                nm = np.maximum(nm, black_blue_paint_number_late_mask)
                sp[black_blue_paint_number_late_mask > 0] = 0
                bg[black_blue_paint_number_late_mask > 0] = 0
                tm[black_blue_paint_number_late_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                black_blue_paint_number_late_guard["phase"] = "final_livery_partition"
                for component in black_blue_paint_number_late_guard.get("components", []):
                    component["phase"] = "final_livery_partition"
                black_blue_paint_number_guard = black_blue_paint_number_late_guard
                r["black_blue_paint_number_guard"] = black_blue_paint_number_guard

        white_purple_paint_number_guard = r.get("white_purple_paint_number_guard") or white_purple_paint_number_guard
        if white_purple_paint_number_guard.get("status") != "applied":
            white_purple_paint_number_late_mask, white_purple_paint_number_late_guard = _white_purple_paint_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if white_purple_paint_number_late_mask.any():
                nm = np.maximum(nm, white_purple_paint_number_late_mask)
                sp[white_purple_paint_number_late_mask > 0] = 0
                bg[white_purple_paint_number_late_mask > 0] = 0
                tm[white_purple_paint_number_late_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                white_purple_paint_number_late_guard["phase"] = "final_livery_partition"
                for component in white_purple_paint_number_late_guard.get("components", []):
                    component["phase"] = "final_livery_partition"
                white_purple_paint_number_guard = white_purple_paint_number_late_guard
                r["white_purple_paint_number_guard"] = white_purple_paint_number_guard

        red_white_dark_paint_number_guard = r.get("red_white_dark_paint_number_guard") or red_white_dark_paint_number_guard
        if red_white_dark_paint_number_guard.get("status") != "applied":
            red_white_dark_paint_number_late_mask, red_white_dark_paint_number_late_guard = _red_white_dark_paint_number_supplement(
                rgb, nm, sp, tm, bg
            )
            if red_white_dark_paint_number_late_mask.any():
                nm = np.maximum(nm, red_white_dark_paint_number_late_mask)
                sp[red_white_dark_paint_number_late_mask > 0] = 0
                bg[red_white_dark_paint_number_late_mask > 0] = 0
                tm[red_white_dark_paint_number_late_mask > 0] = 0
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
                red_white_dark_paint_number_late_guard["phase"] = "final_livery_partition"
                for component in red_white_dark_paint_number_late_guard.get("components", []):
                    component["phase"] = "final_livery_partition"
                red_white_dark_paint_number_guard = red_white_dark_paint_number_late_guard
                r["red_white_dark_paint_number_guard"] = red_white_dark_paint_number_guard

        white_livery_number_panel_response_mask, white_livery_number_panel_response_guard = _white_livery_number_panel_to_paint(
            rgb, nm, sp, tm, bg
        )
        if white_livery_number_panel_response_mask.any():
            nm[white_livery_number_panel_response_mask > 0] = 0
            white_livery_number_panel_response_guard["phase"] = "response_partition"
            for component in white_livery_number_panel_response_guard.get("components", []):
                component["phase"] = "response_partition"
            r["white_livery_number_panel_guard"] = _merge_demoted_layer_guard(
                r.get("white_livery_number_panel_guard"),
                white_livery_number_panel_response_guard,
                white_livery_number_panel_accum_mask,
                white_livery_number_panel_response_mask,
                "response_partition",
                "pre_number_recovery",
            )
            white_livery_number_panel_accum_mask = np.maximum(
                white_livery_number_panel_accum_mask,
                white_livery_number_panel_response_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Smart TGA route guard: after every late number-recovery hook, remove
        # any thin sponsor textline that only became isolated in the final mask.
        thin_textline_number_response_guard = r.get("thin_textline_number_false_positive_guard") or {}
        if thin_textline_number_response_guard.get("status") != "applied":
            thin_textline_number_response_mask, thin_textline_number_response_guard = _thin_textline_number_false_positive_to_sponsor(
                rgb, nm, sp, tm, bg
            )
            if thin_textline_number_response_mask.any():
                nm[thin_textline_number_response_mask > 0] = 0
                sp = np.maximum(sp, thin_textline_number_response_mask)
                thin_textline_number_response_guard["phase"] = "response_partition"
                for component in thin_textline_number_response_guard.get("components", []):
                    component["phase"] = "response_partition"
                r["thin_textline_number_false_positive_guard"] = thin_textline_number_response_guard
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})

        # Response-stage number recovery can pull sponsor-logo glyphs back into
        # Numbers after the engine-side cleanup has already run. Demote the
        # actual response masks one final time so Auto-build exports editable
        # sponsor/logo layers instead of graphic badge fragments as numbers.
        number_logo_response_mask, number_logo_response_guard = _number_logo_false_positive_to_sponsor(
            rgb, nm, sp, tm, bg
        )
        number_logo_false_positive_accum_mask = np.maximum(
            number_logo_false_positive_accum_mask,
            number_logo_response_mask,
        )
        if number_logo_response_mask.any():
            nm[number_logo_response_mask > 0] = 0
            sp = np.maximum(sp, number_logo_response_mask)
            number_logo_response_guard["phase"] = "response_partition"
            for component in number_logo_response_guard.get("components", []):
                component["phase"] = "response_partition"
            prior_number_logo_guard = r.get("number_logo_false_positive_guard") or {}
            merged_number_logo_guard = _merge_demoted_layer_guard(
                prior_number_logo_guard,
                number_logo_response_guard,
                None,
                number_logo_response_mask,
                "response_partition",
                "pre_response_partition",
            )
            for key in (
                "max_vertical_strip_demote",
                "max_large_pale_panel_demote",
                "max_large_text_billboard_demote",
                "max_large_warm_script_demote",
            ):
                if key not in merged_number_logo_guard:
                    merged_number_logo_guard[key] = prior_number_logo_guard.get(
                        key,
                        number_logo_response_guard.get(key),
                    )
            r["number_logo_false_positive_guard"] = merged_number_logo_guard
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        large_green_logo_response_mask, large_green_logo_response_guard = _large_green_logo_false_positive_to_sponsor(
            rgb, nm, sp, tm, bg
        )
        if large_green_logo_response_mask.any():
            nm[large_green_logo_response_mask > 0] = 0
            sp = np.maximum(sp, large_green_logo_response_mask)
            large_green_logo_response_guard["phase"] = "response_partition"
            for component in large_green_logo_response_guard.get("components", []):
                component["phase"] = "response_partition"
            r["large_green_logo_false_positive_guard"] = _merge_demoted_layer_guard(
                r.get("large_green_logo_false_positive_guard") or {},
                large_green_logo_response_guard,
                None,
                large_green_logo_response_mask,
                "response_partition",
                "pre_response_partition",
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        if number_logo_response_mask.any() or large_green_logo_response_mask.any():
            panel_text_residual_response_mask, panel_text_residual_response_guard = _panel_text_residual_supplement(
                rgb, nm, sp, tm, bg
            )
            if panel_text_residual_response_mask.any():
                sp = np.maximum(sp, panel_text_residual_response_mask)
                panel_text_residual_response_guard["phase"] = "post_response_number_logo_cleanup"
                for component in panel_text_residual_response_guard.get("components", []):
                    component["phase"] = "post_response_number_logo_cleanup"
                r["panel_text_residual_guard"] = _merge_panel_text_residual_guard(
                    r.get("panel_text_residual_guard") or panel_text_residual_guard,
                    panel_text_residual_response_guard,
                    panel_text_residual_accum_mask,
                    panel_text_residual_response_mask,
                    "post_response_number_logo_cleanup",
                )
                panel_text_residual_accum_mask = np.maximum(
                    panel_text_residual_accum_mask
                    if panel_text_residual_accum_mask is not None
                    else np.zeros_like(panel_text_residual_response_mask, dtype=np.uint8),
                    panel_text_residual_response_mask,
                )
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})

        # GPU-hybrid late recovery can reintroduce logo-like islands inside round number badges.
        badge_interior_response_mask, badge_interior_response_guard = _round_number_badge_interior_to_paint(nm, sp, tm, bg)
        if badge_interior_response_mask.any():
            sp[badge_interior_response_mask > 0] = 0
            bg[badge_interior_response_mask > 0] = 0
            badge_interior_response_guard["phase"] = "response_partition"
            for component in badge_interior_response_guard.get("components", []):
                component["phase"] = "response_partition"
            existing_badge_guard = r.get("badge_interior_guard") or {}
            if existing_badge_guard.get("status") == "applied":
                existing_components = list(existing_badge_guard.get("components") or [])
                response_components = list(badge_interior_response_guard.get("components") or [])
                passes = list(existing_badge_guard.get("passes") or ["pre_response_partition"])
                if "response_partition" not in passes:
                    passes.append("response_partition")
                prior_px = int(existing_badge_guard.get("demoted_px") or 0)
                response_px = int(badge_interior_response_guard.get("demoted_px") or int((badge_interior_response_mask > 0).sum()))
                canvas_px = max(1, int(H) * int(W))
                r["badge_interior_guard"] = {
                    **existing_badge_guard,
                    "status": "applied",
                    "component_count": len(existing_components) + len(response_components),
                    "centered_island_count": (
                        int(existing_badge_guard.get("centered_island_count", 0) or 0)
                        + int(badge_interior_response_guard.get("centered_island_count", 0) or 0)
                    ),
                    "demoted_px": prior_px + response_px,
                    "demoted_frac": round(float(prior_px + response_px) / float(canvas_px), 6),
                    "capped": bool(existing_badge_guard.get("capped")) or bool(badge_interior_response_guard.get("capped")),
                    "components": (existing_components + response_components)[:8],
                    "passes": passes,
                }
            else:
                badge_interior_response_guard["passes"] = ["response_partition"]
                r["badge_interior_guard"] = badge_interior_response_guard
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # After late badge-interior cleanup, sparse outer-ring crumbs may still
        # belong to the already detected round Number badges rather than Sponsors.
        badge_sponsor_crumb_response_mask, badge_sponsor_crumb_response_guard = _round_number_badge_sponsor_crumb_to_number(nm, sp, tm, bg)
        if badge_sponsor_crumb_response_mask.any():
            nm = np.maximum(nm, badge_sponsor_crumb_response_mask)
            sp[badge_sponsor_crumb_response_mask > 0] = 0
            bg[badge_sponsor_crumb_response_mask > 0] = 0
            tm[badge_sponsor_crumb_response_mask > 0] = 0
            badge_sponsor_crumb_response_guard["phase"] = "response_partition"
            for component in badge_sponsor_crumb_response_guard.get("components", []):
                component["phase"] = "response_partition"
            existing_badge_sponsor_guard = r.get("badge_sponsor_crumb_guard") or {}
            if existing_badge_sponsor_guard.get("status") == "applied":
                existing_components = list(existing_badge_sponsor_guard.get("components") or [])
                response_components = list(badge_sponsor_crumb_response_guard.get("components") or [])
                passes = list(existing_badge_sponsor_guard.get("passes") or ["pre_response_partition"])
                if "response_partition" not in passes:
                    passes.append("response_partition")
                prior_px = int(existing_badge_sponsor_guard.get("added_px") or 0)
                response_px = int(badge_sponsor_crumb_response_guard.get("added_px") or int((badge_sponsor_crumb_response_mask > 0).sum()))
                canvas_px = max(1, int(H) * int(W))
                r["badge_sponsor_crumb_guard"] = {
                    **existing_badge_sponsor_guard,
                    "status": "applied",
                    "component_count": len(existing_components) + len(response_components),
                    "candidate_count": (
                        int(existing_badge_sponsor_guard.get("candidate_count", 0) or 0)
                        + int(badge_sponsor_crumb_response_guard.get("candidate_count", 0) or 0)
                    ),
                    "added_px": prior_px + response_px,
                    "added_frac": round(float(prior_px + response_px) / float(canvas_px), 6),
                    "capped": bool(existing_badge_sponsor_guard.get("capped")) or bool(badge_sponsor_crumb_response_guard.get("capped")),
                    "components": (existing_components + response_components)[:8],
                    "passes": passes,
                }
            else:
                badge_sponsor_crumb_response_guard["passes"] = ["response_partition"]
                r["badge_sponsor_crumb_guard"] = badge_sponsor_crumb_response_guard
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Final GPU-response cleanup can leave cool number-outline chips newly
        # unclaimed. Re-run the generic capped trim recovery after all response
        # badge/false-positive passes, even when an earlier trim pass applied.
        existing_trim_guard = r.get("number_trim_fragment_guard") or number_trim_fragment_guard or {}
        number_trim_fragment_guard, number_trim_fragment_accum_mask, number_trim_fragment_applied = (
            _apply_number_trim_supplement(
                rgb,
                nm,
                sp,
                tm,
                bg,
                existing_guard=existing_trim_guard,
                accum_mask=number_trim_fragment_accum_mask,
                phase="post_response_badge_cleanup",
            )
        )
        r["number_trim_fragment_guard"] = number_trim_fragment_guard
        if number_trim_fragment_applied:
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Some panel-anchored sponsor/logo Paint islands only become residual
        # after all GPU-response false-positive, badge, and trim passes finish.
        # Re-run the same constrained helper on the final response masks without
        # widening its thresholds; already-promoted islands are now claimed and
        # therefore naturally excluded from the residual candidate set.
        panel_text_residual_final_response_mask, panel_text_residual_final_response_guard = _panel_text_residual_supplement(
            rgb, nm, sp, tm, bg
        )
        if panel_text_residual_final_response_mask.any():
            sp = np.maximum(sp, panel_text_residual_final_response_mask)
            panel_text_residual_final_response_guard["phase"] = "post_response_final_mask_cleanup"
            for component in panel_text_residual_final_response_guard.get("components", []):
                component["phase"] = "post_response_final_mask_cleanup"
            r["panel_text_residual_guard"] = _merge_panel_text_residual_guard(
                r.get("panel_text_residual_guard") or panel_text_residual_guard,
                panel_text_residual_final_response_guard,
                panel_text_residual_accum_mask,
                panel_text_residual_final_response_mask,
                "post_response_final_mask_cleanup",
            )
            panel_text_residual_accum_mask = (
                panel_text_residual_final_response_mask.copy()
                if panel_text_residual_accum_mask is None
                else np.maximum(panel_text_residual_accum_mask, panel_text_residual_final_response_mask)
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

            # A newly promoted panel crumb can become the local Sponsor anchor
            # for a neighboring micro glyph. Run one bounded follow-up pass on
            # the updated masks; this propagates only through the existing
            # residual criteria and stops after a single extra hop.
            panel_text_residual_followup_mask, panel_text_residual_followup_guard = _panel_text_residual_supplement(
                rgb, nm, sp, tm, bg
            )
            if panel_text_residual_followup_mask.any():
                sp = np.maximum(sp, panel_text_residual_followup_mask)
                panel_text_residual_followup_guard["phase"] = "post_response_final_mask_cleanup_followup"
                for component in panel_text_residual_followup_guard.get("components", []):
                    component["phase"] = "post_response_final_mask_cleanup_followup"
                r["panel_text_residual_guard"] = _merge_panel_text_residual_guard(
                    r.get("panel_text_residual_guard") or panel_text_residual_followup_guard,
                    panel_text_residual_followup_guard,
                    panel_text_residual_accum_mask,
                    panel_text_residual_followup_mask,
                    "post_response_final_mask_cleanup_followup",
                )
                panel_text_residual_accum_mask = (
                    panel_text_residual_followup_mask.copy()
                    if panel_text_residual_accum_mask is None
                    else np.maximum(panel_text_residual_accum_mask, panel_text_residual_followup_mask)
                )
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})

        white_livery_number_panel_final_response_mask, white_livery_number_panel_final_response_guard = _white_livery_number_panel_to_paint(
            rgb, nm, sp, tm, bg
        )
        if white_livery_number_panel_final_response_mask.any():
            nm[white_livery_number_panel_final_response_mask > 0] = 0
            white_livery_number_panel_final_response_guard["phase"] = "post_response_final_mask_cleanup"
            for component in white_livery_number_panel_final_response_guard.get("components", []):
                component["phase"] = "post_response_final_mask_cleanup"
            r["white_livery_number_panel_guard"] = _merge_demoted_layer_guard(
                r.get("white_livery_number_panel_guard"),
                white_livery_number_panel_final_response_guard,
                white_livery_number_panel_accum_mask,
                white_livery_number_panel_final_response_mask,
                "post_response_final_mask_cleanup",
                "pre_number_recovery",
            )
            white_livery_number_panel_accum_mask = np.maximum(
                white_livery_number_panel_accum_mask,
                white_livery_number_panel_final_response_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

            # Final white-livery number-panel cleanup can expose tiny
            # panel-anchored sponsor crumbs after the normal final residual
            # retry has already run. Reuse the same constrained helper without
            # changing its thresholds so this remains an ordering fix only.
            panel_text_residual_white_panel_mask, panel_text_residual_white_panel_guard = _panel_text_residual_supplement(
                rgb, nm, sp, tm, bg
            )
            if panel_text_residual_white_panel_mask.any():
                sp = np.maximum(sp, panel_text_residual_white_panel_mask)
                panel_text_residual_white_panel_guard["phase"] = "post_response_white_livery_number_panel_cleanup"
                for component in panel_text_residual_white_panel_guard.get("components", []):
                    component["phase"] = "post_response_white_livery_number_panel_cleanup"
                r["panel_text_residual_guard"] = _merge_panel_text_residual_guard(
                    r.get("panel_text_residual_guard") or panel_text_residual_white_panel_guard,
                    panel_text_residual_white_panel_guard,
                    panel_text_residual_accum_mask,
                    panel_text_residual_white_panel_mask,
                    "post_response_white_livery_number_panel_cleanup",
                )
                panel_text_residual_accum_mask = (
                    panel_text_residual_white_panel_mask.copy()
                    if panel_text_residual_accum_mask is None
                    else np.maximum(panel_text_residual_accum_mask, panel_text_residual_white_panel_mask)
                )
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})

        decorative_livery_response_mask, decorative_livery_response_guard = _decorative_livery_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if decorative_livery_response_mask.any():
            sp[decorative_livery_response_mask > 0] = 0
            bg[decorative_livery_response_mask > 0] = 0
            decorative_livery_response_guard["phase"] = "post_response_final_mask_cleanup"
            for component in decorative_livery_response_guard.get("components", []):
                component["phase"] = "post_response_final_mask_cleanup"
            r["decorative_livery_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("decorative_livery_sponsor_guard") or decorative_livery_sponsor_guard,
                decorative_livery_response_guard,
                decorative_livery_sponsor_accum_mask,
                decorative_livery_response_mask,
                "post_response_final_mask_cleanup",
                "pre_sponsor_fragment",
            )
            decorative_livery_sponsor_accum_mask = np.maximum(
                decorative_livery_sponsor_accum_mask,
                decorative_livery_response_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        smooth_red_body_panel_response_mask, smooth_red_body_panel_response_guard = _smooth_red_body_panel_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if smooth_red_body_panel_response_mask.any():
            sp[smooth_red_body_panel_response_mask > 0] = 0
            bg[smooth_red_body_panel_response_mask > 0] = 0
            r["smooth_red_body_panel_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("smooth_red_body_panel_sponsor_guard") or smooth_red_body_panel_sponsor_guard,
                smooth_red_body_panel_response_guard,
                smooth_red_body_panel_sponsor_accum_mask,
                smooth_red_body_panel_response_mask,
                "post_response_final_mask_cleanup",
                "pre_sponsor_fragment",
            )
            smooth_red_body_panel_sponsor_accum_mask = np.maximum(
                smooth_red_body_panel_sponsor_accum_mask,
                smooth_red_body_panel_response_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        number_logo_post_decorative_mask, number_logo_post_decorative_guard = _number_logo_false_positive_to_sponsor(
            rgb, nm, sp, tm, bg
        )
        number_logo_false_positive_accum_mask = np.maximum(
            number_logo_false_positive_accum_mask,
            number_logo_post_decorative_mask,
        )
        if number_logo_post_decorative_mask.any():
            nm[number_logo_post_decorative_mask > 0] = 0
            sp = np.maximum(sp, number_logo_post_decorative_mask)
            number_logo_post_decorative_guard["phase"] = "post_response_decorative_cleanup"
            for component in number_logo_post_decorative_guard.get("components", []):
                component["phase"] = "post_response_decorative_cleanup"
            prior_number_logo_guard = r.get("number_logo_false_positive_guard") or {}
            merged_number_logo_guard = _merge_demoted_layer_guard(
                prior_number_logo_guard,
                number_logo_post_decorative_guard,
                None,
                number_logo_post_decorative_mask,
                "post_response_decorative_cleanup",
                "pre_response_partition",
            )
            for key in (
                "max_vertical_strip_demote",
                "max_large_pale_panel_demote",
                "max_large_text_billboard_demote",
                "max_large_warm_script_demote",
            ):
                if key not in merged_number_logo_guard:
                    merged_number_logo_guard[key] = prior_number_logo_guard.get(
                        key,
                        number_logo_post_decorative_guard.get(key),
                    )
            r["number_logo_false_positive_guard"] = merged_number_logo_guard
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Last response-stage layer mutations can expose sponsor/logo crumbs in
        # Paint after the earlier residual retries. Reuse the same constrained
        # helper at materialization time so the GPU-hybrid route matches the
        # engine's final mask semantics without widening any recovery thresholds.
        panel_text_residual_materialization_mask, panel_text_residual_materialization_guard = _panel_text_residual_supplement(
            rgb, nm, sp, tm, bg
        )
        if panel_text_residual_materialization_mask.any():
            sp = np.maximum(sp, panel_text_residual_materialization_mask)
            panel_text_residual_materialization_guard["phase"] = "pre_response_materialization"
            for component in panel_text_residual_materialization_guard.get("components", []):
                component["phase"] = "pre_response_materialization"
            r["panel_text_residual_guard"] = _merge_panel_text_residual_guard(
                r.get("panel_text_residual_guard") or panel_text_residual_guard,
                panel_text_residual_materialization_guard,
                panel_text_residual_accum_mask,
                panel_text_residual_materialization_mask,
                "pre_response_materialization",
            )
            panel_text_residual_accum_mask = (
                panel_text_residual_materialization_mask.copy()
                if panel_text_residual_accum_mask is None
                else np.maximum(panel_text_residual_accum_mask, panel_text_residual_materialization_mask)
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Late Sponsor recovery can also expose textless decorative livery
        # flecks after the earlier decorative retries. Re-run the same strict
        # demoter at materialization time so response PNG masks match engine
        # final-mask semantics without broadening the classifier.
        decorative_livery_materialization_mask, decorative_livery_materialization_guard = _decorative_livery_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if decorative_livery_materialization_mask.any():
            sp[decorative_livery_materialization_mask > 0] = 0
            bg[decorative_livery_materialization_mask > 0] = 0
            decorative_livery_materialization_guard["phase"] = "pre_response_materialization"
            for component in decorative_livery_materialization_guard.get("components", []):
                component["phase"] = "pre_response_materialization"
            r["decorative_livery_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("decorative_livery_sponsor_guard") or decorative_livery_sponsor_guard,
                decorative_livery_materialization_guard,
                decorative_livery_sponsor_accum_mask,
                decorative_livery_materialization_mask,
                "pre_response_materialization",
                "pre_sponsor_fragment",
            )
            decorative_livery_sponsor_accum_mask = np.maximum(
                decorative_livery_sponsor_accum_mask,
                decorative_livery_materialization_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Late Sponsor recovery can expose paint-shaped red livery tiles after
        # the earlier smooth-red retries. Re-run the same strict demoter at
        # response materialization so real Auto-build layers match engine masks.
        smooth_red_body_panel_materialization_mask, smooth_red_body_panel_materialization_guard = _smooth_red_body_panel_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if smooth_red_body_panel_materialization_mask.any():
            sp[smooth_red_body_panel_materialization_mask > 0] = 0
            bg[smooth_red_body_panel_materialization_mask > 0] = 0
            smooth_red_body_panel_materialization_guard["phase"] = "pre_response_materialization"
            for component in smooth_red_body_panel_materialization_guard.get("components", []):
                component["phase"] = "pre_response_materialization"
            r["smooth_red_body_panel_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("smooth_red_body_panel_sponsor_guard") or smooth_red_body_panel_sponsor_guard,
                smooth_red_body_panel_materialization_guard,
                smooth_red_body_panel_sponsor_accum_mask,
                smooth_red_body_panel_materialization_mask,
                "pre_response_materialization",
                "pre_sponsor_fragment",
            )
            smooth_red_body_panel_sponsor_accum_mask = np.maximum(
                smooth_red_body_panel_sponsor_accum_mask,
                smooth_red_body_panel_materialization_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Late Sponsor materialization can expose red number-interior islands
        # after the main single-digit recovery has already built the editable
        # Number layer. Re-run the same constrained supplement so final masks
        # preserve number interiors before real layer PNGs are emitted.
        red_single_digit_number_materialization_mask, red_single_digit_number_materialization_guard = _red_single_digit_number_supplement(
            rgb, nm, sp, tm, bg
        )
        if red_single_digit_number_materialization_mask.any():
            nm = np.maximum(nm, red_single_digit_number_materialization_mask)
            sp[red_single_digit_number_materialization_mask > 0] = 0
            bg[red_single_digit_number_materialization_mask > 0] = 0
            tm[red_single_digit_number_materialization_mask > 0] = 0
            red_single_digit_number_materialization_guard["phase"] = "pre_response_materialization"
            for component in red_single_digit_number_materialization_guard.get("components", []):
                component["phase"] = "pre_response_materialization"
            prior_red_single_digit_guard = r.get("red_single_digit_number_guard") or {}
            prior_components = list(prior_red_single_digit_guard.get("components") or [])
            response_components = list(red_single_digit_number_materialization_guard.get("components") or [])
            merged_red_single_digit_guard = dict(prior_red_single_digit_guard)
            merged_red_single_digit_guard["status"] = "applied"
            merged_red_single_digit_guard["phase"] = "merged"
            merged_red_single_digit_guard["passes"] = list(dict.fromkeys(
                list(prior_red_single_digit_guard.get("passes") or ["pre_number_recovery"])
                + ["pre_response_materialization"]
            ))
            merged_red_single_digit_guard["components"] = (prior_components + response_components)[:16]
            merged_red_single_digit_guard["component_count"] = len(prior_components) + len(response_components)
            merged_red_single_digit_guard["pre_response_materialization_component_count"] = int(
                red_single_digit_number_materialization_guard.get("component_count") or len(response_components)
            )
            merged_red_single_digit_guard["pre_response_materialization_existing_number_fragment_count"] = int(
                red_single_digit_number_materialization_guard.get("existing_number_fragment_count") or 0
            )
            merged_red_single_digit_guard["pre_response_materialization_existing_number_fragment_px"] = int(
                red_single_digit_number_materialization_guard.get("existing_number_fragment_px") or 0
            )
            r["red_single_digit_number_guard"] = merged_red_single_digit_guard
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # The red-number recovery above can split a sponsor-connected livery
        # panel into a now-classifiable smooth red body piece. Run one final
        # strict demotion pass at the true response boundary so the emitted
        # real layers match the post-recovery mask topology.
        smooth_red_body_panel_post_number_mask, smooth_red_body_panel_post_number_guard = _smooth_red_body_panel_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if smooth_red_body_panel_post_number_mask.any():
            sp[smooth_red_body_panel_post_number_mask > 0] = 0
            bg[smooth_red_body_panel_post_number_mask > 0] = 0
            smooth_red_body_panel_post_number_guard["phase"] = "post_response_number_materialization"
            for component in smooth_red_body_panel_post_number_guard.get("components", []):
                component["phase"] = "post_response_number_materialization"
            r["smooth_red_body_panel_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("smooth_red_body_panel_sponsor_guard") or smooth_red_body_panel_sponsor_guard,
                smooth_red_body_panel_post_number_guard,
                smooth_red_body_panel_sponsor_accum_mask,
                smooth_red_body_panel_post_number_mask,
                "post_response_number_materialization",
                "pre_sponsor_fragment",
            )
            smooth_red_body_panel_sponsor_accum_mask = np.maximum(
                smooth_red_body_panel_sponsor_accum_mask,
                smooth_red_body_panel_post_number_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        decorative_livery_post_smooth_mask, decorative_livery_post_smooth_guard = _decorative_livery_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if decorative_livery_post_smooth_mask.any():
            sp[decorative_livery_post_smooth_mask > 0] = 0
            bg[decorative_livery_post_smooth_mask > 0] = 0
            decorative_livery_post_smooth_guard["phase"] = "post_smooth_pre_response_materialization"
            for component in decorative_livery_post_smooth_guard.get("components", []):
                component["phase"] = "post_smooth_pre_response_materialization"
            r["decorative_livery_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("decorative_livery_sponsor_guard") or decorative_livery_sponsor_guard,
                decorative_livery_post_smooth_guard,
                decorative_livery_sponsor_accum_mask,
                decorative_livery_post_smooth_mask,
                "post_smooth_pre_response_materialization",
                "pre_sponsor_fragment",
            )
            decorative_livery_sponsor_accum_mask = np.maximum(
                decorative_livery_sponsor_accum_mask,
                decorative_livery_post_smooth_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Some late demotion/recovery passes can leave a final Sponsor-anchored
        # logo crumb in Paint after the earlier panel-text residual retries.
        # Run the same constrained helper once at the true response boundary;
        # this is an ordering replay, not a threshold broadening.
        panel_text_residual_final_boundary_mask, panel_text_residual_final_boundary_guard = _panel_text_residual_supplement(
            rgb, nm, sp, tm, bg
        )
        if panel_text_residual_final_boundary_mask.any():
            sp = np.maximum(sp, panel_text_residual_final_boundary_mask)
            panel_text_residual_final_boundary_guard["phase"] = "post_response_layer_boundary"
            for component in panel_text_residual_final_boundary_guard.get("components", []):
                component["phase"] = "post_response_layer_boundary"
            r["panel_text_residual_guard"] = _merge_panel_text_residual_guard(
                r.get("panel_text_residual_guard") or panel_text_residual_final_boundary_guard,
                panel_text_residual_final_boundary_guard,
                panel_text_residual_accum_mask,
                panel_text_residual_final_boundary_mask,
                "post_response_layer_boundary",
            )
            panel_text_residual_accum_mask = (
                panel_text_residual_final_boundary_mask.copy()
                if panel_text_residual_accum_mask is None
                else np.maximum(panel_text_residual_accum_mask, panel_text_residual_final_boundary_mask)
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 444: the final panel-text boundary pass can isolate small
        # red/white DLM livery swooshes in Sponsors after the route-level
        # warm-arc retries have already run. Replay the same strict demoter at
        # the true response boundary without widening sponsor/text recovery.
        warm_livery_arc_layer_boundary_mask, warm_livery_arc_layer_boundary_guard = _warm_livery_arc_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if warm_livery_arc_layer_boundary_mask.any():
            sp[warm_livery_arc_layer_boundary_mask > 0] = 0
            bg[warm_livery_arc_layer_boundary_mask > 0] = 0
            warm_livery_arc_layer_boundary_guard["phase"] = "post_response_layer_boundary"
            for component in warm_livery_arc_layer_boundary_guard.get("components", []):
                component["phase"] = "post_response_layer_boundary"
            r["warm_livery_arc_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("warm_livery_arc_sponsor_guard") or warm_livery_arc_sponsor_guard,
                warm_livery_arc_layer_boundary_guard,
                warm_livery_arc_sponsor_accum_mask,
                warm_livery_arc_layer_boundary_mask,
                "post_response_layer_boundary",
                "pre_sponsor_fragment",
            )
            warm_livery_arc_sponsor_accum_mask = np.maximum(
                warm_livery_arc_sponsor_accum_mask,
                warm_livery_arc_layer_boundary_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 442: the final panel-text boundary pass can leave textless DLM
        # woodgrain/body-art panels newly isolated in Sponsors. Re-run the same
        # strict decorative demoter once at the true response boundary.
        decorative_livery_layer_boundary_mask, decorative_livery_layer_boundary_guard = _decorative_livery_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if decorative_livery_layer_boundary_mask.any():
            sp[decorative_livery_layer_boundary_mask > 0] = 0
            bg[decorative_livery_layer_boundary_mask > 0] = 0
            decorative_livery_layer_boundary_guard["phase"] = "post_response_layer_boundary"
            for component in decorative_livery_layer_boundary_guard.get("components", []):
                component["phase"] = "post_response_layer_boundary"
            r["decorative_livery_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("decorative_livery_sponsor_guard") or decorative_livery_sponsor_guard,
                decorative_livery_layer_boundary_guard,
                decorative_livery_sponsor_accum_mask,
                decorative_livery_layer_boundary_mask,
                "post_response_layer_boundary",
                "pre_sponsor_fragment",
            )
            decorative_livery_sponsor_accum_mask = np.maximum(
                decorative_livery_sponsor_accum_mask,
                decorative_livery_layer_boundary_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 427: the final panel-text recovery can add tiny DLM dark-red
        # livery shards after the last smooth-red retry. Re-run the same strict
        # demoter once at the true response boundary; this is ordering-only and
        # keeps sponsor/text thresholds unchanged.
        smooth_red_body_panel_layer_boundary_mask, smooth_red_body_panel_layer_boundary_guard = _smooth_red_body_panel_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if smooth_red_body_panel_layer_boundary_mask.any():
            sp[smooth_red_body_panel_layer_boundary_mask > 0] = 0
            bg[smooth_red_body_panel_layer_boundary_mask > 0] = 0
            smooth_red_body_panel_layer_boundary_guard["phase"] = "post_response_layer_boundary"
            for component in smooth_red_body_panel_layer_boundary_guard.get("components", []):
                component["phase"] = "post_response_layer_boundary"
            r["smooth_red_body_panel_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("smooth_red_body_panel_sponsor_guard") or smooth_red_body_panel_sponsor_guard,
                smooth_red_body_panel_layer_boundary_guard,
                smooth_red_body_panel_sponsor_accum_mask,
                smooth_red_body_panel_layer_boundary_mask,
                "post_response_layer_boundary",
                "pre_sponsor_fragment",
            )
            smooth_red_body_panel_sponsor_accum_mask = np.maximum(
                smooth_red_body_panel_sponsor_accum_mask,
                smooth_red_body_panel_layer_boundary_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 442: one final response-boundary pass catches DLM woodgrain/
        # body-art panels that only satisfy the decorative signature after all
        # earlier final layer cleanups have settled.
        decorative_livery_final_boundary_mask, decorative_livery_final_boundary_guard = _decorative_livery_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if decorative_livery_final_boundary_mask.any():
            sp[decorative_livery_final_boundary_mask > 0] = 0
            bg[decorative_livery_final_boundary_mask > 0] = 0
            decorative_livery_final_boundary_guard["phase"] = "post_response_final_layer_boundary"
            for component in decorative_livery_final_boundary_guard.get("components", []):
                component["phase"] = "post_response_final_layer_boundary"
            r["decorative_livery_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("decorative_livery_sponsor_guard") or decorative_livery_sponsor_guard,
                decorative_livery_final_boundary_guard,
                decorative_livery_sponsor_accum_mask,
                decorative_livery_final_boundary_mask,
                "post_response_final_layer_boundary",
                "pre_sponsor_fragment",
            )
            decorative_livery_sponsor_accum_mask = np.maximum(
                decorative_livery_sponsor_accum_mask,
                decorative_livery_final_boundary_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 444: the final decorative/smooth livery demotions can split a
        # small DLM red/white swoosh into its own component. Replay the strict
        # warm-arc demoter at the final response boundary before PNG emission.
        warm_livery_arc_final_boundary_mask, warm_livery_arc_final_boundary_guard = _warm_livery_arc_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if warm_livery_arc_final_boundary_mask.any():
            sp[warm_livery_arc_final_boundary_mask > 0] = 0
            bg[warm_livery_arc_final_boundary_mask > 0] = 0
            warm_livery_arc_final_boundary_guard["phase"] = "post_response_final_layer_boundary"
            for component in warm_livery_arc_final_boundary_guard.get("components", []):
                component["phase"] = "post_response_final_layer_boundary"
            r["warm_livery_arc_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("warm_livery_arc_sponsor_guard") or warm_livery_arc_sponsor_guard,
                warm_livery_arc_final_boundary_guard,
                warm_livery_arc_sponsor_accum_mask,
                warm_livery_arc_final_boundary_mask,
                "post_response_final_layer_boundary",
                "pre_sponsor_fragment",
            )
            warm_livery_arc_sponsor_accum_mask = np.maximum(
                warm_livery_arc_sponsor_accum_mask,
                warm_livery_arc_final_boundary_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 448: the last livery demotion can expose tiny vertical DLM
        # sponsor-text slivers after the prior panel-text retries have run.
        # Replay the same constrained helper once more at PNG emission time.
        panel_text_residual_png_boundary_mask, panel_text_residual_png_boundary_guard = _panel_text_residual_supplement(
            rgb, nm, sp, tm, bg
        )
        if panel_text_residual_png_boundary_mask.any():
            sp = np.maximum(sp, panel_text_residual_png_boundary_mask)
            panel_text_residual_png_boundary_guard["phase"] = "pre_png_emission"
            for component in panel_text_residual_png_boundary_guard.get("components", []):
                component["phase"] = "pre_png_emission"
            r["panel_text_residual_guard"] = _merge_panel_text_residual_guard(
                r.get("panel_text_residual_guard") or panel_text_residual_png_boundary_guard,
                panel_text_residual_png_boundary_guard,
                panel_text_residual_accum_mask,
                panel_text_residual_png_boundary_mask,
                "pre_png_emission",
            )
            panel_text_residual_accum_mask = (
                panel_text_residual_png_boundary_mask.copy()
                if panel_text_residual_accum_mask is None
                else np.maximum(panel_text_residual_accum_mask, panel_text_residual_png_boundary_mask)
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Final response cleanup can expose a sponsor-owned colored shell
        # around an already detected race number. Re-run the same constrained
        # helper at the PNG boundary so GPU-hybrid Auto-build matches the
        # core car_layers partition.
        _apply_large_stylized_number_shell("pre_png_emission")
        existing_trim_guard = r.get("number_trim_fragment_guard") or number_trim_fragment_guard or {}
        next_number_trim_fragment_guard, number_trim_fragment_accum_mask, number_trim_fragment_applied = (
            _apply_number_trim_supplement(
                rgb,
                nm,
                sp,
                tm,
                bg,
                existing_guard=existing_trim_guard,
                accum_mask=number_trim_fragment_accum_mask,
                phase="post_png_large_stylized_number_shell",
            )
        )
        if number_trim_fragment_applied or existing_trim_guard.get("status") != "applied":
            number_trim_fragment_guard = next_number_trim_fragment_guard
        else:
            number_trim_fragment_guard = existing_trim_guard
        r["number_trim_fragment_guard"] = number_trim_fragment_guard
        if number_trim_fragment_applied:
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 459: final number-shell/trim cleanup can be the step that makes
        # a tiny blue sponsor underline separable from Paint/background. Replay
        # the same strict panel-text helper after that last mask mutation.
        panel_text_residual_post_trim_mask, panel_text_residual_post_trim_guard = _panel_text_residual_supplement(
            rgb, nm, sp, tm, bg
        )
        if panel_text_residual_post_trim_mask.any():
            sp = np.maximum(sp, panel_text_residual_post_trim_mask)
            panel_text_residual_post_trim_guard["phase"] = "post_png_number_trim"
            for component in panel_text_residual_post_trim_guard.get("components", []):
                component["phase"] = "post_png_number_trim"
            r["panel_text_residual_guard"] = _merge_panel_text_residual_guard(
                r.get("panel_text_residual_guard") or panel_text_residual_post_trim_guard,
                panel_text_residual_post_trim_guard,
                panel_text_residual_accum_mask,
                panel_text_residual_post_trim_mask,
                "post_png_number_trim",
            )
            panel_text_residual_accum_mask = (
                panel_text_residual_post_trim_mask.copy()
                if panel_text_residual_accum_mask is None
                else np.maximum(panel_text_residual_accum_mask, panel_text_residual_post_trim_mask)
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 484: pre-PNG stylized-number recovery can reintroduce dense
        # sponsor-logo panels as Numbers after earlier response cleanups. Replay
        # the capped logo demoter at the PNG boundary before masks are emitted.
        number_logo_png_boundary_mask, number_logo_png_boundary_guard = _number_logo_false_positive_to_sponsor(
            rgb, nm, sp, tm, bg
        )
        number_logo_false_positive_accum_mask = np.maximum(
            number_logo_false_positive_accum_mask,
            number_logo_png_boundary_mask,
        )
        if number_logo_png_boundary_mask.any():
            nm[number_logo_png_boundary_mask > 0] = 0
            sp = np.maximum(sp, number_logo_png_boundary_mask)
            number_logo_png_boundary_guard["phase"] = "pre_png_emission"
            for component in number_logo_png_boundary_guard.get("components", []):
                component["phase"] = "pre_png_emission"
            prior_number_logo_guard = r.get("number_logo_false_positive_guard") or {}
            merged_number_logo_guard = _merge_demoted_layer_guard(
                prior_number_logo_guard,
                number_logo_png_boundary_guard,
                None,
                number_logo_png_boundary_mask,
                "pre_png_emission",
                "pre_response_partition",
            )
            for key in (
                "max_vertical_strip_demote",
                "max_large_pale_panel_demote",
                "max_large_text_billboard_demote",
                "max_large_warm_script_demote",
            ):
                if key not in merged_number_logo_guard:
                    merged_number_logo_guard[key] = prior_number_logo_guard.get(
                        key,
                        number_logo_png_boundary_guard.get(key),
                    )
            r["number_logo_false_positive_guard"] = merged_number_logo_guard
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 497: the final PNG-boundary number-logo demotion can be the
        # last step that makes small sponsor-owned wordmark tails visible in
        # Paint. Replay the same constrained panel-text helper after that
        # cleanup so route output matches the final engine partition.
        panel_text_residual_post_number_logo_mask, panel_text_residual_post_number_logo_guard = _panel_text_residual_supplement(
            rgb, nm, sp, tm, bg
        )
        if panel_text_residual_post_number_logo_mask.any():
            sp = np.maximum(sp, panel_text_residual_post_number_logo_mask)
            panel_text_residual_post_number_logo_guard["phase"] = "post_png_number_logo_cleanup"
            for component in panel_text_residual_post_number_logo_guard.get("components", []):
                component["phase"] = "post_png_number_logo_cleanup"
            r["panel_text_residual_guard"] = _merge_panel_text_residual_guard(
                r.get("panel_text_residual_guard") or panel_text_residual_post_number_logo_guard,
                panel_text_residual_post_number_logo_guard,
                panel_text_residual_accum_mask,
                panel_text_residual_post_number_logo_mask,
                "post_png_number_logo_cleanup",
            )
            panel_text_residual_accum_mask = (
                panel_text_residual_post_number_logo_mask.copy()
                if panel_text_residual_accum_mask is None
                else np.maximum(panel_text_residual_accum_mask, panel_text_residual_post_number_logo_mask)
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 504: horizontal DLM livery strokes can become eligible for the
        # decorative demoter only after PNG-boundary panel-text/logo replays
        # settle final Sponsor ownership. Re-run before encoding masks.
        decorative_livery_png_mask, decorative_livery_png_guard = _decorative_livery_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if decorative_livery_png_mask.any():
            sp[decorative_livery_png_mask > 0] = 0
            bg[decorative_livery_png_mask > 0] = 0
            decorative_livery_png_guard["phase"] = "pre_png_emission"
            for component in decorative_livery_png_guard.get("components", []):
                component["phase"] = "pre_png_emission"
            r["decorative_livery_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("decorative_livery_sponsor_guard") or decorative_livery_sponsor_guard,
                decorative_livery_png_guard,
                decorative_livery_sponsor_accum_mask,
                decorative_livery_png_mask,
                "pre_png_emission",
                "pre_sponsor_fragment",
            )
            decorative_livery_sponsor_accum_mask = np.maximum(
                decorative_livery_sponsor_accum_mask,
                decorative_livery_png_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 503: some route-only side-wrap Sponsor components become
        # eligible for vertical livery demotion only after the PNG-boundary
        # number/logo and panel-text replays settle the final masks.
        vertical_livery_stripe_png_guard = r.get("vertical_livery_stripe_sponsor_guard") or {}
        if vertical_livery_stripe_png_guard.get("status") != "applied":
            vertical_livery_stripe_png_mask, vertical_livery_stripe_png_guard = _vertical_livery_stripe_sponsor_to_paint(
                rgb, sp, nm, tm, bg
            )
            if vertical_livery_stripe_png_mask.any():
                sp[vertical_livery_stripe_png_mask > 0] = 0
                bg[vertical_livery_stripe_png_mask > 0] = 0
                vertical_livery_stripe_png_guard["phase"] = "pre_png_emission"
                for component in vertical_livery_stripe_png_guard.get("components", []):
                    component["phase"] = "pre_png_emission"
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["vertical_livery_stripe_sponsor_guard"] = vertical_livery_stripe_png_guard

        # Cycle 508: the final PNG-boundary livery demoters can expose tiny
        # sponsor wordmark hairlines after the last panel-text replay. Re-run
        # the same capped, anchor-gated helper at the actual mask emission
        # boundary so emitted PNG masks match the final Smart TGA ownership.
        panel_text_residual_emit_mask, panel_text_residual_emit_guard = _panel_text_residual_supplement(
            rgb, nm, sp, tm, bg
        )
        if panel_text_residual_emit_mask.any():
            sp = np.maximum(sp, panel_text_residual_emit_mask)
            panel_text_residual_emit_guard["phase"] = "pre_png_emission_after_livery_demoters"
            for component in panel_text_residual_emit_guard.get("components", []):
                component["phase"] = "pre_png_emission_after_livery_demoters"
            r["panel_text_residual_guard"] = _merge_panel_text_residual_guard(
                r.get("panel_text_residual_guard") or panel_text_residual_emit_guard,
                panel_text_residual_emit_guard,
                panel_text_residual_accum_mask,
                panel_text_residual_emit_mask,
                "pre_png_emission_after_livery_demoters",
            )
            panel_text_residual_accum_mask = (
                panel_text_residual_emit_mask.copy()
                if panel_text_residual_accum_mask is None
                else np.maximum(panel_text_residual_accum_mask, panel_text_residual_emit_mask)
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})
            emit_bucket_counts = panel_text_residual_emit_guard.get("bucket_counts") or {}
            if int(emit_bucket_counts.get("sponsor_panel_neutral_textline_gap", 0) or 0) > 0:
                # Flat sponsor text gaps can be fragmented into adjacent
                # residual strokes. The first PNG-boundary pass may materialize
                # enough Sponsor context for the neighbor stroke.
                panel_text_residual_emit_followup_mask, panel_text_residual_emit_followup_guard = _panel_text_residual_supplement(
                    rgb, nm, sp, tm, bg
                )
                if panel_text_residual_emit_followup_mask.any():
                    sp = np.maximum(sp, panel_text_residual_emit_followup_mask)
                    panel_text_residual_emit_followup_guard["phase"] = "pre_png_emission_neighbor_textline"
                    for component in panel_text_residual_emit_followup_guard.get("components", []):
                        component["phase"] = "pre_png_emission_neighbor_textline"
                    r["panel_text_residual_guard"] = _merge_panel_text_residual_guard(
                        r.get("panel_text_residual_guard") or panel_text_residual_emit_followup_guard,
                        panel_text_residual_emit_followup_guard,
                        panel_text_residual_accum_mask,
                        panel_text_residual_emit_followup_mask,
                        "pre_png_emission_neighbor_textline",
                    )
                    panel_text_residual_accum_mask = (
                        panel_text_residual_emit_followup_mask.copy()
                        if panel_text_residual_accum_mask is None
                        else np.maximum(panel_text_residual_accum_mask, panel_text_residual_emit_followup_mask)
                    )
                    decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                    pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 537: true last-chance sponsor/text completion. Several route
        # demoters can run after the previous panel-text retries, exposing one
        # more Sponsor-ringed neutral glyph fragment right before PNG encoding.
        # This keeps Auto-build output aligned with the final helper semantics
        # without broadening any classifier thresholds.
        panel_text_residual_last_chance_mask, panel_text_residual_last_chance_guard = _panel_text_residual_supplement(
            rgb, nm, sp, tm, bg
        )
        if panel_text_residual_last_chance_mask.any():
            sp = np.maximum(sp, panel_text_residual_last_chance_mask)
            panel_text_residual_last_chance_guard["phase"] = "pre_png_final_textline_completion"
            for component in panel_text_residual_last_chance_guard.get("components", []):
                component["phase"] = "pre_png_final_textline_completion"
            r["panel_text_residual_guard"] = _merge_panel_text_residual_guard(
                r.get("panel_text_residual_guard") or panel_text_residual_last_chance_guard,
                panel_text_residual_last_chance_guard,
                panel_text_residual_accum_mask,
                panel_text_residual_last_chance_mask,
                "pre_png_final_textline_completion",
            )
            panel_text_residual_accum_mask = (
                panel_text_residual_last_chance_mask.copy()
                if panel_text_residual_accum_mask is None
                else np.maximum(panel_text_residual_accum_mask, panel_text_residual_last_chance_mask)
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 542: final sponsor/text completion can reintroduce smooth,
        # textless DLM red body bars after earlier livery demoters have run.
        # Replay the same strict demoter at the true PNG boundary so live
        # Auto-build output matches the engine-side final ownership cleanup.
        smooth_red_body_panel_png_boundary_mask, smooth_red_body_panel_png_boundary_guard = _smooth_red_body_panel_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if smooth_red_body_panel_png_boundary_mask.any():
            sp[smooth_red_body_panel_png_boundary_mask > 0] = 0
            bg[smooth_red_body_panel_png_boundary_mask > 0] = 0
            smooth_red_body_panel_png_boundary_guard["phase"] = "pre_png_final_smooth_red_cleanup"
            for component in smooth_red_body_panel_png_boundary_guard.get("components", []):
                component["phase"] = "pre_png_final_smooth_red_cleanup"
            r["smooth_red_body_panel_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("smooth_red_body_panel_sponsor_guard") or smooth_red_body_panel_sponsor_guard,
                smooth_red_body_panel_png_boundary_guard,
                smooth_red_body_panel_sponsor_accum_mask,
                smooth_red_body_panel_png_boundary_mask,
                "pre_png_final_smooth_red_cleanup",
                "pre_sponsor_fragment",
            )
            smooth_red_body_panel_sponsor_accum_mask = np.maximum(
                smooth_red_body_panel_sponsor_accum_mask,
                smooth_red_body_panel_png_boundary_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 544: the true final DLM PNG boundary can still contain compact
        # contingency sponsor badges in Numbers after late sponsor/livery passes.
        # Replay the same capped logo demoter once more; this is ordering only.
        number_logo_final_png_mask, number_logo_final_png_guard = _number_logo_false_positive_to_sponsor(
            rgb, nm, sp, tm, bg
        )
        number_logo_false_positive_accum_mask = np.maximum(
            number_logo_false_positive_accum_mask,
            number_logo_final_png_mask,
        )
        if number_logo_final_png_mask.any():
            nm[number_logo_final_png_mask > 0] = 0
            sp = np.maximum(sp, number_logo_final_png_mask)
            number_logo_final_png_guard["phase"] = "pre_png_final_number_logo_cleanup"
            for component in number_logo_final_png_guard.get("components", []):
                component["phase"] = "pre_png_final_number_logo_cleanup"
            prior_number_logo_guard = r.get("number_logo_false_positive_guard") or {}
            merged_number_logo_guard = _merge_demoted_layer_guard(
                prior_number_logo_guard,
                number_logo_final_png_guard,
                None,
                number_logo_final_png_mask,
                "pre_png_final_number_logo_cleanup",
                "pre_response_partition",
            )
            for key in (
                "max_vertical_strip_demote",
                "max_large_pale_panel_demote",
                "max_large_text_billboard_demote",
                "max_large_warm_script_demote",
            ):
                if key not in merged_number_logo_guard:
                    merged_number_logo_guard[key] = prior_number_logo_guard.get(
                        key,
                        number_logo_final_png_guard.get(key),
                    )
            r["number_logo_false_positive_guard"] = merged_number_logo_guard
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 550: final PNG false-number cleanup can reintroduce compact,
        # textless orange DLM livery shapes as Sponsors. Replay the same
        # strict smooth-red demoter after that last sponsor-additive pass.
        smooth_red_body_panel_post_png_number_logo_mask, smooth_red_body_panel_post_png_number_logo_guard = _smooth_red_body_panel_sponsor_to_paint(
            rgb, sp, nm, tm, bg
        )
        if smooth_red_body_panel_post_png_number_logo_mask.any():
            sp[smooth_red_body_panel_post_png_number_logo_mask > 0] = 0
            bg[smooth_red_body_panel_post_png_number_logo_mask > 0] = 0
            smooth_red_body_panel_post_png_number_logo_guard["phase"] = "post_png_number_logo_smooth_red_cleanup"
            for component in smooth_red_body_panel_post_png_number_logo_guard.get("components", []):
                component["phase"] = "post_png_number_logo_smooth_red_cleanup"
            r["smooth_red_body_panel_sponsor_guard"] = _merge_demoted_layer_guard(
                r.get("smooth_red_body_panel_sponsor_guard") or smooth_red_body_panel_sponsor_guard,
                smooth_red_body_panel_post_png_number_logo_guard,
                smooth_red_body_panel_sponsor_accum_mask,
                smooth_red_body_panel_post_png_number_logo_mask,
                "post_png_number_logo_smooth_red_cleanup",
                "pre_sponsor_fragment",
            )
            smooth_red_body_panel_sponsor_accum_mask = np.maximum(
                smooth_red_body_panel_sponsor_accum_mask,
                smooth_red_body_panel_post_png_number_logo_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 547: GPU-hybrid replay can leave repeated orange/black DLM
        # number decals in Sponsors after the earlier supplement sequence.
        # Run one final partition check on the exact masks that are about to
        # be encoded so app-facing Auto-build matches the helper's verdict.
        final_number_shell_mask, final_number_shell_guard = _large_stylized_number_sponsor_shell_to_number(
            rgb, nm, sp, tm, bg
        )
        large_stylized_number_shell_accum_mask = np.maximum(
            large_stylized_number_shell_accum_mask,
            final_number_shell_mask,
        )
        if final_number_shell_mask.any():
            nm = np.maximum(nm, final_number_shell_mask)
            sp[final_number_shell_mask > 0] = 0
            bg[final_number_shell_mask > 0] = 0
            tm[final_number_shell_mask > 0] = 0
            final_number_shell_guard["phase"] = "final_response_partition"
            for component in final_number_shell_guard.get("components", []):
                component["phase"] = "final_response_partition"
            existing_shell_guard = r.get("large_stylized_number_shell_guard") or {}
            if existing_shell_guard.get("status") == "applied":
                existing_components = list(existing_shell_guard.get("components") or [])
                final_components = list(final_number_shell_guard.get("components") or [])
                passes = list(existing_shell_guard.get("passes") or [])
                if "final_response_partition" not in passes:
                    passes.append("final_response_partition")
                prior_px = int(existing_shell_guard.get("added_px") or 0)
                final_px = int(final_number_shell_guard.get("added_px") or int((final_number_shell_mask > 0).sum()))
                canvas_px = max(1, int(H) * int(W))
                r["large_stylized_number_shell_guard"] = {
                    **existing_shell_guard,
                    "status": "applied",
                    "component_count": len(existing_components) + len(final_components),
                    "candidate_count": (
                        int(existing_shell_guard.get("candidate_count", 0) or 0)
                        + int(final_number_shell_guard.get("candidate_count", 0) or 0)
                    ),
                    "added_px": prior_px + final_px,
                    "added_frac": round(float(prior_px + final_px) / float(canvas_px), 6),
                    "capped": bool(existing_shell_guard.get("capped")) or bool(final_number_shell_guard.get("capped")),
                    "components": (existing_components + final_components)[:8],
                    "passes": passes,
                }
            else:
                final_number_shell_guard["passes"] = ["final_response_partition"]
                r["large_stylized_number_shell_guard"] = final_number_shell_guard
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        neutral_body_watermark_template_guard = r.get("neutral_body_watermark_template_guard") or {}
        if force_gpu_supplements or neutral_body_watermark_template_guard.get("status") != "applied":
            neutral_body_watermark_template_mask, neutral_body_watermark_template_guard = (
                _neutral_body_watermark_template_to_paint(rgb, nm, sp, tm, bg)
            )
            if neutral_body_watermark_template_mask.any():
                tm[neutral_body_watermark_template_mask > 0] = 0
                neutral_body_watermark_template_guard["phase"] = "final_response_partition"
                for component in neutral_body_watermark_template_guard.get("components", []):
                    component["phase"] = "final_response_partition"
                decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
                pt = np.where(decals, np.uint8(0), np.uint8(255))
                layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                               "brand_graphics": bg, "paint": pt})
            r["neutral_body_watermark_template_guard"] = neutral_body_watermark_template_guard

        # Cycle 589: the final number-shell recovery can reintroduce tiny
        # left-edge DLM livery stripe crumbs into Numbers after the earlier
        # white-livery cleanup has already run. Replay the same constrained
        # demoter at the true response boundary before layer priority/PNG
        # emission; this is ordering-only and keeps number recovery thresholds
        # unchanged.
        white_livery_number_panel_png_boundary_mask, white_livery_number_panel_png_boundary_guard = _white_livery_number_panel_to_paint(
            rgb, nm, sp, tm, bg
        )
        if white_livery_number_panel_png_boundary_mask.any():
            nm[white_livery_number_panel_png_boundary_mask > 0] = 0
            white_livery_number_panel_png_boundary_guard["phase"] = "pre_png_final_white_livery_cleanup"
            for component in white_livery_number_panel_png_boundary_guard.get("components", []):
                component["phase"] = "pre_png_final_white_livery_cleanup"
            r["white_livery_number_panel_guard"] = _merge_demoted_layer_guard(
                r.get("white_livery_number_panel_guard"),
                white_livery_number_panel_png_boundary_guard,
                white_livery_number_panel_accum_mask,
                white_livery_number_panel_png_boundary_mask,
                "pre_png_final_white_livery_cleanup",
                "pre_number_recovery",
            )
            white_livery_number_panel_accum_mask = np.maximum(
                white_livery_number_panel_accum_mask,
                white_livery_number_panel_png_boundary_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        layer_priority_guard = _enforce_smart_tga_layer_priority(nm, sp, tm, bg)
        if layer_priority_guard.get("status") == "applied":
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})
        r["layer_priority_guard"] = layer_priority_guard

        # Cycle 595: layer-priority/export assembly can still leave smooth
        # textless DLM body plates in the final Numbers mask. Replay the same
        # strict Numbers-to-Paint guard after priority and before PNG emission
        # so Smart Sort and live layer creation see the corrected mask.
        white_livery_number_panel_post_priority_mask, white_livery_number_panel_post_priority_guard = _white_livery_number_panel_to_paint(
            rgb, nm, sp, tm, bg
        )
        if white_livery_number_panel_post_priority_mask.any():
            nm[white_livery_number_panel_post_priority_mask > 0] = 0
            white_livery_number_panel_post_priority_guard["phase"] = "post_priority_pre_png"
            for component in white_livery_number_panel_post_priority_guard.get("components", []):
                component["phase"] = "post_priority_pre_png"
            r["white_livery_number_panel_guard"] = _merge_demoted_layer_guard(
                r.get("white_livery_number_panel_guard"),
                white_livery_number_panel_post_priority_guard,
                white_livery_number_panel_accum_mask,
                white_livery_number_panel_post_priority_mask,
                "post_priority_pre_png",
                "pre_number_recovery",
            )
            white_livery_number_panel_accum_mask = np.maximum(
                white_livery_number_panel_accum_mask,
                white_livery_number_panel_post_priority_mask,
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 599: compact DLM sponsor wordmarks can be restored to Numbers
        # by the final number-shell/priority passes. Replay the same capped
        # false-number demoter at the true response boundary so live Smart Sort
        # gets the same verdict as helper-level diagnostics.
        number_logo_post_priority_mask, number_logo_post_priority_guard = _number_logo_false_positive_to_sponsor(
            rgb, nm, sp, tm, bg
        )
        number_logo_false_positive_accum_mask = np.maximum(
            number_logo_false_positive_accum_mask,
            number_logo_post_priority_mask,
        )
        if number_logo_post_priority_mask.any():
            nm[number_logo_post_priority_mask > 0] = 0
            sp = np.maximum(sp, number_logo_post_priority_mask)
            number_logo_post_priority_guard["phase"] = "post_priority_pre_png"
            for component in number_logo_post_priority_guard.get("components", []):
                component["phase"] = "post_priority_pre_png"
            r["number_logo_false_positive_guard"] = _merge_demoted_layer_guard(
                r.get("number_logo_false_positive_guard"),
                number_logo_post_priority_guard,
                None,
                number_logo_post_priority_mask,
                "post_priority_pre_png",
                "pre_response_partition",
            )
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})

        # Cycle 608: a true small race-number decal can be embedded inside a
        # whole fixed-part Template proposal (for example, a number printed over
        # a headlight). Extract only when the evidence module proves two large
        # palette anchors, an already-owned small scale variant, and a matching
        # two-color Template inlay. The surrounding fixed car part stays put.
        try:
            from engine.spec_sculpt.component_evidence import number_family_template_inlay
            number_family_template_inlay_mask, number_family_template_inlay_guard = (
                number_family_template_inlay(rgb, nm, tm)
            )
        except Exception as number_family_inlay_error:
            number_family_template_inlay_mask = np.zeros_like(nm, dtype=np.uint8)
            number_family_template_inlay_guard = {
                "status": "error",
                "reason": type(number_family_inlay_error).__name__,
                "message": str(number_family_inlay_error)[:160],
            }
        if number_family_template_inlay_mask.any():
            nm = np.maximum(nm, number_family_template_inlay_mask)
            tm[number_family_template_inlay_mask > 0] = 0
            sp[number_family_template_inlay_mask > 0] = 0
            bg[number_family_template_inlay_mask > 0] = 0
            decals = (nm > 0) | (sp > 0) | (tm > 0) | (bg > 0)
            pt = np.where(decals, np.uint8(0), np.uint8(255))
            layers.update({"numbers": nm, "sponsors": sp, "template": tm,
                           "brand_graphics": bg, "paint": pt})
        r["number_family_template_inlay_guard"] = number_family_template_inlay_guard

        # Cycle 605 architecture: the route performs additional guarded mask
        # repairs after ``separate_into_layers`` returns, so produce the public
        # shadow comparison at this literal PNG-response boundary.  The gate is
        # off/shadow only and the proposal never replaces nm/sp/tm/bg/pt.
        try:
            if route_candidate_snapshot is not None:
                from engine.spec_sculpt.candidate_evidence import (
                    capture_candidate_adapter_snapshot,
                    capture_owner_neutral_appearance_snapshot,
                    capture_mask_evidence_batch,
                    merge_candidate_snapshots,
                )
                appearance_candidate_snapshot = None
                appearance_mode = str(os.environ.get(
                    "SPB_SMART_TGA_OWNER_NEUTRAL_APPEARANCE", ""
                )).strip().lower()
                if appearance_mode in {
                    "1", "true", "yes", "on", "shadow", "seeded",
                }:
                    appearance_candidate_snapshot = capture_owner_neutral_appearance_snapshot(
                        rgb,
                        support_mask=pt,
                        support_mode="seed" if appearance_mode == "seeded" else "clip",
                    )
                route_candidate_snapshot = merge_candidate_snapshots(
                    route_candidate_snapshot,
                    appearance_candidate_snapshot,
                    capture_candidate_adapter_snapshot([{
                        "mask": hot_pink_paint_number_accum_mask,
                        "proposed_owner": "numbers",
                        "source_stage": "legacy_proposal_pre_apply",
                        "source": "legacy_guard:hot_pink_paint_number",
                        "reason": "hot_pink_paint_number",
                    }]),
                )
                route_mask_evidence.extend(capture_mask_evidence_batch([
                    {
                        "mask": panel_text_residual_accum_mask,
                        "target_owner": "sponsors",
                        "source_stage": "route_final_accumulated",
                        "source": "legacy_guard:panel_text_residual",
                        "reason": "panel_text_residual",
                    },
                    {
                        "mask": warm_livery_arc_sponsor_accum_mask,
                        "target_owner": "paint",
                        "source_stage": "route_final_accumulated",
                        "source": "legacy_guard:warm_livery_arc",
                        "reason": "warm_livery_arc_sponsor_to_paint",
                    },
                    {
                        "mask": number_trim_fragment_accum_mask,
                        "target_owner": "numbers",
                        "source_stage": "route_final_accumulated",
                        "source": "legacy_guard:number_trim_fragment",
                        "reason": "number_trim_fragment",
                    },
                    {
                        "mask": smooth_red_body_panel_sponsor_accum_mask,
                        "target_owner": "paint",
                        "source_stage": "route_final_accumulated",
                        "source": "legacy_guard:smooth_red_body_panel",
                        "reason": "smooth_red_body_panel_sponsor_to_paint",
                    },
                    {
                        "mask": white_livery_number_panel_accum_mask,
                        "target_owner": "paint",
                        "source_stage": "route_final_accumulated",
                        "source": "legacy_guard:white_livery_number_panel",
                        "reason": "white_livery_number_panel_to_paint",
                    },
                    {
                        "mask": number_logo_false_positive_accum_mask,
                        "target_owner": "sponsors",
                        "source_stage": "route_final_accumulated",
                        "source": "legacy_guard:number_logo_false_positive",
                        "reason": "number_logo_false_positive_to_sponsor",
                    },
                    {
                        "mask": large_stylized_number_shell_accum_mask,
                        "target_owner": "numbers",
                        "source_stage": "route_final_accumulated",
                        "source": "legacy_guard:large_stylized_number_shell",
                        "reason": "large_stylized_number_sponsor_shell_to_number",
                    },
                ]))
            from engine.spec_sculpt.component_evidence import run_shadow_if_enabled
            r["adjudicator_shadow"] = run_shadow_if_enabled(
                rgb,
                {"numbers": nm, "sponsors": sp, "template": tm,
                 "brand_graphics": bg, "paint": pt},
                ocr_regions=tuple(route_ocr_regions),
                candidate_snapshot=route_candidate_snapshot,
                mask_evidence=tuple(route_mask_evidence),
            )
        except Exception as adjudicator_error:  # pragma: no cover - defensive fallback
            r["adjudicator_shadow"] = {
                "status": "error",
                "mode": "shadow",
                "schema": "smart-tga-component-evidence-v1",
                "error": type(adjudicator_error).__name__,
                "message": str(adjudicator_error)[:240],
                "output_applied": False,
            }

        def _png(arr):
            b = io.BytesIO(); Image.fromarray(arr).save(b, "PNG")
            return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode('ascii')

        # overlay preview: numbers=red, sponsors=blue, template=green, brand-graphics=amber
        ov = rgb.astype(np.float32)
        ov[tm > 0] = ov[tm > 0] * 0.45 + np.array([45, 220, 90], np.float32) * 0.55
        ov[bg > 0] = ov[bg > 0] * 0.30 + np.array([255, 160, 30], np.float32) * 0.70
        ov[nm > 0] = ov[nm > 0] * 0.25 + np.array([255, 45, 45], np.float32) * 0.75
        ov[sp > 0] = ov[sp > 0] * 0.25 + np.array([55, 95, 255], np.float32) * 0.75
        ov = np.clip(ov, 0, 255).astype(np.uint8)

        return jsonify({"success": True,
                        "car": r["car"],
                        "layers": {"numbers": _png(np.stack([nm] * 3, -1)),
                                   "sponsors": _png(np.stack([sp] * 3, -1)),
                                   "template": _png(np.stack([tm] * 3, -1)),
                                   "brand_graphics": _png(np.stack([bg] * 3, -1)),
                                   "paint": _png(np.stack([pt] * 3, -1))},
                        "overlay": _png(ov),
                        "fractions": {"numbers": round(float((nm > 0).mean()), 4),
                                      "sponsors": round(float((sp > 0).mean()), 4),
                                      "template": round(float((tm > 0).mean()), 4),
                                      "brand_graphics": round(float((bg > 0).mean()), 4),
                                      "paint": round(float((pt > 0).mean()), 4)},
                        "engine": r.get("engine", "heuristic_ocr"),
                        "smart_tga": {"build": SPB_SMART_TGA_BUILD_ID,
                                      "route": "api_auto_layers",
                                      "spb_version": SPB_VERSION,
                                      "server_pid": os.getpid()},
                        "gpu_cache": _gpu_info,
                        "source": {"mode": _source_mode,
                                   "label": _source_label,
                                   "bytes": _source_bytes},
                        "template_guard": r.get("template_guard"),
                        "layer_priority_guard": r.get("layer_priority_guard"),
                        "adjudicator_shadow": r.get("adjudicator_shadow"),
                        "sponsor_fragment_guard": r.get("sponsor_fragment_guard"),
                        "isolated_wordmark_guard": r.get("isolated_wordmark_guard"),
                        "tiny_logotype_guard": r.get("tiny_logotype_guard"),
                        "micro_logotype_guard": r.get("micro_logotype_guard"),
                        "colored_micro_logo_guard": r.get("colored_micro_logo_guard"),
                        "bright_panel_micro_logo_guard": r.get("bright_panel_micro_logo_guard"),
                        "panel_text_residual_guard": r.get("panel_text_residual_guard"),
                        "stacked_front_clip_template_guard": r.get("stacked_front_clip_template_guard"),
                        "horizontal_front_clip_template_guard": r.get("horizontal_front_clip_template_guard"),
                        "paired_rear_lamp_template_guard": r.get("paired_rear_lamp_template_guard"),
                        "number_template_false_positive_guard": r.get("number_template_false_positive_guard"),
                        "template_contained_paint_trim_guard": r.get("template_contained_paint_trim_guard"),
                        "neutral_body_watermark_template_guard": r.get("neutral_body_watermark_template_guard"),
                        "faint_number_outline_guard": r.get("faint_number_outline_guard"),
                        "flat_livery_sponsor_guard": r.get("flat_livery_sponsor_guard"),
                        "warm_edge_livery_sponsor_guard": r.get("warm_edge_livery_sponsor_guard"),
                        "vertical_livery_stripe_sponsor_guard": r.get("vertical_livery_stripe_sponsor_guard"),
                        "solid_warm_livery_sponsor_guard": r.get("solid_warm_livery_sponsor_guard"),
                        "bright_warm_body_color_sponsor_guard": r.get("bright_warm_body_color_sponsor_guard"),
                        "warm_tan_body_panel_sponsor_guard": r.get("warm_tan_body_panel_sponsor_guard"),
                        "diagonal_warm_livery_slash_sponsor_guard": r.get("diagonal_warm_livery_slash_sponsor_guard"),
                        "decorative_livery_sponsor_guard": r.get("decorative_livery_sponsor_guard"),
                        "large_red_livery_sponsor_guard": r.get("large_red_livery_sponsor_guard"),
                        "smooth_red_body_panel_sponsor_guard": r.get("smooth_red_body_panel_sponsor_guard"),
                        "small_flat_red_livery_sponsor_guard": r.get("small_flat_red_livery_sponsor_guard"),
                        "red_orange_livery_block_sponsor_guard": r.get("red_orange_livery_block_sponsor_guard"),
                        "warm_livery_arc_sponsor_guard": r.get("warm_livery_arc_sponsor_guard"),
                        "geometric_livery_sponsor_guard": r.get("geometric_livery_sponsor_guard"),
                        "pale_body_panel_sponsor_guard": r.get("pale_body_panel_sponsor_guard"),
                        "ornamental_neutral_livery_sponsor_guard": r.get("ornamental_neutral_livery_sponsor_guard"),
                        "dark_body_panel_sponsor_guard": r.get("dark_body_panel_sponsor_guard"),
                        "white_livery_sponsor_guard": r.get("white_livery_sponsor_guard"),
                        "tiny_dark_sponsor_speck_guard": r.get("tiny_dark_sponsor_speck_guard"),
                        "number_logo_false_positive_guard": r.get("number_logo_false_positive_guard"),
                        "number_family_template_inlay_guard": r.get("number_family_template_inlay_guard"),
                        "multicolor_logo_false_positive_guard": r.get("multicolor_logo_false_positive_guard"),
                        "green_white_logo_false_positive_guard": r.get("green_white_logo_false_positive_guard"),
                        "large_green_logo_false_positive_guard": r.get("large_green_logo_false_positive_guard"),
                        "white_livery_number_panel_guard": r.get("white_livery_number_panel_guard"),
                        "small_sponsor_panel_false_positive_guard": r.get("small_sponsor_panel_false_positive_guard"),
                        "thin_textline_number_false_positive_guard": r.get("thin_textline_number_false_positive_guard"),
                        "red_single_digit_number_guard": r.get("red_single_digit_number_guard"),
                        "red_two_digit_number_guard": r.get("red_two_digit_number_guard"),
                        "number_trim_fragment_guard": r.get("number_trim_fragment_guard"),
                        "number_badge_graphic_guard": r.get("number_badge_graphic_guard"),
                        "round_badge_number_guard": r.get("round_badge_number_guard"),
                        "repeated_round_badge_number_guard": r.get("repeated_round_badge_number_guard"),
                        "yellow_panel_number_guard": r.get("yellow_panel_number_guard"),
                        "pale_sponsor_panel_number_guard": r.get("pale_sponsor_panel_number_guard"),
                        "hot_pink_paint_number_guard": r.get("hot_pink_paint_number_guard"),
                        "black_blue_paint_number_guard": r.get("black_blue_paint_number_guard"),
                        "white_purple_paint_number_guard": r.get("white_purple_paint_number_guard"),
                        "red_white_dark_paint_number_guard": r.get("red_white_dark_paint_number_guard"),
                        "badge_interior_guard": r.get("badge_interior_guard"),
                        "badge_number_crumb_guard": r.get("badge_number_crumb_guard"),
                        "badge_sponsor_crumb_guard": r.get("badge_sponsor_crumb_guard"),
                        "large_stylized_number_shell_guard": r.get("large_stylized_number_shell_guard"),
                        "companion_numbers": companion_info,
                        "companion_decals": companion_decal_info,
                        "brand_graphics_merge": r.get("brand_graphics_merge", _merge),
                        "size": [int(H), int(W)]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if temp_created:
            try:
                os.remove(temp_created)
            except Exception as _spb_ex:
                _spb_swallow('api_auto_layers@L11798', _spb_ex)


@app.route('/api/smart-separate/refine', methods=['POST'])
def api_smart_separate_refine():
    """SMART SEPARATE STUDIO (2026-06-26): GUIDED, refinable split of a FLAT livery into
    NUMBERS / SPONSORS / PAINT. Sibling to /api/auto-separate-livery — same overlay/mask/fraction shape,
    but driven by user HINT scribbles (which class a region is) + include/exclude brushes (force pixels
    in/out of the active layer). Re-sort + grow + refine, NOT a re-detection.

    JSON body (drawn at preview_size, in the squashed 768-square preview space):
      image           base64 PNG data URL of the source (required unless paint_file given).
      paint_file      internal-only path (X-Shokker-Internal guard), instead of image.
      preview_size    int, clamped 256..1024 (default 768).
      sensitivity     0.3..2.0;  number_size 0.4..2.5.
      active_layer    "numbers"|"sponsors"|"paint"|null — which layer the brushes act on.
      number_hint, sponsor_hint, include_mask, exclude_mask
                      base64 PNG grayscale data URLs (white = marked).
      base_masks      optional {"numbers","sponsors","paint"} base64 PNG data URLs (client echo of the
                      last result, to skip re-detection).

    Returns {success, detected, overlay, masks:{numbers,sponsors,paint}, fractions:{...}} — overlay blends
    numbers=red[255,45,45], sponsors=blue[55,95,255] over the source. On error: {success:False,error} 500."""
    import os, io, base64
    import uuid as _uuid
    temp_created = None
    try:
        from engine.spec_sculpt.core import load_paint_rgb_float01
        from engine.spec_sculpt.generate import separate_livery_layers_guided
        from PIL import Image
        import numpy as np
        import cv2

        data = request.get_json(force=True, silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "JSON body required"}), 400

        def _f(k, lo, hi, dv):
            try:
                v = data.get(k)
                return max(lo, min(hi, float(v))) if v not in (None, "") else dv
            except (TypeError, ValueError):
                return dv
        sens = _f("sensitivity", 0.3, 2.0, 1.0)
        nsz = _f("number_size", 0.4, 2.5, 1.0)
        prev = int(_f("preview_size", 256, 1024, 768))
        active_layer = data.get("active_layer")
        if active_layer not in ("numbers", "sponsors", "paint"):
            active_layer = None

        def _decode_mask(v):
            """base64 PNG data URL (or bare base64) grayscale → np.uint8 HxW, mirroring the brush-map
            route. Returns None on missing / undecodable input."""
            if not isinstance(v, str) or not v:
                return None
            try:
                payload = v.split(",", 1)[1] if "," in v else v
                im = Image.open(io.BytesIO(base64.b64decode(payload))).convert("L")
                return np.asarray(im)
            except Exception:
                return None

        # ----- load the source tex (squashed to preview_size square, like load_paint_rgb_float01) -----
        tex = None
        img_url = data.get("image")
        if isinstance(img_url, str) and img_url:
            try:
                payload = img_url.split(",", 1)[1] if "," in img_url else img_url
                im = Image.open(io.BytesIO(base64.b64decode(payload))).convert("RGB")
                im = im.resize((prev, prev), Image.LANCZOS)
                tex = np.asarray(im, dtype=np.float32) / 255.0
            except Exception as e:
                return jsonify({"success": False, "error": f"could not decode image: {e}"}), 400
        else:
            pf = str(data.get("paint_file") or "").strip()
            if not pf:
                return jsonify({"success": False, "error": "image (base64 data URL) or paint_file required"}), 400
            ok_internal, err = _require_spb_internal_request()
            if not ok_internal:
                return jsonify({"success": False, "error": "paint_file is internal-only: " + err}), 403
            paint_disk = os.path.abspath(os.path.expanduser(pf))
            if not os.path.isfile(paint_disk):
                return jsonify({"success": False, "error": f"paint_file not found: {paint_disk}"}), 404
            if paint_disk.lower().endswith(".psd"):
                return jsonify({"success": False, "error": "Smart Separate is for FLAT images (TGA/PNG/JPEG) — a PSD already has its layers."}), 400
            tex, _o, _ff = load_paint_rgb_float01(paint_disk, target_size=prev)

        number_hint = _decode_mask(data.get("number_hint"))
        sponsor_hint = _decode_mask(data.get("sponsor_hint"))
        include_mask = _decode_mask(data.get("include_mask"))
        exclude_mask = _decode_mask(data.get("exclude_mask"))

        base_masks = None
        bm = data.get("base_masks")
        if isinstance(bm, dict):
            base_masks = {}
            for k in ("numbers", "sponsors", "paint"):
                dm = _decode_mask(bm.get(k))
                if dm is not None:
                    base_masks[k] = dm
            if not base_masks:
                base_masks = None

        res = separate_livery_layers_guided(
            tex, number_hint=number_hint, sponsor_hint=sponsor_hint,
            include_mask=include_mask, exclude_mask=exclude_mask,
            active_layer=active_layer, base_masks=base_masks,
            sensitivity=sens, number_size=nsz, max_decal_frac=0.6)

        a = np.asarray(tex)
        rgb = np.clip(a[:, :, :3] * (255.0 if (a.size and a.max() <= 1.5) else 1.0), 0, 255).astype(np.uint8)

        def _png(arr):
            b = io.BytesIO(); Image.fromarray(arr).save(b, "PNG")
            return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode('ascii')

        nm, sp, pt = res["numbers"], res["sponsors"], res["paint"]
        detected = bool((nm > 0).any() or (sp > 0).any())
        ov = rgb.astype(np.float32)
        # masks may be full-res of the source; overlay is over the (square) preview rgb — align if needed
        if nm.shape != rgb.shape[:2]:
            nm = cv2.resize(nm, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)
            sp = cv2.resize(sp, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)
            pt = cv2.resize(pt, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)
        ov[nm > 0] = ov[nm > 0] * 0.25 + np.array([255, 45, 45], np.float32) * 0.75
        ov[sp > 0] = ov[sp > 0] * 0.25 + np.array([55, 95, 255], np.float32) * 0.75
        ov = np.clip(ov, 0, 255).astype(np.uint8)
        return jsonify({"success": True, "detected": detected, "overlay": _png(ov),
                        "masks": {"numbers": _png(np.stack([nm] * 3, -1)),
                                  "sponsors": _png(np.stack([sp] * 3, -1)),
                                  "paint": _png(np.stack([pt] * 3, -1))},
                        "fractions": {"numbers": round(float((nm > 0).mean()), 4),
                                      "sponsors": round(float((sp > 0).mean()), 4),
                                      "paint": round(float((pt > 0).mean()), 4)},
                        "sensitivity": sens, "number_size": nsz, "active_layer": active_layer})
    except Exception as e:
        logger.error(f"/api/smart-separate/refine failed: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if temp_created:
            try:
                os.remove(temp_created)
            except Exception as _spb_ex:
                _spb_swallow('api_smart_separate_refine@L11941', _spb_ex)


@app.route('/api/spec-sculpt/hue-map', methods=['POST'])
def api_spec_sculpt_hue_map():
    """COLOR -> MATERIAL (Spec Sculpt #7): assign a material behavior to each paint COLOR FAMILY
    ("reds -> chrome, blacks -> matte"). Body: paint_file (path) or an uploaded file; rules =
    [{"key":"red"|...|"dark"|"light","material":"chrome"|"matte"|"wet"|"satin"|"carbon"|"gloss"}];
    base = default material for unruled pixels. Returns the spec preview. Iron-safe by construction."""
    temp_created = None
    try:
        import os
        import json as _json
        import uuid as _uuid
        from engine.spec_sculpt.core import load_paint_rgb_float01
        from engine.spec_sculpt.generate import hue_material_spec, tone_material_spec, layer_material_spec, gradient_material_spec
        from engine.spec_sculpt.preview import spec_preview_png_data_urls

        ct = (request.content_type or "").lower()
        jb = request.get_json(silent=True) if ct.startswith("application/json") else None

        def gv(key, default=None):
            if jb is not None:
                v = jb.get(key)
                return default if v is None else v
            return request.form.get(key, default)

        def jparse(v):
            if v is None or v == "":
                return None
            if isinstance(v, (list, dict)):
                return v
            try:
                return _json.loads(str(v))
            except Exception:
                return None

        uploaded = request.files.get('paint_file') or request.files.get('file')
        if uploaded is not None and uploaded.filename:
            temp_created = _spb_temp_file_path(f"spec_sculpt_huemap_{_uuid.uuid4().hex}_{uploaded.filename}")
            uploaded.save(temp_created)
            paint_disk = temp_created
        else:
            pf = str(gv("paint_file") or "").strip()
            if not pf:
                return jsonify({"success": False, "error": "paint_file (path) or an uploaded file required"}), 400
            paint_disk = os.path.abspath(os.path.expanduser(pf))
            if not os.path.isfile(paint_disk):
                return jsonify({"success": False, "error": f"paint_file not found: {paint_disk}"}), 400

        size = _safe_int(gv("preview_tex_size"), 1024)
        if size not in (512, 1024, 2048):
            size = 1024
        rules = jparse(gv("rules")) or []
        tone_bands = jparse(gv("tone_bands"))
        layer_materials = jparse(gv("layer_materials"))
        gradient = jparse(gv("gradient"))
        base = str(gv("base") or "satin").strip().lower()

        tex, orig_hw, _ = load_paint_rgb_float01(paint_disk, target_size=size)
        if temp_created:
            try:
                os.remove(temp_created)
                temp_created = None
            except OSError as _spb_ex:
                _spb_swallow('api_spec_sculpt_hue_map@L12006', _spb_ex)

        spec_u8 = None
        if layer_materials:
            _psd_src = str(gv("psd_path") or "").strip()
            if not _psd_src and paint_disk.lower().endswith('.psd'):
                _psd_src = paint_disk
            if _psd_src:
                spec_u8 = layer_material_spec(_psd_src, layer_materials, base=base, max_size=size)
        if spec_u8 is None and isinstance(gradient, dict) and gradient.get("a") and gradient.get("b"):
            spec_u8 = gradient_material_spec(gradient.get("a"), gradient.get("b"),
                                             direction=gradient.get("direction", "horizontal"), out_size=size)
        if spec_u8 is None:
            spec_u8 = tone_material_spec(tex, tone_bands, base=base) if tone_bands else hue_material_spec(tex, rules, base=base)
        previews = spec_preview_png_data_urls(spec_u8)
        return jsonify({"success": True, "previews": previews, "size": size})
    except Exception as e:
        logger.error(f"/api/spec-sculpt/hue-map failed: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        try:
            import os as _os
            if temp_created and _os.path.exists(temp_created):
                _os.remove(temp_created)
        except Exception as _spb_ex:
            _spb_swallow('api_spec_sculpt_hue_map@L12031', _spb_ex)


@app.route('/api/spec-sculpt/brush-map', methods=['POST'])
def api_spec_sculpt_brush_map():
    """REGION BRUSH (Spec Sculpt #13): stamp hand-painted material masks onto a spec. JSON body:
    strokes = [{material, mask_b64 (data:image/png)}], size (512/1024/2048), base. Returns spec preview."""
    try:
        import io as _io
        import base64 as _b64
        import numpy as np
        from PIL import Image as _PImg
        from engine.spec_sculpt.generate import brush_material_spec
        from engine.spec_sculpt.preview import spec_preview_png_data_urls

        data = request.get_json(force=True, silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "JSON body required"}), 400
        size = _safe_int(data.get("size"), 1024)
        if size not in (512, 1024, 2048):
            size = 1024
        base = str(data.get("base") or "satin").strip().lower()
        strokes = []
        for s in (data.get("strokes") or []):
            mat = (s or {}).get("material")
            mb = (s or {}).get("mask_b64") or ""
            if not mat or not isinstance(mb, str) or "," not in mb:
                continue
            try:
                im = _PImg.open(_io.BytesIO(_b64.b64decode(mb.split(",", 1)[1]))).convert("L")
                strokes.append({"material": mat, "mask": np.asarray(im)})
            except Exception as _spb_ex:
                _spb_swallow('api_spec_sculpt_brush_map@L12063', _spb_ex); continue
        if not strokes:
            return jsonify({"success": False, "error": "no painted strokes provided"}), 400
        spec = brush_material_spec(strokes, base=base, out_size=size)
        return jsonify({"success": True, "previews": spec_preview_png_data_urls(spec), "size": size})
    except Exception as e:
        logger.error(f"/api/spec-sculpt/brush-map failed: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/spec-sculpt/audit', methods=['GET'])
def api_spec_sculpt_audit_get():
    """Return the saved Spec Sculpt preset-audit verdicts so the page can preload."""
    try:
        entries = _load_spec_sculpt_audit()
        return jsonify({"ok": True, "entries": entries, "total": len(entries),
                        "counts": _audit_counts(entries)})
    except Exception as e:
        logger.error(f"/api/spec-sculpt/audit GET failed: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/spec-sculpt/audit', methods=['POST'])
def api_spec_sculpt_audit_post():
    """Merge posted preset-audit verdicts into _audit/spec_sculpt_audit.json (+ history).

    Body: ``{"entries": {pid: {verdict, rating, reasons[], name, notes, ts}}}``.
    Merge keeps the newer ``ts`` per preset so concurrent tabs don't clobber.
    """
    try:
        denial = _external_write_denial(SPEC_SCULPT_AUDIT_DIR, "spec-sculpt-audit-save")
        if denial:
            return jsonify(denial), 403
        data = request.get_json(silent=True) or {}
        incoming = data.get("entries")
        if not isinstance(incoming, dict):
            return jsonify({"ok": False, "error": "body needs an 'entries' object"}), 400

        os.makedirs(SPEC_SCULPT_AUDIT_DIR, exist_ok=True)
        merged = _load_spec_sculpt_audit()
        changed = 0
        for pid, raw in incoming.items():
            if not isinstance(raw, dict):
                continue
            verdict = raw.get("verdict")
            if verdict is not None and verdict not in _VALID_AUDIT_VERDICTS:
                verdict = None
            clean = {
                "verdict": verdict,
                "rating": _safe_int(raw.get("rating"), 0) or None,
                "reasons": [str(r)[:40] for r in raw.get("reasons", []) if r][:20],
                "name": str(raw.get("name") or "")[:120],
                "notes": str(raw.get("notes") or "")[:2000],
                "ts": _safe_int(raw.get("ts"), 0),
            }
            prev = merged.get(pid)
            if prev and int(prev.get("ts", 0)) > int(clean["ts"] or 0):
                continue  # keep the newer existing entry
            merged[pid] = clean
            changed += 1

        # [2026-09-05 codebase-health S3] atomic write (temp + os.replace)
        from engine.atomic_io import atomic_write_json
        atomic_write_json(SPEC_SCULPT_AUDIT_JSON, {"entries": merged, "updated": int(time.time())}, indent=2)
        try:
            with open(SPEC_SCULPT_AUDIT_HISTORY, 'a', encoding='utf-8') as hf:
                hf.write(json.dumps({"ts": int(time.time()), "changed": changed,
                                     "total": len(merged)}) + "\n")
        except OSError as _spb_ex:
            _spb_swallow('api_spec_sculpt_audit_post@L12132', _spb_ex)

        return jsonify({"ok": True, "total": len(merged), "changed": changed,
                        "counts": _audit_counts(merged)})
    except Exception as e:
        logger.error(f"/api/spec-sculpt/audit POST failed: {e}\n{traceback.format_exc()}")
        return jsonify({"ok": False, "error": str(e)}), 500


def _easy_catalog_description(value):
    """Turn registry audit prose into short customer-facing material copy."""
    text = str(value or "").strip()
    if not text:
        return ""
    # Renderer registries intentionally carry audit breadcrumbs. They are useful
    # to developers, but Easy users should never see ticket IDs or raw M/R/CC
    # assignments while deciding whether a finish feels satin, candy, or metal.
    marker = r"(?:(?:BASE|WEAK|GGX|FLAG|SPB|HA|TICK|CYCLE|HARDMODE|MATL|LAZY|WARN)(?:(?:[-_][A-Z0-9]+)|\d+)+|M7(?:[-_][A-Z0-9]+)*)"
    text = re.sub(rf"\s*\([^)]*\b{marker}\b[^)]*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(rf"\s*(?:[—–-]\s*)?{marker}\b.*$", "", text, flags=re.IGNORECASE)
    audit_word = r"(?:owner|rebuild|rated|doctored|proof|flat[- ]?fix|cc\s+fixed|paint_fn|spec_fn|verdict|audit|score)"
    text = re.sub(rf"\s*\([^)]*\b{audit_word}\b[^)]*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+from\s+(?:paint_fn|spec_fn)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(
        rf"\s*(?:[.—–-]\s*)?(?:v\d+\s+)?\b(?:owner|rebuild|flat[- ]?fix|cc\s+fixed|verdict|audit)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:CC|MR|M|R)\s*=\s*[-+]?\d+(?:\s*(?:→|->)\s*[-+]?\d+)?\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bM\s*/\s*R\s*/\s*CC\b", "finish", text, flags=re.IGNORECASE)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"(?:\s*[,;:]\s*){2,}", ", ", text)
    text = re.sub(r"\s*[—–-]\s*$", "", text)
    return re.sub(r"\s+", " ", text).strip(" ,;:-—–")[:180]


_EASY_CATALOG_PREFIXES = {
    "flm": "Fractured Flames",
    "grad": "Gradient",
    "cs": "Color Science",
    "cx": "COLORSHOXX",
    "ff": "Fractured Forge",
    "vm": "Viva Mexico",
    "fm": "Fractured Minds",
    "rs": "Rising Sun",
    "ms": "Mortal Shokk",
    "msh": "MONEY SHOKK",
    "msha": "MONEY SHOKK",
    "mshc": "MONEY SHOKK",
    "mshx": "MONEY SHOKK",
    "pf": "Prism Forge",
    "gf": "Grunge & Fun",
    "uj": "Union Jacked",
    "cc": "Color Clash",
    "f": "Foundation",
    "fs": "Fractured Souls",
    "cf": "Chromatic Flake",
    "enh": "Enhanced",
    "pp": "Pattern Plate",
    "fc": "Fractured Cryptid",
    "efx": "Effects",
    "fr": "Fractured Rainbow",
    "fo": "Fractured Occult",
    "fu": "Fractured UFO",
    "mc": "Multi-Color",
    "lfr": "Let Freedom Ring",
    "p": "PARADIGM",
    "grd": "Gradient",
    "aniso": "Anisotropic",
    "anime2": "Anime",
    "materials2": "Materials & Physics",
    "optics2": "Light & Optics",
    "neon2": "Neon Underground",
    "prizm": "PRIZM",
    "dualshift": "Dual Shift",
    "microshift": "Micro Shift",
    "multiscale": "Multi-Scale",
    "trizone": "Tri-Zone",
    "twoface": "Two-Face",
}

_EASY_FRACTURED_DEEP_IDS = {
    "fd_anglerfish", "fd_jellyfall", "fd_hadal_glow", "fd_bioluminescence",
    "fd_ripple_glass", "fd_hydrothermal", "fd_maelstrom", "fd_kelp_drift",
    "fd_cephalopod", "fd_nacre", "fd_sonar_glass", "fd_brine_glass",
    "fd_krakenink", "fd_whalefall", "fd_abyssalsnow", "fd_eeldischarge",
    "fd_pressurestrata", "fd_siphonophore", "fd_glasssquid", "fd_trenchfault",
}

_EASY_CATALOG_EXACT_NAMES = {
    # Preserve the authored, demo-worthy PARADIGM concepts; the terse p_ IDs
    # were implementation aliases, not product names.
    "p_superfluid": "PARADIGM Absolute Zero Superfluid",
    "p_coronal": "PARADIGM Coronal Mass Ejection",
    "p_seismic": "PARADIGM Seismic Faultline",
    "p_hypercane": "PARADIGM Category 5 Hypercane",
    "p_geomagnetic": "PARADIGM Geomagnetic Storm",
    "p_non_euclidean": "PARADIGM Non-Euclidean Hypercube",
    "p_time_reversed": "PARADIGM Time-Reversed Entropy",
    "p_programmable": "PARADIGM Programmable Utility Fog",
    "p_erised": "PARADIGM Negative Normal Mirror",
    "p_schrodinger": "PARADIGM Schrodinger's Dust",
    "p_mercury": "PARADIGM Mercury",
    "p_phantom": "PARADIGM Phantom",
    "p_volcanic": "PARADIGM Volcanic",
    "p_aurora": "PARADIGM Aurora",
    "p_static": "PARADIGM Static",
    # Rework packs also carry much stronger authored display names than their
    # short registry aliases. Easy is the two-minute demo; keep those concepts.
    "grd_oklab_flow": "Gradient OKLab Flow",
    "grd_iridescent": "Gradient Iridescent",
    "grd_ridged_contour": "Gradient Ridged Contour",
    "grd_mesh_bleed": "Gradient Mesh Bleed",
    "grd_duotone_grain": "Gradient Duotone Grain",
    "grd_chromatic_aberration": "Gradient Chromatic Aberration",
    "grd_spectral_sweep": "Gradient Spectral Sweep",
    "grd_liquid_marble": "Gradient Liquid Marble",
    "grd_moire_interference": "Gradient Moire Interference",
    "grd_holo_foil": "Gradient Holo Foil",
    "grd_radial_burst": "Gradient Radial Burst",
    # SPB-105 NU-V4-LIVE-1 — preserve the authored v4 product names in Easy.
    "neon_blacklight": "Neon Underground Blacklight Garage",
    "neon_cyber_yellow": "Neon Underground Tunnel Vision",
    "neon_dual_glow": "Neon Underground Split Underglow",
    "neon_electric_blue": "Neon Underground Neon Underglow",
    "neon_ice_white": "Neon Underground Nitro Purge",
    "neon_orange_hazard": "Neon Underground Burnout Ember",
    "neon_pink_blaze": "Neon Underground Import Royalty",
    "neon_rainbow_tube": "Neon Underground Afterburn Chrome",
    "neon_red_alert": "Neon Underground Redline Rush",
    "neon_toxic_green": "Neon Underground Toxic Overdrive",
    "neon2_sign_tubes": "Neon Underground Signglass Shatter",
    "neon2_circuit_city": "Neon Underground Seoul Circuit",
    "neon2_laser_web": "Neon Underground Laser Lane",
    "neon2_rain": "Neon Underground Tokyo Rain",
    "neon2_splatter": "Neon Underground Midnight Drift",
    "neon2_wireframe": "Neon Underground Grid Runner",
    "neon2_plasma_tubes": "Neon Underground Boost Spool",
    "neon2_honeycomb": "Neon Underground Carbon Voltage",
    "neon2_flow_tubes": "Neon Underground Street Pulse",
    "neon2_synthwave_sun": "Neon Underground Arcade Afterhours",
    "neon2_quarter_mile_weave": "Neon Underground Quarter Mile",
    "neon2_torque_scar": "Neon Underground Wet Apex",
    "neon2_phantom_mica": "Neon Underground Phantom Taillights",
    "neon2_emberwake_delam": "Neon Underground Turbo Heat",
    "neon2_frequency_fault": "Neon Underground Midnight Candy",
    "anime2_cel_shade": "Anime Cel Shade",
    "anime2_screentone": "Anime Manga Screentone",
    "anime2_sakura": "Anime Sakura Storm",
    "anime2_mecha": "Anime Mecha Panels",
    # These four coexist with older, separately authored Anime materials. Keep
    # their visible names distinct so Easy Mode never presents two different
    # engines as the same customer choice.
    "anime2_speed_lines": "Anime Speed Lines: Action Burst",
    "anime2_energy_aura": "Anime Energy Aura: Ki Charge",
    "anime2_crystal": "Anime Crystal Facet: Jewel Shards",
    "anime2_gradient_hair": "Anime Gradient Hair: Gloss Strands",
    "optics2_dvd": "Light & Optics Diffraction Spiral",
    "optics2_thinfilm": "Light & Optics Thin-Film Oil Slick",
    "optics2_caustics": "Light & Optics Refractive Caustics",
    "optics2_newton": "Light & Optics Newton's Rings",
    "optics2_prism": "Light & Optics Prism Dispersion",
    "optics2_moire": "Light & Optics Moire Interference",
    "optics2_aurora": "Light & Optics Aurora Veil",
    "optics2_bubbles": "Light & Optics Soap-Bubble Froth",
    "optics2_fiber": "Light & Optics Fiber-Optic Bundle",
    "optics2_holo": "Light & Optics Holographic Foil",
    "optics2_lenticular": "Light & Optics Lenticular Flip",
    "materials2_carbon": "Materials & Physics Carbon Twill Weave",
    "materials2_forged": "Materials & Physics Forged Carbon",
    "materials2_engine": "Materials & Physics Engine-Turned Metal",
    "materials2_liquid": "Materials & Physics Liquid Metal",
    "materials2_crystal": "Materials & Physics Crystal Lattice",
    "materials2_ferro": "Materials & Physics Ferrofluid Spikes",
    "materials2_fracture": "Materials & Physics Fracture Net",
    "materials2_damascus": "Materials & Physics Damascus Steel",
    "materials2_kevlar": "Materials & Physics Kevlar Aramid Weave",
    "materials2_titanium": "Materials & Physics Anodized Titanium",
    "materials2_meteorite": "Materials & Physics Meteorite Widmanstatten",
    # Imported SHOKK Drop assets historically kept upload filenames as IDs.
    # Easy Mode names the visual instead of exposing a generator/date/hash.
    "ui_bjeans1": "SHOKK Drop Blue Jeans",
    "ui_black_rainbow_holo_x2": "SHOKK Drop Black Rainbow Holo X2",
    "ui_chatgpt_image_jun_16_2026_03_01_34_pm": "SHOKK Drop Custom Artwork",
    "ui_groovy_waves": "SHOKK Drop Groovy Waves",
    "ui_jeans_light_weathered": "SHOKK Drop Light Weathered Denim",
    "ui_jeans_light_weathered_2": "SHOKK Drop Light Weathered Denim II",
    "ui_jeans_light_weathered_3": "SHOKK Drop Light Weathered Denim III",
    "ui_krak": "SHOKK Drop Kraken",
    "ui_mag01": "SHOKK Drop Custom Artwork II",
    "ui_stw_3c4c676f_02": "SHOKK Drop Voronoi Beach · Jelly Iridescent",
    # The first Fractured Deep pack predates the underscore naming convention.
    "fd_jellyfall": "Fractured Deep Jelly Fall",
    "fd_krakenink": "Fractured Deep Kraken Ink",
    "fd_whalefall": "Fractured Deep Whale Fall",
    "fd_abyssalsnow": "Fractured Deep Abyssal Snow",
    "fd_eeldischarge": "Fractured Deep Eel Discharge",
    "fd_pressurestrata": "Fractured Deep Pressure Strata",
    "fd_glasssquid": "Fractured Deep Glass Squid",
    "fd_trenchfault": "Fractured Deep Trench Fault",
}


def _easy_catalog_name(key, asset_ordinal=None):
    """Expand internal family abbreviations without changing look identity."""
    raw = str(key or "")
    exact = _EASY_CATALOG_EXACT_NAMES.get(raw.lower())
    if exact:
        return exact
    prefix, separator, remainder = raw.partition("_")
    if prefix.lower() == "gf":
        lower = remainder.lower()
        if "yellow_hexagon_halftone" in lower:
            return "Grunge & Fun Yellow Hexagon Halftone"
        if "blue_hexagon_pattern" in lower:
            return "Grunge & Fun Blue Hexagon Pattern"
        if lower.startswith("magnific_digital_illustration"):
            return "Grunge & Fun Dark Illustration"
        return f"Grunge & Fun Artwork {int(asset_ordinal or 0):02d}"
    if prefix.lower() == "fd":
        # Two independently-authored packs historically share fd_. Keep the
        # registry ID untouched, but give each customer its real family name.
        family = "Fractured Deep" if raw.lower() in _EASY_FRACTURED_DEEP_IDS else "Forbidden Dragon"
    else:
        family = _EASY_CATALOG_PREFIXES.get(prefix.lower())
    if family and separator and remainder:
        name = f"{family} {id_to_display_name(remainder)}"
    else:
        name = id_to_display_name(raw)
    for short, readable in {
        "Od": "OD",
        "Pvd": "PVD",
        "Rgb": "RGB",
        "Uv": "UV",
        "Hsv": "HSV",
        "Vis": "Visible",
    }.items():
        name = re.sub(rf"\b{short}\b", readable, name)
    return name


@app.route('/api/spec-sculpt/catalog-index', methods=['GET'])
def api_spec_sculpt_catalog_index():
    """Lightweight bases + monolithic ID lists for Spec Sculpt (no pattern overlays)."""
    try:
        # Expansion packs are intentionally lazy for fast server startup, but a
        # catalog endpoint must never publish the pre-expansion registry as the
        # complete Easy library. Without this warm-up the first page could lock
        # in ~234 missing looks until a reload after some unrelated render.
        # A fresh process begins with only the fast-start registry. Warm and merge
        # every shipping expansion before calling this response complete. The
        # same helper is used by catalog validation, so every listed card is also
        # guaranteed to survive normalize_catalog_stack() when selected.
        from engine.spec_sculpt.catalog_blend import ensure_full_catalog_registries

        BASE_REGISTRY, MONOLITHIC_REGISTRY = ensure_full_catalog_registries()

        gf_keys = sorted(
            key for key in list(BASE_REGISTRY.keys()) + list(MONOLITHIC_REGISTRY.keys())
            if str(key).lower().startswith("gf_")
        )
        gf_ordinals = {key: index + 1 for index, key in enumerate(dict.fromkeys(gf_keys))}

        def _catalog_row(key, value):
            description = ""
            if isinstance(value, dict):
                description = _easy_catalog_description(value.get("desc") or value.get("description") or "")
            return {"id": key, "name": _easy_catalog_name(key, gf_ordinals.get(key)), "description": description}

        bases = [_catalog_row(k, BASE_REGISTRY[k]) for k in sorted(BASE_REGISTRY.keys())]
        specials = [_catalog_row(k, MONOLITHIC_REGISTRY[k]) for k in sorted(MONOLITHIC_REGISTRY.keys())]
        # Never repeat the original race by asserting completeness from intent.
        # These are the current beta's shipping floors; additions are welcome,
        # but a missing pack keeps the client in its retryable loading state
        # instead of displaying "Nothing removed" over a partial library.
        catalog_complete = len(bases) >= 695 and len(specials) >= 1759
        return jsonify({
            "success": True,
            "complete": catalog_complete,
            "counts": {"bases": len(bases), "specials": len(specials)},
            "warning": "Catalog expansion is incomplete; retrying will preserve the paint." if not catalog_complete else "",
            "bases": bases,
            "specials": specials,
        })
    except Exception as e:
        logger.error(f"/api/spec-sculpt/catalog-index failed: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


# --- SHOKK TRACE / AUTO PAINTER (SPB-AUTOPAINT-001, 2026-05-29) ------------
# Step 1 of the Auto Painter pipeline: auto-segment a blank iRacing template
# into named-able zone regions (connected-components on UV islands). The
# auto-painter.html tool can run this client-side too; this route gives full-
# resolution segmentation and the shared zone-map format.
def _shokk_trace_inputs():
    """Resolve (image_arg, source_name, params) from multipart OR JSON request."""
    ct = (request.content_type or "").lower()
    if ct.startswith("application/json"):
        data = request.get_json(silent=True) or {}
        pf = (data.get("template_file") or data.get("paint_file") or "").strip()
        if not pf:
            return None, None, None, "JSON requires template_file"
        path = os.path.abspath(os.path.expanduser(pf))
        if not os.path.isfile(path):
            return None, None, None, f"template_file not found: {path}"
        return path, os.path.basename(path), data, None
    f = request.files.get('file') or request.files.get('template')
    if not f or not f.filename:
        return None, None, None, "No file; use multipart field 'file' or 'template'."
    return f.read(), f.filename, request.form, None


def _shokk_trace_param(params, key, default):
    try:
        v = params.get(key)
        return float(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


@app.route('/api/shokk-trace/segment', methods=['POST'])
def api_shokk_trace_segment():
    """Template -> zone-map JSON (regions w/ bbox, mask, suggested name, mirror).

    Multipart field ``file``/``template``, or JSON ``{"template_file": "/abs.png",
    "bg_tolerance": 34, "close_radius": 2, "overlay": true, "major_only": true}``.
    """
    try:
        from engine.paint_v2 import shokk_trace as _st
        img_arg, src, params, err = _shokk_trace_inputs()
        if err:
            return jsonify({"success": False, "error": err}), 400
        zm = _st.segment_template(
            img_arg,
            bg_tolerance=_shokk_trace_param(params, "bg_tolerance", 34.0),
            close_radius=int(_shokk_trace_param(params, "close_radius", 2)),
            min_area_frac=_shokk_trace_param(params, "min_area_frac", 0.0006),
            major_area_frac=_shokk_trace_param(params, "major_area_frac", 0.01),
            source_name=src,
        )
        if str(params.get("ocr_names", "")).lower() in ("1", "true", "yes"):
            _st.name_zones_from_labels(zm, img_arg)   # PRECISION UNLOCK: name from baked-in labels
        if str(params.get("overlay", "")).lower() in ("1", "true", "yes"):
            zm["overlay_data_url"] = _st.overlay_data_url(
                img_arg, zm,
                major_only=str(params.get("major_only", "")).lower() in ("1", "true", "yes"))
        return jsonify({"success": True, "zone_map": zm})
    except Exception as e:
        logger.error(f"/api/shokk-trace/segment error: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/shokk-trace/preview', methods=['POST'])
def api_shokk_trace_preview():
    """Same inputs as /segment; returns a labelled overlay PNG as a data URL."""
    try:
        from engine.paint_v2 import shokk_trace as _st
        img_arg, src, params, err = _shokk_trace_inputs()
        if err:
            return jsonify({"success": False, "error": err}), 400
        zm = _st.segment_template(
            img_arg,
            bg_tolerance=_shokk_trace_param(params, "bg_tolerance", 34.0),
            close_radius=int(_shokk_trace_param(params, "close_radius", 2)),
            min_area_frac=_shokk_trace_param(params, "min_area_frac", 0.0006),
            source_name=src,
        )
        durl = _st.overlay_data_url(
            img_arg, zm,
            major_only=str(params.get("major_only", "")).lower() in ("1", "true", "yes"))
        return jsonify({"success": True, "preview_data_url": durl,
                        "region_count": zm["region_count"], "major_count": zm["major_count"]})
    except Exception as e:
        logger.error(f"/api/shokk-trace/preview error: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/shokk-trace/build', methods=['POST'])
def api_shokk_trace_build():
    """Whole v1 chain: template + design images -> paint+spec+overlay data URLs.

    Multipart: ``template`` (file) + ``design`` (file). Optional ``names`` (JSON
    map {region_id: name}) + tuning (bg_tolerance, close_radius, min_area_frac).
    """
    try:
        from engine.paint_v2 import shokk_trace as _st
        tf = request.files.get('template')
        df = request.files.get('design')
        if not tf or not tf.filename:
            return jsonify({"success": False, "error": "Missing 'template' file"}), 400
        if not df or not df.filename:
            return jsonify({"success": False, "error": "Missing 'design' file"}), 400
        names = None
        raw_names = request.form.get('names')
        if raw_names:
            try:
                names = json.loads(raw_names)
            except Exception:
                names = None
        res = _st.build_from_images(
            tf.read(), df.read(), names=names, design_name=df.filename,
            want_decals=str(request.form.get("decals", "")).lower() in ("1", "true", "yes"),
            ocr_names=str(request.form.get("ocr_names", "")).lower() in ("1", "true", "yes"),
            bg_tolerance=_shokk_trace_param(request.form, "bg_tolerance", 34.0),
            close_radius=int(_shokk_trace_param(request.form, "close_radius", 2)),
            min_area_frac=_shokk_trace_param(request.form, "min_area_frac", 0.0006),
            major_area_frac=_shokk_trace_param(request.form, "major_area_frac", 0.01),
        )
        return jsonify({"success": True, **res})
    except Exception as e:
        logger.error(f"/api/shokk-trace/build error: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/shokk-trace/build-separators', methods=['POST'])
def api_shokk_trace_build_separators():
    """Real CONNECTED-template chain: gridlines asset + design + seeds -> the same
    bundle as /build (paint+spec+overlay data URLs + region_masks RLE + decals).

    Real iRacing zones are one connected blue mass, so /build's connected-
    components merges them. This path cuts the blue along the DRAWN green separator
    lines and names each panel by the seed inside it. Multipart: ``grid`` (the
    'Zones and Gridlines' image) + ``design`` (file) + ``seeds`` (JSON: a list of
    {name,nx,ny}, or a seed-ref object {"seeds":[...]}). Optional ``names`` (JSON
    {id_or_name: name}), ``decals`` (bool), tuning ``min_cell_frac``/``green_dilate``.
    Seeds are a per-car reference authored once (PSD/OCR/by hand), reused per class.
    """
    try:
        from engine.paint_v2 import shokk_trace as _st
        gf = request.files.get('grid') or request.files.get('template')
        df = request.files.get('design')
        if not gf or not gf.filename:
            return jsonify({"success": False, "error": "Missing 'grid' file"}), 400
        if not df or not df.filename:
            return jsonify({"success": False, "error": "Missing 'design' file"}), 400
        raw_seeds = request.form.get('seeds')
        if not raw_seeds:
            return jsonify({"success": False, "error": "Missing 'seeds' (JSON list of {name,nx,ny})"}), 400
        try:
            sj = json.loads(raw_seeds)
        except Exception:
            return jsonify({"success": False, "error": "'seeds' is not valid JSON"}), 400
        seed_list = sj.get("seeds") if isinstance(sj, dict) else sj
        try:
            seeds = [(s["name"], float(s["nx"]), float(s["ny"])) for s in seed_list]
        except Exception:
            return jsonify({"success": False, "error": "each seed needs name/nx/ny"}), 400
        if not seeds:
            return jsonify({"success": False, "error": "'seeds' is empty"}), 400
        names = None
        raw_names = request.form.get('names')
        if raw_names:
            try:
                names = json.loads(raw_names)
            except Exception:
                names = None
        res = _st.build_from_separators(
            gf.read(), df.read(), seeds, names=names, design_name=df.filename,
            want_decals=str(request.form.get("decals", "")).lower() in ("1", "true", "yes"),
            min_cell_frac=_shokk_trace_param(request.form, "min_cell_frac", 0.0008),
            green_dilate=int(_shokk_trace_param(request.form, "green_dilate", 3)),
        )
        return jsonify({"success": True, **res})
    except Exception as e:
        logger.error(f"/api/shokk-trace/build-separators error: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/shokk-trace/segment-separators', methods=['POST'])
def api_shokk_trace_segment_separators():
    """Real CONNECTED template -> editable zones, NO design needed. Multipart:
    ``grid`` (the 'Zones and Gridlines' image) + ``seeds`` (JSON list of
    {name,nx,ny}, or a seed-ref object). Returns a Send-ready bundle (region_masks
    RLE + a default per-zone colour/spec + overlay) so a painter can drop a real
    template and get their panels straight into Paint Booth to paint themselves.
    """
    try:
        from engine.paint_v2 import shokk_trace as _st
        gf = request.files.get('grid') or request.files.get('template')
        if not gf or not gf.filename:
            return jsonify({"success": False, "error": "Missing 'grid' file"}), 400
        raw_seeds = request.form.get('seeds')
        if not raw_seeds:
            return jsonify({"success": False, "error": "Missing 'seeds' (JSON list of {name,nx,ny})"}), 400
        try:
            sj = json.loads(raw_seeds)
        except Exception:
            return jsonify({"success": False, "error": "'seeds' is not valid JSON"}), 400
        seed_list = sj.get("seeds") if isinstance(sj, dict) else sj
        try:
            seeds = [(s["name"], float(s["nx"]), float(s["ny"])) for s in seed_list]
        except Exception:
            return jsonify({"success": False, "error": "each seed needs name/nx/ny"}), 400
        if not seeds:
            return jsonify({"success": False, "error": "'seeds' is empty"}), 400
        res = _st.zones_from_separators(
            gf.read(), seeds,
            min_cell_frac=_shokk_trace_param(request.form, "min_cell_frac", 0.0008),
            green_dilate=int(_shokk_trace_param(request.form, "green_dilate", 3)),
        )
        return jsonify({"success": True, **res})
    except Exception as e:
        logger.error(f"/api/shokk-trace/segment-separators error: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/shokk-trace/seeds-from-labels', methods=['POST'])
def api_shokk_trace_seeds_from_labels():
    """OCR a car's LABELED template guide -> a per-car seed reference (the
    'self-driving' authoring path so a new car needs no PSD/hand-authoring).
    Multipart ``labeled`` (or ``file``) image. Returns {seeds:[{name,nx,ny}],
    report:{found, missing, seed_count, note}}. 503 if OCR isn't installed.
    """
    try:
        from engine.paint_v2 import shokk_trace as _st
        lf = request.files.get('labeled') or request.files.get('file') or request.files.get('grid')
        if not lf or not lf.filename:
            return jsonify({"success": False, "error": "Missing 'labeled' file"}), 400
        seeds, report = _st.seeds_from_labels(lf.read())
        if not report.get("available"):
            return jsonify({"success": False, "error": report.get("note", "OCR unavailable")}), 503
        return jsonify({"success": True,
                        "seeds": [{"name": n, "nx": x, "ny": y} for n, x, y in seeds],
                        "report": report})
    except Exception as e:
        logger.error(f"/api/shokk-trace/seeds-from-labels error: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/spec-sculpt/analyze', methods=['POST'])
def api_spec_sculpt_analyze():
    """Inspect paint dimensions: multipart upload OR JSON ``{\"paint_file\": \"...\"}``."""
    temp_uploaded_path = None
    try:
        ct = (request.content_type or "").lower()
        from PIL import Image as PILImage

        if ct.startswith("application/json"):
            data = request.get_json(silent=True) or {}
            pf = (data.get("paint_file") or "").strip()
            if not pf:
                return jsonify({"success": False, "error": "JSON requires paint_file"}), 400
            path = os.path.abspath(os.path.expanduser(pf))
            if not os.path.isfile(path):
                return jsonify({"success": False, "error": f"paint_file not found: {path}"}), 400
            with PILImage.open(path) as img:
                w, h = img.size
                preview = _spec_sculpt_paint_preview_data_url(img)
            source_token = _remember_spec_sculpt_source(path)
            return jsonify({
                "success": True,
                "filename": os.path.basename(path),
                "path": path.replace("\\", "/"),
                "source_token": source_token,
                "original_resolution": [w, h],
                "target_resolution": [2048, 2048],
                "is_exact_2048": bool(w == 2048 and h == 2048),
                "easy_eligible": bool(w == 2048 and h == 2048),
                "preview_data_url": preview,
                "note": "POST /api/spec-sculpt/generate resizes non-2048 sources to 2048 unless strict2048 is true.",
            })

        if 'file' not in request.files and 'paint_file' not in request.files:
            return jsonify({"success": False, "error": "No file; use multipart field 'file' or 'paint_file'."}), 400
        f = request.files.get('file') or request.files.get('paint_file')
        if not f or not f.filename:
            return jsonify({"success": False, "error": "Empty upload"}), 400
        upload_name = os.path.basename(str(f.filename).replace("\\", "/")) or "paint"
        path = _spb_temp_file_path(f"spec_sculpt_analyze_{uuid.uuid4().hex}_{upload_name}")
        temp_uploaded_path = path
        f.save(path)
        with PILImage.open(path) as img:
            w, h = img.size
            preview = _spec_sculpt_paint_preview_data_url(img)
        return jsonify({
            "success": True,
            "filename": upload_name,
            "original_resolution": [w, h],
            "target_resolution": [2048, 2048],
            "is_exact_2048": bool(w == 2048 and h == 2048),
            "easy_eligible": bool(w == 2048 and h == 2048),
            "preview_data_url": preview,
            "note": "POST /api/spec-sculpt/generate resizes non-2048 sources to 2048 unless strict2048 is true.",
        })
    except Exception as e:
        logger.error(f"/api/spec-sculpt/analyze error: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if temp_uploaded_path:
            try:
                os.remove(temp_uploaded_path)
            except OSError as _spb_ex:
                _spb_swallow('api_spec_sculpt_analyze@L12731', _spb_ex)


@app.route('/api/spec-sculpt/sample-source-color', methods=['POST'])
def api_spec_sculpt_sample_source_color():
    """Return a source-true RGB sample from an exact 2048 iRacing paint.

    JSON accepts ``source_token`` (preferred for a path analyzed earlier) or an
    internal, allow-listed ``paint_file`` path plus normalized ``x``/``y``.
    Multipart accepts ``paint_file``/``file`` and the same form coordinates.
    The display JPEG is never consulted.
    """
    temp_uploaded_path = None
    try:
        from PIL import Image as PILImage

        content_type = (request.content_type or "").lower()
        json_body = request.get_json(silent=True) if content_type.startswith("application/json") else None
        values = json_body if isinstance(json_body, dict) else request.form
        raw_x = values.get("x", values.get("nx"))
        raw_y = values.get("y", values.get("ny"))
        if raw_x is None or raw_y is None:
            return jsonify({
                "success": False,
                "code": "normalized_coordinates_required",
                "error": "x and y are required normalized coordinates between 0 and 1",
            }), 400
        try:
            nx = float(raw_x)
            ny = float(raw_y)
            radius = int(values.get("radius", 2))
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "code": "invalid_sample_coordinates",
                "error": "x, y, and radius must be numeric",
            }), 400

        source_via = "upload"
        source_filename = "paint"
        if json_body is not None:
            allowed, blocked_reason = _require_spb_internal_request()
            if not allowed:
                return jsonify({
                    "success": False,
                    "code": "internal_request_required",
                    "error": blocked_reason,
                }), 403
            source_token = str(values.get("source_token") or "").strip()
            if source_token:
                paint_path, token_error = _resolve_spec_sculpt_source_token(source_token)
                if token_error:
                    return jsonify({
                        "success": False,
                        "code": "invalid_source_token",
                        "error": token_error,
                    }), 409
                source_via = "source_token"
            else:
                paint_path, path_error = _resolve_spec_sculpt_sample_path(values.get("paint_file"))
                if path_error:
                    return jsonify({
                        "success": False,
                        "code": "source_path_not_allowed",
                        "error": path_error,
                    }), 403
                source_via = "paint_file"
            source_filename = os.path.basename(paint_path)
        else:
            uploaded = request.files.get("paint_file") or request.files.get("file")
            if not uploaded or not uploaded.filename:
                return jsonify({
                    "success": False,
                    "code": "paint_source_required",
                    "error": "Upload paint_file/file or send JSON source_token/paint_file",
                }), 400
            source_filename = os.path.basename(str(uploaded.filename).replace("\\", "/")) or "paint"
            temp_uploaded_path = _spb_temp_file_path(
                f"spec_sculpt_sample_{uuid.uuid4().hex}_{source_filename}"
            )
            uploaded.save(temp_uploaded_path)
            paint_path = temp_uploaded_path

        extension = os.path.splitext(paint_path)[1].lower()
        if extension not in {".tga", ".png", ".jpg", ".jpeg"}:
            return jsonify({
                "success": False,
                "code": "unsupported_paint_source",
                "error": "Source color sampling supports TGA, PNG, JPG, and JPEG paints",
            }), 400
        if not os.path.isfile(paint_path):
            return jsonify({
                "success": False,
                "code": "paint_source_not_found",
                "error": "Source paint is no longer available",
            }), 404

        with PILImage.open(paint_path) as image:
            width, height = image.size
            if width != 2048 or height != 2048:
                return jsonify({
                    "success": False,
                    "code": "easy_requires_2048",
                    "error": "Easy Mode source-color sampling requires an exact 2048x2048 iRacing paint template.",
                    "original_resolution": [int(width), int(height)],
                }), 400
            sample = _spec_sculpt_native_color_sample(image, nx, ny, radius)

        return jsonify({
            "success": True,
            "rgb": sample["rgb"],
            "hex": sample["hex"],
            "sample": sample,
            "palette": sample["palette"],
            "source": {
                "filename": source_filename,
                "resolution": [2048, 2048],
                "exact_2048": True,
                "via": source_via,
            },
        })
    except ValueError as exc:
        return jsonify({
            "success": False,
            "code": "invalid_sample_coordinates",
            "error": str(exc),
        }), 400
    except Exception as exc:
        logger.error(f"/api/spec-sculpt/sample-source-color error: {exc}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        if temp_uploaded_path:
            try:
                os.remove(temp_uploaded_path)
            except OSError as _spb_ex:
                _spb_swallow('api_spec_sculpt_sample_source_color@L12866', _spb_ex)


@app.route('/api/spec-sculpt/generate', methods=['POST'])
def api_spec_sculpt_generate():
    """Scratch spec from paint + optional ``job_*`` outputs matching ``/render``.

    **Multipart** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â ``file`` or ``paint_file`` (upload).

    **JSON** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â ``{"paint_file": "/abs/path.tga", ...}`` so Electron/desktop can pass Source Paint path.

    Shared parameters (form or JSON keys):

      seed, chromatic_shift, strict2048, save_tga, iracing_id, use_custom_number,
      output_dir, live_link, deploy_car_folder (iRacing car folder basename ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Documents/iRacing/paint/<name>/),
      preset_stack (JSON list), catalog_stack (JSON list), fusion_mix (0ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“1 blend toward catalog when both stacks set),
      fusion_strategy (linear | gloss_win_metallic), fusion_mix_m/r/cc (optional per-channel 0ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“1),
      paint_emphasis (uniform|highlights|shadows|saturated|desaturated), paint_emphasis_strength (0ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“1),
      hue_focus_deg, hue_focus_width, hue_focus_strength (optional hue tie-in),
      spec_detail_scale (optional VM/Rising Sun DS intensity ~0.85ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“2.35, maps to _pre_adjust detail_scale),
      preview_tex_size (512 | 1024 | 2048) ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â only applies when save_tga is false (live preview): runs spec pipeline at that square size for speed; full Generate uses 2048 always.
      preview_progressive (bool, JSON or form) ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â when save_tga is false: run 512Ãƒâ€šÃ‚Â² then 1024Ãƒâ€šÃ‚Â² in one request; returns previews_by_size {"512":{...},"1024":{...}} and previews set to the 1024 pass (omit preview_tex_size or it is ignored).
    """
    temp_created_path = None
    try:
        ct = (request.content_type or "").lower()
        json_body = request.get_json(silent=True) if ct.startswith("application/json") else None

        def gv(key, default=None):
            if json_body is not None:
                val = json_body.get(key)
                return default if val is None else val
            return request.form.get(key, default)

        cfg = load_config()
        seed = _safe_int(gv("seed"), 9101) & 0xFFFFFFFF
        chromatic = _parse_bool_form(gv("chromatic_shift"))
        if chromatic is None:
            chromatic = True
        strict = _parse_bool_form(gv("strict2048"))
        if strict is None:
            strict = False
        save_tga = _parse_bool_form(gv("save_tga"))
        if save_tga is None:
            save_tga = True
        fast_trace = _parse_bool_form(gv("fast_trace"))
        if fast_trace is None:
            fast_trace = False

        # Owner Easy Mode 2026-07-18: identity belongs to export, not creative
        # preview. Full Generate retains the validated saved-ID fallback; a
        # preview may run with no ID at all and never writes a customer file.
        raw_id = str(gv("iracing_id") or "").strip()
        if not raw_id:
            raw_id = str(cfg.get("iracing_id") or "").strip()
        ok_id, validated_id, id_err = _validate_iracing_id(raw_id)
        if save_tga and not ok_id:
            return jsonify({"success": False, "error": id_err}), 400
        iracing_id = validated_id if ok_id else ""

        use_custom_number = _parse_bool_form(gv("use_custom_number"))
        if use_custom_number is None:
            use_custom_number = bool(cfg.get("use_custom_number", True))
        car_prefix = "car_num" if use_custom_number else "car"

        output_dir_user = str(gv("output_dir") or "").strip()
        use_live_link = _parse_bool_form(gv("live_link"))
        if use_live_link is None:
            use_live_link = False
        deploy_car_folder = str(gv("deploy_car_folder") or "").strip()

        def _gv_float(key, default):
            val = gv(key)
            if val is None:
                return default
            if isinstance(val, str) and not str(val).strip():
                return default
            try:
                return float(val)
            except (TypeError, ValueError):
                return default

        dark_interior_flatten = max(0.0, min(1.0, _gv_float("dark_interior_flatten", 0.38)))
        void_metallic_max = max(1.0, min(255.0, _gv_float("void_metallic_max", 92.0)))
        void_roughness_min = max(1.0, min(255.0, _gv_float("void_roughness_min", 158.0)))
        void_clearcoat_max = max(1.0, min(255.0, _gv_float("void_clearcoat_max", 44.0)))
        spec_multiplier = max(0.0, min(1.0, _gv_float("spec_multiplier", 1.0)))

        def _gv_opt_float(key):
            v = gv(key)
            if v is None or (isinstance(v, str) and not str(v).strip()):
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        fusion_strategy_raw = str(gv("fusion_strategy") or "linear").strip().lower()
        if fusion_strategy_raw in ("gloss_win", "gloss_win_metallic", "showroom", "pop_metallic"):
            fusion_strategy = "gloss_win_metallic"
        else:
            fusion_strategy = "linear"
        fusion_mix_m = _gv_opt_float("fusion_mix_m")
        fusion_mix_r = _gv_opt_float("fusion_mix_r")
        fusion_mix_cc = _gv_opt_float("fusion_mix_cc")
        paint_emphasis = str(gv("paint_emphasis") or "uniform").strip().lower()
        if paint_emphasis not in (
            "uniform", "highlights", "shadows", "saturated", "desaturated",
        ):
            paint_emphasis = "uniform"
        paint_emphasis_strength = max(0.0, min(1.0, _gv_float("paint_emphasis_strength", 0.0)))
        hue_focus_deg = _gv_opt_float("hue_focus_deg")
        if hue_focus_deg is not None:
            hue_focus_deg = float(hue_focus_deg % 360.0)
        hue_focus_width = max(8.0, min(180.0, _gv_float("hue_focus_width", 60.0)))
        hue_focus_strength = max(0.0, min(1.0, _gv_float("hue_focus_strength", 0.0)))

        spec_detail_scale = _gv_opt_float("spec_detail_scale")
        if spec_detail_scale is not None:
            spec_detail_scale = max(0.85, min(2.35, float(spec_detail_scale)))

        # FRACTURE mode — ignites an arbitrary loaded paint with the FRACTURED look via the
        # shared engine (engine/spec_sculpt/fracture.py through generate.fracture_spec_from_any_paint).
        # Selected by mode="fracture"; the 5 dials are clamped here to the engine's safe ranges
        # (the engine re-clips too). Any other mode value runs the existing scratch/catalog/fusion path.
        sculpt_mode = str(gv("mode") or "").strip().lower()
        fracture_ignition = max(0.0, min(2.0, _gv_float("fracture_ignition", 1.0)))
        fracture_angle_gate = max(0.25, min(2.0, _gv_float("fracture_angle_gate", 1.0)))
        fracture_trace_strength = max(0.0, min(2.0, _gv_float("fracture_trace_strength", 1.0)))
        fracture_calm_floor = max(14.0, min(110.0, _gv_float("fracture_calm_floor", 30.0)))
        fracture_decorrelation = max(0.0, min(1.0, _gv_float("fracture_decorrelation", 0.0)))

        # CANDY DEPTH mode (2026-06-19): mode="candy_depth" -> bottomless wet-candy clearcoat + suspended
        # flakes via generate.candy_depth_spec_from_any_paint. Dials clamped here (engine re-clips too).
        candy_depth = max(0.0, min(1.5, _gv_float("candy_depth", 1.0)))
        candy_flake_density = max(0.0, min(1.0, _gv_float("candy_flake_density", 0.5)))
        candy_flake_size = max(0.5, min(3.0, _gv_float("candy_flake_size", 1.0)))
        candy_wetness = max(0.0, min(1.0, _gv_float("candy_wetness", 0.78)))
        candy_satin_floor = max(0.15, min(0.8, _gv_float("candy_satin_floor", 0.42)))

        style_notes = str(gv("style_notes") or "").strip()
        mix_style_notes = _parse_bool_form(gv("mix_style_notes"))
        if mix_style_notes is None:
            mix_style_notes = False

        effective_seed = seed & 0xFFFFFFFF
        if mix_style_notes and style_notes:
            import zlib
            effective_seed = (seed + (zlib.adler32(style_notes.encode("utf-8")) & 0xFFFFFFFF)) & 0xFFFFFFFF

        raw_ps = gv("preset_stack")
        preset_stack_payload = None
        if raw_ps is not None and raw_ps != "":
            if isinstance(raw_ps, str):
                try:
                    preset_stack_payload = json.loads(raw_ps)
                except Exception:
                    preset_stack_payload = None
            elif isinstance(raw_ps, list):
                preset_stack_payload = raw_ps

        raw_cs = gv("catalog_stack")
        catalog_stack_payload = None
        if raw_cs is not None and raw_cs != "":
            if isinstance(raw_cs, str):
                try:
                    catalog_stack_payload = json.loads(raw_cs)
                except Exception:
                    catalog_stack_payload = None
            elif isinstance(raw_cs, list):
                catalog_stack_payload = raw_cs

        paint_disk_path = None
        if json_body is not None:
            pf = str(gv("paint_file") or "").strip()
            if not pf:
                return jsonify({"success": False, "error": "JSON body requires paint_file (absolute path)"}), 400
            paint_disk_path = os.path.abspath(os.path.expanduser(pf))
            if not os.path.isfile(paint_disk_path):
                return jsonify({"success": False, "error": f"paint_file not found: {paint_disk_path}"}), 400
        else:
            if 'file' not in request.files and 'paint_file' not in request.files:
                return jsonify({"success": False, "error": "No file; use multipart field 'file' or 'paint_file'."}), 400
            f = request.files.get('file') or request.files.get('paint_file')
            if not f or not f.filename:
                return jsonify({"success": False, "error": "Empty upload"}), 400
            upload_name = os.path.basename(str(f.filename).replace("\\", "/")) or "paint"
            temp_created_path = _spb_temp_file_path(f"spec_sculpt_in_{uuid.uuid4().hex}_{upload_name}")
            f.save(temp_created_path)
            paint_disk_path = temp_created_path

        # Owner Easy Mode 2026-07-18: the 2048-only promise is a front-door
        # contract. Reject before loading registries or running any sculpt math,
        # for previews as well as saved jobs. Pro callers can still opt out by
        # sending strict2048=false and retain the legacy resize behavior.
        if strict:
            from PIL import Image as _StrictPILImage
            with _StrictPILImage.open(paint_disk_path) as _strict_img:
                _strict_w, _strict_h = _strict_img.size
            if _strict_w != 2048 or _strict_h != 2048:
                return jsonify({
                    "success": False,
                    "error": "Easy Mode requires an exact 2048x2048 iRacing paint template.",
                    "code": "easy_requires_2048",
                    "original_resolution": [int(_strict_w), int(_strict_h)],
                }), 400

        import numpy as np

        from engine.spec_sculpt.core import load_paint_rgb_float01
        from engine.spec_sculpt.generate import scratch_spec_from_any_paint, fracture_spec_from_any_paint, candy_depth_spec_from_any_paint, zoned_auto_spec, apply_sculpt_mask, build_protect_mask, refine_sculpt_mask, auto_protect_mask_from_paint, auto_levels, hsb_shift, apply_channel_gain, iron_fix, weather_spec, hue_material_spec, tone_material_spec
        # HSB source recolor (e.g. pink base -> blue) before sculpting; feeds the brightness-keyed FRACTURED finishes too.
        def _hsbf(k, d):
            try:
                return float(gv(k))
            except (TypeError, ValueError):
                return d
        _hsb_h = max(-180.0, min(180.0, _hsbf("hsb_h", 0.0)))
        _hsb_s = max(0.0, min(2.0, _hsbf("hsb_s", 1.0)))
        _hsb_v = max(0.2, min(2.0, _hsbf("hsb_v", 1.0)))
        # COLOR -> MATERIAL / TONE -> MATERIAL as a first-class GENERATE source: when the client sends
        # hue_rules or tone_bands, build the full 2048 spec from them (so the previewed map is what deploys).
        def _jparse_gen(v):
            if v in (None, ""):
                return None
            if isinstance(v, (list, dict)):
                return v
            try:
                return json.loads(str(v))
            except Exception:
                return None
        _hue_rules = _jparse_gen(gv("hue_rules"))
        _tone_bands = _jparse_gen(gv("tone_bands"))
        if not isinstance(_hue_rules, list):
            _hue_rules = None
        if not isinstance(_tone_bands, list):
            _tone_bands = None
        _material_base = str(gv("material_base") or "satin").strip().lower()
        _auto_levels_on = bool(_parse_bool_form(gv("auto_levels")))
        # #auto-protect: best-effort decal protection from a FLAT paint (no PSD). Only used when no PSD mask.
        _auto_protect_on = bool(_parse_bool_form(gv("auto_protect")))
        try:
            _ap_strength = max(0.3, min(2.0, float(gv("auto_protect_strength")))) if gv("auto_protect_strength") not in (None, "") else 1.0
        except (TypeError, ValueError):
            _ap_strength = 1.0

        def _gain(k):
            try:
                v = float(gv(k))
                return max(0.3, min(2.0, v)) if v else 1.0
            except (TypeError, ValueError):
                return 1.0
        _gm, _gr, _gcc = _gain("spec_gain_m"), _gain("spec_gain_r"), _gain("spec_gain_cc")
        from engine.spec_sculpt.catalog_blend import normalize_catalog_stack
        from engine.spec_sculpt.easy_material_layers import (
            apply_material_impact,
            apply_material_impact_to_report,
            composite_easy_color_layers,
            normalize_material_impact,
            normalize_material_scale,
            parse_easy_color_layers,
            pattern_tile_for_scale,
            recolor_easy_paint,
        )
        from engine.spec_sculpt.presets import normalize_preset_stack
        from engine.spec_sculpt.preview import spec_preview_png_data_urls
        from engine.spec_sculpt.export import save_spec_tga_iron_safe
        from PIL import Image as PILImage

        is_fracture = sculpt_mode == "fracture"
        is_candy = sculpt_mode == "candy_depth"
        is_zoned = sculpt_mode == "zoned"
        _zoned_drama = max(0.55, min(1.45, _gv_float("zoned_drama", 1.0)))
        material_scale = normalize_material_scale(gv("material_scale"), 1.0)
        material_impact = normalize_material_impact(gv("material_impact"))
        _easy_color_layers = parse_easy_color_layers(gv("easy_color_layers"))
        _easy_color_report = []

        def _run_primary_sculpt(_tex):
            """Route the loaded paint tex to ZONED / COLOR/TONE→MATERIAL / CANDY DEPTH / FRACTURE / scratch."""
            if is_zoned:
                return zoned_auto_spec(_tex, effective_seed, drama=_zoned_drama)   # Easy intent + per-region map
            if _hue_rules or _tone_bands:
                import numpy as _np
                _m = hue_material_spec(_tex, _hue_rules, base=_material_base) if _hue_rules \
                    else tone_material_spec(_tex, _tone_bands, base=_material_base)
                _m = _np.asarray(_m)
                # the pipeline contract is HxWx4 (R=M,G=R,B=Cc,A); hue/tone_material_spec return HxWx3.
                if _m.ndim == 3 and _m.shape[2] == 3:
                    _alpha = _np.full(_m.shape[:2] + (1,), 255, _np.uint8)
                    _m = _np.concatenate([_m.astype(_np.uint8), _alpha], axis=2)
                return _m
            if is_candy:
                return candy_depth_spec_from_any_paint(
                    _tex,
                    depth=candy_depth,
                    flake_density=candy_flake_density,
                    flake_size=candy_flake_size,
                    wetness=candy_wetness,
                    satin_floor=candy_satin_floor,
                    seed=effective_seed,
                )
            if is_fracture:
                return fracture_spec_from_any_paint(
                    _tex,
                    ignition=fracture_ignition,
                    angle_gate=fracture_angle_gate,
                    trace_strength=fracture_trace_strength,
                    calm_floor=fracture_calm_floor,
                    decorrelation=fracture_decorrelation,
                )
            return scratch_spec_from_any_paint(
                _tex,
                seed=effective_seed,
                chromatic_shift=chromatic,
                dark_interior_flatten=dark_interior_flatten,
                void_metallic_max=void_metallic_max,
                void_roughness_min=void_roughness_min,
                void_clearcoat_max=void_clearcoat_max,
                spec_multiplier=spec_multiplier,
                preset_stack=preset_stack_arg,
                catalog_stack=catalog_stack_arg,
                fusion_mix=fusion_pass,
                fusion_mix_m=fusion_mix_m,
                fusion_mix_r=fusion_mix_r,
                fusion_mix_cc=fusion_mix_cc,
                fusion_strategy=fusion_strategy,
                paint_emphasis=paint_emphasis,
                paint_emphasis_strength=paint_emphasis_strength,
                hue_focus_deg=hue_focus_deg if hue_focus_strength > 1e-6 else None,
                hue_focus_width=hue_focus_width,
                hue_focus_strength=hue_focus_strength,
                vm_detail_scale=spec_detail_scale,
                pattern_tile=pattern_tile_for_scale(material_scale),
                fast_trace=fast_trace,
            )

        def _run_sculpt_spec(_tex):
            """Render the whole-paint look, then bounded Easy color material layers."""
            base_spec = _run_primary_sculpt(_tex)
            if not _easy_color_layers:
                _easy_color_report[:] = []
                return base_spec

            # Reuse a full material render when two selected colors share a look.
            # Their color masks stay independent; only the expensive look bake is cached.
            _look_cache = {}

            def _render_easy_layer(layer):
                # Each guided color is its own stable material layer. The client
                # derives this from only that color + look, so editing one color
                # cannot reshuffle the whole-paint texture or its sibling colors.
                _layer_seed = int(layer.get("seed") if layer.get("seed") is not None else effective_seed) & 0xFFFFFFFF
                _key = (
                    layer["kind"], layer["look_id"], layer.get("catalog_type", ""),
                    layer["material_scale"], _layer_seed,
                    int(_tex.shape[0]), int(_tex.shape[1]),
                )
                if _key in _look_cache:
                    return _look_cache[_key]
                if layer["kind"] == "mode":
                    if layer["look_id"] == "zoned":
                        rendered = zoned_auto_spec(_tex, _layer_seed, drama=_zoned_drama)
                    elif layer["look_id"] == "fracture":
                        rendered = fracture_spec_from_any_paint(
                            _tex,
                            ignition=fracture_ignition,
                            angle_gate=fracture_angle_gate,
                            trace_strength=fracture_trace_strength,
                            calm_floor=fracture_calm_floor,
                            decorrelation=fracture_decorrelation,
                        )
                    else:
                        rendered = candy_depth_spec_from_any_paint(
                            _tex,
                            depth=candy_depth,
                            flake_density=candy_flake_density,
                            flake_size=candy_flake_size,
                            wetness=candy_wetness,
                            satin_floor=candy_satin_floor,
                            seed=_layer_seed,
                        )
                else:
                    rendered = scratch_spec_from_any_paint(
                        _tex,
                        seed=_layer_seed,
                        chromatic_shift=chromatic,
                        dark_interior_flatten=dark_interior_flatten,
                        void_metallic_max=void_metallic_max,
                        void_roughness_min=void_roughness_min,
                        void_clearcoat_max=void_clearcoat_max,
                        spec_multiplier=spec_multiplier,
                        preset_stack=[(layer["look_id"], 1.0)] if layer["kind"] == "preset" else None,
                        catalog_stack=[{
                            "id": layer["look_id"],
                            "weight": 1.0,
                            "registry_type": layer.get("catalog_type"),
                        }] if layer["kind"] == "catalog" else None,
                        paint_emphasis=paint_emphasis,
                        paint_emphasis_strength=paint_emphasis_strength,
                        hue_focus_deg=hue_focus_deg if hue_focus_strength > 1e-6 else None,
                        hue_focus_width=hue_focus_width,
                        hue_focus_strength=hue_focus_strength,
                        vm_detail_scale=spec_detail_scale,
                        pattern_tile=pattern_tile_for_scale(layer["material_scale"]),
                        fast_trace=fast_trace,
                    )
                _look_cache[_key] = rendered
                return rendered

            composited, report = composite_easy_color_layers(
                base_spec, _tex, _easy_color_layers, _render_easy_layer,
            )
            _easy_color_report[:] = report
            return composited

        preset_stack_norm = normalize_preset_stack(preset_stack_payload)
        catalog_stack_norm = normalize_catalog_stack(catalog_stack_payload)

        raw_fusion = gv("fusion_mix")
        fusion_mix_val = None
        if raw_fusion is not None and str(raw_fusion).strip() != "":
            try:
                fusion_mix_val = max(0.0, min(1.0, float(raw_fusion)))
            except (TypeError, ValueError):
                fusion_mix_val = None

        preview_progressive = _parse_bool_form(gv("preview_progressive"))
        if preview_progressive is None:
            preview_progressive = False
        if save_tga:
            preview_progressive = False

        preview_tex_size = _safe_int(gv("preview_tex_size"), 2048)
        if preview_tex_size not in (512, 1024, 2048):
            preview_tex_size = 2048
        load_target = 2048 if save_tga else preview_tex_size

        warnings = []
        if catalog_stack_norm and preset_stack_norm:
            if fusion_mix_val is None:
                warnings.append(
                    "catalog_stack and preset_stack both set ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â catalog used; add fusion_mix (0ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“1) to blend both."
                )

        if catalog_stack_norm and preset_stack_norm and fusion_mix_val is not None:
            catalog_stack_arg = catalog_stack_norm
            preset_stack_arg = preset_stack_norm
            fusion_pass = fusion_mix_val
        elif catalog_stack_norm and preset_stack_norm and fusion_mix_val is None:
            catalog_stack_arg = catalog_stack_norm
            preset_stack_arg = None
            fusion_pass = None
        else:
            catalog_stack_arg = catalog_stack_norm if catalog_stack_norm else None
            preset_stack_arg = preset_stack_norm if preset_stack_norm else None
            fusion_pass = None

        tex = None
        orig_hw = None
        final_hw = None
        spec_u8 = None
        previews = None
        previews_by_size = None

        # LAYER-AWARE SCULPT (2026-06-24, Spec Sculpt prototype): if the client passed a PSD path +
        # the names of layers to PROTECT (sponsors/logos/numbers/decals), build a mask once and shield
        # those pixels from the sculpt. Fully additive + guarded: no PSD / no names -> _protect_mask
        # stays None and generate behaves exactly as before.
        _protect_mask = None
        try:
            _protect_raw = gv("protect_layers")
            _protect_keys_raw = gv("protect_layer_keys")
            _psd_src = gv("psd_path") or gv("psd_src")
            if _psd_src and (_protect_raw or _protect_keys_raw):
                def _protect_id_list(raw_value):
                    if not raw_value:
                        return []
                    if isinstance(raw_value, (list, tuple)):
                        return list(raw_value)
                    _s = str(raw_value).strip()
                    try:
                        import json as _json
                        parsed = _json.loads(_s)
                        return parsed if isinstance(parsed, list) else [str(parsed)]
                    except Exception:
                        return [x.strip() for x in _s.split(",") if x.strip()]

                _protect_names = _protect_id_list(_protect_raw)
                _protect_keys = _protect_id_list(_protect_keys_raw)
                _protect_mask = build_protect_mask(
                    _psd_src, _protect_names, protect_keys=_protect_keys
                )
                if _protect_mask is not None:
                    try:
                        app.logger.info(
                            "[Spec Sculpt] layer-aware: protecting %d PSD layer identity(s)",
                            len(_protect_names) + len(_protect_keys),
                        )
                    except Exception as _spb_ex:
                        _spb_swallow('api_spec_sculpt_generate@L13366', _spb_ex)
        except Exception:
            _protect_mask = None

        # #24 Mask refine: grow/contract the protected region (px) + boundary feather (px).
        try:
            _mask_grow = _safe_int(gv("mask_grow"), 0)
        except Exception:
            _mask_grow = 0
        try:
            _mf = gv("mask_feather")
            _mask_feather = max(0.0, min(12.0, float(_mf))) if _mf not in (None, "") else 2.0
        except (TypeError, ValueError):
            _mask_feather = 2.0
        # protected-decal finish (realism): default 'matte' keeps the legacy neutral (no behavior change).
        _PROTECT_MATS = {'matte': (0, 160, 0), 'satin': (105, 110, 140), 'gloss': (135, 45, 240), 'wet': (110, 35, 248), 'carbon': (70, 150, 55)}
        _protect_neutral = _PROTECT_MATS.get(str(gv("protect_material") or "matte").strip().lower(), (0, 160, 0))
        if _protect_mask is not None and _mask_grow:
            _protect_mask = refine_sculpt_mask(_protect_mask, _mask_grow)

        # Material weathering / detail (#13j): procedural micro-texture baked into preview + deploy.
        _weather_kind = str(gv("weather_kind") or "").strip().lower() or None
        try:
            _wa = gv("weather_amount")
            _weather_amt = max(0.0, min(1.0, float(_wa))) if _wa not in (None, "") else 0.5
        except (TypeError, ValueError):
            _weather_amt = 0.5
        _weather_seed = _safe_int(gv("seed"), 9101)

        if preview_progressive:
            previews_by_size = {}
            for psz in (512, 1024):
                tex, orig_hw, final_hw = load_paint_rgb_float01(paint_disk_path, target_size=psz)
                tex = hsb_shift(tex, _hsb_h, _hsb_s, _hsb_v)
                if _auto_levels_on:
                    tex = auto_levels(tex)
                spec_u8 = _run_sculpt_spec(tex)
                spec_u8 = apply_channel_gain(spec_u8, _gm, _gr, _gcc)
                spec_u8 = apply_material_impact(spec_u8, material_impact)
                _easy_color_report[:] = apply_material_impact_to_report(_easy_color_report, material_impact)
                _eff_mask = _protect_mask
                if _eff_mask is None and _auto_protect_on:
                    _eff_mask = auto_protect_mask_from_paint(tex, strength=_ap_strength)
                    if _eff_mask is not None and _mask_grow:
                        _eff_mask = refine_sculpt_mask(_eff_mask, _mask_grow)
                if _eff_mask is not None:
                    spec_u8 = apply_sculpt_mask(spec_u8, _eff_mask, feather=_mask_feather, neutral=_protect_neutral)
                if _weather_kind:
                    spec_u8 = weather_spec(spec_u8, _weather_kind, _weather_amt, seed=_weather_seed)
                spec_u8 = iron_fix(spec_u8)
                previews_by_size[str(psz)] = spec_preview_png_data_urls(spec_u8)
            previews = previews_by_size.get("1024") or previews_by_size.get("512")
        else:
            tex, orig_hw, final_hw = load_paint_rgb_float01(paint_disk_path, target_size=load_target)
            tex = hsb_shift(tex, _hsb_h, _hsb_s, _hsb_v)
            if _auto_levels_on:
                tex = auto_levels(tex)
            spec_u8 = _run_sculpt_spec(tex)
            spec_u8 = apply_channel_gain(spec_u8, _gm, _gr, _gcc)
            spec_u8 = apply_material_impact(spec_u8, material_impact)
            _easy_color_report[:] = apply_material_impact_to_report(_easy_color_report, material_impact)
            _eff_mask = _protect_mask
            if _eff_mask is None and _auto_protect_on:
                _eff_mask = auto_protect_mask_from_paint(tex, strength=_ap_strength)
                if _eff_mask is not None and _mask_grow:
                    _eff_mask = refine_sculpt_mask(_eff_mask, _mask_grow)
            if _eff_mask is not None:
                spec_u8 = apply_sculpt_mask(spec_u8, _eff_mask, feather=_mask_feather, neutral=_protect_neutral)
            if _weather_kind:
                spec_u8 = weather_spec(spec_u8, _weather_kind, _weather_amt, seed=_weather_seed)
            spec_u8 = iron_fix(spec_u8)
            # Owner 2026-07-20: a warmed multi-material install measured 19.43s.
            # TGAs remain exact 2048; four full-size browser PNGs alone cost 2.64s.
            _preview_spec_u8 = spec_u8
            if save_tga and max(spec_u8.shape[:2]) > 512:
                _preview_spec_u8 = np.asarray(
                    PILImage.fromarray(spec_u8, mode="RGBA").resize(
                        (512, 512), PILImage.Resampling.LANCZOS
                    ),
                    dtype=np.uint8,
                )
            previews = spec_preview_png_data_urls(_preview_spec_u8)

        if strict and save_tga and (orig_hw[0] != 2048 or orig_hw[1] != 2048):
            return jsonify({
                "success": False,
                "error": "strict2048: source must be 2048ÃƒÆ’Ã¢â‚¬â€2048",
                "original_resolution": [int(orig_hw[1]), int(orig_hw[0])],
            }), 400
        if save_tga and (orig_hw[0] != 2048 or orig_hw[1] != 2048):
            warnings.append(f"Resized source {orig_hw[1]}ÃƒÆ’Ã¢â‚¬â€{orig_hw[0]} ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ 2048ÃƒÆ’Ã¢â‚¬â€2048 for scratch pipeline.")

        paint_tex = recolor_easy_paint(tex, _easy_color_layers)
        paint_rgb_u8 = (np.clip(paint_tex, 0.0, 1.0) * 255.0).astype(np.uint8)

        job_id = None
        job_dir = None
        out_paint_tga = None
        spec_path_out = None
        export_path = None
        output_dir_status = None
        live_link_status = None
        deploy_status = None
        preview_urls = {}
        download_urls = {}

        if save_tga:
            job_id = f"sculpt_{int(time.time())}_{iracing_id}_{uuid.uuid4().hex[:12]}"
            job_dir = os.path.join(SPEC_SCULPT_JOBS_DIR, f"job_{job_id}")
            os.makedirs(job_dir, exist_ok=True)

            out_paint_tga = os.path.join(job_dir, f"{car_prefix}_{iracing_id}.tga")
            spec_path_out = os.path.join(job_dir, f"car_spec_{iracing_id}.tga")
            engine.write_tga_24bit(out_paint_tga, paint_rgb_u8)
            # SPB beta hardening 2026-07-21: ``iron_fix`` ran immediately above.
            # Skip a byte-identical second 2048² safety copy during export.
            export_path = save_spec_tga_iron_safe(spec_u8, spec_path_out, already_safe=True)

            try:
                _paint_preview_img = PILImage.fromarray(paint_rgb_u8)
                _spec_preview_img = PILImage.fromarray(spec_u8, mode="RGBA")
                if max(paint_rgb_u8.shape[:2]) > 512:
                    _paint_preview_img = _paint_preview_img.resize((512, 512), PILImage.Resampling.LANCZOS)
                    _spec_preview_img = _spec_preview_img.resize((512, 512), PILImage.Resampling.LANCZOS)
                _paint_preview_img.save(os.path.join(job_dir, "PREVIEW_paint.png"))
                _spec_preview_img.save(os.path.join(job_dir, "PREVIEW_spec.png"))
            except Exception as exc:
                logger.warning(f"spec-sculpt: preview PNG save failed: {exc}")

            try:
                _latest_dir = os.path.join(SPEC_SCULPT_JOBS_DIR, "_latest_render")
                os.makedirs(_latest_dir, exist_ok=True)
                if os.path.exists(spec_path_out):
                    shutil.copy2(spec_path_out, os.path.join(_latest_dir, "spec.tga"))
                if os.path.exists(out_paint_tga):
                    shutil.copy2(out_paint_tga, os.path.join(_latest_dir, "paint.tga"))
                _pv = os.path.join(job_dir, "PREVIEW_paint.png")
                if os.path.exists(_pv):
                    shutil.copy2(_pv, os.path.join(_latest_dir, "preview.png"))
                if os.path.exists(spec_path_out):
                    try:
                        PILImage.open(spec_path_out).resize((512, 512), PILImage.Resampling.LANCZOS).save(os.path.join(_latest_dir, "spec.png"))
                    except Exception as _spb_ex:
                        _spb_swallow('api_spec_sculpt_generate@L13509', _spb_ex)
            except Exception as exc:
                logger.warning(f"spec-sculpt: _latest_render persist failed: {exc}")

            def _job_file_url(route_name, fname):
                return f"/{route_name}/{job_id}/{quote(fname, safe='')}"

            for fname in os.listdir(job_dir):
                if fname.endswith(".png"):
                    preview_urls[fname] = _job_file_url("preview", fname)
            for fname in os.listdir(job_dir):
                if fname.endswith(".tga"):
                    download_urls[fname.replace(".tga", "")] = _job_file_url("download", fname)

            _osc_target = _coerce_output_dir(output_dir_user)
            if _osc_target:
                target = _osc_target
                try:
                    pushed = _push_standard_car_outputs_to_dir(
                        job_dir, iracing_id, car_prefix, target, "Spec Sculpt output_dir"
                    )
                    output_dir_status = {
                        "success": True,
                        "verified": True,
                        "path": target.replace("\\", "/"),
                        "pushed_files": pushed,
                        "message": f"Saved {len(pushed)} files to {target}",
                    }
                except Exception as exc:
                    output_dir_status = {"success": False, "path": target.replace("\\", "/"), "error": str(exc)}
                    logger.error(f"Spec Sculpt output_dir error: {exc}")

            elif output_dir_user.strip():
                output_dir_status = {
                    "success": False,
                    "path": output_dir_user.strip().replace("\\", "/"),
                    "error": f"iRacing output folder not found: {output_dir_user.strip()} — set this to your iRacing car FOLDER (Documents\\iRacing\\paint\\<car>), not a file.",
                }

            if use_live_link:
                car_path, active_car, live_link_error, live_link_source = _resolve_live_link_target(
                    cfg, output_dir_user
                )
                if car_path:
                    try:
                        pushed = _push_standard_car_outputs_to_dir(
                            job_dir, iracing_id, car_prefix, car_path, "Spec Sculpt Live Link"
                        )
                        live_link_status = {
                            "success": True,
                            "verified": True,
                            "car": active_car,
                            "path": car_path.replace("\\", "/"),
                            "source": live_link_source,
                            "pushed_files": pushed,
                            "message": f"Pushed {len(pushed)} files to iRacing! Alt+Tab and Ctrl+R.",
                        }
                    except Exception as exc:
                        live_link_status = {
                            "success": False,
                            "car": active_car,
                            "path": car_path.replace("\\", "/"),
                            "source": live_link_source,
                            "error": str(exc),
                        }
                        logger.error(f"Spec Sculpt Live Link error: {exc}")
                else:
                    live_link_status = {
                        "success": False,
                        "car": active_car,
                        "source": live_link_source,
                        "error": live_link_error,
                    }

            if deploy_car_folder:
                deploy_status = _deploy_job_dir_to_iracing_paint(job_dir, deploy_car_folder, iracing_id)

        def _spec_sculpt_payload_finish():
            if is_candy:
                return f"spec_sculpt_candy_{effective_seed}", "candy_depth"
            if is_fracture:
                return f"spec_sculpt_fracture_{effective_seed}", "fracture"
            if catalog_stack_arg and preset_stack_arg and fusion_pass is not None:
                fp = float(fusion_pass)
                if fp >= 1.0 - 1e-7:
                    fid = ("catalog_blend_" + "_".join(p[0] for p in catalog_stack_arg))[:220]
                elif fp <= 1e-7:
                    fid = (
                        f"spec_sculpt_{effective_seed}_blend_" + "_".join(p[0] for p in preset_stack_arg)
                    )[:220]
                else:
                    fid = (
                        f"fusion_{fp:.3f}_cat_" + "_".join(p[0] for p in catalog_stack_arg)
                        + "_scr_" + "_".join(p[0] for p in preset_stack_arg)
                    )[:220]
                return fid, "fusion_registry_scratch"
            if catalog_stack_arg:
                return ("catalog_blend_" + "_".join(p[0] for p in catalog_stack_arg))[:220], "catalog_registry"
            if preset_stack_arg:
                return (
                    f"spec_sculpt_{effective_seed}_blend_" + "_".join(p[0] for p in preset_stack_arg),
                    "scratch_presets",
                )
            return f"spec_sculpt_{effective_seed}", "scratch_solo"

        _finish_tag, _blend_mode_tag = _spec_sculpt_payload_finish()

        payload = {
            "success": True,
            "seed": seed,
            "chromatic_shift": chromatic,
            "iracing_id": iracing_id,
            "car_prefix": car_prefix,
            "use_custom_number": use_custom_number,
            "original_resolution": [int(orig_hw[1]), int(orig_hw[0])],
            "working_resolution": [int(final_hw[1]), int(final_hw[0])],
            "warnings": warnings,
            "previews": previews,
            "sculpt": {
                "seed_requested": seed,
                "seed_effective": effective_seed,
                "finish_id": _finish_tag,
                "blend_mode": _blend_mode_tag,
                "fusion_mix": fusion_pass,
                "preset_stack": [{"id": a, "weight": round(b, 5)} for a, b in preset_stack_norm],
                "preset_stack_effective": [{"id": a, "weight": round(b, 5)} for a, b in (preset_stack_arg or [])],
                "catalog_stack": [{"id": a, "weight": round(b, 5)} for a, b in catalog_stack_norm],
                "catalog_stack_effective": [{"id": a, "weight": round(b, 5)} for a, b in (catalog_stack_arg or [])],
                "chromatic_shift": chromatic,
                "dark_interior_flatten": dark_interior_flatten,
                "void_metallic_max": void_metallic_max,
                "void_roughness_min": void_roughness_min,
                "void_clearcoat_max": void_clearcoat_max,
                "spec_multiplier": spec_multiplier,
                "style_notes_chars": len(style_notes),
                "mix_style_notes": mix_style_notes,
                "fusion_strategy": fusion_strategy,
                "fusion_mix_m": fusion_mix_m,
                "fusion_mix_r": fusion_mix_r,
                "fusion_mix_cc": fusion_mix_cc,
                "paint_emphasis": paint_emphasis,
                "paint_emphasis_strength": paint_emphasis_strength,
                "hue_focus_deg": hue_focus_deg,
                "hue_focus_width": hue_focus_width,
                "hue_focus_strength": hue_focus_strength,
                "spec_detail_scale": spec_detail_scale,
                "material_scale": material_scale,
                "material_impact": material_impact,
                "fast_trace": bool(fast_trace),
                "easy_color_layers": list(_easy_color_report),
                "preview_tex_size": int(final_hw[0]) if not save_tga else 2048,
                "mode": "candy_depth" if is_candy else ("fracture" if is_fracture else (sculpt_mode or "scratch")),
                "zoned_drama": _zoned_drama if is_zoned else None,
                "fracture_ignition": fracture_ignition,
                "fracture_angle_gate": fracture_angle_gate,
                "fracture_trace_strength": fracture_trace_strength,
                "fracture_calm_floor": fracture_calm_floor,
                "fracture_decorrelation": fracture_decorrelation,
                "candy_depth": candy_depth,
                "candy_flake_density": candy_flake_density,
                "candy_flake_size": candy_flake_size,
                "candy_wetness": candy_wetness,
                "candy_satin_floor": candy_satin_floor,
            },
            "channels": {
                "R": "Metallic",
                "G": "Roughness",
                "B": "Clearcoat",
                "A": "255 (spike; zone workflow supplies mask separately)",
            },
        }
        if previews_by_size is not None:
            payload["previews_by_size"] = previews_by_size
        if save_tga:
            payload["job_id"] = job_id
            payload["job_dir"] = job_dir.replace("\\", "/") if job_dir else None
            payload["paint_path"] = out_paint_tga.replace("\\", "/") if out_paint_tga else None
            payload["spec_path"] = export_path.replace("\\", "/") if export_path else None
            payload["preview_urls"] = preview_urls
            payload["download_urls"] = download_urls
        if output_dir_status is not None:
            payload["output_dir"] = output_dir_status
        if live_link_status is not None:
            payload["live_link"] = live_link_status
        if deploy_status is not None:
            payload["deploy_to_iracing"] = deploy_status
        if save_tga:
            _schedule_spec_sculpt_purge()
        return jsonify(payload)
    except Exception as e:
        logger.error(f"/api/spec-sculpt/generate error: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if temp_created_path:
            try:
                os.remove(temp_created_path)
            except Exception as _spb_ex:
                _spb_swallow('api_spec_sculpt_generate@L13706', _spb_ex)


from server_routes.file_picker_routes import register_file_picker_routes
register_file_picker_routes(
    app,
    load_config=load_config,
    logger=logger,
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
)

from server_routes.iracing_utility_routes import register_iracing_utility_routes

SCRUBBED_IRACING_GEAR_FOLDERS = {"helmet", "helmets", "suit", "suits"}


def _is_scrubbed_iracing_gear_folder(folder_name):
    """True for retired helmet/suit targets that should never be car destinations."""
    return os.path.basename(str(folder_name or "").strip()).lower() in SCRUBBED_IRACING_GEAR_FOLDERS

register_iracing_utility_routes(
    app,
    output_folder_getter=lambda: OUTPUT_FOLDER,
    scrubbed_folder_predicate=_is_scrubbed_iracing_gear_folder,
    rate_limit=_rate_limit,
    safe_int=_safe_int,
    candidate_roots_getter=_candidate_iracing_roots,
    documents_dir_getter=_iracing_documents_dir,
    ui_summary_getter=_iracing_ui_summary,
    car_package_summary_getter=_iracing_car_package_summary,
    output_job_dir_resolver=_resolve_output_job_dir,
    deploy_job_dir_to_iracing_paint=_deploy_job_dir_to_iracing_paint,
    logger=logger,
)


from server_routes.legacy_apply_finish_routes import register_legacy_apply_finish_routes
register_legacy_apply_finish_routes(
    app,
    engine_getter=lambda: engine,
    output_folder_getter=lambda: OUTPUT_FOLDER,
    load_config=load_config,
    logger=logger,
)


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


# [SPB-PROJECTS 2026-08-21] SPB Layered Workflow project files (.spbproj)
from server_routes.project_routes import register_project_routes
register_project_routes(
    app,
    logger=logger,
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
)

from server_routes.shokk_routes import register_shokk_routes
register_shokk_routes(
    app,
    manager_getter=_get_shokk_manager,
    output_folder_getter=lambda: OUTPUT_FOLDER,
    spb_version_getter=lambda: getattr(CFG, 'VERSION', '5.0.0'),
    logger=logger,
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
)

# ================================================================
# PHOTOSHOP LAYER EXPORT (#21)
# ================================================================
from server_routes.psd_layer_export_routes import register_psd_layer_export_routes
register_psd_layer_export_routes(
    app,
    output_folder_getter=lambda: OUTPUT_FOLDER,
    repair_base_overlay_pattern_reactive_payload=lambda zone: _repair_base_overlay_pattern_reactive_payload(zone),
    convert_zone_keys=lambda zone: _convert_zone_keys(zone),
    apply_paint_recolor=lambda paint_file, recolor_rules, job_dir: apply_paint_recolor(paint_file, recolor_rules, job_dir),
    decode_rle_mask_payload=lambda payload, label, **kwargs: _decode_rle_mask_payload(payload, label, **kwargs),
    decode_source_layer_rgb_payload=lambda payload, label, **kwargs: _decode_source_layer_rgb_payload(payload, label, **kwargs),
    image_shape_getter=lambda path, label: _image_rle_shape(path, label),
    max_zones_per_request=MAX_ZONES_PER_REQUEST,
    build_multi_zone=lambda *args, **kwargs: __import__('shokker_engine_v2').build_multi_zone(*args, **kwargs),
    logger=logger,
)

from server_routes.spec_channel_export_routes import register_spec_channel_export_routes
register_spec_channel_export_routes(
    app,
    output_folder_getter=lambda: OUTPUT_FOLDER,
    shokk_manager_getter=_get_shokk_manager,
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
    logger=logger,
)

from server_routes.default_asset_routes import register_default_asset_routes
register_default_asset_routes(
    app,
    default_asset_filenames=DEFAULT_ASSET_FILENAMES,
    default_asset_path=_default_asset_path,
    output_folder=OUTPUT_FOLDER,
    engine=engine,
)


# ================================================================
# MAIN
# ================================================================


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
        except Exception as _spb_ex:
            _spb_swallow('_load_custom_finishes@L13847', _spb_ex)
    return []


def _save_custom_finishes(finishes):
    """Save custom finishes list to JSON file."""
    with open(_CUSTOM_FINISHES_PATH, 'w', encoding='utf-8') as f:
        json.dump(finishes, f, indent=2, ensure_ascii=False)


# [2026-09-05 RETIRED LEDGER] Finish Mixer / custom finishes SCRAPPED by the owner
# ("we scrapped that part of the app"). The routes are no longer registered; the module
# server_routes/custom_finish_routes.py stays on disk, inert, for the archaeology.
# scripts/retired_catalog.json feature=finish_mixer; gate: scripts/spb_retired_gate.py

_USER_IMPORTS_DIR = os.environ.get('SPB_USER_IMPORTS_DIR') or os.path.join(
    os.environ.get('APPDATA', os.path.expanduser('~')),
    'ShokkerPaintBooth',
    'user_imports',
)
if not _external_write_denial(_USER_IMPORTS_DIR, "user-import-storage-init"):
    os.makedirs(_USER_IMPORTS_DIR, exist_ok=True)
os.environ.setdefault('SPB_USER_IMPORTS_DIR', _USER_IMPORTS_DIR)

from server_routes.user_import_routes import register_user_import_routes
register_user_import_routes(
    app,
    engine_getter=lambda: engine,
    finish_catalog_cache_clear=_finish_catalog_cache['clear'],
    logger=logger,
    external_write_guard=lambda path, operation: _external_write_denial(path, operation),
)

from server_routes.guest_designer_routes import register_guest_designer_routes
register_guest_designer_routes(app, logger=logger)

# [SPB-AI 2026-09-30] OPTIONAL AI copilot: buyer-supplied OpenRouter key, held only by this server (DPAPI-encrypted), local origins only.
from server_routes.ai_copilot_routes import register_ai_copilot_routes
register_ai_copilot_routes(app, logger=logger)
from server_routes.mcp_bridge_routes import register_mcp_bridge_routes
register_mcp_bridge_routes(app, logger=logger)
from server_routes.ai_car_routes import register_ai_car_routes
register_ai_car_routes(app, logger=logger)
from server_routes.support_routes import register_support_routes
from server_routes.trace_routes import register_trace_routes
register_support_routes(app, logger=logger, output_folder=OUTPUT_FOLDER)  # output_folder: "Show my files" opens a render's job folder when no iRacing folder is set (2026-10-04)
register_trace_routes(app, logger=logger)

if not _external_write_denial(_USER_IMPORTS_DIR, "user-import-inbox-startup"):
    try:
        from engine.paint_v2.user_imports_inbox import process_inbox
        from engine.paint_v2.user_imports import sync_registry as _sync_user_imports

        _inbox_imported = process_inbox()
        if _inbox_imported:
            _n = _sync_user_imports(engine.MONOLITHIC_REGISTRY, engine.PATTERN_REGISTRY)
            _finish_catalog_cache['clear']()
            logger.info(f"[user-imports] Inbox startup: imported {len(_inbox_imported)} finish(es), {_n} active")
    except Exception as _inbox_err:
        logger.debug(f"[user-imports] Inbox startup skipped: {_inbox_err}")


# [2026-09-05 RETIRED LEDGER] Finish Mixer preview routes (/api/mix-preview, /api/mix-paint-preview)
# no longer registered -- feature scrapped by the owner; see scripts/retired_catalog.json.

from server_routes.validation_routes import register_validation_routes
register_validation_routes(
    app,
    validate_path_safe=_validate_path_safe,
    max_zones_per_request=MAX_ZONES_PER_REQUEST,
    logger=logger,
)

# ================================================================
# HARDENED UTILITY ENDPOINTS ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â added in v6.2 hardening pass.
# Read-only diagnostics + safe maintenance. Prefixed /api/ so they
# do not collide with any UI / static routes.
# ================================================================

from server_routes.finish_lookup_routes import register_finish_lookup_routes
_finish_meta_cache_clear = register_finish_lookup_routes(
    app,
    engine_getter=lambda: engine,
    id_to_display_name=id_to_display_name,
    logger=logger,
)

from server_routes.spec_result_support import normalize_spec_result_to_rgba as _normalize_spec_result_to_rgba

from server_routes.finish_viewer_render_routes import register_finish_viewer_render_routes
register_finish_viewer_render_routes(
    app,
    engine_getter=lambda: engine,
    rate_limit=_rate_limit,
    safe_int=_safe_int,
    swatch_display_color=_swatch_display_color,
    invoke_monolithic_spec_fn=_invoke_monolithic_spec_fn,
    normalize_spec_result_to_rgba=_normalize_spec_result_to_rgba,
    logger=logger,
)

# Sun Sweep — angle-flash relight preview (2026-06-19). Renders any finish to paint+spec via the same
# unified path and sweeps a virtual sun across it; returns base64 frames (+ optional hero GIF).
from server_routes.sun_sweep_routes import register_sun_sweep_routes
register_sun_sweep_routes(
    app,
    engine_getter=lambda: engine,
    invoke_monolithic_spec_fn=_invoke_monolithic_spec_fn,
    normalize_spec_result_to_rgba=_normalize_spec_result_to_rgba,
    logger=logger,
)
from server_routes.job_cleanup import auto_cleanup_old_jobs, start_background_janitor
start_background_janitor(
    output_folder=OUTPUT_FOLDER,
    temp_folder=SPB_TEMP_FOLDER,
    render_stats=_render_stats,
    render_stats_lock=_render_stats_lock,
)


if __name__ == '__main__':
    from server_routes.server_bootstrap import run_local_server
    run_local_server(
        app=app,
        server_dir=SERVER_DIR,
        load_config=load_config,
        engine=engine,
        gpu_info=gpu_info,
        finish_catalog_cache=_finish_catalog_cache,
        logger=logger,
        auto_cleanup_old_jobs=auto_cleanup_old_jobs,
        output_folder=OUTPUT_FOLDER,
        spb_version=SPB_VERSION,
        engine_version=SPB_ENGINE_VERSION,
        build_id=SPB_BUILD_ID,
    )
