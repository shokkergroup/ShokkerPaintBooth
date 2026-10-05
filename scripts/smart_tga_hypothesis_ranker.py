"""Train and apply an additive, zero-authority Smart TGA review ranker.

Cycle740 turns Cycle739's immutable anchor-free hypotheses into exact-mask
families.  All proposals and provenance remain available.  A paint-disjoint
model may add a small number of review candidates, but it cannot remove an
intrinsic candidate, assign semantics, claim ownership, or affect output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import joblib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from sklearn.ensemble import ExtraTreesClassifier


FEATURE_NAMES = (
    "intrinsic_score",
    "d4_similarity",
    "log_pixel_area",
    "support_height_fraction",
    "support_width_fraction",
    "support_bbox_occupancy",
    "panel_occupancy",
    "border_touch_fraction",
    "is_raw_palette_role",
    "is_enclosed_silhouette",
    "is_post_open_silhouette",
    "lightness_rank",
    "post_open_kernel_fraction",
    "retained_component_count",
    "connected_component_count",
    "hole_count",
    "perimeter_over_sqrt_area",
    "row_projection_cv",
    "column_projection_cv",
    "support_aspect_ratio",
)


@dataclass(frozen=True)
class ExactMaskBank:
    masks: dict[str, np.ndarray]

    @classmethod
    def load(cls, path: str | Path) -> "ExactMaskBank":
        payload = np.load(Path(path), allow_pickle=True)
        masks: dict[str, np.ndarray] = {}
        for index, proposal_id in enumerate(payload["proposal_ids"].tolist()):
            shape = tuple(map(int, payload["shapes"][index]))
            pixel_count = int(np.prod(shape))
            offset = int(payload["offsets"][index])
            length = int(payload["lengths"][index])
            packed = payload["packed"][offset : offset + length]
            masks[str(proposal_id)] = (
                np.unpackbits(packed)[:pixel_count].reshape(shape).astype(np.uint8)
            )
        return cls(masks=masks)


def exact_mask_id(mask: np.ndarray) -> str:
    """Return a shape-aware identity for an exact immutable mask."""
    shape = np.asarray(mask.shape, dtype=np.int32).tobytes()
    return hashlib.sha256(shape + np.packbits(mask.astype(bool)).tobytes()).hexdigest()


def _safe_array(values: Iterable[float], default: float = 0.0) -> np.ndarray:
    array = np.asarray(list(values), dtype=np.float64)
    return array if array.size else np.asarray([default], dtype=np.float64)


def proposal_features(row: dict, mask: np.ndarray) -> np.ndarray:
    """Extract intrinsic mask/provenance evidence without semantic ownership."""
    binary = mask.astype(np.uint8)
    ys, xs = np.where(binary > 0)
    if not len(xs):
        return np.zeros(len(FEATURE_NAMES), dtype=np.float64)

    height, width = binary.shape
    support_width = int(xs.max() - xs.min() + 1)
    support_height = int(ys.max() - ys.min() + 1)
    pixel_area = max(1, int(binary.sum()))
    contours, hierarchy = cv2.findContours(
        binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    hole_count = 0
    if hierarchy is not None:
        hole_count = sum(1 for entry in hierarchy[0] if int(entry[3]) >= 0)
    component_count = int(cv2.connectedComponentsWithStats(binary, 8)[0] - 1)
    perimeter = sum(float(cv2.arcLength(contour, True)) for contour in contours)
    row_projection = binary.sum(axis=1)
    column_projection = binary.sum(axis=0)
    row_projection = row_projection[row_projection > 0]
    column_projection = column_projection[column_projection > 0]
    border_touches = sum(
        (
            int(xs.min()) == 0,
            int(ys.min()) == 0,
            int(xs.max()) + 1 == width,
            int(ys.max()) + 1 == height,
        )
    )

    features = row.get("features", {})
    provenance = row.get("provenance", {})
    variant = provenance.get("assembly_variant") or "raw_palette_role"
    return np.asarray(
        [
            float(row.get("intrinsic_score", 0.0)),
            float(row.get("corroborative_d4_similarity", 0.0)),
            math.log1p(pixel_area),
            float(features.get("height_fraction", support_height / max(1, height))),
            float(features.get("width_fraction", support_width / max(1, width))),
            float(
                features.get(
                    "bbox_occupancy", pixel_area / max(1, support_width * support_height)
                )
            ),
            float(features.get("panel_occupancy", pixel_area / max(1, width * height))),
            float(features.get("border_touches", border_touches)) / 4.0,
            float(variant == "raw_palette_role"),
            float(variant == "enclosed_multicolor_silhouette"),
            float(variant == "enclosed_silhouette_vertical_open"),
            float(provenance.get("lab_lightness_rank", 0)) / 7.0,
            float(
                provenance.get("post_assembly_vertical_open_kernel_height", 1) or 1
            )
            / 31.0,
            float(len(provenance.get("retained_components") or [])),
            float(component_count),
            float(hole_count),
            perimeter / math.sqrt(pixel_area),
            float(np.std(row_projection) / max(1.0, np.mean(row_projection))),
            float(np.std(column_projection) / max(1.0, np.mean(column_projection))),
            support_width / max(1, support_height),
        ],
        dtype=np.float64,
    )


def collapse_panel_families(
    hypotheses: list[dict], bank: ExactMaskBank, panel_name: str
) -> list[dict]:
    """Collapse exact duplicates while preserving every member and provenance."""
    grouped: dict[str, list[dict]] = {}
    for row in hypotheses:
        if row["panel_name"] != panel_name:
            continue
        mask = bank.masks[row["proposal_id"]]
        grouped.setdefault(exact_mask_id(mask), []).append(row)

    families: list[dict] = []
    for mask_id, rows in grouped.items():
        representative = max(rows, key=lambda item: float(item.get("rank_score", 0.0)))
        mask = bank.masks[representative["proposal_id"]]
        families.append(
            {
                "family_id": f"{panel_name}:{mask_id[:16]}",
                "exact_mask_sha256": mask_id,
                "panel_name": panel_name,
                "representative_proposal_id": representative["proposal_id"],
                "expanded_panel_bbox": representative["expanded_panel_bbox"],
                "member_proposal_ids": [row["proposal_id"] for row in rows],
                "member_provenance": [row.get("provenance", {}) for row in rows],
                "member_features": [
                    proposal_features(row, bank_mask).tolist()
                    for row, bank_mask in (
                        (row, bank.masks[row["proposal_id"]]) for row in rows
                    )
                ],
                "proposal_count": len(rows),
                "baseline_score": max(float(row.get("rank_score", 0.0)) for row in rows),
                "semantic_label": None,
                "owner_neutral": True,
                "ownership_authority": False,
                "output_authority": False,
                "relationship_authority": False,
            }
        )
    families.sort(key=lambda row: row["baseline_score"], reverse=True)
    for rank, family in enumerate(families):
        family["baseline_unique_rank"] = rank
    return families


def _labels(path: str | Path) -> dict[str, dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {row["paint_label"]: row for row in payload.get("labels", [])}


def _training_groups(ledger_path: str | Path, labels_path: str | Path) -> list[dict]:
    ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    labels = _labels(labels_path)
    groups: list[dict] = []
    for record in ledger["records"]:
        label = labels.get(record["paint_label"])
        if not label:
            continue
        proposal_id = label["proposal_id"]
        panel_name = proposal_id.split(":", 1)[0]
        bank = ExactMaskBank.load(record["exact_hypotheses"])
        families = collapse_panel_families(record["hypotheses"], bank, panel_name)
        positive_mask_id = exact_mask_id(bank.masks[proposal_id])
        positive_family_id = f"{panel_name}:{positive_mask_id[:16]}"
        groups.append(
            {
                "paint_label": record["paint_label"],
                "families": families,
                "positive_family_id": positive_family_id,
            }
        )
    return groups


def _matrix(groups: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    features, labels = [], []
    for group in groups:
        for family in group["families"]:
            is_positive = family["family_id"] == group["positive_family_id"]
            for member_features in family["member_features"]:
                features.append(member_features)
                labels.append(is_positive)
    return np.asarray(features, dtype=np.float64), np.asarray(labels, dtype=np.uint8)


def new_ranker() -> ExtraTreesClassifier:
    return ExtraTreesClassifier(
        n_estimators=300,
        min_samples_leaf=1,
        max_features=0.8,
        class_weight="balanced",
        random_state=740,
        n_jobs=1,
    )


def leave_one_paint_out(groups: list[dict]) -> list[dict]:
    results = []
    for index, heldout in enumerate(groups):
        training = [group for offset, group in enumerate(groups) if offset != index]
        features, labels = _matrix(training)
        model = new_ranker().fit(features, labels)
        scores = np.asarray(
            [
                max(
                    model.predict_proba(np.asarray(family["member_features"]))[:, 1]
                )
                for family in heldout["families"]
            ]
        )
        target = next(
            offset
            for offset, family in enumerate(heldout["families"])
            if family["family_id"] == heldout["positive_family_id"]
        )
        results.append(
            {
                "paint_label": heldout["paint_label"],
                "positive_family_id": heldout["positive_family_id"],
                "learned_rank": int(np.sum(scores > scores[target])),
                "candidate_family_count": len(heldout["families"]),
            }
        )
    return results


def train_ranker(
    ledger_path: str | Path, labels_path: str | Path
) -> tuple[ExtraTreesClassifier, list[dict], list[dict]]:
    groups = _training_groups(ledger_path, labels_path)
    if len(groups) < 3:
        raise ValueError("at least three paint-disjoint reviewed groups are required")
    features, labels = _matrix(groups)
    model = new_ranker().fit(features, labels)
    return model, groups, leave_one_paint_out(groups)


def _rank_record(
    record: dict,
    model: ExtraTreesClassifier,
    baseline_slots: int,
    learned_rescue_slots: int,
) -> tuple[dict, ExactMaskBank]:
    bank = ExactMaskBank.load(record["exact_hypotheses"])
    panels = sorted({row["panel_name"] for row in record["hypotheses"]})
    ranked_panels = []
    for panel_name in panels:
        families = collapse_panel_families(record["hypotheses"], bank, panel_name)
        if not families:
            continue
        scores = np.asarray(
            [
                max(model.predict_proba(np.asarray(family["member_features"]))[:, 1])
                for family in families
            ]
        )
        order = np.argsort(-scores, kind="stable")
        for learned_rank, family_index in enumerate(order.tolist()):
            families[family_index]["learned_score"] = float(scores[family_index])
            families[family_index]["learned_unique_rank"] = learned_rank

        baseline_ids = {
            family["family_id"] for family in families[:baseline_slots]
        }
        learned_ids = {
            families[index]["family_id"] for index in order[:learned_rescue_slots]
        }
        review_ids = baseline_ids | learned_ids
        for family in families:
            family["baseline_review_slot"] = family["family_id"] in baseline_ids
            family["learned_rescue_slot"] = (
                family["family_id"] in learned_ids
                and family["family_id"] not in baseline_ids
            )
            family["combined_review_shortlist"] = family["family_id"] in review_ids
        families.sort(
            key=lambda row: (
                not row["combined_review_shortlist"],
                not row["baseline_review_slot"],
                row["baseline_unique_rank"]
                if row["baseline_review_slot"]
                else row["learned_unique_rank"],
            )
        )
        ranked_panels.append(
            {
                "panel_name": panel_name,
                "family_count": len(families),
                "combined_review_count": sum(
                    bool(family["combined_review_shortlist"]) for family in families
                ),
                "families": families,
            }
        )
    return (
        {
            "paint_label": record["paint_label"],
            "source": record["source"],
            "owner_neutral": True,
            "output_authority": False,
            "panels": ranked_panels,
        },
        bank,
    )


def _find_family(ranked_record: dict, proposal_id: str) -> dict:
    panel_name = proposal_id.split(":", 1)[0]
    panel = next(row for row in ranked_record["panels"] if row["panel_name"] == panel_name)
    return next(
        family
        for family in panel["families"]
        if proposal_id in family["member_proposal_ids"]
    )


def evaluate_labels(ranked_records: list[dict], labels_path: str | Path) -> dict:
    labels = _labels(labels_path)
    rows = []
    for record in ranked_records:
        label = labels.get(record["paint_label"])
        if not label:
            continue
        family = _find_family(record, label["proposal_id"])
        panel = next(
            panel
            for panel in record["panels"]
            if panel["panel_name"] == family["panel_name"]
        )
        raw_rows = [
            proposal
            for proposal in json.loads(
                Path(record["_source_ledger"]).read_text(encoding="utf-8")
            )["records"][record["_source_record_index"]]["hypotheses"]
            if proposal["panel_name"] == family["panel_name"]
        ]
        raw_rank = next(
            index
            for index, proposal in enumerate(raw_rows)
            if proposal["proposal_id"] == label["proposal_id"]
        )
        rows.append(
            {
                "paint_label": record["paint_label"],
                "proposal_id": label["proposal_id"],
                "semantic": label.get("semantic"),
                "clean_number_core": bool(
                    label.get("clean_number_core", label.get("clean_instance", False))
                ),
                "baseline_raw_rank": raw_rank,
                "baseline_unique_rank": family["baseline_unique_rank"],
                "learned_unique_rank": family["learned_unique_rank"],
                "combined_review_shortlist": family["combined_review_shortlist"],
                "abstain_required": bool(label.get("abstain_required", False)),
                "panel_family_count": panel["family_count"],
            }
        )

    clean = [row for row in rows if row["clean_number_core"]]
    denominator = len(rows)
    return {
        "paint_count": denominator,
        "rows": rows,
        "clean_number_core_baseline_raw_top12": sum(
            row["baseline_raw_rank"] < 12 for row in clean
        ),
        "clean_number_core_exact_family_top12": sum(
            row["baseline_unique_rank"] < 12 for row in clean
        ),
        "clean_number_core_learned_top12": sum(
            row["learned_unique_rank"] < 12 for row in clean
        ),
        "clean_number_core_combined_review": sum(
            row["combined_review_shortlist"] for row in clean
        ),
        "metric_denominator_all_paints": denominator,
        "authority_accepts": 0,
    }


def _font(size: int = 18) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def render_learned_additions(
    ranked_record: dict, bank: ExactMaskBank, output: Path
) -> str | None:
    additions = [
        family
        for panel in ranked_record["panels"]
        for family in panel["families"]
        if family["learned_rescue_slot"]
    ]
    if not additions:
        return None
    source = Image.open(ranked_record["source"]).convert("RGB")
    cell_width, cell_height = 330, 250
    sheet = Image.new("RGB", (cell_width * len(additions), cell_height), (28, 31, 36))
    draw = ImageDraw.Draw(sheet)
    font = _font(15)
    for index, family in enumerate(additions):
        proposal_id = family["representative_proposal_id"]
        mask = bank.masks[proposal_id]
        left, top, width, height = map(int, family["expanded_panel_bbox"])
        crop = source.crop((left, top, left + width, top + height)).resize(
            (300, 180), Image.Resampling.NEAREST
        )
        overlay = np.asarray(crop).copy()
        resized_mask = cv2.resize(
            mask, (300, 180), interpolation=cv2.INTER_NEAREST
        ).astype(bool)
        overlay[resized_mask] = (
            0.55 * overlay[resized_mask] + 0.45 * np.asarray([255, 40, 180])
        ).astype(np.uint8)
        sheet.paste(Image.fromarray(overlay), (index * cell_width + 15, 10))
        draw.text(
            (index * cell_width + 15, 195),
            f"{family['panel_name']}\nlearned #{family['learned_unique_rank']} / "
            f"base #{family['baseline_unique_rank']}\n{proposal_id[-24:]}",
            fill=(240, 242, 246),
            font=font,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return str(output.resolve())


def render_family_shortlists(
    ranked_record: dict, bank: ExactMaskBank, output_dir: Path
) -> list[str]:
    """Render the de-duplicated review shortlist without changing its masks."""
    source = Image.open(ranked_record["source"]).convert("RGB")
    font = _font(14)
    paths = []
    for panel in ranked_record["panels"]:
        families = [
            family
            for family in panel["families"]
            if family["combined_review_shortlist"]
        ]
        if not families:
            continue
        columns, cell_width, cell_height = 4, 330, 250
        rows = int(math.ceil(len(families) / columns))
        sheet = Image.new(
            "RGB", (columns * cell_width, rows * cell_height), (28, 31, 36)
        )
        draw = ImageDraw.Draw(sheet)
        for index, family in enumerate(families):
            proposal_id = family["representative_proposal_id"]
            mask = bank.masks[proposal_id]
            left, top, width, height = map(int, family["expanded_panel_bbox"])
            crop = source.crop((left, top, left + width, top + height)).resize(
                (300, 180), Image.Resampling.NEAREST
            )
            overlay = np.asarray(crop).copy()
            resized_mask = cv2.resize(
                mask, (300, 180), interpolation=cv2.INTER_NEAREST
            ).astype(bool)
            overlay[resized_mask] = (
                0.55 * overlay[resized_mask]
                + 0.45 * np.asarray([255, 40, 180])
            ).astype(np.uint8)
            x = (index % columns) * cell_width + 15
            y = (index // columns) * cell_height + 10
            sheet.paste(Image.fromarray(overlay), (x, y))
            draw.text(
                (x, y + 185),
                f"unique #{family['baseline_unique_rank']} | members={family['proposal_count']}\n"
                f"learned #{family['learned_unique_rank']}\n{proposal_id[-24:]}",
                fill=(240, 242, 246),
                font=font,
            )
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_panel = panel["panel_name"].replace("/", "_").replace(" ", "_")
        path = output_dir / f"{safe_panel}_exact_family_shortlist.png"
        sheet.save(path)
        paths.append(str(path.resolve()))
    return paths


def score_ledger(
    ledger_path: str | Path,
    model: ExtraTreesClassifier,
    baseline_slots: int = 12,
    learned_rescue_slots: int = 0,
) -> tuple[list[dict], dict[str, ExactMaskBank]]:
    ledger_path = Path(ledger_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ranked_records, banks = [], {}
    for index, record in enumerate(ledger["records"]):
        ranked, bank = _rank_record(
            record, model, baseline_slots, learned_rescue_slots
        )
        ranked["_source_ledger"] = str(ledger_path.resolve())
        ranked["_source_record_index"] = index
        ranked_records.append(ranked)
        banks[record["paint_label"]] = bank
    return ranked_records, banks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-ledger", type=Path, required=True)
    parser.add_argument("--train-labels", type=Path, required=True)
    parser.add_argument("--score-ledger", type=Path, required=True)
    parser.add_argument("--score-labels", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-slots", type=int, default=12)
    parser.add_argument("--learned-rescue-slots", type=int, default=0)
    args = parser.parse_args()

    model, training_groups, cross_validation = train_ranker(
        args.train_ledger, args.train_labels
    )
    training_paints = {group["paint_label"] for group in training_groups}
    score_payload = json.loads(args.score_ledger.read_text(encoding="utf-8"))
    scoring_paints = {record["paint_label"] for record in score_payload["records"]}
    overlap = training_paints & scoring_paints
    if overlap:
        raise ValueError(f"training/scoring paint overlap: {sorted(overlap)}")

    ranked_records, banks = score_ledger(
        args.score_ledger,
        model,
        baseline_slots=args.baseline_slots,
        learned_rescue_slots=args.learned_rescue_slots,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    review_sheets = {}
    shortlist_review_sheets = {}
    for record in ranked_records:
        safe = record["paint_label"].replace("/", "_").replace(" ", "_")
        sheet = render_learned_additions(
            record, banks[record["paint_label"]], args.output / f"{safe}_learned_additions.png"
        )
        review_sheets[record["paint_label"]] = sheet
        shortlist_review_sheets[record["paint_label"]] = render_family_shortlists(
            record, banks[record["paint_label"]], args.output / safe
        )

    model_path = args.output / "hypothesis_ranker.joblib"
    joblib.dump(model, model_path)
    evaluation = evaluate_labels(ranked_records, args.score_labels) if args.score_labels else None
    ledger = {
        "schema": "smart_tga_additive_hypothesis_ranker_v1",
        "feature_names": list(FEATURE_NAMES),
        "model": {
            "kind": "ExtraTreesClassifier",
            "status": "shadow_only_not_accepted_for_review_expansion",
            "parameters": {
                "n_estimators": 300,
                "min_samples_leaf": 1,
                "max_features": 0.8,
                "class_weight": "balanced",
                "random_state": 740,
            },
            "artifact": str(model_path.resolve()),
        },
        "training_paints": sorted(training_paints),
        "scoring_paints": sorted(scoring_paints),
        "paint_disjoint": not bool(overlap),
        "cross_validation": cross_validation,
        "baseline_slots_preserved": args.baseline_slots,
        "learned_rescue_slots": args.learned_rescue_slots,
        "semantic_authority": False,
        "ownership_authority": False,
        "output_authority": False,
        "apply_locked": True,
        "records": ranked_records,
        "evaluation": evaluation,
        "review_sheets": review_sheets,
        "shortlist_review_sheets": shortlist_review_sheets,
    }
    path = args.output / "ranked_family_ledger.json"
    path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ledger": str(path.resolve()),
                "training_paints": len(training_paints),
                "scoring_paints": len(scoring_paints),
                "evaluation": evaluation,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
