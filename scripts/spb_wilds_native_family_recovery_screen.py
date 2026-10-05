"""Render one old-Wilds silhouette representative per motif family at 2048.

SPB-WILDS-RECOVERY-I1 / SPB-105, 2026-08-24. Owner acceptance is native
2048x2048 only. This screen does not promote old shared renderers; it exposes
their full-size paint/spec output so a genuinely useful silhouette can be
recovered once, then rebuilt behind a bespoke source. Picker size, hashes and
metrics are not acceptance evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "_wilds_fullres_progress_20260824" / "family_recovery_i1"
IDS = (
    "fc_feathered_wing",
    "fmo_starling_sheen",
    "fmo_soap_bubble",
    "fmo_black_opal",
    "fmo_stag_carapace",
    "fmo_nacre_brick",
    "fbl_magenta_mosaic",
    "fpe_lime_chains",
    "fpe_magenta_plankton",
    "fpe_violet_frustule",
)


def _write_rgb(path: Path, rgb: np.ndarray) -> None:
    u8 = np.clip(np.rint(np.asarray(rgb) * 255.0), 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(u8, cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def main() -> int:
    from scripts.spb_wilds_110_bake import _install_and_ids
    from engine.registry import MONOLITHIC_REGISTRY

    _install_and_ids()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    size = 2048
    shape = (size, size)
    substrate = np.zeros((size, size, 3), np.float32)
    mask = np.ones(shape, np.float32)
    rows = []
    for fid in IDS:
        spec_fn, paint_fn = MONOLITHIC_REGISTRY[fid]
        paint = paint_fn(substrate, shape, mask, 1701, 1.0, None)
        spec = spec_fn(shape, mask, 1701, 1.0)[:, :, :3]
        paint_path = OUTPUT / f"{fid}_paint_2048.png"
        spec_path = OUTPUT / f"{fid}_spec_2048.png"
        _write_rgb(paint_path, paint)
        if not cv2.imwrite(str(spec_path), spec):
            raise OSError(f"could not write {spec_path}")
        rows.append({
            "id": fid,
            "paint": paint_path.name,
            "spec": spec_path.name,
            "status": "REJECT-OLD-SHARED-COMPOSER-DO-NOT-PORT",
            "owner_accepted": False,
            "production_wired": False,
        })
    (OUTPUT / "manifest.json").write_text(
        json.dumps({
            "schema": "spb-wilds-native-family-recovery-i1/1",
            "decision_surface": "individual native 2048x2048 images",
            "warning": "old shared-composer silhouettes only; surviving art must receive a bespoke port",
            "rows": rows,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
