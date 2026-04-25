"""
Shokker V5 Smoke Test
======================
Minimal sanity check: registries load, key finishes render, iron rules pass.
Run after engine changes to catch regressions quickly.

Usage:
  cd "Shokker Paint Booth Gold to Platinum"
  python tests/smoke_test.py          # script mode
  python -m pytest tests/smoke_test.py -q   # pytest mode
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows: avoid charmap errors when engine/server log Unicode
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []


def _safe_str(s):
    try:
        return str(s).encode("ascii", "replace").decode("ascii")
    except Exception:
        return "?"


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    icon = PASS if ok else FAIL
    safe_detail = _safe_str(detail) if detail else ""
    print(f"  {icon} {name}" + (f" -- {safe_detail}" if safe_detail else ""))


def is_valid_png(data):
    return data and len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------------------
# main() — runs the full smoke battery in script mode
# ---------------------------------------------------------------------------
def main():
    global results
    results = []

    print("\n" + "=" * 60)
    print("  SHOKKER PAINT BOOTH — SMOKE TEST")
    print("=" * 60 + "\n")

    import numpy as np

    # == 1. REGISTRY LOAD =================================================
    print("1. Registry load")
    try:
        from shokker_engine_v2 import (
            BASE_REGISTRY,
            PATTERN_REGISTRY,
            MONOLITHIC_REGISTRY,
        )
        check("BASE_REGISTRY loaded", len(BASE_REGISTRY) >= 50, f"{len(BASE_REGISTRY)} entries")
        check("PATTERN_REGISTRY loaded", len(PATTERN_REGISTRY) >= 200, f"{len(PATTERN_REGISTRY)} entries")
        check("MONOLITHIC_REGISTRY loaded", len(MONOLITHIC_REGISTRY) >= 100, f"{len(MONOLITHIC_REGISTRY)} entries")
    except Exception as e:
        check("Registry load", False, str(e))
        print("\n  ABORTED: Registry failed to load\n")
        sys.exit(1)

    print()

    # == 2. TEXTURE FUNCTIONS =============================================
    print("2. Pattern texture functions")
    shape = (128, 128)
    mask = np.ones(shape, np.float32)

    hero_patterns = ['carbon_fiber', 'hex_mesh', 'diamond_plate', 'holographic_flake',
                     'lightning', 'tribal_flame', 'ekg', 'camo']
    tex_ok = tex_err = 0
    for name in hero_patterns:
        entry = PATTERN_REGISTRY.get(name, {})
        tfn = entry.get('texture_fn')
        if tfn:
            try:
                result = tfn(shape, mask, 42, 1.0)
                pv = result['pattern_val'] if isinstance(result, dict) else result
                ok = pv is not None and pv.shape[:2] == shape
                check(f"texture {name}", ok, f"shape={pv.shape if pv is not None else 'None'}")
                if ok: tex_ok += 1
                else: tex_err += 1
            except Exception as e:
                check(f"texture {name}", False, str(e)[:50])
                tex_err += 1

    print()

    # == 3. PAINT FUNCTIONS (production 3D+2D path) =======================
    print("3. Paint functions (production path)")
    paint3 = np.full((128, 128, 3), 0.5, np.float32)
    bb2 = np.full(shape, 0.5, np.float32)

    # Test base, pattern, and monolithic paints
    base_ok = base_err = 0
    for name, entry in list(BASE_REGISTRY.items())[:50]:
        if not isinstance(entry, dict): continue
        pfn = entry.get('paint_fn')
        if pfn is None: continue
        try:
            pfn(paint3.copy(), shape, mask, 42, 1.0, bb2)
            base_ok += 1
        except:
            base_err += 1

    check(f"Base paint (50 sample)", base_err == 0, f"{base_ok} OK, {base_err} errors")

    mono_ok = mono_err = 0
    for name, val in list(MONOLITHIC_REGISTRY.items())[:50]:
        if not isinstance(val, tuple) or len(val) < 2: continue
        try:
            val[1](paint3.copy(), shape, mask, 42, 1.0, bb2)
            mono_ok += 1
        except:
            mono_err += 1

    check(f"Mono paint (50 sample)", mono_err == 0, f"{mono_ok} OK, {mono_err} errors")

    print()

    # == 4. COMPOSE PIPELINE ==============================================
    print("4. Compose pipeline")
    try:
        from engine.compose import compose_finish
        spec = compose_finish('candy', 'carbon_fiber', shape, mask, 42, 1.0)
        spec = np.asarray(spec)
        check("compose_finish", spec.shape == (128, 128, 4), f"shape={spec.shape}")
    except Exception as e:
        check("compose_finish", False, str(e)[:50])

    print()

    # == 5. IRON RULES ====================================================
    print("5. Iron rules (R>=15 non-chrome, CC>=16)")
    iron_violations = 0
    for name, val in MONOLITHIC_REGISTRY.items():
        if not isinstance(val, tuple) or len(val) < 1: continue
        try:
            s = np.asarray(val[0](shape, mask, 42, 1.0), dtype=np.float32)
            if s.ndim < 3 or s.shape[2] < 3: continue
            if np.any((s[:, :, 1] < 15) & (s[:, :, 0] < 240)):
                iron_violations += 1
        except:
            pass

    check("Iron rules (monolithics)", iron_violations == 0, f"{iron_violations} violations")

    # Check compose output
    try:
        from engine.compose import compose_finish
        spec = np.asarray(compose_finish('candy', 'carbon_fiber', shape, mask, 42, 1.0))
        M = spec[:, :, 0].astype(float)
        R = spec[:, :, 1].astype(float)
        CC = spec[:, :, 2].astype(float)
        r_bad = np.sum((R < 15) & (M < 240))
        cc_bad = np.sum(CC < 16)
        check("Iron rules (compose)", r_bad == 0 and cc_bad == 0, f"R_viol={r_bad} CC_viol={cc_bad}")
    except Exception as e:
        check("Iron rules (compose)", False, str(e)[:50])

    print()

    # == 6. PERFORMANCE SPOT CHECK ========================================
    print("6. Performance (2048x2048)")
    perf_shape = (2048, 2048)
    perf_mask = np.ones(perf_shape, np.float32)

    t0 = time.time()
    from engine.compose import compose_finish
    compose_finish('candy', 'carbon_fiber', perf_shape, perf_mask, 42, 1.0)
    ms = int((time.time() - t0) * 1000)
    check(f"compose_finish @ 2048", ms < 5000, f"{ms}ms (target <5s)")

    print()

    # == SUMMARY =========================================================
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed

    print("=" * 60)
    print(f"  RESULTS: {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} FAILED)")
        print()
        print("  FAILED:")
        for name, ok, detail in results:
            if not ok:
                safe = _safe_str(detail) if detail else ""
                print(f"    {FAIL} {name}" + (f" -- {safe}" if safe else ""))
    else:
        print("  -- ALL PASSED")
    print("=" * 60 + "\n")

    return failed


# ---------------------------------------------------------------------------
# pytest entry points
# ---------------------------------------------------------------------------
def test_smoke():
    """Full engine smoke test — registries, textures, paints, compose, iron rules."""
    failed = main()
    assert failed == 0, f"{failed} smoke checks failed"


def test_rect_color_selection():
    """Verify rectangle selection keeps the real positive-value gate."""
    canvas_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "paint-booth-3-canvas.js",
    )
    with open(canvas_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    assert "const useColorFilter = (value > 0)" in content


def test_layer_fill_gradient_source_guards():
    """Verify layer fill/gradient keep the shared origin/color contract and baked-special helpers."""
    canvas_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "paint-booth-3-canvas.js",
    )
    with open(canvas_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    assert "function getLayerCanvasOrigin(layer)" in content
    assert "const fg = typeof _foregroundColor === 'string' ? _foregroundColor : '#000000';" in content
    assert "const bg = typeof _backgroundColor === 'string' ? _backgroundColor : '#ffffff';" in content
    assert "function _drawLayerSpecialStamp(ctx, x, y, radius, opacity, hardness)" in content
    assert "function _applyBakedSpecialFloodFill(data, visited, lw, lh, minX, minY, maxX, maxY, opacity)" in content


def test_no_decal_double_push():
    """Verify new raster assets route through the shared layer helper."""
    boot_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "paint-booth-6-ui-boot.js",
    )
    with open(boot_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    assert "function addImageToUnifiedLayerStack(options)" in content
    add_number_start = content.index("function addNumberDecal()")
    add_number_end = content.index("function checkDecalHit", add_number_start)
    add_number_block = content[add_number_start:add_number_end]
    assert "addImageToUnifiedLayerStack({" in add_number_block
    assert "decalLayers.push({" not in add_number_block


def test_layer_fill_gradient_undo_routing():
    """Verify fill/gradient route by explicit toolbar mode for Alpha safety."""
    canvas_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "paint-booth-3-canvas.js",
    )
    with open(canvas_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    assert "_pushLayerUndo(getSelectedLayer(), 'fill bucket on layer');" in content
    assert "_pushLayerUndo(getSelectedLayer(), 'gradient on layer');" in content
    assert "window._gradientTargetLayerId = _selectedLayerId || null;" in content
    assert "requireLayerToolbarTarget('Fill Bucket')" in content
    assert "requireZoneToolbarMode('Fill Bucket')" in content
    assert "requireLayerToolbarTarget('Gradient')" in content
    assert "requireZoneToolbarMode('Gradient')" in content


def test_layer_tool_options_surface_color_and_baked_special_controls():
    """Verify layer tool options expose solid color + baked Special controls."""
    html_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "paint-booth-v2.html",
    )
    canvas_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "paint-booth-3-canvas.js",
    )
    state_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "paint-booth-2-state-zones.js",
    )
    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    with open(canvas_path, "r", encoding="utf-8", errors="replace") as f:
        canvas = f.read()
    with open(state_path, "r", encoding="utf-8", errors="replace") as f:
        state = f.read()
    assert 'id="layerPaintSourceOptions"' in html
    assert 'id="layerPaintSourceMode"' in html
    assert 'id="layerSpecialPickerBtn"' in html
    assert "function refreshToolbarModeSensitiveUi()" in canvas
    assert "function setLayerPaintSourceMode(mode, options)" in canvas
    assert "function setLayerPaintSpecial(id, options)" in canvas
    assert "function openLayerSpecialPicker(triggerEl)" in canvas
    assert "type === 'layerSpecialPaint'" in state


def test_layer_effects_ui_reachable():
    """Verify the layer effects dialog is reachable from the layer panel."""
    canvas_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "paint-booth-3-canvas.js",
    )
    with open(canvas_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    assert "ondblclick=\"event.stopPropagation(); openLayerEffects('${l.id}')\"" in content
    assert "<button onclick=\"openLayerEffects('${l.id}')\"" in content


def test_render_timeout_config():
    """Verify render timeout constants exist in the API render module.

    Regression guard: the render system must define timeout thresholds
    so that long renders can be aborted gracefully.
    """
    import re
    api_render_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "paint-booth-5-api-render.js",
    )
    assert os.path.isfile(api_render_path), f"API render file not found: {api_render_path}"
    with open(api_render_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    # Check for timeout-related constants (e.g., RENDER_TIMEOUT, timeout, poll interval)
    has_timeout = bool(re.search(r'(?i)(render.*timeout|poll.*interval|timeout.*ms)', content))
    assert has_timeout, "paint-booth-5-api-render.js must define render timeout or poll interval constants"


def test_runtime_copies_in_sync():
    """Verify manifest-managed runtime copies match the root source files."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.join(repo_root, "scripts", "runtime-sync-manifest.json")
    assert os.path.isfile(manifest_path), f"Runtime sync manifest not found: {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8", errors="replace") as f:
        manifest = json.load(f)

    for rel_file in manifest["files"]:
        src_path = os.path.join(repo_root, rel_file)
        assert os.path.isfile(src_path), f"Missing source-of-truth file: {src_path}"
        with open(src_path, "rb") as f:
            src_bytes = f.read()
        for rel_target_dir in manifest["targets"]:
            # 2026-04-21 post-Codex-audit: preserve subdirectory structure
            # when the manifest entry has one (e.g. `engine/compose.py`
            # must mirror to `<target>/engine/compose.py`, not flatten).
            # Matches the path-join fix in scripts/sync-runtime-copies.js.
            target_path = os.path.join(repo_root, rel_target_dir, rel_file)
            assert os.path.isfile(target_path), f"Missing runtime copy: {target_path}"
            with open(target_path, "rb") as f:
                target_bytes = f.read()
            assert src_bytes == target_bytes, f"Runtime copy drifted: {target_path}"


if __name__ == "__main__":
    failed = main()
    sys.exit(0 if failed == 0 else 1)
