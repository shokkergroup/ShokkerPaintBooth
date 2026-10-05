"""Read-only validation and coverage-estimate routes."""

import os

from flask import g, jsonify, request


def register_validation_routes(app, *, validate_path_safe, max_zones_per_request, logger):
    """Register buyer-trust validation routes."""

    @app.route('/api/validate-paint-file', methods=['POST'])
    def api_validate_paint_file():
        """Validate a paint file path: existence, readability, dimensions."""
        rid = getattr(g, '_rid', '-')
        try:
            data = request.get_json(silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"valid": False, "reason": "body_must_be_json_object", "rid": rid}), 400
            raw_path = data.get('path', '')
            expect = data.get('expect_size')
            ok, normed, err = validate_path_safe(raw_path)
            if not ok:
                return jsonify({"valid": False, "reason": err, "rid": rid}), 400
            if not os.path.exists(normed):
                return jsonify({"valid": False, "reason": "file_not_found", "path": normed, "rid": rid}), 404
            if not os.path.isfile(normed):
                return jsonify({"valid": False, "reason": "not_a_regular_file", "path": normed, "rid": rid}), 400
            try:
                size_bytes = os.path.getsize(normed)
            except OSError as e:
                return jsonify({"valid": False, "reason": f"stat_failed: {e}", "rid": rid}), 500
            readable = os.access(normed, os.R_OK)
            try:
                from PIL import Image as _PIL
                with _PIL.open(normed) as img:
                    dims = [img.width, img.height]
            except Exception as e:
                return jsonify({"valid": False, "reason": f"unreadable_image: {e}", "path": normed, "rid": rid}), 400
            ok_dims = True
            if expect and isinstance(expect, list) and len(expect) == 2:
                ok_dims = bool(dims and dims[0] == int(expect[0]) and dims[1] == int(expect[1]))
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

    @app.route('/api/zone-coverage-estimate', methods=['POST'])
    def api_zone_coverage_estimate():
        """Estimate rough pixel coverage percentages for simple color zones."""
        rid = getattr(g, '_rid', '-')
        try:
            data = request.get_json(silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "body_must_be_json_object", "rid": rid}), 400
            paint_file = data.get('paint_file', '')
            zones = data.get('zones', [])
            if not zones:
                return jsonify({"error": "no_zones", "rid": rid}), 400
            if len(zones) > max_zones_per_request:
                return jsonify({
                    "error": "too_many_zones",
                    "limit": max_zones_per_request,
                    "got": len(zones),
                    "rid": rid,
                }), 400
            ok, normed, err = validate_path_safe(paint_file)
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
            result = []
            for z in zones[:max_zones_per_request]:
                color = (z.get('color') or '').lower()
                name = z.get('name') or color or 'unnamed'
                pct = 0.0
                if color == 'everything':
                    pct = 100.0
                else:
                    r, gch, b = arr[..., 0], arr[..., 1], arr[..., 2]
                    if color == 'red':
                        mask = (r > 150) & (gch < 100) & (b < 100)
                    elif color == 'green':
                        mask = (gch > 150) & (r < 100) & (b < 100)
                    elif color == 'blue':
                        mask = (b > 150) & (r < 100) & (gch < 100)
                    elif color == 'black':
                        mask = (r < 32) & (gch < 32) & (b < 32)
                    elif color == 'white':
                        mask = (r > 220) & (gch > 220) & (b > 220)
                    elif color == 'yellow':
                        mask = (r > 200) & (gch > 200) & (b < 100)
                    else:
                        mask = None
                    if mask is not None:
                        pct = round(100.0 * float(mask.sum()) / total_px, 2)
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
