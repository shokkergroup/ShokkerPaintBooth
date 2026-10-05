"""Pattern-only overlay layer route for Shokker Paint Booth."""

from __future__ import annotations

import io
import traceback

from flask import Response as FlaskResponse
from flask import jsonify, request


def register_pattern_layer_routes(
    app,
    *,
    pattern_registry_getter,
    load_image_pattern,
    logger,
) -> None:
    """Register pattern layer preview route."""

    @app.route('/api/pattern-layer', methods=['GET'])
    def api_pattern_layer():
        """Return the pattern texture as PNG for client overlay placement."""
        import numpy as np
        from PIL import Image as PILImage

        pattern_id = None
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
            shape = (int(h), int(w))
            mask = np.ones(shape, dtype=np.float32)
            pattern = pattern_registry_getter().get(pattern_id)
            if pattern is None:
                return jsonify({
                    "error": "pattern_layer_failed",
                    "pattern": pattern_id,
                    "message": f"Unknown pattern layer pattern: {pattern_id}",
                }), 404

            image_path = pattern.get("image_path") if isinstance(pattern, dict) else None
            texture_fn = pattern.get("texture_fn") if isinstance(pattern, dict) else None
            if image_path:
                try:
                    pv = load_image_pattern(image_path, shape, scale=scale, rotation=rotation)
                except Exception as img_err:
                    raise RuntimeError(f"Pattern layer image renderer failed [{pattern_id}]: {img_err}") from img_err
                if pv is None:
                    return jsonify({
                        "error": "pattern_layer_failed",
                        "pattern": pattern_id,
                        "message": f"Pattern layer image renderer returned no pattern [{pattern_id}]",
                    }), 500
            elif callable(texture_fn):
                try:
                    tex = texture_fn(shape, mask, seed, 1.0)
                except Exception as tex_err:
                    raise RuntimeError(f"Pattern layer texture renderer failed [{pattern_id}]: {tex_err}") from tex_err
                pv = tex.get("pattern_val") if isinstance(tex, dict) else tex
            else:
                return jsonify({
                    "error": "pattern_layer_failed",
                    "pattern": pattern_id,
                    "message": f"Pattern layer has no renderer: {pattern_id}",
                }), 500

            if pv is None:
                return jsonify({
                    "error": "pattern_layer_failed",
                    "pattern": pattern_id,
                    "message": f"Pattern layer renderer returned no pattern [{pattern_id}]",
                }), 500

            arr = (np.clip(pv, 0, 1) * 255).astype(np.uint8)
            rgba = np.stack([arr, arr, arr, np.full_like(arr, 255)], axis=-1)
            buf = io.BytesIO()
            PILImage.fromarray(rgba).save(buf, format='PNG')
            buf.seek(0)
            return FlaskResponse(
                buf.getvalue(),
                mimetype='image/png',
                headers={'Cache-Control': 'no-store'},
            )
        except Exception as e:
            logger.warning(f"/api/pattern-layer failed: {e}\n{traceback.format_exc()}")
            return jsonify({
                "error": "pattern_layer_failed",
                "pattern": pattern_id,
                "message": str(e),
            }), 500
