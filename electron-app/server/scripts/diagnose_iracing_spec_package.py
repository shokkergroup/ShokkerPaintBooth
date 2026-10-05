#!/usr/bin/env python
"""Diagnose an iRacing paint/spec package before Trading Paints upload.

This script does not decode proprietary .mip files. It inspects the source
paint/spec TGA or PNG files that iRacing uses to generate the MIP, then reports
the common compatibility traps:

- paint file has an alpha channel when Trading Paints expects normal paints as
  24-bit/no-alpha uploads
- spec map has a non-opaque alpha/specular-mask channel
- metallic spec values are high while the paint/albedo under them is dark,
  which can read as black in iRacing's metallic shader
- dimensions differ or are not 1024/2048 square

Usage:
  python -B scripts/diagnose_iracing_spec_package.py --paint car_num_123.tga --spec car_spec_123.tga
  python -B scripts/diagnose_iracing_spec_package.py --paint car_num_123.tga --spec car_spec_123.tga --mip car_spec_123.mip
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


def _load_image(path: Path) -> tuple[np.ndarray, str]:
    with Image.open(path) as img:
        mode = img.mode
        arr = np.asarray(img.convert("RGBA"), dtype=np.uint8)
    return arr, mode


def _channel_stats(arr: np.ndarray) -> dict[str, float]:
    data = np.asarray(arr, dtype=np.float32)
    return {
        "min": float(data.min()),
        "max": float(data.max()),
        "mean": float(data.mean()),
        "std": float(data.std()),
    }


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def diagnose(paint_path: Path, spec_path: Path, mip_path: Path | None = None) -> dict[str, Any]:
    paint, paint_mode = _load_image(paint_path)
    spec, spec_mode = _load_image(spec_path)

    h, w = paint.shape[:2]
    sh, sw = spec.shape[:2]
    paint_rgb = paint[:, :, :3].astype(np.float32) / 255.0
    paint_alpha = paint[:, :, 3]
    spec_m = spec[:, :, 0]
    spec_r = spec[:, :, 1]
    spec_b = spec[:, :, 2]
    spec_a = spec[:, :, 3]

    # Approximate sRGB luma. This is only a risk metric, not a color-managed render.
    luma = 0.2126 * paint_rgb[:, :, 0] + 0.7152 * paint_rgb[:, :, 1] + 0.0722 * paint_rgb[:, :, 2]
    metallic_mask = spec_m >= 160
    dark_metal_mask = metallic_mask & (luma < 0.22)
    strong_dark_metal_mask = (spec_m >= 210) & (luma < 0.32)

    warnings: list[str] = []
    if (h, w) != (sh, sw):
        warnings.append(f"Paint/spec dimensions differ: paint {w}x{h}, spec {sw}x{sh}.")
    if h != w or h not in (1024, 2048):
        warnings.append(f"Paint is {w}x{h}; iRacing spec workflows expect 1024x1024 or 2048x2048 square files.")
    if sh != sw or sh not in (1024, 2048):
        warnings.append(f"Spec is {sw}x{sh}; iRacing spec workflows expect 1024x1024 or 2048x2048 square files.")
    if paint_mode in ("RGBA", "LA") or int(paint_alpha.min()) < 255:
        warnings.append("Paint has an alpha channel or non-opaque alpha. Trading Paints black-paint troubleshooting points at 32-bit/alpha paint uploads as a common cause.")
    if int(spec_a.min()) < 250:
        pct = float(np.mean(spec_a < 250) * 100.0)
        warnings.append(f"Spec alpha/specular-mask is not fully opaque on {pct:.2f}% of pixels. Alpha can mask lighting and can make materials look dead/black.")
    if dark_metal_mask.any():
        pct = float(np.mean(dark_metal_mask) * 100.0)
        warnings.append(f"{pct:.2f}% of pixels are metallic (M>=160) over very dark paint luma (<0.22). iRacing metallic albedo often needs to be much lighter or it can read black.")
    if strong_dark_metal_mask.any():
        pct = float(np.mean(strong_dark_metal_mask) * 100.0)
        warnings.append(f"{pct:.2f}% of pixels are high-metallic (M>=210) over dark paint luma (<0.32). This is a high-risk black-shift zone.")

    result: dict[str, Any] = {
        "paint": {
            "path": str(paint_path),
            "mode": paint_mode,
            "size": [w, h],
            "sha256": _hash_file(paint_path),
            "alpha": _channel_stats(paint_alpha),
        },
        "spec": {
            "path": str(spec_path),
            "mode": spec_mode,
            "size": [sw, sh],
            "sha256": _hash_file(spec_path),
            "metallic_R": _channel_stats(spec_m),
            "roughness_G": _channel_stats(spec_r),
            "blue_or_clearcoat_B": _channel_stats(spec_b),
            "alpha_spec_mask": _channel_stats(spec_a),
        },
        "risk_metrics": {
            "metallic_pixels_pct": float(np.mean(metallic_mask) * 100.0),
            "dark_metallic_pixels_pct": float(np.mean(dark_metal_mask) * 100.0),
            "strong_dark_metallic_pixels_pct": float(np.mean(strong_dark_metal_mask) * 100.0),
        },
        "warnings": warnings,
        "mip": None,
    }

    if mip_path:
        result["mip"] = {
            "path": str(mip_path),
            "exists": mip_path.exists(),
            "size_bytes": int(mip_path.stat().st_size) if mip_path.exists() else 0,
            "sha256": _hash_file(mip_path) if mip_path.exists() else None,
            "note": "MIP is proprietary; this tool records file identity/size only. Compare before/after Trading Paints downloads by hash.",
        }

    return result


def _print_human(report: dict[str, Any]) -> None:
    print("iRacing/Trading Paints Spec Package Diagnostic")
    print("=" * 48)
    print(f"Paint: {report['paint']['path']}")
    print(f"  mode={report['paint']['mode']} size={report['paint']['size']} alpha={report['paint']['alpha']}")
    print(f"Spec:  {report['spec']['path']}")
    print(f"  mode={report['spec']['mode']} size={report['spec']['size']}")
    for key in ("metallic_R", "roughness_G", "blue_or_clearcoat_B", "alpha_spec_mask"):
        print(f"  {key}: {report['spec'][key]}")
    print("Risk metrics:")
    for key, value in report["risk_metrics"].items():
        print(f"  {key}: {value:.3f}")
    if report["mip"]:
        print(f"MIP: {report['mip']['path']}")
        print(f"  exists={report['mip']['exists']} size_bytes={report['mip']['size_bytes']} sha256={report['mip']['sha256']}")
    if report["warnings"]:
        print("Warnings:")
        for warning in report["warnings"]:
            print(f"  - {warning}")
    else:
        print("Warnings: none")
    print("MIP-only check:")
    print("  After iRacing generates car_spec_<id>.mip, rename/remove car_spec_<id>.tga locally and reload the car.")
    print("  If it turns black locally with only the MIP present, the problem is the MIP conversion/source data, not Trading Paints.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paint", required=True, type=Path, help="Path to car_num_<id>.tga, car_<id>.tga, or paint PNG.")
    parser.add_argument("--spec", required=True, type=Path, help="Path to car_spec_<id>.tga or spec PNG.")
    parser.add_argument("--mip", type=Path, help="Optional car_spec_<id>.mip to hash/compare.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    report = diagnose(args.paint, args.spec, args.mip)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)
    return 1 if report["warnings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
