"""Assemble owner-review evidence for the isolated Neon Oil-Slick reset slate.

SPB-105 / 2026-08-27: this reads the private candidate registry used by the
isolated official M7 harness. It never imports a candidate into the shipping
registry, never edits the live catalog, and never treats the light proxy as a
real mapped-car proof.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spb_neon_oil_slick_pilot_m7 import CANDIDATES  # noqa: E402


EVIDENCE = ROOT / "_neon_oil_slick_reset_work"
M7_REPORT = EVIDENCE / "official_isolated_m7.json"
SUMMARY = EVIDENCE / "slate_review.json"
COLS = 5
TILE = 384


def _rgb(path: Path) -> np.ndarray:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def _write_rgb(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(np.clip(image, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    if not cv2.imwrite(str(path), bgr, [cv2.IMWRITE_PNG_COMPRESSION, 3]):
        raise OSError(path)


def _label(image: np.ndarray, text: str, bar: int = 44) -> np.ndarray:
    out = np.asarray(image, np.uint8).copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], bar), (5, 7, 13), -1)
    cv2.putText(out, text, (11, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.70,
                (255, 235, 130), 2, cv2.LINE_AA)
    return out


def _manifest_name(folder: Path, slug: str) -> tuple[str, str]:
    manifest_path = folder / "manifest.json"
    audit_path = folder / "audit.json"
    manifest: dict[str, Any] = {}
    audit: dict[str, Any] = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if audit_path.is_file():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    nested = audit.get("manifest") if isinstance(audit.get("manifest"), dict) else {}
    finish_id = str(
        manifest.get("finish_id") or audit.get("finish_id") or nested.get("finish_id") or slug
    )
    display_name = str(
        manifest.get("display_name") or audit.get("display_name")
        or nested.get("display_name") or slug.replace("_", " ").title()
    )
    return finish_id, display_name


def _mechanical_green(audit: dict[str, Any]) -> bool | None:
    direct_keys = (
        "all_mechanical_checks_green",
        "mechanical_gates_pass",
        "all_mechanical_gates_pass",
        "all_checks_pass",
    )
    for key in direct_keys:
        if isinstance(audit.get(key), bool):
            return bool(audit[key])
    for key in ("checks", "mechanical_gates"):
        values = audit.get(key)
        if isinstance(values, dict):
            bools = [value for value in values.values() if isinstance(value, bool)]
            if bools:
                return all(bools)
    # Four-run agents use deterministic_4_of_4 plus explicit geometry/material.
    if audit.get("deterministic_4_of_4") is True:
        return True
    return None


def _signature(image: np.ndarray) -> np.ndarray:
    small = cv2.resize(np.asarray(image, np.float32) / 255.0, (160, 160), interpolation=cv2.INTER_AREA)
    lum = small[..., 0] * 0.2126 + small[..., 1] * 0.7152 + small[..., 2] * 0.0722
    local = lum - cv2.GaussianBlur(lum, (0, 0), 4.0)
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    return np.concatenate((local.ravel(), np.hypot(gx, gy).ravel()))


def _corr(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, np.float64)
    b = np.asarray(right, np.float64)
    if a.std() < 1e-9 or b.std() < 1e-9:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def _grid(tiles: list[np.ndarray], cols: int = COLS) -> np.ndarray:
    if not tiles:
        raise ValueError("no tiles")
    blank = np.zeros_like(tiles[0])
    padded = list(tiles) + [blank] * ((-len(tiles)) % cols)
    rows = [np.concatenate(padded[i:i + cols], axis=1) for i in range(0, len(padded), cols)]
    return np.concatenate(rows, axis=0)


def _paged_rows(rows: list[np.ndarray], stem: str, rows_per_page: int = 5) -> list[str]:
    outputs: list[str] = []
    for page, start in enumerate(range(0, len(rows), rows_per_page), 1):
        name = f"{stem}_page_{page:02d}.png"
        _write_rgb(EVIDENCE / name, np.concatenate(rows[start:start + rows_per_page], axis=0))
        outputs.append(name)
    return outputs


def run() -> dict[str, Any]:
    m7_payload = json.loads(M7_REPORT.read_text(encoding="utf-8")) if M7_REPORT.is_file() else {}
    five_audit_path = EVIDENCE / "five_pilot_audit.json"
    five_audit_payload = (
        json.loads(five_audit_path.read_text(encoding="utf-8"))
        if five_audit_path.is_file() else {}
    )
    five_audit_by_slug = {
        str(row.get("slug")): row
        for row in five_audit_payload.get("pilots", [])
        if isinstance(row, dict) and row.get("slug")
    }
    m7_by_slug = {
        str(row.get("slug")): row
        for row in m7_payload.get("byFinish", {}).values()
        if isinstance(row, dict) and row.get("slug")
    }

    records: list[dict[str, Any]] = []
    signatures: dict[str, np.ndarray] = {}
    paint_tiles: list[np.ndarray] = []
    picker_tiles: list[np.ndarray] = []
    material_rows: list[np.ndarray] = []
    light_rows: list[np.ndarray] = []

    for candidate in CANDIDATES:
        slug = str(candidate["slug"])
        folder = EVIDENCE / slug
        audit_path = folder / "audit.json"
        audit = (
            json.loads(audit_path.read_text(encoding="utf-8"))
            if audit_path.is_file() else five_audit_by_slug.get(slug, {})
        )
        finish_id, display_name = _manifest_name(folder, slug)
        required = [
            folder / "paint_2048.png",
            folder / "paint_128.png",
            folder / "material_contact.png",
            folder / "light_sweep_contact.png",
        ]
        missing = [str(path.relative_to(ROOT)).replace("\\", "/") for path in required if not path.is_file()]
        if not audit:
            missing.append(str(audit_path.relative_to(ROOT)).replace("\\", "/"))
        workbook = m7_by_slug.get(slug, {})
        record = {
            "slug": slug,
            "finish_id": finish_id,
            "display_name": display_name,
            "module": candidate["module"],
            "key": candidate["key"],
            "evidence_complete": not missing,
            "missing": missing,
            "mechanical_green": _mechanical_green(audit),
            "m7": workbook.get("composite"),
            "m7_pass_85": bool(workbook.get("pass_85")),
            "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        }
        records.append(record)
        if missing:
            continue

        paint = _rgb(folder / "paint_2048.png")
        picker = _rgb(folder / "paint_128.png")
        signatures[slug] = _signature(paint)
        paint_tiles.append(_label(cv2.resize(paint, (TILE, TILE), interpolation=cv2.INTER_AREA), display_name))
        picker_tiles.append(_label(cv2.resize(picker, (TILE, TILE), interpolation=cv2.INTER_NEAREST), f"{display_name} - 128px"))
        material = cv2.resize(_rgb(folder / "material_contact.png"), (1536, 384), interpolation=cv2.INTER_AREA)
        material_rows.append(_label(material, display_name))
        sweep = cv2.resize(_rgb(folder / "light_sweep_contact.png"), (1536, 512), interpolation=cv2.INTER_AREA)
        light_rows.append(_label(sweep, display_name))

    outputs: dict[str, Any] = {}
    if paint_tiles:
        outputs["paint_contact"] = "slate_paint_contact.png"
        outputs["picker_contact"] = "slate_picker_128_contact.png"
        _write_rgb(EVIDENCE / outputs["paint_contact"], _grid(paint_tiles))
        _write_rgb(EVIDENCE / outputs["picker_contact"], _grid(picker_tiles))
        outputs["material_pages"] = _paged_rows(material_rows, "slate_material")
        outputs["light_pages"] = _paged_rows(light_rows, "slate_light_sweep")

    pairwise: dict[str, float] = {}
    slugs = list(signatures)
    for index, left in enumerate(slugs):
        for right in slugs[index + 1:]:
            pairwise[f"{left}__{right}"] = round(_corr(signatures[left], signatures[right]), 6)
    ids = [record["finish_id"] for record in records]
    payload = {
        "schema": "spb-neon-oil-slick-slate-review/1",
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "candidate_count": len(records),
        "unique_finish_ids": len(ids) == len(set(ids)),
        "all_evidence_complete": all(record["evidence_complete"] for record in records),
        "all_mechanical_green": all(record["mechanical_green"] is True for record in records),
        "all_official_isolated_m7_ge_85": bool(records) and all(record["m7_pass_85"] for record in records),
        "max_abs_pairwise_structural_correlation": (
            max((abs(value) for value in pairwise.values()), default=0.0)
        ),
        "records": records,
        "pairwise_structural_correlation": pairwise,
        "outputs": outputs,
        "shipping_state_changed": False,
        "mapped_car_proof": "PENDING; supplied light sweeps are deterministic three-position proxies only",
    }
    SUMMARY.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = run()
    print(json.dumps({
        "candidate_count": payload["candidate_count"],
        "unique_finish_ids": payload["unique_finish_ids"],
        "all_evidence_complete": payload["all_evidence_complete"],
        "all_mechanical_green": payload["all_mechanical_green"],
        "all_official_isolated_m7_ge_85": payload["all_official_isolated_m7_ge_85"],
        "max_abs_pairwise_structural_correlation": payload["max_abs_pairwise_structural_correlation"],
        "outputs": payload["outputs"],
    }, indent=2))
    return 0 if (
        payload["unique_finish_ids"]
        and payload["all_evidence_complete"]
        and payload["all_mechanical_green"]
        and payload["all_official_isolated_m7_ge_85"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
