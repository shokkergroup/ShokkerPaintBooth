"""
Shokker Engine V5 - Package Entry Point
========================================
Clean modular architecture. Each module has ONE job.

MODULE MAP - go here to fix things:
  core.py          → Noise, field generation, TGA writers, color analysis, masking
  spec_paint.py    → Standard spec_/paint_ implementations (gloss, matte, metallic, carbon, etc.)
  color_shift.py   → ALL Color Shift: adaptive (CS Cool), presets (Deep Ocean), duo (75 pairs)
  fusions.py       → ALL Fusions: Metallic Halos, Sparkle, Texture, Tri-Zone, etc.
  finishes.py      → All standard finish spec/paint functions (gloss, metallic, pearl, etc.)
  arsenal.py       → 24K Arsenal expansion bases/patterns/specials
  paradigm.py      → PARADIGM impossible materials
  registry.py      → BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY (single source of truth)
  base_registry_data.py → 58 bases (canonical); registry merges BLEND_BASES from monolith
  pattern_registry_data.py → PATTERN_REGISTRY (re-export from monolith)
  compose.py       → compose_finish, compose_finish_stacked, compose_paint_mod, compose_paint_mod_stacked
  render.py        → render_generic_finish (full impl; monolith imports from here)
  pipeline.py      → full_render_pipeline, preview_render (re-exports)

USAGE IN server.py:
  import engine
  engine.BASE_REGISTRY, engine.PATTERN_REGISTRY, engine.MONOLITHIC_REGISTRY
  engine.render_zones(...), engine.preview_render(...)
"""

# Re-export the full engine interface for server.py backward compatibility
# server.py does: import shokker_engine_v2 as engine
# V5 server.py will do: import engine
# All the same attributes are available.
#
# Registries are loaded LAZILY to avoid circular import:
# monolith -> engine.spec_paint -> engine package -> registry -> monolith.
# When first accessing BASE_REGISTRY etc., we load registry (which loads monolith).

_registry_loaded = None

def _get_registries():
    global _registry_loaded
    if _registry_loaded is None:
        from engine.registry import (
            BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY,
            FINISH_REGISTRY, FUSION_REGISTRY,
        )
        _registry_loaded = (BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY,
                            FINISH_REGISTRY, FUSION_REGISTRY)
    return _registry_loaded

# Core rendering functions needed by server.py
from engine.core import (
    write_tga_32bit,
    write_tga_24bit,
    multi_scale_noise,
    hsv_to_rgb_vec,
    get_mgrid,
    INTENSITY,
)

# NOTE: The main render pipeline functions (render_zones, preview_render, etc.)
# will be imported from the engine once they are extracted.
# For now, to maintain compatibility during the V5 transition, we fall back
# to importing from shokker_engine_v2 for complex pipeline functions.
# Lazy import to avoid circular import when shokker_engine_v2 does "from engine.utils import ...".
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_legacy_engine = None

def _get_legacy_engine():
    global _legacy_engine
    if _legacy_engine is None:
        import shokker_engine_v2 as _legacy_engine
    return _legacy_engine

@property
def _lazy_full_render_pipeline():
    return _get_legacy_engine().full_render_pipeline

# Expose legacy pipeline and registries as module attributes (lazy)
def __getattr__(name):
    # Registries - load on first access so monolith can finish loading first
    if name in ('BASE_REGISTRY', 'PATTERN_REGISTRY', 'MONOLITHIC_REGISTRY', 'FINISH_REGISTRY', 'FUSION_REGISTRY'):
        from engine.registry import (
            BASE_REGISTRY as _br, PATTERN_REGISTRY as _pr, MONOLITHIC_REGISTRY as _mr,
            FINISH_REGISTRY as _fr, FUSION_REGISTRY as _fu,
        )
        mod = __import__(__name__)
        mod.BASE_REGISTRY = _br
        mod.PATTERN_REGISTRY = _pr
        mod.MONOLITHIC_REGISTRY = _mr
        mod.FINISH_REGISTRY = _fr
        mod.FUSION_REGISTRY = _fu
        return {'BASE_REGISTRY': _br, 'PATTERN_REGISTRY': _pr, 'MONOLITHIC_REGISTRY': _mr,
                'FINISH_REGISTRY': _fr, 'FUSION_REGISTRY': _fu}[name]
    if name in ('compose_finish', 'compose_finish_stacked', 'compose_paint_mod', 'compose_paint_mod_stacked'):
        from engine.compose import (
            compose_finish as _cf, compose_finish_stacked as _cfs,
            compose_paint_mod as _cpm, compose_paint_mod_stacked as _cpms,
        )
        return {'compose_finish': _cf, 'compose_finish_stacked': _cfs,
                'compose_paint_mod': _cpm, 'compose_paint_mod_stacked': _cpms}[name]
    if name in ('full_render_pipeline', 'preview_render', 'render_zones', 'apply_zone_finish', '_sample_zone_color', 'INTENSITY'):
        if name in ('full_render_pipeline', 'preview_render', 'render_zones'):
            from engine.pipeline import full_render_pipeline as _frp, preview_render as _pr
            return _frp if name == 'full_render_pipeline' or name == 'render_zones' else _pr
        e = _get_legacy_engine()
        if name == 'apply_zone_finish':
            return getattr(e, 'apply_single_finish', None)
        if name == '_sample_zone_color':
            return getattr(e, '_sample_zone_color', None)
        if name == 'INTENSITY':
            return e.INTENSITY
    if name == 'render_generic_finish':
        from engine.render import render_generic_finish as _rgf
        return _rgf
    # Fallback: pass through any other attribute from monolith (build_multi_zone, etc.)
    e = _get_legacy_engine()
    if hasattr(e, name):
        return getattr(e, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
