# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090d 2026-08-02] COLOUR-IDENTITY probe for FROST / NEBULA /
TEMPEST (the storm+ice+deep-space trio).

Parent visual review: geometry accepted, COLOUR wrong on two counts —
  (1) complementary-accent confetti: the 11th rung of every `hues` ladder was a
      COMPLEMENT (magenta in a green storm, tan-orange in a slate storm), and
      at ~9 px of hue-cell it reads as electric speckle, not material;
  (2) name-hue mismatch: "white" ids rendering blue/orange, "violet" ids
      rendering hot magenta.

The anchor you SET is not the hue that RENDERS: art_work remaps the thin-film
hue into c +- hspan, and the LUT's hue distribution inside that window is
asymmetric, so the SATURATION-WEIGHTED CIRCULAR MEAN lands off the anchor.
This measures that drift so it can be corrected by the number.

Per finish, on the 512 paint (mask=ones, seed=1234, base 0.5 grey):
  hue   saturation-weighted CIRCULAR MEAN hue, in turns (0..1)
  dom   hue of the heaviest 36-bin sat-weighted bucket
  sat   mean saturation over chromatic pixels (S > 0.12)
  satA  mean saturation over ALL pixels  <- the "does it read white" number
  bins  hue-bin gate count (>= 5 required)
  off   fraction of chromatic pixels further than 0.12 turn from the id's
        target hue  <- the CONFETTI number
  fix   signed circular distance hue -> TARGET (short way round)

  python colorfix.py <frost|nebula|tempest>
"""
import importlib
import json
import os
import sys

import cv2
import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
TRIAGE = os.path.join(ROOT, "_fractured_triage")
sys.path.insert(0, ROOT)

RES = 512

# ── TARGET HUES in turns (HSV convention: 0=red .167=yellow .333=green
# .5=cyan .667=blue .75=violet .833=magenta), and the mean-saturation CEILING
# for ids whose NAME is a white/silver word (those must read as material
# white, which is a saturation statement, not a hue one).
#   TARGET[fid] = (hue_turns, satA_ceiling or None)
TARGET = {
    # ── TEMPEST — weather. slate / steel / navy / storm-white, green-tinged
    # sky only for the supercell ids. NO magenta, NO rust.
    "fte_lichtenberg_crown": (0.680, None),
    "fte_steel_downpour": (0.585, None),
    "fte_storm_cell": (0.430, None),
    "fte_white_arc": (0.570, 0.20),
    "fte_slate_squall": (0.605, None),
    "fte_green_supercell": (0.330, None),
    "fte_thunderhead_white": (0.580, 0.18),
    "fte_slate_vortex": (0.620, None),
    "fte_violet_hail": (0.740, None),
    "fte_blue_bolt": (0.600, None),
    "fte_slate_billows": (0.625, None),
    "fte_violet_twister": (0.750, None),
    "fte_steel_rain": (0.575, None),
    "fte_green_strike": (0.335, None),
    "fte_whiteout_hail": (0.565, 0.18),
    "fte_steel_cyclone": (0.590, None),
    "fte_gustfront_green": (0.345, None),
    "fte_ball_lightning": (0.530, None),
    "fte_slate_hailfield": (0.610, None),
    "fte_violet_cumulonimbus": (0.755, None),
    # ── FROST — ice. white / pale cyan / glacier blue / deep blue shadow,
    # faint violet or aqua ONLY. NO magenta, NO warm.
    "ffr_window_fern": (0.560, None),
    "ffr_cyan_frond": (0.530, None),
    "ffr_glacier_fern": (0.550, None),
    "ffr_violet_rime": (0.755, None),
    "ffr_steel_flurry": (0.600, None),
    "ffr_silver_dendrite": (0.565, 0.20),
    "ffr_diamond_dust": (0.580, 0.20),
    "ffr_violet_sectored": (0.765, None),
    "ffr_cyan_fissure": (0.540, None),
    "ffr_whiteout_rift": (0.585, 0.18),
    "ffr_violet_chasm": (0.725, None),
    "ffr_blue_serac": (0.600, None),
    "ffr_hoarfrost_white": (0.580, 0.18),
    "ffr_silver_hoar": (0.580, 0.20),
    "ffr_cyan_frostbloom": (0.520, None),
    "ffr_ice_needles": (0.570, 0.26),
    "ffr_violet_trapped": (0.725, None),
    "ffr_steel_bubbles": (0.590, None),
    "ffr_cyan_veil": (0.520, None),
    "ffr_snowdrift_ice": (0.555, 0.20),
    # ── OPALSKIN [SPB-OPALSKIN 2026-08-03] — crush-law material patterns.
    # Named ids only; the 6 rainbow fsk_* ids are gated on SPREAD (>=8 even
    # hue bins in verify_guard crush mode), not on a single target, and are
    # deliberately absent here (main() skips unknown ids).
    "fsk_snakeskin": (0.300, None),
    "fsk_diamond_plate": (0.585, None),
    "fsk_carbon_weave": (0.600, None),
    "fsk_dragon_scale": (0.420, None),
    "fsk_chainmail": (0.600, None),
    "fsk_stingray": (0.570, None),
    "fsk_croc_hide": (0.055, None),
    "fsk_damascus": (0.610, None),
    "fsk_hex_mesh": (0.090, None),
    "fsk_knurl": (0.620, None),
    "fsk_herringbone": (0.060, None),
    "fsk_houndstooth": (0.100, None),
    "fsk_basket_weave": (0.095, None),
    "fsk_chesterfield": (0.985, None),
    "fsk_feather_mantle": (0.700, None),
    "fsk_scale_mail": (0.075, None),
    "fsk_spider_silk": (0.575, None),
    "fsk_circuit_trace": (0.055, None),
    "fsk_mosaic_glass": (0.500, None),
    # ── NEBULA — deep space KEEPS its drama; only the NAMED hue has to win.
    "fnb_violet_billows": (0.755, None),
    "fnb_magenta_remnant": (0.880, None),
    "fnb_cyan_spiral": (0.500, None),
    "fnb_golden_cluster": (0.100, None),
    "fnb_teal_annulus": (0.470, None),
    "fnb_cyan_drift": (0.520, None),
    "fnb_gilded_shockfront": (0.100, None),
    "fnb_teal_starfield": (0.460, None),
    "fnb_violet_galaxy": (0.765, None),
    "fnb_magenta_rift": (0.900, None),
    "fnb_teal_lagoon": (0.450, None),
    "fnb_violet_annulus": (0.765, None),
    "fnb_magenta_emission": (0.875, None),
    "fnb_cyan_dustlane": (0.510, None),
    "fnb_golden_pinwheel": (0.100, None),
    "fnb_magenta_stardust": (0.890, None),
    "fnb_cyan_shockwave": (0.495, None),
    "fnb_gilded_veil": (0.105, None),
    "fnb_teal_rift": (0.450, None),
    "fnb_violet_starglow": (0.755, None),
}


def circ_d(a, b):
    """signed short-way distance a -> b, in turns."""
    return ((float(b) - float(a) + 0.5) % 1.0) - 0.5


def hue_stats(paint, tgt):
    u8 = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV).astype(np.float32)
    h = hsv[:, :, 0] * (1.0 / 179.0)
    s = hsv[:, :, 1] * (1.0 / 255.0)
    satA = float(s.mean())
    m = s > 0.12
    if not m.any():
        return 0.0, 0.0, 0.0, satA, 0, 0.0
    hh, ss = h[m], s[m]
    ang = hh * 2.0 * np.pi
    cx = float((np.cos(ang) * ss).sum())
    cy = float((np.sin(ang) * ss).sum())
    mean = (np.arctan2(cy, cx) / (2.0 * np.pi)) % 1.0
    # SPINE hue: the same statistic restricted to the pixels INSIDE the
    # family window (+-0.12 turn of the subject). This is the "at a glance"
    # reading — the hue the dominant population actually renders — measured
    # separately from the whole-field mean, because a deliberate two-sided
    # accent pair (nebula) can hold the whole-field mean on target while the
    # dominant population has walked off it, and vice versa.
    dw = np.abs(((hh - tgt + 0.5) % 1.0) - 0.5) <= 0.12
    if dw.any():
        a2, s2 = ang[dw], ss[dw]
        spine = (np.arctan2(float((np.sin(a2) * s2).sum()),
                            float((np.cos(a2) * s2).sum()))
                 / (2.0 * np.pi)) % 1.0
    else:
        spine = mean
    hist, edges = np.histogram(hh, bins=36, range=(0, 1), weights=ss)
    dom = float(edges[int(np.argmax(hist))] + 1.0 / 72.0)
    # gate replica (verify_guard.hue_bins): S > 38/255, bins with > 0.5% mass
    mg = hsv[:, :, 1] > 38
    tot = paint.shape[0] * paint.shape[1]
    hb = 0
    if mg.any():
        hg, _ = np.histogram(hsv[:, :, 0][mg], bins=36, range=(0, 180))
        hb = int((hg > 0.005 * tot).sum())
    # confetti: chromatic mass more than 0.12 turn off the intended hue
    d = np.abs(((hh - tgt + 0.5) % 1.0) - 0.5)
    off = float((ss * (d > 0.12)).sum() / max(ss.sum(), 1e-9))
    return float(mean), dom, float(ss.mean()), satA, hb, off, float(spine)


def main():
    mod = sys.argv[1]
    M = importlib.import_module("engine.expansions.fractured_%s_2026" % mod)
    K = M.KIT
    base = np.full((RES, RES, 3), 0.5, np.float32)
    mask = np.ones((RES, RES), np.float32)
    out = {}
    for fid in sorted(K.ALL):
        if fid not in TARGET:
            continue      # rainbow ids are spread-gated, not target-gated
        K.art_work_cached.cache_clear()
        K.macro_cached.cache_clear()
        _s, pf = K.mk(fid)
        p = pf(base, (RES, RES), mask, 1234, 1.0, None)
        tgt, satcap = TARGET[fid]
        hue, dom, sat, satA, bins, off, spine = hue_stats(p, tgt)
        d = circ_d(hue, tgt)
        sd = circ_d(spine, tgt)
        acc = circ_d(hue, spine)
        okh = abs(d) <= 0.03 and abs(sd) <= 0.03
        oks = (satcap is None) or (satA <= satcap)
        out[fid] = dict(hue=round(hue, 4), dom=round(dom, 4), sat=round(sat, 3),
                        satA=round(satA, 3), bins=bins, off=round(off, 3),
                        spine=round(spine, 4), sfix=round(sd, 4),
                        acc=round(acc, 4),
                        target=tgt, satcap=satcap, fix=round(d, 4),
                        ok=bool(okh and oks and off <= 0.10 and bins >= 5))
        print("C %-26s hue=%.3f spine=%.3f sat=%.2f satA=%.3f bins=%2d "
              "off=%.3f tgt=%.3f fix=%+0.4f sfix=%+0.4f acc=%+0.4f%s%s%s"
              % (fid, hue, spine, sat, satA, bins, off, tgt, d, sd, acc,
                 "" if okh else " HUE<<", "" if oks else " SAT<<",
                 "" if off <= 0.10 else " CONFETTI<<"))
    json.dump(out, open(os.path.join(TRIAGE, "color_%s.json" % mod), "w"),
              indent=1)
    bad = [f for f, v in out.items() if not v["ok"]]
    print("CSUM %s bad=%d/%d worst_hue=%.4f worst_spine=%.4f worst_off=%.3f "
          "minbins=%d" %
          (mod, len(bad), len(out),
           max(abs(v["fix"]) for v in out.values()),
           max(abs(v["sfix"]) for v in out.values()),
           max(v["off"] for v in out.values()),
           min(v["bins"] for v in out.values())))


if __name__ == "__main__":
    main()
