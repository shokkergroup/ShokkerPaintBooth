"""
engine/overlay_context.py - Per-zone overlay scale (avoids editing shokker_engine_v2 in many places)
=====================================================================================================
The engine sets overlay_scale here at the start of each zone; engine/overlay.py (via the wrapper
in shokker_engine_v2) reads it. So second_base_scale is wired with minimal touches to the big file.
"""

# 0.10–5.0: set by build_multi_zone at start of each zone from zone.get("second_base_scale", 1.0)
overlay_scale = 1.0
