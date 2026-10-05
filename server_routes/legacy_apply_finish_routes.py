"""Legacy apply-finish compatibility route."""

from __future__ import annotations

import json
import os
import time

from flask import jsonify, request


def register_legacy_apply_finish_routes(
    app,
    *,
    engine_getter,
    output_folder_getter,
    load_config,
    logger,
) -> None:
    """Register backward-compatible multipart upload render endpoint."""

    @app.route('/apply-finish', methods=['POST'])
    def apply_finish_legacy():
        """Legacy endpoint kept for older UI integrations."""
        try:
            if 'paint_file' not in request.files:
                return jsonify({"error": "No paint file provided. Use /render with JSON instead."}), 400

            output_folder = output_folder_getter()
            file = request.files['paint_file']
            filename = f"upload_{int(time.time())}_{file.filename}"
            upload_path = os.path.join(output_folder, 'uploads', filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)

            zones_str = request.form.get('zones', '[]')
            zones = json.loads(zones_str)
            iracing_id = request.form.get('iracing_id', '00000')
            req_id = request.form.get('request_id', str(int(time.time())))
            legacy_cfg = load_config()
            legacy_prefix = "car_num" if legacy_cfg.get("use_custom_number", True) else "car"

            job_dir = os.path.join(output_folder, f"job_{req_id}")
            os.makedirs(job_dir, exist_ok=True)

            engine_getter().build_multi_zone(
                paint_file=upload_path,
                output_dir=job_dir,
                zones=zones,
                iracing_id=iracing_id,
                car_prefix=legacy_prefix,
            )

            return jsonify({
                "success": True,
                "job_id": req_id,
                "files": {
                    "paint_tga": os.path.join(job_dir, f"{legacy_prefix}_{iracing_id}.tga"),
                    "spec_tga": os.path.join(job_dir, f"car_spec_{iracing_id}.tga"),
                    "preview_paint": f"/preview/{req_id}/PREVIEW_paint.png",
                    "preview_spec": f"/preview/{req_id}/PREVIEW_spec.png",
                },
            })

        except Exception as e:
            logger.error(f"Legacy endpoint error: {e}")
            return jsonify({"error": str(e)}), 500
