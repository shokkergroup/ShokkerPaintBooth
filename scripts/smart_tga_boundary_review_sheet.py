"""Render model-selected exact candidates with local context for active review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

try:
    from scripts.smart_tga_exact_candidate_utils import decode_support
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_exact_candidate_utils import decode_support  # type: ignore


REVIEW_STATES = (
    "complete_number_copy", "number_fragment", "sponsor_glyph",
    "paint_or_template", "ambiguous_crop",
)


def _fit(image: np.ndarray, width: int, height: int) -> np.ndarray:
    scale = min(width / image.shape[1], height / image.shape[0])
    target = cv2.resize(
        image,
        (max(1, int(round(image.shape[1] * scale))), max(1, int(round(image.shape[0] * scale)))),
        interpolation=cv2.INTER_NEAREST if scale > 1 else cv2.INTER_AREA,
    )
    canvas = np.full((height, width, 3), 24, dtype=np.uint8)
    y = (height - target.shape[0]) // 2
    x = (width - target.shape[1]) // 2
    canvas[y:y + target.shape[0], x:x + target.shape[1]] = target
    return canvas


def _checker(height: int, width: int) -> np.ndarray:
    yy, xx = np.indices((height, width))
    value = np.where((xx // 8 + yy // 8) % 2, 70, 112).astype(np.uint8)
    return np.repeat(value[:, :, None], 3, axis=2)


def _panel(source: np.ndarray, exact, index: int, metadata: dict, code: str) -> np.ndarray:
    x, y, width, height = map(int, exact["bboxes"][index])
    support = decode_support(exact, index)
    crop = source[y:y + height, x:x + width]
    exact_crop = _checker(height, width)
    exact_crop[support] = crop[support]
    margin = max(width, height, 48)
    x0, y0 = max(0, x - margin), max(0, y - margin)
    x1 = min(source.shape[1], x + width + margin)
    y1 = min(source.shape[0], y + height + margin)
    context = source[y0:y1, x0:x1].copy()
    cv2.rectangle(
        context, (x - x0, y - y0), (x + width - x0 - 1, y + height - y0 - 1),
        (0, 220, 255), 2,
    )
    panel = np.full((360, 520, 3), 14, dtype=np.uint8)
    panel[72:318, 8:252] = _fit(exact_crop, 244, 246)
    panel[72:318, 268:512] = _fit(context, 244, 246)
    short_paint = metadata["paint"].replace("dirtlatemodel ", "DLM")
    lines = (
        f"{code} {short_paint}",
        f"idx={index} block={metadata['block']}",
        f"score={metadata['ordinal_score']:.6f} certainty={metadata['certainty_probability']:.6f}",
        f"near={metadata['nearest_boundary']}",
    )
    for offset, text in enumerate(lines):
        cv2.putText(
            panel, text, (10, 18 + 16 * offset), cv2.FONT_HERSHEY_SIMPLEX,
            0.42, (230, 230, 230), 1, cv2.LINE_AA,
        )
    cv2.putText(panel, "EXACT MASK", (80, 342), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 220, 255), 1, cv2.LINE_AA)
    cv2.putText(panel, "LOCAL CONTEXT", (330, 342), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 220, 255), 1, cv2.LINE_AA)
    return panel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--cycle", type=int, default=731)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    queue = json.loads(args.queue.read_text(encoding="utf-8"))["items"][:args.count]
    records = {str(row["paint"]): row for row in bank["records"]}
    source_cache = {}
    exact_cache = {}
    rows, panels = [], []
    try:
        for offset, item in enumerate(queue):
            paint = str(item["paint"])
            record = records[paint]
            if paint not in source_cache:
                source = cv2.imread(record["source_1024"], cv2.IMREAD_COLOR)
                if source is None:
                    raise FileNotFoundError(record["source_1024"])
                source_cache[paint] = source
                exact_cache[paint] = np.load(record["exact_candidate_bank"], allow_pickle=False)
            exact = exact_cache[paint]
            index = int(item["candidate_index"])
            proposal_id = str(exact["proposal_ids"][index])
            if proposal_id != item["proposal_id"]:
                raise RuntimeError(f"queue/bank candidate drift: {paint} #{index}")
            code = f"B{offset:03d}"
            panels.append(_panel(source_cache[paint], exact, index, item, code))
            rows.append({
                "review_code": code, "paint": paint, "candidate_index": index,
                "proposal_id": proposal_id,
                "bbox_for_review_trace_only": list(map(int, exact["bboxes"][index])),
                "block_for_review_trace_only": str(item["block"]),
                "ordinal_score_for_selection_only": float(item["ordinal_score"]),
                "certainty_for_selection_only": float(item["certainty_probability"]),
                "nearest_boundary": str(item["nearest_boundary"]),
                "allowed_states": list(REVIEW_STATES), "direct_state": None,
                "review_status": "pending_direct_visual_review",
                "ownership_authority": False,
            })
    finally:
        for exact in exact_cache.values():
            exact.close()
    columns = 2
    rows_count = int(np.ceil(len(panels) / columns))
    sheet = np.full((rows_count * 360, columns * 520, 3), 8, dtype=np.uint8)
    for offset, panel in enumerate(panels):
        row, column = divmod(offset, columns)
        sheet[row * 360:(row + 1) * 360, column * 520:(column + 1) * 520] = panel
    sheet_path = args.output / "boundary_review_sheet.png"
    if not cv2.imwrite(str(sheet_path), sheet):
        raise RuntimeError(f"failed to write {sheet_path}")
    payload = {
        "schema": "smart-tga-boundary-active-review-v1", "cycle": args.cycle,
        "selection_source": str(args.queue), "review_sheet": str(sheet_path),
        "review_states": list(REVIEW_STATES), "items": rows,
        "safety": {"selection_only": True, "ownership_authority": False, "bbox_model_feature": False},
    }
    (args.output / "boundary_review_queue.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({"items": len(rows), "sheet": str(sheet_path)}, indent=2))


if __name__ == "__main__":
    main()
