"""Render exact persisted Smart TGA candidate masks on a checker background."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def _decode_candidate(npz_path: str, index: int) -> tuple[np.ndarray, list[int]]:
    payload = np.load(npz_path, allow_pickle=False)
    offset = int(payload["offsets"][index])
    length = int(payload["lengths"][index])
    height, width = map(int, payload["shapes"][index])
    packed = payload["packed"][offset:offset + length]
    support = np.unpackbits(packed)[:height * width].reshape(height, width).astype(bool)
    return support, payload["bboxes"][index].astype(int).tolist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=24)
    parser.add_argument(
        "--all-candidates", action="store_true",
        help="Render every immutable bank candidate when the review file is empty.",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    review = json.loads(args.labels.read_text(encoding="utf-8"))
    records = {row["paint"]: row for row in bank["records"]}
    if args.all_candidates and not review.get("labels") and not review.get("items"):
        review["labels"] = []
        for paint, record in records.items():
            for candidate_index, candidate in enumerate(record["candidates"]):
                review["labels"].append({
                    "review_code": f"C{candidate_index:03d}",
                    "paint": paint,
                    "candidate_index": candidate_index,
                    "proposal_id": candidate["proposal_id"],
                    "bbox": candidate["bbox"],
                    "suggested_semantics": ["unscored"],
                    "prediction_for_review_only": "unscored",
                    "ownership_authority": False,
                })
        review["truth_free_all_candidate_scaffold"] = True
    if "labels" not in review and "items" in review:
        # Frozen holdout inference intentionally emits a truth-free queue. Turn
        # it into the same visual scaffold without inventing semantic labels.
        review["labels"] = []
        for offset, item in enumerate(review["items"]):
            candidate = records[item["paint"]]["candidates"][
                int(item["candidate_index"])
            ]
            review["labels"].append({
                "review_code": f"Q{offset:03d}",
                "paint": item["paint"],
                "candidate_index": int(item["candidate_index"]),
                "proposal_id": item["proposal_id"],
                "bbox": candidate["bbox"],
                "suggested_semantics": [str(item.get("nearest_boundary", "unscored"))],
                "prediction_for_review_only": item.get("nearest_boundary"),
                "ownership_authority": False,
            })
    images = {
        paint: np.asarray(Image.open(row["source_1024"]).convert("RGB"))
        for paint, row in records.items()
    }
    width, height, columns = 300, 220, 4
    pages = []
    for page_index, start in enumerate(range(0, len(review["labels"]), args.page_size)):
        subset = review["labels"][start:start + args.page_size]
        canvas = Image.new(
            "RGB", (width * columns, height * math.ceil(len(subset) / columns)),
            (18, 20, 24),
        )
        draw = ImageDraw.Draw(canvas)
        for offset, row in enumerate(subset):
            record = records[row["paint"]]
            support, bbox = _decode_candidate(record["exact_candidate_bank"], row["candidate_index"])
            x, y, box_w, box_h = bbox
            source_crop = images[row["paint"]][y:y + box_h, x:x + box_w]
            yy, xx = np.indices((box_h, box_w))
            checker = np.where(((xx // 8 + yy // 8) % 2)[..., None], 72, 112).astype(np.uint8)
            checker = np.repeat(checker, 3, axis=2)
            crop = checker
            crop[support] = source_crop[support]
            masked = Image.fromarray(crop)
            masked.thumbnail((width - 12, height - 67), Image.Resampling.NEAREST)
            left = (offset % columns) * width + 6
            top = (offset // columns) * height
            canvas.paste(masked, (
                left + (width - 12 - masked.width) // 2,
                top + 61 + (height - 67 - masked.height) // 2,
            ))
            short_paint = row["paint"].replace("dirtlatemodel ", "DLM")
            draw.text(
                (left, top + 5),
                f"{row['review_code']} {short_paint}\nidx={row['candidate_index']} {row['bbox']}\nsuggest={'+'.join(row['suggested_semantics'])}",
                fill=(236, 239, 245),
            )
        path = args.output / f"direct_review_checker_{page_index:02d}.png"
        canvas.save(path)
        pages.append(str(path.resolve()))
    review["checker_review_pages"] = pages
    review["review_background"] = "8px gray checker; source pixels shown exactly on support"
    args.labels.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pages": len(pages), "labels": len(review["labels"])}, indent=2))


if __name__ == "__main__":
    main()
