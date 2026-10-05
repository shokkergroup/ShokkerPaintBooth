"""Build a compact feature bank from reviewed Smart TGA component oracles.

This is offline Smart TGA tooling. It combines ``component_features.json``
files emitted by ``smart_tga_component_label_pack.py`` and writes a single
reviewed dataset plus per-label/per-target summary stats.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
NUMERIC_KEYS = (
    "area_px",
    "aspect",
    "fill",
    "center_x",
    "center_y",
    "mean_saturation",
    "mean_value",
    "edge_density",
    "color_std",
)


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _summarize(records: list[dict[str, Any]], group_key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get(group_key) or "unknown")].append(record)

    summary: dict[str, Any] = {}
    for key, items in sorted(grouped.items()):
        stats: dict[str, Any] = {"count": len(items)}
        for numeric_key in NUMERIC_KEYS:
            vals = [float(item[numeric_key]) for item in items if isinstance(item.get(numeric_key), (int, float))]
            if vals:
                stats[numeric_key] = {
                    "mean": round(mean(vals), 6),
                    "min": round(min(vals), 6),
                    "max": round(max(vals), 6),
                }
        summary[key] = stats
    return summary


def build_bank(args: argparse.Namespace) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    sources: list[str] = []
    for source in args.features:
        path = _repo_path(source)
        rows = _read_json(path)
        if not isinstance(rows, list):
            raise ValueError(f"{path} is not a list of component feature rows")
        for row in rows:
            item = dict(row)
            item["feature_source"] = str(path.resolve())
            records.append(item)
        sources.append(str(path.resolve()))

    out_dir = _repo_path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    records_path = out_dir / "reviewed_component_features.json"
    records_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    summary = {
        "sources": sources,
        "records": len(records),
        "paint_labels": dict(Counter(str(item.get("paint_label")) for item in records)),
        "target_layers": dict(Counter(str(item.get("target_layer")) for item in records)),
        "labels": dict(Counter(str(item.get("label")) for item in records)),
        "by_target_layer": _summarize(records, "target_layer"),
        "by_label": _summarize(records, "label"),
        "records_path": str(records_path.resolve()),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", nargs="+", required=True, help="component_features.json paths")
    parser.add_argument("--output", required=True, help="Output directory for combined feature bank")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(build_bank(parse_args()), indent=2))


if __name__ == "__main__":
    main()
