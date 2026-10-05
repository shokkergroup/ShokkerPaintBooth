import hashlib
from pathlib import Path

import numpy as np
import pytest

from _forge_dlm_official_label_anchors import (
    REQUIRED_CLAIMS,
    assign_anchor_components,
    json_sha256,
    verify_file,
)


RULES = {
    "alpha_threshold": 0,
    "max_nearest_distance_px": 5.0,
    "minimum_nearest_margin_px": 2.0,
    "maximum_layer_bbox_fraction": 0.25,
    "maximum_layer_alpha_fraction": 0.10,
    "allowed_layer_kinds": ["type"],
}


def _fixture():
    labels = np.zeros((32, 40), dtype=np.uint16)
    labels[6:12, 3:9] = 1
    labels[6:12, 25:31] = 2
    return labels


def test_exact_touch_preserves_each_touched_component():
    labels = _fixture()
    alpha = np.zeros_like(labels, dtype=np.uint8)
    alpha[8:10, 7:27] = 255
    result = assign_anchor_components(alpha, labels, RULES)
    assert result["status"] == "SEED_ANCHOR"
    assert result["method"] == "exact_touch"
    assert [item["label_value"] for item in result["components"]] == [1, 2]
    assert [item["touch_pixel_count"] for item in result["components"]] == [4, 4]


def test_unique_nearest_obeys_distance_and_margin():
    labels = _fixture()
    alpha = np.zeros_like(labels, dtype=np.uint8)
    alpha[8:10, 10:12] = 255
    result = assign_anchor_components(alpha, labels, RULES)
    assert result["status"] == "SEED_ANCHOR"
    assert result["method"] == "unique_nearest"
    assert result["components"] == [{"label_value": 1, "touch_pixel_count": 0}]
    assert result["nearest_distance_px"] == 2.0


def test_ambiguous_nearest_abstains():
    labels = np.zeros((24, 24), dtype=np.uint16)
    labels[8:12, 3:7] = 1
    labels[8:12, 17:21] = 2
    alpha = np.zeros_like(labels, dtype=np.uint8)
    alpha[9:11, 11:13] = 255
    rules = {**RULES, "max_nearest_distance_px": 6.0, "minimum_nearest_margin_px": 2.0}
    result = assign_anchor_components(alpha, labels, rules)
    assert result["status"] == "ABSTAIN"
    assert result["reason"] == "nearest_component_ambiguous"
    assert result["components"] == []


def test_missing_and_hash_mismatch_fail_closed(tmp_path: Path):
    owner = tmp_path / "job.json"
    owner.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="sample_file_missing"):
        verify_file(owner, {"path": "missing.bin", "sha256": "0" * 64}, "sample")
    source = tmp_path / "source.bin"
    source.write_bytes(b"official")
    with pytest.raises(ValueError, match="sample_sha256_mismatch"):
        verify_file(owner, {"path": source.name, "sha256": "0" * 64}, "sample")
    correct = hashlib.sha256(source.read_bytes()).hexdigest()
    assert verify_file(owner, {"path": source.name, "sha256": correct}, "sample") == source


def test_deterministic_resolution_and_proof_hash():
    labels = _fixture()
    alpha = np.zeros_like(labels, dtype=np.uint8)
    alpha[8:10, 10:12] = 255
    first = assign_anchor_components(alpha, labels, RULES)
    second = assign_anchor_components(alpha.copy(), labels.copy(), dict(reversed(list(RULES.items()))))
    assert first == second
    assert json_sha256({"result": first, "claims": REQUIRED_CLAIMS}) == json_sha256(
        {"claims": REQUIRED_CLAIMS, "result": second}
    )


def test_empty_alpha_abstains():
    labels = _fixture()
    result = assign_anchor_components(np.zeros_like(labels, dtype=np.uint8), labels, RULES)
    assert result["status"] == "ABSTAIN"
    assert result["reason"] == "empty_layer_alpha"


def test_seed_claims_explicitly_forbid_promotion():
    assert REQUIRED_CLAIMS == {
        "seed_anchors_only": True,
        "dense_uv_mapping": False,
        "whole_surface_ownership": False,
        "livery_reconstruction": False,
        "psd_ready": False,
        "delivery_ready": False,
    }
