# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090d 2026-08-02] Fold the MEASURED hue drift back into the
module's _HUEFIX / _ACCFIX blocks (accumulating, so it converges over rounds).

  python colorfix.py <mod>        # measure -> color_<mod>.json
  python apply_colorfix.py <mod>  # fold into fractured_<mod>_2026.py
  (repeat until colorfix reports every id inside 0.03 turn on BOTH statistics)

TWO KNOBS, because there are two independent ways a ladder can render off its
name and one knob cannot fix both:

  _HUEFIX  rotates the WHOLE ladder. Driven by the mean of the two hue errors
           (whole-field circular mean, and the SPINE = that same statistic
           restricted to the dominant family window). This is the correction
           for the LUT's asymmetric hue density inside the hero window — the
           reason the anchor you set is not the hue that renders.
  _ACCFIX  rotates ONLY the last two rungs (a nebula ladder's accent pair, or
           the far end of a frost/tempest family fan). Driven by the residual
           gap between the whole-field mean and the spine, i.e. the tail's net
           pull. Rotating both tail rungs by d lengthens one lever and
           shortens the other, which is exactly the rebalance an
           unequal-weight pair needs. The tail carries ~0.3 of the colour
           mass, hence the 2.2x lever; capped so a fan can never invert.

Colour-only: art_work re-applies each pixel's own luma after the HSV
roundtrip, so neither knob moves band / autocorr / peakiness / shape /
fineness / coverage.
"""
import ast
import json
import os
import re
import sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
TRIAGE = os.path.join(ROOT, "_fractured_triage")
DEAD = 0.010
GAIN = 0.80
ACC_DEAD = 0.012
ACC_GAIN = 0.65
ACC_LEVER = 2.2
ACC_CAP = 0.070


def fold(src, key, drive, gain, lever, dead, cap):
    m = re.search(r"(?ms)^%s = \{.*?\}\n" % key, src)
    cur = ast.literal_eval(m.group(0).split("=", 1)[1].strip())
    moved = 0
    for fid, d in drive.items():
        if abs(d) > dead:
            v = cur.get(fid, 0.0) + gain * lever * d
            v = max(-cap, min(cap, ((v + 0.5) % 1.0) - 0.5))
            cur[fid] = round(v, 4)
            moved += 1
    lines = ["%s = {" % key]
    for fid in sorted(cur):
        if abs(cur[fid]) > 1e-4:
            lines.append(' "%s": %+0.4f,' % (fid, cur[fid]))
    lines.append("}\n")
    return src[:m.start()] + "\n".join(lines) + src[m.end():], moved


def main():
    mod = sys.argv[1]
    path = os.path.join(ROOT, "engine", "expansions",
                        "fractured_%s_2026.py" % mod)
    src = open(path, encoding="utf-8").read()
    meas = json.load(open(os.path.join(TRIAGE, "color_%s.json" % mod)))

    # whole-ladder rotation: split the difference between the two hue errors,
    # so one rotation drives BOTH toward zero
    spin = {f: 0.5 * (v["fix"] + v["sfix"]) for f, v in meas.items()}
    # tail rotation: close the gap that is left between them
    accd = {f: v["acc"] for f, v in meas.items()}

    src, mv1 = fold(src, "_HUEFIX", spin, GAIN, 1.0, DEAD, 0.25)
    src, mv2 = fold(src, "_ACCFIX", accd, ACC_GAIN, ACC_LEVER, ACC_DEAD,
                    ACC_CAP)
    open(path, "w", encoding="utf-8").write(src)
    print("HUEFIX %s ladder_moved=%d tail_moved=%d" % (mod, mv1, mv2))


if __name__ == "__main__":
    main()
