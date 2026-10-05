"""Render every shadow physical-decal group for manual corpus review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--columns", type=int, default=4)
    args = parser.parse_args()

    records = json.loads(Path(args.inspection).read_text(encoding="utf-8"))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    report = {"schema": "smart-tga-physical-group-audit-v1", "paints": []}
    font = _font(14)
    small = _font(11)
    for record in records:
        telemetry = (
            record.get("route_adjudicator_shadow", {})
            .get("candidate_evidence", {})
            .get("decal_instances", {})
            .get("physical_groups", {})
        )
        groups = list(telemetry.get("samples") or ())
        source = Image.open(record["source_1024"]).convert("RGB")
        tiles = []
        for group in groups:
            x, y, width, height = [int(value) for value in group["bbox"]]
            margin = max(8, int(round(max(width, height) * 0.12)))
            x0, y0 = max(0, x - margin), max(0, y - margin)
            x1, y1 = min(source.width, x + width + margin), min(source.height, y + height + margin)
            crop = source.crop((x0, y0, x1, y1))
            draw = ImageDraw.Draw(crop)
            draw.rectangle((x - x0, y - y0, x + width - x0 - 1, y + height - y0 - 1), outline=(255, 0, 180), width=3)
            crop.thumbnail((250, 190), Image.Resampling.LANCZOS)
            tile = Image.new("RGB", (270, 245), (18, 18, 18))
            tile.paste(crop, ((270 - crop.width) // 2, 42))
            label = f"{group['group_id']}  n={group['member_count']}  area={group['area']}"
            ImageDraw.Draw(tile).text((8, 7), label, fill=(255, 235, 80), font=small)
            ImageDraw.Draw(tile).text((8, 24), str(group.get("edge_reasons") or ()), fill=(210, 210, 210), font=small)
            tiles.append(tile)
        columns = max(1, int(args.columns))
        rows = max(1, (len(tiles) + columns - 1) // columns)
        sheet = Image.new("RGB", (columns * 270, 34 + rows * 245), (10, 10, 10))
        ImageDraw.Draw(sheet).text((8, 8), record["paint_label"], fill=(255, 255, 255), font=font)
        for index, tile in enumerate(tiles):
            sheet.paste(tile, ((index % columns) * 270, 34 + (index // columns) * 245))
        safe = record["paint_label"].replace("/", "_").replace("\\", "_").replace(" ", "_")
        sheet_path = output / f"{safe}_physical_groups.png"
        sheet.save(sheet_path)
        report["paints"].append({
            "paint_label": record["paint_label"],
            "group_count": len(groups),
            "sheet": str(sheet_path.resolve()),
            "groups": groups,
        })
    report["group_count"] = sum(item["group_count"] for item in report["paints"])
    report["casts_votes"] = False
    report["ownership_authority"] = False
    (output / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"paints": len(report["paints"]), "groups": report["group_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
