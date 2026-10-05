"""
engine/paint_v2/money_shokk_claude_blackout.py — ★ MONEY SHOKK · BLACKOUT (Claude)
==================================================================================
The black-base burnthrough family the bake-off was missing.

Owner mandate 2026-05-28: the V1/V2 MONEY SHOKK sets all landed blue/indigo and
the lineup risks becoming "247 shades of blue." The real mechanism is luminance,
not hue — a glow pops when a bright specular flash separates from a DARK,
saturated base. The most extreme case of that is a near-black base with a
saturated color buried in fine gates that only burn through at glancing angles.

That is exactly what COLORSHOXX already does. This module BRIDGES the COLORSHOXX
angle-reveal machinery (engine/paint_v2/structural_color.py: _cx_apply_angle_reveals
paint + _cx_angle_reveal_spec married spec) into the MONEY SHOKK family. The married
spec keeps the absorb regions matte (R~176, deep black reads matte not plastic) and
drives the gated flash pixels glossy (R→12) — the same low-roughness "glow" the
owner's 9/10 finishes used (rising_sun_prismwave R-ceiling 185), but now aligned
pixel-for-pixel with the buried color so every flash reveals chroma, not white.

Three reveal mechanisms, mixed per owner request ("try some of each"):
  * BURIED ARBITRARY — near-black base, an arbitrary saturated color burns through.
    Reveal hue is decoupled from the base, so we get bronze / orange / green /
    magenta / cyan on the SAME black body. (bronze, inferno, emerald, magenta, voltage)
  * COMPLEMENT BLOOM — a dark-TINTED base whose flash blooms toward its complement.
    (oilslick: dark teal-black → warm copper bloom)
  * METALLIC SAME-HUE — a dark metal base + buried brighter same hue + high metal
    floor → "liquid metal" intensify. (liquid_bronze, gunmetal_violet)

Prefix mshcb_. Seed base 9770 (COLORSHOXX uses 9001–9034; my bright set 9750–9759).
See docs/COLOR_CHANGE_BREAKTHROUGH.html (Claude section) for the doctrine.
"""
from __future__ import annotations

import numpy as np

from engine.paint_v2.structural_color import (
    _cx_apply_angle_reveals,
    _cx_angle_reveal_spec,
)
from engine.paint_v2.money_shokk import _ms_decorrelate_depth

__all__ = ["MONEY_SHOKK_CLAUDE_BLACKOUT_BASE_REGISTRY"]

_SEED_BASE = 9770

# Glossy married-spec preset — matte deep base (r_lo high) + glassy gated flash
# (r_hi low). Mirrors the owner-proven low-roughness "glow" but on a black base.
_GLOSS = dict(m_hi=247, m_lo=9, r_hi=12, r_lo=176, cc_hi=15, cc_lo=156)
# Liquid-metal preset — high metal floor (m_lo lifted) so the base itself reads
# metallic, glossier overall (r_lo lower), for same-hue intensify finishes.
_METAL = dict(m_hi=250, m_lo=34, r_hi=10, r_lo=132, cc_hi=18, cc_lo=128)


def _make_blackout(finish_id, seed_off, base_dark, reveals, spec_kw,
                   gate_density=0.0068, underlay_strength=0.0, desc=""):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        del bb
        if getattr(paint, "ndim", 0) == 3 and paint.shape[2] > 3:
            paint = paint[:, :, :3].copy()
        return _cx_apply_angle_reveals(
            paint, shape, mask, seed, pm, seed_off,
            base_dark=base_dark, reveals=reveals,
            gate_density=gate_density, underlay_strength=underlay_strength,
        )

    def spec_fn(shape, seed, sm, base_m, base_r):
        del base_m, base_r
        res = _cx_angle_reveal_spec(shape, seed, sm, seed_off, **spec_kw)
        if isinstance(res, np.ndarray) and res.ndim == 3 and res.shape[2] >= 3:
            M, R, CC = res[:, :, 0], res[:, :, 1], res[:, :, 2]
        else:
            M, R, CC = res
        # 2026-06-20 rework: angle-reveal spec drove M/R/Cc from one field (|corr|≈1.0).
        # Keep the reveal motif (M); rebuild R/Cc with independent 3D-traced geometry.
        return _ms_decorrelate_depth(
            np.asarray(M, dtype=np.float32), np.asarray(R, dtype=np.float32),
            np.asarray(CC, dtype=np.float32), int(seed) + seed_off, seed_off)

    paint_fn.__name__ = f"paint_{finish_id}"
    paint_fn.__doc__ = desc
    spec_fn.__name__ = f"spec_{finish_id}"
    spec_fn.__doc__ = desc
    return paint_fn, spec_fn


# ── FLASH FORGE (2026-06-19) ──────────────────────────────────────────────────
# Build a blackout-family angle-reveal finish from USER input — the engine half of the Flash Forge
# tool. Drives the shipped _make_blackout factory above: `head_on` = the base colour seen straight on
# (near-black bases flash hardest), `hidden` = [{rgb, axis, strength}] colours that ignite on their
# axis, `sharpness` -> gate density (crispness of the flash), `separation` -> strength spread so the
# hidden colours occupy distinct angle bands. Returns registry-shaped (paint_fn, spec_fn).
_FF_AXES = ("u", "v", "diag_a", "diag_b")


def flash_forge_build(finish_id, head_on, hidden, *, sharpness=0.5, separation=0.5,
                      metal=False, seed_off=None, desc=""):
    def _c01(c):
        v = [float(x) for x in (list(c) + [0, 0, 0])[:3]]
        if any(x > 1.0 for x in v):
            v = [x / 255.0 for x in v]
        return tuple(max(0.0, min(1.0, x)) for x in v)

    base = _c01(head_on)
    hidden = list(hidden or [])
    n = max(1, len(hidden))
    reveals = []
    for i, h in enumerate(hidden):
        rgb = _c01(h.get("rgb", (1, 1, 1)))
        axis = h.get("axis") if h.get("axis") in _FF_AXES else _FF_AXES[i % len(_FF_AXES)]
        base_strength = float(h.get("strength", 0.92))
        spread = (i - (n - 1) / 2.0) * 0.12 * max(0.0, min(1.0, float(separation)))
        strength = max(0.40, min(1.0, base_strength - abs(spread)))
        reveals.append((rgb, axis, strength))
    if not reveals:  # at least one reveal so the finish actually flashes
        reveals = [((1.0, 1.0, 1.0), "u", 0.9)]
    gate_density = 0.004 + 0.009 * max(0.0, min(1.0, float(sharpness)))
    spec_kw = _METAL if metal else _GLOSS
    so = int(seed_off) if seed_off is not None else (_SEED_BASE + 7000)
    return _make_blackout(finish_id, so, base, reveals, spec_kw,
                          gate_density=gate_density, desc=(desc or f"Flash Forge custom: {finish_id}"))


_MSHCB_ROWS = [
    # ── BURIED ARBITRARY — black body, an arbitrary saturated color burns through ──
    dict(
        id="mshcb_blackout_bronze",
        seed_off=_SEED_BASE,
        base_dark=(0.020, 0.017, 0.013),
        reveals=[
            ((0.86, 0.62, 0.18), "u", 0.96),
            ((0.99, 0.82, 0.32), "v", 0.90),
            ((0.70, 0.42, 0.12), "diag_a", 0.80),
        ],
        spec_kw=_GLOSS,
        desc=(
            "MONEY SHOKK Blackout Bronze — near-black body, bronze→gold→copper "
            "burns through curved panels under glancing sun. Buried-arbitrary "
            "mechanism: reveal hue decoupled from the (black) base."
        ),
    ),
    dict(
        id="mshcb_blackout_inferno",
        seed_off=_SEED_BASE + 1,
        base_dark=(0.026, 0.016, 0.012),
        reveals=[
            ((0.99, 0.55, 0.12), "u", 0.96),
            ((0.98, 0.28, 0.10), "v", 0.92),
            ((0.98, 0.80, 0.24), "diag_a", 0.80),
        ],
        spec_kw=_GLOSS,
        desc=(
            "MONEY SHOKK Blackout Inferno — near-black body, molten "
            "orange→red→amber burns through. Buried-arbitrary; warm spectrum."
        ),
    ),
    dict(
        id="mshcb_blackout_emerald",
        seed_off=_SEED_BASE + 2,
        base_dark=(0.013, 0.022, 0.017),
        reveals=[
            ((0.16, 0.92, 0.42), "u", 0.95),
            ((0.45, 0.97, 0.28), "v", 0.90),
            ((0.12, 0.80, 0.55), "diag_a", 0.80),
        ],
        spec_kw=_GLOSS,
        desc=(
            "MONEY SHOKK Blackout Emerald — near-black body, emerald→lime→jade "
            "burns through. Buried-arbitrary; proves green works on black "
            "(green only failed earlier because the BASE was bright)."
        ),
    ),
    dict(
        id="mshcb_blackout_magenta",
        seed_off=_SEED_BASE + 3,
        base_dark=(0.024, 0.012, 0.020),
        reveals=[
            ((0.98, 0.20, 0.62), "u", 0.95),
            ((0.99, 0.46, 0.80), "v", 0.90),
            ((0.80, 0.12, 0.50), "diag_a", 0.80),
        ],
        spec_kw=_GLOSS,
        desc=(
            "MONEY SHOKK Blackout Magenta — near-black body, magenta→hot "
            "pink→fuchsia burns through. Buried-arbitrary; hot end of spectrum."
        ),
    ),
    dict(
        id="mshcb_blackout_voltage",
        seed_off=_SEED_BASE + 4,
        base_dark=(0.012, 0.016, 0.024),
        reveals=[
            ((0.20, 0.70, 0.99), "u", 0.96),
            ((0.45, 0.92, 0.99), "v", 0.90),
            ((0.15, 0.45, 0.95), "diag_a", 0.80),
        ],
        spec_kw=dict(m_hi=247, m_lo=9, r_hi=12, r_lo=176, cc_hi=20, cc_lo=150),
        desc=(
            "MONEY SHOKK Blackout Voltage — near-black body, electric "
            "blue→ice-cyan→azure burns through. The owner-beloved ice-blue glow, "
            "but on BLACK instead of a blue base. Buried-arbitrary; lifted CC for glow."
        ),
    ),
    # ── COMPLEMENT BLOOM — dark TINTED base, flash blooms toward its complement ──
    dict(
        id="mshcb_oilslick_copper",
        seed_off=_SEED_BASE + 5,
        base_dark=(0.014, 0.026, 0.026),
        reveals=[
            ((0.95, 0.62, 0.28), "u", 0.88),
            ((0.55, 0.30, 0.95), "v", 0.58),
            ((0.18, 0.86, 0.80), "diag_a", 0.62),
        ],
        spec_kw=_GLOSS,
        desc=(
            "MONEY SHOKK Oilslick Copper — dark teal-black body blooms warm "
            "copper (its complement) plus violet/teal echoes — petroleum-on-water "
            "shimmer. Complement-bloom mechanism on a tinted-dark base."
        ),
    ),
    # ── METALLIC SAME-HUE — dark metal base + buried brighter same hue (liquid metal) ──
    dict(
        id="mshcb_liquid_bronze",
        seed_off=_SEED_BASE + 6,
        base_dark=(0.050, 0.035, 0.018),
        reveals=[
            ((0.90, 0.66, 0.24), "u", 0.95),
            ((1.00, 0.82, 0.35), "v", 0.92),
            ((0.72, 0.48, 0.16), "diag_a", 0.85),
        ],
        spec_kw=_METAL,
        desc=(
            "MONEY SHOKK Liquid Bronze — dark bronze metal body intensifies to "
            "bright liquid bronze on the flash. Metallic same-hue mechanism: "
            "high metal floor (m_lo 34) keeps the body reading as metal, not paint."
        ),
    ),
    dict(
        id="mshcb_gunmetal_violet",
        seed_off=_SEED_BASE + 7,
        base_dark=(0.030, 0.030, 0.038),
        reveals=[
            ((0.55, 0.28, 0.95), "u", 0.95),
            ((0.70, 0.45, 0.99), "v", 0.90),
            ((0.38, 0.18, 0.85), "diag_a", 0.82),
        ],
        spec_kw=dict(m_hi=249, m_lo=30, r_hi=11, r_lo=140, cc_hi=17, cc_lo=138),
        desc=(
            "MONEY SHOKK Gunmetal Violet — gunmetal body flashes electric violet "
            "liquid metal on curves. Metallic same-hue on a neutral-dark base."
        ),
    ),
]


MONEY_SHOKK_CLAUDE_BLACKOUT_BASE_REGISTRY: dict[str, dict] = {}
for _row in _MSHCB_ROWS:
    _fid = _row["id"]
    _paint, _spec = _make_blackout(
        finish_id=_fid,
        seed_off=_row["seed_off"],
        base_dark=_row["base_dark"],
        reveals=_row["reveals"],
        spec_kw=_row["spec_kw"],
        desc=_row["desc"],
    )
    MONEY_SHOKK_CLAUDE_BLACKOUT_BASE_REGISTRY[_fid] = {
        "base_spec_fn": _spec,
        "M": 210,
        "R": 35,
        "CC": 40,
        "paint_fn": _paint,
        "desc": _row["desc"],
    }

assert len(MONEY_SHOKK_CLAUDE_BLACKOUT_BASE_REGISTRY) == 8
