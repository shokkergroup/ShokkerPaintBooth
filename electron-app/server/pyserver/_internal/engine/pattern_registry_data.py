"""
engine/pattern_registry_data.py - Canonical PATTERN_REGISTRY source.
During V5 transition, re-exports from shokker_engine_v2.
Future: Define dict here with texture_fn/paint_fn imported from engine modules.
"""

from shokker_engine_v2 import PATTERN_REGISTRY

__all__ = ["PATTERN_REGISTRY"]
