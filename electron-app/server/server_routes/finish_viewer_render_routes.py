"""Finish Viewer live render routes for Shokker Paint Booth."""

from __future__ import annotations

import base64
import io
import time
import traceback

from flask import jsonify, request


def _finish_viewer_kind_alias(raw_kind):
    kind = (raw_kind or "").strip().lower()
    return {
        "bases": "base",
        "base": "base",
        "patterns": "pattern",
        "pattern": "pattern",
        "special": "monolithic",
        "specials": "monolithic",
        "mono": "monolithic",
        "monolithics": "monolithic",
        "monolithic": "monolithic",
    }.get(kind)


def _finish_viewer_encode_maps(paint_arr, spec_arr):
    import numpy as np
    from PIL import Image as PILImage
    from engine.core import enforce_iron_rules

    paint_np = np.asarray(paint_arr, dtype=np.float32)
    if paint_np.ndim == 3 and paint_np.shape[2] > 3:
        paint_np = paint_np[:, :, :3]
    paint_u8 = (np.clip(paint_np[:, :, :3], 0, 1) * 255).astype(np.uint8)

    spec_np = np.asarray(spec_arr[:, :, :4], dtype=np.float32)
    spec_u8 = np.clip(spec_np, 0, 255).astype(np.uint8)
    enforce_iron_rules(spec_u8)

    def _data_url(arr, mode):
        buf = io.BytesIO()
        PILImage.fromarray(arr, mode).save(buf, "PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    return _data_url(paint_u8, "RGB"), _data_url(spec_u8, "RGBA")


def _entry_spec_paint(entry):
    if isinstance(entry, (tuple, list)) and len(entry) >= 2:
        return entry[0], entry[1]
    if isinstance(entry, dict):
        return entry.get("spec_fn"), entry.get("paint_fn")
    if callable(entry):
        return None, entry
    return None, None


def register_finish_viewer_render_routes(
    app,
    *,
    engine_getter,
    rate_limit,
    safe_int,
    swatch_display_color,
    invoke_monolithic_spec_fn,
    normalize_spec_result_to_rgba,
    logger,
) -> None:
    """Register live Finish Viewer render endpoints."""

    def _ensure_viewer_registry(engine):
        # SPB-WILDS experimental rollout 2026-08-25; owner: "push everything
        # you've accepted as you go so I can test them in the app." The viewer
        # bypasses build_multi_zone(), which is the normal lazy-load trigger,
        # and therefore previously read the legacy Wilds callable even after
        # the accepted adapter was installed. Run the existing idempotent
        # final-authority loader before lookup so the 14 native-reviewed
        # overrides (official M7 85.0-99.4) are the maps actually previewed.
        ensure = getattr(engine, "_ensure_expansions_loaded", None)
        if callable(ensure):
            ensure()
        return engine

    def _finish_viewer_base_color(finish_type, finish_id):
        if finish_id and str(finish_id).startswith("pf_"):
            color_hex = "888888"
        else:
            color_hex = swatch_display_color(finish_type, finish_id, "888888")
        try:
            return tuple(int(color_hex[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        except Exception:
            return (0.53, 0.53, 0.53)

    def _finish_viewer_render_maps(finish_type, finish_id, size, seed):
        """Render a live registry finish into literal paint/spec maps for the Finish Viewer."""
        import numpy as np
        from engine.render import _load_image_pattern

        engine = _ensure_viewer_registry(engine_getter())
        finish_type = _finish_viewer_kind_alias(finish_type)
        if not finish_type:
            raise ValueError("finish_type must be base, pattern, or monolithic")

        shape = (size, size)
        mask = np.ones(shape, dtype=np.float32)
        r, g, b = _finish_viewer_base_color(finish_type, finish_id)
        paint = np.zeros((size, size, 4), dtype=np.float32)
        paint[:, :, 0] = r
        paint[:, :, 1] = g
        paint[:, :, 2] = b
        paint[:, :, 3] = 1.0

        spec = np.zeros((size, size, 4), dtype=np.float32)
        spec[:, :, 0] = 5
        spec[:, :, 1] = 100
        spec[:, :, 2] = 16
        spec[:, :, 3] = 255

        if finish_type == "base":
            base_reg = getattr(engine, "BASE_REGISTRY", {}) or {}
            mono_reg = getattr(engine, "MONOLITHIC_REGISTRY", {}) or {}
            if finish_id not in base_reg and finish_id in mono_reg:
                return _finish_viewer_render_maps("monolithic", finish_id, size, seed)
            entry = base_reg.get(finish_id)
            if not isinstance(entry, dict):
                raise ValueError(f"Unknown base finish: {finish_id}")
            m_val = float(entry.get("M", 5))
            r_val = float(entry.get("R", 100))
            cc_val = float(entry.get("CC", 16))
            paint_fn = entry.get("paint_fn")
            if callable(paint_fn):
                paint = paint_fn(paint, shape, mask, seed, 1.0, 0.0)
                paint = np.asarray(paint, dtype=np.float32)
                if paint.ndim == 3 and paint.shape[2] == 3:
                    paint = np.dstack([paint, np.ones(shape, dtype=np.float32)])
            spec[:, :, 0] = m_val
            spec[:, :, 1] = r_val
            spec[:, :, 2] = cc_val
            base_spec_fn = entry.get("base_spec_fn")
            if callable(base_spec_fn):
                spec_result = base_spec_fn(shape, seed + abs(hash(finish_id)) % 10000, 1.0, m_val, r_val)
                spec = normalize_spec_result_to_rgba(
                    spec_result,
                    shape,
                    default_m=m_val,
                    default_r=r_val,
                    default_cc=cc_val,
                    strict_shapes=False,
                )
            return paint, spec

        if finish_type == "pattern":
            pattern_reg = getattr(engine, "PATTERN_REGISTRY", {}) or {}
            entry = pattern_reg.get(finish_id)
            if not isinstance(entry, dict):
                raise ValueError(f"Unknown pattern finish: {finish_id}")
            texture_fn = entry.get("texture_fn")
            paint_fn = entry.get("paint_fn")
            image_path = entry.get("image_path")
            spec[:, :, 0] = 150
            spec[:, :, 1] = 62
            spec[:, :, 2] = 16
            pattern_val = None
            if image_path and not callable(texture_fn):
                pattern_val = _load_image_pattern(image_path, shape, scale=1.0, rotation=0.0)
            elif callable(texture_fn):
                tex = texture_fn(shape, mask, seed, 1.0)
                if isinstance(tex, dict):
                    pattern_val = tex.get("pattern_val")
                    m_pat = tex.get("M_pattern", pattern_val)
                    r_pat = tex.get("R_pattern", pattern_val)
                    cc_pat = tex.get("CC_pattern", pattern_val)
                    m_range = float(tex.get("M_range", 95))
                    r_range = float(tex.get("R_range", 70))
                    cc_range = float(tex.get("CC_range", 30))
                    if m_pat is not None:
                        spec[:, :, 0] = np.clip(90 + np.asarray(m_pat, dtype=np.float32) * m_range, 0, 255)
                    if r_pat is not None:
                        spec[:, :, 1] = np.clip(120 - np.asarray(r_pat, dtype=np.float32) * r_range, 15, 255)
                    if cc_pat is not None:
                        spec[:, :, 2] = np.clip(16 + (1.0 - np.asarray(cc_pat, dtype=np.float32)) * cc_range, 16, 255)
                else:
                    pattern_val = tex
            if pattern_val is not None:
                pat = np.clip(np.asarray(pattern_val, dtype=np.float32), 0, 1)
                if pat.shape == shape:
                    paint[:, :, :3] = np.clip(paint[:, :, :3] * (0.40 + pat[:, :, None] * 0.92), 0, 1)
                    if not callable(texture_fn):
                        spec[:, :, 0] = np.clip(80 + pat * 130, 0, 255)
                        spec[:, :, 1] = np.clip(145 - pat * 95, 15, 255)
                        spec[:, :, 2] = np.clip(16 + (1.0 - pat) * 40, 16, 255)
            if callable(paint_fn):
                paint = paint_fn(paint, shape, mask, seed, 0.75, 0.0)
                paint = np.asarray(paint, dtype=np.float32)
                if paint.ndim == 3 and paint.shape[2] == 3:
                    paint = np.dstack([paint, np.ones(shape, dtype=np.float32)])
            return paint, spec

        mono = getattr(engine, "MONOLITHIC_REGISTRY", {}) or {}
        entry = mono.get(finish_id)
        dynamic_prefixes = ("grad_", "grad3_", "gradm_", "ghostg_", "clr_", "cs_duo_", "mc_")
        if entry is None and finish_id.startswith(dynamic_prefixes):
            try:
                from finish_colors_lookup import get_finish_colors
                colors = get_finish_colors(finish_id)
            except Exception:
                colors = None
            if colors and hasattr(engine, "render_generic_finish"):
                zone_fake = {"finish": finish_id, "finish_colors": colors}
                spec_out, paint_out = engine.render_generic_finish(
                    finish_id, zone_fake, paint, shape, mask, seed, 1.0, 1.0, 0.0
                )
                spec = normalize_spec_result_to_rgba(spec_out, shape, strict_shapes=False)
                if spec is None:
                    spec = np.zeros((size, size, 4), dtype=np.float32)
                    spec[:, :, 1] = 100
                    spec[:, :, 2] = 16
                    spec[:, :, 3] = 255
                return np.asarray(paint_out, dtype=np.float32), spec
        if entry is None:
            raise ValueError(f"Unknown monolithic finish: {finish_id}")
        spec_fn, paint_fn = _entry_spec_paint(entry)
        if not callable(spec_fn) or not callable(paint_fn):
            raise ValueError(f"Finish has no viewer renderer: {finish_id}")
        spec = normalize_spec_result_to_rgba(
            invoke_monolithic_spec_fn(spec_fn, shape, mask, seed, 1.0, reg_entry=entry),
            shape,
            strict_shapes=True,
        )
        if spec is None:
            raise ValueError(f"Spec renderer returned no data: {finish_id}")
        painted = paint_fn(paint, shape, mask, seed, 1.0, 0.10)
        return np.asarray(painted, dtype=np.float32), spec

    @app.route('/api/finish-viewer/mono/<finish_id>', methods=['GET'])
    def api_finish_viewer_mono(finish_id):
        """Render a monolithic finish as paint/spec PNG data URLs for the material viewer."""
        if not rate_limit("finish-viewer-mono", max_per_second=4):
            return jsonify({"success": False, "error": "rate_limited"}), 429
        try:
            import numpy as np

            engine = _ensure_viewer_registry(engine_getter())
            size = max(128, min(2048, safe_int(request.args.get("size"), 1024)))
            seed = safe_int(request.args.get("seed"), 9101)
            mono = getattr(engine, "MONOLITHIC_REGISTRY", {}) or {}
            if finish_id not in mono:
                return jsonify({"success": False, "error": f"Unknown monolithic: {finish_id}"}), 404
            entry = mono[finish_id]
            spec_fn, paint_fn = _entry_spec_paint(entry)
            if not callable(spec_fn) or not callable(paint_fn):
                return jsonify({"success": False, "error": f"Finish has no viewer renderer: {finish_id}"}), 500

            t0 = time.perf_counter()
            shape = (size, size)
            mask = np.ones(shape, dtype=np.float32)
            spec = normalize_spec_result_to_rgba(
                invoke_monolithic_spec_fn(spec_fn, shape, mask, seed, 1.0, reg_entry=entry),
                shape,
                strict_shapes=True,
            )
            if spec is None:
                return jsonify({"success": False, "error": f"Spec renderer returned no data: {finish_id}"}), 500
            paint = np.ones((size, size, 3), dtype=np.float32) * 0.5
            painted = np.asarray(paint_fn(paint, shape, mask, seed, 1.0, 0.10), dtype=np.float32)
            if painted.ndim == 2:
                painted = np.dstack([painted] * 3)
            if painted.ndim == 3 and painted.shape[2] > 3:
                painted = painted[:, :, :3]
            paint_url, spec_url = _finish_viewer_encode_maps(painted[:, :, :3], spec[:, :, :4])
            return jsonify({
                "success": True,
                "id": finish_id,
                "size": size,
                "seed": seed,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "paint": paint_url,
                "spec": spec_url,
            })
        except Exception as e:
            logger.error(f"Finish viewer render error {finish_id}: {e}\n{traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/finish-viewer/render/<finish_type>/<finish_id>', methods=['GET'])
    def api_finish_viewer_render(finish_type, finish_id):
        """Render any live registry finish as paint/spec PNG data URLs for the material viewer."""
        if not rate_limit("finish-viewer-render", max_per_second=4):
            return jsonify({"success": False, "error": "rate_limited"}), 429
        try:
            size = max(128, min(2048, safe_int(request.args.get("size"), 1024)))
            seed = safe_int(request.args.get("seed"), 9101)
            kind = _finish_viewer_kind_alias(finish_type)
            if not kind:
                return jsonify({"success": False, "error": f"Unknown finish type: {finish_type}"}), 400
            t0 = time.perf_counter()
            paint, spec = _finish_viewer_render_maps(kind, finish_id, size, seed)
            paint_url, spec_url = _finish_viewer_encode_maps(paint, spec)
            return jsonify({
                "success": True,
                "id": finish_id,
                "type": kind,
                "size": size,
                "seed": seed,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "paint": paint_url,
                "spec": spec_url,
            })
        except Exception as e:
            logger.error(f"Finish viewer render error {finish_type}/{finish_id}: {e}\n{traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
