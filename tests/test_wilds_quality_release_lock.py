from __future__ import annotations

import hashlib
import importlib.util
import functools
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest
from PIL import Image, PngImagePlugin

from scripts import spb_wilds_quality_release_lock as gate


SYNTHETIC_IDS = ("fixture_alpha", "fixture_beta")
_REGISTRIES: dict[Path, dict] = {}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _detail(fid: str, kind: str) -> dict:
    common = {"id": fid, "passed": True}
    if kind == "local_feature_scale":
        return {**common, "native_min_px": 8, "native_max_px": 32, "mark_count": 7}
    if kind == "literal_ab":
        return {
            **common, "literal_a": True, "literal_b": True,
            "fractured_flip_pass": True,
        }
    if kind == "separate_m_r_cc":
        return {**common, "channels": ["M", "R", "Cc"], "separate_authorship": True}
    if kind == "motif_spec_collision":
        return {
            **common, "motif_pass": True, "spec_pass": True,
            "whole_app_pass": True,
        }
    if kind == "buyer_96x48":
        return {**common, "width": 96, "height": 48, "topology_readable": True}
    if kind == "m7":
        return {**common, "score": 91.5}
    if kind == "native_2048_perf":
        return {**common, "width": 2048, "height": 2048, "seconds": 2.4}
    raise AssertionError(kind)


def _artifact_payload(fid: str, kind: str) -> dict:
    return {
        "schema": gate.EVIDENCE_SCHEMA,
        "kind": kind,
        **_detail(fid, kind),
    }


def _write_artifact(path: Path, fid: str, kind: str) -> None:
    assertions = _artifact_payload(fid, kind)
    if kind == "buyer_96x48":
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text(
            gate.BUYER_PNG_METADATA_KEY,
            json.dumps(assertions, sort_keys=True),
        )
        color_seed = sum(ord(char) for char in fid)
        Image.new(
            "RGB", (96, 48),
            (31 + color_seed % 173, 47 + color_seed % 151, 59 + color_seed % 137),
        ).save(path, format="PNG", pnginfo=metadata)
    else:
        path.write_text(json.dumps(assertions, indent=2) + "\n", encoding="utf-8")


def _rewrite_json_artifact(
    tmp_path: Path,
    binding: dict,
    **updates: object,
) -> None:
    artifact = tmp_path / binding["path"]
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload.update(updates)
    artifact.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    binding["sha256"] = _sha(artifact)


def _load_fixture_module(source: Path):
    module_name = f"_spb_quality_fixture_{hash(source.resolve()) & 0xffffffff:x}"
    spec = importlib.util.spec_from_file_location(module_name, source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _registry_for(tmp_path: Path) -> dict:
    return _REGISTRIES[tmp_path.resolve()]


def _validate(manifest: Path, expected_ids, *, root: Path):
    return gate.validate_quality_release_manifest(
        manifest,
        expected_ids,
        root=root,
        registry=_registry_for(root),
    )


def _fixture(tmp_path: Path) -> tuple[Path, dict]:
    source = tmp_path / "synthetic_sources.py"
    source.write_text(
        "def alpha_spec(shape, mask, seed, sm):\n"
        "    result = seed + sm\n"
        "    return ('alpha-spec', result, shape, mask)\n\n"
        "def alpha_paint(paint, shape, mask, seed, pm, bb):\n"
        "    result = seed * pm\n"
        "    return ('alpha-paint', result, paint, shape, mask, bb)\n\n"
        "def beta_spec(shape, mask, seed, sm):\n"
        "    result = seed - sm\n"
        "    return ('beta-spec', result, mask, shape)\n\n"
        "def beta_paint(paint, shape, mask, seed, pm, bb):\n"
        "    result = seed / (pm + 1)\n"
        "    return ('beta-paint', result, bb, mask, shape, paint)\n\n"
        "def legacy_spec(shape, mask, seed, sm):\n"
        "    result = seed ** 2\n"
        "    return ('legacy-spec', result, shape, mask, sm)\n\n"
        "def duplicate_alpha_spec(shape, mask, seed, sm):\n"
        "    result = (seed + 17) * sm\n"
        "    return ('duplicate', result, shape, mask)\n\n"
        "def duplicate_beta_spec(shape, mask, seed, sm):\n"
        "    result = (seed + 17) * sm\n"
        "    return ('duplicate', result, shape, mask)\n\n"
        "def shared_composer(tag, shape, mask, seed, sm):\n"
        "    result = seed * 3 + sm\n"
        "    return (tag, result, shape, mask)\n\n"
        "def wrapper_alpha_spec(shape, mask, seed, sm):\n"
        "    return shared_composer('wrapper-alpha', shape, mask, seed, sm)\n\n"
        "def wrapper_beta_spec(shape, mask, seed, sm):\n"
        "    return shared_composer('wrapper-beta', shape, mask, seed, sm)\n\n"
        "def make_closed_spec():\n"
        "    captured = 23\n"
        "    def closed_spec(shape, mask, seed, sm):\n"
        "        return (captured, shape, mask, seed, sm)\n"
        "    return closed_spec\n\n"
        "closed_spec = make_closed_spec()\n"
        "lambda_spec = lambda shape, mask, seed, sm: (shape, mask, seed, sm)\n",
        encoding="utf-8",
    )
    module = _load_fixture_module(source)
    registry = {
        "fixture_alpha": (module.alpha_spec, module.alpha_paint),
        "fixture_beta": (module.beta_spec, module.beta_paint),
    }
    _REGISTRIES[tmp_path.resolve()] = registry
    rows = []
    for fid in SYNTHETIC_IDS:
        evidence = {}
        for kind in gate.REQUIRED_EVIDENCE:
            extension = ".png" if kind == "buyer_96x48" else ".json"
            artifact = tmp_path / "evidence" / f"{fid}__{kind}{extension}"
            artifact.parent.mkdir(exist_ok=True)
            _write_artifact(artifact, fid, kind)
            evidence[kind] = {
                **_detail(fid, kind),
                "path": artifact.relative_to(tmp_path).as_posix(),
                "sha256": _sha(artifact),
            }
        rows.append({
            "id": fid,
            "owner_accepted": True,
            "production_wired": True,
            "registry": {
                "spec": gate.describe_registry_callable(
                    registry[fid][0], root=tmp_path, label=f"{fid}.spec",
                ),
                "paint": gate.describe_registry_callable(
                    registry[fid][1], root=tmp_path, label=f"{fid}.paint",
                ),
            },
            "evidence": evidence,
        })
    payload = {
        "schema": gate.SCHEMA,
        "scope": "fractured_wilds",
        "finishes": rows,
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest, payload


def _write_manifest(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _set_registry_callable(
    tmp_path: Path,
    payload: dict,
    fid: str,
    role: str,
    function,
    *,
    update_binding: bool = True,
) -> None:
    registry = _registry_for(tmp_path)
    spec_fn, paint_fn = registry[fid]
    registry[fid] = (
        function if role == "spec" else spec_fn,
        function if role == "paint" else paint_fn,
    )
    if update_binding:
        row = next(item for item in payload["finishes"] if item["id"] == fid)
        row["registry"][role] = gate.describe_registry_callable(
            function, root=tmp_path, label=f"{fid}.{role}",
        )


def test_synthetic_exact_manifest_opens_quality_lock(tmp_path: Path):
    manifest, _payload = _fixture(tmp_path)
    report = _validate(
        manifest, SYNTHETIC_IDS, root=tmp_path,
    )
    assert report["status"] == "quality_release_lock_open"
    assert report["owner_accepted"] == 2
    assert report["production_wired"] == 2
    assert report["unique_source_bindings"] == 4
    assert report["unique_registry_callable_bindings"] == 4
    assert report["unique_registry_body_fingerprints"] == 4
    assert report["source_paths"] == ["synthetic_sources.py"]
    assert report["unique_evidence_bindings"] == 14
    assert report["decoded_buyer_96x48_artifacts"] == 2
    assert report["m7_minimum"] == 91.5
    assert report["native_2048_seconds_maximum"] == 2.4
    assert report["acceptance_inferred_from_metrics"] is False
    assert report["manifest_sha256"] == _sha(manifest)
    assert len(report["review_bundle_sha256"]) == 64
    assert report["review_bundle_sha256"] == _validate(
        manifest, SYNTHETIC_IDS, root=tmp_path,
    )["review_bundle_sha256"]


def test_missing_manifest_fails_closed_with_zero_acceptance(tmp_path: Path):
    _fixture(tmp_path)
    with pytest.raises(gate.QualityReleaseBlocked, match=r"owner accepted 0/2"):
        _validate(
            tmp_path / "absent.json", SYNTHETIC_IDS, root=tmp_path,
        )


def test_metrics_never_infer_owner_acceptance_or_wiring(tmp_path: Path):
    manifest, payload = _fixture(tmp_path)
    payload["finishes"][0]["evidence"]["m7"]["score"] = 100
    payload["finishes"][0]["evidence"]["native_2048_perf"]["seconds"] = 0.1
    payload["finishes"][0]["owner_accepted"] = False
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match="metrics never confer acceptance"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)

    payload["finishes"][0]["owner_accepted"] = True
    payload["finishes"][0]["production_wired"] = False
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match="contradicts registry"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


def test_duplicate_and_missing_ids_are_rejected(tmp_path: Path):
    manifest, payload = _fixture(tmp_path)
    payload["finishes"][1] = payload["finishes"][0]
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match="duplicate IDs"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)

    manifest, payload = _fixture(tmp_path)
    payload["finishes"].pop()
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match=r"missing=\['fixture_beta'\].*rows=1/2"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


def test_shared_evidence_path_or_content_is_rejected(tmp_path: Path):
    manifest, payload = _fixture(tmp_path)
    alpha = payload["finishes"][0]["evidence"]["local_feature_scale"]
    beta = payload["finishes"][1]["evidence"]["local_feature_scale"]
    beta["path"] = alpha["path"]
    beta["sha256"] = alpha["sha256"]
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match="shared evidence binding"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)

    manifest, payload = _fixture(tmp_path)
    alpha = payload["finishes"][0]["evidence"]["literal_ab"]
    beta = payload["finishes"][1]["evidence"]["literal_ab"]
    beta_path = tmp_path / beta["path"]
    beta_path.write_bytes((tmp_path / alpha["path"]).read_bytes())
    beta["sha256"] = _sha(beta_path)
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match="shared evidence content"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


def test_shared_actual_registry_callable_is_rejected(tmp_path: Path):
    manifest, payload = _fixture(tmp_path)
    registry = _registry_for(tmp_path)
    registry["fixture_beta"] = (
        registry["fixture_alpha"][0],
        registry["fixture_beta"][1],
    )
    payload["finishes"][1]["registry"]["spec"] = payload["finishes"][0]["registry"]["spec"]
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match="shared registry callable object"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


def test_actual_registry_is_mandatory_and_manifest_cannot_self_assert_wiring(tmp_path: Path):
    manifest, _payload = _fixture(tmp_path)
    with pytest.raises(gate.QualityReleaseBlocked, match="actual final registry is required"):
        gate.validate_quality_release_manifest(
            manifest, SYNTHETIC_IDS, root=tmp_path,
        )


def test_manifest_binds_both_actual_registry_callables_and_all_fingerprints(tmp_path: Path):
    manifest, payload = _fixture(tmp_path)
    payload["finishes"][0]["registry"]["spec"]["body_sha256"] = "0" * 64
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match=r"fixture_alpha\.registry\.spec\.body_sha256"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)

    manifest, payload = _fixture(tmp_path)
    payload["finishes"][0]["registry"].pop("paint")
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match="exactly explicit spec and paint"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


def test_registry_rollback_after_owner_review_is_blocked(tmp_path: Path):
    manifest, payload = _fixture(tmp_path)
    registry = _registry_for(tmp_path)
    module = sys.modules[registry["fixture_alpha"][0].__module__]
    reviewed_spec = registry["fixture_alpha"][0]
    _set_registry_callable(
        tmp_path,
        payload,
        "fixture_alpha",
        "spec",
        module.legacy_spec,
        update_binding=False,
    )
    _write_manifest(manifest, payload)
    assert _registry_for(tmp_path)["fixture_alpha"][0] is module.legacy_spec
    assert _registry_for(tmp_path)["fixture_alpha"][0] is not reviewed_spec
    with pytest.raises(gate.QualityReleaseBlocked, match=r"registry\.spec\.qualname"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


def test_identical_normalized_registry_bodies_are_rejected(tmp_path: Path):
    manifest, payload = _fixture(tmp_path)
    registry = _registry_for(tmp_path)
    module = sys.modules[registry["fixture_alpha"][0].__module__]
    _set_registry_callable(
        tmp_path, payload, "fixture_alpha", "spec", module.duplicate_alpha_spec,
    )
    _set_registry_callable(
        tmp_path, payload, "fixture_beta", "spec", module.duplicate_beta_spec,
    )
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match="identical normalized registry body"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


def test_thin_unique_wrappers_cannot_hide_a_shared_composer(tmp_path: Path):
    manifest, payload = _fixture(tmp_path)
    registry = _registry_for(tmp_path)
    module = sys.modules[registry["fixture_alpha"][0].__module__]
    _set_registry_callable(
        tmp_path, payload, "fixture_alpha", "spec", module.wrapper_alpha_spec,
    )
    _set_registry_callable(
        tmp_path, payload, "fixture_beta", "spec", module.wrapper_beta_spec,
    )
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match="shared non-allowlisted composer"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


@pytest.mark.parametrize(
    ("kind", "expected"),
    (
        ("local", "local/factory registry callables are forbidden"),
        ("lambda", "lambda registry callables are forbidden"),
        ("partial", "functools.partial registry callables are forbidden"),
    ),
)
def test_dynamic_registry_callable_forms_are_rejected(
    tmp_path: Path, kind: str, expected: str,
):
    manifest, payload = _fixture(tmp_path)
    registry = _registry_for(tmp_path)
    module = sys.modules[registry["fixture_alpha"][0].__module__]
    replacement = {
        "local": module.closed_spec,
        "lambda": module.lambda_spec,
        "partial": functools.partial(module.alpha_spec, None),
    }[kind]
    _set_registry_callable(
        tmp_path,
        payload,
        "fixture_alpha",
        "spec",
        replacement,
        update_binding=False,
    )
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match=re.escape(expected)):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


def test_claims_only_dummy_artifact_is_rejected(tmp_path: Path):
    manifest, payload = _fixture(tmp_path)
    binding = payload["finishes"][0]["evidence"]["local_feature_scale"]
    artifact = tmp_path / binding["path"]
    artifact.write_text('{"fixture":"claims only"}\n', encoding="utf-8")
    binding["sha256"] = _sha(artifact)
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match="artifact schema"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


def test_artifact_semantics_must_match_manifest_binding(tmp_path: Path):
    manifest, payload = _fixture(tmp_path)
    binding = payload["finishes"][0]["evidence"]["m7"]
    _rewrite_json_artifact(tmp_path, binding, score=92.25)
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match=r"artifact field 'score'.*does not match"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("id", "some_other_finish", "evidence id must bind exactly"),
        ("kind", "literal_ab", "artifact kind must bind exactly"),
        ("passed", False, "passed must be explicit true"),
    ),
)
def test_artifact_common_assertions_are_independently_enforced(
    tmp_path: Path, field: str, value: object, message: str,
):
    manifest, payload = _fixture(tmp_path)
    binding = payload["finishes"][0]["evidence"]["m7"]
    _rewrite_json_artifact(tmp_path, binding, **{field: value})
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match=message):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


def test_buyer_binding_must_decode_a_literal_96x48_png(tmp_path: Path):
    manifest, payload = _fixture(tmp_path)
    binding = payload["finishes"][0]["evidence"]["buyer_96x48"]
    artifact = tmp_path / binding["path"]
    assertions = _artifact_payload("fixture_alpha", "buyer_96x48")
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text(
        gate.BUYER_PNG_METADATA_KEY,
        json.dumps(assertions, sort_keys=True),
    )
    Image.new("RGB", (95, 48), (12, 34, 56)).save(
        artifact, format="PNG", pnginfo=metadata,
    )
    binding["sha256"] = _sha(artifact)
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match=r"decoded buyer PNG is 95x48"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


def test_buyer_binding_rejects_fake_png_or_missing_assertions(tmp_path: Path):
    manifest, payload = _fixture(tmp_path)
    binding = payload["finishes"][0]["evidence"]["buyer_96x48"]
    artifact = tmp_path / binding["path"]
    artifact.write_text("not png pixels", encoding="utf-8")
    binding["sha256"] = _sha(artifact)
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match="cannot be decoded as PNG"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)

    manifest, payload = _fixture(tmp_path)
    binding = payload["finishes"][0]["evidence"]["buyer_96x48"]
    artifact = tmp_path / binding["path"]
    Image.new("RGB", (96, 48), (12, 34, 56)).save(artifact, format="PNG")
    binding["sha256"] = _sha(artifact)
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match="lacks embedded"):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


@pytest.mark.parametrize(
    ("kind", "field", "value", "message"),
    (
        ("m7", "score", 100.001, r"m7\.artifact.*85\.\.100"),
        ("native_2048_perf", "seconds", 0.0, r"native_2048_perf\.artifact.*invalid"),
        ("native_2048_perf", "seconds", 3.001, r"native_2048_perf\.artifact.*exceeds 3s"),
    ),
)
def test_parsed_metric_artifact_values_are_range_checked(
    tmp_path: Path, kind: str, field: str, value: object, message: str,
):
    manifest, payload = _fixture(tmp_path)
    binding = payload["finishes"][0]["evidence"][kind]
    _rewrite_json_artifact(tmp_path, binding, **{field: value})
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match=message):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


@pytest.mark.parametrize(
    ("kind", "field", "value", "message"),
    (
        ("m7", "score", 84.999, "owner ship-bar range 85..100"),
        ("m7", "score", 100.001, "owner ship-bar range 85..100"),
        ("native_2048_perf", "seconds", 0.0, "invalid"),
        ("native_2048_perf", "seconds", 3.001, "exceeds 3s"),
        ("buyer_96x48", "width", 128, "actual 96x48"),
        ("separate_m_r_cc", "separate_authorship", False, "separate M/R/Cc"),
    ),
)
def test_required_evidence_semantics_fail_closed(
    tmp_path: Path, kind: str, field: str, value: object, message: str,
):
    manifest, payload = _fixture(tmp_path)
    payload["finishes"][0]["evidence"][kind][field] = value
    _write_manifest(manifest, payload)
    with pytest.raises(gate.QualityReleaseBlocked, match=message):
        _validate(manifest, SYNTHETIC_IDS, root=tmp_path)


def test_delivery_sync_cli_cannot_green_without_quality_acceptance(
    monkeypatch, capsys,
):
    from scripts import spb_verify_wilds_release_sync as release_sync

    monkeypatch.setattr(
        release_sync, "canonical_wilds_110",
        lambda _registry=None: ({"fixture": list(SYNTHETIC_IDS)}, list(SYNTHETIC_IDS)),
    )
    monkeypatch.setattr(
        release_sync, "verify_exact_two_copy",
        lambda _root, _ids: {
            "ok": True, "wildsCount": 2, "verifiedPairs": 4,
            "expectedPairs": 4, "errors": [],
        },
    )

    def blocked(*_args, **_kwargs):
        raise gate.QualityReleaseBlocked("owner accepted 0/2")

    monkeypatch.setattr(release_sync, "validate_quality_release_manifest", blocked)
    assert release_sync.main([]) == 1
    output = capsys.readouterr().out
    assert "delivery 4/4 exact pairs" in output
    assert "quality_release_blocked" in output
    assert "owner accepted 0/2" in output


def test_packaged_picker_baker_imports_packaged_release_locks():
    """The installer runtime must not depend on root-only release modules."""
    root = Path(__file__).resolve().parents[1]
    packaged = root / "electron-app" / "server"
    code = (
        "from pathlib import Path\n"
        "import rebuild_picker_swatches as baker\n"
        "import scripts.spb_wilds_release_gate as delivery\n"
        "import scripts.spb_wilds_quality_release_lock as quality\n"
        "runtime = Path.cwd().resolve()\n"
        "assert Path(delivery.__file__).resolve().is_relative_to(runtime)\n"
        "assert Path(quality.__file__).resolve().is_relative_to(runtime)\n"
        "assert baker.EXPECTED_WILDS_TOTAL == 110\n"
        "assert baker.DEFAULT_WILDS_QUALITY_MANIFEST == quality.DEFAULT_MANIFEST\n"
    )
    env = os.environ.copy()
    env["SHOKKER_SKIP_PICKER_PREBAKE"] = "1"
    env["SHOKKER_SKIP_SPEC_PREBAKE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=packaged,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_scorecard_write_checks_quality_before_rendering(tmp_path: Path, monkeypatch):
    from scripts import spb_refresh_wilds_shipping_scorecard as scorecard

    scorecard_file = tmp_path / "scorecard.js"
    scorecard_file.write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(scorecard, "SCORECARD", scorecard_file)
    monkeypatch.setattr(scorecard, "_scorecard_parts", lambda: ("", {}, ""))
    monkeypatch.setattr(
        scorecard, "canonical_wilds_110",
        lambda: ({"fixture": list(SYNTHETIC_IDS)}, list(SYNTHETIC_IDS)),
    )
    monkeypatch.setattr(
        scorecard, "_catalog_names",
        lambda: pytest.fail("catalog/render work ran before the quality lock"),
    )

    def blocked(*_args, **_kwargs):
        raise gate.QualityReleaseBlocked("owner accepted 0/2")

    monkeypatch.setattr(scorecard, "validate_quality_release_manifest", blocked)
    with pytest.raises(gate.QualityReleaseBlocked, match="owner accepted 0/2"):
        scorecard.refresh(
            write=True, size=scorecard.AUDIT_SIZE,
            quality_manifest=tmp_path / "absent.json",
        )
