"""PSD layer ZIP export route for Shokker Paint Booth."""

from __future__ import annotations

import base64
import io
import json
import os
import time
import traceback
import zipfile

from flask import jsonify, request, send_file


def register_psd_layer_export_routes(
    app,
    *,
    output_folder_getter,
    repair_base_overlay_pattern_reactive_payload,
    convert_zone_keys,
    apply_paint_recolor,
    decode_rle_mask_payload,
    decode_source_layer_rgb_payload,
    image_shape_getter,
    max_zones_per_request,
    build_multi_zone,
    logger,
) -> None:
    """Register PSD layer ZIP export with explicit server dependencies."""

    def _sanitize_output_name(raw_name):
        output_name = (raw_name or "shokker_layers").strip()
        return "".join(c if c.isalnum() or c in "._- " else "_" for c in output_name).strip() or "shokker_layers"

    def _write_paint_base64(raw_value, target_path):
        raw = raw_value
        if raw.startswith("data:"):
            raw = raw.split(",", 1)[-1]
        with open(target_path, "wb") as f:
            f.write(base64.b64decode(raw))

    def _decode_pattern_strength_map(zone):
        if not zone.get("pattern_strength_map") or not isinstance(zone["pattern_strength_map"], (dict, str)):
            return
        zone["pattern_strength_map"] = decode_rle_mask_payload(
            zone["pattern_strength_map"],
            "export_psd_layers pattern_strength_map",
            max_shape=(512, 512),
        )

    def _copy_optional_float(zone_obj, source, key, *, clamp=None):
        if source.get(key) is None:
            return
        value = float(source[key])
        if clamp:
            lo, hi = clamp
            value = max(lo, min(hi, value))
        zone_obj[key] = value

    def _build_server_zone(z, np):
        zone_obj = {
            "name": z.get("name", "Zone"),
            "color": z.get("color", "everything"),
            "intensity": z.get("intensity", "100"),
        }
        if z.get("base"):
            zone_obj["base"] = z["base"]
            zone_obj["pattern"] = z.get("pattern", "none")
            for key in ("scale", "rotation", "pattern_opacity"):
                _copy_optional_float(zone_obj, z, key)
            if z.get("pattern_stack"):
                zone_obj["pattern_stack"] = z["pattern_stack"]
        elif z.get("finish"):
            zone_obj["finish"] = z["finish"]
            if z.get("finish_colors"):
                zone_obj["finish_colors"] = z["finish_colors"]
            if z.get("pattern") and z["pattern"] != "none":
                zone_obj["pattern"] = z["pattern"]
            for key in ("scale", "rotation", "pattern_opacity"):
                _copy_optional_float(zone_obj, z, key)

        for key in ("region_mask", "source_layer_mask", "source_layer_rgb", "pattern_strength_map"):
            if z.get(key) is not None and isinstance(z[key], np.ndarray):
                zone_obj[key] = z[key]
        if z.get("priority_override") is not None:
            zone_obj["priority_override"] = bool(z.get("priority_override"))
        _copy_optional_float(zone_obj, z, "pattern_spec_mult")
        from server_routes.pattern_controls import copy_pattern_controls
        copy_pattern_controls(zone_obj, z)
        for key in ("pattern_offset_x", "pattern_offset_y"):
            _copy_optional_float(zone_obj, z, key, clamp=(0.0, 1.0))
        for key in ("pattern_flip_h", "pattern_flip_v"):
            if z.get(key) is not None:
                zone_obj[key] = bool(z.get(key))
        if z.get("pattern_placement") is not None:
            zone_obj["pattern_placement"] = z.get("pattern_placement")
        if z.get("pattern_fit_zone") or z.get("pattern_placement") == "fit":
            zone_obj["pattern_fit_zone"] = True
        if z.get("pattern_manual") or z.get("pattern_placement") == "manual":
            zone_obj["pattern_manual"] = True
        for stack_key in (
            "spec_pattern_stack",
            "overlay_spec_pattern_stack",
            "third_overlay_spec_pattern_stack",
            "fourth_overlay_spec_pattern_stack",
            "fifth_overlay_spec_pattern_stack",
        ):
            if z.get(stack_key):
                zone_obj[stack_key] = z.get(stack_key, [])
        for key in ("custom_intensity", "wear_level", "paint_color"):
            if z.get(key):
                zone_obj[key] = z[key]

        _copy_optional_float(zone_obj, z, "base_scale", clamp=(0.01, 10.0))
        _copy_optional_float(zone_obj, z, "base_offset_x", clamp=(0.0, 1.0))
        _copy_optional_float(zone_obj, z, "base_offset_y", clamp=(0.0, 1.0))
        _copy_optional_float(zone_obj, z, "base_rotation", clamp=(-3600.0, 3600.0))
        for key in ("base_flip_h", "base_flip_v"):
            if z.get(key) is not None:
                zone_obj[key] = bool(z.get(key))
        _copy_optional_float(zone_obj, z, "base_strength")
        base_spec_strength = z.get("base_spec_strength")
        if base_spec_strength is None and z.get("baseSpecStrength") is not None:
            base_spec_strength = z.get("baseSpecStrength")
        if base_spec_strength is not None:
            zone_obj["base_spec_strength"] = float(base_spec_strength)

        for key in (
            "base_color_mode",
            "base_color_explicit",
            "base_color",
            "base_color_source",
            "gradient_stops",
            "gradient_direction",
        ):
            if z.get(key) is not None:
                zone_obj[key] = z.get(key)
        if z.get("base_color_fit_zone"):
            zone_obj["base_color_fit_zone"] = True
        if z.get("zone_spec_map"):
            zone_obj["zone_spec_map"] = z.get("zone_spec_map")
            zone_obj["zone_spec_map_strength"] = max(0.0, min(1.0, float(z.get("zone_spec_map_strength", 1.0))))
        if z.get("blend_base"):
            zone_obj["blend_base"] = z["blend_base"]
            zone_obj["blend_dir"] = z.get("blend_dir", "horizontal")
            zone_obj["blend_amount"] = float(z.get("blend_amount", 0.5))

        for pfx in ("second_base", "third_base", "fourth_base", "fifth_base"):
            has_base = z.get(pfx)
            has_src = z.get(f"{pfx}_color_source")
            if not has_base and not has_src:
                continue
            if has_base:
                zone_obj[pfx] = has_base
            zone_obj[f"{pfx}_color"] = z.get(f"{pfx}_color", [1.0, 1.0, 1.0])
            zone_obj[f"{pfx}_color_source"] = has_src
            zone_obj[f"{pfx}_strength"] = float(z.get(f"{pfx}_strength", 0.0))
            zone_obj[f"{pfx}_blend_mode"] = z.get(f"{pfx}_blend_mode", "noise")
            zone_obj[f"{pfx}_noise_scale"] = int(z.get(f"{pfx}_noise_scale", 24))
            zone_obj[f"{pfx}_scale"] = max(0.01, min(5.0, float(z.get(f"{pfx}_scale", 1.0))))
            zone_obj[f"{pfx}_pattern"] = z.get(f"{pfx}_pattern")
            for key in (
                f"{pfx}_spec_strength",
                f"{pfx}_hue_shift",
                f"{pfx}_saturation",
                f"{pfx}_brightness",
                f"{pfx}_pattern_hue_shift",
                f"{pfx}_pattern_saturation",
                f"{pfx}_pattern_brightness",
                f"{pfx}_pattern_opacity",
                f"{pfx}_pattern_scale",
                f"{pfx}_pattern_rotation",
                f"{pfx}_pattern_strength",
                f"{pfx}_pattern_offset_x",
                f"{pfx}_pattern_offset_y",
            ):
                if z.get(key) is not None:
                    zone_obj[key] = float(z[key])
            for key in (
                f"{pfx}_pattern_invert",
                f"{pfx}_pattern_harden",
                f"{pfx}_pattern_flip_h",
                f"{pfx}_pattern_flip_v",
                f"{pfx}_fit_zone",
            ):
                if z.get(key) is not None:
                    zone_obj[key] = bool(z[key])
        return zone_obj

    @app.route('/export-psd-layers', methods=['POST'])
    def export_psd_layers():
        """Export per-zone spec + paint images as a ZIP for Photoshop layer import."""
        logger.info("[export-psd-layers] PSD layer export requested")
        try:
            import numpy as np
            from PIL import Image as PILImage

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
            if not zones:
                return jsonify({"error": "No zones provided"}), 400
            if len(zones) > max_zones_per_request:
                return jsonify({
                    "error": "too_many_zones",
                    "message": f"Zone count {len(zones)} exceeds limit {max_zones_per_request}.",
                    "limit": max_zones_per_request,
                }), 400

            seed = int(data.get("seed", 51))
            output_name = _sanitize_output_name(data.get("output_name"))
            job_id = f"{int(time.time())}_layers"
            job_dir = os.path.join(output_folder_getter(), f"job_{job_id}")
            os.makedirs(job_dir, exist_ok=True)

            if paint_image_base64:
                try:
                    paint_file = os.path.join(job_dir, "paint_with_decals.png")
                    _write_paint_base64(paint_image_base64, paint_file)
                except Exception as e:
                    return jsonify({"error": f"Invalid paint_image_base64: {e}"}), 400

            actual_paint_file = paint_file
            recolor_rules = data.get("recolor_rules", [])
            if recolor_rules:
                try:
                    actual_paint_file = apply_paint_recolor(paint_file, recolor_rules, job_dir)
                except Exception:
                    actual_paint_file = paint_file

            canvas_shape = None
            if any(z.get("region_mask") or z.get("source_layer_mask") for z in zones):
                canvas_shape = image_shape_getter(actual_paint_file, "export_psd_layers paint")

            for z in zones:
                if z.get("region_mask") and isinstance(z["region_mask"], (dict, str)):
                    try:
                        z["region_mask"] = decode_rle_mask_payload(
                            z["region_mask"], "export_psd_layers region_mask",
                            expected_shape=canvas_shape,
                        )
                    except Exception as rm_err:
                        raise ValueError(f"region_mask decode failed: {rm_err}") from rm_err
                if z.get("source_layer_mask") and isinstance(z["source_layer_mask"], (dict, str)):
                    try:
                        z["source_layer_mask"] = decode_rle_mask_payload(
                            z["source_layer_mask"], "export_psd_layers source_layer_mask",
                            expected_shape=canvas_shape,
                        )
                    except Exception as slm_err:
                        raise ValueError(f"source_layer_mask decode failed: {slm_err}") from slm_err
                if z.get("source_layer_rgb_png"):
                    try:
                        z["source_layer_rgb"] = decode_source_layer_rgb_payload(
                            z["source_layer_rgb_png"],
                            "export_psd_layers source_layer_rgb_png",
                            expected_shape=canvas_shape,
                        )
                    except Exception as slr_err:
                        raise ValueError(f"source_layer_rgb decode failed: {slr_err}") from slr_err
                _decode_pattern_strength_map(z)

            server_zones = []
            for z in zones:
                zone_obj = _build_server_zone(z, np)
                if zone_obj.get("zone_spec_map") and not os.path.exists(zone_obj["zone_spec_map"]):
                    logger.warning(
                        f"Zone spec map not found for PSD layer export zone '{zone_obj.get('name', 'Zone')}': "
                        f"{zone_obj['zone_spec_map']}"
                    )
                    zone_obj.pop("zone_spec_map", None)
                    zone_obj.pop("zone_spec_map_strength", None)
                server_zones.append(zone_obj)

            import_spec_map = data.get("import_spec_map")
            if import_spec_map and not os.path.exists(import_spec_map):
                import_spec_map = None

            result = build_multi_zone(
                actual_paint_file,
                job_dir,
                server_zones,
                seed=seed,
                export_layers=True,
                import_spec_map=import_spec_map,
            )
            if len(result) != 4:
                raise RuntimeError(
                    "/export-psd-layers expected build_multi_zone(export_layers=True) "
                    "to return per-zone layer outputs"
                )
            paint_rgb, combined_spec_u8, _zone_masks, zone_layers = result

            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                layers_meta = []
                for layer in zone_layers:
                    idx = layer["zone_index"] + 1
                    zname = layer["zone_name"]
                    safe_name = "".join(c if c.isalnum() or c in "_- " else "_" for c in zname).strip() or f"zone_{idx}"

                    spec_buf = io.BytesIO()
                    PILImage.fromarray(layer["spec"]).save(spec_buf, format="PNG")
                    zf.writestr(f"per_zone_{idx}_spec.png", spec_buf.getvalue())

                    paint_buf = io.BytesIO()
                    PILImage.fromarray(layer["paint"]).save(paint_buf, format="PNG")
                    zf.writestr(f"per_zone_{idx}_paint.png", paint_buf.getvalue())

                    layers_meta.append({
                        "index": idx,
                        "name": zname,
                        "safe_name": safe_name,
                        "spec_file": f"per_zone_{idx}_spec.png",
                        "paint_file": f"per_zone_{idx}_paint.png",
                        "blend_mode": "normal",
                    })

                combined_paint_buf = io.BytesIO()
                PILImage.fromarray(paint_rgb).save(combined_paint_buf, format="PNG")
                zf.writestr("combined_paint.png", combined_paint_buf.getvalue())

                combined_spec_buf = io.BytesIO()
                PILImage.fromarray(combined_spec_u8).save(combined_spec_buf, format="PNG")
                zf.writestr("combined_spec.png", combined_spec_buf.getvalue())

                manifest = {
                    "version": 1,
                    "layers": layers_meta,
                    "combined_paint": "combined_paint.png",
                    "combined_spec": "combined_spec.png",
                    "resolution": [int(paint_rgb.shape[1]), int(paint_rgb.shape[0])],
                    "seed": seed,
                }
                zf.writestr("layers.json", json.dumps(manifest, indent=2))

            zip_buf.seek(0)
            zip_bytes = zip_buf.getvalue()
            zip_path = os.path.join(job_dir, f"{output_name}.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_bytes)

            logger.info(f"PSD layer export: {len(zone_layers)} zones, ZIP={len(zip_bytes)} bytes -> {zip_path}")
            return send_file(
                io.BytesIO(zip_bytes),
                mimetype="application/zip",
                as_attachment=True,
                download_name=f"{output_name}.zip",
            )
        except ValueError as e:
            logger.warning(f"PSD layer export rejected invalid payload: {e}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"PSD layer export failed: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500
