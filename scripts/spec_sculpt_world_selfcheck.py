"""Regression guard for Spec Sculpt "SHOKK THE WORLD" (function-level, NO server, NO deploy).

Encodes the invariants established across the 2026-06-02 overnight fix run (see
docs/SPEC_SCULPT_OVERNIGHT.md) so a future engine change can't silently break SHOKK THE WORLD.
Run after ANY edit under engine/ (the concurrent engine work that ran alongside this fix is exactly
the kind of change this catches):

    python scripts/spec_sculpt_world_selfcheck.py        # exit 0 = all pass, 1 = a regression

It exercises the real pipeline (pick_diverse -> scratch_spec_from_any_paint, the same calls the
/api/spec-sculpt/batch route makes) on the example car + synthesized dark / monochrome / uniform
liveries, and asserts: 24 RENDERABLE distinct picks; paint-AWARENESS; 0 flat looks on textured
liveries; the blank-livery detail floor; and no broken/empty renders. Thresholds carry margin vs the
measured values (chevy paw ~0.56, detail ~62; dark/mono ~0.57/~62; white avg detail ~38).
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHEVY = os.path.join("assets", "defaults", "shokker_paint_booth_chevy_truck.psd")
EMPH = ("highlights", "saturated", "shadows", "highlights", "desaturated")
SEED = 9101
SIZE = 320

_fails: list[str] = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        _fails.append(name)


def _corr(a, b):
    a = a.ravel().astype(np.float64) - a.mean()
    b = b.ravel().astype(np.float64) - b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))


def main() -> int:
    import cv2
    from engine.spec_sculpt.core import load_paint_rgb_float01
    from engine.spec_sculpt.generate import scratch_spec_from_any_paint
    from engine.spec_sculpt.catalog_blend import normalize_catalog_stack
    from engine.spec_sculpt.spec_index import pick_diverse

    paint = os.path.abspath(CHEVY)
    if not os.path.isfile(paint):
        print(f"FAIL: example car not found: {paint}")
        return 1
    base, _, _ = load_paint_rgb_float01(paint, target_size=SIZE)
    picks = pick_diverse(24, seed=SEED)

    def comp(tex, i, fid):
        s = scratch_spec_from_any_paint(tex, seed=SEED + i * 17, chromatic_shift=True,
                                        catalog_stack=[(fid, 1.0)], paint_emphasis=EMPH[i % 5],
                                        paint_emphasis_strength=0.5)
        return np.stack([s[:, :, 0], s[:, :, 1], s[:, :, 2]], axis=2).astype(np.uint8)

    def detail(c):
        return float(cv2.Laplacian(c.mean(2).astype(np.float32), cv2.CV_32F).std())

    def gallery(tex):
        cs = [comp(tex, i, p["id"]) for i, p in enumerate(picks)]
        dets = [detail(c) for c in cs]
        feats = np.array([cv2.resize(c, (10, 10), interpolation=cv2.INTER_AREA).reshape(-1).astype(np.float32) for c in cs])
        D = np.array([[np.linalg.norm(feats[a] - feats[b]) for b in range(len(feats))] for a in range(len(feats))])
        iu = np.triu_indices(len(feats), 1)
        return cs, dets, float(D[iu].min())

    # 1) picker returns 24 RENDERABLE, distinct finishes
    print("1) picker:")
    ids = [p["id"] for p in picks]
    _check("pick_diverse returns 24", len(picks) == 24, f"got {len(picks)}")
    _check("all picks distinct", len(set(ids)) == len(ids))
    unrenderable = [i for i in ids if not normalize_catalog_stack([[i, 1.0]])]
    _check("all picks renderable (0 dropped)", not unrenderable, f"unrenderable={unrenderable}")

    # 2) chevy gallery: distinct, paint-aware, detailed, no broken
    print("2) chevy (real livery):")
    r, g, b = base[..., 0], base[..., 1], base[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    mx = base.max(2); mn = base.min(2); sat = np.where(mx > 1e-5, (mx - mn) / (mx + 1e-6), 0)
    cs, dets, minpair = gallery(base)
    paws = [max(abs(_corr(c[..., 0], lum)), abs(_corr(c[..., 0], sat)),
                abs(_corr(c[..., 2], lum)), abs(_corr(c[..., 2], sat))) for c in cs]
    _, edge_n = __import__(
        "engine.paint_v2.cultural_viva_mexico", fromlist=["_viva_mexico_paint_luma_edge"]
    )._viva_mexico_paint_luma_edge(base, np.ones(base.shape[:2], dtype=np.float32))
    edge_corrs = [
        max(abs(_corr(c[..., 0], edge_n)), abs(_corr(c[..., 1], edge_n)), abs(_corr(c[..., 2], edge_n)))
        for c in cs
    ]
    nflat = sum(1 for d in dets if d < 10)
    broken = sum(1 for c in cs if np.isnan(c).any() or c.std() < 3 or c.mean() < 3)
    _check("0 flat looks", nflat == 0, f"flat={nflat}, min detail={min(dets):.1f}")
    _check("paint-aware (avg>0.40)", np.mean(paws) > 0.40, f"avg paw={np.mean(paws):.3f}")
    _check("edge-traced (avg edge corr>0.32)", np.mean(edge_corrs) > 0.32,
           f"avg edge={np.mean(edge_corrs):.3f}")
    _check("distinct (minpair>150)", minpair > 150, f"minpair={minpair:.0f}")
    _check("no broken/empty", broken == 0, f"broken={broken}")

    # 3) dark + monochrome textured liveries: 0 flat (fix#8/#9 robustness)
    print("3) dark + monochrome liveries:")
    dark = np.clip(base * 0.25, 0, 1)
    mono = np.repeat(lum[..., None], 3, axis=2).astype(np.float32)
    _, dd, _ = gallery(dark)
    _, dm, _ = gallery(mono)
    _check("dark: 0 flat", sum(1 for d in dd if d < 10) == 0, f"flat={sum(1 for d in dd if d < 10)}, min={min(dd):.1f}")
    _check("mono: 0 flat", sum(1 for d in dm if d < 10) == 0, f"flat={sum(1 for d in dm if d < 10)}, min={min(dm):.1f}")

    # 4) blank/uniform livery: detail floor keeps it from going flat (fix#7)
    print("4) uniform white livery (detail floor):")
    _, dw, _ = gallery(np.ones((SIZE, SIZE, 3), dtype=np.float32))
    _check("white floor adds texture (avg detail>12)", np.mean(dw) > 12, f"avg detail={np.mean(dw):.1f}")
    _check("white not all-flat (min>0)", min(dw) > 0.0, f"min detail={min(dw):.2f}")

    print()
    if _fails:
        print(f"RESULT: FAIL ({len(_fails)} check(s)): {_fails}")
        return 1
    print("RESULT: PASS - SHOKK THE WORLD invariants hold (24 renderable/distinct, paint-aware, 0 flat on "
          "textured liveries, detail floor on blank, no broken/empty).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
