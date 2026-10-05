"""Lightweight diagnostic routes for Shokker Paint Booth.

Extracted from server.py to reduce routine reads of the server monolith while
preserving the exact public URLs.
"""

from __future__ import annotations

import gc
import os
import platform
import sys
import time

from flask import Response, current_app, g, jsonify, request
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def _registry_counts(engine):
    return {
        "bases": len(getattr(engine, 'BASE_REGISTRY', {})) if engine else 0,
        "patterns": len(getattr(engine, 'PATTERN_REGISTRY', {})) if engine else 0,
        "monolithics": len(getattr(engine, 'MONOLITHIC_REGISTRY', {})) if engine else 0,
        "fusions": len(getattr(engine, 'FUSION_REGISTRY', {})) if engine else 0,
    }


def _memory_rss_mb():
    try:
        import resource as _res  # POSIX only
        return round(_res.getrusage(_res.RUSAGE_SELF).ru_maxrss / 1024, 1)
    except Exception:
        try:
            import psutil as _ps  # type: ignore
            return round(_ps.Process(os.getpid()).memory_info().rss / (1024 * 1024), 1)
        except Exception:
            return None


def _package_versions():
    versions = {}
    for pkg in ("numpy", "Pillow", "flask", "flask_cors", "psd_tools"):
        try:
            mod = __import__(pkg if pkg != "Pillow" else "PIL")
            versions[pkg] = getattr(mod, "__version__", "unknown")
        except Exception:
            versions[pkg] = None
    return versions


def register_diagnostics_routes(
    app,
    *,
    engine_getter,
    version: str = "6.2.0",
    engine_version: str = "unknown",
    build_id: str = "unknown",
    server_start_time_getter=None,
    gpu_info_func=None,
    logger=None,
    render_stats=None,
    render_stats_lock=None,
    request_count_getter=None,
    recent_renders=None,
    recent_renders_lock=None,
    recent_errors=None,
    recent_errors_lock=None,
    server_dir_getter=None,
    thumbnail_dir_getter=None,
) -> None:
    """Register small health/debug endpoints on the provided Flask app."""

    def uptime_s():
        if server_start_time_getter is not None:
            return int(time.time() - server_start_time_getter())
        return int(time.time() - getattr(app, '_start_time', time.time()))

    def gpu_info():
        return gpu_info_func() if gpu_info_func is not None else {}

    def log_error(message):
        if logger is not None:
            logger.error(message)

    def render_stats_snapshot():
        if render_stats is None:
            return {}
        if render_stats_lock is not None:
            with render_stats_lock:
                return dict(render_stats)
        return dict(render_stats)

    def recent_renders_count():
        if recent_renders is None:
            return 0
        if recent_renders_lock is not None:
            with recent_renders_lock:
                return len(recent_renders)
        return len(recent_renders)

    def recent_errors_snapshot():
        if recent_errors is None:
            return []
        if recent_errors_lock is not None:
            with recent_errors_lock:
                return list(recent_errors)
        return list(recent_errors)

    @app.route('/api/health', methods=['GET'])
    def api_health():
        """Server health check endpoint."""
        rid = getattr(g, '_rid', '-')
        try:
            engine = engine_getter()
            counts = _registry_counts(engine)
            return jsonify({
                "status": "ok",
                "uptime_seconds": round(float(uptime_s()), 1),
                "registries": {
                    "bases": counts["bases"],
                    "patterns": counts["patterns"],
                    "monolithics": counts["monolithics"],
                },
                "version": version,
                "rid": rid,
            })
        except Exception as e:
            log_error(f"[health rid={rid}] {e}")
            return jsonify({"status": "error", "error": str(e), "rid": rid}), 500

    @app.route('/api/ping', methods=['GET'])
    def api_ping():
        """Tiny health probe - returns plaintext 'pong' for fastest possible check."""
        return Response("pong", mimetype='text/plain')

    @app.route('/api/diagnostics/swallowed', methods=['GET'])
    def api_diagnostics_swallowed():
        """[2026-09-05 codebase-health F4] Counters for every deliberately-swallowed exception
        site (server_routes/_swallow.py). 'Weird problem for no reason' -> 'this handler fired
        41 times in your session'. ?reset=1 clears the counters."""
        try:
            from server_routes import _swallow
            if request.args.get('reset') == '1':
                _swallow.reset()
            return jsonify({"status": "ok", **_swallow.snapshot()})
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500

    @app.route('/api/echo', methods=['POST'])
    def api_echo():
        """Debug echo - returns the JSON body and request headers verbatim."""
        rid = getattr(g, '_rid', '-')
        try:
            body = request.get_json(silent=True) or {}
        except Exception:
            body = {}
        # SEC-D (2026-05-30): do NOT reflect ALL request headers — that discloses
        # the internal-gate header + any Authorization/Cookie the browser attached
        # (readable cross-origin under the current wildcard-CORS posture). Whitelist
        # only the safe diagnostics headers.
        safe_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() in ("content-type", "content-length")
        }
        return jsonify({
            "body": body,
            "headers": safe_headers,
            "method": request.method,
            "remote_addr": request.remote_addr,
            "rid": rid,
        })

    @app.route('/api/stats', methods=['GET'])
    def api_stats():
        """Comprehensive server stats: uptime, render count, cache hits, memory."""
        rid = getattr(g, '_rid', '-')
        try:
            renders = render_stats_snapshot()
            req_count = request_count_getter() if request_count_getter is not None else 0
            err_count = len(recent_errors_snapshot())
            engine = engine_getter()

            return jsonify({
                "version": version,
                "engine": engine_version,
                "build": build_id,
                "uptime_s": uptime_s(),
                "request_count": req_count,
                "total_renders": renders.get("total_renders", 0),
                "total_render_time_s": round(renders.get("total_render_time", 0.0), 2),
                "cache_hits": renders.get("cache_hits", 0),
                "cache_misses": renders.get("cache_misses", 0),
                "recent_renders_logged": recent_renders_count(),
                "recent_errors_logged": err_count,
                "memory_rss_mb": _memory_rss_mb(),
                "gc_objects": len(gc.get_objects()),
                "registries": _registry_counts(engine),
                "gpu": gpu_info(),
                "rid": rid,
            })
        except Exception as e:
            log_error(f"[stats rid={rid}] {e}")
            return jsonify({"error": str(e), "rid": rid}), 500

    # NOTE: the user-facing one-click "Report a Problem" payload now lives in
    # server_routes/diagnostics_report_routes.py and OWNS the /api/diagnostics
    # URL (it adds redacted log tails + privacy-safe license boolean). This
    # older endpoint stays available at /api/diagnostics-legacy so the two
    # don't collide on the same Flask rule/endpoint at registration time.
    @app.route('/api/diagnostics-legacy', methods=['GET'])
    def api_diagnostics():
        """Bug-report diagnostics payload: packages, GPU, registries, endpoints."""
        rid = getattr(g, '_rid', '-')
        endpoints = []
        try:
            for rule in app.url_map.iter_rules():
                endpoints.append({
                    "rule": str(rule),
                    "methods": sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS")),
                })
        except Exception as _spb_ex:
            _spb_swallow('api_diagnostics@L220', _spb_ex)
        engine = engine_getter()
        return jsonify({
            "version": version,
            "engine_version": engine_version,
            "build_id": build_id,
            "python": {
                "version": sys.version.split()[0],
                "implementation": platform.python_implementation(),
                "executable": sys.executable,
            },
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
            },
            "packages": _package_versions(),
            "gpu": gpu_info(),
            "registries": _registry_counts(engine),
            "endpoints_count": len(endpoints),
            "endpoints": endpoints,
            "recent_errors": recent_errors_snapshot(),
            "uptime_s": uptime_s(),
            "rid": rid,
        })

    @app.route('/api/server-info', methods=['GET'])
    def api_server_info():
        """Lightweight server info - version, port, paths. Cheaper than /status."""
        rid = getattr(g, '_rid', '-')
        server_dir = server_dir_getter() if server_dir_getter is not None else None
        thumbnail_dir = thumbnail_dir_getter() if thumbnail_dir_getter is not None else None
        payload = {
            "version": version,
            "engine": engine_version,
            "build": build_id,
            "pid": os.getpid(),
            "port": int(os.environ.get('SHOKKER_PORT', 59876)),
            "server_dir": server_dir,
            "thumbnail_dir": thumbnail_dir,
            "uptime_s": uptime_s(),
            "rid": rid,
        }
        identity_getter = current_app.config.get("SPB_RUNTIME_IDENTITY_GETTER")
        if callable(identity_getter):
            try:
                payload.update(identity_getter())
            except Exception as error:  # diagnostic proof must never break health
                log_error(f"[server-info rid={rid}] runtime identity failed: {error}")
        return jsonify(payload)
