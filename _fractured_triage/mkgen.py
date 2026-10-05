# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090b] Assemble newgen_<mod>.py = the proven shared kernel
block (lifted verbatim from the bloom rebuild: the in-band field law, _flat /
_fat / _grain / _fine / _ptier / _cells / _pave, _lut_steep and the _lowcut
transfer wrapper) + this module's own generators from gens_<mod>.py.

Keeps the kernel identical across the three modules without pushing it back
through model context (token mandate: assemble big text on disk).
"""
import sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
NL = chr(10)
RULE = "# " + "\u2550" * 4


def main():
    mod = sys.argv[1]
    src = open(ROOT + r"\engine\expansions\fractured_bloom_2026.py",
               encoding="utf-8").read()
    a = src.rindex(RULE, 0, src.index("# THE IN-BAND FIELD LAW"))
    b = src.rindex(RULE, 0, src.index("# STRUCTURAL GENERATORS"))
    head = src[a:b]
    e = src.index("def _lut_steep(lut, span=0.5):")
    f = src.index(NL + "def _R(", e)
    head = head + src[e:f].rstrip(NL) + NL * 3
    c = src.index("def _lowcut(fn):")
    d = src.index(NL + "ENGINES = {")
    tail = src[c:d]
    gens = open(ROOT + r"\_fractured_triage\gens_%s.py" % mod,
                encoding="utf-8").read()
    out = head + gens.rstrip(NL) + NL * 3 + tail
    open(ROOT + r"\_fractured_triage\newgen_%s.py" % mod, "w",
         encoding="utf-8").write(out)
    print("ASSEMBLED newgen_%s.py bytes=%d" % (mod, len(out)))


if __name__ == "__main__":
    main()
