"""Core status routes for Shokker Paint Booth.

These lightweight endpoints are polled or used for boot diagnostics. Keeping
them out of server.py lets agents inspect status behavior without reading the
server monolith.
"""

from __future__ import annotations

import os
import time

from flask import jsonify


def register_system_status_routes(
    app,
    *,
    engine_getter,
    load_config,
    license_getter,
    version: str,
    build_id: str,
    server_dir_getter,
    server_start_time_getter,
    gpu_info_func,
    logger=None,
) -> None:
    """Register /build-check, /health, and /status routes."""

    def gpu_info():
        return gpu_info_func() if gpu_info_func is not None else {}

    def log_debug(message):
        if logger is not None:
            logger.debug(message)

    @app.route('/build-check', methods=['GET'])
    def build_check():
        """Diagnostic endpoint used by frequent UI polling."""
        log_debug("[build-check] Health check requested")
        return jsonify({
            "build": build_id,
            "version": version,
            "status": "running",
            "debug": False,
            "engine": "Shokker Engine V5 - Modular Architecture",
            "pid": os.getpid(),
            "port": int(os.environ.get('SHOKKER_PORT', 59876)),
            "server_dir": server_dir_getter(),
            "gpu": gpu_info(),
        })

    @app.route('/health', methods=['GET'])
    def health():
        """Lightweight health check - no heavy computation."""
        return jsonify({
            "ok": True,
            "version": version,
            "uptime_s": int(time.time() - server_start_time_getter()),
        })

    @app.route('/status', methods=['GET'])
    def status():
        """Server heartbeat plus engine capabilities."""
        log_debug("[status] Heartbeat requested")
        cfg = load_config()
        engine = engine_getter()
        license_key, license_active = license_getter()
        return jsonify({
            "status": "online",
            "version": version,
            "build": build_id,
            "pid": os.getpid(),
            "port": int(os.environ.get('SHOKKER_PORT', 59876)),
            "engine": "Shokker Engine v6.0 PRO - 24K Arsenal",
            "capabilities": {
                "bases": list(engine.BASE_REGISTRY.keys()),
                "patterns": list(engine.PATTERN_REGISTRY.keys()),
                "monolithics": list(engine.MONOLITHIC_REGISTRY.keys()),
                "legacy_finishes": list(engine.FINISH_REGISTRY.keys()),
                "base_count": len(engine.BASE_REGISTRY),
                "pattern_count": len(engine.PATTERN_REGISTRY),
                "monolithic_count": len(engine.MONOLITHIC_REGISTRY),
                "combination_count": len(engine.BASE_REGISTRY) * len(engine.PATTERN_REGISTRY),
                "features": {
                    "helmet_spec": False,
                    "suit_spec": False,
                    "wear_slider": True,
                    "export_zip": True,
                    "matching_set": False,
                    "dual_spec": True,
                    "live_link": True,
                    "swatch_highres_mono": True,
                },
            },
            "config": {
                "iracing_id": cfg.get("iracing_id", ""),
                "live_link_enabled": cfg.get("live_link_enabled", False),
                "use_custom_number": cfg.get("use_custom_number", True),  # 2026-10-02: the header restored Custom Number on EVERY launch because /status never carried it (undefined !== false)
                "active_car": cfg.get("active_car"),
                "car_paths": cfg.get("car_paths", {}),
            },
            "license": {
                "active": license_active,
                "key_masked": (license_key[:12] + "****") if license_key else "",
            },
            "gpu": gpu_info(),
        })
