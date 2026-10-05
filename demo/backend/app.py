"""Flask-compatible, paid-engine-free backend for SHOKK DEMO."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import string
import tempfile
import threading
import time
from typing import Any, Mapping
from urllib.parse import quote
import uuid

from flask import Flask, Response, jsonify, request, send_file, send_from_directory
from PIL import Image

from .catalog import DemoCatalog
from .compositor import DemoCompositor, SnapshotStore
from .images import (
    MAX_SOURCE_BYTES,
    SourceCache,
    SourceImageError,
    load_source_image,
    png_bytes,
    png_data_url,
)
from .psd_support import create_psd_blueprint
from .recipe import build_render_recipe
from .validation import DemoRequestError, validate_render_request


BACKEND_DIR = Path(__file__).resolve().parent
DEMO_DIR = BACKEND_DIR.parent
DEFAULT_MANIFEST = DEMO_DIR / "product-manifest.json"
DEFAULT_FRONTEND = DEMO_DIR / "frontend"
DEFAULT_ASSET_DIR = BACKEND_DIR / "assets"
SAFE_JOB = re.compile(r"^render_[0-9]{8,20}_[A-Za-z0-9_-]{8,80}$")
SAFE_FILE = re.compile(r"^[A-Za-z0-9_. -]{1,180}$")
FLAT_SOURCE_EXTENSIONS = {".tga", ".png", ".jpg", ".jpeg"}
CONFIG_KEYS = {
    "iracing_id",
    "live_link_enabled",
    "active_car",
    "use_custom_number",
    "car_paths",
    "source_paint_path",
    "output_dir",
}


def _default_runtime_dir() -> Path:
    env = os.environ.get("SHOKK_DEMO_RUNTIME_DIR")
    if env:
        return Path(env).expanduser().resolve()
    demo_user_data = os.environ.get("SPB_DEMO_USER_DATA")
    if demo_user_data:
        return (Path(demo_user_data).expanduser() / "server-runtime").resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return (Path(local_app_data) / "Shokker Paint Booth" / "SHOKK DEMO").resolve()
    return (Path(tempfile.gettempdir()) / "shokk-demo-runtime").resolve()


def _as_path(value: str | Path | None, default: Path) -> Path:
    return Path(value).expanduser().resolve() if value is not None else default.resolve()


def create_app(
    test_config: Mapping[str, Any] | None = None,
    *,
    manifest_path: str | Path | None = None,
    frontend_dir: str | Path | None = None,
    asset_dir: str | Path | None = None,
    runtime_dir: str | Path | None = None,
    starter_psd: str | Path | None = None,
) -> Flask:
    """Create the isolated demo app.

    All path parameters are injectable so the Electron stage and focused tests
    can use the exact same runtime without importing the paid server.
    """

    app = Flask("shokk_demo", static_folder=None)
    app.config.update(
        MAX_CONTENT_LENGTH=90 * 1024 * 1024,
        JSON_SORT_KEYS=False,
        DEMO_LAUNCH_TOKEN=os.environ.get("SPB_DEMO_LAUNCH_TOKEN", "").strip(),
        DEMO_SERVER_PORT=int(os.environ.get("SPB_DEMO_PORT", "59886")),
    )
    if test_config:
        app.config.update(dict(test_config))

    catalog = DemoCatalog(_as_path(manifest_path, DEFAULT_MANIFEST))
    ui_dir = _as_path(frontend_dir, DEFAULT_FRONTEND)
    assets = _as_path(asset_dir, DEFAULT_ASSET_DIR)
    runtime = _as_path(runtime_dir, _default_runtime_dir())
    runtime.mkdir(parents=True, exist_ok=True)
    jobs_dir = runtime / "jobs"
    uploads_dir = runtime / "uploads"
    generated_assets_dir = runtime / "assets"
    for directory in (jobs_dir, uploads_dir, generated_assets_dir):
        directory.mkdir(parents=True, exist_ok=True)

    configured_starter = starter_psd or app.config.get("STARTER_PSD")
    starter_path = (
        Path(configured_starter).expanduser().resolve()
        if configured_starter
        else (assets / "starter" / catalog.raw["starter"]["filename"]).resolve()
    )
    allow_synthetic = bool(app.config.get("ALLOW_SYNTHETIC_SNAPSHOTS", False)) or (
        os.environ.get("SHOKK_DEMO_ALLOW_SYNTHETIC") == "1"
    )
    snapshots = SnapshotStore(
        assets / "snapshots", catalog, allow_synthetic=allow_synthetic
    )
    initial_inventory = snapshots.inventory()
    if initial_inventory["missing"] and not allow_synthetic:
        raise RuntimeError(
            "SHOKK DEMO cannot start without all 30 reviewed material snapshots. "
            "Run `python -m demo.backend.build_snapshots --size 2048 --force` "
            "before staging. Missing: "
            + ", ".join(initial_inventory["missing"])
        )
    compositor = DemoCompositor(catalog, snapshots)
    source_cache = SourceCache(limit=4)
    started_at = time.time()
    config_path = runtime / "config.json"
    config_lock = threading.Lock()

    app.extensions["shokk_demo"] = {
        "catalog": catalog,
        "snapshots": snapshots,
        "compositor": compositor,
        "runtime_dir": runtime,
        "frontend_dir": ui_dir,
        "asset_dir": assets,
        "starter_psd": starter_path,
    }

    def resolve_source_path(raw: str) -> Path:
        value = str(raw or "").strip()
        aliases = set(catalog.raw.get("runtime", {}).get("starter_aliases", []))
        starter_relative = str(catalog.raw["starter"].get("relative_path") or "").replace(
            "\\", "/"
        )
        if value in aliases or value.replace("\\", "/") == starter_relative:
            return starter_path
        if not value:
            raise ValueError("Source path is required")
        return Path(os.path.abspath(os.path.expanduser(value))).resolve()

    def load_config() -> dict[str, Any]:
        defaults: dict[str, Any] = {
            "iracing_id": "",
            "live_link_enabled": False,
            "active_car": None,
            "use_custom_number": True,
            "car_paths": {},
            "source_paint_path": catalog.raw["starter"]["uri"],
            "output_dir": "",
        }
        with config_lock:
            if not config_path.is_file():
                return defaults
            try:
                value = json.loads(config_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return defaults
        if isinstance(value, dict):
            defaults.update({key: value[key] for key in CONFIG_KEYS if key in value})
        return defaults

    def save_config(updates: Mapping[str, Any]) -> dict[str, Any]:
        config = load_config()
        for key in CONFIG_KEYS:
            if key not in updates:
                continue
            if key in {"live_link_enabled", "use_custom_number"}:
                config[key] = bool(updates[key])
            elif key == "car_paths":
                value = updates[key]
                if not isinstance(value, Mapping):
                    raise ValueError("car_paths must be an object")
                config[key] = {str(name): str(path) for name, path in value.items()}
            elif key in {"active_car"}:
                config[key] = None if updates[key] is None else str(updates[key])
            else:
                config[key] = str(updates[key] or "")
        payload = json.dumps(config, indent=2, ensure_ascii=False)
        temporary = config_path.with_suffix(".tmp")
        with config_lock:
            temporary.write_text(payload, encoding="utf-8")
            os.replace(temporary, config_path)
        return config

    def ensure_blank_canvas() -> Path:
        path = generated_assets_dir / "blank_canvas_2048_white.tga"
        if not path.is_file():
            Image.new("RGB", (2048, 2048), (255, 255, 255)).save(path, "TGA")
        return path

    def source_from_request(data: Mapping[str, Any]) -> tuple[Image.Image, str, str | None]:
        data_url = data.get("source_data_url") or data.get("paint_image_base64")
        if data_url:
            record = source_cache.remember_data_url(str(data_url))
            return load_source_image(payload=record.payload), "inline", record.token
        token = str(data.get("paint_source_token") or "").strip()
        if token:
            record = source_cache.resolve(token)
            if record is None:
                raise DemoRequestError(
                    "Preview paint source expired; resend source_data_url",
                    "preview_source_missing",
                    "paint_source_token",
                )
            return load_source_image(payload=record.payload), "token", record.token
        raw_path = str(data.get("paint_file") or data.get("source_path") or "")
        path = resolve_source_path(raw_path)
        return load_source_image(path=path), "file", None

    def public_manifest() -> dict[str, Any]:
        value = {
            key: item
            for key, item in catalog.raw.items()
            if key not in {"runtime", "finishes"}
        }
        def finish_payload(finish: Any) -> dict[str, Any]:
            return {
                "id": finish.id,
                "name": finish.name,
                "category": finish.category,
                "kind": finish.kind,
                "swatch": finish.swatch,
                "thumbnail": f"/demo-assets/thumbnails/{finish.id}.png",
            }

        value["finishes"] = [finish_payload(finish) for finish in catalog.visible]
        # From Special is an independent color source, not a second material
        # layer.  It may use every reviewed snapshot, including the one hidden
        # fracture source, without expanding the main 29-card finish picker.
        value["base_color_sources"] = [
            finish_payload(finish) for finish in catalog.finishes.values()
        ]
        return value

    @app.before_request
    def require_local_demo_client():
        port = int(app.config.get("DEMO_SERVER_PORT", 59886))
        allowed_hosts = {
            "127.0.0.1",
            f"127.0.0.1:{port}",
            "localhost",
            f"localhost:{port}",
        }
        if request.host.lower() not in allowed_hosts:
            return jsonify(
                {
                    "error": "Unexpected Host header",
                    "error_code": "invalid_host",
                    "product": "shokk-demo",
                }
            ), 421

        launch_token = str(app.config.get("DEMO_LAUNCH_TOKEN") or "")
        supplied_token = request.headers.get("X-SPB-Demo-Token", "")
        if launch_token and not hmac.compare_digest(supplied_token, launch_token):
            return jsonify(
                {
                    "error": "SHOKK DEMO launch token required",
                    "error_code": "launch_token_required",
                    "product": "shokk-demo",
                }
            ), 401
        return None

    @app.after_request
    def demo_headers(response: Response) -> Response:
        response.headers["X-SPB-Product"] = "shokk-demo"
        if request.path.startswith("/api/") or request.path in {"/health", "/build-check", "/status"}:
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/demo/health")
    def demo_health():
        # Electron readiness contract.  Keep these two fields stable.
        return jsonify({"ok": True, "product": "shokk-demo"})

    @app.get("/health")
    def health():
        return jsonify(
            {
                "ok": True,
                "product": "shokk-demo",
                "version": catalog.raw["product"]["version"],
                "uptime_s": int(time.time() - started_at),
            }
        )

    @app.get("/build-check")
    def build_check():
        inventory = snapshots.inventory()
        return jsonify(
            {
                "status": "running",
                "product": "shokk-demo",
                "build": catalog.raw["product"]["build_id"],
                "version": catalog.raw["product"]["version"],
                "port": int(os.environ.get("SHOKK_DEMO_PORT", 59886)),
                "engine": "SHOKK DEMO Material Snapshot Compositor",
                "pid": os.getpid(),
                "snapshot_inventory": inventory,
                "release_ready": bool(inventory["release_ready"] and starter_path.is_file()),
                "starter_present": starter_path.is_file(),
            }
        )

    @app.get("/status")
    def status():
        payload = catalog.picker_payload()
        config = load_config()
        return jsonify(
            {
                "status": "online",
                "product": "shokk-demo",
                "version": catalog.raw["product"]["version"],
                "build": catalog.raw["product"]["build_id"],
                "pid": os.getpid(),
                "port": int(os.environ.get("SHOKK_DEMO_PORT", 59886)),
                "engine": "SHOKK DEMO Material Snapshot Compositor",
                "capabilities": {
                    "bases": [entry["id"] for entry in payload["bases"]],
                    "patterns": [],
                    "monolithics": [entry["id"] for entry in payload["specials"]],
                    "legacy_finishes": [],
                    "base_count": payload["counts"]["bases"],
                    "pattern_count": 0,
                    "monolithic_count": payload["counts"]["specials"],
                    "combination_count": payload["counts"]["total"],
                    "features": catalog.raw["capabilities"],
                },
                "config": config,
                "license": {"active": True, "key_masked": "DEMO"},
                "gpu": {},
            }
        )

    @app.get("/api/demo-manifest")
    def demo_manifest():
        return jsonify(public_manifest())

    @app.get("/api/finish-data")
    def finish_data():
        payload = catalog.picker_payload()
        filter_type = request.args.get("type")
        if filter_type in {"bases", "patterns", "specials"}:
            return jsonify(
                {"status": "ok", filter_type: payload[filter_type], "count": len(payload[filter_type])}
            )
        return jsonify({"status": "ok", **payload})

    @app.get("/finish-groups")
    def finish_groups():
        payload = catalog.picker_payload()
        return jsonify(
            {
                "status": "ok",
                "groups": payload["groups"],
                "expansion_counts": payload["counts"],
                "total_bases": payload["counts"]["bases"],
                "total_patterns": 0,
                "total_specials": payload["counts"]["specials"],
                "total_fusions": 0,
                "total_combinations": payload["counts"]["total"],
            }
        )

    @app.get("/api/finish-registry-status")
    def finish_registry_status():
        bases = [finish.id for finish in catalog.visible if finish.kind == "base"]
        monos = [finish.id for finish in catalog.visible if finish.kind == "monolithic"]
        registered = bases + monos
        return jsonify(
            {
                "registered": registered,
                "count": len(registered),
                "mono": len(monos),
                "base": len(bases),
                "pattern": 0,
            }
        )

    @app.get("/api/finish-by-id/<finish_id>")
    def finish_by_id(finish_id: str):
        finish = catalog.get(finish_id)
        if finish is None or not finish.visible:
            return jsonify({"error": "Finish not found"}), 404
        return jsonify(
            {
                "id": finish.id,
                "name": finish.name,
                "category": finish.category,
                "kind": finish.kind,
                "swatch": finish.swatch,
            }
        )

    @app.get("/api/default-assets")
    def default_assets():
        blank = ensure_blank_canvas()
        missing = [] if starter_path.is_file() else ["starter_psd"]
        return (
            jsonify(
                {
                    "ok": not missing,
                    "assets": {
                        "starter_psd": str(starter_path) if starter_path.is_file() else None,
                        "starter_uri": catalog.raw["starter"]["uri"],
                        "blank_canvas_tga": str(blank),
                    },
                    "missing": missing,
                }
            ),
            200 if not missing else 500,
        )

    @app.get("/api/blank-canvas")
    def blank_canvas():
        try:
            width = max(64, min(4096, int(request.args.get("width", 2048))))
            height = max(64, min(4096, int(request.args.get("height", 2048))))
            color = str(request.args.get("color", "ffffff")).lstrip("#")
            if len(color) != 6 or any(ch not in string.hexdigits for ch in color):
                raise ValueError("color must be a six-digit hex value")
            rgb = tuple(int(color[index : index + 2], 16) for index in (0, 2, 4))
            path = generated_assets_dir / f"blank_{width}x{height}_{color.lower()}.tga"
            if not path.is_file():
                Image.new("RGB", (width, height), rgb).save(path, "TGA")
            if request.args.get("mode", "").lower() == "json":
                return jsonify(
                    {
                        "ok": True,
                        "path": str(path),
                        "width": width,
                        "height": height,
                        "color": color.lower(),
                    }
                )
            return send_file(path, mimetype="image/tga", as_attachment=True, download_name=path.name)
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/config", methods=["GET", "POST"])
    @app.route("/api/config", methods=["GET", "POST"])
    def config_endpoint():
        if request.method == "GET":
            return jsonify(load_config())
        updates = request.get_json(silent=True)
        if not isinstance(updates, dict) or not updates:
            return jsonify({"error": "Send a JSON object with config fields to update"}), 400
        try:
            config = save_config(updates)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        warnings = [
            f"Path for {name!r} not found: {path}"
            for name, path in config.get("car_paths", {}).items()
            if path and not Path(path).is_dir()
        ]
        result: dict[str, Any] = {"success": True, "config": config}
        if warnings:
            result["warnings"] = warnings
        return jsonify(result)

    @app.post("/check-file")
    def check_file():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or "path" not in data:
            return jsonify({"error": "Missing 'path' field in request"}), 400
        try:
            path = resolve_source_path(str(data["path"]))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        exists = path.exists()
        is_file = path.is_file() if exists else False
        size = path.stat().st_size if is_file else 0
        return jsonify(
            {
                "path": str(path),
                "exists": exists,
                "is_file": is_file,
                "size": size,
                "size_human": f"{size / 1024:.0f} KB" if size else "0",
            }
        )

    @app.post("/browse-files")
    def browse_files():
        data = request.get_json(silent=True)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400
        browse_path = str(data.get("path") or "").strip()
        raw_filter = str(data.get("filter") or "").lower()
        suffixes = tuple(part.strip() for part in raw_filter.split(",") if part.strip())
        if not browse_path:
            drives = []
            for letter in string.ascii_uppercase:
                candidate = Path(f"{letter}:/")
                if candidate.exists():
                    drives.append({"name": f"{letter}:", "path": str(candidate), "type": "drive"})
            quick_navs = [
                {"name": "SHOKK DEMO Starter", "path": str(starter_path.parent), "type": "shortcut"}
            ]
            return jsonify({"path": "", "drives": drives, "quick_navs": quick_navs, "items": []})
        path = Path(os.path.abspath(os.path.expanduser(browse_path))).resolve()
        if not path.is_dir():
            return jsonify({"error": f"Not a directory: {path}"}), 400
        folders = []
        files = []
        try:
            for entry in path.iterdir():
                if entry.name.startswith("."):
                    continue
                if entry.is_dir():
                    folders.append({"name": entry.name, "path": str(entry), "type": "folder"})
                elif entry.is_file() and (not suffixes or entry.name.lower().endswith(suffixes)):
                    files.append(
                        {
                            "name": entry.name,
                            "path": str(entry),
                            "type": "file",
                            "size": entry.stat().st_size,
                        }
                    )
        except OSError as exc:
            return jsonify({"error": str(exc)}), 403
        folders.sort(key=lambda item: item["name"].lower())
        files.sort(key=lambda item: item["name"].lower())
        items = folders + files[:500]
        parent = path.parent if path.parent != path else None
        return jsonify(
            {
                "path": str(path).replace("\\", "/"),
                "parent": str(parent).replace("\\", "/") if parent else "",
                "items": items,
                "total_folders": len(folders),
                "total_files": len(files),
                "hidden_files": max(0, len(files) - 500),
                "large_dir": len(items) > 300,
                "entry_count": len(folders) + len(files),
            }
        )

    @app.get("/api/file-thumb")
    def file_thumb():
        try:
            path = resolve_source_path(str(request.args.get("path") or ""))
            if not path.is_file():
                return jsonify({"error": "not found"}), 404
            size = max(24, min(512, int(request.args.get("size", 48))))
            image = load_source_image(path=path).convert("RGB")
            edge = min(image.size)
            left = (image.width - edge) // 2
            top = (image.height - edge) // 2
            image = image.crop((left, top, left + edge, top + edge))
            image.thumbnail((size, size), Image.Resampling.BILINEAR)
            return Response(png_bytes(image), mimetype="image/png")
        except FileNotFoundError:
            return jsonify({"error": "not found"}), 404
        except (TypeError, ValueError, SourceImageError) as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/preview-tga")
    def preview_tga():
        try:
            uploaded = request.files.get("file") or request.files.get("paint_file")
            if uploaded is not None and uploaded.filename:
                suffix = Path(uploaded.filename).suffix.lower()
                if suffix not in FLAT_SOURCE_EXTENSIONS:
                    raise SourceImageError(
                        "Browser uploads must be TGA, PNG, JPG, or JPEG files"
                    )
                payload = uploaded.stream.read(MAX_SOURCE_BYTES + 1)
                if not payload or len(payload) > MAX_SOURCE_BYTES:
                    raise SourceImageError(
                        "Browser source upload exceeds the 64 MiB decoded limit"
                    )
                image = load_source_image(payload=payload).convert("RGB")
            else:
                data = request.get_json(silent=True)
                if not isinstance(data, dict) or not data.get("path"):
                    return jsonify({"error": "Missing path or uploaded file"}), 400
                path = resolve_source_path(str(data["path"]))
                if path.suffix.lower() not in FLAT_SOURCE_EXTENSIONS:
                    raise SourceImageError(
                        "Flat source files must be TGA, PNG, JPG, or JPEG"
                    )
                image = load_source_image(path=path).convert("RGB")
            return Response(png_bytes(image), mimetype="image/png")
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        except (ValueError, SourceImageError) as exc:
            return jsonify({"error": str(exc)}), 400

    app.register_blueprint(
        create_psd_blueprint(resolve_source_path=resolve_source_path, upload_dir=uploads_dir)
    )

    @app.post("/preview-render")
    def preview_render():
        started = time.perf_counter()
        data = request.get_json(silent=True)
        try:
            zones = validate_render_request(data, catalog.renderable_ids)
            source, transport, token = source_from_request(data)
            scale = max(0.0625, min(1.0, float(data.get("preview_scale", 1.0))))
            if scale < 1.0:
                source = source.resize(
                    (max(1, round(source.width * scale)), max(1, round(source.height * scale))),
                    Image.Resampling.BILINEAR,
                )
            paint, spec = compositor.render(source, zones)
            paint_payload = png_bytes(paint, compress_level=2)
            spec_payload = png_bytes(spec, compress_level=2)
            response: dict[str, Any] = {
                "success": True,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
                "paint_preview": "data:image/png;base64,"
                + __import__("base64").b64encode(paint_payload).decode("ascii"),
                "spec_preview": "data:image/png;base64,"
                + __import__("base64").b64encode(spec_payload).decode("ascii"),
                "resolution": [paint.width, paint.height],
                "source_transport": transport,
                "paint_sig": hashlib.sha256(paint_payload).hexdigest()[:24],
                "spec_sig": hashlib.sha256(spec_payload).hexdigest()[:24],
            }
            if token:
                response["paint_source_token"] = token
            return jsonify(response)
        except DemoRequestError as exc:
            status_code = 409 if exc.code == "preview_source_missing" else 400
            return jsonify(exc.payload()), status_code
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc), "error_code": "source_not_found"}), 404
        except (SourceImageError, ValueError) as exc:
            return jsonify({"error": str(exc), "error_code": "invalid_source"}), 400
        except Exception as exc:
            app.logger.exception("Demo preview render failed")
            return jsonify({"error": str(exc), "error_code": "render_failed"}), 500

    def safe_output_directory(raw: str) -> Path:
        path = Path(os.path.abspath(os.path.expanduser(raw))).resolve()
        if path == Path(path.anchor):
            raise ValueError("Refusing to use a drive root as the render output directory")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def copy_verified(source: Path, destination: Path) -> None:
        if destination.exists():
            backup = destination.with_name("ORIGINAL_" + destination.name)
            if not backup.exists():
                shutil.copyfile(destination, backup)
        temporary = destination.with_suffix(destination.suffix + ".demo-tmp")
        shutil.copyfile(source, temporary)
        if source.stat().st_size != temporary.stat().st_size:
            temporary.unlink(missing_ok=True)
            raise OSError(f"Output verification failed for {destination.name}")
        os.replace(temporary, destination)

    @app.post("/render")
    def render():
        started = time.perf_counter()
        data = request.get_json(silent=True)
        try:
            zones = validate_render_request(data, catalog.renderable_ids)
            source, transport, token = source_from_request(data)
            paint, spec = compositor.render(source, zones)
            raw_iracing_id = str(data.get("iracing_id") or "00000")
            iracing_id = re.sub(r"[^A-Za-z0-9_-]", "", raw_iracing_id)[:32] or "00000"
            if "use_custom_number" in data:
                use_custom_number = bool(data["use_custom_number"])
            else:
                use_custom_number = bool(data.get("custom_number", True)) and not bool(
                    data.get("sim_stamped_number", False)
                )
            car_prefix = "car_num" if use_custom_number else "car"
            job_id = f"render_{int(time.time())}_{uuid.uuid4().hex[:16]}"
            job_dir = jobs_dir / job_id
            job_dir.mkdir(parents=True, exist_ok=False)
            paint_png = job_dir / "RENDER_paint.png"
            spec_png = job_dir / "RENDER_spec.png"
            paint_tga = job_dir / f"{car_prefix}_{iracing_id}.tga"
            spec_tga = job_dir / f"car_spec_{iracing_id}.tga"
            demo_readme = job_dir / "SHOKK_DEMO_README.txt"
            paint.save(paint_png, "PNG", compress_level=2)
            spec.save(spec_png, "PNG", compress_level=2)
            paint.save(paint_tga, "TGA")
            spec.save(spec_tga, "TGA")
            demo_readme.write_text(
                f"{catalog.raw['branding']['render_credit']}\n\n"
                "Unlock the complete Shokker Paint Booth:\n"
                f"{catalog.raw['branding']['payhip_url']}\n\n"
                "Share your render and get help in Discord:\n"
                f"{catalog.raw['branding']['discord_url']}\n",
                encoding="utf-8",
            )

            preview_urls = {
                paint_png.name: f"/preview/{job_id}/{quote(paint_png.name, safe='')}",
                spec_png.name: f"/preview/{job_id}/{quote(spec_png.name, safe='')}",
            }
            download_urls = {
                paint_tga.stem: f"/download/{job_id}/{quote(paint_tga.name, safe='')}",
                spec_tga.stem: f"/download/{job_id}/{quote(spec_tga.name, safe='')}",
                demo_readme.stem: f"/download/{job_id}/{quote(demo_readme.name, safe='')}",
            }

            output_status = None
            output_dir = str(
                data.get("output_dir")
                or data.get("output_folder")
                or data.get("iracing_car_folder")
                or ""
            ).strip()
            if not output_dir and data.get("live_link"):
                config = load_config()
                output_dir = str(config.get("output_dir") or "").strip()
                if not output_dir and config.get("active_car"):
                    output_dir = str(config.get("car_paths", {}).get(config["active_car"], ""))
            if output_dir:
                target = safe_output_directory(output_dir)
                copy_verified(paint_tga, target / paint_tga.name)
                copy_verified(spec_tga, target / spec_tga.name)
                output_status = {
                    "success": True,
                    "verified": True,
                    "path": str(target),
                    "pushed_files": [paint_tga.name, spec_tga.name],
                    "message": f"Saved 2 files to {target}",
                }

            elapsed_seconds = round(time.perf_counter() - started, 2)
            recipe = build_render_recipe(
                request_data=data,
                zones=zones,
                catalog=catalog,
                job_id=job_id,
                elapsed_seconds=elapsed_seconds,
                source_transport=transport,
                output_status=output_status,
                preview_urls=preview_urls,
                download_urls=download_urls,
                use_custom_number=use_custom_number,
                iracing_id=iracing_id,
            )
            result: dict[str, Any] = {
                "success": True,
                "product": "shokk-demo",
                "job_id": job_id,
                "elapsed_seconds": elapsed_seconds,
                "zone_count": len(zones),
                "wear_level": 0,
                "preview_urls": preview_urls,
                "download_urls": download_urls,
                "source_transport": transport,
                "includes": {"car": True, "helmet": False, "suit": False, "wear": False},
                "links": {
                    "payhip": catalog.raw["branding"]["payhip_url"],
                    "discord": catalog.raw["branding"]["discord_url"],
                },
                "recipe": recipe,
            }
            if token:
                result["paint_source_token"] = token
            if output_status:
                result["output_dir"] = output_status
                if data.get("live_link"):
                    result["live_link"] = dict(output_status)
            return jsonify(result)
        except DemoRequestError as exc:
            status_code = 409 if exc.code == "preview_source_missing" else 400
            return jsonify(exc.payload()), status_code
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc), "error_code": "source_not_found"}), 404
        except (SourceImageError, ValueError) as exc:
            return jsonify({"error": str(exc), "error_code": "invalid_request"}), 400
        except Exception as exc:
            app.logger.exception("Demo full render failed")
            return jsonify({"error": str(exc), "error_code": "render_failed"}), 500

    @app.get("/api/render-status")
    def render_status():
        return jsonify({"status": "idle", "rendering": False, "product": "shokk-demo"})

    def send_job_file(job_id: str, filename: str, *, attachment: bool):
        if not SAFE_JOB.fullmatch(job_id) or not SAFE_FILE.fullmatch(filename):
            return jsonify({"error": "Invalid job path"}), 400
        directory = jobs_dir / job_id
        if not directory.is_dir() or not (directory / filename).is_file():
            return jsonify({"error": "File not found"}), 404
        return send_from_directory(directory, filename, as_attachment=attachment)

    @app.get("/preview/<job_id>/<filename>")
    def preview_file(job_id: str, filename: str):
        return send_job_file(job_id, filename, attachment=False)

    @app.get("/download/<job_id>/<filename>")
    def download_file(job_id: str, filename: str):
        return send_job_file(job_id, filename, attachment=True)

    @app.get("/favicon.ico")
    def favicon():
        return ("", 204)

    @app.get("/demo-assets/thumbnails/<finish_id>.png")
    def finish_thumbnail(finish_id: str):
        finish = catalog.get(finish_id)
        if finish is None:
            return jsonify({"error": "Finish thumbnail not found"}), 404
        thumbnail = assets / "thumbnails" / f"{finish.id}.png"
        if not thumbnail.is_file():
            return jsonify({"error": "Finish thumbnail not found"}), 404
        return send_file(thumbnail, mimetype="image/png", conditional=True, max_age=86400)

    @app.get("/")
    @app.get("/paint-booth-v2.html")
    def index():
        candidate = ui_dir / "paint-booth-v2.html"
        if candidate.is_file():
            return send_file(candidate, mimetype="text/html")
        return Response(
            "<!doctype html><title>SHOKK DEMO</title>"
            "<main><h1>SHOKK DEMO backend is ready.</h1>"
            "<p>The staged frontend has not been copied yet.</p></main>",
            mimetype="text/html",
        )

    @app.get("/<path:filename>")
    def static_file(filename: str):
        candidate = (ui_dir / filename).resolve()
        try:
            candidate.relative_to(ui_dir)
        except ValueError:
            return jsonify({"error": "Invalid static path"}), 400
        if not candidate.is_file():
            return jsonify({"error": "Not found"}), 404
        return send_file(candidate)

    return app


def main() -> None:
    app = create_app()
    port = int(os.environ.get("SHOKK_DEMO_PORT", 59886))
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
