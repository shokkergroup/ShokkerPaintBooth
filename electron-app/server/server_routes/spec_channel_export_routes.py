"""Photoshop spec-channel export routes for Shokker Paint Booth."""

from __future__ import annotations

import glob
import os
import shutil
import tempfile
import traceback

from flask import jsonify, request


def register_spec_channel_export_routes(
    app,
    *,
    output_folder_getter,
    shokk_manager_getter,
    external_write_guard,
    logger,
) -> None:
    """Register Photoshop channel export endpoint with explicit dependencies."""

    def _latest_render_files(output_folder):
        spec_path = None
        paint_path = None
        latest_dir = os.path.join(output_folder, "_latest_render")
        if os.path.isdir(latest_dir):
            for spec_name in ("spec.png", "spec.tga"):
                candidate = os.path.join(latest_dir, spec_name)
                if os.path.exists(candidate):
                    spec_path = candidate
                    break
            paint_candidate = os.path.join(latest_dir, "paint.tga")
            if os.path.exists(paint_candidate):
                paint_path = paint_candidate
        return spec_path, paint_path

    def _latest_job_files(output_folder):
        def _job_mtime(d):
            p = os.path.join(output_folder, d)
            return os.path.getmtime(p) if os.path.exists(p) else 0

        jobs = sorted(
            [d for d in os.listdir(output_folder) if d.startswith("job_")],
            key=_job_mtime,
            reverse=True,
        )
        for job in jobs:
            job_dir = os.path.join(output_folder, job)
            spec_path = None
            paint_path = None
            for spec_name in ("RENDER_spec.png", "spec.png", "PREVIEW_spec.png"):
                candidate = os.path.join(job_dir, spec_name)
                if os.path.exists(candidate):
                    spec_path = candidate
                    break
            if not spec_path:
                matches = glob.glob(os.path.join(job_dir, "car_spec_*.tga"))
                if matches:
                    spec_path = matches[0]
            for paint_name in ("PREVIEW_paint.png", "RENDER_paint.tga", "output.tga"):
                candidate = os.path.join(job_dir, paint_name)
                if os.path.exists(candidate):
                    paint_path = candidate
                    break
            if not paint_path:
                for pattern in ("car_num_*.tga", "car_*.tga"):
                    matches = glob.glob(os.path.join(job_dir, pattern))
                    matches = [m for m in matches if "spec" not in os.path.basename(m)]
                    if matches:
                        paint_path = matches[0]
                        break
            if spec_path:
                return spec_path, paint_path
        return None, None

    def _resolve_output_dir(output_folder, requested):
        requested = (requested or "").strip()
        logger.info(f"PS Export: output_dir from request = '{requested}' (len={len(requested) if requested else 0})")
        if requested and not os.path.isabs(requested):
            logger.warning(f"PS Export: relative path detected '{requested}', resolving to absolute")
            requested = os.path.join(output_folder, "PS_Exports", requested)
            logger.info(f"PS Export: resolved to '{requested}'")
        if requested:
            logger.info(f"PS Export: using user-specified output dir: {requested}")
            return os.path.normpath(requested)
        return os.path.join(output_folder, "PS_Exports")

    @app.route('/api/export-spec-channels', methods=['POST'])
    def api_export_spec_channels():
        """
        Split a spec map into 4 channel PNGs plus optional paint PNG.
        Supports current render jobs and .shokk extraction.
        """
        extract_dir = None
        try:
            import numpy as np
            from PIL import Image as PILImage

            data = request.get_json() or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            output_folder = output_folder_getter()
            shokk_path = data.get("shokk_path", "").strip()
            include_paint = data.get("include_paint", True)
            spec_path = data.get("spec_path")
            paint_path = None

            if shokk_path and os.path.exists(shokk_path):
                manager = shokk_manager_getter()
                if not manager:
                    return jsonify({"error": "SHOKK manager unavailable"}), 500
                extract_dir = tempfile.mkdtemp(dir=output_folder, prefix="shokk_export_")
                result = manager.open(shokk_path, extract_dir=extract_dir)
                spec_path = result.get("spec_path")
                paint_path = result.get("paint_path")
                logger.info(f"PS Export from SHOKK: {shokk_path}")

            if not spec_path or not os.path.exists(spec_path):
                spec_path, paint_path = _latest_render_files(output_folder)

            if not spec_path or not os.path.exists(spec_path):
                spec_path, paint_path = _latest_job_files(output_folder)

            if not spec_path or not os.path.exists(spec_path):
                return jsonify({"error": "No spec map found. Render first, or select a SHOKK file with spec data."}), 404

            img = PILImage.open(spec_path).convert("RGBA")
            arr = np.array(img)
            out_dir = _resolve_output_dir(output_folder, data.get("output_dir", ""))
            denial = external_write_guard(out_dir, "export-spec-channels")
            if denial:
                return jsonify(denial), 403
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception as dir_err:
                fallback_dir = os.path.join(output_folder, "PS_Exports")
                if os.path.normcase(os.path.abspath(out_dir)) == os.path.normcase(os.path.abspath(fallback_dir)):
                    raise
                logger.warning(
                    f"PS Export: could not create output dir '{out_dir}': {dir_err}, using default"
                )
                denial = external_write_guard(fallback_dir, "export-spec-channels")
                if denial:
                    return jsonify(denial), 403
                out_dir = fallback_dir
                os.makedirs(out_dir, exist_ok=True)

            paths = {}
            try:
                spec_backup = os.path.join(out_dir, "spec_full.png")
                img.save(spec_backup)
                paths["Spec (Full RGBA)"] = spec_backup
                logger.info("PS Export: spec_full.png backup saved")
            except Exception as sbe:
                logger.warning(f"PS Export: could not save spec backup: {sbe}")

            if include_paint and paint_path and os.path.exists(paint_path):
                try:
                    paint_img = PILImage.open(paint_path).convert("RGB")
                    paint_out = os.path.join(out_dir, "paint_base.png")
                    paint_img.save(paint_out)
                    paths["Paint (Base)"] = paint_out
                    logger.info("PS Export: paint_base.png saved")
                except Exception as pe:
                    logger.warning(f"PS Export: could not export paint: {pe}")

            for fname, channel, label in [
                ("spec_metallic.png", arr[:, :, 0], "R (Metallic)"),
                ("spec_roughness.png", arr[:, :, 1], "G (Roughness)"),
                ("spec_clearcoat.png", arr[:, :, 2], "B (Clearcoat)"),
                ("spec_mask.png", arr[:, :, 3], "A (Spec Mask)"),
            ]:
                out_path = os.path.join(out_dir, fname)
                PILImage.fromarray(channel, mode="L").save(out_path)
                paths[label] = out_path

            return jsonify({"ok": True, "paths": paths, "spec_source": spec_path})
        except Exception as e:
            logger.error(f"/api/export-spec-channels error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500
        finally:
            if extract_dir:
                shutil.rmtree(extract_dir, ignore_errors=True)
