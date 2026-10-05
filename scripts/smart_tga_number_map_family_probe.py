"""Paint-disjoint probe for classifying nested number probability-map families.

The probe rebuilds exact immutable proposals from the frozen segmenter, joins only
durable human reviews, and evaluates a family scorer with nested paint-disjoint
cross-fitting.  It has no output-layer authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.number_map_family_features import (
        FAMILY_FEATURE_NAMES, FAMILY_OCR_FEATURE_NAMES,
        FAMILY_OWNER_CORROBORATION_FEATURE_NAMES, FAMILY_RELATIONSHIP_FEATURE_NAMES,
        FAMILY_TEMPLATE_POSITION_FEATURE_NAMES,
        map_family_feature_vector, map_family_ocr_features,
        map_family_owner_corroboration_features, map_family_relationship_features,
        map_family_template_position_features,
        map_proposal_feature_vector,
    )
    from engine.spec_sculpt.number_object_assembly import assemble_nested_proposal_families
    from engine.spec_sculpt.number_object_segmentation import (
        build_tiny_unet, image_feature_tensor, probability_region_proposals,
        project_local_support,
    )
    from engine.spec_sculpt.number_object_transfer import isolated_object_views
    from scripts.smart_tga_number_object_active_pool import _build_transfer_teacher
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_map_family_features import (  # type: ignore
        FAMILY_FEATURE_NAMES, FAMILY_OCR_FEATURE_NAMES,
        FAMILY_OWNER_CORROBORATION_FEATURE_NAMES, FAMILY_RELATIONSHIP_FEATURE_NAMES,
        FAMILY_TEMPLATE_POSITION_FEATURE_NAMES,
        map_family_feature_vector, map_family_ocr_features,
        map_family_owner_corroboration_features, map_family_relationship_features,
        map_family_template_position_features,
        map_proposal_feature_vector,
    )
    from engine.spec_sculpt.number_object_assembly import assemble_nested_proposal_families  # type: ignore
    from engine.spec_sculpt.number_object_segmentation import (  # type: ignore
        build_tiny_unet, image_feature_tensor, probability_region_proposals,
        project_local_support,
    )
    from engine.spec_sculpt.number_object_transfer import isolated_object_views  # type: ignore
    from scripts.smart_tga_number_object_active_pool import _build_transfer_teacher  # type: ignore


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


CLIP_TEXT_FEATURE_NAMES = (
    "clip_digit_similarity_max", "clip_digit_similarity_mean",
    "clip_alpha_similarity_max", "clip_alpha_similarity_mean",
    "clip_graphic_similarity_max", "clip_graphic_similarity_mean",
    "clip_digit_minus_alpha_margin", "clip_digit_minus_all_negative_margin",
)


def _build_clip_teacher():
    """Return cached LAION CLIP D4 embeddings plus universal text prototypes."""
    import open_clip
    import torch
    from PIL import Image as PilImage

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, _train, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k",
    )
    model = model.eval().to(device)
    prompts = (
        "Arabic numerals", "a group of large digits", "a two digit race car number",
        "large stylized racing numbers",
        "large stylized alphabetic letters", "an alphabetic acronym logo",
        "a word made of letters", "a company name wordmark", "a sponsor name",
        "a paint livery graphic", "an abstract logo symbol", "a racing team emblem",
    )
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    with torch.no_grad():
        text = model.encode_text(tokenizer(prompts).to(device)).float()
        text = text / text.norm(dim=1, keepdim=True).clamp_min(1e-8)
    text_prototypes = text.cpu().numpy().astype(np.float32)

    def embed(view_sets):
        flat = [view for views in view_sets for view in views]
        output = []
        with torch.no_grad():
            for start in range(0, len(flat), 64):
                images = [
                    preprocess(PilImage.fromarray(
                        (np.transpose(view, (1, 2, 0)).clip(0, 1) * 255).astype(np.uint8)
                    ))
                    for view in flat[start:start + 64]
                ]
                feature = model.encode_image(torch.stack(images).to(device)).float()
                feature = feature / feature.norm(dim=1, keepdim=True).clamp_min(1e-8)
                output.append(feature.cpu().numpy())
        matrix = np.concatenate(output).reshape(len(view_sets), 16, -1)
        appearance = matrix[:, :8].mean(axis=1)
        silhouette = matrix[:, 8:].mean(axis=1)
        appearance /= np.linalg.norm(appearance, axis=1, keepdims=True).clip(1e-8)
        silhouette /= np.linalg.norm(silhouette, axis=1, keepdims=True).clip(1e-8)
        return np.column_stack((appearance, silhouette)).astype(np.float32)

    return embed, text_prototypes


def _clip_text_feature_vector(embedding, text_prototypes):
    half = len(embedding) // 2
    appearance = np.asarray(embedding[:half], np.float32)
    appearance /= np.linalg.norm(appearance).clip(1e-8)
    similarity = text_prototypes @ appearance
    digit = similarity[:4]
    alpha = similarity[4:9]
    graphic = similarity[9:]
    return np.asarray((
        np.max(digit), np.mean(digit), np.max(alpha), np.mean(alpha),
        np.max(graphic), np.mean(graphic),
        np.max(digit) - np.max(alpha),
        np.max(digit) - max(np.max(alpha), np.max(graphic)),
    ), np.float32)


def _summary(truth, accepted):
    truth = np.asarray(truth, bool)
    accepted = np.asarray(accepted, bool)
    hits = int(np.count_nonzero(truth & accepted))
    controls = int(np.count_nonzero(~truth & accepted))
    accepted_count = int(np.count_nonzero(accepted))
    positives = int(np.count_nonzero(truth))
    return {
        "number_families": f"{hits}/{positives}", "accepted_hard_negative_families": controls,
        "accepted_families": accepted_count,
        "precision": round(hits / max(1, accepted_count), 6),
        "recall": round(hits / max(1, positives), 6),
    }


def _zero_negative_operating_point(probability, truth):
    """Maximize recovered positives subject to zero reviewed hard negatives."""
    probability = np.asarray(probability, np.float64)
    truth = np.asarray(truth, bool)
    thresholds = [float(np.nextafter(np.max(probability), np.inf))]
    thresholds.extend(sorted(set(map(float, probability)), reverse=True))
    candidates = []
    for threshold in thresholds:
        accepted = probability >= threshold
        summary = _summary(truth, accepted)
        if summary["accepted_hard_negative_families"] == 0:
            candidates.append((
                int(summary["number_families"].split("/")[0]),
                summary["precision"], -threshold, threshold, summary,
            ))
    return max(candidates, key=lambda item: item[:3])


def _prepare(train_base, train_embedding, test_base, test_embedding, use_transfer):
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    if use_transfer:
        component_count = min(8, len(train_base) - 1, train_embedding.shape[1])
        pca = PCA(n_components=component_count, svd_solver="randomized", random_state=714)
        train = np.column_stack((train_base, pca.fit_transform(train_embedding)))
        test = np.column_stack((test_base, pca.transform(test_embedding)))
    else:
        pca = None
        train, test = train_base, test_base
    scaler = StandardScaler().fit(train)
    return scaler.transform(train), scaler.transform(test), pca, scaler


def _fit_predict(base, embedding, truth, train, test, c_value, use_transfer):
    from sklearn.linear_model import LogisticRegression

    train_matrix, test_matrix, _pca, _scaler = _prepare(
        base[train], embedding[train], base[test], embedding[test], use_transfer,
    )
    model = LogisticRegression(
        C=float(c_value), class_weight="balanced", max_iter=4000, random_state=714,
    )
    model.fit(train_matrix, truth[train])
    return model.predict_proba(test_matrix)[:, 1]


def _group_cross_fitted(base, embedding, truth, groups, c_value, use_transfer):
    from sklearn.model_selection import LeaveOneGroupOut

    output = np.zeros(len(truth), np.float32)
    for train, test in LeaveOneGroupOut().split(base, truth, groups):
        output[test] = _fit_predict(
            base, embedding, truth, train, test, c_value, use_transfer,
        )
    return output


def _select_inner(base, embedding, truth, groups, use_transfer):
    candidates = []
    for c_value in (0.003, 0.01, 0.03, 0.1, 0.3):
        probability = _group_cross_fitted(
            base, embedding, truth, groups, c_value, use_transfer,
        )
        hits, precision, threshold_sort, threshold, summary = _zero_negative_operating_point(
            probability, truth,
        )
        candidates.append((hits, precision, -c_value, threshold_sort, c_value, threshold, summary))
    return max(candidates, key=lambda item: item[:4])


def _nested_cross_fit(base, embedding, truth, groups, use_transfer):
    from sklearn.model_selection import LeaveOneGroupOut

    probability = np.zeros(len(truth), np.float32)
    accepted = np.zeros(len(truth), bool)
    folds = []
    for train, test in LeaveOneGroupOut().split(base, truth, groups):
        selected = _select_inner(
            base[train], embedding[train], truth[train], groups[train], use_transfer,
        )
        _hits, _precision, _negative_c, _threshold_sort, c_value, threshold, inner_summary = selected
        probability[test] = _fit_predict(
            base, embedding, truth, train, test, c_value, use_transfer,
        )
        accepted[test] = probability[test] >= threshold
        folds.append({
            "held_out_paint": str(groups[test][0]), "selected_c": c_value,
            "selected_threshold": round(float(threshold), 6),
            "inner_zero_negative": inner_summary,
        })
    return probability, accepted, folds


def _select_inner_constrained(
    base, embedding, truth, groups, digit_evidence, number_overlap,
    template_number_evidence,
):
    candidates = []
    for c_value in (0.003, 0.01, 0.03, 0.1, 0.3):
        probability = _group_cross_fitted(base, embedding, truth, groups, c_value, True)
        probability_thresholds = [float(np.nextafter(np.max(probability), np.inf))]
        probability_thresholds.extend(sorted(set(map(float, probability)), reverse=True))
        for probability_threshold in probability_thresholds:
            for digit_threshold in (0.24, 0.26, 0.28, 0.30):
                for owner_threshold in (0.10, 0.20, 0.30, 0.40):
                    for position_threshold in (0.05, 0.10, 0.20, 0.30):
                        corroborated = (
                            (
                                (digit_evidence >= digit_threshold)
                                & (template_number_evidence >= position_threshold)
                            )
                            | (number_overlap >= owner_threshold)
                        )
                        accepted = (probability >= probability_threshold) & corroborated
                        summary = _summary(truth, accepted)
                        if summary["accepted_hard_negative_families"]:
                            continue
                        hits = int(summary["number_families"].split("/")[0])
                        candidates.append((
                            hits, summary["precision"],
                            digit_threshold + owner_threshold + position_threshold,
                            -c_value, probability_threshold, digit_threshold,
                            owner_threshold, position_threshold, c_value, summary,
                        ))
    if not candidates:
        raise AssertionError("no zero-negative constrained operating point")
    return max(candidates, key=lambda item: item[:4])


def _nested_cross_fit_constrained(
    base, embedding, truth, groups, digit_evidence, number_overlap,
    template_number_evidence,
):
    from sklearn.model_selection import LeaveOneGroupOut

    probability = np.zeros(len(truth), np.float32)
    accepted = np.zeros(len(truth), bool)
    folds = []
    for train, test in LeaveOneGroupOut().split(base, truth, groups):
        selected = _select_inner_constrained(
            base[train], embedding[train], truth[train], groups[train],
            digit_evidence[train], number_overlap[train], template_number_evidence[train],
        )
        (
            _hits, _precision, _gate_strength, _negative_c,
            probability_threshold, digit_threshold, owner_threshold,
            position_threshold, c_value, inner_summary,
        ) = selected
        probability[test] = _fit_predict(
            base, embedding, truth, train, test, c_value, True,
        )
        corroborated = (
            (
                (digit_evidence[test] >= digit_threshold)
                & (template_number_evidence[test] >= position_threshold)
            )
            | (number_overlap[test] >= owner_threshold)
        )
        accepted[test] = (probability[test] >= probability_threshold) & corroborated
        folds.append({
            "held_out_paint": str(groups[test][0]), "selected_c": c_value,
            "selected_probability_threshold": round(float(probability_threshold), 6),
            "selected_digit_threshold": digit_threshold,
            "selected_number_overlap_threshold": owner_threshold,
            "selected_template_number_threshold": position_threshold,
            "inner_zero_negative": inner_summary,
        })
    return probability, accepted, folds


def _family_records(
    inspection_path, active_pool_path, review_path, segment_model_path,
    transfer_teacher=None, panel_map=None,
):
    import torch

    pool = _read(active_pool_path)
    unlabeled = review_path is None
    review_document = {} if unlabeled else _read(review_path)
    proposal_reviews = review_document.get("proposal_labels", [])
    family_reviews = review_document.get("family_labels", [])
    if not unlabeled and bool(proposal_reviews) == bool(family_reviews):
        raise ValueError("review document must contain exactly one of proposal_labels or family_labels")
    review_by_key = {(item["paint_label"], item["proposal_id"]): item for item in proposal_reviews}
    review_by_family = {(item["paint_label"], item["family_id"]): item for item in family_reviews}
    if unlabeled:
        wanted_by_paint = {}
        for paint in pool["ranking"]:
            for item in paint["objects"]:
                if item.get("source_layer") == "owner_neutral_map":
                    wanted_by_paint.setdefault(item["paint_label"], set()).add(item["proposal_id"])
    elif family_reviews:
        review_manifest = _read(Path(review_document["review_sheet"]).with_suffix(".json"))
        reviewed_family_ids = set(review_by_family)
        selected_family_records = [
            item for item in review_manifest["families"]
            if (item["paint_label"], item["family_id"]) in reviewed_family_ids
        ]
        wanted_by_paint = {}
        for item in selected_family_records:
            wanted_by_paint.setdefault(item["paint_label"], set()).update(item["member_ids"])
    else:
        wanted_by_paint = {}
        for item in proposal_reviews:
            wanted_by_paint.setdefault(item["paint_label"], set()).add(item["proposal_id"])
    active_by_key = {
        (item["paint_label"], item["proposal_id"]): item
        for paint in pool["ranking"] for item in paint["objects"]
        if item.get("source_layer") == "owner_neutral_map"
    }
    inspection = {item["paint_label"]: item for item in _read(inspection_path)}
    blob = torch.load(segment_model_path, map_location="cpu", weights_only=True)
    segment = build_tiny_unet(int(blob["base_channels"]))
    segment.load_state_dict(blob["state_dict"])
    segment.eval()
    teacher = transfer_teacher or _build_transfer_teacher()
    proposal_records = []
    for paint_label in sorted(wanted_by_paint):
        rgb = np.asarray(Image.open(inspection[paint_label]["source_1024"]).convert("RGB"))
        source_parent = Path(inspection[paint_label]["source_1024"]).parent
        layer_masks = {
            path.stem: np.asarray(Image.open(path).convert("L")) > 0
            for path in (source_parent / "masks").glob("*.png")
        }
        with torch.no_grad():
            probability = torch.sigmoid(
                segment(torch.from_numpy(image_feature_tensor(rgb)[None]))
            )[0, 0].numpy()
        probability_canvas = cv2.resize(
            probability, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR,
        )
        wanted = wanted_by_paint[paint_label]
        proposals = [
            item for item in probability_region_proposals(probability, rgb.shape[:2])
            if item["proposal_id"] in wanted
        ]
        recovered = {item["proposal_id"] for item in proposals}
        if recovered != wanted:
            raise AssertionError(f"exact proposal regeneration drift for {paint_label}: {sorted(wanted - recovered)}")
        rgb_small = cv2.resize(rgb, (256, 256), interpolation=cv2.INTER_AREA)
        views = []
        paint_records = []
        for proposal in proposals:
            key = (paint_label, proposal["proposal_id"])
            active = active_by_key[key]
            review = review_by_key.get(key)
            vector = map_proposal_feature_vector(
                rgb, proposal["proposal_bbox"], proposal["raw_support"], probability_canvas,
                proposal["provenance"], active["foundation_probability"],
            )
            small_mask = project_local_support(
                proposal["raw_support"], proposal["proposal_bbox"], rgb.shape[:2], 256,
            )
            record = {
                "paint_label": paint_label, "proposal_id": proposal["proposal_id"],
                "proposal_bbox": proposal["proposal_bbox"],
                "provenance": proposal["provenance"], "vector": vector,
                "foundation_probability": float(active["foundation_probability"]),
                "semantic_class": None if review is None else review["semantic_class"],
                "review_label": None if review is None else review["label"],
                "is_number": None if review is None else str(review["semantic_class"]).lower() == "number",
                "raw_support": proposal["raw_support"], "layer_masks": layer_masks,
                "canvas_shape": rgb.shape[:2],
            }
            paint_records.append(record)
            views.append(isolated_object_views(rgb_small, small_mask))
        embeddings = teacher(views)
        for record, embedding in zip(paint_records, embeddings):
            record["transfer_embedding"] = np.asarray(embedding, np.float32)
        proposal_records.extend(paint_records)

    families = []
    by_id = {item["proposal_id"]: item for item in proposal_records}
    for paint_label in sorted({item["paint_label"] for item in proposal_records}):
        items = [item for item in proposal_records if item["paint_label"] == paint_label]
        assembled = assemble_nested_proposal_families(items)
        for family in assembled:
            members = [by_id[item] for item in family["member_ids"]]
            if unlabeled:
                is_number = None
                member_labels = []
                semantic_classes = []
            elif family_reviews:
                family_review = review_by_family.get((paint_label, family["family_id"]))
                if family_review is None:
                    continue
                is_number = str(family_review["semantic_class"]).lower() == "number"
                member_labels = [family_review["review_label"]]
                semantic_classes = [family_review["semantic_class"]]
            else:
                # A mixed family is unsafe and therefore a hard negative. Geometry is
                # assembly evidence only; it cannot manufacture Number authority.
                is_number = all(item["is_number"] for item in members)
                member_labels = [item["review_label"] for item in members]
                semantic_classes = sorted({item["semantic_class"] for item in members})
            embedding = np.mean([item["transfer_embedding"] for item in members], axis=0)
            embedding /= np.linalg.norm(embedding).clip(1e-8)
            outer = max(
                members,
                key=lambda item: int(item["proposal_bbox"][2]) * int(item["proposal_bbox"][3]),
            )
            families.append({
                "paint_label": paint_label, "family_id": family["family_id"],
                "family_bbox": family["family_bbox"], "member_ids": list(family["member_ids"]),
                "member_labels": member_labels,
                "semantic_classes": semantic_classes,
                "is_number": None if unlabeled else bool(is_number),
                "vector": map_family_feature_vector(members),
                "ocr_features": map_family_ocr_features(
                    family["family_bbox"],
                    (inspection[paint_label].get("route_adjudicator_shadow") or {}).get("ocr_region_samples") or (),
                ),
                "owner_features": map_family_owner_corroboration_features(
                    outer["proposal_bbox"], outer["raw_support"], outer["layer_masks"],
                ),
                "position_features": (
                    map_family_template_position_features(
                        outer["proposal_bbox"], outer["raw_support"],
                        outer["canvas_shape"], panel_map,
                    )
                    if panel_map is not None
                    else np.zeros(len(FAMILY_TEMPLATE_POSITION_FEATURE_NAMES), np.float32)
                ),
                "transfer_embedding": embedding.astype(np.float32),
            })
    return families


def run(
    inspection, active_pool, reviews, segment_model, output, model_output,
    extra_dataset_manifests=(), embedding_encoder="efficientnet", panel_map_path=None,
):
    datasets = [{
        "inspection": str(inspection), "active_pool": str(active_pool),
        "reviews": str(reviews), "segment_model": str(segment_model),
    }]
    datasets.extend(_read(Path(path)) for path in extra_dataset_manifests)
    if embedding_encoder == "clip":
        transfer_teacher, text_prototypes = _build_clip_teacher()
    else:
        transfer_teacher, text_prototypes = _build_transfer_teacher(), None
    panel_map = _read(Path(panel_map_path)) if panel_map_path else None
    families = []
    for dataset in datasets:
        families.extend(_family_records(
            Path(dataset["inspection"]), Path(dataset["active_pool"]),
            Path(dataset["reviews"]), Path(dataset["segment_model"]),
            transfer_teacher, panel_map,
        ))
    base = np.asarray([item["vector"] for item in families], np.float32)
    embedding = np.asarray([item["transfer_embedding"] for item in families], np.float32)
    truth = np.asarray([item["is_number"] for item in families], bool)
    groups = np.asarray([item["paint_label"] for item in families], object)
    relationship = np.zeros((len(families), len(FAMILY_RELATIONSHIP_FEATURE_NAMES)), np.float32)
    ocr = np.asarray([item["ocr_features"] for item in families], np.float32)
    owner = np.asarray([item["owner_features"] for item in families], np.float32)
    position = np.asarray([item["position_features"] for item in families], np.float32)
    clip_text = np.asarray([
        _clip_text_feature_vector(item["transfer_embedding"], text_prototypes)
        if text_prototypes is not None else np.zeros(len(CLIP_TEXT_FEATURE_NAMES), np.float32)
        for item in families
    ], np.float32)
    for paint_label in sorted(set(groups)):
        indexes = np.flatnonzero(groups == paint_label)
        areas = [
            max(1, int(families[index]["family_bbox"][2]) * int(families[index]["family_bbox"][3]))
            for index in indexes
        ]
        relationship[indexes] = map_family_relationship_features(embedding[indexes], areas)
    baseline = _summary(truth, np.ones(len(truth), bool))
    variants = {}
    raw = {}
    encoder_name = "clip" if embedding_encoder == "clip" else "d4"
    variant_specs = [
        ("intrinsic_map_family", False, False, False, False, False),
        (f"intrinsic_map_family_plus_{encoder_name}", True, False, False, False, False),
        (f"intrinsic_map_family_plus_{encoder_name}_peer", True, True, False, False, False),
        (f"intrinsic_map_family_plus_{encoder_name}_ocr", True, False, True, False, False),
        (f"intrinsic_map_family_plus_{encoder_name}_owner", True, False, False, False, True),
        (f"intrinsic_map_family_plus_{encoder_name}_peer_ocr", True, True, True, False, False),
        (f"intrinsic_map_family_plus_{encoder_name}_peer_ocr_owner", True, True, True, False, True),
    ]
    if text_prototypes is not None:
        variant_specs.extend((
            ("intrinsic_map_family_plus_clip_text", True, False, False, True, False),
            ("intrinsic_map_family_plus_clip_text_ocr", True, False, True, True, False),
            ("intrinsic_map_family_plus_clip_peer_text_ocr", True, True, True, True, False),
            ("intrinsic_map_family_plus_clip_peer_text_ocr_owner", True, True, True, True, True),
        ))
    for name, use_transfer, use_relationship, use_ocr, use_text, use_owner in variant_specs:
        columns = [base]
        if use_relationship:
            columns.append(relationship)
        if use_ocr:
            columns.append(ocr)
        if use_text:
            columns.append(clip_text)
        if use_owner:
            columns.append(owner)
        variant_base = np.column_stack(columns)
        probability, accepted, folds = _nested_cross_fit(
            variant_base, embedding, truth, groups, use_transfer,
        )
        final = _select_inner(variant_base, embedding, truth, groups, use_transfer)
        _hits, _precision, _negative_c, _threshold_sort, c_value, threshold, cv_summary = final
        variants[name] = {
            "nested_paint_disjoint": _summary(truth, accepted),
            "full_corpus_cross_fitted_zero_negative": cv_summary,
            "selected_c": c_value, "selected_threshold": round(float(threshold), 6),
            "folds": folds,
            "scores": [
                {
                    "paint_label": item["paint_label"], "family_id": item["family_id"],
                    "member_labels": item["member_labels"], "is_number": item["is_number"],
                    "probability": round(float(score), 6), "accepted": bool(decision),
                    "relationship_features": {
                        feature_name: round(float(feature_value), 6)
                        for feature_name, feature_value in zip(
                            FAMILY_RELATIONSHIP_FEATURE_NAMES, relationship[index],
                        )
                    },
                    "ocr_features": {
                        feature_name: round(float(feature_value), 6)
                        for feature_name, feature_value in zip(FAMILY_OCR_FEATURE_NAMES, ocr[index])
                    },
                    "clip_text_features": {
                        feature_name: round(float(feature_value), 6)
                        for feature_name, feature_value in zip(CLIP_TEXT_FEATURE_NAMES, clip_text[index])
                    },
                    "owner_corroboration_features": {
                        feature_name: round(float(feature_value), 6)
                        for feature_name, feature_value in zip(
                            FAMILY_OWNER_CORROBORATION_FEATURE_NAMES, owner[index],
                        )
                    },
                }
                for index, (item, score, decision) in enumerate(zip(families, probability, accepted))
            ],
        }
        raw[name] = (
            use_transfer, use_relationship, use_ocr, use_text, use_owner,
            c_value, threshold, variant_base,
        )

    constrained_name = "constrained_clip_digit_template_or_legacy_number"
    if text_prototypes is not None:
        constrained_base = np.column_stack((base, relationship, ocr, clip_text, owner, position))
        digit_evidence = clip_text[:, 0]
        number_overlap = owner[:, 0]
        template_number_evidence = position[:, 0]
        probability, accepted, folds = _nested_cross_fit_constrained(
            constrained_base, embedding, truth, groups, digit_evidence, number_overlap,
            template_number_evidence,
        )
        final = _select_inner_constrained(
            constrained_base, embedding, truth, groups, digit_evidence, number_overlap,
            template_number_evidence,
        )
        (
            _hits, _precision, _gate_strength, _negative_c,
            probability_threshold, digit_threshold, owner_threshold,
            position_threshold, c_value, cv_summary,
        ) = final
        variants[constrained_name] = {
            "nested_paint_disjoint": _summary(truth, accepted),
            "full_corpus_cross_fitted_zero_negative": cv_summary,
            "selected_c": c_value,
            "selected_probability_threshold": round(float(probability_threshold), 6),
            "selected_digit_threshold": digit_threshold,
            "selected_number_overlap_threshold": owner_threshold,
            "selected_template_number_threshold": position_threshold,
            "folds": folds,
            "scores": [
                {
                    "paint_label": item["paint_label"], "family_id": item["family_id"],
                    "member_labels": item["member_labels"], "is_number": item["is_number"],
                    "probability": round(float(score), 6), "accepted": bool(decision),
                    "clip_digit_evidence": round(float(digit), 6),
                    "legacy_number_overlap": round(float(overlap), 6),
                    "template_number_evidence": round(float(position_value), 6),
                }
                for item, score, decision, digit, overlap, position_value in zip(
                    families, probability, accepted, digit_evidence, number_overlap,
                    template_number_evidence,
                )
            ],
        }
        raw[constrained_name] = (
            True, True, True, True, True, c_value, probability_threshold,
            constrained_base, digit_threshold, owner_threshold, position_threshold,
        )

    selected_name = (
        constrained_name
        if text_prototypes is not None else "intrinsic_map_family_plus_d4_peer_ocr_owner"
    )
    selected_metrics = variants[selected_name]["nested_paint_disjoint"]
    promotable = (
        selected_metrics["accepted_hard_negative_families"] == 0
        and int(selected_metrics["number_families"].split("/")[0]) >= 2
    )
    if promotable:
        from sklearn.linear_model import LogisticRegression
        selected_raw = raw[selected_name]
        (
            use_transfer, use_relationship, use_ocr, use_text, use_owner,
            c_value, threshold, variant_base,
        ) = selected_raw[:8]
        train, _unused, pca, scaler = _prepare(
            variant_base, embedding, variant_base, embedding, use_transfer,
        )
        model = LogisticRegression(
            C=c_value, class_weight="balanced", max_iter=4000, random_state=714,
        ).fit(train, truth)
        model_output.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            model_output,
            feature_names=np.asarray((
                *FAMILY_FEATURE_NAMES, *FAMILY_RELATIONSHIP_FEATURE_NAMES,
                *FAMILY_OCR_FEATURE_NAMES, *CLIP_TEXT_FEATURE_NAMES,
                *FAMILY_OWNER_CORROBORATION_FEATURE_NAMES,
                *FAMILY_TEMPLATE_POSITION_FEATURE_NAMES,
            )),
            pca_mean=pca.mean_.astype(np.float32), pca_components=pca.components_.astype(np.float32),
            mean=scaler.mean_.astype(np.float32), scale=scaler.scale_.astype(np.float32),
            coefficient=model.coef_[0].astype(np.float32),
            intercept=np.asarray([model.intercept_[0]], np.float32),
            threshold=np.asarray([threshold], np.float32),
            digit_threshold=np.asarray([
                selected_raw[8] if selected_name == constrained_name else 0.0
            ], np.float32),
            number_overlap_threshold=np.asarray([
                selected_raw[9] if selected_name == constrained_name else 0.0
            ], np.float32),
            template_number_threshold=np.asarray([
                selected_raw[10] if selected_name == constrained_name else 0.0
            ], np.float32),
        )
    payload = {
        "schema": "smart-tga-number-map-family-probe-v1", "cycle": 714,
        "validation": "nested leave-one-paint-out selection and evaluation; all preprocessing refit inside each fold",
        "dataset_count": len(datasets), "embedding_encoder": embedding_encoder,
        "reviewed_family_count": len(families),
        "reviewed_paint_count": len(set(groups)),
        "truth_number_families": int(np.count_nonzero(truth)),
        "truth_hard_negative_families": int(np.count_nonzero(~truth)),
        "accepted_map_family_baseline": baseline, "variants": variants,
        "selected_variant": selected_name, "promotable_shadow_model": promotable,
        "model_output": str(model_output).replace("\\", "/") if promotable else None,
        "feature_contract": "intrinsic shape/palette/texture/map stability + D4/CLIP appearance + caller-supplied normalized template-block corroboration; no filename/car/absolute position",
        "casts_votes": False, "ownership_authority": False,
        "exact_reconstruction_impact": "none", "default_runtime_changed": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--active-pool", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--segment-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--extra-dataset-manifest", type=Path, action="append", default=[])
    parser.add_argument("--embedding-encoder", choices=("efficientnet", "clip"), default="efficientnet")
    parser.add_argument("--panel-map", type=Path)
    args = parser.parse_args()
    payload = run(
        args.inspection, args.active_pool, args.reviews, args.segment_model,
        args.output, args.model_output, args.extra_dataset_manifest, args.embedding_encoder,
        args.panel_map,
    )
    print(json.dumps({
        "baseline": payload["accepted_map_family_baseline"],
        "variants": {key: value["nested_paint_disjoint"] for key, value in payload["variants"].items()},
        "promotable_shadow_model": payload["promotable_shadow_model"],
    }, indent=2))


if __name__ == "__main__":
    main()
