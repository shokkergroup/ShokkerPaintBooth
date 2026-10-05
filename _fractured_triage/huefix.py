# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090c 2026-08-02] COLOUR-IDENTITY probe.

Parent visual review: the geometry is right but the colour that RENDERS is not
the colour the recipe SETS. The thin-film LUT's hue distribution inside a hero
window is not symmetric, so the saturation-weighted mean hue drifts off the
anchor (the clockwork agent measured brass landing 0.043 of a turn low and
rendering as bronze). This measures the drift so it can be corrected by the
number instead of by eye.

Per finish, on the 512 paint:
  hue   saturation-weighted CIRCULAR MEAN hue, in turns (0..1)
  dom   hue of the heaviest 36-bin histogram bucket (sat > 0.15)
  sat   mean saturation over chromatic pixels
  d     signed circular distance hue -> the id's TARGET (short way round)

  python huefix.py <mod> [--json]
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

# ── TARGET HUES, in turns. Named after the material/flower the id claims to
# be; these are the numbers the glance test is really asking about.
TARGET = {
    # BLOOM — flowers ARE saturated, keep that; only the NAME has to be true.
    "magenta": 0.870, "pink": 0.920, "blush": 0.950, "coral": 0.020,
    "lilac": 0.755, "leaf": 0.300, "leafvine": 0.300, "butter": 0.135,
    "white": 0.110,
    # PETRI — culture-stain saturation is authentic.
    "amber": 0.090, "cyan": 0.500, "lime": 0.220, "violet": 0.750,
    # RELIC — excavated materials: muted, earthy, low chroma.
    "lapis": 0.625, "gold": 0.115, "turquoise": 0.470, "terracotta": 0.045,
    "malachite": 0.360, "ivory": 0.105,
}


def target_of(fid):
    return TARGET[fid.split("_")[1]]


def hue_stats(paint):
    u8 = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV).astype(np.float32)
    h = hsv[:, :, 0] * (1.0 / 179.0)
    s = hsv[:, :, 1] * (1.0 / 255.0)
    m = s > 0.12
    if not m.any():
        return 0.0, 0.0, 0.0
    hh, ss = h[m], s[m]
    ang = hh * 2.0 * np.pi
    cx = float((np.cos(ang) * ss).sum())
    cy = float((np.sin(ang) * ss).sum())
    mean = (np.arctan2(cy, cx) / (2.0 * np.pi)) % 1.0
    hist, edges = np.histogram(hh, bins=36, range=(0, 1), weights=ss)
    dom = float(edges[int(np.argmax(hist))] + 1.0 / 72.0)
    return float(mean), dom, float(ss.mean())


def circ_d(a, b):
    """signed short-way distance a -> b, in turns."""
    return ((float(b) - float(a) + 0.5) % 1.0) - 0.5


def main():
    mod = sys.argv[1]
    M = importlib.import_module("engine.expansions.fractured_%s_2026" % mod)
    K = M.KIT
    base = np.zeros((RES, RES, 3), np.float32)
    mask = np.ones((RES, RES), np.float32)
    out = {}
    for fid in sorted(K.ALL):
        K.art_work_cached.cache_clear()
        K.macro_cached.cache_clear()
        _s, pf = K.mk(fid)
        p = pf(base, (RES, RES), mask, 1234, 1.0, None)
        hue, dom, sat = hue_stats(p)
        lum = float((0.299 * p[:, :, 0] + 0.587 * p[:, :, 1]
                     + 0.114 * p[:, :, 2]).mean())
        tgt = target_of(fid)
        d = circ_d(hue, tgt)
        out[fid] = dict(hue=round(hue, 4), dom=round(dom, 4),
                        sat=round(sat, 3), lum=round(lum, 3), target=tgt,
                        fix=round(d, 4))
        print("HUE %-24s hue=%.3f dom=%.3f sat=%.2f lum=%.2f target=%.3f  "
              "fix=%+0.4f %s"
              % (fid, hue, dom, sat, lum, tgt, d,
                 "OK" if abs(d) <= 0.03 else "<<"))
    json.dump(out, open(os.path.join(TRIAGE, "hue_%s.json" % mod), "w"),
              indent=1)
    bad = sum(1 for v in out.values() if abs(v["fix"]) > 0.03)
    print("HUESUM %s off_target=%d/%d  worst=%.4f" %
          (mod, bad, len(out), max(abs(v["fix"]) for v in out.values())))


if __name__ == "__main__":
    main()
