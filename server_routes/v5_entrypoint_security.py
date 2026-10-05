"""Fail-closed security and runtime-identity bootstrap for ``server_v5``.

``server_v5`` owns a distinct Flask application.  It inherits URL rules from
``server.py``, but Flask request hooks are app-local, so the V5 entrypoint must
install its own origin guard, external-write guard, and identity response hook.
Keeping this bootstrap separate from observability ensures that disabling crash
logging can never disable security.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Optional
from urllib.parse import urlparse

from flask import has_request_context, jsonify, request

from server_routes.request_security import install_spb_origin_guard
from server_routes.runtime_identity import build_runtime_identity
from server_routes.write_security import external_write_denial


_installed_apps: "set[int]" = set()


def install_v5_entrypoint_security(
    app: Any,
    *,
    logger=None,
    server_dir: Optional[str] = None,
) -> bool:
    """Install V5-only security hooks, raising if installation cannot finish.

    Returns ``True`` on the first successful installation and ``False`` when
    the same application is already protected.  Callers must let exceptions
    abort startup: a partially protected V5 process is not a valid runtime.
    """
    if app is None:
        raise ValueError("server_v5 security requires a Flask app")
    app_id = id(app)
    if app_id in _installed_apps:
        return False

    from config import CFG

    root = os.path.realpath(os.path.abspath(server_dir or CFG.ROOT_DIR))
    output_root = os.path.realpath(os.path.abspath(CFG.OUTPUT_DIR))
    started_at = time.time()
    base_identity = build_runtime_identity(
        canonical_root=root,
        server_path=os.path.join(root, "server.py"),
        launcher_path=os.path.join(root, "server_v5.py"),
        version=CFG.VERSION,
        port=CFG.PORT,
        started_at=started_at,
        external_writes_disabled=bool(os.environ.get("SPB_NO_LIVE_LINK")),
    )

    def runtime_identity():
        payload = dict(base_identity)
        payload["pid"] = os.getpid()
        payload["external_writes_disabled"] = bool(
            os.environ.get("SPB_NO_LIVE_LINK")
        )
        if has_request_context():
            payload["port"] = int(urlparse(request.host_url).port or CFG.PORT)
        return payload

    app.config["SPB_RUNTIME_IDENTITY_GETTER"] = runtime_identity
    install_spb_origin_guard(app, logger=logger)

    @app.before_request
    def _guard_v5_owned_external_routes():
        path = request.path
        method = request.method
        target = operation = None
        if path == "/api/finish-packs/install" and method == "POST":
            appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
            target = os.path.join(
                appdata, "ShokkerPaintBooth", "asset_packs", "reference_textures"
            )
            operation = "finish-pack-install"
        elif method == "POST" and (
            path
            in {
                "/api/projects/save",
                "/api/projects/save/start",
                "/api/projects/delete",
            }
            or path.startswith(
                (
                    "/api/projects/save/chunk/",
                    "/api/projects/save/commit/",
                    "/api/projects/save/abort/",
                )
            )
        ):
            target = os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "Shokker Paint Booth",
                "SPB Projects",
            )
            operation = "project-storage"
        elif path.startswith("/api/user-imports"):
            get_write_exact = {
                "/api/user-imports",
                "/api/user-imports/dna-presets",
                "/api/user-imports/export-all",
            }
            writes = method in {"POST", "PUT", "PATCH", "DELETE"}
            writes = writes or path in get_write_exact or path.startswith(
                (
                    "/api/user-imports/dna-style-thumb/",
                    "/api/user-imports/export/",
                )
            )
            if writes:
                target = os.environ.get("SPB_USER_IMPORTS_DIR") or os.path.join(
                    os.environ.get("APPDATA") or os.path.expanduser("~"),
                    "ShokkerPaintBooth",
                    "user_imports",
                )
                operation = "user-import-storage"
        elif path.startswith("/api/workbench/"):
            target = os.path.join(root, "_workbench")
            operation = "workbench-storage"
        if target is None:
            return None
        denial = external_write_denial(
            target,
            operation,
            owned_root=output_root,
            logger=logger,
        )
        if denial:
            return jsonify(denial), 403
        return None

    @app.after_request
    def _attach_v5_runtime_identity(response):
        if request.path not in {"/build-check", "/status"} or not response.is_json:
            return response
        payload = response.get_json(silent=True)
        if not isinstance(payload, dict):
            return response
        payload.update(runtime_identity())
        response.set_data(json.dumps(payload, separators=(",", ":")))
        return response

    _installed_apps.add(app_id)
    return True
