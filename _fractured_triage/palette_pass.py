# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090d 2026-08-02] COLOUR PASS — rewrite the `hues` ladders and
the saturation dials of FROST / NEBULA / TEMPEST in place.

COLOUR ONLY. art_work re-applies each pixel's own luma after the HSV
roundtrip (Lpre/Lpost), so hues/hspan/satboost/gray move NO luma — band,
autocorr, peakiness, shape-fraction, fineness and coverage are all luma
statistics and stay put (measured: satboost 1.00 -> 0.10 moved slate_squall's
band 0.8387 -> 0.8414, i.e. only the tiny amount that channel CLIPPING at
satboost >= 1 was costing).

TWO STRUCTURAL CHANGES:
 1. LADDER SHAPE. The old ladder was [b]*8 + [b+0.06, b-0.06, COMPLEMENT].
    That 11th rung put ~9% of the pixels a third of a turn away from the
    subject (hot magenta in a kelly-green storm, tan-orange in a slate one) and
    at a ~9 px hue cell it reads as electric speckle. Saturation-weighted it
    was carrying ~28% of the colour mass, not 9%. Replaced by 16-rung
    WITHIN-FAMILY ladders: a dominant base (56-62%) with graded NEIGHBOUR
    rungs walking one direction along the subject's own continuum (storm:
    steel -> slate -> navy; ice: aqua -> cyan -> glacier -> shadow; violet
    storm/ice: violet -> blue-violet -> blue). That satisfies the >= 5 hue-bin
    gate with shades of the subject instead of with its complement, and gives
    the owner's "more shades" doctrine 16 levels instead of 3.
    NEBULA keeps its drama: it gets the same 16-rung spine plus TWO accent
    rungs placed on OPPOSITE sides of the base (H-alpha red + reflection blue
    around a violet; OIII teal + H-alpha magenta around a gold), so the
    saturation-weighted circular mean stays on the NAMED hue instead of being
    dragged a tenth of a turn by a single unbalanced accent.
 2. SATURATION. Storm and ice are GREY-WHITE subjects — value contrast, not
    chroma, carries them. Measured satA was 0.69-1.00 (i.e. fully clipped
    candy). Retargeted to ~0.34 (tinted), ~0.46 (storm green, which has to
    stay legibly green) and ~0.19 (the white/silver/snow ids, whose names are
    a SATURATION statement, not a hue one). Floor: satA ~0.16 is where the
    hue-bin gate's S > 38/255 mask starts to empty, so 0.19 keeps margin.
    NEBULA saturation is left exactly as authored.

  python palette_pass.py <frost|nebula|tempest>
"""
import importlib
import re
import sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, ROOT + r"\_fractured_triage")
from colorfix import TARGET  # noqa: E402

# ── LADDER SHAPES: offsets from the base anchor, in turns. 16 rungs, so the
# dominant base owns 9-10/16 of the macro domain and the rest is graded shade.
# round 2: GREEN and VIOLET fan extents pulled in (0.215 -> 0.150,
# -0.170 -> -0.125) — measured `off` (chromatic mass > 0.12 turn from the
# subject hue) was 0.23 on the supercell ids and 0.17 on the violet ones, i.e.
# the far end of the fan had walked out of the family it was shading.
# round 3, driven by the CONTACT SHEET (numbers were green, the eye was not):
#  * ICE — the frost cyans were reading LIME. A symmetric fan around a 0.49
#    anchor puts base-0.055(fan)-0.055(hspan) = 0.38 on the canvas, which is
#    grass. The ice fan is upward-biased (aqua -> cyan -> glacier -> shadow
#    blue, never past teal downward) and runs a tighter 0.042 window.
#  * lichtenberg_crown moved STORM -> VIOLET for the same reason at the other
#    end: a 0.68 anchor + 0.095 fan + 0.055 window reaches 0.83, i.e. MAGENTA.
STORM = [0.0] * 9 + [+0.020, -0.020, +0.042, -0.038, +0.068, -0.055, +0.095]
VIOLET = [0.0] * 9 + [+0.018, -0.022, -0.040, -0.060, -0.082, -0.104, -0.125]
GREEN = [0.0] * 9 + [+0.022, -0.020, +0.048, +0.075, +0.102, +0.126, +0.150]
WHITE = [0.0] * 9 + [+0.020, -0.022, +0.042, -0.042, +0.066, -0.058, +0.090]
ICE = [0.0] * 9 + [+0.022, -0.016, +0.048, -0.030, +0.075, +0.102, +0.130]
NEB = [0.0] * 10 + [+0.030, -0.030, +0.062, -0.058]

HSPAN = {id(ICE): 0.042}
# violet_galaxy keeps the 0.085 window its clipping fix depends on
ID_HSPAN = {"fnb_violet_galaxy": 0.085}

# ── PER-ID: (ladder shape, target mean saturation). Nebula rows carry the two
# BALANCED accent hues instead of a saturation target.
PLAN = {
    # TEMPEST — weather. Round 3: the greens were reading NEON LIME and the
    # violets PINK on the contact sheet, so every tinted storm id now sits at
    # satA 0.30-0.34. Storm green is a MUTED yellow-green sky, not kelly.
    "fte_lichtenberg_crown": (VIOLET, 0.30),
    "fte_steel_downpour": (STORM, 0.34),
    "fte_storm_cell": (GREEN, 0.28),
    "fte_white_arc": (WHITE, 0.19),
    "fte_slate_squall": (STORM, 0.34),
    "fte_green_supercell": (GREEN, 0.28),
    "fte_thunderhead_white": (WHITE, 0.18),
    "fte_slate_vortex": (STORM, 0.34),
    "fte_violet_hail": (VIOLET, 0.32),
    "fte_blue_bolt": (STORM, 0.36),
    "fte_slate_billows": (STORM, 0.34),
    "fte_violet_twister": (VIOLET, 0.26),
    "fte_steel_rain": (STORM, 0.34),
    "fte_green_strike": (GREEN, 0.26),
    "fte_whiteout_hail": (WHITE, 0.18),
    "fte_steel_cyclone": (STORM, 0.34),
    "fte_gustfront_green": (GREEN, 0.26),
    "fte_ball_lightning": (STORM, 0.34),
    "fte_slate_hailfield": (STORM, 0.34),
    "fte_violet_cumulonimbus": (VIOLET, 0.27),
    # FROST — ice. Cyans on the ICE fan (no green reach), violets pulled off
    # pink toward blue-violet.
    "ffr_window_fern": (ICE, 0.32),
    "ffr_cyan_frond": (ICE, 0.34),
    "ffr_glacier_fern": (ICE, 0.32),
    "ffr_violet_rime": (VIOLET, 0.32),
    "ffr_steel_flurry": (STORM, 0.30),
    "ffr_silver_dendrite": (WHITE, 0.19),
    "ffr_diamond_dust": (WHITE, 0.19),
    "ffr_violet_sectored": (VIOLET, 0.32),
    "ffr_cyan_fissure": (ICE, 0.34),
    "ffr_whiteout_rift": (WHITE, 0.18),
    "ffr_violet_chasm": (VIOLET, 0.25),
    "ffr_blue_serac": (STORM, 0.32),
    "ffr_hoarfrost_white": (WHITE, 0.18),
    "ffr_silver_hoar": (WHITE, 0.19),
    "ffr_cyan_frostbloom": (ICE, 0.34),
    "ffr_ice_needles": (WHITE, 0.24),
    "ffr_violet_trapped": (VIOLET, 0.25),
    "ffr_steel_bubbles": (STORM, 0.30),
    "ffr_cyan_veil": (ICE, 0.34),
    "ffr_snowdrift_ice": (WHITE, 0.19),
    # NEBULA — deep space. Round 3 fixed two things the sheet exposed:
    #  (a) NO GREEN. The balanced-accent maths wanted a rung a third of a turn
    #      BELOW a cyan base, which is chartreuse — and it painted lime blocks
    #      across cyan_spiral/cyan_shockwave and olive ones across the golds.
    #      Green is not a nebula colour. Accents now come only from the real
    #      set (H-alpha rose/red, magenta, violet, indigo, cyan/teal, gold),
    #      which for a cyan base means both accents walk UP into blue/violet.
    #  (b) saturation was CLIPPED FLAT at satA 0.99 — fluorescent poster, not
    #      deep space. Retargeted to ~0.80: still the most saturated of the
    #      three modules by far, but unclipped, so value and hue texture
    #      survive (and every gate improved when violet_galaxy did this).
    "fnb_violet_billows": (NEB, (0.930, 0.660)),
    "fnb_magenta_remnant": (NEB, (0.990, 0.785)),
    "fnb_cyan_spiral": (NEB, (0.700, 0.640)),
    "fnb_golden_cluster": (NEB, (0.165, 0.045)),
    "fnb_teal_annulus": (NEB, (0.660, 0.600)),
    "fnb_cyan_drift": (NEB, (0.715, 0.655)),
    "fnb_gilded_shockfront": (NEB, (0.165, 0.045)),
    "fnb_teal_starfield": (NEB, (0.665, 0.605)),
    "fnb_violet_galaxy": (NEB, (0.940, 0.670)),
    "fnb_magenta_rift": (NEB, (0.010, 0.805)),
    "fnb_teal_lagoon": (NEB, (0.655, 0.595)),
    "fnb_violet_annulus": (NEB, (0.950, 0.680)),
    "fnb_magenta_emission": (NEB, (0.985, 0.780)),
    "fnb_cyan_dustlane": (NEB, (0.710, 0.650)),
    "fnb_golden_pinwheel": (NEB, (0.165, 0.045)),
    "fnb_magenta_stardust": (NEB, (0.000, 0.795)),
    "fnb_cyan_shockwave": (NEB, (0.695, 0.635)),
    "fnb_gilded_veil": (NEB, (0.170, 0.050)),
    "fnb_teal_rift": (NEB, (0.655, 0.595)),
    "fnb_violet_starglow": (NEB, (0.930, 0.660)),
}

# gray-dial de-rating of mean saturation, measured on satsweep.py
_G = [(0.00, 1.000), (0.25, 0.790), (0.30, 0.755), (0.35, 0.737),
      (0.38, 0.715), (0.40, 0.700), (0.60, 0.493)]


def gfac(gy):
    for i in range(len(_G) - 1):
        if gy <= _G[i + 1][0]:
            (x0, y0), (x1, y1) = _G[i], _G[i + 1]
            t = (gy - x0) / max(x1 - x0, 1e-9)
            return y0 + (y1 - y0) * t
    return _G[-1][1]


def main():
    mod = sys.argv[1]
    path = ROOT + r"\engine\expansions\fractured_%s_2026.py" % mod
    src = open(path, encoding="utf-8").read()
    M = importlib.import_module("engine.expansions.fractured_%s_2026" % mod)
    K = M.KIT
    n = 0
    for fid in sorted(K.ALL):
        shape, arg = PLAN[fid]
        b = TARGET[fid][0]
        hues = [round((b + o) % 1.0, 4) for o in shape]
        if shape is NEB:
            hues += [round(float(arg[0]), 4), round(float(arg[1]), 4)]
            gy = float(K.ALL[fid].get("kw", {}).get("gray", 0.0))
            sb_new = max(0.06, round((0.80 / gfac(gy) - 0.080) / 0.93, 3))
        elif "--keepsat" in sys.argv:
            sb_new = float(K.ALL[fid].get("satboost", 1.15))
        else:
            gy = float(K.ALL[fid].get("kw", {}).get("gray", 0.0))
            sb_new = max(0.06, round((float(arg) / gfac(gy) - 0.080) / 0.93, 3))
        # scope the rewrite to this recipe's own dict literal
        i = src.index('"%s": dict(' % fid)
        j = src.find('\n "', i + 1)
        if j < 0:
            j = src.find("\n}", i + 1)
        blk = src[i:j]
        blk2, k = re.subn(
            r"hues=\[[^\]]*\], hspan=[0-9.]+, satboost=[0-9.]+",
            "hues=[%s], hspan=%.3f, satboost=%.3f"
            % (", ".join("%g" % h for h in hues),
               ID_HSPAN.get(fid, HSPAN.get(id(shape), 0.055)), sb_new), blk)
        if k != 1:
            raise SystemExit("PATCH-MISS %s" % fid)
        src = src[:i] + blk2 + src[j:]
        n += 1
        print("P %-26s rungs=%d base=%.3f satboost=%.3f" %
              (fid, len(hues), b, sb_new))
    open(path, "w", encoding="utf-8").write(src)
    print("PALETTE %s patched=%d" % (mod, n))


if __name__ == "__main__":
    main()
