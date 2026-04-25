"""
Benchmark the top finish types to identify the slowest ones.
Run: python benchmark_finishes.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SHOKKER_QUIET"] = "1"

import numpy as np
print("Loading engine...")
import engine
from engine.registry import BASE_REGISTRY, MONOLITHIC_REGISTRY

SHAPE = (1024, 1024)  # Half-res for faster benchmarking
MASK = np.ones(SHAPE, dtype=np.float32)
PAINT = np.random.rand(SHAPE[0], SHAPE[1], 3).astype(np.float32) * 0.5 + 0.25  # 3-channel RGB
SEED = 42
SM, PM, BB = 1.0, 1.0, 0.0

results = []

# Benchmark bases (spec + paint)
print("\n=== BENCHMARKING BASES ===")
for key, entry in list(BASE_REGISTRY.items())[:50]:
    if not isinstance(entry, dict):
        continue
    spec_fn = entry.get("base_spec_fn")
    paint_fn = entry.get("paint_fn")
    M, R = float(entry.get("M", 100)), float(entry.get("R", 100))

    total = 0
    try:
        if spec_fn:
            t0 = time.perf_counter()
            spec_fn(SHAPE, SEED, SM, M, R)
            total += time.perf_counter() - t0
        if paint_fn:
            t0 = time.perf_counter()
            paint_fn(PAINT.copy(), SHAPE, MASK, SEED, PM, BB)
            total += time.perf_counter() - t0
        results.append(("base", key, total))
    except Exception as e:
        results.append(("base", key, -1))

# Benchmark monolithics (spec + paint)
print("=== BENCHMARKING MONOLITHICS ===")
for key, entry in list(MONOLITHIC_REGISTRY.items())[:50]:
    spec_fn = paint_fn = None
    if isinstance(entry, (tuple, list)) and len(entry) >= 2:
        spec_fn, paint_fn = entry[0], entry[1]
    elif isinstance(entry, dict):
        spec_fn = entry.get("spec_fn")
        paint_fn = entry.get("paint_fn")

    total = 0
    try:
        if spec_fn:
            t0 = time.perf_counter()
            spec_fn(SHAPE, MASK, SEED, SM)
            total += time.perf_counter() - t0
        if paint_fn:
            t0 = time.perf_counter()
            paint_fn(PAINT.copy(), SHAPE, MASK, SEED, PM, BB)
            total += time.perf_counter() - t0
        results.append(("mono", key, total))
    except Exception as e:
        results.append(("mono", key, -1))

# Sort by time, show top 20 slowest
results.sort(key=lambda x: x[2], reverse=True)
print(f"\n{'='*60}")
print(f"  TOP 20 SLOWEST FINISHES (at {SHAPE[0]}x{SHAPE[1]})")
print(f"{'='*60}")
for i, (ftype, key, elapsed) in enumerate(results[:20]):
    if elapsed < 0:
        print(f"  {i+1:2d}. [{ftype}] {key}: CRASHED")
    else:
        # Estimate 2048x2048 time (4x pixels)
        est_2k = elapsed * 4
        print(f"  {i+1:2d}. [{ftype}] {key}: {elapsed*1000:.0f}ms (est. {est_2k*1000:.0f}ms at 2048)")

print(f"\n  Tested {len(results)} finishes")
fast = sum(1 for _, _, t in results if 0 <= t < 0.1)
medium = sum(1 for _, _, t in results if 0.1 <= t < 0.5)
slow = sum(1 for _, _, t in results if 0.5 <= t < 2.0)
very_slow = sum(1 for _, _, t in results if t >= 2.0)
crashed = sum(1 for _, _, t in results if t < 0)
print(f"  Fast (<100ms): {fast}")
print(f"  Medium (100-500ms): {medium}")
print(f"  Slow (500ms-2s): {slow}")
print(f"  Very slow (>2s): {very_slow}")
print(f"  Crashed: {crashed}")
print(f"{'='*60}")
