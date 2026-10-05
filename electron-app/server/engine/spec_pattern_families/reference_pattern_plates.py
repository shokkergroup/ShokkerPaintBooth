"""Reference Pattern Plate SPEC overlays.

SPB owner 2026-05-30: same real source plates must also ship as SPEC overlay
patterns, prefixed with SPEC in the UI to avoid name collisions. The paired
M/R/CC plates are built by scripts/build_reference_pattern_plates.py.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from ..spec_patterns import _sm_scale, _validate_spec_output


_ROOT = Path(__file__).resolve().parents[2]
try:
    from engine.asset_packs import resolve_ref_dir as _rrd
except Exception:
    try:
        from ..asset_packs import resolve_ref_dir as _rrd
    except Exception:
        _rrd = lambda r: str(_ROOT / "assets" / "reference_textures" / r)  # noqa: E731
# finish-pack-downloader 2026-06-07: route through resolver so a DOWNLOADED pack works for buyers
_ASSET_DIR = Path(_rrd("pattern_plates"))
_RESIZE_CACHE: "OrderedDict[tuple, np.ndarray]" = OrderedDict()
_CACHE_MAX = 48


def _load_manifest() -> dict:
    path = _ASSET_DIR / "manifest.json"
    if not path.exists():
        return {"finishes": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"finishes": []}


_MANIFEST = _load_manifest()
_META_BY_SPEC = {
    str(item["spec_id"]): item
    for item in _MANIFEST.get("finishes", [])
    if item.get("spec_id") and item.get("spec")
}


def _shape2(shape) -> tuple[int, int]:
    return tuple(shape[:2]) if len(shape) > 2 else tuple(shape)


def _refresh_manifest() -> None:
    global _MANIFEST, _META_BY_SPEC
    _MANIFEST = _load_manifest()
    _META_BY_SPEC = {
        str(item["spec_id"]): item
        for item in _MANIFEST.get("finishes", [])
        if item.get("spec_id") and item.get("spec")
    }


def _cache_put(key: tuple, value: np.ndarray) -> np.ndarray:
    _RESIZE_CACHE[key] = value
    _RESIZE_CACHE.move_to_end(key)
    while len(_RESIZE_CACHE) > _CACHE_MAX:
        _RESIZE_CACHE.popitem(last=False)
    return value


@lru_cache(maxsize=48)
def _load_spec_cached(spec_id: str, mtime_ns: int) -> np.ndarray:
    del mtime_ns
    meta = _META_BY_SPEC.get(spec_id)
    if not meta:
        _refresh_manifest()
        meta = _META_BY_SPEC.get(spec_id)
    if not meta:
        raise KeyError(f"Unknown Reference Pattern Plate spec overlay: {spec_id}")
    path = _ASSET_DIR / str(meta["spec"])
    if not path.exists():
        raise FileNotFoundError(f"Missing Reference Pattern Plate spec: {path}")
    arr = np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32) / 255.0
    return arr[:, :, :3].astype(np.float32)


def _load_spec(spec_id: str) -> np.ndarray:
    meta = _META_BY_SPEC[spec_id]
    path = _ASSET_DIR / str(meta["spec"])
    return _load_spec_cached(spec_id, path.stat().st_mtime_ns)


def _reference_spec(spec_id: str, shape, seed, sm, **kwargs):
    del kwargs
    h, w = _shape2(shape)
    meta = _META_BY_SPEC.get(spec_id)
    if not meta:
        _refresh_manifest()
        meta = _META_BY_SPEC.get(spec_id)
    if not meta:
        raise KeyError(f"Unknown Reference Pattern Plate spec overlay: {spec_id}")
    path = _ASSET_DIR / str(meta["spec"])
    key = (spec_id, path.stat().st_mtime_ns, int(h), int(w))
    cached = _RESIZE_CACHE.get(key)
    if cached is not None:
        _RESIZE_CACHE.move_to_end(key)
        arr = cached.copy()
    else:
        src = _load_spec(spec_id)
        if src.shape[:2] == (h, w):
            arr = src.copy()
        else:
            arr = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)
        arr = _cache_put(key, arr).copy()

    phase = float((int(seed) + len(spec_id) * 97) % 8192) * (np.pi / 4096.0)
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    shimmer = np.sin(xs * (127.0 + phase) + ys * (61.0 - phase * 0.33))
    scan = np.cos(xs * (347.0 - phase * 0.21) - ys * (211.0 + phase * 0.17))
    live = (shimmer * 0.008 + scan * 0.005).astype(np.float32)

    out = np.empty_like(arr, dtype=np.float32)
    out[:, :, 0] = np.clip(arr[:, :, 0] + np.abs(live) * 0.035, 0.0, 1.0)
    out[:, :, 1] = np.clip(arr[:, :, 1] + live * 0.026, 0.03, 0.98)
    out[:, :, 2] = np.clip(arr[:, :, 2] - live * 0.024, 0.02, 1.0)
    return _validate_spec_output(_sm_scale(out, sm), spec_id)


def _make_renderer(spec_id: str):
    def renderer(shape, seed, sm, **kwargs):
        return _reference_spec(spec_id, shape, seed, sm, **kwargs)

    renderer.__name__ = f"render_{spec_id}"
    renderer._spb_concept_complete = True
    return renderer


# ---------------------------------------------------------------------------
# 2026-06-04 OWNER overrides. These two shipped as baked IMAGE plates whose
# generators produced near-identical confetti/hex looks (owner: gunmetal "almost
# identical to spec_lime_pixel_confetti"; teal hex "clean up the artifacting
# around the hexes"). Replace the plate lookup with clean PROCEDURAL renderers
# so they are genuinely distinct and artifact-free. Both keep (h,w,3) [M,R,CC],
# [0,1], and the trailing _sm_scale via _validate_spec_output(_sm_scale(...)).
# ---------------------------------------------------------------------------

def _msnoise(shape, scales, weights, seed):
    from ..spec_patterns import multi_scale_noise, _normalize
    return _normalize(multi_scale_noise(shape, scales, weights, seed))


def _msnoise_fast(shape, scales, weights, seed, max_dim=1024):
    """Same as _msnoise but for SMOOTH low-freq substrate/haze fields: renders the
    carrier noise at a bounded resolution and upscales (avoids enormous Gaussian
    sigmas at 2048px). 2026-06-04 perf pass. Use ONLY for soft fields where the
    sub-pixel detail is invisible anyway. ``max_dim`` (2026-06-13) caps the carrier
    grid -- a smaller cap makes the (already huge) low-freq Gaussians far cheaper
    with no visible change on a pure haze field."""
    from ..spec_patterns import _spb_fast_smooth_noise, _normalize
    return _normalize(_spb_fast_smooth_noise(shape, scales, weights, seed, max_dim=max_dim))


def _render_gunmetal_geo_tessellation(shape, seed, sm, **kwargs):
    """Clean gunmetal GEOMETRIC tessellation: interlocking hexagon facets where
    each facet is a flat satin/metal plane at one of several gunmetal tiers, with
    crisp polished bevel edges between facets. Cool gunmetal (low warm, neutral),
    NOT colored pixel confetti."""
    del kwargs
    h, w = _shape2(shape)
    mn = min(h, w)
    s256 = max(mn / 256.0, 0.55)
    # 2026-06-13 perf: build float32 coordinate grids as broadcastable 1-D arange
    # rows/cols (xx=(1,w), yy=(h,1)) instead of np.mgrid[0:h,0:w].astype(float32),
    # which materialises two full float64 H*W arrays then casts (~0.5s of pure
    # alloc/cast at 2048). NumPy broadcasting produces the SAME float32 values at
    # every pixel, so every downstream expression (cube-round cell IDs, facet
    # tiers, bevel, M/R/CC) is bit-identical -- and the X-only terms (q, cx) stay
    # (1,w) so their elementwise ops touch w cells instead of H*w.
    xx = np.arange(w, dtype=np.float32).reshape(1, w)
    yy = np.arange(h, dtype=np.float32).reshape(h, 1)

    # pointy-top hexagonal tiling -> per-hex cell id + distance to the nearest
    # hex edge (for crisp bevels). Use axial hex rounding.
    # 2026-06-13 perf: the cube-round + cell-ID stage runs in float32 (xx/yy are
    # float32, scalars promote to float32) and the per-hex INTEGER cell ids
    # (cellq/cellr) are exact, so cellhash is exact regardless of fp precision.
    # The continuous fields (cellhash/bru/facet/edge/bevel) are then forced to
    # FLOAT32 instead of leaking to float64 via python-float scalar division
    # (`/65535.0`, `/0.22`, `**1.4`). The discrete tier-bucket decision
    # `(cellhash*5).astype(int)` is unaffected: cellhash is quantised to ~1.5e-5
    # steps, far from the ~3e-8 float32/float64 gap, so no pixel changes bucket.
    # Halves the memory traffic on the ~6 full-canvas elementwise stages (sin,
    # edge max, bevel pow, clips) that dominated the body.
    size = max(11.0 * s256, 5.0)          # hex radius (fine facets at car scale)
    # NOTE: keep these two expressions byte-for-byte as the original -- xx/yy are
    # float32 and the scalars promote to float32, so cx/cz (hence the cube-round
    # integer cell ids) are bit-identical to the prior build.
    q = (2.0 / 3.0 * xx) / size
    r = (-1.0 / 3.0 * xx + (np.sqrt(3.0) / 3.0) * yy) / size
    # cube round
    cx = q
    cz = r
    cy = -cx - cz
    rxr = np.round(cx); ryr = np.round(cy); rzr = np.round(cz)
    dx = np.abs(rxr - cx); dy = np.abs(ryr - cy); dz = np.abs(rzr - cz)
    fix_x = (dx > dy) & (dx > dz)
    fix_z = (~fix_x) & (dz > dy)
    rxr = np.where(fix_x, -ryr - rzr, rxr)
    rzr = np.where(fix_z, -rxr - ryr, rzr)
    cellq = rxr.astype(np.int32); cellr = rzr.astype(np.int32)
    # per-hex gunmetal tier (a few discrete satin/metal facet shades).
    cellhash = (((cellq * 374761393 + cellr * 668265263) & 0xFFFF).astype(np.float32)
                * np.float32(1.0 / 65535.0))
    tiers = np.array([0.30, 0.42, 0.52, 0.63, 0.74], dtype=np.float32)
    facet = tiers[(cellhash * len(tiers)).astype(np.int32).clip(0, len(tiers) - 1)]
    # subtle within-facet brushed-metal gradient (directional satin sheen).
    bru = np.float32(0.5) + np.float32(0.5) * np.sin(
        (xx * np.float32(0.9) + yy * np.float32(0.4)) * np.float32(1.0 / max(3.0 * s256, 1.0))
        + cellhash * np.float32(6.28))
    facet = np.clip(facet + (bru - np.float32(0.5)) * np.float32(0.10), 0.0, 1.0)
    # crisp bevel: distance to hex boundary from fractional hex coords.
    fq = cx - rxr; fr = cz - rzr; fs = cy - ryr
    edge = np.float32(1.0) - np.float32(2.0) * np.maximum(np.maximum(np.abs(fq), np.abs(fr)), np.abs(fs))
    # keep bevel in float32 (np.clip with python-float bounds would promote to
    # float64): clip with float32 bounds, then power stays float32.
    bevel = np.power(np.clip(np.float32(1.0) - edge * np.float32(1.0 / 0.22),
                             np.float32(0.0), np.float32(1.0)), np.float32(1.4))

    # Gunmetal: neutral-cool metal. M carries facet brightness; R moderate (satin
    # roughness on facets, polished on bevels); CC cool. The three "build" clips
    # were no-ops (facet in [~0.2,0.84] keeps every channel strictly interior to
    # its clip range) so they are dropped -- bit-identical, saves 3 full passes.
    M = (np.float32(0.16) + facet * np.float32(0.70))
    R = (np.float32(0.50) - facet * np.float32(0.26))
    CC = (np.float32(0.24) + facet * np.float32(0.48))
    # polished bright bevel edges (specular metal seams) -> crisp interlocking hexes.
    M = np.clip(M + bevel * np.float32(0.36), np.float32(0.0), np.float32(1.0))
    R = np.clip(R - bevel * np.float32(0.28), np.float32(0.04), np.float32(1.0))
    CC = np.clip(CC + bevel * np.float32(0.32), np.float32(0.0), np.float32(1.0))
    # very fine machining micro-grain so it reads detailed, not flat. Kept at FULL
    # resolution (bit-identical): the bounded-res fast path shifted some pixels by
    # ~0.037 (this is the finish's FINEST detail and the owner cares about it), so
    # the small saving is not worth the visible change.
    grain = _msnoise((h, w), [1.4 * s256, 3.2 * s256], [0.6, 0.4], int(seed) + 211)
    M = np.clip(M + (grain - np.float32(0.5)) * np.float32(0.05), np.float32(0.0), np.float32(1.0))
    out = np.stack([M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)], axis=-1)
    return _validate_spec_output(_sm_scale(out, sm), "spec_gunmetal_geo_tessellation")


def _render_teal_hex_haze(shape, seed, sm, **kwargs):
    """Teal hex haze with SMOOTH anti-aliased hex cells (no edge artifacting).
    Soft teal-pearl hex bokeh: each hex cell glows from a soft center with a
    gentle anti-aliased rim, over a hazy translucent clearcoat. Clean."""
    del kwargs
    h, w = _shape2(shape)
    mn = min(h, w)
    # 2026-06-04 perf: this is an entirely SMOOTH field (soft hex bokeh + low-freq
    # haze, no crisp high-frequency detail). At 2048 the full-canvas hex math
    # (round/exp/where over 4.2M px) plus the huge haze Gaussians dominate. Render
    # the whole plate at a capped resolution and INTER_CUBIC up to the canvas; the
    # cell size scales with the render shape so the hex layout/count per canvas is
    # the SAME -- only the rasterization softens (invisible on this bokeh). Small
    # canvases (incl. the 256 audit size) keep the exact full-res path.
    _CAP = 1024
    if max(h, w) > _CAP:
        f = float(_CAP) / float(max(h, w))
        rh = max(2, int(round(h * f))); rw = max(2, int(round(w * f)))
    else:
        rh, rw = h, w
    rmn = min(rh, rw)
    s256 = max(rmn / 256.0, 0.55)
    yy = np.arange(rh, dtype=np.float32)[:, None]
    xx = np.arange(rw, dtype=np.float32)[None, :]

    size = max(15.0 * s256, 6.0)
    q = (2.0 / 3.0 * xx) / size
    r = (-1.0 / 3.0 * xx + (np.sqrt(3.0) / 3.0) * yy) / size
    cx = q; cz = r; cy = -cx - cz
    rxr = np.round(cx); ryr = np.round(cy); rzr = np.round(cz)
    dx = np.abs(rxr - cx); dy = np.abs(ryr - cy); dz = np.abs(rzr - cz)
    fix_x = (dx > dy) & (dx > dz)
    fix_z = (~fix_x) & (dz > dy)
    rxr = np.where(fix_x, -ryr - rzr, rxr)
    rzr = np.where(fix_z, -rxr - ryr, rzr)
    fq = cx - rxr; fr = cz - rzr; fs = cy - ryr
    # distance to hex CENTER (0) vs hex EDGE (1) -- smooth radial bokeh per cell.
    # 2026-06-13 perf: keep these soft fields in float32 (the python-float scalars
    # `/65535.0`, `(...)**2 / (2*0.05**2)` previously promoted to float64). xx/yy
    # are float32 so dedge is already float32; the integer cell ids are exact, so
    # cellhash is exact bar a <1e-7 fp gap on a quantised value -- invisible on
    # this soft bokeh (gated SSIM>=0.997, tiny max-delta).
    dedge = np.float32(2.0) * np.maximum(np.maximum(np.abs(fq), np.abs(fr)), np.abs(fs))  # 0 center -> 1 edge
    # SMOOTH bokeh: soft bright center fading to a gently anti-aliased rim. Using
    # a smoothstep instead of a hard threshold removes the edge artifacting.
    t = np.clip(dedge, np.float32(0.0), np.float32(1.0))
    bokeh = np.float32(1.0) - (t * t * (np.float32(3.0) - np.float32(2.0) * t))  # smoothstep falloff
    # soft anti-aliased rim glow just inside each hex boundary.
    rim = np.exp(-((dedge - np.float32(0.86)) ** 2) * np.float32(1.0 / (2 * 0.05 ** 2)))
    cellhash = (((rxr.astype(np.int32) * 374761393 + rzr.astype(np.int32) * 668265263) & 0xFFFF)
                .astype(np.float32) * np.float32(1.0 / 65535.0))
    cellbright = np.float32(0.6) + np.float32(0.4) * cellhash

    # hazy translucent teal clearcoat substrate (smooth low-freq). Rendered via the
    # bounded-res fast path: at 2048 these sigmas (up to ~384) make full-canvas
    # Gaussians the whole cost; this soft field is identical to the eye.
    # NOTE: the carrier grid resolution is part of the LOOK -- changing max_dim
    # regenerates a different random field (not just a softer one), so the 1024
    # cap is locked. Tested max_dim=512: SSIM ok but max-delta 0.146 (look change).
    haze = _msnoise_fast((rh, rw), [9.0 * s256, 22.0 * s256, 48.0 * s256], [0.5, 0.32, 0.18], int(seed) + 311)
    # Teal -> high CC (clear), moderate M (pearl), low-ish R (smooth/glossy).
    # Deeper bokeh contrast so the clean hex haze reads with body (still soft).
    haze = haze.astype(np.float32)
    M = np.clip(np.float32(0.18) + bokeh * np.float32(0.58) * cellbright + rim * np.float32(0.26),
                np.float32(0.0), np.float32(1.0)).astype(np.float32)
    R = np.clip(np.float32(0.22) + (np.float32(1.0) - bokeh) * np.float32(0.22) + (haze - np.float32(0.5)) * np.float32(0.08),
                np.float32(0.04), np.float32(0.85)).astype(np.float32)
    CC = np.clip(np.float32(0.36) + bokeh * np.float32(0.54) * cellbright + rim * np.float32(0.22) + (haze - np.float32(0.5)) * np.float32(0.18),
                 np.float32(0.0), np.float32(1.0)).astype(np.float32)
    out = np.stack([M, R, CC], axis=-1).astype(np.float32)
    if (rh, rw) != (h, w):
        # 2026-06-13: stack first, then ONE 3-channel cv2.resize -- INTER_CUBIC is
        # per-channel so this is identical to three separate resizes but ~3x less
        # call overhead and one output buffer.
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_CUBIC)
    return _validate_spec_output(_sm_scale(np.clip(out, 0.0, 1.0), sm), "spec_teal_hex_haze")


REFERENCE_PATTERN_SPEC_OVERLAY_CATALOG = {
    spec_id: _make_renderer(spec_id)
    for spec_id in sorted(_META_BY_SPEC)
}

# Procedural overrides (replace the baked image-plate lookups).
REFERENCE_PATTERN_SPEC_OVERLAY_CATALOG["spec_gunmetal_geo_tessellation"] = _render_gunmetal_geo_tessellation
REFERENCE_PATTERN_SPEC_OVERLAY_CATALOG["spec_teal_hex_haze"] = _render_teal_hex_haze
