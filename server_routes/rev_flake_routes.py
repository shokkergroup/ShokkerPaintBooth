"""[SPB-REV-FLAKE 2026-10-10] Flake Studio routes (lane REV-FLAKE). Read-only maths: nothing here touches the disk or any output folder.

POST /api/flake/preview  {params, crop:[x,y,w,h] canvas px, paint_png?: data URL of that crop of the car's paint, base_rgb?: [r,g,b], levels?: 4}
     -> the crop rendered by engine/rev_flake.py (the SAME code the render runs, so preview pixels == render pixels for that crop),
        box-filter mips 0..levels (paint + spec PNGs), the survival meter (spec texel signal per mip vs the owner-fitted bar),
        the flake feature size vs the owner-fitted glitter bar.
POST /api/flake/fit      {params} -> fit_sim_safe(params): the coarse band size + mix that keep the flake at mip 2.
GET  /api/flake/info     -> version, bars + their provenance, kill switch state.
Kill switch: env SPB_FLAKE_OFF=1 -> {"ok": false, "off": true}.
"""
import base64
import io
import time

import numpy as np
from flask import jsonify, request


def _png(arr):
    from PIL import Image
    a = np.clip(np.rint(arr), 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, format="PNG", compress_level=1)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _decode_png(s):
    from PIL import Image
    if not isinstance(s, str) or "," not in s:
        return None
    try:
        return np.asarray(Image.open(io.BytesIO(base64.b64decode(s.split(",", 1)[1]))).convert("RGB"))
    except Exception:
        return None


def register_rev_flake_routes(app):
    from engine import rev_flake as rf

    @app.route("/api/flake/info", methods=["GET"])
    def rev_flake_info():
        return jsonify({"ok": not rf.disabled(), "off": rf.disabled(), "version": rf.VERSION, "S_flat_bar": rf.S_FLAT_BAR, "L_big_frac": rf.L_BIG_FRAC,
                        "provenance": "owner verdicts on the 256 px Spec Sculpt thumbnails (_audit/spec_sculpt_audit.json): flat bar 4.30 (15/18 agree), glitter bar 2.74/256 of the sheet (22/24 agree)"})

    @app.route("/api/flake/fit", methods=["POST"])
    def rev_flake_fit():
        if rf.disabled():
            return jsonify({"ok": False, "off": True})
        body = request.get_json(silent=True) or {}
        p = rf.norm(body.get("params"))
        if p is None:
            return jsonify({"ok": False, "error": "no params"}), 400
        t0 = time.time()
        res = rf.fit_sim_safe(p)
        res["ms"] = round((time.time() - t0) * 1000)
        return jsonify(dict(res, ok=bool(res.get("ok")), fitted=True, bar=rf.S_FLAT_BAR))

    @app.route("/api/flake/preview", methods=["POST"])
    def rev_flake_preview():
        if rf.disabled():
            return jsonify({"ok": False, "off": True})
        t0 = time.time()
        body = request.get_json(silent=True) or {}
        p = rf.norm(body.get("params"))
        if p is None:
            return jsonify({"ok": False, "error": "no params"}), 400
        levels = int(max(0, min(5, int(body.get("levels", 4) or 4))))
        CW, CH = p["canvas"]
        crop = body.get("crop") or [0, 0, 256, 256]
        try:
            x, y, w, h = [int(v) for v in crop[:4]]
        except Exception:
            return jsonify({"ok": False, "error": "bad crop"}), 400
        step = 1 << levels
        w = max(step * 4, min(1024, (w // step) * step)); h = max(step * 4, min(1024, (h // step) * step))
        x = max(0, min(CW - w, (x // step) * step)); y = max(0, min(CH - h, (y // step) * step))
        P = _decode_png(body.get("paint_png"))
        if P is None or P.shape[0] != h or P.shape[1] != w:
            rgb = body.get("base_rgb") or [150, 150, 155]
            P = np.empty((h, w, 3), np.float32); P[...] = np.asarray(rgb[:3], np.float32)
        P = P.astype(np.float32) / 255.0
        flds = rf.fields(p, x, y, x + w, y + h)
        paint, M, G, C = rf.compose(p, flds, P)
        # the engine writes the car TGA by truncation (float -> uint8), so the tiles do too: tile pixels == RENDER pixels (proof: flake/results.json body.endpoint)
        paint8 = np.clip(paint * 255.0, 0, 255).astype(np.uint8).astype(np.float32)
        spec8 = np.stack([np.rint(M), np.rint(G), np.rint(C)], axis=2)
        t_gen = time.time() - t0
        pc, sc = rf.mip_chain(paint8, levels), rf.mip_chain(spec8, levels)
        mt = rf.meter(p, M, G, levels)
        L = rf.corr_len(np.rint(M))
        big_px = rf.L_BIG_FRAC * CW
        mips = [{"k": k, "w": int(pc[k].shape[1]), "paint": _png(pc[k]), "spec": _png(sc[k]),
                 "metal": _png(sc[k][..., 0]), "rough": _png(sc[k][..., 1])} for k in range(levels + 1)]
        return jsonify({"ok": True, "crop": [x, y, w, h], "mips": mips, "meter": mt, "L_px": round(L, 2), "big_px": round(big_px, 1),
                        "glitter": bool(L > big_px), "gen_ms": round(t_gen * 1000), "ms": round((time.time() - t0) * 1000), "version": rf.VERSION})
