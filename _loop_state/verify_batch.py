import sys, time
sys.path.insert(0, r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum")
import numpy as np
from engine.spec_patterns import PATTERN_CATALOG

BATCH = [
    "suspension_rust_ring",
    "tarmac_grit_embed",
    "tire_rubber_transfer",
    "tire_smoke_residue",
    "tire_smoke_streaks",
    "topographic_steps",
    "track_grime",
    "undercarriage_spray",
    "vinyl_seam",
    "vinyl_stretched",
    "vinyl_wrap_texture",
    "voronoi_fracture",
]

fails = []
times = []
for n in BATCH:
    t0 = time.perf_counter()
    out = np.asarray(PATTERN_CATALOG[n]((256, 256), 4242, 1.0), dtype=np.float32)
    dt = (time.perf_counter() - t0) * 1000
    times.append((n, dt))
    ok = (
        out.ndim == 3
        and out.shape == (256, 256, 3)
        and np.isfinite(out).all()
        and 0 <= out.min()
        and out.max() <= 1.001
        and dt < 400
    )
    tag = "OK" if ok else "FAIL"
    if not ok:
        fails.append((n, out.shape, float(out.min()), float(out.max()), dt))
    print(f"{tag} {n:40s} shape={out.shape} range=[{out.min():.2f},{out.max():.2f}] {dt:.0f}ms")

print("FAILS", len(fails))
if times:
    ms = [t for _, t in times]
    print(f"min={min(ms):.0f}ms max={max(ms):.0f}ms mean={sum(ms)/len(ms):.0f}ms")
