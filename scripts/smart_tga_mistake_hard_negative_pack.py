"""Build Smart TGA hard-negative packs from evaluator mistake records.

This is offline Smart TGA active-learning tooling. It reads one or more
`holdout_records.json` / selected-threshold record files from the proposal
evaluator, keeps non-number crops that were predicted as numbers, and exports a
normal hard-negative/taxonomy manifest plus a contact sheet. It does not affect
Auto-build Layers runtime.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:110] or "unknown"


def _is_number_prediction(value: Any) -> bool:
    return str(value or "").lower() == "number"


def _crop_file_for(record: dict[str, Any]) -> Path | None:
    for key in ("file", "crop_file", "record_file"):
        raw = record.get(key)
        if not raw:
            continue
        path = _repo_path(str(raw))
        if path.is_file():
            return path
    return None


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str, max_items: int) -> None:
    rows = records[:max_items]
    if not rows:
        return
    cols = 4
    cell_w = 270
    cell_h = 238
    sheet = Image.new("RGB", (cols * cell_w, ((len(rows) + cols - 1) // cols) * cell_h), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    draw.text((8, 6), title, fill=(255, 255, 255))
    for idx, rec in enumerate(rows):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        src = Path(str(rec.get("file") or ""))
        if src.is_file():
            img = Image.open(src).convert("RGB")
            img.thumbnail((210, 150), Image.Resampling.LANCZOS)
            sheet.paste(img, (x + 30, y + 44))
        draw.text((x + 6, y + 22), f"{idx:02d} {rec.get('subtype', '')}"[:42], fill=(255, 230, 130))
        draw.text((x + 6, y + 184), str(rec.get("group") or "")[:42], fill=(190, 220, 255))
        draw.text((x + 6, y + 204), str(rec.get("source_origin") or "")[:42], fill=(220, 220, 220))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def build_pack(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = _repo_path(args.output)
    if out_dir.exists() and args.clean:
        shutil.rmtree(out_dir)
    crop_dir = out_dir / "hard_negative"
    crop_dir.mkdir(parents=True, exist_ok=True)

    keep_subtypes = {s.lower() for s in args.keep_subtype}
    seen: set[tuple[str, tuple[int, ...], str]] = set()
    records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for record_path_arg in args.records:
        record_path = _repo_path(record_path_arg)
        source_rows = _read_json(record_path)
        if not isinstance(source_rows, list):
            raise ValueError(f"{record_path} did not contain a JSON list")
        for idx, row in enumerate(source_rows):
            truth = str(row.get("truth") or "").lower()
            pred = row.get("pred", row.get("predicted"))
            subtype = str(row.get("subtype") or "reviewed_hard_negative")
            if truth != "non_number" or not _is_number_prediction(pred):
                continue
            if keep_subtypes and subtype.lower() not in keep_subtypes:
                continue
            crop_src = _crop_file_for(row)
            if crop_src is None:
                skipped.append({"records": str(record_path), "index": idx, "reason": "missing_crop"})
                continue
            box = row.get("analyzed_box") or row.get("box") or []
            box_key = tuple(int(v) for v in box) if isinstance(box, list) else tuple()
            source = str(row.get("source_path") or row.get("source") or "")
            dedupe_key = (source, box_key, subtype)
            if dedupe_key in seen:
                skipped.append({"records": str(record_path), "index": idx, "reason": "duplicate"})
                continue
            seen.add(dedupe_key)
            group = str(row.get("group") or Path(source).parent.name + "/" + Path(source).stem)
            out_file = crop_dir / f"hard_negative_{len(records):04d}_{_safe_name(subtype)}_{_safe_name(group)}.png"
            shutil.copyfile(crop_src, out_file)
            features = row.get("features") if isinstance(row.get("features"), dict) else {}
            rec = {
                "source_kind": "mistake_hard_negative",
                "label": "hard_negative",
                "truth": "non_number",
                "target_layer": "sponsors",
                "subtype": subtype,
                "source": source,
                "source_path": source,
                "group": group,
                "file": str(out_file.resolve()),
                "crop_file": str(out_file.resolve()),
                "box": box if isinstance(box, list) else None,
                "analyzed_box": box if isinstance(box, list) else None,
                "features": features,
                "score": row.get("score"),
                "frontier_score": row.get("frontier_score"),
                "source_origin": str(record_path),
                "source_index": idx,
            }
            records.append(rec)

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "hard_negative_manifest.json"
    taxonomy_path = out_dir / "taxonomy_records.json"
    manifest_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    taxonomy_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "records": len(records),
                "record_inputs": [str(_repo_path(p)) for p in args.records],
                "hard_negative_manifest": str(manifest_path.resolve()),
                "taxonomy_records": str(taxonomy_path.resolve()),
                "skipped": skipped,
                "note": "Offline Smart TGA active-learning hard negatives from evaluator false positives.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _contact_sheet(records, out_dir / "hard_negative_mistakes.png", "Smart TGA false-number hard negatives", args.sheet_items)
    return {"records": len(records), "output": str(out_dir.resolve()), "skipped": len(skipped)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", action="append", required=True, help="Evaluator records JSON to mine.")
    parser.add_argument("--output", required=True, help="Output pack directory.")
    parser.add_argument("--keep-subtype", action="append", default=[], help="Optional subtype allow-list.")
    parser.add_argument("--sheet-items", type=int, default=80)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build_pack(args), indent=2))


if __name__ == "__main__":
    main()
