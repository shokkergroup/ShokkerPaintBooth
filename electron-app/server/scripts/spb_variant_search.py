# -*- coding: utf-8 -*-
"""SPB VARIANT SEARCH — mechanical "iterate 10x per finish, keep the best".

Owner mandate 2026-09-04:

    "Iterate a MINIMUM of 10 times PER FINISH AND SPEC. Iterate and then pick the
     best out of the 10. Play around. Find the best finishes possible."
    "NO CONFETTI LOOKS where you put random 'noise' in just to pass gates. I'd
     rather have CLEAN looking specs that are interesting. Don't need a lot of
     grit in them."

Hand-tuning 88 finishes ten times each is not a thing a session can honestly do,
and "I tried some numbers" is exactly the unfalsifiable claim this project has
been burned by before. So the iteration is mechanical and leaves a record:

  * each finish declares a PARAM SPACE (3-6 knobs that materially change the look)
  * this harness samples N points in that space deterministically, renders paint
    AND spec for each, and scores them
  * the winning index is written to a sidecar JSON the module loads at import
  * `--report` prints the full score table, so any claim about "the best of 10"
    can be checked against the numbers that produced it

THE SCORE — built to encode the owner's words, not to be easy to pass
--------------------------------------------------------------------
GRIT      INCOHERENT high-frequency energy.  PENALISED hard.  This is the
          anti-confetti term.  Note it is HF energy weighted by (1 - coherence),
          not raw HF energy: a punched lattice, a moulded channel grid and a
          printer's head bands are all hard-edged and all perfectly organised.
          Sharp is not noisy.  Only HF that fails to correlate with its own
          neighbours counts against a finish.
BAND      std(blur4 - blur24) / std(lum).  Energy in the 8-48px car window — the
          scale the owner has asked for since 2026-05-21.  REWARDED.
COVER     fraction of 8x8 tiles carrying real local variation.  REWARDED.
CONTRAST  p99.5-p00.5 of luminance, saturating at 0.60 so blowing the image out
          cannot buy score.  The wide percentiles are deliberate: p3..p97 reads
          0.000 on a field of small sparse marks, which is a real look.
DEAD      fraction of near-black / near-white pixels.  PENALISED (the 2026-09-02
          COVERAGE axis, which caught three near-solid-black PARADIGM finishes).
SHADES    distinct quantised levels the spec deals across M/R/CC.  REWARDED —
          this is the owner's "WAY more spec coloring/shades" made countable.
FOLLOW    correlation between the paint's structure and the spec's, band-limited.
          REWARDED: the spec has to follow the artwork (FINISH LAW axis 2).

AMP       std of luminance over its MEAN, and BAND_ABS the un-normalised car-window
          energy.  REWARDED, and hard-gated.  Without these the whole score is
          scale-free and a flat-grey finish ties with a strong one.

Hard fails (score forced to -inf, cannot be chosen):
    DEAD > 0.55, CONTRAST < 0.06, GRIT > 0.62, AMP < 0.065, BAND_ABS < 0.010,
    or a render that is not finite.

USAGE
    python scripts/spb_variant_search.py --module engine.paint_v2.wrap_shop_2026
    python scripts/spb_variant_search.py --module ... --report
    python scripts/spb_variant_search.py --module ... --ids wrap_squeegee,wrap_stretch
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

RES = 1024         # search resolution: the metrics below are scale-relative
N_VARIANTS = 10    # the owner's floor


# ───────────────────────────────────────────────────────────── sampling ──
def sample_space(space, n=N_VARIANTS, seed=20260904):
    """Deterministic quasi-random samples of a param space.

    space: {name: (lo, hi)} for floats, or {name: [a, b, c]} for categoricals.
    Index 0 is always the space's midpoint / first categorical, so the default
    build is in the candidate set and a search can only improve on it.
    """
    names = sorted(space)
    out = []
    mid = {}
    for k in names:
        v = space[k]
        mid[k] = (float(v[0]) + float(v[1])) / 2.0 if isinstance(v, tuple) else v[0]
    out.append(mid)
    # additive-recurrence (golden ratio) sequence — low discrepancy, no deps
    phi = [0.7548776662466927, 0.5698402909980532, 0.6180339887498949,
           0.8191725133961646, 0.3819660112501051, 0.2451223337533073]
    for i in range(1, int(n)):
        p = {}
        for j, k in enumerate(names):
            v = space[k]
            t = ((i + 1) * phi[j % len(phi)] + (seed % 97) * 0.01) % 1.0
            if isinstance(v, tuple):
                p[k] = float(v[0]) + (float(v[1]) - float(v[0])) * t
            else:
                p[k] = v[int(t * len(v)) % len(v)]
        out.append(p)
    return out


# ───────────────────────────────────────────────────────────── metrics ──
def _box(a, r):
    """Fast box blur of radius r via a summed-area table (separable, wrap-free)."""
    a = np.asarray(a, np.float32)
    r = max(1, int(r))
    pad = np.pad(a, ((r, r), (r, r)), mode="reflect")
    c = np.cumsum(np.cumsum(pad, 0, dtype=np.float32), 1, dtype=np.float32)
    c = np.pad(c, ((1, 0), (1, 0)), mode="constant")
    h, w = a.shape
    k = 2 * r + 1
    s = (c[k:k + h, k:k + w] - c[0:h, k:k + w] - c[k:k + h, 0:w] + c[0:h, 0:w])
    return (s / float(k * k)).astype(np.float32)


def measure(paint, spec):
    """All scoring statistics for one candidate. paint HxWx3 0..1, spec (M,R,CC) 0..255.

    The band radii SCALE with the render size so the 8-32px car window at 2048 is
    the window measured at any search resolution. Features here are authored in
    absolute pixels, so a fixed radius would judge a 1024 search in a different
    band than the 2048 the finish actually ships at.
    """
    p = np.clip(np.asarray(paint, np.float32), 0, 1)
    lum = p[:, :, 0] * 0.299 + p[:, :, 1] * 0.587 + p[:, :, 2] * 0.114
    sd = float(lum.std())
    if not np.isfinite(sd) or sd < 1e-6:
        return None
    # GRIT = high-frequency energy that is INCOHERENT. The first cut of this metric
    # used raw HF energy and failed six finishes whose structure is hard-edged but
    # perfectly organised (a punched lattice, a moulded channel grid, printer bands).
    # Sharp != noisy. Confetti is HF energy whose residual does not correlate with
    # its own neighbours; a stripe or a lattice correlates strongly along itself.
    # ABSOLUTE amplitude. Every shape term below is divided by std, so a field that
    # is structurally perfect but invisibly faint scores identically to a strong one.
    # That blindness passed all 22 wrap finishes while the 1:1 sheet showed eleven of
    # them as flat grey. amp/band_abs are the terms that cannot be normalised away.
    # Relative to the MEAN, not to its own std: a flat field still scores 0, but a
    # finish is not punished for sitting on a dark livery. (Absolute sd made every
    # multiplicative finish fail the moment the test source went from 0.5 grey to a
    # deep red at 0.28 luminance — the finishes had not changed at all.)
    amp = sd / (float(lum.mean()) + 1e-6)
    hf = lum - _box(lum, 1)
    hsd = float(hf.std())
    if hsd < 1e-6:
        coherence = 1.0
    else:
        z = (hf - hf.mean()) / hsd
        coherence = max(abs(float((z * np.roll(z, 1, 1)).mean())),
                        abs(float((z * np.roll(z, 1, 0)).mean())),
                        abs(float((z * np.roll(z, 2, 1)).mean())),
                        abs(float((z * np.roll(z, 2, 0)).mean())),
                        abs(float((z * np.roll(np.roll(z, 1, 0), 1, 1)).mean())))
    grit = (hsd / (sd + 1e-6)) * (1.0 - min(1.0, coherence))
    _r = max(1, int(round(4 * lum.shape[0] / 2048.0)))      # ~8px feature at 2048
    _R = max(_r + 2, int(round(16 * lum.shape[0] / 2048.0)))  # ~32px feature at 2048
    band_abs = float((_box(lum, _r) - _box(lum, _R)).std())
    band = band_abs / (sd + 1e-6)
    # robust to SPARSE features: p3..p97 reads 0.0 on a field of small marks that
    # occupy under 3% of the canvas, which is a real look, not a broken one.
    lo, hi = np.percentile(lum, [0.5, 99.5])
    contrast = float(hi - lo)
    dead = float(((lum < 0.02) | (lum > 0.98)).mean())

    # coverage: 8x8 tiles that carry local variation relative to the whole image
    h, w = lum.shape
    th, tw = h // 8, w // 8
    tiles = lum[:th * 8, :tw * 8].reshape(8, th, 8, tw).transpose(0, 2, 1, 3)
    tsd = tiles.reshape(64, -1).std(axis=1)
    cover = float((tsd > 0.18 * sd).mean())

    M, R, CC = [np.asarray(c, np.float32) for c in spec]
    shades = 0.0
    for ch in (M, R, CC):
        q = np.unique(np.clip(ch, 0, 255).astype(np.uint8) >> 3)   # 32 buckets
        shades += min(len(q), 32) / 32.0
    shades /= 3.0
    spec_lum = (M + R + CC) / 3.0
    ssd = float(spec_lum.std())
    if ssd > 1e-6:
        a = _box(lum, _r) - _box(lum, _R)
        b = _box(spec_lum, _r) - _box(spec_lum, _R)
        a = (a - a.mean()) / (a.std() + 1e-6)
        b = (b - b.mean()) / (b.std() + 1e-6)
        follow = abs(float((a * b).mean()))
    else:
        follow = 0.0
    return dict(grit=grit, band=band, cover=cover, contrast=contrast,
                amp=amp, band_abs=band_abs,
                dead=dead, shades=shades, follow=follow, spec_sd=ssd,
                coherence=coherence)


def score(m):
    if m is None:
        return float("-inf")
    # An invisible finish is not a finish, however well-shaped it is.
    if m["dead"] > 0.55 or m["contrast"] < 0.06 or m["grit"] > 0.62:
        return float("-inf")
    # amp is a GLOBAL coefficient of variation, so it cannot tell "subtle by
    # design" (print banding, a heat glaze, a colour shift) from "invisible". The
    # floor here is deliberately loose and band_abs — real contrast at car scale —
    # does the actual gating.
    if m["amp"] < 0.065 or m["band_abs"] < 0.010:
        return float("-inf")
    return (5.0 * min(m["amp"], 0.42)
            + 2.2 * m["band"]
            + 1.6 * m["cover"]
            + 1.0 * min(m["contrast"], 0.60)
            + 1.1 * m["shades"]
            + 1.0 * min(m["follow"], 0.75)
            - 2.4 * m["grit"]
            - 1.8 * m["dead"])


# ───────────────────────────────────────────────────────────── driver ──
def sidecar_path(mod):
    return os.path.join(ROOT, "engine", "paint_v2",
                        mod.__name__.rsplit(".", 1)[-1] + "_params.json")


def run(module_name, only=None, report=False, res=RES, n=N_VARIANTS):
    mod = importlib.import_module(module_name)
    space_tbl = getattr(mod, "SPACE", {})
    if not space_tbl:
        print(f"!! {module_name} declares no SPACE table — nothing to search")
        return 1
    ids = [i for i in space_tbl if (only is None or i in only)]
    ids.sort()
    shape = (res, res)
    mask = np.ones(shape, np.float32)
    # A LIVERY colour, not mid-grey. Half this shelf modulates the painter's own
    # paint, and a hue-rotating finish (colour-shift film) is literally invisible on
    # an achromatic source — judging it on grey says "flat" about a working finish.
    src = np.zeros(shape + (3,), np.float32)
    src[:, :, 0], src[:, :, 1], src[:, :, 2] = 0.62, 0.13, 0.16

    chosen, table = {}, {}
    for fid in ids:
        cands = sample_space(space_tbl[fid], n=n)
        rows = []
        t0 = time.time()
        for i, P in enumerate(cands):
            mod.OVERRIDE = (fid, P)
            try:
                paint = getattr(mod, "paint_" + fid)(src, shape, mask, 51, 1.0, None)
                spec = getattr(mod, "spec_" + fid)(shape, 51, 1.0,
                                                   mod.CATALOG[fid].get("M", 0),
                                                   mod.CATALOG[fid].get("R", 100))
                m = measure(paint, spec)
            except Exception as exc:                      # a variant may be invalid
                m, exc_s = None, f"{type(exc).__name__}: {exc}"
                rows.append(dict(i=i, score=float("-inf"), err=exc_s, P=P))
                continue
            rows.append(dict(i=i, score=score(m), P=P, **(m or {})))
        mod.OVERRIDE = None
        rows.sort(key=lambda r: r["score"], reverse=True)
        best = rows[0]
        if best["score"] == float("-inf"):
            print(f"  {fid:26s} ALL {n} VARIANTS FAILED  "
                  f"({rows[0].get('err', 'hard-fail on grit/dead/contrast')})")
            chosen[fid] = 0
        else:
            chosen[fid] = best["i"]
            print(f"  {fid:26s} best #{best['i']:<2d} score {best['score']:+.3f}  "
                  f"grit {best['grit']:.2f} band {best['band']:.2f} cov {best['cover']:.2f} "
                  f"shades {best['shades']:.2f} follow {best['follow']:.2f} "
                  f"[{time.time() - t0:.1f}s / {n}]")
        table[fid] = [{k: v for k, v in r.items() if k != "P"} for r in rows]

    out = sidecar_path(mod)
    prev = {}
    if os.path.exists(out):
        try:
            prev = json.load(open(out, encoding="utf-8")).get("chosen", {})
        except Exception:
            prev = {}
    prev.update(chosen)
    json.dump({"chosen": prev, "n_variants": n, "res": res},
              open(out, "w", encoding="utf-8"), indent=1, sort_keys=True)
    print(f"-> {len(chosen)} winners written to {os.path.relpath(out, ROOT)}")
    if report:
        json.dump(table, open(out.replace(".json", "_report.json"), "w",
                              encoding="utf-8"), indent=1, sort_keys=True, default=str)
        print("-> full score table written alongside")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", required=True)
    ap.add_argument("--ids", default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--res", type=int, default=RES)
    ap.add_argument("--n", type=int, default=N_VARIANTS)
    a = ap.parse_args()
    raise SystemExit(run(a.module, a.ids.split(",") if a.ids else None,
                         a.report, a.res, a.n))
