"""PSD import and rasterization routes for Shokker Paint Booth."""

from __future__ import annotations

import base64
import io
import traceback

from flask import Response, jsonify, request

from server_routes.psd_import_tree import build_layer_tree, iter_leaf_layers
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def rasterize_leaf_pixels(layer):
    from psd_tools.api.layers import Layer

    if isinstance(layer, Layer):
        if layer.is_group():
            # The on-demand endpoint can also name a group. Keep its existing
            # composite semantics; do not reveal every child of that group.
            return layer.composite()
        # Leaf-only routes: retain masks/effects while ignoring ancestor display
        # visibility. Do not mutate the cached PSD or awaken sibling layers.
        return layer.composite(force=True, layer_filter=lambda _: True)
    # SPB's ORA/XCF facades already return their individual raster; they do not
    # implement psd-tools' layer_filter parameter.
    return layer.composite(force=True)


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
    # [SPB-PERF2 2026-10-10] /api/psd-rasterize-all is the bulk of opening a layered PSD (owner's 13-layer ARCA: 16-25 s of psd_tools composites + PNG encodes) and was
    # recomputed on EVERY open of the same file. Same idea as _import_response_cache: the complete response, keyed by (path, mtime_ns, size), 2 entries (~4 MB each),
    # only when every layer rasterized. Identical response; kill switch env SPB_PERF2_OFF=1.
    _raster_response_cache = {}

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

    def _p3_orig_api_psd_import():   # [PERF-3 2026-10-10] routed through api_psd_import below
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

    def _p3_orig_api_psd_rasterize_all():   # [PERF-3 2026-10-10] routed through api_psd_rasterize_all below
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
            import os
            import time

            _rk = None
            if os.environ.get('SPB_PERF2_OFF', '').strip() in ('', '0'):
                try:
                    _st = os.stat(psd_path)
                    _rk = (psd_path, _st.st_mtime_ns, _st.st_size)
                except OSError:
                    _rk = None
            if _rk is not None:
                _hit = _raster_response_cache.pop(_rk, None)
                if _hit is not None:
                    _raster_response_cache[_rk] = _hit
                    logger.info(f"[PSD Rasterize] Reused {_hit.get('count')} layers for {psd_path} (cached)")
                    return jsonify(_hit)
            _skipped = 0

            t0 = time.time()

            for metadata, child in iter_leaf_layers(psd):
                try:
                    img = rasterize_leaf_pixels(child)
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
                    _skipped += 1
                    logger.warning(
                        f"[PSD Rasterize] Skip {metadata['layer_key']} {metadata['path']}: {layer_err}"
                    )

            elapsed = time.time() - t0
            logger.info(f"[PSD Rasterize] Done: {len(result_layers)} layers in {elapsed:.1f}s")

            _payload = {
                "success": True,
                "layers": result_layers,
                "count": len(result_layers),
                "elapsed_ms": round(elapsed * 1000),
            }
            if _rk is not None and _skipped == 0 and result_layers:
                _raster_response_cache[_rk] = _payload
                while len(_raster_response_cache) > 2:
                    _raster_response_cache.pop(next(iter(_raster_response_cache)))
            return jsonify(_payload)
        except Exception as e:
            logger.error(f"/api/psd-rasterize-all failed: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    # [PERF-3 2026-10-10] Persistent PSD-open cache + boot pre-warm. Kill switch: env SPB_PERF3_OFF=1.
    # PERF-2 measured the FIRST open of the owner's 13-layer ARCA PSD in an app session at
    # 19.6-26.5 s (psd_tools composites every layer + the flattened composite); only re-opens were
    # cached, in memory, so every app restart paid it again. Now the exact response BYTES of
    # /api/psd-import and /api/psd-rasterize-all are also kept on disk (SPB_PSD_CACHE_DIR, default
    # %APPDATA%/ShokkerPaintBooth/psd_cache), keyed by path + mtime_ns + size + a blake2b of the
    # file's bytes (+ thumbnail size), and served verbatim on a later open, even after a restart.
    # A raster response is stored only when every leaf layer rasterized. The last opened PSD is
    # pre-warmed in a background thread at server start (the app re-opens it at boot), so a file
    # changed while the app was closed is usually ready by the time the page asks. One lock per
    # file serialises the compute between the pre-warm and a request (no double work, no
    # concurrent psd_tools use of the same object). Numbers: _easy_claude_work/perf2/PERF3_PROGRESS.md.
    # Measured (copies of the owner PSDs, median of 5, open in a fresh app session): ARCA 16.7 s ->
    # 0.16 s, Chevy truck 18.4 s -> 0.10 s; PSD changed while closed + pre-warm: 0.32 s at 25 s after boot.
    import hashlib as _p3_hashlib
    import os as _p3_os
    import threading as _p3_threading
    import json as _p3_json
    _p3_hash_memo = {}
    _p3_path_locks = {}
    _p3_locks_guard = _p3_threading.Lock()

    def _p3_off():
        return str(_p3_os.environ.get("SPB_PERF3_OFF", "")).strip().lower() in ("1", "true", "yes", "on")

    def _p3_cache_dir():
        return _p3_os.environ.get("SPB_PSD_CACHE_DIR") or _p3_os.path.join(
            _p3_os.environ.get("APPDATA", _p3_os.path.expanduser("~")), "ShokkerPaintBooth", "psd_cache")

    def _p3_entry_path(kind, psd_path, extra):
        st = _p3_os.stat(psd_path)
        fkey = (_p3_os.path.normcase(_p3_os.path.abspath(psd_path)), st.st_mtime_ns, st.st_size)
        dig = _p3_hash_memo.get(fkey)
        if dig is None:
            h = _p3_hashlib.blake2b(digest_size=20)
            with open(psd_path, "rb") as fh:
                for chunk in iter(lambda: fh.read(4 << 20), b""):
                    h.update(chunk)
            dig = h.hexdigest()
            _p3_hash_memo[fkey] = dig
        name = _p3_hashlib.blake2b(repr(("psd-open-v1", fkey, dig, kind, extra)).encode("utf-8"),
                                   digest_size=16).hexdigest()
        return _p3_os.path.join(_p3_cache_dir(), f"{kind}_{name}.json")

    def _p3_path_lock(psd_path):
        k = _p3_os.path.normcase(_p3_os.path.abspath(psd_path))
        with _p3_locks_guard:
            lk = _p3_path_locks.get(k)
            if lk is None:
                lk = _p3_path_locks[k] = _p3_threading.Lock()
            return lk

    def _p3_guarded(path, op):
        if external_write_guard is None:
            return True
        try:
            return not external_write_guard(path, op)
        except Exception:
            return False

    def _p3_disk_get(kind, psd_path, extra):
        try:
            fp = _p3_entry_path(kind, psd_path, extra)
            if not _p3_os.path.isfile(fp):
                return None
            with open(fp, "rb") as fh:
                return fh.read()
        except Exception as _e:
            _spb_swallow('perf3_psd_disk_get', _e)
            return None

    def _p3_disk_put(kind, psd_path, extra, data):
        try:
            fp = _p3_entry_path(kind, psd_path, extra)
            d = _p3_os.path.dirname(fp)
            if not _p3_guarded(fp, "psd-open-cache"):
                return
            _p3_os.makedirs(d, exist_ok=True)
            tmp = f"{fp}.{_p3_os.getpid()}.{_p3_threading.get_ident()}.tmp"
            with open(tmp, "wb") as fh:
                fh.write(data)
            _p3_os.replace(tmp, fp)
            entries = sorted(
                (e for e in _p3_os.scandir(d) if e.is_file() and e.name.endswith(".json") and e.name != "last.json"),
                key=lambda e: e.stat().st_mtime,
            )
            for old in entries[:-16]:   # newest 16 responses (~8 PSDs) kept
                try:
                    _p3_os.remove(old.path)
                except OSError:
                    pass
        except Exception as _e:
            logger.warning(f"[PERF-3] PSD cache write skipped: {_e}")

    def _p3_note_last(psd_path, thumb):
        try:
            fp = _p3_os.path.join(_p3_cache_dir(), "last.json")
            if not _p3_guarded(fp, "psd-open-cache"):
                return
            _p3_os.makedirs(_p3_os.path.dirname(fp), exist_ok=True)
            tmp = f"{fp}.{_p3_os.getpid()}.tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                _p3_json.dump({"psd_path": psd_path, "thumbnail_size": thumb}, fh)
            _p3_os.replace(tmp, fp)
        except Exception as _e:
            _spb_swallow('perf3_psd_note_last', _e)

    def _p3_warm_object(psd_path):
        # The original import opened the PSD on every call; later routes (layer fetch, Spec Sculpt)
        # expect it warm. A disk hit skips that, so open it in the background instead.
        def _run():
            try:
                with _p3_path_lock(psd_path):
                    get_cached_psd(psd_path)
            except Exception as _e:
                _spb_swallow('perf3_psd_warm_object', _e)
        _p3_threading.Thread(target=_run, name="spb-perf3-psd-warm", daemon=True).start()

    def _p3_raster_complete(psd_path, payload):
        try:
            psd = get_cached_psd(psd_path)
            n_leaf = sum(1 for _ in iter_leaf_layers(psd))
            return bool(payload.get("success")) and int(payload.get("count") or 0) == n_leaf > 0
        except Exception:
            return False

    def _p3_cached_route(kind, orig):
        if _p3_off() or (request.mimetype or '').startswith('multipart/'):
            return orig()
        try:
            data = request.get_json(force=True, silent=True) or {}
            if not isinstance(data, dict):
                return orig()
            ok, _err = require_internal_request()
            if not ok:
                return orig()
            psd_path, path_err = sanitize_path(data.get('psd_path', ''))
            if (path_err or not psd_path or not psd_path.lower().endswith(('.psd', '.ora', '.xcf'))
                    or not _p3_os.path.isfile(psd_path)):
                return orig()
            extra = str(int(data.get('thumbnail_size', 256))) if kind == "import" else ""
        except Exception:
            return orig()
        t0 = __import__("time").time()
        raw = _p3_disk_get(kind, psd_path, extra)
        if raw is None:
            with _p3_path_lock(psd_path):
                raw = _p3_disk_get(kind, psd_path, extra)   # a pre-warm may have just finished it
                if raw is None:
                    resp = orig()
                    if isinstance(resp, Response) and resp.status_code == 200:
                        try:
                            payload = resp.get_json(silent=True) or {}
                            if (payload.get("composite") if kind == "import" else _p3_raster_complete(psd_path, payload)):
                                _p3_disk_put(kind, psd_path, extra, resp.get_data())
                                if kind == "import":
                                    _p3_note_last(psd_path, int(extra))
                        except Exception as _e:
                            _spb_swallow('perf3_psd_store', _e)
                    return resp
        logger.info(f"[PERF-3] PSD {kind} served from disk cache in {(__import__('time').time() - t0) * 1000:.0f} ms: {psd_path}")
        if kind == "import":
            _p3_note_last(psd_path, int(extra))
            _p3_warm_object(psd_path)
        return Response(raw, status=200, mimetype="application/json")

    @app.route('/api/psd-import', methods=['POST'])
    def api_psd_import():
        """Import a PSD (see _p3_orig_api_psd_import); PERF-3 persistent cache in front."""
        return _p3_cached_route("import", _p3_orig_api_psd_import)

    @app.route('/api/psd-rasterize-all', methods=['POST'])
    def api_psd_rasterize_all():
        """Rasterize all pixel layers (see _p3_orig_api_psd_rasterize_all); PERF-3 persistent cache in front."""
        return _p3_cached_route("raster", _p3_orig_api_psd_rasterize_all)

    def _p3_prewarm():
        try:
            __import__("time").sleep(float(_p3_os.environ.get("SPB_PSD_PREWARM_DELAY", "3")))
            fp = _p3_os.path.join(_p3_cache_dir(), "last.json")
            if _p3_off() or not _p3_os.path.isfile(fp):
                return
            with open(fp, "r", encoding="utf-8") as fh:
                last = _p3_json.load(fh)
            psd_path = last.get("psd_path")
            if not psd_path or not _p3_os.path.isfile(psd_path):
                return
            t0 = __import__("time").time()
            hdr = {"X-Shokker-Internal": "1"}
            with app.test_request_context('/api/psd-import', method='POST', headers=hdr,
                                          json={"psd_path": psd_path, "thumbnail_size": int(last.get("thumbnail_size") or 128)}):
                api_psd_import()
            with app.test_request_context('/api/psd-rasterize-all', method='POST', headers=hdr,
                                          json={"psd_path": psd_path}):
                api_psd_rasterize_all()
            logger.info(f"[PERF-3] PSD pre-warm done in {__import__('time').time() - t0:.1f}s: {psd_path}")
        except Exception as _e:
            logger.warning(f"[PERF-3] PSD pre-warm skipped: {_e}")

    if not _p3_off() and _p3_os.environ.get("SPB_PSD_PREWARM", "1") != "0":
        _p3_threading.Thread(target=_p3_prewarm, name="spb-perf3-psd-prewarm", daemon=True).start()

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

            img = rasterize_leaf_pixels(current)
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
