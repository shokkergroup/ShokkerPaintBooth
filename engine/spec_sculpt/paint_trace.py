"""Paint-traced spec for Spec Sculpt catalog / SHOKK THE WORLD (Viva Mexico playbook).

2026-06-02 overnight — owner: World gallery looked like full-frame wallpaper (magenta/green
overlays) instead of tracing livery graphics. Root cause: ``blend_registered_specs_float``
renders each finish on a uniform mask; weak luminance emphasis is not enough.

This module:
1. ``spatial_envelope_catalog`` — collapse catalog deviation outside paint graphics (kills
   spirals/bands on void panels while keeping finish character on edges/art).
2. ``apply_paint_trace_prepass`` — Viva ridge/crest/chroma/void logic WITHOUT the procedural
   dot/octave grids that caused the 2026-06-01 grid-flash when run on catalog tiles.
3. ``imprint_paint_skeleton`` — fuse paint-derived scratch spec with catalog for structure.

Grid-flash sources deliberately omitted: sparse dot grids, multi-octave mesh, nano fringe,
diagonal weave at high DS (see ``_pre_adjust_viva_mexico_spec`` in cultural_viva_mexico.py).
"""

from __future__ import annotations

import cv2
import numpy as np

from engine.paint_v2.cultural_viva_mexico import (
    _finish_rng_seed,
    _post_adjust_viva_mexico_spec,
    _viva_mexico_highlight_crest,
    _viva_mexico_paint_luma_edge,
)
from engine.paint_v2.cultural_union_jacked import _scratch_spec_from_paint


def paint_graphic_weight(
    tex_rgb_hwc: np.ndarray,
    mask_hw: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """0–1 weight: high on livery edges, crests, and saturated graphics; low on flat void."""
    gray, edge_n = _viva_mexico_paint_luma_edge(tex_rgb_hwc, mask_hw)
    streak_soft, _, _protect = _viva_mexico_highlight_crest(tex_rgb_hwc, mask_hw)
    m = np.clip(mask_hw.astype(np.float32), 0.0, 1.0)
    dark_paint = gray < (34.0 / 255.0)
    dark_interior = dark_paint & (edge_n < 0.28)

    r = tex_rgb_hwc[:, :, 0]
    gch = tex_rgb_hwc[:, :, 1]
    b = tex_rgb_hwc[:, :, 2]
    mx = np.maximum(np.maximum(r, gch), b)
    mn = np.minimum(np.minimum(r, gch), b)
    sat = np.clip((mx - mn) / (mx + 1e-6), 0.0, 1.0)

    # Edge-first graphic mask: saturated fill WITHOUT edges must not read as "graphic"
    # (was letting full-frame catalog wallpaper survive on colored body panels).
    edge_core = np.power(edge_n, 0.52)
    fill_bleed = np.clip(sat, 0.0, 1.0) * (1.0 - np.clip(edge_n * 1.35, 0.0, 1.0)) * 0.42
    graphic = np.clip(edge_core * 1.12 + streak_soft * 0.52 - fill_bleed, 0.0, 1.0) * m
    graphic *= 1.0 - dark_interior.astype(np.float32) * 0.92
    return graphic, gray, edge_n, dark_interior, streak_soft


def apply_fast_paint_trace(
    spec: np.ndarray,
    tex_rgb_hwc: np.ndarray,
    mask_hw: np.ndarray,
    *,
    strength: float = 1.0,
) -> None:
    """One-pass paint coupling for guided/Auto-Sculpt renders.

    [SPB-BETA-2026-07-20 live audit] Owner verdict: Spec Sculpt has to feel
    immediate without turning the finish bland. The legacy catalog trace runs
    five paint-analysis passes after the authored finish bake (measured
    31.7-39.7 s end-to-end on the 2048 Chevy PSD). This opt-in path derives
    luma, chroma, micro-detail, and livery edges once, then shapes the authored
    M/R/Cc channels in place. Advanced/manual renders keep the legacy pipeline.
    First implementation benchmark is recorded in the Living Wiki; visual
    detail is deliberately preserved rather than blurred or enlarged.
    """
    st = float(np.clip(strength, 0.0, 1.5))
    if st < 1e-6:
        return
    tex_full = np.asarray(tex_rgb_hwc[:, :, :3], dtype=np.float32)
    m_full = np.clip(np.asarray(mask_hw, dtype=np.float32), 0.0, 1.0)
    h, w = tex_full.shape[:2]
    # Analyze paint cues at a bounded resolution, then lift only six compact
    # modulation fields to the final canvas. The authored finish itself stays
    # 2048 and retains its 8-32 px detail; this removes ~1 s of redundant
    # full-canvas NumPy work from the guided path.
    work_max = 768
    if max(h, w) > work_max:
        ratio = float(work_max) / float(max(h, w))
        wh = max(64, int(round(h * ratio)))
        ww = max(64, int(round(w * ratio)))
        tex = cv2.resize(tex_full, (ww, wh), interpolation=cv2.INTER_AREA)
        m = cv2.resize(m_full, (ww, wh), interpolation=cv2.INTER_AREA)
    else:
        tex, m = tex_full, m_full
    gray = tex[..., 0] * 0.299 + tex[..., 1] * 0.587 + tex[..., 2] * 0.114
    soft = cv2.GaussianBlur(gray, (0, 0), 1.05)
    micro = np.clip(gray - soft, -0.20, 0.20)
    # A 3px Laplacian catches logos, panel borders, and fine paint boundaries.
    # Fixed normalization avoids a costly percentile reduction and keeps the
    # response stable across mostly-dark and mostly-light liveries.
    edge = np.clip(np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3)) * 1.85, 0.0, 1.0)
    mx = np.maximum(np.maximum(tex[..., 0], tex[..., 1]), tex[..., 2])
    mn = np.minimum(np.minimum(tex[..., 0], tex[..., 1]), tex[..., 2])
    sat = np.clip((mx - mn) / (mx + 1e-6), 0.0, 1.0)
    trace = np.clip(edge * 0.82 + np.abs(micro) * 3.25 + sat * 0.10, 0.0, 1.0) * m

    selected_small = m > 0.5

    # Preserve the authored fine pattern everywhere. Livery graphics receive
    # full contrast; quiet panels retain 72% instead of being flattened into a
    # wallpaper-free but visually bland mean.
    authored_gate = 0.72 + trace * 0.28

    # Paint-edge emboss plus fine source high-pass: the material follows the
    # actual livery without synthesizing a second coarse texture layer.
    ridge = np.power(trace, 0.72) * st
    delta_m = ridge * 78.0 + micro * (92.0 * st)
    delta_r = -ridge * 52.0 - micro * (68.0 * st)
    # Keep clearcoat color alive: the legacy path pulled ridges hard toward one
    # mean, which made the blue channel the weakest/least varied part of the
    # fast proof. Use a light stabilizing pull plus its own ridge and micro
    # response so iRacing receives many distinct clearcoat shades too.
    pull = np.clip(ridge * 0.08, 0.0, 0.12)
    delta_cc = ridge * (32.0 * st) + micro * (50.0 * st)

    # Source-color response adds useful spec shades while keeping RGB output
    # semantics (M / Roughness / Clearcoat), not repainting the livery.
    denom = mx + 1e-6
    warm = np.clip((tex[..., 0] - np.maximum(tex[..., 1], tex[..., 2]) * 0.92) / denom, 0.0, 1.0) * m
    cool = np.clip((tex[..., 2] - np.maximum(tex[..., 0], tex[..., 1]) * 0.92) / denom, 0.0, 1.0) * m
    delta_m += warm * (12.0 * st) - cool * (5.0 * st)
    delta_r += -warm * (16.0 * st) + cool * (10.0 * st)
    delta_cc += -warm * (7.0 * st) + cool * (11.0 * st)

    # Small genuine cavities can read rougher; a dark BASE must not turn the
    # whole car into one matte green map. This mirrors the legacy dark-car guard
    # without recomputing its expensive crest/edge analysis.
    dark = (gray < (34.0 / 255.0)) & (edge < 0.12) & selected_small
    dark_frac = float(dark.sum()) / max(1.0, float(selected_small.sum()))
    dark_scale = float(np.clip(1.0 - (dark_frac - 0.22) / 0.33, 0.0, 1.0))
    cavity = dark.astype(np.float32) * dark_scale * 0.28 * st

    def _lift(field: np.ndarray) -> np.ndarray:
        return field if field.shape == (h, w) else cv2.resize(field, (w, h), interpolation=cv2.INTER_LINEAR)

    gate_full = _lift(authored_gate)
    dm_full, dr_full, dcc_full = _lift(delta_m), _lift(delta_r), _lift(delta_cc)
    pull_full, cavity_full = _lift(pull), _lift(cavity)
    M, R, Cc = spec[..., 0], spec[..., 1], spec[..., 2]
    selected = m_full > 0.5
    cc_target = max(16.0, float(np.mean(Cc[selected]))) if np.any(selected) else 16.0
    for plane in (M, R, Cc):
        mean = float(np.mean(plane[selected])) if np.any(selected) else float(np.mean(plane))
        np.subtract(plane, mean, out=plane)
        np.multiply(plane, gate_full, out=plane)
        np.add(plane, mean, out=plane)
    np.add(M, dm_full, out=M)
    np.add(R, dr_full, out=R)
    np.multiply(Cc, 1.0 - pull_full, out=Cc)
    np.add(Cc, cc_target * pull_full + dcc_full, out=Cc)
    for plane, target in ((M, 10.0), (R, 222.0), (Cc, 12.0)):
        np.multiply(plane, 1.0 - cavity_full, out=plane)
        np.add(plane, target * cavity_full, out=plane)

    np.clip(M, 0.0, 255.0, out=M)
    np.clip(R, 15.0, 255.0, out=R)
    np.clip(Cc, 0.0, 255.0, out=Cc)


def edge_gated_catalog_detail(
    spec: np.ndarray,
    tex_rgb_hwc: np.ndarray,
    mask_hw: np.ndarray,
    *,
    strength: float = 1.0,
) -> None:
    """In-place: keep catalog low-frequency material; gate high-frequency wallpaper by paint edges."""
    st = float(np.clip(strength, 0.0, 1.5))
    if st < 1e-6:
        return
    graphic, _gray, edge_n, _dark_int, streak = paint_graphic_weight(tex_rgb_hwc, mask_hw)
    gate = np.clip(0.05 + graphic * 0.95 + np.power(edge_n, 0.42) * 0.35 + streak * 0.25, 0.0, 1.0)
    gate = gate ** (1.02 + 0.28 * st)
    h, w = spec.shape[:2]
    k = max(3, int(round(min(h, w) / 64)) | 1)
    for ch in range(3):
        plane = spec[:, :, ch].astype(np.float32)
        low = cv2.GaussianBlur(plane, (k, k), 0)
        high = plane - low
        spec[:, :, ch] = np.clip(low + high * gate, 0.0, 255.0)


def spatial_envelope_catalog(
    spec: np.ndarray,
    tex_rgb_hwc: np.ndarray,
    mask_hw: np.ndarray,
    *,
    strength: float = 1.0,
) -> None:
    """In-place: keep catalog finish character only where the livery has graphics."""
    st = float(np.clip(strength, 0.0, 1.5))
    if st < 1e-6:
        return
    graphic, gray, edge_n, dark_interior, _streak = paint_graphic_weight(tex_rgb_hwc, mask_hw)
    m = np.clip(mask_hw.astype(np.float32), 0.0, 1.0)
    # Soft gate: void panels stay near channel means; edges/art carry full catalog texture.
    g = np.clip(0.04 + graphic * 0.96, 0.0, 1.0) ** (1.08 + 0.52 * st)
    for ch in range(3):
        mu = float(np.mean(spec[..., ch]))
        spec[..., ch] = mu + (spec[..., ch] - mu) * (0.10 + 0.90 * g)

    void_w = dark_interior.astype(np.float32) * (1.0 - np.clip(edge_n * 0.70, 0.0, 1.0)) * st * m
    # [SPB-SPEC-SCULPT dark-car diversity 2026-06-05] void_w floods Roughness->~200 and crushes
    # Metallic/Clearcoat on dark-interior pixels (a cavity reads matte). On a predominantly DARK
    # livery (black / dark-purple base) the WHOLE car qualifies as "void", so EVERY finish floods
    # to the same matte/green spec and picking different looks does nothing (owner: dark car ->
    # "majority green every time, no diversity"). This was the dominant cause (Roughness 10->172
    # on chrome). Scale void_w down as the dark fraction of the masked area rises so a dark BASE
    # colour keeps each finish's identity; genuine cavities on normal liveries still void.
    _vsel = m > 0.5
    _dark_frac = float((dark_interior.astype(bool) & _vsel).sum()) / max(1.0, float(_vsel.sum()))
    _dark_scale = float(np.clip(1.0 - (_dark_frac - 0.22) / 0.33, 0.0, 1.0))
    void_w = void_w * _dark_scale
    spec[..., 0] = np.clip(spec[..., 0] * (1.0 - void_w * 0.82) + 10.0 * void_w, 0.0, 255.0)
    spec[..., 1] = np.clip(spec[..., 1] * (1.0 - void_w * 0.12) + 228.0 * void_w * 0.88, 15.0, 255.0)
    spec[..., 2] = np.clip(spec[..., 2] * (1.0 - void_w * 0.85) + 9.0 * void_w, 0.0, 255.0)


def apply_paint_trace_prepass(
    spec: np.ndarray,
    tex_rgb_hwc: np.ndarray,
    mask_hw: np.ndarray,
    finish_id: str,
    *,
    detail_scale: float = 1.38,
    strength: float = 1.0,
    dark_interior_flatten: float = 0.72,
) -> None:
    """In-place Viva paint tracing on float spec — no procedural dot/octave grids."""
    st = float(np.clip(strength, 0.0, 1.5))
    if st < 1e-6:
        return
    DS = float(detail_scale) * st

    seed = _finish_rng_seed(finish_id)
    m = np.clip(mask_hw.astype(np.float32), 0.0, 1.0)
    M = spec[:, :, 0]
    R = spec[:, :, 1]
    Cc = spec[:, :, 2]
    # [SPB-SPEC-SCULPT clearcoat-revive 2026-06-05] Per-finish clearcoat pull-target.
    # The ridge/crest/wet/peak ops below used to pull Cc toward the literal 16.0 (the
    # global clearcoat FLOOR). That is correct for a chrome mirror (Cc ~16-30) but it
    # HALVED finishes with a genuinely live clearcoat (candy ~98-127; real-engine target
    # ~239), collapsing every Shokk-the-World "Pick a look" preview into the same warm
    # red/green wedge. Pull toward THIS finish's own masked clearcoat mean (floored at 16)
    # instead: chrome stays flat/glossy (its own mean is already ~16-30, so this is a
    # no-op there) while candy/carbon keep their live, varied clearcoat and the previews
    # span the gamut like the real combined specs. No new texture is introduced, so the
    # 2026-06-01 grid-flash cannot reappear.
    _cc_in = m > 0.5
    cc_t = max(16.0, float(np.mean(Cc[_cc_in]))) if np.any(_cc_in) else 16.0

    gray, edge_n = _viva_mexico_paint_luma_edge(tex_rgb_hwc, mask_hw)
    dark_paint = gray < (34.0 / 255.0)
    dark_interior = dark_paint & (edge_n < 0.28)
    # [SPB-SPEC-SCULPT dark-car diversity 2026-06-05] The flatten below drives Roughness->237
    # (matte) and kills Metallic/Clearcoat on dark-interior pixels — correct for small dark
    # CAVITIES, but on a predominantly DARK livery (black / dark-purple base) the WHOLE car
    # qualifies, so every finish floods to the same rough/green spec and picking different
    # looks does nothing (owner: dark car -> "majority green every time, no diversity"). Scale
    # the flatten down as the dark fraction of the masked area rises: a dark BASE colour keeps
    # each finish's identity, while genuine cavities on normal liveries still flatten.
    _dsel = m > 0.5
    _dark_frac = float((dark_interior & _dsel).sum()) / max(1.0, float(_dsel.sum()))
    _dark_scale = float(np.clip(1.0 - (_dark_frac - 0.22) / 0.33, 0.0, 1.0))
    blend_v = (
        np.clip(dark_interior.astype(np.float32) * m * 0.93, 0.0, 0.96)
        * float(np.clip(dark_interior_flatten, 0.0, 2.0))
        * _dark_scale
    )
    M[:] = np.clip(M * (1.0 - blend_v) + 8.0 * blend_v, 0.0, 255.0)
    R[:] = np.clip(R * (1.0 - blend_v) + 237.0 * blend_v, 15.0, 255.0)
    Cc[:] = np.clip(Cc * (1.0 - blend_v) + 9.0 * blend_v, 0.0, 255.0)

    h, w = M.shape
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)

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
        R - warm_w * (22.0 * DS) * chrom_interior + cool_w * (14.0 * DS) * chrom_interior,
        15.0,
        255.0,
    )
    M[:] = np.clip(
        M + warm_w * (14.0 * DS) * chrom_interior + cool_w * (-6.0 * DS) * chrom_interior,
        0.0,
        255.0,
    )
    Cc[:] = np.clip(
        Cc + warm_w * (-10.0 * DS) * chrom_interior + cool_w * (12.0 * DS) * chrom_interior,
        0.0,
        255.0,
    )

    # Ridge-linked emboss — THE panel-tracing read (Viva Mexico playbook).
    ridge_w = np.power(edge_n, 0.72) * m
    interior_suppress = (1.0 - dark_interior.astype(np.float32) * 0.65) * (
        1.0 - np.clip((gray - 0.08) / 0.18, 0.0, 1.0) * 0.25
    )
    pop = ridge_w * interior_suppress
    M[:] = np.clip(M + pop * (128.0 * DS), 0.0, 255.0)
    R[:] = np.clip(R - pop * (82.0 * DS), 15.0, 255.0)
    ridge_peak = pop > 0.22
    peak_mask = ridge_peak & (m > 0.5)
    Cc[:] = np.where(peak_mask, Cc * 0.22 + cc_t * 0.78, Cc)
    Cc[:] = np.clip(Cc, 0.0, 255.0)

    streak_soft, streak_core_f, protect_lw = _viva_mexico_highlight_crest(tex_rgb_hwc, mask_hw)
    core_hard = (streak_core_f > 0.5) & (m > 0.5)
    if np.any(core_hard):
        M[:] = np.where(core_hard, np.maximum(M, 252.0), M)
        R[:] = np.where(core_hard, np.minimum(R, 36.0), R)
        Cc[:] = np.where(core_hard, cc_t, Cc)
    wet = streak_soft * m * (1.0 - dark_paint.astype(np.float32))
    wet *= 1.0 - core_hard.astype(np.float32) * 0.92
    M[:] = np.clip(M + wet * (98.0 * DS), 0.0, 255.0)
    R[:] = np.clip(R - wet * (78.0 * DS), 15.0, 255.0)
    Cc[:] = np.where(wet > 0.10, Cc * (1.0 - wet * 0.58) + cc_t * wet * 0.58, Cc)
    Cc[:] = np.clip(Cc, 0.0, 255.0)
    if np.any(core_hard):
        k_ring = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cu8 = core_hard.astype(np.uint8)
        dil_h = cv2.dilate(cu8, k_ring, iterations=2)
        ring_lw = dil_h.astype(bool) & (~core_hard) & (m > 0.5)
        R[:] = np.where(ring_lw, np.clip(R + 36.0 * DS, 15.0, 255.0), R)
        M[:] = np.where(ring_lw, np.clip(M - 46.0 * DS, 0.0, 255.0), M)

    ripple = np.sin(xs * 54.7 + ys * 31.3) * np.sin(xs * -23.1 + ys * 47.8)
    rip_g = np.clip((gray - 0.16) / 0.72, 0.0, 1.0) * (1.0 - dark_paint.astype(np.float32) * 0.85)
    rip_w = rip_g * (0.35 + 0.65 * edge_n) * m * (1.0 - protect_lw.astype(np.float32) * 0.82)
    R[:] = np.clip(R + ripple * (16.0 * DS) * rip_w, 15.0, 255.0)

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
            Cc[:] = np.where(core, np.clip(Cc * 0.45 + cc_t * 0.55, 0.0, 255.0), Cc)
            R[:] = np.where(ring_mask, np.clip(R + 30.0 * DS, 15.0, 255.0), R)
            M[:] = np.where(ring_mask, np.clip(M - 18.0 * DS, 0.0, 255.0), M)


def imprint_paint_skeleton(
    cat_spec: np.ndarray,
    tex_rgb_hwc: np.ndarray,
    mask_hw: np.ndarray,
    finish_id: str,
    *,
    chromatic_shift: bool = False,
    skeleton_mix_m: float = 0.52,
    skeleton_mix_r: float = 0.44,
    skeleton_mix_cc: float = 0.48,
) -> np.ndarray:
    """Fuse catalog spec with paint-derived scratch skeleton (structure from livery)."""
    from engine.spec_sculpt.generate import FUSION_STRATEGY_GLOSS_WIN, fuse_registry_and_scratch_specs

    m = np.clip(mask_hw.astype(np.float32), 0.0, 1.0)
    scratch = np.asarray(
        _scratch_spec_from_paint(tex_rgb_hwc, m, finish_id, chromatic_shift=chromatic_shift),
        dtype=np.float32,
    )
    return fuse_registry_and_scratch_specs(
        cat_spec,
        scratch,
        float(skeleton_mix_m),
        float(skeleton_mix_r),
        float(skeleton_mix_cc),
        strategy=FUSION_STRATEGY_GLOSS_WIN,
    )


def imprint_scratch_highpass(
    spec: np.ndarray,
    tex_rgb_hwc: np.ndarray,
    mask_hw: np.ndarray,
    finish_id: str,
    *,
    mix: float = 0.52,
    chromatic_shift: bool = False,
) -> None:
    """In-place: replace catalog wallpaper high-freq with paint-scratch layout (keeps catalog low-freq)."""
    st = float(np.clip(mix, 0.0, 1.0))
    if st < 1e-6:
        return
    graphic, _g, edge_n, _di, streak = paint_graphic_weight(tex_rgb_hwc, mask_hw)
    gate = np.clip(0.08 + graphic * 0.92 + np.power(edge_n, 0.45) * 0.40 + streak * 0.30, 0.0, 1.0)
    m = np.clip(mask_hw.astype(np.float32), 0.0, 1.0)
    scratch = np.asarray(
        _scratch_spec_from_paint(tex_rgb_hwc, m, finish_id, chromatic_shift=chromatic_shift),
        dtype=np.float32,
    )
    h, w = spec.shape[:2]
    k = max(3, int(round(min(h, w) / 48)) | 1)
    for ch in range(3):
        plane = spec[:, :, ch]
        slow = cv2.GaussianBlur(plane, (k, k), 0)
        shigh = plane - slow
        sslow = cv2.GaussianBlur(scratch[:, :, ch], (k, k), 0)
        scratch_h = scratch[:, :, ch] - sslow
        g = gate * st
        spec[:, :, ch] = np.clip(slow + shigh * (1.0 - g * 0.85) + scratch_h * g, 0.0, 255.0)


def trace_catalog_spec(
    cat_spec: np.ndarray,
    tex_rgb_hwc: np.ndarray,
    mask_hw: np.ndarray,
    finish_id: str,
    *,
    envelope_strength: float = 1.0,
    skeleton_mix_m: float = 0.52,
    skeleton_mix_r: float = 0.44,
    skeleton_mix_cc: float = 0.48,
    trace_strength: float = 1.0,
    chromatic_shift: bool = False,
) -> np.ndarray:
    """Full paint-trace pipeline on a catalog blend (float HxWx4)."""
    spec = np.asarray(cat_spec, dtype=np.float32).copy()
    spatial_envelope_catalog(spec, tex_rgb_hwc, mask_hw, strength=envelope_strength)
    spec = imprint_paint_skeleton(
        spec,
        tex_rgb_hwc,
        mask_hw,
        finish_id,
        chromatic_shift=chromatic_shift,
        skeleton_mix_m=skeleton_mix_m,
        skeleton_mix_r=skeleton_mix_r,
        skeleton_mix_cc=skeleton_mix_cc,
    )
    apply_paint_trace_prepass(
        spec,
        tex_rgb_hwc,
        mask_hw,
        finish_id,
        strength=trace_strength,
    )
    return spec


def finalize_traced_spec_u8(
    spec_f32: np.ndarray,
    tex_rgb_hwc: np.ndarray,
    mask_hw: np.ndarray,
    *,
    void_metallic_max: float = 92.0,
    void_roughness_min: float = 158.0,
    void_clearcoat_max: float = 44.0,
) -> np.ndarray:
    """Ridge-protected void clamp (Viva post) — safe on traced catalog, no grid."""
    # [SPB-SPEC-SCULPT dark-car diversity 2026-06-05] The void clamp forces void pixels matte
    # (Metallic<=92, Roughness>=158). On a predominantly DARK livery the whole car reads as void,
    # flooding every finish to matte/green and killing look diversity (this was the dominant
    # remaining cause after the spatial_envelope fix: chrome Roughness 25->142 here). Relax the
    # clamp toward no-op as the dark fraction of the masked area rises so a dark BASE colour keeps
    # each finish's identity; genuine cavities on normal liveries still clamp. (We relax the
    # PARAMS here rather than editing the shared cultural_viva_mexico helper, so no other
    # subsystem is affected.)
    try:
        _gray, _edge = _viva_mexico_paint_luma_edge(tex_rgb_hwc, mask_hw)
        _msel = np.clip(mask_hw.astype(np.float32), 0.0, 1.0) > 0.5
        _di = (_gray < (34.0 / 255.0)) & (_edge < 0.28) & _msel
        _dark_frac = float(_di.sum()) / max(1.0, float(_msel.sum()))
        _ds = float(np.clip(1.0 - (_dark_frac - 0.22) / 0.33, 0.0, 1.0))
    except Exception:
        _ds = 1.0
    void_metallic_max = void_metallic_max + (255.0 - void_metallic_max) * (1.0 - _ds)
    void_roughness_min = void_roughness_min * _ds + 15.0 * (1.0 - _ds)
    void_clearcoat_max = void_clearcoat_max + (255.0 - void_clearcoat_max) * (1.0 - _ds)
    u8 = np.clip(np.round(spec_f32), 0, 255).astype(np.uint8)
    return _post_adjust_viva_mexico_spec(
        u8,
        tex_rgb_hwc,
        mask_hw,
        void_metallic_max=void_metallic_max,
        void_roughness_min=void_roughness_min,
        void_clearcoat_max=void_clearcoat_max,
    )
