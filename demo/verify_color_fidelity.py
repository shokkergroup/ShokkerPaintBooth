"""Build-only release gate: real shipped captures, no paid-engine imports.

Run python -m demo.verify_color_fidelity. Checks both native snapshot sizes,
every allowed material, finish-own and special color, and literal PNG/TGA output.
This file is deliberately absent from the shipping runtime allowlist.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .backend.catalog import DemoCatalog
from .backend.compositor import DemoCompositor, SnapshotStore
from .backend.validation import validate_render_request


def main():
    root = Path(__file__).resolve().parent
    catalog = DemoCatalog(root / "product-manifest.json")
    snapshots = SnapshotStore(root / "backend/assets/snapshots", catalog)
    compositor = DemoCompositor(catalog, snapshots)
    records = []
    for size in (1024, 2048):
        source = Image.new("RGB", (size, size), (128, 128, 128))
        for finish_id in catalog.finishes:
            snapshot = snapshots.get(finish_id, size)
            assert snapshot.paint.shape[:2] == (size, size), (finish_id, size, "missing native capture")
            assert snapshot.paint_lo is not None and snapshot.color_src is not None, finish_id
            errors = {}
            cases = (
                ("solid", "fs_core_emerald", {"baseColor": [241 / 255, 4 / 255, 20 / 255]}, np.array([241, 4, 20])),
                ("finish", finish_id, {}, snapshot.paint),
                ("special", "fs_core_emerald", {"baseColorSource": finish_id}, snapshot.color_src),
            )
            for mode, material, fields, expected in cases:
                # Red is checked over each base material, not just the Fracture shortcut.
                if mode == "solid":
                    material = finish_id
                request = {"zones": [{"finish": material, "color": "remaining", "baseColorMode": mode,
                    "baseColorDepth": .65, "baseColorFlip": 180, "baseColorUnderglow": .5,
                    "baseStrength": 1, "baseColorStrength": 1, "baseSpecStrength": 3, **fields}]}
                zones = validate_render_request(request, catalog.renderable_ids)
                paint, spec = compositor.render(source, zones)
                actual = np.asarray(paint.convert("RGB"))
                error = int(np.max(np.abs(actual.astype(np.int16) - np.asarray(expected).astype(np.int16))))
                errors[mode] = error
                assert error == 0, (finish_id, size, mode, error)
                # 2026-09-06 Cherry Polka regression: enabling Color Lab at
                # neutral defaults must also preserve every selected color.
                request['zones'][0].update(baseColorLabEnabled=True,
                    baseColorDepth=0, baseColorFlip=0, baseColorUnderglow=0)
                neutral_paint, neutral_spec = compositor.render(source,
                    validate_render_request(request, catalog.renderable_ids))
                neutral = np.asarray(neutral_paint.convert('RGB'))
                assert np.array_equal(neutral, actual), (finish_id, size, mode, 'neutral Lab')
                assert np.array_equal(np.asarray(neutral_spec), np.asarray(spec)), (finish_id, size, mode, 'spec changed')
                for fmt in ('PNG', 'TGA'):
                    encoded = io.BytesIO()
                    neutral_paint.save(encoded, fmt)
                    encoded.seek(0)
                    assert np.array_equal(np.asarray(Image.open(encoded).convert('RGB')), actual)
                if mode == "solid":
                    for fmt in ("PNG", "TGA"):
                        buffer = io.BytesIO()
                        paint.save(buffer, fmt)
                        buffer.seek(0)
                        assert np.all(np.asarray(Image.open(buffer).convert("RGB")) == expected), (finish_id, size, fmt)
            records.append({"finish": finish_id, "size": size, "max_rgb_error": errors})
            print(f"PASS {size} {finish_id}: {errors}", flush=True)
    report = {"build": catalog.raw["product"]["version"], "ok": True,
              "red": "#F10414", "color_lab": "off and enabled with neutral effects; PNG/TGA exact", "checks": records}
    (root / "color-fidelity-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"PASS: {len(records) * 3} Lab-off + {len(records) * 3} neutral-Lab color checks; PNG/TGA exact; spec unchanged.")


if __name__ == "__main__":
    main()
