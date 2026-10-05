"""Single-finish lookup route for Shokker Paint Booth."""

from functools import lru_cache

from flask import g, jsonify


def register_finish_lookup_routes(app, *, engine_getter, id_to_display_name, logger):
    """Register finish metadata lookup route and return a cache clear function."""

    @lru_cache(maxsize=4096)
    def memo_finish_meta(finish_id):
        if not isinstance(finish_id, str) or not finish_id:
            return None
        engine = engine_getter()
        base_reg = getattr(engine, 'BASE_REGISTRY', {}) or {}
        pat_reg = getattr(engine, 'PATTERN_REGISTRY', {}) or {}
        mono_reg = getattr(engine, 'MONOLITHIC_REGISTRY', {}) or {}
        fus_reg = getattr(engine, 'FUSION_REGISTRY', {}) or {}
        if finish_id in base_reg:
            return ("base", id_to_display_name(finish_id), "base")
        if finish_id in pat_reg:
            return ("pattern", id_to_display_name(finish_id), "pattern")
        if finish_id in mono_reg:
            return ("monolithic", id_to_display_name(finish_id), "monolithic")
        if finish_id in fus_reg:
            return ("fusion", id_to_display_name(finish_id), "fusion")
        return None

    @app.route('/api/finish-by-id/<finish_id>', methods=['GET'])
    def api_finish_by_id(finish_id):
        """Return single-finish metadata: id, kind, display name, category, swatch URL."""
        rid = getattr(g, '_rid', '-')
        try:
            meta = memo_finish_meta(finish_id)
            if not meta:
                return jsonify({"error": "finish_not_found", "finish_id": finish_id, "rid": rid}), 404
            kind, name, category = meta
            return jsonify({
                "id": finish_id,
                "kind": kind,
                "name": name,
                "category": category,
                "swatch_url": f"/api/swatch/{kind}/{finish_id}",
                "rid": rid,
            })
        except Exception as e:
            logger.error(f"[finish-by-id rid={rid}] {e}")
            return jsonify({"error": str(e), "rid": rid}), 500

    return memo_finish_meta.cache_clear
