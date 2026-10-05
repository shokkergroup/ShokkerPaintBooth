"""Persistent config routes for Shokker Paint Booth."""

from __future__ import annotations

import os

from flask import jsonify, request


def register_config_routes(
    app,
    *,
    load_config,
    save_config,
    logger,
    config_path=None,
    external_write_guard=None,
) -> None:
    """Register config GET/POST endpoints while keeping storage helpers in server.py."""
    from server_routes.finish_preferences import register_finish_preferences
    register_finish_preferences(app, external_write_guard=external_write_guard)

    @app.route('/config', methods=['GET'])
    def get_config():
        """Return current config."""
        logger.debug("[config] GET config requested")
        return jsonify(load_config())

    @app.route('/config', methods=['POST'])
    def set_config():
        """Update config. Merges with existing config."""
        try:
            updates = request.get_json(silent=True)
            if not isinstance(updates, dict) or not updates:
                return jsonify({"error": "No JSON body. Send a JSON object with config fields to update."}), 400

            if external_write_guard is not None and config_path is not None:
                denial = external_write_guard(config_path, "config-save")
                if denial:
                    return jsonify(denial), 403

            logger.info(f"[config] POST update: keys={list(updates.keys())}")
            # [2026-09-05 codebase-health S3] load -> mutate -> save is exclusive per file:
            # with THREADED=True two settings saves in flight used to be last-writer-wins.
            from engine.atomic_io import file_lock
            with file_lock(config_path):
                cfg = load_config()

                if "iracing_id" in updates:
                    cfg["iracing_id"] = str(updates["iracing_id"])
                if "live_link_enabled" in updates:
                    cfg["live_link_enabled"] = bool(updates["live_link_enabled"])
                if "active_car" in updates:
                    cfg["active_car"] = updates["active_car"]
                if "use_custom_number" in updates:
                    cfg["use_custom_number"] = bool(updates["use_custom_number"])
                if "car_paths" in updates:
                    cfg.setdefault("car_paths", {}).update(updates["car_paths"])
                if "imported_spec_path" in updates:
                    v = updates["imported_spec_path"]
                    cfg["imported_spec_path"] = str(v).strip() if v else None

                warnings = []
                for car, path in cfg.get("car_paths", {}).items():
                    if not os.path.isdir(path):
                        warnings.append(f"Path for '{car}' not found: {path}")

                save_config(cfg)
            result = {"success": True, "config": cfg}
            if warnings:
                result["warnings"] = warnings
            return jsonify(result)

        except Exception as e:
            return jsonify({"error": str(e)}), 500
