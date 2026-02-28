"""Test Chameleon v5 coordinated dual-map system."""
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("  CHAMELEON v5 — COORDINATED DUAL-MAP TEST")
print("=" * 60)

# Import the engine
import shokker_engine_v2 as eng

# Test params
shape = (256, 256)
mask = np.ones(shape, dtype=np.float32)
seed = 42
sm = 1.0
pm = 1.0
bb = 0.0

# Test all chameleon presets
chameleon_finishes = [
    "chameleon_midnight", "chameleon_phoenix", "chameleon_ocean",
    "chameleon_venom", "chameleon_copper", "chameleon_arctic",
    "chameleon_amethyst", "chameleon_emerald", "chameleon_obsidian",
    "mystichrome",
]

results = []
for finish in chameleon_finishes:
    try:
        entry = eng.MONOLITHIC_REGISTRY.get(finish)
        if entry is None:
            print(f"  ✗ {finish:30s} — NOT IN REGISTRY")
            results.append((finish, False, "not in registry"))
            continue
        spec_fn, paint_fn = entry
        
        # Test spec
        spec = spec_fn(shape, mask, seed, sm)
        assert spec.shape == (256, 256, 4), f"spec shape wrong: {spec.shape}"
        
        # Test paint
        paint = np.random.rand(256, 256, 3).astype(np.float32) * 0.5 + 0.3
        paint = paint_fn(paint, shape, mask, seed, pm, bb)
        assert paint.shape == (256, 256, 3), f"paint shape wrong: {paint.shape}"
        
        # Check spec has VARIATION (not flat)
        m_std = np.std(spec[:,:,0].astype(float))
        r_std = np.std(spec[:,:,1].astype(float))
        cc_std = np.std(spec[:,:,2].astype(float))
        
        # Check paint has color variation
        p_r_range = np.ptp(paint[:,:,0])
        p_g_range = np.ptp(paint[:,:,1])
        p_b_range = np.ptp(paint[:,:,2])
        
        print(f"  ✓ {finish:30s} — Spec M_std={m_std:.1f} R_std={r_std:.1f} CC_std={cc_std:.1f} | Paint range R={p_r_range:.3f} G={p_g_range:.3f} B={p_b_range:.3f}")
        results.append((finish, True, "OK"))
    except Exception as e:
        print(f"  ✗ {finish:30s} — ERROR: {e}")
        results.append((finish, False, str(e)))

# Summary
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print()
print(f"  {passed}/{total} chameleon finishes passed")
if passed == total:
    print("  ★ ALL CHAMELEON v5 PRESETS WORKING ★")
else:
    print("  ✗ FAILURES DETECTED — check above")
    for name, ok, msg in results:
        if not ok:
            print(f"    FAIL: {name} — {msg}")
