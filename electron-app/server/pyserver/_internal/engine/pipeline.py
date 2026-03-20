"""
engine/pipeline.py - Render Pipeline
====================================
full_render_pipeline, preview_render, render_zones.

During V5 transition, re-exports from shokker_engine_v2.
Future: Full implementation will live here (extracted from monolith).
"""

from shokker_engine_v2 import (
    full_render_pipeline,
    preview_render,
)

# render_zones is internal - full_render_pipeline and preview_render use it
# Expose if needed: render_zones = getattr(__import__('shokker_engine_v2'), 'render_zones', None)

__all__ = [
    "full_render_pipeline",
    "preview_render",
]
