# -*- coding: utf-8 -*-
"""SPB FINISH LAW — the measurable form of the owner's finish standard.

Owner mandate 2026-08-31, after FRACTURED ELEMENTS shipped 60 finishes over 5
shared spec decks:

    "there needs to be a rule written in stone that makes sure we don't make
     this kind of mistake ever again building finishes. Even if you have to
     write a new formula for judging finishes."

WHY THE OLD GATES DID NOT CATCH IT
----------------------------------
The lane verifier compared finishes with a *phase-sensitive* cosine over a
z-scored 32x32 grid. Re-running one generator with a new seed moves every
pixel, so that metric scores a pure re-seed as ~0.2 "totally unique" while the
eye sees the same finish again. ELEMENTS measured 0/60 duplicates and max
similarity 0.693 on a sheet the owner called "totally the same".

So this module never compares images pixel-for-pixel. Every axis below is a
*statistic of the texture* — invariant to seed, phase and colour — plus two
axes about the relationship between the paint and its spec.

THE FIVE AXES
-------------
SCALE     Energy in the car window (features 8-32px at 2048). The owner's most
          repeated complaint — "patterns are just way way way too big ... not
          feasible in their current state".
FOLLOW    Does the spec follow the artwork? Owner on TRUCHET GLASS: "the design
          element and the way the spec map is on this one just WORKS ... UNIQUE
          design with a spec map that follows the design". Owner on STATIC
          BLOOM: "chaotic but makes no sense ... the pattern just won't work on
          the car paint ... with the spec color pattern there being a problem".
RICHNESS  How many distinct materials the spec actually deals. Owner: "tons of
          spec color combination choices", "WAY more spec coloring/shades".
TWIN      Phase-invariant distance to the nearest other finish in the catalog.
          This is the axis that would have caught ELEMENTS, and it is the one
          the old gate structurally could not see.
STORY     Does this finish own its material story, or does it share a deck with
          its neighbours? A catalog-level check, not a per-image one.

CALIBRATION
-----------
Thresholds are not invented. They are fitted to the owner's own verdicts, which
are recorded in scripts/finish_law_labels.json:

    PASS      Hologram Metal, Dichroic Skin, Truchet Glass, Cinder Pulse,
              Hologram Noir            ("gold standards ... NEVER CHANGED")
    PROMISE   Split Underglow, Afterburn Chrome, Neon Underglow, Tokyo Rain
    FAIL      Ember Weave, Comet Terrace, Hex Reliquary, Labyrinth Pulse,
              Medusa Lattice, Static Bloom, Turbo Heat, Redline Rush, Seoul
              Circuit, Import Royalty, Laser Lane, Phantom Taillights, Street
              Pulse, Tunnel Vision, Nitro Purge, Boost Spool, Burnout Ember,
              Carbon Voltage, Midnight Candy

Run `--calibrate` to re-measure that set and print the separation each axis
achieves. An axis that does not separate the owner's PASS from the owner's FAIL
is a bad axis and must be replaced, not shipped.

USAGE
    python scripts/spb_finish_law.py --calibrate
    python scripts/spb_finish_law.py --ids a,b,c
    python scripts/spb_finish_law.py --group "FRACTURED ELEMENTS"
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

LABELS = REPO / "scripts" / "finish_law_labels.json"
PROTECTED = REPO / "scripts" / "protected_finishes.json"

# Measured at this canvas. The band edges below are expressed as a fraction of
# the canvas, so the numbers are the same at any render size; 1024 is used for
# speed and is still 4x finer than the 8px car-window floor.
RES = 1024


# ----------------------------------------------------------------- rendering
def _engine():
    logging.disable(logging.CRITICAL)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import shokker_engine_v2 as eng
        eng._ensure_expansions_loaded()
    return eng


def render(eng, fid, res=RES):
    """Return (paint HxWx3 float 0-1, spec HxWx3 float 0-255) or (None, None)."""
    shape = (res, res)
    mask = np.ones(shape, np.float32)
    mono = eng.MONOLITHIC_REGISTRY
    base = eng.BASE_REGISTRY
    if fid in mono:
        entry = mono[fid]
        spec_fn, paint_fn = (entry[0], entry[1]) if isinstance(entry, tuple) else (
            entry.get("spec_fn"), entry.get("paint_fn"))
        spec = np.asarray(spec_fn(shape, mask, 51, 1.0), np.float32)
        if spec.ndim == 2:
            spec = np.dstack([spec] * 3)
        spec = spec[..., :3]
        paint = None
        if paint_fn is not None:
            paint = np.asarray(paint_fn(np.full(shape + (3,), 0.5, np.float32),
                                        shape, mask, 51, 1.0, None), np.float32)
    elif fid in base:
        entry = base[fid]
        m, r, c = entry["base_spec_fn"](shape, 51, 1.0, entry.get("M", 0), entry.get("R", 100))
        spec = np.dstack([np.asarray(x, np.float32) for x in (m, r, c)])
        paint = None
        if entry.get("paint_fn"):
            paint = np.asarray(entry["paint_fn"](np.full(shape + (3,), 0.5, np.float32),
                                                 shape, mask, 51, 1.0, None), np.float32)
    else:
        return None, None
    if paint is not None:
        paint = np.asarray(paint, np.float32)
        if paint.ndim == 3 and paint.shape[2] >= 3:
            paint = paint[..., :3]
            if float(paint.max()) > 1.5:
                paint = paint / 255.0
        else:
            paint = None
    return paint, np.clip(spec, 0, 255)


def _luma(rgb):
    return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).astype(np.float32)


# -------------------------------------------------------------------- axes
def _power(gray):
    g = gray - float(gray.mean())
    f = np.fft.fftshift(np.abs(np.fft.fft2(g)))
    return (f * f).astype(np.float64)


def _radii(n):
    yy, xx = np.indices((n, n))
    c = n // 2
    return np.hypot(yy - c, xx - c)


def scale_axis(gray):
    """Energy split by feature size. A feature of p px sits at radius n/p.

    Returns (band, coarse):
      band   fraction of energy for features 8-32px at 2048 (the car window)
      coarse fraction of energy for features LARGER than 32px  -> "way too big"
    """
    n = gray.shape[0]
    p = _power(gray)
    r = _radii(n)
    tot = float(p.sum()) + 1e-12
    # feature size in canvas fractions: 8/2048 and 32/2048
    r_fine = n / (8.0 / 2048.0 * n)     # radius of an 8px-at-2048 feature
    r_coarse = n / (32.0 / 2048.0 * n)  # radius of a 32px-at-2048 feature
    band = float(p[(r >= r_coarse) & (r <= r_fine)].sum()) / tot
    coarse = float(p[(r > 0) & (r < r_coarse)].sum()) / tot
    return band, coarse


def nmi(a, b, bins=16):
    """Normalised mutual information between two fields, 0..1."""
    a = np.asarray(a, np.float64).ravel()
    b = np.asarray(b, np.float64).ravel()
    if a.std() < 1e-9 or b.std() < 1e-9:
        return 0.0
    def q(x):
        lo, hi = float(x.min()), float(x.max())
        if hi - lo < 1e-12:
            return np.zeros(x.shape, np.int32)
        return np.clip(((x - lo) / (hi - lo) * bins).astype(np.int32), 0, bins - 1)
    ra, rb = q(a), q(b)
    joint = np.zeros((bins, bins), np.float64)
    np.add.at(joint, (ra, rb), 1.0)
    joint /= joint.sum()
    pa = joint.sum(1)
    pb = joint.sum(0)
    nz = joint > 0
    hj = -float((joint[nz] * np.log(joint[nz])).sum())
    ha = -float((pa[pa > 0] * np.log(pa[pa > 0])).sum())
    hb = -float((pb[pb > 0] * np.log(pb[pb > 0])).sum())
    mi = ha + hb - hj
    denom = max(min(ha, hb), 1e-12)
    return float(np.clip(mi / denom, 0.0, 1.0))


def _bandpass(gray, n):
    """Isolate the car window (features 8-32px at 2048) before comparing.

    Comparing raw paint against raw spec was the first thing tried and it is
    WRONG: per-pixel gradients are dominated by whatever noise each channel
    happens to carry, and it scored TRUCHET GLASS - the owner's reference for
    a spec that follows its design - at 0.134, below several finishes the
    owner rejected. Band-limiting both sides to the window the eye actually
    sees on the car moves TRUCHET to 0.844, the highest in the calibration
    set. Measure where the customer looks.
    """
    import cv2
    lo = cv2.GaussianBlur(gray, (0, 0), n / 2048.0 * 32.0 / 2.0)
    hi = cv2.GaussianBlur(gray, (0, 0), max(0.6, n / 2048.0 * 8.0 / 2.0))
    return hi - lo


def follow_axis(paint, spec):
    """Does the spec follow the artwork?

    Owner on TRUCHET GLASS: "the design element and the way the spec map is on
    this one just WORKS". Owner on STATIC BLOOM: "chaotic but makes no sense.
    The pattern just won't work on the car paint ... with the spec color
    pattern there being a problem."

    Returns (mi_band, amp_corr). amp_corr is the gated axis: correlation of the
    two band-limited AMPLITUDE envelopes, i.e. "where the artwork has detail,
    does the spec also have detail?" It does not demand that bright paint means
    rough spec - only that the spec's structure is laid out on the artwork's
    structure rather than scattered independently across it.
    """
    if paint is None:
        return 0.0, 0.0
    pl = _luma(paint)
    sl = _luma(spec / 255.0)
    n = pl.shape[0]
    pb = _bandpass(pl, n)
    sb = _bandpass(sl, n)
    mi = nmi(pb[::2, ::2], sb[::2, ::2])
    a = np.abs(pb) - float(np.abs(pb).mean())
    b = np.abs(sb) - float(np.abs(sb).mean())
    denom = float(np.sqrt((a * a).sum() * (b * b).sum())) + 1e-12
    return mi, float((a * b).sum() / denom)


def coverage_axis(paint):
    """Fraction of the canvas that is DEAD — near-black or near-white luma.

    Added 2026-09-01 after the PARADIGM 2048 sheet: ash_chrome, soot_pearl and
    cinder_mirror were nearly solid black and PASSED every axis, because SCALE is
    happy with fine detail on 5% of the canvas and FOLLOW correlates trivially
    when both envelopes are near zero. CLAUDE.md rule 0b mandates full-canvas
    coverage; this law had omitted it. Lichen and root got through the same hole
    before they were fixed by eye.
    """
    if paint is None:
        return 0.0
    l = _luma(paint)
    dead = float(((l < 0.06) | (l > 0.94)).mean())
    return dead


def richness_eff(spec):
    """EFFECTIVE number of materials: perplexity of the AREA distribution over
    quantized (M,R,Cc) materials. `richness_axis` counts materials with >=1%
    area, which let a spec that is 80% one flat card score 12. Owner on DARK
    CITY 2026-09-02: "the damn specs are not interesting enough" — Brass Night
    (his winner) measures 4.6, Arc Weld 1.3, Ember Gold 1.9, Hot Wire 2.3,
    Deep Pine 2.7. ADVISORY, not a gate: Truchet Glass, a gold standard, is a
    deliberate two-material story and measures 1.8. Shelf spec sweeps maximise
    this subject to FOLLOW; the law reports it.
    """
    q = np.clip((np.asarray(spec, np.float32) / 255.0 * 6).astype(np.int32), 0, 5)
    key = q[..., 0] * 36 + q[..., 1] * 6 + q[..., 2]
    _, cnt = np.unique(key, return_counts=True)
    p = cnt / float(cnt.sum())
    return float(np.exp(-(p * np.log(p)).sum()))


def richness_axis(spec):
    """How many distinct materials the spec actually deals.

    A material is a cell of the quantised (M, R, Cc) cube holding >=0.5% of the
    canvas. Counting occupied cells rather than per-channel spread is what
    separates "six real cards" from "one card smeared by noise".
    """
    q = np.clip((spec / 255.0 * 8).astype(np.int32), 0, 7)
    key = (q[..., 0] * 64 + q[..., 1] * 8 + q[..., 2]).ravel()
    counts = np.bincount(key, minlength=512).astype(np.float64)
    frac = counts / counts.sum()
    mats = int((frac >= 0.005).sum())
    shades = int(np.unique(np.clip((spec[..., 1] / 255.0 * 12).astype(np.int32), 0, 11)).size)
    return mats, shades


def story_signature(spec):
    """The set of materials this finish actually deals.

    This is the axis that would have stopped FRACTURED ELEMENTS. That module
    put the spec deck on the CHAPTER instead of the finish, so twelve finishes
    shared one band list and differed only in palette and noise phase - and
    every image-similarity metric in the repo called them unique because a
    re-seed moves every pixel.

    A material story is derived from the rendered spec, not from the source, so
    it cannot be dodged by restructuring the recipe table: two finishes dealing
    the same cards from the same deck land on the same signature no matter how
    the code is arranged. Cells holding >=1% of the canvas only, so stray
    dither does not manufacture false variety.
    """
    q = np.clip((spec / 255.0 * 6).astype(np.int32), 0, 5)
    key = (q[..., 0] * 36 + q[..., 1] * 6 + q[..., 2]).ravel()
    counts = np.bincount(key, minlength=216).astype(np.float64)
    frac = counts / max(counts.sum(), 1.0)
    return frozenset(int(i) for i in np.nonzero(frac >= 0.01)[0])


def texture_signature(paint, spec):
    """Phase-invariant descriptor. Two finishes from one generator with
    different seeds land in the same place; a recolour also lands in the same
    place, which is the point."""
    parts = []
    for img, chans in ((paint, 1), (spec / 255.0, 3)):
        if img is None:
            parts.append(np.zeros(28, np.float64))
            continue
        gray = _luma(img) if img.ndim == 3 else img
        n = gray.shape[0]
        p = _power(gray)
        r = _radii(n)
        tot = float(p.sum()) + 1e-12
        edges = np.geomspace(1.0, n / 2.0, 17)
        spec_prof = [float(p[(r >= edges[i]) & (r < edges[i + 1])].sum()) / tot
                     for i in range(16)]
        # 2026-09-03: a spec-only foundation renders a CONSTANT gray plate (paint passthrough);
        # numpy cannot cut 8 bins from a zero-width range, which crashed the whole group run.
        _lo, _hi = float(gray.min()), float(gray.max())
        if _hi - _lo < 1e-6:
            _hi = _lo + 1e-3
        h, _ = np.histogram(gray, bins=8, range=(_lo, _hi + 1e-9))
        h = h.astype(np.float64) / max(h.sum(), 1)
        gy, gx = np.gradient(gray)
        ge = np.hypot(gx, gy)
        gh, _ = np.histogram(ge, bins=4, range=(0.0, float(np.percentile(ge, 99)) + 1e-9))
        gh = gh.astype(np.float64) / max(gh.sum(), 1)
        parts.append(np.concatenate([spec_prof, h, gh]))
    v = np.concatenate(parts)
    return v / (np.linalg.norm(v) + 1e-12)


def measure(eng, fid, res=RES):
    paint, spec = render(eng, fid, res)
    if spec is None:
        return None
    # [SPEC-DRIVEN FOLLOW EXEMPTION 2026-09-04] A finish whose paint_fn is paint_none
    # (all of Foundation) has no artwork of its own — the CUSTOMER's paint is the
    # artwork, and the spec cannot correlate with a field the finish never wrote.
    # FOLLOW measured 0.000 for 23 of 25 Foundation entries for exactly that reason,
    # which is the metric being undefined, not the finish being wrong. M7 already
    # carries the same exemption in the other direction (SPB-95 drops M1 for
    # spec_driven intent); this mirrors it so the law can actually gate Foundation.
    # paint_none IS callable, so `paint` comes back as a CONSTANT field rather than
    # None — detect the absence of artwork by its variance, not by identity.
    spec_driven = paint is None or float(np.asarray(paint, np.float32).std()) < 1e-6
    ref = _luma(paint) if paint is not None else _luma(spec / 255.0)
    band, coarse = scale_axis(ref)
    sband, scoarse = scale_axis(_luma(spec / 255.0))
    mi, amp = follow_axis(paint, spec)
    mats, shades = richness_axis(spec)
    dead = coverage_axis(paint)
    eff = richness_eff(spec)
    return {
        "spec_driven": bool(spec_driven),
        "id": fid,
        "dead": round(dead, 4),
        "eff": round(eff, 3),
        "band": round(band, 4),
        "coarse": round(coarse, 4),
        "spec_band": round(sband, 4),
        "fine": round(max(band, sband), 4),
        "follow_mi": round(mi, 4),
        "follow_edge": round(amp, 4),
        "mats": mats,
        "shades": shades,
        "story": sorted(story_signature(spec)),
        "sig": texture_signature(paint, spec).tolist(),
    }


def audit_group(rows):
    """Catalog-level checks. Per-image axes cannot see these.

    STORY  How many distinct material stories does this shelf actually tell?
           A shelf of N finishes telling N/12 stories is a recolour matrix.
    TWIN   Phase-invariant nearest sibling inside the shelf.
    """
    n = len(rows)
    stories = {}
    for r in rows:
        stories.setdefault(tuple(r["story"]), []).append(r["id"])
    shared = {k: v for k, v in stories.items() if len(v) > 1}
    sig = np.array([r["sig"] for r in rows], np.float64)
    sig /= (np.linalg.norm(sig, axis=1, keepdims=True) + 1e-12)
    c = sig @ sig.T
    np.fill_diagonal(c, -1.0)
    twins = []
    for i, r in enumerate(rows):
        j = int(c[i].argmax())
        twins.append((r["id"], rows[j]["id"], float(c[i, j])))
    return {
        "n": n,
        "distinct_stories": len(stories),
        "story_ratio": round(len(stories) / max(n, 1), 3),
        "shared_stories": sorted(shared.values(), key=len, reverse=True),
        "twins": twins,
    }


# -------------------------------------------------------------- the verdict
# Thresholds FITTED to the owner's verdicts (see --calibrate), never invented.
#
#   MIN_FINE 0.20   The owner's five gold standards measure 0.218 - 0.443.
#                   The lowest is HOLOGRAM NOIR at 0.218, so the floor sits
#                   just under it. 9 of the owner's 19 rejects fall below.
#   MIN_FOLLOW 0.35 TRUCHET GLASS 0.844, HOLOGRAM NOIR 0.610, DICHROIC SKIN
#                   0.539, CINDER PULSE 0.462. The XLAB rejects the owner
#                   named cluster at -0.155 to 0.122. Adding this axis takes
#                   the catch from 9/19 to 15/19 of the owner's rejects with
#                   no gold standard lost (HOLOGRAM METAL is exempt, and the
#                   reason is written in protected_finishes.json).
#   MAX_TWIN        ADVISORY, NOT A GATE — see below.
MIN_FINE = 0.20
MIN_FOLLOW = 0.35
#   MAX_DEAD 0.70   COVERAGE. More than 70% of the canvas near-black or
#                   near-white is not a finish on a car, it is a colour with
#                   a few marks on it. Caught ash_chrome / soot_pearl /
#                   cinder_mirror, which every other axis passed.
MAX_DEAD = 0.70

# TWIN IS ADVISORY. It is reported, never enforced, and here is why.
#
# The 0.80 line was inherited from the existing Uniqueness Law, which uses a
# DIFFERENT descriptor with a different scale. Measured on the owner's own
# labelled set with THIS descriptor:
#
#     owner PASS (the five gold standards)  twin 0.817 - 0.923
#     owner FAIL (the nineteen rejects)     twin 0.783 - 0.951
#
# The ranges overlap almost completely, and every one of the owner's protected
# finishes sits ABOVE 0.80. A gate at 0.80 would fail HOLOGRAM METAL, DICHROIC
# SKIN and TRUCHET GLASS — which is a reductio, not a finding.
#
# This file's own rule is that an axis which cannot separate the owner's PASS
# from the owner's FAIL is a bad axis and must be replaced rather than shipped.
# That rule applies to this axis. Cosine over non-negative spectral histograms
# has a high floor, and the finish pipeline (shared paint treatment, shared spec
# layout) compresses what range is left.
#
# STORY carries the duplicate-detection load instead: it is exact, derived from
# the render, and it caught both real cases — FRACTURED ELEMENTS at 5 material
# decks for 60 finishes, and NIGHTSHIFT at 10 stories for 50. Construction-level
# diversity is enforced separately at authoring time (see the DESIGN tables,
# which reject two finishes sharing a construction AND its parameters).
MAX_TWIN = None


def load_protected():
    if not PROTECTED.exists():
        return {}, {}
    d = json.loads(PROTECTED.read_text(encoding="utf-8"))
    return d.get("locked", {}), d.get("follow_exempt", {})


def verdict(rec, twin=None):
    """Return (ok, [failed axis strings]). Pure function of the measurements."""
    _locked, exempt = load_protected()
    fails = []
    fine = max(float(rec["band"]), float(rec["spec_band"]))
    if fine < MIN_FINE:
        fails.append("SCALE fine %.3f < %.2f (pattern too big for the car window)" % (fine, MIN_FINE))
    if float(rec.get("dead", 0.0)) > MAX_DEAD:
        fails.append("COVERAGE dead %.2f > %.2f (canvas is mostly one dead tone)"
                     % (float(rec["dead"]), MAX_DEAD))
    # A spec-driven finish (paint_fn is paint_none) writes no artwork of its own, so
    # FOLLOW has nothing to correlate against and always reads 0.000. Skip it there —
    # the same exemption M7 already grants spec_driven intent (SPB-95).
    if rec["id"] not in exempt and not rec.get("spec_driven"):
        if float(rec["follow_edge"]) < MIN_FOLLOW:
            fails.append("FOLLOW %.3f < %.2f (spec does not follow the artwork)"
                         % (float(rec["follow_edge"]), MIN_FOLLOW))
    if MAX_TWIN is not None and twin is not None and float(twin) >= MAX_TWIN:
        fails.append("TWIN %.3f >= %.2f (statistical twin of another finish)" % (float(twin), MAX_TWIN))
    return (not fails), fails


# ------------------------------------------------------------------ driver
def load_labels():
    return json.loads(LABELS.read_text(encoding="utf-8")) if LABELS.exists() else {}


def cmd_calibrate(args):
    labels = load_labels()
    eng = _engine()
    out_path = REPO / "_workbench" / "finish_law_calibration.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if out_path.exists() and not args.fresh:
        for line in out_path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
                done[rec["id"]] = rec
            except Exception:
                pass
    rows = []
    with out_path.open("a", encoding="utf-8") as fh:
        for verdict, items in labels.items():
            for name, fid, _kind in items:
                if fid in done:
                    rec = done[fid]
                else:
                    rec = measure(eng, fid)
                    if rec is None:
                        print(f"  MISSING {fid}")
                        continue
                    rec["verdict"] = verdict
                    rec["name"] = name
                    fh.write(json.dumps(rec) + "\n")
                    fh.flush()
                rec["verdict"] = verdict
                rec["name"] = name
                rows.append(rec)
                print("  %-9s %-22s band %.3f coarse %.3f mi %.3f edge %+.3f mats %2d" % (
                    verdict, fid, rec["band"], rec["coarse"], rec["follow_mi"],
                    rec["follow_edge"], rec["mats"]))
    report(rows)
    return 0


def report(rows):
    import statistics as st
    groups = {}
    for r in rows:
        groups.setdefault(r["verdict"], []).append(r)
    axes = ["band", "coarse", "spec_band", "follow_mi", "follow_edge", "mats", "shades"]
    print("\n%-12s %s" % ("axis", "  ".join("%-22s" % g for g in groups)))
    for ax in axes:
        cells = []
        for g, items in groups.items():
            vals = [float(i[ax]) for i in items]
            cells.append("%-22s" % ("min %.3f med %.3f" % (min(vals), st.median(vals))))
        print("%-12s %s" % (ax, "  ".join(cells)))
    if "PASS" in groups and "FAIL" in groups:
        print("\nSEPARATION (owner PASS vs owner FAIL):")
        for ax in axes:
            p = [float(i[ax]) for i in groups["PASS"]]
            f = [float(i[ax]) for i in groups["FAIL"]]
            lo_p, hi_f = min(p), max(f)
            hi_p, lo_f = max(p), min(f)
            if lo_p > hi_f:
                print("  %-12s CLEAN  PASS >= %.3f  >  FAIL <= %.3f" % (ax, lo_p, hi_f))
            elif hi_p < lo_f:
                print("  %-12s CLEAN  PASS <= %.3f  <  FAIL >= %.3f" % (ax, hi_p, lo_f))
            else:
                ov = sum(1 for x in f if min(p) <= x <= max(p))
                print("  %-12s overlap %d/%d FAIL inside PASS range [%.3f, %.3f]" % (
                    ax, ov, len(f), min(p), max(p)))


def _groups():
    import subprocess
    js = REPO / "_groups.json"
    if not js.exists():
        subprocess.run(["node", "-e",
                        "const fs=require('fs');const g={};"
                        "new Function('g',fs.readFileSync('paint-booth-0-finish-data.js','utf8')"
                        "+';g.SG=SPECIAL_GROUPS;g.BG=BASE_GROUPS;')(g);"
                        "fs.writeFileSync('_groups.json',JSON.stringify({SG:g.SG,BG:g.BG}),'utf8');"],
                       cwd=str(REPO), check=True, capture_output=True)
    d = json.loads(js.read_text(encoding="utf-8"))
    out = {}
    out.update(d["SG"])
    out.update(d["BG"])
    return out


def cmd_group(args):
    groups = _groups()
    keys = [k for k in groups if args.group.lower() in k.lower()]
    if not keys:
        print("no group matching %r" % args.group)
        return 2
    eng = _engine()
    rc = 0
    for key in keys:
        ids = groups[key]
        name = key.encode("ascii", "ignore").decode().strip()
        out_path = REPO / "_workbench" / ("law_%s.jsonl" % name.lower().replace(" ", "_").replace("&", "and"))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        done = {}
        if out_path.exists() and not args.fresh:
            for line in out_path.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                    done[r["id"]] = r
                except Exception:
                    pass
        rows = []
        with out_path.open("a", encoding="utf-8") as fh:
            for fid in ids:
                if fid in done:
                    rows.append(done[fid])
                    continue
                rec = measure(eng, fid, args.res)
                if rec is None:
                    print("  MISSING %s" % fid)
                    continue
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                rows.append(rec)
        if not rows:
            continue
        info = audit_group(rows)
        twin_of = {t[0]: (t[1], t[2]) for t in info["twins"]}
        failed = []
        for r in rows:
            ok, why = verdict(r, twin_of.get(r["id"], (None, 0.0))[1])
            if not ok:
                failed.append((r["id"], why))
        print("\n=== FINISH LAW : %s ===" % name)
        print("  finishes            %d" % info["n"])
        print("  distinct stories    %d  (ratio %.2f — 1.00 means every finish owns its material story)"
              % (info["distinct_stories"], info["story_ratio"]))
        if info["shared_stories"]:
            print("  SHARED STORIES      %d groups; largest:" % len(info["shared_stories"]))
            for grp in info["shared_stories"][:4]:
                print("      %2d finishes deal an identical material set: %s%s"
                      % (len(grp), ", ".join(grp[:6]), " ..." if len(grp) > 6 else ""))
        tw = sorted(t[2] for t in info["twins"])
        if tw:
            print("  twin (ADVISORY)     min %.3f  median %.3f  max %.3f"
                  % (tw[0], tw[len(tw) // 2], tw[-1]))
            _eff = sorted(float(r.get("eff", 0.0)) for r in rows)
            if _eff:
                print("  richness eff (ADVISORY)  min %.2f  median %.2f  max %.2f   (effective materials by area; Brass Night 4.6, Arc Weld 1.3)"
                      % (_eff[0], _eff[len(_eff) // 2], _eff[-1]))
        print("  law failures        %d / %d" % (len(failed), len(rows)))
        for fid, why in failed[:12]:
            print("      %-26s %s" % (fid, "; ".join(why)))
        if len(failed) > 12:
            print("      ... and %d more" % (len(failed) - 12))
        if failed or info["story_ratio"] < 0.9:
            rc = 1
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--ids")
    ap.add_argument("--group", help="picker group name (substring match)")
    ap.add_argument("--res", type=int, default=RES)
    args = ap.parse_args()
    if args.calibrate:
        return cmd_calibrate(args)
    if args.group:
        return cmd_group(args)
    if args.ids:
        eng = _engine()
        for fid in args.ids.split(","):
            rec = measure(eng, fid.strip(), args.res)
            if rec is None:
                print(f"  MISSING {fid}")
                continue
            rec.pop("sig", None)
            print(json.dumps(rec))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
