"""[SPB-REV-WEAR2 2026-10-10] Race Wear layer store routes (lane REV-WEAR-2).

POST /api/rev-wear/layer  body = the binary container built by js/rev/wear/wear-ui.js (see engine/rev_wear_layer.py): decoded and kept by the
                           engine module; answers {"ok": true, "key": "<sha256[:40]>", ...}. The key is computed HERE from the bytes.
GET  /api/rev-wear/has?key=...  -> {"has": true|false} (the page asks before a render, so a server that restarted since the upload is noticed).
Later /preview-render and /render requests carry {"rw2": "<key>"} instead of 4-14 MB of base64 PNG.
Kill switch: env SPB_REV_WEAR2_OFF=1 -> both routes answer {"ok": false, "off": true} and the page keeps sending the layer inline (the old path).
Nothing here touches the disk or any output folder.
"""
from flask import jsonify, request

MAX_LAYER_BYTES = 96 * 1024 * 1024


def register_rev_wear_routes(app):
    from engine import rev_wear_layer as _rw

    @app.route("/api/rev-wear/layer", methods=["POST"])
    def rev_wear_put_layer():
        if _rw.disabled2() or _rw.disabled():
            return jsonify({"ok": False, "off": True}), 200
        try:
            request.max_content_length = MAX_LAYER_BYTES   # Flask 3.1 per-request cap (the app-wide 16 MB cap would refuse a 10 MB + 3 MB upload pair at worst)
        except Exception:
            pass
        try:
            raw = request.get_data(cache=False)
        except Exception as exc:
            return jsonify({"ok": False, "error": "unreadable body: %s" % exc}), 413
        try:
            key, ent, new = _rw.put_layer(raw)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except Exception as exc:  # never let a bad upload take the route down
            return jsonify({"ok": False, "error": "layer could not be stored: %s" % exc}), 500
        return jsonify({"ok": True, "key": key, "new": bool(new), "bytes": len(raw), "decode_ms": ent.get("ms"), "res": ent.get("res"), "store_layers": _rw.store_stats()["layers"], "store_bytes": _rw.store_stats()["bytes"]})

    @app.route("/api/rev-wear/has", methods=["GET"])
    def rev_wear_has_layer():
        if _rw.disabled2() or _rw.disabled():
            return jsonify({"ok": False, "off": True, "has": False}), 200
        return jsonify({"ok": True, "has": bool(_rw.has_layer(request.args.get("key", "")))})

    return app
