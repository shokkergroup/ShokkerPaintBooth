"""PHOTO-TO-LIVERY route — bonus MEGA FEATURE (image counterpart to Prompt-to-Livery).

Exposes ONE additive endpoint:

    POST /api/design-from-image
        multipart/form-data with an ``image`` file part   (preferred), OR
        JSON  {"image_base64": "data:image/png;base64,..." | "<base64>", "seed": 51?}
        -> {"ok": true, "zones": [...], "explanation": "...", "palette": [...], "meta": {...}}

The heavy lifting is in ``engine/photo_livery.py`` (pure local palette + mood
extraction, then it reuses ``engine/livery_designer.design_from_prompt`` for the
actual zone assembly — NO external LLM, NO new heavy dep).  This module is a thin,
flag-guarded wrapper: it never mutates global state and adds no behavior unless
explicitly registered, so with the feature unwired the app behaves exactly as today.

Register from server.py (mirrors livery_designer / june_audit; the client applies
the returned zones to window.zones and renders through the existing path)::

    from server_routes.photo_livery_routes import register_photo_livery_routes
    register_photo_livery_routes(app, logger=logger)
"""
from __future__ import annotations

import base64
import binascii
import traceback
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


# Hard cap so a giant upload can never wedge the local server (this is a local
# parser; a livery only needs the palette, not a full-res image).
_MAX_IMAGE_BYTES = 24 * 1024 * 1024  # 24 MB


def register_photo_livery_routes(app, *, logger=None, **_kw) -> None:
    """Register the photo-to-livery endpoint. Additive + import-safe.

    Args:
        app: the Flask app.
        logger: optional logger (falls back to a no-op if absent).
    """
    from flask import jsonify, request

    class _NullLog:
        def info(self, *a, **k):
            pass

        warning = error = debug = info

    log = logger or _NullLog()

    def _design(image_bytes: bytes, seed, car_colors=None):
        # Import lazily so a registration failure can never break server boot.
        try:
            from engine.photo_livery import design_from_image
        except Exception:  # pragma: no cover - top-level fallback
            from photo_livery import design_from_image  # type: ignore
        # car_colors optional + backward-compatible with older engine builds.
        try:
            return design_from_image(image_bytes, seed=seed, car_colors=car_colors)
        except TypeError:  # pragma: no cover - engine predates car_colors
            return design_from_image(image_bytes, seed=seed)

    def _decode_b64(raw: str) -> bytes:
        """Accept a bare base64 string or a data: URL; return raw image bytes."""
        s = (raw or "").strip()
        if s.startswith("data:"):
            comma = s.find(",")
            if comma != -1:
                s = s[comma + 1:]
        s = s.replace("\n", "").replace("\r", "").replace(" ", "")
        return base64.b64decode(s, validate=False)

    def _loaded_car_colors(request):
        """Best-effort dominant colors of the LOADED CAR PAINT (NOT the reference
        photo). The client posts the live composite as ``paint_image`` (base64 /
        data-uri) or ``paint_file`` (server path), or pre-extracts ``car_colors``.
        Returns a list or None; NEVER raises — failure just disables the coverage
        mapping so the feature degrades to the legacy photo-palette selectors.
        """
        try:
            import os as _os

            # 0) form / json sources
            form = {}
            try:
                form = request.form or {}
            except Exception:
                form = {}
            data = request.get_json(silent=True) or {}
            if not isinstance(data, dict):
                data = {}

            # 1) pre-extracted car_colors (JSON only — a list).
            cc = data.get("car_colors")
            if isinstance(cc, list) and cc:
                return cc

            try:
                from engine.livery_designer import extract_dominant_colors
            except Exception:  # pragma: no cover
                from livery_designer import extract_dominant_colors  # type: ignore

            import io as _io
            import numpy as _np
            from PIL import Image as _Image

            # 2) a second multipart file part for the loaded paint.
            try:
                pf = request.files.get("paint_image") or request.files.get("paint")
                if pf is not None and getattr(pf, "filename", ""):
                    arr = _np.asarray(_Image.open(pf.stream).convert("RGB"), dtype=_np.uint8)
                    return extract_dominant_colors(arr, max_colors=5)
            except Exception as _spb_ex:
                _spb_swallow('_loaded_car_colors@L113', _spb_ex)

            # 3) base64 / data-uri loaded paint (live composite).
            b64 = form.get("paint_image") or data.get("paint_image") or data.get("paint_base64")
            if isinstance(b64, str) and b64.strip():
                arr = _np.asarray(_Image.open(_io.BytesIO(_decode_b64(b64))).convert("RGB"), dtype=_np.uint8)
                return extract_dominant_colors(arr, max_colors=5)

            # 4) server-readable loaded paint path.
            path = form.get("paint_file") or data.get("paint_file")
            if isinstance(path, str) and path.strip():
                p = path.strip().strip('"')
                if _os.path.isfile(p):
                    arr = _np.asarray(_Image.open(p).convert("RGB"), dtype=_np.uint8)
                    return extract_dominant_colors(arr, max_colors=5)
        except Exception as e:  # noqa: BLE001
            try:
                log.warning(f"/api/design-from-image loaded-car extract skipped: {e}")
            except Exception as _spb_ex:
                _spb_swallow('_loaded_car_colors@L132', _spb_ex)
        return None

    @app.route("/api/design-from-image", methods=["POST"])
    def design_from_image_route():  # noqa: D401
        try:
            image_bytes = None
            seed = 51

            # 1) multipart file upload (preferred — no base64 bloat).
            try:
                if request.files:
                    f = request.files.get("image") or next(iter(request.files.values()), None)
                    if f is not None:
                        image_bytes = f.read()
                seed = request.form.get("seed", seed) if request.form else seed
            except Exception as _spb_ex:
                _spb_swallow('design_from_image_route@L149', _spb_ex)

            # 2) JSON body with base64 (or data URL).
            if not image_bytes:
                data = request.get_json(silent=True) or {}
                b64 = data.get("image_base64") or data.get("image") or data.get("imageData")
                if isinstance(b64, str) and b64.strip():
                    try:
                        image_bytes = _decode_b64(b64)
                    except (binascii.Error, ValueError):
                        return jsonify({"ok": False, "error": "invalid base64 image data"}), 400
                seed = data.get("seed", seed)

            if not image_bytes:
                return jsonify({
                    "ok": False,
                    "error": "send an image: multipart 'image' file part, or JSON 'image_base64'",
                }), 400
            if len(image_bytes) > _MAX_IMAGE_BYTES:
                return jsonify({"ok": False,
                                "error": f"image too large (> {_MAX_IMAGE_BYTES // (1024*1024)} MB)"}), 413

            try:
                seed = int(seed)
            except (TypeError, ValueError):
                seed = 51

            car_colors = _loaded_car_colors(request)
            result = _design(image_bytes, seed, car_colors=car_colors)
            zones = result.get("zones", [])
            return jsonify({
                "ok": True,
                "seed": seed,
                "zones": zones,
                "zone_count": len(zones),
                "car_mapped": bool(result.get("_meta", {}).get("car_mapped")),
                "explanation": result.get("explanation", ""),
                "palette": result.get("palette", []),
                "meta": result.get("_meta", {}),
            })
        except Exception as e:  # noqa: BLE001
            try:
                log.error(f"/api/design-from-image failed: {e}\n{traceback.format_exc()}")
            except Exception as _spb_ex:
                _spb_swallow('design_from_image_route@L193', _spb_ex)
            return jsonify({"ok": False, "error": str(e)}), 500
