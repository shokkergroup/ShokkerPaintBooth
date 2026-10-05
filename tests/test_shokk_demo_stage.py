from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import uuid

import numpy as np
import pytest

from demo import build_demo_stage as stage


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture_repo(tmp_path: Path) -> tuple[Path, Path, bytes]:
    repo = tmp_path / f"fixture-repo-{uuid.uuid4().hex}"
    backend = repo / "demo" / "backend"
    frontend = repo / "demo" / "frontend"
    backend.mkdir(parents=True)
    frontend.mkdir(parents=True)
    shutil.copy2(PROJECT_ROOT / "demo" / "product-manifest.json", repo / "demo" / "product-manifest.json")
    for relative in stage.BACKEND_FILES:
        target = backend / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# test fixture\n", encoding="utf-8")
    for relative in stage.FRONTEND_FILES:
        target = frontend / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"fixture {relative}\n", encoding="utf-8")
    thumbnails = backend / "assets" / "thumbnails"
    thumbnails.mkdir(parents=True)
    for finish_id in stage.RENDERABLE_FINISH_IDS:
        (thumbnails / f"{finish_id}.png").write_bytes(b"synthetic-thumbnail")
    starter_data = b"8BPS\x00\x01synthetic-test-only"
    starter = repo / "fixture" / stage.STARTER_FILENAME
    starter.parent.mkdir(parents=True)
    starter.write_bytes(starter_data)
    return repo, starter, starter_data


def test_manifest_is_exact_reviewed_demo_contract():
    manifest = json.loads((PROJECT_ROOT / "demo" / "product-manifest.json").read_text(encoding="utf-8"))
    stage.validate_manifest(manifest)
    assert len(stage.VISIBLE_FINISH_IDS) == 29
    assert stage.RENDERABLE_FINISH_IDS[-1] == "fs_core_emerald"
    assert len(stage.RENDERABLE_FINISH_IDS) == 30


def test_portable_dependency_copy_prunes_tests_docs_and_bytecode(tmp_path: Path):
    case = tmp_path / uuid.uuid4().hex
    source = case / "package"
    destination = case / "stage-package"
    (source / "tests").mkdir(parents=True)
    (source / "docs").mkdir()
    (source / "runtime").mkdir()
    (source / "tests" / "test_example.py").write_text("fail\n", encoding="utf-8")
    (source / "docs" / "guide.rst").write_text("guide\n", encoding="utf-8")
    (source / "README.md").write_text("readme\n", encoding="utf-8")
    (source / "LICENSE.md").write_text("license\n", encoding="utf-8")
    (source / "cached.pyc").write_bytes(b"bytecode")
    (source / "testing.py").write_text("runtime helper\n", encoding="utf-8")
    (source / "runtime" / "module.py").write_text("value = 1\n", encoding="utf-8")

    stage._copy_tree_allowlisted(source, destination)

    assert (destination / "testing.py").is_file()
    assert (destination / "runtime" / "module.py").is_file()
    assert (destination / "LICENSE.md").is_file()
    assert not (destination / "tests").exists()
    assert not (destination / "docs").exists()
    assert not (destination / "README.md").exists()
    assert not (destination / "cached.pyc").exists()


def test_output_guard_accepts_only_fixed_release_target(tmp_path: Path):
    repo = tmp_path / "repo"
    expected = repo / "electron-demo" / ".stage"
    assert stage.validate_output_path(repo, expected, test_mode=False) == expected.resolve()
    with pytest.raises(stage.StageBuildError, match="exactly"):
        stage.validate_output_path(repo, repo / "somewhere-else", test_mode=False)
    with pytest.raises(stage.StageBuildError, match="may not replace"):
        stage.validate_output_path(
            stage.DEFAULT_REPO_ROOT,
            stage.DEFAULT_OUTPUT,
            test_mode=True,
        )


def test_stage_build_is_allowlisted_hashed_and_test_marked(tmp_path: Path):
    repo, starter, starter_data = _fixture_repo(tmp_path)
    output = repo / "electron-demo" / ".stage"
    inventory_path = stage.build_stage(
        repo_root=repo,
        output=output,
        test_mode=True,
        synthetic_snapshots=True,
        skip_python=True,
        starter_source=starter,
        starter_sha256=_sha(starter_data),
        starter_size=len(starter_data),
    )

    server = output / "server"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert inventory["schema"] == "spb-demo-stage-inventory/1"
    assert inventory["test_build"] is True
    assert inventory["inventory_self_excluded"] is True
    assert len(inventory["renderable_finish_ids"]) == 30
    assert len(list((server / "assets" / "snapshots").glob("*.npz"))) == 30
    assert set(path.name for path in (server / "assets" / "thumbnails").glob("*.png")) == {
        f"{finish_id}.png" for finish_id in stage.RENDERABLE_FINISH_IDS
    }
    assert (server / "assets" / "starter" / stage.STARTER_FILENAME).read_bytes() == starter_data
    assert not (server / "backend" / "build_snapshots.py").exists()
    assert not (server / "python").exists()

    indexed = {item["path"]: item for item in inventory["files"]}
    assert "inventory.json" not in indexed
    assert "demo_server.py" in indexed
    assert "backend/app.py" in indexed
    assert "frontend/js/app.js" in indexed
    assert "frontend/js/preview-interactions.js" in indexed
    assert "frontend/assets/branding/spb-splash-intro.mp4" in indexed
    assert indexed["product-manifest.json"]["sha256"] == stage.sha256_file(
        server / "product-manifest.json"
    )
    assert set(path.name for path in (server / "assets" / "snapshots").glob("*.npz")) == {
        f"{finish_id}.npz" for finish_id in stage.RENDERABLE_FINISH_IDS
    }


def test_stage_rejects_paid_import_even_when_filename_is_in_allowlist(tmp_path: Path):
    repo, starter, starter_data = _fixture_repo(tmp_path)
    output = repo / "electron-demo" / ".stage"
    stage.build_stage(
        repo_root=repo,
        output=output,
        test_mode=True,
        synthetic_snapshots=True,
        skip_python=True,
        starter_source=starter,
        starter_sha256=_sha(starter_data),
        starter_size=len(starter_data),
    )
    app_path = output / "server" / "backend" / "app.py"
    app_path.write_text("import shokker_engine_v2\n", encoding="utf-8")
    with pytest.raises(stage.StageBuildError, match="Forbidden paid/runtime import"):
        stage.validate_stage_tree(output / "server", test_python_omitted=True)


def test_stage_rejects_any_unexpected_top_level_file(tmp_path: Path):
    repo, starter, starter_data = _fixture_repo(tmp_path)
    output = repo / "electron-demo" / ".stage"
    stage.build_stage(
        repo_root=repo,
        output=output,
        test_mode=True,
        synthetic_snapshots=True,
        skip_python=True,
        starter_source=starter,
        starter_sha256=_sha(starter_data),
        starter_size=len(starter_data),
    )
    (output / "server" / "surprise.txt").write_text("not allowlisted", encoding="utf-8")
    with pytest.raises(stage.StageBuildError, match="unexpected=.*surprise.txt"):
        stage.validate_stage_tree(output / "server", test_python_omitted=True)


def test_stage_rejects_unresolved_local_frontend_module_import(tmp_path: Path):
    frontend = tmp_path / "frontend"
    (frontend / "js").mkdir(parents=True, exist_ok=True)
    (frontend / "js" / "app.js").write_text(
        "import { helper } from './missing-helper.js?v=release';\nhelper();\n",
        encoding="utf-8",
    )

    with pytest.raises(stage.StageBuildError, match="frontend module is missing"):
        stage.validate_frontend_module_closure(frontend)


def test_snapshot_validator_checks_identity_schema_shape_and_dtype(tmp_path: Path):
    good = tmp_path / "good.npz"
    data = np.zeros((8, 8, 3), dtype=np.uint8)
    np.savez_compressed(
        good,
        schema=np.array(stage.SNAPSHOT_SCHEMA),
        finish_id=np.array("f_chrome"),
        build_size=np.array([8, 8], dtype=np.int32),
        seed=np.array(51, dtype=np.int32),
        paint=data,
        spec=data,
    )
    stage.validate_snapshot(good, "f_chrome", expected_size=8)

    wrong = tmp_path / "wrong.npz"
    np.savez_compressed(
        wrong,
        schema=np.array(stage.SNAPSHOT_SCHEMA),
        finish_id=np.array("gloss"),
        build_size=np.array([8, 8], dtype=np.int32),
        seed=np.array(51, dtype=np.int32),
        paint=data,
        spec=data,
    )
    with pytest.raises(stage.StageBuildError, match="identity/schema"):
        stage.validate_snapshot(wrong, "f_chrome", expected_size=8)


def test_portable_python_copy_uses_only_explicit_allowlists(tmp_path: Path):
    unique = uuid.uuid4().hex
    repo = tmp_path / f"repo-{unique}"
    source = repo / "electron-app" / "server" / "python"
    for filename in stage.PYTHON_ROOT_FILES:
        target = source / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"runtime")
    site = source / "Lib" / "site-packages"
    for package in stage.PYTHON_SITE_PACKAGES:
        target = site / package
        if Path(package).suffix == ".py":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# dependency\n", encoding="utf-8")
        else:
            target.mkdir(parents=True, exist_ok=True)
            (target / "payload.txt").write_text("dependency\n", encoding="utf-8")
            (target / "__pycache__").mkdir()
            (target / "__pycache__" / "ignored.pyc").write_bytes(b"cache")
    (source / "ReShade.log").write_text("must not ship", encoding="utf-8")
    (site / "paid_registry.py").write_text("must not ship", encoding="utf-8")

    destination = tmp_path / f"destination-{unique}"
    stage.copy_portable_python(repo, destination)
    assert (destination / "python" / "python.exe").is_file()
    assert (destination / "python" / "Lib" / "site-packages" / "flask" / "payload.txt").is_file()
    assert not (destination / "python" / "ReShade.log").exists()
    assert not (destination / "python" / "Lib" / "site-packages" / "paid_registry.py").exists()
    assert not list(destination.rglob("*.pyc"))


def test_cli_test_switches_require_explicit_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("SHOKK_DEMO_STAGE_TEST_MODE", raising=False)
    result = stage.main(
        [
            "--output",
            str(tmp_path / ".stage"),
            "--test-synthetic-snapshots",
            "--test-skip-python",
        ]
    )
    assert result == 2


def test_electron_stage_never_enables_test_artifacts():
    source = (PROJECT_ROOT / "electron-demo" / "stage.js").read_text(encoding="utf-8")
    assert "--test-synthetic-snapshots" not in source
    assert "--test-skip-python" not in source
