"""Photoshop round-trip import helper routes for Shokker Paint Booth."""

from __future__ import annotations

import json
import os
import shutil
import time

from flask import jsonify, request, send_file
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def _safe_join(root, subpath):
    """Join root with subpath while preventing .. escapes."""
    if ".." in subpath or subpath.startswith("/"):
        return None
    root = os.path.normpath(root)
    full = os.path.normpath(os.path.join(root, subpath))
    try:
        real_root = os.path.realpath(root)
        real_full = os.path.realpath(full)
        if real_full != real_root and not real_full.startswith(real_root + os.sep):
            return None
    except OSError:
        return None
    return full


def _coerce_user_dir(raw):
    """If a USER-pasted path is a file (or its parent is a dir), return the
    containing folder; else return the normalized value unchanged.

    Mirrors server._coerce_output_dir's lenience but never returns None so the
    caller's existing isdir() 404 still fires for a truly bad path. A pasted
    ``...\\some_file.tga`` Exchange path resolves to its folder instead of 404.
    """
    if not raw:
        return raw
    p = os.path.normpath(str(raw).strip().strip('"').strip("'"))
    if os.path.isdir(p):
        return p
    parent = os.path.dirname(p)
    if parent and os.path.isdir(parent):
        return parent
    return p


def _is_primary_spec_tga(filename):
    lowered = filename.lower()
    return (
        lowered.endswith(".tga")
        and "spec" in lowered
        and "metallic" not in lowered
        and "roughness" not in lowered
        and "clearcoat" not in lowered
        and "mask" not in lowered
    )


def register_photoshop_import_routes(
    app, *, exchange_root_getter, output_folder, require_internal_request, logger
) -> None:
    """Register Photoshop import/list helper endpoints."""

    def _exchange_root_from_args():
        user_val = (request.args.get("exchange_folder") or "").strip()
        if user_val:
            allowed, error = require_internal_request()
            if not allowed:
                return None, error
            # User-pasted: accept a file path and resolve to its folder.
            return _coerce_user_dir(user_val), None
        return os.path.normpath(exchange_root_getter()), None

    @app.route('/api/photoshop-import-list', methods=['GET'])
    def photoshop_import_list():
        exchange_root, error = _exchange_root_from_args()
        if error:
            return jsonify({"error": error}), 403
        if not os.path.isdir(exchange_root):
            return jsonify({"error": "Exchange folder not found."}), 404
        subpath = (request.args.get("subpath") or "").strip().replace("\\", "/").strip("/")
        list_dir = exchange_root if not subpath else _safe_join(exchange_root, subpath)
        if list_dir is None or not os.path.isdir(list_dir):
            return jsonify({"subfolders": [], "files": []})
        subfolders = []
        files = []
        for name in sorted(os.listdir(list_dir)):
            full = os.path.join(list_dir, name)
            if os.path.isdir(full):
                subfolders.append(name)
            elif name.lower().endswith(".tga"):
                files.append(name)
        return jsonify({"subfolders": subfolders, "files": files})

    @app.route('/api/photoshop-import-file', methods=['GET'])
    def photoshop_import_file():
        exchange_root, error = _exchange_root_from_args()
        if error:
            return jsonify({"error": error}), 403
        if not os.path.isdir(exchange_root):
            return jsonify({"error": "Exchange folder not found."}), 404
        path_arg = (request.args.get("path") or "").strip().replace("\\", "/").lstrip("/")
        if not path_arg:
            return jsonify({"error": "Missing path."}), 400
        full_path = _safe_join(exchange_root, path_arg)
        if full_path is None or not os.path.isfile(full_path):
            return jsonify({"error": "File not found or path invalid."}), 404
        return send_file(full_path, mimetype="image/x-tga", as_attachment=False)

    @app.route('/api/photoshop-import-paint', methods=['GET'])
    def photoshop_import_paint():
        exchange_root, error = _exchange_root_from_args()
        if error:
            return jsonify({"error": error}), 403
        if not os.path.isdir(exchange_root):
            return jsonify({"error": "Exchange folder not found."}), 404
        path_arg = (request.args.get("path") or "").strip().replace("\\", "/").lstrip("/")
        if path_arg:
            full_path = _safe_join(exchange_root, path_arg)
            if full_path is None or not os.path.isfile(full_path):
                return jsonify({"error": "Paint file not found."}), 404
            return send_file(full_path, mimetype="image/x-tga", as_attachment=False)
        paint_path = os.path.join(exchange_root, "import_for_shokker", "paint.tga")
        if not os.path.isfile(paint_path):
            return jsonify({"error": "No paint file in import folder. Put paint.tga in import_for_shokker or pick a file."}), 404
        return send_file(paint_path, mimetype="image/x-tga", as_attachment=False)

    @app.route('/api/photoshop-import-spec', methods=['GET'])
    def photoshop_import_spec():
        exchange_root, error = _exchange_root_from_args()
        if error:
            return jsonify({"error": error}), 403
        if not os.path.isdir(exchange_root):
            return jsonify({"error": "Exchange folder not found."}), 404
        spec_path = os.path.join(exchange_root, "import_for_shokker", "spec.tga")
        if not os.path.isfile(spec_path):
            return jsonify({"error": "No spec file in import folder. Put spec.tga in import_for_shokker."}), 404
        return send_file(spec_path, mimetype="image/x-tga", as_attachment=False)

    @app.route('/api/photoshop-import-spec-from-last-export', methods=['POST'])
    def photoshop_import_spec_from_last_export():
        try:
            data = request.get_json() or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            user_val = (data.get("exchange_folder") or "").strip()
            # User-pasted exchange folder: accept a file path -> its folder.
            exchange_root = _coerce_user_dir(user_val) if user_val else os.path.normpath(exchange_root_getter())
            spec_src = None

            last_export_path = os.path.join(exchange_root, "last_export.json")
            if os.path.isfile(last_export_path):
                try:
                    with open(last_export_path) as f:
                        last = json.load(f)
                    car_dir = last.get("exchange_dir", "")
                    if car_dir and os.path.isdir(car_dir):
                        for fname in os.listdir(car_dir):
                            if _is_primary_spec_tga(fname):
                                spec_src = os.path.join(car_dir, fname)
                                break
                except Exception as _spb_ex:
                    _spb_swallow('photoshop_import_spec_from_last_export@L163', _spb_ex)

            if not spec_src and os.path.isdir(exchange_root):
                for name in sorted(os.listdir(exchange_root), reverse=True):
                    sub = os.path.join(exchange_root, name)
                    if os.path.isdir(sub):
                        for fname in os.listdir(sub):
                            if _is_primary_spec_tga(fname):
                                spec_src = os.path.join(sub, fname)
                                break
                        if spec_src:
                            break

            if not spec_src or not os.path.isfile(spec_src):
                return jsonify({"error": "No spec map found from a previous export. Export to Photoshop first."}), 404

            from PIL import Image as PILImage

            temp_dir = os.path.join(output_folder, 'temp_spec_imports')
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, f'imported_spec_ps_{int(time.time())}.tga')
            shutil.copy2(spec_src, temp_path)
            img = PILImage.open(temp_path)
            return jsonify({
                "success": True,
                "temp_path": temp_path.replace("\\", "/"),
                "resolution": [img.width, img.height],
                "source_file": os.path.basename(spec_src),
            })
        except Exception as exc:
            logger.exception("photoshop-import-spec-from-last-export")
            return jsonify({"error": str(exc)}), 500

    @app.route('/api/photoshop-exchange-root', methods=['GET'])
    def photoshop_exchange_root():
        """Return the default Photoshop exchange folder path for UI."""
        return jsonify({"path": exchange_root_getter()})
