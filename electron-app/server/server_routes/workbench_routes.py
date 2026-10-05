# -*- coding: utf-8 -*-
"""SPB Workbench — the owner work-management tool (dev/owner-only, additive).

One persistent place to manage the whole library instead of regenerating a
throwaway audit HTML every round. Served at ``/SPB_WORKBENCH.html`` by the SPB
server; talks to these JSON APIs (all under ``/api/workbench``):

  GET  /api/workbench/catalog              live registry -> tabs/groups/items,
                                           merged with each item's current
                                           rating + per-item source mtime +
                                           an "edited since you last rated it" flag.
  GET  /api/workbench/swatch/<kind>/<id>   render-on-demand PAINT|SPEC swatch
                                           (cached by source mtime under _workbench/cache).
  POST /api/workbench/rating               {id,kind,rating,verdict,reasons,notes}
                                           -> append a rating row (history kept).
  GET  /api/workbench/bugs                 bug list (+ threaded comments).
  POST /api/workbench/bugs                 create bug {title,body,reporter,severity}.
  POST /api/workbench/bugs/<id>            update {status} and/or add {comment,author}.
  GET  /api/workbench/worklog              dated work-done feed.
  POST /api/workbench/worklog              add {entry,tags,author}.

Storage: a single SQLite db at ``_workbench/spb_workbench.db`` (stdlib sqlite3,
zero new dependency) the assistant reads back directly when Ricky says
"look through the workbench". On first init the existing
``_audit/june_<cat>_audit.json`` verdicts are migrated in so nothing is lost.

Register from server.py (mirrors register_june_audit_routes):
    from server_routes.workbench_routes import register_workbench_routes
    register_workbench_routes(app, server_dir=SERVER_DIR, logger=logger)

Everything here is brand-new routes wrapped defensively — a failure can never
block server boot (owner mandate: nothing breaks what already works).
"""
from __future__ import annotations

import contextlib
import hashlib
import inspect
import io
import json
import os
import re
import sqlite3
import subprocess
import threading
import time
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows

_SAFE_ID = re.compile(r"^[A-Za-z0-9_.\-]{1,80}$")
_VALID_VERDICTS = {"keep", "rebuild", "replace", "rename", "remove"}
_VALID_BUG_STATUS = {"open", "in_progress", "blocked", "done", "wontfix"}

# Picker-group buckets -> Workbench tab + render kind.  (base/special are both
# "finishes" to the owner; patterns and spec overlays get their own tabs.)
_TAB_FOR = {"base": "finishes", "special": "finishes",
            "pattern": "patterns", "spec": "spec_overlays"}
_KIND_FOR = {"base": "base", "special": "monolithic",
             "pattern": "pattern", "spec": "spec-pattern"}


# ───────────────────────── enumeration (finish-data.js via node, mtime-cached)
_GROUPS_CACHE: dict = {"mtime": None, "data": None}
_GROUPS_LOCK = threading.Lock()

_NODE_DUMP = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = { window: undefined, console: { log() {}, warn() {} }, setTimeout() {} };
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 8000 });
function meta(arrName) {
  return Object.fromEntries((vm.runInContext(arrName, ctx) || []).filter(x => x && x.id).map(x => [x.id, x]));
}
console.log(JSON.stringify({
  base: vm.runInContext('BASE_GROUPS', ctx) || {},
  pattern: vm.runInContext('PATTERN_GROUPS', ctx) || {},
  special: vm.runInContext('SPECIAL_GROUPS', ctx) || {},
  spec: vm.runInContext('SPEC_PATTERN_GROUPS', ctx) || {},
  meta: Object.assign({}, meta('BASES'), meta('PATTERNS'), meta('MONOLITHICS'), meta('SPEC_PATTERNS'))
}));
"""


def _load_picker_groups(server_dir: str) -> dict:
    """{base,pattern,special,spec,meta} parsed from finish-data.js. Cached by mtime."""
    fd = os.path.join(server_dir, "paint-booth-0-finish-data.js")
    try:
        mtime = os.path.getmtime(fd)
    except OSError:
        return {"base": {}, "pattern": {}, "special": {}, "spec": {}, "meta": {}}
    with _GROUPS_LOCK:
        if _GROUPS_CACHE["mtime"] == mtime and _GROUPS_CACHE["data"] is not None:
            return _GROUPS_CACHE["data"]
        out = subprocess.check_output(
            ["node", "-e", _NODE_DUMP], cwd=server_dir, text=True,
            encoding="utf-8", timeout=30)
        data = json.loads(out)
        _GROUPS_CACHE["mtime"] = mtime
        _GROUPS_CACHE["data"] = data
        return data


# ───────────────────────── per-item source mtime ("last edited")
_SRC_FILE_CACHE: dict = {}


def _fn_mtime(fn) -> float:
    if fn is None:
        return 0.0
    key = id(fn)
    if key in _SRC_FILE_CACHE:
        path = _SRC_FILE_CACHE[key]
    else:
        try:
            path = inspect.getsourcefile(fn) or inspect.getfile(fn)
        except (TypeError, OSError):
            path = None
        _SRC_FILE_CACHE[key] = path
    if not path:
        return 0.0
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _item_src_mtime(eng, item_id: str, kind: str) -> float:
    try:
        if kind == "base" and item_id in eng.BASE_REGISTRY:
            e = eng.BASE_REGISTRY[item_id]
            return max(_fn_mtime(e.get("paint_fn")), _fn_mtime(e.get("base_spec_fn")))
        if kind == "monolithic" and item_id in eng.MONOLITHIC_REGISTRY:
            e = eng.MONOLITHIC_REGISTRY[item_id]
            return max(_fn_mtime(e[0] if len(e) > 0 else None),
                       _fn_mtime(e[1] if len(e) > 1 else None))
        if kind == "pattern" and item_id in eng.PATTERN_REGISTRY:
            return _fn_mtime(eng.PATTERN_REGISTRY[item_id].get("texture_fn"))
        if kind == "spec-pattern":
            from engine.spec_patterns import PATTERN_CATALOG
            if item_id in PATTERN_CATALOG:
                return _fn_mtime(PATTERN_CATALOG[item_id])
    except Exception:
        return 0.0
    return 0.0


# ───────────────────────── render core (ported from scripts/spb_visual_workbench)
def _norm01(arr):
    import numpy as np
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _spec_array(spec, shape):
    import numpy as np
    import cv2
    if spec is None:
        return None
    if isinstance(spec, tuple):
        chans = [np.asarray(c, dtype=np.float32) for c in spec[:3]]
        while len(chans) < 3:
            chans.append(np.zeros(shape, dtype=np.float32))
        arr = np.stack(chans[:3], axis=2)
    else:
        arr = np.asarray(spec, dtype=np.float32)
        if arr.ndim == 2:
            arr = np.repeat(arr[:, :, None], 3, axis=2)
        elif arr.ndim == 3:
            arr = arr[:, :, :3]
        else:
            return None
    if arr.shape[:2] != tuple(shape):
        arr = cv2.resize(arr, (int(shape[1]), int(shape[0])), interpolation=cv2.INTER_LINEAR)
    return np.clip(arr, 0, 255).astype(np.uint8)


def _pattern_spec_from_pv(pv):
    import numpy as np
    return np.dstack([
        np.clip(pv * 255, 0, 255),
        np.clip((1.0 - pv) * 180 + 15, 15, 255),
        np.clip(16 + pv * 140, 16, 255),
    ]).astype(np.uint8)


def _render_item(eng, item_id: str, kind: str, size: int, seed: int, meta=None):
    """Return (rgb float[0..1] HxWx3, spec uint8 HxWx3|None, actual_kind)."""
    import numpy as np
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.full((size, size, 3), 0.18, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)

    if kind in {"auto", "base"} and item_id in eng.BASE_REGISTRY:
        entry = eng.BASE_REGISTRY[item_id]
        rgb = paint.copy()
        if entry.get("paint_fn"):
            rgb = entry["paint_fn"](rgb, shape, mask, seed, 1.0, bb)
        spec = None
        if entry.get("base_spec_fn"):
            spec = entry["base_spec_fn"](shape, seed, 1.0,
                                         float(entry.get("M", 120)), float(entry.get("R", 80)))
        return np.clip(rgb[:, :, :3], 0, 1), _spec_array(spec, shape), "base"

    if kind in {"auto", "monolithic", "special"} and item_id in eng.MONOLITHIC_REGISTRY:
        entry = eng.MONOLITHIC_REGISTRY[item_id]
        spec_fn, paint_fn = entry[:2]
        rgb = paint_fn(paint.copy(), shape, mask, seed, 1.0, bb)
        try:
            spec = spec_fn(shape, mask, seed, 1.0)
        except TypeError:
            spec = spec_fn(shape, seed, 1.0, 120, 80)
        return np.clip(rgb[:, :, :3], 0, 1), _spec_array(spec, shape), "monolithic"

    if kind in {"auto", "pattern"} and item_id in eng.PATTERN_REGISTRY:
        entry = eng.PATTERN_REGISTRY[item_id]
        tex_fn = entry.get("texture_fn")
        if tex_fn is not None:
            tex = tex_fn(shape, mask, seed, 1.0)
            pv = _norm01(tex.get("pattern_val") if isinstance(tex, dict) else tex)
            rgb = np.dstack([pv, pv, pv]).astype(np.float32)
            return rgb, _pattern_spec_from_pv(pv), "pattern"
        image_path = str(entry.get("image_path") or "").strip()
        if image_path:
            asset = os.path.join(eng.__dict__.get("SERVER_DIR", ""), image_path.lstrip("/\\"))
            if os.path.isfile(asset):
                from PIL import Image, ImageOps
                im = ImageOps.fit(ImageOps.exif_transpose(Image.open(asset).convert("RGB")),
                                  (size, size), method=Image.Resampling.LANCZOS)
                rgb = np.asarray(im, dtype=np.float32) / 255.0
                return rgb, _pattern_spec_from_pv(_norm01(rgb.mean(axis=2))), "image_pattern"

    if kind in {"auto", "spec", "spec-pattern", "spec_pattern"}:
        from engine.spec_patterns import PATTERN_CATALOG
        if item_id in PATTERN_CATALOG:
            pv = _norm01(PATTERN_CATALOG[item_id](shape, seed, 1.0))
            rgb = np.dstack([pv, pv, pv]).astype(np.float32)
            return rgb, _pattern_spec_from_pv(pv), "spec_pattern"

    # never crash a grid — return a labelled placeholder
    return paint, None, "missing"


def _swatch_png(eng, item_id: str, kind: str, size: int, seed: int) -> bytes:
    import numpy as np
    from PIL import Image, ImageDraw
    rgb, spec, _k = _render_item(eng, item_id, kind, size, seed)
    paint_u8 = (np.clip(rgb[:, :, :3], 0, 1) * 255).astype(np.uint8)
    if spec is None:
        spec = np.zeros((size, size, 3), dtype=np.uint8)
    elif spec.shape[:2] != (size, size):
        import cv2
        spec = cv2.resize(spec, (size, size), interpolation=cv2.INTER_LINEAR)
    gap = 4
    canvas = np.full((size, size * 2 + gap, 3), 14, dtype=np.uint8)
    canvas[:, :size] = paint_u8
    canvas[:, size + gap:] = spec[:, :, :3]
    im = Image.fromarray(canvas, "RGB")
    d = ImageDraw.Draw(im)
    d.text((6, 6), "PAINT", fill=(255, 255, 255))
    d.text((size + gap + 6, 6), "SPEC  R=M G=R B=CC", fill=(255, 255, 255))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


# ───────────────────────── SQLite store
_DB_LOCK = threading.Lock()


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_db(db_path: str, server_dir: str, logger) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with _DB_LOCK, _db(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ratings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              item_id TEXT NOT NULL, kind TEXT, rating INTEGER, verdict TEXT,
              reasons TEXT, notes TEXT, ts INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS ix_ratings_item ON ratings(item_id, ts);
            CREATE TABLE IF NOT EXISTS bugs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL, body TEXT, reporter TEXT, severity TEXT,
              status TEXT NOT NULL DEFAULT 'open',
              created_ts INTEGER NOT NULL, updated_ts INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS bug_comments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              bug_id INTEGER NOT NULL, body TEXT NOT NULL, author TEXT, ts INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS worklog (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              entry TEXT NOT NULL, tags TEXT, author TEXT, ts INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS meta_kv (k TEXT PRIMARY KEY, v TEXT);
            """
        )
        row = conn.execute("SELECT v FROM meta_kv WHERE k='june_migrated'").fetchone()
        if not row:
            _migrate_june_audit(conn, server_dir, logger)
            conn.execute("INSERT OR REPLACE INTO meta_kv(k,v) VALUES('june_migrated','1')")
        conn.commit()


def _migrate_june_audit(conn, server_dir, logger) -> None:
    audit_dir = os.path.join(server_dir, "_audit")
    if not os.path.isdir(audit_dir):
        return
    n = 0
    for fn in os.listdir(audit_dir):
        m = re.match(r"^june_([a-z0-9_]+)_audit\.json$", fn)
        if not m:
            continue
        try:
            with open(os.path.join(audit_dir, fn), "r", encoding="utf-8") as f:
                entries = (json.load(f) or {}).get("entries", {})
        except (OSError, json.JSONDecodeError) as _spb_ex:
            _spb_swallow('_migrate_june_audit@L324', _spb_ex); continue
        for item_id, e in (entries or {}).items():
            if not isinstance(e, dict):
                continue
            conn.execute(
                "INSERT INTO ratings(item_id,kind,rating,verdict,reasons,notes,ts) "
                "VALUES(?,?,?,?,?,?,?)",
                (item_id, None, e.get("rating"), e.get("verdict"),
                 json.dumps(e.get("reasons") or []), str(e.get("notes") or ""),
                 int(e.get("ts") or 0) or int(time.time() * 1000)))
            n += 1
    if n and logger:
        logger.info(f"[workbench] migrated {n} june-audit verdicts into SQLite")


def _current_ratings(conn) -> dict:
    """Newest rating row per item_id."""
    rows = conn.execute(
        "SELECT r.item_id, r.rating, r.verdict, r.reasons, r.notes, r.ts "
        "FROM ratings r JOIN (SELECT item_id, MAX(ts) mt FROM ratings GROUP BY item_id) j "
        "ON r.item_id=j.item_id AND r.ts=j.mt").fetchall()
    out = {}
    for r in rows:
        try:
            reasons = json.loads(r["reasons"] or "[]")
        except (TypeError, json.JSONDecodeError):
            reasons = []
        out[r["item_id"]] = {"rating": r["rating"], "verdict": r["verdict"],
                             "reasons": reasons, "notes": r["notes"] or "", "ts": r["ts"]}
    return out


# ───────────────────────── route registration
def register_workbench_routes(app, *, server_dir, logger, external_write_guard=None) -> None:
    from flask import jsonify, request, send_file, abort

    wb_dir = os.path.join(server_dir, "_workbench")
    db_path = os.path.join(wb_dir, "spb_workbench.db")
    cache_dir = os.path.join(wb_dir, "cache")

    @app.before_request
    def _guard_workbench_storage():
        # Even GETs open SQLite in WAL mode and can initialize the DB/cache.
        if request.path.startswith("/api/workbench/") and external_write_guard is not None:
            denial = external_write_guard(wb_dir, "workbench-storage")
            if denial:
                return jsonify(denial), 403
        return None

    # Defer ALL filesystem/DB work to first request so route registration can
    # never throw (a throw here would be swallowed by server.py's try/except and
    # the routes would silently not register -> 404 on /SPB_WORKBENCH.html).
    _ready = {"done": False}

    def _ensure_ready():
        if _ready["done"]:
            return
        os.makedirs(cache_dir, exist_ok=True)
        _init_db(db_path, server_dir, logger)
        _ready["done"] = True

    _eng_ref = {"eng": None}

    def _engine():
        if _eng_ref["eng"] is None:
            import shokker_engine_v2 as eng
            with contextlib.suppress(Exception):
                if hasattr(eng, "_ensure_expansions_loaded"):
                    eng._ensure_expansions_loaded()
            if not hasattr(eng, "SERVER_DIR"):
                eng.SERVER_DIR = server_dir
            _eng_ref["eng"] = eng
        return _eng_ref["eng"]

    def _safe_int(v, default=0):
        try:
            return int(round(float(v)))
        except (TypeError, ValueError):
            return default

    # ---- catalog: the whole library, merged with ratings + edited-since flag
    @app.route("/api/workbench/catalog", methods=["GET"])
    def wb_catalog():
        try:
            _ensure_ready()
            groups = _load_picker_groups(server_dir)
            eng = _engine()
            with _DB_LOCK, _db(db_path) as conn:
                current = _current_ratings(conn)
            meta = groups.get("meta", {})
            sections = {"finishes": [], "patterns": [], "spec_overlays": []}
            stats = {"total": 0, "rated": 0, "edited_since": 0}
            for bucket in ("base", "special", "pattern", "spec"):
                tab = _TAB_FOR[bucket]
                kind = _KIND_FOR[bucket]
                for group_name, ids in (groups.get(bucket) or {}).items():
                    items = []
                    for item_id in ids:
                        m = meta.get(item_id, {}) or {}
                        src = _item_src_mtime(eng, item_id, kind)
                        cur = current.get(item_id)
                        edited_since = bool(cur and cur.get("ts") and src
                                            and src * 1000.0 > float(cur["ts"]))
                        items.append({
                            "id": item_id, "kind": kind, "tab": tab, "group": group_name,
                            "name": m.get("name", item_id), "desc": m.get("desc", ""),
                            "swatch": m.get("swatch", ""),
                            "src_mtime": int(src) if src else 0,
                            "rating": (cur or {}).get("rating"),
                            "verdict": (cur or {}).get("verdict"),
                            "reasons": (cur or {}).get("reasons", []),
                            "notes": (cur or {}).get("notes", ""),
                            "rating_ts": (cur or {}).get("ts"),
                            "edited_since": edited_since,
                        })
                        stats["total"] += 1
                        if cur and (cur.get("verdict") or cur.get("rating")):
                            stats["rated"] += 1
                        if edited_since:
                            stats["edited_since"] += 1
                    if items:
                        sections[tab].append({"group": group_name, "items": items})
            return jsonify({"ok": True, "generated": int(time.time()),
                            "sections": sections, "stats": stats})
        except Exception as e:  # noqa: BLE001
            if logger:
                logger.error(f"/api/workbench/catalog failed: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ---- swatch: render-on-demand PAINT|SPEC, cached by source mtime
    @app.route("/api/workbench/swatch/<kind>/<item_id>", methods=["GET"])
    def wb_swatch(kind, item_id):
        if not _SAFE_ID.match(item_id or "") or kind not in {"base", "monolithic", "pattern", "spec-pattern"}:
            abort(404)
        try:
            _ensure_ready()
            size = max(96, min(1024, _safe_int(request.args.get("size"), 416)))  # 1024 = readable zoom (lightbox)
            eng = _engine()
            src = _item_src_mtime(eng, item_id, kind)
            safe = re.sub(r"[^A-Za-z0-9_.\-]+", "_", item_id)
            tag = hashlib.md5(f"{kind}:{item_id}:{int(src)}:{size}".encode()).hexdigest()[:10]
            cache_path = os.path.join(cache_dir, f"{kind}__{safe}__{tag}.png")
            if not os.path.isfile(cache_path):
                # drop older cache variants for this id
                with contextlib.suppress(OSError):
                    for old in os.listdir(cache_dir):
                        if old.startswith(f"{kind}__{safe}__") and old != os.path.basename(cache_path):
                            os.remove(os.path.join(cache_dir, old))
                png = _swatch_png(eng, item_id, kind, size, 7777)
                with open(cache_path, "wb") as f:
                    f.write(png)
            resp = send_file(os.path.abspath(cache_path), mimetype="image/png")
            resp.headers["Cache-Control"] = "public, max-age=86400"
            return resp
        except Exception as e:  # noqa: BLE001
            if logger:
                logger.warning(f"/api/workbench/swatch/{kind}/{item_id} failed: {e}")
            abort(500)

    # ---- ratings
    @app.route("/api/workbench/rating", methods=["POST"])
    def wb_rating():
        try:
            _ensure_ready()
            d = request.get_json(silent=True) or {}
            item_id = str(d.get("id") or "")
            if not _SAFE_ID.match(item_id):
                return jsonify({"ok": False, "error": "bad id"}), 400
            verdict = d.get("verdict")
            if verdict not in _VALID_VERDICTS:
                verdict = None
            rating = d.get("rating")
            rating = None if rating in (None, "", 0) else max(1, min(100, _safe_int(rating)))
            reasons = [str(r)[:60] for r in (d.get("reasons") or []) if r][:20]
            notes = str(d.get("notes") or "")[:4000]
            ts = _safe_int(d.get("ts"), 0) or int(time.time() * 1000)
            with _DB_LOCK, _db(db_path) as conn:
                conn.execute(
                    "INSERT INTO ratings(item_id,kind,rating,verdict,reasons,notes,ts) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (item_id, d.get("kind"), rating, verdict, json.dumps(reasons), notes, ts))
                conn.commit()
            return jsonify({"ok": True, "id": item_id, "rating": rating,
                            "verdict": verdict, "reasons": reasons, "notes": notes, "ts": ts})
        except Exception as e:  # noqa: BLE001
            if logger:
                logger.error(f"/api/workbench/rating failed: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/workbench/rating/<item_id>", methods=["GET"])
    def wb_rating_history(item_id):
        if not _SAFE_ID.match(item_id or ""):
            abort(404)
        _ensure_ready()
        with _DB_LOCK, _db(db_path) as conn:
            rows = conn.execute(
                "SELECT rating,verdict,reasons,notes,ts FROM ratings WHERE item_id=? ORDER BY ts DESC",
                (item_id,)).fetchall()
        return jsonify({"ok": True, "id": item_id,
                        "history": [dict(r) for r in rows]})

    # ---- bugs
    @app.route("/api/workbench/bugs", methods=["GET"])
    def wb_bugs_get():
        _ensure_ready()
        with _DB_LOCK, _db(db_path) as conn:
            bugs = [dict(r) for r in conn.execute(
                "SELECT * FROM bugs ORDER BY (status='done' OR status='wontfix'), updated_ts DESC").fetchall()]
            for b in bugs:
                b["comments"] = [dict(c) for c in conn.execute(
                    "SELECT body,author,ts FROM bug_comments WHERE bug_id=? ORDER BY ts", (b["id"],)).fetchall()]
        return jsonify({"ok": True, "bugs": bugs})

    @app.route("/api/workbench/bugs", methods=["POST"])
    def wb_bugs_post():
        try:
            _ensure_ready()
            d = request.get_json(silent=True) or {}
            title = str(d.get("title") or "").strip()[:240]
            if not title:
                return jsonify({"ok": False, "error": "title required"}), 400
            now = int(time.time() * 1000)
            sev = str(d.get("severity") or "normal")[:20]
            with _DB_LOCK, _db(db_path) as conn:
                cur = conn.execute(
                    "INSERT INTO bugs(title,body,reporter,severity,status,created_ts,updated_ts) "
                    "VALUES(?,?,?,?, 'open', ?,?)",
                    (title, str(d.get("body") or "")[:8000], str(d.get("reporter") or "")[:80], sev, now, now))
                conn.commit()
                bug_id = cur.lastrowid
            return jsonify({"ok": True, "id": bug_id})
        except Exception as e:  # noqa: BLE001
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/workbench/bugs/<int:bug_id>", methods=["POST"])
    def wb_bugs_update(bug_id):
        try:
            _ensure_ready()
            d = request.get_json(silent=True) or {}
            now = int(time.time() * 1000)
            with _DB_LOCK, _db(db_path) as conn:
                if not conn.execute("SELECT 1 FROM bugs WHERE id=?", (bug_id,)).fetchone():
                    return jsonify({"ok": False, "error": "no such bug"}), 404
                status = d.get("status")
                if status in _VALID_BUG_STATUS:
                    conn.execute("UPDATE bugs SET status=?, updated_ts=? WHERE id=?", (status, now, bug_id))
                comment = str(d.get("comment") or "").strip()
                if comment:
                    conn.execute("INSERT INTO bug_comments(bug_id,body,author,ts) VALUES(?,?,?,?)",
                                 (bug_id, comment[:8000], str(d.get("author") or "")[:80], now))
                    conn.execute("UPDATE bugs SET updated_ts=? WHERE id=?", (now, bug_id))
                conn.commit()
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return jsonify({"ok": False, "error": str(e)}), 500

    # ---- worklog
    @app.route("/api/workbench/worklog", methods=["GET"])
    def wb_worklog_get():
        _ensure_ready()
        with _DB_LOCK, _db(db_path) as conn:
            rows = [dict(r) for r in conn.execute(
                "SELECT id,entry,tags,author,ts FROM worklog ORDER BY ts DESC LIMIT 500").fetchall()]
        return jsonify({"ok": True, "worklog": rows})

    @app.route("/api/workbench/worklog", methods=["POST"])
    def wb_worklog_post():
        try:
            _ensure_ready()
            d = request.get_json(silent=True) or {}
            entry = str(d.get("entry") or "").strip()[:8000]
            if not entry:
                return jsonify({"ok": False, "error": "entry required"}), 400
            with _DB_LOCK, _db(db_path) as conn:
                conn.execute("INSERT INTO worklog(entry,tags,author,ts) VALUES(?,?,?,?)",
                             (entry, str(d.get("tags") or "")[:200], str(d.get("author") or "")[:80],
                              int(time.time() * 1000)))
                conn.commit()
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return jsonify({"ok": False, "error": str(e)}), 500

    # ---- similarity (uniqueness) index — reads the baked catalog fingerprint
    @app.route("/api/workbench/similarity", methods=["GET"])
    def wb_similarity():
        _ensure_ready()
        meta_path = os.path.join(wb_dir, "catalog_fp_meta.json")
        if not os.path.isfile(meta_path):
            return jsonify({"ok": False, "baked": False,
                            "error": "Catalog similarity index not built yet. Run: python scripts/spb_catalog_fingerprint.py"})
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({"ok": True, "baked": True, "generated": data.get("generated"),
                            "count": data.get("count"), "items": data.get("items", {})})
        except Exception as e:  # noqa: BLE001
            return jsonify({"ok": False, "baked": False, "error": str(e)})

    # ---- serve the SPA
    @app.route("/SPB_WORKBENCH.html")
    def wb_page():
        path = os.path.join(server_dir, "SPB_WORKBENCH.html")
        if os.path.isfile(path):
            return send_file(os.path.abspath(path), mimetype="text/html")
        abort(404)

    if logger:
        logger.info("[workbench] routes registered (/SPB_WORKBENCH.html)")
