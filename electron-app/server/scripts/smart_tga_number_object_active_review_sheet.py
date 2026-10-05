"""Build context/isolated-object review sheets from a frozen active-learning pool."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

try:
    from engine.spec_sculpt.number_context_component_proposals import component_proposal_candidates
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_component_proposals import component_proposal_candidates  # type: ignore


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _tile(rgb, support, bbox, size=210):
    x, y, width, height = map(int, bbox)
    margin = max(12, int(round(max(width, height) * 0.28)))
    x0, y0 = max(0, x - margin), max(0, y - margin)
    x1, y1 = min(rgb.shape[1], x + width + margin), min(rgb.shape[0], y + height + margin)
    context = Image.fromarray(rgb[y0:y1, x0:x1]).convert("RGB")
    context.thumbnail((size, size))
    isolated = np.full_like(rgb[y0:y1, x0:x1], 127)
    crop_support = np.zeros((y1 - y0, x1 - x0), bool)
    local = np.asarray(support, bool)
    target = crop_support[y - y0:y - y0 + local.shape[0], x - x0:x - x0 + local.shape[1]]
    target[:] = local[:target.shape[0], :target.shape[1]]
    isolated[crop_support] = rgb[y0:y1, x0:x1][crop_support]
    isolated = Image.fromarray(isolated).convert("RGB")
    isolated.thumbnail((size, size))
    return context, isolated


def build(active_pool: Path, inspection_root: Path, output: Path, scope="selected"):
    pool = _read(active_pool)
    selected = {item["paint_label"] for item in pool["selected_paints"]}
    queue = []
    for paint in pool["ranking"]:
        is_selected = paint["paint_label"] in selected
        if (scope == "selected" and not is_selected) or (scope == "unselected" and is_selected):
            continue
        slug = paint["paint_label"].replace("/", "_").replace(" ", "_").replace(".tga", "")
        folder = inspection_root / slug
        rgb = np.asarray(Image.open(folder / "source_1024.png").convert("RGB"))
        masks = {path.stem: np.asarray(Image.open(path).convert("L")) > 0 for path in (folder / "masks").glob("*.png")}
        proposals = component_proposal_candidates(rgb.shape[:2], masks, _read(folder / "component_records.json"), min_pixels=400)
        proposal_map = {
            (str(item["provenance"]["source_layer"]), int(item["provenance"]["component_index"])): item
            for item in proposals
        }
        ranked = sorted(
            paint["objects"],
            key=lambda item: (item["foundation_probability"] >= pool["frozen_threshold"], item["delta"], item["foundation_probability"]),
            reverse=True,
        )
        chosen = [
            item for item in ranked
            if item["foundation_probability"] >= pool["frozen_threshold"]
            or item["delta"] > 0.45
            or item["uncertainty"] < 0.08
        ][:14]
        for item in chosen:
            proposal = proposal_map[(item["source_layer"], int(item["component_index"]))]
            context, isolated = _tile(rgb, proposal["raw_support"], item["bbox"])
            queue.append({"paint_label": paint["paint_label"], "record": item, "context": context, "isolated": isolated})

    tile = 210
    caption = 54
    columns = 4
    rows = (len(queue) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * tile * 2, rows * (tile + caption)), (15, 15, 20))
    draw = ImageDraw.Draw(canvas)
    records = []
    for index, item in enumerate(queue):
        column, row = index % columns, index // columns
        x, y = column * tile * 2, row * (tile + caption)
        context, isolated = item["context"], item["isolated"]
        canvas.paste(context, (x + (tile - context.width) // 2, y + (tile - context.height) // 2))
        canvas.paste(isolated, (x + tile + (tile - isolated.width) // 2, y + (tile - isolated.height) // 2))
        record = item["record"]
        paint = item["paint_label"].split("/")[-1].replace("car_num_", "").replace(".tga", "")
        text = f"{paint} {record['source_layer']}#{record['component_index']}  old {record['cycle710_probability']:.2f}  new {record['foundation_probability']:.2f}  d {record['delta']:+.2f}"
        draw.rectangle((x, y + tile, x + tile * 2, y + tile + caption), fill=(8, 8, 12))
        draw.text((x + 5, y + tile + 7), text, fill=(238, 238, 242))
        records.append({key: value for key, value in record.items() if key not in {"uncertainty"}} | {"paint_label": item["paint_label"]})
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    output.with_suffix(".json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--active-pool", type=Path, required=True)
    parser.add_argument("--inspection-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scope", choices=("selected", "unselected"), default="selected")
    args = parser.parse_args()
    records = build(args.active_pool, args.inspection_root, args.output, args.scope)
    print(json.dumps({"review_records": len(records), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
