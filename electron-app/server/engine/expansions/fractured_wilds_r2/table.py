# -*- coding: utf-8 -*-
"""FRACTURED WILDS R2 - the 110-row table (id, name, chapter, desc, fn, seed).

[S20 2026-10-12 owner: Fractured Wilds rebuild] Descriptions say what the
finish LOOKS like (<= 140 chars). Chapter order is the picker order.
"""
from __future__ import annotations

import importlib

CHAPTERS = [
    ("cryptid", "👣 CRYPTID"),
    ("morpho", "🦚 MORPHO"),
    ("bloom", "🌸 BLOOM"),
    ("petri", "🧫 PETRI"),
]
BLURB = ("One hundred and ten nature finishes: the hides and plumage of things nobody can prove exist, "
         "structural colour in feathers, shells and stones, one plant per finish and one microbe per finish. "
         "Every one is its own design.")

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
                          seed=9000 + _ci * 1000 + _k * 37 + 11))

BY_ID = {r["id"]: r for r in TABLE}
