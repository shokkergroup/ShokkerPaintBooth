"""Custom dual color-shift preview and registration routes."""

from __future__ import annotations

import base64
import io
import traceback

from flask import jsonify, request


def register_dual_shift_routes(app, *, logger) -> None:
    """Register custom dual-shift preview and temporary finish endpoints."""

    def _norm_color(color, np_module):
        values = [float(x) for x in color]
        if any(x > 1.0 for x in values):
            values = [x / 255.0 for x in values]
        return tuple(np_module.clip(values, 0, 1))

    @app.route('/api/dual-shift-preview', methods=['POST'])
    def api_dual_shift_preview():
        """Generate a quick paint/spec preview of a custom dual color shift."""
        import numpy as np

        try:
            data = request.get_json(force=True, silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            raw_a = data.get('color_a', [255, 50, 140])
            raw_b = data.get('color_b', [255, 230, 25])
            intensity = float(data.get('shift_intensity', 1.0))
            size = int(data.get('size', 256))
            size = max(64, min(512, size))

            ca = _norm_color(raw_a, np)
            cb = _norm_color(raw_b, np)

            from engine.dual_color_shift import paint_dual_shift, spec_dual_shift

            shape = (size, size)
            mask = np.ones(shape, dtype=np.float32)
            seed = 42

            spec = spec_dual_shift(
                shape,
                mask,
                seed,
                1.0,
                color_a=ca,
                color_b=cb,
                shift_intensity=intensity,
            )

            paint = np.full((size, size, 3), 0.5, dtype=np.float32)
            bb = np.zeros(shape, dtype=np.float32)
            paint = paint_dual_shift(
                paint,
                shape,
                mask,
                seed,
                1.0,
                bb,
                color_a=ca,
                color_b=cb,
                shift_intensity=intensity,
            )

            paint_u8 = (np.clip(paint[:, :, :3], 0, 1) * 255).astype(np.uint8)
            spec_vis = np.zeros((size, size, 3), dtype=np.uint8)
            spec_vis[:, :, 0] = spec[:, :, 0]
            spec_vis[:, :, 1] = spec[:, :, 1]
            spec_vis[:, :, 2] = spec[:, :, 2]

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
        """Register a custom dual shift as a temporary monolithic finish."""
        import numpy as np

        try:
            data = request.get_json(force=True, silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            raw_a = data.get('color_a', [255, 50, 140])
            raw_b = data.get('color_b', [255, 230, 25])
            intensity = float(data.get('shift_intensity', 1.0))
            name = data.get('name', 'Custom Dual Shift')

            ca = _norm_color(raw_a, np)
            cb = _norm_color(raw_b, np)

            from engine.dual_color_shift import paint_dual_shift, spec_dual_shift
            import shokker_engine_v2 as eng

            finish_hash = hash((ca, cb, intensity)) & 0xFFFFFF
            finish_id = f"dualshift_custom_{finish_hash:06x}"

            def _spec(shape, mask, seed, sm, _ca=ca, _cb=cb, _intensity=intensity):
                return spec_dual_shift(
                    shape,
                    mask,
                    seed,
                    sm,
                    color_a=_ca,
                    color_b=_cb,
                    shift_intensity=_intensity,
                )

            def _paint(paint, shape, mask, seed, pm, bb, _ca=ca, _cb=cb, _intensity=intensity):
                return paint_dual_shift(
                    paint,
                    shape,
                    mask,
                    seed,
                    pm,
                    bb,
                    color_a=_ca,
                    color_b=_cb,
                    shift_intensity=_intensity,
                )

            if hasattr(eng, 'MONOLITHIC_REGISTRY'):
                eng.MONOLITHIC_REGISTRY[finish_id] = (_spec, _paint)
                logger.info(
                    f"Registered custom dual shift: {finish_id} ({name}) "
                    f"A={ca} B={cb} int={intensity}"
                )
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
