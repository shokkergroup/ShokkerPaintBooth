"""
wild_spec_lab.py — WILD, x2.0-AWARE, ANGLE-REVEAL spec rebuild for the SHOKK
SERIES + EXTREME & EXPERIMENTAL base finishes.

WHY THIS EXISTS
---------------
The app-default spec intensity scale is x2.0 (engine/core.py:881
``_INTENSITY_SCALE['spec'] = 2.0``). At render time the *primary base spec*
path (engine/compose.py:2487) passes ``_sm_base = sm * base_spec_strength``
(≈2.0 at app default) straight into each base's ``base_spec_fn`` and uses the
returned (M, R, CC) DIRECTLY — there is NO external multiply. So the spec_fn
itself fully controls how sm is applied.

Most existing SHOKK specs scale their variation by ``* sm`` internally
(``m_lo + field*(m_hi-m_lo)*sm + flash*58*sm``). At sm=2.0 that pins the
metallic channel at ~255 for most finishes, so they all look identical even
though they are algorithmically distinct.

THE x2.0-AWARE FIX
------------------
Every generated spec here is built on a FIXED [0,255] design anchored at a mid
value, and ``sm`` is used only as a damped *contrast-around-the-anchor* knob:

    contrast = 1.0 + (sm - 1.0) * SM_CONTRAST_GAIN          # SM_CONTRAST_GAIN=0.42
    M = m_anchor + (m_field - 0.5) * m_span * contrast

At sm=2.0 contrast≈1.42 (NOT 2.0+), so the channel stays centered and the
post-sm values land in a varied mid range (~30–220) instead of clipping at
255. This recovers per-finish variety AND honours the x2.0 default.

ANGLE-REVEAL MECHANISM
----------------------
Each finish marries:
  * a directional reveal field (``_cx_directional_mask`` on a per-finish axis +
    freq) so different pan angles light up different buried zones,
  * a buried pin gate + fine spec pins (``_cx_buried_reveal_gate`` /
    ``_cx_fine_spec_pins``) — the 8–32px metallic glints that *trigger* the
    flip at specular angles,
  * a per-finish surface field (``_cx_fine_field`` + ``_cx_ultra_micro``).

Two reveal axes are blended with opposing weights so panning U vs V swaps which
zone is bright (sheen flip). For finishes whose PAINT already carries dual hues
(chameleon, color_flip_wrap, pagani_tricolore, holographic_base, prismatic) the
spec's angle-keyed sheen rides the paint's hue flip → true colour flips
(purple<->yellow, pink<->green). For mono-colour paints the spec delivers a
dramatic angle-dependent metallic/roughness/sheen flip.

SAFETY (owner ships the Alpha today)
------------------------------------
* NON-DESTRUCTIVE: we only OVERRIDE each finish's ``base_spec_fn`` key. The
  ``paint_fn`` (colour identity — mercury stays silver) is never touched.
* Each override is wrapped so ANY error inside the new spec_fn falls back to the
  finish's ORIGINAL base_spec_fn (or the registry's static M/R/CC) — no finish
  can crash a render.
* Behind a module flag ``WILD_SPEC_ENABLED``. Flip to False to disable wholesale
  without touching the wiring.

CONTRACT
--------
base_spec_fn(shape, seed, sm, base_m, base_r) -> (M, R, CC)
  shape : (h, w[, c]) — only h, w are used
  seed  : int (deterministic per render)
  sm    : float spec multiplier (≈2.0 at app default) — used as damped contrast
  base_m, base_r : float registry scalars (advisory only; we do NOT trust high
                   base_m like mercury's 255 to avoid re-clipping)
  returns 3 float32 (h, w) arrays clipped M[0,255], R[15,255], CC[16,255].
"""

import numpy as np

try:
    import cv2  # used for upscale of the downscaled work field
    _HAVE_CV2 = True
except Exception:  # pragma: no cover - cv2 is always present in this app
    _HAVE_CV2 = False

from engine.paint_v2.structural_color import (
    _cx_directional_mask,
    _cx_fine_spec_pins,
    _cx_buried_reveal_gate,
    _cx_ultra_micro,
    _cx_fine_field,
    _cx_hash01,
    _cx_tri_wave,
    _cx_xy,
)

# ── Master switch ──────────────────────────────────────────────────────────
WILD_SPEC_ENABLED = True

# Damping factor for how much sm boosts contrast around the mid-anchor.
# sm=2.0 -> contrast = 1 + (2-1)*0.42 = 1.42 (NOT 2.0+). This is the heart of
# the x2.0-awareness: variation widens with sm but never runs to 255.
SM_CONTRAST_GAIN = 0.42

# Work resolution cap for the angle fields (perf; upscaled to canvas after).
_WILD_WORK_MAX = 512


# ═══════════════════════════════════════════════════════════════════════════
# CONFIG — one UNIQUE entry per finish.
#
# Fields (all distinct per finish so no two read alike):
#   so          : seed_off — gates pin lattice + decorrelates fields (UNIQUE).
#   axis_a/b    : the two reveal axes that swap on pan ("u","v","diag_a","diag_b").
#   wa/wb       : opposing weights for axis_a / axis_b (drives the flip strength).
#   freq        : directional mask frequency (band density of the reveal).
#   pin_d       : pin density (0.004–0.013) — coarse vs fine glint sprinkle.
#   pin_l       : pin layers (3–7) — depth of the buried lattice.
#   m_anchor    : metallic mid-anchor (the centre the channel breathes around).
#   m_span      : metallic peak-to-peak swing (the angle-flip amplitude).
#   r_anchor    : roughness mid-anchor.
#   r_span      : roughness swing (negatively correlated to flash = shiny on flip).
#   cc_anchor   : clearcoat mid-anchor.
#   cc_span     : clearcoat swing.
#   flip        : sheen behaviour — "sheen" (default), "chrome" (mirror flips),
#                 "matte" (void/absorptive, tiny metallic), "spectral"
#                 (rainbow micro-grooves), "thermal" (hot/cool banding).
#   note        : the intended look (purple<->yellow, pink<->green, etc.).
# ═══════════════════════════════════════════════════════════════════════════
CONFIG = {
    # ── SHOKK SERIES (33) ──────────────────────────────────────────────────
    "burnt_headers":   dict(so=7301, axis_a="u",      axis_b="diag_a", wa=1.0, wb=0.7,  freq=58.0, pin_d=0.0072, pin_l=5,
                            m_anchor=128, m_span=150, r_anchor=70,  r_span=70,  cc_anchor=70,  cc_span=58,  flip="thermal",
                            note="exhaust gold<->blue oxide heat banding"),
    "electric_ice":    dict(so=7302, axis_a="v",      axis_b="u",     wa=1.0, wb=0.62, freq=66.0, pin_d=0.0090, pin_l=6,
                            m_anchor=120, m_span=140, r_anchor=46,  r_span=58,  cc_anchor=60,  cc_span=70,  flip="chrome",
                            note="icy cyan<->white frost glints"),
    "mercury":         dict(so=7303, axis_a="diag_a", axis_b="diag_b",wa=1.0, wb=0.85, freq=44.0, pin_d=0.0060, pin_l=4,
                            m_anchor=140, m_span=160, r_anchor=34,  r_span=46,  cc_anchor=48,  cc_span=44,  flip="chrome",
                            note="liquid silver pooling mirror flow (stays silver)"),
    "plasma_metal":    dict(so=7304, axis_a="u",      axis_b="v",     wa=0.9, wb=1.0,  freq=72.0, pin_d=0.0100, pin_l=6,
                            m_anchor=126, m_span=148, r_anchor=58,  r_span=64,  cc_anchor=58,  cc_span=60,  flip="sheen",
                            note="phase-shift liquid smart-metal magenta<->teal"),
    "shokk_blood":     dict(so=7305, axis_a="u",      axis_b="diag_b",wa=1.0, wb=0.66, freq=54.0, pin_d=0.0078, pin_l=5,
                            m_anchor=118, m_span=146, r_anchor=66,  r_span=66,  cc_anchor=56,  cc_span=52,  flip="sheen",
                            note="arterial crimson<->dark micro-shift edges"),
    "shokk_pulse":     dict(so=7306, axis_a="v",      axis_b="u",     wa=1.0, wb=0.74, freq=78.0, pin_d=0.0110, pin_l=6,
                            m_anchor=132, m_span=150, r_anchor=50,  r_span=60,  cc_anchor=58,  cc_span=66,  flip="sheen",
                            note="hot-pink<->electric-blue pulse wave (PINK<->BLUE)"),
    "shokk_static":    dict(so=7307, axis_a="diag_a", axis_b="diag_b",wa=1.0, wb=0.8,  freq=88.0, pin_d=0.0128, pin_l=7,
                            m_anchor=110, m_span=150, r_anchor=78,  r_span=78,  cc_anchor=54,  cc_span=50,  flip="sheen",
                            note="crackling static interference blue-gray hiss"),
    "shokk_venom":     dict(so=7308, axis_a="u",      axis_b="v",     wa=1.0, wb=0.7,  freq=62.0, pin_d=0.0066, pin_l=5,
                            m_anchor=96,  m_span=128, r_anchor=72,  r_span=70,  cc_anchor=52,  cc_span=48,  flip="sheen",
                            note="TOXIC GREEN<->BLACK-PURPLE venom flip (GREEN<->PURPLE)"),
    "shokk_void":      dict(so=7309, axis_a="diag_b", axis_b="u",     wa=1.0, wb=0.5,  freq=40.0, pin_d=0.0048, pin_l=4,
                            m_anchor=34,  m_span=78,  r_anchor=176, r_span=72,  cc_anchor=150, cc_span=80,  flip="matte",
                            note="near-vantablack absorption, faint buried edge shimmer"),
    "volcanic":        dict(so=7310, axis_a="u",      axis_b="diag_a",wa=1.0, wb=0.62, freq=50.0, pin_d=0.0070, pin_l=5,
                            m_anchor=86,  m_span=120, r_anchor=150, r_span=86,  cc_anchor=80,  cc_span=64,  flip="thermal",
                            note="cooled ash crust with molten ember crack reveal"),
    "shokk_flux":      dict(so=7311, axis_a="v",      axis_b="diag_a",wa=1.0, wb=0.78, freq=70.0, pin_d=0.0092, pin_l=6,
                            m_anchor=124, m_span=152, r_anchor=52,  r_span=60,  cc_anchor=70,  cc_span=74,  flip="spectral",
                            note="thin-film interference wavelength sweep"),
    "shokk_phase":     dict(so=7312, axis_a="diag_a", axis_b="v",     wa=1.0, wb=0.7,  freq=64.0, pin_d=0.0084, pin_l=5,
                            m_anchor=104, m_span=158, r_anchor=58,  r_span=70,  cc_anchor=50,  cc_span=56,  flip="sheen",
                            note="liquid-crystal domains M=void..mirror per cell"),
    "shokk_dual":      dict(so=7313, axis_a="u",      axis_b="v",     wa=1.0, wb=1.0,  freq=60.0, pin_d=0.0076, pin_l=5,
                            m_anchor=122, m_span=154, r_anchor=64,  r_span=72,  cc_anchor=54,  cc_span=52,  flip="sheen",
                            note="hard binary complementary flip, interlocking cells"),
    "shokk_spectrum":  dict(so=7314, axis_a="u",      axis_b="diag_b",wa=1.0, wb=0.6,  freq=96.0, pin_d=0.0120, pin_l=7,
                            m_anchor=134, m_span=146, r_anchor=60,  r_span=74,  cc_anchor=58,  cc_span=62,  flip="spectral",
                            note="diffraction grating spectral bands"),
    "shokk_aurora":    dict(so=7315, axis_a="v",      axis_b="diag_a",wa=1.0, wb=0.82, freq=46.0, pin_d=0.0062, pin_l=5,
                            m_anchor=118, m_span=140, r_anchor=48,  r_span=56,  cc_anchor=64,  cc_span=70,  flip="spectral",
                            note="atmospheric curtain folds green<->violet"),
    "shokk_helix":     dict(so=7316, axis_a="diag_a", axis_b="diag_b",wa=1.0, wb=0.9,  freq=68.0, pin_d=0.0088, pin_l=6,
                            m_anchor=128, m_span=148, r_anchor=56,  r_span=64,  cc_anchor=66,  cc_span=68,  flip="sheen",
                            note="double-strand spiral, strand dominance swaps"),
    "shokk_catalyst":  dict(so=7317, axis_a="u",      axis_b="diag_a",wa=1.0, wb=0.72, freq=56.0, pin_d=0.0074, pin_l=5,
                            m_anchor=100, m_span=150, r_anchor=70,  r_span=72,  cc_anchor=52,  cc_span=54,  flip="thermal",
                            note="BZ reaction four-phase spiral wavefronts"),
    "shokk_mirage":    dict(so=7318, axis_a="diag_b", axis_b="u",     wa=1.0, wb=0.68, freq=52.0, pin_d=0.0064, pin_l=4,
                            m_anchor=138, m_span=150, r_anchor=42,  r_span=54,  cc_anchor=50,  cc_span=58,  flip="chrome",
                            note="heat-shimmer refraction color displacement"),
    "shokk_polarity":  dict(so=7319, axis_a="u",      axis_b="v",     wa=1.0, wb=0.95, freq=74.0, pin_d=0.0102, pin_l=6,
                            m_anchor=120, m_span=156, r_anchor=60,  r_span=70,  cc_anchor=56,  cc_span=60,  flip="sheen",
                            note="magnetic polarity flip yellow<->purple (PURPLE<->YELLOW)"),
    "shokk_reactor":   dict(so=7320, axis_a="v",      axis_b="diag_b",wa=1.0, wb=0.78, freq=82.0, pin_d=0.0116, pin_l=7,
                            m_anchor=130, m_span=150, r_anchor=52,  r_span=66,  cc_anchor=60,  cc_span=68,  flip="thermal",
                            note="reactor core glow rings, hot center"),
    "shokk_prism":     dict(so=7321, axis_a="diag_a", axis_b="u",     wa=1.0, wb=0.7,  freq=98.0, pin_d=0.0124, pin_l=7,
                            m_anchor=132, m_span=148, r_anchor=58,  r_span=76,  cc_anchor=58,  cc_span=66,  flip="spectral",
                            note="prism shatter full-spectrum dispersion"),
    "shokk_wraith":    dict(so=7322, axis_a="diag_b", axis_b="v",     wa=1.0, wb=0.64, freq=44.0, pin_d=0.0058, pin_l=4,
                            m_anchor=92,  m_span=140, r_anchor=92,  r_span=80,  cc_anchor=54,  cc_span=52,  flip="sheen",
                            note="ghost violet<->steel apparition (VIOLET<->STEEL)"),
    "shokk_tesseract_v2":dict(so=7323, axis_a="u",    axis_b="diag_b",wa=1.0, wb=0.86, freq=90.0, pin_d=0.0108, pin_l=7,
                            m_anchor=116, m_span=158, r_anchor=62,  r_span=72,  cc_anchor=56,  cc_span=58,  flip="sheen",
                            note="4D hypercube faces, impossible coexisting planes"),
    "shokk_fusion_base":dict(so=7324, axis_a="v",     axis_b="u",     wa=1.0, wb=0.7,  freq=76.0, pin_d=0.0098, pin_l=6,
                            m_anchor=112, m_span=150, r_anchor=68,  r_span=74,  cc_anchor=54,  cc_span=56,  flip="thermal",
                            note="tokamak toroid blackbody temperature map"),
    "shokk_rift":      dict(so=7325, axis_a="diag_a", axis_b="diag_b",wa=1.0, wb=0.74, freq=60.0, pin_d=0.0086, pin_l=6,
                            m_anchor=108, m_span=156, r_anchor=66,  r_span=78,  cc_anchor=52,  cc_span=54,  flip="sheen",
                            note="dimensional fracture, mirror-bright crack lightning"),
    "shokk_vortex":    dict(so=7326, axis_a="diag_b", axis_b="diag_a",wa=1.0, wb=0.9,  freq=86.0, pin_d=0.0104, pin_l=6,
                            m_anchor=126, m_span=150, r_anchor=50,  r_span=64,  cc_anchor=66,  cc_span=70,  flip="sheen",
                            note="logarithmic spiral Moire drain shifts with angle"),
    "shokk_surge":     dict(so=7327, axis_a="u",      axis_b="v",     wa=1.0, wb=0.82, freq=80.0, pin_d=0.0112, pin_l=7,
                            m_anchor=118, m_span=152, r_anchor=60,  r_span=70,  cc_anchor=56,  cc_span=60,  flip="sheen",
                            note="standing-wave superposition node flicker"),
    "shokk_cipher":    dict(so=7328, axis_a="v",      axis_b="diag_a",wa=1.0, wb=0.68, freq=92.0, pin_d=0.0118, pin_l=7,
                            m_anchor=104, m_span=150, r_anchor=72,  r_span=76,  cc_anchor=50,  cc_span=52,  flip="sheen",
                            note="encrypted glyph lattice green<->magenta scramble"),
    "shokk_inferno":   dict(so=7329, axis_a="u",      axis_b="diag_a",wa=1.0, wb=0.6,  freq=54.0, pin_d=0.0080, pin_l=5,
                            m_anchor=120, m_span=160, r_anchor=72,  r_span=82,  cc_anchor=62,  cc_span=64,  flip="thermal",
                            note="blackbody crimson<->blue temperature map (CRIMSON<->BLUE)"),
    "shokk_apex":      dict(so=7330, axis_a="diag_a", axis_b="v",     wa=1.0, wb=0.88, freq=100.0,pin_d=0.0122, pin_l=7,
                            m_anchor=134, m_span=150, r_anchor=54,  r_span=70,  cc_anchor=64,  cc_span=72,  flip="spectral",
                            note="crown jewel — every technique stacked"),
    # chameleon REMOVED 2026-06-14: reborn as Candy & Pearl "Orchid Shift Pearl"
    # (engine.paint_v2.candy_pearl_2026). wild_spec must NOT reclaim its base_spec_fn.
    # "chameleon":       dict(so=7331, axis_a="u",      axis_b="v",     wa=1.0, wb=0.92, freq=64.0, pin_d=0.0084, pin_l=6,
    #                         m_anchor=124, m_span=156, r_anchor=58,  r_span=66,  cc_anchor=58,  cc_span=64,  flip="sheen",
    #                         note="dual-tone chameleon — spec sheen rides paint hue flip"),
    "color_flip_wrap": dict(so=7332, axis_a="v",      axis_b="u",     wa=1.0, wb=0.94, freq=58.0, pin_d=0.0070, pin_l=5,
                            m_anchor=118, m_span=150, r_anchor=56,  r_span=62,  cc_anchor=54,  cc_span=58,  flip="sheen",
                            note="dual-colour flip vinyl — sheen keyed to paint flip"),
    "pagani_tricolore":dict(so=7333, axis_a="diag_a", axis_b="diag_b",wa=1.0, wb=0.78, freq=62.0, pin_d=0.0066, pin_l=5,
                            m_anchor=130, m_span=148, r_anchor=44,  r_span=56,  cc_anchor=52,  cc_span=58,  flip="sheen",
                            note="premium tricolore three-tone angle-resolved shift"),

    # ── EXTREME & EXPERIMENTAL (11) ────────────────────────────────────────
    "bioluminescent":  dict(so=7401, axis_a="v",      axis_b="diag_a",wa=1.0, wb=0.7,  freq=48.0, pin_d=0.0090, pin_l=6,
                            m_anchor=70,  m_span=120, r_anchor=64,  r_span=70,  cc_anchor=48,  cc_span=56,  flip="sheen",
                            note="deep-sea organism cyan<->magenta glow pins"),
    "dark_matter":     dict(so=7402, axis_a="diag_b", axis_b="u",     wa=1.0, wb=0.55, freq=42.0, pin_d=0.0052, pin_l=4,
                            m_anchor=40,  m_span=92,  r_anchor=172, r_span=78,  cc_anchor=148, cc_span=84,  flip="matte",
                            note="hidden angle-only reveal in maximum absorption"),
    "holographic_base":dict(so=7403, axis_a="u",      axis_b="v",     wa=1.0, wb=0.96, freq=104.0,pin_d=0.0126, pin_l=7,
                            m_anchor=136, m_span=150, r_anchor=52,  r_span=78,  cc_anchor=60,  cc_span=72,  flip="spectral",
                            note="full prismatic rainbow hologram — strong angle shift"),
    "neutron_star":    dict(so=7404, axis_a="diag_a", axis_b="diag_b",wa=1.0, wb=0.6,  freq=120.0,pin_d=0.0096, pin_l=6,
                            m_anchor=60,  m_span=150, r_anchor=150, r_span=96,  cc_anchor=140, cc_span=96,  flip="thermal",
                            note="void sink + intense orbital accretion ring"),
    "plasma_core":     dict(so=7405, axis_a="v",      axis_b="diag_a",wa=1.0, wb=0.8,  freq=78.0, pin_d=0.0106, pin_l=6,
                            m_anchor=122, m_span=152, r_anchor=54,  r_span=66,  cc_anchor=58,  cc_span=66,  flip="thermal",
                            note="reactor plasma electric purple<->blue core"),
    "quantum_black":   dict(so=7406, axis_a="diag_b", axis_b="v",     wa=1.0, wb=0.5,  freq=38.0, pin_d=0.0046, pin_l=4,
                            m_anchor=30,  m_span=72,  r_anchor=184, r_span=64,  cc_anchor=156, cc_span=74,  flip="matte",
                            note="near-perfect absorption, faint quantum glints"),
    "solar_panel":     dict(so=7407, axis_a="u",      axis_b="diag_b",wa=1.0, wb=0.66, freq=72.0, pin_d=0.0072, pin_l=5,
                            m_anchor=88,  m_span=120, r_anchor=78,  r_span=70,  cc_anchor=50,  cc_span=52,  flip="sheen",
                            note="photovoltaic cell grid gold<->copper sheen flip"),
    "superconductor":  dict(so=7408, axis_a="diag_a", axis_b="u",     wa=1.0, wb=0.62, freq=50.0, pin_d=0.0068, pin_l=5,
                            m_anchor=110, m_span=130, r_anchor=120, r_span=82,  cc_anchor=58,  cc_span=60,  flip="chrome",
                            note="absolute-zero frosted metal micro-ice crystals"),
    "prismatic":       dict(so=7409, axis_a="u",      axis_b="v",     wa=1.0, wb=0.98, freq=112.0,pin_d=0.0130, pin_l=7,
                            m_anchor=138, m_span=150, r_anchor=50,  r_span=80,  cc_anchor=60,  cc_span=74,  flip="spectral",
                            note="over-tuned hologram, impossible prismatic colors"),
    "liquid_obsidian": dict(so=7410, axis_a="diag_b", axis_b="diag_a",wa=1.0, wb=0.86, freq=46.0, pin_d=0.0058, pin_l=4,
                            m_anchor=132, m_span=158, r_anchor=40,  r_span=58,  cc_anchor=48,  cc_span=50,  flip="chrome",
                            note="flowing glass-metal phase boundary, near-zero R"),
    "vantablack":      dict(so=7411, axis_a="v",      axis_b="diag_b",wa=1.0, wb=0.45, freq=36.0, pin_d=0.0042, pin_l=3,
                            m_anchor=24,  m_span=64,  r_anchor=196, r_span=56,  cc_anchor=170, cc_span=66,  flip="matte",
                            note="absolute void, single buried specular whisper"),
}


# ═══════════════════════════════════════════════════════════════════════════
# Core x2.0-aware angle-reveal spec generator.
# ═══════════════════════════════════════════════════════════════════════════
def _wild_work_shape(h, w):
    if max(h, w) <= _WILD_WORK_MAX:
        return h, w
    scale = _WILD_WORK_MAX / float(max(h, w))
    return max(1, int(round(h * scale))), max(1, int(round(w * scale)))


def _wild_upscale(arr, h, w):
    if arr.shape[:2] == (h, w):
        return arr.astype(np.float32, copy=False)
    if _HAVE_CV2:
        return cv2.resize(arr.astype(np.float32), (w, h),
                          interpolation=cv2.INTER_LINEAR).astype(np.float32)
    # numpy-only nearest fallback (cv2 always present in app, this is paranoia)
    yi = (np.linspace(0, arr.shape[0] - 1, h)).astype(np.int32)
    xi = (np.linspace(0, arr.shape[1] - 1, w)).astype(np.int32)
    return arr[yi][:, xi].astype(np.float32)


def make_wild_spec(shape, seed, sm, base_m, base_r, cfg):
    """x2.0-AWARE angle-reveal spec builder.

    Builds M/R/CC on a fixed [0,255] design anchored at per-finish mid values and
    uses ``sm`` only as a damped contrast knob, so post-sm output stays varied in
    the ~30–220 band instead of clipping at 255.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    h, w = int(h), int(w)
    wh, ww = _wild_work_shape(h, w)
    ws = (wh, ww)

    so = int(cfg["so"])
    s = int(seed)

    # damped, x2.0-aware contrast. sm≈2.0 (app default) -> ~1.42, not 2.0+.
    sm_f = float(sm) if sm and sm > 0 else 1.0
    contrast = 1.0 + (sm_f - 1.0) * SM_CONTRAST_GAIN
    contrast = float(np.clip(contrast, 0.55, 1.75))

    # ── directional reveal: two axes that swap on pan (the flip) ──────────
    axis_a = _cx_directional_mask(ws, cfg["axis_a"], s + so, freq=float(cfg["freq"]))
    axis_b = _cx_directional_mask(ws, cfg["axis_b"], s + so + 311, freq=float(cfg["freq"]) * 0.83)
    wa = float(cfg["wa"]); wb = float(cfg["wb"])
    # signed reveal in [-1,1]: +1 = axis_a zone lit, -1 = axis_b zone lit.
    reveal = (axis_a * wa - axis_b * wb) / max(wa + wb, 1e-6)
    reveal = np.clip(reveal, -1.0, 1.0).astype(np.float32)
    reveal01 = (reveal + 1.0) * 0.5  # [0,1]

    # ── buried pin gate + fine glints: the angle TRIGGER ──────────────────
    gate = _cx_buried_reveal_gate(ws, s, so, density=float(cfg["pin_d"]), layers=int(cfg["pin_l"]))
    pins = _cx_fine_spec_pins(ws, s + 331, so, density=float(cfg["pin_d"]) * 1.35,
                              layers=max(int(cfg["pin_l"]), 4))
    glints = np.clip(gate * 0.6 + pins * 0.7, 0.0, 1.0).astype(np.float32)

    # ── per-finish surface field + micro flake ────────────────────────────
    field = _cx_fine_field(ws, s + so)
    micro = _cx_ultra_micro(ws, s + so * 17)

    # flash: where the lit axis + glints coincide -> bright specular pop.
    flash = np.clip(reveal01 * (0.40 + glints * 0.95), 0.0, 1.0).astype(np.float32)

    flip = cfg.get("flip", "sheen")

    # spectral micro-grooves (rainbow dispersion bands) for spectral finishes.
    if flip == "spectral":
        x, y = _cx_xy(ws)
        groove = _cx_tri_wave(x * (float(cfg["freq"]) * 1.6) + y * 7.0 + field * 0.5)
        groove2 = _cx_tri_wave((x - y) * (float(cfg["freq"]) * 1.2) + micro * 0.6)
        spectral = np.clip(groove * 0.6 + groove2 * 0.4, 0.0, 1.0).astype(np.float32)
    else:
        spectral = None

    # ── METALLIC: anchor + signed (field/reveal) swing * damped contrast ──
    m_anchor = float(cfg["m_anchor"]); m_span = float(cfg["m_span"])
    # combine the buried field with the directional reveal so the bright zone
    # moves with pan angle. (field-0.5) gives surface variety; reveal moves it.
    m_drive = (field - 0.5) * 0.55 + reveal * 0.45
    M = m_anchor + m_drive * (m_span * 0.5) * contrast
    M = M + (flash - 0.42) * 46.0 + (glints - 0.30) * 40.0
    if flip == "chrome":
        M = M + (reveal01 - 0.5) * 34.0 + pins * 26.0
    elif flip == "matte":
        # tiny metallic — buried glints are the ONLY bright pixels.
        M = m_anchor + glints * (m_span * 0.85) + flash * 30.0 + (field - 0.5) * 10.0
    elif flip == "thermal":
        # hot zone = high M (molten/mirror), cool = low M.
        M = m_anchor + (reveal) * (m_span * 0.5) * contrast + flash * 38.0 + (field - 0.5) * 22.0
    elif flip == "spectral" and spectral is not None:
        M = M + (spectral - 0.5) * 40.0 * contrast

    # ── ROUGHNESS: inverse of flash (shiny where it flips) ────────────────
    r_anchor = float(cfg["r_anchor"]); r_span = float(cfg["r_span"])
    r_drive = (0.5 - field) * 0.5 - reveal * 0.4
    R = r_anchor + r_drive * (r_span * 0.5) * contrast
    R = R - flash * 30.0 - glints * 26.0 + (micro - 0.5) * 18.0
    if flip == "matte":
        # mostly rough; only pin sites dip toward gloss.
        R = r_anchor - glints * (r_span * 0.6) - flash * 22.0 + (field - 0.5) * 14.0
    elif flip == "chrome":
        R = R - (reveal01 - 0.5) * 22.0 - pins * 20.0
    elif flip == "thermal":
        R = r_anchor - (reveal) * (r_span * 0.5) * contrast - flash * 26.0 + (field - 0.5) * 16.0

    # ── CLEARCOAT: boost on flash + pins (wet pop at flip angle) ──────────
    cc_anchor = float(cfg["cc_anchor"]); cc_span = float(cfg["cc_span"])
    cc_drive = (field - 0.5) * 0.5 + reveal * 0.35
    CC = cc_anchor + cc_drive * (cc_span * 0.5) * contrast
    CC = CC + flash * 34.0 + pins * 28.0 + (micro - 0.5) * 16.0
    if flip == "matte":
        CC = cc_anchor + (field - 0.5) * (cc_span * 0.35) + glints * 24.0
    elif flip == "spectral" and spectral is not None:
        CC = CC + (spectral - 0.5) * 36.0

    # decorrelate adjacent finishes by a faint per-finish hash dither.
    dither = (_cx_hash01(ws, s + so, 909) - 0.5)
    M = M + dither * 8.0
    R = R + dither * 6.0
    CC = CC + dither * 6.0

    M = np.clip(M, 0, 255).astype(np.float32)
    R = np.clip(R, 15, 255).astype(np.float32)
    CC = np.clip(CC, 16, 255).astype(np.float32)

    if ws != (h, w):
        M = _wild_upscale(M, h, w)
        R = _wild_upscale(R, h, w)
        CC = _wild_upscale(CC, h, w)
        M = np.clip(M, 0, 255).astype(np.float32)
        R = np.clip(R, 15, 255).astype(np.float32)
        CC = np.clip(CC, 16, 255).astype(np.float32)

    return M, R, CC


# ── wild-spec-v2 dedicated generator registry ──────────────────────────────
# wild-spec-v2 2026-06-07, owner rejected v1 as lazy (no spec diversity), demands
# many-hue triplet zones. The make_wild_spec template below is now ONLY a
# last-resort fallback. The real generators live in the wild_specs sub-package:
# one DEDICATED spec_<id>(shape, seed, sm, base_m, base_r) per finish, each with
# its OWN algorithm + motif and STRUCTURALLY DIFFERENT M/R/Cc geometry.
#
# _make_wild_spec_fn looks up WILD_SPEC_FNS[finish_id] FIRST and uses it; the v1
# CONFIG template + the original fn + static M/R/CC remain as a 3-level fallback
# chain so no finish can ever crash a render. The lookup is lazy + cached so an
# import error in the sub-package can never break the v1 harness wiring.
_WILD_SPEC_FNS_CACHE = None


def _get_wild_spec_fns():
    """Return the dedicated-generator registry {finish_id: fn} from the
    wild_specs sub-package, or {} if it cannot be imported. Lazy + cached so the
    harness import never depends on the (heavier) generator package and a broken
    sub-package can never abort wiring."""
    global _WILD_SPEC_FNS_CACHE
    if _WILD_SPEC_FNS_CACHE is not None:
        return _WILD_SPEC_FNS_CACHE
    fns = {}
    try:
        from engine.expansions.wild_specs import WILD_SPEC_FNS as _fns
        if isinstance(_fns, dict):
            fns = _fns
    except Exception:
        fns = {}
    _WILD_SPEC_FNS_CACHE = fns
    return fns


def _make_wild_spec_fn(finish_id, cfg, original_fn, base_def):
    """Return a base_spec_fn closure for ``finish_id``.

    PRIMARY (wild-spec-v2): the dedicated per-finish generator
    ``WILD_SPEC_FNS[finish_id]`` from the wild_specs sub-package — its own
    algorithm + motif, with STRUCTURALLY DIFFERENT M/R/Cc geometry.

    FALLBACK CHAIN (so no finish can crash a render):
      1) the v1 make_wild_spec template for this finish's CONFIG entry,
      2) the finish's ORIGINAL base_spec_fn,
      3) flat static M/R/CC from the registry scalars.
    """
    base_M = float(base_def.get("M", 128))
    base_R = float(base_def.get("R", 30))
    base_CC = float(base_def.get("CC", 16))

    def _wild_spec(shape, seed, sm, base_m, base_r):
        # ── PRIMARY: dedicated wild-spec-v2 generator for this finish ─────────
        dedicated = _get_wild_spec_fns().get(finish_id)
        if callable(dedicated):
            try:
                res = dedicated(shape, seed, sm, base_m, base_r)
                if isinstance(res, tuple) and len(res) >= 3:
                    return res[0], res[1], res[2]
                if isinstance(res, np.ndarray) and res.ndim == 3 and res.shape[2] >= 3:
                    return (res[:, :, 0], res[:, :, 1], res[:, :, 2])
                # unexpected shape -> drop through to the fallback chain below.
            except Exception:
                pass  # any error -> fall through to the v1 template / original.
        # ── FALLBACK 1: v1 make_wild_spec template (CONFIG metadata) ──────────
        try:
            return make_wild_spec(shape, seed, sm, base_m, base_r, cfg)
        except Exception:
            # FALLBACK 2: the finish's own ORIGINAL base_spec_fn
            if callable(original_fn):
                try:
                    res = original_fn(shape, seed, sm, base_m, base_r)
                    if isinstance(res, np.ndarray) and res.ndim == 3 and res.shape[2] >= 3:
                        return (res[:, :, 0], res[:, :, 1], res[:, :, 2])
                    return res
                except Exception:
                    pass
            # FALLBACK 3: last-resort flat static M/R/CC from the registry scalars
            h, w = shape[:2] if len(shape) > 2 else shape
            h, w = int(h), int(w)
            M = np.full((h, w), np.clip(base_M, 0, 255), dtype=np.float32)
            R = np.full((h, w), np.clip(base_R, 15, 255), dtype=np.float32)
            CC = np.full((h, w), np.clip(base_CC, 16, 255), dtype=np.float32)
            return M, R, CC

    _wild_spec.__name__ = f"wild_spec_{finish_id}"
    _wild_spec.__qualname__ = _wild_spec.__name__
    _wild_spec.__module__ = __name__
    _wild_spec._wild_spec_lab = True  # marker for diagnostics
    return _wild_spec


def _collect_target_registries(passed_base_registry):
    """Return every distinct base-registry dict that a render might read.

    The engine keeps SEVERAL BASE_REGISTRY objects: the one shokker_engine_v2
    passes here, and the render-authoritative ``engine.registry.BASE_REGISTRY``
    (built independently by ``_build_registries()``). For some finishes the
    per-entry dicts are shared between them, for others they are NOT — so a
    single override on the passed registry misses ~29 of the 44 at render time.
    We override the entry in EVERY registry where it appears, so the render path
    always sees the wild spec regardless of which object it resolves through.
    """
    registries = []
    seen_ids = set()

    def _add(reg):
        if isinstance(reg, dict) and id(reg) not in seen_ids:
            seen_ids.add(id(reg))
            registries.append(reg)

    _add(passed_base_registry)
    # The render path imports BASE_REGISTRY from engine.registry — make that the
    # authority too. Guarded so a missing/circular import can never break us.
    try:
        from engine.registry import BASE_REGISTRY as _render_base_registry
        _add(_render_base_registry)
    except Exception:
        pass
    return registries


def apply_wild_specs(BASE_REGISTRY, MONOLITHIC_REGISTRY=None):
    """Override ONLY the ``base_spec_fn`` of each configured finish with a wild
    x2.0-aware angle-reveal spec. KEEPS paint_fn (colour identity untouched).

    Applies to EVERY base-registry object the render path may read (the passed
    one + ``engine.registry.BASE_REGISTRY``) so no finish is missed. Returns the
    number of finishes wired in the passed registry. Each finish is wrapped in
    its own try/except so one bad entry can never abort the pass, and each
    installed spec_fn additionally falls back to the original at render time.
    """
    if not WILD_SPEC_ENABLED:
        return 0
    registries = _collect_target_registries(BASE_REGISTRY)
    wired = 0
    missing = []
    for finish_id, cfg in CONFIG.items():
        found_anywhere = False
        for reg in registries:
            try:
                base_def = reg.get(finish_id)
                if base_def is None:
                    continue
                # don't double-wrap if this exact entry dict was already wilded
                existing = base_def.get("base_spec_fn")
                if getattr(existing, "_wild_spec_lab", False):
                    found_anywhere = True
                    continue
                new_fn = _make_wild_spec_fn(finish_id, cfg, existing, base_def)
                # NON-DESTRUCTIVE: only the spec key changes; paint_fn untouched.
                base_def["base_spec_fn"] = new_fn
                found_anywhere = True
                if reg is BASE_REGISTRY:
                    wired += 1
            except Exception:
                # never let a single finish/registry abort the pass.
                continue
        if not found_anywhere:
            missing.append(finish_id)
    if missing:
        try:
            print(f"  [Wild Spec] {len(missing)} configured finish(es) not in any BASE_REGISTRY: {missing}")
        except Exception:
            pass
    return wired
