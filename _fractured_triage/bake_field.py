# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090b 2026-08-02] Bake tune_<mod>.json into the module's
_TUNE block (assemble on disk, never through model context).

  python bake_field.py <bloom|petri|relic>
"""
import json
import os
import sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
TRIAGE = os.path.join(ROOT, "_fractured_triage")
VAR = {"bloom": "_BLOOM", "petri": "_PETRI", "relic": "_RELIC"}


def main():
    mod = sys.argv[1]
    var = VAR[mod]
    path = os.path.join(ROOT, "engine", "expansions",
                        "fractured_%s_2026.py" % mod)
    src = open(path, encoding="utf-8").read()
    tune = json.load(open(os.path.join(TRIAGE, "tune_%s.json" % mod)))

    lines = ["_TUNE = {"]
    for fid in sorted(tune):
        t = tune[fid]
        kv = "span=%g, lowcut=%g, soft=%g, val=%g" % (
            t["span"], t["lowcut"], t.get("soft", 0.0), t["val"])
        lines.append(' "%s": dict(%s),   # band %.3f ac %.3f pk %.3f'
                     % (fid, kv, t["band"], t["ac"], t["pk"]))
    lines.append("}")
    block = "\n".join(lines)

    a = src.index("_TUNE = {")
    # the freshly spliced module carries an EMPTY one-line placeholder; a
    # re-bake carries a full dict. Getting this wrong swallows everything up
    # to the next closing brace — which is GROUPS — so it is asserted.
    b = a + 11 if src[a:a + 11] == "_TUNE = {}\n" else src.index("\n}\n", a) + 3
    assert "GROUPS = {" in src[b:], "bake would eat GROUPS - abort"
    src = src[:a] + block + "\n" + src[b:]
    open(path, "w", encoding="utf-8").write(src)
    print("BAKED %s n=%d" % (mod, len(tune)))


if __name__ == "__main__":
    main()
