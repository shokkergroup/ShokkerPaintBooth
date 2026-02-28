"""Test ALL Color Shift finishes — v5 coordinated dual-map system."""
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("  COLOR SHIFT v5 - FULL TEST (15 Adaptive + 10 Preset)")
print("=" * 60)

import shokker_engine_v2 as eng

shape = (256, 256)
mask = np.ones(shape, dtype=np.float32)
seed = 42
sm = 1.0
pm = 1.0
bb = 0.0

# ALL CS finishes
cs_adaptive = [
    "cs_chrome_shift", "cs_complementary", "cs_cool", "cs_earth",
    "cs_extreme", "cs_monochrome", "cs_neon_shift", "cs_ocean_shift",
    "cs_prism_shift", "cs_rainbow", "cs_split", "cs_subtle",
    "cs_triadic", "cs_vivid", "cs_warm",
]

cs_preset = [
    "cs_deepocean", "cs_emerald", "cs_inferno", "cs_mystichrome",
    "cs_nebula", "cs_solarflare", "cs_supernova",
]

results = []
for group_name, finishes in [("ADAPTIVE", cs_adaptive), ("PRESET", cs_preset)]:
    print(f"\n  --- {group_name} ---")
    for finish in finishes:
        try:
            entry = eng.MONOLITHIC_REGISTRY.get(finish)
            if entry is None:
                print(f"  X {finish:30s} - NOT IN REGISTRY")
                results.append((finish, False, "not in registry"))
                continue
            spec_fn, paint_fn = entry

            spec = spec_fn(shape, mask, seed, sm)
            assert spec.shape == (256, 256, 4), f"spec shape: {spec.shape}"

            paint = np.random.rand(256, 256, 3).astype(np.float32) * 0.5 + 0.3
            paint = paint_fn(paint, shape, mask, seed, pm, bb)
            assert paint.shape == (256, 256, 3), f"paint shape: {paint.shape}"

            m_std = np.std(spec[:,:,0].astype(float))
            p_range = max(np.ptp(paint[:,:,0]), np.ptp(paint[:,:,1]), np.ptp(paint[:,:,2]))

            print(f"  OK {finish:30s} - Spec M_std={m_std:.1f} Paint_range={p_range:.3f}")
            results.append((finish, True, "OK"))
        except Exception as e:
            print(f"  X {finish:30s} - ERROR: {e}")
            results.append((finish, False, str(e)))

passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"\n  {passed}/{total} CS finishes passed")
if passed == total:
    print("  ALL COLOR SHIFT v5 PRESETS WORKING")
else:
    for name, ok, msg in results:
        if not ok:
            print(f"    FAIL: {name} - {msg}")
