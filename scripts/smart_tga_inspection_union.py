"""Create an explicit, provenance-preserving union of Smart TGA inspections.

Successful duplicate paint labels are never resolved implicitly.  The caller
must select the winning run with ``--select paint_label=run_name``; unique
records and a successful retry replacing failures are safe to merge directly.
The output keeps original artifact paths and writes a compact provenance map.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence


def _read_records(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "inspection_records.json"
    if not path.is_file():
        raise FileNotFoundError(f"inspection run has no records: {run_dir}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"expected a record list in {path}")
    return payload


def _normalized_label(record: dict[str, Any]) -> str:
    label = str(record.get("paint_label") or "").replace("\\", "/")
    if not label:
        raise ValueError("inspection record has no paint_label")
    return label


def _selection_map(values: Sequence[str]) -> dict[str, str]:
    selections: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"selection must be paint_label=run_name: {value!r}")
        label, run_name = value.rsplit("=", 1)
        label = label.replace("\\", "/").strip()
        run_name = run_name.strip()
        if not label or not run_name:
            raise ValueError(f"invalid selection: {value!r}")
        if label in selections:
            raise ValueError(f"duplicate selection for {label}")
        selections[label] = run_name
    return selections


def merge_runs(
    run_dirs: Sequence[Path],
    selections: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for run_dir in run_dirs:
        resolved = Path(run_dir).resolve()
        for record in _read_records(resolved):
            candidates.setdefault(_normalized_label(record), []).append((resolved, record))

    merged = []
    provenance: dict[str, Any] = {}
    unused_selections = set(selections)
    for label in sorted(candidates):
        options = candidates[label]
        successful = [(run, record) for run, record in options if bool(record.get("success"))]
        if len(successful) <= 1:
            winner = successful[0] if successful else options[-1]
            policy = "unique_success" if successful else "latest_failure"
        else:
            selected = selections.get(label)
            if selected is None:
                runs = ", ".join(run.name for run, _record in successful)
                raise ValueError(
                    f"duplicate successful records for {label}; choose one with --select "
                    f"{label}=<run_name> from: {runs}"
                )
            matches = [item for item in successful if item[0].name == selected or str(item[0]) == selected]
            if len(matches) != 1:
                raise ValueError(f"selection {label}={selected} did not identify exactly one successful run")
            winner = matches[0]
            policy = "explicit_selection"
            unused_selections.discard(label)
        run, record = winner
        copied = dict(record)
        copied["_union_source_run"] = str(run)
        merged.append(copied)
        provenance[label] = {
            "selected_run": str(run),
            "policy": policy,
            "candidate_runs": [str(candidate_run) for candidate_run, _record in options],
            "successful_candidate_count": len(successful),
        }
    if unused_selections:
        raise ValueError("selections did not match duplicate labels: " + ", ".join(sorted(unused_selections)))
    return merged, provenance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", type=Path, required=True)
    parser.add_argument("--select", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records, provenance = merge_runs(args.run, _selection_map(args.select))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "inspection_records.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )
    (args.output / "provenance.json").write_text(
        json.dumps({
            "schema": "spb-smart-tga-inspection-union-v1",
            "source_runs": [str(path.resolve()) for path in args.run],
            "record_count": len(records),
            "records": provenance,
        }, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "record_count": len(records),
        "explicit_selection_count": sum(
            item["policy"] == "explicit_selection" for item in provenance.values()
        ),
        "output": str(args.output.resolve()),
    }, indent=2))


if __name__ == "__main__":
    main()
