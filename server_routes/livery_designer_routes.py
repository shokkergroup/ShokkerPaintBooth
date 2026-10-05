"""PROMPT-TO-LIVERY route — MEGA FEATURE 1.

Exposes ONE additive endpoint:

    POST /api/design-from-prompt
        {"prompt": "...", "seed": 51?,
         "image": "<data-uri|base64>"?,    # the LOADED paint (preferred)
         "paint_file": "<server path>"?,   # OR a server-readable paint path
         "car_colors": [[r,g,b], ...]?}    # OR pre-extracted dominant colors
        -> {"ok": true, "zones": [...], "explanation": "...", "meta": {...}}

The heavy lifting is in ``engine/livery_designer.py`` (pure local parse, no
external LLM). This module is a thin, flag-guarded wrapper: it never mutates
global state and adds no behavior unless explicitly registered, so with the
feature unwired the app behaves exactly as today.

THE COVERAGE FIX (2026-06-13): when the client posts the LOADED paint (the live
composite raster the renderer uses, same source Shokker-ize sends), this route
extracts its dominant colors and passes them as ``car_colors`` so the design's
finishes are MAPPED onto the car's real regions — the car actually transforms.
With no paint posted the call is byte-for-byte the old palette-selector behavior.

Register from server.py (do NOT call build_multi_zone here — the client applies
the returned zones to window.zones and renders through the existing path)::

    from server_routes.livery_designer_routes import register_livery_designer_routes
    register_livery_designer_routes(app, logger=logger)
"""
from __future__ import annotations

import base64
import os
import traceback
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def register_livery_designer_routes(app, *, logger=None, **_kw) -> None:
    """Register the prompt-to-livery endpoint. Additive + import-safe.

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

    def _design(prompt: str, seed, car_colors=None):
        # Import lazily so a registration failure can never break server boot.
        try:
            from engine.livery_designer import design_from_prompt
        except Exception:  # pragma: no cover - fall back to top-level import
            from livery_designer import design_from_prompt  # type: ignore
        # car_colors is optional + backward-compatible (older engine builds that
        # lack the param still work via the legacy call).
        try:
            return design_from_prompt(prompt, seed=seed, car_colors=car_colors)
        except TypeError:  # pragma: no cover - engine predates car_colors
            return design_from_prompt(prompt, seed=seed)

    def _extract_dominant(data):
        """Best-effort: turn the posted LOADED paint into dominant colors.

        Accepts (priority order): an already-extracted ``car_colors`` list, a
        base64/data-uri ``image`` (the live composite the client posts), or a
        server-readable ``paint_file`` path. Returns a list for ``car_colors`` or
        None. NEVER raises — a failure here just falls back to the legacy
        palette-selector design (the feature degrades, it never breaks).
        """
        try:
            # 1) caller already did the extraction (e.g. client-side k-means).
            cc = data.get("car_colors")
            if isinstance(cc, list) and cc:
                return cc

            try:
                from engine.livery_designer import extract_dominant_colors
            except Exception:  # pragma: no cover
                from livery_designer import extract_dominant_colors  # type: ignore

            import io
            import numpy as np
            from PIL import Image

            # 2) base64 / data-uri image (the live composite raster).
            b64 = data.get("image") or data.get("image_base64") or data.get("paint_base64")
            if isinstance(b64, str) and b64.strip():
                s = b64.strip()
                if s.lower().startswith("data:") and "," in s:
                    s = s.split(",", 1)[1]
                s = s.replace("\n", "").replace("\r", "").replace(" ", "")
                raw = base64.b64decode(s, validate=False)
                arr = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"), dtype=np.uint8)
                return extract_dominant_colors(arr, max_colors=5)

            # 3) server-readable on-disk paint path.
            path = data.get("paint_file")
            if isinstance(path, str) and path.strip():
                p = path.strip().strip('"')
                if os.path.isfile(p):
                    arr = np.asarray(Image.open(p).convert("RGB"), dtype=np.uint8)
                    return extract_dominant_colors(arr, max_colors=5)
        except Exception as e:  # noqa: BLE001 - degrade gracefully
            try:
                log.warning(f"/api/design-from-prompt dominant-color extract skipped: {e}")
            except Exception as _spb_ex:
                _spb_swallow('_extract_dominant@L111', _spb_ex)
        return None

    @app.route("/api/design-from-prompt", methods=["POST"])
    def design_from_prompt_route():  # noqa: D401
        try:
            data = request.get_json(silent=True) or {}
            prompt = data.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                return jsonify({"ok": False,
                                "error": "body needs a non-empty 'prompt' string"}), 400
            prompt = prompt[:2000]  # hard cap — this is a local parser, no LLM cost
            seed = data.get("seed", 51)
            try:
                seed = int(seed)
            except (TypeError, ValueError):
                seed = 51

            car_colors = _extract_dominant(data)
            result = _design(prompt, seed, car_colors=car_colors)
            zones = result.get("zones", [])
            return jsonify({
                "ok": True,
                "prompt": prompt,
                "seed": seed,
                "zones": zones,
                "zone_count": len(zones),
                "car_mapped": bool(result.get("_meta", {}).get("car_mapped")),
                "explanation": result.get("explanation", ""),
                "meta": result.get("_meta", {}),
            })
        except Exception as e:  # noqa: BLE001
            try:
                log.error(f"/api/design-from-prompt failed: {e}\n{traceback.format_exc()}")
            except Exception as _spb_ex:
                _spb_swallow('design_from_prompt_route@L146', _spb_ex)
            return jsonify({"ok": False, "error": str(e)}), 500
