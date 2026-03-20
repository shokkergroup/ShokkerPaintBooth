"""
Shokker V5 Smoke Test
======================
Minimal sanity check: registries load, key finishes render to valid PNG.
Run after engine changes to catch regressions quickly.

Usage:
  cd "Shokker Paint Booth V5"
  python tests/smoke_test.py
"""

import sys
import os

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
    """Avoid Windows console encoding errors with Unicode in exception messages."""
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
    """PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A"""
    return data and len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n"


print("\n" + "=" * 60)
print("  SHOKKER V5 SMOKE TEST")
print("=" * 60 + "\n")

# == 1. REGISTRY LOAD =================================================
print("1. Registry load")
try:
    from engine.registry import (
        BASE_REGISTRY,
        PATTERN_REGISTRY,
        MONOLITHIC_REGISTRY,
        FUSION_REGISTRY,
    )
    check("BASE_REGISTRY loaded", len(BASE_REGISTRY) >= 50, f"{len(BASE_REGISTRY)} entries")
    check("PATTERN_REGISTRY loaded", len(PATTERN_REGISTRY) >= 200, f"{len(PATTERN_REGISTRY)} entries")
    check("MONOLITHIC_REGISTRY loaded", len(MONOLITHIC_REGISTRY) >= 500, f"{len(MONOLITHIC_REGISTRY)} entries")
    check("FUSION_REGISTRY loaded", len(FUSION_REGISTRY) >= 100, f"{len(FUSION_REGISTRY)} entries")
except Exception as e:
    check("Registry load", False, str(e))
    print("\n" + "=" * 60)
    print("  ABORTED: Registry failed to load")
    print("=" * 60 + "\n")
    sys.exit(1)

print()

# == 2. SWATCH RENDER (full API path) =================================
print("2. Swatch render (base, metallic, cs_cool)")
try:
    from server_v5 import render_swatch
    if render_swatch is None:
        check("render_swatch available", False, "server import failed")
    else:
        # Base: gloss
        png = render_swatch("base", "gloss", "888888", 64, 42)
        check("Base gloss -> PNG", is_valid_png(png), f"{len(png) if png else 0} bytes")

        # Base: metallic
        png2 = render_swatch("base", "metallic", "446688", 64, 42)
        check("Base metallic -> PNG", is_valid_png(png2), f"{len(png2) if png2 else 0} bytes")

        # Monolithic: cs_cool
        png3 = render_swatch("monolithic", "cs_cool", "888888", 64, 42)
        check("Monolithic cs_cool -> PNG", is_valid_png(png3), f"{len(png3) if png3 else 0} bytes")
except Exception as e:
    check("Swatch render", False, str(e)[:80])

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

sys.exit(0 if failed == 0 else 1)
