"""Build the release-priority Smart TGA evaluation queue.

The commercial beta target is Dirt Late Models, NASCAR-style stock cars, and
trucks.  In iRacing paint folders ``car_num_*`` (and ``car_num_team_*``)
denotes a paint expected to contain a custom number; plain ``car_*`` and
``car_team_*`` paints are non-numbered controls.  This module makes that
contract machine-readable so corpus work cannot drift toward unrelated GT
cars or mistake a numbered paint for an empty-number control.

The tool is read-only.  It inventories real TGA files and writes a compact,
deterministic JSON queue.  Exact car/car_num pairs are ranked first for
conservative pair auditing; their image delta becomes number truth only after
the separate safety gate.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_ROOTS = (
    Path.home() / "Documents/iRacing/paint",
    Path(r"C:\DRIVE E BACKUP\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\SPB Smart TGA Examples"),
)
DEFAULT_OUTPUT = Path("_smart_tga_runs/smart_tga_market_queue_v1/queue.json")


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def market_segment(folder: str) -> str | None:
    """Return the owner's beta market segment, or None when out of market."""
    name = _normalized(folder)
    if "dirtlatemodel" in name or name in {"latemodel", "latemodel2023", "superlatemodel"}:
        return "dirt_late_model"
    if "truck" in name:
        return "truck"
    if any(token in name for token in ("stockcars", "arca", "streetstock", "nascar")):
        return "nascar_stock_car"
    return None


def filename_intent(filename: str) -> str | None:
    """Classify iRacing paint naming without inferring from image contents."""
    name = filename.lower()
    if not name.endswith(".tga"):
        return None
    if re.match(r"^car_num_(?:team_)?[a-z0-9].*\.tga$", name):
        return "numbered"
    if name.startswith("car_num_"):
        return None
    if name.startswith(("car_decal_", "car_spec_")):
        return None
    if re.match(r"^car_(?:team_)?[a-z0-9].*\.tga$", name):
        return "non_numbered_control"
    return None


def _number_key(filename: str) -> str | None:
    name = filename.lower()
    for prefix in ("car_num_team_", "car_num_"):
        if name.startswith(prefix) and name.endswith(".tga"):
            return name[len(prefix):-4]
    return None


@dataclass(frozen=True)
class QueueRecord:
    path: str
    paint_label: str
    source_family: str
    segment: str
    filename_intent: str
    paired_control: str | None
    priority: int


def inventory(roots: list[Path]) -> list[QueueRecord]:
    records: list[QueueRecord] = []
    seen: set[str] = set()
    seen_labels: set[str] = set()
    for root in roots:
        root = root.resolve()
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.tga"), key=lambda p: str(p).lower()):
            segment = market_segment(path.parent.name)
            intent = filename_intent(path.name)
            if segment is None or intent is None:
                continue
            resolved = str(path.resolve())
            folded = resolved.lower()
            paint_label = f"{path.parent.name}/{path.name}"
            folded_label = paint_label.lower()
            if folded in seen or folded_label in seen_labels:
                continue
            seen.add(folded)
            seen_labels.add(folded_label)
            paired: str | None = None
            key = _number_key(path.name)
            if intent == "numbered" and key:
                candidate = path.with_name(f"car_{key}.tga")
                if candidate.is_file():
                    paired = str(candidate.resolve())
            priority = 0 if paired else (1 if intent == "numbered" else 2)
            records.append(QueueRecord(
                path=resolved,
                paint_label=paint_label,
                source_family=path.parent.name,
                segment=segment,
                filename_intent=intent,
                paired_control=paired,
                priority=priority,
            ))
    return records


def select_queue(records: list[QueueRecord], limit: int, control_fraction: float = 0.10) -> list[QueueRecord]:
    """Select a deterministic segment-balanced, numbered-heavy evaluation set."""
    if limit <= 0:
        return []
    control_slots = min(int(round(limit * max(0.0, min(control_fraction, 0.5)))), limit)
    numbered_slots = limit - control_slots
    segments = ("dirt_late_model", "nascar_stock_car", "truck")
    pools: dict[tuple[str, str], list[QueueRecord]] = defaultdict(list)
    for record in records:
        pools[(record.segment, record.filename_intent)].append(record)
    # Diversify vehicle folders within every segment.  A purely alphabetical
    # queue hid most DLM/NASCAR/truck templates behind one large folder.
    for key, pool in list(pools.items()):
        diversified: list[QueueRecord] = []
        for priority in sorted({record.priority for record in pool}):
            family_pools: dict[str, list[QueueRecord]] = defaultdict(list)
            for record in pool:
                if record.priority == priority:
                    family_pools[record.source_family].append(record)
            for family_pool in family_pools.values():
                family_pool.sort(key=lambda r: r.paint_label.lower())
            families = sorted(family_pools, key=str.lower)
            offset = 0
            while True:
                added = False
                for family in families:
                    family_pool = family_pools[family]
                    if offset < len(family_pool):
                        diversified.append(family_pool[offset])
                        added = True
                if not added:
                    break
                offset += 1
        pools[key] = diversified

    selected: list[QueueRecord] = []

    def take_round_robin(intent: str, slots: int) -> None:
        indices = {segment: 0 for segment in segments}
        while slots > 0:
            progressed = False
            for segment in segments:
                pool = pools[(segment, intent)]
                idx = indices[segment]
                if idx >= len(pool):
                    continue
                selected.append(pool[idx])
                indices[segment] += 1
                slots -= 1
                progressed = True
                if slots == 0:
                    break
            if not progressed:
                break

    take_round_robin("numbered", numbered_slots)
    take_round_robin("non_numbered_control", control_slots)
    return selected


def build_report(roots: list[Path], limit: int, control_fraction: float) -> dict:
    records = inventory(roots)
    selected = select_queue(records, limit=limit, control_fraction=control_fraction)
    return {
        "schema": "spb-smart-tga-market-queue-v1",
        "policy": {
            "release_segments": ["dirt_late_model", "nascar_stock_car", "truck"],
            "primary_filename_intent": "car_num_* / car_num_team_* => numbered",
            "control_filename_intent": "car_* / car_team_* => non-numbered control",
            "control_fraction": control_fraction,
            "selection": "segment round-robin; exact car/car_num audit candidates first",
            "pair_safety": "paired_control is not truth until smart_tga_number_pair_audit classifies it safe",
        },
        "roots": [str(root.resolve()) for root in roots],
        "inventory_count": len(records),
        "inventory_by_segment": dict(Counter(r.segment for r in records)),
        "inventory_by_intent": dict(Counter(r.filename_intent for r in records)),
        "paired_numbered_count": sum(bool(r.paired_control) for r in records),
        "selected_count": len(selected),
        "selected_by_segment": dict(Counter(r.segment for r in selected)),
        "selected_by_intent": dict(Counter(r.filename_intent for r in selected)),
        "records": [asdict(record) for record in selected],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, default=[])
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--control-fraction", type=float, default=0.10)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(args.root or list(DEFAULT_ROOTS), args.limit, args.control_fraction)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "inventory_count", "inventory_by_segment", "inventory_by_intent",
        "paired_numbered_count", "selected_count", "selected_by_segment",
        "selected_by_intent",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
