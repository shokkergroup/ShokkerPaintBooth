"""Guest Designer catalog routes — picker merge for shipped designer plates."""

from __future__ import annotations

from flask import jsonify

from engine.paint_v2.guest_designers import get_catalog_for_picker


def register_guest_designer_routes(app, *, logger=None):
    @app.route("/api/guest-designers/catalog", methods=["GET"])
    def api_guest_designers_catalog():
        try:
            entries = get_catalog_for_picker()
            groups: dict = {}
            for entry in entries:
                group = entry.get("group") or "Guest Designer"
                groups.setdefault(group, []).append(entry["id"])
            return jsonify({"success": True, "entries": entries, "groups": groups})
        except Exception as e:
            if logger:
                logger.error(f"[guest-designers] catalog error: {e}")
            return jsonify({"error": str(e)}), 500
