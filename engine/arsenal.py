"""
engine/arsenal.py - 24K Arsenal Expansion
===========================================
185 bases + 164 patterns + 240 specials from the 24K Arsenal.
These are the premium finish library entries.

STRUCTURE:
  24K Arsenal entries are defined in shokker_24k_expansion.py
  This module provides clean access and override points.

FIX GUIDE:
  "Arsenal base X renders wrong"   → shokker_24k_expansion.py → BASE_REGISTRY["X"]
  "Arsenal pattern Y wrong size"   → shokker_24k_expansion.py → PATTERN_REGISTRY["Y"]
  "Arsenal special Z bad color"    → shokker_24k_expansion.py → MONOLITHIC_REGISTRY["Z"]

  To override a SPECIFIC entry in V5 without touching the expansion:
    from engine.arsenal import ARSENAL_BASE_REGISTRY
    ARSENAL_BASE_REGISTRY["my_base"] = (my_spec_fn, my_paint_fn)

STATUS: Delegated to shokker_24k_expansion.py (stable).
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import shokker_24k_expansion as _exp24k

    ARSENAL_BASE_REGISTRY = getattr(_exp24k, 'BASE_REGISTRY', {})
    ARSENAL_PATTERN_REGISTRY = getattr(_exp24k, 'PATTERN_REGISTRY', {})
    ARSENAL_MONOLITHIC_REGISTRY = getattr(_exp24k, 'MONOLITHIC_REGISTRY', {})
    get_expansion_group_map = _exp24k.get_expansion_group_map
    get_expansion_counts = _exp24k.get_expansion_counts
    _ARSENAL_LOADED = True

except Exception as _ex:
    print(f"[V5 Arsenal] Warning: Could not load 24K Arsenal: {_ex}")
    ARSENAL_BASE_REGISTRY = {}
    ARSENAL_PATTERN_REGISTRY = {}
    ARSENAL_MONOLITHIC_REGISTRY = {}
    def get_expansion_group_map(): return {}
    def get_expansion_counts(): return {}
    _ARSENAL_LOADED = False
