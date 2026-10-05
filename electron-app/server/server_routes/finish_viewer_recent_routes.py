"""Finish Viewer recent-render and status routes for Shokker Paint Booth."""

from __future__ import annotations

import io
import os
import subprocess
import time
import traceback

from flask import jsonify, request, send_file
from PIL import Image as PILImage


def _latest_map_paths(output_folder):
    latest_dir = os.path.join(output_folder, "_latest_render")
    paint_candidates = (
        os.path.join(latest_dir, "paint.tga"),
        os.path.join(latest_dir, "paint.png"),
        os.path.join(latest_dir, "preview.png"),
    )
    spec_candidates = (
        os.path.join(latest_dir, "spec.png"),
        os.path.join(latest_dir, "spec.tga"),
    )
    paint_path = next((path for path in paint_candidates if os.path.isfile(path)), None)
    spec_path = next((path for path in spec_candidates if os.path.isfile(path)), None)
    return latest_dir, paint_path, spec_path


def register_finish_viewer_latest_routes(
    app,
    *,
    output_folder_getter,
    full_dna_job,
    full_dna_status_path_getter,
    full_dna_status_reader,
    rate_limit,
    safe_int,
    server_dir,
    sys_executable,
    logger,
    external_write_guard=None,
) -> None:
    """Register lightweight Finish Viewer latest/status endpoints."""

    @app.route('/api/finish-viewer/full-dna-export/status', methods=['GET'])
    def api_finish_viewer_full_dna_export_status():
        return jsonify({"success": True, "job": full_dna_status_reader()})

    @app.route('/api/finish-viewer/full-dna-export', methods=['POST'])
    def api_finish_viewer_full_dna_export_start():
        """Start an unattended full-catalog Finish DNA export in a background process."""
        proc = full_dna_job.get("process")
        if proc is not None and proc.poll() is None:
            return jsonify({
                "success": False,
                "error": "full_catalog_dna_export_already_running",
                "job": full_dna_status_reader(),
            }), 409

        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400
        size = max(128, min(2048, safe_int(body.get("size") or request.args.get("size"), 512)))
        scope = str(body.get("scope") or request.args.get("scope") or "all").strip().lower()
        allowed_scopes = (
            "all",
            "base",
            "bases",
            "pattern",
            "patterns",
            "monolithic",
            "monolithics",
            "special",
            "specials",
        )
        if scope not in allowed_scopes:
            return jsonify({"success": False, "error": f"Unsupported scope: {scope}"}), 400

        limit = max(0, safe_int(body.get("limit") or request.args.get("limit"), 0))
        retry_errors = str(
            body.get("retryErrors")
            or request.args.get("retry_errors")
            or request.args.get("retryErrors")
            or ""
        ).strip()
        ids = str(body.get("ids") or request.args.get("ids") or "").strip()

        status_file = full_dna_status_path_getter()
        if external_write_guard is not None:
            denial = external_write_guard(status_file, "finish-dna-export")
            if denial:
                return jsonify(denial), 403
        os.makedirs(os.path.dirname(status_file), exist_ok=True)
        script = os.path.join(server_dir, "tools", "export_full_dna_bible.py")
        if not os.path.isfile(script):
            return jsonify({"success": False, "error": f"Exporter script missing: {script}"}), 500

        cmd = [sys_executable, script, "--size", str(size), "--scope", scope, "--status-file", status_file]
        if limit:
            cmd.extend(["--limit", str(limit)])
        if retry_errors:
            cmd.extend(["--retry-errors", retry_errors])
        if ids:
            cmd.extend(["--ids", ids])

        try:
            log_path = os.path.join(os.path.dirname(status_file), "_latest_export.log")
            log_handle = open(log_path, "a", encoding="utf-8")
            try:
                proc = subprocess.Popen(cmd, cwd=server_dir, stdout=log_handle, stderr=subprocess.STDOUT)
            finally:
                log_handle.close()
            full_dna_job.update({
                "process": proc,
                "status_file": status_file,
                "started_at": time.time(),
                "log_path": log_path,
            })
            return jsonify({
                "success": True,
                "status": "started",
                "pid": proc.pid,
                "statusFile": status_file,
                "logFile": log_path,
                "poll": "/api/finish-viewer/full-dna-export/status",
                "message": "Full-catalog Finish DNA export started. This can run for up to about an hour.",
            })
        except Exception as exc:
            logger.error(f"Could not start full DNA export: {exc}\n{traceback.format_exc()}")
            return jsonify({"success": False, "error": str(exc)}), 500

    @app.route('/api/finish-viewer/latest', methods=['GET'])
    def api_finish_viewer_latest():
        """Return browser-loadable URLs for the actual latest SPB render paint/spec maps."""
        if not rate_limit("finish-viewer-latest", max_per_second=6):
            return jsonify({"success": False, "error": "rate_limited"}), 429
        latest_dir, paint_path, spec_path = _latest_map_paths(output_folder_getter())
        if not paint_path or not spec_path:
            return jsonify({
                "success": False,
                "error": "No latest render paint/spec pair found. Render in SPB first.",
                "latest_dir": latest_dir,
            }), 404
        modified = max(os.path.getmtime(paint_path), os.path.getmtime(spec_path))
        return jsonify({
            "success": True,
            "label": "latest_render",
            "latest_dir": latest_dir,
            "paint_file": os.path.basename(paint_path),
            "spec_file": os.path.basename(spec_path),
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(modified)),
            "paint": "/api/finish-viewer/latest-map/paint",
            "spec": "/api/finish-viewer/latest-map/spec",
        })

    @app.route('/api/finish-viewer/latest-map/<kind>', methods=['GET'])
    def api_finish_viewer_latest_map(kind):
        """Serve latest render paint/spec as PNG, converting TGA on the fly when needed."""
        if kind not in ("paint", "spec"):
            return jsonify({"success": False, "error": "kind must be paint or spec"}), 400
        _, paint_path, spec_path = _latest_map_paths(output_folder_getter())
        path = paint_path if kind == "paint" else spec_path
        if not path:
            return jsonify({"success": False, "error": f"No latest render {kind} map found."}), 404
        try:
            if path.lower().endswith(".png"):
                return send_file(path, mimetype="image/png")
            img = PILImage.open(path)
            img = img.convert("RGB" if kind == "paint" else "RGBA")
            buf = io.BytesIO()
            img.save(buf, "PNG")
            buf.seek(0)
            return send_file(buf, mimetype="image/png")
        except Exception as e:
            logger.error(f"Finish viewer latest map error {kind}: {e}\n{traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
