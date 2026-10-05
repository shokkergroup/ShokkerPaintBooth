"""
Shokker Color Clash Expansion — 25 Harsh Gradient Finishes
============================================================
Intentionally clashing, punk, neon-vs-dark color gradients.
Layout: dominant center color, contrasting edges (left-to-right).
Each finish has a UNIQUE spec character (chrome, matte, satin, mixed zones, etc.)

Spec Contract: spec functions return uint8 [H,W,4] RGBA
  Channel 0 (R): Roughness (0=smooth/glossy, 255=rough/matte)
  Channel 1 (G): Metallic  (0=non-metallic, 255=fully metallic)
  Channel 2 (B): Reserved/specular
  Channel 3 (A): Usually 255

Paint Contract: paint functions modify float32 [H,W,3] paint array in-place
  pm=0 => return paint unchanged (PM Identity Contract)

Author: Shokker Engine — Color Clash Series
"""

from collections import OrderedDict

import numpy as np

# ----------------------------------------------------------------------------
# PERF (2026-06-13): the Color Clash V2 finishes build ~30 transcendental
# fields over the full 2048x2048 grid in BOTH the paint and spec passes, which
# pushed every finish to 16-24s combined (owner budget is ~1s, >3s = FAIL).
# numpy ufuncs are single-threaded but RELEASE THE GIL, so we run the purely
# elementwise field/motif math over horizontal row-chunks across a small thread
# pool. Each chunk evaluates the IDENTICAL op sequence on its own rows, so the
# assembled result is BIT-IDENTICAL to the serial version (verified via
# np.array_equal at 2048) while running ~3x faster on multi-core hosts.
# The only cross-row op (np.gradient on `body`) is deliberately kept serial on
# the fully-assembled array, so it too is unchanged.
# ----------------------------------------------------------------------------
import os as _os
from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor

_CC_NCHUNK = min(8, max(1, (_os.cpu_count() or 4)))
_CC_POOL = _ThreadPoolExecutor(max_workers=_CC_NCHUNK) if _CC_NCHUNK > 1 else None


def _cc_parallel_rows(fn, h, *, min_rows=256):
    """Run `fn(row_start, row_stop)` over `_CC_NCHUNK` contiguous row bands in
    parallel and return the band slices used. `fn` must write into shared output
    arrays for its [row_start:row_stop) band only (no cross-row coupling), so the
    assembled result is bit-identical to a single full-array evaluation.
    Falls back to a single serial call for small images or no pool."""
    if _CC_POOL is None or h < min_rows:
        fn(0, h)
        return
    step = (h + _CC_NCHUNK - 1) // _CC_NCHUNK
    bands = [(i * step, min(i * step + step, h)) for i in range(_CC_NCHUNK)]
    bands = [(s, e) for (s, e) in bands if s < e]
    list(_CC_POOL.map(lambda be: fn(be[0], be[1]), bands))


# ================================================================
# HELPERS
# ================================================================

def _gradient_lr(shape):
    """Left-to-right gradient 0..1 across width."""
    h, w = shape[:2]
    return np.tile(np.linspace(0, 1, w, dtype=np.float32), (h, 1))


def _center_weight(shape):
    """Center-dominant weight: 1 at center, 0 at edges (left-to-right)."""
    h, w = shape[:2]
    x = np.linspace(-1, 1, w, dtype=np.float32)
    # Bell curve centered at 0
    cw = np.exp(-3.0 * x * x)
    return np.tile(cw, (h, 1))


def _edge_weight(shape):
    """Edge weight: 1 at edges, 0 at center (complement of center_weight)."""
    return 1.0 - _center_weight(shape)


def _apply_clash_gradient(paint, shape, mask, center_rgb, edge_rgb, seed, pm, bb):
    """Apply center-dominant, edge-contrasting L-R gradient to paint.
    PM Identity Contract: pm=0 returns paint unchanged.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint

    cw = _center_weight(shape)
    ew = _edge_weight(shape)

    for ch in range(3):
        target = cw * center_rgb[ch] + ew * edge_rgb[ch]
        paint[:, :, ch] = np.clip(
            paint[:, :, ch] * (1.0 - pm * mask) + target * pm * mask,
            0, 1
        )

    # Apply base brightness boost — normalize bb to 2D
    bb_2d = np.mean(bb[:,:,:3], axis=2) if hasattr(bb, 'ndim') and bb.ndim == 3 else (bb if hasattr(bb, 'ndim') and bb.ndim == 2 else np.full(paint.shape[:2], float(np.mean(bb)), dtype=np.float32))
    paint = np.clip(paint + bb_2d[:, :, np.newaxis] * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


def _uniform_spec(shape, mask, sm, roughness, metallic, specular=16):
    """Build a uniform spec map with given roughness/metallic values.
    iRacing channel order: 0=Metallic, 1=Roughness, 2=Clearcoat, 3=SpecMask."""
    h, w = shape[:2]
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    M_arr = np.clip(metallic * mask * sm, 0, 255)
    R_arr = np.clip(roughness * mask * sm, 0, 255)
    # Iron rule: R >= 15 for non-chrome (M < 240), CC >= 16
    R_arr = np.where((M_arr < 240) & (mask > 0.5), np.maximum(R_arr, 15), R_arr)
    spec[:, :, 0] = M_arr.astype(np.uint8)    # M = channel 0
    spec[:, :, 1] = R_arr.astype(np.uint8)    # R = channel 1
    spec[:, :, 2] = max(int(specular) if np.isscalar(specular) else 16, 16)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


def _gradient_spec(shape, mask, sm, r_center, m_center, r_edge, m_edge, specular=16):
    """Build a spec map that varies from center to edges (L-R).
    iRacing: 0=Metallic, 1=Roughness, 2=Clearcoat, 3=SpecMask."""
    h, w = shape[:2]
    cw = _center_weight(shape)
    ew = _edge_weight(shape)

    roughness = cw * r_center + ew * r_edge
    metallic = cw * m_center + ew * m_edge

    spec = np.zeros((h, w, 4), dtype=np.uint8)
    M_arr = np.clip(metallic * mask * sm, 0, 255)
    R_arr = np.clip(roughness * mask * sm, 0, 255)
    # Iron rule: R >= 15 for non-chrome (M < 240), CC >= 16
    R_arr = np.where((M_arr < 240) & (mask > 0.5), np.maximum(R_arr, 15), R_arr)
    spec[:, :, 0] = M_arr.astype(np.uint8)    # M = channel 0
    spec[:, :, 1] = R_arr.astype(np.uint8)    # R = channel 1
    spec[:, :, 2] = max(int(specular) if np.isscalar(specular) else 16, 16)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


def _multizone_spec(shape, mask, sm, zones, specular=16):
    """Build spec with multiple zones across L-R axis.
    zones: list of (roughness, metallic) tuples, evenly distributed.
    """
    h, w = shape[:2]
    n = len(zones)
    roughness = np.zeros((h, w), dtype=np.float32)
    metallic = np.zeros((h, w), dtype=np.float32)
    x = np.linspace(0, 1, w, dtype=np.float32)

    for i in range(n - 1):
        start = i / (n - 1)
        end = (i + 1) / (n - 1)
        blend = np.clip((x - start) / (end - start + 1e-8), 0, 1)
        zone_mask_1d = ((x >= start) & (x <= end)).astype(np.float32)
        r_val = zones[i][0] * (1 - blend) + zones[i + 1][0] * blend
        m_val = zones[i][1] * (1 - blend) + zones[i + 1][1] * blend
        roughness += np.tile(r_val * zone_mask_1d, (h, 1))
        metallic += np.tile(m_val * zone_mask_1d, (h, 1))

    # Remove overlapping accumulations by just doing a clean interpolation
    roughness = np.zeros((h, w), dtype=np.float32)
    metallic = np.zeros((h, w), dtype=np.float32)
    positions = np.linspace(0, 1, n, dtype=np.float32)
    r_vals = np.array([z[0] for z in zones], dtype=np.float32)
    m_vals = np.array([z[1] for z in zones], dtype=np.float32)
    r_interp = np.interp(x, positions, r_vals)
    m_interp = np.interp(x, positions, m_vals)
    roughness = np.tile(r_interp, (h, 1))
    metallic = np.tile(m_interp, (h, 1))

    spec = np.zeros((h, w, 4), dtype=np.uint8)
    M_arr = np.clip(metallic * mask * sm, 0, 255)
    R_arr = np.clip(roughness * mask * sm, 0, 255)
    # Iron rule: R >= 15 for non-chrome (M < 240), CC >= 16
    R_arr = np.where((M_arr < 240) & (mask > 0.5), np.maximum(R_arr, 15), R_arr)
    spec[:, :, 0] = M_arr.astype(np.uint8)    # M = channel 0
    spec[:, :, 1] = R_arr.astype(np.uint8)    # R = channel 1
    spec[:, :, 2] = max(int(specular) if np.isscalar(specular) else 16, 16)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


def _add_noise_to_spec(spec, shape, seed, intensity=8):
    """Add subtle noise to spec for realism. Enforces R>=15 for non-chrome."""
    rng = np.random.RandomState(seed)
    noise = rng.randint(-intensity, intensity + 1, size=(shape[0], shape[1]), dtype=np.int16)
    for ch in range(2):  # roughness and metallic only
        spec[:, :, ch] = np.clip(spec[:, :, ch].astype(np.int16) + noise, 0, 255).astype(np.uint8)
    # GGX floor: R>=15 for non-chrome (M<240)
    non_chrome = spec[:, :, 0] < 240
    spec[:, :, 1] = np.where(non_chrome, np.maximum(spec[:, :, 1], 15), spec[:, :, 1]).astype(np.uint8)
    return spec


# ================================================================
# 1. cc_neon_bruise — Electric purple center, toxic green edges — CHROME
# ================================================================

def spec_cc_neon_bruise(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=15, metallic=250)
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_neon_bruise(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.55, 0.0, 0.85),   # electric purple
                                  edge_rgb=(0.2, 0.95, 0.1),      # toxic green
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 2. cc_acid_burn — Acid yellow center, deep purple edges — MATTE
# ================================================================

def spec_cc_acid_burn(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=220, metallic=15)
    spec = _add_noise_to_spec(spec, shape, seed, 6)
    spec[:,:,1] = np.maximum(spec[:,:,1], 15)  # R≥15 roughness floor (non-chrome)
    return spec

def paint_cc_acid_burn(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.95, 0.95, 0.0),   # acid yellow
                                  edge_rgb=(0.25, 0.0, 0.5),      # deep purple
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 3. cc_blood_orange — Blood red center, electric blue edges — SATIN
# ================================================================

def spec_cc_blood_orange(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=100, metallic=130)
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_blood_orange(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.7, 0.05, 0.0),    # blood red
                                  edge_rgb=(0.0, 0.3, 0.95),      # electric blue
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 4. cc_toxic_sunset — Hot pink center, acid green edges — CHROME fading to MATTE
# ================================================================

def spec_cc_toxic_sunset(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=15, m_center=245,    # chrome center
                          r_edge=210, m_edge=20)        # matte edges
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_toxic_sunset(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.1, 0.55),    # hot pink
                                  edge_rgb=(0.3, 0.95, 0.05),     # acid green
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 5. cc_electric_conflict — Cyan center, magenta edges — HIGH GLOSS
# ================================================================

def spec_cc_electric_conflict(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=25, metallic=200)
    return _add_noise_to_spec(spec, shape, seed, 4)

def paint_cc_electric_conflict(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.0, 0.9, 0.95),    # cyan
                                  edge_rgb=(0.9, 0.0, 0.7),       # magenta
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 6. cc_nuclear_dawn — Nuclear green center, crimson edges — ROUGH MATTE
# ================================================================

def spec_cc_nuclear_dawn(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=240, metallic=15)
    return _add_noise_to_spec(spec, shape, seed, 8)

def paint_cc_nuclear_dawn(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.15, 0.95, 0.0),   # nuclear green
                                  edge_rgb=(0.7, 0.0, 0.05),      # crimson
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 7. cc_voltage_split — Electric yellow center, deep navy edges — CHROME center, MATTE edges
# ================================================================

def spec_cc_voltage_split(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=10, m_center=250,    # chrome center
                          r_edge=230, m_edge=10)        # matte edges
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_voltage_split(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.95, 0.0),    # electric yellow
                                  edge_rgb=(0.0, 0.05, 0.3),      # deep navy
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 8. cc_coral_venom — Coral center, viper green edges — SATIN
# ================================================================

def spec_cc_coral_venom(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=90, metallic=140)
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_coral_venom(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.4, 0.3),     # coral
                                  edge_rgb=(0.0, 0.6, 0.1),       # viper green
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 9. cc_ultraviolet_burn — UV purple center, safety orange edges — SEMI-GLOSS
# ================================================================

def spec_cc_ultraviolet_burn(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=60, metallic=170)
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_ultraviolet_burn(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.4, 0.0, 0.9),     # UV purple
                                  edge_rgb=(1.0, 0.5, 0.0),       # safety orange
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 10. cc_rust_vs_ice — Rust orange center, ice blue edges — MATTE center, CHROME edges
# ================================================================

def spec_cc_rust_vs_ice(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=200, m_center=30,    # matte center
                          r_edge=15, m_edge=240)        # chrome edges
    return _add_noise_to_spec(spec, shape, seed, 7)

def paint_cc_rust_vs_ice(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.7, 0.3, 0.05),    # rust orange
                                  edge_rgb=(0.7, 0.85, 0.95),     # ice blue
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 11. cc_magma_freeze — Molten red center, arctic white edges — MIXED (chrome/matte/satin zones)
# ================================================================

def spec_cc_magma_freeze(shape, mask, seed, sm):
    # 5 zones: chrome | satin | matte | satin | chrome
    zones = [
        (15, 245),   # chrome (left edge)
        (100, 130),  # satin
        (200, 20),   # matte (center)
        (100, 130),  # satin
        (15, 245),   # chrome (right edge)
    ]
    spec = _multizone_spec(shape, mask, sm, zones)
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_magma_freeze(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.9, 0.15, 0.0),    # molten red
                                  edge_rgb=(0.92, 0.95, 1.0),     # arctic white
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 12. cc_punk_static — Hot pink center, black & white static edges — FLAT MATTE
# ================================================================

def spec_cc_punk_static(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=235, metallic=10)
    # Add heavier noise for static feel at edges
    rng = np.random.RandomState(seed + 100)
    ew = _edge_weight(shape)
    noise = (rng.randint(0, 30, size=(shape[0], shape[1])) * ew).astype(np.int16)
    spec[:, :, 0] = np.clip(spec[:, :, 0].astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return spec

def paint_cc_punk_static(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint
    cw = _center_weight(shape)
    ew = _edge_weight(shape)
    # Center: hot pink
    for ch, val in enumerate([1.0, 0.05, 0.5]):
        paint[:, :, ch] = np.clip(
            paint[:, :, ch] * (1.0 - pm * mask * cw) + val * pm * mask * cw,
            0, 1)
    # Edges: black & white static
    rng = np.random.RandomState(seed + 200)
    static = rng.choice([0.0, 1.0], size=(shape[0], shape[1])).astype(np.float32)
    for ch in range(3):
        paint[:, :, ch] = np.clip(
            paint[:, :, ch] * (1.0 - pm * mask * ew) + static * pm * mask * ew,
            0, 1)
    bb_2d = np.mean(bb[:,:,:3], axis=2) if hasattr(bb, 'ndim') and bb.ndim == 3 else (bb if hasattr(bb, 'ndim') and bb.ndim == 2 else np.full(paint.shape[:2], float(np.mean(bb)), dtype=np.float32))
    paint = np.clip(paint + bb_2d[:, :, np.newaxis] * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# 13. cc_radioactive — Neon green center, deep maroon edges — GLOSS
# ================================================================

def spec_cc_radioactive(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=35, metallic=180)
    return _add_noise_to_spec(spec, shape, seed, 4)

def paint_cc_radioactive(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.1, 1.0, 0.05),    # neon green
                                  edge_rgb=(0.35, 0.0, 0.05),     # deep maroon
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 14. cc_bruised_sky — Deep purple center, sickly yellow edges — SATIN to MATTE
# ================================================================

def spec_cc_bruised_sky(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=90, m_center=140,    # satin center
                          r_edge=210, m_edge=25)        # matte edges
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_bruised_sky(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.3, 0.0, 0.55),    # deep purple
                                  edge_rgb=(0.85, 0.85, 0.2),     # sickly yellow
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 15. cc_chemical_spill — Lime green center, chemical orange edges — CHROME
# ================================================================

def spec_cc_chemical_spill(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=20, metallic=245)
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_chemical_spill(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.4, 0.95, 0.0),    # lime green
                                  edge_rgb=(1.0, 0.45, 0.0),      # chemical orange
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 16. cc_deep_friction — Deep red center, electric teal edges — ROUGH TEXTURE
# ================================================================

def spec_cc_deep_friction(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=235, metallic=70)
    # Add heavy grain for texture
    rng = np.random.RandomState(seed + 300)
    grain = rng.randint(-15, 16, size=(shape[0], shape[1]), dtype=np.int16)
    spec[:, :, 0] = np.clip(spec[:, :, 0].astype(np.int16) + grain, 0, 255).astype(np.uint8)
    return spec

def paint_cc_deep_friction(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.55, 0.0, 0.0),    # deep red
                                  edge_rgb=(0.0, 0.85, 0.75),     # electric teal
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 17. cc_plasma_edge — White-hot center, plasma blue edges — ULTRA CHROME
# ================================================================

def spec_cc_plasma_edge(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=5, metallic=255)
    return _add_noise_to_spec(spec, shape, seed, 3)

def paint_cc_plasma_edge(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.98, 0.9),    # white-hot
                                  edge_rgb=(0.1, 0.2, 0.95),      # plasma blue
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 18. cc_candy_poison — Candy pink center, poison black-green edges — GLOSS to MATTE
# ================================================================

def spec_cc_candy_poison(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=30, m_center=190,    # gloss center
                          r_edge=220, m_edge=30)        # matte edges
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_candy_poison(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.4, 0.65),    # candy pink
                                  edge_rgb=(0.05, 0.15, 0.05),    # poison black-green
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 19. cc_solar_clash — Solar gold center, void black edges — CHROME center only
# ================================================================

def spec_cc_solar_clash(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=10, m_center=250,    # chrome center
                          r_edge=120, m_edge=60)        # semi-matte edges
    return _add_noise_to_spec(spec, shape, seed, 5)

def paint_cc_solar_clash(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.8, 0.1),     # solar gold
                                  edge_rgb=(0.02, 0.02, 0.02),    # void black
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 20. cc_fever_dream — Fever red center, hallucination purple edges — MULTI-FINISH (4 zones)
# ================================================================

def spec_cc_fever_dream(shape, mask, seed, sm):
    # 4 distinct zones: matte | chrome | satin | rough
    zones = [
        (210, 20),   # matte (left edge)
        (15, 245),   # chrome
        (90, 130),   # satin (center-right)
        (230, 50),   # rough (right edge)
    ]
    spec = _multizone_spec(shape, mask, sm, zones)
    spec = _add_noise_to_spec(spec, shape, seed, 7)
    spec[:,:,1] = np.maximum(spec[:,:,1], 15)  # R≥15 roughness floor (non-chrome)
    return spec

def paint_cc_fever_dream(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.9, 0.1, 0.05),    # fever red
                                  edge_rgb=(0.5, 0.0, 0.75),      # hallucination purple
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 21. cc_digital_rot — Digital cyan center, rot brown edges — SATIN
# ================================================================

def spec_cc_digital_rot(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=85, metallic=145)
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_digital_rot(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.0, 0.9, 0.9),     # digital cyan
                                  edge_rgb=(0.4, 0.2, 0.05),      # rot brown
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 22. cc_flash_burn — Flash white center, burn orange-red edges — CHROME to ROUGH
# ================================================================

def spec_cc_flash_burn(shape, mask, seed, sm):
    spec = _gradient_spec(shape, mask, sm,
                          r_center=10, m_center=240,    # chrome center
                          r_edge=225, m_edge=60)        # rough edges
    return _add_noise_to_spec(spec, shape, seed, 6)

def paint_cc_flash_burn(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 1.0, 0.95),    # flash white
                                  edge_rgb=(0.9, 0.3, 0.0),       # burn orange-red
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 23. cc_venom_strike — Venom green center, black edges — HIGH GLOSS
# ================================================================

def spec_cc_venom_strike(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=20, metallic=210)
    return _add_noise_to_spec(spec, shape, seed, 4)

def paint_cc_venom_strike(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(0.15, 0.85, 0.0),   # venom green
                                  edge_rgb=(0.02, 0.02, 0.02),    # black
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 24. cc_neon_war — Neon orange center, neon blue edges — CHROME
# ================================================================

def spec_cc_neon_war(shape, mask, seed, sm):
    spec = _uniform_spec(shape, mask, sm, roughness=15, metallic=248)
    return _add_noise_to_spec(spec, shape, seed, 4)

def paint_cc_neon_war(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _apply_clash_gradient(paint, shape, mask,
                                  center_rgb=(1.0, 0.4, 0.0),     # neon orange
                                  edge_rgb=(0.0, 0.3, 1.0),       # neon blue
                                  seed=seed, pm=pm, bb=bb)


# ================================================================
# 25. cc_chaos_theory — Shifting rainbow center, black edges — MIXED EVERYTHING
# ================================================================

def spec_cc_chaos_theory(shape, mask, seed, sm):
    # 7 zones cycling through all finish types
    zones = [
        (230, 15),   # rough matte (left edge)
        (15, 250),   # chrome
        (90, 130),   # satin
        (50, 200),   # semi-gloss (center)
        (200, 40),   # matte
        (10, 245),   # chrome
        (230, 15),   # rough matte (right edge)
    ]
    spec = _multizone_spec(shape, mask, sm, zones)
    spec = _add_noise_to_spec(spec, shape, seed, 8)
    spec[:,:,1] = np.maximum(spec[:,:,1], 15)  # R≥15 roughness floor (non-chrome)
    return spec

def paint_cc_chaos_theory(paint, shape, mask, seed, pm, bb):
    """Rainbow center with black edges — uses multi-band color injection."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint

    h, w = shape[:2]
    cw = _center_weight(shape)
    ew = _edge_weight(shape)

    # Rainbow bands across center
    x = np.linspace(0, 2 * np.pi, w, dtype=np.float32)
    rainbow_r = np.tile(np.clip(np.sin(x) * 0.5 + 0.5, 0, 1), (h, 1))
    rainbow_g = np.tile(np.clip(np.sin(x + 2.094) * 0.5 + 0.5, 0, 1), (h, 1))  # +120 deg
    rainbow_b = np.tile(np.clip(np.sin(x + 4.189) * 0.5 + 0.5, 0, 1), (h, 1))  # +240 deg

    for ch, rainbow in enumerate([rainbow_r, rainbow_g, rainbow_b]):
        center_color = rainbow * cw
        edge_color = 0.02 * ew  # near-black edges
        target = center_color + edge_color
        paint[:, :, ch] = np.clip(
            paint[:, :, ch] * (1.0 - pm * mask) + target * pm * mask,
            0, 1)

    bb_2d = np.mean(bb[:,:,:3], axis=2) if hasattr(bb, 'ndim') and bb.ndim == 3 else (bb if hasattr(bb, 'ndim') and bb.ndim == 2 else np.full(paint.shape[:2], float(np.mean(bb)), dtype=np.float32))
    paint = np.clip(paint + bb_2d[:, :, np.newaxis] * 0.5 * mask[:, :, np.newaxis], 0, 1)
    return paint


# ================================================================
# OWNER-CONFIRMED COLOR CLASH V2 - dynamic, fine, ultra-gradient
# ================================================================

def _cc_stable_seed(text):
    acc = 2166136261
    for ch in text:
        acc = (acc ^ ord(ch)) * 16777619
        acc &= 0xFFFFFFFF
    return acc


_CC_COORD_CACHE = OrderedDict()
_CC_COORD_CACHE_MAX = 4


def _cc_xy(shape):
    h, w = shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    x = (x / max(w - 1, 1)) * 2.0 - 1.0
    y = (y / max(h - 1, 1)) * 2.0 - 1.0
    return x, y


def _cc_coords(shape):
    key = (int(shape[0]), int(shape[1]))
    cached = _CC_COORD_CACHE.get(key)
    if cached is not None:
        _CC_COORD_CACHE.move_to_end(key)
        return cached
    x, y = _cc_xy(shape)
    r = np.sqrt(x * x + y * y).astype(np.float32)
    theta = np.arctan2(y, x).astype(np.float32)
    cached = (x, y, r, theta)
    _CC_COORD_CACHE[key] = cached
    if len(_CC_COORD_CACHE) > _CC_COORD_CACHE_MAX:
        _CC_COORD_CACHE.popitem(last=False)
    return cached


def _cc_bb2d(bb, shape):
    if hasattr(bb, "ndim") and bb.ndim == 3:
        return np.mean(bb[:, :, :3], axis=2).astype(np.float32)
    if hasattr(bb, "ndim") and bb.ndim == 2:
        return bb.astype(np.float32)
    return np.full(shape[:2], float(np.mean(bb)), dtype=np.float32)


def _cc_profile(center, edge, accent, mode, freq, twist, metal, rough, clearcoat, balance=1.0):
    return {
        "center": tuple(float(v) for v in center),
        "edge": tuple(float(v) for v in edge),
        "accent": tuple(float(v) for v in accent),
        "mode": mode,
        "motif": "linear",
        "freq": float(freq),
        "twist": float(twist),
        "metal": tuple(float(v) for v in metal),
        "rough": tuple(float(v) for v in rough),
        "clearcoat": tuple(float(v) for v in clearcoat),
        "balance": float(balance),
    }


def _cc_dynamic_fields(item_id, profile, shape, seed):
    x, y, r, theta = _cc_coords(shape)
    sid = _cc_stable_seed(item_id) + int(seed)
    phase = (sid % 6283) / 1000.0
    freq = profile["freq"]
    twist = profile["twist"]
    mode = profile["mode"]

    h = x.shape[0]
    body = np.empty(x.shape, np.float32)
    micro = np.empty(x.shape, np.float32)

    # PERF: the per-pixel field math below is identical to the original serial
    # form; we evaluate it over contiguous row bands in parallel (numpy ufuncs
    # release the GIL) and write each band into the shared `body`/`micro`
    # buffers. Result is bit-identical (verified via np.array_equal @2048).
    def _band(rs, re):
        xb = x[rs:re]; yb = y[rs:re]; rb = r[rs:re]; tb = theta[rs:re]
        microb = 0.5 + 0.5 * np.sin((xb + yb) * 143.0 + np.sin(tb * 9.0) + phase * 1.9)
        micro[rs:re] = microb
        # Compute only the constituent fields the selected mode actually uses.
        if mode == "plasma":
            waves = 0.5 + 0.5 * np.sin(xb * (freq * 4.1) + yb * (freq * 2.7) + np.sin(tb * twist + phase) * 1.7 + phase)
            ribbons = 0.5 + 0.5 * np.sin((xb - yb) * (freq * 5.3) + rb * twist * 5.0 + phase * 1.31)
            rings = 0.5 + 0.5 * np.sin(rb * freq * 19.0 - tb * twist + phase * 0.71)
            shard = np.power(np.clip(1.0 - np.abs(np.sin((xb * twist - yb * freq) * 8.0 + phase)), 0, 1), 4.0)
            b = np.clip(waves * 0.38 + ribbons * 0.26 + rings * 0.24 + shard * 0.22, 0, 1)
        elif mode == "spill":
            waves = 0.5 + 0.5 * np.sin(xb * (freq * 4.1) + yb * (freq * 2.7) + np.sin(tb * twist + phase) * 1.7 + phase)
            ribbons = 0.5 + 0.5 * np.sin((xb - yb) * (freq * 5.3) + rb * twist * 5.0 + phase * 1.31)
            rings = 0.5 + 0.5 * np.sin(rb * freq * 19.0 - tb * twist + phase * 0.71)
            shard = np.power(np.clip(1.0 - np.abs(np.sin((xb * twist - yb * freq) * 8.0 + phase)), 0, 1), 4.0)
            cellular = np.maximum(shard, np.power(np.clip(ribbons, 0, 1), 2.4))
            b = np.clip(cellular * 0.46 + waves * 0.28 + rings * 0.16 + microb * 0.10, 0, 1)
        elif mode == "electric":
            ribbons = 0.5 + 0.5 * np.sin((xb - yb) * (freq * 5.3) + rb * twist * 5.0 + phase * 1.31)
            shard = np.power(np.clip(1.0 - np.abs(np.sin((xb * twist - yb * freq) * 8.0 + phase)), 0, 1), 4.0)
            scan = np.power(np.clip(1.0 - np.abs(np.sin((yb * freq * 18.0) + phase)), 0, 1), 7.0)
            fine = 0.5 + 0.5 * np.sin(xb * 91.0 + yb * (73.0 + freq) + phase)
            b = np.clip(scan * 0.40 + shard * 0.34 + ribbons * 0.18 + fine * 0.12, 0, 1)
        elif mode == "rot":
            waves = 0.5 + 0.5 * np.sin(xb * (freq * 4.1) + yb * (freq * 2.7) + np.sin(tb * twist + phase) * 1.7 + phase)
            ribbons = 0.5 + 0.5 * np.sin((xb - yb) * (freq * 5.3) + rb * twist * 5.0 + phase * 1.31)
            rings = 0.5 + 0.5 * np.sin(rb * freq * 19.0 - tb * twist + phase * 0.71)
            shard = np.power(np.clip(1.0 - np.abs(np.sin((xb * twist - yb * freq) * 8.0 + phase)), 0, 1), 4.0)
            cellular = np.maximum(shard, np.power(np.clip(ribbons, 0, 1), 2.4))
            fine = 0.5 + 0.5 * np.sin(xb * 91.0 + yb * (73.0 + freq) + phase)
            b = np.clip((1.0 - rings) * 0.34 + cellular * 0.34 + fine * 0.18 + waves * 0.14, 0, 1)
        elif mode == "magma":
            waves = 0.5 + 0.5 * np.sin(xb * (freq * 4.1) + yb * (freq * 2.7) + np.sin(tb * twist + phase) * 1.7 + phase)
            rings = 0.5 + 0.5 * np.sin(rb * freq * 19.0 - tb * twist + phase * 0.71)
            shard = np.power(np.clip(1.0 - np.abs(np.sin((xb * twist - yb * freq) * 8.0 + phase)), 0, 1), 4.0)
            b = np.clip(np.power(rings, 2.0) * 0.36 + shard * 0.32 + waves * 0.22 + microb * 0.12, 0, 1)
        elif mode == "venom":
            ribbons = 0.5 + 0.5 * np.sin((xb - yb) * (freq * 5.3) + rb * twist * 5.0 + phase * 1.31)
            shard = np.power(np.clip(1.0 - np.abs(np.sin((xb * twist - yb * freq) * 8.0 + phase)), 0, 1), 4.0)
            scan = np.power(np.clip(1.0 - np.abs(np.sin((yb * freq * 18.0) + phase)), 0, 1), 7.0)
            b = np.clip(shard * 0.42 + ribbons * 0.22 + scan * 0.20 + microb * 0.16, 0, 1)
        elif mode == "storm":
            waves = 0.5 + 0.5 * np.sin(xb * (freq * 4.1) + yb * (freq * 2.7) + np.sin(tb * twist + phase) * 1.7 + phase)
            rings = 0.5 + 0.5 * np.sin(rb * freq * 19.0 - tb * twist + phase * 0.71)
            shard = np.power(np.clip(1.0 - np.abs(np.sin((xb * twist - yb * freq) * 8.0 + phase)), 0, 1), 4.0)
            scan = np.power(np.clip(1.0 - np.abs(np.sin((yb * freq * 18.0) + phase)), 0, 1), 7.0)
            b = np.clip(waves * 0.25 + scan * 0.28 + rings * 0.22 + shard * 0.30, 0, 1)
        elif mode == "burn":
            ribbons = 0.5 + 0.5 * np.sin((xb - yb) * (freq * 5.3) + rb * twist * 5.0 + phase * 1.31)
            rings = 0.5 + 0.5 * np.sin(rb * freq * 19.0 - tb * twist + phase * 0.71)
            shard = np.power(np.clip(1.0 - np.abs(np.sin((xb * twist - yb * freq) * 8.0 + phase)), 0, 1), 4.0)
            fine = 0.5 + 0.5 * np.sin(xb * 91.0 + yb * (73.0 + freq) + phase)
            b = np.clip(ribbons * 0.34 + np.power(rings, 2.8) * 0.30 + fine * 0.14 + shard * 0.26, 0, 1)
        else:
            waves = 0.5 + 0.5 * np.sin(xb * (freq * 4.1) + yb * (freq * 2.7) + np.sin(tb * twist + phase) * 1.7 + phase)
            ribbons = 0.5 + 0.5 * np.sin((xb - yb) * (freq * 5.3) + rb * twist * 5.0 + phase * 1.31)
            shard = np.power(np.clip(1.0 - np.abs(np.sin((xb * twist - yb * freq) * 8.0 + phase)), 0, 1), 4.0)
            fine = 0.5 + 0.5 * np.sin(xb * 91.0 + yb * (73.0 + freq) + phase)
            b = np.clip(waves * 0.34 + ribbons * 0.26 + shard * 0.24 + fine * 0.16, 0, 1)
        body[rs:re] = b

    _cc_parallel_rows(_band, h)

    edge_energy = np.clip(np.abs(np.gradient(body, axis=0)) + np.abs(np.gradient(body, axis=1)), 0, 1)
    edge_energy = np.clip(edge_energy * 8.0, 0, 1)
    ultra = np.clip(body * 0.72 + edge_energy * 0.20 + micro * 0.08, 0, 1).astype(np.float32)
    return ultra, edge_energy.astype(np.float32), micro.astype(np.float32)


def _cc_motif_layers(item_id, profile, shape, seed, field, edges, micro):
    x, y, r, theta = _cc_coords(shape)
    phase = ((_cc_stable_seed(item_id) + int(seed) * 17) % 6283) / 1000.0
    motif = profile.get("motif", "linear")
    freq = profile["freq"]
    twist = profile["twist"]

    h = x.shape[0]
    weight = np.empty(x.shape, np.float32)
    accent = np.empty(x.shape, np.float32)

    # PERF: each motif branch below is the IDENTICAL per-pixel math; we evaluate
    # over contiguous row bands in parallel and write each band into the shared
    # weight/accent buffers -> bit-identical to the serial version (verified via
    # np.array_equal @2048). The lone cross-row op (np.gradient in
    # "sunset_horizon") forces a single serial band so it too is unchanged.
    def _band(rs, re):
        xb = x[rs:re]; yb = y[rs:re]; rb = r[rs:re]; tb = theta[rs:re]
        fieldb = field[rs:re]; edgesb = edges[rs:re]; microb = micro[rs:re]
        if motif == "edge_rim":
            w = np.clip(1.0 - np.abs(rb - 0.36) * 2.65 + (fieldb - 0.5) * 0.40, 0, 1)
            a = np.clip(edgesb * 0.75 + np.power(1.0 - rb, 2.0) * 0.50, 0, 1)
        elif motif == "chemical_cells":
            cells = np.sin((xb * 17.0 + fieldb * 3.0) + phase) + np.sin((yb * 23.0 - microb * 2.0) - phase)
            cells = np.clip((cells + 2.0) / 4.0, 0, 1)
            w = np.where(cells > 0.56, 0.18 + cells * 0.82, fieldb * 0.34)
            a = np.clip(edgesb * 0.42 + (microb > 0.74).astype(np.float32) * 0.65, 0, 1)
        elif motif == "chemical_sheen":
            run = np.clip(1.0 - np.abs(np.sin((xb * 19.0 + yb * 3.2 + fieldb * 2.4 + phase) * np.pi)) * 8.6, 0, 1)
            small_pits = (microb > 0.88).astype(np.float32)
            film = np.clip(0.28 + fieldb * 0.28 + np.sin((xb - yb) * 9.0 + phase) * 0.10, 0, 1)
            w = np.clip(film * 0.40 + run * 0.34 + small_pits * 0.22, 0, 1)
            a = np.clip(run * 0.72 + small_pits * 0.50 + edgesb * 0.22, 0, 1)
        elif motif == "lightning_split":
            bolt = xb + np.sin(yb * freq * 5.0 + phase) * 0.18 + (fieldb - 0.5) * 0.18
            w = (bolt > 0).astype(np.float32) * 0.78 + np.clip(1.0 - np.abs(bolt) * 7.5, 0, 1) * 0.35
            a = np.clip(1.0 - np.abs(bolt) * 17.0, 0, 1)
        elif motif == "fever_spiral":
            spiral = np.sin(tb * twist + rb * freq * 12.0 + fieldb * 2.3 + phase)
            w = np.clip((spiral + 1.0) * 0.5 * 0.78 + microb * 0.24, 0, 1)
            a = np.clip(np.power(np.abs(spiral), 5.0) * 0.7 + edgesb * 0.35, 0, 1)
        elif motif == "bruise_bands":
            bands = np.sin((xb * 2.2 + yb * freq * 3.7 + fieldb * 1.8 + phase) * np.pi)
            w = np.clip((bands + 1.0) * 0.36 + np.power(fieldb, 1.6) * 0.34, 0, 1)
            a = np.clip(edgesb * 0.55 + np.power(1.0 - np.abs(yb), 2.0) * 0.30, 0, 1)
        elif motif == "neon_contusion":
            pocket_a = np.exp(-(((xb + 0.34) * 2.9) ** 2 + ((yb - 0.10) * 1.7) ** 2))
            pocket_b = np.exp(-(((xb - 0.28) * 2.5) ** 2 + ((yb + 0.30) * 2.2) ** 2))
            capillary = np.clip(1.0 - np.abs(np.sin((xb * 28.0 - yb * 17.0 + fieldb * 3.0) * np.pi)) * 10.0, 0, 1)
            w = np.clip((pocket_a + pocket_b) * 0.46 + capillary * 0.34 + fieldb * 0.16, 0, 1)
            a = np.clip(capillary * 0.72 + edgesb * 0.26, 0, 1)
        elif motif == "war_cross":
            cross = np.maximum(
                np.clip(1.0 - np.abs(xb + yb * 0.72) * 2.8, 0, 1),
                np.clip(1.0 - np.abs(xb - yb * 0.78) * 3.3, 0, 1),
            )
            w = np.clip((xb > 0).astype(np.float32) * 0.55 + cross * 0.40 + fieldb * 0.22, 0, 1)
            a = np.clip(cross + edgesb * 0.32, 0, 1)
        elif motif == "neon_war_shards":
            shard_a = np.clip(1.0 - np.abs(np.sin((xb * 14.0 + yb * 6.0 + phase) * np.pi)) * 7.0, 0, 1)
            shard_b = np.clip(1.0 - np.abs(np.sin((xb * -9.0 + yb * 18.0 - fieldb * 2.0) * np.pi)) * 7.8, 0, 1)
            split = (np.sin((xb * 3.0 - yb * 2.0 + phase) * np.pi) > 0.0).astype(np.float32)
            row = np.clip(1.0 - np.abs(np.sin((yb * 22.0 + phase) * np.pi)) * 8.5, 0, 1)
            w = np.clip(split * 0.36 + shard_a * 0.34 + shard_b * 0.30 + row * 0.22, 0, 1)
            a = np.clip(shard_a * 0.54 + shard_b * 0.62 + row * 0.34, 0, 1)
        elif motif == "dawn_horizon":
            sun = np.exp(-((xb * 1.8) ** 2 + ((yb + 0.42) * 2.6) ** 2))
            horizon = np.clip(1.0 - np.abs(yb + 0.18) * 3.2, 0, 1)
            w = np.clip(sun * 0.82 + horizon * 0.26 + fieldb * 0.16, 0, 1)
            a = np.clip(horizon * 0.70 + edgesb * 0.30, 0, 1)
        elif motif == "sunset_horizon":
            # cross-row np.gradient -> band == full array (serial), see _band call
            horizon = np.clip((1.0 - yb) * 0.42 + np.sin(xb * 8.0 + fieldb * 2.0 + phase) * 0.16, 0, 1)
            w = np.clip(horizon + np.power(fieldb, 2.2) * 0.25, 0, 1)
            a = np.clip(np.abs(np.gradient(horizon, axis=0)) * 5.0 + edgesb * 0.35, 0, 1)
        elif motif == "burn_patches":
            heat = np.sin(rb * freq * 10.0 + tb * twist + phase)
            w = np.clip(np.power((heat + 1.0) * 0.5, 2.2) * 0.76 + fieldb * 0.20, 0, 1)
            a = np.clip(edgesb * 0.60 + (microb > 0.82).astype(np.float32) * 0.45, 0, 1)
        elif motif == "uv_scan_burn":
            scan = np.clip(1.0 - np.abs(np.sin((yb * 42.0 + np.sin(xb * 8.0 + phase) * 0.55) * np.pi)) * 7.4, 0, 1)
            flare = np.clip(1.0 - np.abs(xb + yb * 0.16) * 2.8, 0, 1)
            speck = (microb > 0.90).astype(np.float32)
            w = np.clip(scan * 0.42 + flare * 0.32 + fieldb * 0.18 + speck * 0.20, 0, 1)
            a = np.clip(scan * 0.70 + speck * 0.48 + edgesb * 0.20, 0, 1)
        elif motif == "coral_branch":
            branch = np.abs(np.sin((xb * 9.0 - yb * 16.0 + np.sin(tb * 5.0) + phase) * np.pi))
            branch = np.clip(1.0 - branch * 7.0, 0, 1)
            w = np.clip(fieldb * 0.36 + branch * 0.66, 0, 1)
            a = np.clip(branch + edgesb * 0.22, 0, 1)
        elif motif == "friction_scrape":
            scrape = np.clip(1.0 - np.abs(np.sin((xb * 36.0 + yb * 4.0 + fieldb * 4.0) * np.pi)) * 9.0, 0, 1)
            w = np.clip((yb > 0).astype(np.float32) * 0.38 + scrape * 0.48 + fieldb * 0.18, 0, 1)
            a = np.clip(scrape * 0.80 + edgesb * 0.25, 0, 1)
        elif motif == "digital_blocks":
            bx = np.floor((xb + 1.0) * 11.0)
            by = np.floor((yb + 1.0) * 15.0)
            blocks = np.sin(bx * 12.9898 + by * 78.233 + phase) * 43758.5453
            blocks = blocks - np.floor(blocks)
            w = np.clip(blocks * 0.62 + fieldb * 0.28 + (microb > 0.82).astype(np.float32) * 0.24, 0, 1)
            a = np.clip((blocks > 0.78).astype(np.float32) * 0.85 + edgesb * 0.28, 0, 1)
        elif motif == "magma_cracks":
            crack = np.minimum(
                np.abs(np.sin((xb * 13.0 + yb * 5.0 + fieldb * 2.0 + phase) * np.pi)),
                np.abs(np.sin((xb * -5.0 + yb * 17.0 - fieldb * 2.4) * np.pi)),
            )
            crack = np.clip(1.0 - crack * 9.0, 0, 1)
            w = np.clip((1.0 - rb) * 0.28 + crack * 0.74 + fieldb * 0.18, 0, 1)
            a = np.clip(crack + edgesb * 0.22, 0, 1)
        elif motif == "acid_etch":
            etch_a = np.clip(1.0 - np.abs(np.sin((xb * 31.0 + yb * 11.0 + fieldb * 4.0) * np.pi)) * 10.5, 0, 1)
            etch_b = np.clip(1.0 - np.abs(np.sin((xb * -17.0 + yb * 37.0 - phase) * np.pi)) * 12.0, 0, 1)
            mist = np.clip(fieldb * 0.34 + (microb > 0.86).astype(np.float32) * 0.28, 0, 1)
            w = np.clip(mist * 0.42 + etch_a * 0.36 + etch_b * 0.30, 0, 1)
            a = np.clip(etch_a * 0.64 + etch_b * 0.56 + edgesb * 0.24, 0, 1)
        elif motif == "blood_drip":
            columns = np.clip(1.0 - np.abs(np.sin((xb * 7.0 + phase) * np.pi)) * 5.8, 0, 1)
            length = np.clip((yb + 0.82 + np.sin(xb * 11.0 + phase) * 0.24), 0, 1)
            taper = np.power(length, 2.2) * columns
            clot = ((np.sin(xb * 31.0 + yb * 9.0 + phase) * np.sin(yb * 27.0 - phase)) > 0.68).astype(np.float32)
            w = np.clip(taper * 0.72 + length * 0.24 + clot * 0.18, 0, 1)
            a = np.clip(taper * 0.80 + clot * 0.48, 0, 1)
        elif motif == "flash_shear":
            shear = yb + xb * 0.34 + np.sin(xb * 9.0 + phase) * 0.08
            blast = np.clip(1.0 - np.abs(shear) * 3.6, 0, 1)
            afterimage = np.clip(1.0 - np.abs(shear - 0.42) * 8.0, 0, 1)
            sparks = (microb > 0.84).astype(np.float32)
            w = np.clip(blast * 0.72 + afterimage * 0.34 + sparks * 0.20, 0, 1)
            a = np.clip(blast * 0.62 + afterimage * 0.78 + sparks * 0.38, 0, 1)
        elif motif == "hazard_fan":
            fan = (np.sin(tb * 3.0 + phase) > 0.0).astype(np.float32)
            ring = np.clip(1.0 - np.abs(np.sin(rb * freq * 14.0)) * 5.5, 0, 1)
            w = np.clip(fan * 0.56 + ring * 0.30 + fieldb * 0.22, 0, 1)
            a = np.clip(ring * 0.85 + edgesb * 0.32, 0, 1)
        elif motif == "radioactive_dust":
            ring = np.clip(1.0 - np.abs(np.sin(rb * freq * 36.0 + phase)) * 9.0, 0, 1)
            dust = (microb > 0.84).astype(np.float32)
            vein = np.clip(1.0 - np.abs(np.sin((tb * 7.0 + rb * 18.0 + fieldb * 2.0) * np.pi)) * 9.2, 0, 1)
            w = np.clip(ring * 0.32 + dust * 0.32 + vein * 0.28 + fieldb * 0.14, 0, 1)
            a = np.clip(ring * 0.44 + dust * 0.56 + vein * 0.50, 0, 1)
        elif motif == "rust_ice_split":
            split = np.clip((xb + np.sin(yb * 9.0 + phase) * 0.10 + fieldb * 0.08) * 4.0 + 0.5, 0, 1)
            crust = np.clip(1.0 - np.abs(np.sin((xb * 18.0 + yb * 21.0 + phase) * np.pi)) * 8.0, 0, 1)
            w = np.clip(split * 0.74 + crust * 0.26, 0, 1)
            a = np.clip(crust * 0.72 + edgesb * 0.25, 0, 1)
        elif motif == "rust_ice_islands":
            cell_x = np.floor((xb + 1.0) * 20.0)
            cell_y = np.floor((yb + 1.0) * 24.0)
            cell = np.sin(cell_x * 17.13 + cell_y * 41.71 + phase) * 43758.5453
            cell = cell - np.floor(cell)
            coastline = np.clip(1.0 - np.abs(cell - 0.50) * 6.2, 0, 1)
            frost = np.clip(1.0 - np.abs(np.sin((xb * 39.0 - yb * 35.0 + fieldb * 2.2) * np.pi)) * 10.5, 0, 1)
            w = np.clip((cell > 0.56).astype(np.float32) * 0.42 + coastline * 0.28 + frost * 0.30, 0, 1)
            a = np.clip(coastline * 0.58 + frost * 0.64 + edgesb * 0.18, 0, 1)
        elif motif == "solar_starburst":
            rays = np.clip(1.0 - np.abs(np.sin(tb * 9.0 + phase)) * 4.5, 0, 1)
            core = np.exp(-(rb * 2.8) ** 2)
            w = np.clip(core * 0.72 + rays * 0.44 + fieldb * 0.16, 0, 1)
            a = np.clip(rays * 0.85 + edgesb * 0.22, 0, 1)
        elif motif == "venom_strike":
            strike = yb - xb * 0.72 + np.sin((xb + yb) * 12.0 + phase) * 0.08
            w = np.clip((strike > 0).astype(np.float32) * 0.45 + np.clip(1.0 - np.abs(strike) * 10.0, 0, 1) * 0.55, 0, 1)
            a = np.clip(1.0 - np.abs(strike) * 22.0, 0, 1)
        elif motif == "coral_fan":
            vertical = np.clip((yb + 1.0) * 0.45, 0, 1)
            branch_a = np.clip(1.0 - np.abs(np.sin((xb * 13.0 + vertical * 8.0 + phase) * np.pi)) * 7.2, 0, 1)
            branch_b = np.clip(1.0 - np.abs(np.sin((xb * -17.0 + yb * 11.0 + fieldb * 2.0) * np.pi)) * 8.4, 0, 1)
            shelf = np.clip(1.0 - np.abs(yb - 0.24) * 5.2, 0, 1)
            w = np.clip(vertical * 0.26 + branch_a * 0.42 + branch_b * 0.34 + shelf * 0.18, 0, 1)
            a = np.clip(branch_a * 0.58 + branch_b * 0.62 + shelf * 0.28, 0, 1)
        elif motif == "candy_crack":
            pane = np.clip(1.0 - np.abs(np.sin((xb * 8.0 - yb * 10.0 + phase) * np.pi)) * 5.6, 0, 1)
            vein = np.clip(1.0 - np.abs(np.sin((xb * 30.0 + yb * 18.0 + fieldb * 2.6) * np.pi)) * 10.2, 0, 1)
            diagonal = np.clip((xb + yb + 0.5) * 0.34, 0, 1)
            w = np.clip(diagonal + pane * 0.42 + vein * 0.22, 0, 1)
            a = np.clip(pane * 0.55 + vein * 0.70 + edgesb * 0.20, 0, 1)
        elif motif == "bruised_clouds":
            cloud = np.clip(fieldb * 0.52 + np.sin((xb * 4.0 + yb * 7.0 + phase) * np.pi) * 0.18 + 0.28, 0, 1)
            torn = np.clip(1.0 - np.abs(np.sin((xb * 18.0 - yb * 15.0 + fieldb * 2.0) * np.pi)) * 9.0, 0, 1)
            w = np.clip(cloud * 0.58 + torn * 0.30, 0, 1)
            a = np.clip(torn * 0.62 + edgesb * 0.34, 0, 1)
        elif motif == "voltage_zigzag":
            zig = xb - np.sign(np.sin(yb * np.pi * 8.0 + phase)) * 0.28
            w = np.clip((zig > 0).astype(np.float32) * 0.68 + np.clip(1.0 - np.abs(zig) * 8.0, 0, 1) * 0.42, 0, 1)
            a = np.clip(1.0 - np.abs(zig) * 18.0, 0, 1)
        else:
            axis = xb + (fieldb - 0.5) * 0.55 + (microb - 0.5) * 0.18
            w = np.exp(-np.square(axis * (1.15 + profile["balance"] * 0.35)))
            w = np.clip(w * (0.82 + fieldb * 0.24), 0, 1)
            a = np.clip(edgesb * 0.45 + fieldb * 0.35, 0, 1)
        weight[rs:re] = w
        accent[rs:re] = a

    if motif == "sunset_horizon":
        _band(0, h)  # serial: np.gradient couples rows
    else:
        _cc_parallel_rows(_band, h)

    return weight.astype(np.float32), accent.astype(np.float32)


def _make_cc_v2_paint(item_id, profile):
    def _paint(paint, shape, mask, seed, pm, bb):
        if paint.ndim == 3 and paint.shape[2] > 3:
            paint = paint[:, :, :3].copy()
        if pm == 0.0:
            return paint
        h, w = shape[:2]
        mask_arr = np.asarray(mask, dtype=np.float32)
        field, edges, micro = _cc_dynamic_fields(item_id, profile, (h, w), seed)
        center = np.asarray(profile["center"], dtype=np.float32)
        edge = np.asarray(profile["edge"], dtype=np.float32)
        accent = np.asarray(profile["accent"], dtype=np.float32)
        center_weight, accent_weight = _cc_motif_layers(item_id, profile, (h, w), seed, field, edges, micro)
        bb2d = _cc_bb2d(bb, (h, w))
        src = paint[:, :, :3]
        pm_blend = np.clip(float(pm) * 0.96, 0, 1)
        out = np.empty((h, w, 3), np.float32)

        # PERF: the per-pixel color assembly below is mathematically identical to
        # the original full-array form; we run it over contiguous row bands in
        # parallel (and avoid several full-2048 temporaries) -> bit-identical
        # (verified via np.array_equal @2048).
        def _band(rs, re):
            cw = center_weight[rs:re, :, np.newaxis]
            base = edge[np.newaxis, np.newaxis, :] * (1.0 - cw) + center[np.newaxis, np.newaxis, :] * cw
            glow = np.clip(accent_weight[rs:re] * 0.70 + field[rs:re] * 0.22 + edges[rs:re] * 0.22, 0, 1)
            shade = np.clip(0.58 + field[rs:re] * 0.34 + edges[rs:re] * 0.22 + (micro[rs:re] - 0.5) * 0.16, 0.28, 1.22)
            target = base * shade[:, :, np.newaxis]
            target += accent[np.newaxis, np.newaxis, :] * glow[:, :, np.newaxis] * 0.56
            target += edge[np.newaxis, np.newaxis, :] * edges[rs:re, :, np.newaxis] * 0.12
            target += center[np.newaxis, np.newaxis, :] * np.power(np.clip(center_weight[rs:re], 0, 1), 2.2)[:, :, np.newaxis] * 0.18
            target = np.clip(target + bb2d[rs:re, :, np.newaxis] * 0.18, 0, 1)
            blend = pm_blend * mask_arr[rs:re, :, np.newaxis]
            out[rs:re] = np.clip(src[rs:re] * (1.0 - blend) + target * blend, 0, 1)

        _cc_parallel_rows(_band, h)
        return np.ascontiguousarray(out)
    _paint._spb_color_clash_v2 = item_id
    return _paint


def _make_cc_v2_spec(item_id, profile):
    def _spec(shape, mask, seed, sm):
        h, w = shape[:2]
        mask_arr = np.asarray(mask, dtype=np.float32)
        field, edges, micro = _cc_dynamic_fields(item_id, profile, (h, w), seed + 991)
        motif_weight, motif_accent = _cc_motif_layers(item_id, profile, (h, w), seed + 991, field, edges, micro)
        m_base, m_detail, m_edge = profile["metal"]
        r_base, r_detail, r_edge = profile["rough"]
        cc_base, cc_detail, cc_edge = profile["clearcoat"]
        style = profile.get("spec_style", _cc_stable_seed(item_id) % 6)
        route = profile.get("spec_route")
        spec = np.empty((h, w, 4), dtype=np.uint8)

        # PERF: per-pixel M/R/CC math below is identical to the original
        # full-array form; evaluated over contiguous row bands in parallel and
        # written straight into the uint8 spec buffer -> bit-identical (verified
        # via np.array_equal @2048).
        def _band(rs, re):
            fieldb = field[rs:re]; edgesb = edges[rs:re]; microb = micro[rs:re]
            mwb = motif_weight[rs:re]; mab = motif_accent[rs:re]; maskb = mask_arr[rs:re]
            line = np.clip(mab * 0.82 + edgesb * 0.34, 0, 1)
            body = np.clip(mwb * 0.78 + fieldb * 0.22, 0, 1)
            grit = np.clip(np.abs(mwb - fieldb) * 0.70 + microb * 0.30, 0, 1)
            if style == 0:  # chrome core with rough rim
                M = m_base + body * (m_detail + 32.0) + line * m_edge
                R = r_base + (1.0 - body) * (r_detail + 18.0) - line * r_edge
                CC = cc_base + line * (cc_edge + 42.0) + fieldb * cc_detail
            elif style == 1:  # matte chemical etch: red/rough-heavy spec preview
                M = m_base * 0.45 + line * (m_edge * 0.62) + grit * 34.0
                R = r_base + grit * (r_detail + 88.0) + line * 28.0
                CC = cc_base + body * (cc_detail * 0.42) + line * (cc_edge * 0.50)
            elif style == 2:  # rough-edge flip: blue/clearcoat-heavy edges
                M = m_base + line * (m_edge + 68.0) + (1.0 - body) * 22.0
                R = r_base + body * (r_detail * 0.55) + grit * 42.0 - line * (r_edge * 0.50)
                CC = cc_base + (1.0 - body) * (cc_detail + 70.0) + line * cc_edge
            elif style == 3:  # satin blocks: green/red midrange separation
                M = m_base + np.round(body * 5.0) / 5.0 * (m_detail + 22.0) + microb * 16.0
                R = r_base + np.round(grit * 6.0) / 6.0 * (r_detail + 52.0)
                CC = cc_base + line * (cc_edge * 0.74) + (1.0 - grit) * 34.0
            elif style == 4:  # clearcoat veins over subdued metal
                M = m_base * 0.70 + fieldb * (m_detail * 0.40) + line * 30.0
                R = r_base + (1.0 - line) * (r_detail + 24.0) + grit * 22.0
                CC = cc_base + line * (cc_edge + 96.0) + body * 30.0
            else:  # electric-line high metal / low roughness streaks
                M = m_base + line * (m_detail + m_edge + 42.0) + microb * 18.0
                R = r_base + (1.0 - line) * (r_detail + 46.0) - line * (r_edge * 0.85)
                CC = cc_base + body * (cc_detail * 0.45) + line * (cc_edge + 58.0)
            if route is not None:
                sources = [
                    body,
                    line,
                    grit,
                    fieldb,
                    edgesb,
                    microb,
                    np.abs(body - line),
                    np.abs(fieldb - microb),
                    1.0 - body,
                    1.0 - line,
                    1.0 - grit,
                    np.clip(body * line * 1.45, 0, 1),
                    np.clip((body + line) * 0.5, 0, 1),
                ]
                mi, ri, ci = route
                M = m_base * 0.42 + 18.0 + sources[mi] * (m_detail + m_edge + 74.0) + microb * 14.0
                R = r_base * 0.55 + 15.0 + sources[ri] * (r_detail + r_edge + 92.0) + (1.0 - sources[mi]) * 12.0
                CC = cc_base * 0.50 + 16.0 + sources[ci] * (cc_detail + cc_edge + 110.0) + edgesb * 12.0
            M = np.clip(M * maskb * sm, 0, 255)
            R = np.clip(R * maskb * sm, 0, 255)
            CC = np.clip(CC * maskb * sm, 16, 255)
            R = np.where((M < 240) & (maskb > 0.5), np.maximum(R, 15), R)
            spec[rs:re, :, 0] = M.astype(np.uint8)
            spec[rs:re, :, 1] = R.astype(np.uint8)
            spec[rs:re, :, 2] = CC.astype(np.uint8)
            spec[rs:re, :, 3] = np.clip(maskb * 255, 0, 255).astype(np.uint8)

        _cc_parallel_rows(_band, h)
        return spec
    _spec._spb_color_clash_v2 = item_id
    return _spec


_COLOR_CLASH_V2_PROFILES = {
    "cc_neon_bruise": _cc_profile((0.64, 0.00, 0.92), (0.08, 0.92, 0.05), (0.98, 0.08, 0.82), "storm", 5.8, 4.2, (190, 52, 44), (42, 84, 32), (28, 116, 42), 1.10),
    "cc_acid_burn": _cc_profile((0.98, 0.94, 0.02), (0.21, 0.00, 0.48), (0.05, 1.00, 0.36), "spill", 6.4, 3.7, (32, 92, 28), (122, 92, 46), (40, 128, 34), 0.96),
    "cc_blood_orange": _cc_profile((0.82, 0.04, 0.00), (0.00, 0.26, 0.95), (1.00, 0.36, 0.04), "burn", 5.3, 4.8, (118, 104, 52), (62, 76, 34), (34, 104, 38), 1.02),
    "cc_toxic_sunset": _cc_profile((1.00, 0.08, 0.56), (0.21, 0.96, 0.03), (1.00, 0.78, 0.06), "plasma", 5.9, 5.1, (160, 86, 64), (52, 118, 44), (42, 132, 50), 1.12),
    "cc_electric_conflict": _cc_profile((0.00, 0.95, 1.00), (0.92, 0.00, 0.76), (1.00, 0.95, 0.04), "electric", 7.2, 4.5, (205, 70, 52), (34, 72, 28), (30, 122, 44), 1.18),
    "cc_nuclear_dawn": _cc_profile((0.13, 1.00, 0.00), (0.72, 0.00, 0.04), (0.98, 0.96, 0.04), "spill", 6.8, 3.3, (58, 106, 34), (150, 90, 48), (44, 118, 38), 1.00),
    "cc_voltage_split": _cc_profile((1.00, 0.95, 0.00), (0.00, 0.03, 0.32), (0.04, 0.74, 1.00), "electric", 7.6, 5.0, (214, 58, 54), (30, 124, 34), (24, 126, 48), 1.20),
    "cc_coral_venom": _cc_profile((1.00, 0.36, 0.26), (0.00, 0.64, 0.10), (0.04, 0.98, 0.70), "venom", 5.6, 4.0, (130, 82, 48), (68, 88, 32), (36, 110, 44), 1.03),
    "cc_ultraviolet_burn": _cc_profile((0.38, 0.00, 0.96), (1.00, 0.48, 0.00), (0.08, 0.86, 1.00), "burn", 6.1, 5.4, (180, 78, 46), (46, 92, 30), (32, 120, 42), 1.08),
    "cc_rust_vs_ice": _cc_profile((0.76, 0.30, 0.04), (0.72, 0.90, 1.00), (0.05, 0.54, 1.00), "magma", 5.2, 3.8, (142, 100, 58), (70, 104, 42), (38, 106, 46), 0.94),
    "cc_magma_freeze": _cc_profile((0.94, 0.12, 0.00), (0.88, 0.96, 1.00), (1.00, 0.64, 0.02), "magma", 6.9, 4.6, (184, 78, 70), (36, 130, 52), (30, 136, 58), 1.08),
    "cc_radioactive": _cc_profile((0.08, 1.00, 0.02), (0.33, 0.00, 0.05), (0.92, 1.00, 0.04), "storm", 6.7, 3.4, (174, 72, 48), (42, 92, 34), (34, 126, 46), 1.04),
    "cc_bruised_sky": _cc_profile((0.30, 0.00, 0.58), (0.86, 0.84, 0.16), (0.98, 0.05, 0.40), "plasma", 5.4, 4.1, (116, 92, 44), (80, 102, 38), (36, 112, 36), 1.00),
    "cc_chemical_spill": _cc_profile((0.38, 0.98, 0.00), (1.00, 0.43, 0.00), (0.02, 0.92, 1.00), "spill", 6.5, 5.2, (210, 64, 54), (30, 88, 34), (30, 132, 48), 1.12),
    "cc_deep_friction": _cc_profile((0.58, 0.00, 0.00), (0.00, 0.88, 0.78), (1.00, 0.16, 0.06), "rot", 6.2, 3.9, (86, 104, 38), (130, 90, 52), (34, 104, 42), 0.96),
    "cc_plasma_edge": _cc_profile((1.00, 0.98, 0.88), (0.06, 0.18, 1.00), (0.16, 0.95, 1.00), "plasma", 7.8, 5.6, (224, 72, 64), (18, 82, 22), (24, 150, 54), 1.22),
    "cc_candy_poison": _cc_profile((1.00, 0.36, 0.68), (0.03, 0.14, 0.04), (0.12, 1.00, 0.38), "venom", 5.7, 4.7, (150, 88, 46), (54, 126, 40), (36, 122, 46), 1.06),
    "cc_solar_clash": _cc_profile((1.00, 0.80, 0.06), (0.01, 0.01, 0.01), (1.00, 0.18, 0.00), "burn", 5.9, 4.4, (218, 58, 58), (24, 100, 30), (28, 136, 44), 1.16),
    "cc_fever_dream": _cc_profile((0.92, 0.08, 0.04), (0.50, 0.00, 0.80), (0.08, 0.98, 0.90), "plasma", 6.4, 5.8, (172, 94, 52), (46, 108, 42), (34, 124, 48), 1.10),
    "cc_digital_rot": _cc_profile((0.00, 0.92, 0.92), (0.40, 0.19, 0.04), (0.85, 1.00, 0.10), "rot", 8.2, 3.1, (138, 90, 50), (62, 96, 38), (34, 108, 42), 1.04),
    "cc_flash_burn": _cc_profile((1.00, 1.00, 0.92), (0.92, 0.28, 0.00), (0.08, 0.56, 1.00), "burn", 7.0, 4.3, (204, 82, 58), (24, 128, 34), (28, 142, 48), 1.18),
    "cc_venom_strike": _cc_profile((0.14, 0.88, 0.00), (0.01, 0.01, 0.01), (0.78, 1.00, 0.04), "venom", 7.5, 5.5, (190, 78, 54), (28, 108, 28), (30, 132, 50), 1.20),
    "cc_neon_war": _cc_profile((1.00, 0.38, 0.00), (0.00, 0.26, 1.00), (0.98, 0.02, 0.88), "electric", 7.1, 5.0, (210, 68, 58), (26, 86, 30), (28, 130, 48), 1.18),
}


# ================================================================
# REGISTRY — Maps finish IDs to (spec_fn, paint_fn) tuples
# ================================================================

_COLOR_CLASH_V2_MOTIFS = {
    "cc_plasma_edge": "edge_rim",
    "cc_chemical_spill": "chemical_sheen",
    "cc_electric_conflict": "lightning_split",
    "cc_fever_dream": "fever_spiral",
    "cc_neon_bruise": "neon_contusion",
    "cc_neon_war": "neon_war_shards",
    "cc_nuclear_dawn": "dawn_horizon",
    "cc_toxic_sunset": "sunset_horizon",
    "cc_ultraviolet_burn": "uv_scan_burn",
    "cc_blood_orange": "blood_drip",
    "cc_acid_burn": "acid_etch",
    "cc_bruised_sky": "bruised_clouds",
    "cc_candy_poison": "candy_crack",
    "cc_coral_venom": "coral_fan",
    "cc_deep_friction": "friction_scrape",
    "cc_digital_rot": "digital_blocks",
    "cc_flash_burn": "flash_shear",
    "cc_magma_freeze": "magma_cracks",
    "cc_radioactive": "radioactive_dust",
    "cc_rust_vs_ice": "rust_ice_islands",
    "cc_solar_clash": "solar_starburst",
    "cc_venom_strike": "venom_strike",
    "cc_voltage_split": "voltage_zigzag",
}

for _cc_item_id, _cc_motif in _COLOR_CLASH_V2_MOTIFS.items():
    if _cc_item_id in _COLOR_CLASH_V2_PROFILES:
        _COLOR_CLASH_V2_PROFILES[_cc_item_id]["motif"] = _cc_motif

_COLOR_CLASH_V2_SPEC_STYLES = {
    "cc_plasma_edge": 0,
    "cc_chemical_spill": 1,
    "cc_electric_conflict": 5,
    "cc_fever_dream": 4,
    "cc_neon_bruise": 3,
    "cc_neon_war": 5,
    "cc_nuclear_dawn": 2,
    "cc_toxic_sunset": 0,
    "cc_ultraviolet_burn": 4,
    "cc_blood_orange": 1,
    "cc_acid_burn": 1,
    "cc_bruised_sky": 3,
    "cc_candy_poison": 2,
    "cc_coral_venom": 4,
    "cc_deep_friction": 1,
    "cc_digital_rot": 3,
    "cc_flash_burn": 5,
    "cc_magma_freeze": 2,
    "cc_radioactive": 4,
    "cc_rust_vs_ice": 3,
    "cc_solar_clash": 0,
    "cc_venom_strike": 5,
    "cc_voltage_split": 2,
}

for _cc_item_id, _cc_spec_style in _COLOR_CLASH_V2_SPEC_STYLES.items():
    if _cc_item_id in _COLOR_CLASH_V2_PROFILES:
        _COLOR_CLASH_V2_PROFILES[_cc_item_id]["spec_style"] = _cc_spec_style

_COLOR_CLASH_V2_SPEC_ROUTES = {
    "cc_plasma_edge": (0, 9, 1),
    "cc_chemical_spill": (6, 2, 5),
    "cc_electric_conflict": (1, 8, 11),
    "cc_fever_dream": (3, 10, 6),
    "cc_neon_bruise": (2, 7, 12),
    "cc_neon_war": (11, 4, 1),
    "cc_nuclear_dawn": (8, 2, 3),
    "cc_toxic_sunset": (12, 6, 0),
    "cc_ultraviolet_burn": (5, 9, 4),
    "cc_blood_orange": (10, 1, 7),
    "cc_acid_burn": (7, 3, 10),
    "cc_bruised_sky": (4, 11, 2),
    "cc_candy_poison": (6, 8, 12),
    "cc_coral_venom": (1, 10, 5),
    "cc_deep_friction": (9, 6, 11),
    "cc_digital_rot": (2, 12, 8),
    "cc_flash_burn": (11, 7, 0),
    "cc_magma_freeze": (0, 4, 9),
    "cc_radioactive": (5, 6, 1),
    "cc_rust_vs_ice": (7, 11, 3),
    "cc_solar_clash": (12, 8, 4),
    "cc_venom_strike": (1, 5, 10),
    "cc_voltage_split": (4, 9, 11),
}

for _cc_item_id, _cc_spec_route in _COLOR_CLASH_V2_SPEC_ROUTES.items():
    if _cc_item_id in _COLOR_CLASH_V2_PROFILES:
        _COLOR_CLASH_V2_PROFILES[_cc_item_id]["spec_route"] = _cc_spec_route


COLOR_CLASH_MONOLITHICS = {
    "cc_neon_bruise":       (spec_cc_neon_bruise,       paint_cc_neon_bruise),
    "cc_acid_burn":         (spec_cc_acid_burn,         paint_cc_acid_burn),
    "cc_blood_orange":      (spec_cc_blood_orange,      paint_cc_blood_orange),
    "cc_toxic_sunset":      (spec_cc_toxic_sunset,      paint_cc_toxic_sunset),
    "cc_electric_conflict": (spec_cc_electric_conflict, paint_cc_electric_conflict),
    "cc_nuclear_dawn":      (spec_cc_nuclear_dawn,      paint_cc_nuclear_dawn),
    "cc_voltage_split":     (spec_cc_voltage_split,     paint_cc_voltage_split),
    "cc_coral_venom":       (spec_cc_coral_venom,       paint_cc_coral_venom),
    "cc_ultraviolet_burn":  (spec_cc_ultraviolet_burn,  paint_cc_ultraviolet_burn),
    "cc_rust_vs_ice":       (spec_cc_rust_vs_ice,       paint_cc_rust_vs_ice),
    "cc_magma_freeze":      (spec_cc_magma_freeze,      paint_cc_magma_freeze),
    "cc_punk_static":       (spec_cc_punk_static,       paint_cc_punk_static),
    "cc_radioactive":       (spec_cc_radioactive,       paint_cc_radioactive),
    "cc_bruised_sky":       (spec_cc_bruised_sky,       paint_cc_bruised_sky),
    "cc_chemical_spill":    (spec_cc_chemical_spill,    paint_cc_chemical_spill),
    "cc_deep_friction":     (spec_cc_deep_friction,     paint_cc_deep_friction),
    "cc_plasma_edge":       (spec_cc_plasma_edge,       paint_cc_plasma_edge),
    "cc_candy_poison":      (spec_cc_candy_poison,      paint_cc_candy_poison),
    "cc_solar_clash":       (spec_cc_solar_clash,       paint_cc_solar_clash),
    "cc_fever_dream":       (spec_cc_fever_dream,       paint_cc_fever_dream),
    "cc_digital_rot":       (spec_cc_digital_rot,       paint_cc_digital_rot),
    "cc_flash_burn":        (spec_cc_flash_burn,        paint_cc_flash_burn),
    "cc_venom_strike":      (spec_cc_venom_strike,      paint_cc_venom_strike),
    "cc_neon_war":          (spec_cc_neon_war,          paint_cc_neon_war),
    "cc_chaos_theory":      (spec_cc_chaos_theory,      paint_cc_chaos_theory),
}

COLOR_CLASH_MONOLITHICS.update({
    item_id: (_make_cc_v2_spec(item_id, profile), _make_cc_v2_paint(item_id, profile))
    for item_id, profile in _COLOR_CLASH_V2_PROFILES.items()
})


# ═══════════════ 2026-06-21 COLOR SCIENCE REDIRECT — COLOR CLASH SPECS ═══════════════
# The cc_ specs were flat _uniform_spec/_gradient_spec (M≈R → |corr|~0.97, low dynamism).
# Replace EVERY cc_ spec with a UNIQUE elaborate color_science_2026 spec (sharp/high-contrast
# "clash" looks + candy-depth + motion). Keep the V2 paint. This is the LAST cc_ spec write.
_CC_CS_LOOKS = ["crystal_facets", "guilloche", "spectral_spiral", "holographic_mosaic",
                "oilslick_thinfilm", "ripple_caustics", "iridescent_flow"]
_CC_CS_CANDY = {
    "std": {}, "warm": dict(m_hi=244, cc_edge=186, r_edge=120),
    "dark": dict(m_lo=60, m_hi=216, cc_edge=180),
    "deep": dict(m_hi=240, cc_edge=194, r_core=18, gamma=1.5),
    "icy": dict(m_hi=232, r_edge=96, cc_edge=150, gamma=1.5),
}
_CC_CANDY_KEYS = list(_CC_CS_CANDY.keys())


def _cc_cs_recipe(fid, idx):
    hh = (sum(ord(c) for c in fid) * 2654435761) & 0x7FFFFFFF
    look = _CC_CS_LOOKS[hh % len(_CC_CS_LOOKS)]
    if look == "crystal_facets":
        kw = dict(cells=float(32 + (hh % 6) * 7))
    elif look == "guilloche":
        kw = dict(a=float(10 + hh % 6), b=float(12 + (hh // 6) % 6))
    elif look == "spectral_spiral":
        kw = dict(arms=float(4 + hh % 8), twist=float(3 + (hh // 8) % 8))
    elif look == "holographic_mosaic":
        kw = dict(cells=float(22 + (hh % 10) * 2))
    elif look == "oilslick_thinfilm":
        kw = dict(bands=float(5 + hh % 6))
    elif look == "ripple_caustics":
        kw = dict(rings=float(7 + hh % 8))
    else:
        kw = dict(scale=float(3 + hh % 4))
    rec = {"look": look, "look_kwargs": kw, "depth_from": ("structure", "invert")[hh % 2],
           "candy": dict(_CC_CS_CANDY[_CC_CANDY_KEYS[hh % len(_CC_CANDY_KEYS)]]),
           "motion": 0.30 + (hh % 5) * 0.05, "phase": (hh % 7) * 0.45, "relief": 28.0}
    return rec, 6000 + idx * 53


def _cc_cs_spec_fn(recipe, seed_off):
    _rc = dict(recipe); _so = int(seed_off)

    def spec_fn(shape, mask, seed, sm):
        import numpy as _np
        from engine.paint_v2 import color_science_2026 as _csx
        h, w = int(shape[0]), int(shape[1])
        spec = _csx.compose_cs_spec((h, w), int(seed) + _so, 1.0, _rc).astype(_np.float32)
        m = _np.asarray(mask, _np.float32)
        if m.ndim == 3:
            m = m[:, :, 0]
        if m.shape != (h, w):
            try:
                import cv2 as _cv2
                m = _cv2.resize(m, (w, h))
            except Exception:
                m = _np.ones((h, w), _np.float32)
        M = _np.clip(spec[:, :, 0] * m * sm, 0, 255)
        R = _np.clip(spec[:, :, 1] * m * sm, 0, 255)
        R = _np.where((M < 240) & (m > 0.5), _np.maximum(R, 15), R)
        Cc = _np.clip(_np.maximum(spec[:, :, 2], 16), 16, 255)
        out = _np.zeros((h, w, 4), _np.uint8)
        out[:, :, 0] = M.astype(_np.uint8)
        out[:, :, 1] = R.astype(_np.uint8)
        out[:, :, 2] = Cc.astype(_np.uint8)
        out[:, :, 3] = _np.clip(m * 255, 0, 255).astype(_np.uint8)
        return out
    return spec_fn


for _cc_idx, _cc_id in enumerate(list(COLOR_CLASH_MONOLITHICS.keys())):
    if _cc_id.startswith("cc_"):
        _cc_rec, _cc_so = _cc_cs_recipe(_cc_id, _cc_idx)
        COLOR_CLASH_MONOLITHICS[_cc_id] = (_cc_cs_spec_fn(_cc_rec, _cc_so),
                                           COLOR_CLASH_MONOLITHICS[_cc_id][1])


def integrate_color_clash(engine_module):
    """Merge Color Clash expansion into the engine's registries."""
    engine_module.MONOLITHIC_REGISTRY.update(COLOR_CLASH_MONOLITHICS)

    # Sort registry alphabetically after merge
    reg = engine_module.MONOLITHIC_REGISTRY
    sorted_reg = dict(sorted(reg.items()))
    reg.clear()
    reg.update(sorted_reg)

    count = len(COLOR_CLASH_MONOLITHICS)
    print(f"[COLOR CLASH] Loaded {count} color clash gradient finishes")
    return count
