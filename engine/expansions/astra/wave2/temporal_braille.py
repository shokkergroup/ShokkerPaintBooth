"""Temporal Braille - ASTRA R2 (SPB-105 / ASTRA-R2, 2026-09-27, Claude).

Owner on the R1 rebuild: "surprisingly AWFUL" - asked for finishes that are
unique, jump off the screen and do what the name says. Construction:
engine/expansions/astra/future_shoxx.py::temporal_braille; identity contract in r2.TABLE.
Finish-law axes at rebuild (lab, 1024): SCALE paint 0.587 / spec 0.599,
FOLLOW 0.705, dead 0.357. R1 source: _astra_claude_work/r1_backup/.
"""
from ..r2 import adopt

adopt(__name__, 'temporal_braille')
