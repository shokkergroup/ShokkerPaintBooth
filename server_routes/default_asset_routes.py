"""Default starter asset routes for Shokker Paint Booth.

These first-launch helpers are kept out of server.py so startup/workflow checks
can be inspected without reading the full server monolith.
"""

from __future__ import annotations

import os

from flask import jsonify, request, send_file


def register_default_asset_routes(
    app,
    *,
    default_asset_filenames,
    default_asset_path,
    output_folder,
    engine,
) -> None:
    """Register packaged default asset and blank canvas endpoints."""

    @app.route('/api/default-assets', methods=['GET'])
    def api_default_assets():
        """Return packaged starter-source paths for first launch and blank canvas."""
        try:
            assets = {key: default_asset_path(name) for key, name in default_asset_filenames.items()}
            missing = [key for key, path in assets.items() if not path]
            return jsonify({
                "ok": not missing,
                "assets": assets,
                "missing": missing,
            }), 200 if not missing else 500
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route('/api/blank-canvas', methods=['GET'])
    def api_blank_canvas():
        """Return a flat TGA suitable as a blank starting canvas."""
        try:
            import numpy as np

            w = max(64, min(4096, int(request.args.get('width', 2048))))
            h = max(64, min(4096, int(request.args.get('height', 2048))))
            color_hex = request.args.get('color', 'ffffff').lstrip('#')
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)

            canvas = np.full((h, w, 3), [r, g, b], dtype=np.uint8)
            tga_path = os.path.join(output_folder, "blank_canvas.tga")
            os.makedirs(output_folder, exist_ok=True)
            engine.write_tga_24bit(tga_path, canvas)
            if request.args.get('mode', '').lower() == 'json':
                return jsonify({
                    "ok": os.path.isfile(tga_path),
                    "path": tga_path,
                    "width": w,
                    "height": h,
                    "color": color_hex,
                })
            return send_file(tga_path, mimetype='image/tga', download_name='blank_canvas.tga', as_attachment=True)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
