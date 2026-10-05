"""Focused contract tests for exact-pair transactional iRacing deployment."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import threading

from PIL import Image
import pytest

from server_routes.iracing_pair_deploy import PairDeploymentError, deploy_iracing_tga_pair


TEST_SIZE = (12, 12)
IRACING_ID = "23371"


def _write_tga(path: Path, color: tuple[int, int, int], size=TEST_SIZE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format="TGA")


def _make_pair(root: Path, paint_color, spec_color, *, prefix="car_num") -> tuple[Path, Path]:
    paint = root / f"{prefix}_{IRACING_ID}.tga"
    spec = root / f"car_spec_{IRACING_ID}.tga"
    _write_tga(paint, paint_color)
    _write_tga(spec, spec_color)
    return paint, spec


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pair_hashes(paths: tuple[Path, Path]) -> tuple[str, str]:
    return _hash(paths[0]), _hash(paths[1])


def _private_artifacts(target: Path) -> list[Path]:
    return list(target.glob(".spb-pair-*"))


def test_success_commits_and_verifies_exact_expected_pair(tmp_path):
    source = _make_pair(tmp_path / "source", (10, 20, 30), (40, 50, 60))
    target = tmp_path / "target"

    result = deploy_iracing_tga_pair(
        *source,
        target,
        IRACING_ID,
        expected_dimensions=TEST_SIZE,
    )

    live = (target / source[0].name, target / source[1].name)
    assert result["success"] is True
    assert result["verified"] is True
    assert result["deployed"] == [source[0].name, source[1].name]
    assert _pair_hashes(live) == _pair_hashes(source)
    assert {row["name"] for row in result["files"]} == {source[0].name, source[1].name}
    assert all(row["width"] == TEST_SIZE[0] for row in result["files"])
    assert all(row["height"] == TEST_SIZE[1] for row in result["files"])
    assert not _private_artifacts(target)


def test_first_existing_pair_is_preserved_as_original_and_never_overwritten(tmp_path):
    first_source = _make_pair(tmp_path / "first", (10, 20, 30), (40, 50, 60))
    second_source = _make_pair(tmp_path / "second", (110, 120, 130), (140, 150, 160))
    target = tmp_path / "target"
    live = _make_pair(target, (1, 2, 3), (4, 5, 6))
    original_hashes = _pair_hashes(live)
    preserved = (target / f"ORIGINAL_{live[0].name}", target / f"ORIGINAL_{live[1].name}")
    for path in preserved:
        path.unlink(missing_ok=True)

    deploy_iracing_tga_pair(*first_source, target, IRACING_ID, expected_dimensions=TEST_SIZE)
    assert _pair_hashes(preserved) == original_hashes

    deploy_iracing_tga_pair(*second_source, target, IRACING_ID, expected_dimensions=TEST_SIZE)
    assert _pair_hashes(preserved) == original_hashes
    assert _pair_hashes(live) == _pair_hashes(second_source)
    assert not _private_artifacts(target)


@pytest.mark.parametrize(
    "fault_step",
    [
        "before_stage",
        "after_stage_verified",
        "after_rollback_copies",
        "after_paint_commit",
        "after_spec_commit",
        "after_pair_verified",
    ],
)
def test_fault_injection_always_restores_wholly_old_pair(tmp_path, fault_step):
    old = _make_pair(tmp_path / "old", (1, 2, 3), (4, 5, 6))
    new = _make_pair(tmp_path / "new", (101, 102, 103), (104, 105, 106))
    target = tmp_path / "target"
    live = _make_pair(target, (1, 2, 3), (4, 5, 6))
    old_hashes = _pair_hashes(old)
    assert _pair_hashes(live) == old_hashes

    def inject(step, _context):
        if step == fault_step:
            raise OSError(f"injected failure at {step}")

    with pytest.raises(PairDeploymentError) as captured:
        deploy_iracing_tga_pair(
            *new,
            target,
            IRACING_ID,
            expected_dimensions=TEST_SIZE,
            fault_injector=inject,
        )

    assert captured.value.code in {"staging_failed", "commit_failed_rolled_back"}
    assert _pair_hashes(live) == old_hashes
    assert not _private_artifacts(target)


def test_commit_failure_removes_new_pair_when_target_was_empty(tmp_path):
    source = _make_pair(tmp_path / "source", (22, 33, 44), (55, 66, 77))
    target = tmp_path / "empty-target"

    def fail_after_first_replace(step, _context):
        if step == "after_paint_commit":
            raise PermissionError("simulated locked spec target")

    with pytest.raises(PairDeploymentError) as captured:
        deploy_iracing_tga_pair(
            *source,
            target,
            IRACING_ID,
            expected_dimensions=TEST_SIZE,
            fault_injector=fail_after_first_replace,
        )

    assert captured.value.code == "commit_failed_rolled_back"
    assert not (target / source[0].name).exists()
    assert not (target / source[1].name).exists()
    assert not _private_artifacts(target)


def test_wrong_size_or_wrong_identity_is_rejected_before_target_mutation(tmp_path):
    source = _make_pair(tmp_path / "source", (11, 12, 13), (14, 15, 16))
    target = tmp_path / "target"
    live = _make_pair(target, (1, 1, 1), (2, 2, 2))
    original = _pair_hashes(live)
    _write_tga(source[1], (99, 99, 99), size=(8, 8))

    with pytest.raises(PairDeploymentError) as dimensions_error:
        deploy_iracing_tga_pair(
            *source,
            target,
            IRACING_ID,
            expected_dimensions=TEST_SIZE,
        )
    assert dimensions_error.value.code == "invalid_dimensions"
    assert _pair_hashes(live) == original

    wrong_name = source[0].with_name("some_other_paint.tga")
    _write_tga(wrong_name, (10, 20, 30))
    with pytest.raises(PairDeploymentError) as name_error:
        deploy_iracing_tga_pair(
            wrong_name,
            source[1],
            target,
            IRACING_ID,
            expected_dimensions=(8, 8),
        )
    assert name_error.value.code == "unexpected_source_name"
    assert _pair_hashes(live) == original
    assert not _private_artifacts(target)


def test_concurrent_writers_serialize_and_finish_on_one_complete_winning_pair(tmp_path):
    target = tmp_path / "same-target"
    live = _make_pair(target, (1, 1, 1), (2, 2, 2))
    sources = [
        _make_pair(tmp_path / f"source-{index}", (index, 10, 20), (30, index, 40))
        for index in range(10, 18)
    ]
    candidates = {_pair_hashes(pair) for pair in sources}
    start = threading.Barrier(len(sources))

    def deploy(pair):
        start.wait(timeout=5)
        result = deploy_iracing_tga_pair(
            *pair,
            target,
            IRACING_ID,
            expected_dimensions=TEST_SIZE,
        )
        return result["transaction_id"]

    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        transaction_ids = list(pool.map(deploy, sources))

    assert len(set(transaction_ids)) == len(sources)
    assert _pair_hashes(live) in candidates
    assert not _private_artifacts(target)


def test_concurrent_failed_and_successful_writers_never_leave_a_mixed_pair(tmp_path):
    target = tmp_path / "same-target"
    live = _make_pair(target, (1, 1, 1), (2, 2, 2))
    winner = _make_pair(tmp_path / "winner", (70, 80, 90), (100, 110, 120))
    loser = _make_pair(tmp_path / "loser", (170, 180, 190), (200, 210, 220))
    start = threading.Barrier(2)

    def successful_writer():
        start.wait(timeout=5)
        return deploy_iracing_tga_pair(
            *winner,
            target,
            IRACING_ID,
            expected_dimensions=TEST_SIZE,
        )

    def failing_writer():
        start.wait(timeout=5)

        def inject(step, _context):
            if step == "after_paint_commit":
                raise OSError("injected concurrent commit failure")

        with pytest.raises(PairDeploymentError):
            deploy_iracing_tga_pair(
                *loser,
                target,
                IRACING_ID,
                expected_dimensions=TEST_SIZE,
                fault_injector=inject,
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(successful_writer), pool.submit(failing_writer)]
        for future in futures:
            future.result(timeout=10)

    # The successful writer must win regardless of whether it runs before or
    # after the failed writer; the failed transaction restores its snapshot.
    assert _pair_hashes(live) == _pair_hashes(winner)
    assert not _private_artifacts(target)
