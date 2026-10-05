"""Render status and monitoring routes for Shokker Paint Booth."""

from __future__ import annotations

import time

from flask import g, jsonify, request


def _clamped_limit(value, safe_int, default=25, max_value=64):
    return max(1, min(max_value, safe_int(value, default)))


def register_render_monitoring_routes(
    app,
    *,
    render_progress,
    render_stats,
    render_stats_lock,
    recent_renders,
    recent_renders_lock,
    safe_int,
    gpu_info_func,
    logger,
) -> None:
    """Register read-only render status/statistics endpoints."""

    @app.route('/api/render-status', methods=['GET'])
    def api_render_status():
        """Return render progress in the format the JS poller expects."""
        pct = 0
        if render_progress["active"] and render_progress["total_zones"] > 0:
            pct = int((render_progress["current_zone"] / render_progress["total_zones"]) * 100)
        return jsonify({
            "active": render_progress["active"],
            "total_zones": render_progress["total_zones"],
            "current_zone": render_progress["current_zone"],
            "zone_name": render_progress["current_zone_name"],
            "phase": render_progress["phase"],
            "percent": max(5, min(95, pct)) if render_progress["active"] else 0,
            "elapsed_ms": int((time.time() - render_progress["started_at"]) * 1000)
            if render_progress["active"] else render_progress["elapsed_ms"],
        })

    @app.route('/api/render-progress', methods=['GET'])
    def api_render_progress():
        """Return current render progress for the UI progress bar."""
        return jsonify(render_progress)

    @app.route('/api/render-stats', methods=['GET'])
    def api_render_stats():
        """Return render statistics for the current session."""
        logger.debug("[render-stats] Stats requested")
        with render_stats_lock:
            total = render_stats["total_renders"]
            total_time = render_stats["total_render_time"]
            avg_time = total_time / total if total > 0 else 0.0
            zone_avgs = {}
            for zname, times in render_stats["zone_times"].items():
                zone_avgs[zname] = round(sum(times) / len(times), 2) if times else 0.0
            hits = render_stats["cache_hits"]
            misses = render_stats["cache_misses"]
            cache_total = hits + misses
            cache_rate = round(hits / cache_total * 100, 1) if cache_total > 0 else 0.0
            uptime = 0.0
            if render_stats["session_start"]:
                uptime = round(time.time() - render_stats["session_start"], 1)

        return jsonify({
            "total_renders": total,
            "average_render_time": round(avg_time, 2),
            "total_render_time": round(total_time, 2),
            "per_zone_avg_times": zone_avgs,
            "cache_hit_rate": cache_rate,
            "cache_hits": hits,
            "cache_misses": misses,
            "gpu": gpu_info_func(),
            "session_uptime_seconds": uptime,
        })

    @app.route('/api/recent-renders', methods=['GET'])
    def api_recent_renders():
        """Return the last N renders (preview + full) with timestamps + elapsed."""
        rid = getattr(g, '_rid', '-')
        limit = _clamped_limit(request.args.get('limit'), safe_int, default=25, max_value=64)
        with recent_renders_lock:
            items = list(recent_renders)[:limit]
        return jsonify({"count": len(items), "items": items, "rid": rid})
