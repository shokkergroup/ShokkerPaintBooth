#!/usr/bin/env python3
"""
Registry health script — one-command check for Shokker Paint Booth V5.
Loads the engine, verifies registry counts, and runs contract tests on a sample
of monolithics (spec shape/dtype, paint no-crash, optional PM identity).
Run from repo root: python scripts/validate_registry.py
Output: one-page summary (pass/fail, counts, any failing IDs).
"""

import sys
import os

# Run from V5 root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

def main():
    import numpy as np
    from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY

    SH = (64, 64)
    rng = np.random.RandomState(42)
    paint = rng.rand(*SH, 3).astype(np.float32)
    mask = np.ones(SH, dtype=np.float32)
    bb = 0.5
    seed = 123

    # ---- Counts ----
    n_bases = len(BASE_REGISTRY)
    n_patterns = len(PATTERN_REGISTRY)
    n_mono = len(MONOLITHIC_REGISTRY)

    # ---- Sample monolithics: atelier, grad_, cs_, mc_, fusion_, ghost_, etc. ----
    keys = list(MONOLITHIC_REGISTRY.keys())
    samples = []
    for prefix in ("atelier_", "grad_", "cs_", "mc_", "fusion_", "ghost_", "gradient_", "depth_", "quilt_"):
        for k in keys:
            if k.startswith(prefix):
                samples.append(k)
                if len(samples) >= 80:
                    break
        if len(samples) >= 80:
            break
    # Add random others up to 60 total
    for k in rng.choice(keys, min(60, len(keys)), replace=False):
        if k not in samples:
            samples.append(k)
    samples = samples[:60]

    spec_fail = []
    paint_fail = []
    pm_fail = []

    for kid in samples:
        if kid not in MONOLITHIC_REGISTRY:
            continue
        entry = MONOLITHIC_REGISTRY[kid]
        if isinstance(entry, dict):
            spec_fn = entry.get("spec_fn") or entry.get(0)
            paint_fn = entry.get("paint_fn") or entry.get(1)
        else:
            spec_fn, paint_fn = entry[0], entry[1]
        if spec_fn is None or paint_fn is None:
            spec_fail.append((kid, "missing spec_fn or paint_fn"))
            continue
        try:
            s = spec_fn(SH, mask, seed, 0.5)
            if s.dtype != np.uint8 or s.ndim != 3 or s.shape[2] != 4:
                spec_fail.append((kid, f"spec dtype={s.dtype} shape={s.shape}"))
        except Exception as e:
            spec_fail.append((kid, str(e)))
        try:
            out = paint_fn(paint.copy(), SH, mask, seed, 0.0, bb)
            if out is None or out.shape != paint.shape:
                paint_fail.append((kid, "bad paint output shape"))
            else:
                # PM identity: at pm=0 output should equal input (or very close for some effects)
                diff = np.max(np.abs(out.astype(np.float64) - paint.astype(np.float64)))
                if diff > 0.5:  # allow some finishes to change paint even at pm=0
                    pm_fail.append((kid, f"pm_diff={diff:.4f}"))
        except Exception as e:
            paint_fail.append((kid, str(e)))

    # ---- Report ----
    lines = [
        "========== Registry Health ==========",
        f"Bases:     {n_bases}",
        f"Patterns:  {n_patterns}",
        f"Monolithics: {n_mono}",
        "",
        f"Sampled {len(samples)} monolithics.",
        f"Spec failures:  {len(spec_fail)}",
        f"Paint failures: {len(paint_fail)}",
        f"PM identity (diff>0.5): {len(pm_fail)} (informational)",
        "",
    ]
    if spec_fail:
        lines.append("Spec failures:")
        for kid, msg in spec_fail[:15]:
            lines.append(f"  {kid}: {msg}")
        if len(spec_fail) > 15:
            lines.append(f"  ... and {len(spec_fail) - 15} more")
        lines.append("")
    if paint_fail:
        lines.append("Paint failures:")
        for kid, msg in paint_fail[:15]:
            lines.append(f"  {kid}: {msg}")
        if len(paint_fail) > 15:
            lines.append(f"  ... and {len(paint_fail) - 15} more")
        lines.append("")

    ok = len(spec_fail) == 0 and len(paint_fail) == 0
    lines.append("PASS" if ok else "FAIL")
    report = "\n".join(lines)
    print(report)

    # Optional: write to file
    out_path = os.path.join(ROOT, "REGISTRY_HEALTH.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nWrote {out_path}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
