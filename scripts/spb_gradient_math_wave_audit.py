"""Focused owner-eye bake for the twelve 2026-08-23 Gradient math finishes.

This intentionally does not promote thumbnails.  It runs each card through the
same production snapshot path as the full 178-finish gate, writes paint/spec
contact sheets, and records exact/non-flat evidence so visual iterations stay
cheap without weakening the final all-Gradient release bake.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spb_gradient_overhaul_bake import (  # noqa: E402
    _contact_sheet,
    _engine_and_ids,
    _spec_sheet,
)
from scripts.spb_wilds_110_bake import (  # noqa: E402
    _prepare_unique_stage,
    _run_current_bake,
)


WORK = ROOT / "_gradient_work" / "math_wave_iterations"


def main() -> int:
    import rebuild_thumbnails as baker
    from engine.expansions.gradient_overhaul_2026 import MATH_SPECS

    engine, shipping_ids, _counts = _engine_and_ids()
    ids = sorted(MATH_SPECS)
    if len(ids) != 12 or not set(ids).issubset(shipping_ids):
        raise RuntimeError(f"Gradient math census drift: {len(ids)}")

    stage = _prepare_unique_stage(WORK)
    output_dir = stage / "monolithic"
    rows = []
    failures = []
    for index, finish_id in enumerate(ids, 1):
        try:
            path = _run_current_bake(baker, finish_id, stage)
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None or image.shape[:2] != (256, 256):
                raise RuntimeError(f"invalid baked card: {None if image is None else image.shape}")
            digest = hashlib.sha256(np.ascontiguousarray(image).tobytes()).hexdigest()
            rgb_std = float(image.std())
            unique_rgb = int(np.unique(image.reshape(-1, 3), axis=0).shape[0])
            rows.append({
                "id": finish_id,
                "rgbStd": round(rgb_std, 6),
                "uniqueRgb": unique_rgb,
                "rgbSha256": digest,
            })
            if rgb_std < 8.0 or unique_rgb < 128:
                failures.append(f"{finish_id}: std={rgb_std:.3f} unique={unique_rgb}")
            print(
                f"[gradient-math-audit] {index:02d}/12 {finish_id} "
                f"std={rgb_std:.2f} unique={unique_rgb}",
                flush=True,
            )
        except Exception as exc:
            failures.append(f"{finish_id}: {exc}")

    hashes = [row["rgbSha256"] for row in rows]
    if len(hashes) != len(set(hashes)):
        failures.append("decoded-pixel hash collision")
    _contact_sheet(ids, output_dir, stage / "gradient_12_math_wave_paint_contact.png", 4, 224)
    _spec_sheet(engine, ids, stage / "gradient_12_math_wave_spec_contact.png")
    report = {
        "schema": 1,
        "ticket": "SPB-GRADIENT-MATH-2026-08-23 GM-4",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "count": len(rows),
        "failures": failures,
        "stage": str(stage.relative_to(ROOT)).replace("\\", "/"),
        "finishes": rows,
    }
    (stage / "gradient_12_math_wave_audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[gradient-math-audit] stage={report['stage']}", flush=True)
    return 1 if failures or len(rows) != 12 else 0


if __name__ == "__main__":
    raise SystemExit(main())
