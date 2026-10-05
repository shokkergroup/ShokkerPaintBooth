# -*- coding: utf-8 -*-
"""How many DIFFERENT materials is a TESSERA finish actually firing at once?

Owner, 2026-08-31: *"the spec channel colors are not diverse enough ... I'd LIKE
to see many other states created inside of these specs. Where side-by-side lives
chrome, pearl, mercury, candy, metallic, flat, clear matte, wet look, clearcoat,
gloss carbon, milk glass, frozen, etc ... so many different types of material
looks firing on the car at one time its a shock to the system."*

So the gate is not "is the spec varied" in the abstract — it is: classify every
pixel to its nearest card in the Spec Guide deck and count how many DISTINCT
cards, and how many distinct FAMILIES, hold a real share of the surface.

  MATS   distinct material cards holding >= 1.5% of the canvas   (target >= 8)
  FAM    distinct families among them                            (target >= 4)
  CHR    share of the canvas in the chrome tier (M >= 240)       (0.04 - 0.34)
  DRIFT  mean distance from a pixel to the card it was dealt     (target <= 26)
         — a card blended away from its own anchor is not that material any
         more, which is how a deck of thirteen can still read as one colour.

usage: python _tessera_work/materials.py [fid ...]
"""
import os
import sys

import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import engine.expansions.fractured_tessera_kit_2026 as kit    # noqa: E402
import engine.expansions.fractured_tessera_2026 as m          # noqa: E402

N = 1024                       # material identity is scale-free; 1024 is plenty
MASK = np.ones((N, N), np.float32)
MIN_MATS, MIN_FAM, DRIFT_MAX = 8, 4, 26.0
CHR_LO, CHR_HI = 0.04, 0.34

_NAMES = list(kit.MATERIALS)
_DECK = np.asarray([kit.MATERIALS[n] for n in _NAMES], np.float32)
_FAM_OF = {n: f for f, names in kit.FAMILIES.items() for n in names}


def classify(spec):
    px = spec.reshape(-1, 3).astype(np.float32)[::7]          # stride: 150k samples
    d = ((px[:, None, :] - _DECK[None, :, :]) ** 2).sum(-1)
    idx = d.argmin(1)
    drift = float(np.sqrt(d[np.arange(idx.size), idx]).mean())
    share = np.bincount(idx, minlength=len(_NAMES)) / float(idx.size)
    return share, drift


def main(argv):
    only = set(argv[1:])
    ids = [f for f in m.TESSERA if not only or f in only]
    rows, bad = [], 0
    print("%-26s %5s %4s %6s %7s  %s" % ("FINISH", "MATS", "FAM", "CHR", "DRIFT", "top materials"))
    for fid in ids:
        spec_fn, _paint_fn = m._mk(fid)
        s = np.asarray(spec_fn((N, N, 3), MASK, 51, 1.0))[..., :3]
        share, drift = classify(s)
        live = [(_NAMES[i], share[i]) for i in np.argsort(-share) if share[i] >= 0.015]
        fams = {_FAM_OF.get(n, "?") for n, _s in live}
        chrome = float(share[[i for i, n in enumerate(_NAMES)
                              if _FAM_OF.get(n) == "chrome"]].sum())
        fail = []
        if len(live) < MIN_MATS:
            fail.append("MATS")
        if len(fams) < MIN_FAM:
            fail.append("FAM")
        if not (CHR_LO <= chrome <= CHR_HI):
            fail.append("CHR")
        if drift > DRIFT_MAX:
            fail.append("DRIFT")
        bad += bool(fail)
        rows.append((fid, len(live), len(fams), chrome, drift))
        print("%-26s %5d %4d %6.2f %7.1f  %s%s"
              % (m.TESSERA[fid]["name"][:26], len(live), len(fams), chrome, drift,
                 ", ".join("%s %.0f%%" % (n, s * 100) for n, s in live[:6]),
                 "   <<< " + " ".join(fail) if fail else ""))
    if rows:
        print("\nmedian materials %d | median families %d | median drift %.1f"
              % (int(np.median([r[1] for r in rows])),
                 int(np.median([r[2] for r in rows])),
                 float(np.median([r[4] for r in rows]))))
    print("RESULT: %d/%d pass" % (len(rows) - bad, len(rows)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
