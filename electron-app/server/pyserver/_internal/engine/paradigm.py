"""
engine/paradigm.py - PARADIGM Impossible Materials
====================================================
37 PARADIGM impossible material finishes.
These are spec-only extreme materials that push iRacing's PBR limits.

CATEGORIES:
  PARADIGM BASES (10)     → The impossible base materials
  PARADIGM PATTERNS (10)  → Impossible pattern overlays
  PARADIGM SPECIALS (17)  → Unique impossible one-shot finishes

FIX GUIDE:
  "A PARADIGM base renders wrong" → shokker_paradigm_expansion.py → BASE_REGISTRY
  "A PARADIGM pattern wrong"      → shokker_paradigm_expansion.py → PATTERN_REGISTRY
  "A PARADIGM special wrong"      → shokker_paradigm_expansion.py → MONOLITHIC_REGISTRY
  In V5: add override below after fixing in paradigm expansion.

STATUS: Delegated to shokker_paradigm_expansion.py (stable, no known issues).
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import shokker_paradigm_expansion as _paradigm_exp

    PARADIGM_BASE_REGISTRY = getattr(_paradigm_exp, 'BASE_REGISTRY', {})
    PARADIGM_PATTERN_REGISTRY = getattr(_paradigm_exp, 'PATTERN_REGISTRY', {})
    PARADIGM_MONOLITHIC_REGISTRY = getattr(_paradigm_exp, 'MONOLITHIC_REGISTRY', {})
    get_paradigm_group_map = _paradigm_exp.get_paradigm_group_map
    _PARADIGM_LOADED = True

except Exception as _ex:
    print(f"[V5 Paradigm] Warning: Could not load paradigm: {_ex}")
    PARADIGM_BASE_REGISTRY = {}
    PARADIGM_PATTERN_REGISTRY = {}
    PARADIGM_MONOLITHIC_REGISTRY = {}
    def get_paradigm_group_map(): return {}
    _PARADIGM_LOADED = False
