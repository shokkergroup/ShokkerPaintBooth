"""Cultural / Viva Mexico image-based monolithic finishes.

The Viva Mexico set uses prepared 2048 paint plates plus paired M/R/CC spec
plates. The source posters are cleaned into texture assets first so the app
does not carry the bottom card text/numbering into rendered paints.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


_ROOT = Path(__file__).resolve().parents[2]
_ASSET_DIR = _ROOT / "assets" / "reference_textures" / "cultural" / "viva_mexico"

_FALLBACK_FINISH_IDS = (
    "vm_aztec_sunfire",
    "vm_talavera_azul",
    "vm_quetzal_sunset",
    "vm_sacred_heart_eclipse",
    "vm_guadalupe_lowrider",
)


def _manifest_finish_ids():
    path = _ASSET_DIR / "manifest.json"
    if not path.exists():
        return _FALLBACK_FINISH_IDS
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        ids = tuple(item["id"] for item in data.get("finishes", []) if item.get("id"))
        return ids or _FALLBACK_FINISH_IDS
    except Exception:
        return _FALLBACK_FINISH_IDS


_FINISH_IDS = _manifest_finish_ids()


def _shape2(shape):
    return shape[:2] if len(shape) > 2 else shape


def _mask2(mask, shape):
    h, w = _shape2(shape)
    if np.isscalar(mask) or (hasattr(mask, "ndim") and mask.ndim == 0):
        return np.full((h, w), float(mask), dtype=np.float32)
    arr = np.asarray(mask, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr[:, :, 0]
    if arr.shape != (h, w):
        arr = cv2.resize(arr, (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(arr, 0.0, 1.0).astype(np.float32)


def _resize(arr, shape, interpolation):
    h, w = _shape2(shape)
    if arr.shape[:2] == (h, w):
        return arr
    return cv2.resize(arr, (w, h), interpolation=interpolation)


@lru_cache(maxsize=128)
def _load_rgb_cached(finish_id, mtime_ns):
    path = _ASSET_DIR / f"{finish_id}.png"
    if not path.exists():
        raise FileNotFoundError(f"Missing Viva Mexico texture: {path}")
    img = Image.open(path).convert("RGB")
    return (np.asarray(img, dtype=np.float32) / 255.0).astype(np.float32)


def _load_rgb(finish_id):
    path = _ASSET_DIR / f"{finish_id}.png"
    return _load_rgb_cached(finish_id, path.stat().st_mtime_ns)


@lru_cache(maxsize=128)
def _load_spec_cached(finish_id, mtime_ns):
    path = _ASSET_DIR / f"{finish_id}_spec.png"
    if not path.exists():
        raise FileNotFoundError(f"Missing Viva Mexico spec map: {path}")
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def _load_spec(finish_id):
    path = _ASSET_DIR / f"{finish_id}_spec.png"
    return _load_spec_cached(finish_id, path.stat().st_mtime_ns)


def _paint_from_asset(finish_id, paint, shape, mask, pm):
    h, w = _shape2(shape)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    m3 = _mask2(mask, (h, w))[:, :, None]
    strength = np.clip(float(pm) * 0.98, 0.0, 1.0)
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - m3 * strength) + tex[:, :, :3] * (m3 * strength)
    return np.clip(paint, 0.0, 1.0).astype(np.float32)


def _finish_rng_seed(finish_id: str) -> int:
    """Stable 31-bit seed per finish for repeatable but distinct noise grids."""
    digest = hashlib.blake2s(finish_id.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest[:4], "big") % (2**31)


def _viva_mexico_paint_luma_edge(tex_rgb_hwc, mask_hw):
    """Rec.709 luma + normalized edge magnitude for DNA-aware sculpting."""
    gray = np.clip(
        tex_rgb_hwc
        @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32),
        0.0,
        1.0,
    )
    g255 = (gray * 255.0).astype(np.float32)
    lap = cv2.Laplacian(g255, cv2.CV_32F, ksize=3)
    emag = np.abs(lap)
    sel = mask_hw > 0.5
    if np.any(sel):
        hi = float(np.percentile(emag[sel], 98.0))
    else:
        hi = float(np.max(emag)) + 1e-6
    edge_n = np.clip(emag / (hi + 1e-6), 0.0, 1.0).astype(np.float32)
    return gray, edge_n


def _viva_mexico_highlight_crest(tex_rgb_hwc, mask_hw):
    """Paint-driven highlight crest (ridge residual): hero flashes + protect halo for void logic.

    Same idea as Agave's 'living water' strip — works on any plate with bright ridges / bands.
    Returns soft envelope, pin cores, dilated protect mask.
    """
    gray, _edge_n = _viva_mexico_paint_luma_edge(tex_rgb_hwc, mask_hw)
    m = mask_hw > 0.5
    dark = gray < (34.0 / 255.0)
    g255 = (gray * 255.0).astype(np.float32)
    base = cv2.GaussianBlur(g255, (0, 0), 4.2)
    crest = np.clip(g255 - base, 0.0, 255.0)

    if not np.any(m):
        z = np.zeros_like(gray, dtype=np.float32)
        return z, z, z.astype(bool)

    p85 = float(np.percentile(gray[m], 85.0))
    p93 = float(np.percentile(crest[m], 93.0))
    p97 = float(np.percentile(crest[m], 97.0))
    bright_band = m & (~dark) & (gray >= p85)
    ridge_band = m & (~dark) & (crest >= max(p93 * 0.42, 5.0))
    thin_ridge = m & (~dark) & (crest >= max(p97 * 0.55, 9.0))
    cand = ((bright_band & ridge_band) | thin_ridge).astype(np.uint8)

    k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thin = cv2.erode(cand, k3, iterations=1)
    core_u8 = cv2.erode(thin, k3, iterations=1)
    streak_core = core_u8.astype(bool) & m

    hi_crest = float(np.percentile(crest[m], 99.5)) + 1e-3
    intensity = np.clip(crest / hi_crest, 0.0, 1.0) * cand.astype(np.float32)
    streak_soft = np.clip(intensity * (1.0 - dark.astype(np.float32)), 0.0, 1.0)

    dil_core = cv2.dilate(core_u8, k5, iterations=2)
    protect = (dil_core.astype(bool) & m) | streak_core

    return streak_soft, streak_core.astype(np.float32), protect


def _pre_adjust_viva_mexico_spec(
    spec,
    tex_rgb_hwc,
    mask_hw,
    finish_id: str,
    *,
    dark_interior_flatten: float = 1.0,
    detail_scale: float | None = None,
):
    """Catalog-wide DNA-aligned spec enhancement for all Viva Mexico image monolithics.

    Finish DNA v2: *dark paint* = preview luma < 34 (8-bit). Applied before sm/mask multiply.

    ``dark_interior_flatten`` scales void-style flattening (default 1.0). Union Jacked uses
    <1.0 so procedural/baked metallic survives on ink-heavy navy plates that still carry
    bright filigree — otherwise DNA reads the whole field as ``void`` and wipes channel 0.

    - Void flatten on dark interiors only (edges protected).
    - Ridge-linked metallic / roughness / clearcoat for motif read and pearlescence.
    - Per-finish seeded sparse accents for diffuse rigs (distinct grids per id).
    - Highlight crest cores where paint has thin bright bands (optional per plate).
    - **Chromatic gloss steering**: paint RGB drives varied M/R/Cc triplets (warm/cool/green/yellow
      micro-reads) plus multi-octave micro-detail so adjacent pixels rarely share one gloss shade.
    """
    # Global spec “push”: baseline +18% vs prior pass (~+58% vs original); tune here first.
    DS = float(detail_scale) if detail_scale is not None else 1.59

    seed = _finish_rng_seed(finish_id)
    rng = np.random.default_rng(seed ^ 0xA5F0)
    rng_b = np.random.default_rng(seed ^ 0x3C91)
    rng_c = np.random.default_rng(seed ^ 0x71E4)
    rng_d = np.random.default_rng(seed ^ 0xBEEF)

    m = np.clip(mask_hw.astype(np.float32), 0.0, 1.0)
    M = spec[:, :, 0]
    R = spec[:, :, 1]
    Cc = spec[:, :, 2]

    gray, edge_n = _viva_mexico_paint_luma_edge(tex_rgb_hwc, mask_hw)
    # DNA: darkPaintPct uses absolute luma < 34 on loaded preview (8-bit style).
    dark_paint = gray < (34.0 / 255.0)
    dark_interior = dark_paint & (edge_n < 0.28)
    blend_v = (
        np.clip(dark_interior.astype(np.float32) * m * 0.93, 0.0, 0.96)
        * float(np.clip(dark_interior_flatten, 0.0, 2.0))
    )
    M[:] = np.clip(M * (1.0 - blend_v) + 8.0 * blend_v, 0.0, 255.0)
    R[:] = np.clip(R * (1.0 - blend_v) + 237.0 * blend_v, 15.0, 255.0)
    Cc[:] = np.clip(Cc * (1.0 - blend_v) + 9.0 * blend_v, 0.0, 255.0)

    h, w = M.shape
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)

    # Paint-chroma → spec triplets: varied gloss “temperature” (channel blends), not one flat green/red.
    tr = tex_rgb_hwc[:, :, 0]
    tg = tex_rgb_hwc[:, :, 1]
    tb = tex_rgb_hwc[:, :, 2]
    tmax = np.maximum(np.maximum(tr, tg), tb) + 1e-6
    warm_w = np.clip((tr - np.maximum(tg, tb) * 0.92) / tmax, 0.0, 1.0) * m
    cool_w = np.clip((tb - np.maximum(tr, tg) * 0.92) / tmax, 0.0, 1.0) * m
    green_dom = np.clip((tg - np.maximum(tr, tb)) / tmax, 0.0, 1.0) * m
    yellow_hint = (
        np.clip((tr + tg) * 0.5 - tb, 0.0, 1.0)
        * np.clip(tr - 0.18, 0.0, 1.0)
        * np.clip(tg - 0.18, 0.0, 1.0)
        * m
    )
    chrom_interior = 1.0 - dark_interior.astype(np.float32) * 0.55
    R[:] = np.clip(
        R
        - warm_w * (22.0 * DS) * chrom_interior
        + cool_w * (14.0 * DS) * chrom_interior,
        15.0,
        255.0,
    )
    M[:] = np.clip(
        M + warm_w * (14.0 * DS) * chrom_interior + cool_w * (-6.0 * DS) * chrom_interior,
        0.0,
        255.0,
    )
    Cc[:] = np.clip(
        Cc
        + warm_w * (-10.0 * DS) * chrom_interior
        + cool_w * (12.0 * DS) * chrom_interior,
        0.0,
        255.0,
    )
    phase_g = np.sin(xs * (380.0 + float(seed % 97)) + ys * (260.0 + float((seed >> 5) % 83)))
    g_split_w = green_dom * chrom_interior * (0.55 + 0.45 * edge_n)
    R[:] = np.clip(R + phase_g * (17.0 * DS) * g_split_w, 15.0, 255.0)
    Cc[:] = np.clip(Cc - phase_g * (11.0 * DS) * g_split_w, 0.0, 255.0)
    M[:] = np.clip(M + np.abs(phase_g) * (9.0 * DS) * g_split_w, 0.0, 255.0)

    # Pattern relief: emboss motif boundaries / internal drawing (alive, not uniform gloss).
    ridge_w = np.power(edge_n, 0.72) * m
    interior_suppress = (1.0 - dark_interior.astype(np.float32) * 0.65) * (
        1.0 - np.clip((gray - 0.08) / 0.18, 0.0, 1.0) * 0.25
    )
    pop = ridge_w * interior_suppress
    M[:] = np.clip(M + pop * (118.0 * DS), 0.0, 255.0)
    R[:] = np.clip(R - pop * (76.0 * DS), 15.0, 255.0)
    ridge_peak = pop > 0.22
    peak_mask = ridge_peak & (m > 0.5)
    Cc[:] = np.where(peak_mask, Cc * 0.22 + 16.0 * 0.78, Cc)
    Cc[:] = np.clip(Cc, 0.0, 255.0)

    gw = max(3, h // 5)
    gh = max(3, w // 5)
    grid = rng.random((gw, gh), dtype=np.float32)
    dots = cv2.resize((grid > 0.974).astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
    mid_tone = np.clip((gray - 0.20) / 0.52, 0.0, 1.0) * np.clip((0.70 - gray) / 0.48, 0.0, 1.0)
    flat_w = np.clip(1.0 - edge_n * 1.15, 0.0, 1.0)
    acc = dots * mid_tone * m * flat_w * (1.0 - dark_paint.astype(np.float32) * 0.92)
    M[:] = np.clip(M + acc * (102.0 * DS), 0.0, 255.0)
    R[:] = np.clip(R - acc * (66.0 * DS), 15.0, 255.0)
    hit_cc = acc > 0.35
    Cc[:] = np.where(hit_cc, Cc * 0.35 + 16.0 * 0.65, Cc)
    Cc[:] = np.clip(Cc, 0.0, 255.0)

    grid_b = rng_b.random((gw + 1, gh + 1), dtype=np.float32)
    dots_b = cv2.resize((grid_b > 0.977).astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
    shadow_band = np.clip((gray - 0.08) / 0.28, 0.0, 1.0) * np.clip((0.40 - gray) / 0.30, 0.0, 1.0)
    acc_b = dots_b * shadow_band * m * flat_w * (1.0 - dark_interior.astype(np.float32) * 0.55)
    M[:] = np.clip(M + acc_b * (74.0 * DS), 0.0, 255.0)
    R[:] = np.clip(R - acc_b * (50.0 * DS), 15.0, 255.0)
    hit_b = acc_b > 0.4
    Cc[:] = np.where(hit_b, Cc * 0.30 + 16.0 * 0.70, Cc)
    Cc[:] = np.clip(Cc, 0.0, 255.0)

    gw2 = max(4, h // 11)
    gh2 = max(4, w // 11)
    grid_c = rng_c.random((gw2 + 2, gh2 + 2), dtype=np.float32)
    dots_c = cv2.resize((grid_c > 0.974).astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
    flat_rig = np.clip((gray - 0.11) / 0.58, 0.0, 1.0) * np.clip((0.72 - gray) / 0.46, 0.0, 1.0)
    acc_c = dots_c * flat_rig * m * np.clip(1.0 - edge_n * 0.95, 0.15, 1.0)
    acc_c *= 1.0 - dark_paint.astype(np.float32) * 0.75
    M[:] = np.clip(M + acc_c * (62.0 * DS), 0.0, 255.0)
    R[:] = np.clip(R - acc_c * (44.0 * DS), 15.0, 255.0)
    hit_c = acc_c > 0.38
    Cc[:] = np.where(hit_c, Cc * 0.28 + 16.0 * 0.72, Cc)
    Cc[:] = np.clip(Cc, 0.0, 255.0)

    # Highlight crest(s): thin bright ridges → flash cores + wet envelope (Ch2=16 on peaks).
    streak_soft, streak_core_f, protect_lw = _viva_mexico_highlight_crest(tex_rgb_hwc, mask_hw)
    core_hard = (streak_core_f > 0.5) & (m > 0.5)
    if np.any(core_hard):
        M[:] = np.where(core_hard, np.maximum(M, 252.0), M)
        R[:] = np.where(core_hard, np.minimum(R, 36.0), R)
        Cc[:] = np.where(core_hard, 16.0, Cc)
    wet = streak_soft * m * (1.0 - dark_paint.astype(np.float32))
    wet *= 1.0 - core_hard.astype(np.float32) * 0.92
    M[:] = np.clip(M + wet * (92.0 * DS), 0.0, 255.0)
    R[:] = np.clip(R - wet * (74.0 * DS), 15.0, 255.0)
    Cc[:] = np.where(wet > 0.10, Cc * (1.0 - wet * 0.58) + 16.0 * wet * 0.58, Cc)
    Cc[:] = np.clip(Cc, 0.0, 255.0)
    if np.any(core_hard):
        k_ring = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cu8 = core_hard.astype(np.uint8)
        dil_h = cv2.dilate(cu8, k_ring, iterations=2)
        ring_lw = dil_h.astype(bool) & (~core_hard) & (m > 0.5)
        R[:] = np.where(ring_lw, np.clip(R + 36.0 * DS, 15.0, 255.0), R)
        M[:] = np.where(ring_lw, np.clip(M - 46.0 * DS, 0.0, 255.0), M)

    # Rare “gold / lemon” spec sparks where paint is warm-yellow (sparse; reads as hero flecks).
    spark_u = rng_d.random((h, w), dtype=np.float32)
    spark_mask = (
        (spark_u > 0.9955)
        & (yellow_hint > 0.12)
        & (m > 0.5)
        & (~dark_paint)
    ).astype(np.float32)
    spark_mask *= 0.55 + 0.45 * np.clip(edge_n * 1.4, 0.0, 1.0)
    M[:] = np.clip(M + spark_mask * (48.0 * DS), 0.0, 255.0)
    R[:] = np.clip(R - spark_mask * (40.0 * DS), 15.0, 255.0)
    Cc[:] = np.clip(Cc - spark_mask * (22.0 * DS), 0.0, 255.0)

    # Multi-octave micro grit: pixel-adjacent spec variance (hue-adaptive weights).
    oct_ph = float(seed % 4096) * (np.pi / 2048.0)
    oct_a = np.sin(xs * (103.0 + oct_ph) + ys * 67.3)
    oct_b = np.sin(xs * -89.1 + ys * 41.7 + oct_ph * 2.0)
    oct_c = np.sin(xs * 31.9 + ys * 127.4 - oct_ph)
    oct = oct_a * 0.45 + oct_b * 0.35 + oct_c * 0.20
    mic_g = (
        np.clip((gray - 0.12) / 0.78, 0.0, 1.0)
        * (1.0 - dark_paint.astype(np.float32) * 0.72)
        * m
        * (0.38 + 0.62 * edge_n)
    )
    hue_warm = np.clip(warm_w + yellow_hint * 0.85, 0.0, 1.0)
    hue_cool = np.clip(cool_w * 1.05, 0.0, 1.0)
    hue_green = np.clip(green_dom * 1.05, 0.0, 1.0)
    R[:] = np.clip(
        R + oct * (26.0 * DS) * mic_g * (0.65 + 0.22 * hue_warm - 0.12 * hue_cool + 0.18 * hue_green),
        15.0,
        255.0,
    )
    Cc[:] = np.clip(
        Cc + oct * (18.0 * DS) * mic_g * (0.55 + 0.35 * hue_green + 0.15 * hue_cool),
        0.0,
        255.0,
    )
    M[:] = np.clip(
        M + np.abs(oct) * (12.0 * DS) * mic_g * (0.45 + 0.55 * hue_warm),
        0.0,
        255.0,
    )
    curl = np.sin(xs * 211.0 + ys * -173.0 + oct_ph * 3.0) * np.cos(xs * 97.0 + ys * 149.0)
    R[:] = np.clip(R + curl * (14.0 * DS) * mic_g * yellow_hint, 15.0, 255.0)

    # Fine diagonal weave tied to finish id (breaks axis-aligned banding).
    weave = np.sin((xs + ys) * (240.0 + float(seed % 61))) * np.cos((xs - ys * 1.31) * (180.0 + float((seed >> 7) % 53)))
    weave_w = mic_g * (0.25 + 0.75 * chrom_interior)
    R[:] = np.clip(R + weave * (11.0 * DS) * weave_w, 15.0, 255.0)
    Cc[:] = np.clip(Cc + weave * (9.0 * DS) * weave_w * (0.6 + 0.4 * green_dom), 0.0, 255.0)

    # Nanoscopic crystalline fringe: mip0-only sparkle / hue shear (orthogonal to octave mesh).
    hf_ph = float((seed >> 11) % 4096) * (np.pi / 2048.0)
    nano = np.sin(xs * (587.0 + hf_ph) + ys * (443.0 - hf_ph * 0.7)) * np.cos(
        xs * (-521.0 + hf_ph * 0.35) + ys * (612.0 + hf_ph * 1.05)
    )
    nano_g = mic_g * (0.38 + 0.62 * chrom_interior) * np.clip(1.12 - gray * 0.28, 0.28, 1.05)
    R[:] = np.clip(R + nano * (14.0 * DS) * nano_g * (0.72 + 0.28 * hue_warm), 15.0, 255.0)
    Cc[:] = np.clip(Cc + nano * (11.0 * DS) * nano_g * (0.52 + 0.38 * hue_green + 0.14 * cool_w), 0.0, 255.0)
    M[:] = np.clip(M + np.abs(nano) * (8.5 * DS) * nano_g * (0.48 + 0.52 * hue_warm), 0.0, 255.0)

    # Light anisotropic ripple on mid/high paint only (living / angle); avoids uniform gloss wash.
    ripple = np.sin(xs * 54.7 + ys * 31.3) * np.sin(xs * -23.1 + ys * 47.8)
    rip_g = np.clip((gray - 0.16) / 0.72, 0.0, 1.0) * (1.0 - dark_paint.astype(np.float32) * 0.85)
    rip_w = rip_g * (0.35 + 0.65 * edge_n) * m * (1.0 - protect_lw.astype(np.float32) * 0.82)
    R[:] = np.clip(R + ripple * (18.0 * DS) * rip_w, 15.0, 255.0)

    sel = m > 0.5
    if np.any(sel):
        thr_m = float(np.percentile(M[sel], 58.0))
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        M_dil = cv2.dilate(M.astype(np.float32), k)
        core = sel & (M >= M_dil - 2.5) & (M >= thr_m)
        if np.any(core):
            ring_mask = cv2.dilate(core.astype(np.uint8), k).astype(bool) & (~core) & sel
            R[:] = np.where(core, np.clip(R - 34.0 * DS, 15.0, 255.0), R)
            M[:] = np.where(core, np.clip(M + 26.0 * DS, 0.0, 255.0), M)
            Cc[:] = np.where(core, np.clip(Cc * 0.45 + 16.0 * 0.55, 0.0, 255.0), Cc)
            R[:] = np.where(ring_mask, np.clip(R + 30.0 * DS, 15.0, 255.0), R)
            M[:] = np.where(ring_mask, np.clip(M - 18.0 * DS, 0.0, 255.0), M)


def _post_adjust_viva_mexico_spec(
    spec_u8,
    tex_rgb_hwc,
    mask_hw,
    *,
    void_metallic_max: float = 11.0,
    void_roughness_min: float = 222.0,
    void_clearcoat_max: float = 15.0,
):
    """Post composite: DNA void on dark paint; preserve ridges + highlight crest corridor."""
    m = np.clip(mask_hw.astype(np.float32), 0.0, 1.0)
    s = spec_u8.astype(np.float32)
    gray, edge_n = _viva_mexico_paint_luma_edge(tex_rgb_hwc, mask_hw)
    _ss, _sc, protect_lw = _viva_mexico_highlight_crest(tex_rgb_hwc, mask_hw)
    sel = m > 0.5
    dark_paint = gray < (34.0 / 255.0)
    ridge_protect = edge_n > 0.38
    void_px = sel & dark_paint & (~ridge_protect) & (~protect_lw)
    if np.any(void_px):
        s[:, :, 0] = np.where(void_px, np.minimum(s[:, :, 0], float(void_metallic_max)), s[:, :, 0])
        s[:, :, 1] = np.where(void_px, np.maximum(s[:, :, 1], float(void_roughness_min)), s[:, :, 1])
        s[:, :, 2] = np.where(void_px, np.minimum(s[:, :, 2], float(void_clearcoat_max)), s[:, :, 2])
    s[:, :, 0] = np.clip(s[:, :, 0], 0, 255)
    s[:, :, 1] = np.clip(s[:, :, 1], 15, 255)
    s[:, :, 2] = np.clip(s[:, :, 2], 8, 255)
    s[:, :, 3] = 255
    return np.clip(np.round(s), 0, 255).astype(np.uint8)


def _spec_from_asset(finish_id, shape, mask, sm):
    h, w = _shape2(shape)
    spec = _resize(_load_spec(finish_id), (h, w), cv2.INTER_AREA).astype(np.float32)
    m = _mask2(mask, (h, w))
    outside = 1.0 - m

    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    _pre_adjust_viva_mexico_spec(spec, tex, m, finish_id)

    spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m + 4.0 * outside, 0, 255)
    spec[:, :, 1] = np.clip(spec[:, :, 1] * m + 120.0 * outside, 15, 255)
    spec[:, :, 2] = np.clip(spec[:, :, 2] * m + 80.0 * outside, 16, 255)
    spec[:, :, 3] = 255
    out = spec.astype(np.uint8)
    out = _post_adjust_viva_mexico_spec(out, tex, m)
    return out


def _make_paint_fn(finish_id):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        return _paint_from_asset(finish_id, paint, shape, mask, pm)

    paint_fn.__name__ = f"paint_{finish_id}"
    return paint_fn


def _make_spec_fn(finish_id):
    def spec_fn(shape, mask, seed, sm):
        return _spec_from_asset(finish_id, shape, mask, sm)

    spec_fn.__name__ = f"spec_{finish_id}"
    return spec_fn


VIVA_MEXICO_MONOLITHICS = {
    finish_id: (_make_spec_fn(finish_id), _make_paint_fn(finish_id))
    for finish_id in _FINISH_IDS
}
