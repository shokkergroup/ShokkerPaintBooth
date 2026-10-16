# -*- coding: utf-8 -*-
"""FRACTURED COSMOS R2 - the 60-row table (id, name, chapter, desc, fn, seed).

[S19 2026-10-12 owner: Fractured Cosmos rebuild] Descriptions say what the
finish LOOKS like (<= 140 chars). Chapter order is the picker order.
"""
from __future__ import annotations

import importlib

CHAPTERS = [
    ("stellar", "\u2600 STELLAR"),
    ("nebula", "\U0001f32b NEBULAE"),
    ("worlds", "\U0001fa90 WORLDS"),
    ("exotic", "\U0001f573 GRAVITY & EXOTIC"),
    ("galaxies", "\U0001f300 GALAXIES & LARGE SCALE"),
    ("craft", "\U0001f6f8 CRAFT & SIGNALS"),
]
BLURB = ("Sixty space finishes: stars, nebulae, alien worlds, black holes, galaxies and the craft "
         "that visit them. Every one is its own design.")

TABLE = []
for _ci, (_key, _label) in enumerate(CHAPTERS):
    try:
        _mod = importlib.import_module("." + _key, __package__)
    except ModuleNotFoundError as _ex:                      # chapter not written yet
        if _key not in str(_ex):
            raise
        continue
    for _k, (_fid, _name, _desc, _fn) in enumerate(_mod.FINISHES):
        assert len(_desc) <= 140, (_fid, len(_desc))
        TABLE.append(dict(id=_fid, name=_name, chapter=_key, desc=_desc, fn=_fn,
                          seed=7000 + _ci * 1000 + _k * 37 + 11))

BY_ID = {r["id"]: r for r in TABLE}
