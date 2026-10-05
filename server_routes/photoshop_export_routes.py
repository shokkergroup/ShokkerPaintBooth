"""Photoshop round-trip export routes for Shokker Paint Booth."""

from __future__ import annotations

import base64
import json
import os
import shutil
import time

from flask import jsonify, request


def register_photoshop_export_routes(
    app,
    *,
    engine_getter,
    output_folder_getter,
    photoshop_exchange_root,
    repair_base_overlay_pattern_reactive_payload,
    convert_zone_keys,
    max_zones_per_request,
    apply_paint_recolor,
    decode_rle_mask_payload,
    decode_source_layer_rgb_payload,
    decode_spatial_mask_payload,
    image_shape_getter,
    external_write_guard,
    logger,
) -> None:
    """Register Photoshop export endpoint with explicit server dependencies."""

    def _sanitize_car_file_name(raw_name):
        car_file_name = (raw_name or "shokker_export").strip()
        if not car_file_name:
            car_file_name = "shokker_export"
        return "".join(
            c if c.isalnum() or c in "._- " else "_"
            for c in car_file_name
        ).strip() or "shokker_export"

    def _write_base64_file(raw_value, target_path, error_label):
        try:
            raw = raw_value
            if raw.startswith("data:"):
                raw = raw.split(",", 1)[-1]
            buf = base64.b64decode(raw)
            with open(target_path, "wb") as f:
                f.write(buf)
            return None
        except Exception as e:
            return f"Invalid {error_label}: {e}"

    def _decode_pattern_strength_map(zone):
        if not zone.get("pattern_strength_map") or not isinstance(zone["pattern_strength_map"], (dict, str)):
            return
        zone["pattern_strength_map"] = decode_rle_mask_payload(
            zone["pattern_strength_map"],
            "export_to_photoshop pattern_strength_map",
            max_shape=(512, 512),
        )

    @app.route('/api/export-to-photoshop', methods=['POST'])
    def export_to_photoshop():
        """
        Export current zones as a named car file for Photoshop round-trip.
        """
        try:
            data = request.get_json() or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            paint_file = data.get("paint_file")
            paint_image_base64 = data.get("paint_image_base64")
            if not paint_file and not paint_image_base64:
                return jsonify({"error": "Missing 'paint_file' or 'paint_image_base64'"}), 400
            if paint_file and not paint_image_base64 and not os.path.exists(paint_file):
                return jsonify({"error": f"Paint file not found: {paint_file}"}), 404

            zones = [
                repair_base_overlay_pattern_reactive_payload(convert_zone_keys(z))
                for z in data.get("zones", [])
            ]
            stamp_spec_finish = data.get("stamp_spec_finish", "gloss")
            stamp_image_path = None
            decal_spec_finishes = data.get("decal_spec_finishes", [])
            decal_mask_base64 = data.get("decal_mask_base64")
            import_spec_map_early = data.get("import_spec_map")
            if not zones and not import_spec_map_early:
                return jsonify({"error": "No zones provided"}), 400
            if len(zones) > max_zones_per_request:
                return jsonify({
                    "error": "too_many_zones",
                    "message": f"Zone count {len(zones)} exceeds limit {max_zones_per_request}.",
                    "limit": max_zones_per_request,
                }), 400

            car_file_name = _sanitize_car_file_name(data.get("car_file_name"))
            exchange_root = (data.get("exchange_folder") or "").strip() or photoshop_exchange_root()
            exchange_root = os.path.normpath(exchange_root)
            exchange_dir = os.path.join(exchange_root, car_file_name)
            denial = external_write_guard(exchange_root, "export-to-photoshop")
            if denial:
                return jsonify(denial), 403
            os.makedirs(exchange_dir, exist_ok=True)

            iracing_id = "00000"
            seed = int(data.get("seed", 51))
            job_id = f"{int(time.time())}_{iracing_id}"
            job_dir = os.path.join(output_folder_getter(), f"job_{job_id}")
            os.makedirs(job_dir, exist_ok=True)

            decal_paint_path = None
            if paint_image_base64:
                decal_paint_path = os.path.join(job_dir, "paint_with_decals.png")
                error = _write_base64_file(paint_image_base64, decal_paint_path, "paint_image_base64")
                if error:
                    return jsonify({"error": error}), 400
                paint_file = decal_paint_path

            stamp_image_base64 = data.get("stamp_image_base64")
            if stamp_image_base64:
                stamp_image_path = os.path.join(job_dir, "stamp_overlay.png")
                error = _write_base64_file(stamp_image_base64, stamp_image_path, "stamp_image_base64")
                if error:
                    return jsonify({"error": error}), 400

            actual_paint_file = paint_file
            recolor_rules = data.get("recolor_rules", [])
            recolor_mask_rle = data.get("recolor_mask", None)
            recolor_mask_has_include = data.get("recolor_mask_has_include", False)
            if recolor_rules:
                try:
                    actual_paint_file = apply_paint_recolor(
                        paint_file, recolor_rules, job_dir, recolor_mask_rle, recolor_mask_has_include
                    )
                except ValueError:
                    raise
                except Exception:
                    actual_paint_file = paint_file

            canvas_shape = None
            if any(z.get("region_mask") or z.get("source_layer_mask") or z.get("spatial_mask") for z in zones):
                canvas_shape = image_shape_getter(actual_paint_file, "export_to_photoshop paint")

            for z in zones:
                if z.get("region_mask") and isinstance(z["region_mask"], (dict, str)):
                    try:
                        z["region_mask"] = decode_rle_mask_payload(
                            z["region_mask"], "export_to_photoshop region_mask",
                            expected_shape=canvas_shape,
                        )
                    except Exception as rm_err:
                        raise ValueError(f"region_mask decode failed: {rm_err}") from rm_err
                if z.get("source_layer_mask") and isinstance(z["source_layer_mask"], (dict, str)):
                    try:
                        z["source_layer_mask"] = decode_rle_mask_payload(
                            z["source_layer_mask"], "export_to_photoshop source_layer_mask",
                            expected_shape=canvas_shape,
                        )
                    except Exception as slm_err:
                        raise ValueError(f"source_layer_mask decode failed: {slm_err}") from slm_err
                if z.get("source_layer_rgb_png"):
                    try:
                        z["source_layer_rgb"] = decode_source_layer_rgb_payload(
                            z["source_layer_rgb_png"],
                            "export_to_photoshop source_layer_rgb_png",
                            expected_shape=canvas_shape,
                        )
                    except Exception as slr_err:
                        raise ValueError(f"source_layer_rgb decode failed: {slr_err}") from slr_err
                if z.get("spatial_mask") and isinstance(z["spatial_mask"], (dict, str)):
                    try:
                        z["spatial_mask"] = decode_spatial_mask_payload(
                            z["spatial_mask"], "export_to_photoshop spatial_mask",
                            expected_shape=canvas_shape,
                        )
                        z.pop("region_mask", None)
                    except Exception as spm_err:
                        raise ValueError(f"spatial_mask decode failed: {spm_err}") from spm_err
                _decode_pattern_strength_map(z)

            import_spec_map = data.get("import_spec_map")
            import_spec_map = import_spec_map if (import_spec_map and os.path.exists(import_spec_map)) else None
            engine = engine_getter()
            engine.full_render_pipeline(
                car_paint_file=actual_paint_file,
                output_dir=job_dir,
                zones=zones,
                iracing_id=iracing_id,
                seed=seed,
                helmet_paint_file=None,
                suit_paint_file=None,
                wear_level=0,
                car_folder_name=car_file_name,
                export_zip=False,
                dual_spec=False,
                night_boost=0.7,
                import_spec_map=import_spec_map,
                car_prefix="car_num",
                stamp_image=stamp_image_path,
                stamp_spec_finish=stamp_spec_finish,
                decal_spec_finishes=decal_spec_finishes if decal_spec_finishes else None,
                decal_paint_path=decal_paint_path,
                decal_mask_base64=decal_mask_base64,
            )

            # Generate channel TGAs in job_dir (same as main render path) so we can copy base + spec + channels
            spec_tga = os.path.join(job_dir, f"car_spec_{iracing_id}.tga")
            if os.path.exists(spec_tga):
                try:
                    import numpy as np
                    from PIL import Image as PILImage

                    img = PILImage.open(spec_tga).convert("RGBA")
                    arr = np.array(img)
                    for fname, ch_idx in [
                        ("spec_metallic.tga", 0),
                        ("spec_roughness.tga", 1),
                        ("spec_clearcoat.tga", 2),
                        ("spec_mask.tga", 3),
                    ]:
                        ch = arr[:, :, ch_idx]
                        rgb = np.stack([ch, ch, ch], axis=-1)
                        engine.write_tga_24bit(os.path.join(job_dir, fname), rgb)
                except Exception as e:
                    logger.warning(f"Export to Photoshop: channel TGA export failed: {e}")
            paint_tga = os.path.join(job_dir, f"car_num_{iracing_id}.tga")
            if os.path.exists(paint_tga):
                try:
                    shutil.copy2(paint_tga, os.path.join(job_dir, "paint_base.tga"))
                except Exception as e:
                    logger.warning(f"Export to Photoshop: paint_base.tga copy failed: {e}")

            base_name = car_file_name
            paint_src = os.path.join(job_dir, f"car_num_{iracing_id}.tga")
            spec_src = os.path.join(job_dir, f"car_spec_{iracing_id}.tga")
            paint_dst = os.path.join(exchange_dir, f"{base_name}.tga")
            spec_dst = os.path.join(exchange_dir, f"{base_name} Spec.tga")
            if os.path.exists(paint_src):
                shutil.copy2(paint_src, paint_dst)
            if os.path.exists(spec_src):
                shutil.copy2(spec_src, spec_dst)

            channel_map = [
                ("spec_metallic.tga", f"{base_name} spec_metallic.tga"),
                ("spec_roughness.tga", f"{base_name} spec_roughness.tga"),
                ("spec_clearcoat.tga", f"{base_name} spec_clearcoat.tga"),
                ("spec_mask.tga", f"{base_name} spec_mask.tga"),
                ("paint_base.tga", f"{base_name} paint_base.tga"),
            ]
            for src_fname, dst_fname in channel_map:
                src = os.path.join(job_dir, src_fname)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(exchange_dir, dst_fname))

            channel_files = [dst_f for _, dst_f in channel_map if os.path.exists(os.path.join(exchange_dir, dst_f))]
            manifest = {
                "name": car_file_name,
                "paint_path": paint_dst,
                "spec_path": spec_dst,
                "channel_files": channel_files,
                "timestamp": int(time.time()),
                "exchange_dir": exchange_dir,
            }
            manifest_path = os.path.join(exchange_dir, "manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            last_export = {
                "car_file_name": car_file_name,
                "exchange_dir": exchange_dir,
                "timestamp": manifest["timestamp"],
            }
            with open(os.path.join(exchange_root, "last_export.json"), "w") as f:
                json.dump(last_export, f)

            logger.info(f"Export to Photoshop: {car_file_name} -> {exchange_dir}")
            return jsonify({
                "success": True,
                "car_file_name": car_file_name,
                "exchange_dir": exchange_dir,
                "manifest_path": manifest_path,
            })
        except ValueError as e:
            logger.warning(f"export-to-photoshop rejected invalid payload: {e}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.exception("export-to-photoshop")
            return jsonify({"error": str(e)}), 500
