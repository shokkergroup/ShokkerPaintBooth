"""License activation routes for Shokker Paint Booth.

Extracted for SPB-105 so license behavior can be inspected without reading the
full server monolith.
"""

from __future__ import annotations

from flask import jsonify, request


def register_license_routes(
    app,
    *,
    license_getter,
    license_setter,
    validate_license_key,
    save_license,
    logger,
    license_path=None,
    external_write_guard=None,
) -> None:
    """Register license status, activation, and deactivation endpoints."""

    @app.route('/license', methods=['GET', 'POST'])
    def license_endpoint():
        """Check or activate license."""
        license_key, license_active = license_getter()
        logger.info(f"[license] {request.method} request")

        if request.method == 'GET':
            return jsonify({
                "active": license_active,
                "key_masked": (license_key[:12] + "****") if license_key else "",
            })

        data = request.get_json() or {}
        # EH-A (2026-05-30): a non-dict JSON body (array/string/number) would make
        # data.get(...) raise AttributeError -> uncaught 500. Reject cleanly as 400.
        if not isinstance(data, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400
        key = (data.get('key', '') or '').strip().upper()

        if not key:
            return jsonify({"error": "No license key provided"}), 400

        if not validate_license_key(key):
            return jsonify({"error": "Invalid license key format. Expected: SHOKKER-XXXX-XXXX-XXXX"}), 400

        if external_write_guard is not None and license_path is not None:
            denial = external_write_guard(license_path, "license-activate")
            if denial:
                return jsonify(denial), 403

        # Alpha behavior: valid local format means activated.
        license_setter(key, True)
        save_license(key, True)
        logger.info(f"License activated: {key[:12]}****")

        return jsonify({
            "active": True,
            "key_masked": key[:12] + "****",
            "message": "License activated successfully!",
        })

    @app.route('/license/deactivate', methods=['POST'])
    def license_deactivate():
        """Deactivate the current license."""
        if external_write_guard is not None and license_path is not None:
            denial = external_write_guard(license_path, "license-deactivate")
            if denial:
                return jsonify(denial), 403
        license_setter('', False)
        save_license('', False)
        logger.info("License deactivated")
        return jsonify({"active": False, "message": "License deactivated."})
