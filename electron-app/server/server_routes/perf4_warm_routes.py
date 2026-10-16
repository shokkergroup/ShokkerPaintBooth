"""[PERF-4 2026-10-10] Warm a Material / Spec Brush coat's full-canvas render while the user is still picking / starting the stroke.

Why: a studio coat (engine/rev_material_layer.py _bs_render_full) renders its finish ONCE on the full canvas and keeps it in the PERF-3 memo,
so every later stroke of the same (finish, sliders) is only a re-composite. The FIRST stroke of a finish pays that render inside the stroke's own
preview: candy 4.4-5.2 s, terrazzo 5.8-8.7 s, sequin 6.0 s (BRUSH-STUDIO report, loaded host). The render does not depend on the stroke, so the
page asks for it earlier: on Apply in the brush's finish picker and on pointer-down of a stroke (POST /api/perf4/warm-coat).

How (byte-identical by construction): the warm is a REAL preview render through the same ``engine.preview_render`` call the live preview uses
(same downscaled paint source, same seed, iracing_id "preview"), over one dummy zone (all-zero mask, flat gloss) that carries the coat in a
``_spb_rev_material`` layer with a one-pixel mask. The engine's own ``_bs_render_full`` then renders + stores the coat under exactly the memo key
a real stroke uses. Nothing is computed by a second implementation.

Scheduling (must never delay a render the user asked for):
 * the warm runs in a daemon thread, only when the server is idle (preview lock free AND no preview/render request for IDLE_S); a busy server
   skips it (the stroke then renders the finish itself = today's behaviour);
 * it holds the SAME ``_preview_render_lock`` as every preview / render (the engine is not safe to run twice at once: global np.random seeding), with
   its OWN abort event, so a user request does not make it throw its work away;
 * a user request that arrives while it runs WAITS for it (``acquire_preview_lock`` below extends that request's lock timeout while a warm holds the
   lock, instead of answering 429) and then hits the memo when it needs the same coat = never slower than rendering it itself. A request that does not
   need the coat waits at most for the warm's remaining time (the engine cannot be interrupted mid finish);
 * one warm slot: a newer warm request replaces a queued one; recent duplicates are skipped.

Kill switches: env SPB_PERF4_OFF=1 (everything), SPB_PERF4_2_OFF=1 (this unit). Counters: GET /api/perf4/stats.
"""
import os
import shutil
import tempfile
import threading
import time
from collections import OrderedDict

IDLE_S = 0.35            # no user preview/render request for this long before a warm may start
WAIT_BUSY_S = 6.0        # a queued warm gives up when the server stays busy this long
USER_WAIT_CAP_S = 30.0   # a user request never waits longer than this for a running warm
DONE_TTL_S = 600.0

_STATE = {"seq": 0, "holding": 0, "last_user": 0.0}
_STATS = {"requests": 0, "ran": 0, "skipped_busy": 0, "skipped_dup": 0, "skipped_off": 0, "superseded": 0, "source_missing": 0,
          "errors": 0, "last_run_s": None, "user_waits": 0, "user_wait_s": 0.0, "last_error": None}
_DONE = OrderedDict()    # warm signature -> finished-at (monotonic)
_GUARD = threading.Lock()


def off(unit=None):
    for k in ("SPB_PERF4_OFF",) + (("SPB_PERF4_%s_OFF" % unit,) if unit else ()):
        if str(os.environ.get(k, "")).strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def note_user_request():
    """Called by /preview-render and /render on arrival: the warm waits for the server to be idle."""
    _STATE["last_user"] = time.monotonic()


def warm_holding():
    return _STATE["holding"] > 0


def acquire_preview_lock(lock, base_timeout):
    """``lock.acquire(timeout=base_timeout)``, except that while a warm HOLDS the lock the caller keeps waiting (up to USER_WAIT_CAP_S) instead of
    giving up with 429. Identical to the old call when no warm is running (or SPB_PERF4_OFF)."""
    if off(2):
        return lock.acquire(timeout=base_timeout)
    t0 = time.monotonic()
    deadline = t0 + float(base_timeout)
    waited = False
    while True:
        if lock.acquire(timeout=0.05):
            if waited:
                _STATS["user_waits"] += 1
                _STATS["user_wait_s"] = round(_STATS["user_wait_s"] + (time.monotonic() - t0), 3)
            return True
        now = time.monotonic()
        if now >= deadline:
            if not warm_holding() or now - t0 >= USER_WAIT_CAP_S:
                return False
            waited = True


def _dummy_zone(np, coat_zone, size):
    return {
        "name": "perf4 warm", "color": "everything", "intensity": "100", "base": "gloss", "pattern": "none", "pattern_opacity": 1.0,
        "region_mask": np.zeros((8, 8), dtype=np.float32),
        "_spb_rev_material": {"v": 1, "size": [int(size[0]), int(size[1])],
                              "coats": [{"zone": coat_zone, "anchor": "car", "plane": "paint"}]},
    }


def _sig(token, seed, scale, coat):
    import hashlib
    import json
    z = {k: v for k, v in coat.items() if k not in ("region_mask", "name", "_spb_rev_material")}
    return hashlib.blake2b(json.dumps([token, seed, scale, z], sort_keys=True, default=str).encode("utf-8"), digest_size=16).hexdigest()


def register_perf4_warm_routes(app, *, engine, preview_lock, source_cache, logger):
    from flask import jsonify, request

    def _run(job, seq):
        t_wait = time.monotonic()
        while True:
            if seq != _STATE["seq"]:
                _STATS["superseded"] += 1
                return
            idle = time.monotonic() - _STATE["last_user"] >= IDLE_S
            if idle and preview_lock.acquire(blocking=False):
                break
            if time.monotonic() - t_wait > WAIT_BUSY_S:
                _STATS["skipped_busy"] += 1
                return
            time.sleep(0.05)
        _STATE["holding"] += 1
        tmp = None
        try:
            import numpy as np
            rec = source_cache.resolve(job["token"])
            if rec is None:
                _STATS["source_missing"] += 1
                return
            tmp = tempfile.mkdtemp(prefix="shokker_perf4_warm_")
            paint = os.path.join(tmp, "paint_with_decals.png")
            with open(paint, "wb") as f:
                f.write(rec.payload)
            t0 = time.perf_counter()
            engine.preview_render(paint, [_dummy_zone(np, job["coat"], job["size"])], seed=job["seed"],
                                  preview_scale=job["scale"], abort_event=threading.Event())
            dt = time.perf_counter() - t0
            _STATS["ran"] += 1
            _STATS["last_run_s"] = round(dt, 2)
            with _GUARD:
                _DONE[job["sig"]] = time.monotonic()
                while len(_DONE) > 64:
                    _DONE.popitem(last=False)
            logger.info("[PERF-4] warmed a brush coat in %.2fs (%s)", dt, (job["coat"].get("base") or job["coat"].get("finish") or "?"))
        except Exception as e:  # a warm must never break anything
            _STATS["errors"] += 1
            _STATS["last_error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
            logger.warning("[PERF-4] warm failed: %s", e)
        finally:
            _STATE["holding"] -= 1
            preview_lock.release()
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)

    @app.route("/api/perf4/warm-coat", methods=["POST"])
    def perf4_warm_coat():
        _STATS["requests"] += 1
        if off(2):
            _STATS["skipped_off"] += 1
            return jsonify({"success": True, "status": "off"})
        d = request.get_json(silent=True) or {}
        coat, token = d.get("coat"), d.get("paint_source_token")
        if not isinstance(coat, dict) or not isinstance(token, str) or not token:
            return jsonify({"success": False, "status": "bad_request"}), 400
        try:
            seed = int(d.get("seed", 51))
            scale = float(d.get("preview_scale", 0.5))
            size = d.get("size") or [2048, 2048]
            size = [int(size[0]), int(size[1])]
        except Exception:
            return jsonify({"success": False, "status": "bad_request"}), 400
        sig = _sig(token, seed, scale, coat)
        with _GUARD:
            done = _DONE.get(sig)
            if done is not None and time.monotonic() - done < DONE_TTL_S:
                _STATS["skipped_dup"] += 1
                return jsonify({"success": True, "status": "duplicate"})
            _STATE["seq"] += 1
            seq = _STATE["seq"]
        job = {"token": token, "seed": seed, "scale": scale, "size": size, "coat": coat, "sig": sig}
        threading.Thread(target=_run, args=(job, seq), daemon=True, name="perf4-warm").start()
        return jsonify({"success": True, "status": "queued"})

    @app.route("/api/perf4/stats", methods=["GET"])
    def perf4_stats():
        return jsonify(dict(_STATS, holding=_STATE["holding"], off=off(), unit2_off=off(2)))
