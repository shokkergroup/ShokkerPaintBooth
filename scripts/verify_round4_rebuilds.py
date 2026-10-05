"""Verification script for round-4 spec-pattern rebuilds (2026-05-24).

Confirms each rebuilt pattern returns (256, 256, 3) float32 with no NaN/Inf
and values in [0, 1].
"""
import sys
sys.path.insert(0, r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum")
import numpy as np
from engine.spec_patterns import PATTERN_CATALOG

NAMES = [
    "diffraction_grating",
    "brushed_linear",
    "engraved_crosshatch",
    "spec_carbon_plain_weave",
    "spec_kevlar_weave",
    "spec_hammered_dimple",
    "spec_wood_grain_fine",
    "spec_stone_marble",
    "spec_lava_flow",
    "spec_xirallic_crystal",
    "spec_chromatic_aberration",
]

failures = []
for n in NAMES:
    fn = PATTERN_CATALOG.get(n)
    if fn is None:
        failures.append(f"{n}: NOT IN CATALOG")
        print(f"FAIL {n}: not in PATTERN_CATALOG")
        continue
    try:
        out = np.asarray(fn((256, 256), 4242, 1.0), dtype=np.float32)
    except Exception as e:
        failures.append(f"{n}: render exception {e}")
        print(f"FAIL {n}: render exception {e}")
        continue
    if out.ndim != 3 or out.shape != (256, 256, 3):
        failures.append(f"{n}: bad shape {out.shape}")
        print(f"FAIL {n}: bad shape {out.shape}")
        continue
    if not np.isfinite(out).all():
        failures.append(f"{n}: non-finite values")
        print(f"FAIL {n}: non-finite values")
        continue
    amin, amax = float(out.min()), float(out.max())
    if amin < 0 or amax > 1.001:
        failures.append(f"{n}: bad range [{amin},{amax}]")
        print(f"FAIL {n}: bad range [{amin},{amax}]")
        continue
    print(f"OK {n:32s} M={out[:, :, 0].mean():.2f} R={out[:, :, 1].mean():.2f} CC={out[:, :, 2].mean():.2f}")

print()
if failures:
    print(f"SUMMARY: {len(failures)} FAILURES")
    for f in failures:
        print("  -", f)
    sys.exit(1)
else:
    print(f"SUMMARY: ALL {len(NAMES)} PASS")
