"""Static asset and thumbnail routes for Shokker Paint Booth."""

import os

from flask import jsonify, request, send_file


def register_asset_routes(app, *, server_dir, bundle_dir, thumbnail_dir):
    """Register favicon, thumbnail, and JS/CSS/static asset routes."""

    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    @app.route('/thumbnails/<path:filename>')
    def serve_thumbnail(filename):
        """Serve pre-baked thumbnails directly as static files."""
        if ".." in filename.replace("\\", "/").split("/"):
            return jsonify({"error": "invalid_path"}), 400
        thumb_path = os.path.join(thumbnail_dir, filename)
        if os.path.exists(thumb_path):
            resp = send_file(thumb_path, mimetype='image/png', conditional=True)
            resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            return resp
        return jsonify({"error": "thumbnail_not_found", "path": filename}), 404

    @app.route('/<path:filename>')
    def serve_static_assets(filename):
        """Serve JS/CSS/image assets from the server or bundle directory."""
        # [SPB SPEED-TUNEUP 2026-08-30] no-cache + conditional instead of
        # no-store: browser still revalidates every load (never stale), but an
        # unchanged file 304s instead of re-downloading. See server_v5.py
        # serve_static_assets for the measured 21s-boot rationale.
        if filename.endswith(('.js', '.css', '.png', '.svg', '.ico')):
            for candidate_dir in [server_dir, bundle_dir]:
                fpath = os.path.join(candidate_dir, filename)
                if os.path.exists(fpath):
                    resp = send_file(fpath, conditional=True)
                    if filename.endswith(('.js', '.css')):
                        resp.headers['Cache-Control'] = 'no-cache'
                    return resp
        return jsonify({"error": "not_found", "path": request.path}), 404
