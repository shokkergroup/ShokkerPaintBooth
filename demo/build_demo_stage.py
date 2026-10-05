"""Build the isolated, allowlisted SHOKK DEMO Electron server stage.

The paid application tree is a build-time source only.  The resulting stage
contains a small demo backend, a small demo frontend, one starter PSD, exactly
30 reviewed material snapshots, and the minimum portable Python dependency
closure.  No paid server, registry, renderer, licence, or updater code is
copied.

Release command (the output path is intentionally fixed)::

    python demo/build_demo_stage.py --output electron-demo/.stage

The two ``--test-*`` switches are guarded by ``SHOKK_DEMO_STAGE_TEST_MODE=1``
and exist only so focused tests can avoid copying hundreds of megabytes.  The
Electron staging script does not use them.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_REPO_ROOT = SCRIPT_PATH.parent.parent
DEFAULT_OUTPUT = DEFAULT_REPO_ROOT / "electron-demo" / ".stage"
DEFAULT_STARTER = Path(r"C:\1Shokker Paint Car Examples\SPB ARCA Chevy V6.psd")
STARTER_FILENAME = "SPB ARCA Chevy V6.psd"
STARTER_SIZE = 18_534_362
STARTER_SHA256 = "9eae8405b6bccda7c68c097b4a35f0e1f5894c66d97d02d23280729f314ab0aa"
SNAPSHOT_SCHEMA = "spb-demo-material-snapshot/1"
SNAPSHOT_SIZE = 2048

VISIBLE_FINISH_IDS = (
    "f_chrome",
    "gloss",
    "f_frozen",
    "f_powder_coat",
    "f_metallic",
    "efx_holographic_drift",
    "fo_lava_lamp",
    "cherry_polka",
    "tac_frozen_bank",
    "elm_tsunami",
    "elm_black_ice",
    "ffo_haz_bloom",
    "fmo_chrysina_gold",
    "dkc_hematite",
    "fab_glass_slipper",
    "fab_woodcut_block",
    "beetle_ground",
    "butterfly_swallowtail",
    "cs_chocolate_mint",
    "xlab_shatter_royale",
    "xlab_stained_circuit",
    "grad_neon_rush",
    "grad_fire_fade_h",
    "aurora_black_rainbow",
    "fm_herringbone",
    "ff_wovencell",
    "ffl_foundry_spatter",
    "ff_truchet_glass",
    "impossible_cinder_pulse",
)
HIDDEN_FINISH_IDS = ("fs_core_emerald",)
RENDERABLE_FINISH_IDS = VISIBLE_FINISH_IDS + HIDDEN_FINISH_IDS

# Copying by explicit relative filename is deliberate.  In particular,
# backend/build_snapshots.py is a build-only paid-engine adapter and must never
# be present in the shipping stage.
BACKEND_FILES = (
    "__init__.py",
    "app.py",
    "catalog.py",
    "compositor.py",
    "images.py",
    "psd_support.py",
    "recipe.py",
    "validation.py",
    "requirements.txt",
)
FRONTEND_FILES = (
    "paint-booth-v2.html",
    "styles.css",
    "branding-recipe.css",
    "js/api.js",
    "js/app.js",
    "js/branding-recipe.js",
    "js/canvas.js",
    "js/preview-interactions.js",
    "js/exclude-mask.js",
    "js/exclude-brush.js",
    "assets/branding/shokk-handmark.png",
    "assets/branding/shokker-paint-booth.png",
    "assets/branding/shokker-road.png",
    "assets/branding/spb-splash-intro.mp4",
)

# The portable distribution's standard-library ZIP contains pure-Python
# stdlib modules.  Only extension modules needed by Flask, NumPy, Pillow,
# psd-tools, networking, hashing, and compressed image/PSD decoding are kept.
PYTHON_ROOT_FILES = (
    "python.exe",
    "python3.dll",
    "python313.dll",
    "python313.zip",
    "python313._pth",
    "python.cat",
    "LICENSE.txt",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "libcrypto-3.dll",
    "libssl-3.dll",
    "libffi-8.dll",
    "_asyncio.pyd",
    "_bz2.pyd",
    "_ctypes.pyd",
    "_decimal.pyd",
    "_elementtree.pyd",
    "_hashlib.pyd",
    "_lzma.pyd",
    "_multiprocessing.pyd",
    "_overlapped.pyd",
    "_queue.pyd",
    "_socket.pyd",
    "_ssl.pyd",
    "_uuid.pyd",
    "_zoneinfo.pyd",
    "pyexpat.pyd",
    "select.pyd",
    "unicodedata.pyd",
)
PYTHON_SITE_PACKAGES = (
    "attr",
    "attrs",
    "attrs-26.1.0.dist-info",
    "blinker",
    "blinker-1.9.0.dist-info",
    "click",
    "click-8.3.1.dist-info",
    "colorama",
    "colorama-0.4.6.dist-info",
    "flask",
    "flask-3.1.3.dist-info",
    "itsdangerous",
    "itsdangerous-2.2.0.dist-info",
    "jinja2",
    "jinja2-3.1.6.dist-info",
    "markupsafe",
    "markupsafe-3.0.3.dist-info",
    "numpy",
    "numpy-2.4.4.dist-info",
    "numpy.libs",
    "PIL",
    "pillow-12.2.0.dist-info",
    "psd_tools",
    "psd_tools-1.15.0.post1.dist-info",
    "psd_tools.libs",
    "typing_extensions.py",
    "typing_extensions-4.15.0.dist-info",
    "werkzeug",
    "werkzeug-3.1.6.dist-info",
)
PYTHON_PRUNED_DIR_NAMES = frozenset({"doc", "docs", "test", "testing", "tests"})
PYTHON_PRUNED_SUFFIXES = frozenset({".md", ".rst"})

FORBIDDEN_PATH_PARTS = {
    "__pycache__",
    "pyserver",
    "_internal",
    "activation",
    "entitlement",
    "serial",
    "secrets",
}
FORBIDDEN_FILENAMES = {
    "server.py",
    "server_v5.py",
    "shokker_engine_v2.py",
    "base_registry_data.py",
    "paint-booth-0-finish-data.js",
    "spec_patterns.py",
    "license.html",
    "license-preload.js",
    "spb-license-secrets.json",
}
FORBIDDEN_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".log",
    ".pdb",
    ".pem",
    ".key",
    ".pfx",
    ".p12",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".whl",
}
FORBIDDEN_IMPORT_ROOTS = {
    "server",
    "server_v5",
    "engine",
    "shokker_engine_v2",
    "base_registry_data",
}


class StageBuildError(RuntimeError):
    """A release invariant failed; an incomplete stage must not be packaged."""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_output_path(repo_root: Path, requested: Path, *, test_mode: bool) -> Path:
    """Resolve and prove a deletion target before any mutation occurs."""

    repo = repo_root.resolve()
    expected = (repo / "electron-demo" / ".stage").resolve()
    raw = requested.expanduser()
    resolved = raw.resolve()
    if raw.exists() and raw.is_symlink():
        raise StageBuildError("Refusing to replace a symlinked stage directory")
    if resolved == expected:
        if test_mode and repo == DEFAULT_REPO_ROOT.resolve():
            raise StageBuildError("Test artifacts may not replace the canonical Electron stage")
        return resolved
    if not test_mode:
        raise StageBuildError(f"Output must resolve exactly to {expected}")

    temporary_root = Path(tempfile.gettempdir()).resolve()
    if (
        resolved.name != ".stage"
        or resolved in {temporary_root, resolved.anchor and Path(resolved.anchor)}
        or not _is_relative_to(resolved, temporary_root)
    ):
        raise StageBuildError(
            "Test output must be a directory named .stage beneath the system temp directory"
        )
    return resolved


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StageBuildError(f"Cannot read demo product manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise StageBuildError("Demo product manifest must contain a JSON object")
    return payload


def validate_manifest(payload: dict[str, Any]) -> None:
    if payload.get("schema") != "spb-demo-product/1":
        raise StageBuildError("Unexpected demo manifest schema")
    product = payload.get("product")
    if not isinstance(product, dict) or product.get("id") != "shokk-demo":
        raise StageBuildError("Manifest product identity is not shokk-demo")
    if product.get("server_port") != 59886:
        raise StageBuildError("Manifest demo server port must be 59886")

    starter = payload.get("starter")
    if not isinstance(starter, dict):
        raise StageBuildError("Manifest starter contract is missing")
    if starter.get("filename") != STARTER_FILENAME:
        raise StageBuildError("Manifest starter PSD filename changed")
    if starter.get("relative_path") != f"assets/starter/{STARTER_FILENAME}":
        raise StageBuildError("Manifest starter relative path changed")

    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, dict):
        raise StageBuildError("Manifest capabilities are missing")
    exact_capabilities = {
        "visible_finish_count": 29,
        "renderable_finish_count": 30,
        "tools": ["pick", "exclude"],
        "patterns": False,
        "pattern_stacks": False,
        "spec_patterns": False,
        "spec_pattern_stacks": False,
        "extra_base_overlays": 0,
        "finish_authoring": False,
        "finish_import": False,
    }
    for key, expected in exact_capabilities.items():
        if capabilities.get(key) != expected:
            raise StageBuildError(f"Manifest capability {key!r} must be {expected!r}")

    finishes = payload.get("finishes")
    if not isinstance(finishes, list):
        raise StageBuildError("Manifest finishes must be a list")
    if not all(isinstance(item, dict) for item in finishes):
        raise StageBuildError("Every manifest finish must be an object")
    ids = tuple(item.get("id") for item in finishes)
    if ids != RENDERABLE_FINISH_IDS:
        raise StageBuildError("Manifest finish ids/order do not match the reviewed 30-finish allowlist")
    visible_ids = tuple(item.get("id") for item in finishes if item.get("visible") is True)
    hidden_ids = tuple(item.get("id") for item in finishes if item.get("visible") is False)
    if visible_ids != VISIBLE_FINISH_IDS or hidden_ids != HIDDEN_FINISH_IDS:
        raise StageBuildError("Manifest visibility does not match 29 picker finishes + hidden FRACTURE")


def _copy_file(source: Path, destination: Path) -> None:
    if not source.is_file() or source.is_symlink():
        raise StageBuildError(f"Required regular source file is missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_tree_allowlisted(source: Path, destination: Path) -> None:
    if not source.is_dir() or source.is_symlink():
        raise StageBuildError(f"Required source package is missing: {source}")
    for candidate in sorted(source.rglob("*")):
        relative = candidate.relative_to(source)
        lower_parts = tuple(part.lower() for part in relative.parts)
        legal_notice = "license" in candidate.name.lower() or "licenses" in lower_parts
        if candidate.is_symlink():
            raise StageBuildError(f"Symlink is forbidden in portable dependency: {candidate}")
        if candidate.is_dir():
            continue
        if PYTHON_PRUNED_DIR_NAMES.intersection(lower_parts[:-1]) and not legal_notice:
            continue
        if "__pycache__" in lower_parts:
            continue
        if candidate.suffix.lower() in {".pyc", ".pyo"}:
            continue
        if candidate.suffix.lower() in PYTHON_PRUNED_SUFFIXES and not legal_notice:
            continue
        _copy_file(candidate, destination / relative)


def copy_runtime_sources(repo_root: Path, server_root: Path) -> None:
    demo_root = repo_root / "demo"
    for relative in BACKEND_FILES:
        _copy_file(demo_root / "backend" / relative, server_root / "backend" / relative)
    for relative in FRONTEND_FILES:
        _copy_file(demo_root / "frontend" / relative, server_root / "frontend" / relative)
    _copy_file(demo_root / "product-manifest.json", server_root / "product-manifest.json")


_LOCAL_JS_IMPORT = re.compile(
    r"(?:\bfrom\s*|\bimport\s*)[\"'](?P<specifier>\.{1,2}/[^\"']+)[\"']"
)


def validate_frontend_module_closure(frontend_root: Path) -> None:
    """Reject a stage whose JavaScript imports a local module it did not ship."""

    root = frontend_root.resolve()
    for script in sorted(root.rglob("*.js")):
        try:
            source = script.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise StageBuildError(f"Cannot inspect staged frontend module {script}: {exc}") from exc
        for match in _LOCAL_JS_IMPORT.finditer(source):
            specifier = match.group("specifier").split("?", 1)[0].split("#", 1)[0]
            dependency = (script.parent / specifier).resolve()
            if not _is_relative_to(dependency, root):
                raise StageBuildError(
                    f"Frontend module import escapes the staged frontend: {script.name} -> {specifier}"
                )
            if not dependency.is_file():
                relative_script = script.relative_to(root).as_posix()
                raise StageBuildError(
                    f"Staged frontend module is missing: {relative_script} imports {specifier}"
                )


def copy_portable_python(repo_root: Path, server_root: Path) -> None:
    source = repo_root / "electron-app" / "server" / "python"
    destination = server_root / "python"
    for filename in PYTHON_ROOT_FILES:
        _copy_file(source / filename, destination / filename)
    site_source = source / "Lib" / "site-packages"
    site_destination = destination / "Lib" / "site-packages"
    for package_name in PYTHON_SITE_PACKAGES:
        package_source = site_source / package_name
        package_destination = site_destination / package_name
        if package_source.is_dir():
            _copy_tree_allowlisted(package_source, package_destination)
        else:
            _copy_file(package_source, package_destination)


def _validate_starter(source: Path, *, expected_sha256: str, expected_size: int | None) -> None:
    if not source.is_file() or source.is_symlink():
        raise StageBuildError(f"Required starter PSD is missing: {source}")
    size = source.stat().st_size
    if expected_size is not None and size != expected_size:
        raise StageBuildError(f"Starter PSD size mismatch: expected {expected_size}, found {size}")
    actual_hash = sha256_file(source)
    if actual_hash.lower() != expected_sha256.lower():
        raise StageBuildError(
            f"Starter PSD SHA256 mismatch: expected {expected_sha256}, found {actual_hash}"
        )


def _run_snapshot_exporter(repo_root: Path) -> None:
    exporter = repo_root / "demo" / "backend" / "build_snapshots.py"
    if not exporter.is_file():
        raise StageBuildError(
            "Reviewed snapshots are missing and the build-only snapshot exporter is unavailable"
        )
    command = [
        sys.executable,
        "-m",
        "demo.backend.build_snapshots",
        "--size",
        str(SNAPSHOT_SIZE),
    ]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown exporter error").strip()
        raise StageBuildError(f"Snapshot exporter failed: {detail[-4000:]}")


def _load_numpy():
    try:
        import numpy as np  # type: ignore
    except ImportError as exc:
        raise StageBuildError("NumPy is required at build time to verify demo snapshots") from exc
    return np


def validate_snapshot(path: Path, finish_id: str, *, expected_size: int = SNAPSHOT_SIZE) -> None:
    np = _load_numpy()
    required_keys = {"schema", "finish_id", "build_size", "seed", "paint", "spec"}
    # [SPB-DEMO-PARITY 2026-09-03] A finish is captured as a RESPONSE to the customer's
    # source art, not one frozen frame: paint_lo/paint_hi bracket that response, color_src
    # holds the "From special" field, and spec_lo/spec_hi appear only for the few finishes
    # whose spec tracks the source.  Everything here stays an allowlist — an unknown key
    # is still a hard failure, so nothing unreviewed can ride into the package.
    optional_keys = {"paint_lo", "paint_hi", "color_src", "spec_lo", "spec_hi"}
    try:
        with np.load(path, allow_pickle=False) as payload:
            present = set(payload.files)
            if not required_keys <= present or not (present - required_keys) <= optional_keys:
                raise StageBuildError(
                    f"{finish_id}.npz must contain {sorted(required_keys)} and may add only "
                    f"{sorted(optional_keys)}; found {sorted(present)}"
                )
            for key in sorted(present & optional_keys):
                field = np.asarray(payload[key])
                if field.dtype != np.uint8 or field.ndim != 3 or field.shape[2] != 3:
                    raise StageBuildError(
                        f"Snapshot {finish_id} field {key!r} must be a uint8 HxWx3 field"
                    )
            schema = str(np.asarray(payload["schema"]).item())
            embedded_id = str(np.asarray(payload["finish_id"]).item())
            build_size = tuple(int(value) for value in np.asarray(payload["build_size"]).ravel())
            seed = int(np.asarray(payload["seed"]).item())
            paint = np.asarray(payload["paint"])
            spec = np.asarray(payload["spec"])
    except StageBuildError:
        raise
    except Exception as exc:
        raise StageBuildError(f"Cannot validate {finish_id}.npz: {exc}") from exc
    expected_shape = (expected_size, expected_size, 3)
    if schema != SNAPSHOT_SCHEMA or embedded_id != finish_id:
        raise StageBuildError(f"Snapshot identity/schema mismatch for {finish_id}")
    if build_size != (expected_size, expected_size) or seed != 51:
        raise StageBuildError(f"Snapshot build metadata mismatch for {finish_id}")
    if paint.shape != expected_shape or spec.shape != expected_shape:
        raise StageBuildError(
            f"Snapshot {finish_id} must contain two {expected_shape} material fields"
        )
    if paint.dtype != np.uint8 or spec.dtype != np.uint8:
        raise StageBuildError(f"Snapshot {finish_id} fields must use uint8")


def _make_synthetic_snapshots(destination: Path, manifest: dict[str, Any]) -> None:
    """Create tiny deterministic fixtures; guarded and never release-eligible."""

    np = _load_numpy()
    destination.mkdir(parents=True, exist_ok=True)
    swatches = {
        item["id"]: str(item.get("swatch", "#808080"))
        for item in manifest["finishes"]
    }
    size = 16
    yy, xx = np.mgrid[0:size, 0:size]
    for index, finish_id in enumerate(RENDERABLE_FINISH_IDS):
        raw = swatches[finish_id].lstrip("#")
        rgb = tuple(int(raw[offset : offset + 2], 16) for offset in (0, 2, 4))
        paint = np.empty((size, size, 3), dtype=np.uint8)
        for channel, value in enumerate(rgb):
            paint[:, :, channel] = (value + xx * (index + 1) + yy * (channel + 3)) % 256
        spec = np.stack(
            (
                (xx * 17 + index * 7) % 256,
                (yy * 19 + index * 11) % 256,
                ((xx + yy) * 13 + index * 5) % 256,
            ),
            axis=-1,
        ).astype(np.uint8)
        with (destination / f"{finish_id}.npz").open("wb") as handle:
            np.savez_compressed(
                handle,
                schema=np.array(SNAPSHOT_SCHEMA),
                finish_id=np.array(finish_id),
                build_size=np.array([size, size], dtype=np.int32),
                seed=np.array(51, dtype=np.int32),
                paint=paint,
                spec=spec,
            )


def copy_release_snapshots(repo_root: Path, destination: Path) -> None:
    source = repo_root / "demo" / "backend" / "assets" / "snapshots"
    missing = [finish_id for finish_id in RENDERABLE_FINISH_IDS if not (source / f"{finish_id}.npz").is_file()]
    if missing:
        _run_snapshot_exporter(repo_root)
    # [SPB-DEMO-PREVIEW 2026-09-03] Each finish ships its full-size capture plus an optional
    # "<id>@<size>.npz" captured natively at the live-preview resolution.  Both are still an
    # exact allowlist keyed to the 30 reviewed IDs — an unknown stem is a hard build failure.
    def _split(stem: str) -> tuple[str, int | None]:
        if "@" in stem:
            base, _, suffix = stem.rpartition("@")
            if suffix.isdigit():
                return base, int(suffix)
        return stem, None

    actual = {path.stem: _split(path.stem) for path in source.glob("*.npz")} if source.is_dir() else {}
    expected_ids = set(RENDERABLE_FINISH_IDS)
    actual_ids = {base for base, _ in actual.values()}
    if actual_ids != expected_ids:
        missing_after = sorted(expected_ids - actual_ids)
        unexpected = sorted(actual_ids - expected_ids)
        raise StageBuildError(
            f"Snapshot source must contain exactly 30 reviewed NPZs; "
            f"missing={missing_after}, unexpected={unexpected}"
        )
    for finish_id in RENDERABLE_FINISH_IDS:
        source_file = source / f"{finish_id}.npz"
        validate_snapshot(source_file, finish_id)
        _copy_file(source_file, destination / f"{finish_id}.npz")
    for stem, (base, preview_size) in sorted(actual.items()):
        if preview_size is None:
            continue
        companion = source / f"{stem}.npz"
        validate_snapshot(companion, base, expected_size=preview_size)
        _copy_file(companion, destination / f"{stem}.npz")


def copy_release_thumbnails(repo_root: Path, destination: Path) -> None:
    """Copy the 29 picker thumbnails plus the authorized Fracture shortcut thumbnail."""
    source = repo_root / "demo" / "backend" / "assets" / "thumbnails"
    for finish_id in RENDERABLE_FINISH_IDS:
        source_file = source / f"{finish_id}.png"
        if not source_file.is_file():
            raise StageBuildError(f"Required demo thumbnail is missing: {source_file}")
        _copy_file(source_file, destination / source_file.name)


def _wrapper_source() -> str:
    return '''"""Packaged entrypoint for the isolated SHOKK DEMO backend."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from backend.app import create_app


ROOT = Path(__file__).resolve().parent


def parse_args():
    parser = argparse.ArgumentParser(description="Run the local SHOKK DEMO service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=59886)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.host != "127.0.0.1":
        raise SystemExit("SHOKK DEMO only listens on 127.0.0.1")
    if args.port != 59886:
        raise SystemExit("SHOKK DEMO uses the isolated port 59886")
    runtime_root = Path(
        os.environ.get("SPB_DEMO_USER_DATA", ROOT / ".runtime")
    ).expanduser().resolve() / "Runtime"
    app = create_app(
        manifest_path=ROOT / "product-manifest.json",
        frontend_dir=ROOT / "frontend",
        asset_dir=ROOT / "assets",
        runtime_dir=runtime_root,
        starter_psd=ROOT / "assets" / "starter" / "SPB ARCA Chevy V6.psd",
    )
    if args.check:
        with app.test_client() as client:
            response = client.get("/build-check")
            payload = response.get_json(silent=True) or {}
        snapshots = payload.get("snapshot_inventory") or {}
        if (
            response.status_code != 200
            or payload.get("product") != "shokk-demo"
            or payload.get("release_ready") is not True
            or snapshots.get("expected") != 30
            or snapshots.get("present") != 30
        ):
            raise SystemExit("Packaged demo backend self-check failed: " + json.dumps(payload))
        print(json.dumps({"ok": True, "product": "shokk-demo"}))
        return
    app.run(host=args.host, port=args.port, debug=False, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
'''


def _write_wrapper(server_root: Path) -> None:
    wrapper = server_root / "demo_server.py"
    wrapper.write_text(_wrapper_source(), encoding="utf-8", newline="\n")


def _iter_files(root: Path) -> Iterable[Path]:
    return (path for path in sorted(root.rglob("*")) if path.is_file())


def _validate_python_imports(path: Path) -> None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        raise StageBuildError(f"Cannot audit Python source {path}: {exc}") from exc
    for node in ast.walk(tree):
        imported: list[str] = []
        if isinstance(node, ast.Import):
            imported = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported = [node.module]
        for module in imported:
            if module.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
                raise StageBuildError(f"Forbidden paid/runtime import {module!r} in {path}")


def validate_stage_tree(server_root: Path, *, test_python_omitted: bool) -> None:
    top_level = {path.name for path in server_root.iterdir()}
    expected_top_level = {
        "demo_server.py",
        "product-manifest.json",
        "backend",
        "frontend",
        "assets",
    }
    if not test_python_omitted:
        expected_top_level.add("python")
    unexpected_top_level = top_level - expected_top_level - {"inventory.json"}
    missing_top_level = expected_top_level - top_level
    if unexpected_top_level or missing_top_level:
        raise StageBuildError(
            "Top-level stage entries differ from the allowlist; "
            f"missing={sorted(missing_top_level)}, unexpected={sorted(unexpected_top_level)}"
        )

    backend_files = {
        path.relative_to(server_root / "backend").as_posix()
        for path in _iter_files(server_root / "backend")
    }
    if backend_files != set(BACKEND_FILES):
        raise StageBuildError("Staged backend does not match its explicit runtime file allowlist")
    frontend_files = {
        path.relative_to(server_root / "frontend").as_posix()
        for path in _iter_files(server_root / "frontend")
    }
    if frontend_files != set(FRONTEND_FILES):
        raise StageBuildError("Staged frontend does not match its explicit file allowlist")
    validate_frontend_module_closure(server_root / "frontend")

    expected_snapshots = {f"{finish_id}.npz" for finish_id in RENDERABLE_FINISH_IDS}
    snapshot_dir = server_root / "assets" / "snapshots"
    found_snapshots = {path.name for path in snapshot_dir.glob("*.npz")}
    allowed_preview = {
        f"{finish_id}@{size}.npz"
        for finish_id in RENDERABLE_FINISH_IDS
        for size in (1024, 512, 256)
    }
    if not expected_snapshots <= found_snapshots or not (found_snapshots - expected_snapshots) <= allowed_preview:
        raise StageBuildError("Staged snapshot filenames do not match the exact 30-ID allowlist")
    expected_thumbnails = {f"{finish_id}.png" for finish_id in RENDERABLE_FINISH_IDS}
    thumbnail_dir = server_root / "assets" / "thumbnails"
    found_thumbnails = {path.name for path in thumbnail_dir.glob("*.png")}
    if found_thumbnails != expected_thumbnails:
        raise StageBuildError("Staged thumbnail filenames do not match the exact 30-ID render allowlist")
    psd_files = list(server_root.rglob("*.psd"))
    if psd_files != [server_root / "assets" / "starter" / STARTER_FILENAME]:
        raise StageBuildError("Stage must contain exactly the approved starter PSD")
    if not test_python_omitted and not (server_root / "python" / "python.exe").is_file():
        raise StageBuildError("Portable Python runtime is missing")
    if not test_python_omitted:
        python_root = server_root / "python"
        python_root_files = {path.name for path in python_root.iterdir() if path.is_file()}
        if python_root_files != set(PYTHON_ROOT_FILES):
            raise StageBuildError("Portable Python root does not match its explicit file allowlist")
        python_root_dirs = {path.name for path in python_root.iterdir() if path.is_dir()}
        if python_root_dirs != {"Lib"}:
            raise StageBuildError("Portable Python may contain only the allowlisted Lib directory")
        lib_entries = {path.name for path in (python_root / "Lib").iterdir()}
        if lib_entries != {"site-packages"}:
            raise StageBuildError("Portable Python Lib may contain only site-packages")
        site_entries = {
            path.name for path in (python_root / "Lib" / "site-packages").iterdir()
        }
        if site_entries != set(PYTHON_SITE_PACKAGES):
            raise StageBuildError("Portable site-packages does not match its explicit allowlist")
        for path in _iter_files(python_root / "Lib" / "site-packages"):
            relative = path.relative_to(python_root / "Lib" / "site-packages")
            lower_parts = tuple(part.lower() for part in relative.parts)
            legal_notice = "license" in path.name.lower() or "licenses" in lower_parts
            if PYTHON_PRUNED_DIR_NAMES.intersection(lower_parts[:-1]) and not legal_notice:
                raise StageBuildError(f"Portable dependency test/docs directory leaked: {relative.as_posix()}")
            if path.suffix.lower() in PYTHON_PRUNED_SUFFIXES and not legal_notice:
                raise StageBuildError(f"Portable dependency documentation leaked: {relative.as_posix()}")

    for path in _iter_files(server_root):
        relative = path.relative_to(server_root)
        lower_parts = {part.lower() for part in relative.parts}
        lower_name = path.name.lower()
        if lower_parts & FORBIDDEN_PATH_PARTS:
            raise StageBuildError(f"Forbidden path in stage: {relative.as_posix()}")
        if lower_name in FORBIDDEN_FILENAMES:
            raise StageBuildError(f"Forbidden paid source in stage: {relative.as_posix()}")
        if path.suffix.lower() in FORBIDDEN_EXTENSIONS:
            raise StageBuildError(f"Forbidden file extension in stage: {relative.as_posix()}")
        if path.suffix.lower() == ".py":
            _validate_python_imports(path)


def _write_inventory(server_root: Path, manifest: dict[str, Any], *, test_build: bool) -> Path:
    inventory_path = server_root / "inventory.json"
    files = []
    for path in _iter_files(server_root):
        if path == inventory_path:
            continue
        relative = path.relative_to(server_root).as_posix()
        files.append(
            {
                "path": relative,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    payload = {
        "schema": "spb-demo-stage-inventory/1",
        "product": "shokk-demo",
        "version": manifest["product"]["version"],
        "build_id": manifest["product"]["build_id"],
        "test_build": bool(test_build),
        "inventory_self_excluded": True,
        "visible_finish_ids": list(VISIBLE_FINISH_IDS),
        "renderable_finish_ids": list(RENDERABLE_FINISH_IDS),
        "files": files,
    }
    inventory_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return inventory_path


def _run_portable_self_check(server_root: Path) -> None:
    python = server_root / "python" / "python.exe"
    wrapper = server_root / "demo_server.py"
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "SPB_DEMO": "1",
        }
    )
    with tempfile.TemporaryDirectory(prefix="shokk-demo-self-check-") as temporary:
        environment["SPB_DEMO_USER_DATA"] = temporary
        completed = subprocess.run(
            [str(python), str(wrapper), "--check"],
            cwd=server_root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown self-check error").strip()
        raise StageBuildError(f"Staged portable runtime self-check failed: {detail[-4000:]}")


def build_stage(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    output: Path = DEFAULT_OUTPUT,
    test_mode: bool = False,
    synthetic_snapshots: bool = False,
    skip_python: bool = False,
    starter_source: Path = DEFAULT_STARTER,
    starter_sha256: str = STARTER_SHA256,
    starter_size: int | None = STARTER_SIZE,
) -> Path:
    if (synthetic_snapshots or skip_python) and not test_mode:
        raise StageBuildError("Synthetic snapshots and Python omission are test-only")
    repo = repo_root.resolve()
    stage_root = validate_output_path(repo, output, test_mode=test_mode)
    manifest_source = repo / "demo" / "product-manifest.json"
    manifest = _read_manifest(manifest_source)
    validate_manifest(manifest)
    _validate_starter(
        starter_source.resolve(),
        expected_sha256=starter_sha256,
        expected_size=starter_size,
    )

    # This is the only recursive deletion.  Its exact target was proven above.
    if stage_root.exists() and not stage_root.is_dir():
        raise StageBuildError(f"Stage output exists but is not a directory: {stage_root}")
    if stage_root.exists():
        shutil.rmtree(stage_root)
    server_root = stage_root / "server"
    server_root.mkdir(parents=True)

    copy_runtime_sources(repo, server_root)
    _write_wrapper(server_root)
    _copy_file(
        starter_source.resolve(),
        server_root / "assets" / "starter" / STARTER_FILENAME,
    )
    snapshot_destination = server_root / "assets" / "snapshots"
    if synthetic_snapshots:
        _make_synthetic_snapshots(snapshot_destination, manifest)
    else:
        copy_release_snapshots(repo, snapshot_destination)
    copy_release_thumbnails(repo, server_root / "assets" / "thumbnails")
    if skip_python:
        # Intentionally no marker file: a test stage should make the omission
        # obvious by the absent directory and cannot be mistaken for release.
        pass
    else:
        copy_portable_python(repo, server_root)

    if not skip_python:
        _run_portable_self_check(server_root)
    validate_stage_tree(server_root, test_python_omitted=skip_python)
    inventory = _write_inventory(server_root, manifest, test_build=test_mode)
    return inventory


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--test-synthetic-snapshots", action="store_true")
    parser.add_argument("--test-skip-python", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    requested_test_mode = bool(args.test_synthetic_snapshots or args.test_skip_python)
    test_mode_enabled = os.environ.get("SHOKK_DEMO_STAGE_TEST_MODE") == "1"
    if requested_test_mode and not test_mode_enabled:
        print(
            "SHOKK DEMO stage failed: test switches require SHOKK_DEMO_STAGE_TEST_MODE=1",
            file=sys.stderr,
        )
        return 2
    try:
        inventory = build_stage(
            output=args.output,
            test_mode=requested_test_mode,
            synthetic_snapshots=args.test_synthetic_snapshots,
            skip_python=args.test_skip_python,
        )
    except (StageBuildError, OSError, subprocess.SubprocessError) as exc:
        print(f"SHOKK DEMO stage failed: {exc}", file=sys.stderr)
        return 1
    payload = json.loads(inventory.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "ok": True,
                "stage": str(inventory.parent.parent),
                "files": len(payload["files"]),
                "snapshots": len(payload["renderable_finish_ids"]),
                "test_build": payload["test_build"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
