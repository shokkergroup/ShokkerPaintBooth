"""Verify Smart TGA companion-decal fixtures against `/api/auto-layers`.

This offline checker consumes the fixture manifest produced by
`smart_tga_decal_companion_audit.py --export-applied-masks`, calls the Flask
test client for each source TGA, decodes the returned Sponsor/Number masks, and
measures whether the expected companion-decal Sponsor pixels survived the route.
It does not start, stop, or modify the live app server.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


DEFAULT_MANIFEST = Path("_smart_tga_runs/cycle103_decal_companion_audit_export_v1/applied_masks/manifest.json")
DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_decal_route_fixture_check")
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _read_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"expected manifest list in {path}")
    return data


def _decode_data_url_mask(data_url: str, size: tuple[int, int] | None = None) -> np.ndarray:
    if not isinstance(data_url, str) or "," not in data_url:
        raise ValueError("expected PNG data URL")
    raw = base64.b64decode(data_url.split(",", 1)[1])
    img = Image.open(io.BytesIO(raw)).convert("L")
    if size and img.size != size:
        img = img.resize(size, Image.Resampling.NEAREST)
    return np.asarray(img) > 127


def _read_expected_mask(path: str, size: tuple[int, int] | None = None) -> np.ndarray:
    img = Image.open(path).convert("L")
    if size and img.size != size:
        img = img.resize(size, Image.Resampling.NEAREST)
    return np.asarray(img) > 127


def _source_image(path: str, size: tuple[int, int]) -> Image.Image:
    return Image.open(path).convert("RGB").resize(size, Image.Resampling.LANCZOS)


def _effective_stats(expected: np.ndarray, sponsors: np.ndarray, numbers: np.ndarray) -> dict[str, Any]:
    expected_effective = expected & ~numbers
    expected_count = int(expected.sum())
    effective_count = int(expected_effective.sum())
    covered = int((expected_effective & sponsors).sum())
    missing = int((expected_effective & ~sponsors).sum())
    route_extra_on_expected = int((expected & sponsors).sum())
    recall = covered / max(1, effective_count)
    raw_recall = route_extra_on_expected / max(1, expected_count)
    return {
        "expected_pixels": expected_count,
        "expected_effective_pixels": effective_count,
        "covered_pixels": covered,
        "missing_pixels": missing,
        "expected_recall_after_number_priority": round(float(recall), 6),
        "expected_raw_sponsor_recall": round(float(raw_recall), 6),
        "expected_removed_by_numbers": int((expected & numbers).sum()),
    }


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str) -> None:
    if not records:
        return
    cols = 4
    cell_w = 260
    cell_h = 230
    rows = int(np.ceil(len(records) / cols))
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(records):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        thumb = Image.open(rec["comparison_overlay"]).convert("RGB").resize((190, 190), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x + 35, y + 25))
        status = "PASS" if rec["pass"] else "FAIL"
        draw.text((x + 7, y + 5), f"{status} rec={rec['expected_recall_after_number_priority']:.4f}", fill=(255, 230, 160))
        label = f"{rec.get('folder')} {rec.get('id')} {rec.get('source_kind')}"
        draw.text((x + 7, y + 200), label[:36], fill=(220, 220, 220))
        draw.text((x + 7, y + 214), str(rec.get("mask_source") or "")[:36], fill=(190, 210, 255))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def _write_comparison_overlay(
    rec: dict[str, Any],
    expected: np.ndarray,
    sponsors: np.ndarray,
    numbers: np.ndarray,
    out_dir: Path,
) -> str:
    source = _source_image(rec["source"], (expected.shape[1], expected.shape[0])).convert("RGBA")
    expected_effective = expected & ~numbers
    covered = expected_effective & sponsors
    missing = expected_effective & ~sponsors
    extras = sponsors & ~expected

    overlay = source.copy()
    layers = (
        (extras, (50, 120, 255, 75)),
        (covered, (255, 255, 255, 190)),
        (missing, (255, 30, 80, 210)),
        (numbers & expected, (255, 220, 30, 185)),
    )
    for mask, color in layers:
        tint = Image.new("RGBA", overlay.size, color)
        overlay.alpha_composite(Image.composite(tint, Image.new("RGBA", overlay.size, (0, 0, 0, 0)), Image.fromarray(mask.astype(np.uint8) * 255, "L")))

    sample = out_dir / f"{rec['fixture_index']:03d}_{_safe_name(str(rec.get('folder')) + '_' + str(rec.get('id')) + '_' + str(rec.get('source_kind')))}.png"
    sample.parent.mkdir(parents=True, exist_ok=True)
    overlay.convert("RGB").save(sample)
    return str(sample.resolve())


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:96] or "sample"


def _route_client(disable_gpu: bool):
    if disable_gpu:
        os.environ["SPB_SMART_TGA_GPU"] = "0"
    os.environ.setdefault("SPB_SMART_TGA_COMPANION_DECALS", "1")
    os.environ.setdefault("SPB_SMART_TGA_COMPANION_DECAL_RGB_FALLBACK", "1")
    os.environ.setdefault("SPB_SMART_TGA_COMPANION_DECAL_MIN", "0.00025")
    import server

    server.app.config["TESTING"] = True
    return server.app.test_client()


def _post_auto_layers(client: Any, rec: dict[str, Any], preview_size: int) -> tuple[dict[str, Any], float, int]:
    payload = {
        "paint_file": rec["source"],
        "paint_file_hint": rec["source"],
        "car_hint_path": rec["source"],
        "preview_size": preview_size,
        "brand_graphics_merge": "sponsors",
    }
    start = time.perf_counter()
    response = client.post("/api/auto-layers", json=payload, headers={"X-Shokker-Internal": "1"})
    elapsed = time.perf_counter() - start
    try:
        body = response.get_json() or {}
    except Exception:
        body = {"success": False, "error": response.get_data(as_text=True)[:500]}
    return body, elapsed, int(response.status_code)


def check_fixtures(args: argparse.Namespace) -> dict[str, Any]:
    manifest = _read_manifest(args.manifest)
    if args.mask_source:
        manifest = [rec for rec in manifest if str(rec.get("mask_source")) == args.mask_source]
    if args.only_id:
        wanted = {str(v).strip() for v in args.only_id if str(v).strip()}
        manifest = [rec for rec in manifest if str(rec.get("id")) in wanted]
    if args.limit:
        manifest = manifest[: args.limit]

    args.output.mkdir(parents=True, exist_ok=True)
    comparison_dir = args.output / "comparison_overlays"
    client = _route_client(disable_gpu=not args.allow_gpu)
    records: list[dict[str, Any]] = []

    for idx, base_rec in enumerate(manifest):
        rec = dict(base_rec)
        rec["fixture_index"] = idx
        body, elapsed, status_code = _post_auto_layers(client, rec, args.preview_size)
        rec.update({
            "http_status": status_code,
            "elapsed_sec": round(float(elapsed), 3),
            "route_success": bool(body.get("success")),
            "route_engine": body.get("engine"),
            "route_fractions": body.get("fractions"),
            "route_companion_decals": body.get("companion_decals"),
        })
        if not body.get("success"):
            rec.update({
                "pass": False,
                "failure_reason": f"route_error:{body.get('error')}",
                "expected_recall_after_number_priority": 0.0,
            })
            records.append(rec)
            continue

        layers = body.get("layers") or {}
        sponsors = _decode_data_url_mask(layers["sponsors"])
        numbers = _decode_data_url_mask(layers["numbers"], size=(sponsors.shape[1], sponsors.shape[0]))
        expected = _read_expected_mask(rec["expected_sponsor_decal_mask"], size=(sponsors.shape[1], sponsors.shape[0]))
        stats = _effective_stats(expected, sponsors, numbers)
        rec.update(stats)
        rec["comparison_overlay"] = _write_comparison_overlay(rec, expected, sponsors, numbers, comparison_dir)

        companion = body.get("companion_decals") or {}
        telemetry_ok = companion.get("status") == "applied"
        if rec.get("mask_source"):
            telemetry_ok = telemetry_ok and str(companion.get("mask_source") or "alpha") == str(rec.get("mask_source"))
        rec["telemetry_ok"] = bool(telemetry_ok)
        rec["pass"] = bool(
            telemetry_ok
            and stats["expected_effective_pixels"] > 0
            and stats["expected_recall_after_number_priority"] >= args.min_recall
        )
        if not rec["pass"]:
            rec["failure_reason"] = (
                "telemetry" if not telemetry_ok else
                f"recall<{args.min_recall}"
            )
        records.append(rec)

    passed = [rec for rec in records if rec.get("pass")]
    failed = [rec for rec in records if not rec.get("pass")]
    _contact_sheet(passed, args.output / "passes_contact_sheet.png", "Smart TGA decal route fixture passes")
    _contact_sheet(failed, args.output / "failures_contact_sheet.png", "Smart TGA decal route fixture failures")
    records_path = args.output / "route_fixture_records.json"
    records_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    recalls = [float(rec.get("expected_recall_after_number_priority", 0.0)) for rec in records]
    summary = {
        "manifest": str(args.manifest),
        "output": str(args.output.resolve()),
        "samples": len(records),
        "passed": len(passed),
        "failed": len(failed),
        "min_recall_required": args.min_recall,
        "min_recall_observed": round(float(min(recalls)) if recalls else 0.0, 6),
        "mean_recall_observed": round(float(np.mean(recalls)) if recalls else 0.0, 6),
        "route_engines": dict(Counter(str(rec.get("route_engine")) for rec in records)),
        "mask_sources": dict(Counter(str(rec.get("mask_source")) for rec in records)),
        "failure_reasons": dict(Counter(str(rec.get("failure_reason") or "pass") for rec in records)),
        "records": str(records_path.resolve()),
        "passes_contact_sheet": str((args.output / "passes_contact_sheet.png").resolve()) if passed else None,
        "failures_contact_sheet": str((args.output / "failures_contact_sheet.png").resolve()) if failed else None,
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only-id", action="append", default=[])
    parser.add_argument("--mask-source", choices=("alpha", "rgb_opaque_fallback"), default=None)
    parser.add_argument("--preview-size", type=int, default=1024)
    parser.add_argument("--min-recall", type=float, default=0.98)
    parser.add_argument("--allow-gpu", action="store_true", help="Use optional GPU bridge instead of the CPU fallback route.")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(check_fixtures(parse_args()), indent=2))


if __name__ == "__main__":
    main()
