"""Dichroic Rivets - ASTRA R2 (SPB-105 / ASTRA-R2, 2026-09-27, Claude).

Owner on the R1 rebuild: "surprisingly AWFUL" - asked for finishes that are
unique, jump off the screen and do what the name says. Construction:
engine/expansions/astra/color_shoxx.py::redshift_rivets; identity contract in r2.TABLE.
Finish-law axes at rebuild (lab, 1024): SCALE paint 0.668 / spec 0.724,
FOLLOW 0.649, dead 0.035. R1 source: _astra_claude_work/r1_backup/.
"""
from ..r2 import adopt

adopt(__name__, 'redshift_rivets')
