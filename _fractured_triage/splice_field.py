# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090b 2026-08-02] Splice a rebuilt generator block into one
FRACTURED module without pushing the old text back through model context
(token mandate: assemble big text on disk).

  python splice_field.py <bloom|petri|relic>

1. replaces [def _grain(  ...  ENGINES = {) with newgen_<mod>.py
2. wraps ENGINES in the _lowcut decorator
3. blanks the pass-2 eargs in the recipe table (the generators own their
   geometry now: 1 engine : 1 finish) and installs the _TUNE override block
"""
import os
import re
import sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
TRIAGE = os.path.join(ROOT, "_fractured_triage")
VAR = {"bloom": "_BLOOM", "petri": "_PETRI", "relic": "_RELIC"}

TUNE_BLOCK = '''
# ════════════════════════════════════════════════════════════════════════════
# PER-FINISH FIELD TUNE — [SPB-FRACTURED-090b 2026-08-02]
# The generators own their geometry now (this module is 1 engine : 1 finish),
# so a recipe's eargs are the four transfer dials plus its LUT anchor:
#   span   width of the thin-film LUT walk (the biggest band lever: the LUT is
#          an oscillator, and a full walk MULTIPLIES the generator frequencies)
#   mid    where that walk is centred — the steepest monotone stretch of this
#          recipe's own LUT, probed by _lut_steep (centring on 0.5 can land on
#          an extremum and yield a flat, colour-only finish)
#   lowcut high-pass knee on T, in px at GEN (1.6 == r 64, the band floor)
#   soft   sub-pixel blur that deletes the r>200 harmonics a hard edge throws
#          off — they inflate band while destroying the coherence it certifies
# Values are the measured optimum from _fractured_triage/tune_field.py
# (maximise car-band subject to ac>=0.56 / peakiness>=0.32 / shape>=0.56 /
# fineness>6.6 / hue bins>=5).
#
# Kit-level band hygiene, applied to every id:
#   vd (0.96, 1.06) + tmod 0.0 — a wide value swing or a phase walk IS
#          low-frequency power, and the metric is a ratio, so macro luma drama
#          is charged twice. Macro identity rides the HUE anchors instead,
#          which are luma-neutral (art_work re-applies each pixel's own luma).
#   ambient 0.05 — the wide bloom mix is a low-pass copy of the field
#   sparkle 0.08 — that octave lands at r~320, ABOVE the band: pure denominator
#   hero-dominant palette + a coarse hue field — 7/11 hero, 2/11 second, one
#          each for the accents, on a smoothed probe: four equal anchors picked
#          per feature rendered the whole module as a two-colour halftone
#          screen. Colour static is a failure however good the numbers are.
# ════════════════════════════════════════════════════════════════════════════

_TUNE = {}

for _fid, _e in _TUNE.items():
    _e = dict(_e)
    %(var)s[_fid]["val"] = _e.pop("val")
    _e["mid"] = _lut_steep(%(var)s[_fid]["lut"], _e.get("span", 1.0))
    %(var)s[_fid]["eargs"] = _e
for _d in %(var)s.values():
    _d["vd"] = (0.96, 1.06)
    _d["tmod"] = 0.0
    _d["kw"]["ambient"] = 0.05
    _d["kw"]["sparkle"] = 0.08
    _h = _d["hues"]
    _d["hues"] = [_h[0]] * 7 + [_h[1]] * 2 + [_h[2], _h[3]]
    _d["hue_levels"] = 0.9
    _d["hue_jit"] = 0.10
    _d["hue_blur"] = 3.2
    _d["hue_cell"] = max(float(_d.get("hue_cell", 8.0)), 14.0)

'''


def main():
    mod = sys.argv[1]
    var = VAR[mod]
    path = os.path.join(ROOT, "engine", "expansions",
                        "fractured_%s_2026.py" % mod)
    src = open(path, encoding="utf-8").read()
    new = open(os.path.join(TRIAGE, "newgen_%s.py" % mod), encoding="utf-8").read()

    a = src.index("def _grain(xx, yy, cell, salt, thr=0.62):")
    b = src.index("\nENGINES = {")
    src = src[:a] + new.rstrip("\n") + "\n\n" + src[b + 1:]

    # 2. wrap ENGINES
    if "_lowcut(v)" not in src:
        i = src.index("ENGINES = {")
        j = src.index("\n}\n", i) + 3
        src = (src[:j] + "ENGINES = {k: _lowcut(v) for k, v in ENGINES.items()}\n"
               + src[j:])

    # 3. blank pass-2 eargs
    src, n = re.subn(r"(?m)^(\s*)dict\([^()]*\), \(", r"\1dict(), (", src)

    # 4. install the tune block
    if "_TUNE = {" not in src:
        k = src.index("\nassert len(%s) == 20" % var)
        src = src[:k] + "\n" + (TUNE_BLOCK % {"var": var}) + src[k:]

    open(path, "w", encoding="utf-8").write(src)
    print("SPLICED %s eargs_blanked=%d bytes=%d" % (mod, n, len(src)))


if __name__ == "__main__":
    main()
