"""Custom finish mixer preview routes for Shokker Paint Booth."""

from __future__ import annotations

import base64
import io
import re
import traceback

from flask import jsonify, request


def _normalize_weights(weights):
    weight_sum = sum(weights)
    if weight_sum > 0:
        return [w / weight_sum for w in weights]
    return [1.0 / len(weights)] * len(weights)


def register_custom_finish_mixer_routes(
    app,
    *,
    engine_getter,
    render_swatch_bytes,
    logger,
) -> None:
    """Register custom finish mixer preview routes."""

    @app.route('/api/mix-preview', methods=['POST'])
    def api_mix_preview():
        """Generate a 256x256 preview of blended spec channels."""
        logger.info("[mix-preview] Mix preview requested")
        try:
            data = request.get_json(force=True)
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            finish_ids = data.get('finish_ids', [])
            weights = data.get('weights', [])
            try:
                seed = int(data.get('seed', 51))
            except (TypeError, ValueError):
                return jsonify({"error": "seed must be an integer"}), 400

            if len(finish_ids) < 2 or len(finish_ids) > 3:
                return jsonify({"error": "Need 2-3 finish_ids"}), 400
            if len(finish_ids) != len(weights):
                return jsonify({"error": "finish_ids and weights must match in length"}), 400

            from engine.compose import mix_finishes
            import numpy as np
            from PIL import Image

            engine = engine_getter()
            shape = (256, 256)
            mask = np.ones(shape, dtype=np.float32)
            spec = mix_finishes(
                shape,
                mask,
                seed,
                1.0,
                finish_ids,
                weights,
                monolithic_registry=engine.MONOLITHIC_REGISTRY,
            )

            preview = np.zeros((256, 256, 3), dtype=np.uint8)
            preview[:, :, 0] = spec[:, :, 2]
            preview[:, :, 1] = spec[:, :, 1]
            preview[:, :, 2] = spec[:, :, 0]

            img = Image.fromarray(preview, 'RGB')
            buf = io.BytesIO()
            img.save(buf, format='PNG', optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode('ascii')
            return jsonify({"image": f"data:image/png;base64,{b64}"})
        except Exception as e:
            logger.error(f"[mix-preview] Error: {e}")
            logger.error(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    @app.route('/api/mix-paint-preview', methods=['POST'])
    def api_mix_paint_preview():
        """Generate a split paint/spec preview for custom finish blends."""
        try:
            data = request.get_json(force=True)
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            finish_ids = data.get('finish_ids', [])
            weights = data.get('weights', [])
            try:
                seed = int(data.get('seed', 51))
            except (TypeError, ValueError):
                return jsonify({"error": "seed must be an integer"}), 400
            color_hex = str(data.get('color', '888888')).replace('#', '').strip()
            if not re.match(r'^[0-9a-fA-F]{6}$', color_hex):
                logger.warning(f"[mix-preview] Invalid color_hex '{color_hex}', defaulting to 888888")
                color_hex = '888888'
            if len(finish_ids) < 2 or len(finish_ids) > 3 or len(finish_ids) != len(weights):
                return jsonify({"error": "Need 2-3 matching finish_ids and weights"}), 400

            import numpy as np
            from PIL import Image

            engine = engine_getter()
            size = 128
            weights = _normalize_weights(weights)

            base_registry = getattr(engine, 'BASE_REGISTRY', {})
            mono_registry = getattr(engine, 'MONOLITHIC_REGISTRY', {})
            for fid in finish_ids:
                if fid not in base_registry and fid not in mono_registry:
                    return jsonify({
                        "error": "mix_paint_preview_failed",
                        "message": f"Unknown mix preview finish: {fid}",
                        "finish_id": fid,
                    }), 404

            paint_blend = np.zeros((size, size, 3), dtype=np.float32)
            for fid, wt in zip(finish_ids, weights):
                swatch_bytes = None
                if fid in mono_registry:
                    try:
                        swatch_bytes = render_swatch_bytes('monolithic', fid, color_hex, size, seed)
                    except Exception as e:
                        return jsonify({
                            "error": "mix_paint_preview_failed",
                            "message": f"Mix paint preview swatch renderer failed [{fid}]: {e}",
                            "finish_id": fid,
                        }), 500
                if not swatch_bytes and fid in base_registry:
                    try:
                        swatch_bytes = render_swatch_bytes('base', fid, color_hex, size, seed)
                    except Exception as e:
                        return jsonify({
                            "error": "mix_paint_preview_failed",
                            "message": f"Mix paint preview swatch renderer failed [{fid}]: {e}",
                            "finish_id": fid,
                        }), 500
                if not swatch_bytes:
                    return jsonify({
                        "error": "mix_paint_preview_failed",
                        "message": f"Mix paint preview swatch renderer returned no image [{fid}]",
                        "finish_id": fid,
                    }), 500

                try:
                    swatch_img = Image.open(io.BytesIO(swatch_bytes)).convert('RGB')
                    swatch_arr = np.array(swatch_img).astype(np.float32) / 255.0
                    paint_blend += swatch_arr * wt
                except Exception as e:
                    return jsonify({
                        "error": "mix_paint_preview_failed",
                        "message": f"Mix paint preview swatch PNG decode failed [{fid}]: {e}",
                        "finish_id": fid,
                    }), 500

            paint_u8 = np.clip(paint_blend * 255, 0, 255).astype(np.uint8)

            from engine.compose import mix_finishes
            spec_shape = (size, size)
            mask = np.ones(spec_shape, dtype=np.float32)
            try:
                spec = mix_finishes(
                    spec_shape,
                    mask,
                    seed,
                    1.0,
                    finish_ids,
                    weights,
                    monolithic_registry=mono_registry,
                )
                spec_vis = np.zeros((size, size, 3), dtype=np.uint8)
                spec_vis[:, :, 0] = spec[:, :, 0]
                spec_vis[:, :, 1] = spec[:, :, 1]
                spec_vis[:, :, 2] = spec[:, :, 2]
                spec_info = {
                    "M_avg": round(float(np.mean(spec[:, :, 0])), 1),
                    "R_avg": round(float(np.mean(spec[:, :, 1])), 1),
                    "CC_avg": round(float(np.mean(spec[:, :, 2])), 1),
                }
            except Exception as e:
                logger.warning(f"[mix-preview] spec blend failed: {e}")
                return jsonify({
                    "error": "mix_paint_preview_failed",
                    "message": f"Mix paint preview spec renderer failed: {e}",
                }), 500

            combined = np.zeros((size, size * 2 + 4, 3), dtype=np.uint8)
            combined[:, :size, :] = paint_u8
            combined[:, size:size + 4, :] = 60
            combined[:, size + 4:, :] = spec_vis

            img = Image.fromarray(combined, 'RGB')
            buf = io.BytesIO()
            img.save(buf, format='PNG', optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode('ascii')
            return jsonify({"image": f"data:image/png;base64,{b64}", "spec_summary": spec_info})
        except Exception as e:
            logger.error(f"[mix-paint-preview] Error: {e}")
            logger.error(traceback.format_exc())
            return jsonify({"error": str(e)}), 500
