"""Focused regressions for the 2026-08-22 flow/security hardening pass."""

from __future__ import annotations

import ast
import base64
import hashlib
import importlib
import io
import json
import os
import subprocess
import threading
from pathlib import Path

import pytest
from flask import Flask, jsonify, request
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


class _Logger:
    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


def _load_functions(path: Path, *names: str, namespace=None):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list = []
            wanted.append(node)
    assert {node.name for node in wanted} == set(names)
    scope = dict(namespace or {})
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(path), "exec"), scope)
    return [scope[name] for name in names]


def test_shared_rle_decoder_binds_shape_values_and_aggregate_budget():
    (decode,) = _load_functions(ROOT / "server.py", "_decode_rle_mask_payload", namespace={"json": json})
    app = Flask(__name__)
    app.config["SPB_RLE_DECODE_BUDGET_BYTES"] = 16

    with app.test_request_context("/"):
        decoded = decode(
            {"width": 2, "height": 2, "runs": [[255, 4]]},
            "mask",
            expected_shape=(2, 2),
        )
        assert decoded.shape == (2, 2)
        with pytest.raises(ValueError, match="aggregate RLE decode budget"):
            decode({"width": 1, "height": 1, "runs": [[255, 1]]}, "second")

    with pytest.raises(ValueError, match="do not match source"):
        decode({"width": 2, "height": 2, "runs": [[255, 4]]}, "mask", expected_shape=(1, 4))
    with pytest.raises(ValueError, match="field limit"):
        decode({"width": 513, "height": 1, "runs": [[255, 513]]}, "strength", max_shape=(512, 512))
    with pytest.raises(ValueError, match="invalid mask value"):
        decode({"width": 1, "height": 1, "runs": [[float("nan"), 1]]}, "mask")
    with pytest.raises(ValueError, match="RLE run exceeds"):
        decode({"width": 2, "height": 1, "runs": [[255, 0], [0, 2]]}, "mask")

    (decode_rgb,) = _load_functions(
        ROOT / "server.py",
        "_decode_source_layer_rgb_payload",
        namespace={"base64": base64, "io": io},
    )
    png = io.BytesIO()
    Image.new("RGBA", (2, 2), (1, 2, 3, 255)).save(png, "PNG")
    encoded = base64.b64encode(png.getvalue()).decode("ascii")
    with app.test_request_context("/decode-rgb"):
        app.config["SPB_RLE_DECODE_BUDGET_BYTES"] = 16
        assert decode_rgb(encoded, "rgb", expected_shape=(2, 2)).shape == (2, 2, 4)
        with pytest.raises(ValueError, match="do not match source"):
            decode_rgb(encoded, "rgb", expected_shape=(1, 4))


def test_server_release_identity_is_derived_from_config_singleton():
    source = (ROOT / "server.py").read_text(encoding="utf-8")
    config_import = source.index("from config import CFG")
    version_assignment = source.index("SPB_VERSION = str(CFG.VERSION)")
    build_assignment = source.index("SPB_BUILD_ID = str(CFG.BUILD_TAG)")
    assert config_import < version_assignment < build_assignment
    assert 'SPB_VERSION = "8.0.3-beta"' not in source
    assert 'SPB_BUILD_ID = "Spring Catalogue"' not in source


def test_sensitive_reads_require_exact_browser_origin_port():
    from server_routes.request_security import (
        install_spb_origin_guard,
        is_sensitive_local_path as sensitive,
    )

    assert sensitive("/recent-renders/list")
    assert sensitive("/status")
    assert sensitive("/build-check")
    assert sensitive("/swatch/base/pattern")
    app = Flask(__name__)
    install_spb_origin_guard(app, logger=_Logger())
    app.add_url_rule("/api/probe", "api_probe", lambda: "ok", methods=["GET", "POST"])
    app.add_url_rule("/public", "public", lambda: "ok", methods=["GET"])
    client = app.test_client()
    base = "http://127.0.0.1:59876"

    assert client.get("/api/probe", base_url=base).status_code == 200
    assert client.get("/api/probe", base_url=base, headers={"Origin": base}).status_code == 200
    assert client.get("/api/probe", base_url=base, headers={"Origin": "http://localhost:9999"}).status_code == 403
    assert client.get("/api/probe", base_url=base, headers={"Referer": "https://attacker.example/x"}).status_code == 403
    assert client.post("/api/probe", base_url=base, headers={"Origin": "https://attacker.example"}).status_code == 403
    assert client.get("/public", base_url=base, headers={"Origin": "https://attacker.example"}).status_code == 200


def test_verification_config_uses_strict_isolated_output_and_skips_external_dirs(
    monkeypatch, tmp_path
):
    from config import _Config

    root = tmp_path / f"config-root-{os.getpid()}"
    evidence = root / "_release_evidence" / "run" / "server-output"
    external = tmp_path / f"external-runtime-{os.getpid()}"
    monkeypatch.setattr(_Config, "ROOT_DIR", str(root))
    monkeypatch.setattr(_Config, "SHOKK_LIBRARY_DIR", str(external / "shokk"))
    monkeypatch.setattr(_Config, "SHOKK_FACTORY_DIR", str(external / "factory"))
    monkeypatch.setattr(_Config, "PATTERN_FOR_REVIEW_DIR", str(external / "review"))
    monkeypatch.setenv("SPB_NO_LIVE_LINK", "1")
    monkeypatch.setenv("SPB_ISOLATED_OUTPUT_DIR", str(evidence))

    isolated = _Config()
    assert os.path.realpath(isolated.OUTPUT_DIR) == os.path.realpath(evidence)
    assert os.path.dirname(isolated.LOG_FILE) == os.path.realpath(evidence)
    assert evidence.is_dir()
    assert not external.exists()

    monkeypatch.setenv("SPB_ISOLATED_OUTPUT_DIR", str(tmp_path / "outside-evidence"))
    with pytest.raises(RuntimeError, match="strict descendant"):
        _Config()

    server_source = (ROOT / "server.py").read_text(encoding="utf-8")
    assert "OUTPUT_FOLDER = os.path.realpath(os.path.abspath(CFG.OUTPUT_DIR))" in server_source
    v5_source = (ROOT / "server_v5.py").read_text(encoding="utf-8")
    assert "_log_file = CFG.LOG_FILE" in v5_source
    assert "_log_file = os.path.join(CFG.ROOT_DIR, 'server_log.txt')" not in v5_source
    verifier_source = (ROOT / "scripts/spb_isolated_verify.js").read_text(encoding="utf-8")
    assert "SPB_ISOLATED_OUTPUT_DIR: path.join(evidenceDir, 'server-output')" in verifier_source
    assert "SHOKKER_CRASH_LOG: path.join(evidenceDir, 'server-output', 'server_crashes.log')" in verifier_source


def test_server_v5_app_installs_origin_guard_and_runtime_identity(monkeypatch):
    # Security is independent of the observability opt-out: production V5 owns
    # a distinct Flask app and must install its own request hooks.
    v5_source = (ROOT / "server_v5.py").read_text(encoding="utf-8")
    bootstrap_source = (ROOT / "server_routes/v5_entrypoint_security.py").read_text(
        encoding="utf-8"
    )
    assert "install_v5_entrypoint_security(app" in v5_source
    assert 'raise RuntimeError("V5 security hooks are required")' in v5_source
    assert "SHOKKER_OBSERVABILITY" not in bootstrap_source
    monkeypatch.setenv("SPB_NO_LIVE_LINK", "1")
    monkeypatch.setenv("SHOKKER_OBSERVABILITY", "0")
    importlib.reload(importlib.import_module("config"))
    module = importlib.import_module("server_v5")
    base_server = importlib.import_module("server")
    assert "SPB_RUNTIME_IDENTITY_GETTER" not in base_server.app.config
    client = module.app.test_client()
    base = "http://127.0.0.1:59876"

    assert client.get(
        "/build-check", base_url=base, headers={"Origin": "https://attacker.example"}
    ).status_code == 403
    assert client.get(
        "/status", base_url=base, headers={"Referer": "http://localhost:9999/x"}
    ).status_code == 403

    response = client.get("/build-check", base_url=base, headers={"Origin": base})
    assert response.status_code == 200
    payload = response.get_json()
    required = {
        "canonical_root",
        "source_hash",
        "source_hash_manifest",
        "source_hash_algorithm",
        "source_hash_files",
        "server_hash",
        "launcher_hash",
        "pid",
        "started_at",
        "version",
        "port",
        "external_writes_disabled",
    }
    assert required <= payload.keys()
    assert payload["canonical_root"] == os.path.realpath(str(ROOT))
    assert payload["port"] == 59876
    assert payload["external_writes_disabled"] is True

    manifest = json.loads((ROOT / "runtime_identity_manifest.json").read_text(encoding="utf-8"))
    manifest_roles = [item["role"] for item in manifest["files"]]
    assert manifest_roles[:2] == ["server", "launcher"]
    assert len(manifest_roles) == 44
    assert {
        "config", "html", "finish_data", "state", "canvas", "api", "ui_boot", "projects", "easy",
        "zone_workflow", "engine_pipeline", "request_security", "write_security",
        "observability", "project_routes", "psd_import", "psd_export",
        "psd_tree", "psd_import_safety", "clipping_mask", "diagnostics",
        "cache_admin", "file_picker", "render_files", "photoshop_import",
        "photoshop_export", "spec_channel_export", "config_routes",
        "license_routes", "june_audit", "custom_finish", "workbench",
        "finish_recent", "shokk_routes", "iracing_utility", "iracing_deploy",
        "swatch_routes", "user_import_routes",
    } <= set(manifest_roles)
    sync_files = json.loads(
        (ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8")
    )["files"]
    assert {entry["path"] for entry in manifest["files"]} <= set(sync_files)
    for runtime_file in (
        "runtime_identity_manifest.json",
        "server_routes/request_security.py",
        "server_routes/runtime_identity.py",
        "server_routes/write_security.py",
        "scripts/spb_runtime_identity.js",
    ):
        assert runtime_file in sync_files
    server_hash = hashlib.sha256((ROOT / "server.py").read_bytes()).hexdigest()
    launcher_hash = hashlib.sha256((ROOT / "server_v5.py").read_bytes()).hexdigest()
    expected_input = "".join(
        f"{entry['role']}:{hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest()}\n"
        for entry in manifest["files"]
    ).encode("utf-8")
    expected = hashlib.sha256(expected_input).hexdigest()
    assert payload["server_hash"] == server_hash
    assert payload["launcher_hash"] == launcher_hash
    assert payload["source_hash"] == expected
    node_identity = json.loads(subprocess.run(
        ["node", str(ROOT / "scripts/spb_runtime_identity.js")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout)
    assert node_identity["sourceHash"] == payload["source_hash"]
    assert node_identity["sourceHashAlgorithm"] == payload["source_hash_algorithm"]
    assert node_identity["files"] == payload["source_hash_files"]

    status_payload = client.get("/status", base_url=base).get_json()
    assert required <= status_payload.keys()

    inherited = client.get("/api/server-info", base_url=base)
    assert inherited.status_code == 200
    assert required <= inherited.get_json().keys()
    assert client.post(
        "/api/finish-packs/install", base_url=base, json={"id": "anything"}
    ).status_code == 403
    assert client.post(
        "/config", base_url=base, json={"live_link_enabled": False}
    ).status_code == 403
    assert client.post(
        "/api/projects/save/start",
        base_url=base,
        json={"filename": "blocked.spbproj", "totalBytes": 1},
        headers={"X-Shokker-Internal": "1"},
    ).status_code == 403
    assert client.get("/api/user-imports", base_url=base).status_code == 403
    assert client.get("/api/workbench/catalog", base_url=base).status_code == 403
    assert "V5 security hooks are required" in (
        ROOT / "server_v5.py"
    ).read_text(encoding="utf-8")


def test_spec_preview_get_degrades_to_memory_without_external_cache_write(monkeypatch, tmp_path):
    from PIL import Image
    import server

    cache_root = tmp_path / "external-thumbnails"
    monkeypatch.setenv("SPB_NO_LIVE_LINK", "1")
    monkeypatch.setattr(server, "THUMBNAIL_DIR", str(cache_root))
    monkeypatch.setattr(server, "_validate_spec_pattern_preview_request", lambda _key: None)
    monkeypatch.setattr(
        server,
        "_generate_spec_preview_image",
        lambda _key: Image.new("RGB", (4, 4), (1, 2, 3)),
    )

    response = server.app.test_client().get("/api/spec-pattern-preview/probe")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert not cache_root.exists()

    source = (ROOT / "server.py").read_text(encoding="utf-8")
    assert '"spec-thumbnail-prebake"' in source
    assert '"user-import-inbox-startup"' in source


def test_runtime_identity_is_manifest_driven_and_fails_closed(tmp_path):
    from server_routes.runtime_identity import build_runtime_identity

    root = tmp_path / f"identity-root-{os.getpid()}"
    root.mkdir(exist_ok=True)
    (root / "server.py").write_bytes(b"server")
    (root / "launcher.py").write_bytes(b"launcher")
    (root / "policy.py").write_bytes(b"policy")
    manifest = {
        "schema": 1,
        "hash": "sha256",
        "source_hash_algorithm": "sha256(utf8(concat(role, ':', sha256(file), '\\n') for files in listed order))",
        "files": [
            {"role": "launcher", "path": "launcher.py"},
            {"role": "policy", "path": "policy.py"},
            {"role": "server", "path": "server.py"},
        ],
    }
    (root / "identity.json").write_text(json.dumps(manifest), encoding="utf-8")
    payload = build_runtime_identity(
        canonical_root=root,
        server_path=root / "server.py",
        launcher_path=root / "launcher.py",
        version="test",
        port=1,
        started_at=1,
        external_writes_disabled=False,
        identity_manifest="identity.json",
    )
    assert [entry["role"] for entry in payload["source_hash_files"]] == [
        "launcher", "policy", "server",
    ]
    expected_input = "".join(
        f"{entry['role']}:{entry['sha256']}\n" for entry in payload["source_hash_files"]
    ).encode("utf-8")
    assert payload["source_hash"] == hashlib.sha256(expected_input).hexdigest()

    (root / "policy.py").write_bytes(b"policy-changed")
    changed = build_runtime_identity(
        canonical_root=root,
        server_path=root / "server.py",
        launcher_path=root / "launcher.py",
        version="test",
        port=1,
        started_at=1,
        external_writes_disabled=False,
        identity_manifest="identity.json",
    )
    assert changed["source_hash"] != payload["source_hash"]
    assert changed["server_hash"] == payload["server_hash"]
    assert changed["launcher_hash"] == payload["launcher_hash"]

    with pytest.raises(ValueError, match="missing or outside"):
        build_runtime_identity(
            canonical_root=root,
            server_path=root / "server.py",
            launcher_path=root / "launcher.py",
            version="test",
            port=1,
            started_at=1,
            external_writes_disabled=False,
            identity_manifest="missing.json",
        )


def test_file_thumbnail_requires_picker_approval(tmp_path):
    from server_routes.file_picker_routes import register_file_picker_routes

    case_dir = tmp_path / "flow_security_thumb_case"
    case_dir.mkdir(exist_ok=True)
    image_path = case_dir / "paint.png"
    Image.new("RGB", (8, 8), (10, 20, 30)).save(image_path)
    app = Flask(__name__)
    register_file_picker_routes(app, load_config=lambda: {}, logger=_Logger())
    client = app.test_client()

    direct = client.get("/api/file-thumb", query_string={"path": str(image_path)})
    assert direct.status_code == 403
    browse = client.post("/browse-files", json={"path": str(case_dir), "filter": ".png"})
    assert browse.status_code == 200
    approved = client.get("/api/file-thumb", query_string={"path": str(image_path)})
    assert approved.status_code == 200
    assert approved.mimetype == "image/png"


def test_clear_cache_is_post_only(tmp_path):
    from server_routes.cache_admin_routes import register_cache_admin_routes

    app = Flask(__name__)
    register_cache_admin_routes(
        app,
        swatch_cache={},
        swatch_cache_lock=threading.Lock(),
        finish_catalog_cache_clear=lambda: True,
        finish_meta_cache_clear=lambda: None,
        psd_cache_getter=lambda: {},
        prev_spec_cache_getter=lambda: None,
        prev_spec_cache_setter=lambda _value: None,
        thumbnail_dir_getter=lambda: str(tmp_path),
        validate_thumbnail_regen_request=lambda kind, _finish: kind,
        queue_thumbnail_regen=lambda *_args: None,
        clear_zone_cache=lambda: 0,
        logger=_Logger(),
    )
    client = app.test_client()
    assert client.get("/api/clear-cache").status_code == 405
    assert client.post("/api/clear-cache").status_code == 200


def test_thumbnail_refresh_uses_post_only_and_reports_partial_failure_truthfully():
    source = (ROOT / "js/zones/zone-thumbnail-controls.js").read_text(encoding="utf-8")
    assert "method: 'POST'" in source
    assert "method: 'GET'" not in source
    assert "serverCacheCleared" in source
    assert "server cache could not be cleared" in source


def test_photoshop_custom_read_root_requires_internal_capability(tmp_path):
    from server_routes.photoshop_import_routes import register_photoshop_import_routes

    default_root = tmp_path / "default_exchange"
    custom_root = tmp_path / "custom_exchange"
    output_root = tmp_path / "output"
    default_root.mkdir(exist_ok=True)
    custom_root.mkdir(exist_ok=True)
    output_root.mkdir(exist_ok=True)

    def require_internal():
        if request.headers.get("X-Shokker-Internal") == "1":
            return True, None
        return False, "missing internal capability"

    app = Flask(__name__)
    register_photoshop_import_routes(
        app,
        exchange_root_getter=lambda: str(default_root),
        output_folder=str(output_root),
        require_internal_request=require_internal,
        logger=_Logger(),
    )
    client = app.test_client()
    assert client.get("/api/photoshop-import-list").status_code == 200
    denied = client.get(
        "/api/photoshop-import-list", query_string={"exchange_folder": str(custom_root)}
    )
    assert denied.status_code == 403
    allowed = client.get(
        "/api/photoshop-import-list",
        query_string={"exchange_folder": str(custom_root)},
        headers={"X-Shokker-Internal": "1"},
    )
    assert allowed.status_code == 200


def test_external_write_kill_switch_and_route_coverage(tmp_path, monkeypatch):
    from server_routes.photoshop_export_routes import register_photoshop_export_routes
    from server_routes.render_file_routes import register_render_file_routes
    from server_routes.spec_channel_export_routes import register_spec_channel_export_routes
    from server_routes.write_security import external_write_denial

    case_dir = tmp_path / "flow_security_external_case"
    case_dir.mkdir(exist_ok=True)
    owned_dir = case_dir / "owned"
    def guard(path, operation):
        return external_write_denial(
            path, operation, owned_root=owned_dir, logger=_Logger()
        )
    monkeypatch.setenv("SPB_NO_LIVE_LINK", "1")
    assert guard(owned_dir / "job", "internal") is None
    assert guard(case_dir / "outside", "external")["error"] == "external_write_disabled"

    external_dir = case_dir / "iracing"
    external_dir.mkdir(exist_ok=True)
    paint = external_dir / "car_num_123.tga"
    backup = external_dir / "ORIGINAL_car_num_123.tga"
    paint.write_bytes(b"paint")
    backup.write_bytes(b"backup")
    app = Flask(__name__)
    register_render_file_routes(
        app,
        output_job_dir_resolver=lambda _job: None,
        logger=_Logger(),
        external_write_guard=guard,
    )
    client = app.test_client()
    save = client.post(
        "/save-render-to-keep", json={"output_dir": str(external_dir), "iracing_id": "123"}
    )
    assert save.status_code == 403
    assert not (external_dir / "Shokker Paint Booth").exists()
    reset = client.post(
        "/reset-backup", json={"paint_file": str(paint), "iracing_id": "123"}
    )
    assert reset.status_code == 403
    assert backup.read_bytes() == b"backup"

    photoshop_target = case_dir / "photoshop_exchange"
    photoshop_app = Flask("photoshop_guard")
    register_photoshop_export_routes(
        photoshop_app,
        engine_getter=lambda: pytest.fail("engine must not run after external-write denial"),
        output_folder_getter=lambda: str(owned_dir),
        photoshop_exchange_root=lambda: str(photoshop_target),
        repair_base_overlay_pattern_reactive_payload=lambda zone: zone,
        convert_zone_keys=lambda zone: zone,
        max_zones_per_request=50,
        apply_paint_recolor=lambda *args: args[0],
        decode_rle_mask_payload=lambda *_args, **_kwargs: pytest.fail("no mask expected"),
        decode_source_layer_rgb_payload=lambda *_args: pytest.fail("no RGB expected"),
        decode_spatial_mask_payload=lambda *_args, **_kwargs: pytest.fail("no mask expected"),
        image_shape_getter=lambda *_args: pytest.fail("no source-sized mask expected"),
        external_write_guard=guard,
        logger=_Logger(),
    )
    denied_export = photoshop_app.test_client().post(
        "/api/export-to-photoshop",
        json={"paint_file": str(paint), "zones": [{"name": "Body"}]},
    )
    assert denied_export.status_code == 403
    assert not photoshop_target.exists()

    spec_source = case_dir / "spec.png"
    Image.new("RGBA", (2, 2), (1, 2, 3, 4)).save(spec_source)
    spec_target = case_dir / "spec_external"
    spec_app = Flask("spec_guard")
    register_spec_channel_export_routes(
        spec_app,
        output_folder_getter=lambda: str(owned_dir),
        shokk_manager_getter=lambda: None,
        external_write_guard=guard,
        logger=_Logger(),
    )
    denied_spec = spec_app.test_client().post(
        "/api/export-spec-channels",
        json={"spec_path": str(spec_source), "output_dir": str(spec_target)},
    )
    assert denied_spec.status_code == 403
    assert not spec_target.exists()

    render_source = (ROOT / "server_routes/render_file_routes.py").read_text(encoding="utf-8")
    photoshop_source = (ROOT / "server_routes/photoshop_export_routes.py").read_text(encoding="utf-8")
    spec_source = (ROOT / "server_routes/spec_channel_export_routes.py").read_text(encoding="utf-8")
    assert 'external_write_guard(keep_dir, "save-render-to-keep")' in render_source
    assert 'external_write_guard(source_dir, "reset-backup")' in render_source
    assert 'external_write_guard(exchange_root, "export-to-photoshop")' in photoshop_source
    assert 'external_write_guard(out_dir, "export-spec-channels")' in spec_source


def test_kill_switch_blocks_config_license_and_project_storage(tmp_path, monkeypatch):
    from server_routes.config_routes import register_config_routes
    from server_routes.license_routes import register_license_routes
    from server_routes.project_routes import register_project_routes
    from server_routes.write_security import external_write_denial

    owned = tmp_path / "owned"
    external = tmp_path / "external"

    def guard(path, operation):
        return external_write_denial(path, operation, owned_root=owned, logger=_Logger())

    monkeypatch.setenv("SPB_NO_LIVE_LINK", "1")
    saved_configs = []
    config_app = Flask("config_kill")
    register_config_routes(
        config_app,
        load_config=lambda: {},
        save_config=saved_configs.append,
        logger=_Logger(),
        config_path=external / "shokker_config.json",
        external_write_guard=guard,
    )
    denied = config_app.test_client().post("/config", json={"iracing_id": "123"})
    assert denied.status_code == 403
    assert denied.get_json()["error"] == "external_write_disabled"
    assert saved_configs == []

    state = {"key": "", "active": False}
    saved_licenses = []
    license_app = Flask("license_kill")
    register_license_routes(
        license_app,
        license_getter=lambda: (state["key"], state["active"]),
        license_setter=lambda key, active: state.update(key=key, active=active),
        validate_license_key=lambda _key: True,
        save_license=lambda key, active: saved_licenses.append((key, active)),
        logger=_Logger(),
        license_path=external / "shokker_license.json",
        external_write_guard=guard,
    )
    assert license_app.test_client().post(
        "/license", json={"key": "SHOKKER-AAAA-BBBB-CCCC"}
    ).status_code == 403
    assert license_app.test_client().post("/license/deactivate").status_code == 403
    assert state == {"key": "", "active": False}
    assert saved_licenses == []

    projects_dir = external / "SPB Projects"
    project_app = Flask("project_kill")
    register_project_routes(
        project_app,
        logger=_Logger(),
        projects_dir_getter=lambda: str(projects_dir),
        external_write_guard=guard,
    )
    project_client = project_app.test_client()
    for path in (
        "/api/projects/save",
        "/api/projects/save/start",
        "/api/projects/save/chunk/token",
        "/api/projects/save/commit/token",
        "/api/projects/save/abort/token",
        "/api/projects/delete",
    ):
        assert project_client.post(path, json={}).status_code == 403
    assert not projects_dir.exists()

    # Normal desktop runtime remains unchanged when the verification env is absent.
    monkeypatch.delenv("SPB_NO_LIVE_LINK")
    assert guard(external / "normal.json", "normal-save") is None
    ok = config_app.test_client().post("/config", json={"iracing_id": "456"})
    assert ok.status_code == 200
    assert saved_configs[-1]["iracing_id"] == "456"


def test_kill_switch_blocks_review_workbench_library_and_import_writes(tmp_path, monkeypatch):
    from server_routes.custom_finish_routes import register_custom_finish_routes
    from server_routes.june_audit_routes import register_june_audit_routes
    from server_routes.shokk_routes import register_shokk_routes
    from server_routes.user_import_routes import register_user_import_routes
    from server_routes.workbench_routes import register_workbench_routes
    from server_routes.write_security import external_write_denial

    owned = tmp_path / "owned"
    external = tmp_path / "external"
    user_imports = external / "user_imports"
    monkeypatch.setenv("SPB_NO_LIVE_LINK", "1")
    monkeypatch.setenv("SPB_USER_IMPORTS_DIR", str(user_imports))

    def guard(path, operation):
        return external_write_denial(path, operation, owned_root=owned, logger=_Logger())

    june_app = Flask("june_kill")
    register_june_audit_routes(
        june_app, server_dir=str(external), logger=_Logger(), external_write_guard=guard
    )
    assert june_app.test_client().post(
        "/api/june-audit/bases", json={"entries": {}}
    ).status_code == 403
    assert not (external / "_audit").exists()

    workbench_app = Flask("workbench_kill")
    register_workbench_routes(
        workbench_app,
        server_dir=str(external),
        logger=_Logger(),
        external_write_guard=guard,
    )
    assert workbench_app.test_client().get("/api/workbench/catalog").status_code == 403
    assert not (external / "_workbench").exists()

    custom_saves = []
    custom_app = Flask("custom_kill")
    register_custom_finish_routes(
        custom_app,
        load_custom_finishes=lambda: [],
        save_custom_finishes=custom_saves.append,
        storage_path=external / "custom_finishes.json",
        external_write_guard=guard,
        logger=_Logger(),
    )
    assert custom_app.test_client().post(
        "/api/save-custom-finish",
        json={"name": "x", "finish_ids": ["a", "b"], "weights": [1, 1]},
    ).status_code == 403
    assert custom_saves == []

    class _Manager:
        library_dir = str(external / "SHOKK Library")
        factory_dir = str(external / "factory")

        def save(self, **_kwargs):
            pytest.fail("SHOKK save must not run")

        def delete(self, _filename):
            pytest.fail("SHOKK delete must not run")

    shokk_app = Flask("shokk_kill")
    register_shokk_routes(
        shokk_app,
        manager_getter=_Manager,
        output_folder_getter=lambda: str(owned),
        spb_version_getter=lambda: "test",
        logger=_Logger(),
        external_write_guard=guard,
    )
    shokk_client = shokk_app.test_client()
    assert shokk_client.post("/api/shokk/save", json={}).status_code == 403
    assert shokk_client.post(
        "/api/shokk/delete", json={"filename": "x.shokk"}
    ).status_code == 403
    assert shokk_client.post(
        "/api/shokk/rename", json={"old_name": "x.shokk", "new_name": "y.shokk"}
    ).status_code == 403

    import_app = Flask("import_kill")
    register_user_import_routes(
        import_app,
        engine_getter=lambda: pytest.fail("engine must not load"),
        finish_catalog_cache_clear=lambda: None,
        logger=_Logger(),
        external_write_guard=guard,
    )
    assert import_app.test_client().post("/api/user-imports/reload").status_code == 403
    assert import_app.test_client().get("/api/user-imports").status_code == 403
    assert import_app.test_client().get("/api/user-imports/dna-presets").status_code == 403
    assert import_app.test_client().get("/api/user-imports/export-all").status_code == 403
    assert not user_imports.exists()


def test_kill_switch_blocks_cache_psd_temp_and_background_export(tmp_path, monkeypatch):
    import io
    import tempfile

    from server_routes.cache_admin_routes import register_cache_admin_routes
    from server_routes.finish_viewer_recent_routes import register_finish_viewer_latest_routes
    from server_routes.psd_import_routes import register_psd_import_routes
    from server_routes.write_security import external_write_denial

    owned = tmp_path / "owned"
    external = tmp_path / "external"
    monkeypatch.setenv("SPB_NO_LIVE_LINK", "1")

    def guard(path, operation):
        return external_write_denial(path, operation, owned_root=owned, logger=_Logger())

    memory_cache = {"keep": b"value"}
    cache_app = Flask("cache_kill")
    register_cache_admin_routes(
        cache_app,
        swatch_cache=memory_cache,
        swatch_cache_lock=threading.Lock(),
        finish_catalog_cache_clear=lambda: pytest.fail("memory cache must remain unchanged"),
        finish_meta_cache_clear=lambda: None,
        psd_cache_getter=lambda: {},
        prev_spec_cache_getter=lambda: None,
        prev_spec_cache_setter=lambda _value: None,
        thumbnail_dir_getter=lambda: str(external / "thumbnails"),
        validate_thumbnail_regen_request=lambda kind, _finish: kind,
        queue_thumbnail_regen=lambda *_args: pytest.fail("regen must not queue"),
        clear_zone_cache=lambda: 0,
        logger=_Logger(),
        external_write_guard=guard,
    )
    cache_client = cache_app.test_client()
    assert cache_client.post("/api/clear-cache").status_code == 403
    assert memory_cache == {"keep": b"value"}
    assert cache_client.post("/api/thumb-regen/base/example").status_code == 403

    monkeypatch.setattr(tempfile, "tempdir", str(external / "os-temp"))
    psd_app = Flask("psd_temp_kill")
    register_psd_import_routes(
        psd_app,
        require_internal_request=lambda: (True, None),
        sanitize_path=lambda path: (path, None),
        get_cached_psd=lambda _path: pytest.fail("PSD must not open"),
        logger=_Logger(),
        external_write_guard=guard,
    )
    denied_upload = psd_app.test_client().post(
        "/api/psd-import",
        data={"file": (io.BytesIO(b"not-a-psd"), "paint.psd")},
        content_type="multipart/form-data",
    )
    assert denied_upload.status_code == 403
    assert not (external / "os-temp").exists()

    viewer_app = Flask("viewer_export_kill")
    register_finish_viewer_latest_routes(
        viewer_app,
        output_folder_getter=lambda: str(owned),
        full_dna_job={"process": None},
        full_dna_status_path_getter=lambda: str(external / "dna" / "status.json"),
        full_dna_status_reader=lambda: {},
        rate_limit=lambda *_args, **_kwargs: True,
        safe_int=lambda value, default: int(value or default),
        server_dir=str(ROOT),
        sys_executable="python",
        logger=_Logger(),
        external_write_guard=guard,
    )
    assert viewer_app.test_client().post(
        "/api/finish-viewer/full-dna-export", json={}
    ).status_code == 403
    assert not (external / "dna").exists()


def test_export_routes_use_shared_bounded_decoder_and_source_shape():
    photoshop = (ROOT / "server_routes/photoshop_export_routes.py").read_text(encoding="utf-8")
    psd = (ROOT / "server_routes/psd_layer_export_routes.py").read_text(encoding="utf-8")
    recolor = (ROOT / "server_routes/paint_recolor_support.py").read_text(encoding="utf-8")
    for source in (photoshop, psd):
        assert "max_shape=(512, 512)" in source
        assert "expected_shape=canvas_shape" in source
        assert "psm_flat = np.zeros" not in source
    assert "decode_spatial_mask_payload(" in recolor
    assert "spatial_mask = np.zeros" not in recolor


def test_electron_server_restart_is_child_bound_and_single_flight():
    source = (ROOT / "electron-app/main.js").read_text(encoding="utf-8")
    assert "let serverRestartPromise = null;" in source
    assert "const intentionalServerStops = new WeakSet();" in source
    assert "if (serverProcess !== child)" in source
    assert "if (serverRestartPromise)" in source
    assert "const childToStop = serverProcess;" in source
    assert "intentionalServerStops.add(childToStop);" in source
