"""Saved custom-finish metadata routes for Shokker Paint Booth."""

from __future__ import annotations

import traceback
from datetime import datetime

from flask import jsonify, request
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def _weights_as_floats(weights):
    return [float(w) for w in weights]


def _next_custom_finish_id(finishes):
    existing_nums = []
    for finish in finishes:
        cid = finish.get('id', '')
        if isinstance(cid, str) and cid.startswith('custom_'):
            try:
                existing_nums.append(int(cid.split('_')[1]))
            except (IndexError, ValueError) as _spb_ex:
                _spb_swallow('_next_custom_finish_id@L22', _spb_ex)
    return f"custom_{max(existing_nums, default=0) + 1:03d}"


def register_custom_finish_routes(
    app,
    *,
    load_custom_finishes,
    save_custom_finishes,
    now_func=datetime.now,
    logger,
    storage_path=None,
    external_write_guard=None,
) -> None:
    """Register saved custom finish CRUD routes."""

    @app.route('/api/save-custom-finish', methods=['POST'])
    def api_save_custom_finish():
        """Save a custom mixed finish recipe."""
        logger.info("[save-custom-finish] Save custom finish requested")
        try:
            if external_write_guard is not None and storage_path is not None:
                denial = external_write_guard(storage_path, "custom-finish-save")
                if denial:
                    return jsonify(denial), 403
            data = request.get_json(force=True)
            # EH-B (2026-05-30): non-dict JSON body -> clean 400, not a 500 from the
            # catch-all below.
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            name = str(data.get('name') or '').strip()
            finish_ids = data.get('finish_ids', [])
            weights = data.get('weights', [])

            if not name:
                return jsonify({"error": "Name is required"}), 400
            if len(finish_ids) < 2 or len(finish_ids) > 3:
                return jsonify({"error": "Need 2-3 finish_ids"}), 400
            if len(finish_ids) != len(weights):
                return jsonify({"error": "finish_ids and weights must match in length"}), 400

            weights = _weights_as_floats(weights)
            weight_sum = sum(weights)
            if weight_sum > 0:
                weights = [round(w / weight_sum, 4) for w in weights]
            else:
                weights = [round(1.0 / len(weights), 4)] * len(weights)

            finishes = load_custom_finishes()
            new_id = _next_custom_finish_id(finishes)
            entry = {
                "id": new_id,
                "name": name,
                "finish_ids": finish_ids,
                "weights": weights,
                "mix_mode": data.get('mix_mode', 'both'),
                "created": now_func().isoformat(),
            }
            finishes.append(entry)
            save_custom_finishes(finishes)

            logger.info(f"[mixer] Saved custom finish: {new_id} = {name}")
            return jsonify(entry)
        except Exception as e:
            logger.error(f"[save-custom-finish] Error: {e}")
            logger.error(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    @app.route('/api/custom-finishes', methods=['GET'])
    def api_custom_finishes():
        """Return the list of saved custom mixed finishes."""
        try:
            return jsonify(load_custom_finishes())
        except Exception as e:
            logger.error(f"[custom-finishes] Error: {e}")
            return jsonify([])

    @app.route('/api/delete-custom-finish', methods=['POST'])
    def api_delete_custom_finish():
        """Delete a saved custom finish by ID."""
        try:
            if external_write_guard is not None and storage_path is not None:
                denial = external_write_guard(storage_path, "custom-finish-delete")
                if denial:
                    return jsonify(denial), 403
            data = request.get_json(force=True)
            delete_id = str(data.get('id') or '').strip()
            if not delete_id:
                return jsonify({"error": "id is required"}), 400
            finishes = load_custom_finishes()
            original_count = len(finishes)
            finishes = [f for f in finishes if f.get('id') != delete_id]
            if len(finishes) == original_count:
                return jsonify({"error": f"Custom finish '{delete_id}' not found"}), 404
            save_custom_finishes(finishes)
            return jsonify({"success": True, "deleted": delete_id})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
