"""Pack Smart TGA selected-threshold misses for active learning.

This is offline Smart TGA tooling. It consumes
``holdout_selected_threshold_records.json`` files emitted by
``smart_tga_multiclass_proposal_eval.py`` and writes a deduped taxonomy-like
miss pack plus a contact sheet. The output can be reused as evaluator taxonomy
input in later diagnostics; it is not runtime Auto-build logic.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_selected_miss_pack")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:110] or "unknown"


def _record_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(record.get("source") or record.get("source_path") or ""),
        str(record.get("analyzed_box") or record.get("box") or ""),
        str(record.get("subtype") or ""),
        str(record.get("file") or ""),
    )


def _copy_crop(record: dict[str, Any], out_dir: Path, index: int) -> dict[str, Any]:
    item = dict(record)
    src = Path(str(record.get("file") or record.get("crop_file") or ""))
    if src.is_file():
        folder = _safe_name(str(record.get("group") or record.get("folder") or src.parent.name))
        dst = out_dir / "crops" / f"miss_{index:04d}_{folder}.png"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        item["file"] = str(dst.resolve())
        item["crop_file"] = str(dst.resolve())
    return item


def _contact_sheet(rows: list[dict[str, Any]], out_path: Path, max_items: int) -> None:
    rows = rows[:max_items]
    if not rows:
        return
    cols = 5
    cell_w = 240
    cell_h = 220
    sheet = Image.new("RGB", (cols * cell_w, int(np.ceil(len(rows) / cols)) * cell_h), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    for idx, record in enumerate(rows):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        src = Path(str(record.get("file") or ""))
        if src.is_file():
            img = Image.open(src).convert("RGB")
            img.thumbnail((180, 145), Image.Resampling.LANCZOS)
            sheet.paste(img, (x + 28, y + 40))
        title = f"{idx:02d} {record.get('truth', '?')} -> {record.get('pred', '?')}"
        draw.text((x + 6, y + 5), title[:36], fill=(255, 225, 120))
        draw.text((x + 6, y + 20), str(record.get("subtype") or "")[:36], fill=(170, 220, 255))
        score = record.get("frontier_score")
        threshold = record.get("frontier_threshold")
        if score is not None or threshold is not None:
            draw.text((x + 6, y + 184), f"score {score} / thr {threshold}"[:38], fill=(210, 210, 210))
        draw.text((x + 6, y + 200), str(record.get("group") or "")[:38], fill=(220, 220, 220))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def build_pack(args: argparse.Namespace) -> dict[str, Any]:
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    seen: set[tuple[str, str, str, str]] = set()
    rows: list[dict[str, Any]] = []
    inputs: list[str] = []
    for path in args.records:
        inputs.append(str(path))
        records = _read_json(path)
        for record in records:
            if not args.include_correct and str(record.get("pred")) == str(record.get("truth")):
                continue
            key = _record_key(record)
            if key in seen:
                continue
            seen.add(key)
            rows.append(_copy_crop(record, out, len(rows)))
    rows.sort(key=lambda record: (str(record.get("subtype") or ""), str(record.get("group") or ""), str(record.get("file") or "")))
    pack_path = out / "selected_misses.json"
    pack_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    _contact_sheet(rows, out / "selected_misses.png", args.sheet_items)
    summary = {
        "inputs": inputs,
        "output": str(out.resolve()),
        "records": len(rows),
        "by_subtype": dict(Counter(str(record.get("subtype") or "unknown") for record in rows)),
        "by_group": dict(Counter(str(record.get("group") or "unknown") for record in rows)),
        "pack": str(pack_path.resolve()),
        "contact_sheet": str((out / "selected_misses.png").resolve()) if rows else None,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--include-correct", action="store_true")
    parser.add_argument("--sheet-items", type=int, default=120)
    args = parser.parse_args()
    print(json.dumps(build_pack(args), indent=2))


if __name__ == "__main__":
    main()
