"""Focused regression guard for the owner-protected X LAB Hologram Metal.

Run: C:/Python313/python.exe scripts/spb_verify_protected_hologram_metal.py

This deliberately checks only the semantic recipe line and style-21 diffraction
carrier.  Other X LAB work can proceed without a whole-file hash tripwire;
altering this benchmark requires an intentional update to this guard and Wiki.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "engine" / "expansions" / "x_lab_2026.py"
EXPECTED = {
    "recipe": "807e74a29c1865febb6c3e6a175821f89b894c913f3fc71981ee6a52f48016bc",
    "style21": "d47513e50b868669df7820815617b13aaaf927152426860ad58185541b7c9497",
}


def _digest(label: str, value: str) -> bool:
    actual = hashlib.sha256(value.encode("utf-8")).hexdigest()
    if actual != EXPECTED[label]:
        print(f"FAIL {label}: {actual} != protected {EXPECTED[label]}")
        return False
    print(f"PASS {label}: {actual[:12]}")
    return True


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    recipe = re.search(r'^\s*Recipe\("xlab_hologram_metal".*$', text, re.MULTILINE)
    carrier = re.search(r'^    elif style == 21:.*?(?=^    elif style == 22:)', text, re.MULTILINE | re.DOTALL)
    if recipe is None or carrier is None:
        print("FAIL protected Hologram Metal recipe/carrier cannot be located")
        return 1
    return 0 if _digest("recipe", recipe.group(0)) and _digest("style21", carrier.group(0)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
