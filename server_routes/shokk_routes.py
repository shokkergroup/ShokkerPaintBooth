"""SHOKK library/package routes for Shokker Paint Booth."""

from __future__ import annotations

import base64
import glob
import os
import tempfile
import traceback

from flask import Response, jsonify, request, send_file


def _find_job_files(job_dir):
    """Find spec, paint, and preview files in a render job directory."""
    spec_path = None
    paint_path = None
    preview_path = None

    for name in ("RENDER_spec.png", "spec.png"):
        path = os.path.join(job_dir, name)
        if os.path.exists(path):
            spec_path = path
            break
    if not spec_path:
        matches = glob.glob(os.path.join(job_dir, "car_spec_*.tga"))
        if matches:
            spec_path = matches[0]

    for name in ("RENDER_paint.tga", "output.tga"):
        path = os.path.join(job_dir, name)
        if os.path.exists(path):
            paint_path = path
            break
    if not paint_path:
        for pattern in ("car_num_*.tga", "car_*.tga"):
            matches = glob.glob(os.path.join(job_dir, pattern))
            matches = [m for m in matches if "spec" not in os.path.basename(m)]
            if matches:
                paint_path = matches[0]
                break

    for name in ("PREVIEW_paint.png", "preview.png", "preview.jpg"):
        path = os.path.join(job_dir, name)
        if os.path.exists(path):
            preview_path = path
            break

    return spec_path, paint_path, preview_path


def _sanitize_shokk_filename(filename):
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in filename)


def _plain_filename(filename):
    filename = (filename or "").strip()
    if not filename or os.path.basename(filename) != filename:
        return None
    return filename


def register_shokk_routes(
    app,
    *,
    manager_getter,
    output_folder_getter,
    spb_version_getter,
    logger,
    external_write_guard=None,
) -> None:
    """Register SHOKK file management routes."""

    def _manager_or_error():
        mgr = manager_getter()
        if not mgr:
            return None, (jsonify({"error": "SHOKK manager unavailable"}), 500)
        return mgr, None

    @app.route('/api/shokk/library-path', methods=['GET'])
    def api_shokk_library_path():
        """Return the SHOKK Library folder path for Open Folder."""
        mgr, error = _manager_or_error()
        if error:
            return error
        return jsonify({"path": mgr.library_dir, "ok": True})

    @app.route('/api/shokk/list', methods=['GET'])
    def api_shokk_list():
        """List all .shokk files in the library and factory dirs."""
        logger.info("[shokk/list] Listing SHOKK library")
        mgr, error = _manager_or_error()
        if error:
            return error
        try:
            entries = mgr.list_library()
            return jsonify({"ok": True, "shokks": entries, "count": len(entries)})
        except Exception as e:
            logger.error(f"/api/shokk/list error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/shokk/save', methods=['POST'])
    def api_shokk_save():
        """Package and save current session as a .shokk file."""
        logger.info("[shokk/save] Save requested")
        mgr, error = _manager_or_error()
        if error:
            return error
        if external_write_guard is not None:
            denial = external_write_guard(mgr.library_dir, "shokk-library-save")
            if denial:
                return jsonify(denial), 403
        output_folder = output_folder_getter()
        live_paint_path = None
        try:
            data = request.get_json() or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            name = data.get("name", "Untitled SHOKK").strip() or "Untitled SHOKK"
            author = data.get("author", "").strip()
            description = data.get("description", "").strip()
            tags = data.get("tags") or []
            session_json = data.get("session_json") or {}
            include_paint = data.get("include_paint", True)
            paint_image_base64 = data.get("paint_image_base64")
            paint_source = "render_job"

            spec_path = None
            paint_path = None
            preview_path = None
            if include_paint and paint_image_base64:
                try:
                    raw = paint_image_base64
                    if raw.startswith("data:"):
                        raw = raw.split(",", 1)[-1]
                    paint_bytes = base64.b64decode(raw)
                    with tempfile.NamedTemporaryFile(
                        suffix=".png",
                        prefix="shokk_live_paint_",
                        dir=output_folder,
                        delete=False,
                    ) as tmp_live:
                        tmp_live.write(paint_bytes)
                        live_paint_path = tmp_live.name
                    paint_source = "live_canvas"
                    logger.info("SHOKK save: Using live paint_image_base64 payload for bundled paint")
                except Exception as e:
                    logger.warning(f"SHOKK save: Invalid paint_image_base64 payload: {e}")
                    return jsonify({"error": f"Invalid paint_image_base64: {e}"}), 400

            target_job_id = data.get("job_id", "").strip()
            if target_job_id:
                target_job_dir = os.path.join(output_folder, f"job_{target_job_id}")
                if os.path.isdir(target_job_dir):
                    spec_path, paint_path, preview_path = _find_job_files(target_job_dir)
                    logger.info(
                        f"SHOKK save: Using specific job_id={target_job_id} "
                        f"spec={spec_path is not None} paint={paint_path is not None}"
                    )

            if not spec_path:
                latest_dir = os.path.join(output_folder, "_latest_render")
                if os.path.isdir(latest_dir):
                    latest_spec = None
                    latest_paint = None
                    latest_preview = None
                    for name in ("spec.png", "spec.tga"):
                        path = os.path.join(latest_dir, name)
                        if os.path.exists(path):
                            latest_spec = path
                            break
                    for name in ("paint.tga",):
                        path = os.path.join(latest_dir, name)
                        if os.path.exists(path):
                            latest_paint = path
                            break
                    for name in ("preview.png",):
                        path = os.path.join(latest_dir, name)
                        if os.path.exists(path):
                            latest_preview = path
                            break
                    if latest_spec:
                        spec_path = latest_spec
                        if not paint_path:
                            paint_path = latest_paint
                        if not preview_path:
                            preview_path = latest_preview
                        logger.info(f"SHOKK save: Using _latest_render/ spec={spec_path is not None}")

            if not spec_path and os.path.isdir(output_folder):
                jobs = sorted(
                    [d for d in os.listdir(output_folder) if d.startswith("job_")],
                    key=lambda d: os.path.getmtime(os.path.join(output_folder, d)),
                    reverse=True,
                )
                for job in jobs:
                    job_dir = os.path.join(output_folder, job)
                    candidate_spec, candidate_paint, candidate_preview = _find_job_files(job_dir)
                    if candidate_spec:
                        spec_path = candidate_spec
                        if not paint_path:
                            paint_path = candidate_paint
                        if not preview_path:
                            preview_path = candidate_preview
                        break

            if live_paint_path:
                paint_path = live_paint_path

            out_path = mgr.save(
                name=name,
                author=author,
                description=description,
                tags=tags,
                session_json=session_json,
                spec_path=spec_path,
                paint_path=paint_path if include_paint else None,
                preview_path=preview_path,
                include_paint=include_paint,
                spb_version=spb_version_getter(),
            )

            return jsonify({
                "ok": True,
                "path": out_path,
                "filename": os.path.basename(out_path),
                "has_spec": spec_path is not None,
                "has_paint": include_paint and paint_path is not None,
                "paint_source": paint_source if include_paint and paint_path is not None else None,
            })
        except Exception as e:
            logger.error(f"/api/shokk/save error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500
        finally:
            try:
                if live_paint_path and os.path.exists(live_paint_path):
                    os.remove(live_paint_path)
            except Exception:
                logger.warning("SHOKK save: failed to remove temporary live paint payload", exc_info=True)

    @app.route('/api/shokk/open', methods=['POST'])
    def api_shokk_open():
        """Extract a .shokk file and return its contents."""
        logger.info("[shokk/open] Open requested")
        mgr, error = _manager_or_error()
        if error:
            return error
        output_folder = output_folder_getter()
        try:
            data = request.get_json() or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            shokk_path = data.get("path", "").strip()
            if not shokk_path or not os.path.exists(shokk_path):
                return jsonify({"error": f"File not found: {shokk_path}"}), 404

            extract_dir = tempfile.mkdtemp(dir=output_folder, prefix="shokk_open_")
            result = mgr.open(shokk_path, extract_dir=extract_dir)

            paint_url = None
            if result.get("paint_path"):
                ext_basename = os.path.basename(extract_dir)
                paint_basename = os.path.basename(result["paint_path"])
                if ext_basename.startswith("shokk_open_") and paint_basename:
                    paint_url = f"/api/shokk/extracted/{ext_basename}/{paint_basename}"

            return jsonify({
                "ok": True,
                "manifest": result["manifest"],
                "session_json": result["session_json"],
                "spec_path": result["spec_path"],
                "paint_path": result["paint_path"],
                "paint_url": paint_url,
                "extract_dir": extract_dir,
            })
        except Exception as e:
            logger.error(f"/api/shokk/open error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/shokk/extracted/<extract_basename>/<filename>', methods=['GET'])
    def api_shokk_extracted_file(extract_basename, filename):
        """Serve a file from an extracted SHOKK dir so client can load paint."""
        safe_extract = os.path.basename(extract_basename)
        safe_file = os.path.basename(filename)
        if not safe_extract.startswith("shokk_open_") or not safe_file:
            return jsonify({"error": "Invalid path"}), 400
        output_folder = output_folder_getter()
        path = os.path.abspath(os.path.join(output_folder, safe_extract, safe_file))
        out_abs = os.path.abspath(output_folder)
        if not path.startswith(out_abs + os.sep) and path != out_abs:
            return jsonify({"error": "Invalid path"}), 400
        if not os.path.isfile(path):
            return jsonify({"error": "File not found"}), 404
        mimetype = "image/tga" if safe_file.lower().endswith(".tga") else None
        return send_file(path, mimetype=mimetype, as_attachment=False)

    @app.route('/api/shokk/preview/<filename>', methods=['GET'])
    def api_shokk_preview(filename):
        """Serve the preview.jpg from inside a .shokk file."""
        filename = _plain_filename(filename)
        if not filename:
            return jsonify({"error": "Invalid filename"}), 400
        mgr, error = _manager_or_error()
        if error:
            return error
        try:
            for search_dir in [mgr.library_dir, mgr.factory_dir]:
                if not search_dir:
                    continue
                path = os.path.join(search_dir, filename)
                if os.path.exists(path):
                    preview_bytes = mgr.get_preview_bytes(path)
                    if preview_bytes:
                        return Response(
                            preview_bytes,
                            mimetype='image/jpeg',
                            headers={'Cache-Control': 'max-age=3600'},
                        )
            return jsonify({"error": "No preview in this SHOKK file"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/shokk/delete', methods=['POST'])
    def api_shokk_delete():
        """Delete a .shokk from the user library, never factory."""
        mgr, error = _manager_or_error()
        if error:
            return error
        if external_write_guard is not None:
            denial = external_write_guard(mgr.library_dir, "shokk-library-delete")
            if denial:
                return jsonify(denial), 403
        try:
            data = request.get_json() or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            filename = _plain_filename(data.get("filename", ""))
            if not filename or not filename.endswith(".shokk"):
                return jsonify({"error": "Invalid filename"}), 400
            ok = mgr.delete(filename)
            return jsonify({"ok": ok})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/shokk/rename', methods=['POST'])
    def api_shokk_rename():
        """Rename a .shokk in the user library, never factory."""
        mgr, error = _manager_or_error()
        if error:
            return error
        if external_write_guard is not None:
            denial = external_write_guard(mgr.library_dir, "shokk-library-rename")
            if denial:
                return jsonify(denial), 403
        try:
            data = request.get_json() or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            old_name = _plain_filename(data.get("old_name", ""))
            new_name = _plain_filename(data.get("new_name", ""))
            if not old_name or not new_name or not old_name.endswith(".shokk") or not new_name.endswith(".shokk"):
                return jsonify({"error": "Invalid filename - must end in .shokk"}), 400
            safe_new = _sanitize_shokk_filename(new_name)
            if not safe_new or safe_new == ".shokk":
                return jsonify({"error": "Invalid new name"}), 400
            old_path = os.path.join(mgr.library_dir, old_name)
            new_path = os.path.join(mgr.library_dir, safe_new)
            if not os.path.exists(old_path):
                return jsonify({"error": "File not found"}), 404
            if os.path.exists(new_path):
                return jsonify({"error": f'A file named "{safe_new}" already exists'}), 409
            os.rename(old_path, new_path)
            return jsonify({"ok": True, "new_name": safe_new})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
