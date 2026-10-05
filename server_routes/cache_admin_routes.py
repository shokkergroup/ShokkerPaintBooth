"""Cache and thumbnail admin routes for Shokker Paint Booth."""

from __future__ import annotations

import os
import shutil

from flask import g, jsonify
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def _clear_engine_zone_cache():
    try:
        import shokker_engine_v2 as _eng
        if hasattr(_eng.build_multi_zone, '_zone_cache'):
            cleared = len(_eng.build_multi_zone._zone_cache)
            _eng.build_multi_zone._zone_cache.clear()
            return cleared
    except Exception as _spb_ex:
        _spb_swallow('_clear_engine_zone_cache@L18', _spb_ex)
    return 0


def register_cache_admin_routes(
    app,
    *,
    swatch_cache,
    swatch_cache_lock,
    finish_catalog_cache_clear,
    finish_meta_cache_clear,
    psd_cache_getter,
    prev_spec_cache_getter,
    prev_spec_cache_setter,
    thumbnail_dir_getter,
    validate_thumbnail_regen_request,
    queue_thumbnail_regen,
    clear_zone_cache=_clear_engine_zone_cache,
    logger=None,
    external_write_guard=None,
) -> None:
    """Register cache clear, reload, thumbnail regen, and legacy debug admin routes."""

    @app.route('/api/clear-cache', methods=['POST'])
    def api_clear_cache():
        """Clear in-memory + disk swatch caches. Use after code changes or for hard reset."""
        swatch_disk_dir = os.path.join(thumbnail_dir_getter(), 'swatch_cache')
        if external_write_guard is not None:
            denial = external_write_guard(swatch_disk_dir, "swatch-cache-clear")
            if denial:
                return jsonify(denial), 403
        if logger is not None:
            logger.info("[clear-cache] Cache clear requested")

        with swatch_cache_lock:
            swatch_cache.clear()
        finish_catalog_cache_clear()

        cleared_disk = 0
        if os.path.isdir(swatch_disk_dir):
            try:
                shutil.rmtree(swatch_disk_dir)
                cleared_disk = 1
            except Exception as _spb_ex:
                _spb_swallow('api_clear_cache@L62', _spb_ex)
        return jsonify({"status": "ok", "message": f"Caches cleared (memory + disk={cleared_disk})."})

    @app.route('/api/thumb-regen/<finish_type>/<finish_id>', methods=['POST'])
    def regen_thumbnail(finish_type, finish_id):
        """Force regeneration of a specific thumbnail after hot-adding or editing a finish."""
        try:
            normalized_type = validate_thumbnail_regen_request(finish_type, finish_id)
        except Exception as e:
            if isinstance(e, ValueError) and str(e).startswith("Invalid finish_type"):
                status_code = 400
            elif isinstance(e, ValueError) and str(e).startswith("Unknown thumbnail"):
                status_code = 404
            else:
                status_code = 500
            if logger is not None:
                logger.warning(f"[thumb-regen] Rejected {finish_type}/{finish_id}: {e}")
            return jsonify({
                "error": "thumbnail_regen_failed",
                "finish_type": finish_type,
                "id": finish_id,
                "message": str(e),
            }), status_code

        if logger is not None:
            logger.info(f"[thumb-regen] Queuing regen: {normalized_type}/{finish_id}")
        if external_write_guard is not None:
            denial = external_write_guard(thumbnail_dir_getter(), "thumbnail-regenerate")
            if denial:
                return jsonify(denial), 403
        queue_thumbnail_regen(normalized_type, finish_id)
        return jsonify({"status": "queued", "finish_type": normalized_type, "id": finish_id})

    @app.route('/debug-rotation-log', methods=['GET'])
    def debug_rotation_log():
        """Return the old rotation debug endpoint response for compatibility."""
        return "Debug rotation logging removed in build 29", 200, {'Content-Type': 'text/plain'}

    @app.route('/api/reload-engine', methods=['POST'])
    def api_reload_engine():
        """Soft-reload runtime caches without re-importing Python source files."""
        rid = getattr(g, '_rid', '-')
        try:
            finish_catalog_cache_clear()
            finish_meta_cache_clear()
            cleared_zones = clear_zone_cache()
            with swatch_cache_lock:
                sw_count = len(swatch_cache)
                swatch_cache.clear()
            if logger is not None:
                logger.info(f"[reload-engine rid={rid}] cleared {sw_count} swatches, {cleared_zones} zone cache entries")
            return jsonify({
                "ok": True,
                "cleared": {
                    "swatches": sw_count,
                    "zones": cleared_zones,
                    "finish_meta": True,
                    "finish_data_cache": True,
                },
                "rid": rid,
            })
        except Exception as e:
            if logger is not None:
                logger.error(f"[reload-engine rid={rid}] {e}")
            return jsonify({"error": str(e), "rid": rid}), 500

    @app.route('/api/clear-cache/<cache_name>', methods=['POST'])
    def api_clear_cache_named(cache_name):
        """Granular cache clearing for dev/admin recovery."""
        rid = getattr(g, '_rid', '-')
        cleared = {}
        try:
            name = (cache_name or "").lower().strip()
            if name in ("swatch", "swatches", "all"):
                with swatch_cache_lock:
                    cleared["swatch"] = len(swatch_cache)
                    swatch_cache.clear()
            if name in ("finish_data", "finish-data", "all"):
                cleared["finish_data"] = 1 if finish_catalog_cache_clear() else 0
            if name in ("zone", "zones", "all"):
                cleared["zone"] = clear_zone_cache()
            if name in ("spec_delta", "spec-delta", "all"):
                cleared["spec_delta"] = 1 if prev_spec_cache_getter() is not None else 0
                prev_spec_cache_setter(None)
            if name in ("psd", "all"):
                psd_cache = psd_cache_getter()
                cleared["psd"] = len(psd_cache)
                psd_cache.clear()
            if name in ("finish_meta", "finish-meta", "all"):
                finish_meta_cache_clear()
                cleared["finish_meta"] = 1
            if not cleared:
                return jsonify({
                    "error": f"Unknown cache: {cache_name}",
                    "valid": ["swatch", "finish_data", "zone", "spec_delta", "psd", "finish_meta", "all"],
                    "rid": rid,
                }), 400
            return jsonify({"ok": True, "cleared": cleared, "rid": rid})
        except Exception as e:
            if logger is not None:
                logger.error(f"[clear-cache rid={rid}] {e}")
            return jsonify({"error": str(e), "rid": rid}), 500
