# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090c 2026-08-02] Fold the MEASURED hue drift back into the
module's _HUEFIX block (accumulating, so it converges over rounds).

  python huefix.py <mod>        # measure -> hue_<mod>.json
  python apply_huefix.py <mod>  # fold into engine/expansions/fractured_<mod>_2026.py
  (repeat until huefix reports off_target=0)

Only ids whose drift exceeds `dead` are touched, so converged ids stop moving.
"""
import ast
import json
import os
import re
import sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
TRIAGE = os.path.join(ROOT, "_fractured_triage")
DEAD = 0.012
# Damped: moving a hero anchor by d does NOT move the rendered mean by d (the
# window can straddle a LUT hue boundary), so a full-step correction rings.
GAIN = 0.55


def main():
    mod = sys.argv[1]
    path = os.path.join(ROOT, "engine", "expansions",
                        "fractured_%s_2026.py" % mod)
    src = open(path, encoding="utf-8").read()
    meas = json.load(open(os.path.join(TRIAGE, "hue_%s.json" % mod)))

    m = re.search(r"(?ms)^_HUEFIX = \{.*?\}\n", src)
    cur = ast.literal_eval(m.group(0).split("=", 1)[1].strip()) if m else {}
    if not m:
        m = re.search(r"(?m)^_HUEFIX = \{\}\n", src)
        cur = {}

    moved = 0
    for fid, v in meas.items():
        if abs(v["fix"]) > DEAD:
            cur[fid] = round(((cur.get(fid, 0.0) + GAIN * v["fix"]) + 0.5) % 1.0 - 0.5, 4)
            moved += 1
    lines = ["_HUEFIX = {"]
    for fid in sorted(cur):
        if abs(cur[fid]) > 1e-4:
            lines.append(' "%s": %+0.4f,' % (fid, cur[fid]))
    lines.append("}\n")
    src = src[:m.start()] + "\n".join(lines) + src[m.end():]
    open(path, "w", encoding="utf-8").write(src)
    print("HUEFIX %s moved=%d entries=%d" % (mod, moved, len(cur)))


if __name__ == "__main__":
    main()
