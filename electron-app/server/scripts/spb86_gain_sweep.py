#!/usr/bin/env python3
"""
SPB-86 — gain sweep tool. Pre-stages the owner's pick between 36 / 54 / 72.

Monkey-patches `_spb_group_detail_profile` to override the Enhanced Foundation
spec_gain at runtime, then bakes 3 representative finishes at each candidate
gain. Reports the predicted macro_std32 mean and saves visual previews so the
owner can click through them side-by-side.

NO source modification. Patch is reverted after each iteration.

USAGE
-----
    python scripts/spb86_gain_sweep.py

Outputs:
* `_workbook_metrics/spb86_gain_sweep.json` — measured macro_std32 per gain
* `_workbook_metrics/spb86_gain_sweep/<finish>_gain<NN>.png` — visual previews

Representative finishes covered:
* `enh_chrome` — chrome-class (high M, low R, high contrast under variation)
* `enh_brushed` — mid-M brushed-metal
* `enh_carbon_fiber` — low-M, dark-substrate
* `enh_pearl` — mid-M with CC contribution
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

V5_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V5_ROOT))


CANDIDATE_GAINS = [18.0, 36.0, 54.0, 72.0]  # 18 = baseline
PROBE_FINISHES = ["enh_chrome", "enh_brushed", "enh_carbon_fiber", "enh_pearl"]
RENDER = 512  # smaller than full bake for speed; macro_std32 stays valid


def block_mean_std(arr: np.ndarray, block: int = 32) -> float:
    h, w = arr.shape[:2]
    if h < block or w < block:
        return float(arr.std())
    bh = h // block; bw = w // block
    cropped = arr[: bh * block, : bw * block]
    blocks = cropped.reshape(bh, block, bw, block).mean(axis=(1, 3))
    return float(blocks.std())


def spec_to_rgb_preview(M, R, CC, swatch_hex: str = "#808080") -> np.ndarray:
    """Same formula as bake_spec_driven_thumbnails.py — make the spec visible."""
    sb = (M * 1.0 + (255.0 - R) * 0.6 + CC * 0.3) / 1.9
    sb = np.clip(sb, 0, 255)
    lo, hi = sb.min(), sb.max()
    if hi - lo > 2.0:
        sb = (sb - lo) / (hi - lo) * 255.0
    sb = np.clip(sb, 0, 255).astype(np.uint8)
    s = swatch_hex.lstrip("#")
    if len(s) == 6:
        tr, tg, tb = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    else:
        tr = tg = tb = 128
    tint = 0.30
    base = sb.astype(np.float32)
    r = base * (1.0 - tint) + (base * (tr / 255.0)) * tint
    g = base * (1.0 - tint) + (base * (tg / 255.0)) * tint
    b = base * (1.0 - tint) + (base * (tb / 255.0)) * tint
    return np.stack([r, g, b], axis=-1).clip(0, 255).astype(np.uint8)


def main() -> int:
    import shokker_engine_v2 as eng  # noqa: F401

    out_dir = V5_ROOT / "_workbook_metrics" / "spb86_gain_sweep"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = V5_ROOT / "_workbook_metrics" / "spb86_gain_sweep.json"

    base = eng.BASE_REGISTRY
    original_profile = eng._spb_group_detail_profile  # save

    results = {}  # gain -> {finish -> macro_std32}

    for gain in CANDIDATE_GAINS:
        # Monkey-patch: only override Enhanced Foundation; defer everything else
        # to the original profile function.
        def patched(group, base_id, _g=gain, _orig=original_profile):
            tup = _orig(group, base_id)
            if group == "Enhanced Foundation":
                # tuple shape: (paint_gain, chroma_gain, spec_gain, structure_mix)
                return (tup[0], tup[1], _g, tup[3])
            return tup
        eng._spb_group_detail_profile = patched

        gain_results = {}
        for stem in PROBE_FINISHES:
            entry = base.get(stem)
            if not entry or not callable(entry.get("base_spec_fn")):
                continue
            seed = hash(stem) & 0x7FFFFFFF
            result = entry["base_spec_fn"]((RENDER, RENDER), seed, 1.0,
                                            entry.get("M", 128),
                                            entry.get("R", 80))
            if len(result) == 2:
                M, R = result
                CC = np.full_like(M, max(16.0, float(entry.get("CC", 16))), dtype=np.float32)
            else:
                M, R, CC = result
            M = M.astype(np.float32, copy=False)
            R = R.astype(np.float32, copy=False)
            CC = CC.astype(np.float32, copy=False)
            m32 = block_mean_std(M)
            r32 = block_mean_std(R)
            cc32 = block_mean_std(CC)
            mean32 = (m32 + r32 + cc32) / 3.0
            gain_results[stem] = {
                "M_macro_std32": round(m32, 3),
                "R_macro_std32": round(r32, 3),
                "CC_macro_std32": round(cc32, 3),
                "mean_macro_std32": round(mean32, 3),
                "M_std": round(float(M.std()), 3),
            }
            # Save preview PNG so owner can click through
            rgb = spec_to_rgb_preview(M, R, CC, "#808080")
            img = Image.fromarray(rgb).resize((256, 256), Image.LANCZOS)
            img.save(out_dir / f"{stem}_gain{int(gain):03d}.png")

        results[f"gain_{int(gain)}"] = {
            "gain": gain,
            "finishes": gain_results,
            "mean_across_probes": round(
                float(np.mean([v["mean_macro_std32"] for v in gain_results.values()])),
                3,
            ) if gain_results else 0.0,
        }

    # Restore
    eng._spb_group_detail_profile = original_profile

    # Report
    print(f"[spb86-sweep] probed {len(PROBE_FINISHES)} finishes at {len(CANDIDATE_GAINS)} gain values")
    print(f"[spb86-sweep] previews saved to: {out_dir}")
    print()
    print(f"  {'gain':>6s}  {'mean':>7s}  " + "  ".join(f"{s[:14]:>14s}" for s in PROBE_FINISHES))
    for gkey, gdata in results.items():
        means = [gdata["finishes"].get(s, {}).get("mean_macro_std32", float("nan")) for s in PROBE_FINISHES]
        print(f"  {int(gdata['gain']):>6d}  {gdata['mean_across_probes']:>7.3f}  " +
              "  ".join(f"{m:>14.3f}" for m in means))

    print()
    base18 = results["gain_18"]["mean_across_probes"]
    for g in [36, 54, 72]:
        cur = results[f"gain_{g}"]["mean_across_probes"]
        ratio = cur / base18 if base18 > 0 else float('inf')
        print(f"  gain {g}: {cur:.3f} mean macro_std32 → {ratio:.2f}× baseline (gain=18)")

    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print()
    print(f"[spb86-sweep] wrote {json_path}")
    print(f"[spb86-sweep] Open the PNGs side-by-side to choose: enh_chrome_gain036.png vs _gain054 vs _gain072")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
