# -*- coding: utf-8 -*-
"""SPB Catalog Fingerprint Index — the curated similarity map of the WHOLE catalog.

Renders every finish (base + monolithic/special + pattern) at low res, computes a
COLOR-INDEPENDENT structural fingerprint (so recolors are caught), and a
spec-traces-paint score (does the spec mirror the paint's structure?). Caches to
_workbench/catalog_fp.npz (+ catalog_fp_meta.json) keyed by per-finish source mtime,
so re-runs only re-fingerprint what changed.

This is the data behind docs/UNIQUENESS_LAW.md and scripts/spb_uniqueness_gate.py.

Run:
  python scripts/spb_catalog_fingerprint.py                # incremental update of the whole catalog
  python scripts/spb_catalog_fingerprint.py --ids a,b,c    # only these ids
  python scripts/spb_catalog_fingerprint.py --limit 40     # quick partial (smoke test)
  python scripts/spb_catalog_fingerprint.py --force        # re-fingerprint everything
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import cv2

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FP_RES = 256          # render size for fingerprinting
SEED = 7777
SOLID_STD = 0.012     # paint luma std below this = a flat SOLID (no structure to clone;
                      # solids differ only by spec/color and are exempt from the structural rules)
WB_DIR = REPO / "_workbench"
NPZ = WB_DIR / "catalog_fp.npz"
META = WB_DIR / "catalog_fp_meta.json"

# ---- structural fingerprint (luma only -> color independent) ----------------
def _phash_bits(luma: np.ndarray) -> np.ndarray:
    """256-bit DCT perceptual hash of the luma. Near-duplicate detector."""
    g = cv2.resize(luma.astype(np.float32), (64, 64))
    d = cv2.dct(g)
    low = d[:16, :16].copy()
    low[0, 0] = 0.0
    med = float(np.median(low))
    return np.packbits((low > med).astype(np.uint8).ravel())  # 32 bytes


def _struct_desc(luma: np.ndarray) -> np.ndarray:
    """Multi-scale structural descriptor: macro forms + edge shape + texture freq."""
    g = cv2.resize(luma.astype(np.float32), (64, 64))

    def z(a):
        a = a.astype(np.float32)
        return (a - a.mean()) / (a.std() + 1e-6)

    macro = z(cv2.resize(g, (16, 16)))                                  # broad layout
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    edge = z(cv2.resize(np.sqrt(gx * gx + gy * gy), (16, 16)))          # shapes/edges
    freq = z(cv2.resize(np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(g)))), (16, 16)))  # texture
    v = np.concatenate([macro.ravel(), edge.ravel(), 0.6 * freq.ravel()]).astype(np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


def fingerprint(rgb: np.ndarray, spec):
    """Return (struct[768], phash[32 uint8], trace_score, energy).

    The design's structure can live in the PAINT (e.g. carbon weave) OR in the SPEC
    (e.g. FRACTURED — flat dark albedo, all the geometry is in the spec). So we
    fingerprint whichever channel CARRIES the structure, and only call a finish
    'solid' when BOTH paint and spec are flat (true gloss/matte)."""
    plum = np.clip(rgb[:, :, :3], 0, 1).mean(axis=2)
    p_energy = float(cv2.resize(plum.astype(np.float32), (64, 64)).std())
    if spec is not None:
        slum = np.asarray(spec[:, :, :3], np.float32).mean(axis=2) / 255.0
        s_energy = float(cv2.resize(slum.astype(np.float32), (64, 64)).std())
    else:
        slum, s_energy = None, 0.0
    energy = max(p_energy, s_energy)                       # solid only if BOTH flat
    carrier = plum if (slum is None or p_energy >= s_energy) else slum
    pf = _struct_desc(carrier)
    ph = _phash_bits(carrier)
    # trace ('does the spec mirror the paint?') only applies when the PAINT carries structure
    if slum is not None and p_energy >= SOLID_STD:
        trace = float(np.dot(_struct_desc(plum), _struct_desc(slum)))
    else:
        trace = 1.0                                        # flat paint / no spec -> trace N/A
    return pf, ph, trace, energy


# ---- catalog enumeration + render ------------------------------------------
def _enumerate():
    """[(id, kind, category)] for base + monolithic + pattern across the picker."""
    from spb_visual_workbench import _load_picker_groups
    g = _load_picker_groups()
    out = []
    for bucket, kind in (("base", "base"), ("special", "monolithic"), ("pattern", "pattern")):
        for cat, ids in (g.get(bucket) or {}).items():
            for i in ids:
                out.append((i, kind, cat))
    # de-dupe (an id can appear once); keep first
    seen, uniq = set(), []
    for i, k, c in out:
        if i not in seen:
            seen.add(i); uniq.append((i, k, c))
    return uniq, g.get("meta", {})


def _src_mtime(eng, item_id, kind):
    import inspect
    fns = []
    try:
        if kind == "base" and item_id in eng.BASE_REGISTRY:
            e = eng.BASE_REGISTRY[item_id]; fns = [e.get("paint_fn"), e.get("base_spec_fn")]
        elif kind == "monolithic" and item_id in eng.MONOLITHIC_REGISTRY:
            e = eng.MONOLITHIC_REGISTRY[item_id]; fns = [e[0] if e else None, e[1] if len(e) > 1 else None]
        elif kind == "pattern" and item_id in eng.PATTERN_REGISTRY:
            fns = [eng.PATTERN_REGISTRY[item_id].get("texture_fn")]
    except Exception:
        return 0.0
    m = 0.0
    for fn in fns:
        try:
            p = inspect.getsourcefile(fn) if fn else None
            if p:
                m = max(m, os.path.getmtime(p))
        except (TypeError, OSError):
            pass
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    WB_DIR.mkdir(parents=True, exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()):
        import shokker_engine_v2 as eng
        if hasattr(eng, "_ensure_expansions_loaded"):
            eng._ensure_expansions_loaded()
    from spb_visual_workbench import _render_item

    items, meta = _enumerate()
    if args.ids:
        want = {x.strip() for x in args.ids.split(",") if x.strip()}
        items = [it for it in items if it[0] in want]
    if args.limit:
        items = items[: args.limit]

    # load existing cache
    cache = {}
    if NPZ.exists() and not args.force:
        try:
            z = np.load(NPZ, allow_pickle=True)
            ids = list(z["ids"]); struct = z["struct"]; phash = z["phash"]
            old_meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
            for k, i in enumerate(ids):
                cache[i] = (struct[k], phash[k], old_meta.get(i, {}))
        except Exception:
            cache = {}

    rows_struct, rows_phash, ids_out, meta_out = [], [], [], {}
    rendered = skipped = failed = 0
    t0 = time.perf_counter()
    for n, (item_id, kind, cat) in enumerate(items):
        mt = _src_mtime(eng, item_id, kind)
        prev = cache.get(item_id)
        if prev and not args.force and abs(float(prev[2].get("mtime", -1)) - mt) < 1e-6:
            rows_struct.append(prev[0]); rows_phash.append(prev[1])
            ids_out.append(item_id); meta_out[item_id] = prev[2]; skipped += 1
            continue
        try:
            rgb, spec, _ = _render_item(eng, item_id, kind, FP_RES, SEED, meta.get(item_id, {}))
            pf, ph, trace, energy = fingerprint(rgb, spec)
        except Exception as e:
            failed += 1
            continue
        rows_struct.append(pf); rows_phash.append(ph); ids_out.append(item_id)
        meta_out[item_id] = {"kind": kind, "category": cat,
                             "name": (meta.get(item_id, {}) or {}).get("name", item_id),
                             "trace": round(trace, 4), "energy": round(energy, 4),
                             "solid": bool(energy < SOLID_STD), "mtime": mt}
        rendered += 1
        if rendered % 50 == 0:
            print(f"  …{rendered} rendered ({n+1}/{len(items)})")

    struct = np.asarray(rows_struct, np.float32)
    phash = np.asarray(rows_phash, np.uint8)
    np.savez_compressed(NPZ, ids=np.array(ids_out, dtype=object), struct=struct, phash=phash)

    # nearest-neighbor pass (cross-category) so the gate/slider is instant
    nn = _neighbors(ids_out, struct, phash, meta_out)
    for i, info in nn.items():
        meta_out[i]["max_sim"] = info["max_sim"]
        meta_out[i]["neighbors"] = info["neighbors"]
    META.write_text(json.dumps({"generated": int(time.time()), "count": len(ids_out),
                                "res": FP_RES, "items": meta_out}, indent=1), encoding="utf-8")
    print(f"DONE: {rendered} rendered, {skipped} cached, {failed} failed, "
          f"{len(ids_out)} indexed in {time.perf_counter()-t0:.1f}s -> {NPZ.name}")


def _sim_matrix(struct, phash):
    """combined similarity 0..1 = 0.5*struct_cosine + 0.5*phash_match."""
    cos = struct @ struct.T                                   # normalized rows -> cosine
    bits = np.unpackbits(phash, axis=1).astype(np.int16)      # N x 256
    # hamming sim = 1 - hamming/256 ; via matmul of {-1,+1}
    pm = (bits * 2 - 1).astype(np.int16)
    match = (pm @ pm.T).astype(np.float32)                    # in [-256,256]
    phash_sim = (match + 256.0) / 512.0
    return 0.5 * cos + 0.5 * phash_sim


def _neighbors(ids, struct, phash, meta_out, topk=6):
    if len(ids) < 2:
        return {i: {"max_sim": 0.0, "neighbors": []} for i in ids}
    S = _sim_matrix(struct, phash)
    np.fill_diagonal(S, -1.0)
    out = {}
    for k, i in enumerate(ids):
        order = np.argsort(-S[k])[:topk]
        neigh = [{"id": ids[j], "sim": round(float(S[k][j]), 3),
                  "category": meta_out.get(ids[j], {}).get("category", "")}
                 for j in order if S[k][j] > 0]
        out[i] = {"max_sim": round(float(neigh[0]["sim"]) if neigh else 0.0, 3),
                  "neighbors": neigh}
    return out


if __name__ == "__main__":
    main()
