# SPB Performance Guide

> Where SPB spends its time, what to measure, and how to make it faster without breaking it.

---

## Perf Budgets

These are rough targets for a modern mid-range Windows laptop (Ryzen 7, 16 GB RAM, no GPU acceleration):

| Operation | Budget | Current |
|---|---:|---:|
| Cold boot to main window | < 6 s | ~4–5 s |
| Load a PSD (10–20 layers) | < 3 s | ~2–3 s |
| Render a simple livery (1 finish, no pattern) | < 800 ms | ~600 ms |
| Render a complex livery (5 zones, 3 patterns, 2 overlays) | < 3 s | ~2.5–3 s |
| TGA export | < 500 ms | ~400 ms |
| Undo/redo step | < 50 ms | varies (see below) |

If you're hitting these, ship it. If you're 2x over, profile before optimizing.

---

## Known Hotspots

### 1. `shokker_engine_v2.py` — the render loop
The engine walks every zone, every pattern, and every overlay. It's numpy-heavy.

**Optimization wins that worked:**
- Vectorizing pixel-per-pixel operations to `np.where` / `np.choose`
- Pre-computing LUTs (lookup tables) for color-shift curves
- Caching the last spec map if geometry hasn't changed
- Using `np.float32` instead of `np.float64` when precision allows

**Pitfalls:**
- `np.einsum` can be slower than naive broadcasting in some cases
- `np.copy()` on every zone is death — mutate in place when safe
- PIL → numpy conversion is expensive; keep things in numpy

### 2. DOM rebuild in `renderZones()`
`paint-booth-2-state-zones.js` rebuilds the entire zone list on any state change. For users with 50+ zones this stutters.

**Known fix on backlog:** diff-based updates with keyed DOM nodes. Not yet implemented.

**Workaround if you hit it:** throttle `renderZones()` calls with `requestAnimationFrame` debouncing.

### 3. Undo stack (unbounded)
Every state mutation pushes onto an unbounded stack. Users doing heavy painting can grow this to hundreds of MB.

**Known fix on backlog:** cap at 100 entries + LZ4-compress older entries.

### 4. Render preview polling
Client polls `/render/status` every 250 ms. With many concurrent renders this adds up.

**Known fix on backlog:** Server-Sent Events (SSE) for push updates.

### 5. Finish data linear scans
`paint-booth-0-finish-data.js` ships flat arrays. Lookups are O(n). With 500+ finishes that's noticeable.

**Known fix on backlog:** build an index at boot (`BASES_BY_ID = Object.fromEntries(BASES.map(b => [b.id, b]))`).

---

## Measuring

### Server timing
Add a decorator to hot functions:

```python
import time, functools
def timed(fn):
    @functools.wraps(fn)
    def wrap(*a, **kw):
        t = time.perf_counter()
        r = fn(*a, **kw)
        print(f"[timing] {fn.__name__}: {(time.perf_counter()-t)*1000:.1f}ms")
        return r
    return wrap
```

### Client timing
```js
performance.mark('render-start');
await doRender();
performance.mark('render-end');
performance.measure('render', 'render-start', 'render-end');
console.log(performance.getEntriesByName('render')[0].duration, 'ms');
```

### Memory
Python: `import psutil; psutil.Process().memory_info().rss`
JS: `performance.memory.usedJSHeapSize`

### End-to-end bench
`benchmark_finishes.py` runs each registered finish once at 2048x2048 and prints per-finish timing. Use as a regression guard:

```bash
python benchmark_finishes.py > bench_before.txt
# make your change
python benchmark_finishes.py > bench_after.txt
diff bench_before.txt bench_after.txt
```

---

## Optimization Principles

1. **Measure, don't guess.** Always profile before optimizing. "Obvious" bottlenecks usually aren't.
2. **Make it work, then fast.** Correctness first. A slow render is debuggable; a fast wrong render is a mystery.
3. **Cache aggressively, invalidate correctly.** The classic. LRU caches on finish functions work well.
4. **Prefer vectorized numpy.** Hot loops in Python are ~50x slower than vectorized.
5. **Avoid allocations in inner loops.** Pre-allocate output arrays; reuse buffers.
6. **Don't optimize UI code prematurely.** Users tolerate 100 ms latency on a click. They don't tolerate wrong output.
7. **Respect the 3-copy sync rule.** Don't hand-optimize one copy only.

---

## Profiling Session Template

```bash
# 1. Baseline
python benchmark_finishes.py > bench_baseline.txt

# 2. Profile the slow op
python -m cProfile -o profile.prof -s cumulative benchmark_finishes.py --finish <slow_id>

# 3. Visualize
snakeviz profile.prof
# or
python -c "import pstats; pstats.Stats('profile.prof').sort_stats('cumulative').print_stats(30)"

# 4. Make your change

# 5. Re-measure
python benchmark_finishes.py > bench_after.txt
diff bench_baseline.txt bench_after.txt

# 6. Sanity check: does render output still match pixel-for-pixel (or within tolerance)?
python scripts/compare_renders.py <old.png> <new.png>  # if such a script exists
```

---

## GPU Acceleration

`engine/gpu.py` has experimental GPU paths. Not all finishes use them. If you're optimizing a specific finish, check whether a GPU implementation would help — but be aware:

- Users without CUDA fall back to CPU. Keep the CPU path correct.
- GPU transfer overhead wipes out gains for small renders.
- Typical breakeven: 2048x2048 becomes GPU-favorable at ~5 passes.

---

## Don't-Optimize List

Stuff that looks slow but isn't worth touching:

- `import numpy` at module top (happens once; ~50 ms)
- JSON serialization of `.spb` files (user is saving; latency is acceptable)
- PSD layer parsing (one-shot on load; `psd-tools` is already good)
- PIL JPEG encoding (not in hot path)

---

## See Also

- [DEBUGGING.md](DEBUGGING.md)
- [TESTING.md](TESTING.md) — add perf regression tests where useful
- [ARCHITECTURE.md](ARCHITECTURE.md) — understand the system before optimizing it
