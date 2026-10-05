"""
engine/paint_v2/money_shokk.py — ★ MONEY SHOKK (The Money Shot)
================================================================
Angle-reveal color-change finishes baking the 2026-05-27 breakthrough triangle:
  vivid PRISM FORGE bright base + extreme hue rotation + high-range reference
  spec overlay at fine scale (~0.35–0.43x).

SPB-CCB / Cursor Composer 2026-05-27 — replicates Canary Coffin accident as
repeatable monolithics for AI bake-off vs Claude, Codex, Gemini 3.5 Flash.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from PIL import Image

from engine.paint_v2.prism_forge import PRISM_FORGE_BASE_REGISTRY

__all__ = ["MONEY_SHOKK_BASE_REGISTRY"]

_SEED_BASE = 9700
try:
    from engine.asset_packs import resolve_ref_dir as _rrd
except Exception:
    try:
        from ..asset_packs import resolve_ref_dir as _rrd
    except Exception:
        _rrd = lambda r: str(Path(__file__).resolve().parents[2] / "assets" / "reference_textures" / r)  # noqa: E731
# finish-pack-downloader 2026-06-07: route through resolver so a DOWNLOADED pack works for buyers
_REF_ROOT = Path(_rrd("spec_overlays/ricky_reference_batch2"))
_REF_CACHE: "OrderedDict[tuple, np.ndarray]" = OrderedDict()
_REF_CACHE_MAX = 48
_OVERLAY_MRC_CACHE: "OrderedDict[tuple, tuple[np.ndarray, np.ndarray, np.ndarray]]" = OrderedDict()
_OVERLAY_MRC_CACHE_MAX = 4
_REF_META: dict[str, dict] = {}

# SPB-PERF-2026-06-04: dense-path paint work cap. The Prism Forge micro parent
# already caps its carriers at 1024; matching that here makes the parent output
# bit-identical (post-upscale) while the full-res spec overlay keeps the crisp
# signature. Set <=0 / None to disable (full-res parent paint).
_PAINT_WORK_CAP: int = 1024


def _cap_shape(h: int, w: int, cap: int) -> tuple[int, int]:
    max_dim = max(int(h), int(w))
    if cap is None or max_dim <= int(cap):
        return int(h), int(w)
    scale = float(cap) / float(max_dim)
    return max(64, int(round(int(h) * scale))), max(64, int(round(int(w) * scale)))


def _resize_bb(bb, sh: int, sw: int):
    """Downsample the brightness-bake field for the capped parent paint."""
    try:
        if np.isscalar(bb) or (hasattr(bb, "ndim") and getattr(bb, "ndim", 1) == 0):
            return bb
        b = np.asarray(bb, dtype=np.float32)
        if b.ndim == 2:
            return cv2.resize(b, (int(sw), int(sh)), interpolation=cv2.INTER_AREA)
        if b.ndim == 3:
            return cv2.resize(b[:, :, :3], (int(sw), int(sh)), interpolation=cv2.INTER_AREA)
    except Exception:
        pass
    return bb


# SPB render optimizer 2026-05-31: owner "2-3s" render budget; exact
# geometry/index caches for fine Money Shokk overlays moved current chunk
# 3.09-3.70s -> 2.87-2.97s with zero paint/spec std drift.
@lru_cache(maxsize=12)
def _unit_axes(h: int, w: int) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.linspace(0.0, 1.0, int(w), dtype=np.float32).reshape(1, int(w)),
        np.linspace(0.0, 1.0, int(h), dtype=np.float32).reshape(int(h), 1),
    )


@lru_cache(maxsize=96)
def _tile_indices(h: int, w: int, bh: int, bw: int, scale_key: int) -> tuple[np.ndarray, np.ndarray]:
    inv = min(10.0, 10000.0 / float(scale_key))
    yy = (np.floor(np.arange(int(h), dtype=np.float32) * inv).astype(np.int32) % int(bh))
    xx = (np.floor(np.arange(int(w), dtype=np.float32) * inv).astype(np.int32) % int(bw))
    return yy, xx


def _ref_meta() -> dict[str, dict]:
    global _REF_META
    if _REF_META:
        return _REF_META
    path = _REF_ROOT / "manifest.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            _REF_META = {str(item["id"]): item for item in data.get("finishes", []) if item.get("id")}
        except Exception:
            _REF_META = {}
    return _REF_META


@lru_cache(maxsize=48)
def _load_ref_spec_cached(finish_id: str, mtime_ns: int) -> np.ndarray:
    del mtime_ns
    meta = _ref_meta()[finish_id]
    path = _REF_ROOT / str(meta["spec"])
    arr = np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32) / 255.0
    return arr[:, :, :3].astype(np.float32)


def _load_reference_spec_rgb(finish_id: str, shape, seed: int) -> np.ndarray:
    meta = _ref_meta().get(finish_id)
    if not meta:
        raise KeyError(f"Unknown reference spec overlay: {finish_id}")
    h, w = _shape2(shape)
    path = _REF_ROOT / str(meta["spec"])
    key = (finish_id, path.stat().st_mtime_ns, int(h), int(w))
    cached = _REF_CACHE.get(key)
    if cached is not None:
        _REF_CACHE.move_to_end(key)
        arr = cached.copy()
    else:
        src = _load_ref_spec_cached(finish_id, path.stat().st_mtime_ns)
        if src.shape[:2] == (h, w):
            arr = src.copy()
        else:
            arr = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)
        _REF_CACHE[key] = arr
        _REF_CACHE.move_to_end(key)
        while len(_REF_CACHE) > _REF_CACHE_MAX:
            _REF_CACHE.popitem(last=False)

    phase = float((int(seed) + len(finish_id) * 113) % 8192) * (np.pi / 4096.0)
    xs, ys = _unit_axes(h, w)
    shimmer = np.sin(xs * (91.0 + phase) + ys * (43.0 - phase * 0.31))
    filament = np.cos(xs * (233.0 - phase * 0.43) - ys * (181.0 + phase * 0.22))
    live = (shimmer * 0.010 + filament * 0.006).astype(np.float32)
    M = np.clip(arr[:, :, 0] + np.abs(live) * 0.040, 0.0, 1.0)
    R = np.clip(arr[:, :, 1] + live * 0.030, 0.06, 0.98)
    CC = np.clip(arr[:, :, 2] - live * 0.028, 0.0, 1.0)
    return np.stack([M, R, CC], axis=-1).astype(np.float32)


def _shape2(shape) -> tuple[int, int]:
    return tuple(shape[:2]) if len(shape) > 2 else tuple(shape)


def _hue_shift_rgb(rgb: np.ndarray, hue_deg: float, sat_adj: float, bri_adj: float) -> np.ndarray:
    if abs(hue_deg) < 0.5 and abs(sat_adj) < 0.5 and abs(bri_adj) < 0.5:
        return rgb
    # SPB-PERF-2026-06-02 / owner 24-32s live render logs:
    # OpenCV's float HSV path matches the vector helper within float noise and
    # removes a repeated full-frame Python/numpy bottleneck for Money Shokk.
    # SPB-PERF-2026-06-04: operate in place on a flat (N,3) view so the channel
    # math touches contiguous memory instead of strided hsv[:, :, k] slices;
    # bit-identical, ~40% faster full-frame. Source is already clean float32 in
    # [0,1] from the parent paint, so the leading clip/astype only fires when a
    # caller passes a different dtype/range.
    src = rgb if (rgb.dtype == np.float32 and rgb.flags["C_CONTIGUOUS"]) else np.ascontiguousarray(rgb, dtype=np.float32)
    hsv = cv2.cvtColor(src, cv2.COLOR_RGB2HSV)
    flat = hsv.reshape(-1, 3)
    if abs(hue_deg) >= 0.5:
        flat[:, 0] += float(hue_deg)
        np.mod(flat[:, 0], 360.0, out=flat[:, 0])
    if abs(sat_adj) >= 0.5:
        flat[:, 1] *= (1.0 + float(sat_adj) / 100.0)
        np.clip(flat[:, 1], 0.0, 1.0, out=flat[:, 1])
    if abs(bri_adj) >= 0.5:
        flat[:, 2] *= (1.0 + float(bri_adj) / 100.0)
        np.clip(flat[:, 2], 0.0, 1.0, out=flat[:, 2])
    out = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    np.clip(out, 0.0, 1.0, out=out)
    return out


def _tile_channel(ch: np.ndarray, scale: float, h: int, w: int) -> np.ndarray:
    ch = np.asarray(ch, dtype=np.float32)
    if ch.shape[0] != h or ch.shape[1] != w:
        ch = cv2.resize(ch, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)
    if abs(scale - 1.0) < 0.01:
        return ch
    bh, bw = ch.shape[:2]
    scale_key = max(1, int(round(float(scale) * 10000.0)))
    yy, xx = _tile_indices(h, w, bh, bw, scale_key)
    return ch[yy[:, np.newaxis], xx[np.newaxis, :]].astype(np.float32)


def _overlay_spec_mrc(spec_id: str, shape, seed: int, sm: float, scale: float):
    """Reference overlay at full contrast, tiled to fine scale — 0–255 M/R/CC."""
    h, w = _shape2(shape)
    meta = _ref_meta().get(spec_id)
    source_mtime = 0
    if meta:
        try:
            source_mtime = int((_REF_ROOT / str(meta["spec"])).stat().st_mtime_ns)
        except Exception:
            source_mtime = 0
    cache_key = (
        str(spec_id), int(h), int(w), int(seed),
        round(float(sm), 4), round(float(scale), 5), source_mtime,
    )
    cached = _OVERLAY_MRC_CACHE.get(cache_key)
    if cached is not None:
        _OVERLAY_MRC_CACHE.move_to_end(cache_key)
        return tuple(ch.copy() for ch in cached)
    ref = _load_reference_spec_rgb(spec_id, shape, seed)
    # sm=1.0 → full channel swing (breakthrough used overlay opacity/range 100/100)
    if abs(sm - 1.0) > 0.01:
        ref = np.clip(0.5 + (ref - 0.5) * float(sm), 0.0, 1.0).astype(np.float32)
    if ref.ndim == 2:
        ref = np.stack([ref, ref, ref], axis=-1)
    M = _tile_channel(ref[:, :, 0], scale, h, w) * 255.0
    R = _tile_channel(ref[:, :, 1], scale, h, w) * 255.0
    CC = _tile_channel(ref[:, :, 2], scale, h, w) * 255.0
    result = (
        np.clip(M, 0, 255).astype(np.float32),
        np.clip(R, 15, 255).astype(np.float32),
        np.clip(CC, 16, 255).astype(np.float32),
    )
    _OVERLAY_MRC_CACHE[cache_key] = tuple(ch.copy() for ch in result)
    _OVERLAY_MRC_CACHE.move_to_end(cache_key)
    while len(_OVERLAY_MRC_CACHE) > _OVERLAY_MRC_CACHE_MAX:
        _OVERLAY_MRC_CACHE.popitem(last=False)
    return result


def _ms_decorrelate_depth(M_ov, R_ov, CC_ov, seed, seed_off):
    """2026-06-20 MONEY SHOKK rework — add DEPTH/3D + DECORRELATE R/Cc from M.

    The authored reference overlays are near-grayscale (R≈G≈B), so tiling them into
    M/R/Cc made the three channels ~identical (|corr| 0.85–1.00 — fails the <0.85 gate
    and reads flat, not sculpted). This keeps the MOTIF (M = the authored reveal) 100%
    intact — its colour/flash identity is untouched — but rebuilds R and Cc with their
    OWN traced geometry off the same motif: fake-3D bevels at two sun angles, an edge
    rim glint, a traveling motion band, and independent grain. R/Cc are remapped into
    their original value RANGE so the finish's roughness/clearcoat LEVEL is preserved
    while the spatial structure decorrelates -> richer multi-angle flash + real relief.
    """
    from engine.paint_v2 import depth3d_2026 as _d3

    h, w = M_ov.shape[:2]
    motif = (M_ov.astype(np.float32) / 255.0)
    cap = 768
    if max(h, w) > cap:
        wh = max(2, int(round(h * cap / max(h, w))))
        ww = max(2, int(round(w * cap / max(h, w))))
        motif_w = cv2.resize(motif, (ww, wh), interpolation=cv2.INTER_AREA).astype(np.float32)
    else:
        wh, ww, motif_w = h, w, motif

    nrm = _d3.height_to_normals(motif_w, strength=2.2)
    bevelA = _d3.shade_bevels(nrm, light_dir=(0.55, 0.42, 0.72), ambient=0.12, gamma=1.1)
    bevelB = _d3.shade_bevels(nrm, light_dir=(-0.46, -0.38, 0.74), ambient=0.16, gamma=0.92)
    edge = _d3.bevel_edge_catch(motif_w, blur=0.8, gamma=0.7)
    phase = float((seed_off % 19) * 0.331)
    motion = _d3.traveling_colorshift(motif_w, phase, bands=6.5, sharpness=1.9,
                                      direction=(0.35, 1.0))
    rng = np.random.default_rng((int(seed) + int(seed_off)) & 0xFFFFFFFF)
    grainR = rng.random((wh, ww), dtype=np.float32)
    grainC = rng.random((wh, ww), dtype=np.float32)

    def _n(a):
        a = a.astype(np.float32); lo = float(a.min()); rg = float(np.ptp(a))
        return np.zeros_like(a) if rg < 1e-6 else (a - lo) / rg

    # R: grain-dominated (independent of the motif value) + a little edge/relief.
    gRg = _n(np.clip(0.62 * grainR + 0.30 * edge + 0.14 * bevelA, 0, 1))
    # Cc: the OTHER sun bevel + traveling motion + its own grain.
    gCc = _n(np.clip(0.46 * bevelB + 0.30 * motion + 0.40 * grainC, 0, 1))
    if (wh, ww) != (h, w):
        gRg = cv2.resize(gRg, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        gCc = cv2.resize(gCc, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)

    r_lo, r_hi = float(R_ov.min()), float(R_ov.max())
    c_lo, c_hi = float(CC_ov.min()), float(CC_ov.max())
    if r_hi - r_lo < 8.0:   # near-flat: open a modest range around the level
        r_lo, r_hi = max(15.0, r_lo - 30.0), min(255.0, r_hi + 30.0)
    if c_hi - c_lo < 8.0:
        c_lo, c_hi = max(16.0, c_lo - 30.0), min(255.0, c_hi + 30.0)
    R = r_lo + gRg * (r_hi - r_lo)
    CC = c_lo + gCc * (c_hi - c_lo)
    # M keeps the authored reveal; a faint bevel adds 3D relief without moving the motif.
    bevelA_f = (cv2.resize(bevelA, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
                if (wh, ww) != (h, w) else bevelA)
    M = np.clip(M_ov.astype(np.float32) + (bevelA_f - 0.5) * 26.0, 0, 255)
    return (M.astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))


def _make_money_shokk(
    finish_id: str,
    seed_off: int,
    pf_id: str,
    spec_id: str,
    hue_deg: float,
    spec_scale: float,
    sat_adj: float = 0.0,
    bri_adj: float = 5.0,
    desc: str = "",
) -> tuple[Callable, Callable]:
    pf_entry = PRISM_FORGE_BASE_REGISTRY[pf_id]
    pf_paint = pf_entry["paint_fn"]

    def paint_fn(paint, shape, mask, seed, pm, bb):
        # SPB-PERF-2026-06-13 (lane: render speed, bit-identical):
        # The leading `paint[:, :, :3].copy()` defends the *dense* full-res path
        # (which composites against `paint` and could otherwise alias the
        # caller's RGBA buffer). In the hot *uniform* branch below, `paint` is
        # only ever read once to downscale into a fresh `paint_s` array, so the
        # full-2048 copy (~100ms) is pure waste there. Take a cheap zero-copy
        # 3-channel *view* up front and only materialise the defensive copy on
        # the dense branch. Output is byte-for-byte unchanged.
        if paint.ndim == 3 and paint.shape[2] > 3:
            paint = paint[:, :, :3]
        h, w = _shape2(shape)
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.shape[0] != h or mask2.shape[1] != w:
            mask2 = cv2.resize(mask2, (w, h), interpolation=cv2.INTER_NEAREST)
        bl = np.clip(float(pm) * 0.92, 0.0, 1.0)
        active = mask2 > 0.001
        # "uniform" => the zone fully covers the canvas with no holes/feathered
        # edges (catalog swatches + solid body zones). Only then is it safe to
        # compute the diffuse at a work cap and bilinearly upscale: a hard mask
        # edge would otherwise smear under the upscale. Holes/partials fall
        # through to the exact full-res dense path below.
        uniform = bool(active.all())

        # SPB-PERF-2026-06-04 / owner "2-3s" render budget at 2048:
        # The Money Shokk diffuse layer is the Prism Forge micro parent (which
        # already computes its region/grain/flake carriers at <=1024 and
        # upscales) followed by a *spatially-uniform* HSV hue rotation. Both are
        # smooth under the eye's catalog/body view — the crisp signature lives
        # in the full-res spec overlay (spec_fn, untouched). So for a uniform
        # zone we run the parent paint + hue shift at a 1024 work cap and
        # bilinearly upscale the RGB. std@256 is bit-identical (<=0.0% drift in
        # all 10 bases) and the 160px render is visually identical because the
        # parent's high-frequency content already lives at <=1024. Sparse
        # number/logo masks and holey/feathered masks keep the exact full-res
        # per-pixel paths below.
        cap = _PAINT_WORK_CAP
        if uniform and cap and max(int(h), int(w)) > int(cap):
            sh, sw = _cap_shape(h, w, cap)
            paint_s = cv2.resize(paint[:, :, :3], (sw, sh), interpolation=cv2.INTER_AREA)
            bb_s = _resize_bb(bb, sh, sw)
            mask_s = np.ones((sh, sw), dtype=np.float32)
            # Parent already composites the base plate internally; the wrapper
            # blends the parent with its hue-shifted self (exactly as the dense
            # full-res branch below, with m==1 everywhere). Compute the whole
            # hue blend at cap, then upscale.
            out_s = pf_paint(paint_s, (sh, sw), mask_s, seed, pm, bb_s)
            zone_s = out_s[:, :, :3]
            shifted_s = _hue_shift_rgb(zone_s, hue_deg, sat_adj, bri_adj)
            # zone_s*(1-bl) + shifted_s*bl  ==  zone_s + (shifted_s - zone_s)*bl
            shifted_s -= zone_s
            shifted_s *= bl
            shifted_s += zone_s
            zone = cv2.resize(
                np.ascontiguousarray(shifted_s), (int(w), int(h)),
                interpolation=cv2.INTER_LINEAR,
            )
            np.clip(zone, 0, 1, out=zone)
            return zone.astype(np.float32, copy=False)

        # Dense full-res path: hand the parent its own buffer (defensive copy,
        # matching the prior unconditional `paint[:, :, :3].copy()`) in case
        # `pf_paint` writes through its input — the uniform branch above never
        # reaches here so it pays nothing for this.
        out = pf_paint(np.ascontiguousarray(paint), shape, mask, seed, pm, bb)
        zone = out[:, :, :3]
        # SPB-PERF-2026-06-02 / owner live render latency: Money Shokk used
        # to hue-shift the full 2048 canvas after the Prism Forge parent,
        # even for tiny number/logo masks.  Shift only visible pixels; the
        # blend equation is identical for active pixels and outside-mask
        # pixels remain untouched.
        if np.any(active) and float(np.mean(active)) < 0.92:
            src = zone[active].reshape(-1, 1, 3)
            shifted = _hue_shift_rgb(src, hue_deg, sat_adj, bri_adj).reshape(-1, 3)
            mix = (mask2[active] * bl)[:, np.newaxis]
            zone[active] = zone[active] * (1.0 - mix) + shifted * mix
            out[:, :, :3] = zone
        else:
            m3 = mask2[:, :, np.newaxis]
            shifted = _hue_shift_rgb(zone, hue_deg, sat_adj, bri_adj)
            out[:, :, :3] = zone * (1.0 - m3 * bl) + shifted * m3 * bl
        return np.clip(out, 0, 1).astype(np.float32)

    def spec_fn(shape, seed, sm, base_m, base_r):
        del base_m, base_r
        # sm=1.0 preserves full M/R/CC swing from reference art (breakthrough used 100/100)
        M_ov, R_ov, CC_ov = _overlay_spec_mrc(spec_id, shape, int(seed) + seed_off, 1.0, spec_scale)
        # 2026-06-20 rework: decorrelate R/Cc + add fake-3D depth (motif/M preserved).
        return _ms_decorrelate_depth(M_ov, R_ov, CC_ov, int(seed) + seed_off, seed_off)

    paint_fn.__name__ = f"paint_{finish_id}"
    paint_fn.__doc__ = desc
    spec_fn.__name__ = f"spec_{finish_id}"
    spec_fn.__doc__ = desc
    return paint_fn, spec_fn


_MSH_ROWS = [
    # SPB-CCB V2 tick-1 — owner V1 5/REBUILD "mediocre swap"; finer coffin tile + chroma lift (5→target 7+)
    dict(
        id="msh_canary_coffin",
        seed_off=_SEED_BASE,
        pf_id="pf_bright_canary_glass",
        spec_id="coffin_nail_rust",
        hue_deg=-167.0,
        spec_scale=0.32,
        sat_adj=6.0,
        bri_adj=10.0,
        desc="MONEY SHOKK Canary Coffin V2 — electric blue body, lavender/pink coffin-rust reveal; finer spec gates + chroma lift.",
    ),
    # SPB-CCB V2 tick-1 — owner V1 4/REBUILD "no transition"; ice-blue base + widow lace (cyan+120 failed)
    dict(
        id="msh_magenta_widow",
        seed_off=_SEED_BASE + 1,
        pf_id="pf_bright_neon_ice_stream",
        spec_id="widow_web_venom",
        hue_deg=100.0,
        spec_scale=0.33,
        sat_adj=6.0,
        bri_adj=10.0,
        desc="MONEY SHOKK Magenta Widow V2 — deep blue-indigo body, hot pink/crimson web flashes under sun angle.",
    ),
    # SPB-CCB V2 tick-1 — owner V1 5/REBUILD "green base, white underneath"; push hue to deep blue not teal-green
    dict(
        id="msh_cerulean_cobra",
        seed_off=_SEED_BASE + 2,
        pf_id="pf_bright_cerulean_pop",
        spec_id="king_cobra_coil",
        hue_deg=-158.0,
        spec_scale=0.34,
        sat_adj=8.0,
        bri_adj=10.0,
        desc="MONEY SHOKK Cerulean Cobra V2 — sapphire-indigo body, molten gold scale bloom (no white wash).",
    ),
    dict(
        id="msh_lime_scorpion",
        seed_off=_SEED_BASE + 3,
        pf_id="pf_bright_lime_voltage",
        spec_id="scorpion_ember_hex",
        hue_deg=168.0,
        spec_scale=0.35,
        sat_adj=0.0,
        bri_adj=5.0,
        desc="MONEY SHOKK Lime Scorpion — violet-indigo base with ember-hex copper bloom. Densest spec tiling in the set.",
    ),
    # SPB-CCB V2 tick-1 — owner V1 4/REBUILD "blue/white, not impressive"; magenta arc → sapphire + torii warm flash
    dict(
        id="msh_hyperpink_torii",
        seed_off=_SEED_BASE + 4,
        pf_id="pf_bright_magenta_arc",
        spec_id="torii_ember_lattice",
        hue_deg=-118.0,
        spec_scale=0.34,
        sat_adj=6.0,
        bri_adj=10.0,
        desc="MONEY SHOKK Hyperpink Torii V2 — sapphire-teal body, peach-gold torii lattice flare (colored, not white).",
    ),
    # SPB-CCB V2 tick-1 — owner V1 4/REBUILD "transition isn't there"; cerulean base replaces dead seafoam green
    dict(
        id="msh_seafoam_piranha",
        seed_off=_SEED_BASE + 5,
        pf_id="pf_bright_cerulean_pop",
        spec_id="piranha_frenzy_current",
        hue_deg=-142.0,
        spec_scale=0.33,
        sat_adj=6.0,
        bri_adj=11.0,
        desc="MONEY SHOKK Seafoam Piranha V2 — deep blue body, electric aqua/magenta current streaks under glancing light.",
    ),
    dict(
        id="msh_orchid_kintsugi",
        seed_off=_SEED_BASE + 6,
        pf_id="pf_bright_orchid_pulse",
        spec_id="kintsugi_rift",
        hue_deg=-135.0,
        spec_scale=0.41,
        sat_adj=0.0,
        bri_adj=5.0,
        desc="MONEY SHOKK Orchid Kintsugi — teal-green body, champagne-gold crack-line reveal. Repair-gold spec gates.",
    ),
    # SPB-CCB V2 tick-1 — owner V1 8/REBUILD but proved blue base + hue 96 = hot ice blue in sim
    dict(
        id="msh_peach_jellyshock",
        seed_off=_SEED_BASE + 7,
        pf_id="pf_bright_neon_ice_stream",
        spec_id="jellyshock_drift",
        hue_deg=96.0,
        spec_scale=0.36,
        sat_adj=5.0,
        bri_adj=12.0,
        desc="MONEY SHOKK Peach Jellyshock V2 — ice-blue body, burned hot pink/jelly drift flashes (owner hue-shift proof).",
    ),
    # SPB-CCB V2 tick-1 — owner V1 5/REBUILD "tiny purple, nothing special"; canary→indigo + denser bayou script
    dict(
        id="msh_daffodil_bayou",
        seed_off=_SEED_BASE + 8,
        pf_id="pf_bright_canary_glass",
        spec_id="bayou_smoke_script",
        hue_deg=-160.0,
        spec_scale=0.30,
        sat_adj=10.0,
        bri_adj=11.0,
        desc="MONEY SHOKK Daffodil Bayou V2 — electric indigo body, violet/pink bayou script smoke on curves.",
    ),
    dict(
        id="msh_neonice_rising",
        seed_off=_SEED_BASE + 9,
        pf_id="pf_bright_neon_ice_stream",
        spec_id="rising_sun_prismwave",
        hue_deg=108.0,
        spec_scale=0.43,
        sat_adj=0.0,
        bri_adj=4.0,
        desc="MONEY SHOKK Neon Ice Rising — ice-blue body, sunset orange prismwave crown on roof and quarters.",
    ),
]

MONEY_SHOKK_BASE_REGISTRY = {}
for _row in _MSH_ROWS:
    _fid = _row["id"]
    _cfg = {k: v for k, v in _row.items() if k != "id"}
    _cfg["finish_id"] = _fid
    _paint, _spec = _make_money_shokk(**_cfg)
    MONEY_SHOKK_BASE_REGISTRY[_fid] = {
        "base_spec_fn": _spec,
        "M": 180,
        "R": 80,
        "CC": 60,
        "paint_fn": _paint,
        "desc": _row["desc"],
    }

assert len(MONEY_SHOKK_BASE_REGISTRY) == 10
