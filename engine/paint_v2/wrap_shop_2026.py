"""WRAP SHOP — the material language of printed vinyl wrap  (owner mandate 2026-09-04)

STATUS: SHIPPING — 22 finishes, installed via `install()`.

WHY THIS SHELF EXISTS.  The product is a paint booth, but the thing an iRacing
livery actually IS in the real world is a printed vinyl wrap: a laminated film
squeegeed onto panels, knifed at the edges, overlapped at the seams, stretched
thin over the curves and bubbled where the air did not chase out.  The catalog
had none of it.  Verified before building rather than assumed:

    CORRECTION (2026-09-04, before install): an earlier draft of this note claimed
    "wrap-named finishes .... 0". That was wrong, and checking it is what found the
    real gap. The catalog actually holds NINE vinyl-named bases:

      gloss_wrap  R=15   matte_wrap R=195  satin_wrap R=130  stealth_wrap R=200
      textured_wrap R=95 liquid_wrap R=80  enh_vinyl_wrap / f_vinyl_wrap R=95
      color_flip_wrap M=155

    But read the numbers: eight of the nine differ from one another only in SHEEN.
    They are roughness presets wearing wrap names — "matte wrap" is matte, "gloss
    wrap" is gloss. Not one of them models wrap as an APPLIED SHEET. There is still
    no seam, no squeegee mark, no trapped air, no knifed edge, no perforation, and
    "squeegee" returns 0 hits across the whole catalog.

Every other material family here is about a COATING (sprayed, cured, weathered).
Wrap is an APPLIED SHEET, and sheet behaviour is a different geometry entirely:
seams and overlaps are discontinuities, not noise; bubbles are trapped volume;
squeegee marks are a directional burnish; stretch thins the print over a crown.
None of that is producible by the coating generators already in the catalog.

DESIGN RULE FOR THIS SHELF.  These finishes MODULATE the incoming paint rather
than replace it — the painter's own livery colour is the printed film, and the
shelf supplies the material behaviour on top.  That is what makes the shelf
useful rather than decorative: a painter can wrap the scheme they already have.

TWENTY-TWO MECHANISMS, NO TWO ALIKE.  Owner 2026-09-04: "ALL finishes MUST be
unique. Don't reuse the same math for finishes OR specs."  So the shelf is
deliberately spread across structural families rather than being twenty-two
flavours of noise:

    DIRECTIONAL  squeegee (X streak), brushed film (Y streak), roll memory (chirp)
    PERIODIC     perf window (punched lattice), air release (rhombic channels),
                 laminate (four-angle CMYK rosette), print banding (head passes)
    PARTITION    panel seam (parallel sheets), knife edge (full-circle facets),
                 layered cut (stacked height steps)
    CELLULAR     forged film (Worley platelets), ceramic coat (sparse domains)
    RADIAL       stretch (tension around pull points), wet apply (drying rings)
    MORPHOLOGY   micro-bubble (clustered dilation), rivet conform (tenting)
    FIELD OPS    heat gun (variable-radius blur), conform recess (bridging),
                 creases (folded-noise ridges), lift curl (boundary bands)
    OPTICAL      colour flip (normal-driven hue rotation), holographic (grating)

SPEC GRAMMARS.  Owner: "Specs DIVERSE ... different shades of colors and putting
them in unique ways/patterns really can help paint jobs come to life", and "NO
CONFETTI ... I'd rather have CLEAN looking specs".  Every spec here reads the
SAME geometry as its paint (the FINISH LAW's FOLLOW axis demands it) but maps it
through its own grammar — quantised ladders, dual populations, domain-constant
palettes, hard duotones, smooth ramps.  None of them sprinkle grain to pass a
gate; the variant search actively penalises that (see GRIT in the harness).

ITERATION.  Each finish declares a SPACE of knobs; scripts/spb_variant_search.py
renders and scores ten samples of it and writes the winner to
wrap_shop_2026_params.json.  That file, plus its _report.json sibling, is the
record of which of the ten won and by how much.
"""

from __future__ import annotations

import numpy as np

from engine.core import get_mgrid, _resize_array
from engine.paint_v2._variant_params import chooser

_WRAP_CACHE: dict = {}
OVERRIDE = None          # (finish_id, params) — set by the variant search harness


def _cache(key, build):
    hit = _WRAP_CACHE.get(key)
    if hit is None:
        if len(_WRAP_CACHE) > 200:
            _WRAP_CACHE.clear()
        hit = build()
        _WRAP_CACHE[key] = hit
    return hit


def _P(fid):
    if OVERRIDE is not None and OVERRIDE[0] == fid:
        return OVERRIDE[1]
    return _CHOSEN[fid]


def _k(P):
    return tuple(sorted((k, round(float(v), 5)) for k, v in P.items()))


def _norm(a):
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return np.zeros_like(a) if hi - lo < 1e-7 else ((a - lo) / (hi - lo)).astype(np.float32)


def _box(a, r):
    """Box blur via summed-area table — the module's only shared filter."""
    a = np.asarray(a, np.float32)
    r = max(1, int(r))
    pad = np.pad(a, ((r, r), (r, r)), mode="reflect")
    c = np.cumsum(np.cumsum(pad, 0, dtype=np.float32), 1, dtype=np.float32)
    c = np.pad(c, ((1, 0), (1, 0)), mode="constant")
    h, w = a.shape
    kk = 2 * r + 1
    s = c[kk:kk + h, kk:kk + w] - c[0:h, kk:kk + w] - c[kk:kk + h, 0:w] + c[0:h, 0:w]
    return (s / float(kk * kk)).astype(np.float32)


def _mid(shape, feature_px, seed, octaves=3, falloff=0.55):
    """Value noise with features at an exact pixel size.

    multi_scale_noise cannot serve the 8-32px window on this build — measured,
    its scale=8 already lands at ~72px features and only grows — so the band is
    built directly from a lattice and bilinearly upsampled.
    """
    h, w = shape[:2]
    key = ("m", h, w, float(feature_px), int(seed), int(octaves))

    def build():
        out = np.zeros((h, w), np.float32)
        amp, total = 1.0, 0.0
        for o in range(int(octaves)):
            fp = max(2.0, float(feature_px) / (2 ** o))
            gh, gw = max(2, int(round(h / fp))), max(2, int(round(w / fp)))
            rng = np.random.default_rng((int(seed) * 7717 + o * 33413) & 0xFFFFFFFF)
            out += amp * _resize_array(rng.random((gh, gw), dtype=np.float32), h, w)
            total += amp
            amp *= float(falloff)
        return (out / max(total, 1e-6)).astype(np.float32)

    return _cache(key, build)


def _streak(a, length, axis=1):
    """Long directional blur — the operator that makes a BRUSH read as a brush."""
    a = np.asarray(a, np.float32)
    n = max(2, int(length))
    pad = [(0, 0), (0, 0)]
    pad[axis] = (n, n)
    q = np.pad(a, pad, mode="wrap")
    c = np.cumsum(q, axis=axis, dtype=np.float32)
    if axis == 1:
        out = (c[:, 2 * n:] - c[:, :-2 * n]) / float(2 * n)
    else:
        out = (c[2 * n:, :] - c[:-2 * n, :]) / float(2 * n)
    return out[: a.shape[0], : a.shape[1]].astype(np.float32)


def _ladder(a, steps, lo, hi):
    """Quantise a 0..1 field into `steps` discrete material levels spanning lo..hi.

    The shelf's clean-shades operator: a ladder gives many DISTINCT spec values
    (the owner's "more shades") without a single grain of noise, which is the
    opposite of passing a richness gate by sprinkling hash.
    """
    s = max(2, int(steps))
    q = np.floor(np.clip(a, 0, 0.9999) * s) / (s - 1.0)
    return (float(lo) + (float(hi) - float(lo)) * q).astype(np.float32)


def _finish(out, paint, mask):
    out = np.clip(out, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return out * m + np.asarray(paint, np.float32)[:, :, :3] * (1 - m)


def _incoming(paint, shape):
    """The painter's own livery colour — this shelf modulates it, never replaces it."""
    p = np.asarray(paint, np.float32)
    if p.ndim == 3 and p.shape[2] > 3:
        p = p[:, :, :3]
    if p.ndim == 2:
        p = np.dstack([p] * 3)
    h, w = shape[:2]
    if p.shape[0] != h or p.shape[1] != w:
        p = np.dstack([_resize_array(p[:, :, c], h, w) for c in range(3)])
    return np.clip(p, 0, 1).astype(np.float32)


def _warp(shape, seed, amp, px_scale):
    """Warped pixel coordinates — ONE low-frequency displacement applied to the whole
    plane, so any number of straight cuts drawn through it come out hand-laid.

    This replaced a per-cut `_mid` call: at 2048 a fresh lattice+resize per cut is
    what put knife edge at 7.1s and panel seam at 4.0s against a 3s budget.
    """
    h, w = shape[:2]

    def build():
        py, px = _px(shape)
        wy = (_mid(shape, px_scale, seed + 5, octaves=2) - 0.5) * float(amp)
        wx = (_mid(shape, px_scale, seed + 6, octaves=2) - 0.5) * float(amp)
        return (py + wy).astype(np.float32), (px + wx).astype(np.float32)

    return _cache(("wrp", h, w, int(seed), float(amp), float(px_scale)), build)


def _px(shape):
    """Pixel coordinates (py, px), each spanning 0..h-1 / 0..w-1.

    NOTE — get_mgrid ALREADY returns pixel indices, not normalised 0..1. The
    2026-09-04 first build of this module (and its `yy = y * h` idiom, copied from
    older shelves) multiplied by the size a second time, so every coordinate-driven
    feature landed at 1/512 of its intended size: the halftone rosette sat below the
    sampling floor, the panel seams were sub-pixel hairlines, and the recess, rivet
    and drying-ring fields were empty to three decimal places. Measured, not assumed:
    get_mgrid((512,512)) returns two 512x512 arrays spanning 0..511.
    """
    y, x = get_mgrid(shape[:2])
    return np.asarray(y, np.float32), np.asarray(x, np.float32)


# ══════════════════════════════════════════════════════ 01 · PANEL SEAM ══
def _panels(shape, seed, P):
    """Parallel half-plane cuts: long sheets laid roughly side by side."""
    h, w = shape[:2]

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x2E51) & 0xFFFFFFFF)
        py, px = _warp(shape, seed + 40, 30.0, 300.0)
        pid = np.zeros((h, w), np.float32)
        edge = np.zeros((h, w), np.float32)
        tone = np.zeros((h, w), np.float32)
        n_cuts = max(4, int(round(w / float(P["panel_px"]))))
        inv = 1.0 / max(1.0, float(P["seam_px"]))
        # A car wrapped in three sheets is three lines on an empty panel — which is
        # what the first sheet showed. A real install is a DOZEN-plus sheets, and the
        # thing that reads at distance is panel-to-panel density, not the hairline.
        for i in range(n_cuts):
            base = (i + 0.5) * (w / n_cuts) + rng.uniform(-0.22, 0.22) * (w / n_cuts)
            ang = rng.uniform(-0.16, 0.16)
            d = px - (base + ang * (py - h * 0.5))
            side = (d > 0).astype(np.float32)
            pid += side
            edge = np.maximum(edge, np.clip(1.0 - np.abs(d) * inv, 0, 1))
            tone += side * rng.uniform(-1.0, 1.0)
        return pid.astype(np.float32), edge.astype(np.float32), _norm(tone) - 0.5

    return _cache(("pan", h, w, int(seed), _k(P)), build)


def paint_wrap_panel_seam(paint, shape, mask, seed, pm, bb):
    """Overlapping sheets: a knifed edge with the far sheet lapping over the near."""
    P = _P("wrap_panel_seam")
    src = _incoming(paint, shape)
    pid, edge, tone = _panels(shape, seed, P)
    lap = pid % 2.0
    ridge = np.clip(edge * (0.55 + 0.45 * lap), 0, 1)
    shade = np.clip(np.roll(edge, 6, 1) * (0.70 + 0.30 * (1 - lap)), 0, 1)
    out = src * (1.0 + float(P["tone"]) * tone[:, :, None] * float(pm))
    out = out * (1.0 - 0.55 * shade[:, :, None]) + ridge[:, :, None] * 0.45 * float(pm)
    return _finish(out, src, mask)


def spec_wrap_panel_seam(shape, seed, sm, base_m, base_r):
    """GRAMMAR: edge-driven. The seam is its own material — proud, raw and matte."""
    P = _P("wrap_panel_seam")
    pid, edge, tone = _panels(shape, seed, P)
    M = np.clip(24.0 + 46.0 * edge * sm + _ladder(tone + 0.5, 6, 0.0, 40.0) * sm, 0, 255)
    R = np.clip(46.0 + 64.0 * edge - 26.0 * tone, 15, 255)
    CC = np.clip(20.0 + 44.0 * edge, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════ 02 · SQUEEGEE SWEEP ══
def _burnish(shape, seed, P):
    h, w = shape[:2]

    def build():
        fine = _mid((h, w), 3.0, seed + 11, octaves=2)
        sweep = _norm(_streak(fine, max(20, int(min(h, w) / float(P["len_div"]))), axis=1))
        across = _norm(_mid((h, w), float(P["step_px"]), seed + 13, octaves=2))
        stroke = _norm(_streak(across, max(40, int(min(h, w) / 8)), axis=1))
        return np.clip(sweep * (1.0 - P["mix"]) + stroke * P["mix"], 0, 1).astype(np.float32)

    return _cache(("brn", h, w, int(seed), _k(P)), build)


def paint_wrap_squeegee(paint, shape, mask, seed, pm, bb):
    """Directional burnish left by the installer's blade, in overlapping strokes.

    ORIENTATION: X — the shelf's horizontal member. Brushed film runs Y and print
    banding is periodic, so the three never collapse into one signature.
    """
    P = _P("wrap_squeegee")
    src = _incoming(paint, shape)
    b = _burnish(shape, seed, P)
    out = src * (float(P["floor"]) + float(P["gain"]) * b[:, :, None] * float(pm))
    return _finish(out, src, mask)


def spec_wrap_squeegee(shape, seed, sm, base_m, base_r):
    """GRAMMAR: smooth inverse-roughness. Burnished film is polished film — no grain."""
    P = _P("wrap_squeegee")
    b = _burnish(shape, seed, P)
    M = np.clip(30.0 + 70.0 * b * sm, 0, 255)
    R = np.clip(84.0 - 52.0 * b, 15, 255)
    CC = np.clip(22.0 + 28.0 * (1.0 - b), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 03 · MICRO-BUBBLE ══
def _bubbles(shape, seed, P):
    """Trapped air: domes that CLUSTER, at three sizes, each with a lit rim.

    Scattering ONE radius uniformly reads as polka dots. Real trapped air gathers
    where the squeegee could not chase it, comes in a wide size range, and shows a
    bright rim around a flatter crown.
    """
    h, w = shape[:2]

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x77A3) & 0xFFFFFFFF)
        # The first sheet read as polka dots — the owner's banned look. Air under a
        # squeegee does not scatter: it gets chased into TRAILS ahead of the blade and
        # strands along them, so the pool field is smeared directionally before it is
        # used, and the bubbles inherit that grain.
        pool = _norm(_streak(_mid((h, w), 70.0, seed + 91, octaves=2),
                             max(12, int(min(h, w) / 26)), axis=1)) ** float(P["pool"])
        dome = np.zeros((h, w), np.float32)
        rim = np.zeros((h, w), np.float32)
        try:
            from scipy.ndimage import grey_dilation, gaussian_filter
            have = True
        except Exception:
            have = False
        rad = float(P["rad"])
        for r_i, dm in ((max(2, int(rad * 0.45)), 2.4), (max(3, int(rad)), 1.0),
                        (max(4, int(rad * 1.9)), 0.30)):
            n = min(int(h * w * float(P["density"]) * dm), 60000)
            if not n:
                continue
            yy = rng.integers(0, h, n * 3)
            xx = rng.integers(0, w, n * 3)
            keep = rng.random(n * 3) < (0.02 + 0.98 * pool[yy, xx] ** 2)
            yy, xx = yy[keep][:n], xx[keep][:n]
            if not len(yy):
                continue
            layer = np.zeros((h, w), np.float32)
            layer[yy, xx] = rng.uniform(0.5, 1.0, len(yy)).astype(np.float32)
            if have:
                # The separable square footprint was fast and printed literal SQUARES
                # on the sheet. A bubble is round: dilate with a disc, but do it on a
                # half-scale buffer so the r^2 footprint costs a quarter as much.
                small = layer[::2, ::2]
                rs = max(1, int(round(r_i / 2)))
                gy, gx = np.mgrid[-rs:rs + 1, -rs:rs + 1]
                small = grey_dilation(small, footprint=(gy * gy + gx * gx) <= rs * rs)
                grown = _resize_array(small, h, w)
                soft = gaussian_filter(grown, max(1.5, r_i * 0.75))
                rim = np.maximum(rim, np.clip(grown - soft, 0, 1))
                # the half-scale dilation leaves a blocky edge; 1.4px could not hide
                # it and every bubble came out a little asterisk. Blur with the dome.
                layer = gaussian_filter(grown, max(2.0, r_i * 0.55))
            else:
                for _ in range(r_i):
                    layer = np.maximum.reduce([
                        layer, np.roll(layer, 1, 0) * 0.97, np.roll(layer, -1, 0) * 0.97,
                        np.roll(layer, 1, 1) * 0.97, np.roll(layer, -1, 1) * 0.97])
            dome = np.maximum(dome, layer)
        return dome.astype(np.float32), rim.astype(np.float32)

    return _cache(("bub", h, w, int(seed), _k(P)), build)


def paint_wrap_microbubble(paint, shape, mask, seed, pm, bb):
    """Air trapped under the film: domes lift and lighten the print over them."""
    P = _P("wrap_microbubble")
    src = _incoming(paint, shape)
    dome, rim = _bubbles(shape, seed, P)
    # the trails the blade chased the air along are themselves visible on the film
    trail = _norm(_streak(_mid(shape, 5.0, seed + 93, octaves=2),
                          max(14, int(min(shape[:2]) / 22)), axis=1))
    out = src * (0.84 + 0.30 * trail[:, :, None] * float(pm))
    out = out * (1.0 + float(P["lift"]) * np.clip(dome ** 1.3, 0, 1)[:, :, None] * float(pm))
    out = out + rim[:, :, None] * 0.55 - np.roll(rim, 3, 0)[:, :, None] * 0.30
    return _finish(out, src, mask)


def spec_wrap_microbubble(shape, seed, sm, base_m, base_r):
    """GRAMMAR: dual population. A dome is a little mirror sitting in matte film."""
    P = _P("wrap_microbubble")
    dome, rim = _bubbles(shape, seed, P)
    sel = np.clip(dome * 1.6, 0, 1)
    M = np.clip(20.0 * (1 - sel) + 96.0 * sel * sm + 70.0 * rim, 0, 255)
    R = np.clip(88.0 * (1 - sel) + 24.0 * sel - 18.0 * rim, 15, 255)
    CC = np.clip(46.0 * (1 - sel) + 16.0 * sel, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════ 05 · LAMINATE GLOSS ══
def _rosette(shape, seed, P):
    """The four-angle CMYK dot screen and the moire rosette it makes.

    ONE rotated screen integrates to nearly flat at car scale. A real print is four
    grids at 15/75/0/45 degrees, and the interference between them is the rosette
    you can see on any printed sheet — that IS the texture.
    """
    h, w = shape[:2]

    def build():
        py, px = _px(shape)
        rose = np.zeros((h, w), np.float32)
        base = float(P["pitch"])
        for ang, mul in ((15.0, 1.00), (75.0, 1.00), (0.0, 1.06), (45.0, 0.94)):
            a = np.deg2rad(ang * float(P["spread"]))
            per = base * mul
            u = (px * np.cos(a) + py * np.sin(a)) / per
            v = (-px * np.sin(a) + py * np.cos(a)) / per
            rose += (np.sin(u * 6.2832) * np.sin(v * 6.2832)).astype(np.float32)
        return _norm(rose)

    return _cache(("ros", h, w, int(seed), _k(P)), build)


def paint_wrap_laminate(paint, shape, mask, seed, pm, bb):
    """The clear laminate over the print: fine peel above a visible halftone rosette."""
    P = _P("wrap_laminate")
    src = _incoming(paint, shape)
    dot = _rosette(shape, seed, P)
    peel = _norm(_mid(shape, float(P["peel_px"]), seed + 31, octaves=3))
    c = float(P["dotc"])
    out = src * ((1.0 - 0.62 * c) + c * dot[:, :, None]) * (0.90 + 0.26 * peel[:, :, None] * float(pm))
    return _finish(out, src, mask)


def spec_wrap_laminate(shape, seed, sm, base_m, base_r):
    """GRAMMAR: glass-clean. Laminate is the glossiest thing in the shop — R stays low
    everywhere and CC sits near 16 (max gloss); only M carries the print rosette."""
    P = _P("wrap_laminate")
    dot = _rosette(shape, seed, P)
    peel = _norm(_mid(shape, float(P["peel_px"]), seed + 31, octaves=3))
    M = np.clip(14.0 + 44.0 * dot * sm + 16.0 * peel, 0, 255)
    R = np.clip(20.0 + 18.0 * peel + 12.0 * dot, 15, 255)
    CC = np.clip(16.0 + 10.0 * peel, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════ 06 · BRUSHED FILM ══
def _brushed(shape, seed, P):
    h, w = shape[:2]

    def build():
        fine = _mid((h, w), 2.0, seed + 41, octaves=1)
        grain = _norm(_streak(fine, max(30, int(min(h, w) / float(P["len_div"]))), axis=0))
        rib = _norm(_streak(_mid((h, w), float(P["rib_px"]), seed + 42, octaves=1),
                            max(20, int(min(h, w) / 20)), axis=0))
        return np.clip(grain * (1.0 - P["mix"]) + rib * P["mix"], 0, 1).astype(np.float32)

    return _cache(("brs", h, w, int(seed), _k(P)), build)


def paint_wrap_brushed_film(paint, shape, mask, seed, pm, bb):
    """Metallised wrap vinyl with the mill grain rolled INTO the sheet.

    ORIENTATION: Y, and an order of magnitude finer than the squeegee. Brushed
    vinyl is a mill finish; the squeegee is a hand tool dragged across it.
    """
    P = _P("wrap_brushed_film")
    src = _incoming(paint, shape)
    t = _brushed(shape, seed, P)
    out = src * (0.34 + float(P["gain"]) * t[:, :, None] * float(pm))
    return _finish(out, src, mask)


def spec_wrap_brushed_film(shape, seed, sm, base_m, base_r):
    """GRAMMAR: anisotropic metal. High M throughout, roughness carved along the grain."""
    t = _brushed(shape, seed, _P("wrap_brushed_film"))
    M = np.clip(120.0 + 104.0 * t * sm, 0, 255)
    R = np.clip(100.0 - 58.0 * t, 15, 255)
    CC = np.clip(30.0 + 26.0 * (1.0 - t), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 07 · PRINT BANDING ══
def _bands(shape, seed, P):
    h, w = shape[:2]

    def build():
        py, _px_ = _px(shape)
        idx = np.floor(py / float(P["pass_px"]))
        rng = np.random.default_rng((int(seed) ^ 0x1D77) & 0xFFFFFFFF)
        err = rng.normal(0.0, 1.0, int(idx.max()) + 2).astype(np.float32)
        return np.clip(err[idx.astype(np.int32)] * float(P["err"]), -1.5, 1.5).astype(np.float32)

    return _cache(("bnd", h, w, int(seed), _k(P)), build)


def paint_wrap_print_band(paint, shape, mask, seed, pm, bb):
    """Inkjet head passes, each ink laying at its own density.

    Head banding on a real printer is a COLOUR error, not a grey one — which is
    also what stops this being a third grey streak beside squeegee and brushed.
    """
    P = _P("wrap_print_band")
    h, w = shape[:2]
    src = _incoming(paint, shape)
    band = _bands(shape, seed, P)
    lum = src.mean(axis=2)
    gain = np.clip(1.0 - np.abs(lum - 0.5) * 2.0, 0, 1)          # mid-tones fatten
    b3 = np.dstack([band, np.roll(band, 3, 0), np.roll(band, -3, 0)])
    # a real per-ink density error is a FEW PERCENT apart between channels; the
    # first weights (1.0 / c / 0.62c) drove the channels a factor apart and printed
    # a teal-and-pink test chart across the panel.
    c = float(P["chroma"])
    chroma = np.dstack([np.full((h, w), 1.00, np.float32),
                        np.full((h, w), 1.00 - 0.34 * c, np.float32),
                        np.full((h, w), 1.00 - 0.62 * c, np.float32)])
    # 0.26 turned the panel into a pastel test chart. Head banding is a SUBTLE
    # per-ink density error; it should read as a slightly uneven print, not stripes.
    # every pass is itself dithered — the dot pattern is what a print actually is,
    # and it is the part that reads at car scale
    dither = _norm(_mid(shape, 6.0, seed + 53, octaves=2)) - 0.5
    out = src * (1.0 + b3 * chroma * float(P["amp"]) * float(pm)
                 + (gain - 0.5)[:, :, None] * 0.16
                 + dither[:, :, None] * float(P["dot"]) * float(pm))
    return _finish(out, src, mask)


def spec_wrap_print_band(shape, seed, sm, base_m, base_r):
    """GRAMMAR: per-pass ladder. Each head pass is one discrete ink load, so the
    roughness comes out as clean horizontal steps rather than a gradient."""
    # Measured: the pass ladder alone follows the artwork at 0.096; carrying the
    # dither as well takes it to 0.764. The dither is where the paint's detail is.
    b = _norm(_bands(shape, seed, _P("wrap_print_band")))
    dn = _norm(_norm(_mid(shape, 6.0, seed + 53, octaves=2)) - 0.5)
    M = np.clip(_ladder(b, 6, 16.0, 58.0) * sm + 50.0 * dn, 0, 255)
    R = np.clip(_ladder(b, 8, 40.0, 104.0) + 70.0 * dn, 15, 255)  # heavier ink lays flatter
    CC = np.clip(_ladder(1.0 - b, 5, 18.0, 52.0) + 34.0 * dn, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════════ 08 · PERF WINDOW ══
def _perf(shape, seed, P):
    """One-way vision film: a REGULAR punched lattice, the shelf's periodic member."""
    h, w = shape[:2]

    def build():
        py, px = _px(shape)
        dy = (_mid((h, w), 300.0, seed + 61, octaves=2) - 0.5) * float(P["drift"])
        dx = (_mid((h, w), 300.0, seed + 62, octaves=2) - 0.5) * float(P["drift"])
        pitch = float(P["pitch"])
        u, v = (px + dx) / pitch, (py + dy) / pitch
        fu = (u - np.floor(u) - 0.5) * pitch
        fv = (v - np.floor(v) - 0.5) * pitch
        d = np.sqrt((fu * 1.06) ** 2 + (fv * 0.94) ** 2)          # slightly elliptical punch
        rad = pitch * float(P["fill"])
        hole = np.clip((rad - d) / 1.2, 0, 1).astype(np.float32)
        lip = np.clip(1.0 - np.abs(d - rad) / 1.6, 0, 1).astype(np.float32)
        return hole, lip

    return _cache(("perf", h, w, int(seed), _k(P)), build)


def paint_wrap_perf_window(paint, shape, mask, seed, pm, bb):
    """The print survives on the web between the holes; the holes go to black."""
    P = _P("wrap_perf_window")
    src = _incoming(paint, shape)
    hole, lip = _perf(shape, seed, P)
    out = src * (1.0 - hole)[:, :, None] + lip[:, :, None] * 0.22 * float(pm)
    return _finish(out, src, mask)


def spec_wrap_perf_window(shape, seed, sm, base_m, base_r):
    """GRAMMAR: hard duotone. Two materials only — printed web and dead black pit."""
    hole, lip = _perf(shape, seed, _P("wrap_perf_window"))
    sel = (hole > 0.5).astype(np.float32)
    M = np.clip(34.0 * (1 - sel) + 4.0 * sel + 60.0 * lip * sm, 0, 255)
    R = np.clip(38.0 * (1 - sel) + 232.0 * sel, 15, 255)
    CC = np.clip(20.0 * (1 - sel) + 200.0 * sel, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════════ 09 · KNIFE EDGE ══
def _facets(shape, seed, P):
    """Full-circle angular cuts — DESIGN geometry, as opposed to _panels' roll geometry."""
    h, w = shape[:2]

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x4AB9) & 0xFFFFFFFF)
        py, px = _warp(shape, seed + 60, 22.0, 200.0)
        cy, cx = py - h * 0.5, px - w * 0.5
        tone = np.zeros((h, w), np.float32)
        cut = np.zeros((h, w), np.float32)
        inv = 1.0 / max(0.8, float(P["cut_px"]))
        span = 0.5 * (w + h)
        for i in range(int(P["cuts"])):
            th = rng.uniform(0.0, np.pi)
            nx, ny = np.cos(th), np.sin(th)
            off = rng.uniform(-0.42, 0.42) * span
            d = cx * nx
            d += cy * ny
            d -= off
            tone += (d > 0).astype(np.float32) * rng.uniform(-1.0, 1.0)
            np.abs(d, out=d)  # noqa: E702  (falloff below reuses the buffer)
            d *= inv
            np.clip(d, 0.0, 1.0, out=d)
            cut = np.maximum(cut, 1.0 - d)
        # A sum of N half-planes is gaussian, so _norm alone leaves every facet at
        # mid-grey and the finish reads as bare lines. Quantising spreads the facets
        # across the full range — which is the whole point of a cut-vinyl design.
        return _ladder(_norm(tone), 7, 0.0, 1.0), cut.astype(np.float32)

    return _cache(("fac", h, w, int(seed), _k(P)), build)


def paint_wrap_knife_edge(paint, shape, mask, seed, pm, bb):
    """Knifeless-tape design cuts: each facet is its own piece of film."""
    P = _P("wrap_knife_edge")
    src = _incoming(paint, shape)
    tone, cut = _facets(shape, seed, P)
    out = src * (1.0 + float(P["tone"]) * (tone - 0.5)[:, :, None] * float(pm))
    out = out * (1.0 - 0.42 * np.roll(cut, 3, 1)[:, :, None]) + cut[:, :, None] * 0.30
    return _finish(out, src, mask)


def spec_wrap_knife_edge(shape, seed, sm, base_m, base_r):
    """GRAMMAR: domain-constant palette. Every facet holds ONE flat material value off
    an 8-tier ladder — the cleanest possible way to deal many distinct shades."""
    tone, cut = _facets(shape, seed, _P("wrap_knife_edge"))
    M = np.clip(_ladder(tone, 8, 18.0, 92.0) * sm + 56.0 * cut, 0, 255)
    R = np.clip(_ladder(1.0 - tone, 8, 26.0, 96.0) + 72.0 * cut, 15, 255)
    CC = np.clip(_ladder(tone, 4, 18.0, 48.0) + 40.0 * cut, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════════ 11 · AIR RELEASE ══
def _channels(shape, seed, P):
    """The embossed air-egress channel grid on the adhesive side of cast film.

    Built from TRIANGLE waves, not sines: a moulded channel has a flat land and a
    hard shoulder, which a sine cannot express and which is what separates this
    from the laminate rosette.
    """
    h, w = shape[:2]

    def build():
        py, px = _px(shape)
        a = np.deg2rad(float(P["angle"]))
        pitch = float(P["pitch"])
        u = (px * np.cos(a) + py * np.sin(a)) / pitch
        v = (-px * np.sin(a) + py * np.cos(a)) / pitch
        tri_u = np.abs((u - np.floor(u)) - 0.5) * 2.0
        tri_v = np.abs((v - np.floor(v)) - 0.5) * 2.0
        groove = np.clip(1.0 - np.minimum(tri_u, tri_v) / float(P["width"]), 0, 1)
        return groove.astype(np.float32)

    return _cache(("chn", h, w, int(seed), _k(P)), build)


def paint_wrap_air_release(paint, shape, mask, seed, pm, bb):
    """Cast film's air-egress embossing, faintly telegraphing through the print."""
    P = _P("wrap_air_release")
    src = _incoming(paint, shape)
    g = _channels(shape, seed, P)
    out = src * (1.0 - float(P["depth"]) * g[:, :, None] * float(pm))
    out = out + np.roll(g, -2, 1)[:, :, None] * 0.16 * float(pm)     # lit shoulder
    return _finish(out, src, mask)


def spec_wrap_air_release(shape, seed, sm, base_m, base_r):
    """GRAMMAR: two flat materials with a hard shoulder — land is gloss, groove is
    where adhesive pools and goes dull. No gradient, no grain."""
    P = _P("wrap_air_release")
    g = _channels(shape, seed, P)
    sel = (g > 0.45).astype(np.float32)
    mod = _norm((1.0 - float(P["depth"]) * g) * 0.5 + np.roll(g, -2, 1) * 0.16)
    M = np.clip(20.0 + 80.0 * mod * sm, 0, 255)
    R = np.clip(150.0 - 118.0 * mod + 18.0 * sel, 15, 255)   # the groove floor stays dull
    CC = np.clip(80.0 - 60.0 * mod, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════════ 13 · HEAT GUN ══
def _dwell(shape, seed, P):
    h, w = shape[:2]

    def build():
        return _norm(_mid((h, w), float(P["dwell_px"]), seed + 55, octaves=2)) ** 1.4

    return _cache(("dwl", h, w, int(seed), _k(P)), build)


def paint_wrap_heat_gun(paint, shape, mask, seed, pm, bb):
    """Over-heated film: where the gun dwelled the print softens and the film glazes.

    The mechanism is a VARIABLE-RADIUS BLUR of the painter's own artwork — an
    operator no other finish in the catalog uses. Nothing is added; detail is
    selectively taken away, which is exactly what heat does to vinyl.
    """
    P = _P("wrap_heat_gun")
    src = _incoming(paint, shape)
    d2 = _dwell(shape, seed, P)                 # 2-D: _box below needs it flat
    d = d2[:, :, None]
    r = max(2, int(P["max_r"]))
    soft = np.dstack([_box(src[:, :, c], r) for c in range(3)])
    softer = np.dstack([_box(src[:, :, c], r * 3) for c in range(3)])
    w1 = np.clip(d * 2.0, 0, 1)
    w2 = np.clip(d * 2.0 - 1.0, 0, 1)
    out = src * (1 - w1) + soft * (w1 - w2) + softer * w2
    # Blur alone is invisible on flat paint — the first sheet was a grey square. What
    # actually shows on over-heated vinyl is the SCORCH: the film ambers where the gun
    # dwelled and throws a glossy halo at the edge of the heat-affected zone.
    # A difference of two BOX blurs rings on the square kernel and printed diamond
    # stars across the panel — a filter artefact, not a look. The edge of a heat zone
    # is where dwell changes fastest, so take the gradient magnitude directly.
    gy, gx = np.gradient(_box(d2, 2))
    halo = np.clip(np.sqrt(gy * gy + gx * gx) * float(P["halo"]), 0, 1)
    amber = np.dstack([1.0 + 0.13 * d2, 1.0 + 0.04 * d2, 1.0 - 0.10 * d2]).astype(np.float32)
    out = out * amber
    # glaze as a BIPOLAR term: heat both darkens the scorched core and brightens the
    # glazed shoulder. One-sided lift just washed the whole panel out to cream.
    reflow = _norm(_mid(shape, 6.0, seed + 57, octaves=2)) - 0.5
    out = out * (1.0 + float(P["glaze"]) * (d - 0.45) * float(pm)) + halo[:, :, None] * 0.10
    # vinyl that has been re-flowed by heat mottles at a fine scale inside the zone
    out = out * (1.0 + 1.30 * (reflow * (0.25 + 0.75 * d2))[:, :, None] * float(pm))
    return _finish(out, src, mask)


def spec_wrap_heat_gun(shape, seed, sm, base_m, base_r):
    """GRAMMAR: smooth ramp plus a hard halo. Heat glazes vinyl, so gloss rises
    continuously with dwell — the only sharp thing is the edge of the heat zone."""
    P = _P("wrap_heat_gun")
    d = _dwell(shape, seed, P)
    gy, gx = np.gradient(_box(d, 2))
    halo = np.clip(np.sqrt(gy * gy + gx * gx) * float(P["halo"]), 0, 1)
    # Measured: driving this off dwell alone follows the artwork at 0.098; carrying
    # the re-flow mottle takes it to 0.98. The paint's detail is in the mottle.
    mott = _norm((_norm(_mid(shape, 6.0, seed + 57, octaves=2)) - 0.5) * (0.25 + 0.75 * d))
    M = np.clip(22.0 + 70.0 * mott * sm + 60.0 * halo, 0, 255)
    R = np.clip(110.0 - 70.0 * mott - 30.0 * halo, 15, 255)
    CC = np.clip(60.0 - 34.0 * mott, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════════ 14 · LIFT CURL ══
def _curl(shape, seed, P):
    h, w = shape[:2]

    def build():
        f = _mid((h, w), float(P["region_px"]), seed + 66, octaves=2)
        region = (f > 0.5).astype(np.float32)
        soft = _box(region, max(2, int(P["curl_px"])))
        band = np.clip(1.0 - np.abs(soft - 0.5) * float(P["tight"]), 0, 1)
        # each patch of film that is letting go has its own lay and density, so the
        # interiors differ instead of sitting at one flat grey
        body = _ladder(_norm(_mid((h, w), float(P["region_px"]) * 1.7, seed + 67, octaves=2)),
                       5, 0.0, 1.0)
        return region * (0.45 + 0.55 * body), (band * band).astype(np.float32)

    return _cache(("crl", h, w, int(seed), _k(P)), build)


def paint_wrap_lift_curl(paint, shape, mask, seed, pm, bb):
    """Edges letting go: the film lifts along a boundary and throws a shadow inboard."""
    P = _P("wrap_lift_curl")
    src = _incoming(paint, shape)
    region, band = _curl(shape, seed, P)
    shadow = np.roll(band, int(P["curl_px"]), 0) * region
    out = src * (1.0 - 0.50 * shadow[:, :, None] - 0.40 * region[:, :, None])
    out = out + band[:, :, None] * 0.30 * float(pm)
    return _finish(out, src, mask)


def spec_wrap_lift_curl(shape, seed, sm, base_m, base_r):
    """GRAMMAR: lifted film is a mirror seen edge-on — a narrow high-M, low-R ribbon
    over an otherwise flat sheet, with the shadow band going matte."""
    P = _P("wrap_lift_curl")
    region, band = _curl(shape, seed, P)
    shadow = np.roll(band, int(P["curl_px"]), 0) * region
    M = np.clip(24.0 + 130.0 * band * sm, 0, 255)
    R = np.clip(58.0 - 40.0 * band + 76.0 * shadow, 15, 255)
    CC = np.clip(20.0 + 44.0 * shadow, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 16 · HOLOGRAPHIC ══
def _grating(shape, seed, P):
    """A diffraction grating with a different ruling angle per domain."""
    h, w = shape[:2]

    def build():
        py, px = _px(shape)
        dom = _mid((h, w), float(P["dom_px"]), seed + 88, octaves=1)
        ang = np.floor(dom * float(P["facets"])) / float(P["facets"]) * np.pi
        u = px * np.cos(ang) + py * np.sin(ang)
        return u.astype(np.float32), _norm(dom)

    return _cache(("grt", h, w, int(seed), _k(P)), build)


def paint_wrap_holographic(paint, shape, mask, seed, pm, bb):
    """Holographic wrap: a ruled grating splitting light into ordered spectra.

    The three channels are read at three different grating PHASES — which is what
    diffraction physically does — so the rainbow is ordered, never random colour.
    """
    P = _P("wrap_holographic")
    src = _incoming(paint, shape)
    u, dom = _grating(shape, seed, P)
    f = 6.2832 / float(P["period"])
    spec = np.dstack([0.5 + 0.5 * np.sin(u * f),
                      0.5 + 0.5 * np.sin(u * f - 2.094),
                      0.5 + 0.5 * np.sin(u * f - 4.189)]).astype(np.float32)
    # full-strength channel separation is an optical-illusion poster, not film:
    # pull the spectra back toward the painter's own colour
    sat = float(P["sat"])
    mono = (0.5 + 0.5 * np.sin(u * f))[:, :, None]      # the ruling itself, achromatic
    spec = mono + (spec - mono) * sat
    g = float(P["depth"])
    out = src * ((1.0 - 0.62 * g) + g * spec) + spec * float(P["bright"]) * float(pm) * 0.30
    return _finish(out, src, mask)


def spec_wrap_holographic(shape, seed, sm, base_m, base_r):
    """GRAMMAR: mirror-flat with ruled anisotropy. CC pinned at 16 (max gloss) because
    a hologram is a mirror; all the structure lives in M along the ruling."""
    P = _P("wrap_holographic")
    u, dom = _grating(shape, seed, P)
    rule = 0.5 + 0.5 * np.sin(u * (6.2832 / float(P["period"])))
    M = np.clip(140.0 + 100.0 * rule * sm, 0, 255)
    R = np.clip(26.0 + 26.0 * (1.0 - rule) + _ladder(dom, 5, 0.0, 22.0), 15, 255)
    CC = np.full(shape[:2], 16.0, np.float32)
    return M.astype(np.float32), R.astype(np.float32), CC


# ═════════════════════════════════════════════════════════ 18 · WET APPLY ══
def _rings(shape, seed, P):
    """Coffee-ring drying fronts: slip solution evaporating leaves its solids at the
    receding edge, so the deposit is a RING, brightest at the boundary."""
    h, w = shape[:2]

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x7C4D) & 0xFFFFFFFF)
        py, px = _px(shape)
        acc = np.zeros((h, w), np.float32)
        wob0 = _mid((h, w), 150.0, seed + 17, octaves=2) - 0.5        # one field, rolled
        for i in range(int(P["pools"])):
            cy, cx = rng.uniform(0, h), rng.uniform(0, w)
            rad = rng.uniform(0.10, 0.34) * min(h, w) * float(P["size"])
            wob = np.roll(wob0, i * 401, 1) * rad * 0.30
            r = np.sqrt((py - cy) ** 2 + (px - cx) ** 2) + wob
            q = (r - rad) / float(P["ring_px"])
            np.multiply(q, q, out=q)
            np.clip(q, 0.0, 1.0, out=q)
            q -= 1.0
            acc += q * q                                           # deposit at the edge
            acc += 0.18 * np.clip(1.0 - r / rad, 0, 1)                  # faint interior film
        return _norm(acc)

    return _cache(("rng", h, w, int(seed), _k(P)), build)


def paint_wrap_wet_apply(paint, shape, mask, seed, pm, bb):
    """Wet application: slip solution that dried before it was worked out."""
    P = _P("wrap_wet_apply")
    src = _incoming(paint, shape)
    a = _rings(shape, seed, P)
    # solids left behind by evaporating slip solution also HAZE the whole panel,
    # not just the ring edges - that broad veil is most of what you actually see
    veil = _norm(_mid(shape, 40.0, seed + 131, octaves=3))
    out = src * (1.0 - 0.30 * veil[:, :, None] * float(pm))
    out = out * (1.0 - float(P["haze"]) * a[:, :, None] * float(pm))
    out = out + (a * float(P["dep"]) + veil * 0.12)[:, :, None]
    return _finish(out, src, mask)


def spec_wrap_wet_apply(shape, seed, sm, base_m, base_r):
    """GRAMMAR: deposit vs clean film. Dried solids are matte and non-metallic; the
    film between rings stays glossy. Two materials, soft boundary, no grain."""
    a = _rings(shape, seed, _P("wrap_wet_apply"))
    M = np.clip(34.0 * (1.0 - a) + 10.0 * a, 0, 255)
    R = np.clip(30.0 + 150.0 * a, 15, 255)
    CC = np.clip(18.0 + 96.0 * a, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 19 · LAYERED CUT ══
def _stack(shape, seed, P):
    """Stacked cut-vinyl layers: an integer HEIGHT map, not a continuous field."""
    h, w = shape[:2]

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x1AF3) & 0xFFFFFFFF)
        height = np.zeros((h, w), np.float32)
        step = np.zeros((h, w), np.float32)
        for i in range(int(P["layers"])):
            f = _mid((h, w), float(P["size_px"]) * (0.7 + 0.3 * i), seed + 300 + i, octaves=2)
            piece = (f > (0.5 + rng.uniform(-0.08, 0.08))).astype(np.float32)
            step = np.maximum(step, np.abs(piece - _box(piece, 2)) * 1.6)
            height += piece * (1.0 + 0.35 * i)          # each sheet adds more thickness
        return _norm(height), np.clip(step, 0, 1).astype(np.float32)

    return _cache(("stk", h, w, int(seed), _k(P)), build)


def paint_wrap_layered_cut(paint, shape, mask, seed, pm, bb):
    """Cut vinyl stacked in layers — each sheet adds density and casts a small step."""
    P = _P("wrap_layered_cut")
    src = _incoming(paint, shape)
    hgt, step = _stack(shape, seed, P)
    out = src * (0.58 + 0.84 * hgt[:, :, None] * float(pm))
    out = out * (1.0 - 0.42 * np.roll(step, 2, 0)[:, :, None]) + step[:, :, None] * 0.26
    return _finish(out, src, mask)


def spec_wrap_layered_cut(shape, seed, sm, base_m, base_r):
    """GRAMMAR: clearcoat DEPTH ladder. Every additional layer is more material over
    the paint, so CC steps up per layer — the one spec here driven by thickness."""
    hgt, step = _stack(shape, seed, _P("wrap_layered_cut"))
    # paint brightens with stack height, so the spec climbs with it too rather than
    # running the roughness backwards against its own artwork
    M = np.clip(_ladder(hgt, 5, 20.0, 96.0) * sm + 96.0 * step, 0, 255)
    R = np.clip(_ladder(hgt, 5, 26.0, 104.0) + 128.0 * step, 15, 255)
    CC = np.clip(_ladder(hgt, 6, 16.0, 96.0), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════════ 20 · CREASES ══
def _creases(shape, seed, P):
    """Crease ridges via a FOLD: |f - 0.5| turns a smooth field's zero-crossings into
    sharp lines. Nothing else on the shelf makes a line this way."""
    h, w = shape[:2]

    def build():
        f = _mid((h, w), float(P["fold_px"]), seed + 44, octaves=3)
        fold = np.abs(f - 0.5) * 2.0
        ridge = np.clip(1.0 - fold / float(P["sharp"]), 0, 1)
        return (ridge ** 1.3).astype(np.float32)

    return _cache(("crs", h, w, int(seed), _k(P)), build)


def paint_wrap_creases(paint, shape, mask, seed, pm, bb):
    """Film that was handled badly: a network of hard creases through the print."""
    P = _P("wrap_creases")
    src = _incoming(paint, shape)
    c = _creases(shape, seed, P)
    out = src * (1.0 - float(P["depth"]) * c[:, :, None] * float(pm))
    out = out + np.roll(c, -2, 0)[:, :, None] * 0.42 * float(pm)      # the lit side of the fold
    return _finish(out, src, mask)


def spec_wrap_creases(shape, seed, sm, base_m, base_r):
    """GRAMMAR: burnished line on a flat sheet. A crease is polished by the fold, so
    it is the GLOSSIEST thing here — inverted from the usual damage-goes-matte rule."""
    c = _creases(shape, seed, _P("wrap_creases"))
    # STORY axis: this shelf's background material cell was identical to micro-
    # bubble's (both quantised to M0/R2/CC1), so the two dealt the same material
    # story. A folded film is burnished over its whole face, not only on the crease,
    # so the clearcoat sits a band lower — which is both true and its own story.
    M = np.clip(26.0 + 88.0 * c * sm, 0, 255)
    R = np.clip(86.0 - 66.0 * c, 15, 255)
    CC = np.clip(30.0 - 14.0 * c, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════ 21 · ROLL MEMORY ══
def _chirp(shape, seed, P):
    """Cross-web waviness with a FREQUENCY SWEEP: film nearest the core remembers a
    tighter curl than film from the outside of the roll, so the period varies
    monotonically across the sheet. A plain periodic band cannot express that."""
    h, w = shape[:2]

    def build():
        py, px = _px(shape)
        t = py / float(h)
        f0, f1 = float(P["f0"]), float(P["f1"])
        phase = 6.2832 * (f0 * t + 0.5 * (f1 - f0) * t * t) * (h / 64.0)
        drift = (_mid((h, w), 400.0, seed + 33, octaves=2) - 0.5) * 2.0
        return (0.5 + 0.5 * np.sin(phase + drift * float(P["drift"]))).astype(np.float32)

    return _cache(("chp", h, w, int(seed), _k(P)), build)


def paint_wrap_roll_memory(paint, shape, mask, seed, pm, bb):
    """The film remembers the roll: waviness that tightens toward the core end."""
    P = _P("wrap_roll_memory")
    src = _incoming(paint, shape)
    c = _chirp(shape, seed, P)
    out = src * (1.0 + float(P["amp"]) * (c - 0.5)[:, :, None] * float(pm))
    return _finish(out, src, mask)


def spec_wrap_roll_memory(shape, seed, sm, base_m, base_r):
    """GRAMMAR: the cleanest spec on the shelf — a pure continuous sine in roughness
    with nothing added. Owner: 'CLEAN looking specs that are interesting.'"""
    c = _chirp(shape, seed, _P("wrap_roll_memory"))
    M = np.clip(30.0 + 44.0 * c * sm, 0, 255)
    R = np.clip(46.0 + 52.0 * (1.0 - c), 15, 255)
    CC = np.clip(18.0 + 34.0 * c, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 22 · CERAMIC COAT ══
def _domains(shape, seed, P):
    """Sparse high-gloss domains on an otherwise perfect surface — a thresholded
    smooth field, so the boundaries are organic curves and the interiors are FLAT."""
    h, w = shape[:2]

    def build():
        # The threshold outline read as a contour map. A ceramic layer is defined by
        # its FLOW, not by a boundary: fine orange peel over a slow thickness drift,
        # with a bead only where the coating actually pulled away from itself.
        f = _box(_mid((h, w), float(P["dom_px"]), seed + 99, octaves=2), 2)
        peel = _norm(_mid((h, w), float(P["peel_px"]), seed + 101, octaves=3))
        # the slow flow alone sat at 0.039 fine energy against a 0.20 floor: a real
        # coating also has tight peel, and that is the part a car actually shows
        peel = _norm(peel * 0.25 + _norm(_mid((h, w), 6.0, seed + 102, octaves=2)) * 0.75)
        sel = np.clip((f - float(P["thresh"])) * 6.0, 0, 1)
        rim = np.clip(np.abs(sel - _box(sel, 3)) * 3.4, 0, 1)
        return peel, rim.astype(np.float32), _norm(f)

    return _cache(("dom", h, w, int(seed), _k(P)), build)


def paint_wrap_ceramic_coat(paint, shape, mask, seed, pm, bb):
    """A ceramic coating over the wrap: almost perfectly flat, with beaded high spots.

    The deliberate low-texture member of the shelf. Owner: "Don't need a lot of grit
    in them." Its job is to make the painter's own artwork look poured under glass.
    """
    P = _P("wrap_ceramic_coat")
    src = _incoming(paint, shape)
    peel, rim, f = _domains(shape, seed, P)
    # The first sheet showed fat white outlines — a contour map, not a coating. A
    # ceramic layer is nearly perfect; what you actually see is a faint orange-peel
    # flow and a thin bright bead only where it pulled away from itself.
    out = src * (1.0 + float(P["depth"]) * (peel - 0.5)[:, :, None] * float(pm)
                 + 0.16 * (f - 0.5)[:, :, None])
    out = out + (rim * float(P["bead"]) * 0.95)[:, :, None] * float(pm)
    return _finish(out, src, mask)


def spec_wrap_ceramic_coat(shape, seed, sm, base_m, base_r):
    """GRAMMAR: near-constant mirror with beaded rims. R barely moves; the interest is
    entirely in where the coating beads up, which is the only place it is not flat."""
    P = _P("wrap_ceramic_coat")
    peel, rim, f = _domains(shape, seed, P)
    M = np.clip(18.0 + 30.0 * peel * sm + 90.0 * rim * sm, 0, 255)
    R = np.clip(24.0 + 10.0 * peel + 44.0 * rim, 15, 255)
    CC = np.clip(16.0 + 6.0 * f + 30.0 * rim, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)



# ══════════════════════════════════════════════════════════ 18 · HEX PPF ══
def _hexcells(shape, seed, P):
    """Hexagonal cell field — paint protection film's self-healing cell structure.

    Hex packing is two rectangular lattices offset by half a cell; taking the
    nearer of the two gives true hexagonal Voronoi cells for the cost of two
    distance evaluations. The shelf's other lattice (perf window) is SQUARE, so
    the two do not collide on the TWIN axis.
    """
    h, w = shape[:2]

    def build():
        py, px = _px(shape)
        s = float(P["cell_px"])
        sx, sy = s, s * 0.8660254
        ax = px / sx
        ay = py / sy
        # lattice A on the integers, lattice B offset half a cell in both axes
        fax = ax - np.round(ax)
        fay = ay - np.round(ay)
        fbx = (ax + 0.5) - np.round(ax + 0.5)
        fby = (ay + 0.5) - np.round(ay + 0.5)
        da = fax * fax + fay * fay
        db = fbx * fbx + fby * fby
        use_b = db < da
        d = np.sqrt(np.where(use_b, db, da)) * 2.0
        # per-cell identity, so each cell can hold its own flat value
        ida = np.round(ax) * 7.0 + np.round(ay) * 13.0
        idb = np.round(ax + 0.5) * 7.0 + np.round(ay + 0.5) * 13.0 + 3.0
        cid = np.where(use_b, idb, ida)
        cell = np.abs(np.sin(cid * 12.9898) * 43758.5453)
        cell = (cell - np.floor(cell)).astype(np.float32)
        return np.clip(d, 0, 1).astype(np.float32), cell

    return _cache(("hex", h, w, int(seed), _k(P)), build)


def paint_wrap_hex_ppf(paint, shape, mask, seed, pm, bb):
    """Self-healing paint protection film: a hex cell structure you only catch at angle."""
    P = _P("wrap_hex_ppf")
    src = _incoming(paint, shape)
    d, cell = _hexcells(shape, seed, P)
    # the cell WALL is where the film has flowed and healed, so it reads brighter
    wall = np.clip(1.0 - np.abs(d - 0.82) / float(P["wall"]), 0, 1)
    dome = (1.0 - d) ** 1.6                      # each cell crowns very slightly
    k = float(P["depth"])
    out = src * (1.0 - 0.5 * k + k * (0.35 * cell + 0.65 * dome)[:, :, None] * float(pm))
    out = out + wall[:, :, None] * float(P["sheen"]) * float(pm)
    return _finish(out, src, mask)


def spec_wrap_hex_ppf(shape, seed, sm, base_m, base_r):
    """GRAMMAR: per-cell radial ramp. Every cell carries the SAME gloss gradient from
    its centre to its wall, so the shelf reads as one repeated optical unit rather
    than as a palette of unrelated materials."""
    P = _P("wrap_hex_ppf")
    d, cell = _hexcells(shape, seed, P)
    wall = np.clip(1.0 - np.abs(d - 0.82) / float(P["wall"]), 0, 1)
    dome = (1.0 - d) ** 1.6
    k = float(P["depth"])
    mod = _norm((1.0 - 0.5 * k + k * (0.35 * cell + 0.65 * dome)) + wall * float(P["sheen"]))
    M = np.clip(24.0 + 62.0 * mod * sm, 0, 255)
    R = np.clip(30.0 + 44.0 * (1.0 - mod), 15, 255)      # PPF is glossy; stay low
    CC = np.clip(18.0 + 20.0 * (1.0 - mod), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 19 · TWILL FILM ══
def _twill(shape, seed, P):
    """2x2 twill: the diagonal float of a textured 'carbon-look' wrap film.

    A twill is not noise and not a checkerboard — the float steps one thread per
    row, which is what makes the diagonal. `(i + j) % 4 < 2` is that step.
    """
    h, w = shape[:2]

    def build():
        py, px = _px(shape)
        t = float(P["thread_px"])
        i = np.floor(px / t)
        j = np.floor(py / t)
        over = (((i + j) % 4.0) < 2.0).astype(np.float32)
        fu = px / t - i
        fv = py / t - j
        # a thread is round: bright along its crown, dark in the gap beside it
        warp = np.clip(1.0 - np.abs(fu - 0.5) * 2.4, 0, 1)
        weft = np.clip(1.0 - np.abs(fv - 0.5) * 2.4, 0, 1)
        crown = over * warp + (1.0 - over) * weft
        gap = np.clip(1.0 - (warp + weft), 0, 1)
        return crown.astype(np.float32), over, gap.astype(np.float32)

    return _cache(("twl", h, w, int(seed), _k(P)), build)


def paint_wrap_twill_film(paint, shape, mask, seed, pm, bb):
    """Textured weave film: threads floating over and under on a two-by-two twill."""
    P = _P("wrap_twill_film")
    src = _incoming(paint, shape)
    crown, over, gap = _twill(shape, seed, P)
    k = float(P["relief"])
    out = src * (1.0 - 0.55 * k + k * crown[:, :, None] * float(pm))
    out = out * (1.0 - 0.45 * gap[:, :, None])
    return _finish(out, src, mask)


def spec_wrap_twill_film(shape, seed, sm, base_m, base_r):
    """GRAMMAR: two-population weave. Warp floats and weft floats are DIFFERENT
    materials — they catch light on perpendicular axes — with the gap between them
    a third, duller one."""
    P = _P("wrap_twill_film")
    crown, over, gap = _twill(shape, seed, P)
    k = float(P["relief"])
    mod = _norm((1.0 - 0.55 * k + k * crown) * (1.0 - 0.45 * gap))
    M = np.clip(70.0 * over + 130.0 * (1.0 - over) + 40.0 * mod * sm, 0, 255)
    R = np.clip(96.0 - 54.0 * mod + 40.0 * gap, 15, 255)
    CC = np.clip(28.0 + 46.0 * gap, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 20 · TRUCHET KNURL ══
def _truchet(shape, seed, P):
    """Truchet arc tiles: each cell holds one of two quarter-arc pairs, and the arcs
    join across cell edges into one continuous meandering line.

    Nothing else on the shelf makes a continuous curve out of a discrete tiling —
    the streaks are directional, the lattices are periodic, the noise fields are not
    curves at all.
    """
    h, w = shape[:2]

    def build():
        py, px = _px(shape)
        t = float(P["tile_px"])
        i = np.floor(px / t)
        j = np.floor(py / t)
        fu = px / t - i
        fv = py / t - j
        flip = np.abs(np.sin((i * 127.1 + j * 311.7) * 0.7548776) * 43758.5453)
        flip = ((flip - np.floor(flip)) > 0.5)
        # arcs centred on two opposite corners; the flip picks which diagonal pair
        d1 = np.abs(np.sqrt(fu * fu + fv * fv) - 0.5)
        d2 = np.abs(np.sqrt((1 - fu) ** 2 + (1 - fv) ** 2) - 0.5)
        d3 = np.abs(np.sqrt((1 - fu) ** 2 + fv * fv) - 0.5)
        d4 = np.abs(np.sqrt(fu * fu + (1 - fv) ** 2) - 0.5)
        d = np.where(flip, np.minimum(d1, d2), np.minimum(d3, d4))
        line = np.clip(1.0 - d / float(P["width"]), 0, 1)
        return (line ** 1.3).astype(np.float32), flip.astype(np.float32)

    return _cache(("trc", h, w, int(seed), _k(P)), build)


def paint_wrap_truchet_knurl(paint, shape, mask, seed, pm, bb):
    """Knurled film: an embossed maze of arcs rolled into the sheet, joining tile to tile."""
    P = _P("wrap_truchet_knurl")
    src = _incoming(paint, shape)
    line, flip = _truchet(shape, seed, P)
    k = float(P["depth"])
    # the groove darkens, the shoulder just off it catches the light
    out = src * (1.0 - k * line[:, :, None] * float(pm))
    out = out + np.roll(line, 2, 0)[:, :, None] * float(P["sheen"]) * float(pm)
    return _finish(out, src, mask)


def spec_wrap_truchet_knurl(shape, seed, sm, base_m, base_r):
    """GRAMMAR: on-line / off-line duotone with a shoulder. The embossed groove is a
    different material from the land, and the roll of the shoulder gets a third."""
    P = _P("wrap_truchet_knurl")
    line, flip = _truchet(shape, seed, P)
    k = float(P["depth"])
    mod = _norm((1.0 - k * line) + np.roll(line, 2, 0) * float(P["sheen"]))
    M = np.clip(30.0 + 96.0 * (1.0 - mod) * sm, 0, 255)
    R = np.clip(52.0 + 92.0 * (1.0 - mod), 15, 255)
    CC = np.clip(22.0 + 40.0 * (1.0 - mod), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 21 · CRAZE NET ══
def _craze(shape, seed, P):
    """Solvent crazing: the EDGE network of a cell field, with no cell shading at all.

    Deliberately the opposite use of a cellular field from a platelet finish: there
    the cell interiors carry the look, here only the seams between them do.
    """
    h, w = shape[:2]

    def build():
        cell = float(P["cell_px"])
        rng = np.random.default_rng((int(seed) ^ 0x51C3) & 0xFFFFFFFF)
        gh, gw = max(2, int(round(h / cell))), max(2, int(round(w / cell)))
        jy = rng.random((gh, gw), dtype=np.float32)
        jx = rng.random((gh, gw), dtype=np.float32)
        yy = np.arange(h, dtype=np.float32)[:, None] / np.float32(cell)
        xx = np.arange(w, dtype=np.float32)[None, :] / np.float32(cell)
        cy = np.floor(yy).astype(np.int32)
        cx = np.floor(xx).astype(np.int32)
        best = np.full((h, w), 1e9, np.float32)
        second = np.full((h, w), 1e9, np.float32)
        for ddy in (-1, 0, 1):
            for ddx in (-1, 0, 1):
                iy, ix = (cy + ddy) % gh, (cx + ddx) % gw
                sy = np.floor(yy) + ddy + jy[iy, ix]
                sx = np.floor(xx) + ddx + jx[iy, ix]
                d = (yy - sy) ** 2 + (xx - sx) ** 2
                closer = d < best
                second = np.where(closer, best, np.minimum(second, d))
                best = np.where(closer, d, best)
        seam = np.sqrt(second) - np.sqrt(best)
        crack = np.clip(1.0 - seam / float(P["width"]), 0, 1)
        return (crack ** 1.5).astype(np.float32)

    return _cache(("crz", h, w, int(seed), _k(P)), build)


def paint_wrap_craze_net(paint, shape, mask, seed, pm, bb):
    """Solvent craze: a hairline crack network opened in the clear over the print."""
    P = _P("wrap_craze_net")
    src = _incoming(paint, shape)
    c = _craze(shape, seed, P)
    k = float(P["depth"])
    out = src * (1.0 - k * c[:, :, None] * float(pm))
    out = out + np.clip(c - np.roll(c, 2, 1), 0, 1)[:, :, None] * float(P["glint"])
    return _finish(out, src, mask)


def spec_wrap_craze_net(shape, seed, sm, base_m, base_r):
    """GRAMMAR: distance-from-crack ladder. Materials step OUTWARD from the crack in
    discrete rings — the clear has lifted furthest at the crack and settles back to
    intact film, and the steps make that legible instead of smearing it."""
    P = _P("wrap_craze_net")
    c = _craze(shape, seed, P)
    step = _ladder(c, 6, 0.0, 1.0)
    M = np.clip(22.0 + 44.0 * step * sm, 0, 255)
    R = np.clip(34.0 + 140.0 * step, 15, 255)            # a crack is raw and dull
    CC = np.clip(16.0 + 96.0 * step, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 22 · LENS ARRAY ══
def _lens(shape, seed, P):
    """Optically-clear lens film: each dimple REFRACTS, so the artwork under it is
    displaced rather than merely shaded.

    This is the only finish on the shelf that moves the painter's pixels instead of
    scaling them, which is what a lens physically does.
    """
    h, w = shape[:2]

    def build():
        py, px = _px(shape)
        t = float(P["pitch"])
        fu = px / t - np.floor(px / t) - 0.5
        fv = py / t - np.floor(py / t) - 0.5
        r2 = (fu * fu + fv * fv) * 4.0
        inside = np.clip(1.0 - r2, 0, 1)
        # displacement grows toward the rim of each lens, like a real plano-convex cap
        k = float(P["power"]) * t
        dx = (fu * 2.0) * inside * k
        dy = (fv * 2.0) * inside * k
        yi = np.clip((py + dy).astype(np.int32), 0, h - 1)
        xi = np.clip((px + dx).astype(np.int32), 0, w - 1)
        rim = np.clip((r2 - 0.55) * 3.0, 0, 1) * (r2 < 1.05)
        return yi, xi, inside.astype(np.float32), rim.astype(np.float32)

    return _cache(("lns", h, w, int(seed), _k(P)), build)


def paint_wrap_lens_array(paint, shape, mask, seed, pm, bb):
    """Lens film: a dimple array that bends the artwork underneath it."""
    P = _P("wrap_lens_array")
    src = _incoming(paint, shape)
    yi, xi, inside, rim = _lens(shape, seed, P)
    bent = np.dstack([src[:, :, c][yi, xi] for c in range(3)])
    out = bent * (0.86 + 0.34 * inside[:, :, None] * float(pm))
    out = out * (1.0 - float(P["rimdark"]) * rim[:, :, None]) + inside[:, :, None] * 0.10
    return _finish(out, src, mask)


def spec_wrap_lens_array(shape, seed, sm, base_m, base_r):
    """GRAMMAR: three-material optic — a polished cap, a dark rim where the curve turns
    away, and flat land between. Hard boundaries, no grain, which is what an optical
    surface actually looks like."""
    P = _P("wrap_lens_array")
    yi, xi, inside, rim = _lens(shape, seed, P)
    cap = (inside > 0.15).astype(np.float32)
    M = np.clip(18.0 + 74.0 * inside * sm + 30.0 * cap, 0, 255)
    R = np.clip(96.0 - 74.0 * inside + 84.0 * rim, 15, 255)
    CC = np.clip(20.0 + 60.0 * rim + 18.0 * (1.0 - cap), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 23 · FLOW LINE ══
def _flowlines(shape, seed, P):
    """Line-integral convolution: a fine field smeared ALONG a curl field, so the
    streaks bend with the surface instead of running straight.

    Squeegee streaks along X and brushed film along Y are both straight by
    construction; this one has no single direction anywhere on the panel.
    """
    h, w = shape[:2]

    def build():
        pot = _box(_mid(shape, float(P["flow_px"]), seed + 5, octaves=2), 3)
        gy, gx = np.gradient(pot)
        # rotate the gradient 90 degrees -> a divergence-free (curl) field
        vx, vy = -gy, gx
        mag = np.sqrt(vx * vx + vy * vy) + 1e-6
        vx = (vx / mag) * float(P["step"])
        vy = (vy / mag) * float(P["step"])
        fine = _mid(shape, float(P["grain_px"]), seed + 7, octaves=1)
        py, px = _px(shape)
        acc = fine.copy()
        n = 1.0
        for k in (1.0, 2.0, 3.0, -1.0, -2.0, -3.0):     # 6 taps, both directions
            yi = np.clip((py + vy * k).astype(np.int32), 0, h - 1)
            xi = np.clip((px + vx * k).astype(np.int32), 0, w - 1)
            acc = acc + fine[yi, xi]
            n += 1.0
        lic = _norm(acc / n)
        return lic, _norm(mag)

    return _cache(("flw", h, w, int(seed), _k(P)), build)


def paint_wrap_flow_wrapline(paint, shape, mask, seed, pm, bb):
    """Flow lines: film relaxed along the curve of a panel, so the grain follows it."""
    P = _P("wrap_flow_wrapline")
    src = _incoming(paint, shape)
    lic, mag = _flowlines(shape, seed, P)
    k = float(P["gain"])
    out = src * (1.0 - 0.5 * k + k * lic[:, :, None] * float(pm))
    return _finish(out, src, mask)


def spec_wrap_flow_wrapline(shape, seed, sm, base_m, base_r):
    """GRAMMAR: streamline anisotropy on a speed ladder. Roughness follows the grain,
    and the SPEED of the flow is quantised so fast and slow regions of the panel deal
    visibly different materials."""
    P = _P("wrap_flow_wrapline")
    lic, mag = _flowlines(shape, seed, P)
    k = float(P["gain"])
    mod = _norm(1.0 - 0.5 * k + k * lic)
    M = np.clip(40.0 + 88.0 * mod * sm, 0, 255)
    R = np.clip(120.0 - 84.0 * mod + _ladder(mag, 5, 0.0, 34.0), 15, 255)
    CC = np.clip(24.0 + 30.0 * (1.0 - mod), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 24 · SPIRAL BURNISH ══
def _swirl(shape, seed, P):
    """Rotary polisher holograms: LOGARITHMIC spiral scratch trails.

    Roll memory is a chirp in a straight line; this is a chirp in POLAR space, which
    is a different curve family and reads completely differently on a body panel.
    """
    h, w = shape[:2]

    def build():
        py, px = _px(shape)
        acc = np.zeros((h, w), np.float32)
        rng = np.random.default_rng((int(seed) ^ 0x3F19) & 0xFFFFFFFF)
        for i in range(int(P["heads"])):
            cy = rng.uniform(0.1, 0.9) * h
            cx = rng.uniform(0.1, 0.9) * w
            dy, dx = py - cy, px - cx
            r = np.sqrt(dy * dy + dx * dx) + 1.0
            th = np.arctan2(dy, dx)
            phase = float(P["turns"]) * np.log(r) + th
            acc += np.sin(phase * float(P["density"])) / (1.0 + r / (min(h, w) * 0.5))
        return _norm(acc)

    return _cache(("swl", h, w, int(seed), _k(P)), build)


def paint_wrap_spiral_burnish(paint, shape, mask, seed, pm, bb):
    """Swirl marks: the rotary trails a polisher leaves in a clear coat."""
    P = _P("wrap_spiral_burnish")
    src = _incoming(paint, shape)
    s = _swirl(shape, seed, P)
    k = float(P["gain"])
    out = src * (1.0 - 0.5 * k + k * s[:, :, None] * float(pm))
    return _finish(out, src, mask)


def spec_wrap_spiral_burnish(shape, seed, sm, base_m, base_r):
    """GRAMMAR: phase-quantised polar ladder. The swirl phase is stepped, so the panel
    deals a fixed set of materials that spiral through one another — the look a
    polisher actually leaves under a low sun."""
    P = _P("wrap_spiral_burnish")
    s = _swirl(shape, seed, P)
    step = _ladder(s, 7, 0.0, 1.0)
    M = np.clip(50.0 + 120.0 * step * sm, 0, 255)
    R = np.clip(70.0 - 48.0 * step, 15, 255)
    CC = np.clip(26.0 + 26.0 * (1.0 - step), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 25 · OVERLAP GHOST ══
def _overlaps(shape, seed, P):
    """Three sets of narrow translucent bands at different angles. Where sheets lap,
    density MULTIPLIES, so the panel resolves into discrete density plateaus.

    The count of overlapping layers is an integer field — a different object from
    every continuous field on this shelf.
    """
    h, w = shape[:2]

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x64D2) & 0xFFFFFFFF)
        py, px = _warp(shape, seed + 90, 14.0, 240.0)
        count = np.zeros((h, w), np.float32)
        edge = np.zeros((h, w), np.float32)
        for i in range(3):
            th = rng.uniform(0.0, np.pi)
            u = (px * np.cos(th) + py * np.sin(th)) / float(P["band_px"])
            f = u - np.floor(u)
            band = (f < float(P["duty"])).astype(np.float32)
            count += band
            edge = np.maximum(edge, np.clip(1.0 - np.abs(f - float(P["duty"])) * 26.0, 0, 1))
        return count / 3.0, edge.astype(np.float32)

    return _cache(("ovl", h, w, int(seed), _k(P)), build)


def paint_wrap_overlap_ghost(paint, shape, mask, seed, pm, bb):
    """Ghost overlaps: translucent sheets lapping, each crossing darkening the print again."""
    P = _P("wrap_overlap_ghost")
    src = _incoming(paint, shape)
    count, edge = _overlaps(shape, seed, P)
    k = float(P["density"])
    out = src * (1.0 - k * count[:, :, None] * float(pm))
    out = out + edge[:, :, None] * float(P["lip"]) * float(pm)
    return _finish(out, src, mask)


def spec_wrap_overlap_ghost(shape, seed, sm, base_m, base_r):
    """GRAMMAR: layer-count ladder. Clearcoat depth steps once per sheet of overlap —
    the only spec here whose levels are literally a COUNT rather than a measurement."""
    P = _P("wrap_overlap_ghost")
    count, edge = _overlaps(shape, seed, P)
    k = float(P["density"])
    mod = _norm(1.0 - k * count + edge * float(P["lip"]))
    M = np.clip(28.0 + 52.0 * mod * sm, 0, 255)
    R = np.clip(60.0 + 74.0 * (1.0 - mod), 15, 255)
    CC = np.clip(20.0 + _ladder(count, 4, 0.0, 120.0), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════════════ CATALOG ══
CATALOG = {
    "wrap_panel_seam":     {"M": 30,  "R": 60, "CC": 26,
                            "desc": "Panel Seam — overlapping wrap sheets with a knifed edge and a proud lap ridge"},
    "wrap_squeegee":       {"M": 45,  "R": 58, "CC": 30,
                            "desc": "Squeegee Sweep — directional blade burnish in overlapping installer strokes"},
    "wrap_microbubble":    {"M": 32,  "R": 45, "CC": 28,
                            "desc": "Micro-Bubble — trapped air pooling into lit domes under the film"},
    "wrap_laminate":       {"M": 28,  "R": 32, "CC": 18,
                            "desc": "Laminate Gloss — clear laminate over a four-angle CMYK print rosette"},
    "wrap_brushed_film":   {"M": 170, "R": 70, "CC": 40,
                            "desc": "Brushed Film — metallised vinyl with the mill grain rolled into the sheet"},
    "wrap_print_band":     {"M": 32,  "R": 70, "CC": 30,
                            "desc": "Print Banding — inkjet head passes laying each ink at its own density"},
    "wrap_perf_window":    {"M": 40,  "R": 90, "CC": 60,
                            "desc": "Perf Window — one-way vision film punched through on a regular lattice"},
    "wrap_knife_edge":     {"M": 36,  "R": 56, "CC": 30,
                            "desc": "Knife Edge — knifeless-tape design cuts, each facet its own piece of film"},
    "wrap_air_release":    {"M": 34,  "R": 54, "CC": 34,
                            "desc": "Air Release — the moulded egress channels embossed into cast film"},
    "wrap_heat_gun":       {"M": 34,  "R": 74, "CC": 42,
                            "desc": "Heat Gun — where the gun dwelled the print softens and the film glazes"},
    "wrap_lift_curl":      {"M": 44,  "R": 60, "CC": 32,
                            "desc": "Lift Curl — an edge letting go, throwing a shadow back across the panel"},
    "wrap_holographic":    {"M": 190, "R": 34, "CC": 16,
                            "desc": "Holographic — a ruled grating splitting light into ordered spectra"},
    "wrap_wet_apply":      {"M": 26,  "R": 96, "CC": 56,
                            "desc": "Wet Apply — slip solution that dried into rings before it was worked out"},
    "wrap_layered_cut":    {"M": 38,  "R": 58, "CC": 46,
                            "desc": "Layered Cut — stacked cut vinyl, clearcoat deepening with every sheet"},
    "wrap_creases":        {"M": 40,  "R": 66, "CC": 32,
                            "desc": "Creases — a network of hard folds burnished glossy through the print"},
    "wrap_roll_memory":    {"M": 36,  "R": 62, "CC": 30,
                            "desc": "Roll Memory — waviness that tightens toward the core end of the roll"},
    "wrap_ceramic_coat":   {"M": 26,  "R": 28, "CC": 18,
                            "desc": "Ceramic Coat — a poured-glass coating, beading only where it lifts"},
    "wrap_hex_ppf":        {"M": 44,  "R": 40, "CC": 24,
                            "desc": "Hex PPF — self-healing protection film, its cell structure caught at angle"},
    "wrap_twill_film":     {"M": 100, "R": 74, "CC": 40,
                            "desc": "Twill Film — textured weave vinyl, threads floating over and under"},
    "wrap_truchet_knurl":  {"M": 60,  "R": 92, "CC": 34,
                            "desc": "Truchet Knurl — an embossed maze of arcs rolled tile to tile into the sheet"},
    "wrap_craze_net":      {"M": 30,  "R": 88, "CC": 52,
                            "desc": "Craze Net — a hairline crack network opened in the clear over the print"},
    "wrap_lens_array":     {"M": 46,  "R": 66, "CC": 38,
                            "desc": "Lens Array — a dimple film that bends the artwork underneath it"},
    "wrap_flow_wrapline":  {"M": 74,  "R": 80, "CC": 34,
                            "desc": "Flow Line — grain that follows the curve of the panel it was laid on"},
    "wrap_spiral_burnish": {"M": 96,  "R": 50, "CC": 32,
                            "desc": "Spiral Burnish — rotary swirl trails left in the clear by a polisher"},
    "wrap_overlap_ghost":  {"M": 48,  "R": 84, "CC": 60,
                            "desc": "Overlap Ghost — translucent sheets lapping, each crossing darkening again"},
}
WRAP_SHOP = CATALOG          # back-compat alias

# ─────────────────────────────────────────────────── variant search space ──
# Ranges are the knobs that MATERIALLY change each look. Index 0 of every space is
# its midpoint, so the search can only improve on the hand-authored default.
SPACE = {
    "wrap_panel_seam":     {"panel_px": (60.0, 140.0), "seam_px": (2.5, 7.0), "tone": (0.30, 0.62)},
    "wrap_squeegee":       {"len_div": (8.0, 20.0), "step_px": (10.0, 30.0), "mix": (0.35, 0.75),
                            "gain": (1.00, 1.70), "floor": (0.22, 0.48)},
    "wrap_microbubble":    {"density": (0.00700, 0.02200), "rad": (2.0, 4.5),
                            "pool": (2.0, 4.5), "lift": (0.55, 1.00)},
    "wrap_laminate":       {"pitch": (9.0, 24.0), "spread": (0.85, 1.15), "peel_px": (6.0, 16.0),
                            "dotc": (0.55, 1.05)},
    "wrap_brushed_film":   {"len_div": (4.0, 10.0), "rib_px": (4.0, 12.0), "mix": (0.24, 0.52),
                            "gain": (1.10, 1.70)},
    "wrap_print_band":     {"pass_px": (14.0, 38.0), "err": (0.45, 0.90), "chroma": (0.10, 0.35),
                            "amp": (0.06, 0.15), "dot": (0.55, 0.85)},
    "wrap_perf_window":    {"pitch": (10.0, 20.0), "fill": (0.26, 0.40), "drift": (1.2, 4.0)},
    "wrap_knife_edge":     {"cuts": [14, 20, 26], "cut_px": (2.0, 5.0), "tone": (0.62, 1.15)},
    "wrap_air_release":    {"pitch": (11.0, 26.0), "angle": (20.0, 70.0), "width": (0.18, 0.45),
                            "depth": (0.24, 0.46)},
    "wrap_heat_gun":       {"dwell_px": (26.0, 80.0), "max_r": (2.0, 7.0), "glaze": (0.20, 0.46),
                            "halo": (120.0, 600.0)},
    "wrap_lift_curl":      {"region_px": (26.0, 80.0), "curl_px": (3.0, 9.0), "tight": (2.2, 6.0)},
    "wrap_holographic":    {"dom_px": (40.0, 130.0), "facets": [6, 8, 12, 16], "period": (8.0, 20.0),
                            "bright": (0.20, 0.60), "sat": (0.12, 0.40), "depth": (0.30, 0.62)},
    "wrap_wet_apply":      {"pools": [22, 30, 38], "size": (0.035, 0.10), "ring_px": (1.5, 3.2),
                            "haze": (1.40, 2.60), "dep": (1.00, 2.00)},
    "wrap_layered_cut":    {"layers": [3, 4, 5, 6], "size_px": (46.0, 130.0)},
    "wrap_creases":        {"fold_px": (34.0, 110.0), "sharp": (0.06, 0.20), "depth": (0.45, 0.85)},
    "wrap_roll_memory":    {"f0": (0.5, 2.0), "f1": (3.0, 9.0), "amp": (0.30, 0.70),
                            "drift": (0.4, 1.6)},
    "wrap_ceramic_coat":   {"dom_px": (90.0, 260.0), "thresh": (0.46, 0.60), "bead": (0.35, 1.30),
                            "peel_px": (16.0, 40.0), "depth": (0.30, 1.15)},
    "wrap_hex_ppf":        {"cell_px": (14.0, 30.0), "wall": (0.10, 0.30), "depth": (0.35, 1.05),
                            "sheen": (0.10, 0.34)},
    "wrap_twill_film":     {"thread_px": (7.0, 16.0), "relief": (0.50, 1.30)},
    "wrap_truchet_knurl":  {"tile_px": (14.0, 32.0), "width": (0.10, 0.26), "depth": (0.35, 0.95),
                            "sheen": (0.12, 0.40)},
    "wrap_craze_net":      {"cell_px": (16.0, 34.0), "width": (0.06, 0.20), "depth": (0.40, 1.10),
                            "glint": (0.10, 0.40)},
    "wrap_lens_array":     {"pitch": (11.0, 26.0), "power": (0.06, 0.20), "rimdark": (0.30, 0.80)},
    "wrap_flow_wrapline":  {"flow_px": (60.0, 200.0), "grain_px": (2.0, 5.0), "step": (1.2, 3.4),
                            "gain": (0.60, 1.50)},
    "wrap_spiral_burnish": {"heads": [3, 5, 8], "turns": (6.0, 22.0), "density": (14.0, 44.0),
                            "gain": (0.50, 1.30)},
    "wrap_overlap_ghost":  {"band_px": (13.0, 30.0), "duty": (0.34, 0.62), "density": (0.20, 0.55),
                            "lip": (0.10, 0.34)},
}

_CHOSEN = chooser(__name__, SPACE)


def install(registry):
    """Wire WRAP SHOP into a BASE_REGISTRY. Returns the number of finishes installed."""
    import sys as _sys
    me = _sys.modules[__name__]
    n = 0
    for fid, meta in CATALOG.items():
        entry = registry.setdefault(fid, {})
        entry.update(meta)
        entry["paint_fn"] = getattr(me, "paint_" + fid)
        entry["base_spec_fn"] = getattr(me, "spec_" + fid)
        n += 1
    return n
