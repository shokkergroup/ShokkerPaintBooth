from __future__ import annotations

import json
from pathlib import Path

import pytest

from _forge_dlm_chiral_decode_gate import ChiralDecodeError, build


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_chiral_decode_gate" / "run133_job.json"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return build(JOB, tmp_path_factory.mktemp("run133"))


def _scenarios(built: dict) -> dict[str, dict]:
    return {row["scenario"]: row for row in built["synthetic"]["scenarios"]}


def test_live_core4_stays_fail_closed_without_run132_identity_roles(built: dict) -> None:
    report = built["report"]
    assert report["status"] == "DENSE_CHIRAL_DECODE_ABSTAIN"
    assert report["counts"] == {
        "role_count": 10,
        "identity_accepted_role_count": 0,
        "dense_decode_accepted_role_count": 0,
        "dense_decode_abstained_role_count": 10,
    }
    assert all(row["accepted"] is False for row in report["role_results"])
    assert all("CHIRAL_DECODE_REQUIRES_RUN132_IDENTITY_ACCEPTANCE" in row["reasons"] for row in report["role_results"])
    assert all(row["projector_allowed"] is False and row["psd_allowed"] is False for row in report["core4_release_status"])


def test_clean_hash_bound_codec_decodes_every_sample_exactly(built: dict) -> None:
    clean = _scenarios(built)["correct_stack"]
    assert clean["accepted"] is True
    assert clean["sample_count"] == 1024
    assert clean["decoded_sample_count"] == 1024
    assert clean["decoded_fraction"] == 1.0
    assert clean["exact_native_fraction"] == 1.0
    assert clean["maximum_orientation_residual"] < 0.003


def test_axis_family_swap_rejects_dense_decode(built: dict) -> None:
    swapped = _scenarios(built)["axis_family_swap"]
    assert swapped["accepted"] is False
    assert swapped["decoded_fraction"] < 0.02
    assert swapped["exact_native_fraction"] == 0.0
    assert "CHIRAL_DECODE_DENSE_COVERAGE_TOO_LOW" in swapped["reasons"]


def test_each_native_coordinate_reflection_rejects(built: dict) -> None:
    scenarios = _scenarios(built)
    for name in ("u_coordinate_reflection", "v_coordinate_reflection"):
        row = scenarios[name]
        assert row["accepted"] is False
        assert row["decoded_fraction"] < 0.02
        assert row["exact_native_fraction"] == 0.0


def test_chiral_signal_reflection_rejects_whole_stack(built: dict) -> None:
    reflected = _scenarios(built)["chiral_signal_reflection"]
    assert reflected["accepted"] is False
    assert reflected["decoded_fraction"] < 0.10
    assert reflected["exact_native_fraction"] < 0.10
    assert "ABSTAIN_ORIENTATION_PASS_INCONSISTENT" in reflected["status_histogram"]


def test_downstream_claims_remain_false(built: dict) -> None:
    claims = built["report"]["claims"]
    assert claims["synthetic_native_uv_decode"] is True
    for key in ("live_native_uv_decode", "physical_surface_ownership", "physical_side_polarity", "readable_direction", "stored_orientation", "projector", "psd", "delivery", "app", "fidelity_95"):
        assert claims[key] is False


def test_bound_run132_hash_tamper_rejects(tmp_path: Path) -> None:
    job = json.loads(JOB.read_text(encoding="utf-8"))
    job["sources"]["run132_report"]["sha256"] = "0" * 64
    path = tmp_path / "tampered_job.json"
    path.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(ChiralDecodeError, match="run132_report_sha256_mismatch"):
        build(path, tmp_path / "out")


def test_reusable_decoder_has_no_livery_identity_literals() -> None:
    source = (ROOT / "_forge_dlm_chiral_decode_gate.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "dominos", "crystal_lake", "sex_wax"):
        assert forbidden not in source
