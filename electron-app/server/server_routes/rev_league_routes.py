"""[SPB-REV-LEAGUE 2026-10-10] League Pack routes (lane REV-LEAGUE).

The page renders every driver through the app's own /render (same payload, same iRacing file names: car_num_<custid>.tga / car_<custid>.tga + car_spec_<custid>.tga);
these routes only do the folder bookkeeping around it. Additive: nothing here is called by any other feature, no existing route or engine path changes.

POST /api/rev-league/prepare  {root, custids:[..]}          -> creates <root>/<custid>/ for every id (the render's output_dir must already exist), refuses an unsafe root
POST /api/rev-league/status   {root, template, hashes:{custid:hash}, prefix}
                                                              -> which drivers are already rendered (same template hash, both TGAs still on disk)
POST /api/rev-league/mark     {root, custid, hash, template, prefix, meta:{..}}
                                                              -> checks the two TGAs, tucks the extra channel TGAs the render also writes into <driver>/channels/ (moved, never deleted),
                                                                 records the driver in <root>/league_manifest.json
POST /api/rev-league/finish   {root, template, title}        -> contact_sheet.png (from the TGAs on disk, i.e. what iRacing gets) + README.txt
Safety: custid is digits only; only fixed file names are written inside <root>; the write guard of server_routes/write_security.py applies (a lane test server never writes
into Documents\\iRacing\\paint); nothing is ever deleted. Kill switch: env SPB_REV_LEAGUE_OFF=1 -> every route answers {"ok": false, "off": true}.
"""
import json
import os
import re
import time

from flask import jsonify, request

MANIFEST = "league_manifest.json"
EXTRA_CHANNEL_FILES = ("spec_metallic.tga", "spec_roughness.tga", "spec_clearcoat.tga", "spec_mask.tga", "paint_base.tga")
_ID = re.compile(r"^\d{1,9}$")
_MIN_TGA = 1_000_000          # a 2048x2048 32-bit TGA is 16.8 MB; anything under 1 MB is a failed / partial write


def _off():
    return str(os.environ.get("SPB_REV_LEAGUE_OFF", "")).strip().lower() not in ("", "0", "false", "off", "no")


def _root_of(raw):
    """Absolute, normalised folder from the page, or (None, why)."""
    p = str(raw or "").strip().strip('"').strip("'")
    if not p:
        return None, "Pick a folder for the league pack first."
    if not os.path.isabs(p):
        return None, "The folder must be a full path (like D:\\League\\Round 5)."
    p = os.path.normpath(p)
    if len(p) <= 3:
        return None, "Pick a folder, not the whole drive."
    return p, None


_DENIAL = [None]          # server.py hands in its own _external_write_denial (verification mode + the lane test-server guard)


def _denied(path, op):
    fn = _DENIAL[0]
    if fn is None:
        return None
    try:
        return fn(path, op)
    except Exception:
        return None


def _paint_name(prefix, custid):
    return "%s_%s.tga" % ("car" if prefix == "car" else "car_num", custid)


def _read_manifest(root):
    p = os.path.join(root, MANIFEST)
    try:
        with open(p, "r", encoding="utf-8") as fh:
            j = json.load(fh)
        if isinstance(j, dict):
            j.setdefault("drivers", {})
            return j
    except Exception:
        pass
    return {"v": 1, "template": "", "drivers": {}}


def _write_manifest(root, j):
    p = os.path.join(root, MANIFEST)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(j, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, p)


def _files_ok(root, custid, prefix):
    d = os.path.join(root, custid)
    out = {}
    for nm in (_paint_name(prefix, custid), "car_spec_%s.tga" % custid):
        fp = os.path.join(d, nm)
        try:
            out[nm] = os.path.getsize(fp)
        except OSError:
            return None
    if any(v < _MIN_TGA for v in out.values()):
        return None
    return out


def _tga_thumb(path, size):
    from PIL import Image
    im = Image.open(path)
    im.load()
    im = im.convert("RGB")
    im.thumbnail((size, size), Image.LANCZOS)
    return im


def _font(px, bold=False):
    from PIL import ImageFont
    for nm in (("arialbd.ttf" if bold else "arial.ttf"), "segoeui.ttf", "DejaVuSans.ttf"):
        for base in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu"):
            fp = os.path.join(base, nm)
            if os.path.exists(fp):
                try:
                    return ImageFont.truetype(fp, px)
                except Exception:
                    pass
    return ImageFont.load_default()


def _contact_sheet(root, man, prefix, title):
    from PIL import Image, ImageDraw
    ids = [k for k in man["drivers"] if _files_ok(root, k, prefix)]
    ids.sort(key=lambda k: man["drivers"][k].get("order", 0))
    if not ids:
        return None, 0
    n = len(ids)
    cols = 4 if n > 6 else (3 if n > 4 else max(1, n))
    rows = (n + cols - 1) // cols
    T, LBL, PAD = 480, 54, 14
    W = cols * (T + PAD) + PAD
    H = rows * (T + LBL + PAD) + PAD + 56
    sheet = Image.new("RGB", (W, H), (28, 28, 32))
    dr = ImageDraw.Draw(sheet)
    dr.text((PAD, 14), title, fill=(232, 232, 234), font=_font(26, True))
    f1, f2 = _font(20, True), _font(15)
    for i, cid in enumerate(ids):
        r, c = divmod(i, cols)
        x = PAD + c * (T + PAD)
        y = 56 + PAD + r * (T + LBL + PAD)
        try:
            th = _tga_thumb(os.path.join(root, cid, _paint_name(prefix, cid)), T)
            sheet.paste(th, (x + (T - th.width) // 2, y + (T - th.height) // 2))
        except Exception:
            dr.rectangle([x, y, x + T, y + T], outline=(120, 60, 60))
        meta = man["drivers"][cid]
        dr.text((x + 2, y + T + 4), ("#%s  %s" % (meta.get("number", ""), meta.get("name", "")))[:34], fill=(232, 232, 234), font=f1)
        dr.text((x + 2, y + T + 30), "ID %s   %s" % (cid, ("%.1fs" % meta["seconds"]) if meta.get("seconds") else ""), fill=(157, 157, 166), font=f2)
    out = os.path.join(root, "contact_sheet.png")
    sheet.save(out)
    return out, n


def register_rev_league_routes(app, denial=None):
    _DENIAL[0] = denial

    @app.route("/api/rev-league/prepare", methods=["POST"])
    def rev_league_prepare():
        if _off():
            return jsonify({"ok": False, "off": True})
        d = request.get_json(silent=True) or {}
        root, why = _root_of(d.get("root"))
        if not root:
            return jsonify({"ok": False, "error": why})
        ids = [str(x) for x in (d.get("custids") or [])]
        if not ids or any(not _ID.match(i) for i in ids):
            return jsonify({"ok": False, "error": "Every customer ID must be digits only."})
        den = _denied(root, "league-prepare")
        if den:
            return jsonify({"ok": False, "error": den.get("message") or "This server may not write there.", "denied": True})
        made = {}
        try:
            os.makedirs(root, exist_ok=True)
            for i in ids:
                p = os.path.join(root, i)
                os.makedirs(p, exist_ok=True)
                made[i] = p
        except OSError as e:
            return jsonify({"ok": False, "error": "Could not create the folders: %s" % e})
        return jsonify({"ok": True, "root": root, "dirs": made})

    @app.route("/api/rev-league/status", methods=["POST"])
    def rev_league_status():
        if _off():
            return jsonify({"ok": False, "off": True})
        d = request.get_json(silent=True) or {}
        root, why = _root_of(d.get("root"))
        if not root:
            return jsonify({"ok": False, "error": why})
        man = _read_manifest(root) if os.path.isdir(root) else {"drivers": {}, "template": ""}
        prefix = "car" if d.get("prefix") == "car" else "car_num"
        done = {}
        for cid, h in (d.get("hashes") or {}).items():
            if not _ID.match(str(cid)):
                continue
            rec = man["drivers"].get(str(cid))
            if rec and rec.get("hash") == h and rec.get("template") == d.get("template") and rec.get("prefix", prefix) == prefix and _files_ok(root, str(cid), prefix):
                done[str(cid)] = {"seconds": rec.get("seconds"), "at": rec.get("at")}
        return jsonify({"ok": True, "done": done, "had_manifest": bool(man.get("drivers"))})

    @app.route("/api/rev-league/mark", methods=["POST"])
    def rev_league_mark():
        if _off():
            return jsonify({"ok": False, "off": True})
        d = request.get_json(silent=True) or {}
        root, why = _root_of(d.get("root"))
        cid = str(d.get("custid") or "")
        if not root or not _ID.match(cid):
            return jsonify({"ok": False, "error": why or "Bad customer ID."})
        if _denied(root, "league-mark"):
            return jsonify({"ok": False, "error": "This server may not write there.", "denied": True})
        prefix = "car" if d.get("prefix") == "car" else "car_num"
        files = _files_ok(root, cid, prefix)
        if not files:
            return jsonify({"ok": False, "error": "The render did not leave both TGA files in %s." % os.path.join(root, cid)})
        moved = []
        dd = os.path.join(root, cid)
        for nm in EXTRA_CHANNEL_FILES:       # the render also drops 5 helper TGAs next to the pair: tuck them away (moved, not deleted)
            src = os.path.join(dd, nm)
            if os.path.isfile(src):
                try:
                    os.makedirs(os.path.join(dd, "channels"), exist_ok=True)
                    os.replace(src, os.path.join(dd, "channels", nm))
                    moved.append(nm)
                except OSError:
                    pass
        man = _read_manifest(root)
        meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
        man["template"] = d.get("template") or man.get("template", "")
        man["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        man["drivers"][cid] = {
            "hash": d.get("hash"), "template": d.get("template"), "prefix": prefix, "at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "seconds": meta.get("seconds"), "name": str(meta.get("name", ""))[:60], "number": str(meta.get("number", ""))[:4],
            "team": str(meta.get("team", ""))[:20], "order": meta.get("order", 0), "files": files,
        }
        try:
            _write_manifest(root, man)
        except OSError as e:
            return jsonify({"ok": False, "error": "Could not save the pack list: %s" % e})
        return jsonify({"ok": True, "files": files, "tucked": moved})

    @app.route("/api/rev-league/finish", methods=["POST"])
    def rev_league_finish():
        if _off():
            return jsonify({"ok": False, "off": True})
        d = request.get_json(silent=True) or {}
        root, why = _root_of(d.get("root"))
        if not root or not os.path.isdir(root):
            return jsonify({"ok": False, "error": why or "The pack folder is not there."})
        if _denied(root, "league-finish"):
            return jsonify({"ok": False, "error": "This server may not write there.", "denied": True})
        prefix = "car" if d.get("prefix") == "car" else "car_num"
        man = _read_manifest(root)
        title = str(d.get("title") or "League Pack")[:80]
        try:
            sheet, n = _contact_sheet(root, man, prefix, title)
        except Exception as e:
            return jsonify({"ok": False, "error": "Contact sheet failed: %s" % e})
        lines = ["%s" % title, "Made with Shokker Paint Booth, League Pack, %s" % time.strftime("%Y-%m-%d %H:%M"), "",
                 "One folder per driver (named by iRacing customer ID). Each holds the two files iRacing reads:",
                 "  %s_<id>.tga   the paint" % ("car" if prefix == "car" else "car_num"), "  car_spec_<id>.tga     the spec map (metal / rough / clearcoat / mask)",
                 "A 'channels' folder next to them holds the four spec channels and the flat paint, for Photoshop. iRacing ignores it.", "",
                 "%-10s %-4s %-28s %s" % ("Customer", "No.", "Driver", "Folder")]
        for cid in sorted(man["drivers"], key=lambda k: man["drivers"][k].get("order", 0)):
            m = man["drivers"][cid]
            if _files_ok(root, cid, prefix):
                lines.append("%-10s %-4s %-28s %s" % (cid, m.get("number", ""), m.get("name", "")[:28], os.path.join(root, cid)))
        lines += ["", "Pack list: %s (lets League Pack skip drivers that are already done)." % MANIFEST]
        try:
            with open(os.path.join(root, "README.txt"), "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
        except OSError as e:
            return jsonify({"ok": False, "error": "Could not write the README: %s" % e})
        return jsonify({"ok": True, "sheet": sheet, "drivers": n, "readme": os.path.join(root, "README.txt")})

    return app
