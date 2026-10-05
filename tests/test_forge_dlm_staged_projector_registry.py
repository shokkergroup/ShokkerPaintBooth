import copy
from pathlib import Path

import numpy as np
import pytest

from _forge_dlm_staged_projector_registry import PASS_STATUS, ProjectorRegistryError, build, canonical_board


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_staged_projector_registry" / "run141_job.json"


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return build(JOB, tmp_path_factory.mktemp("run141"))


def test_passes_only_the_eight_proved_canonical_projectors(result):
    report = result["report"]
    assert report["valid"] is True
    assert report["status"] == PASS_STATUS
    assert report["metrics"]["projector_ready_surface_count"] == 8
    assert report["metrics"]["abstaining_surface_count"] == 10
    assert report["metrics"]["exact_projected_pixel_count"] == 739912


def test_partial_claims_remain_fail_closed(result):
    claims = result["report"]["claims"]
    assert claims["canonical_eight_surface_projector"] is True
    assert all(value is False for key, value in claims.items() if key != "canonical_eight_surface_projector")


def test_every_registered_transform_is_positive_and_masked(result):
    rows = result["report"]["surface_projectors"]
    assert len(rows) == 8
    assert all(row["homography_determinant"] > 0 for row in rows)
    assert all(row["canonical_projector_ready"] for row in rows)
    assert all(not row["physical_readable_direction_validated"] for row in rows)
    assert sum(row["exact_mask_pixels"] for row in rows) == 739912
    assert np.count_nonzero(result["projection"][..., 3]) == 739912
    assert result["canonical_index"].shape == (1500, 3000)
    assert np.count_nonzero(result["canonical_index"]) > 0


def test_coordinate_board_is_asymmetric_and_opaque():
    board = canonical_board((3000, 1500))
    assert board.shape == (1500, 3000, 4)
    assert np.all(board[..., 3] == 255)
    assert not np.array_equal(board[100, 100], board[100, 2900])
    assert not np.array_equal(board[100, 100], board[1400, 100])


def test_source_hash_drift_fails_closed(tmp_path):
    job = copy.deepcopy(__import__("json").loads(JOB.read_text(encoding="utf-8")))
    for source in job["sources"].values():
        source["path"] = str((JOB.parent / source["path"]).resolve())
    job["sources"]["exact_index"]["sha256"] = "0" * 64
    bad = tmp_path / "bad.json"
    bad.write_text(__import__("json").dumps(job), encoding="utf-8")
    with pytest.raises(ProjectorRegistryError, match="source_hash_drift"):
        build(bad, tmp_path / "out")
