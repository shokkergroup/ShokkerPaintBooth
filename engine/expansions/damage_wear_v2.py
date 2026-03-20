# -*- coding: utf-8 -*-
"""Damage & Wear v2 — 14 physics-based pattern entries. Loads from _staging; wraps paint_fns for scalar bb."""
import numpy as np
import os
import importlib.util


def _ensure_bb_2d(shape, bb):
    """Expand scalar or 0-d bb to (H,W) so paint_fns can use bb[:,:,np.newaxis]."""
    if np.isscalar(bb) or (hasattr(bb, "ndim") and bb.ndim == 0):
        return np.full((shape[0], shape[1]), float(bb), dtype=np.float32)
    return bb


def _wrap_paint_bb(fn):
    """Wrap a pattern paint_fn so it accepts scalar bb from the engine."""
    def wrapped(paint, shape, mask, seed, pm, bb):
        bb = _ensure_bb_2d(shape, bb)
        return fn(paint, shape, mask, seed, pm, bb)
    return wrapped


def _load_staging_damage():
    """Load DAMAGE_WEAR_PATTERNS from _staging/pattern_upgrades/damage_wear_v2.py."""
    this_dir = os.path.dirname(os.path.abspath(__file__))
    v5_root = os.path.normpath(os.path.join(this_dir, "..", ".."))
    staging_path = os.path.join(v5_root, "_staging", "pattern_upgrades", "damage_wear_v2.py")
    if not os.path.isfile(staging_path):
        return {}
    spec = importlib.util.spec_from_file_location("damage_wear_v2_staging", staging_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "DAMAGE_WEAR_PATTERNS", {})


_raw_damage = _load_staging_damage()
DAMAGE_WEAR_PATTERNS = {}
for pid, entry in _raw_damage.items():
    DAMAGE_WEAR_PATTERNS[pid] = {
        "texture_fn": entry["texture_fn"],
        "paint_fn": _wrap_paint_bb(entry["paint_fn"]),
        "variable_cc": entry.get("variable_cc", False),
        "desc": entry.get("desc", ""),
    }
