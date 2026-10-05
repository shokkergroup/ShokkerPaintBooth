# -*- coding: utf-8 -*-
"""Triage for the 2026-08-31 commission: MONEY SHOKK, COLORSHOXX, CULTURAL.

Owner:
  * MONEY SHOKK  — *"forty themed exotic engines about wealth in every form —
    mint foil, vault steel, counterfeit gold, burn-a-stack green. Flexes harder
    than chrome... right now we are falling WELL SHORT. Needs a total rework."*
  * COLORSHOXX   — *"77 finishes originally designed to do something unique with
    color flipping. It's outdated and very repetitive now."* → WORLD OF COLOR, 100.
  * CULTURAL     — keep the base paint, **rework ALL the specs** for FORBIDDEN
    DRAGON, LET FREEDOM RING, RISING SUN, UNION JACKED, VIVA MEXICO.

One engine boot, one render per finish, one verdict line each. This measures the
CURRENT state so the rebuild is aimed at what is actually wrong, not at a guess.

  band    car-band energy of the paint, 8-32px window   (want >= 0.45)
  smat    distinct spec material cards >= 1.5% area     (want >= 5)
  sfam    material families among them                  (want >= 3)
  drift   mean distance from the nearest card anchor    (want low; deck-shaped)
  sband   car-band energy of the roughness channel      (want >= 0.45)
  follow  spec tracks the paint's geometry at 256       (want >= 0.30)
  srange  spread of the spec: std of M / Rough / Cc      (want each >= 20)
  twin    nearest sibling inside its own set, colour-independent

usage: python _wealth_work/triage.py [money|color|cultural ...]
"""
import contextlib
import io as _io
import json
import logging
import os
import sys

import cv2
import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT)
sys.path.insert(0, ROOT)
OUT = "_wealth_work"
os.makedirs(OUT + "/thumbs", exist_ok=True)

logging.disable(logging.CRITICAL)
_buf = _io.StringIO()
with contextlib.redirect_stdout(_buf), contextlib.redirect_stderr(_buf):
    import shokker_engine_v2 as eng
from engine.paint_v2 import spec_cards as SC                    # noqa: E402

N = 2048
SHAPE = (N, N)
MASK = np.ones(SHAPE, np.float32)
BASE = np.full(SHAPE + (3,), 0.5, np.float32)


def catalog_group(substr):
    """Read the shelf straight out of the JS catalog so the sets match the picker."""
    import subprocess
    r = subprocess.run(["node", "scripts/spb_catalog_query.js", "dump", substr],
                       capture_output=True, text=True, encoding="utf-8")
    rows = json.loads(r.stdout[r.stdout.index("["):r.stdout.rindex("]") + 1])
    return [(x["id"], x["name"], x["group"]) for x in rows]


SETS = {
    "money": lambda: catalog_group("MONEY SHOKK"),
    "color": lambda: catalog_group("COLORSHOXX"),
    "cultural": lambda: (catalog_group("DRAGON") + catalog_group("FREEDOM")
                         + catalog_group("RISING") + catalog_group("UNION")
                         + catalog_group("MEXICO")),
}


def band(L, lo=32, hi=256):
    F = np.fft.fftshift(np.abs(np.fft.fft2(L - L.mean())) ** 2)
    n = L.shape[0]
    yy, xx = np.mgrid[0:n, 0:n] - n // 2
    r = np.hypot(xx, yy)
    return float(F[(r >= lo) & (r <= hi)].sum() / max(F[r >= 2].sum(), 1e-9))


def sig(L, k=64):
    s = cv2.resize(L, (k, k), interpolation=cv2.INTER_AREA).astype(np.float32)
    s -= s.mean()
    n = np.linalg.norm(s)
    return s / n if n > 1e-9 else s


def follow(L, S, k=256):
    a, b = sig(L, k), sig(1.0 - S[..., 1].astype(np.float32) / 255.0, k)
    return abs(float((a * b).sum()))


def main(argv):
    want = [a for a in argv[1:] if a in SETS] or list(SETS)
    all_rows = []
    for key in want:
        items = SETS[key]()
        rows, sigs = [], {}
        for fid, name, group in items:
            try:
                spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[fid]
                p = np.asarray(paint_fn(BASE.copy(), SHAPE, MASK, 51, 1.0, None), np.float32)
                s = np.asarray(spec_fn(SHAPE, MASK, 51, 1.0))[..., :3].astype(np.uint8)
            except Exception as exc:
                rows.append({"set": key, "fid": fid, "name": name, "group": group,
                             "err": "%s: %s" % (type(exc).__name__, exc)})
                print("ERR  %-28s %s" % (fid, exc), flush=True)
                continue
            if p.max() > 1.5:
                p = p / 255.0
            L = (0.2126 * p[..., 0] + 0.7152 * p[..., 1] + 0.0722 * p[..., 2]).astype(np.float32)
            live, fams, chrome, drift = SC.report(s)
            rows.append({
                "set": key, "fid": fid, "name": name, "group": group,
                "band": round(band(L), 3), "smat": len(live), "sfam": fams,
                "drift": round(drift, 1), "sband": round(band(s[..., 1].astype(np.float32) / 255.0), 3),
                "follow": round(follow(L, s), 3),
                "sM": round(float(s[..., 0].std()), 1),
                "sR": round(float(s[..., 1].std()), 1),
                "sC": round(float(s[..., 2].std()), 1)})
            sigs[fid] = sig(L)
            c0 = (N - 512) // 2
            p8 = np.clip(p * 255, 0, 255).astype(np.uint8)
            cv2.imwrite("%s/thumbs/%s.png" % (OUT, fid), np.concatenate([
                cv2.resize(p8, (512, 512), interpolation=cv2.INTER_AREA),
                p8[c0:c0 + 512, c0:c0 + 512], s[c0:c0 + 512, c0:c0 + 512]], 1)[:, :, ::-1])
            print("%-28s band %.3f smat %2d sfam %d sband %.3f sM %5.1f sR %5.1f sC %5.1f"
                  % (fid, rows[-1]["band"], len(live), fams, rows[-1]["sband"],
                     rows[-1]["sM"], rows[-1]["sR"], rows[-1]["sC"]), flush=True)
        keys = list(sigs)
        for a in keys:
            b_, who = -1.0, ""
            for b in keys:
                if a != b:
                    c = float((sigs[a] * sigs[b]).sum())
                    if c > b_:
                        b_, who = c, b
            for r in rows:
                if r["fid"] == a:
                    r["sim"], r["twin"] = round(b_, 3), who
        all_rows += rows
        json.dump(rows, _io.open("%s/triage_%s.json" % (OUT, key), "w", encoding="utf-8"), indent=1)
    json.dump(all_rows, _io.open(OUT + "/triage_all.json", "w", encoding="utf-8"), indent=1)
    print("\nwrote %d rows" % len(all_rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
