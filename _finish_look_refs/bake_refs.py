# -*- coding: utf-8 -*-
# [SPB 2026-08-29] LOOK-FREEZE bake for HOUDINI + X-LAB (owner: "I'm good with the way they
# look now unless they are changed"). For every registered houdini_*/xlab_* monolithic:
#   - render paint+spec at 2048, seed 51, scale 1.0 (the approved look)
#   - record SHA-256 of the canonical float32 bytes  -> THE bit-exact contract
#   - save a 1024px PNG pair                          -> the human eyeball copy
#   - record per-card timings                         -> the perf before-state
# Incremental: manifest written after EVERY card; safe to re-run (skips done ids).
import sys, os, io, json, time, hashlib, contextlib, logging
import numpy as np
from PIL import Image

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT)
sys.path.insert(0, ROOT)
logging.disable(logging.CRITICAL)
OUT = "_finish_look_refs/2026-08-29"
os.makedirs(OUT, exist_ok=True)
MANIFEST = os.path.join(OUT, "manifest.json")
man = json.load(open(MANIFEST, encoding="utf-8")) if os.path.exists(MANIFEST) else {}

buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    import shokker_engine_v2 as eng

ids = sorted(k for k in eng.MONOLITHIC_REGISTRY if k.startswith(("houdini_", "xlab_")))
# [IMPROVE-mode re-bake] ids passed on the command line are re-baked even if already in the
# manifest — run after a DECLARED look improvement so the contract tracks the new baseline.
force = set(a for a in sys.argv[1:] if not a.startswith("-"))
unknown = force - set(ids)
if unknown:
    print("WARNING: not registered houdini_/xlab_ ids, ignoring:", sorted(unknown))
    force -= unknown
shape = (2048, 2048)
mask = np.ones(shape, dtype=bool)
SEED, SM = 51, 1.0

def render(fid):
    spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[fid]
    base = np.full(shape + (3,), 128, dtype=np.uint8)
    t0 = time.time()
    p = paint_fn(base.copy(), shape, mask, SEED, SM, None)
    t1 = time.time()
    try:
        s = spec_fn(shape, mask, SEED, SM)
    except TypeError:
        s = spec_fn(shape, SEED, SM)
    t2 = time.time()
    return np.asarray(p), np.asarray(s), t1 - t0, t2 - t1

def sha(a):
    return hashlib.sha256(np.ascontiguousarray(a.astype(np.float32)).tobytes()).hexdigest()

def save_png(a, path):
    x = np.asarray(a)
    if x.dtype != np.uint8:
        x = np.clip(x.astype(np.float32) * (255.0 if x.max() <= 1.5 else 1.0), 0, 255).astype(np.uint8)
    if x.ndim == 2:
        x = np.stack([x] * 3, axis=-1)
    Image.fromarray(x[..., :3]).resize((1024, 1024), Image.LANCZOS).save(path)

det_checked = 0
for i, fid in enumerate(ids):
    if fid in man and man[fid].get("paint_sha") and fid not in force:
        continue
    try:
        p, s, pt, st = render(fid)
        rec = {"paint_sha": sha(p), "spec_sha": sha(s),
               "paint_ms": int(pt * 1000), "spec_ms": int(st * 1000),
               "total_ms": int((pt + st) * 1000),
               "paint_stats": [round(float(p.std()), 4), round(float(np.asarray(p, dtype=np.float64).mean()), 4)],
               "over_budget": (pt + st) > 3.0}
        if det_checked < 3:
            p2, s2, _, _ = render(fid)
            rec["deterministic"] = (sha(p2) == rec["paint_sha"] and sha(s2) == rec["spec_sha"])
            det_checked += 1
        save_png(p, os.path.join(OUT, fid + "_paint.png"))
        save_png(s, os.path.join(OUT, fid + "_spec.png"))
        man[fid] = rec
        print(f"[{i+1}/{len(ids)}] {fid} total={rec['total_ms']}ms" +
              (" OVER-BUDGET" if rec["over_budget"] else "") +
              (f" det={rec.get('deterministic')}" if "deterministic" in rec else ""), flush=True)
    except Exception as e:
        man[fid] = {"error": f"{type(e).__name__}: {e}"[:200]}
        print(f"[{i+1}/{len(ids)}] {fid} ERROR {e}", flush=True)
    json.dump(man, open(MANIFEST, "w", encoding="utf-8"), indent=1)

over = [k for k, v in man.items() if v.get("over_budget")]
print(f"DONE: {len(man)} baked, {len(over)} over the 3s budget")
json.dump(man, open(MANIFEST, "w", encoding="utf-8"), indent=1)
