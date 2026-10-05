"""SHOKKER-IZE route — POST a paint image, get back the auto-generated
angle-reactive color-shift spec map (winner physics from the art's own geometry).

MEGA FEATURE 2 (owner mandate 2026-06-13). Additive + flag-guarded. This module
only READS the engine (engine.shokkerize.shokkerize) — it registers no finishes
and mutates no existing state.

Register from server.py (additive; NOT auto-registered here):

    from server_routes.shokkerize_routes import register_shokkerize_routes
    register_shokkerize_routes(app, logger=logger)

Flag guard: set env SPB_SHOKKERIZE_DISABLE=1 to register the endpoints as
disabled (503) without removing the route — lets the owner kill the feature
without a code change if anything ever misbehaves.
"""
from __future__ import annotations

import base64
import io
import os
import traceback
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def register_shokkerize_routes(app, **kw) -> None:
    """Register the Shokker-ize endpoints. kw: logger (optional)."""
    logger = kw.get("logger")

    def _log_err(msg: str) -> None:
        if logger is not None:
            try:
                logger.error(msg)
                return
            except Exception as _spb_ex:
                _spb_swallow('_log_err@L34', _spb_ex)

    def _disabled() -> bool:
        return os.environ.get("SPB_SHOKKERIZE_DISABLE", "") not in ("", "0", "false", "False")

    def _read_image_from_request(request, np_module):
        """Pull an image out of the request as HxWx3/4 uint8 RGB(A).

        Accepts, in priority order:
          - multipart file upload under key ``image`` (or ``file``)
          - JSON body ``{"image": "<data-uri or base64>"}``
          - JSON body ``{"paint_file": "<server path>"}``  (read off disk)
        Returns (rgb_uint8, source_label) or (None, error_message).
        """
        from PIL import Image as PILImage

        # 1) multipart upload
        up = None
        try:
            up = request.files.get("image") or request.files.get("file")
        except Exception:
            up = None
        if up is not None and getattr(up, "filename", ""):
            try:
                img = PILImage.open(up.stream).convert("RGB")
                return np_module.asarray(img, dtype=np_module.uint8), "upload"
            except Exception as e:  # noqa: BLE001
                return None, f"could not decode uploaded image: {e}"

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            data = {}

        # 2) base64 / data-uri in JSON. This is the PRIMARY current-paint source:
        #    the client posts the live composite canvas (PSD composite / flat
        #    canvas / edited pixels) — the same raster the renderer uses — so the
        #    REAL current paint is shokker-ized even when no .tga exists on disk.
        b64 = data.get("image")
        if isinstance(b64, str) and b64:
            try:
                if "," in b64 and b64.strip().lower().startswith("data:"):
                    b64 = b64.split(",", 1)[1]
                raw = base64.b64decode(b64)
                img = PILImage.open(io.BytesIO(raw)).convert("RGB")
                return np_module.asarray(img, dtype=np_module.uint8), "base64"
            except Exception as e:  # noqa: BLE001
                # Only hard-fail if there is no on-disk fallback to try below.
                if not (isinstance(data.get("paint_file"), str) and data.get("paint_file").strip()):
                    return None, f"could not decode base64 image: {e}"

        # 3) server-side path
        path = data.get("paint_file")
        if isinstance(path, str) and path.strip():
            p = path.strip().strip('"')
            if not os.path.isfile(p):
                return None, f"paint_file not found: {p}"
            try:
                img = PILImage.open(p).convert("RGB")
                return np_module.asarray(img, dtype=np_module.uint8), "paint_file"
            except Exception as e:  # noqa: BLE001
                return None, f"could not read paint_file: {e}"

        return None, "no image provided (send multipart 'image', JSON 'image' base64, or 'paint_file' path)"

    def _intensity_from_request(request) -> float:
        val = None
        try:
            data = request.get_json(silent=True) or {}
            if isinstance(data, dict):
                val = data.get("intensity")
        except Exception:
            val = None
        if val is None:
            try:
                val = request.form.get("intensity")
            except Exception:
                val = None
        if val is None:
            try:
                val = request.args.get("intensity")
            except Exception:
                val = None
        try:
            f = float(val)
        except (TypeError, ValueError):
            f = 1.0
        return max(0.0, min(1.0, f))

    def _preset_from_request(request) -> str:
        """Pull the look preset id (JSON / form / query). Defaults to the
        proven 'balanced' winner; unknown ids fall back inside the engine."""
        val = None
        try:
            data = request.get_json(silent=True) or {}
            if isinstance(data, dict):
                val = data.get("preset")
        except Exception:
            val = None
        if val is None:
            try:
                val = request.form.get("preset")
            except Exception:
                val = None
        if val is None:
            try:
                val = request.args.get("preset")
            except Exception:
                val = None
        if isinstance(val, str) and val.strip():
            return val.strip().lower()
        return "balanced"

    @app.route("/api/shokkerize/presets", methods=["GET"])
    def api_shokkerize_presets():
        """List the one-click look presets for the panel buttons.

        Returns ``{"success": true, "presets": [{"id","label","blurb"}, ...]}``
        in display order. Cheap + import-light (no registry boot).
        """
        from flask import jsonify

        if _disabled():
            return jsonify({"error": "shokkerize disabled (SPB_SHOKKERIZE_DISABLE)"}), 503
        try:
            from engine.shokkerize import list_presets
            return jsonify({"success": True, "presets": list_presets()})
        except Exception as e:  # noqa: BLE001
            _log_err(f"/api/shokkerize/presets failed: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/shokkerize", methods=["POST"])
    def api_shokkerize():
        """Turn the posted paint into an angle-reactive color-shift spec map.

        Returns JSON::

            {"success": true,
             "intensity": 1.0,
             "preset": "balanced",
             "width": W, "height": H,
             "stats": {"M_mean":.., "G_mean":.., "B_mean":.., "G_lane_cov":..},
             "spec_png": "data:image/png;base64,...",   # R=M G=G B=clearcoat
             "spec_tga": "data:image/x-tga;base64,..."} # same data, TGA bytes

        On bad input -> 400 with {"error": ..}; on engine failure -> 500.
        """
        from flask import jsonify, request

        if _disabled():
            return jsonify({"error": "shokkerize disabled (SPB_SHOKKERIZE_DISABLE)"}), 503

        import numpy as np

        try:
            rgb, source = _read_image_from_request(request, np)
            if rgb is None:
                return jsonify({"error": source}), 400

            intensity = _intensity_from_request(request)
            preset = _preset_from_request(request)

            from engine.shokkerize import shokkerize

            spec = shokkerize(rgb, intensity=intensity, preset=preset)  # HxWx3 uint8, R/G/B = M/G/B
            h, w = spec.shape[:2]

            M = spec[:, :, 0].astype(np.float32)
            G = spec[:, :, 1].astype(np.float32)
            B = spec[:, :, 2].astype(np.float32)
            stats = {
                "M_mean": round(float(M.mean()), 2),
                "G_mean": round(float(G.mean()), 2),
                "B_mean": round(float(B.mean()), 2),
                "G_lane_cov": round(float((G > 50).mean()), 4),
            }

            from PIL import Image as PILImage

            img = PILImage.fromarray(spec, "RGB")
            png_buf = io.BytesIO()
            img.save(png_buf, "PNG", optimize=True)
            png_b64 = base64.b64encode(png_buf.getvalue()).decode("ascii")

            tga_buf = io.BytesIO()
            img.save(tga_buf, "TGA")
            tga_b64 = base64.b64encode(tga_buf.getvalue()).decode("ascii")

            return jsonify({
                "success": True,
                "source": source,
                "intensity": intensity,
                "preset": preset,
                "width": w,
                "height": h,
                "stats": stats,
                "spec_png": f"data:image/png;base64,{png_b64}",
                "spec_tga": f"data:image/x-tga;base64,{tga_b64}",
            })
        except Exception as e:  # noqa: BLE001
            _log_err(f"/api/shokkerize failed: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500
