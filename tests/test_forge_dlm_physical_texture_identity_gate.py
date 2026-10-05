from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

import _forge_dlm_physical_texture_identity_gate as gate


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_physical_texture_identity_gate" / "run132_job.json"


def _isolated_job(tmp_path: Path) -> Path:
    job = json.loads(JOB.read_text(encoding="utf-8"))
    for record in job["sources"].values():
        record["path"] = str((JOB.parent / record["path"]).resolve())
    path = tmp_path / f"run132_{uuid.uuid4().hex}.json"
    path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    root = tmp_path_factory.mktemp("run132_identity")
    return gate.build(_isolated_job(root), root / "out")


def test_live_build_abstains_with_zero_routed_rendered_signals(built: dict[str, object]) -> None:
    report = built["report"]
    assert report["counts"] == {
        "role_count": 10,
        "expected_source_texture_count": 90,
        "routed_source_texture_count": 0,
        "accepted_identity_role_count": 0,
        "abstained_identity_role_count": 10,
    }
    assert report["expected_asset_order"] == list(gate.EXPECTED_ASSETS)
    assert all(row["psd_allowed"] is False for row in report["core4_release_status"])
    assert report["claims"]["absolute_axis_polarity"] is False
    assert report["claims"]["psd"] is False


def test_correct_rendered_signal_stack_passes_in_band_identity(built: dict[str, object]) -> None:
    scenarios = {row["scenario"]: row for row in built["rehearsal"]["scenarios"]}
    correct = scenarios["correct_stack"]
    assert correct["accepted"] is True
    metrics = correct["metrics"]
    assert metrics["responsive_fraction"] > 0.50
    assert metrics["control_luma_span"] > 0.50
    assert metrics["axis_family_angle_separation_degrees"] > 70.0
    assert min(metrics["axis_families"]["u"]["adjacent_energy_ratios"]) > 1.5
    assert min(metrics["axis_families"]["v"]["adjacent_energy_ratios"]) > 1.5
    assert metrics["minimum_signal_pair_mae"] > 0.05


def test_frequency_misroute_rejects_coarse_to_fine_order(built: dict[str, object]) -> None:
    scenarios = {row["scenario"]: row for row in built["rehearsal"]["scenarios"]}
    row = scenarios["u_frequency_misroute"]
    assert row["accepted"] is False
    assert "PHASE_U_FREQUENCY_ORDER_INVALID" in row["metrics"]["reasons"]
    assert "PHASE_U_FREQUENCY_RATIO_WEAK" in row["metrics"]["reasons"]


def test_signal_replay_and_control_swap_fail_closed(built: dict[str, object]) -> None:
    scenarios = {row["scenario"]: row for row in built["rehearsal"]["scenarios"]}
    replay = scenarios["signal_replay"]
    assert replay["accepted"] is False
    assert "SIGNAL_ASSET_REPLAY" in replay["metrics"]["reasons"]
    assert "SIGNAL_ASSETS_NOT_DISTINCT" in replay["metrics"]["reasons"]
    control = scenarios["control_swap"]
    assert control["accepted"] is False
    assert "CONTROL_LUMA_ORDER_INVALID" in control["metrics"]["reasons"]


def test_live_roles_require_pair_bookend_and_nine_signal_evidence(built: dict[str, object]) -> None:
    for row in built["report"]["role_results"]:
        assert row["accepted"] is False
        assert row["routed_source_texture_count"] == 0
        assert row["reasons"] == [
            "IDENTITY_ROLE_REQUIRES_ELEVEN_ACCEPTED_WIRE_PAIRS",
            "IDENTITY_ROLE_REQUIRES_BOOKEND_ACCEPTANCE",
            "IDENTITY_ROLE_REQUIRES_NINE_ROUTED_SOURCE_TEXTURES",
        ]


def test_source_tamper_and_livery_identity_branching_are_rejected() -> None:
    record = json.loads(JOB.read_text(encoding="utf-8"))["sources"]["run131_drift_report"].copy()
    record["sha256"] = "0" * 64
    with pytest.raises(gate.TextureIdentityError, match="run131_drift_report_sha256_mismatch"):
        gate._load_bound(JOB, record, "run131_drift_report")
    source = (ROOT / "_forge_dlm_physical_texture_identity_gate.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "sex wax", "sponsor", "car_name"):
        assert forbidden not in source
