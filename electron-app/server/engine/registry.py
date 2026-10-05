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

# [2026-09-05 codebase-health F1/F3] _build_registries() used to run TWICE per boot in the server's
# import order: once here at import (line ~1130) and again from shokker_engine_v2.py's REGISTRY
# MERGE block (~line 10490), which first-wins-merges the result into the legacy dicts. Both calls
# saw the same inputs and produced the same content (measured: key -> function-identity dump is
# byte-identical), so the second call now returns the first build's objects. Saves ~0.7-1.0 s and
# 82 duplicated log lines per boot. A re-entrant call DURING the first build (registry-first
# import order used by scripts) still builds, exactly as before.
_BUILT = None


def _build_registries():
    global _BUILT
    # SPB_REGISTRY_REBUILD=1 restores the pre-2026-09-05 double build (verification/A-B only).
    if _BUILT is not None and not os.environ.get("SPB_REGISTRY_REBUILD"):
        return _BUILT
    _BUILT = _build_registries_once()
    return _BUILT


def _build_registries_once():
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
        raise RuntimeError(
            "V5 pattern expansion registry failed; refusing to continue with "
            "missing expansion patterns"
        ) from ex

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
            # SPB-105 color routing tick3: retain the authored color callback
            # before material/detail wrappers replace the active paint callback.
            pattern_reg.update({pid: dict(entry,
                _spb_authored_paint_fn=entry.get("paint_fn"),
                _spb_authored_texture_fn=entry.get("texture_fn"))
                for pid, entry in _pats.items()})
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
    # FUSIONS — engine.expansions.fusions (150 paradigm + 50 spectrum shift)
    # ================================================================
    try:
        from engine.expansions.fusions import FUSION_REGISTRY as _fexp_fusions
        if _fexp_fusions:
            mono_reg.update(_fexp_fusions)
            fusion_reg.update(_fexp_fusions)
            print(f"[V5 Registry] Fusions expansion: {len(_fexp_fusions)} loaded")
    except Exception as _fex:
        print(f"[V5 Registry] Warning: Fusions expansion load failed: {_fex}")
    try:
        from engine.fusions import FUSION_REGISTRY as _fusions_v5
        if _fusions_v5:
            mono_reg.update(_fusions_v5)
            fusion_reg.update(_fusions_v5)
    except Exception:
        pass

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
    # SHOKKER LIVING FINISHES - phase-field motion illusion materials
    # ================================================================
    try:
        from engine.expansions.living_finishes import LIVING_FINISH_REGISTRY
        mono_reg.update(LIVING_FINISH_REGISTRY)
        print(f"[V5 Registry] Living Finishes: {len(LIVING_FINISH_REGISTRY)} monolithics loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Living Finishes load failed: {ex}")

    # ================================================================
    # OWNER REVIEW ATMOSPHERE - SPB-26 visual review rebuilds
    # ================================================================
    try:
        from engine.expansions.owner_review_atmosphere import OWNER_REVIEW_ATMOSPHERE_MONOLITHICS
        mono_reg.update(OWNER_REVIEW_ATMOSPHERE_MONOLITHICS)
        print(f"[V5 Registry] Owner Review Atmosphere: {len(OWNER_REVIEW_ATMOSPHERE_MONOLITHICS)} monolithics loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Owner Review Atmosphere load failed: {ex}")

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

    # ================================================================
    # CULTURAL / RISING SUN - image-authored paint/spec finish set
    # ================================================================
    try:
        from engine.paint_v2.cultural_rising_sun import RISING_SUN_MONOLITHICS
        mono_reg.update(RISING_SUN_MONOLITHICS)
        print(f"[V5 Registry] Cultural / Rising Sun: {len(RISING_SUN_MONOLITHICS)} monolithics loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Cultural / Rising Sun load failed: {ex}")

    # ================================================================
    # CULTURAL / VIVA MEXICO - image-authored paint/spec finish set
    # ================================================================
    try:
        from engine.paint_v2.cultural_viva_mexico import VIVA_MEXICO_MONOLITHICS
        mono_reg.update(VIVA_MEXICO_MONOLITHICS)
        print(f"[V5 Registry] Cultural / Viva Mexico: {len(VIVA_MEXICO_MONOLITHICS)} monolithics loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Cultural / Viva Mexico load failed: {ex}")

    # ================================================================
    # CULTURAL / FORBIDDEN DRAGON - image paint + Viva Mexico spec pipeline
    # ================================================================
    try:
        from engine.paint_v2.cultural_forbidden_dragon import FORBIDDEN_DRAGON_MONOLITHICS
        mono_reg.update(FORBIDDEN_DRAGON_MONOLITHICS)
        print(f"[V5 Registry] Cultural / Forbidden Dragon: {len(FORBIDDEN_DRAGON_MONOLITHICS)} monolithics loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Cultural / Forbidden Dragon load failed: {ex}")

    # ================================================================
    # CULTURAL / LET FREEDOM RING - fully-procedural patriotic monolithics
    # (no image plates: renders for every buyer with zero downloads)
    # ================================================================
    try:
        from engine.paint_v2.cultural_let_freedom_ring import LFR_MONOLITHICS
        mono_reg.update(LFR_MONOLITHICS)
        print(f"[V5 Registry] Cultural / Let Freedom Ring: {len(LFR_MONOLITHICS)} monolithics loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Cultural / Let Freedom Ring load failed: {ex}")

    # ================================================================
    # FABLE - 20 flagship monolithics built on engine/color_science
    # (OKLab ramps, Beer-Lambert candy, quantized interference, flip
    # lattices, hue-travel specs). Fully procedural, no image plates.
    # ================================================================
    try:
        from engine.paint_v2.fable_collection import FABLE_MONOLITHICS
        mono_reg.update(FABLE_MONOLITHICS)
        print(f"[V5 Registry] FABLE: {len(FABLE_MONOLITHICS)} monolithics loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: FABLE load failed: {ex}")

    # ================================================================
    # CULTURAL / GRUNGE & FUN - image paint + Viva Mexico spec pipeline
    # ================================================================
    try:
        from engine.paint_v2.cultural_grunge_fun import GRUNGE_FUN_MONOLITHICS

        mono_reg.update(GRUNGE_FUN_MONOLITHICS)
        print(f"[V5 Registry] Cultural / Grunge & Fun: {len(GRUNGE_FUN_MONOLITHICS)} monolithics loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Cultural / Grunge & Fun load failed: {ex}")

    # ================================================================
    # MATERIAL WORLD / SOURCE PATTERN PLATES - owner 2026-05-30 real-source plates
    # ================================================================
    try:
        from engine.paint_v2.reference_pattern_plates import REFERENCE_PATTERN_PLATE_MONOLITHICS

        mono_reg.update(REFERENCE_PATTERN_PLATE_MONOLITHICS)
        print(f"[V5 Registry] Source Pattern Plates: {len(REFERENCE_PATTERN_PLATE_MONOLITHICS)} monolithics loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Source Pattern Plates load failed: {ex}")

    # ================================================================
    # CULTURAL / UNION JACKED - image paint + scratch-built procedural spec
    # ================================================================
    try:
        from engine.paint_v2.cultural_union_jacked import UNION_JACKED_MONOLITHICS
        mono_reg.update(UNION_JACKED_MONOLITHICS)
        print(f"[V5 Registry] Cultural / Union Jacked: {len(UNION_JACKED_MONOLITHICS)} monolithics loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Cultural / Union Jacked load failed: {ex}")

    # ================================================================
    # ★ MORTAL SHOKK V2 — author 4K plates + scratch spec + VM pipeline (manifest)
    # ================================================================
    try:
        from engine.paint_v2.cultural_mortal_shokk import (
            MORTAL_SHOKK_MONOLITHICS,
            mortal_shokk_base_registry_bridge,
        )
        mono_reg.update(MORTAL_SHOKK_MONOLITHICS)
        base_reg.update(mortal_shokk_base_registry_bridge())
        if MORTAL_SHOKK_MONOLITHICS:
            print(f"[V5 Registry] Mortal Shokk V2: {len(MORTAL_SHOKK_MONOLITHICS)} monolithics loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Mortal Shokk V2 load failed: {ex}")

    # ================================================================
    # GUEST DESIGNERS — author albedo + metallic + roughness plates per manifest
    # ================================================================
    try:
        from engine.paint_v2.guest_designers import GUEST_DESIGNER_MONOLITHICS
        mono_reg.update(GUEST_DESIGNER_MONOLITHICS)
        if GUEST_DESIGNER_MONOLITHICS:
            print(f"[V5 Registry] Guest Designers: {len(GUEST_DESIGNER_MONOLITHICS)} monolithics loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Guest Designers load failed: {ex}")

    # USER IMPORTS — local AppData library (paint monolithics; patterns/overlays later)
    try:
        from engine.paint_v2.user_imports import register_user_imports
        n_ui = register_user_imports(mono_reg, pattern_reg)
        if n_ui:
            print(f"[V5 Registry] USER IMPORTS: {n_ui} entries loaded")
    except Exception as ex:
        print(f"[V5 Registry] Warning: USER IMPORTS load failed: {ex}")

    # COLORSHOXX AI REFERENCE BATCH — owner 2026-05-27 poster plates + traced spec
    try:
        from engine.paint_v2.cultural_colorshoxx_ai import apply_colorshoxx_ai_registry

        n_ai = apply_colorshoxx_ai_registry(base_reg, mono_reg)
        if n_ai:
            print(f"[V5 Registry] COLORSHOXX AI Reference: {n_ai} finishes wired to image plates")
    except Exception as ex:
        print(f"[V5 Registry] Warning: COLORSHOXX AI Reference load failed: {ex}")

    # 2026-06-03 case-collision dedup: drop the 23 PATTERN ids that are pure case-variants of a
    # LIVE tile (18 PascalCase scanner-mints whose curated lowercase twin is the live tile + 5
    # skate/surf lowercase whose live tile is the PascalCase). Computed by
    # scripts/analyze_case_dups.py against finish-data references; KEEP-BOTH distinct pairs
    # (Art_Deco/art_deco, Mandala/mandala, Mosaic/mosaic) and the registry-only Norse_Rune pair
    # are intentionally NOT removed. These collide as the same file on case-insensitive (Windows)
    # filesystems, so deduping fixes picker dupes + thumbnail cache overwrites.
    _CASE_DUP_REMOVE = (
        "Aztec_Alt1", "Aztec_Alt2", "Basket_Weave", "Carbon_Alt_1", "Carbon_Weave",
        "Dragon_Scale", "Dragon_Scale_Alt", "Fleur_de_Lis", "Fleur_de_Lis_Alt", "Geo_Weave",
        "Hex_Carbon", "Japanese_Wave", "Mandela_Ornate", "Muertos_DOD1", "Muertos_DOD2",
        "Multi_Directional", "Steampunk_Gears", "Wavy_Carbon",
        "billabong_board", "bong_surfer", "surf_80s", "surfin_80s", "thrash_metal_skate",
    )
    _n_dedup = sum(1 for _d in _CASE_DUP_REMOVE if pattern_reg.pop(_d, None) is not None)
    if _n_dedup:
        print(f"[V5 Registry] Case-collision dedup: removed {_n_dedup} duplicate case-variant pattern(s)")

    # SPB-GRADIENT-OVERHAUL-2026-08-23 G-13 — production import-order fix.
    # Owner verdict: gradients were severely lacking and the replacement must
    # be the buyer-facing authority.  Installing only from shokker_engine_v2
    # let an `engine`/`server`-first process keep 10 material and 11 showcase
    # cards from older fusions/gradients_catalog modules, even while isolated
    # tests reported 166/166.  This is the final mutation in _build_registries,
    # after every expansion/fusion update, so all import orders own the same v3
    # functions.  Metric movement is recorded after the final 166-card bake.
    try:
        from engine.expansions.gradient_overhaul_2026 import install_gradient_overhaul

        _gradient_counts = install_gradient_overhaul(
            mono_reg, base_reg=base_reg, fusion_reg=fusion_reg
        )
        print(f"[V5 Registry] Gradient Overhaul final authority: {_gradient_counts}")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Gradient Overhaul final install failed: {ex}")

    # SPB-105 tick NU-25-LIVE-1 (2026-08-27) — owner rejected the legacy
    # object-led Neon rebuild. Reassert after every fusion/quality mutation so
    # all import orders expose the causal-material v3 slate (isolated M7
    # 25/25 >=85, 85.2-88.9) on 10 base and all 25 mono selection routes.
    try:
        from engine.expansions.neon_catalog_2026 import install_into_engine as _install_neon_v3

        print("[V5 Registry] Neon Underground final authority: " + _install_neon_v3(
            mono_reg, base_reg=base_reg, fusion_reg=fusion_reg
        ))
    except Exception as ex:
        print(f"[V5 Registry] Warning: Neon Underground final install failed: {ex}")

    # SPB-105 / X-LAB-1, 2026-08-28. Owner gave Codex carte blanche for 30
    # independent material experiments. Install dead-last so the SHOKKER group
    # cannot silently fall back to a legacy renderer with the same ID.
    try:
        from engine.expansions.x_lab_2026 import install_into_engine as _install_x_lab

        print("[V5 Registry] X LAB final authority: " + _install_x_lab(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: X LAB final install failed: {ex}")

    # SPB X-LAB-SHIFT, 2026-08-29. Owner: expand X LAB 30 -> 50 with the Hologram
    # Metal mechanism generalized ("the colors will DANCE and be ALIVE"). 20 new
    # region-coherent material-cell finishes; ids xlab_* join the same group.
    try:
        from engine.expansions.x_lab_shift_2026 import install_into_engine as _install_x_lab_shift

        print("[V5 Registry] X LAB shift wave: " + _install_x_lab_shift(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: X LAB shift wave install failed: {ex}")

    # SPB-105 / FRACTURED-HOUDINI-LIVE-1, 2026-08-29. Owner requires visual
    # inspection in the live development catalog. These remain material-only
    # lighting-reveal candidates; real-track proof decides the final keep/rebuild.
    try:
        # SPB-105 / FSH20-I2: owner09-18 replaces HOUDINI with twenty original
        # spectral materials. Development visibility; in-sim acceptance pending.
        from engine.expansions.fractured_shokk_2026 import install_into_engine as _install_houdini

        print("[V5 Registry] FRACTURED SHOKK: " + _install_houdini(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: FRACTURED SHOKK install failed: {ex}")

    # SPB-105 / IMPOSSIBLE-FIRST-LIGHT-1, 2026-08-29. Owner asked for a
    # separate, non-hand-paintable material lane inspired by Hologram Metal.
    # Keep it isolated from X LAB and legacy Flames: Hologram Metal remains a
    # protected benchmark while successors earn their own cards.
    # FRACTURED RELICS 2026-08-30 — owner rebuild 100 -> 50 ("the cabinet of
    # cursed things"). MUST be installed HERE, not only in shokker_engine_v2:
    # this V5 registry copies the legacy registry at import time and is the one
    # /api/finish-data enumerates, so a legacy-only install is invisible to the
    # picker (the client prunes any id absent from that payload). The legacy 100
    # relic ids stay registered by their own modules so saved projects render.
    # FRACTURED TESSERA 2026-08-30 — owner: protect TRUCHET GLASS and move it
    # somewhere safe. The new category IS its mechanism (tiling -> jewel panes ->
    # ignitable cames), so it can never be orphaned again. `ff_truchet_glass`
    # itself is untouched in FORGE; only its picker shelf changes.
    # FRACTURED FOUNDRY 2026-08-30 — owner: "masculine, industrial". Worked
    # metal: every finish is the mark a real process leaves, shaded through an
    # anisotropic metal model. A different mechanism from RELICS and TESSERA by
    # design — that is what gives the category its identity.
    try:
        from engine.expansions.fractured_foundry_2026 import install_into_engine as _install_foundry

        print("[V5 Registry] FRACTURED FOUNDRY: " + _install_foundry(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: FRACTURED FOUNDRY install failed: {ex}")

    try:
        from engine.expansions.fractured_tessera_2026 import install_into_engine as _install_tessera

        print("[V5 Registry] FRACTURED TESSERA: " + _install_tessera(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: FRACTURED TESSERA install failed: {ex}")

    # FRACTURED ELEMENTS 2026-08-31 rebuild — 60 weather finishes, absorbing
    # the good ideas from SHOKKER ATMOSPHERE (retired). The old shelf was 20
    # deep-sea creatures plus two colour grids.
    try:
        from engine.expansions.fractured_elements_2026 import install_into_engine as _install_elm

        print("[V5 Registry] FRACTURED ELEMENTS: " + _install_elm(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: FRACTURED ELEMENTS install failed: {ex}")

    # FRACTURED COSMOS 2026-08-31 rebuild — 60 finishes that are all actually
    # off-planet. The old shelf was 20 on-theme, 20 colour-grid recolours and
    # 20 iridescent finishes with no space in them.
    try:
        from engine.expansions.fractured_cosmos_2026 import install_into_engine as _install_cos

        print("[V5 Registry] FRACTURED COSMOS: " + _install_cos(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: FRACTURED COSMOS install failed: {ex}")

    # WORLD OF COLOR 2026-08-31 — COLORSHOXX repurposed. The old 77 cx_ ids were
    # three generations of colour-pair flips whose specs measured 2 material
    # cards over 2 families, roughness sigma 7 and clearcoat sigma 2.5. These 100
    # are 20 places x 5, each finish a material or process that place actually
    # makes colour with. Old cx_ ids stay registered for saved projects.
    try:
        from engine.expansions.world_of_color_2026 import install_into_engine as _install_woc

        print("[V5 Registry] WORLD OF COLOR: " + _install_woc(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: WORLD OF COLOR install failed: {ex}")

    # MONEY SHOKK 2026-08-31 total rework — the old 40 were a colour x creature
    # grid (Canary Coffin, Cerulean Cobra, Lime Scorpion) with a money name on
    # the box. These 40 are the machinery of wealth: mint, vault, asset,
    # counterfeit, burn. Old msh_/mshc_/msha_/mshx_ ids stay registered.
    try:
        from engine.expansions.money_shokk_2026 import install_into_engine as _install_msk

        print("[V5 Registry] MONEY SHOKK: " + _install_msk(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: MONEY SHOKK install failed: {ex}")

    # PARADIGM 2026-08-31 redesign — 34 finishes with no shared idea replaced by
    # 50 that all do one thing: show a substance you recognise and behave like a
    # different one. The old ids stay registered so saved projects still render.
    try:
        from engine.expansions.paradigm_2026 import install_into_engine as _install_pdg

        print("[V5 Registry] PARADIGM: " + _install_pdg(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: PARADIGM install failed: {ex}")

    # FRACTURED NIGHTSHIFT 2026-08-31 rebuild — 101 down to 50, and this time
    # the day/night hue change is measured (engine/paint_v2/daynight.py). The
    # old lab modules stay registered so saved projects keep rendering.
    try:
        from engine.expansions.fractured_nightshift_2026 import install_into_engine as _install_nsx

        print("[V5 Registry] FRACTURED NIGHTSHIFT: " + _install_nsx(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: FRACTURED NIGHTSHIFT install failed: {ex}")

    # FRACTURED FLAMES 2026-08-30 rebuild — owner: 144 cards down to 75. The old
    # shelf was a cross-product (51 structures x 3 spec modes x a palette NAME
    # that never reached the paint); this is one card per idea, coloured by
    # Planck's law and real chemiluminescence. Installed AFTER the legacy
    # flames_catalog_2026 so the new ids win; the legacy flm_* ids stay
    # registered so saved projects still render.
    try:
        from engine.expansions.fractured_flames_2026 import install_into_engine as _install_flames

        print("[V5 Registry] FRACTURED FLAMES: " + _install_flames(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: FRACTURED FLAMES install failed: {ex}")

    try:
        from engine.expansions.fractured_relics_2026 import install_into_engine as _install_relics

        print("[V5 Registry] FRACTURED RELICS: " + _install_relics(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: FRACTURED RELICS install failed: {ex}")

    try:
        from engine.expansions.impossible_finishes_2026 import install_into_engine as _install_impossible

        print("[V5 Registry] IMPOSSIBLE FINISHES first light: " + _install_impossible(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: IMPOSSIBLE FINISHES install failed: {ex}")

    # SPB-105 / IMPOSSIBLE-NOIR-I2, 2026-08-29. Separate dark lattice
    # successor informed by (but never replacing) protected Hologram Metal.
    try:
        from engine.expansions import impossible_hologram_noir_i1_2026 as _holo_noir

        mono_reg["impossible_hologram_noir"] = (
            _holo_noir.spec_impossible_hologram_noir,
            _holo_noir.paint_impossible_hologram_noir,
        )
        print("[V5 Registry] IMPOSSIBLE FINISHES Hologram Noir I2 staged")
    except Exception as ex:
        print(f"[V5 Registry] Warning: IMPOSSIBLE FINISHES Hologram Noir I2 install failed: {ex}")

    # SPB-105 / IMPOSSIBLE-PRISM-I5, 2026-08-29. Owner specifically asked for
    # every fine square to carry its own adjacent paint and M/R/Cc state. This
    # replaces the weak green-on-black Hologram Noir card only; protected X LAB
    # Hologram Metal remains entirely separate and hash-guarded.
    try:
        from engine.expansions import impossible_prism_mosaic_i1_2026 as _prism_i5

        mono_reg["impossible_hologram_noir"] = (
            _prism_i5.spec_impossible_prism_mosaic,
            _prism_i5.paint_impossible_prism_mosaic,
        )
        print("[V5 Registry] IMPOSSIBLE FINISHES Prism Mosaic I5 promoted over Hologram Noir")
    except Exception as ex:
        print(f"[V5 Registry] Warning: IMPOSSIBLE FINISHES Prism Mosaic I5 install failed: {ex}")

    # SPB-105 / IMPOSSIBLE-LIVING-OBSIDIAN-I2, 2026-08-29. A distinct
    # image-authored dark lacquer: 1.502s direct 2048², M/R/Cc std
    # 45.0/37.8/43.0. I1 was picker-black; I2 repairs body exposure without
    # changing the irregular local material states. Hologram Metal untouched.
    try:
        from engine.expansions import impossible_living_obsidian_i1_2026 as _living_obsidian

        mono_reg["impossible_living_obsidian"] = (
            _living_obsidian.spec_impossible_living_obsidian,
            _living_obsidian.paint_impossible_living_obsidian,
        )
        print("[V5 Registry] IMPOSSIBLE FINISHES Living Obsidian I2 staged")
    except Exception as ex:
        print(f"[V5 Registry] Warning: IMPOSSIBLE FINISHES Living Obsidian I2 install failed: {ex}")

    # SPB-105 / XLAB-ANAMORPHIC-I3, 2026-08-29. Owner requested each pearl
    # cell have its own real material state and no vertical stripe read. This
    # override stays under the existing, catalog-visible X LAB card only after
    # direct native/picker evidence: 0.586s, M/R/Cc std 67.8/49.0/54.7.
    try:
        from engine.expansions import xlab_anamorphic_pearl_i3_2026 as _anamorphic_i3

        mono_reg["xlab_anamorphic_pearl"] = (
            _anamorphic_i3.spec_anamorphic_pearl,
            _anamorphic_i3.paint_anamorphic_pearl,
        )
        print("[V5 Registry] X LAB Anamorphic Pearl I3 installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: X LAB Anamorphic Pearl I3 install failed: {ex}")

    # SPB-105 / GV-MYCELIUM-I2, 2026-08-29. Replace the macro-cap/spore
    # carrier only after native owner-eye evidence: connected 1970s mycelial
    # resin, 1.771s direct 2048², M/R/Cc std 30.4/36.5/36.7.
    try:
        from engine.expansions import groovy_mushroom_fade_i2_2026 as _mushroom_i2

        base_reg["mushroom_fade"]["paint_fn"] = _mushroom_i2.paint_mushroom_fade
        base_reg["mushroom_fade"]["base_spec_fn"] = _mushroom_i2.spec_mushroom_fade
        print("[V5 Registry] Groovy Mushroom Fade I2 installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Groovy Mushroom Fade I2 install failed: {ex}")

    # SPB-105 / GV-PSYCHEDELIC-SWIRL-I2, 2026-08-29. Owner's picker-scale
    # audit rejected the old cartoon territory read. This isolated lacquer
    # replacement cleared native/picker review: 0.697s direct 2048² and
    # M/R/Cc std 26.1/23.2/23.2 from paint-causal ink/lip/pearl geometry.
    try:
        from engine.expansions import groovy_psychedelic_swirl_i1_2026 as _psychedelic_i2

        base_reg["psychedelic_swirl"]["paint_fn"] = _psychedelic_i2.paint_psychedelic_swirl
        base_reg["psychedelic_swirl"]["base_spec_fn"] = _psychedelic_i2.spec_psychedelic_swirl
        print("[V5 Registry] Groovy Psychedelic Swirl I2 installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Groovy Psychedelic Swirl I2 install failed: {ex}")

    # SPB-105 / SH-JUKEBOX-NEON-I1, 2026-08-29. Picker audit rejected the
    # legacy black-square carrier. This replacement is a continuous 1950s
    # jukebox-glass bezel material: 0.611s direct 2048², M/R/Cc std
    # 67.1/59.6/64.7, all states bound to the visible curved rail geometry.
    try:
        from engine.expansions import sock_jukebox_neon_i1_2026 as _jukebox_i1

        base_reg["jukebox_neon"]["paint_fn"] = _jukebox_i1.paint_jukebox_neon
        base_reg["jukebox_neon"]["base_spec_fn"] = _jukebox_i1.spec_jukebox_neon
        print("[V5 Registry] Sock Hop Jukebox Neon I1 installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Sock Hop Jukebox Neon I1 install failed: {ex}")

    # SPB-105 / SH-DINER-CHECKER-I1, 2026-08-29. Owner-eye audit found the
    # legacy card was dusty noise with a flat olive spec. Candidate evidence:
    # 0.555s direct 2048²; 16px porcelain, 2px chrome grout and 8px soda-glass
    # states bind every M/R/Cc change to visible 1950s diner geometry.
    try:
        from engine.expansions import sock_diner_enamel_checker_i1_2026 as _diner_i1

        base_reg["diner_checker"]["paint_fn"] = _diner_i1.paint_diner_enamel_checker
        base_reg["diner_checker"]["base_spec_fn"] = _diner_i1.spec_diner_enamel_checker
        print("[V5 Registry] Sock Hop Diner Checkerboard I1 installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Sock Hop Diner Checkerboard I1 install failed: {ex}")

    # SPB-105 / SH-FORMICA-BOOMERANG-I4, 2026-08-30. Owner's native-scale
    # audit rejected the legacy ~94px station. This compact laminate keeps
    # 3–24px inlays in 52px composed clusters: 0.712s direct 2048² and
    # M/R/Cc std 47.6/45.1/47.8, all tied to actual Formica print geometry.
    try:
        from engine.expansions import sock_formica_compact_boomerang_i4_2026 as _formica_i4

        base_reg["formica_boomerang"]["paint_fn"] = _formica_i4.paint_formica_compact_boomerang
        base_reg["formica_boomerang"]["base_spec_fn"] = _formica_i4.spec_formica_compact_boomerang
        print("[V5 Registry] Sock Hop Formica Boomerang I4 installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Sock Hop Formica Boomerang I4 install failed: {ex}")

    # SPB-105 / SH-ATOMIC-STARBURST-I4, 2026-08-30. The legacy atomic card
    # used oversized icon spacing plus an unrelated hatch grid. I4 is a real
    # 1950s cocktail print: 8–28px core/rays/orbits/satellites in compact 64px
    # compositions, 1.149s direct 2048², M/R/Cc std 44.8/38.2/41.4.
    try:
        from engine.expansions import sock_atomic_cocktail_i4_2026 as _atomic_i4

        base_reg["atomic_starburst"]["paint_fn"] = _atomic_i4.paint_atomic_cocktail
        base_reg["atomic_starburst"]["base_spec_fn"] = _atomic_i4.spec_atomic_cocktail
        print("[V5 Registry] Sock Hop Atomic Starburst I4 installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Sock Hop Atomic Starburst I4 install failed: {ex}")

    # SPB-105 / GV-OIL-SLICK-I3, 2026-08-30. Legacy Oil Slick Groove was
    # literal rainbow bands plus disconnected spec. I3 is a fine wet-film
    # interference carrier: each 8–24px lens owns pigment/rim/mica/trough MRC,
    # 0.857s direct 2048² and M/R/Cc std 74.1/65.9/79.1.
    try:
        from engine.expansions import groovy_oil_lens_i3_2026 as _oil_i3

        base_reg["oil_slick_groove"]["paint_fn"] = _oil_i3.paint_oil_lens
        base_reg["oil_slick_groove"]["base_spec_fn"] = _oil_i3.spec_oil_lens
        print("[V5 Registry] Groovy Oil Slick Lens I3 installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Groovy Oil Slick Lens I3 install failed: {ex}")


    # SPB-105 / 2026-08-29 — owner-eye screened 1970s silkscreen ink lacquer.
    # Acid Swirl's prior picker was a flat pale split; this carrier has dense
    # 8–32px authored print, pearl-lip and ink-pool geometry with linked M/R/Cc.
    try:
        from engine.expansions import groovy_acid_ink_silkscreen_i1_2026 as _acid_ink_i2

        base_reg["acid_swirl"]["paint_fn"] = _acid_ink_i2.paint_groovy_acid_ink_silkscreen
        base_reg["acid_swirl"]["base_spec_fn"] = _acid_ink_i2.spec_groovy_acid_ink_silkscreen
        print("[V5 Registry] Groovy Acid Ink Silk-Screen I2 installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Groovy Acid Ink Silk-Screen I2 install failed: {ex}")

    # SPB-105 / GV-TIE-DYE-CRUMPLE-I1, 2026-08-29. Picker audit rejected the
    # old flat/noise-like crumple. This wax-resist silk + pearl lacquer is a
    # separate 1960s material: 0.657s direct 2048², M/R/Cc std 26.0/24.2/23.7
    # from visible fold, wax boundary, pigment and hue populations.
    try:
        from engine.expansions import groovy_tie_dye_crumple_i1_2026 as _crumple_i1

        base_reg["tie_dye_crumple"]["paint_fn"] = _crumple_i1.paint_tie_dye_crumple
        base_reg["tie_dye_crumple"]["base_spec_fn"] = _crumple_i1.spec_tie_dye_crumple
        print("[V5 Registry] Groovy Tie-Dye Crumple I1 installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Groovy Tie-Dye Crumple I1 install failed: {ex}")

    # SPB-105 / GV-HIPPIE-RAINBOW-REGIONAL-I2 / 2026-08-30. I1's correct
    # macramé cords collapsed into a dark mesh. I2 keeps 2–28px cord/knot
    # construction but gives adjacent cells coherent hand-dyed regions:
    # 1.958s direct 2048², M/R/Cc 83.6/74.4/86.9. Live picker decides keep.
    try:
        from engine.expansions import groovy_hippie_rainbow_regional_i2_2026 as _hippie_i2

        base_reg["hippie_rainbow"]["paint_fn"] = _hippie_i2.paint_hippie_rainbow_regional
        base_reg["hippie_rainbow"]["base_spec_fn"] = _hippie_i2.spec_hippie_rainbow_regional
        print("[V5 Registry] Groovy Hippie Rainbow Regional Macramé I2 live trial installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Groovy Hippie Rainbow Regional Macramé I2 install failed: {ex}")

    # SPB-105 / GV-MELTING-CELLULOID-I1 / 2026-08-30. Replaces literal
    # rainbow striping with opaque liquid-light film: regional pigment pools
    # are formed from fine 8–32px gel cells, mica scars and ink tears (2.095s
    # direct 2048²; M/R/Cc 54.5/55.1/64.4). Live route decides promotion.
    try:
        from engine.expansions import groovy_melting_celluloid_i1_2026 as _celluloid_i1

        base_reg["melting_rainbow"]["paint_fn"] = _celluloid_i1.paint_melting_celluloid
        base_reg["melting_rainbow"]["base_spec_fn"] = _celluloid_i1.spec_melting_celluloid
        print("[V5 Registry] Groovy Melting Celluloid I1 live trial installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Groovy Melting Celluloid I1 install failed: {ex}")

    # SPB-105 / SH-CHERRY-COLA-FIZZ-I1 / 2026-08-30. Replaces literal Cherry
    # Polka dots with connected 8–28px candy-glass carbonation, cream foam,
    # syrup depth and chrome glints (1.422s direct 2048²; M/R/Cc 45.8/43.0/42.7).
    # It promotes only if the real live swatch keeps a recognizable diner read.
    try:
        from engine.expansions import sock_cherry_cola_fizz_i1_2026 as _cherry_fizz_i1

        base_reg["cherry_polka"]["paint_fn"] = _cherry_fizz_i1.paint_cherry_cola_fizz
        base_reg["cherry_polka"]["base_spec_fn"] = _cherry_fizz_i1.spec_cherry_cola_fizz
        print("[V5 Registry] Sock Hop Cherry Cola Fizz I1 live trial installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Sock Hop Cherry Cola Fizz I1 install failed: {ex}")

    # SPB-105 / SH-PINK-FLECK-SHATTERCOAT-I3 / 2026-08-30. I2's square
    # lanes were rejected. I3 uses irregular 8–32px Candy Apple cells with
    # neighboring pink/chrome/pearl/flat material states (0.437s direct 2048²,
    # M/R/Cc 47.7/62.4/43.6); actual live swatch decides keep or rollback.
    try:
        from engine.expansions import sock_pink_fleck_shattercoat_i3_2026 as _pink_i3

        base_reg["pink_fleck"]["paint_fn"] = _pink_i3.paint_pink_fleck_shattercoat_i3
        base_reg["pink_fleck"]["base_spec_fn"] = _pink_i3.spec_pink_fleck_shattercoat_i3
        print("[V5 Registry] Sock Hop Pink Fleck Shattercoat I3 live trial installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Sock Hop Pink Fleck Shattercoat I3 install failed: {ex}")

    # SPB-105 / SH-SODA-FOUNTAIN-GLASS-I1 / 2026-08-30. Replace Soda
    # Check's purple grid only if its real live card keeps the fine soda-glass
    # structure readable: 4–28px fizzy cells, lips, inclusions and causal
    # M/R/Cc (1.513s direct 2048², 54.5/49.9/56.4). Owner-eye route decides.
    try:
        from engine.expansions import sock_soda_fountain_glass_i1_2026 as _soda_glass_i1

        base_reg["soda_check"]["paint_fn"] = _soda_glass_i1.paint_soda_fountain_glass
        base_reg["soda_check"]["base_spec_fn"] = _soda_glass_i1.spec_soda_fountain_glass
        print("[V5 Registry] Sock Hop Soda Fountain Glass I1 live trial installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Sock Hop Soda Fountain Glass I1 install failed: {ex}")

    # SPB-105 / SH-GINGHAM-WOVEN-I2 / 2026-08-30. Rebuild Gingham Red as
    # actual 2–12px yarn faces and seams inside a 24px woven repeat instead
    # of a broad graphic checker. Red/cream warp, weft, crossings, lint and
    # dye uptake each carry different M/R/Cc states (1.876s direct 2048²;
    # M/R/Cc 61.3/48.9/61.8); retain only after the true live card passes.
    try:
        from engine.expansions import sock_gingham_woven_i2_2026 as _gingham_i2

        base_reg["gingham_red"]["paint_fn"] = _gingham_i2.paint_gingham_woven
        base_reg["gingham_red"]["base_spec_fn"] = _gingham_i2.spec_gingham_woven
        print("[V5 Registry] Sock Hop Gingham Red Woven I2 live trial installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Sock Hop Gingham Red Woven I2 install failed: {ex}")

    # SPB-105 / SH-VINYL-RECORD-PRESS-I2 / 2026-08-30. Replaces the rejected
    # red upholstery detour with actual pressed black vinyl: 1–3px groove
    # ridges, 4–8px lacquer lands, polish arcs, press seams and micro-specks
    # have independent M/R/Cc response (1.694s direct 2048²; 46.4/37.8/48.5).
    # Two off-canvas stamp centres cover the car without a giant record decal.
    try:
        from engine.expansions import sock_vinyl_record_press_i2_2026 as _vinyl_i2

        base_reg["vinyl_groove"]["paint_fn"] = _vinyl_i2.paint_vinyl_record_press
        base_reg["vinyl_groove"]["base_spec_fn"] = _vinyl_i2.spec_vinyl_record_press
        print("[V5 Registry] Sock Hop Vinyl Record Press I2 live trial installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Sock Hop Vinyl Record Press I2 install failed: {ex}")

    # SPB-105 / SH-TURQUOISE-METALFLAKE-I2 / 2026-08-30. Real custom-car
    # candy enamel over 2–10px oriented metal platelets and 1–2px rim facets;
    # enamel depth only organizes the coat. Platelets, faces, rims, troughs
    # and candy lots own independent M/R/Cc states (2.606s direct 2048²;
    # M/R/Cc 71.4/69.3/74.3). Promote only with true live-card evidence.
    try:
        from engine.expansions import sock_turquoise_metalflake_i2_2026 as _turquoise_i2

        base_reg["turquoise_fleck"]["paint_fn"] = _turquoise_i2.paint_turquoise_metalflake
        base_reg["turquoise_fleck"]["base_spec_fn"] = _turquoise_i2.spec_turquoise_metalflake
        print("[V5 Registry] Sock Hop Turquoise Metalflake I2 live trial installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Sock Hop Turquoise Metalflake I2 install failed: {ex}")

    # SPB-105 / GV-GROOVY-ZIGZAG-I2 / 2026-08-30. A true period woven
    # poster-print: 6–16px colored ink ribbons, fine crossings, registration
    # edges, mica flecks and chevron junctions carry causal M/R/Cc response
    # (1.701s direct 2048²; 36.4/39.6/35.7). The larger rhythm is composed
    # entirely of those fine marks, not one macro chevron.
    try:
        from engine.expansions import groovy_zigzag_i2_2026 as _zigzag_i2

        base_reg["groovy_zigzag"]["paint_fn"] = _zigzag_i2.paint_groovy_zigzag
        base_reg["groovy_zigzag"]["base_spec_fn"] = _zigzag_i2.spec_groovy_zigzag
        print("[V5 Registry] Groovy Zigzag I2 live trial installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Groovy Zigzag I2 install failed: {ex}")

    # SPB-105 / SH-LEMON-POLKA-PASTILLE-I2 / 2026-08-30. Restore actual
    # 1950s polka language with intentional 6–18px pearl pastilles, 1–3px
    # candy halos, inset faces and pin-lines—not a yellow cell field. Field,
    # dot, halo, rim, face and pin states own M/R/Cc response (2.561s direct
    # 2048²; 57.9/53.0/61.3). Retain only after true live-card evidence.
    try:
        from engine.expansions import sock_lemon_polka_pastille_i2_2026 as _lemon_i2

        base_reg["lemon_polka"]["paint_fn"] = _lemon_i2.paint_lemon_polka_pastille
        base_reg["lemon_polka"]["base_spec_fn"] = _lemon_i2.spec_lemon_polka_pastille
        print("[V5 Registry] Sock Hop Lemon Polka Pastille I2 live trial installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: Sock Hop Lemon Polka Pastille I2 install failed: {ex}")

    # SPB-105 / IMPOSSIBLE-CINDER-I3 / 2026-08-30. Hologram-lesson trial:
    # charcoal 16px cells with four 8px physical sub-states and a coherent
    # regional selector. A true forced-live swatch decides promotion/rollback.
    try:
        from engine.expansions import impossible_cinder_matrix_i3_2026 as _cinder_i3
        mono_reg["impossible_cinder_pulse"] = (_cinder_i3.spec_impossible_cinder_matrix,
                                               _cinder_i3.paint_impossible_cinder_matrix)
        print("[V5 Registry] IMPOSSIBLE Cinder Matrix I3 live trial installed")
    except Exception as ex:
        print(f"[V5 Registry] Warning: IMPOSSIBLE Cinder Matrix I3 install failed: {ex}")

    # 2026-09-02 owner: "3 more [IMPOSSIBLE] that totally push the boundaries ... millions of
    # colors with the most intricate designs". Penrose Reactor / Nacre Terrace / Caustic Loom.
    try:
        from engine.expansions.impossible_trio_2026 import install_into_engine as _install_impossible_trio
        print("[V5 Registry] IMPOSSIBLE trio: " + _install_impossible_trio(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: IMPOSSIBLE trio install failed: {ex}")

    # 2026-09-02 owner: "take what you could learn from [Cinder Pulse] ... make 2-3 more VERY SIMILAR
    # ... with other colors" + "[Hologram Noir] make a few more with THIS in mind". Six recipes.
    try:
        from engine.expansions.impossible_glint_2026 import install_into_engine as _install_impossible_glint
        print("[V5 Registry] IMPOSSIBLE glint/mosaic: " + _install_impossible_glint(mono_reg))
    except Exception as ex:
        print(f"[V5 Registry] Warning: IMPOSSIBLE glint/mosaic install failed: {ex}")

    # SPB-105 / ASTRA A1: owner commissioned ten independent material bases.
    # Installing inside the builder covers both V5 and legacy registry callers.
    from engine.expansions.astra import install as _install_astra
    _install_astra(base_reg)
    return base_reg, pattern_reg, mono_reg, finish_reg, fusion_reg


# Build all registries at import time
BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY, FINISH_REGISTRY, FUSION_REGISTRY = _build_registries()

# FOUNDATION ONE (owner 2026-09-03): retired base ids -> surviving cell. Applied HERE, at
# module level, and NOT inside _build_registries(): shokker_engine_v2 calls _build_registries()
# mid-import and then wraps entries BY ID with per-group texture, so an alias that already
# pointed `enh_metallic` at f_metallic's dict let the Enhanced-group wrapper texture the flat
# f_metallic cell (M spread 45; tests/test_regression_foundation_spec_flatness.py caught it).
try:
    from engine.base_registry_data import apply_base_id_aliases as _apply_base_aliases
    _n_alias = _apply_base_aliases(BASE_REGISTRY)
    print(f"[V5 Registry] FOUNDATION ONE: {_n_alias} retired base id(s) aliased to survivors")
    try:
        from engine.base_registry_data import _upgrade_foundation_material_spec as _v5_fnd_mat
        _v5_fnd_mat(BASE_REGISTRY)
    except Exception as _v5_fnd_exc:
        print(f"[V5 Registry] Foundation material spec skipped: {_v5_fnd_exc}")

    # [WRAP SHOP 2026-09-04] Also installed here: a finish that exists only in
    # shokker_engine_v2 is invisible in the picker, because the client prunes the
    # base list against /api/finish-data, which enumerates THIS registry.
    try:
        from engine.paint_v2.wrap_shop_2026 import install as _v5_wrap
        print(f"[V5 Registry] WRAP SHOP: {_v5_wrap(BASE_REGISTRY)} wrap finishes installed")
    except Exception as _v5_wrap_exc:
        print(f"[V5 Registry] Wrap Shop skipped: {_v5_wrap_exc}")

    # [FLAW LAB 2026-09-04] Also installed here: a finish present only in
    # shokker_engine_v2 is invisible in the picker, because the client prunes the
    # base list against /api/finish-data, which enumerates THIS registry.
    try:
        from engine.paint_v2.flaw_lab_2026 import install as _v5_flaw
        print(f"[V5 Registry] FLAW LAB: {_v5_flaw(BASE_REGISTRY)} inspection finishes installed")
        from engine.paint_v2.flaw_lab_rebuild_2026 import register as _flaw_r1
        _flaw_r1(BASE_REGISTRY)
    except Exception as _v5_flaw_exc:
        print(f"[V5 Registry] Flaw Lab skipped: {_v5_flaw_exc}")

    # [THE BOOTH 2026-09-04] Also here: a finish present only in shokker_engine_v2
    # is invisible in the picker, which prunes against THIS registry.
    try:
        from engine.paint_v2.the_booth_2026 import install as _v5_booth
        print(f"[V5 Registry] THE BOOTH: {_v5_booth(BASE_REGISTRY)} defect finishes installed")
    except Exception as _v5_booth_exc:
        print(f"[V5 Registry] The Booth skipped: {_v5_booth_exc}")

    # [MULE 2026-09-04] Also here so the picker can see it.
    try:
        from engine.paint_v2.mule_2026 import install as _v5_mule
        print(f"[V5 Registry] MULE: {_v5_mule(BASE_REGISTRY)} disguise finishes installed")
    except Exception as _v5_mule_exc:
        print(f"[V5 Registry] Mule skipped: {_v5_mule_exc}")

    # [LIGHTNING SHOKK 2026-09-04] Also here so the picker can see it.
    try:
        from engine.paint_v2.lightning_shokk_2026 import install as _v5_lsk
        print(f"[V5 Registry] LIGHTNING SHOKK: {_v5_lsk(BASE_REGISTRY)} discharge finishes installed")
    except Exception as _v5_lsk_exc:
        print(f"[V5 Registry] Lightning Shokk skipped: {_v5_lsk_exc}")

    # [SLITHERIN 2026-09-04] Also here so the picker can see it.
    try:
        from engine.paint_v2.slitherin_2026 import install as _v5_slt
        print(f"[V5 Registry] SLITHERIN: {_v5_slt(BASE_REGISTRY)} snake finishes installed")
    except Exception as _v5_slt_exc:
        print(f"[V5 Registry] Slitherin skipped: {_v5_slt_exc}")
    # SPB-105 / SHOKK WORKS 2026-09-30: selected native constructions, no quality wrapper.
    from engine.paint_v2.core_works_2026 import install as _core_works_install
    _core_works_install(BASE_REGISTRY)
except Exception as ex:
    print(f"[V5 Registry] Warning: base id alias pass failed: {ex}")

print(f"[V5 Registry] READY - "
      f"{len(BASE_REGISTRY)} bases, "
      f"{len(PATTERN_REGISTRY)} patterns, "
      f"{len(MONOLITHIC_REGISTRY)} monolithics "
      f"({len(FUSION_REGISTRY)} fusions)")
