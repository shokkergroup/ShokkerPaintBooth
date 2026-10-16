"""Edit in PhotoCraft - round trip between SPB layers and a layered PSD.

Flow (all routes need the X-Shokker-Internal header):
  POST /api/photocraft/export   client sends its layer stack -> layered PSD in a work folder
                                (+ hidden spec group), PhotoCraft is launched on it
  GET  /api/photocraft/poll     "has the painter saved in PhotoCraft?" (file settled + changed)
  POST /api/photocraft/import   diff the saved PSD against the exported baseline, return ONLY
                                changed layers (+ metadata + new layers + optional spec)
  POST /api/photocraft/ack      client applied it -> saved PSD becomes the new baseline
  GET  /api/photocraft/status   exe found? where from? work folder?
  POST /api/photocraft/settings remember a PhotoCraft exe path the painter picked

PhotoCraft (github.com/storytold/photocraft, Apache-2.0 / MIT) is bundled as tools/photocraft/photocraft.exe (owner 2026-10-09; GUI only, no CLI, not portable mode); see NOTICE.
Kill switch: env SPB_PHOTOCRAFT_OFF=1 (client: window.SPB_PHOTOCRAFT_OFF).
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid

from flask import jsonify, request

HELP_URL = "https://github.com/storytold/photocraft/releases"
_SID_RE = re.compile(r"^[0-9a-f]{12}$")


def find_photocraft_exe(settings_path=None, project_root=None):
    """Return (path_or_None, source). Order: env, saved setting, bundled, installed, PATH."""
    env = (os.environ.get("SPB_PHOTOCRAFT_EXE") or "").strip().strip('"')
    if env and os.path.isfile(env):
        return env, "env"
    if settings_path and os.path.isfile(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                p = (json.load(f).get("exe") or "").strip()
            if p and os.path.isfile(p):
                return p, "settings"
        except Exception:
            pass
    roots = [project_root] if project_root else []
    roots.append(os.path.dirname(os.path.abspath(sys.argv[0] or ".")))
    for r in roots:
        for rel in (("tools", "photocraft", "photocraft.exe"), ("photocraft", "photocraft.exe"),
                    ("..", "tools", "photocraft", "photocraft.exe")):
            cand = os.path.normpath(os.path.join(r, *rel))
            if os.path.isfile(cand):
                return cand, "bundled"
    for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("ProgramFiles"),
                 os.environ.get("ProgramFiles(x86)")):
        if not base:
            continue
        for sub in (("Programs", "PhotoCraft"), ("PhotoCraft",), ("Programs", "Photocraft")):
            cand = os.path.join(base, *sub, "photocraft.exe")
            if os.path.isfile(cand):
                return cand, "installed"
    w = shutil.which("photocraft")
    if w:
        return w, "path"
    return None, "missing"


def register_photocraft_routes(app, *, require_internal_request, work_root_getter,
                               settings_path_getter, project_root, output_folder,
                               external_write_guard, logger) -> None:
    from server_routes import photocraft_psd as pcp

    sessions = {}  # sid -> dict(dir, psd, baseline, manifest, handled_mtime, proc, ...)

    def _off():
        return os.environ.get("SPB_PHOTOCRAFT_OFF", "") in ("1", "true", "yes")

    def _gate():
        if _off():
            return jsonify({"ok": False, "error": "Edit in PhotoCraft is switched off (SPB_PHOTOCRAFT_OFF)."}), 403
        ok, err = require_internal_request()
        if not ok:
            return jsonify({"ok": False, "error": err}), 403
        return None

    def _safe(raw, fallback="shokker_car"):
        s = "".join(c if c.isalnum() or c in "._- " else "_" for c in str(raw or fallback)).strip(" .")
        return (s or fallback)[:60]

    def _decode_png(data_url):
        raw = data_url.split(",", 1)[-1]
        from PIL import Image
        return Image.open(io.BytesIO(base64.b64decode(raw))).convert("RGBA")

    def _png_url(img):
        buf = io.BytesIO()
        img.save(buf, "PNG", compress_level=1)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    def _sig(path):
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)

    def _session(sid):
        if not isinstance(sid, str) or not _SID_RE.match(sid):
            return None
        s = sessions.get(sid)
        if s:
            return s
        # survive a server restart: rebuild from manifest on disk
        for d in os.listdir(work_root_getter()) if os.path.isdir(work_root_getter()) else []:
            mp = os.path.join(work_root_getter(), d, "manifest.json")
            if d.endswith("-" + sid) and os.path.isfile(mp):
                with open(mp, "r", encoding="utf-8") as f:
                    m = json.load(f)
                s = {"dir": os.path.join(work_root_getter(), d), "psd": m["psd"], "baseline": m["baseline"],
                     "manifest": m, "handled_sig": _sig(m["psd"]), "proc": None, "last_seen": None}
                sessions[sid] = s
                return s
        return None

    @app.route("/api/photocraft/status", methods=["GET"])
    def photocraft_status():
        if _off():
            return jsonify({"ok": True, "off": True})
        exe, source = find_photocraft_exe(settings_path_getter(), project_root)
        return jsonify({"ok": True, "off": False, "found": bool(exe), "exe": exe, "source": source,
                        "help_url": HELP_URL, "work_root": work_root_getter()})

    @app.route("/api/photocraft/settings", methods=["POST"])
    def photocraft_settings():
        blocked = _gate()
        if blocked:
            return blocked
        data = request.get_json(silent=True) or {}
        p = str(data.get("exe") or "").strip().strip('"')
        if not p or not os.path.isfile(p) or not p.lower().endswith(".exe"):
            return jsonify({"ok": False, "error": "That is not an .exe file."}), 400
        sp = settings_path_getter()
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        with open(sp, "w", encoding="utf-8") as f:
            json.dump({"exe": p}, f)
        return jsonify({"ok": True, "exe": p})

    def _launch(sid):
        s = sessions[sid]
        exe, source = find_photocraft_exe(settings_path_getter(), project_root)
        if not exe:
            return {"launched": False, "reason": "missing", "help_url": HELP_URL}
        try:
            flags = 0
            if os.name == "nt":
                flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            s["proc"] = subprocess.Popen([exe, s["psd"]], cwd=s["dir"], close_fds=True,
                                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL, creationflags=flags)
            return {"launched": True, "exe": exe, "source": source}
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PhotoCraft] launch failed: %s", exc)
            return {"launched": False, "reason": "launch-failed", "error": str(exc), "help_url": HELP_URL}

    @app.route("/api/photocraft/export", methods=["POST"])
    def photocraft_export():
        blocked = _gate()
        if blocked:
            return blocked
        try:
            data = request.get_json(silent=True) or {}
            width, height = int(data.get("width") or 0), int(data.get("height") or 0)
            layers_in = data.get("layers") or []
            if not (0 < width <= 8192 and 0 < height <= 8192) or not layers_in:
                return jsonify({"ok": False, "error": "No layers to send (open a paint or layered PSD first)."}), 400
            if len(layers_in) > 300:
                return jsonify({"ok": False, "error": "Too many layers (limit 300)."}), 400
            name = _safe(data.get("name"))
            sid = uuid.uuid4().hex[:12]
            root = work_root_getter()
            denial = external_write_guard(root, "photocraft-export")
            if denial:
                return jsonify(denial), 403
            sdir = os.path.join(root, f"{name}-{sid}")
            os.makedirs(sdir, exist_ok=True)

            layers, ids = [], []
            for lay in layers_in:
                bbox = [int(v) for v in lay["bbox"]]
                img = _decode_png(lay["png"])
                if img.size != (bbox[2] - bbox[0], bbox[3] - bbox[1]):
                    bbox = [bbox[0], bbox[1], bbox[0] + img.width, bbox[1] + img.height]
                layers.append({
                    "name": str(lay.get("name") or "Layer")[:120],
                    "group_path": [str(g)[:120] for g in (lay.get("group_path") or [])],
                    "visible": lay.get("visible") is not False,
                    "opacity": int(lay.get("opacity", 255)),
                    "blend": lay.get("blend") or "normal",
                    "clipping": bool(lay.get("clipping")),
                    "bbox": bbox, "rgba": img,
                })
                ids.append(str(lay.get("id") or ""))

            spec = None
            spec_path = str(data.get("spec_path") or "").strip()
            if not spec_path and data.get("include_spec"):
                # last render's spec map (R metallic, G roughness, B clearcoat, A mask)
                spec_path = os.path.join(output_folder, "_latest_render", "spec.tga")
            if spec_path and os.path.isfile(spec_path):
                from PIL import Image
                spec = Image.open(spec_path).convert("RGBA")
                if spec.size != (width, height):
                    spec = None
            psd_path = os.path.join(sdir, f"{name}.psd")
            # [SPB-TLAY2 2026-10-10 L2-4] (1) group opacity / blend / visibility travel with the groups; (2) ids are re-ordered to the
            # order the saved PSD is READ back in (a group sits where its first member was added): with non-contiguous group members the
            # old sent-order table handed a PhotoCraft edit of one layer to a different SPB layer.
            groups_in = []
            for g in (data.get("groups") or [])[:200]:
                try:
                    groups_in.append({"path": [str(x)[:120] for x in (g.get("path") or [])],
                                      "opacity": int(g.get("opacity", 255)), "blend": str(g.get("blend") or "normal"),
                                      "visible": g.get("visible") is not False, "pass_through": bool(g.get("pass_through"))})
                except Exception:  # noqa: BLE001
                    pass
            order = pcp.walk_order(layers)
            if order != list(range(len(layers))):
                logger.info("[PhotoCraft] group members not contiguous: saved order differs from sent order; id table re-ordered")
                ids = [ids[i] for i in order]
            pcp.build_psd(psd_path, width, height, layers, spec, groups_in)
            baseline = os.path.join(sdir, "baseline.psd")
            shutil.copy2(psd_path, baseline)
            manifest = {"sid": sid, "name": name, "psd": psd_path, "baseline": baseline, "ids": ids,
                        "width": width, "height": height, "has_spec": spec is not None,
                        "created": int(time.time())}
            with open(os.path.join(sdir, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(manifest, f)
            sessions[sid] = {"dir": sdir, "psd": psd_path, "baseline": baseline, "manifest": manifest,
                             "handled_sig": _sig(psd_path), "proc": None, "last_seen": None}
            launch = _launch(sid) if data.get("launch", True) else {"launched": False, "reason": "not-requested"}
            logger.info("[PhotoCraft] exported %d layers -> %s (launched=%s)", len(layers), psd_path, launch.get("launched"))
            return jsonify({"ok": True, "session": sid, "psd_path": psd_path, "layers": len(layers),
                            "has_spec": spec is not None, "size_mb": round(os.path.getsize(psd_path) / 1048576, 1),
                            **{"launch": launch}})
        except Exception as exc:  # noqa: BLE001
            logger.exception("photocraft-export")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/photocraft/launch", methods=["POST"])
    def photocraft_launch():
        blocked = _gate()
        if blocked:
            return blocked
        sid = (request.get_json(silent=True) or {}).get("session")
        if not _session(sid):
            return jsonify({"ok": False, "error": "Unknown session"}), 404
        return jsonify({"ok": True, **_launch(sid)})

    @app.route("/api/photocraft/poll", methods=["GET"])
    def photocraft_poll():
        blocked = _gate()
        if blocked:
            return blocked
        s = _session(request.args.get("session"))
        if not s:
            return jsonify({"ok": False, "error": "Unknown session"}), 404
        try:
            st = os.stat(s["psd"])
        except OSError:
            return jsonify({"ok": True, "state": "missing"})
        running = bool(s.get("proc") and s["proc"].poll() is None)
        sig = (st.st_mtime_ns, st.st_size)
        if sig == s["handled_sig"]:
            return jsonify({"ok": True, "state": "waiting", "running": running})
        # changed: only report "saved" once size+mtime held still across two polls (write finished)
        prev = s.get("last_seen")
        s["last_seen"] = sig
        if prev != sig or (time.time() - st.st_mtime) < 1.0:
            return jsonify({"ok": True, "state": "writing", "running": running})
        return jsonify({"ok": True, "state": "saved", "running": running, "mtime": st.st_mtime})

    @app.route("/api/photocraft/import", methods=["POST"])
    def photocraft_import():
        blocked = _gate()
        if blocked:
            return blocked
        try:
            sid = (request.get_json(silent=True) or {}).get("session")
            s = _session(sid)
            if not s:
                return jsonify({"ok": False, "error": "Unknown session"}), 404
            t0 = time.time()
            sig_now = _sig(s["psd"])
            base = pcp.read_psd(s["baseline"])
            new = pcp.read_psd(s["psd"])
            if (new["width"], new["height"]) != (base["width"], base["height"]):
                return jsonify({"ok": False, "error": f"PhotoCraft saved a {new['width']}x{new['height']} canvas; SPB needs "
                                f"{base['width']}x{base['height']}. Nothing was changed in SPB."}), 409
            diff = pcp.diff_against_baseline(base, new)
            ids = s["manifest"]["ids"]
            out_layers = []
            pairs_rev = dict(diff["pairs"])
            for ni, nl in enumerate(new["layers"]):
                bi = diff["pairs"].get(ni)
                pix = ni in diff["changed"] or ni in diff["added"]
                meta = diff["meta_changed"].get(ni)
                if not (pix or meta):
                    continue
                below = next((ids[pairs_rev[j]] for j in range(ni - 1, -1, -1)
                              if j in pairs_rev and pairs_rev[j] < len(ids) and ids[pairs_rev[j]]), None)
                out_layers.append({
                    "below_id": below,
                    "spb_id": ids[bi] if bi is not None and bi < len(ids) else None,
                    "name": nl["name"], "group_path": nl["group_path"], "index": ni,
                    "visible": nl["visible"], "opacity": nl["opacity"], "blend": nl["blend"],
                    "bbox": nl["bbox"], "pixels_changed": pix, "meta_changed": meta or [],
                    "png": _png_url(nl["rgba"]) if pix else None,
                    "max_diff": diff["stats"].get(ni, {}).get("max"),
                })
            spec_info = None
            if new["spec"] is not None and base["spec"] is not None:
                import numpy as np
                a, b = np.array(base["spec"]), np.array(new["spec"])
                if int(np.abs(a.astype(np.int16) - b.astype(np.int16)).max()) > 0:
                    tdir = os.path.join(output_folder, "temp_spec_imports")
                    os.makedirs(tdir, exist_ok=True)
                    tp = os.path.join(tdir, f"imported_spec_photocraft_{int(time.time())}.tga")
                    new["spec"].save(tp, format="TGA")
                    spec_info = {"temp_path": tp.replace("\\", "/"), "resolution": [new["width"], new["height"]]}
            s["_pending_sig"] = sig_now
            s["_pending_ids"] = [ids[diff["pairs"][ni]] if ni in diff["pairs"] and diff["pairs"][ni] < len(ids) else None
                                 for ni in range(len(new["layers"]))]
            return jsonify({
                "ok": True, "session": sid, "width": new["width"], "height": new["height"],
                "layers": out_layers, "removed": [base["layers"][i]["name"] for i in diff["removed"]],
                "unchanged": len(diff["same"]), "spec": spec_info,
                "group_changes": pcp.diff_groups(base, new),   # [SPB-TLAY2 2026-10-10 L2-4] reported, never applied silently
                "color_profile_embedded": bool(new["icc"]),
                "ms": int((time.time() - t0) * 1000),
            })
        except Exception as exc:  # noqa: BLE001
            logger.exception("photocraft-import")
            return jsonify({"ok": False, "error": f"Could not read the saved PSD: {exc}"}), 500

    @app.route("/api/photocraft/ack", methods=["POST"])
    def photocraft_ack():
        blocked = _gate()
        if blocked:
            return blocked
        sid = (request.get_json(silent=True) or {}).get("session")
        s = _session(sid)
        if not s:
            return jsonify({"ok": False, "error": "Unknown session"}), 404
        shutil.copy2(s["psd"], s["baseline"])
        added = (request.get_json(silent=True) or {}).get("added_ids") or {}
        pend = s.pop("_pending_ids", None)
        if pend is not None:  # keep baseline-index -> SPB layer id aligned with the new baseline
            for k, v in added.items():
                if str(k).isdigit() and int(k) < len(pend):
                    pend[int(k)] = str(v)
            s["manifest"]["ids"] = [p or "" for p in pend]
            with open(os.path.join(s["dir"], "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(s["manifest"], f)
        s["handled_sig"] = s.pop("_pending_sig", _sig(s["psd"]))
        s["last_seen"] = None
        return jsonify({"ok": True})
