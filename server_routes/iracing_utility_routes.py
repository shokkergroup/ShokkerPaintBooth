"""iRacing discovery and render-job maintenance routes."""

import os
import shutil
import time

from flask import jsonify, request


def register_iracing_utility_routes(
    app,
    *,
    output_folder_getter,
    scrubbed_folder_predicate,
    rate_limit=None,
    safe_int=None,
    candidate_roots_getter=None,
    documents_dir_getter=None,
    ui_summary_getter=None,
    car_package_summary_getter=None,
    output_job_dir_resolver=None,
    deploy_job_dir_to_iracing_paint=None,
    logger,
):
    """Register lightweight iRacing utility routes."""

    @app.route('/iracing-cars', methods=['GET'])
    def list_iracing_cars():
        """Discover car folders in the user's iRacing paint directory."""
        logger.info("[iracing-cars] Car discovery requested")
        try:
            documents_dir = documents_dir_getter() if documents_dir_getter is not None else None
            iracing_paint = os.path.join(documents_dir, "paint") if documents_dir else ""
            if not os.path.isdir(iracing_paint):
                return jsonify({"cars": [], "paint_dir": "", "error": "iRacing paint folder not found"})

            cars = []
            for entry in sorted(os.listdir(iracing_paint)):
                if scrubbed_folder_predicate(entry):
                    logger.info(f"[iracing-cars] Skipping scrubbed gear folder: {entry}")
                    continue
                car_path = os.path.join(iracing_paint, entry)
                if os.path.isdir(car_path):
                    tga_count = len([f for f in os.listdir(car_path) if f.endswith('.tga')])
                    cars.append({
                        "name": entry,
                        "path": car_path.replace("\\", "/"),
                        "tga_count": tga_count,
                    })

            return jsonify({
                "cars": cars,
                "paint_dir": iracing_paint.replace("\\", "/"),
                "count": len(cars),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/cleanup', methods=['POST'])
    def cleanup_jobs():
        """Delete old render job folders to free disk space."""
        try:
            data = request.get_json(silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            logger.info(f"[cleanup] Cleanup requested (max_age_hours={data.get('max_age_hours', 0)})")
            try:
                max_age_hours = float(data.get("max_age_hours", 0) or 0)
            except (TypeError, ValueError):
                max_age_hours = 0
            output_folder = output_folder_getter()

            deleted = 0
            freed_bytes = 0
            kept = 0
            now = time.time()

            if not os.path.exists(output_folder):
                return jsonify({"success": True, "deleted": 0, "kept": 0, "freed_mb": 0})

            for entry in os.listdir(output_folder):
                if not entry.startswith("job_"):
                    continue
                job_path = os.path.join(output_folder, entry)
                if not os.path.isdir(job_path):
                    continue
                if max_age_hours > 0:
                    age_hours = (now - os.path.getmtime(job_path)) / 3600
                    if age_hours < max_age_hours:
                        kept += 1
                        continue
                for root, _dirs, files in os.walk(job_path):
                    for fname in files:
                        try:
                            freed_bytes += os.path.getsize(os.path.join(root, fname))
                        except OSError:
                            pass
                shutil.rmtree(job_path, ignore_errors=True)
                deleted += 1

            freed_mb = round(freed_bytes / (1024 * 1024), 1)
            logger.info(f"Cleanup: deleted {deleted} jobs, freed {freed_mb}MB, kept {kept}")
            return jsonify({
                "success": True,
                "deleted": deleted,
                "kept": kept,
                "freed_mb": freed_mb,
                "message": f"Cleaned {deleted} render jobs, freed {freed_mb}MB",
            })
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/iracing-viewer-info', methods=['GET'])
    def api_iracing_viewer_info():
        """Detect local iRacing viewer/asset plumbing for the Finish Viewer bridge."""
        if rate_limit is not None and not rate_limit("iracing-viewer-info", max_per_second=2):
            return jsonify({"success": False, "error": "rate_limited"}), 429
        limit_value = safe_int(request.args.get("limit"), 180) if safe_int is not None else 180
        limit = max(20, min(500, limit_value))
        roots = []
        for root in candidate_roots_getter():
            exists = os.path.isdir(root)
            if not exists:
                roots.append({"path": root, "exists": False})
                continue
            version_file = os.path.join(root, "version_system.txt")
            version = None
            if os.path.isfile(version_file):
                try:
                    with open(version_file, "r", encoding="utf-8", errors="replace") as fh:
                        version = fh.read().strip()
                except OSError:
                    version = None
            roots.append({
                "path": root,
                "exists": True,
                "version": version,
                "ui": ui_summary_getter(root),
                "cars": car_package_summary_getter(root, limit=limit),
            })
        docs_dir = documents_dir_getter()
        return jsonify({
            "success": True,
            "documents_dir": docs_dir,
            "paint_dir": os.path.join(docs_dir, "paint") if docs_dir else None,
            "roots": roots,
            "selected_root": next((root["path"] for root in roots if root.get("exists")), None),
            "official_preview_model": {
                "type": "native-dll-child-window",
                "dll": "iRacingViewer.dll",
                "model_assets": "packed .dat archives containing .3do meshes and .mip textures",
                "electron_bridge": "preload interop.viewerCreateView / viewerLoadObject / viewerPaintItem",
                "redistribution_warning": "Use locally installed assets only; do not bundle iRacing models or DLLs.",
            },
        })

    @app.route('/deploy-to-iracing', methods=['POST'])
    def deploy_to_iracing():
        """Copy rendered TGAs from a job to an iRacing car folder."""
        try:
            data = request.get_json(silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            logger.info(f"[deploy] Deploy requested: car={data.get('car_folder')}, job={data.get('job_id')}")
            job_id = data.get("job_id", "")
            car_folder = data.get("car_folder", "")
            iracing_id = data.get("iracing_id", "00000")

            if not job_id:
                return jsonify({"error": "Missing job_id"}), 400
            if not car_folder:
                return jsonify({"error": "Missing car_folder"}), 400

            job_dir = output_job_dir_resolver(str(job_id).strip())
            if not job_dir:
                return jsonify({"error": f"Job not found: {job_id}"}), 404

            result = deploy_job_dir_to_iracing_paint(job_dir, car_folder, iracing_id)
            if not result.get("success"):
                if result.get("error") == "external_write_disabled":
                    code = 403
                else:
                    code = 404 if result.get("error") == "invalid_job_dir" else 400
                return jsonify({"error": result.get("error", "deploy_failed")}), code

            return jsonify({
                "success": True,
                "verified": result.get("verified") is True,
                "deployed": result["deployed"],
                "files": result.get("files", []),
                "target": result["target"],
                "message": result["message"],
            })
        except Exception as e:
            logger.error(f"Deploy error: {e}")
            return jsonify({"error": str(e)}), 500
