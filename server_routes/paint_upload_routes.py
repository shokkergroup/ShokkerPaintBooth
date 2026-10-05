"""Paint upload and local image serving routes for Shokker Paint Booth."""

import base64
import io
import os
import time
import traceback
import urllib.parse
import uuid

from flask import jsonify, request, send_file
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def _raw_path_is_traversal(raw_path):
    """True if the RAW (pre-abspath) request arg contains a parent escape.

    Must run BEFORE os.path.abspath(), which collapses '..' segments and makes
    a post-abspath '..' check dead code. We look at the literal user string with
    both separators normalized so 'a/../../etc' and 'a\\..\\..\\etc' are caught.
    """
    if not raw_path:
        return False
    normalized = raw_path.replace("\\", "/")
    parts = [seg for seg in normalized.split("/")]
    return ".." in parts


def _default_allowed_roots(output_folder):
    """Roots a served local file may legitimately resolve under.

    Single-user loopback desktop app: legitimate paint/spec assets live under
    the app output folder, the Photoshop exchange tree, the user's ShokkerPaintBooth
    documents, and the iRacing paints folder. Anything outside these is rejected so
    a crafted absolute path cannot read arbitrary on-disk .tga/.png/.jpg files.
    """
    home = os.path.expanduser("~")
    candidates = [
        output_folder,
        os.path.join(home, "Documents", "ShokkerPaintBooth"),
        os.path.join(home, "Documents", "iRacing", "paint"),
        os.path.join(home, "Documents", "iRacing", "paints"),
    ]
    roots = []
    for cand in candidates:
        if not cand:
            continue
        try:
            real = os.path.realpath(cand)
        except OSError as _spb_ex:
            _spb_swallow('_default_allowed_roots@L49', _spb_ex); continue
        if real not in roots:
            roots.append(real)
    return roots


def _resolve_within_roots(raw_path, allowed_roots, logger):
    """Validate raw_path then resolve it, constrained to allowed_roots.

    Returns the resolved realpath on success, or None if the raw input attempts a
    traversal escape or the resolved path lands outside every allowed root. Mirrors
    the realpath-startswith containment used by photoshop_import_routes._safe_join.
    """
    if _raw_path_is_traversal(raw_path):
        logger.warning(f"[serve-local-file] Path traversal attempt blocked (raw): {raw_path!r}")
        return None
    try:
        real_full = os.path.realpath(os.path.abspath(raw_path))
    except OSError:
        return None
    for root in allowed_roots:
        if real_full == root or real_full.startswith(root + os.sep):
            return real_full
    logger.warning(f"[serve-local-file] Path outside allowed roots blocked: {real_full}")
    return None


def register_paint_upload_routes(app, *, output_folder, temp_file_path, logger, allowed_roots_getter=None):
    """Register paint upload and local-file bridge routes."""

    def _allowed_roots():
        if allowed_roots_getter is not None:
            try:
                roots = allowed_roots_getter() or []
            except Exception:
                roots = []
            out = []
            for cand in roots:
                if not cand:
                    continue
                try:
                    real = os.path.realpath(cand)
                except OSError as _spb_ex:
                    _spb_swallow('_allowed_roots@L92', _spb_ex); continue
                if real not in out:
                    out.append(real)
            if out:
                return out
        return _default_allowed_roots(output_folder)

    @app.route('/upload-composited-paint', methods=['POST'])
    def upload_composited_paint():
        """Receive a composited paint PNG and save it as a temporary TGA."""
        try:
            from PIL import Image as PILImage

            data = request.get_json() or {}
            paint_data = data.get('paint_data', '')
            iracing_id = data.get('iracing_id', '00000')

            if not paint_data or not paint_data.startswith('data:image'):
                return jsonify({"error": "Missing or invalid paint_data"}), 400

            b64_start = paint_data.index(',') + 1
            img_bytes = base64.b64decode(paint_data[b64_start:])
            img = PILImage.open(io.BytesIO(img_bytes)).convert('RGB')

            temp_dir = os.path.join(output_folder, 'temp_composites')
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, f'composited_{iracing_id}_{int(time.time())}.tga')
            img.save(temp_path, 'TGA')

            return jsonify({
                "success": True,
                "temp_path": temp_path.replace("\\", "/"),
                "resolution": [img.width, img.height],
            })
        except Exception as e:
            logger.error(f"Composited paint upload error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/upload-spec-map', methods=['POST'])
    def upload_spec_map():
        """Receive a spec map TGA/PNG (base64) for import and merge mode."""
        logger.info("[upload-spec-map] Spec map upload requested")
        try:
            from PIL import Image as PILImage

            data = request.get_json() or {}
            spec_data = data.get('spec_data', '')
            spec_path = data.get('spec_path', '')

            temp_dir = os.path.join(output_folder, 'temp_spec_imports')
            os.makedirs(temp_dir, exist_ok=True)

            if spec_path and os.path.isfile(spec_path):
                ext = os.path.splitext(spec_path)[1].lower()
                if ext not in {'.tga', '.png', '.jpg', '.jpeg'}:
                    return jsonify({"error": "Spec map path must be TGA/PNG/JPG"}), 400
                img = PILImage.open(spec_path)
                return jsonify({
                    "success": True,
                    "temp_path": spec_path.replace("\\", "/"),
                    "resolution": [img.width, img.height],
                    "mode": img.mode,
                })

            if not spec_data or not spec_data.startswith('data:image'):
                return jsonify({"error": "Missing spec_data or spec_path"}), 400

            b64_start = spec_data.index(',') + 1
            img_bytes = base64.b64decode(spec_data[b64_start:])
            img = PILImage.open(io.BytesIO(img_bytes))
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            temp_path = os.path.join(temp_dir, f'imported_spec_{int(time.time())}.tga')
            img.save(temp_path, 'TGA')

            logger.info(f"Spec map imported: {img.width}x{img.height} {img.mode} -> {temp_path}")
            return jsonify({
                "success": True,
                "temp_path": temp_path.replace("\\", "/"),
                "resolution": [img.width, img.height],
                "mode": "RGBA",
            })
        except Exception as e:
            logger.error(f"Spec map upload error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/upload-paint-file', methods=['POST'])
    def api_upload_paint_file():
        """Accept a paint file upload and return its server path."""
        try:
            if 'file' not in request.files and 'paint_file' not in request.files:
                return jsonify({"error": "No file in request. Send multipart with 'file' or 'paint_file'."}), 400
            f = request.files.get('file') or request.files.get('paint_file')
            if not f or not f.filename:
                return jsonify({"error": "No file selected"}), 400
            safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in f.filename)
            upload_dir = os.path.join(output_folder, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            path = os.path.join(upload_dir, f"paint_{int(time.time())}_{safe_name}")
            f.save(path)
            return jsonify({"ok": True, "path": os.path.abspath(path).replace("\\", "/")})
        except Exception as e:
            logger.error(f"Upload paint file error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/upload-tga-decal', methods=['POST'])
    def upload_tga_decal():
        """Convert an uploaded TGA file to PNG for use as a decal."""
        try:
            from PIL import Image as PILImage

            if 'file' not in request.files:
                return jsonify({"error": "No file uploaded"}), 400
            f = request.files['file']
            if not f.filename.lower().endswith('.tga'):
                return jsonify({"error": "File must be a TGA"}), 400

            temp_tga = temp_file_path(f"decal_{uuid.uuid4().hex}.tga")
            f.save(temp_tga)
            img = PILImage.open(temp_tga).convert('RGBA')
            temp_png = temp_tga.replace('.tga', '.png')
            img.save(temp_png, 'PNG')
            try:
                os.remove(temp_tga)
            except Exception as _spb_ex:
                _spb_swallow('upload_tga_decal@L218', _spb_ex)

            with open(temp_png, 'rb') as pf:
                png_b64 = base64.b64encode(pf.read()).decode('utf-8')
            try:
                os.remove(temp_png)
            except Exception as _spb_ex:
                _spb_swallow('upload_tga_decal@L225', _spb_ex)

            logger.info(f"TGA decal uploaded: {f.filename} -> {img.width}x{img.height} PNG")
            return jsonify({
                "success": True,
                "png_base64": f"data:image/png;base64,{png_b64}",
                "width": img.width,
                "height": img.height,
            })
        except Exception as e:
            logger.error(f"TGA decal upload error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/serve-local-file', methods=['POST'])
    def api_serve_local_file():
        """Verify a local image file path and return a download URL."""
        try:
            data = request.get_json() or {}
            raw_path = data.get("path", "").strip()
            if not raw_path:
                return jsonify({"error": "No path provided"}), 400
            file_path = _resolve_within_roots(raw_path, _allowed_roots(), logger)
            if file_path is None:
                return jsonify({"ok": False, "error": "Invalid path"}), 400
            if not os.path.isfile(file_path):
                return jsonify({"ok": False, "error": f"File not found: {file_path}"}), 404
            encoded = urllib.parse.quote(file_path, safe='')
            return jsonify({"ok": True, "url": f"/api/serve-local-file/download?p={encoded}"})
        except Exception as e:
            logger.error(f"serve-local-file error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/serve-local-file/download', methods=['GET'])
    def api_serve_local_file_download():
        """Serve a local image file to the client."""
        raw_path = urllib.parse.unquote(request.args.get('p', ''))
        if not raw_path:
            return jsonify({"error": "No path"}), 400
        # Validate the RAW arg for traversal BEFORE abspath collapses '..', then
        # constrain the resolved realpath to the allowed roots (realpath startswith).
        file_path = _resolve_within_roots(raw_path, _allowed_roots(), logger)
        if file_path is None:
            return jsonify({"error": "Invalid path"}), 400
        if not os.path.isfile(file_path):
            return jsonify({"error": "File not found"}), 404
        ext = os.path.splitext(file_path)[1].lower()
        allowed_types = {'.tga': 'image/tga', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
        mimetype = allowed_types.get(ext)
        if not mimetype:
            logger.warning(f"[serve-local-file] Rejected non-image file type: {ext}")
            return jsonify({"error": f"File type '{ext}' not allowed. Only TGA/PNG/JPG permitted."}), 400
        logger.debug(f"[serve-local-file] Serving: {os.path.basename(file_path)}")
        return send_file(file_path, mimetype=mimetype, as_attachment=False)
