# -*- coding: utf-8 -*-
"""spb_zone_cost_bench.py -- per-zone render cost bench + old-vs-new bit-exact harness.

ENGINE_ZONE_COST lane (2026-10-05). One engine boot per run; every verdict is one line.

    python scripts/spb_zone_cost_bench.py --check            # old (SPB_ZONE_BBOX=0) vs new, bit-exact per payload
    python scripts/spb_zone_cost_bench.py --time --runs 3     # timing table old vs new (cold zone cache each run)
    python scripts/spb_zone_cost_bench.py --profile P05       # cProfile one payload -> _zone_cost_bench/profile_<id>.txt
    python scripts/spb_zone_cost_bench.py --list              # payload ids

Payloads: synthetic flames / part-region / gradient / Foundation spec-only / pattern / monolithic
zones on a real 2048 ARCA paint, plus the captured output/job_render_*/zones_payload.json files
(their source_layer masks are not recoverable from the JSON dump, so those keys are dropped and the
zones replay as global colour/region zones). Engine log spam goes to _zone_cost_bench/engine.log.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import glob
import io
import json
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "_zone_cost_bench")
os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, "engine.log"), "a", encoding="utf-8", errors="replace")

H = W = 2048
PAINT_DIRS = sorted(glob.glob(os.path.join(ROOT, "output", "job_render_*")))


def _paint_file():
    for d in reversed(PAINT_DIRS):
        p = os.path.join(d, "ORIGINAL_paint_with_decals.png")
        if os.path.exists(p):
            return p
    raise SystemExit("no paint found under output/job_render_*")


# ---------------------------------------------------------------- masks
PARTS = {  # rough ARCA-sheet part rects (y0, y1, x0, x1); front = 'l' or 'r'
    "left": (90, 560, 80, 1960, "l"),
    "right": (1490, 1960, 80, 1960, "l"),
    "hood": (720, 1320, 1240, 1900, "r"),
}


def flame_mask(part, licks=6, length=0.62, seed=1, inner=0.0):
    y0, y1, x0, x1, front = PARTS[part]
    m = np.zeros((H, W), np.float32)
    hh, ww = y1 - y0, x1 - x0
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    u = xx / ww if front == "l" else 1.0 - xx / ww
    v = yy / hh
    rng = np.random.default_rng(seed)
    out = u < (0.08 - inner * 0.05)
    for k in range(licks):
        vc = (k + 0.5) / licks + 0.04 * np.sin(u * 9.0 + k)
        L = length * (0.6 + 0.4 * rng.random()) * (1.0 - inner)
        half = (0.5 / licks) * (1.0 - inner) * np.clip(1.0 - u / max(L, 1e-3), 0, 1) ** 1.1
        out |= (np.abs(v - vc) < half) & (u < L)
    m[y0:y1, x0:x1] = out.astype(np.float32)
    return m


def ring(mask, w=7):
    import cv2
    k = np.ones((2 * w + 1, 2 * w + 1), np.uint8)
    d = cv2.dilate((mask > 0.5).astype(np.uint8), k)
    return ((d > 0) & (mask < 0.5)).astype(np.float32)


def rect(y0, y1, x0, x1):
    m = np.zeros((H, W), np.float32)
    m[y0:y1, x0:x1] = 1.0
    return m


def soft_ellipse(cy, cx, ry, rx, feather=12.0):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2)
    return np.clip((1.0 - d) * min(ry, rx) / feather, 0, 1).astype(np.float32)


def flames_all(**kw):
    m = np.zeros((H, W), np.float32)
    for i, p in enumerate(("left", "right", "hood")):
        m = np.maximum(m, flame_mask(p, seed=i + 1, **kw))
    return m


def _z(name, base, region=None, color="everything", mode="source", **extra):
    z = {"name": name, "color": color, "intensity": "100", "base": base, "pattern": "none",
         "pattern_paint_mode": "overlay", "pattern_hue_shift": 0, "pattern_saturation": 0,
         "pattern_spec_opacity": 0, "base_color_mode": mode, "base_color_explicit": True,
         "base_color_strength": 1, "hard_edge": True}
    if region is not None:
        z["region_mask"] = region
    z.update(extra)
    return z


def _rem(base="gloss", intensity="50"):
    z = _z("Everything Else", base, color="remaining")
    z["intensity"] = intensity
    return z


FIRE = [{"pos": 0.0, "color": [1.0, 0.96, 0.7]}, {"pos": 0.1, "color": [1.0, 0.85, 0.0]},
        {"pos": 0.34, "color": [1.0, 0.54, 0.0]}, {"pos": 0.62, "color": [0.89, 0.15, 0.06]},
        {"pos": 1.0, "color": [0.55, 0.09, 0.04]}]


def synthetic_payloads():
    P = {}
    fl = flames_all()
    P["S01_body_only"] = [_rem("gloss", "100")]
    P["S02_plus1_solid_3pct"] = [_z("hood box", "f_candy", rect(800, 1100, 1350, 1750), mode="solid",
                                    base_color=[0.1, 0.3, 0.9]), _rem()]
    P["S03_plus2_solid_grad"] = [
        _z("hood box", "f_candy", rect(800, 1100, 1350, 1750), mode="solid", base_color=[0.1, 0.3, 0.9]),
        _z("side stripe", "wet_look", rect(300, 380, 100, 1900), mode="gradient", gradient_stops=FIRE,
           gradient_direction="horizontal"), _rem()]
    P["S04_plus4_mixed"] = [
        _z("hood box", "f_candy", rect(800, 1100, 1350, 1750), mode="solid", base_color=[0.1, 0.3, 0.9]),
        _z("side stripe", "wet_look", rect(300, 380, 100, 1900), mode="gradient", gradient_stops=FIRE,
           gradient_direction="horizontal"),
        _z("roof chrome (spec only)", "f_chrome", rect(1150, 1400, 200, 900)),
        _z("rocker solid", "f_pearl", rect(1880, 1950, 100, 1900), mode="solid", base_color=[0.9, 0.9, 0.1]),
        _rem()]
    P["S05_flames_hotrod"] = [
        _z("flames fill", "f_candy", fl, mode="gradient", gradient_stops=FIRE, gradient_direction="horizontal"),
        _z("flames outline", "wet_look", ring(fl, 7), mode="solid", base_color=[0.12, 0.3, 1.0]),
        _rem()]
    outer = fl
    mid = flames_all(inner=0.35)
    core = flames_all(inner=0.65)
    P["S06_truefire_3layers"] = [
        _z("core", "wet_look", core, mode="solid", base_color=[1.0, 0.89, 0.48]),
        _z("mid", "f_candy", mid, mode="solid", base_color=[1.0, 0.42, 0.0]),
        _z("outer", "f_candy", outer, mode="gradient", gradient_stops=FIRE, gradient_direction="horizontal",
           base_color_fit_zone=True),
        _rem()]
    P["S07_foundation_spec_only_parts"] = [
        _z("hood satin chrome", "f_satin_chrome", rect(720, 1320, 1240, 1900)),
        _z("left soft matte", "f_soft_matte", rect(90, 560, 80, 1960)),
        _z("right chrome", "f_chrome", rect(1490, 1960, 80, 1960)),
        _rem()]
    P["S08_soft_edge_solid_strength"] = [
        _z("soft blob", "f_metallic", soft_ellipse(1000, 600, 140, 260), mode="solid",
           base_color=[0.2, 0.9, 0.3], base_color_strength=0.6, hard_edge=False),
        _z("grad vertical scaled", "f_pearl", rect(1500, 1900, 300, 900), mode="gradient", gradient_stops=FIRE,
           gradient_direction="vertical", base_scale=0.5),
        _rem()]
    P["S09_pattern_and_noise_base"] = [
        _z("candy noise", "candy", rect(800, 1100, 1350, 1750), mode="solid", base_color=[0.6, 0.0, 0.9]),
        _z("pattern zone", "gloss", rect(300, 500, 200, 800), mode="solid", base_color=[0.9, 0.2, 0.2],
           pattern="carbon_fiber"),
        _rem()]
    P["S10_monolithic_region"] = [
        dict(_z("truchet hood", None, rect(800, 1200, 1300, 1800)), finish="ff_truchet_glass",
             finish_colors={"c1": "#1e96aa", "c2": None, "c3": None, "ghost": None}),
        _z("solid stripe", "gloss", rect(600, 660, 100, 1900), mode="solid", base_color=[0.0, 0.0, 0.0]),
        _rem()]
    P["S11_hsb_and_colormatch"] = [
        _z("hsb tweak", "f_metallic", rect(400, 600, 300, 1000), base_hue_offset=30, base_saturation_adjust=10),
        _z("recolor dark", "f_candy", color={"color_rgb": [40, 40, 40], "tolerance": 18}, mode="solid",
           base_color=[0.4, 0.1, 0.6]),
        _rem()]
    for k in list(P):
        for z in P[k]:
            if z.get("base") is None:
                z.pop("base", None)
    return P


def captured_payloads():
    P = {}
    for f in PAINT_DIRS:
        jp = os.path.join(f, "zones_payload.json")
        if not os.path.exists(jp):
            continue
        d = json.load(open(jp, encoding="utf-8"))
        zones = []
        for z in d["zones"]:
            z = {k: v for k, v in z.items() if not k.startswith("source_layer") and not k.startswith("_source_layer")
                 and k not in ("region_mask", "spatial_mask")}
            zones.append(z)
        P["C_" + os.path.basename(f)[-12:]] = zones
    return P


def all_payloads():
    P = synthetic_payloads()
    P.update(captured_payloads())
    return P


# ---------------------------------------------------------------- engine
def boot():
    with contextlib.redirect_stdout(LOG), contextlib.redirect_stderr(LOG):
        import shokker_engine_v2 as eng
    return eng


def render(eng, zones, paint_file, bbox_on):
    os.environ["SPB_ZONE_BBOX"] = "1" if bbox_on else "0"
    if hasattr(eng.build_multi_zone, "_zone_cache"):
        eng.build_multi_zone._zone_cache.clear()
    zs = copy.deepcopy(zones)
    t = time.perf_counter()
    with contextlib.redirect_stdout(LOG), contextlib.redirect_stderr(LOG):
        paint, spec, _ms = eng.preview_render(paint_file, zs, seed=51, preview_scale=1.0)
    dt = time.perf_counter() - t
    return np.asarray(paint), np.asarray(spec), dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--time", action="store_true")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--lines", default=None, help="line-level timer of build_multi_zone for one payload")
    ap.add_argument("--unit", action="store_true", help="float-level compose_paint_mod full vs gathered")
    ap.add_argument("--only", default=None, help="comma list of payload id prefixes")
    a = ap.parse_args()
    P = all_payloads()
    if a.only:
        pre = a.only.split(",")
        P = {k: v for k, v in P.items() if any(k.startswith(p) for p in pre)}
    if a.list:
        for k, v in P.items():
            print(k, len(v), "zones")
        return 0
    paint_file = _paint_file()
    eng = boot()
    render(eng, P[next(iter(P))], paint_file, False)  # warm caches / lazy loads
    rc = 0
    if a.profile:
        import cProfile
        import pstats
        key = next(k for k in P if k.startswith(a.profile))
        on = os.environ.get("BENCH_PROFILE_NEW", "0") == "1"
        render(eng, P[key], paint_file, on)
        pr = cProfile.Profile()
        pr.enable()
        _, _, dt = render(eng, P[key], paint_file, on)
        pr.disable()
        fn = os.path.join(OUT, f"profile_{key}_{'new' if on else 'old'}.txt")
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(45)
        s2 = io.StringIO()
        pstats.Stats(pr, stream=s2).sort_stats("tottime").print_stats(30)
        open(fn, "w", encoding="utf-8").write(s.getvalue() + "\n\n==== TOTTIME ====\n" + s2.getvalue())
        print(f"PROFILE {key} {'new' if on else 'old'}: {dt:.2f}s -> {fn}")
    if a.lines:
        # Line-level cumulative timer for build_multi_zone's own frame (callee time included).
        key = next(k for k in P if k.startswith(a.lines))
        on = os.environ.get("BENCH_PROFILE_NEW", "0") == "1"
        render(eng, P[key], paint_file, on)
        acc = {}
        target = eng.build_multi_zone.__code__
        state = {}

        def _local(frame, event, arg):
            if event in ("line", "return"):
                now = time.perf_counter()
                prev = state.get(id(frame))
                if prev is not None:
                    acc[prev[0]] = acc.get(prev[0], 0.0) + (now - prev[1])
                state[id(frame)] = (frame.f_lineno, time.perf_counter())
            return _local

        def _global(frame, event, arg):
            if event == "call" and frame.f_code is target:
                return _local
            return None
        sys.settrace(_global)
        try:
            _, _, dt = render(eng, P[key], paint_file, on)
        finally:
            sys.settrace(None)
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:40]
        fn = os.path.join(OUT, f"lines_{key}_{'new' if on else 'old'}.txt")
        with open(fn, "w", encoding="utf-8") as f:
            f.write(f"total {dt:.2f}s\n")
            for ln, t in top:
                f.write(f"{t:7.3f}s  L{ln}\n")
        print(f"LINES {key}: {dt:.2f}s -> {fn}")
    if a.unit:
        # Float-level (pre-uint8) equality: compose_paint_mod full canvas vs compose_paint_mod_gathered.
        from engine.compose import compose_paint_mod, compose_paint_mod_gathered
        rng = np.random.default_rng(7)
        base_paint = rng.random((H, W, 3), dtype=np.float32)
        masks = {"hard_flames": flames_all(), "ring": ring(flames_all(), 7),
                 "soft_ellipse": soft_ellipse(1000, 600, 140, 260),
                 "noisy_soft": (rng.random((H, W), dtype=np.float32) * rect(200, 900, 300, 1500))}
        grads = [dict(stops=FIRE, direction=d) for d in ("horizontal", "vertical", "diagonal_down", "diagonal_up", "radial", "weird")]
        cases = []
        for mname, m in masks.items():
            cases.append((mname, "f_candy", dict(base_color_mode="solid", base_color=[0.1, 0.3, 0.9])))
            cases.append((mname, "wet_look", dict(base_color_mode="solid", base_color="#ff8800", base_color_strength=0.55)))
            cases.append((mname, "f_pearl", dict(base_color_mode="source", base_hue_offset=40, base_saturation_adjust=-20, base_brightness_adjust=15)))
            cases.append((mname, "gloss", dict(base_color_mode="source", base_strength=0.4)))
            cases.append((mname, "f_metallic", dict(base_color_mode="solid", base_color=[0.9, 0.1, 0.2], base_strength=0.7, base_hue_offset=-25)))
            for g in grads:
                cases.append((mname, "f_candy", dict(base_color_mode="gradient", base_color=g, base_color_strength=0.8)))
            cases.append((mname, "f_candy", dict(base_color_mode="gradient", base_color=grads[0], base_color_fit_zone=True)))
            cases.append((mname, "f_pearl", dict(base_color_mode="gradient", base_color=grads[4], base_color_fit_zone=True, base_hue_offset=12)))
            cases.append((mname, "wet_look", dict(base_color_mode="solid", base_color=[0.2, 0.7, 0.4], base_color_fit_zone=True)))
            for g in grads:
                cases.append((mname, "f_pearl", dict(base_color_mode="gradient", base_color=g, base_hue_offset=-33, base_saturation_adjust=25)))
                cases.append((mname, "f_candy", dict(base_color_mode="gradient", base_color=g, base_color_fit_zone=True, base_brightness_adjust=-18, base_strength=0.6)))
            cases.append((mname, "f_metallic", dict(base_color_mode="solid", base_color=[0.5, 0.2, 0.8], base_saturation_adjust=40, base_brightness_adjust=10)))
        bad = 0
        for mname, base, kw in cases:
            m = masks[mname]
            full = np.asarray(compose_paint_mod(base, "none", base_paint.copy(), (H, W), m, 51, 1.0, 1.0, scale=1.0, rotation=0, **kw))
            g, why = compose_paint_mod_gathered(base, "none", base_paint.copy(), (H, W), m, 51, 1.0, 1.0, scale=1.0, rotation=0, **kw)
            if g is None:
                print(f"UNIT {mname:12s} {base:10s} {kw.get('base_color_mode')}: REJECTED ({why})")
                continue
            same = full.shape == g.shape and full.dtype == g.dtype and np.array_equal(full.view(np.uint32), g.view(np.uint32))
            d = float(np.max(np.abs(full.astype(np.float64) - g.astype(np.float64)))) if full.shape == g.shape else -1
            if not same:
                bad += 1
            desc = (kw.get("base_color", {}).get("direction") if isinstance(kw.get("base_color"), dict) else "") + ("+fit" if kw.get("base_color_fit_zone") else "")
            print(f"UNIT {mname:12s} {base:10s} {kw.get('base_color_mode'):8s} {desc:13s} {'FLOAT-EXACT' if same else 'DIFF'} maxabs={d:.3g}")
        print(f"UNIT SUMMARY: {len(cases) - bad}/{len(cases)} float-exact")
        rc = rc or (1 if bad else 0)
    if a.check:
        for k, zones in P.items():
            try:
                p0, s0, _ = render(eng, zones, paint_file, False)
                p1, s1, _ = render(eng, zones, paint_file, True)
                dp = int(np.max(np.abs(p0.astype(np.int32) - p1.astype(np.int32)))) if p0.shape == p1.shape else -1
                ds = int(np.max(np.abs(s0.astype(np.int32) - s1.astype(np.int32)))) if s0.shape == s1.shape else -1
                nd = int(np.count_nonzero(np.any(p0 != p1, axis=-1))) + int(np.count_nonzero(np.any(s0 != s1, axis=-1))) if dp >= 0 and ds >= 0 else -1
                v = "BIT-EXACT" if dp == 0 and ds == 0 else ("DIFF<=1" if 0 <= dp <= 1 and 0 <= ds <= 1 else "DIFF")
                if v != "BIT-EXACT":
                    rc = 1
                print(f"CHECK {k:34s} {v:9s} paint_maxabs={dp} spec_maxabs={ds} px_diff={nd} dtype={p0.dtype}/{s0.dtype}")
            except Exception as ex:
                rc = 1
                print(f"CHECK {k:34s} ERROR {type(ex).__name__}: {ex}")
    if a.time:
        rows = []
        for k, zones in P.items():
            told, tnew = [], []
            for _ in range(a.runs):
                told.append(render(eng, zones, paint_file, False)[2])
                tnew.append(render(eng, zones, paint_file, True)[2])
            mo, mn = float(np.median(told)), float(np.median(tnew))
            rows.append((k, len(zones), mo, mn))
            print(f"TIME {k:34s} zones={len(zones)} old={mo:.2f}s new={mn:.2f}s  ({' '.join(f'{x:.2f}' for x in told)} | {' '.join(f'{x:.2f}' for x in tnew)})")
        with open(os.path.join(OUT, "timing.json"), "w") as f:
            json.dump(rows, f, indent=1)
    return rc


if __name__ == "__main__":
    sys.exit(main())
