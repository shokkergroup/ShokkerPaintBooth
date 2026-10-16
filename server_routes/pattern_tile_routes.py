"""[TICKETS-4 2026-10-10 item 7] POST /api/render-pattern-tile - a seamless pattern tile for the canvas Pattern Brush.

Why: paint-booth-3-canvas.js loadPatternBrush() has always POSTed {pattern, size} here, but the route never existed, so every pick of
a brush pattern 404-ed and fell back to the client's procedural tile (PORT-W5B). This adds the route, built like the swatch routes
(server_routes/swatch_routes.py ``/swatch/pattern/<id>``): the engine pattern's own ``texture_fn`` rendered at ``size`` px (default 256),
tinted with the pattern's swatch colour, then made seamless (the brush tiles it across the whole 2048 canvas by modulo).

Request : JSON ``{"pattern": "<engine PATTERN_REGISTRY id>", "size": 256}``  (size clamped to 32..512)
Response: 200 ``{"image": "data:image/png;base64,...", "pattern": "<engine id>", "size": 256, "seamless_fix": true|false}``
          404 ``{"error": ...}`` for an id the engine does not know (the page then keeps its procedural tile, as before)
          404 also for an engine id that has no tile renderer; 500 when the renderer itself fails (same page fallback)

The six built-in Pattern Brush names (carbon, metal_flake, crosshatch, brushed_metal, canvas_weave, noise) are NOT served from here: the page keeps its own
tuned tiles for them (PORT-W5B, paint-booth-3-canvas.js loadPatternBrush) and no longer asks the server. This route is for engine pattern ids.
No disk writes. In-memory LRU of 48 tiles. Kill switch: env SPB_T4_OFF=1 / SPB_T4_7_OFF=1 -> the route answers 404 like before.
"""
import base64
import inspect
import io
import os
import re
import threading
from collections import OrderedDict

_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,96}$")
_CACHE = OrderedDict()
_CACHE_MAX = 48
_LOCK = threading.Lock()
_STATS = {"requests": 0, "ok": 0, "not_found": 0, "errors": 0, "cache_hits": 0}


def _off():
    for k in ("SPB_T4_OFF", "SPB_T4_7_OFF"):
        if str(os.environ.get(k, "")).strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def _seamless(pv, np):
    """Return (array, fixed). Leaves a tile alone when its wrap-around seam is no rougher than the tile's own pixel-to-pixel detail;
    otherwise cross-fades it with a half-shifted copy of itself through a cosine window (0 at the edges, 1 in the middle), the standard
    wrap-blend, so the tile repeats without a visible seam."""
    h, w = pv.shape[:2]
    p = pv if pv.ndim == 2 else pv.mean(axis=2)
    inner = (np.abs(np.diff(p, axis=1)).mean() + np.abs(np.diff(p, axis=0)).mean()) / 2.0 + 1e-6
    seam = (np.abs(p[:, 0] - p[:, -1]).mean() + np.abs(p[0, :] - p[-1, :]).mean()) / 2.0
    if seam <= inner * 1.6:
        return pv, False
    wx = np.sin(np.linspace(0.0, np.pi, w, dtype=np.float32)) ** 2
    wy = np.sin(np.linspace(0.0, np.pi, h, dtype=np.float32)) ** 2
    win = np.outer(wy, wx).astype(np.float32)
    if pv.ndim == 3:
        win = win[:, :, None]
    shifted = np.roll(np.roll(pv, h // 2, axis=0), w // 2, axis=1)
    return pv * win + shifted * (1.0 - win), True


def _render_tile(engine, pid, size):
    import numpy as np
    from PIL import Image

    reg = engine.PATTERN_REGISTRY[pid]
    tex_fn = reg.get("texture_fn")
    if tex_fn is None:
        raise RuntimeError("pattern has no texture renderer")
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    n_params = len(inspect.signature(tex_fn).parameters)
    if n_params >= 4:
        tex = tex_fn(shape, mask, 42, 1.0)
    elif n_params >= 2:
        tex = tex_fn(shape, 42)
    else:
        tex = tex_fn(shape)
    if isinstance(tex, dict):
        pv = tex.get("pattern_val", np.zeros(shape, dtype=np.float32))
        m_pat, r_pat = tex.get("M_pattern"), tex.get("R_pattern")
    else:
        pv = tex if isinstance(tex, np.ndarray) else np.zeros(shape, dtype=np.float32)
        m_pat = r_pat = None
    pv = np.asarray(pv, dtype=np.float32)
    if pv.shape[:2] != shape:
        img = Image.fromarray((np.clip(pv if pv.ndim == 2 else pv.mean(axis=2), 0, 1) * 255).astype(np.uint8))
        pv = np.asarray(img.resize(shape, Image.LANCZOS), dtype=np.float32) / 255.0
    if pv.ndim == 3:
        pv = pv.mean(axis=2)
    tint = reg.get("_swatch_rgb") or (0.62, 0.66, 0.74)
    tr, tg, tb = tint
    if m_pat is not None and r_pat is not None:
        m_pat = np.asarray(m_pat, dtype=np.float32)
        r_pat = np.asarray(r_pat, dtype=np.float32)
        m_p = np.clip(m_pat, 0, 1) if m_pat.shape == shape else np.clip(pv, 0, 1)
        r_p = np.clip(r_pat, 0, 1) if r_pat.shape == shape else np.clip(1.0 - pv, 0, 1)
        lum = m_p * 0.6 + (1.0 - r_p) * 0.4
        base = np.stack([lum * tr + 0.10, lum * tg + 0.08, lum * tb + 0.12], axis=2)
    else:
        lum = np.clip(pv, 0, 1)
        base = np.stack([lum * tr * 0.8 + 0.12, lum * tg * 0.8 + 0.10, lum * tb * 0.8 + 0.14], axis=2)
    base = np.clip(base, 0, 1).astype(np.float32)
    base, fixed = _seamless(base, np)
    out = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8), "RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"), fixed


def register_pattern_tile_routes(app, *, engine, logger=None):
    from flask import jsonify, request

    @app.route("/api/render-pattern-tile", methods=["POST"])
    def render_pattern_tile():
        _STATS["requests"] += 1
        if _off():
            return jsonify({"error": "pattern tiles are switched off"}), 404
        body = request.get_json(silent=True) or {}
        name = str(body.get("pattern") or "").strip()
        try:
            size = int(body.get("size") or 256)
        except (TypeError, ValueError):
            size = 256
        size = max(32, min(512, size))
        if not _ID_RE.match(name):
            _STATS["not_found"] += 1
            return jsonify({"error": "pattern name missing or invalid"}), 404
        pid = name
        eng = engine() if callable(engine) else engine
        if pid not in getattr(eng, "PATTERN_REGISTRY", {}):
            _STATS["not_found"] += 1
            return jsonify({"error": "unknown pattern: %s" % name}), 404
        key = (pid, size)
        with _LOCK:
            hit = _CACHE.get(key)
            if hit is not None:
                _CACHE.move_to_end(key)
        if hit is not None:
            _STATS["cache_hits"] += 1
            image, fixed = hit
        else:
            if not eng.PATTERN_REGISTRY[pid].get("texture_fn"):
                _STATS["not_found"] += 1
                return jsonify({"error": "pattern has no tile renderer: %s" % name}), 404
            try:
                image, fixed = _render_tile(eng, pid, size)
            except Exception as e:  # the page keeps its own tile
                _STATS["errors"] += 1
                if logger:
                    logger.error("pattern tile %s: %s", pid, e)
                return jsonify({"error": "pattern tile failed: %s" % e}), 500
            with _LOCK:
                _CACHE[key] = (image, fixed)
                while len(_CACHE) > _CACHE_MAX:
                    _CACHE.popitem(last=False)
        _STATS["ok"] += 1
        return jsonify({"image": image, "pattern": pid, "size": size, "seamless_fix": bool(fixed)})

    @app.route("/api/render-pattern-tile/stats", methods=["GET"])
    def render_pattern_tile_stats():
        return jsonify(dict(_STATS, cached=len(_CACHE)))
