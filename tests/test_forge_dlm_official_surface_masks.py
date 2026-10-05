from pathlib import Path

import numpy as np

from _forge_dlm_official_surface_masks import (
    REQUIRED_CLAIMS,
    assess_bound_user_mask,
    sha256_file,
    verify_source,
)


RULES = {
    "allowed_proof_layer_kinds": ["pixel", "group"],
    "mask_threshold": 127,
    "minimum_mask_pixels": 4,
    "maximum_mask_fraction": 0.40,
    "require_explicit_proof_binding": True,
}


def _binding(surface_id="surface_a"):
    return {
        "layer_path": "Paintable Area/Surface A Proof",
        "proof_kind": "user_layer_mask",
        "ownership_surface_id": surface_id,
    }


def test_label_alpha_without_explicit_proof_binding_abstains():
    label_alpha = np.full((16, 16), 255, dtype=np.uint8)
    result = assess_bound_user_mask(
        label_alpha,
        surface_id="surface_a",
        proof_binding=None,
        layer_kind="type",
        has_user_mask=False,
        mask_disabled=False,
        rules=RULES,
    )
    assert result == {"status": "ABSTAIN", "reason": "explicit_proof_binding_missing"}


def test_global_pixel_guide_cannot_substitute_for_bound_user_mask():
    guide_alpha = np.zeros((16, 16), dtype=np.uint8)
    guide_alpha[2:8, 2:8] = 255
    result = assess_bound_user_mask(
        guide_alpha,
        surface_id="surface_a",
        proof_binding=_binding(),
        layer_kind="pixel",
        has_user_mask=False,
        mask_disabled=False,
        rules=RULES,
    )
    assert result["status"] == "ABSTAIN"
    assert result["reason"] == "bound_layer_has_no_user_mask"


def test_explicit_surface_bound_user_mask_is_exact_and_binary():
    mask = np.zeros((20, 24), dtype=np.uint8)
    mask[5:10, 7:13] = 200
    result = assess_bound_user_mask(
        mask,
        surface_id="surface_a",
        proof_binding=_binding(),
        layer_kind="pixel",
        has_user_mask=True,
        mask_disabled=False,
        rules=RULES,
    )
    exact = result.pop("mask")
    assert result["status"] == "EXACT_MASK"
    assert result["pixel_count"] == 30
    assert result["bbox"] == [7, 5, 13, 10]
    assert set(np.unique(exact)) == {0, 255}


def test_surface_mismatch_disabled_and_oversize_masks_fail_closed():
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[2:8, 2:8] = 255
    mismatch = assess_bound_user_mask(
        mask,
        surface_id="surface_a",
        proof_binding=_binding("surface_b"),
        layer_kind="pixel",
        has_user_mask=True,
        mask_disabled=False,
        rules=RULES,
    )
    assert mismatch["reason"] == "proof_binding_surface_mismatch"
    disabled = assess_bound_user_mask(
        mask,
        surface_id="surface_a",
        proof_binding=_binding(),
        layer_kind="pixel",
        has_user_mask=True,
        mask_disabled=True,
        rules=RULES,
    )
    assert disabled["reason"] == "bound_user_mask_disabled"
    oversize = assess_bound_user_mask(
        np.full((20, 20), 255, dtype=np.uint8),
        surface_id="surface_a",
        proof_binding=_binding(),
        layer_kind="pixel",
        has_user_mask=True,
        mask_disabled=False,
        rules=RULES,
    )
    assert oversize["reason"] == "bound_user_mask_oversize"


def test_hash_bound_sources_fail_closed(tmp_path: Path):
    owner = tmp_path / "job.json"
    owner.write_text("{}", encoding="utf-8")
    source = tmp_path / "source.bin"
    source.write_bytes(b"official")
    good = sha256_file(source)
    assert verify_source(owner, {"path": source.name, "sha256": good}, "sample") == source
    try:
        verify_source(owner, {"path": source.name, "sha256": "0" * 64}, "sample")
    except ValueError as exc:
        assert str(exc) == "sample_sha256_mismatch"
    else:
        raise AssertionError("hash mismatch must fail closed")


def test_claim_contract_forbids_promotion():
    assert REQUIRED_CLAIMS == {
        "conservative_proved_masks_only": True,
        "dense_uv_mapping": False,
        "whole_uv_coverage": False,
        "whole_surface_ownership": False,
        "livery_reconstruction": False,
        "psd_ready": False,
        "delivery_ready": False,
    }
