# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090c 2026-08-02] Fold MEASURED mean-luma back into _VALFIX.

Same measured-correction method as the hue fix, for the other half of
"excavated": catlib crushes the art with `art * (val*VAL_GAIN / art.max())`,
i.e. it normalises by the MAX. Two finishes carrying the same `val` therefore
render at very different LIGHTNESS depending on how peaky their field is —
measured spread on relic lapis was 0.19 to 0.37 mean luma at one val, which is
the difference between deep ultramarine and cornflower. This targets the MEAN.

  python huefix.py <mod>        # measures hue AND lum
  python apply_valfix.py <mod>  # folds lum into _VALFIX
"""
import ast
import json
import os
import re
import sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
TRIAGE = os.path.join(ROOT, "_fractured_triage")
GAIN = 0.7
DEAD = 0.04

# per-family target MEAN luma of the 512 paint
TARGET_LUM = {
    "lapis": 0.160, "malachite": 0.185, "terracotta": 0.245,
    "turquoise": 0.260, "gold": 0.320, "ivory": 0.440,
}


def main():
    mod = sys.argv[1]
    path = os.path.join(ROOT, "engine", "expansions",
                        "fractured_%s_2026.py" % mod)
    src = open(path, encoding="utf-8").read()
    meas = json.load(open(os.path.join(TRIAGE, "hue_%s.json" % mod)))

    m = re.search(r"(?ms)^_VALFIX = \{.*?\}\n", src)
    cur = ast.literal_eval(m.group(0).split("=", 1)[1].strip())

    moved = 0
    for fid, v in meas.items():
        fam = fid.split("_")[1]
        if fam not in TARGET_LUM or not v.get("lum"):
            continue
        want = TARGET_LUM[fam]
        ratio = want / max(float(v["lum"]), 1e-3)
        if abs(ratio - 1.0) > DEAD:
            k = cur.get(fid, 1.0) * (1.0 + GAIN * (ratio - 1.0))
            cur[fid] = round(min(max(k, 0.45), 1.9), 3)
            moved += 1
    lines = ["_VALFIX = {"]
    for fid in sorted(cur):
        if abs(cur[fid] - 1.0) > 1e-3:
            lines.append(' "%s": %.3f,' % (fid, cur[fid]))
    lines.append("}\n")
    src = src[:m.start()] + "\n".join(lines) + src[m.end():]
    open(path, "w", encoding="utf-8").write(src)
    print("VALFIX %s moved=%d entries=%d" % (mod, moved, len(cur)))


if __name__ == "__main__":
    main()
