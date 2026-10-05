"""
engine/paint_v2/money_shokk_claude.py — ★ MONEY SHOKK (Claude bake-off entry)
=============================================================================
Claude Opus 4.7 entry in the 2026-05-27 four-way MONEY SHOKK bake-off
(Claude vs. Cursor Composer vs. CODEX vs. Gemini 3.5 Flash / Antigravity).

V2 (2026-05-28) — rebuilt the 7 owner-flagged REBUILD finishes after the
V1 ratings. Two doctrines came out of the owner's 40-finish read:

  GATE 1 — the base must LAND blue/indigo for a BRIGHT-base finish, because
  the iRacing sun highlight is warm gold-white; only a cool base reads the
  highlight as a distinct second color. Warm/green bright bases mush
  ("green on green", "red on red").

  GATE 2 — for a bright base, the overlay roughness ceiling decides glow vs.
  white-smear. Glossy overlays (R-ceiling ≤193: rising_sun_prismwave,
  seigaiha_chrome, jellyshock_drift, hornet_swarm_static) throw the tight
  fast Fresnel "glow"; matte overlays (R-ceiling ≥234) smear to white.

  CONSEQUENCE — warm + green colors (bronze, gold, orange, ember, emerald)
  CANNOT pop on a bright base under a warm sun. To deliver them you need the
  DARK BURIED-COLOR route (COLORSHOXX doctrine, docs/COLORSHOXX_ANGLE_REVEAL.md):
  a near-black base with buried pigments revealed by a glossy directional spec
  gate. The reveal color is the buried PIGMENT, decoupled from sun warmth —
  so any color works.

This V2 set is therefore split (owner request 2026-05-28: more color
diversity + a few dark bases; warm palette = orange/copper/ember):
  * 4 DARK buried-color finishes — orange / copper / amber / ember burning
    through black (reuse engine/paint_v2/structural_color COLORSHOXX helpers).
  * 3 COOL bright-base jewel tones — violet / magenta / purple (spread so the
    lineup is not all blue).
  * 3 KEEP finishes untouched from V1 (owner KEEP: oxblood_seigaiha 7,
    amber_panther 7, copper_jubilee 6).

Bright plumbing borrowed from money_shokk.py (Composer) so the contest stays
recipe-vs-recipe. Dark plumbing borrowed from structural_color.py so the dark
finishes ride proven COLORSHOXX angle-reveal code.

See docs/COLOR_CHANGE_BREAKTHROUGH.html (Claude post-mortem) for the full
gate analysis and the per-finish V1→V2 rationale.
"""
from __future__ import annotations

import numpy as np

from engine.core import multi_scale_noise
from engine.paint_v2.money_shokk import _make_money_shokk, _ms_decorrelate_depth

__all__ = ["MONEY_SHOKK_CLAUDE_BASE_REGISTRY"]

_SEED_BASE = 9750

# Fixed gate seed. The renderer passes paint_fn the raw `seed` but spec_fn
# `seed + abs(hash(base_id)) % 10000` (see engine/compose.py). For the buried
# colour in the paint to land exactly where the spec flashes, both gates must be
# driven from the SAME seed — so the dark route ignores the runtime seed and
# derives its gate from this fixed constant + the per-finish offset. Flagship
# finishes are deterministic anyway, so losing per-car seed variation is fine.
_GATE_SEED = 4242


def _shape2(shape):
    return tuple(shape[:2]) if len(shape) > 2 else tuple(shape)


def _msc(h, w, scales, seed, weights=(0.5, 0.3, 0.2)):
    """multi_scale_noise normalised to 0–1."""
    n = multi_scale_noise((h, w), list(scales), list(weights)[: len(scales)], int(seed))
    return ((np.asarray(n, dtype=np.float32) + 1.0) * 0.5).astype(np.float32)


_DARK_CACHE: dict = {}


def _dark_layers(h, w, seed_off, reveals, feat_px):
    """All fields the dark route needs, on ONE fixed seed so paint & spec align:

      * ``ember``  — organic, mostly-black buried-colour bloom (soft irregular
        patches, axis-biased) that both the paint colour and the spec activity
        ride on, so the burn lights exactly where the colour is.
      * ``spark``  — sparse white-hot spark field.
      * ``flake / grain / coat`` — THREE INDEPENDENT designs (different seeds and
        spatial scales) that drive M, R and CC separately. This is the owner's
        2026-05-28 note made literal: each spec channel is its own drawing, so
        the combined spec map carries hundreds of distinct (M,R,CC) microstates
        and different ember pixels glint at different angles — the colour
        *breathes/moves* on the truck instead of every pixel being one material
        at a different brightness (the flat V2 spec the owner found underwhelming,
        measured decorr 0.0 / 17 colours; prismwave the 10 was 0.27 / 110).
    """
    key = (int(seed_off), int(h), int(w), round(float(feat_px), 2), len(reveals))
    cached = _DARK_CACHE.get(key)
    if cached is not None:
        return cached
    gs = _GATE_SEED + int(seed_off)
    s = max(6, int(feat_px))
    fine = _msc(h, w, [3, 6, 12], gs + 11)
    spark = np.clip((fine - 0.74) * 4.5, 0.0, 1.0).astype(np.float32)
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    ember = np.zeros((h, w), dtype=np.float32)
    for i, (_rgb, axis, strength) in enumerate(reveals):
        patch = _msc(h, w, [s, s * 2, max(3, s // 2)], gs + i * 97 + 5)
        if axis == "u":
            bias = np.broadcast_to(xs, (h, w))
        elif axis == "v":
            bias = np.broadcast_to(ys, (h, w))
        elif axis == "diag_a":
            bias = (xs + ys) * 0.5
        else:
            bias = (xs - ys + 1.0) * 0.5
        patch = patch * (0.45 + 0.55 * bias)
        amt = np.clip((patch - 0.42) * 2.6, 0.0, 1.0)
        amt = np.clip(amt * (0.6 + 0.4 * fine) + spark * 0.55, 0.0, 1.0) * float(strength)
        ember = np.maximum(ember, amt)
    ember = np.clip(ember, 0.0, 1.0).astype(np.float32)
    flake = _msc(h, w, [2, 4, 8], gs + 401)        # fine metallic flake -> M
    grain = _msc(h, w, [5, 11, 21], gs + 733)      # roughness grain     -> R  (independent)
    coat = _msc(h, w, [9, 19, 40], gs + 1217)      # clearcoat bloom     -> CC (independent)
    out = (ember, spark, flake, grain, coat)
    if len(_DARK_CACHE) > 12:
        _DARK_CACHE.clear()
    _DARK_CACHE[key] = out
    return out


def _make_money_shokk_dark(
    finish_id: str,
    seed_off: int,
    base_dark,
    reveals,
    bloom_freq: float = 16.0,
    desc: str = "",
):
    """Dark buried-colour MONEY SHOKK finish — near-black body, buried warm
    pigments bloom through, and M/R/CC each carry an INDEPENDENT fine design so
    the combined spec map shows hundreds of distinct microstates (the owner's
    "hundreds of shades" = the surface that breathes on the truck). The reveal
    colour is the buried pigment, decoupled from the warm sun, so any colour
    works. Paint and spec share a fixed seed so the burn lights where the colour
    is, while each channel's own design decides which ember pixels glint at which
    angle."""
    base_dark = np.asarray(base_dark, dtype=np.float32).reshape(1, 1, 3)
    # 3-stop ember gradient: black -> deep tone -> hot tone (by intensity).
    c0 = np.asarray(reveals[0][0], dtype=np.float32)
    c1 = np.asarray(reveals[-1][0], dtype=np.float32)
    lum0 = float(0.21 * c0[0] + 0.72 * c0[1] + 0.07 * c0[2])
    lum1 = float(0.21 * c1[0] + 0.72 * c1[1] + 0.07 * c1[2])
    rgb_lo, rgb_hi = (c0, c1) if lum0 <= lum1 else (c1, c0)
    rgb_lo = rgb_lo.reshape(1, 1, 3)
    rgb_hi = rgb_hi.reshape(1, 1, 3)
    hot = np.asarray((1.0, 0.86, 0.58), dtype=np.float32).reshape(1, 1, 3)  # white-hot spark core

    def paint_fn(paint, shape, mask, seed, pm, bb):
        del seed, bb
        if paint.ndim == 3 and paint.shape[2] > 3:
            paint = paint[:, :, :3].copy()
        h, w = _shape2(shape)
        m3 = np.asarray(mask, dtype=np.float32)
        m3 = m3[:, :, np.newaxis] if m3.ndim == 2 else m3
        bl = float(np.clip(pm * 0.94, 0.0, 1.0))
        ember, spark, _flake, _grain, _coat = _dark_layers(h, w, seed_off, reveals, bloom_freq)
        t = ember[:, :, np.newaxis]
        lo_mix = np.clip(t * 2.0, 0.0, 1.0)           # black -> deep tone over t in [0,0.5]
        hi_mix = np.clip((t - 0.5) * 2.0, 0.0, 1.0)   # deep -> hot tone over t in [0.5,1]
        color = np.broadcast_to(base_dark, (h, w, 3)) * (1.0 - lo_mix) + rgb_lo * lo_mix
        color = color * (1.0 - hi_mix) + rgb_hi * hi_mix
        sp = spark[:, :, np.newaxis]
        color = np.clip(color * (1.0 - sp * 0.55) + hot * sp * 0.55, 0.0, 1.0)  # white-hot cores
        ch3 = paint[:, :, :3]
        ch3[:] = ch3 * (1.0 - m3 * bl) + color * m3 * bl
        return np.clip(paint, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, seed, sm, base_m, base_r):
        del base_m, base_r
        h, w = _shape2(shape)
        ember, spark, flake, grain, coat = _dark_layers(h, w, seed_off, reveals, bloom_freq)
        sm = float(sm)
        # Each channel = its OWN independent design, but the rich variation is
        # GATED toward the ember (fire) so the spec design follows the colour:
        # dark body stays calm with occasional sparks, while the fire carries the
        # decorrelated M/R/CC variation. flake/grain/coat use different seeds +
        # scales => hundreds of distinct (M,R,CC) microstates inside the fire, and
        # because R (gloss) is independent of M, neighbouring fire pixels flash vs
        # stay matte — that is the "moving fire" shimmer the owner is after.
        gate = 0.22 + 0.78 * ember
        M = 20.0 + ember * 55.0 + flake * 155.0 * sm * gate + spark * 65.0
        R = 58.0 + grain * 160.0 * sm * gate - ember * 22.0
        CC = 28.0 + coat * 155.0 * sm * gate + ember * 48.0
        # 2026-06-20 rework: keep the fire reveal (M) but decorrelate R/Cc + add
        # fake-3D relief so neighbouring fire pixels flash vs stay matte (shared
        # ember gate had re-correlated 4/10 to |corr|>0.85).
        return _ms_decorrelate_depth(
            np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32),
            int(seed) + seed_off, seed_off)

    paint_fn.__name__ = f"paint_{finish_id}"
    paint_fn.__doc__ = desc
    spec_fn.__name__ = f"spec_{finish_id}"
    spec_fn.__doc__ = desc
    return paint_fn, spec_fn


_MSHC_ROWS = [
    # ── DARK buried-colour route (orange / copper / amber / ember) ──────────
    dict(
        id="mshc_tigerblood_voltage",
        kind="dark",
        seed_off=_SEED_BASE,
        base_dark=(0.035, 0.022, 0.018),
        reveals=[
            ((1.00, 0.46, 0.10), "u", 1.15),
            ((0.92, 0.20, 0.05), "diag_a", 0.90),
        ],
        bloom_freq=30.0,
        desc=(
            "MONEY SHOKK Tigerblood Ember (V2 DARK) — near-black body, molten "
            "ORANGE → ember-red tiger burn erupting on curved panels at glancing "
            "sun. V1 owner 6/REBUILD: bright lime base only flashed white. V2: "
            "warm colour cannot pop on a bright base under a warm sun, so this is "
            "rebuilt as a COLORSHOXX dark buried-colour reveal — the reveal hue is "
            "the buried orange pigment, not the sun. Owner palette pick: orange/ember."
        ),
    ),
    dict(
        id="mshc_emerald_sharkbite",
        kind="dark",
        seed_off=_SEED_BASE + 2,
        base_dark=(0.028, 0.024, 0.022),
        reveals=[
            ((0.82, 0.44, 0.18), "v", 1.30),
            ((0.98, 0.64, 0.28), "diag_b", 1.05),
        ],
        bloom_freq=26.0,
        desc=(
            "MONEY SHOKK Copper Sharkbite (V2 DARK) — near-black body, COPPER → "
            "bright copper-gold sharkskin burn on a v/diagonal gate. V1 owner "
            "5/REBUILD: seafoam base landed red, 'doesn't pop'. V2: rebuilt dark "
            "so a warm metal can read as a true second colour. (ID keeps the "
            "emerald slug; display is Copper Sharkbite per owner orange/copper pick.)"
        ),
    ),
    dict(
        id="mshc_canary_widow_redux",
        kind="dark",
        seed_off=_SEED_BASE + 8,
        base_dark=(0.032, 0.026, 0.016),
        reveals=[
            ((0.98, 0.66, 0.16), "u", 1.10),
            ((0.85, 0.46, 0.14), "v", 0.80),
        ],
        bloom_freq=34.0,
        desc=(
            "MONEY SHOKK Amber Widow (V2 DARK) — near-black body, AMBER-GOLD → "
            "warm copper widow-web burn. V1 owner 2/REBUILD: 'very weak, dull, "
            "lifeless' — canary +63° landed green on a bright base. V2: canary's "
            "yellow identity now lives as buried amber-gold over black, which a "
            "bright base physically cannot do. Owner palette pick: gold/copper edge."
        ),
    ),
    dict(
        id="mshc_rosethorn_bonsai",
        kind="dark",
        seed_off=_SEED_BASE + 9,
        base_dark=(0.036, 0.018, 0.018),
        reveals=[
            ((0.95, 0.30, 0.08), "diag_a", 1.10),
            ((1.00, 0.52, 0.16), "diag_b", 0.85),
        ],
        bloom_freq=22.0,
        desc=(
            "MONEY SHOKK Ember Rosethorn (V2 DARK) — near-black body, deep EMBER "
            "red-orange → hot-orange thorn burn on crossed diagonals. V1 owner "
            "3/REBUILD: neon-ice −52° landed green with the worst (matte, no-gloss) "
            "overlay in batch. V2: rebuilt dark; ember is the buried pigment so the "
            "fiery second colour survives the warm sun. Owner palette pick: ember."
        ),
    ),
    # ── COOL bright-base jewel tones (spread, not all blue) ─────────────────
    dict(
        id="mshc_violet_kyoto",
        seed_off=_SEED_BASE + 4,
        pf_id="pf_bright_cerulean_pop",
        spec_id="seigaiha_chrome",
        hue_deg=72.0,
        spec_scale=0.36,
        sat_adj=8.0,
        bri_adj=6.0,
        desc=(
            "MONEY SHOKK Violet Kyoto (V2 COOL) — cerulean rotated +72° lands "
            "VIOLET (~0.78), a cool jewel that pops pink/gold against the warm sun. "
            "V1 owner 4/REBUILD: +85° overshot to magenta then kyoto_filigree "
            "(R-ceiling 245) washed it white. V2 fix: violet landing + seigaiha_chrome "
            "(R-ceiling 170, glossiest in batch) for a hard chrome-wave flash."
        ),
    ),
    dict(
        id="mshc_acid_hornet",
        seed_off=_SEED_BASE + 5,
        pf_id="pf_bright_magenta_arc",
        spec_id="hornet_swarm_static",
        hue_deg=6.0,
        spec_scale=0.34,
        sat_adj=10.0,
        bri_adj=7.0,
        desc=(
            "MONEY SHOKK Magenta Hornet (V2 COOL) — magenta_arc held near its "
            "native MAGENTA (~0.90), which two-tones to gold/peach under the warm "
            "highlight. V1 owner 3/REBUILD: hyperpink base read pale across two "
            "agents. V2 fix: richer magenta_arc base + hornet_swarm_static "
            "(R-ceiling 193 glossy), scale opened 0.30→0.34×."
        ),
    ),
    dict(
        id="mshc_oni_orchid_glass",
        seed_off=_SEED_BASE + 6,
        pf_id="pf_bright_orchid_pulse",
        spec_id="jellyshock_drift",
        hue_deg=8.0,
        spec_scale=0.36,
        sat_adj=8.0,
        bri_adj=7.0,
        desc=(
            "MONEY SHOKK Oni Orchid (V2 COOL) — orchid held near its native "
            "ORCHID-MAGENTA (~0.83 / ~300°), distinct from the violet and "
            "blue-violet finishes; reveals pink/gold under glancing sun. V1 owner "
            "3/REBUILD: +148° landed GREEN ('green on green no pop') with a matte "
            "overlay. V2 fix: orchid-magenta landing + jellyshock_drift "
            "(R-ceiling 172) glossy glow."
        ),
    ),
    # ── KEEP finishes — untouched from V1 (owner KEEP) ──────────────────────
    dict(
        id="mshc_oxblood_seigaiha",
        seed_off=_SEED_BASE + 1,
        pf_id="pf_bright_magenta_arc",
        spec_id="seigaiha_chrome",
        hue_deg=-158.0,
        spec_scale=0.36,
        sat_adj=0.0,
        bri_adj=4.0,
        desc=(
            "MONEY SHOKK Oxblood Seigaiha — magenta → sea-green wave body with "
            "chrome crest peaks. M_range 95–250 (tightest in batch) drives "
            "hard-edge wave reveal under direct sun. [V1 KEEP 7 — untouched.]"
        ),
    ),
    dict(
        id="mshc_amber_panther",
        seed_off=_SEED_BASE + 3,
        pf_id="pf_bright_peach_fizz",
        spec_id="panther_shadow_claw",
        hue_deg=172.0,
        spec_scale=0.41,
        sat_adj=0.0,
        bri_adj=6.0,
        desc=(
            "MONEY SHOKK Amber Panther — peach → deep teal-night body, amber "
            "pearl glints catch on curve. Modest channel stds (32/33/33) — "
            "tests whether the recipe survives without channel extremity. "
            "[V1 KEEP 7 — untouched.]"
        ),
    ),
    dict(
        id="mshc_copper_jubilee",
        seed_off=_SEED_BASE + 7,
        pf_id="pf_bright_solar_daffodil",
        spec_id="root_doctor_copper",
        hue_deg=-140.0,
        spec_scale=0.43,
        sat_adj=0.0,
        bri_adj=6.0,
        desc=(
            "MONEY SHOKK Copper Jubilee — daffodil → indigo body with warm "
            "copper voodoo-root reveal. Looser 0.43× scale + warm overlay "
            "reference. [V1 KEEP 6 — untouched.]"
        ),
    ),
]


MONEY_SHOKK_CLAUDE_BASE_REGISTRY: dict[str, dict] = {}
for _row in _MSHC_ROWS:
    _fid = _row["id"]
    _cfg = {k: v for k, v in _row.items() if k != "id"}
    _cfg["finish_id"] = _fid
    if _cfg.pop("kind", "bright") == "dark":
        _paint, _spec = _make_money_shokk_dark(**_cfg)
    else:
        _paint, _spec = _make_money_shokk(**_cfg)
    MONEY_SHOKK_CLAUDE_BASE_REGISTRY[_fid] = {
        "base_spec_fn": _spec,
        "M": 180,
        "R": 80,
        "CC": 60,
        "paint_fn": _paint,
        "desc": _row["desc"],
    }

assert len(MONEY_SHOKK_CLAUDE_BASE_REGISTRY) == 10
