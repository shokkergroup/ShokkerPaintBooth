"""Fail-closed real-engine bake for SPB-GRADIENT-OVERHAUL-2026-08-23.

Stages all 178 Gradient cards in a fresh directory, rejects stale/flat/exactly
duplicated output, writes paint/spec contact sheets and palette-occupancy
evidence, then transactionally promotes the complete set to the shipping
monolithic thumbnail tree.  Buyer picker cards are rebuilt separately after
this metric/owner-eye gate passes.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spb_wilds_110_bake import (  # noqa: E402
    _prepare_unique_stage,
    _promote_after_all_gates,
    _run_current_bake,
)

WORK = ROOT / "_gradient_work"
REPORT = WORK / "gradient_178_thumbnail_gate.json"
CARD_SIZE = 256
EXPECTED_COUNTS = {"legacy": 125, "showcase": 43, "material": 10}
EXPECTED_TOTAL = sum(EXPECTED_COUNTS.values())


def _engine_and_ids():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()
    ids = sorted(
        finish_id
        for finish_id in engine.MONOLITHIC_REGISTRY
        if finish_id.startswith(("grad_", "grd_", "gradient_"))
    )
    counts = {
        "legacy": sum(fid.startswith("grad_") for fid in ids),
        "showcase": sum(fid.startswith("grd_") for fid in ids),
        "material": sum(fid.startswith("gradient_") for fid in ids),
    }
    if counts != EXPECTED_COUNTS:
        raise RuntimeError(f"Gradient census drift: {counts}")
    return engine, ids, counts


def _write_report(report: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temp = REPORT.with_name(f"{REPORT.name}.tmp.{os.getpid()}")
    temp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, REPORT)


def _contact_sheet(ids: list[str], source_dir: Path, target: Path, columns: int, image_size: int) -> None:
    label_h = 24
    cell_w = image_size + 12
    cell_h = image_size + label_h + 8
    rows = (len(ids) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), (12, 15, 21))
    draw = ImageDraw.Draw(sheet)
    for index, finish_id in enumerate(ids):
        image = Image.open(source_dir / f"{finish_id}.png").convert("RGB")
        image = image.resize((image_size, image_size), Image.Resampling.LANCZOS)
        x = (index % columns) * cell_w + 6
        y = (index // columns) * cell_h + 4
        sheet.paste(image, (x, y))
        label = finish_id.replace("gradient_", "gmat_")
        draw.text((x, y + image_size + 3), label[:28], fill=(228, 234, 242))
    sheet.save(target)


def _spec_sheet(engine, ids: list[str], target: Path) -> None:
    columns, size, gap, label_h = 5, 192, 10, 24
    rows = (len(ids) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * (size + gap), rows * (size + label_h + gap)), (12, 15, 21))
    draw = ImageDraw.Draw(sheet)
    mask = np.ones((size, size), np.float32)
    for index, finish_id in enumerate(ids):
        spec_fn = engine.MONOLITHIC_REGISTRY[finish_id][0]
        spec = spec_fn((size, size), mask, 7301, 1.0)
        rgb = np.ascontiguousarray(spec[:, :, :3].astype(np.uint8))
        image = Image.fromarray(rgb, mode="RGB")
        x = (index % columns) * (size + gap) + 5
        y = (index // columns) * (size + label_h + gap) + 4
        sheet.paste(image, (x, y))
        draw.text((x, y + size + 3), finish_id[:28], fill=(228, 234, 242))
    sheet.save(target)


def main() -> int:
    import rebuild_thumbnails as baker
    from engine.expansions.gradient_overhaul_2026 import (
        EXTREME_SPECS,
        MATH_SPECS,
        gradient_palette_occupancy,
        gradient_recipe,
    )

    engine, ids, counts = _engine_and_ids()
    stage = _prepare_unique_stage(WORK)
    output_dir = stage / "monolithic"
    rows: list[dict] = []
    failures: list[str] = []

    for index, finish_id in enumerate(ids, 1):
        try:
            path = _run_current_bake(baker, finish_id, stage)
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None:
                raise RuntimeError(f"{finish_id}: baked PNG did not decode")
            rgb_std = float(image.std())
            unique_rgb = int(np.unique(image.reshape(-1, 3), axis=0).shape[0])
            pixel_hash = hashlib.sha256(np.ascontiguousarray(image).tobytes()).hexdigest()
            recipe = gradient_recipe(finish_id)
            occupancy = gradient_palette_occupancy(finish_id, 256, 7301)
            row = {
                "id": finish_id,
                "family": recipe.family,
                "topology": recipe.topology,
                "orientation": recipe.orientation,
                "paletteStops": recipe.stop_count,
                "minimumStopOccupancy": round(min(occupancy), 8),
                "rgbStd": round(rgb_std, 6),
                "uniqueRgb": unique_rgb,
                "rgbSha256": pixel_hash,
                "fileSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "width": int(image.shape[1]),
                "height": int(image.shape[0]),
            }
            rows.append(row)
            if image.shape[:2] != (CARD_SIZE, CARD_SIZE) or rgb_std < 8.0 or unique_rgb < 128:
                failures.append(
                    f"{finish_id}: shape={image.shape[:2]} std={rgb_std:.3f} unique={unique_rgb}"
                )
            if recipe.family in {"showcase", "extreme", "math"} and not (10 <= recipe.stop_count <= 15):
                failures.append(f"{finish_id}: invalid showcase palette depth {recipe.stop_count}")
            if recipe.family == "extreme" and min(occupancy) < 0.01:
                failures.append(f"{finish_id}: dead palette stop, min occupancy={min(occupancy):.6f}")
            print(
                f"[gradient-bake] {index:03d}/{len(ids)} {finish_id} "
                f"stops={recipe.stop_count} std={rgb_std:.2f}",
                flush=True,
            )
        except Exception as exc:
            failures.append(str(exc))
            print(f"[gradient-bake] {index:03d}/{len(ids)} FAIL {finish_id}: {exc}", flush=True)

    hashes = [row["rgbSha256"] for row in rows]
    duplicate_hashes = sorted({digest for digest in hashes if hashes.count(digest) > 1})
    if duplicate_hashes:
        failures.append(f"{len(duplicate_hashes)} exact decoded-pixel duplicate hash(es)")

    report = {
        "schema": 1,
        "ticket": "SPB-GRADIENT-OVERHAUL-2026-08-23 tick GM-1",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "scope": counts,
        "count": len(rows),
        "extremeCount": len(EXTREME_SPECS),
        "mathCount": len(MATH_SPECS),
        "allNonFlat": not failures and len(rows) == EXPECTED_TOTAL,
        "allExactHashesUnique": not duplicate_hashes and len(hashes) == EXPECTED_TOTAL,
        "minimumRgbStd": min((row["rgbStd"] for row in rows), default=None),
        "minimumUniqueRgb": min((row["uniqueRgb"] for row in rows), default=None),
        "minimumExtremeStopOccupancy": min(
            (row["minimumStopOccupancy"] for row in rows if row["family"] == "extreme"),
            default=None,
        ),
        "failures": failures,
        "stage": str(stage.relative_to(ROOT)).replace("\\", "/"),
        "promotionState": "blocked",
        "publishedToRoot": False,
        "finishes": rows,
    }

    if not failures and len(rows) == EXPECTED_TOTAL:
        try:
            all_contact = stage / "gradient_178_paint_contact.png"
            extreme_contact = stage / "gradient_20_extreme_paint_contact.png"
            vortex_contact = stage / "gradient_50_vortex_paint_contact.png"
            extreme_spec = stage / "gradient_20_extreme_spec_contact.png"
            math_contact = stage / "gradient_12_math_wave_paint_contact.png"
            math_spec = stage / "gradient_12_math_wave_spec_contact.png"
            extreme_ids = sorted(EXTREME_SPECS)
            math_ids = sorted(MATH_SPECS)
            vortex_ids = [finish_id for finish_id in ids if finish_id.endswith("_vortex")]
            _contact_sheet(ids, output_dir, all_contact, 10, 128)
            _contact_sheet(extreme_ids, output_dir, extreme_contact, 5, 192)
            _contact_sheet(vortex_ids, output_dir, vortex_contact, 5, 160)
            _spec_sheet(engine, extreme_ids, extreme_spec)
            _contact_sheet(math_ids, output_dir, math_contact, 4, 224)
            _spec_sheet(engine, math_ids, math_spec)
            report["contactSheets"] = [
                str(path.relative_to(ROOT)).replace("\\", "/")
                for path in (
                    all_contact,
                    extreme_contact,
                    vortex_contact,
                    extreme_spec,
                    math_contact,
                    math_spec,
                )
            ]
            report["promotionState"] = "all-gates-passed; promotion-pending"
            _write_report(report)
            _promote_after_all_gates(ids, output_dir, ROOT / "thumbnails" / "monolithic")
            report["promotionState"] = "committed"
            report["publishedToRoot"] = True
        except Exception as exc:
            failures.append(str(exc))
            report["failures"] = failures
            report["promotionState"] = "failed; prior root set restored"

    _write_report(report)
    if failures or len(rows) != EXPECTED_TOTAL:
        print(f"[gradient-bake] FAIL: {len(failures)} issue(s)", flush=True)
        return 1
    print(
        f"[gradient-bake] PASS: {EXPECTED_TOTAL}/{EXPECTED_TOTAL} non-flat, "
        "exact hashes unique, promoted",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
