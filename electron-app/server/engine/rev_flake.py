"""[SPB-REV-FLAKE 2026-10-10] Flake Studio engine: metallic flake + pearl designed for iRacing's mip distance (lane REV-FLAKE).

WHY: real metallic / pearl paint is flake. In iRacing a flake drawn too fine averages to flat grey once the texture mips at distance; drawn too
coarse it looks like glitter. This module draws flake from physical parameters (size in canvas px from the car's cm scale, density, sparkle,
flake colour, pearl colour, base metal / roughness / clearcoat) and measures how much of it survives each mip level.

ONE optional zone field, ``spb_flake`` (plain JSON, see ``norm``), read by ONE hook in ``build_multi_zone`` after the zone's own spec
material steps and before the zone cache store. Every server zone dict goes through that loop, so a zone (finish override that keeps the
zone's colour), a Brush Studio coat zone and a layer-material coat zone all render the flake through the SAME code, in the live preview and
in RENDER. The field name does not start with ``_spb_``, so it is part of the zone cache key (a changed flake never replays a stale zone).

Flakes are a Voronoi mosaic of jittered seeds, one per cell of ``size_px`` canvas px, hashed from the cell's integer canvas coordinates:
any crop at any resolution computes the same flake (the preview endpoint renders a crop, the engine the whole zone box; a 1024 preview
computes at canvas resolution and box-filters down, exactly what the sim's first mip does).

Spec per flake: M = base_m + is_flake * (flake_m - base_m) * (1 - 0.5 * sparkle * (1 - face)),  G = base_r + is_flake * (flake_r - base_r
+ 80 * sparkle * (1 - face)), CC = cc (uniform). ``face`` = u^3 (few flakes face the light, most are edge-on). Paint keeps the zone colour P:
P' = P * A + flake_rgb * Bf + pearl_rgb * Bp (per-flake brightness, flake colour, pearl colour-shift weighted by a per-flake tone).
Iron rules: CC >= 16, G >= 15 everywhere this module writes.

Sim-safe: a coarse flake band (``coarse_px``) mixed with the fine one (``coarse_mix``); the mix is FITTED by ``fit_sim_safe`` against the
owner-verdict bar (``_easy_claude_work/rev_tools/flake/fit.json``) and stored in the params, so the render never re-fits.

Kill switch: env ``SPB_FLAKE_OFF=1`` -> ``apply_zone_flake`` returns its inputs untouched (byte-identical render).
"""
import math
import os

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

VERSION = "flake-1.0"
CC_FLOOR = 16
ROUGH_FLOOR = 15

# Fitted bars (owner verdicts on the 256 px Spec Sculpt thumbnails, _easy_claude_work/rev_tools/flake/fit_verdicts.py -> fit.json, 2026-10-10):
#   S_FLAT_BAR: texel-to-texel spec signal (mean of M,R std(x - box3x3 x), levels) separating 'flat' verdicts from keeps: 4.30 (15/18 agree, not separated)
#   L_BIG_BAR : flake correlation length separating 'big' (glitter) verdicts from keeps: 2.74 px of a 256 px sheet = 1.07% of the sheet width (22/24 agree)
S_FLAT_BAR = 4.30
L_BIG_FRAC = 2.74 / 256.0


def disabled():
    return str(os.environ.get("SPB_FLAKE_OFF", "")).strip().lower() in ("1", "true", "yes", "on")


def _f(v, d, lo, hi):
    try:
        x = float(v)
        if not math.isfinite(x):
            return d
        return max(lo, min(hi, x))
    except Exception:
        return d


def _rgb(v):
    if not isinstance(v, (list, tuple)) or len(v) < 3:
        return None
    try:
        return [max(0.0, min(255.0, float(c))) for c in v[:3]]
    except Exception:
        return None


def norm(raw):
    """Clamp the JSON params; None = not a flake field."""
    if not isinstance(raw, dict):
        return None
    cw = raw.get("canvas") if isinstance(raw.get("canvas"), (list, tuple)) and len(raw.get("canvas")) >= 2 else [2048, 2048]
    p = {
        "canvas": [int(_f(cw[0], 2048, 64, 8192)), int(_f(cw[1], 2048, 64, 8192))],
        "size_px": _f(raw.get("size_px"), 2.0, 0.5, 64.0),
        "density": _f(raw.get("density"), 0.6, 0.0, 1.0),
        "sparkle": _f(raw.get("sparkle"), 0.6, 0.0, 1.0),
        "base_m": _f(raw.get("base_m"), 120.0, 0.0, 255.0),
        "base_r": _f(raw.get("base_r"), 60.0, 0.0, 255.0),
        "flake_m": _f(raw.get("flake_m"), 235.0, 0.0, 255.0),
        "flake_r": _f(raw.get("flake_r"), 20.0, 0.0, 255.0),
        "cc": _f(raw.get("cc"), 16.0, 16.0, 255.0),
        "flake_rgb": _rgb(raw.get("flake_rgb")),
        "flake_mix": _f(raw.get("flake_mix"), 0.0, 0.0, 1.0),
        "pearl_rgb": _rgb(raw.get("pearl_rgb")),
        "pearl_mix": _f(raw.get("pearl_mix"), 0.0, 0.0, 1.0),
        "bright": _f(raw.get("bright"), 0.30, 0.0, 1.0),
        "sim_safe": bool(raw.get("sim_safe")),
        "coarse_px": _f(raw.get("coarse_px"), 6.0, 2.0, 64.0),
        "coarse_mix": _f(raw.get("coarse_mix"), 0.0, 0.0, 1.0),
        "seed": int(_f(raw.get("seed"), 7, 0, 2 ** 31 - 1)),
    }
    return p


# ------------------------------------------------------------------------------------------------ hashing (uint32, wraps)
_M1, _M2, _M3, _M4 = np.uint32(0x8DA6B343), np.uint32(0xD8163841), np.uint32(0x7FEB352D), np.uint32(0x846CA68B)


def _mix(h):
    h = h ^ (h >> np.uint32(16))
    h = h * _M3
    h = h ^ (h >> np.uint32(15))
    h = h * _M4
    h = h ^ (h >> np.uint32(16))
    return h


def _hash(a, b, seed):
    with np.errstate(over="ignore"):
        h = (np.asarray(a).astype(np.int64).astype(np.uint32) * _M1) ^ (np.asarray(b).astype(np.int64).astype(np.uint32) * _M2) ^ np.uint32(seed & 0xFFFFFFFF)
        return _mix(h)


def _u(h, salt):
    with np.errstate(over="ignore"):
        return (_mix(h ^ np.uint32((salt * 0x9E3779B1) & 0xFFFFFFFF)) >> np.uint32(8)).astype(np.float32) * np.float32(1.0 / 16777216.0)


# ------------------------------------------------------------------------------------------------ one flake layer
def _layer(X0, Y0, X1, Y1, s, density, seed):
    """Per-pixel flake attributes on the canvas box [X0,X1) x [Y0,Y1): (is_flake, face, tone) float32 HxW."""
    H, W = Y1 - Y0, X1 - X0
    if s < 1.6:   # sub-2px flakes: one flake per pixel (a Voronoi of 1 px cells is the pixel grid)
        ys, xs = np.mgrid[Y0:Y1, X0:X1]
        h = _hash(xs, ys, seed)
        return ((_u(h, 1) < density).astype(np.float32), _u(h, 2) ** 3, _u(h, 3))
    halo = int(math.ceil(3.0 * s)) + 2
    BX0, BY0, BX1, BY1 = X0 - halo, Y0 - halo, X1 + halo, Y1 + halo
    i0, i1 = int(math.floor(BX0 / s)) - 1, int(math.floor(BX1 / s)) + 1
    j0, j1 = int(math.floor(BY0 / s)) - 1, int(math.floor(BY1 / s)) + 1
    jj, ii = np.mgrid[j0:j1 + 1, i0:i1 + 1]
    h = _hash(ii, jj, seed)
    px = np.floor((ii + 0.15 + 0.7 * _u(h, 11)) * s).astype(np.int64)
    py = np.floor((jj + 0.15 + 0.7 * _u(h, 12)) * s).astype(np.int64)
    ok = (px >= BX0) & (px < BX1) & (py >= BY0) & (py < BY1)
    px, py, h = px[ok] - BX0, py[ok] - BY0, h[ok]
    BH, BW = BY1 - BY0, BX1 - BX0
    img = np.ones((BH, BW), np.uint8)
    img[py, px] = 0
    a_img = np.zeros((3, BH, BW), np.float32)
    a_img[0][py, px] = (_u(h, 1) < density).astype(np.float32)
    a_img[1][py, px] = _u(h, 2) ** 3
    a_img[2][py, px] = _u(h, 3)
    _d, lab = cv2.distanceTransformWithLabels(img, cv2.DIST_L2, cv2.DIST_MASK_PRECISE, labelType=cv2.DIST_LABEL_PIXEL)
    zy, zx = np.nonzero(img == 0)   # label k (1-based) = k-th seed pixel in raster order
    lab = lab[halo:halo + H, halo:halo + W].astype(np.int64) - 1
    return tuple(a_img[k][zy, zx][lab] for k in range(3))


def _coeffs(p, isf, face, tone):
    """Linear fields: spec M, G (float levels) and paint P' = P*A + FL*Bf + PR*Bp."""
    sp = p["sparkle"]
    edge = 1.0 - face
    M = p["base_m"] + isf * (p["flake_m"] - p["base_m"]) * (1.0 - 0.5 * sp * edge)
    G = p["base_r"] + isf * ((p["flake_r"] - p["base_r"]) + 80.0 * sp * edge)
    a1 = 1.0 + isf * (p["bright"] * sp * (face - 0.25) * 2.0)
    fm = isf * (p["flake_mix"] if p["flake_rgb"] is not None else 0.0)
    pm = isf * (p["pearl_mix"] if p["pearl_rgb"] is not None else 0.0) * tone
    A = a1 * (1.0 - fm) * (1.0 - pm)
    Bf = fm * (1.0 - pm)
    Bp = pm
    return [M.astype(np.float32), G.astype(np.float32), A.astype(np.float32), Bf.astype(np.float32), Bp.astype(np.float32)]


def fields(p, X0, Y0, X1, Y1, coarse_mix=None):
    """[M, G, A, Bf, Bp] at CANVAS resolution on the box. coarse_mix overrides p['coarse_mix'] (fit uses it)."""
    fine = _coeffs(p, *_layer(X0, Y0, X1, Y1, p["size_px"], p["density"], p["seed"]))
    w = p["coarse_mix"] if coarse_mix is None else coarse_mix
    if not p["sim_safe"] or w <= 0:
        return fine
    coarse = _coeffs(p, *_layer(X0, Y0, X1, Y1, p["coarse_px"], p["density"], p["seed"] + 7919))
    return [f * (1.0 - w) + c * w for f, c in zip(fine, coarse)]


def _down(a, w, h):
    if a.shape[1] == w and a.shape[0] == h:
        return a
    return cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA)


def render_box(p, x0, y0, x1, y1, rw, rh):
    """Fields for the RENDER-resolution box [x0,x1)x[y0,y1) of an rw x rh render of the p['canvas'] sheet.
    Computed at canvas resolution and box-filtered down when the render is smaller (the live preview)."""
    CW, CH = p["canvas"]
    fx, fy = CW / float(rw), CH / float(rh)
    if abs(fx - 1.0) < 1e-6 and abs(fy - 1.0) < 1e-6:
        return fields(p, x0, y0, x1, y1)
    X0, Y0 = int(math.floor(x0 * fx)), int(math.floor(y0 * fy))
    X1, Y1 = int(math.ceil(x1 * fx)), int(math.ceil(y1 * fy))
    return [_down(a, x1 - x0, y1 - y0) for a in fields(p, X0, Y0, X1, Y1)]


def compose(p, flds, P):
    """P float 0..1 HxWx3 (the zone's own colour) -> (paint float 0..1, spec float M,G,CC)."""
    M, G, A, Bf, Bp = flds
    out = P[..., :3] * A[..., None]
    if p["flake_rgb"] is not None:
        out = out + (np.asarray(p["flake_rgb"], np.float32) / 255.0)[None, None, :] * Bf[..., None]
    if p["pearl_rgb"] is not None:
        out = out + (np.asarray(p["pearl_rgb"], np.float32) / 255.0)[None, None, :] * Bp[..., None]
    out = np.clip(out, 0.0, 1.0)
    Mq = np.clip(M, 0, 255)
    Gq = np.clip(G, ROUGH_FLOOR, 255)
    Cq = np.full_like(Mq, max(float(CC_FLOOR), p["cc"]))
    return out, Mq, Gq, Cq


_POOL = None


def _pool():
    global _POOL
    if _POOL is None:
        from concurrent.futures import ThreadPoolExecutor
        _POOL = ThreadPoolExecutor(max_workers=max(1, min(8, (os.cpu_count() or 2))), thread_name_prefix="rev_flake")
    return _POOL


def _strip_rows(y0, y1, fy):
    """Row ranges for the strip-parallel apply. Strips start on multiples of the integer down-factor so INTER_AREA of a strip ==
    the same rows of INTER_AREA of the whole box. Non-integer factors (never used by the app: 1.0 render, 0.5 preview) = one strip."""
    k = int(round(fy))
    if abs(fy - k) > 1e-6 or k < 1:
        return [(y0, y1)]
    n = max(1, min(16, (y1 - y0) // 96))
    if n == 1:
        return [(y0, y1)]
    step = int(math.ceil((y1 - y0) / float(n)))
    step = max(k, step - (step % k))
    out, a = [], y0
    while a < y1:
        b = min(y1, a + step)
        out.append((a, b)); a = b
    return out


def _apply_rows(p, zone_spec, paint, m, x0, x1, ya, yb, rw, rh):
    flds = render_box(p, x0, ya, x1, yb, rw, rh)
    P = np.asarray(paint[ya:yb, x0:x1, :3], np.float32)
    newP, M, G, C = compose(p, flds, P)
    mb = m[ya:yb, x0:x1]
    inside = mb > 0.0
    zs = zone_spec[ya:yb, x0:x1]
    for ch, v in ((0, M), (1, G), (2, C)):
        np.copyto(zs[..., ch], np.clip(np.rint(v), 0, 255).astype(np.uint8), where=inside)
    pb = paint[ya:yb, x0:x1, :3]
    mm = mb[..., None]
    blended = P * (1.0 - mm) + newP * mm
    np.copyto(pb, blended.astype(pb.dtype, copy=False), where=inside[..., None])


def apply_zone_flake(zone_spec, paint, zone_mask, raw, name="zone"):
    """The build_multi_zone hook. zone_spec uint8 HxWx4, paint float HxWx(3|4) 0..1, zone_mask float HxW. Returns (zone_spec, paint)."""
    if disabled() or cv2 is None:
        return zone_spec, paint
    p = norm(raw)
    if p is None or zone_spec is None or paint is None or zone_mask is None:
        return zone_spec, paint
    m = np.asarray(zone_mask, np.float32)
    if m.ndim == 3:
        m = m[..., 0]
    rh, rw = m.shape[:2]
    nz = m > 0.0
    rows = np.flatnonzero(nz.any(axis=1))
    if rows.size == 0:
        return zone_spec, paint
    import time as _t
    t0 = _t.time()
    cols = np.flatnonzero(nz.any(axis=0))
    y0, y1, x0, x1 = int(rows[0]), int(rows[-1]) + 1, int(cols[0]), int(cols[-1]) + 1
    strips = _strip_rows(y0, y1, p["canvas"][1] / float(rh))
    if len(strips) == 1:
        _apply_rows(p, zone_spec, paint, m, x0, x1, y0, y1, rw, rh)
    else:
        futs = [_pool().submit(_apply_rows, p, zone_spec, paint, m, x0, x1, ya, yb, rw, rh) for ya, yb in strips]
        for f in futs:
            f.result()
    print("    [%s] FLAKE STUDIO %s size %.2fpx dens %.2f sparkle %.2f%s box %dx%d @%dx%d in %.2fs (%d strips)" % (
        name, VERSION, p["size_px"], p["density"], p["sparkle"],
        (" sim-safe coarse %.1fpx mix %.2f" % (p["coarse_px"], p["coarse_mix"])) if p["sim_safe"] and p["coarse_mix"] > 0 else "",
        x1 - x0, y1 - y0, rw, rh, _t.time() - t0, len(strips)))
    return zone_spec, paint


# ------------------------------------------------------------------------------------------------ measuring (the survival meter)
def mip_chain(a, n):
    """2x2 box-filter chain (what the sim's mips do), float32."""
    out = [np.asarray(a, np.float32)]
    for _ in range(n):
        x = out[-1]
        h, w = x.shape[:2]
        h2, w2 = h // 2, w // 2
        x = x[:h2 * 2, :w2 * 2]
        out.append(0.25 * (x[0::2, 0::2] + x[1::2, 0::2] + x[0::2, 1::2] + x[1::2, 1::2]))
    return out


def texel_signal(ch):
    x = np.asarray(ch, np.float32)
    if min(x.shape[:2]) < 4:
        return 0.0
    return float(np.std(x - cv2.blur(x, (3, 3), borderType=cv2.BORDER_REFLECT)))


def spec_signal(M, G):
    return 0.5 * (texel_signal(M) + texel_signal(G))


def corr_len(ch):
    """autocorrelation half-width (px) of the high-passed channel"""
    x = np.asarray(ch, np.float32)
    hp = x - cv2.GaussianBlur(x, (0, 0), 8)
    hp = hp - hp.mean()
    F = np.fft.rfft2(hp)
    ac = np.fft.irfft2(F * np.conj(F), s=hp.shape)
    ac = np.fft.fftshift(ac)
    if ac.max() <= 1e-9:
        return 0.0
    ac = ac / ac.max()
    h, w = ac.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - h // 2, xx - w // 2).astype(np.int32)
    prof = np.bincount(r.ravel(), ac.ravel()) / np.maximum(np.bincount(r.ravel()), 1)
    below = np.nonzero(prof < 0.5)[0]
    if not len(below):
        return float(len(prof))
    i = int(below[0])
    return float(i - 1 + (prof[i - 1] - 0.5) / max(prof[i - 1] - prof[i], 1e-9))


def meter(p, M, G, levels=4):
    """Survival per mip of the spec flake signal. M, G float at canvas resolution (8-bit rounded first, like the TGA)."""
    Mc, Gc = mip_chain(np.rint(M), levels), mip_chain(np.rint(G), levels)
    S = [spec_signal(a, b) for a, b in zip(Mc, Gc)]
    s0 = S[0] if S[0] > 1e-6 else 1.0
    return {"S": [round(v, 2) for v in S], "survive_pct": [round(100.0 * v / s0, 1) for v in S],
            "reads": ["flake" if v >= S_FLAT_BAR else "flat" for v in S], "bar": S_FLAT_BAR}


FIT_TILES = ((0, 0), (768, 256), (1280, 1024), (256, 1536))   # four 512 px tiles (canvas px) spread over the sheet
FIT_PATCH = 256                                               # every 256 px patch of each tile must read at the target mip


def _worst_patch_S(Ms, Gs, target_mip, patch):
    """min over all patch x patch sub-squares (at canvas res) of the spec texel signal at mip target_mip, 8-bit rounded first."""
    worst = None
    q = patch >> target_mip
    for M, G in zip(Ms, Gs):
        mM, mG = mip_chain(np.rint(M), target_mip)[-1], mip_chain(np.rint(G), target_mip)[-1]
        for y in range(0, mM.shape[0] - q + 1, q):
            for x in range(0, mM.shape[1] - q + 1, q):
                v = spec_signal(mM[y:y + q, x:x + q], mG[y:y + q, x:x + q])
                worst = v if worst is None or v < worst else worst
    return worst if worst is not None else 0.0


def fit_sim_safe(p, tile=512, sizes=(4, 5, 6, 8, 10, 12, 16, 20), target_mip=2):
    """Smallest coarse mix (and its coarse size) that keeps the spec flake signal at mip `target_mip` at or above the owner-fitted
    flat bar on EVERY 256 px patch of four 512 px tiles, with the coarse flakes under the owner-fitted glitter bar."""
    q = dict(p, sim_safe=True)
    CW, CH = p["canvas"]
    big_px = L_BIG_FRAC * CW
    tiles = [(min(x, max(0, CW - tile)), min(y, max(0, CH - tile))) for x, y in FIT_TILES]
    fine = [fields(dict(q, coarse_mix=0.0), x, y, x + tile, y + tile, coarse_mix=0.0) for x, y in tiles]
    fMs, fGs = [f[0] for f in fine], [f[1] for f in fine]
    base_S = _worst_patch_S(fMs, fGs, target_mip, FIT_PATCH)
    res = {"bar": S_FLAT_BAR, "mip": target_mip, "fine_S": round(base_S, 2), "big_px": round(big_px, 1), "tried": [],
           "rule": "worst %d px patch of %d tiles" % (FIT_PATCH, len(tiles))}
    if base_S >= S_FLAT_BAR:
        res.update(ok=True, coarse_px=p["coarse_px"], coarse_mix=0.0, S=round(base_S, 2), why="the fine flake already survives mip %d" % target_mip)
        return res
    best = None
    for c in sizes:
        if c > big_px:
            continue
        lay = [_coeffs(q, *_layer(x, y, x + tile, y + tile, float(c), q["density"], q["seed"] + 7919)) for x, y in tiles]
        hit = None
        for k in range(1, 21):
            w = k / 20.0
            if best is not None and w >= best[1] - 1e-9:
                break
            s_ = _worst_patch_S([f * (1 - w) + l[0] * w for f, l in zip(fMs, lay)], [g * (1 - w) + l[1] * w for g, l in zip(fGs, lay)], target_mip, FIT_PATCH)
            if s_ >= S_FLAT_BAR:
                hit = (w, s_)
                break
        res["tried"].append({"coarse_px": c, "mix": hit[0] if hit else None, "S": round(hit[1], 2) if hit else None})
        if hit and (best is None or hit[0] < best[1] - 1e-9):
            best = (c, hit[0], hit[1])
    if best is None:
        res.update(ok=False, coarse_px=p["coarse_px"], coarse_mix=0.0, S=None, why="no coarse size under the glitter bar reaches the flat bar")
        return res
    res.update(ok=True, coarse_px=float(best[0]), coarse_mix=best[1], S=round(best[2], 2), why="coarse %dpx at %d%% keeps every patch at mip %d >= %.2f (worst %.2f)" % (
        best[0], round(best[1] * 100), target_mip, S_FLAT_BAR, best[2]))
    return res
