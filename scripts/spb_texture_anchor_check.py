# -*- coding: utf-8 -*-
"""spb_texture_anchor_check.py -- ENGINE_TEXTURE_ANCHOR lane (2026-10-06). One engine boot per run.

    python scripts/spb_texture_anchor_check.py --baseline   # store sha of the 15 bench payloads (bbox on + off)
    python scripts/spb_texture_anchor_check.py --check      # no-flag regression vs baseline + roof-copy cases
    python scripts/spb_texture_anchor_check.py --roof       # roof-copy cases only
    python scripts/spb_texture_anchor_check.py --time       # timing: roof copy with/without anchor, big F zone

Roof-copy case: ORIGINAL = one whole-car zone (colour 'everything'); COPY = the same zone limited to
the roof rect with zone["texture_anchor"] = "canvas" and the SAME render_seed_index. Verdict compares
paint + spec INSIDE the roof rect. 'noflag' rows show today's behaviour for the same copy without the flag.
Engine log spam -> _zone_cost_bench/engine.log. One verdict line per case.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spb_zone_cost_bench as B  # noqa: E402  (chdirs to ROOT, sets up the log)

BASE_FILE = os.path.join(B.OUT, "texture_anchor_baseline.json")
ROOF = (850, 1550, 440, 1180)  # y0, y1, x0, x1 (prim_inapp BOX['roof'] = x0,y0,x1,y1 440,850,1180,1550)

# (label, zone fields) -- ~8 finish families
CASES = [
    ("foundation_pearl_src", dict(base="f_pearl")),
    ("foundation_chrome_src", dict(base="f_chrome")),
    ("metallic", dict(base="metallic")),
    ("pearl", dict(base="pearl")),
    ("candy", dict(base="candy", base_color_mode="solid", base_color=[0.6, 0.0, 0.9])),
    ("chrome", dict(base="chrome")),
    ("chalky_base", dict(base="chalky_base")),
    ("noise_electric_ice", dict(base="electric_ice")),
    ("noise_patina_bronze", dict(base="patina_bronze")),
    ("pattern_carbon", dict(base="gloss", pattern="carbon_fiber", base_color_mode="solid", base_color=[0.9, 0.2, 0.2])),
    ("mono_truchet", dict(finish="ff_truchet_glass", finish_colors={"c1": "#1e96aa", "c2": None, "c3": None, "ghost": None})),
]


def _zone(name, fields, region=None, rsi=5, anchor=False):
    f = dict(fields)
    base = f.pop("base", None)
    z = B._z(name, base, region, mode=f.pop("base_color_mode", "source"), **f)
    if base is None:
        z.pop("base", None)
    z["render_seed_index"] = rsi
    if anchor:
        z["texture_anchor"] = "canvas"
    return z


def _sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()[:16]


def _diff(a, b):
    d = np.abs(a.astype(np.int32) - b.astype(np.int32))
    return int(d.max()), float(np.mean(np.any(d > 0, axis=-1)) * 100.0)


def known(eng, fields):
    if "finish" in fields:
        return fields["finish"] in getattr(eng, "MONOLITHIC_REGISTRY", {})
    from engine.registry import BASE_REGISTRY as R
    return fields["base"] in R


def roof_cases(eng, paint_file, rows):
    y0, y1, x0, x1 = ROOF
    roof = B.rect(y0, y1, x0, x1)
    for label, fields in CASES:
        if not known(eng, fields):
            print(f"ROOF {label:24s} SKIP (id not registered)")
            continue
        try:
            whole = B.rect(0, B.H, 0, B.W)  # whole-car zone as a full-canvas region, so masks match inside the roof
            po, so, to = B.render(eng, [_zone("orig", fields, region=whole)], paint_file, True)
            for tag, anchor in (("anchor", True), ("noflag", False)):
                pc, sc, tc = B.render(eng, [_zone("copy", fields, region=roof, anchor=anchor)], paint_file, True)
                dp, fp = _diff(po[y0:y1, x0:x1], pc[y0:y1, x0:x1])
                ds, fs = _diff(so[y0:y1, x0:x1], sc[y0:y1, x0:x1])
                v = "BIT-EXACT" if dp == 0 and ds == 0 else ("DIFF<=1" if dp <= 1 and ds <= 1 else "DIFF")
                print(f"ROOF {label:24s} {tag:6s} {v:9s} paint_max={dp} paint_px={fp:5.1f}% spec_max={ds} spec_px={fs:5.1f}%  t_orig={to:.2f}s t_copy={tc:.2f}s")
                rows.append(dict(case=label, mode=tag, verdict=v, paint_max=dp, paint_px=fp, spec_max=ds, spec_px=fs, t_orig=to, t_copy=tc))
            # original under an everything-but-roof zone (the _seedtest.py scenario), anchored
            notroof = 1.0 - roof
            top = _zone("top", dict(base="f_soft_gloss" if known(eng, dict(base="f_soft_gloss")) else "gloss"), region=notroof, rsi=9)
            pa, sa, ta = B.render(eng, [top, _zone("orig", fields, region=whole, anchor=True)], paint_file, True)
            dp, fp = _diff(po[y0:y1, x0:x1], pa[y0:y1, x0:x1])
            ds, fs = _diff(so[y0:y1, x0:x1], sa[y0:y1, x0:x1])
            v = "BIT-EXACT" if dp == 0 and ds == 0 else ("DIFF<=1" if dp <= 1 and ds <= 1 else "DIFF")
            print(f"ROOF {label:24s} under  {v:9s} paint_max={dp} paint_px={fp:5.1f}% spec_max={ds} spec_px={fs:5.1f}%  (orig anchored, everything-but-roof zone on top)")
            rows.append(dict(case=label, mode="under", verdict=v, paint_max=dp, paint_px=fp, spec_max=ds, spec_px=fs))
        except Exception as ex:
            print(f"ROOF {label:24s} ERROR {type(ex).__name__}: {ex}")
            rows.append(dict(case=label, mode="error", verdict="ERROR"))


def noop_cases(eng, paint_file):
    """Every paint-noop base whose flat plate declines (all Foundation f_* PURE specs + noisy-spec
    paint_none bases), sampled, over 4 mask shapes, alone and under a catch-all: new path vs old."""
    from engine.registry import BASE_REGISTRY as R
    ids = sorted(k for k, v in R.items()
                 if eng._base_paint_fn_is_noop(v.get("paint_fn")) and eng._flat_base_spec_constants(k, v) is None
                 and not v.get("blend_only"))
    pick = [b for b in ("f_pearl", "f_chrome", "f_metallic", "f_satin_chrome", "f_soft_matte", "f_brushed") if b in ids]
    pick += [b for b in ids[:: max(1, len(ids) // 10)] if b not in pick][:10]
    y0, y1, x0, x1 = ROOF
    masks = {"notroof": 1.0 - B.rect(y0, y1, x0, x1), "roof": B.rect(y0, y1, x0, x1),
             "soft": B.soft_ellipse(1000, 600, 140, 260),
             "noisy": (np.random.default_rng(5).random((B.H, B.W), dtype=np.float32) * B.rect(200, 900, 300, 1500))}
    print(f"NOOP candidates {len(ids)} paint-noop bases without a flat plate; testing {len(pick)}")
    bad = n = 0
    told, tnew = [], []
    for b in pick:
        for mn, m in masks.items():
            for tag, zs in (("alone", [_zone("F", dict(base=b), region=m, rsi=7)]),
                            ("+rem", [_zone("F", dict(base=b), region=m, rsi=7), B._rem()])):
                os.environ["SPB_NOOP_PAINT_SKIP"] = "0"
                p0, s0, t0 = B.render(eng, zs, paint_file, True)
                os.environ["SPB_NOOP_PAINT_SKIP"] = "1"
                p1, s1, t1 = B.render(eng, zs, paint_file, True)
                same = np.array_equal(p0, p1) and np.array_equal(s0, s1)
                n += 1
                bad += 0 if same else 1
                if mn == "notroof":
                    told.append(t0)
                    tnew.append(t1)
                dp, _ = _diff(p0, p1)
                ds, _ = _diff(s0, s1)
                print(f"NOOP {b:24s} {mn:8s} {tag:5s} {'BIT-EXACT' if same else 'DIFF'} paint_max={dp} spec_max={ds} t_old={t0:.2f}s t_new={t1:.2f}s")
    os.environ.pop("SPB_NOOP_PAINT_SKIP", None)
    print(f"NOOP SUMMARY {n - bad}/{n} bit-exact; notroof median old={np.median(told):.2f}s new={np.median(tnew):.2f}s")
    return 1 if bad else 0


def bench_hashes(eng, paint_file):
    out = {}
    for k, zones in B.all_payloads().items():
        for on in (True, False):
            p, s, _ = B.render(eng, zones, paint_file, on)
            out[f"{k}|bbox={int(on)}"] = [_sha(p), _sha(s)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--roof", action="store_true")
    ap.add_argument("--time", action="store_true")
    ap.add_argument("--old", action="store_true", help="with --baseline: bake it with the flag gate patched to False (= pre-change engine), then restore")
    ap.add_argument("--noop", action="store_true", help="paint-noop spec-only path: on vs SPB_NOOP_PAINT_SKIP=0, bit-exact + timing")
    ap.add_argument("--profile", action="store_true", help="cProfile the big Foundation F zone -> _zone_cost_bench/profile_F_zone.txt")
    a = ap.parse_args()
    paint_file = B._paint_file()
    eng = B.boot()
    B.render(eng, [B._rem("gloss", "100")], paint_file, True)  # warm
    rc = 0
    if a.profile:
        import cProfile
        import io
        import pstats
        y0, y1, x0, x1 = ROOF
        zs = [_zone("F", dict(base="f_pearl"), region=1.0 - B.rect(y0, y1, x0, x1))]
        B.render(eng, zs, paint_file, True)
        pr = cProfile.Profile()
        pr.enable()
        _, _, dt = B.render(eng, zs, paint_file, True)
        pr.disable()
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(50)
        s2 = io.StringIO()
        pstats.Stats(pr, stream=s2).sort_stats("tottime").print_stats(35)
        fn = os.path.join(B.OUT, "profile_F_zone.txt")
        open(fn, "w", encoding="utf-8").write(s.getvalue() + "\n\n==== TOTTIME ====\n" + s2.getvalue())
        print(f"PROFILE F zone (f_pearl, not-roof): {dt:.2f}s -> {fn}")
    if os.environ.get("PYTHONHASHSEED") != "0":
        print("WARN PYTHONHASHSEED is not 0: base seed offsets use hash(base_id) (the app runs with 0); cross-process shas will not match")
    if a.baseline:
        _real = eng._zone_texture_anchor_canvas
        if a.old:
            eng._zone_texture_anchor_canvas = lambda z: False
            os.environ["SPB_NOOP_PAINT_SKIP"] = "0"
        try:
            h = bench_hashes(eng, paint_file)
        finally:
            eng._zone_texture_anchor_canvas = _real
            os.environ.pop("SPB_NOOP_PAINT_SKIP", None)
        json.dump(h, open(BASE_FILE, "w"), indent=1)
        print(f"BASELINE {len(h)} renders -> {BASE_FILE}")
    if a.check:
        ref = json.load(open(BASE_FILE))
        cur = bench_hashes(eng, paint_file)
        bad = 0
        for k, v in cur.items():
            same = ref.get(k) == v
            bad += 0 if same else 1
            print(f"NOFLAG {k:46s} {'BIT-EXACT' if same else 'CHANGED'}")
        print(f"NOFLAG SUMMARY: {len(cur) - bad}/{len(cur)} bit-exact vs baseline")
        rc = rc or (1 if bad else 0)
    if a.noop:
        rc = rc or noop_cases(eng, paint_file)
    if a.check or a.roof:
        rows = []
        roof_cases(eng, paint_file, rows)
        json.dump(rows, open(os.path.join(B.OUT, "texture_anchor_roof.json"), "w"), indent=1)
        n_ok = sum(1 for r in rows if r.get("mode") in ("anchor", "under") and r["verdict"] in ("BIT-EXACT", "DIFF<=1"))
        n_all = sum(1 for r in rows if r.get("mode") in ("anchor", "under", "error"))
        print(f"ROOF SUMMARY: {n_ok}/{n_all} anchored rows bit-exact (or <=1)")
    if a.time:
        y0, y1, x0, x1 = ROOF
        roof = B.rect(y0, y1, x0, x1)
        notroof = 1.0 - roof
        sets = {
            "roof_copy_f_pearl_noflag": [_zone("copy", dict(base="f_pearl"), region=roof)],
            "roof_copy_f_pearl_anchor": [_zone("copy", dict(base="f_pearl"), region=roof, anchor=True)],
            "roof_copy_chalk_noflag": [_zone("copy", dict(base="chalky_base"), region=roof)],
            "roof_copy_chalk_anchor": [_zone("copy", dict(base="chalky_base"), region=roof, anchor=True)],
            "F_f_pearl_not_roof": [_zone("F", dict(base="f_pearl"), region=notroof)],
            "F_f_pearl_not_roof+rem": [_zone("F", dict(base="f_pearl"), region=notroof), B._rem()],
            "F_f_pearl_everything": [_zone("F", dict(base="f_pearl"))],
        }
        for k, zs in sets.items():
            ts = []
            for _ in range(3):
                ts.append(B.render(eng, zs, paint_file, True)[2])
            print(f"TIME {k:28s} median={float(np.median(ts)):.2f}s ({' '.join(f'{t:.2f}' for t in ts)})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
