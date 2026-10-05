"""Spec from arbitrary paint — primarily by routing presets to REAL SPB finishes.

2026-06-01 PIVOT: presets now map to real registered finish spec functions (the
diverse, proven ones the main app uses) and render through the catalog path
(``blend_registered_specs_float`` → ``_resolve_finish_spec``), **skipping the Viva
pre/post pass** — that pass stamped a grid-flash mesh on every finish and lowered
diversity. The legacy paint-derived scratch (``_scratch_spec_from_paint`` + Viva) is
kept only as the no-selection fallback.
"""

from __future__ import annotations

import cv2
import numpy as np

from engine.paint_v2.cultural_union_jacked import _scratch_spec_from_paint
from engine.paint_v2.cultural_viva_mexico import _post_adjust_viva_mexico_spec, _pre_adjust_viva_mexico_spec
from engine.spec_sculpt.catalog_blend import blend_registered_specs_float, normalize_catalog_stack
from engine.spec_sculpt.presets import normalize_preset_stack, preset_stack_to_catalog, PRESET_TILE_BY_ID

FUSION_STRATEGY_LINEAR = "linear"
FUSION_STRATEGY_GLOSS_WIN = "gloss_win_metallic"
VALID_FUSION_STRATEGIES = frozenset({FUSION_STRATEGY_LINEAR, FUSION_STRATEGY_GLOSS_WIN})

# Max real finishes blended into one spec (preset stack + catalog picks combined).
MAX_FINISH_BLEND = 5

PAINT_EMPHASIS_UNIFORM = "uniform"
PAINT_EMPHASIS_HIGHLIGHTS = "highlights"
PAINT_EMPHASIS_SHADOWS = "shadows"
PAINT_EMPHASIS_SATURATED = "saturated"
PAINT_EMPHASIS_DESATURATED = "desaturated"
VALID_PAINT_EMPHASIS = frozenset(
    {
        PAINT_EMPHASIS_UNIFORM,
        PAINT_EMPHASIS_HIGHLIGHTS,
        PAINT_EMPHASIS_SHADOWS,
        PAINT_EMPHASIS_SATURATED,
        PAINT_EMPHASIS_DESATURATED,
    }
)


def _resolve_fusion_triplet(
    fusion_mix: float,
    fusion_mix_m: float | None,
    fusion_mix_r: float | None,
    fusion_mix_cc: float | None,
) -> tuple[float, float, float]:
    fm = float(np.clip(fusion_mix, 0.0, 1.0))
    am = float(np.clip(fusion_mix_m if fusion_mix_m is not None else fm, 0.0, 1.0))
    ar = float(np.clip(fusion_mix_r if fusion_mix_r is not None else fm, 0.0, 1.0))
    ac = float(np.clip(fusion_mix_cc if fusion_mix_cc is not None else fm, 0.0, 1.0))
    return am, ar, ac


def fuse_registry_and_scratch_specs(
    spec_cat: np.ndarray,
    spec_scr: np.ndarray,
    am: float,
    ar: float,
    ac: float,
    *,
    strategy: str,
) -> np.ndarray:
    """Fuse catalog float spec with procedural scratch spec.

    ``linear``: weighted average per channel (default).
    ``gloss_win_metallic``: metallic uses ``max(cat * am, scr * (1-am))`` so brighter local
    metallic reads survive; roughness & clearcoat stay linear — closer to “show car pop”.
    """
    cat = np.asarray(spec_cat, dtype=np.float32)
    scr = np.asarray(spec_scr, dtype=np.float32)
    out = np.zeros_like(cat)
    st = strategy if strategy in VALID_FUSION_STRATEGIES else FUSION_STRATEGY_LINEAR
    if st == FUSION_STRATEGY_GLOSS_WIN:
        out[:, :, 0] = np.maximum(cat[:, :, 0] * am, scr[:, :, 0] * (1.0 - am))
        out[:, :, 1] = cat[:, :, 1] * ar + scr[:, :, 1] * (1.0 - ar)
        out[:, :, 2] = cat[:, :, 2] * ac + scr[:, :, 2] * (1.0 - ac)
    else:
        out[:, :, 0] = cat[:, :, 0] * am + scr[:, :, 0] * (1.0 - am)
        out[:, :, 1] = cat[:, :, 1] * ar + scr[:, :, 1] * (1.0 - ar)
        out[:, :, 2] = cat[:, :, 2] * ac + scr[:, :, 2] * (1.0 - ac)
    out[:, :, 3] = 255.0
    np.clip(out, 0.0, 255.0, out=out)
    return out


def apply_paint_linked_emphasis(
    spec: np.ndarray,
    tex_rgb_hwc: np.ndarray,
    *,
    emphasis: str = PAINT_EMPHASIS_UNIFORM,
    strength: float = 0.0,
    hue_deg: float | None = None,
    hue_width: float = 60.0,
    hue_strength: float = 0.0,
) -> None:
    """In-place float spec — boost metallic/clearcoat using source paint cues.

    Runs **before** ``_pre_adjust_viva_mexico_spec``. Safe no-op when uniform / zero strength.
    """
    mode = emphasis if emphasis in VALID_PAINT_EMPHASIS else PAINT_EMPHASIS_UNIFORM
    st = float(np.clip(strength, 0.0, 1.0))
    tex = np.asarray(tex_rgb_hwc[:, :, :3], dtype=np.float32)
    r, g, b = tex[..., 0], tex[..., 1], tex[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = np.where(mx > 1e-5, (mx - mn) / (mx + 1e-6), 0.0)

    if mode != PAINT_EMPHASIS_UNIFORM and st > 1e-6:
        # [SPB-SPEC-SCULPT fix#8 2026-06-02] Percentile-ADAPTIVE cues so coupling works on ANY livery
        # brightness/saturation, not just mid-tone. The old FIXED absolute thresholds (0.32/0.52) made
        # highlights-mode looks FLAT on a dark livery and shadows-mode looks FLAT on a bright one
        # (diagnosed: dark/bright galleries had 3-4 of 24 flat looks + paint-awareness 0.30-0.40 vs 0.56
        # at mid-tone). Anchoring to the livery's OWN luminance/saturation percentiles selects its
        # relatively-bright / dark / saturated regions regardless of absolute level. (Near-uniform paint
        # has no spread, but fix#7's detail floor covers that case.)
        def _norm(x, lo_p, hi_p):
            # [perf fix#12] compute percentile THRESHOLDS on a <=256 downsample (percentiles are
            # downsample-robust) but apply on full-res x -> same result, no full-res np.percentile cost.
            xs = x if x.size <= 256 * 256 else cv2.resize(x, (256, 256), interpolation=cv2.INTER_AREA)
            lo = float(np.percentile(xs, lo_p))
            hi = float(np.percentile(xs, hi_p))
            return np.clip((x - lo) / (hi - lo + 1e-4), 0.0, 1.0).astype(np.float32)
        if mode == PAINT_EMPHASIS_HIGHLIGHTS:
            w = _norm(lum, 35, 92)
            w = w * w
        elif mode == PAINT_EMPHASIS_SHADOWS:
            w = 1.0 - _norm(lum, 8, 65)
            w = w * w
        elif mode == PAINT_EMPHASIS_SATURATED:
            # [SPB-SPEC-SCULPT fix#9 2026-06-02] A monochrome/grayscale livery (B&W, carbon) has NO
            # saturation signal, so saturated/desaturated-mode looks went flat (diagnosed: gray car
            # saturated-mode detail 28.9 + 1/5 flat, desaturated 1/4 flat). When sat has no spread, fall
            # back to the luminance cue so the look still couples to the livery's texture. Gated on
            # sat.std() so colourful liveries (chevy sat.std() >> 0.02) are unchanged.
            w = _norm(sat, 30, 95) if float(sat.std()) >= 0.02 else (_norm(lum, 35, 92) ** 2)
        elif mode == PAINT_EMPHASIS_DESATURATED:
            w = (1.0 - _norm(sat, 5, 70)) if float(sat.std()) >= 0.02 else ((1.0 - _norm(lum, 8, 65)) ** 2)
        else:
            w = np.ones_like(lum, dtype=np.float32) * 0.5
        gain = 1.0 + st * (w.astype(np.float32) - 0.35) * 1.35
        gain = np.clip(gain, 0.52, 1.62)
        spec[..., 0] *= gain
        spec[..., 2] *= gain
        # [SPB-SPEC-SCULPT fix#5 2026-06-02] ADDITIVE paint coupling on top of the multiplicative
        # gain. Diagnosed (function test, 10 diverse finishes): the gain alone is swamped by finishes
        # with strong intrinsic metallic/clearcoat patterns -> paw 0.14 (nure_onna) / 0.18 (tesla_coil)
        # while neutral finishes hit 0.8+. avg paw only 0.39. A zero-mean paint signal, sized to each
        # channel's OWN variation (so it competes with the finish's pattern) plus a floor (so flat
        # channels still adapt), guarantees the livery comes through on EVERY finish without shifting
        # its mean level/tone or erasing its pattern. owner: "smartly spec out the canvas".
        wz = (w.astype(np.float32) - float(np.mean(w)))
        for _ch in (0, 2):
            _amp = st * (1.2 * float(spec[..., _ch].std()) + 28.0)
            spec[..., _ch] += _amp * wz

    hst = float(np.clip(hue_strength, 0.0, 1.0))
    if hue_deg is not None and hst > 1e-6 and hue_width > 1e-3:
        u8 = np.clip(tex * 255.0, 0.0, 255.0).astype(np.uint8)
        hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV)
        h_chan = hsv[:, :, 0].astype(np.float32)
        h_paint = h_chan * (360.0 / 180.0)
        tgt = float(hue_deg) % 360.0
        wd = float(max(hue_width, 8.0))
        d = np.abs(h_paint - tgt)
        d = np.minimum(d, 360.0 - d)
        mask = np.exp(-0.5 * (d / wd) ** 2).astype(np.float32)
        lum_gate = np.clip(lum * 1.85, 0.0, 1.0)
        gate = mask * (0.35 + 0.65 * lum_gate) * (0.25 + 0.75 * np.clip(sat * 3.5, 0.0, 1.0))
        hgain = 1.0 + hst * (gate - 0.28) * 1.55
        hgain = np.clip(hgain, 0.55, 1.65)
        spec[..., 0] *= hgain
        spec[..., 2] *= hgain


def _inject_uniform_paint_detail_floor(spec: np.ndarray, seed: int) -> None:
    """In-place: add a subtle seed-varied FINE micro-texture to M / Rgh / CC.

    Used ONLY when the source paint is near-uniform (blank canvas / solid color), where the
    paint-linked emphasis contributes ~nothing and low-intrinsic-detail finishes would otherwise
    render FLAT (the owner's forbidden "uniform result"). INDEPENDENT noise per channel so it adds
    detail WITHOUT desaturating (a single shared field would correlate the channels toward gray —
    the fix#6 trap). Multi-octave, fine-dominant (owner doctrine: small fine patterns). Deterministic
    per seed, so a look's preview tile and its /generate full render match.
    """
    h, w = spec.shape[:2]
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    # [perf fix#12] generate the fine noise at <=512 then upsample. The floor is fine-SCALE micro-
    # texture, so building it at 512 and resizing is visually equivalent but ~(2048/512)^2 = 16x cheaper
    # than 9 large-sigma GaussianBlurs at 2048 (which cost ~3s and blew the render budget on blank liveries).
    ww = int(min(max(h, w), 512))
    bw = float(ww)

    def _fine_field() -> np.ndarray:
        f = np.zeros((ww, ww), dtype=np.float32)
        for div, amp in ((256.0, 1.0), (128.0, 0.6), (64.0, 0.35)):
            sig = max(0.6, bw / div)
            n = cv2.GaussianBlur(rng.standard_normal((ww, ww)).astype(np.float32), (0, 0), sig)
            f += amp * (n / (n.std() + 1e-6))
        f = f / (f.std() + 1e-6)
        if (ww, ww) != (h, w):
            f = cv2.resize(f, (w, h), interpolation=cv2.INTER_LINEAR)
        return f

    # Roughness + clearcoat get a strong share: a chrome finish pegs metallic at 255 (the +M field
    # clips away), so the detail must survive in the rarely-saturated R/CC channels.
    spec[:, :, 0] = np.clip(spec[:, :, 0] + 28.0 * _fine_field(), 0.0, 255.0)
    spec[:, :, 1] = np.clip(spec[:, :, 1] + 26.0 * _fine_field(), 0.0, 255.0)
    spec[:, :, 2] = np.clip(spec[:, :, 2] + 30.0 * _fine_field(), 0.0, 255.0)


def apply_sculpt_mask(spec, sculpt_mask, *, neutral=(0, 160, 0), feather=2.0):
    """LAYER-AWARE SCULPT (2026-06-24, Spec Sculpt prototype): keep the sculpted spec ONLY where
    ``sculpt_mask`` > 0 (the layers the user chose to sculpt); everywhere else fall back to a flat
    NEUTRAL spec (default matte M=0 / R=160 / Cc=0) so sponsors / logos / numbers / decals are NOT
    sculpted into metal/gloss. ``sculpt_mask`` = HxW float 0..1 or 0..255 (or bool / HxWxA). Edges
    soft-feathered. Returns HxWx3 uint8. No-op (returns ``spec`` unchanged) when ``sculpt_mask`` is None."""
    if sculpt_mask is None:
        return spec
    s = np.asarray(spec)
    h, w = s.shape[:2]
    m = np.asarray(sculpt_mask, dtype=np.float32)
    if m.ndim == 3:
        m = m[:, :, 3] if m.shape[2] == 4 else (m[:, :, 0] if m.shape[2] == 1 else m.mean(axis=2))
    if float(m.max() if m.size else 0.0) > 1.5:
        m = m / 255.0
    if m.shape[:2] != (h, w):
        m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)
    if feather and feather > 0:
        k = max(1, int(feather)) * 2 + 1
        m = cv2.GaussianBlur(m, (k, k), float(feather))
    m = np.clip(m, 0.0, 1.0)[:, :, None]
    neu = s.astype(np.float32).copy()  # preserve any alpha / extra channels; only M/R/Cc go neutral
    neu[:, :, 0] = float(neutral[0]); neu[:, :, 1] = float(neutral[1]); neu[:, :, 2] = float(neutral[2])
    out = s.astype(np.float32) * m + neu * (1.0 - m)
    return np.clip(out, 0, 255).astype(np.uint8)


def hsb_shift(tex, h_deg=0.0, s_mult=1.0, v_mult=1.0):
    """Recolor the SOURCE PAINT before sculpting (#HSB, 2026-06-25): shift Hue by ``h_deg`` degrees and scale
    Saturation / Brightness. Lets a user change a pink base to blue (or brighten/darken zones — which the
    FRACTURED color-shift finishes key off of) from inside Spec Sculpt. Accepts float 0..1 OR uint8; returns
    float 0..1 (alpha preserved). Guarded + no-op when all neutral."""
    try:
        if abs(float(h_deg)) < 0.5 and abs(float(s_mult) - 1.0) < 1e-3 and abs(float(v_mult) - 1.0) < 1e-3:
            return tex
        a = np.asarray(tex, dtype=np.float32)
        if a.ndim == 2:
            a = np.stack([a] * 3, axis=-1)
        rgb = a[:, :, :3]
        if float(rgb.max() if rgb.size else 0.0) > 1.5:
            rgb = rgb / 255.0
        hsv = cv2.cvtColor(np.clip(rgb, 0.0, 1.0).astype(np.float32), cv2.COLOR_RGB2HSV)  # H 0..360, S/V 0..1
        hsv[:, :, 0] = np.mod(hsv[:, :, 0] + float(h_deg), 360.0)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * float(s_mult), 0.0, 1.0)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * float(v_mult), 0.0, 1.0)
        out = np.clip(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB), 0.0, 1.0)
        if a.ndim == 3 and a.shape[2] == 4:
            al = a[:, :, 3:4]
            if float(al.max() if al.size else 0.0) > 1.5:
                al = al / 255.0
            return np.concatenate([out, np.clip(al, 0.0, 1.0)], axis=2)
        return out
    except Exception:
        return tex


def auto_levels(tex, strength=1.0, low_pct=1.0, high_pct=99.0):
    """Auto-contrast the source paint before sculpting (#48, 2026-06-25).

    Per-channel percentile stretch (``low_pct``..``high_pct`` → 0..1), blended by ``strength``. A flat /
    washed-out livery gets normalized contrast so the luminance/saturation-keyed spec derivation has more to
    work with. Accepts float 0..1 OR uint8 0..255; returns float 0..1 (alpha preserved). Guarded — returns the
    input unchanged on any failure or a degenerate (already-flat) channel."""
    try:
        a = np.asarray(tex, dtype=np.float32)
        if a.ndim == 2:
            a = np.stack([a] * 3, axis=-1)
        rgb = a[:, :, :3]
        if float(rgb.max() if rgb.size else 0.0) > 1.5:
            rgb = rgb / 255.0
        s = max(0.0, min(1.0, float(strength)))
        if s <= 0.0:
            return np.clip(rgb, 0.0, 1.0)
        out = rgb.copy()
        for c in range(3):
            ch = rgb[:, :, c]
            lo = float(np.percentile(ch, low_pct))
            hi = float(np.percentile(ch, high_pct))
            if hi - lo < 1e-3:
                continue
            stretched = np.clip((ch - lo) / (hi - lo), 0.0, 1.0)
            out[:, :, c] = ch * (1.0 - s) + stretched * s
        out = np.clip(out, 0.0, 1.0)
        if a.ndim == 3 and a.shape[2] == 4:
            alpha = a[:, :, 3:4]
            if float(alpha.max() if alpha.size else 0.0) > 1.5:
                alpha = alpha / 255.0
            return np.concatenate([out, np.clip(alpha, 0.0, 1.0)], axis=-1)
        return out
    except Exception:
        return tex


def apply_channel_gain(spec, gm=1.0, gr=1.0, gcc=1.0):
    """Per-channel fine-trim gain on a built spec (#49, 2026-06-25): multiply Metallic/Roughness/Clearcoat
    by ``gm``/``gr``/``gcc`` and clip 0..255. A power-user nudge; the route runs ``iron_fix`` after so the
    result stays iRacing-legal. No-op when all gains ≈ 1. Guarded — returns the input on any failure."""
    try:
        if abs(float(gm) - 1.0) < 1e-3 and abs(float(gr) - 1.0) < 1e-3 and abs(float(gcc) - 1.0) < 1e-3:
            return spec
        s = np.asarray(spec).astype(np.float32)
        if s.ndim != 3 or s.shape[2] < 3:
            return spec
        s[:, :, 0] = np.clip(s[:, :, 0] * float(gm), 0, 255)
        s[:, :, 1] = np.clip(s[:, :, 1] * float(gr), 0, 255)
        s[:, :, 2] = np.clip(s[:, :, 2] * float(gcc), 0, 255)
        return s.astype(np.uint8)
    except Exception:
        return spec


def refine_sculpt_mask(mask, grow=0):
    """Grow / shrink the PROTECTED region of a sculpt mask (#24 Mask refine, 2026-06-25).

    ``mask`` convention (as returned by ``build_protect_mask``): 255 = sculpt, 0 = protected.
    ``grow`` in pixels:
        grow > 0  → EXPAND protection (erode the sculpt region) — shield a bigger halo around logos.
        grow < 0  → CONTRACT protection (dilate the sculpt region) — sculpt closer to the edges.
    No-op when ``mask`` is None or ``grow`` == 0. Feathering of the boundary is handled separately by
    ``apply_sculpt_mask(..., feather=...)``. Robust: clamps the kernel and swallows cv2 errors."""
    if mask is None or not grow:
        return mask
    try:
        m = np.asarray(mask)
        g = min(64, int(abs(grow)))
        if g <= 0:
            return mask
        k = np.ones((g * 2 + 1, g * 2 + 1), np.uint8)
        return cv2.erode(m, k) if grow > 0 else cv2.dilate(m, k)
    except Exception:
        return mask


def _normalize_rgb_u8(tex):
    """tex (HxWx3/4, float 0..1 or 0..255, or HxW) -> uint8 RGB HxWx3, or None."""
    a = np.asarray(tex)
    if a.ndim == 2:
        a = np.stack([a] * 3, axis=-1)
    if a.ndim != 3 or a.shape[2] < 3:
        return None
    a = a[:, :, :3]
    if a.dtype == np.uint8:
        return np.ascontiguousarray(a)
    af = np.nan_to_num(a.astype(np.float32), nan=0.0, posinf=255.0, neginf=0.0)
    if af.size == 0:
        return None
    hi = float(np.percentile(af, 99.5))
    if hi <= 1.5:
        af = af * 255.0
    elif hi > 255.0:
        af = af * (255.0 / hi)
    return np.ascontiguousarray(np.clip(af, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------------------------------------------
# Signal 1: grill / mesh — LOCAL periodic texture (a periodic island surrounded by aperiodic paint).
# ---------------------------------------------------------------------------------------------------
def _grill_mesh_periodic_mask(lum, grad, st):
    """Return uint8 HxW mask (255 where local-periodic mesh) or None. Over-protect safe: a globally
    periodic BASE (carbon weave / hex / grid) trips the GLOBAL-PERIODICITY bail or fails the LOCAL-
    CONTRAST test and yields nothing."""
    Hw, Ww = lum.shape
    WIN = max(48, (min(Hw, Ww) // 10) | 1)
    STEP = max(24, WIN // 2)
    gx = (Ww - WIN) // STEP + 1
    gy = (Hw - WIN) // STEP + 1
    if gx < 3 or gy < 3:
        return None
    win2d = np.outer(np.hanning(WIN), np.hanning(WIN)).astype(np.float32)
    score = np.zeros((gy, gx), np.float32)
    detail = np.zeros((gy, gx), np.float32)
    fy = np.fft.fftfreq(WIN)[:, None]
    fx = np.fft.fftfreq(WIN)[None, :]
    rad = np.sqrt(fy * fy + fx * fx)
    lowcore = rad < (3.0 / WIN)
    nyq_ring = rad > 0.47
    valid = ~(lowcore | nyq_ring)
    for j in range(gy):
        for i in range(gx):
            y = j * STEP
            x = i * STEP
            w = lum[y:y + WIN, x:x + WIN]
            detail[j, i] = float(grad[y:y + WIN, x:x + WIN].mean())
            w = (w - w.mean()) * win2d
            P = np.abs(np.fft.fft2(w)) ** 2
            P = P * valid
            tot = float(P.sum())
            if tot < 1e-8:
                continue
            flat = np.sort(P.ravel())
            topk = float(flat[-6:].sum())
            peak = topk / tot
            ang_axis = float(P[:, :3].sum() + P[:, -2:].sum() + P[:3, :].sum() + P[-2:, :].sum())
            aniso = ang_axis / tot
            score[j, i] = peak * (0.5 + 0.5 * aniso)
    pk_thr = 0.085 - 0.02 * (st - 1.0)
    det_thr = max(1e-4, float(np.percentile(grad, 60)))
    cells = (score > pk_thr) & (detail > det_thr)
    if cells.sum() == 0:
        return None
    # GLOBAL-PERIODICITY bail (TIGHTENED): a real grill is a small localized region of the UV. If
    # periodic cells cover more than ~14% of the windows, the periodicity is a GLOBAL feature (carbon
    # weave, hex/grid base, or — the real-livery trap — an iRacing TEMPLATE wireframe/grid overlay), not
    # a grill. Fail closed.
    if float(cells.mean()) > 0.14:
        return None
    # LOCAL-CONTRAST (TIGHTENED): kept cell's periodicity must be MARKEDLY higher than its 8-neighbour
    # halo (center > ~2x halo). A globally-periodic field has a uniformly high halo so nothing passes.
    halo = cv2.blur(score, (3, 3)) - score / 9.0           # mean of the 8 neighbours (approx)
    local_pop = (score > pk_thr) & (halo < (0.50 * score)) & (score > (pk_thr + 0.03))
    keep_cells = cells & local_pop
    if keep_cells.sum() == 0:
        return None
    # ISOLATION: the surviving periodic cells must form a COMPACT island, not a sprawling component that
    # snakes across the whole UV (which is what a global template grid produces). Reject if any kept
    # component spans more than ~45% of the grid in either axis OR the kept cells are too scattered.
    kc = keep_cells.astype(np.uint8)
    ncc, lcc, scc, _ = cv2.connectedComponentsWithStats(kc, 8)
    keep2 = np.zeros_like(kc)
    for ci in range(1, ncc):
        cw = scc[ci, cv2.CC_STAT_WIDTH]
        ch = scc[ci, cv2.CC_STAT_HEIGHT]
        if cw > 0.45 * gx or ch > 0.45 * gy:
            continue                                        # sprawling -> a global grid, not a grill
        keep2[lcc == ci] = 1
    if keep2.sum() == 0:
        return None
    m = np.zeros((Hw, Ww), np.uint8)
    ys, xs = np.where(keep2 > 0)
    for j, i in zip(ys, xs):
        y = j * STEP
        x = i * STEP
        m[y:y + WIN, x:x + WIN] = 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    fine = (grad > det_thr).astype(np.uint8)
    fine = cv2.dilate(fine, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    m = m & (fine * 255)
    mf = float((m > 0).mean())
    if mf < 1e-4 or mf > 0.10:                              # grill clusters are small; bigger -> base
        return None
    return m


# ---------------------------------------------------------------------------------------------------
# Signal 3: color-agnostic SWT/MSER glyph detector (COLORED numbers / bold wordmarks on busy bases).
# ---------------------------------------------------------------------------------------------------
def _glyph_swt_mask(f, Hw, Ww, N):
    """Return uint8 HxW mask (1 where a stable, consistent-stroke-width glyph region) or None.
    Color-agnostic: keys on local lightness+chroma contrast so yellow/red numbers light up. Stroke-
    width consistency rejects flake/weave/candy/grid (their 'strokes' vary wildly)."""
    u8 = np.uint8
    f32 = np.float32
    try:
        lab = cv2.cvtColor((np.clip(f, 0, 1) * 255).astype(u8), cv2.COLOR_RGB2LAB).astype(f32)
    except Exception:
        return None
    Lc = lab[..., 0] / 2.55
    Ac = lab[..., 1] - 128.0
    Bc = lab[..., 2] - 128.0
    chroma = np.sqrt(Ac * Ac + Bc * Bc)
    k = max(3, (min(Hw, Ww) // 90) | 1)
    ker = np.ones((k, k), u8)

    def local_range(x):
        return cv2.dilate(x, ker) - cv2.erode(x, ker)

    lc = local_range(Lc) / 100.0 + 0.6 * local_range(chroma) / 128.0
    lc = cv2.normalize(lc, None, 0, 255, cv2.NORM_MINMAX).astype(u8)

    area_lo = max(8, int(6e-5 * N))
    area_hi = int(8e-3 * N)
    try:
        mser = cv2.MSER_create()
        mser.setDelta(5)
        mser.setMinArea(area_lo)
        mser.setMaxArea(area_hi)
        try:
            mser.setMaxVariation(0.30)
        except Exception:
            pass
        regions, _ = mser.detectRegions(lc)
        regions = list(regions) + list(mser.detectRegions(255 - lc)[0])
    except Exception:
        return None

    glyph = np.zeros((Hw, Ww), u8)
    n_keep = 0
    for pts in regions:
        xs = pts[:, 0]
        ys = pts[:, 1]
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        bw = x1 - x0 + 1
        bh = y1 - y0 + 1
        if max(bw, bh) > 0.55 * max(Hw, Ww):
            continue
        asp = max(bw, bh) / max(1, min(bw, bh))
        if asp > 12:
            continue
        blob = np.zeros((bh, bw), u8)
        blob[ys - y0, xs - x0] = 1
        fillf = float(blob.mean())
        if fillf > 0.92:
            continue
        dt = cv2.distanceTransform(blob, cv2.DIST_L2, 3)
        ridge = dt >= (cv2.dilate(dt, np.ones((3, 3), f32)) - 1e-3)
        sw = 2.0 * dt[ridge & (dt > 0.5)]
        if sw.size < 8:
            continue
        sw_mean = float(sw.mean())
        sw_cv = float(sw.std() / (sw_mean + 1e-6))
        thick = sw_mean / max(1.0, min(bw, bh))
        if sw_cv > 0.48:
            continue
        if not (0.08 <= thick <= 0.42):
            continue
        glyph[ys, xs] = 1
        n_keep += 1
    if n_keep == 0:
        return None
    return glyph


def _glyph_textline_mask(f, Hw, Ww, N, cap, H0, W0):
    """TEXT-LINE recall fallback (2026-06-25). When the full fusion bails on a BUSY all-over livery, recover
    the numbers/wordmarks by keeping ONLY glyph components that form TEXT ROWS: a horizontal run of >=2
    components that share a baseline, have consistent height, and sit adjacently (letters of a word/number).
    This is the principled discriminator the earlier glyph-only fallback lacked — camo blobs (random size/
    position) and carbon/weave grids (uniform 2-D lattice, too many rows) do NOT form coherent isolated text
    rows, so they are rejected and the over-protect guarantee holds. Returns a (0=protect,255=sculpt) mask at
    (H0,W0) or None."""
    try:
        glyph = _glyph_swt_mask(f, Hw, Ww, N)
        if glyph is None:
            return None
        g = (glyph > 0).astype(np.uint8)
        g = cv2.morphologyEx(g, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        if not g.any():
            return None
        lum = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
        n, lbl, stats, cent = cv2.connectedComponentsWithStats(g, 8)
        amin = max(12.0, 9e-5 * N)
        amax = 0.04 * N
        comps = []   # (cx, cy, x, y, w, h, label)
        for i in range(1, n):
            ar = stats[i, cv2.CC_STAT_AREA]
            if ar < amin or ar > amax:
                continue
            x = stats[i, cv2.CC_STAT_LEFT]; y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]; h = stats[i, cv2.CC_STAT_HEIGHT]
            if w >= 0.55 * Ww or h >= 0.55 * Hw:
                continue
            if max(w, h) / max(1, min(w, h)) > 10.0:   # weave/grid slivers
                continue
            ext = ar / float(max(1, w * h))
            if ext < 0.12:
                continue
            comps.append((float(cent[i][0]), float(cent[i][1]), int(x), int(y), int(w), int(h), i))
        if len(comps) < 2:
            return None
        med_h = float(np.median([c[5] for c in comps]))
        if med_h < 2:
            return None

        # ---- cluster into horizontal rows by y-center ----
        comps.sort(key=lambda c: c[1])
        rows = []
        for c in comps:
            placed = False
            for row in rows:
                cy_mean = sum(rc[1] for rc in row) / len(row)
                if abs(c[1] - cy_mean) < 0.6 * med_h:
                    row.append(c); placed = True; break
            if not placed:
                rows.append([c])

        # ---- validate each row as TEXT: >=2 similar-height, horizontally-adjacent, contrasty comps ----
        kept_labels = []
        text_rows = 0
        for row in rows:
            if len(row) < 2:
                continue
            hs = np.array([rc[5] for rc in row], np.float32)
            if float(hs.std() / (hs.mean() + 1e-6)) > 0.65:     # letters of a word are similar height
                continue
            row.sort(key=lambda c: c[0])                        # left-to-right
            wmed = float(np.median([rc[4] for rc in row]))
            adj = 0
            for a, b in zip(row[:-1], row[1:]):
                gap = (b[2]) - (a[2] + a[4])                    # x-gap between consecutive comps
                if -0.3 * wmed <= gap <= 2.2 * wmed:            # adjacent (kerning), not scattered
                    adj += 1
            if adj < len(row) - 1:                              # most comps must be adjacent in the run
                continue
            # standout: the row must contrast against the strip just above/below it (text sits ON a base)
            x0 = min(rc[2] for rc in row); x1 = max(rc[2] + rc[4] for rc in row)
            y0 = min(rc[3] for rc in row); y1 = max(rc[3] + rc[5] for rc in row)
            pad = max(2, int(0.6 * med_h))
            inner = lum[max(0, y0):min(Hw, y1), max(0, x0):min(Ww, x1)]
            ring_t = lum[max(0, y0 - pad):y0, max(0, x0):min(Ww, x1)]
            ring_b = lum[y1:min(Hw, y1 + pad), max(0, x0):min(Ww, x1)]
            ring = np.concatenate([r.ravel() for r in (ring_t, ring_b) if r.size]) if (ring_t.size or ring_b.size) else inner.ravel()
            if inner.size and ring.size and abs(float(inner.mean()) - float(ring.mean())) < 0.06:
                continue
            text_rows += 1
            kept_labels.extend(rc[6] for rc in row)
        if not kept_labels:
            return None

        # ---- GRID / TEXTURE rejection: a real livery has a FEW text rows; a weave/dot grid makes many
        #      uniform rows. If there are lots of "text" rows AND they are near-uniformly spaced, bail. ----
        if text_rows >= 14:
            row_ys = sorted(sum(rc[1] for rc in row) / len(row)
                            for row in rows if len(row) >= 2)
            if len(row_ys) >= 14:
                gaps = np.diff(row_ys)
                if gaps.size and float(gaps.std() / (gaps.mean() + 1e-6)) < 0.30:   # many + very even = grid
                    return None

        keep = np.isin(lbl, kept_labels).astype(np.uint8) * 255
        gf = float((keep > 0).mean())
        tight = min(float(cap), 0.26)
        if gf < 0.0006 or gf > tight:
            return None
        occ = cv2.resize((keep > 0).astype(np.float32), (16, 16), interpolation=cv2.INTER_AREA)
        if float((occ > 0.20).mean()) > 0.5:
            return None
        keep = cv2.dilate(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        mask_small = np.where(keep > 0, np.uint8(0), np.uint8(255))
        mask = mask_small if (Hw, Ww) == (H0, W0) else cv2.resize(
            mask_small, (W0, H0), interpolation=cv2.INTER_NEAREST)
        if float((mask == 0).mean()) > tight:
            return None
        return np.ascontiguousarray(mask, dtype=np.uint8)
    except Exception:
        return None


# ---------------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------------
def auto_protect_mask_from_paint(tex, strength=1.0, max_protect_frac=0.55):
    """Decipher likely decals/numbers/logos/template-features in a FLAT car texture -> SCULPT mask.

    v2: adds (1) local periodic grill/vent mesh, (2) smooth dark-housed light clusters, (3) color-
    agnostic stroke-width-consistent glyphs (colored numbers) on top of the existing standout-edge +
    base-color-deviation + extreme-luminance fusion. All signals are fused BEFORE the global-busy,
    patterned-base, and cap guards, which remain the final authority.

    Returns uint8 HxW mask (255=SCULPT, 0=PROTECT), or None when unsure. Never throws."""
    try:
        rgb_full = _normalize_rgb_u8(tex)
        if rgb_full is None:
            return None
        H0, W0 = rgb_full.shape[:2]
        if H0 < 16 or W0 < 16:
            return None

        st = float(np.clip(strength, 0.0, 2.0))
        cap = float(np.clip(max_protect_frac, 0.05, 0.95))

        WORK = 768
        s = min(1.0, WORK / float(max(H0, W0)))
        if s < 1.0:
            Ww = max(16, int(round(W0 * s)))
            Hw = max(16, int(round(H0 * s)))
            small = cv2.resize(rgb_full, (Ww, Hw), interpolation=cv2.INTER_AREA)
        else:
            small = rgb_full
            Hw, Ww = H0, W0
        N = Hw * Ww

        f = small.astype(np.float32) / 255.0
        r, g, b = f[..., 0], f[..., 1], f[..., 2]
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        mx = np.maximum(np.maximum(r, g), b)
        mn = np.minimum(np.minimum(r, g), b)
        sat = mx - mn
        V = mx

        def gmag(ch):
            gx = cv2.Sobel(ch, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(ch, cv2.CV_32F, 0, 1, ksize=3)
            return cv2.magnitude(gx, gy)

        grad = gmag(lum)
        for c in range(3):
            grad = np.maximum(grad, gmag(f[..., c]) * 0.85)
        grad = cv2.GaussianBlur(grad, (0, 0), 1.0)

        bk = max(15, (min(Hw, Ww) // 12) | 1)
        base_g = cv2.blur(grad, (bk, bk))
        gp80 = float(np.percentile(grad, 80)) + 1e-6
        g_glob_hi = max(float(np.percentile(grad, 92)) * 1.5, 0.30)
        REL = 2.2
        ABS_FRAC = 0.6
        standout = (grad > (base_g * REL + ABS_FRAC * gp80)).astype(np.uint8)
        edge_frac = float(standout.mean())

        sigma = max(6.0, 0.045 * max(Hw, Ww))
        base_col = cv2.GaussianBlur(f, (0, 0), sigma)
        dev = np.abs(f - base_col).sum(axis=2)

        base_lum = float(np.median(lum))
        white_px = (V > 0.85) & (sat < 0.18)
        black_px = (V < 0.12)
        if base_lum > 0.78:
            white_px[:] = False
        if base_lum < 0.16:
            black_px[:] = False
        extreme = (white_px | black_px)

        dev_floor = float(np.clip(0.18 - 0.05 * (st - 1.0), 0.12, 0.30))
        dev_thr = max(dev_floor, float(np.percentile(dev, 92)))
        cand = (dev > dev_thr) | extreme
        cand = cand.astype(np.uint8)

        # ---------------- SIGNAL 2: light-cluster contributor (fused into cand) ----------------
        # warm/red taillight term + near-white headlight term, each requiring smooth interior, then a
        # per-blob dark-housing ring. Field-level fraction gate: a glassy/bright BASE bails the whole cue.
        warm = (r - np.maximum(g, b))
        tail = (warm > 0.18) & (V > 0.45) & (r > 0.50)
        v_hi = max(0.80, float(np.percentile(V, 97)) - 0.02)
        head = (V > v_hi) & (sat < 0.28) & (V > base_col.max(axis=2) + 0.12)
        bright_light = (tail | head)
        g_lo = float(np.percentile(grad, 55)) + 1e-6
        smooth = cv2.GaussianBlur((grad < g_lo).astype(np.float32), (0, 0), 2.0) > 0.5
        light_seed = (bright_light & smooth).astype(np.uint8)
        light_seed = cv2.morphologyEx(light_seed, cv2.MORPH_OPEN,
                                      cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        light_seed = cv2.morphologyEx(light_seed, cv2.MORPH_CLOSE,
                                      cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
        if float(light_seed.mean()) > 0.06:
            light_seed[:] = 0  # too much "light" => it's the base, bail this cue
        if light_seed.any():
            n2, lbl2, st2, _ = cv2.connectedComponentsWithStats(light_seed, 8)
            grad_p75 = float(np.percentile(grad, 75))
            for i in range(1, n2):
                ar = st2[i, cv2.CC_STAT_AREA]
                if ar < max(12.0, 6e-5 * N) or ar > 0.04 * N:
                    continue
                bw_ = st2[i, cv2.CC_STAT_WIDTH]
                bh_ = st2[i, cv2.CC_STAT_HEIGHT]
                if max(bw_, bh_) / max(1, min(bw_, bh_)) > 3.5:
                    continue
                comp = (lbl2 == i).astype(np.uint8)
                if comp.sum() / float(max(1, bw_ * bh_)) < 0.45:
                    continue
                ring = (cv2.dilate(comp, np.ones((9, 9), np.uint8)) - comp).astype(bool)
                if ring.sum() < 12:
                    continue
                if float(V[comp > 0].mean()) - float(V[ring].mean()) < 0.18:
                    continue
                if float(grad[comp > 0].mean()) > grad_p75:
                    continue
                cand = (cand.astype(bool) | (comp > 0)).astype(np.uint8)

        # ---------------- SIGNAL 3: color-agnostic glyph recall (fused into cand) ----------------
        # Only run when not already globally busy (keeps cost + over-fire down). Additive into cand,
        # then every downstream guard re-checks it.
        if float(cand.mean()) < 0.34:
            glyph = _glyph_swt_mask(f, Hw, Ww, N)
            if glyph is not None:
                cand = (cand.astype(bool) | (glyph > 0)).astype(np.uint8)

        k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, k5, iterations=1)
        cand = cv2.morphologyEx(
            cand, cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=1)

        cand_frac = float(cand.mean())

        # High-confidence TEXT-LINE fallback for busy all-over liveries (computed once; None on textured
        # bases — camo/weave/carbon don't form coherent isolated text rows).
        glyph_fb = _glyph_textline_mask(f, Hw, Ww, N, cap, H0, W0)

        if cand_frac > 0.34:
            dev_thr2 = max(0.34, float(np.percentile(dev, 98.5)))
            cand2 = ((dev > dev_thr2) | white_px).astype(np.uint8)
            # busy-retry also gets the color-agnostic glyph recall (the colored-number miss on busy bases)
            glyph2 = _glyph_swt_mask(f, Hw, Ww, N)
            if glyph2 is not None:
                cand2 = (cand2.astype(bool) | (glyph2 > 0)).astype(np.uint8)
            cand2 = cv2.morphologyEx(cand2, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
            cand2 = cv2.morphologyEx(cand2, cv2.MORPH_CLOSE, k5)
            cand2 = cv2.morphologyEx(cand2, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
            cf2 = float(cand2.mean())
            if 0.0006 < cf2 < 0.30:
                cand = cand2
                cand_frac = cf2
            else:
                return glyph_fb            # busy base drowned the candidate -> text rows only

        if edge_frac > 0.20:
            return glyph_fb                # very busy field -> text rows only (None if no coherent text)
        if cand_frac < 0.0006 or cand_frac > 0.34:
            return glyph_fb

        G = 16
        occ = cv2.resize(cand.astype(np.float32), (G, G), interpolation=cv2.INTER_AREA)
        cell_hit = float((occ > 0.02).mean())
        cell_busy = float((occ > 0.20).mean())
        if cell_hit > 0.82 and cand_frac > 0.08:
            return glyph_fb                # candidate blankets the car -> text rows only
        if cell_busy > 0.45:
            return glyph_fb
        if occ.std() < 0.05 and cell_hit > 0.6:
            return glyph_fb

        n_lbl, lbl, stats, _ = cv2.connectedComponentsWithStats(cand, 8)
        if n_lbl > 6000:
            return glyph_fb

        protect = np.zeros((Hw, Ww), np.uint8)
        area_min = max(8.0, 8e-5 * N)
        area_max = 0.12 * N
        ring_ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        kept_any = False
        kept_areas = []
        kept_colors = []

        for i in range(1, n_lbl):
            ar = stats[i, cv2.CC_STAT_AREA]
            if ar < area_min or ar > area_max:
                continue
            bw = stats[i, cv2.CC_STAT_WIDTH]
            bh = stats[i, cv2.CC_STAT_HEIGHT]
            if bw >= 0.82 * Ww or bh >= 0.82 * Hw:
                continue
            longside = max(bw, bh)
            shortside = max(1, min(bw, bh))
            if longside / shortside > 14.0:
                continue
            extent = ar / float(max(1, bw * bh))
            if extent < 0.10:
                continue

            comp = (lbl == i).astype(np.uint8)
            dil_in = cv2.dilate(comp, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
            dil = cv2.dilate(comp, ring_ker)
            ring = (dil > 0) & (dil_in == 0)
            rsum = int(ring.sum())
            if rsum < 8:
                continue
            ring_busy = float(cand[ring].mean())
            if ring_busy > 0.45:
                continue
            g_ring = float(grad[ring].mean())
            if g_ring > g_glob_hi:
                continue

            cmask = comp > 0
            protect[cmask] = 255
            kept_any = True
            kept_areas.append(float(ar))
            kept_colors.append(f[cmask].mean(axis=0))

        # ---------------- SIGNAL 1: grill/vent mesh fused into protect BEFORE the guards ----------------
        grill = _grill_mesh_periodic_mask(lum, grad, st)
        if grill is not None and grill.any():
            protect = np.maximum(protect, grill)
            kept_any = True
            # feed the grill blobs to the patterned-base bookkeeping too, so it still gates them.
            ng, lbg, stg, _ = cv2.connectedComponentsWithStats((grill > 0).astype(np.uint8), 8)
            for j in range(1, ng):
                mg = (lbg == j)
                if mg.sum() < area_min:
                    continue
                kept_areas.append(float(stg[j, cv2.CC_STAT_AREA]))
                kept_colors.append(f[mg].mean(axis=0))

        # PATTERNED-BASE guard: many same-size, same-color islands = repeating motif BASE -> bail.
        if len(kept_areas) >= 18:
            _ar = np.asarray(kept_areas, np.float32)
            _cv = float(_ar.std() / (_ar.mean() + 1e-6))
            _cols = np.asarray(kept_colors, np.float32)
            _spread = float(np.mean(np.std(_cols, axis=0))) if _cols.size else 1.0
            if _cv < 0.55 and _spread < 0.12:
                return None

        if not kept_any:
            return None

        protect = cv2.morphologyEx(
            protect, cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        protect = cv2.dilate(
            protect, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))

        prot_frac = float((protect > 0).mean())
        if prot_frac < 0.0006 or prot_frac > cap:
            return None

        mask_small = np.where(protect > 0, np.uint8(0), np.uint8(255))
        if (Hw, Ww) != (H0, W0):
            mask = cv2.resize(mask_small, (W0, H0), interpolation=cv2.INTER_NEAREST)
        else:
            mask = mask_small
        if float((mask == 0).mean()) > cap:
            return None
        return np.ascontiguousarray(mask, dtype=np.uint8)
    except Exception:
        return None


def separate_livery_layers(tex, sensitivity=1.0, number_size=1.0, max_decal_frac=0.6):
    """AUTO-SEPARATE (2026-06-26): best-effort split of a FLAT livery (TGA/PNG/JPEG, no PSD) into three
    masks — NUMBERS, SPONSORS (logos + wordmarks), and PAINT (the base) — so the main app can lift a flat
    paint into editable layers. Reuses Spec Sculpt's decal detectors (glyph SWT/MSER + standout-edge
    islands), then classifies: the TALLEST text glyphs = car NUMBERS; remaining text + non-text islands =
    SPONSORS; everything else = PAINT.

    Tunable (tolerance sliders):
      sensitivity 0.3..2.0 — higher detects MORE as decals (lower size floor + looser standout).
      number_size 0.4..2.5 — glyph height (× the livery's median glyph height) above which a glyph is a
                              NUMBER rather than sponsor text.
    Returns {"numbers","sponsors","paint"} of full-res HxW uint8 masks (255 = member), or None. Never raises."""
    try:
        rgb_full = _normalize_rgb_u8(tex)
        if rgb_full is None:
            return None
        H0, W0 = rgb_full.shape[:2]
        if H0 < 16 or W0 < 16:
            return None
        sens = float(np.clip(sensitivity, 0.3, 2.0))
        nsz = float(np.clip(number_size, 0.4, 2.5))
        WORK = 768
        s = min(1.0, WORK / float(max(H0, W0)))
        if s < 1.0:
            Ww = max(16, int(round(W0 * s))); Hw = max(16, int(round(H0 * s)))
            small = cv2.resize(rgb_full, (Ww, Hw), interpolation=cv2.INTER_AREA)
        else:
            small = rgb_full; Hw, Ww = H0, W0
        N = Hw * Ww
        f = small.astype(np.float32) / 255.0
        lum = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]

        numbers = np.zeros((Hw, Ww), np.uint8)
        sponsors = np.zeros((Hw, Ww), np.uint8)

        # ---------------- TEXT glyphs -> NUMBERS (tallest) vs SPONSOR text ----------------
        glyph = _glyph_swt_mask(f, Hw, Ww, N)
        if glyph is not None:
            g = cv2.morphologyEx((glyph > 0).astype(np.uint8), cv2.MORPH_OPEN,
                                 cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
            n, lbl, stats, _ = cv2.connectedComponentsWithStats(g, 8)
            amin = max(10.0, (8e-5 / sens) * N)
            amax = 0.05 * N
            heights, comps = [], []
            for i in range(1, n):
                ar = stats[i, cv2.CC_STAT_AREA]
                if ar < amin or ar > amax:
                    continue
                w = stats[i, cv2.CC_STAT_WIDTH]; h = stats[i, cv2.CC_STAT_HEIGHT]
                if w >= 0.6 * Ww or h >= 0.6 * Hw:
                    continue
                comps.append((i, h)); heights.append(h)
            if comps:
                med_h = float(np.median(heights))
                num_thr = med_h * (1.35 * nsz)            # car numbers are the boldest/tallest glyphs
                for i, h in comps:
                    (numbers if h >= num_thr else sponsors)[lbl == i] = 255

        # ---------------- non-text decal ISLANDS (logos / badges) -> SPONSORS ----------------
        def _gmag(ch):
            gx = cv2.Sobel(ch, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(ch, cv2.CV_32F, 0, 1, ksize=3)
            return cv2.magnitude(gx, gy)
        grad = _gmag(lum)
        for c in range(3):
            grad = np.maximum(grad, _gmag(f[..., c]) * 0.85)
        grad = cv2.GaussianBlur(grad, (0, 0), 1.0)
        bk = max(15, (min(Hw, Ww) // 12) | 1)
        base_g = cv2.blur(grad, (bk, bk))
        gp80 = float(np.percentile(grad, 80)) + 1e-6
        REL = max(1.5, 2.2 / sens)                        # higher sensitivity -> looser standout
        standout = (grad > (base_g * REL + 0.6 * gp80)).astype(np.uint8)
        # local color deviation from a soft base (logos sit on a calmer base)
        sigma = max(6.0, 0.045 * max(Hw, Ww))
        base_col = cv2.GaussianBlur(f, (0, 0), sigma)
        dev = np.abs(f - base_col).sum(axis=2)
        dev_thr = max(0.14, float(np.percentile(dev, 95 - 8 * (sens - 1.0))))
        island = ((standout > 0) | (dev > dev_thr)).astype(np.uint8)
        island = cv2.morphologyEx(island, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        island = cv2.morphologyEx(island, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        # keep compact, isolated, contrasty islands (NOT a busy base): per-component ring test
        already = (numbers > 0) | (sponsors > 0)
        ni, ilbl, istats, _ = cv2.connectedComponentsWithStats(island, 8)
        ring_in = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        ring_out = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
        a_min = max(20.0, (1.2e-4 / sens) * N)
        a_max = 0.10 * N
        for i in range(1, ni):
            ar = istats[i, cv2.CC_STAT_AREA]
            if ar < a_min or ar > a_max:
                continue
            w = istats[i, cv2.CC_STAT_WIDTH]; h = istats[i, cv2.CC_STAT_HEIGHT]
            if w >= 0.7 * Ww or h >= 0.7 * Hw:
                continue
            if float(ar) / float(max(1, w * h)) < (0.18 / max(0.6, sens)):   # solid blob, not a sparse edge web
                continue
            comp = (ilbl == i).astype(np.uint8)
            ring = (cv2.dilate(comp, ring_out) > 0) & (cv2.dilate(comp, ring_in) == 0)
            if int(ring.sum()) < 10:
                continue
            if float(island[ring].mean()) > (0.30 + 0.12 * (sens - 1.0)):   # in a denser decal field -> busy base, skip
                continue
            cm = comp > 0
            if float(np.abs(f[cm].mean(0) - f[ring].mean(0)).sum()) < (0.17 - 0.05 * (sens - 1.0)):  # must contrast its surround
                continue
            sponsors[cm & (~already)] = 255

        # ---------------- finalize ----------------
        k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        numbers = cv2.morphologyEx(numbers, cv2.MORPH_CLOSE, k5)
        sponsors = cv2.morphologyEx(sponsors, cv2.MORPH_CLOSE, k5)
        sponsors[numbers > 0] = 0                          # numbers win overlaps
        decals = (numbers > 0) | (sponsors > 0)
        if float(decals.mean()) > float(np.clip(max_decal_frac, 0.1, 0.9)):
            return None                                    # caught too much -> almost surely a busy base
        paint = np.where(decals, np.uint8(0), np.uint8(255))

        def _up(m):
            return m if (Hw, Ww) == (H0, W0) else cv2.resize(m, (W0, H0), interpolation=cv2.INTER_NEAREST)
        return {"numbers": _up(numbers), "sponsors": _up(sponsors), "paint": _up(paint)}
    except Exception:
        return None


# ===================================================================================================
# SMART SEPARATE STUDIO (2026-06-26): GUIDED, refinable livery separation.
# A user-hint-driven re-sort + grow + refine pass on top of the auto detector. ADDITIVE — leaves
# separate_livery_layers untouched. The auto pass classifies; the guided pass lets the user correct it
# with hint scribbles (which class a region is) and include/exclude brushes (force pixels in/out of the
# active layer), all band-confined + edge-snapped so a sloppy stroke only touches the decal it traces.
# ===================================================================================================
def _gmag_rgb(f, lum):
    """Combined gradient magnitude over luminance + each RGB channel (module-level lift of the local
    `_gmag` closure in separate_livery_layers, so the guided path + edge-snap can share it). ``f`` is
    HxWx3 float 0..1, ``lum`` its luminance. Returns a blurred float32 HxW magnitude. Never raises."""
    try:
        def _g(ch):
            gx = cv2.Sobel(ch, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(ch, cv2.CV_32F, 0, 1, ksize=3)
            return cv2.magnitude(gx, gy)
        grad = _g(lum)
        for c in range(3):
            grad = np.maximum(grad, _g(f[..., c]) * 0.85)
        return cv2.GaussianBlur(grad, (0, 0), 1.0)
    except Exception:
        return np.zeros(lum.shape[:2], np.float32)


def _coerce_hint_mask(m, Hw, Ww):
    """None-safe coercion of any hint/brush input → bool HxW at (Hw, Ww). Accepts None, HxW or HxWxC
    arrays of any dtype/scale; treats >0 (after a luma collapse for color) as marked; NEAREST-resizes to
    the work grid (hints are drawn in the squashed preview space). Returns None for None / empty / blank."""
    if m is None:
        return None
    try:
        a = np.asarray(m)
        if a.size == 0:
            return None
        if a.ndim == 3:
            a = a[..., :3].astype(np.float32).mean(axis=2) if a.shape[2] >= 3 else a[..., 0].astype(np.float32)
        elif a.ndim != 2:
            return None
        a = np.nan_to_num(a.astype(np.float32), nan=0.0, posinf=255.0, neginf=0.0)
        thr = 0.5 if float(a.max()) <= 1.5 else 127.5
        b = (a > thr)
        if b.shape != (Hw, Ww):
            b = cv2.resize(b.astype(np.uint8), (Ww, Hw), interpolation=cv2.INTER_NEAREST) > 0
        if not bool(b.any()):
            return None
        return np.ascontiguousarray(b)
    except Exception:
        return None


def _band_from_hint(hint_bool, Hw, Ww, pad_frac=0.12):
    """Bbox band around a hint's marked pixels, padded ~pad_frac of the larger dim, clamped to the grid.
    Returns a bool HxW band (the crop region GrabCut / edge-snap is confined to). None on empty hint."""
    if hint_bool is None or not bool(hint_bool.any()):
        return None
    ys, xs = np.where(hint_bool)
    pad = max(6, int(round(pad_frac * max(Hw, Ww))))
    y0 = max(0, int(ys.min()) - pad); y1 = min(Hw, int(ys.max()) + 1 + pad)
    x0 = max(0, int(xs.min()) - pad); x1 = min(Ww, int(xs.max()) + 1 + pad)
    band = np.zeros((Hw, Ww), bool)
    band[y0:y1, x0:x1] = True
    return band


def _grabcut_grow_in_band(small_bgr, seed_bool, band_bool, current_active=None, iters=4):
    """Scribble-seeded GrabCut, CROPPED to the band bbox for speed (~64-256px). seed core → GC_FGD,
    band → GC_PR_BGD, current-active pixels in band → GC_PR_FGD. Returns a grown bool HxW mask (full grid)
    or None. A grown region that collapses to ≈the seed (stray scribble) is dropped by the caller."""
    try:
        if seed_bool is None or band_bool is None or not bool(seed_bool.any()) or not bool(band_bool.any()):
            return None
        Hw, Ww = band_bool.shape
        ys, xs = np.where(band_bool)
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        if (y1 - y0) < 8 or (x1 - x0) < 8:
            return None
        sub = np.ascontiguousarray(small_bgr[y0:y1, x0:x1])
        # FAST + CORRECT (2026-06-26): a near-uniform band has NO decal — and GrabCut is
        # pathologically slow on uniform colour (degenerate GMM ~50s on a blank base). Bail now.
        if float(np.asarray(sub, np.float32).reshape(-1, sub.shape[-1]).std(axis=0).mean()) < 6.0:
            return None
        gc = np.full(sub.shape[:2], cv2.GC_PR_BGD, np.uint8)
        if current_active is not None:
            ca = current_active[y0:y1, x0:x1]
            gc[ca] = cv2.GC_PR_FGD
        seed_sub = seed_bool[y0:y1, x0:x1]
        # erode the seed a touch so only the scribble CORE is hard-foreground (robust to sloppy strokes)
        seed_core = cv2.erode(seed_sub.astype(np.uint8),
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))) > 0
        if not seed_core.any():
            seed_core = seed_sub
        gc[seed_core] = cv2.GC_FGD
        if not (gc == cv2.GC_FGD).any() or not ((gc == cv2.GC_PR_BGD) | (gc == cv2.GC_BGD)).any():
            return None
        bgdm = np.zeros((1, 65), np.float64)
        fgdm = np.zeros((1, 65), np.float64)
        cv2.grabCut(sub, gc, None, bgdm, fgdm, int(max(1, min(5, iters))), cv2.GC_INIT_WITH_MASK)
        grown_sub = ((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD))
        # DECAL-PRESENCE GATE (2026-06-26 refine — fixes overgrow=1.0 on blank/uniform bases):
        # over uniform paint there is no colour edge, so GrabCut fills the WHOLE band. Keep only
        # pixels that STAND OUT from the band's paint background (colour distance OR a strong local
        # edge), and DROP the grow entirely if almost nothing stands out (= no real decal under the
        # scribble). Kills the over-fill AND snaps the grow to the actual decal (the owner's ask).
        sub_f = sub.astype(np.float32)
        bg_src = sub_f[~grown_sub] if bool((~grown_sub).any()) else sub_f.reshape(-1, 3)
        bg = np.median(bg_src.reshape(-1, 3), axis=0)
        dev = np.sqrt(((sub_f - bg.reshape(1, 1, 3)) ** 2).sum(axis=2))  # colour distance from paint
        thr = max(26.0, float(np.percentile(dev, 92)) * 0.55)
        standout = dev > thr
        try:
            _lap = np.abs(cv2.Laplacian(cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY), cv2.CV_32F))
            standout = standout | (_lap > max(14.0, float(np.percentile(_lap, 96)) * 0.6))
        except Exception:
            pass
        keep = grown_sub & standout
        keep |= (seed_core & (dev > thr * 0.55))  # honor the hard scribble core if it stands out at all
        # LOCALITY: a mark grows only the decal CONNECTED to the scribble, never the whole busy field.
        # On a busy/colourful base everything "stands out", so without this the grow fills the band.
        try:
            ncc, lbl = cv2.connectedComponents(keep.astype(np.uint8), connectivity=8)
            if ncc > 2 and bool(seed_core.any()):
                seed_lbls = [int(v) for v in np.unique(lbl[seed_core]) if v > 0]
                if seed_lbls:
                    keep = np.isin(lbl, seed_lbls)
        except Exception:
            pass
        band_area = int(band_bool[y0:y1, x0:x1].sum()) or grown_sub.size
        ks = int(keep.sum())
        if ks < max(12, int(0.004 * band_area)):
            return None  # nothing real under the scribble (uniform paint) — drop the grow
        # RUNAWAY GUARD (2026-06-26, 60-sheet review: over-grow flooded paint in 43/60). A real
        # number/decal is SMALL vs the whole car; a runaway grow over a large paint field is huge.
        # Size is the only reliable discriminator (fill-ratio conflates a tight-hinted solid decal
        # with paint), so drop only grows that exceed a generous single-decal area. Real big numbers
        # stay well under this; the whole-body floods (Next Gen Monster, car_40638) exceed it.
        if ks > 0.12 * (Hw * Ww):
            return None
        keep = cv2.morphologyEx(keep.astype(np.uint8), cv2.MORPH_CLOSE,
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))) > 0
        out = np.zeros((Hw, Ww), bool)
        out[y0:y1, x0:x1] = keep
        return out
    except Exception:
        return None


def _edge_snap_mask(mask_bool, lum, grad, band_bool):
    """Snap a (sloppy) mask to the underlying decal edges, CONFINED to the band so a stroke only adds the
    decal side. ximgproc.guidedFilter when available, else a _gmag_rgb-steered GaussianBlur+threshold that
    pulls the boundary toward high-gradient ridges. Returns a refined bool HxW mask. Never raises."""
    try:
        if mask_bool is None or not bool(mask_bool.any()):
            return mask_bool
        if band_bool is not None:
            work = mask_bool & band_bool
        else:
            work = mask_bool
        if not bool(work.any()):
            return mask_bool
        m = work.astype(np.float32)
        gf = getattr(getattr(cv2, "ximgproc", None), "guidedFilter", None)
        if gf is not None:
            try:
                guide = np.clip(lum * 255.0, 0, 255).astype(np.uint8)
                sm = gf(guide, (m * 255.0).astype(np.uint8), radius=4, eps=64) / 255.0
                refined = sm > 0.5
            except Exception:
                refined = None
        else:
            refined = None
        if refined is None:
            # edge-steered: blur the mask, then bias the threshold UP where the gradient is strong so the
            # boundary lands on the high-contrast decal ridge rather than mid-paint.
            sm = cv2.GaussianBlur(m, (0, 0), 1.5)
            g = grad
            gmax = float(g.max()) + 1e-6
            edge = np.clip(g / gmax, 0.0, 1.0)
            thr = 0.45 + 0.10 * edge
            refined = sm > thr
        if band_bool is not None:
            # outside the band, keep the original mask exactly — the brush only acts in its band
            out = mask_bool.copy()
            out[band_bool] = refined[band_bool]
            return out
        return refined
    except Exception:
        return mask_bool


def _reclassify_components_by_hint(numbers, sponsors, number_hint, sponsor_hint):
    """RE-SORT: for each connected component of (numbers|sponsors), vote by hint overlap —
    number_hint→NUMBERS, sponsor_hint→SPONSORS, both→greater overlap (tie→NUMBERS), neither→keep auto
    class. Mutates and returns (numbers, sponsors) uint8 (255=member). Components flow to the voted class."""
    try:
        nh = number_hint if number_hint is not None else np.zeros(numbers.shape, bool)
        sh = sponsor_hint if sponsor_hint is not None else np.zeros(numbers.shape, bool)
        if not (nh.any() or sh.any()):
            return numbers, sponsors
        any_decal = ((numbers > 0) | (sponsors > 0)).astype(np.uint8)
        n, lbl, _stats, _ = cv2.connectedComponentsWithStats(any_decal, 8)
        out_n = numbers.copy(); out_s = sponsors.copy()
        for i in range(1, n):
            comp = (lbl == i)
            no = int((comp & nh).sum())
            so = int((comp & sh).sum())
            if no == 0 and so == 0:
                continue                                   # no hint → keep auto class as-is
            if no > 0 and so > 0:
                to_numbers = (no >= so)                     # both → greater overlap, tie → NUMBERS
            else:
                to_numbers = (no > 0)
            if to_numbers:
                out_n[comp] = 255; out_s[comp] = 0
            else:
                out_s[comp] = 255; out_n[comp] = 0
        return out_n, out_s
    except Exception:
        return numbers, sponsors


def separate_livery_layers_guided(tex, *, number_hint=None, sponsor_hint=None,
        include_mask=None, exclude_mask=None, active_layer=None, base_masks=None,
        sensitivity=1.0, number_size=1.0, max_decal_frac=0.6):
    """GUIDED SEPARATE (2026-06-26, Smart Separate Studio): a refinable re-sort + grow + refine pass on
    top of ``separate_livery_layers``. Splits a FLAT livery into NUMBERS / SPONSORS / PAINT, corrected by
    user hint scribbles (which class a region is) + include/exclude brushes (force pixels in/out of the
    active layer). Flow = re-sort the auto result, grow under un-detected hints, refine the active layer
    with band-confined edge-snapped brushes — NOT a from-scratch detection.

    Args (all hint/brush masks are None-safe, any size/dtype, drawn in the squashed preview space):
      number_hint / sponsor_hint — scribbles marking number / sponsor regions.
      include_mask / exclude_mask — force pixels INTO / OUT OF the active_layer.
      active_layer — "numbers" | "sponsors" | "paint" | None (which layer the brushes act on).
      base_masks — optional {"numbers","sponsors","paint"} uint8 echo of the last result (skip re-detect).
      sensitivity / number_size / max_decal_frac — passed to the auto pass.

    Returns {"numbers","sponsors","paint"} of FULL-RES HxW uint8 masks (255 = member). Never raises."""
    try:
        rgb_full = _normalize_rgb_u8(tex)
        if rgb_full is None:
            # last-ditch: an all-paint result at a tiny default so callers always get a dict
            z = np.zeros((16, 16), np.uint8)
            return {"numbers": z.copy(), "sponsors": z.copy(),
                    "paint": np.full((16, 16), 255, np.uint8)}
        H0, W0 = rgb_full.shape[:2]
        sens = float(np.clip(sensitivity, 0.3, 2.0))
        nsz = float(np.clip(number_size, 0.4, 2.5))

        WORK = 768
        s = min(1.0, WORK / float(max(H0, W0)))
        if s < 1.0:
            Ww = max(16, int(round(W0 * s))); Hw = max(16, int(round(H0 * s)))
            small = cv2.resize(rgb_full, (Ww, Hw), interpolation=cv2.INTER_AREA)
        else:
            small = rgb_full; Hw, Ww = H0, W0
        f = small.astype(np.float32) / 255.0
        lum = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
        small_bgr = cv2.cvtColor(small, cv2.COLOR_RGB2BGR)
        grad = _gmag_rgb(f, lum)

        # coerce every hint/brush to the work grid
        nh = _coerce_hint_mask(number_hint, Hw, Ww)
        sh = _coerce_hint_mask(sponsor_hint, Hw, Ww)
        inc = _coerce_hint_mask(include_mask, Hw, Ww)
        exc = _coerce_hint_mask(exclude_mask, Hw, Ww)
        any_hint = any(x is not None for x in (nh, sh, inc, exc))
        al = str(active_layer).strip().lower() if active_layer else None
        if al not in ("numbers", "sponsors", "paint"):
            al = None

        # ----- 1. AUTO pass (or echoed base_masks) -----
        def _to_work(m):
            mm = np.asarray(m)
            if mm.ndim == 3:
                mm = mm[..., 0]
            mm = (mm > 0).astype(np.uint8) * 255
            if mm.shape != (Hw, Ww):
                mm = cv2.resize(mm, (Ww, Hw), interpolation=cv2.INTER_NEAREST)
            return mm
        numbers = np.zeros((Hw, Ww), np.uint8)
        sponsors = np.zeros((Hw, Ww), np.uint8)
        if isinstance(base_masks, dict) and (base_masks.get("numbers") is not None
                                             or base_masks.get("sponsors") is not None):
            try:
                if base_masks.get("numbers") is not None:
                    numbers = _to_work(base_masks["numbers"])
                if base_masks.get("sponsors") is not None:
                    sponsors = _to_work(base_masks["sponsors"])
            except Exception:
                numbers = np.zeros((Hw, Ww), np.uint8); sponsors = np.zeros((Hw, Ww), np.uint8)
        else:
            auto = separate_livery_layers(tex, sensitivity=sens, number_size=nsz,
                                          max_decal_frac=max_decal_frac)
            if auto is not None:
                numbers = _to_work(auto["numbers"]); sponsors = _to_work(auto["sponsors"])
            # auto None + hints present → start from empty (handled by the zeros above)

        # ----- 2. RE-SORT by hint overlap -----
        numbers, sponsors = _reclassify_components_by_hint(numbers, sponsors, nh, sh)

        # ----- 3. GROW under hinted regions with no detected component beneath them -----
        MAX_GROWN = 12
        for hint_bool, target_is_numbers in ((nh, True), (sh, False)):
            if hint_bool is None:
                continue
            # split the hint into connected scribble regions; grow each that has no decal under it
            nlbl, lbl_h, stat_h, _ = cv2.connectedComponentsWithStats(hint_bool.astype(np.uint8), 8)
            order = sorted(range(1, nlbl), key=lambda i: -int(stat_h[i, cv2.CC_STAT_AREA]))
            grown_count = 0
            for i in order:
                if grown_count >= MAX_GROWN:
                    break
                region = (lbl_h == i)
                if not region.any():
                    continue
                existing = ((numbers > 0) | (sponsors > 0))
                # already covered enough by a detected component → re-sort handled it, skip grow
                if float((region & existing).sum()) >= 0.55 * float(region.sum()):
                    continue
                band = _band_from_hint(region, Hw, Ww)
                current_active = (numbers > 0) if target_is_numbers else (sponsors > 0)
                grown = _grabcut_grow_in_band(small_bgr, region, band,
                                              current_active=current_active, iters=4)
                if grown is None or not grown.any():
                    continue
                # drop if it collapsed to ≈the seed (stray scribble = no-op): require meaningful growth
                if int(grown.sum()) <= int(region.sum()) * 1.15 + 4:
                    continue
                grown = grown & band
                if target_is_numbers:
                    numbers[grown] = 255; sponsors[grown] = 0
                else:
                    sponsors[grown] = 255; numbers[grown] = 0
                grown_count += 1

        # ----- 4. REFINE brushes (act on the active layer only, band-confined + edge-snapped) -----
        if al is not None and (inc is not None or exc is not None):
            band = None
            for brush in (inc, exc):
                if brush is not None:
                    b = _band_from_hint(brush, Hw, Ww, pad_frac=0.06)
                    band = b if band is None else (band | b)
            if al == "numbers":
                active = (numbers > 0)
            elif al == "sponsors":
                active = (sponsors > 0)
            else:
                active = (numbers == 0) & (sponsors == 0)   # paint
            if inc is not None:
                # snap the include stroke to the decal it traces, confined to its band
                add = _edge_snap_mask(inc, lum, grad, band)
                add = add & (band if band is not None else add)
                if al == "paint":
                    # include into PAINT = remove those pixels from numbers/sponsors
                    numbers[add] = 0; sponsors[add] = 0
                elif al == "numbers":
                    numbers[add] = 255; sponsors[add] = 0
                else:
                    sponsors[add] = 255; numbers[add] = 0
            if exc is not None:
                rem = exc & (band if band is not None else exc)
                if al == "numbers":
                    numbers[rem] = 0
                elif al == "sponsors":
                    sponsors[rem] = 0
                else:
                    # exclude from PAINT = nothing to remove from a derived layer; no-op (paint is ~decals)
                    pass

        # ----- 5. FINALIZE exactly like separate_livery_layers -----
        k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        numbers = cv2.morphologyEx(numbers, cv2.MORPH_CLOSE, k5)
        sponsors = cv2.morphologyEx(sponsors, cv2.MORPH_CLOSE, k5)
        sponsors[numbers > 0] = 0                            # numbers win overlaps
        decals = (numbers > 0) | (sponsors > 0)
        # only bail on over-capture when there are NO hints (a hint = explicit user intent, trust it)
        if not any_hint and float(decals.mean()) > float(np.clip(max_decal_frac, 0.1, 0.9)):
            numbers = np.zeros((Hw, Ww), np.uint8)
            sponsors = np.zeros((Hw, Ww), np.uint8)
            decals = np.zeros((Hw, Ww), bool)
        paint = np.where(decals, np.uint8(0), np.uint8(255))

        def _up(m):
            return m if (Hw, Ww) == (H0, W0) else cv2.resize(m, (W0, H0), interpolation=cv2.INTER_NEAREST)
        return {"numbers": _up(numbers), "sponsors": _up(sponsors), "paint": _up(paint)}
    except Exception:
        # NEVER raise: best-effort all-paint at the input size
        try:
            rgb_full = _normalize_rgb_u8(tex)
            H0, W0 = (rgb_full.shape[:2] if rgb_full is not None else (16, 16))
        except Exception:
            H0, W0 = (16, 16)
        z = np.zeros((H0, W0), np.uint8)
        return {"numbers": z.copy(), "sponsors": z.copy(), "paint": np.full((H0, W0), 255, np.uint8)}


def _build_protect_mask_from_psd(psd, want_names, want_keys):
    """Rasterize selected PSD leaf identities into the inverse sculpt mask."""
    W, H = int(psd.width), int(psd.height)
    if W <= 0 or H <= 0:
        return None
    protect = np.zeros((H, W), dtype=np.float32)
    stack = [(layer, (index,)) for index, layer in enumerate(psd)]
    matched = 0
    while stack:
        layer, index_path = stack.pop()
        if getattr(layer, 'kind', None) == 'group':
            try:
                stack.extend(
                    (child, index_path + (child_index,))
                    for child_index, child in enumerate(layer)
                )
            except Exception:
                pass
            continue
        try:
            layer_key = '.'.join(str(part) for part in index_path)
            name_match = str(getattr(layer, 'name', '')).strip().lower() in want_names
            if not name_match and layer_key not in want_keys:
                continue
            img = layer.composite()
            if img is None:
                continue
            if img.mode not in ('RGBA', 'LA'):
                img = img.convert('RGBA')
            alpha = np.asarray(img.split()[-1], dtype=np.float32) / 255.0
            left, top, right, bottom = (int(part) for part in layer.bbox)
            left0, top0 = max(0, left), max(0, top)
            right0, bottom0 = min(W, right), min(H, bottom)
            if right0 <= left0 or bottom0 <= top0:
                continue
            alpha_inside = alpha[(top0 - top):(bottom0 - top), (left0 - left):(right0 - left)]
            if alpha_inside.shape != (bottom0 - top0, right0 - left0):
                alpha_inside = alpha_inside[:bottom0 - top0, :right0 - left0]
            region = protect[top0:bottom0, left0:right0]
            protect[top0:bottom0, left0:right0] = np.maximum(
                region, alpha_inside[:region.shape[0], :region.shape[1]]
            )
            matched += 1
        except Exception:
            continue
    if matched == 0 or float(protect.max()) <= 0.0:
        return None
    return ((1.0 - np.clip(protect, 0.0, 1.0)) * 255.0).astype(np.uint8)


def build_protect_mask(psd_path, protect_names=None, protect_keys=None):
    """Build a SCULPT mask from PSD layer names and/or positional keys.

    Returns a uint8 HxW mask that is 255 (sculpt) everywhere EXCEPT where any layer whose
    name is in ``protect_names`` or key is in ``protect_keys`` is opaque — those pixels become 0 so ``apply_sculpt_mask``
    keeps them flat/neutral. This is the real engine fix for "it sculpts the whole car incl.
    sponsors/logos": pass the protected (e.g. sponsor/logo/number/decal) layer names and their
    actual painted shape is shielded, not a bounding box.

    Robust by design — returns ``None`` (callers no-op) when psd-tools is missing, the PSD is
    unreadable, both identity lists are empty, or nothing matched. Handles negative layer offsets and
    composites that extend past the canvas (common in iRacing template PSDs)."""
    try:
        # Owner Easy Mode 2026-07-18: display names are not PSD identities. The
        # guided path supplies collision-free positional keys; names remain a
        # backwards-compatible fallback for existing Spec Lab recipes. This is
        # mask plumbing only, so catalog finish output and M7 scores are unchanged.
        want = set(str(n).strip().lower() for n in (protect_names or []) if str(n).strip())
        want_keys = set(str(k).strip() for k in (protect_keys or []) if str(k).strip())
        if not want and not want_keys:
            return None
        import os as _os
        try:
            _mt = round(_os.path.getmtime(psd_path), 1)
        except Exception:
            _mt = 0.0
        _key = (str(psd_path), _mt, tuple(sorted(want)), tuple(sorted(want_keys)))
        _cached = _PROTECT_MASK_CACHE.get(_key)
        if _cached is not None:
            return _cached
        from psd_tools import PSDImage
        psd = PSDImage.open(psd_path)
        out = _build_protect_mask_from_psd(psd, want, want_keys)
        if out is None:
            return None
        if len(_PROTECT_MASK_CACHE) > 16:
            _PROTECT_MASK_CACHE.clear()
        _PROTECT_MASK_CACHE[_key] = out
        return out
    except Exception:
        return None


# Material behaviors as (Metallic, Roughness, Clearcoat) — all iron-safe by construction
# (Cc>=16, R>=15, M<240 so never a "chrome plate"). Spec is colorless; the paint carries the hue.
HUE_MATERIALS = {
    'keep':   None,
    # ---- mirror / chrome family ----
    'chrome':        (238, 30, 232),
    'liquid_chrome': (252, 22, 248),
    'dark_chrome':   (205, 48, 222),
    'chrome_satin':  (210, 82, 184),
    'black_chrome':  (190, 64, 150),
    # ---- metal family ----
    'brushed_metal': (180, 120, 150),
    'gunmetal':      (150, 92, 122),
    'titanium':      (172, 96, 162),
    'steel':         (160, 110, 130),
    'satin_metal':   (162, 104, 160),
    # ---- warm metals ----
    'gold':          (202, 70, 212),
    'rose_gold':     (190, 86, 206),
    'copper':        (192, 82, 200),
    'bronze':        (170, 100, 178),
    # ---- pearl / candy / optical ----
    'pearl':         (92, 130, 200),
    'deep_pearl':    (72, 150, 222),
    'candy':         (116, 40, 250),
    'wet':           (110, 35, 248),
    'wet_candy':     (120, 28, 252),
    'holographic':   (162, 58, 230),
    'anodized':      (176, 70, 220),
    'iridescent':    (150, 66, 226),
    # ---- gloss ladder ----
    'gloss':         (135, 45, 240),
    'semi_gloss':    (116, 96, 190),
    'satin':         (105, 110, 140),
    # ---- matte / technical ----
    'carbon':        (70, 150, 55),
    'forged_carbon': (92, 140, 82),
    'ceramic':       (52, 176, 62),
    'matte':         (40, 205, 18),
    'flat':          (20, 230, 16),
    'velvet':        (34, 216, 28),
    'rubber':        (24, 222, 20),
}
# Color families -> behavior. Saturated pixels match by hue band; dark/light match by value.
_HUE_BANDS = {
    'red': (345, 15), 'orange': (15, 45), 'yellow': (45, 75), 'green': (75, 165),
    'cyan': (165, 195), 'blue': (195, 255), 'purple': (255, 290), 'pink': (290, 345),
}


def hue_material_spec(tex, rules, base='satin', feather=2.0):
    """COLOR -> MATERIAL (Spec Sculpt #7): paint hue/tone families each get a chosen material behavior.
    `rules` = [{'key': 'red'|'orange'|...|'dark'|'light', 'material': 'chrome'|'matte'|'wet'|...}].
    Returns HxWx3 uint8 spec; unruled pixels keep the `base` behavior. Iron-safe by construction."""
    rgb = np.clip(np.asarray(tex) * 255.0, 0, 255).astype(np.uint8)
    if rgb.ndim == 2:
        rgb = np.stack([rgb] * 3, axis=-1)
    rgb = rgb[:, :, :3]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    H = hsv[:, :, 0] * 2.0          # cv2 hue is 0..179 -> 0..360
    S = hsv[:, :, 1] / 255.0
    V = hsv[:, :, 2] / 255.0
    h, w = H.shape

    bm = HUE_MATERIALS.get(base) or HUE_MATERIALS['satin']
    spec = np.empty((h, w, 3), np.float32)
    spec[:, :, 0] = bm[0]; spec[:, :, 1] = bm[1]; spec[:, :, 2] = bm[2]

    def _fam(key):
        if key == 'dark':
            return V < 0.28
        if key == 'light':
            return (V > 0.80) & (S < 0.22)
        band = _HUE_BANDS.get(key)
        if not band:
            return np.zeros((h, w), bool)
        lo, hi = band
        hm = ((H >= lo) | (H < hi)) if lo > hi else ((H >= lo) & (H < hi))
        return hm & (S > 0.18) & (V > 0.12)

    for r in (rules or []):
        try:
            rd = r or {}
            mat = HUE_MATERIALS.get(rd.get('material'))
            if not mat:
                continue
            col = rd.get('color')
            if col and len(col) >= 3:
                # COLOR-TARGET rule (#40 eyedropper): pixels within tol° of the SAMPLED hue → material.
                arr = np.array([[[float(col[0]), float(col[1]), float(col[2])]]], np.float32)
                if float(arr.max()) <= 1.0:
                    arr = arr * 255.0
                chsv = cv2.cvtColor(np.clip(arr, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV)[0, 0]
                target_h = float(chsv[0]) * 2.0
                target_s = float(chsv[1]) / 255.0
                try:
                    tol = max(4.0, min(90.0, float(rd.get('tol', 28.0))))
                except Exception:
                    tol = 28.0
                if target_s < 0.12:
                    # near-greyscale sample → match by low saturation (hue is meaningless)
                    m = S < 0.18
                else:
                    dh = np.abs(((H - target_h + 180.0) % 360.0) - 180.0)  # circular hue distance
                    m = (dh <= tol) & (S > 0.15)
                if m.any():
                    spec[m] = mat
                continue
            m = _fam(rd.get('key'))
            if m.any():
                spec[m] = mat
        except Exception:
            continue

    if feather and feather > 0:
        k = max(1, int(feather)) * 2 + 1
        spec = cv2.GaussianBlur(spec, (k, k), float(feather))
    return np.clip(spec, 0, 255).astype(np.uint8)


def tone_material_spec(tex, bands, base='satin', feather=2.0):
    """LUMINANCE -> MATERIAL (Spec Sculpt #9): map tonal ranges (shadows..highlights) to material
    behaviors — "shadows -> deep wet candy, highlights -> satin". ``bands`` = [{'lo':0..1,'hi':0..1,
    'material':...}]. Unbanded pixels keep ``base``. Iron-safe by construction (same HUE_MATERIALS)."""
    rgb = np.clip(np.asarray(tex) * 255.0, 0, 255).astype(np.uint8)
    if rgb.ndim == 2:
        rgb = np.stack([rgb] * 3, axis=-1)
    rgb = rgb[:, :, :3].astype(np.float32)
    L = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]) / 255.0  # 0..1 luminance
    h, w = L.shape
    bm = HUE_MATERIALS.get(base) or HUE_MATERIALS['satin']
    spec = np.empty((h, w, 3), np.float32)
    spec[:, :, 0] = bm[0]; spec[:, :, 1] = bm[1]; spec[:, :, 2] = bm[2]
    for bd in (bands or []):
        try:
            mat = HUE_MATERIALS.get((bd or {}).get('material'))
            if not mat:
                continue
            lo = float((bd or {}).get('lo', 0.0))
            hi = float((bd or {}).get('hi', 1.0))
            m = (L >= lo) if hi >= 1.0 else ((L >= lo) & (L < hi))
            if m.any():
                spec[m] = mat
        except Exception:
            continue
    if feather and feather > 0:
        k = max(1, int(feather)) * 2 + 1
        spec = cv2.GaussianBlur(spec, (k, k), float(feather))
    return np.clip(spec, 0, 255).astype(np.uint8)


def layer_material_spec(psd_path, assignments, base='satin', feather=2.0, max_size=2048):
    """PER-PSD-LAYER MATERIAL (Spec Sculpt #10): assign a material behavior to each NAMED PSD layer
    ("Body -> satin, Chrome trim -> chrome, Sponsors -> matte"). ``assignments`` = {layer_name: material}.
    Layers are stamped in document order so upper layers win their pixels; unassigned pixels keep ``base``.
    Returns HxWx3 uint8 (iron-safe via HUE_MATERIALS) or None if the PSD is unreadable / nothing assigned."""
    try:
        want = {str(k).strip().lower(): v for k, v in (assignments or {}).items()
                if v and HUE_MATERIALS.get(v)}
        if not want:
            return None
        from psd_tools import PSDImage
        psd = PSDImage.open(psd_path)
        W0, H0 = int(psd.width), int(psd.height)
        if W0 <= 0 or H0 <= 0:
            return None
        s = min(1.0, float(max_size) / max(W0, H0)) if max_size else 1.0  # build at <=max_size for speed
        W = max(1, int(round(W0 * s)))
        H = max(1, int(round(H0 * s)))
        bm = HUE_MATERIALS.get(base) or HUE_MATERIALS['satin']
        spec = np.empty((H, W, 3), np.float32)
        spec[:, :, 0] = bm[0]; spec[:, :, 1] = bm[1]; spec[:, :, 2] = bm[2]

        leaves = []

        def _walk(node):
            for L in node:
                if getattr(L, 'kind', None) == 'group':
                    try:
                        _walk(L)
                    except Exception:
                        pass
                else:
                    leaves.append(L)
        _walk(psd)

        matched = 0
        for L in leaves:                      # document order -> later (upper) layers overwrite
            nm = str(getattr(L, 'name', '')).strip().lower()
            matv = HUE_MATERIALS.get(want.get(nm))
            if not matv:
                continue
            try:
                arr = L.numpy()              # raw layer pixels — far faster than composite()
                if arr is None:
                    continue
                arr = np.asarray(arr, dtype=np.float32)
                if arr.ndim == 2:
                    a = np.ones(arr.shape[:2], np.float32)
                elif arr.shape[2] >= 4:
                    a = arr[:, :, 3]
                else:
                    a = np.ones(arr.shape[:2], np.float32)
                if a.size and a.max() > 1.5:
                    a = a / 255.0
                bb = L.bbox
                l = int(round(bb[0] * s)); t = int(round(bb[1] * s))
                r = int(round(bb[2] * s)); b = int(round(bb[3] * s))
                aw, ah = max(1, r - l), max(1, b - t)
                a = cv2.resize(a, (aw, ah), interpolation=cv2.INTER_AREA)
                l0, t0, r0, b0 = max(0, l), max(0, t), min(W, r), min(H, b)
                if r0 <= l0 or b0 <= t0:
                    continue
                ai = a[(t0 - t):(b0 - t), (l0 - l):(r0 - l)]
                m = ai[:b0 - t0, :r0 - l0] > 0.5
                region = spec[t0:b0, l0:r0]
                region[m] = matv
                spec[t0:b0, l0:r0] = region
                matched += 1
            except Exception:
                continue
        if matched == 0:
            return None
        if feather and feather > 0:
            k = max(1, int(feather)) * 2 + 1
            spec = cv2.GaussianBlur(spec, (k, k), float(feather))
        return np.clip(spec, 0, 255).astype(np.uint8)
    except Exception:
        return None


def iron_validate(spec):
    """Check a spec (HxWx3 uint8 = Metallic, Roughness, Clearcoat) against the iRacing iron rules.
    Returns {"valid": bool, "issues": [{rule, frac, msg}]}."""
    s = np.asarray(spec)
    M = s[:, :, 0].astype(np.int16)
    R = s[:, :, 1].astype(np.int16)
    Cc = s[:, :, 2].astype(np.int16)
    issues = []
    cc_band = float(((Cc >= 1) & (Cc < 16)).mean())
    if cc_band > 0.001:
        issues.append({"rule": "clearcoat_band", "frac": round(cc_band, 4),
                       "msg": "clearcoat in the illegal 1-15 whitewash band"})
    low_r = float(((R < 15) & (M < 240)).mean())
    if low_r > 0.001:
        issues.append({"rule": "low_roughness", "frac": round(low_r, 4),
                       "msg": "roughness below 15 on non-mirror pixels"})
    plate = float((M >= 240).mean())
    if plate > 0.55:
        issues.append({"rule": "chrome_plate", "frac": round(plate, 4),
                       "msg": "mirror-chrome over 55% of the car"})
    return {"valid": len(issues) == 0, "issues": issues}


def iron_fix(spec):
    """Correct any iron-rule violations in a spec (HxWx3 uint8). Only violating pixels change —
    an already-legal spec passes through unchanged. Returns HxWx3 uint8."""
    s = np.asarray(spec).astype(np.int16).copy()
    M = s[:, :, 0]
    R = s[:, :, 1]
    Cc = s[:, :, 2]
    if float((M >= 240).mean()) > 0.55:            # giant mirror plate -> demote to non-mirror
        M[M >= 240] = 239
    sel = (R < 15) & (M < 240)                     # roughness floor on non-mirror pixels
    R[sel] = 15
    band = (Cc >= 1) & (Cc < 16)                   # no clearcoat whitewash band: snap to 0 or 16
    Cc[band] = np.where(Cc[band] < 8, 0, 16)
    return np.clip(s, 0, 255).astype(np.uint8)


def brush_material_spec(strokes, base='satin', out_size=1024, feather=2.0):
    """REGION BRUSH (Spec Sculpt #13): stamp hand-painted material masks onto a spec. ``strokes`` =
    [{'material': name, 'mask': HxW grayscale array}] (later strokes win their pixels). Unpainted
    pixels keep ``base``. Returns out_size x out_size uint8, iron-safe via HUE_MATERIALS."""
    S = int(out_size)
    bm = HUE_MATERIALS.get(base) or HUE_MATERIALS['satin']
    spec = np.empty((S, S, 3), np.float32)
    spec[:, :, 0] = bm[0]; spec[:, :, 1] = bm[1]; spec[:, :, 2] = bm[2]
    for st in (strokes or []):
        try:
            matv = HUE_MATERIALS.get((st or {}).get('material'))
            if not matv:
                continue
            m = (st or {}).get('mask')
            if m is None:
                continue
            m = np.asarray(m, dtype=np.float32)
            if m.ndim == 3:
                m = m[:, :, -1] if m.shape[2] in (2, 4) else m[:, :, 0]
            if m.size and m.max() > 1.5:
                m = m / 255.0
            if m.shape[:2] != (S, S):
                m = cv2.resize(m, (S, S), interpolation=cv2.INTER_LINEAR)
            spec[m > 0.4] = matv
        except Exception:
            continue
    if feather and feather > 0:
        k = max(1, int(feather)) * 2 + 1
        spec = cv2.GaussianBlur(spec, (k, k), float(feather))
    return np.clip(spec, 0, 255).astype(np.uint8)


def _weather_noise(H, W, rng, scale):
    """Smooth low-frequency noise (blobs) upscaled from a small grid — fast."""
    h2 = max(2, int(H / max(1.0, scale)))
    w2 = max(2, int(W / max(1.0, scale)))
    n = rng.random((h2, w2)).astype(np.float32)
    return cv2.resize(n, (W, H), interpolation=cv2.INTER_CUBIC)


def weather_spec(spec, kind='swirls', amount=0.5, seed=7):
    """MATERIAL WEATHERING / DETAIL (Spec Sculpt #13j): overlay hand-finished / aged micro-texture onto a
    spec by modulating Roughness (and Clearcoat) — never the overall material. kind = swirls | scratches |
    brushed | grime | orangepeel. amount 0..1. Returns HxWx3 uint8 (caller should iron_fix)."""
    s = np.asarray(spec).astype(np.float32).copy()
    H, W = s.shape[:2]
    amt = max(0.0, min(1.0, float(amount)))
    if amt <= 0:
        return np.clip(s, 0, 255).astype(np.uint8)
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    R = s[:, :, 1]
    Cc = s[:, :, 2]
    k = str(kind or '').lower()
    if k == 'scratches':
        det = np.zeros((H, W), np.float32)
        for _ in range(int(120 + 700 * amt)):
            x0, y0 = int(rng.integers(0, W)), int(rng.integers(0, H))
            ang = float(rng.random()) * np.pi
            L = int(rng.integers(max(4, int(W * 0.05)), max(8, int(W * 0.4))))
            cv2.line(det, (x0, y0), (int(x0 + np.cos(ang) * L), int(y0 + np.sin(ang) * L)), float(rng.uniform(0.4, 1.0)), 1)
        det = cv2.GaussianBlur(det, (0, 0), 0.6)
        R += det * (70.0 * amt)
    elif k == 'swirls':
        det = np.zeros((H, W), np.float32)
        r = max(3, int(W * 0.012))
        for _ in range(int(200 + 1400 * amt)):
            cx, cy = int(rng.integers(0, W)), int(rng.integers(0, H))
            a0 = int(rng.integers(0, 360))
            cv2.ellipse(det, (cx, cy), (r, r), 0, a0, a0 + int(rng.integers(120, 300)), float(rng.uniform(0.3, 0.8)), 1)
        det = cv2.GaussianBlur(det, (0, 0), 0.5)
        R += det * (45.0 * amt)
    elif k == 'brushed':
        n = _weather_noise(H, W, rng, 2.0)
        kk = max(5, int(W * 0.04))
        ker = np.full((1, kk), 1.0 / kk, np.float32)
        n = cv2.filter2D(n, -1, ker)
        R += (n - float(n.mean())) * (120.0 * amt)
    elif k == 'grime':
        g = np.clip((_weather_noise(H, W, rng, 18.0) - 0.45) * 3.0, 0.0, 1.0)
        R += g * (95.0 * amt)
        Cc -= g * (120.0 * amt)
    elif k == 'orangepeel':
        Cc += (_weather_noise(H, W, rng, 7.0) - 0.5) * (45.0 * amt)
    elif k == 'hairline':
        # very fine, dense, near-parallel hairline scratches (machined/satin polish lines)
        det = np.zeros((H, W), np.float32)
        base_ang = float(rng.random()) * np.pi
        for _ in range(int(300 + 1800 * amt)):
            x0, y0 = int(rng.integers(0, W)), int(rng.integers(0, H))
            ang = base_ang + float(rng.uniform(-0.18, 0.18))
            L = int(rng.integers(max(6, int(W * 0.04)), max(10, int(W * 0.18))))
            cv2.line(det, (x0, y0), (int(x0 + np.cos(ang) * L), int(y0 + np.sin(ang) * L)), float(rng.uniform(0.25, 0.7)), 1)
        det = cv2.GaussianBlur(det, (0, 0), 0.4)
        R += det * (50.0 * amt)
    elif k == 'waterspots':
        # dried water-spot rings: thin raised-roughness rings with a calmer centre (Cc dips on the ring)
        det = np.zeros((H, W), np.float32)
        for _ in range(int(40 + 260 * amt)):
            cx, cy = int(rng.integers(0, W)), int(rng.integers(0, H))
            rad = int(rng.integers(max(3, int(W * 0.006)), max(6, int(W * 0.035))))
            cv2.circle(det, (cx, cy), rad, float(rng.uniform(0.4, 0.9)), 1)
        det = cv2.GaussianBlur(det, (0, 0), 0.6)
        R += det * (60.0 * amt)
        Cc -= det * (50.0 * amt)
    elif k == 'hammered':
        # dimpled hammered-metal: medium-frequency rounded bumps in roughness + a little clearcoat play
        bump = _weather_noise(H, W, rng, max(6.0, W * 0.012))
        bump = (bump - float(bump.mean()))
        R += bump * (85.0 * amt)
        Cc += bump * (28.0 * amt)
    elif k == 'sandblast':
        # fine uniform matte grit (even micro-roughness lift, no direction) — bead-blasted satin
        grit = _weather_noise(H, W, rng, 1.2)
        R += (grit - float(grit.mean())) * (38.0 * amt) + (55.0 * amt)
        Cc -= (38.0 * amt)
    s[:, :, 1] = R
    s[:, :, 2] = Cc
    return np.clip(s, 0, 255).astype(np.uint8)


def gradient_material_spec(mat_a, mat_b, direction='horizontal', out_size=1024):
    """MATERIAL GRADIENT (Spec Sculpt #13l): fade finish A into finish B across the car. direction =
    horizontal | vertical | diagonal | radial. Returns out_size square uint8 (iron-safe — every
    HUE_MATERIALS clearcoat is >=18, roughness >=30, metallic <=238, so the lerp never breaks a rule)."""
    S = int(out_size)
    A = np.asarray(HUE_MATERIALS.get(mat_a) or HUE_MATERIALS['chrome'], np.float32)
    B = np.asarray(HUE_MATERIALS.get(mat_b) or HUE_MATERIALS['matte'], np.float32)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    d = str(direction or 'horizontal').lower()
    if d == 'vertical':
        t = yy / max(1, S - 1)
    elif d == 'diagonal':
        t = (xx + yy) / max(1, 2 * (S - 1))
    elif d == 'radial':
        c = (S - 1) / 2.0
        t = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
        t = t / max(1e-6, float(t.max()))
    else:
        t = xx / max(1, S - 1)
    t = t[:, :, None]
    spec = A[None, None, :] * (1.0 - t) + B[None, None, :] * t
    return iron_fix(np.clip(spec, 0, 255).astype(np.uint8))


def _decorrelate_roughness(spec_u8, tex01, seed):
    """SPEC-SCULPT roughness enrichment (2026-06-25, QA over real liveries).

    The paint-derived scratch builds Roughness as Metallic's terms with negated signs, so corr(M,R)
    sat at -0.90..-0.98 on 33/52 real cars — the composite read as binary red-XOR-green blocks with no
    brushed-metal mid-tones or intra-region micro-structure. This gives Roughness its OWN geometry from an
    INDEPENDENT paint cue (local high-frequency detail energy + a fine brushed micro-grain gated to that
    detail), then ADAPTIVELY solves for the amplitude that lands |corr(M,R)| at the band centre (~0.785,
    inside the <0.85 decorrelation doctrine). Metallic is UNTOUCHED (overall read preserved), mirror/gloss
    is spared, iron-safe inline. No-op when the spec is already decorrelated (e.g. authored catalog blends).
    A/B-picked over satin-grain/rotated-luma/hybrid (8/8 files in-band, tightest spread, ~160ms @1024)."""
    spec = np.asarray(spec_u8)
    if spec.ndim != 3 or spec.shape[2] < 3:
        return spec_u8
    try:
        H, W = spec.shape[:2]
        out = spec.astype(np.float32).copy()
        M = out[:, :, 0]; R = out[:, :, 1]; Cc = out[:, :, 2]
        tex = np.asarray(tex01, dtype=np.float32)
        if tex.ndim == 2:
            tex = np.stack([tex] * 3, axis=-1)
        tex = tex[:, :, :3]
        if tex.size and float(tex.max()) > 1.5:
            tex = tex / 255.0
        if tex.shape[:2] != (H, W):
            tex = cv2.resize(tex, (W, H), interpolation=cv2.INTER_AREA)
        lum = (0.299 * tex[:, :, 0] + 0.587 * tex[:, :, 1] + 0.114 * tex[:, :, 2]).astype(np.float32)

        # CUE A: local high-frequency detail energy (independent of M's chrome/edge/streak drivers).
        rad = max(1.0, 0.0016 * max(H, W))
        mean = cv2.GaussianBlur(lum, (0, 0), rad)
        sq = cv2.GaussianBlur(lum * lum, (0, 0), rad)
        detail = np.sqrt(np.maximum(sq - mean * mean, 0.0))
        d_lo = float(np.percentile(detail, 35)); d_hi = float(np.percentile(detail, 97)) + 1e-6
        detail_n = np.clip((detail - d_lo) / (d_hi - d_lo), 0.0, 1.0).astype(np.float32)

        # CUE B: fine brushed micro-grain, amplitude-gated by the detail field (brushed, not speckle).
        rng = np.random.default_rng((int(seed) & 0xFFFFFFFF) ^ 0x5EED)
        gw = min(W, 512); gh = min(H, 512)
        raw = rng.standard_normal((gh, gw)).astype(np.float32)
        raw = cv2.GaussianBlur(raw, (0, 0), 0.6)
        brushed = cv2.GaussianBlur(raw, (9, 1), 0)
        brushed = brushed / (brushed.std() + 1e-6)
        if (gh, gw) != (H, W):
            brushed = cv2.resize(brushed, (W, H), interpolation=cv2.INTER_LINEAR)
        grain = brushed * (0.30 + 0.70 * detail_n)

        detail_c = detail_n - float(detail_n.mean())
        field = 0.55 * detail_c + 1.0 * grain
        field = field - float(field.mean())
        field = field / (field.std() + 1e-6)

        Mn = M / 255.0
        gloss = np.clip(Mn * 1.15, 0.0, 1.0) * np.clip((110.0 - R) / 110.0, 0.0, 1.0)
        gate = (1.0 - 0.78 * gloss).astype(np.float32)
        gate = np.where(M >= 240.0, 0.0, gate)
        ugate = (field * gate).astype(np.float32)

        # ADAPTIVE amplitude: solve the quadratic in s so corr(M, R + s*u) hits the band centre.
        TARGET = 0.785
        stp = max(1, int(np.sqrt((H * W) / 200000.0)))
        Mf = M[::stp, ::stp].astype(np.float64).ravel()
        Rf = R[::stp, ::stp].astype(np.float64).ravel()
        uf = ugate[::stp, ::stp].astype(np.float64).ravel()
        Mc = Mf - Mf.mean(); Rc = Rf - Rf.mean(); uc = uf - uf.mean()
        sM = Mc.std() + 1e-9
        covMR = float((Mc * Rc).mean()); varR = float((Rc * Rc).mean())
        covRu = float((Rc * uc).mean()); varU = float((uc * uc).mean()) + 1e-12
        cur = abs(covMR / (sM * (np.sqrt(varR) + 1e-9)))
        if cur <= TARGET or varU < 1e-9:
            scale = 0.0
        else:
            K = (covMR / (sM * TARGET)) ** 2
            disc = (2.0 * covRu) ** 2 - 4.0 * varU * (varR - K)
            scale = 64.0 if disc <= 0.0 else (-(2.0 * covRu) + np.sqrt(disc)) / (2.0 * varU)
        scale = float(np.clip(scale, 0.0, 120.0))

        add_R = scale * ugate
        up = np.minimum(add_R, np.where(R < 55.0, 42.0, 255.0))   # spare glossy pixels
        R_new = np.clip(R + up, 15.0, 255.0)
        Cc_new = Cc + (-10.0 * np.clip(add_R / (scale + 1e-6), 0.0, 1.0) * (Cc > 40.0))

        out[:, :, 1] = R_new
        out[:, :, 2] = Cc_new
        out = np.clip(out, 0.0, 255.0)
        # iron-safe inline (route iron_fix runs after too)
        nonmirror = out[:, :, 0] < 240.0
        Rc2 = out[:, :, 1]; Rc2[nonmirror & (Rc2 < 15.0)] = 15.0
        Ccc = out[:, :, 2]; band = (Ccc >= 1.0) & (Ccc < 16.0)
        Ccc[band] = np.where(Ccc[band] >= 8.0, 16.0, 0.0)
        if out.shape[2] == 4:
            out[:, :, 3] = 255.0
        return out.astype(np.uint8)
    except Exception:
        return spec_u8


def _clearcoat_depth(spec_u8, tex01, seed):
    """SPEC-SCULPT clearcoat depth (2026-06-25, QA over real liveries). QA found Cc under-developed +
    flat (median Cc_mean 35 vs M 120/R 131; 22/52 with Cc_std<20) — cars read more matte than a real
    clear-coated paint. This adds paint-anchored clearcoat DEPTH that peaks on the SPECULAR CRESTS / bright
    highlight ridges (white top-hat on paint luma + bright-ridge term), gated to gloss-readiness (bright +
    smooth + saturated; matte/dark/textured stays dry), additive so the low-Cc flats are preserved (not a
    uniform sheet), mirror plates left alone, Metallic untouched, a tiny same-sign R dip on the wettest
    crests (keeps decorrelation). Iron-safe inline. A/B-won (crest-specular) over gloss/candy/hybrid:
    +20 Cc_mean / +21 Cc_std across 8 real cars, 0 iron fails, corr(M,R) shift <=0.02, ~95ms @1024."""
    spec = np.asarray(spec_u8)
    if spec.ndim != 3 or spec.shape[2] < 3:
        return spec_u8
    try:
        H, W = spec.shape[:2]
        out = spec.astype(np.float32).copy()
        M = out[:, :, 0]; R = out[:, :, 1]; Cc = out[:, :, 2]
        tex = np.asarray(tex01, dtype=np.float32)
        if tex.ndim == 2:
            tex = np.stack([tex] * 3, axis=-1)
        tex = tex[:, :, :3]
        if tex.size and float(tex.max()) > 1.5:
            tex = tex / 255.0
        if tex.shape[:2] != (H, W):
            tex = cv2.resize(tex, (W, H), interpolation=cv2.INTER_AREA)
        tex = np.clip(tex, 0.0, 1.0)
        r, g, b = tex[:, :, 0], tex[:, :, 1], tex[:, :, 2]
        lum = (0.299 * r + 0.587 * g + 0.114 * b).astype(np.float32)
        mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b)
        sat = (mx - mn)
        scale = float(max(H, W))
        DS = 512
        s = min(1.0, DS / scale)
        if s < 1.0:
            Wd, Hd = max(16, int(round(W * s))), max(16, int(round(H * s)))
            lum_s = cv2.resize(lum, (Wd, Hd), interpolation=cv2.INTER_AREA)
            sat_s = cv2.resize(sat, (Wd, Hd), interpolation=cv2.INTER_AREA)
        else:
            Wd, Hd = W, H; lum_s, sat_s = lum, sat
        scl_s = float(max(Hd, Wd))

        def _tophat(ksize):
            k = max(3, int(ksize) | 1)
            return cv2.morphologyEx(lum_s, cv2.MORPH_TOPHAT,
                                    cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        crest = np.maximum(_tophat(0.012 * scl_s), 0.65 * _tophat(0.030 * scl_s))
        crest = cv2.GaussianBlur(crest, (0, 0), max(0.6, 0.0012 * scl_s))
        c_hi = float(np.percentile(crest, 99.0)) + 1e-6
        crest_n = (np.clip(crest / c_hi, 0.0, 1.0) ** 0.80).astype(np.float32)

        l_lo = float(np.percentile(lum_s, 70.0)); l_hi = float(np.percentile(lum_s, 99.0)) + 1e-6
        bright = np.clip((lum_s - l_lo) / (l_hi - l_lo), 0.0, 1.0).astype(np.float32)
        bright = bright * bright

        rad = max(1.0, 0.0016 * scl_s)
        mean = cv2.GaussianBlur(lum_s, (0, 0), rad)
        sq = cv2.GaussianBlur(lum_s * lum_s, (0, 0), rad)
        detail = np.sqrt(np.maximum(sq - mean * mean, 0.0))
        d_hi = float(np.percentile(detail, 92.0)) + 1e-6
        smooth = np.clip(1.0 - detail / d_hi, 0.0, 1.0).astype(np.float32)
        bright_gate = np.clip(lum_s * 1.25, 0.0, 1.0)
        sat_gate = 0.45 + 0.55 * np.clip(sat_s * 2.6, 0.0, 1.0)
        shadow_kill = np.clip((lum_s - 0.06) / 0.14, 0.0, 1.0)
        gloss_ready = np.clip((0.35 + 0.65 * smooth) * bright_gate * sat_gate * shadow_kill, 0.0, 1.0).astype(np.float32)

        wet = (0.78 * crest_n + 0.42 * bright) * gloss_ready
        wet = cv2.GaussianBlur(wet, (0, 0), max(0.6, 0.0018 * scl_s))
        w_hi = float(np.percentile(wet, 99.0)) + 1e-6
        wet = np.clip(wet / w_hi, 0.0, 1.0).astype(np.float32)
        if (Hd, Wd) != (H, W):
            wet = cv2.resize(wet, (W, H), interpolation=cv2.INTER_LINEAR)
            gloss_ready = cv2.resize(gloss_ready, (W, H), interpolation=cv2.INTER_LINEAR)

        not_mirror = (M < 240.0).astype(np.float32)
        add_cc = (150.0 * wet + 26.0 * gloss_ready * (wet > 0.05)) * not_mirror
        wet_strong = np.clip((wet - 0.55) / 0.45, 0.0, 1.0)
        out[:, :, 0] = M
        out[:, :, 1] = R - (10.0 * wet_strong * not_mirror)
        out[:, :, 2] = Cc + add_cc
        out = np.clip(out, 0.0, 255.0)
        nonmirror = out[:, :, 0] < 240.0
        Rc = out[:, :, 1]; Rc[nonmirror & (Rc < 15.0)] = 15.0
        Ccc = out[:, :, 2]; band = (Ccc >= 1.0) & (Ccc < 16.0)
        Ccc[band] = np.where(Ccc[band] >= 8.0, 16.0, 0.0)
        if out.shape[2] == 4:
            out[:, :, 3] = 255.0
        return out.astype(np.uint8)
    except Exception:
        return spec_u8


def _zone_classify(rgb, busy, cov):
    """Pick a material NAME for a color cluster from its mean color + texture + COVERAGE. Coverage is the
    key intelligence: a small bright-neutral cluster = chrome trim/number, but a BIG bright-neutral field =
    satin body (so a white car doesn't become a whole-car chrome mirror)."""
    r, g, b = float(rgb[0]), float(rgb[1]), float(rgb[2])
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    mx, mn = max(r, g, b), min(r, g, b)
    sat = (mx - mn) / (mx + 1e-5)
    big = cov >= 0.16
    if busy > 0.40 and luma < 0.58 and not big:
        return "forged_carbon" if luma > 0.3 else "carbon"
    if luma < 0.14:
        return "flat"
    if luma < 0.30 and sat < 0.28:
        return "matte"
    if luma > 0.74 and sat < 0.16:
        return "satin" if big else "chrome"
    if luma > 0.60 and sat < 0.20:
        return "satin" if big else "brushed_metal"
    if sat > 0.42:
        if r > g and g > b and luma > 0.40:
            return "gold" if luma > 0.6 else "copper"
        if b >= r and b >= g:
            return "anodized" if luma > 0.45 else "candy"
        return "gloss" if (big and cov > 0.45) else "candy"
    if sat > 0.22:
        return "pearl" if luma > 0.45 else "semi_gloss"
    if luma > 0.6:
        return "satin"
    if luma > 0.4:
        return "semi_gloss"
    return "gunmetal"


def zoned_auto_spec(tex01, seed, drama=1.0):
    """PER-PANEL geometry-aware auto-spec (2026-06-26): segment the paint into color regions and assign a
    fitting MATERIAL per region (chrome on bright graphics, satin on the body, matte on dark, carbon on busy
    zones, candy/gold/anodized on vivid color), then build ONE feathered, detail-modulated, iron-safe spec.
    The "program knows where to sculpt" one-click. tex01: HxWx3 float 0..1 -> HxWx4 uint8 (M,R,Cc,255).
    A/B-won (color-cluster) over superpixel/feature-blend: ~9 distinct materials/livery, 0 iron fails, ~130ms.
    ``drama`` is the bounded Easy Mode intent control: below 1 moves materials toward safe satin;
    above 1 increases the same per-region material contrast and fine paint response."""
    try:
        mats = {k: np.asarray(tuple(v)[:3], np.float32) for k, v in HUE_MATERIALS.items()
                if hasattr(v, "__len__") and len(v) >= 3}
        if "satin" not in mats:
            mats["satin"] = np.asarray((105, 110, 140), np.float32)
        mirror = {n for n, v in mats.items() if v[0] >= 235 and v[1] <= 40}
        rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
        tex = np.clip(np.asarray(tex01, np.float32), 0.0, 1.0)
        if tex.ndim == 2:
            tex = np.stack([tex] * 3, -1)
        tex = tex[:, :, :3]
        H, W = tex.shape[:2]
        seg = 256
        scale = seg / max(H, W)
        sw, sh = max(1, int(round(W * scale))), max(1, int(round(H * scale)))
        small = cv2.resize(tex, (sw, sh), interpolation=cv2.INTER_AREA)
        lum_s = 0.299 * small[..., 0] + 0.587 * small[..., 1] + 0.114 * small[..., 2]
        busy_s = cv2.GaussianBlur(np.abs(lum_s - cv2.GaussianBlur(lum_s, (0, 0), 2.0)), (0, 0), 3.0)
        busy_s = busy_s / (busy_s.max() + 1e-5)
        mx = small.max(-1); mn = small.min(-1)
        sat_s = (mx - mn) / (mx + 1e-5)
        feat = np.concatenate([small.reshape(-1, 3), lum_s.reshape(-1, 1) * 0.6,
                               sat_s.reshape(-1, 1) * 0.9], axis=1).astype(np.float32)
        K = 8
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 14, 0.5)
        cv2.setRNGSeed(int(seed) & 0x7FFFFFFF)
        feat_j = feat + rng.normal(0, 1e-3, feat.shape).astype(np.float32)
        _, labels, centers = cv2.kmeans(feat_j, K, None, crit, 1, cv2.KMEANS_PP_CENTERS)
        labels = labels.reshape(sh, sw)
        flat_rgb = small.reshape(-1, 3); flat_busy = busy_s.reshape(-1); lab_flat = labels.reshape(-1)
        clu_rgb = np.zeros((K, 3), np.float32); clu_busy = np.zeros(K, np.float32); clu_cov = np.zeros(K, np.float32)
        for k in range(K):
            m = lab_flat == k; nk = int(m.sum()); clu_cov[k] = nk / lab_flat.size
            if nk == 0:
                clu_rgb[k] = centers[k, :3]; continue
            clu_rgb[k] = flat_rgb[m].mean(0); clu_busy[k] = flat_busy[m].mean()
        names = [_zone_classify(clu_rgb[k], clu_busy[k], clu_cov[k]) for k in range(K)]
        names = [n if n in mats else "satin" for n in names]
        mirror_cov = sum(clu_cov[k] for k in range(K) if names[k] in mirror)
        if mirror_cov > 0.50:
            for k in np.argsort(-clu_cov):
                if names[k] in mirror and clu_cov[k] > 0.20:
                    names[k] = "satin_metal" if (clu_rgb[k].mean() > 0.7 and "satin_metal" in mats) else "brushed_metal"
                    names[k] = names[k] if names[k] in mats else "satin"
                    mirror_cov -= clu_cov[k]
                    if mirror_cov <= 0.50:
                        break
        mat_vec = np.stack([mats[n] for n in names], 0)
        # Owner Easy Mode 2026-07-18: one human intent control, not three PBR
        # channel sliders. Less moves assigned materials toward safe satin;
        # Wild increases the same per-region contrast. Existing fine features
        # stay the same size, and catalog finishes are not modified.
        drama = float(np.clip(drama, 0.55, 1.45))
        satin_center = np.asarray((105.0, 110.0, 140.0), np.float32)
        mat_vec = np.clip(satin_center + (mat_vec - satin_center) * drama, 0.0, 255.0)
        onehot = np.zeros((K, sh, sw), np.float32)
        for k in range(K):
            onehot[k] = (labels == k).astype(np.float32)
        feather = max(1.0, seg / 110.0)
        big = np.zeros((K, H, W), np.float32)
        for k in range(K):
            big[k] = cv2.resize(cv2.GaussianBlur(onehot[k], (0, 0), feather), (W, H), interpolation=cv2.INTER_LINEAR)
        big /= (big.sum(0) + 1e-6)[None]
        spec = np.tensordot(big.transpose(1, 2, 0), mat_vec, axes=([2], [0]))
        lum = 0.299 * tex[..., 0] + 0.587 * tex[..., 1] + 0.114 * tex[..., 2]
        detail = np.clip(lum - cv2.GaussianBlur(lum, (0, 0), 2.2), -0.25, 0.25)
        spec[..., 0] += detail * 26.0 * drama
        spec[..., 1] += -detail * 22.0 * drama + cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.8) * 2.0
        spec[..., 2] += detail * 30.0 * drama
        spec = np.clip(spec, 0, 255)
        M = spec[..., 0]; R = spec[..., 1]; Cc = spec[..., 2]
        R = np.where((M < 240) & (R < 15), 15.0, R)
        Cc = np.where((Cc >= 1) & (Cc < 16), 16.0, Cc)
        out3 = np.clip(np.round(np.stack([M, R, Cc], -1)), 0, 255).astype(np.uint8)
        return np.dstack([out3, np.full((H, W), 255, np.uint8)])
    except Exception:
        return scratch_spec_from_any_paint(np.asarray(tex01, np.float32), seed=int(seed) & 0x7FFFFFFF)


def scratch_spec_from_any_paint(
    tex_rgb_hwc: np.ndarray,
    *,
    seed: int = 9101,
    chromatic_shift: bool = True,
    dark_interior_flatten: float = 0.38,
    void_metallic_max: float = 92.0,
    void_roughness_min: float = 158.0,
    void_clearcoat_max: float = 44.0,
    spec_multiplier: float = 1.0,
    preset_stack: list[tuple[str, float]] | None = None,
    catalog_stack: list[tuple[str, float]] | None = None,
    fusion_mix: float | None = None,
    fusion_mix_m: float | None = None,
    fusion_mix_r: float | None = None,
    fusion_mix_cc: float | None = None,
    fusion_strategy: str = FUSION_STRATEGY_LINEAR,
    paint_emphasis: str = PAINT_EMPHASIS_UNIFORM,
    paint_emphasis_strength: float = 0.0,
    hue_focus_deg: float | None = None,
    hue_focus_width: float = 60.0,
    hue_focus_strength: float = 0.0,
    vm_detail_scale: float | None = None,
    pattern_tile: float = 1.0,
    fast_trace: bool = False,
) -> np.ndarray:
    """Return HxWx4 uint8 RGBA spec (A=255), paint-aware scratch + VM DNA clamps.

    Uses the same stack as Union Jacked live scratch when no baked *_spec.png exists:
    ``_scratch_spec_from_paint`` → ``_pre_adjust_viva_mexico_spec`` → masked composite
    (full-frame: mask=1, outside=0) → ``_post_adjust_viva_mexico_spec``.

    ``fusion_strategy``: ``linear`` (default) or ``gloss_win_metallic`` — latter lets local
    metallic “win” per pixel instead of averaging, often closer to layered showroom reads.

    Optional ``fusion_mix_m`` / ``fusion_mix_r`` / ``fusion_mix_cc`` override per-channel
    catalog weights when fusing registry + scratch (defaults follow ``fusion_mix``).

    ``paint_emphasis`` + ``paint_emphasis_strength`` tie metallic/clearcoat to luminance or
    saturation in the source paint. ``hue_focus_*`` boosts spec where paint hue matches a target.

    ``vm_detail_scale`` maps to ``detail_scale`` (``DS``) inside ``_pre_adjust_viva_mexico_spec`` —
    the same global intensity knob used across Viva Mexico, Rising Sun, and Union Jacked catalog
    finishes (see ``VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md``). Default ``None`` uses engine
    default (~1.59).
    """
    if tex_rgb_hwc.ndim != 3 or tex_rgb_hwc.shape[2] < 3:
        raise ValueError("tex_rgb_hwc must be HxWx3")
    tex = np.ascontiguousarray(tex_rgb_hwc[:, :, :3], dtype=np.float32)
    h, w = tex.shape[:2]
    m = np.ones((h, w), dtype=np.float32)
    outside = 1.0 - m
    sm = float(np.clip(spec_multiplier, 0.0, 1.0))

    cat = normalize_catalog_stack(catalog_stack)
    stack = normalize_preset_stack(preset_stack)
    base_seed = int(seed) & 0xFFFFFFFF

    # [SPB-SPEC-SCULPT fix#4 2026-06-02] Paint-aware BY DEFAULT + preview<->final consistency.
    # When the caller requests no emphasis (UNIFORM, strength<=0), derive a per-SEED emphasis so the
    # spec adapts to the car paint AND any caller using the same finish+seed gets the IDENTICAL
    # result — SHOKK THE WORLD's preview tile and the /generate full-res render of that picked look
    # now match (iteration 4 made only the preview paint-aware, which desynced them). Explicit
    # emphasis from the manual UI is always respected (we only fill the unset case).
    if paint_emphasis == PAINT_EMPHASIS_UNIFORM and paint_emphasis_strength <= 0.0:
        _auto_emph = (PAINT_EMPHASIS_HIGHLIGHTS, PAINT_EMPHASIS_SATURATED, PAINT_EMPHASIS_SHADOWS,
                      PAINT_EMPHASIS_HIGHLIGHTS, PAINT_EMPHASIS_DESATURATED)
        paint_emphasis = _auto_emph[base_seed % len(_auto_emph)]
        paint_emphasis_strength = 0.5

    # Build ONE unified real-finish catalog stack from the user's catalog picks and/or
    # the selected presets (presets map to real finish ids). fusion_mix weights the two
    # sources when both are present (catalog * a, presets * (1-a)).
    preset_cat = preset_stack_to_catalog(stack) if stack else []
    fuse = fusion_mix
    if fuse is not None:
        fuse = float(np.clip(fuse, 0.0, 1.0))

    unified: dict[str, float] = {}
    if cat and preset_cat and fuse is not None:
        a = float(fuse)
        for fid, wv in cat:
            unified[fid] = unified.get(fid, 0.0) + wv * a
        for fid, wv in preset_cat:
            unified[fid] = unified.get(fid, 0.0) + wv * (1.0 - a)
    else:
        for fid, wv in cat:
            unified[fid] = unified.get(fid, 0.0) + wv
        for fid, wv in preset_cat:
            unified[fid] = unified.get(fid, 0.0) + wv

    if unified:
        # --- REAL-FINISH path: blend registered finish specs, NO Viva grid pass ---
        ordered = sorted(unified.items(), key=lambda kv: kv[1], reverse=True)[:MAX_FINISH_BLEND]
        tw = sum(wv for _, wv in ordered) or 1.0
        finish_stack = [(fid, wv / tw) for fid, wv in ordered]
        # Per-preset pattern fineness (owner audit "too big" fix): a flagged preset carries
        # tile>1 so ONLY it renders finer; keeps stay whole-frame. An explicit caller
        # pattern_tile can still push finer, never coarser.
        eff_tile = max(float(pattern_tile),
                       max((PRESET_TILE_BY_ID.get(pid, 1.0) for pid, _ in stack), default=1.0))
        # BUGFIX 2026-10-04 (encyclopedia pass, "dead Mix strategy / Showroom"): fusion_strategy and
        # fusion_mix_m/r/cc were accepted here but NEVER read -- measured spec diff 0.000 for
        # Showroom and for the split-channel sliders vs Balanced. When BOTH sources are present
        # (catalog + presets with a fusion_mix) and the user picked Showroom or split channels,
        # render each source on its own and fuse them with fuse_registry_and_scratch_specs
        # (catalog = "registry", presets = second source). Balanced/no-split keeps the original
        # single weighted blend byte-identical. Single-source and legacy paths have nothing to mix.
        _split = any(v is not None for v in (fusion_mix_m, fusion_mix_r, fusion_mix_cc))
        _two_src = bool(cat and preset_cat and fuse is not None)
        if _two_src and (fusion_strategy == FUSION_STRATEGY_GLOSS_WIN or _split):
            def _norm_top(rows):
                rows = sorted(rows, key=lambda kv: kv[1], reverse=True)[:MAX_FINISH_BLEND]
                t = sum(wv for _, wv in rows) or 1.0
                return [(fid, wv / t) for fid, wv in rows]
            _cap = 512 if fast_trace else None
            _spec_cat = blend_registered_specs_float((h, w), m, seed=base_seed, sm=sm, stack=_norm_top(cat),
                                                     tile=eff_tile, render_cap_px=_cap)
            _spec_pre = blend_registered_specs_float((h, w), m, seed=base_seed, sm=sm, stack=_norm_top(preset_cat),
                                                     tile=eff_tile, render_cap_px=_cap)
            _a = float(fuse)
            _am = float(np.clip(fusion_mix_m if fusion_mix_m is not None else _a, 0.0, 1.0))
            _ar = float(np.clip(fusion_mix_r if fusion_mix_r is not None else _a, 0.0, 1.0))
            _ac = float(np.clip(fusion_mix_cc if fusion_mix_cc is not None else _a, 0.0, 1.0))
            spec = fuse_registry_and_scratch_specs(
                np.asarray(_spec_cat, dtype=np.float32), np.asarray(_spec_pre, dtype=np.float32),
                _am, _ar, _ac, strategy=fusion_strategy)
        else:
            spec = blend_registered_specs_float((h, w), m, seed=base_seed, sm=sm, stack=finish_stack,
                                                tile=eff_tile, render_cap_px=512 if fast_trace else None)
        spec = np.asarray(spec, dtype=np.float32)
        # [SPB-SPEC-SCULPT fix#13 2026-06-02] Viva paint-trace on catalog World looks.
        # Owner overnight: gallery read as full-frame magenta/green wallpaper, not tracing truck
        # panels. Metrics (lum corr) passed but eye failed — uniform-mask catalog + weak emphasis.
        # Pipeline: spatial envelope -> scratch skeleton fuse -> ridge/crest trace -> post void.
        # Skips Viva dot/octave grids (2026-06-01 grid-flash). paw chevy ~0.58 -> ~0.72; edge corr up.
        from engine.spec_sculpt.paint_trace import (
            apply_fast_paint_trace,
            apply_paint_trace_prepass,
            edge_gated_catalog_detail,
            finalize_traced_spec_u8,
            imprint_scratch_highpass,
            spatial_envelope_catalog,
        )

        finish_id = f"spec_sculpt_{base_seed}"
        if fast_trace:
            # SPB-BETA-2026-07-20: Easy/Simple/Auto-Sculpt uses one paint-aware
            # pass so a 2048 result does not spend 30-40 seconds recomputing the
            # same livery cues. Authored finish detail is already present in
            # ``spec``; Advanced/manual keeps the exact five-pass legacy trace.
            apply_fast_paint_trace(spec, tex, m, strength=1.0)
        else:
            edge_gated_catalog_detail(spec, tex, m, strength=1.08)
            imprint_scratch_highpass(spec, tex, m, finish_id, mix=0.48, chromatic_shift=chromatic_shift)
            spatial_envelope_catalog(spec, tex, m, strength=0.92)
            apply_paint_linked_emphasis(
                spec, tex,
                emphasis=paint_emphasis, strength=paint_emphasis_strength,
                hue_deg=hue_focus_deg, hue_width=hue_focus_width, hue_strength=hue_focus_strength,
            )
            apply_paint_trace_prepass(spec, tex, m, finish_id, strength=1.05, detail_scale=1.48)
        # [SPB-SPEC-SCULPT fix#7 2026-06-02] Blank/solid-livery detail floor (GATED on near-uniform
        # paint). On the chevy etc. (tex.std() >> 0.04) this is a NO-OP, so the gallery-confirmed
        # real-livery path stays byte-identical. On a blank/solid livery the paint coupling adds
        # nothing and 7 of 24 picks (void, worn_chrome, weathered_paint, ...) render FLAT — inject a
        # subtle fine micro-texture so SHOKK THE WORLD never yields a uniform result, even on a blank
        # canvas. Diagnosed iter9: white-car min look detail 0.8 (flat) despite chevy detail 33-58.
        if float(tex.std()) < 0.04:
            _inject_uniform_paint_detail_floor(spec, base_seed)
        spec = np.clip(np.round(spec), 0, 255).astype(np.uint8) if fast_trace else finalize_traced_spec_u8(spec, tex, m)
        # Iron-safe floors + outside fill. (sm already applied inside the blend.)
        spec = spec.astype(np.float32)
        spec[:, :, 0] = np.clip(spec[:, :, 0] * m + 4.0 * outside, 0, 255)
        spec[:, :, 1] = np.clip(spec[:, :, 1] * m + 120.0 * outside, 15, 255)
        spec[:, :, 2] = np.clip(spec[:, :, 2] * m + 80.0 * outside, 16, 255)
        spec[:, :, 3] = 255.0
        # NOTE 2026-06-25: catalog/preset/fusion blends carry AUTHORED finish specs (FRACTURED, carbon
        # weave, etc.). Do NOT decorrelate them — it rewrites their roughness ~180 levels and destroys the
        # owner-tuned look. Decorrelation is ONLY for the pure paint-derived legacy scratch below (the path
        # that builds Roughness as inverted Metallic). Fusion that is scratch-dominant accepts mild
        # correlation as the cost of preserving the authored finish the user deliberately blended in.
        return spec.astype(np.uint8)

    # --- LEGACY fallback (no preset / no catalog selected): paint-derived scratch + Viva ---
    finish_id = f"spec_sculpt_{base_seed}"
    spec = np.asarray(
        _scratch_spec_from_paint(tex, m, finish_id, chromatic_shift=chromatic_shift), dtype=np.float32)
    apply_paint_linked_emphasis(
        spec, tex,
        emphasis=paint_emphasis, strength=paint_emphasis_strength,
        hue_deg=hue_focus_deg, hue_width=hue_focus_width, hue_strength=hue_focus_strength,
    )
    _pre_adjust_viva_mexico_spec(
        spec, tex, m, finish_id, dark_interior_flatten=dark_interior_flatten, detail_scale=vm_detail_scale)
    spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m + 4.0 * outside, 0, 255)
    spec[:, :, 1] = np.clip(spec[:, :, 1] * m + 120.0 * outside, 15, 255)
    spec[:, :, 2] = np.clip(spec[:, :, 2] * m + 80.0 * outside, 16, 255)
    spec[:, :, 3] = 255.0
    out = _post_adjust_viva_mexico_spec(
        spec.astype(np.uint8), tex, m,
        void_metallic_max=void_metallic_max, void_roughness_min=void_roughness_min,
        void_clearcoat_max=void_clearcoat_max)
    return _clearcoat_depth(_decorrelate_roughness(out, tex, base_seed), tex, base_seed)


# FRACTURE constant default mirrors fracture.py's _FR_G_FLOOR so the route + UI agree.
FRACTURE_CALM_FLOOR_DEFAULT = 30.0


def fracture_spec_from_any_paint(
    tex_rgb_hwc: np.ndarray,
    *,
    ignition: float = 1.0,
    angle_gate: float = 1.0,
    trace_strength: float = 1.0,
    calm_floor: float = FRACTURE_CALM_FLOOR_DEFAULT,
    decorrelation: float = 0.0,
) -> np.ndarray:
    """FRACTURE mode for Spec Sculpt — ignite an arbitrary paint with the FRACTURED look.

    Wraps the shared, verified FRACTURE engine (``engine.spec_sculpt.fracture.fracture_spec``)
    with the full-frame mask convention the Spec Sculpt route uses everywhere else
    (mask=1 over the whole canvas; the zone workflow supplies the real mask later). The 5
    dials pass straight through (the engine clips each to its safe range):

      ignition       0..2     overall drama (lane contrast + how hard the motif pops).
      angle_gate     0.25..2  ignition tightness (higher = sharper, more concentrated lanes).
      trace_strength 0..2     how strongly the paint's own geometry drives the motif lanes.
      calm_floor     14..110  off-motif roughness (lower = glossier mirror body).
      decorrelation  0..1     pushes M / R / Cc motifs apart so the channels aren't carbon copies.

    Returns HxWx4 uint8 RGBA spec (R=Metallic, G=Roughness, B=Clearcoat, A=255) — the same
    contract ``scratch_spec_from_any_paint`` returns, so the route handles it identically.
    """
    if tex_rgb_hwc.ndim != 3 or tex_rgb_hwc.shape[2] < 3:
        raise ValueError("tex_rgb_hwc must be HxWx3")
    # Imported lazily so generate.py keeps importing even if fracture deps shift; the
    # engine itself is shared + verified and MUST NOT be modified here.
    from engine.spec_sculpt.fracture import fracture_spec

    tex = np.ascontiguousarray(tex_rgb_hwc[:, :, :3], dtype=np.float32)
    h, w = tex.shape[:2]
    mask = np.ones((h, w), dtype=np.float32)
    return fracture_spec(
        tex,
        mask,
        ignition=ignition,
        angle_gate=angle_gate,
        trace_strength=trace_strength,
        calm_floor=calm_floor,
        decorrelation=decorrelation,
        as_uint8=True,
    )


def candy_depth_spec_from_any_paint(
    tex_rgb_hwc: np.ndarray,
    *,
    depth: float = 1.0,
    flake_density: float = 0.5,
    flake_size: float = 1.0,
    wetness: float = 0.78,
    satin_floor: float = 0.42,
    seed: int = 7,
    as_uint8: bool = True,
) -> np.ndarray:
    """CANDY DEPTH mode for Spec Sculpt (2026-06-19) — sculpt bottomless WET-CANDY clearcoat from any paint.

    Derives a per-pixel DEPTH field from the source paint (rich/dark areas read as deep glassy candy;
    pale areas as thin satin — so the designer 'paints thickness' by painting the art), then:
      * drives CLEARCOAT toward 16 (max clear) in the deep pools, dull (~175) where thin;
      * a tight LOW-ROUGHNESS lobe in the deep pools (wet glass), satin where thin;
      * suspends bright metallic FLAKES that read THROUGH the coat where it's deep enough.
    Ends with enforce_iron_rules so 16=max clearcoat / R>=15 are guaranteed legal.

    Returns HxWx4 uint8 (R=Metallic, G=Roughness, B=Clearcoat, A=255) — same contract as
    fracture_spec_from_any_paint, so the Spec Sculpt route handles it identically. The candy COLOUR
    lives in the user's paint (tint-through-clear is an albedo effect); this generates the SPEC only.

    dials: depth 0..1.5 (overall candy depth) · flake_density 0..1 · flake_size 0.5..3 px ·
           wetness 0..1 (gloss of deep pools) · satin_floor 0.15..0.8 (roughness of shallow regions).
    """
    import cv2
    from engine.core import enforce_iron_rules

    if tex_rgb_hwc.ndim != 3 or tex_rgb_hwc.shape[2] < 3:
        raise ValueError("tex_rgb_hwc must be HxWx3")
    tex = np.ascontiguousarray(tex_rgb_hwc[:, :, :3], dtype=np.float32)
    if tex.size and tex.max() > 1.5:
        tex = tex / 255.0
    H, W = tex.shape[:2]

    lum = 0.299 * tex[..., 0] + 0.587 * tex[..., 1] + 0.114 * tex[..., 2]
    sat = tex.max(-1) - tex.min(-1)
    raw = 0.6 * (1.0 - lum) + 0.4 * sat                      # rich/dark -> deeper candy
    lo, hi = float(np.percentile(raw, 5)), float(np.percentile(raw, 95))  # percentile-adaptive
    df = np.clip((raw - lo) / (hi - lo + 1e-6), 0.0, 1.0)
    df = cv2.GaussianBlur(df, (0, 0), 1.2) * float(np.clip(depth, 0.0, 1.5))
    df = np.clip(df, 0.0, 1.0)

    Cc = 16.0 + (1.0 - df) * (175.0 - 16.0)                  # deep -> max clear, thin -> dull
    wet = (1.0 - float(np.clip(wetness, 0.0, 1.0))) * 0.25 + 0.05
    sf = float(np.clip(satin_floor, 0.15, 0.8))
    Rough = (wet + (1.0 - df) * (sf - wet)) * 255.0          # deep -> wet/glossy, thin -> satin
    M = (0.40 + 0.30 * df) * 255.0                           # body mid-metal rising with depth

    rng = np.random.default_rng(int(seed))
    thr = 0.018 * float(np.clip(flake_density, 0.0, 1.0)) * 2.0
    flake = (rng.random((H, W)) < thr).astype(np.float32)
    fs = max(1, int(round(float(flake_size))))
    if fs > 1:
        flake = cv2.dilate(flake, np.ones((fs, fs), np.uint8))
    flake = flake * (df > 0.25)                              # flakes only where candy is deep enough
    M = np.where(flake > 0, 250.0, M)                        # flakes very metallic
    Rough = np.where(flake > 0, 16.0, Rough)                 # flakes glint
    Cc = np.where(flake > 0, 16.0, Cc)                       # flakes under max-clear coat

    spec = np.stack([M, Rough, Cc, np.full((H, W), 255.0, np.float32)], -1)
    spec = np.clip(spec, 0, 255).astype(np.uint8)
    enforce_iron_rules(spec)
    return spec if as_uint8 else (spec.astype(np.float32) / 255.0)
