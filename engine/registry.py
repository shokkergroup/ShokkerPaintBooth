"""
engine/registry.py - Single Source of Truth for ALL Finish IDs
================================================================
This is the ONLY place where finish IDs map to functions.

REGISTRIES:
  BASE_REGISTRY      → base finishes (spec_fn, paint_fn) - every combinable base
  PATTERN_REGISTRY   → pattern overlays (spec_fn, pattern_fn)
  MONOLITHIC_REGISTRY→ one-shot finishes (spec_fn, paint_fn) - CS, Fusions, effects
  FINISH_REGISTRY    → legacy finish IDs (backward compat)
  FUSION_REGISTRY    → fusions subset of MONOLITHIC_REGISTRY

HOW TO ADD A NEW FINISH:
  1. Write the paint_fn and spec_fn in the appropriate module
  2. Import those functions HERE
  3. Add ONE line: MONOLITHIC_REGISTRY["my_finish_id"] = (spec_fn, paint_fn)
  4. Add UI entry in paint-booth-v2.html
  Done. Nothing else to change.

HOW TO DEBUG "finish not found":
  Print sorted(BASE_REGISTRY.keys()) or sorted(MONOLITHIC_REGISTRY.keys())
  If the ID isn't there, it's not registered here yet.
"""

import sys
import os

# Add parent to path for legacy engine fallback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ================================================================
# STRATEGY: During V5 transition, we delegate to shokker_engine_v2
# for all registries and extend with V5 modules.
# Once transition is complete, all registry entries move here.
# ================================================================

def _build_registries():
    """Build all registries. Called once at import time."""

    # BASE_REGISTRY: built from engine modules (58 bases + 10 BLEND_BASES from monolith)
    from engine.base_registry_data import BASE_REGISTRY as _base_data
    base_reg = dict(_base_data)

    # Legacy engine: mono_reg, finish_reg, fusion_reg, BLEND_BASES
    try:
        import shokker_engine_v2 as _e
        base_reg.update(_e.BLEND_BASES)
        from engine.pattern_registry_data import PATTERN_REGISTRY as _pattern_data
        pattern_reg = dict(_pattern_data)
        mono_reg = dict(_e.MONOLITHIC_REGISTRY)
        finish_reg = dict(getattr(_e, 'FINISH_REGISTRY', {}))
        fusion_reg = dict(getattr(_e, 'FUSION_REGISTRY', {}))
    except Exception as ex:
        print(f"[V5 Registry] Warning: Could not load from shokker_engine_v2: {ex}")
        pattern_reg = {}
        mono_reg = {}
        finish_reg = {}
        fusion_reg = {}

    # ================================================================
    # PATTERN EXPANSION - Decades, Flames, Music, Astro, Hero, Sports.
    # Each expansion ID has its own texture_fn + paint_fn (engine/expansion_patterns.py).
    # ================================================================
    try:
        from engine.pattern_expansion import NEW_PATTERNS
        pattern_reg.update(NEW_PATTERNS)
        print(f"[V5 Registry] Pattern expansion: {len(NEW_PATTERNS)} patterns (built individually)")
    except Exception as ex:
        print(f"[V5 Registry] Warning: pattern_expansion failed: {ex}")

    # ================================================================
    # STAGING DECADES — 20 unique patterns per decade (replace generic 10)
    # From _staging/pattern_upgrades/decades_*_v2.py (tiled, named).
    # ================================================================
    _decade_prefixes = ("decade_50s_", "decade_60s_", "decade_70s_", "decade_80s_", "decade_90s_")
    for pid in list(pattern_reg.keys()):
        if any(pid.startswith(p) for p in _decade_prefixes):
            del pattern_reg[pid]
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _staging_pattern_dir = os.path.join(_root, "_staging", "pattern_upgrades")
    _staging_modules = [
        ("decades_50s_v2", "DECADES_50S_PATTERNS"),
        ("decades_60s_v2", "DECADES_60S_PATTERNS"),
        ("decades_70s_v2", "DECADES_70S_PATTERNS"),
        ("decades_80s_v2", "DECADES_80S_PATTERNS"),
        ("decades_90s_v2", "DECADES_90S_PATTERNS"),
    ]
    if os.path.isdir(_staging_pattern_dir) and _staging_pattern_dir not in sys.path:
        sys.path.insert(0, _staging_pattern_dir)
    for _mod_name, _var_name in _staging_modules:
        try:
            _mod = __import__(_mod_name, fromlist=[_var_name])
            _pats = getattr(_mod, _var_name, {})
            pattern_reg.update(_pats)
        except Exception as _ex:
            print(f"[V5 Registry] Warning: Staging decades {_mod_name} failed: {_ex}")
    _n_dec = sum(1 for k in pattern_reg if any(k.startswith(p) for p in _decade_prefixes))
    if _n_dec:
        print(f"[V5 Registry] Staging decades: {_n_dec} patterns (20 per decade)")

    # ================================================================
    # IMAGE-BASED PATTERNS (DYNAMIC LOAD)
    # Scans the assets/patterns directory for any .png or .jpg
    # and registers them blindly as image patterns. No more missing file errors!
    # Does NOT overwrite if the ID has already been claimed by a procedural implementation.
    # ================================================================
    try:
        from engine.spec_paint import paint_none
        # root_dir: registry lives in engine/, so root is one folder up
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        patterns_dir = os.path.join(root_dir, "assets", "patterns")
        
        if os.path.exists(patterns_dir):
            for root, dirs, files in os.walk(patterns_dir):
                for file_name in files:
                    if file_name.lower().endswith((".png", ".jpg", ".jpeg")):
                        # e.g., 'abstract_experimental/biomechanical.png'
                        full_path = os.path.join(root, file_name)
                        rel_path = os.path.relpath(full_path, root_dir)
                        # Normalize to forward slashes for the server paths
                        rel_path = rel_path.replace("\\", "/")
                        
                        pid = os.path.splitext(file_name)[0]
                        
                        # Only register it as an image if it isn't already handled procedurally
                        if pid not in pattern_reg:
                            pattern_reg[pid] = {
                                "image_path": rel_path,
                                "paint_fn": paint_none,
                                "desc": f"Image-based pattern - {pid}"
                            }
    except Exception as ex:
        print(f"[V5 Registry] Warning: Dynamic image pattern load failed: {ex}")

    # ================================================================
    # USER PATTERN EXAMPLES (basespatterns_examples/patternexamples)
    # Main folder only (no subfolders) - exact image file patterns.
    # ================================================================
    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        examples_dir = os.path.join(root_dir, "basespatterns_examples", "patternexamples")
        if os.path.isdir(examples_dir):
            for file_name in os.listdir(examples_dir):
                if not file_name.lower().endswith((".png", ".jpg", ".jpeg")):
                    continue
                full_path = os.path.join(examples_dir, file_name)
                if not os.path.isfile(full_path):
                    continue
                rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
                stem = os.path.splitext(file_name)[0]
                pid = stem.replace(" ", "_").replace("(", "").replace(")", "").strip("_")
                if not pid:
                    pid = stem
                if pid not in pattern_reg:
                    pattern_reg[pid] = {
                        "image_path": rel_path,
                        "paint_fn": paint_none,
                        "desc": f"Image pattern: {stem}"
                    }
            n_ex = sum(1 for v in pattern_reg.values() if "patternexamples" in v.get("image_path", ""))
            if n_ex:
                print(f"[V5 Registry] Pattern examples: {n_ex} images from patternexamples")

        # Subfolders of patternexamples (e.g. AbstractExperimental, Skate_Surf)
        if os.path.isdir(examples_dir):
            for sub_root, _sub_dirs, sub_files in os.walk(examples_dir):
                for file_name in sub_files:
                    if not file_name.lower().endswith((".png", ".jpg", ".jpeg")):
                        continue
                    full_path = os.path.join(sub_root, file_name)
                    if not os.path.isfile(full_path):
                        continue
                    rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
                    stem = os.path.splitext(file_name)[0]
                    pid = stem.replace(" ", "_").replace("(", "").replace(")", "").strip("_")
                    if not pid:
                        pid = stem
                    if pid not in pattern_reg:
                        pattern_reg[pid] = {
                            "image_path": rel_path,
                            "paint_fn": paint_none,
                            "desc": f"Image pattern: {stem}"
                        }
            n_sub = sum(1 for v in pattern_reg.values() if "patternexamples" in v.get("image_path", "")) - n_ex
            if n_sub > 0:
                print(f"[V5 Registry] Pattern examples subfolders: {n_sub} images")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Pattern examples load failed: {ex}")

    # ================================================================
    # V5 OVERRIDES - Replace legacy implementations with V5 modules
    # CS functions that have been rewritten (better color accuracy)
    # ================================================================
    try:
        from engine.color_shift import (
            # Adaptive
            paint_cs_cool, spec_cs_cool,
            paint_cs_warm, spec_cs_warm,
            paint_cs_complementary, spec_cs_complementary,
            paint_cs_monochrome, spec_cs_monochrome,
            paint_cs_subtle, spec_cs_subtle,
            paint_cs_rainbow, spec_cs_rainbow,
            paint_cs_vivid, spec_cs_vivid,
            paint_cs_extreme, spec_cs_extreme,
            paint_cs_triadic, spec_cs_triadic,
            paint_cs_split, spec_cs_split,
            paint_cs_neon_shift, spec_cs_neon_shift,
            paint_cs_ocean_shift, spec_cs_ocean_shift,
            paint_cs_chrome_shift, spec_cs_chrome_shift,
            paint_cs_earth, spec_cs_earth,
            paint_cs_prism_shift, spec_cs_prism_shift,
            # Fixed presets
            paint_cs_cool, spec_cs_cool,
            paint_cs_deepocean, spec_cs_deepocean,
            paint_cs_solarflare, spec_cs_solarflare,
            paint_cs_inferno, spec_cs_inferno,
            paint_cs_nebula, spec_cs_nebula,
            paint_cs_mystichrome, spec_cs_mystichrome,
            paint_cs_supernova, spec_cs_supernova,
            paint_cs_emerald, spec_cs_emerald,
            # Other presets (delegated to legacy)
            paint_cs_candypaint, spec_cs_candypaint,
            paint_cs_oilslick, spec_cs_oilslick,
            paint_cs_rosegold, spec_cs_rosegold,
            paint_cs_goldrush, spec_cs_goldrush,
            paint_cs_toxic, spec_cs_toxic,
            paint_cs_darkflame, spec_cs_darkflame,
        )

        # Override CS Adaptive entries
        cs_adaptive_overrides = {
            "cs_cool":         (spec_cs_cool,         paint_cs_cool),
            "cs_warm":         (spec_cs_warm,         paint_cs_warm),
            "cs_complementary":(spec_cs_complementary,paint_cs_complementary),
            "cs_monochrome":   (spec_cs_monochrome,   paint_cs_monochrome),
            "cs_subtle":       (spec_cs_subtle,       paint_cs_subtle),
            "cs_rainbow":      (spec_cs_rainbow,      paint_cs_rainbow),
            "cs_vivid":        (spec_cs_vivid,        paint_cs_vivid),
            "cs_extreme":      (spec_cs_extreme,      paint_cs_extreme),
            "cs_triadic":      (spec_cs_triadic,      paint_cs_triadic),
            "cs_split":        (spec_cs_split,        paint_cs_split),
            "cs_neon_shift":   (spec_cs_neon_shift,   paint_cs_neon_shift),
            "cs_ocean_shift":  (spec_cs_ocean_shift,  paint_cs_ocean_shift),
            "cs_chrome_shift": (spec_cs_chrome_shift, paint_cs_chrome_shift),
            "cs_earth":        (spec_cs_earth,        paint_cs_earth),
            "cs_prism_shift":  (spec_cs_prism_shift,  paint_cs_prism_shift),
        }
        mono_reg.update(cs_adaptive_overrides)

        # Override CS Preset entries
        cs_preset_overrides = {
            "cs_deepocean":    (spec_cs_deepocean,    paint_cs_deepocean),
            "cs_solarflare":   (spec_cs_solarflare,   paint_cs_solarflare),
            "cs_inferno":      (spec_cs_inferno,      paint_cs_inferno),
            "cs_nebula":       (spec_cs_nebula,       paint_cs_nebula),
            "cs_mystichrome":  (spec_cs_mystichrome,  paint_cs_mystichrome),
            "cs_supernova":    (spec_cs_supernova,    paint_cs_supernova),
            "cs_emerald":      (spec_cs_emerald,      paint_cs_emerald),
            "cs_candypaint":   (spec_cs_candypaint,   paint_cs_candypaint),
            "cs_oilslick":     (spec_cs_oilslick,     paint_cs_oilslick),
            "cs_rosegold":     (spec_cs_rosegold,     paint_cs_rosegold),
            "cs_goldrush":     (spec_cs_goldrush,     paint_cs_goldrush),
            "cs_toxic":        (spec_cs_toxic,        paint_cs_toxic),
            "cs_darkflame":    (spec_cs_darkflame,    paint_cs_darkflame),
        }
        mono_reg.update(cs_preset_overrides)

        # Override CS Duo entries (all 75)
        from engine.color_shift import build_cs_duo_registry
        duo_entries = build_cs_duo_registry()
        mono_reg.update(duo_entries)

        print(f"[V5 Registry] CS overrides applied: {len(cs_adaptive_overrides)} adaptive, "
              f"{len(cs_preset_overrides)} presets, {len(duo_entries)} duos")

    except Exception as ex:
        print(f"[V5 Registry] Warning: CS override failed: {ex}")
        import traceback
        traceback.print_exc()

    # ================================================================
    # FUSIONS - apply any V5 overrides from engine.fusions
    # ================================================================
    try:
        from engine.fusions import FUSION_REGISTRY as _fusions_v5
        if _fusions_v5:
            mono_reg.update(_fusions_v5)
            fusion_reg.update(_fusions_v5)
    except Exception as _fex:
        pass  # Fusions stay as loaded from legacy

    # Merge fusions into mono_reg if not already there
    for k, v in fusion_reg.items():
        mono_reg.setdefault(k, v)

    # ================================================================
    # V5 NATIVE FINISHES - New bases written directly in engine/finishes.py
    # These use the full CC range (17-255) for CC-exploitation effects.
    # ================================================================
    try:
        from engine.finishes import V5_BASE_FINISHES
        if V5_BASE_FINISHES:
            n_before = len(mono_reg)
            mono_reg.update(V5_BASE_FINISHES)
            print(f"[V5 Registry] Native finishes: {len(V5_BASE_FINISHES)} new bases added "
                  f"({len(mono_reg) - n_before} net new in monolithic)")
    except Exception as _fex:
        print(f"[V5 Registry] Warning: V5 native finishes failed: {_fex}")

    # ================================================================
    # PARADIGM EXPANSION - Physics-exploiting materials
    # ================================================================
    try:
        import engine.expansions.paradigm as _paradigm
        class _RegistryMod:
            pass
        _reg_mod = _RegistryMod()
        _reg_mod.BASE_REGISTRY = base_reg
        _reg_mod.PATTERN_REGISTRY = pattern_reg
        _reg_mod.MONOLITHIC_REGISTRY = mono_reg
        _paradigm.integrate_paradigm(_reg_mod)
    except Exception as ex:
        print(f"[V5 Registry] Warning: Paradigm load failed: {ex}")

    # ================================================================
    # COLOR CLASH — 25 harsh contrasting gradient finishes
    # ================================================================
    try:
        import engine.expansions.color_clash as _color_clash
        _cc_mod = _RegistryMod()
        _cc_mod.MONOLITHIC_REGISTRY = mono_reg
        _color_clash.integrate_color_clash(_cc_mod)
    except Exception as ex:
        print(f"[V5 Registry] Warning: Color Clash load failed: {ex}")

    # ================================================================
    # SHOKK PATTERNS — Data stream / glitch / digital corruption
    # ================================================================
    try:
        from engine.expansions.shokk_patterns import SHOKK_PATTERNS
        pattern_reg.update(SHOKK_PATTERNS)
        print(f"[V5 Registry] SHOKK patterns: {len(SHOKK_PATTERNS)} data-stream/glitch patterns loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: SHOKK patterns load failed: {ex}")

    # ================================================================
    # DUAL COLOR SHIFT > COLORSHOXX (angle-dependent color shifting)
    # Now registers under cx_* IDs with dualshift_* backward compat
    # ================================================================
    try:
        from engine.dual_color_shift import DUAL_SHIFT_MONOLITHICS
        _ds_added = 0
        for k, v in DUAL_SHIFT_MONOLITHICS.items():
            if k not in mono_reg:
                mono_reg[k] = v
                _ds_added += 1
        if _ds_added:
            print(f"[V5 Registry] Dual Shift > COLORSHOXX: {_ds_added} monolithics registered")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Dual Color Shift load failed: {ex}")

    # ================================================================
    # CS DUO > MICRO-FLAKE CONVERSION (replaces old flat-gradient duos)
    # ================================================================
    try:
        from engine.micro_flake_shift import CS_DUO_MICRO_MONOLITHICS
        _csd_added = 0
        for k, v in CS_DUO_MICRO_MONOLITHICS.items():
            mono_reg[k] = v  # Overwrite old CS Duo entries with micro-flake versions
            _csd_added += 1
        if _csd_added:
            print(f"[V5 Registry] CS Duo to Micro-Flake: {_csd_added} monolithics upgraded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: CS Duo micro-flake conversion failed: {ex}")

    # ================================================================
    # MICRO-FLAKE COLOR SHIFT — per-flake micro shimmer (now part of COLORSHOXX)
    # ================================================================
    try:
        from engine.micro_flake_shift import MICRO_SHIFT_MONOLITHICS
        _ms_added = 0
        for k, v in MICRO_SHIFT_MONOLITHICS.items():
            if k not in mono_reg:
                mono_reg[k] = v
                _ms_added += 1
        if _ms_added:
            print(f"[V5 Registry] Micro-Flake > COLORSHOXX: {_ms_added} monolithics registered")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Micro-Flake Shift load failed: {ex}")

    # ================================================================
    # COLORSHOXX WAVE 4 — New multi-color flake shifts
    # ================================================================
    try:
        from engine.micro_flake_shift import CX_WAVE4_MONOLITHICS
        _w4_added = 0
        for k, v in CX_WAVE4_MONOLITHICS.items():
            if k not in mono_reg:
                mono_reg[k] = v
                _w4_added += 1
        if _w4_added:
            print(f"[V5 Registry] COLORSHOXX Wave 4: {_w4_added} new finishes registered")
    except Exception as ex:
        print(f"[V5 Registry] Warning: COLORSHOXX Wave 4 load failed: {ex}")

    # ================================================================
    # COLORSHOXX HYPERFLIP — perceptual opponent-pixel color flip
    # ================================================================
    try:
        from engine.perceptual_color_shift import HYPERFLIP_MONOLITHICS
        _hf_added = 0
        for k, v in HYPERFLIP_MONOLITHICS.items():
            mono_reg[k] = v
            _hf_added += 1
        if _hf_added:
            print(f"[V5 Registry] COLORSHOXX HyperFlip: {_hf_added} perceptual flip finishes registered")
    except Exception as ex:
        print(f"[V5 Registry] Warning: COLORSHOXX HyperFlip load failed: {ex}")

    return base_reg, pattern_reg, mono_reg, finish_reg, fusion_reg


# Build all registries at import time
BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY, FINISH_REGISTRY, FUSION_REGISTRY = _build_registries()

print(f"[V5 Registry] READY - "
      f"{len(BASE_REGISTRY)} bases, "
      f"{len(PATTERN_REGISTRY)} patterns, "
      f"{len(MONOLITHIC_REGISTRY)} monolithics "
      f"({len(FUSION_REGISTRY)} fusions)")
