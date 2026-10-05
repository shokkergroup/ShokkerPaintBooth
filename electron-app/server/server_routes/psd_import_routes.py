"""PSD import and rasterization routes for Shokker Paint Booth."""

from __future__ import annotations

import base64
import io
import traceback

from flask import jsonify, request

from server_routes.psd_import_tree import build_layer_tree, iter_leaf_layers
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def register_psd_import_routes(
    app,
    *,
    require_internal_request,
    sanitize_path,
    get_cached_psd,
    logger,
    external_write_guard=None,
) -> None:
    """Register PSD layer-tree import and rasterization endpoints."""

    # Composite generation is the expensive half of importing a large layered
    # template (the owner's 2048² Chevy PSD measured ~15 s on every repeat).
    # Cache the complete immutable import response by file mtime so reopening
    # Original Spec Sculpt is instant without ever serving stale PSD pixels.
    _import_response_cache = {}

    def _validate_psd_path(psd_path, missing_message):
        ok, req_err = require_internal_request()
        if not ok:
            return None, (jsonify({"error": req_err}), 403)

        psd_path, path_err = sanitize_path(psd_path)
        if path_err:
            return None, (jsonify({"error": path_err}), 400)
        # [2026-07-04 owner] .ora (OpenRaster — GIMP/Krita export) and .xcf (GIMP
        # native) import through the same routes via psd_tools-compatible facades.
        if not psd_path.lower().endswith(('.psd', '.ora', '.xcf')):
            return None, (jsonify({"error": "Only .psd, .ora (OpenRaster) and .xcf (GIMP) files are allowed"}), 400)

        import os

        if not os.path.exists(psd_path):
            return None, (jsonify({"error": missing_message}), 404)
        return psd_path, None

    @app.route('/api/psd-import', methods=['POST'])
    def api_psd_import():
        """Import a PSD file and return its layer tree plus flattened composite.

        Accepts EITHER a JSON body ``{"psd_path": "/abs/path.psd"}`` OR a multipart upload
        (field ``file`` / ``psd_file`` / ``paint_file``). The upload path exists because
        browsers and sandboxed Electron expose a picked File with no local ``.path`` — the
        bytes are saved to a temp ``.psd`` whose path is returned so the caller can reuse it
        for sculpting (load_paint / build_protect_mask read it server-side)."""
        try:
            import os
            uploaded = (request.files.get('file') or request.files.get('psd_file')
                        or request.files.get('paint_file'))
            if uploaded is not None and uploaded.filename:
                ok, req_err = require_internal_request()
                if not ok:
                    return jsonify({"error": req_err}), 403
                if not uploaded.filename.lower().endswith(('.psd', '.ora', '.xcf')):
                    return jsonify({"error": "Only .psd, .ora (OpenRaster) and .xcf (GIMP) files are allowed"}), 400
                import tempfile
                import uuid
                _up_ext = os.path.splitext(uploaded.filename.lower())[1] or '.psd'
                psd_path = os.path.join(tempfile.gettempdir(), f"spb_specsculpt_{uuid.uuid4().hex}{_up_ext}")
                if external_write_guard is not None:
                    denial = external_write_guard(psd_path, "psd-import-temp-upload")
                    if denial:
                        return jsonify(denial), 403
                uploaded.save(psd_path)
                # Keep only the last 10 uploaded PSDs in temp so we never bloat the disk — older
                # imports cycle out automatically (newest 10 by mtime are retained).
                try:
                    import glob as _glob
                    _temps = sorted(
                        _glob.glob(os.path.join(tempfile.gettempdir(), "spb_specsculpt_*.psd"))
                        + _glob.glob(os.path.join(tempfile.gettempdir(), "spb_specsculpt_*.ora"))
                        + _glob.glob(os.path.join(tempfile.gettempdir(), "spb_specsculpt_*.xcf")),
                        key=os.path.getmtime,
                    )
                    for _old in _temps[:-10]:
                        try:
                            os.remove(_old)
                        except OSError as _spb_ex:
                            _spb_swallow('api_psd_import@L91', _spb_ex)
                except Exception as _spb_ex:
                    _spb_swallow('api_psd_import@L93', _spb_ex)
                try:
                    _thumb_size = int(request.form.get('thumbnail_size', 256) or 256)
                except (TypeError, ValueError):
                    _thumb_size = 256
            else:
                data = request.get_json(force=True, silent=True) or {}
                if not isinstance(data, dict):
                    return jsonify({"error": "Request body must be a JSON object"}), 400
                psd_path = data.get('psd_path', '')
                try:
                    _thumb_size = int(data.get('thumbnail_size', 256))
                except (TypeError, ValueError):
                    return jsonify({"error": "thumbnail_size must be an integer"}), 400

                psd_path, error_response = _validate_psd_path(psd_path, "PSD file not found")
                if error_response:
                    return error_response

            try:
                import psd_tools  # noqa: F401
            except ImportError:
                return jsonify({"error": "psd-tools not installed. Run: pip install psd-tools"}), 500

            psd = get_cached_psd(psd_path)
            logger.info(f"[PSD Import] Opened {psd_path}: {psd.width}x{psd.height}, {len(psd)} top layers")

            cache_key = (psd_path, os.path.getmtime(psd_path), _thumb_size)
            cached_response = _import_response_cache.pop(cache_key, None)
            if cached_response is not None:
                _import_response_cache[cache_key] = cached_response
                logger.info(f"[PSD Import] Reused composite + layer tree for {psd_path}")
                return jsonify(cached_response)

            # Urgent owner report 2026-07-17: names are not identifiers. Deep
            # group paths were truncated by the client and duplicate sibling
            # names overwrote each other in rasterize-all, so the first Layer
            # recomposite could replace a correct source preview with black.
            layers = build_layer_tree(psd, psd.width, psd.height)

            composite_b64 = None
            try:
                composite = psd.composite()
                buf = io.BytesIO()
                composite.save(buf, 'PNG')
                composite_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('ascii')
            except Exception as comp_err:
                logger.warning(f"[PSD Import] Composite failed: {comp_err}")

            logger.info(f"[PSD Import] Success: {len(layers)} top layers extracted")
            payload = {
                "success": True,
                "width": psd.width,
                "height": psd.height,
                "layers": layers,
                "composite": composite_b64,
                "psd_path": psd_path,
            }
            if composite_b64:
                _import_response_cache[cache_key] = payload
                while len(_import_response_cache) > 4:
                    _import_response_cache.pop(next(iter(_import_response_cache)))
            return jsonify(payload)

        except Exception as e:
            logger.error(f"/api/psd-import failed: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/psd-rasterize-all', methods=['POST'])
    def api_psd_rasterize_all():
        """Rasterize all pixel layers from a PSD, returning base64 images."""
        try:
            data = request.get_json(force=True, silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            psd_path = data.get('psd_path', '')
            psd_path, error_response = _validate_psd_path(psd_path, "PSD not found")
            if error_response:
                return error_response

            psd = get_cached_psd(psd_path)
            result_layers = {}
            import time

            t0 = time.time()

            for metadata, child in iter_leaf_layers(psd):
                try:
                    was_visible = bool(child.visible)
                    if not was_visible:
                        child.visible = True
                    try:
                        img = child.composite(force=True)
                    finally:
                        if not was_visible:
                            child.visible = False
                    if img is None or img.size[0] == 0:
                        continue
                    buf = io.BytesIO()
                    img.save(buf, 'PNG')
                    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
                    # Stable positional key is collision-free even when names
                    # repeat; the human-readable full path remains diagnostic.
                    result_layers[metadata["layer_key"]] = {
                        "image": f"data:image/png;base64,{b64}",
                        "bbox": list(child.bbox),
                        "size": [img.width, img.height],
                        **metadata,
                    }
                    logger.info(
                        f"[PSD Rasterize] {metadata['layer_key']} {metadata['path']}: {img.size}"
                    )
                except Exception as layer_err:
                    logger.warning(
                        f"[PSD Rasterize] Skip {metadata['layer_key']} {metadata['path']}: {layer_err}"
                    )

            elapsed = time.time() - t0
            logger.info(f"[PSD Rasterize] Done: {len(result_layers)} layers in {elapsed:.1f}s")

            return jsonify({
                "success": True,
                "layers": result_layers,
                "count": len(result_layers),
                "elapsed_ms": round(elapsed * 1000),
            })
        except Exception as e:
            logger.error(f"/api/psd-rasterize-all failed: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/psd-layer', methods=['POST'])
    def api_psd_layer():
        """Rasterize a specific layer from a PSD file on demand."""
        try:
            data = request.get_json(force=True, silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            psd_path = data.get('psd_path', '')
            layer_path = data.get('layer_path', [])
            psd_path, error_response = _validate_psd_path(psd_path, "PSD not found")
            if error_response:
                return error_response

            psd = get_cached_psd(psd_path)
            current = psd
            for name in layer_path:
                found = None
                for child in current:
                    if child.name == name:
                        found = child
                        break
                if found is None:
                    return jsonify({"error": f"Layer '{name}' not found"}), 404
                current = found

            img = current.composite()
            if img is None:
                return jsonify({"error": "Layer could not be rasterized"}), 500

            buf = io.BytesIO()
            img.save(buf, 'PNG')
            b64 = base64.b64encode(buf.getvalue()).decode('ascii')

            return jsonify({
                "success": True,
                "image": f"data:image/png;base64,{b64}",
                "size": [img.width, img.height],
                "bbox": list(current.bbox) if hasattr(current, 'bbox') else [0, 0, img.width, img.height],
            })
        except Exception as e:
            logger.error(f"/api/psd-layer failed: {e}")
            return jsonify({"error": str(e)}), 500
