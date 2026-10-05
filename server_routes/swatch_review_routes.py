"""For Review pattern swatch routes for Shokker Paint Booth."""

from __future__ import annotations

import os

from flask import Response, jsonify, request


def register_swatch_review_routes(
    app,
    *,
    review_dir_getter,
    render_pattern_swatch_from_image_path,
    logger=None,
) -> None:
    """Register For Review pattern image list and swatch preview routes."""

    def _int_arg(name, default, minimum=None, maximum=None):
        raw_value = request.args.get(name, default)
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            value = default
        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    @app.route('/api/for-review/list', methods=['GET'])
    def api_for_review_list():
        """List pattern images in the For Review folder."""
        try:
            review_dir = review_dir_getter()
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
            if logger is not None:
                logger.warning(f"For-review list error: {e}")
            return jsonify({"items": [], "error": str(e)}), 500

    @app.route('/api/swatch/review', methods=['GET'])
    def api_swatch_review():
        """Render a pattern swatch using an image from the For Review folder."""
        filename = request.args.get('image', '').strip()
        if not filename:
            return jsonify({"error": "missing image parameter"}), 400
        if os.path.basename(filename) != filename:
            return jsonify({"error": "invalid image parameter"}), 400

        review_dir = review_dir_getter()
        if not review_dir:
            return jsonify({"error": "For Review not configured"}), 500
        abs_path = os.path.join(review_dir, filename)
        if not os.path.isfile(abs_path):
            return jsonify({"error": "file not found", "image": filename}), 404

        color_hex = request.args.get('color', '888888').lstrip('#').ljust(6, '0')[:6]
        size = _int_arg('size', 64, 32, 256)
        seed = _int_arg('seed', 42)
        try:
            png_bytes = render_pattern_swatch_from_image_path(abs_path, color_hex, size, seed)
            return Response(
                png_bytes,
                mimetype='image/png',
                headers={'Cache-Control': 'no-store, no-cache, must-revalidate', 'Pragma': 'no-cache'},
            )
        except Exception as e:
            if logger is not None:
                logger.warning(f"Review swatch error [{filename}]: {e}")
            return jsonify({
                "error": "review_swatch_render_failed",
                "image": filename,
                "message": str(e),
            }), 500
