"""Shokker Engine V5 -- Local Flask Server (main entry point).

V5 wires the modular :mod:`engine` package + :mod:`config` singleton, inherits
legacy route handlers from :mod:`server`, and exposes the V5-specific
``/api/registry-check``, ``/api/finish-data``, ``/api/health`` and
``/build-check`` endpoints.

Run
---
    python server_v5.py                       # Default: http://localhost:59876
    SHOKKER_PORT=59877 python server_v5.py    # Secondary/dev port
    SHOKKER_DEV=1 python server_v5.py         # Hot reload + verbose logging
    SHOKKER_NO_CLEAN=1 python server_v5.py    # Explicit secondary/dev instance

Startup sequence
----------------
1. Clear ``__pycache__`` (stale .pyc protection after auto-updates).
2. Import :data:`config.CFG` (applies env overrides).
3. Import V5 engine registries and patch the legacy engine to use them.
4. Wire UI-catalog patterns/monolithics to family fallbacks.
5. Build the Flask app, configure rotating logs.
6. Inherit unmodified routes from ``server.py``.
7. Run :func:`server_health.run_startup_checks`.
8. Start the local-only WSGI listeners.

Cross-module dependencies
-------------------------
* :mod:`config`             -- paths, port, debug flag.
* :mod:`engine.registry`    -- V5 BASE/PATTERN/MONOLITHIC/FUSION registries.
* :mod:`shokker_engine_v2`  -- legacy pipeline (patched to use V5 registries).
* :mod:`server`             -- provides inherited route handlers.
* :mod:`server_health`      -- startup/liveness checks.

This module intentionally keeps the big import-side-effect registry patching
at module top-level; do not wrap it in ``if __name__``  blocks or the child
route handlers (from ``server.py``) will see the wrong dicts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, request, jsonify, send_file, Response, send_from_directory
from flask_cors import CORS
import os
import time
import json
import shutil
import logging
import sys
import traceback
import io
import base64
import socket


# Refuse accidental duplicate production launches before importing the large
# registries/models below.  A second direct ``python server_v5.py`` used to
# allocate several gigabytes before discovering that the live SPB server
# already owned port 59876.  ``SHOKKER_NO_CLEAN=1`` remains the explicit escape
# hatch for intentional secondary/dev instances.
_SPB_SINGLE_INSTANCE_MUTEX = None


def _guard_single_instance_early() -> None:
    global _SPB_SINGLE_INSTANCE_MUTEX

    if __name__ != "__main__" or os.environ.get("SHOKKER_NO_CLEAN", "0") == "1":
        return

    port = int(os.environ.get("SHOKKER_PORT", "59876"))

    # Fast path for an already-running, healthy SPB server.  This also protects
    # launches made while an older build (without the mutex below) is running.
    try:
        from urllib.request import urlopen

        with urlopen(f"http://127.0.0.1:{port}/health", timeout=0.75) as response:
            payload = json.loads(response.read(4096).decode("utf-8", errors="replace"))
        if response.status == 200 and payload.get("ok") is True:
            print(f"[Startup] SPB is already healthy on port {port}; duplicate launch cancelled.")
            raise SystemExit(0)
    except SystemExit:
        raise
    except Exception:
        pass

    # Cover the race where two launches begin before either one has bound the
    # HTTP port.  Keep the handle alive for the lifetime of this process.
    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            create_mutex = kernel32.CreateMutexW
            create_mutex.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
            create_mutex.restype = ctypes.c_void_p
            handle = create_mutex(None, False, f"Local\\ShokkerPaintBoothV5_{port}")
            if handle and ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
                kernel32.CloseHandle(ctypes.c_void_p(handle))
                print(f"[Startup] SPB port {port} is already starting; duplicate launch cancelled.")
                raise SystemExit(0)
            _SPB_SINGLE_INSTANCE_MUTEX = handle
        except SystemExit:
            raise
        except Exception as exc:
            print(f"[Startup] Single-instance mutex unavailable: {exc}")


_guard_single_instance_early()

# Track startup timing so we can log total boot duration on __main__.
_STARTUP_T0: float = time.perf_counter()

#: Publicly exported names from this module (for ``from server_v5 import *``
#: and documentation tooling).
__all__ = [
    "app",
    "logger",
    "load_license",
    "save_license",
    "validate_license_key",
    "load_config",
    "save_config",
    "full_render_pipeline",
    "preview_render",
    "render_swatch",
]

# ================================================================
# CLEAR STALE __pycache__ ON EVERY STARTUP
# Prevents cached .pyc bytecode from loading old function signatures
# after code updates (auto-updater changes .py but not .pyc)
# ================================================================
def _clear_pycache() -> int:
    """Remove stale ``__pycache__`` directories under the module root.

    Auto-updaters change ``.py`` files but can leave old ``.pyc`` bytecode
    behind, leading to mysterious AttributeErrors after an update. Clearing
    at startup is cheap and robust.

    Returns:
        Count of directories removed (``0`` if everything was clean).
    """
    _root = os.path.dirname(os.path.abspath(__file__))
    _cleared = 0
    for dirpath, dirnames, _filenames in os.walk(_root):
        if '__pycache__' in dirnames:
            _cache_dir = os.path.join(dirpath, '__pycache__')
            try:
                shutil.rmtree(_cache_dir)
                _cleared += 1
            except OSError:
                # Directory locked by a concurrent process -- not fatal.
                pass
    if _cleared:
        print(f"[Startup] Cleared {_cleared} __pycache__ directories")
    return _cleared

if not os.environ.get("SPB_NO_LIVE_LINK"):
    _clear_pycache()

# ================================================================
# CONFIG - single source of truth for port, paths, debug
# ================================================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG



import engine
import engine.fusions as _fusion_mod
# Also import legacy engine for pipeline functions not yet migrated
import shokker_engine_v2 as _legacy_engine

# The monolith still performs final catalog wiring after a circular V5 registry
# merge. Importing registry globals directly here can capture the stale
# half-built snapshot and make shipping UI IDs fall back to generic looks.
import engine.registry as _registry_mod


def _sync_final_legacy_registries():
    """Make every runtime registry reference point at the final loaded tables."""
    global BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY, FINISH_REGISTRY, FUSION_REGISTRY

    BASE_REGISTRY = _legacy_engine.BASE_REGISTRY
    PATTERN_REGISTRY = _legacy_engine.PATTERN_REGISTRY
    MONOLITHIC_REGISTRY = _legacy_engine.MONOLITHIC_REGISTRY
    FINISH_REGISTRY = getattr(_legacy_engine, "FINISH_REGISTRY", {})
    # Fusions are authored by the modular engine and mirrored into monolithics
    # for legacy rendering. The legacy module has no fusion table; reading it
    # here used to erase only the reporting/API reference and print "Fusions: 0".
    FUSION_REGISTRY = _fusion_mod.FUSION_REGISTRY

    _registry_mod.BASE_REGISTRY = BASE_REGISTRY
    _registry_mod.PATTERN_REGISTRY = PATTERN_REGISTRY
    _registry_mod.MONOLITHIC_REGISTRY = MONOLITHIC_REGISTRY
    _registry_mod.FINISH_REGISTRY = FINISH_REGISTRY
    _registry_mod.FUSION_REGISTRY = FUSION_REGISTRY


_sync_final_legacy_registries()

# [2026-09-05 RETIRED LEDGER] Owner: "MAKE SURE that things that are supposed to be dead and
# buried stay dead and buried." scripts/retired_catalog.json is the one list of retired ids.
# The engine keeps their renderers (saved cars must still paint) but /api/finish-data reports
# them in a top-level "retired" list so no client shows them. Gate: scripts/spb_retired_gate.py
def _load_retired_ids():
    try:
        # NOTE: SERVER_DIR is defined further down this module; use this file's own directory
        # (root in dev, resources/server when packaged -- the ledger is in the sync manifest).
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "retired_catalog.json")
        with open(_p, encoding="utf-8") as _f:
            return frozenset(e["id"] for e in json.load(_f).get("entries", []) if "id" in e)
    except Exception as _ex:
        print(f"[V5] retired ledger not loaded ({_ex}); /api/finish-data will report retired=[]")
        return frozenset()


RETIRED_IDS = _load_retired_ids()
print(f"[V5] Retired ledger: {len(RETIRED_IDS)} ids hidden from every picker (scripts/retired_catalog.json)")

# Startup check: confirm image patterns (e.g. upgraded smile) are in registry for render
if "race_day_gloss" in PATTERN_REGISTRY:
    pass
# Use legacy pipeline render functions (unchanged in V5)
# Note: legacy engine uses full_render_pipeline, not render_zones
full_render_pipeline = _legacy_engine.full_render_pipeline
preview_render = _legacy_engine.preview_render

# Setup Flask
app = Flask(__name__)
CORS(app)

# ================================================================
# PATHS - all from config.py
# ================================================================
SERVER_DIR = CFG.ROOT_DIR
BUNDLE_DIR = CFG.ROOT_DIR
if getattr(sys, 'frozen', False):
    SERVER_DIR = os.environ.get('SHOKKER_EXE_DIR', os.path.dirname(sys.executable))
    BUNDLE_DIR = getattr(sys, '_MEIPASS', SERVER_DIR)

OUTPUT_FOLDER = CFG.OUTPUT_DIR
CONFIG_FILE = CFG.CONFIG_FILE
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ── Rotating log handler - prevents server_log.txt growing forever ──
from logging.handlers import RotatingFileHandler
_log_file = CFG.LOG_FILE

handlers = [logging.StreamHandler()]
try:
    _rot_handler = RotatingFileHandler(_log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    _rot_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    handlers.append(_rot_handler)
except Exception:
    # If the file is locked by a ghost .exe process, do not instantly crash.
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=handlers
)
logger = logging.getLogger('shokker_v5')

# V5 owns a distinct Flask app, so its request guards cannot be inherited with
# URL rules from server.py. Security installation is explicit and fail-closed:
# SPB must never start a partially protected V5 runtime.
try:
    from server_routes.v5_entrypoint_security import install_v5_entrypoint_security
    install_v5_entrypoint_security(app, logger=logger, server_dir=SERVER_DIR)
except Exception as _security_e:
    logger.critical(f"V5 security hooks could not be installed: {_security_e}")
    raise RuntimeError("V5 security hooks are required") from _security_e

# Observability (audit "No observability" gap): install a global sys.excepthook
# (-> local rotating crash log) + a catch-all Flask errorhandler(Exception) that
# logs the full traceback and returns a clean JSON 500 without leaking internals.
# Additive + opt-out-safe (SHOKKER_OBSERVABILITY=0 disables; default on;
# local-only). Observability is independent of the mandatory security bootstrap.
try:
    from server_routes.observability import install_observability, log_startup as _spb_log_startup
    install_observability(app, logger=logger, server_dir=SERVER_DIR)
    _spb_log_startup(
        logger,
        name="server_v5.py",
        version=getattr(CFG, "APP_VERSION", None) or getattr(CFG, "BUILD_TAG", None),
        host=CFG.HOST,
        port=CFG.PORT,
    )
except Exception as _obs_e:  # pragma: no cover - defensive
    logger.warning(f"Observability hooks not installed: {_obs_e}")

# ================================================================
# LICENSE (same as v4)
# ================================================================
LICENSE_FILE = CFG.LICENSE_FILE

#: Required prefix for all valid Shokker license keys.
VALID_LICENSE_PREFIX: str = "SHOKKER-"

#: Number of dash-separated parts expected in a license key (SHOKKER-XXXX-XXXX-XXXX).
_LICENSE_PART_COUNT: int = 4

#: Length of each group after the prefix.
_LICENSE_GROUP_LEN: int = 4


def load_license() -> Tuple[str, bool]:
    """Load license key and activation status from :data:`LICENSE_FILE`.

    Returns:
        Tuple of ``(license_key, activated)``. Empty/False on any error.
    """
    try:
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data.get('license_key', ''), bool(data.get('activated', False))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logging.getLogger('shokker_v5').debug("[license] load failed: %s", e)
    return '', False


def save_license(key: str, activated: bool) -> bool:
    """Persist license state to :data:`LICENSE_FILE` (atomic).

    Args:
        key: License key string (unchecked -- use :func:`validate_license_key` first).
        activated: True if the key has been activated against the server.

    Returns:
        True on success, False if the write failed.
    """
    payload = {
        'license_key': key,
        'activated': bool(activated),
        'timestamp': time.time(),
    }
    tmp_path = LICENSE_FILE + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        # Atomic replace -- safe under concurrent reads.
        os.replace(tmp_path, LICENSE_FILE)
        return True
    except OSError as e:
        logging.getLogger('shokker_v5').warning("[license] save failed: %s", e)
        # Best-effort cleanup.
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return False


def validate_license_key(key: str) -> bool:
    """Check whether ``key`` has the SHOKKER-XXXX-XXXX-XXXX structure.

    This is a *syntactic* check only; server-side activation is still required
    before the app is unlocked.

    Args:
        key: Candidate license key.

    Returns:
        True if the key matches the expected format, False otherwise.
    """
    if not key or not isinstance(key, str):
        return False
    key = key.strip().upper()
    if not key.startswith(VALID_LICENSE_PREFIX):
        return False
    parts = key.split('-')
    if len(parts) != _LICENSE_PART_COUNT:
        return False
    for part in parts[1:]:
        if len(part) != _LICENSE_GROUP_LEN or not part.isalnum():
            return False
    return True


_license_key, _license_active = load_license()

# ================================================================
# CONFIG
# ================================================================

#: Default user-config shape (mirrors ``config.validate_config`` schema).
_DEFAULT_USER_CONFIG: Dict[str, Any] = {
    "iracing_id": "23371",
    "car_paths": {},
    "live_link_enabled": False,
    "active_car": None,
    "use_custom_number": True,
}


def load_config() -> Dict[str, Any]:
    """Load ``shokker_config.json`` with validation + auto-repair.

    Returns:
        A dict guaranteed to contain all keys in :data:`_DEFAULT_USER_CONFIG`.
        Missing file or unreadable JSON returns the defaults.
    """
    if not os.path.exists(CONFIG_FILE):
        return dict(_DEFAULT_USER_CONFIG)
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logging.getLogger('shokker_v5').warning(
            "[config] %s unreadable (%s); using defaults", CONFIG_FILE, e
        )
        return dict(_DEFAULT_USER_CONFIG)
    # Opportunistic validation via the config module (best-effort).
    try:
        from config import repair_config  # local import to avoid cycles
        return repair_config(data)
    except Exception:
        # Fallback: merge with defaults manually.
        merged = dict(_DEFAULT_USER_CONFIG)
        if isinstance(data, dict):
            merged.update(data)
        return merged


def save_config(cfg: Dict[str, Any]) -> bool:
    """Persist the user config atomically.

    Args:
        cfg: Config dict (should validate against :data:`_DEFAULT_USER_CONFIG`).

    Returns:
        True on success, False on write failure.
    """
    if not isinstance(cfg, dict):
        raise TypeError(f"save_config expected dict, got {type(cfg).__name__}")
    tmp_path = CONFIG_FILE + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp_path, CONFIG_FILE)
        return True
    except OSError as e:
        logging.getLogger('shokker_v5').warning("[config] save failed: %s", e)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return False

# ================================================================
# ROUTES - same as server.py but using V5 engine
# ================================================================

@app.errorhandler(404)
def _handle_404(e):
    return jsonify({"error": "not_found", "path": request.path}), 404


@app.route('/assets/patterns/<path:filename>')
def serve_pattern_asset(filename):
    """Serve pattern PNGs from assets/patterns/ for image-based pattern swatches."""
    assets_dir = os.path.join(SERVER_DIR, 'assets', 'patterns')
    if not os.path.isdir(assets_dir):
        return jsonify({"error": "not_found", "path": request.path}), 404
    return send_from_directory(assets_dir, filename)


# OFFLINE_BUILDER 2026-10-04 (SPB Encyclopedia reader, owner: "a true SPB Encyclopedia"): the generic static
# route above only serves .js/.css/.png/.svg/.ico, so article JSON and WebP figures 404'd. Scoped to
# data/encyclopedia/ only (never widen the generic route to .json: config/license files live in the root).
_ENC_EXT = ('.json', '.svg', '.webp', '.png', '.jpg')
@app.route('/data/encyclopedia/<path:filename>')
def serve_encyclopedia_data(filename):
    # owner rule 2026-10-04: hidden features (Easy mode) are listed in scripts/ai_atlas/enc_hidden_features.json; the reader skips them
    if filename == 'hidden_features.json':
        for candidate_dir in [SERVER_DIR, BUNDLE_DIR]:
            hp = os.path.join(candidate_dir, 'scripts', 'ai_atlas', 'enc_hidden_features.json')
            if os.path.isfile(hp):
                resp = send_file(hp, conditional=True, mimetype='application/json')
                resp.headers['Cache-Control'] = 'no-cache'
                return resp
    # Orchestrator 2026-10-05: '_' files are private drafts EXCEPT the search alias overlay the helper/reader fetch
    # (it 404'd in-app, so in-app search lacked the aliases the Node gates used).
    if filename.lower().endswith(_ENC_EXT) and (filename == '_alias_overlay.json' or not filename.replace('\\', '/').split('/')[0].startswith('_')):
        for candidate_dir in [SERVER_DIR, BUNDLE_DIR]:
            enc_dir = os.path.join(candidate_dir, 'data', 'encyclopedia')
            if os.path.isfile(os.path.join(enc_dir, filename)):
                resp = send_from_directory(enc_dir, filename, conditional=True)
                resp.headers['Cache-Control'] = 'no-cache'
                return resp
    return jsonify({"error": "not_found", "path": request.path}), 404


@app.route('/<path:filename>')
def serve_static_assets(filename):
    # [SPB SPEED-TUNEUP 2026-08-30] Was: no-store + ETag/Last-Modified stripped,
    # which forced a FULL re-download of ~10 MB of JS on every app boot
    # (21.3s DOMContentLoaded measured). Now: Cache-Control: no-cache with
    # conditional=True — the browser MUST revalidate every load (so an edited
    # file can never be served stale, same guarantee as before), but an
    # unchanged file answers with a tiny 304 instead of the full body.
    if filename.endswith(('.js', '.css', '.png', '.svg', '.ico')):
        for candidate_dir in [SERVER_DIR, BUNDLE_DIR]:
            fpath = os.path.join(candidate_dir, filename)
            if os.path.exists(fpath):
                resp = send_file(fpath, conditional=True)
                if filename.endswith(('.js', '.css')):
                    resp.headers['Cache-Control'] = 'no-cache'
                return resp
    return jsonify({"error": "not_found", "path": request.path}), 404

@app.route('/')
def serve_paint_booth():
    for candidate in [
        os.path.join(SERVER_DIR, 'paint-booth-v2.html'),
        os.path.join(BUNDLE_DIR, 'paint-booth-v2.html'),
    ]:
        if os.path.exists(candidate):
            try:
                with open(os.path.abspath(candidate), 'r', encoding='utf-8') as hf:
                    html_content = hf.read()
                html_content = html_content.replace(
                    '</head>',
                    f'<!-- V5-SERVED PID={os.getpid()} TIME={time.strftime("%H:%M:%S")} -->\n</head>',
                    1
                )
                return Response(html_content, mimetype='text/html',
                    headers={'Cache-Control': 'no-cache, no-store, must-revalidate'})
            except Exception:
                return send_file(os.path.abspath(candidate), mimetype='text/html')
    return "Paint Booth HTML not found", 404

@app.route('/finish-viewer.html')
def serve_finish_viewer():
    for candidate in [
        os.path.join(SERVER_DIR, 'finish-viewer.html'),
        os.path.join(BUNDLE_DIR, 'finish-viewer.html'),
    ]:
        if os.path.exists(candidate):
            return send_file(os.path.abspath(candidate), mimetype='text/html')
    return "Finish Viewer HTML not found", 404


def _finish_viewer_normalize_spec_to_rgba(spec_result, shape):
    """Accept the engine's different spec contracts and return HxWx4 uint8."""
    import numpy as np

    h, w = shape[:2]

    def plane(value, fallback):
        if value is None:
            return np.full((h, w), float(fallback), dtype=np.float32)
        arr = np.asarray(value, dtype=np.float32)
        if arr.ndim == 0:
            return np.full((h, w), float(arr), dtype=np.float32)
        if arr.shape != (h, w):
            arr = np.resize(arr, (h, w)).astype(np.float32)
        return arr

    if isinstance(spec_result, dict):
        for key in ("spec", "rgba", "result"):
            if key in spec_result:
                return _finish_viewer_normalize_spec_to_rgba(spec_result[key], shape)
        if any(k in spec_result for k in ("M", "R", "CC")):
            m = plane(spec_result.get("M"), 5)
            r = plane(spec_result.get("R"), 100)
            cc = plane(spec_result.get("CC"), 16)
            out = np.empty((h, w, 4), dtype=np.uint8)
            out[:, :, 0] = np.clip(m, 0, 255).astype(np.uint8)
            out[:, :, 1] = np.clip(r, 0, 255).astype(np.uint8)
            out[:, :, 2] = np.clip(cc, 0, 255).astype(np.uint8)
            out[:, :, 3] = 255
            return out
        return None

    if isinstance(spec_result, (tuple, list)) and len(spec_result) >= 2:
        m = plane(spec_result[0], 5)
        r = plane(spec_result[1], 100)
        cc = plane(spec_result[2] if len(spec_result) >= 3 else None, 16)
        out = np.empty((h, w, 4), dtype=np.uint8)
        out[:, :, 0] = np.clip(m, 0, 255).astype(np.uint8)
        out[:, :, 1] = np.clip(r, 0, 255).astype(np.uint8)
        out[:, :, 2] = np.clip(cc, 0, 255).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    if spec_result is None:
        return None

    arr = np.asarray(spec_result, dtype=np.float32)
    if arr.ndim == 3 and arr.shape[0] in (3, 4) and arr.shape[1:3] == (h, w):
        arr = np.moveaxis(arr, 0, -1)
    if arr.ndim == 2:
        out = np.empty((h, w, 4), dtype=np.uint8)
        out[:, :, 0] = np.clip(plane(arr, 5), 0, 255).astype(np.uint8)
        out[:, :, 1] = 100
        out[:, :, 2] = 16
        out[:, :, 3] = 255
        return out
    if arr.ndim == 3 and arr.shape[:2] == (h, w):
        out = np.empty((h, w, 4), dtype=np.uint8)
        chans = arr.shape[2]
        out[:, :, 0] = np.clip(arr[:, :, 0], 0, 255).astype(np.uint8)
        out[:, :, 1] = np.clip(arr[:, :, 1] if chans > 1 else 100, 0, 255).astype(np.uint8)
        out[:, :, 2] = np.clip(arr[:, :, 2] if chans > 2 else 16, 0, 255).astype(np.uint8)
        out[:, :, 3] = np.clip(arr[:, :, 3] if chans > 3 else 255, 0, 255).astype(np.uint8)
        return out
    return None


@app.route('/api/finish-viewer/mono/<finish_id>', methods=['GET'])
def api_finish_viewer_mono(finish_id):
    """Render a monolithic finish as paint/spec PNG data URLs for the material viewer."""
    try:
        import numpy as np
        from PIL import Image as PILImage

        def safe_int(value, default=0):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        size = max(128, min(2048, safe_int(request.args.get("size"), 1024)))
        seed = safe_int(request.args.get("seed"), 9101)

        if finish_id not in MONOLITHIC_REGISTRY:
            return jsonify({"success": False, "error": f"Unknown monolithic: {finish_id}"}), 404

        entry = MONOLITHIC_REGISTRY[finish_id]
        if isinstance(entry, (tuple, list)) and len(entry) >= 2:
            spec_fn, paint_fn = entry[0], entry[1]
        elif isinstance(entry, dict):
            spec_fn, paint_fn = entry.get("spec_fn"), entry.get("paint_fn")
        elif callable(entry):
            spec_fn, paint_fn = None, entry
        else:
            spec_fn, paint_fn = None, None
        if not callable(spec_fn) or not callable(paint_fn):
            return jsonify({"success": False, "error": f"Finish has no viewer renderer: {finish_id}"}), 500

        t0 = time.perf_counter()
        shape = (size, size)
        mask = np.ones(shape, dtype=np.float32)
        spec = _finish_viewer_normalize_spec_to_rgba(spec_fn(shape, mask, seed, 1.0), shape)
        if spec is None:
            return jsonify({"success": False, "error": f"Spec renderer returned no data: {finish_id}"}), 500

        paint = np.ones((size, size, 3), dtype=np.float32) * 0.5
        painted = np.asarray(paint_fn(paint, shape, mask, seed, 1.0, 0.10), dtype=np.float32)
        if painted.ndim == 2:
            painted = np.dstack([painted, painted, painted])
        if painted.ndim == 3 and painted.shape[2] > 3:
            painted = painted[:, :, :3]
        painted_u8 = (np.clip(painted[:, :, :3], 0, 1) * 255).astype(np.uint8)

        def data_url(arr, mode):
            buf = io.BytesIO()
            PILImage.fromarray(arr, mode).save(buf, "PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

        return jsonify({
            "success": True,
            "id": finish_id,
            "size": size,
            "seed": seed,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "paint": data_url(painted_u8, "RGB"),
            "spec": data_url(spec, "RGBA"),
        })
    except Exception as e:
        logger.error("Finish viewer render error %s: %s\n%s", finish_id, e, traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/build-check', methods=['GET'])
def build_check():
    return jsonify({
        "build": CFG.BUILD_TAG,
        "version": CFG.VERSION,
        "status": "running",
        "pid": os.getpid(),
        "engine": "Shokker Engine V5 - Modular Architecture",
        "port": CFG.PORT,
        "debug": CFG.DEBUG,
        "server_dir": SERVER_DIR,
        "v5_modules": ["engine.core", "engine.color_shift", "engine.registry",
                       "engine.fusions", "engine.finishes", "engine.arsenal", "engine.paradigm"],
        "registry_counts": {
            "bases": len(BASE_REGISTRY),
            "patterns": len(PATTERN_REGISTRY),
            "monolithics": len(MONOLITHIC_REGISTRY),
            "fusions": len(FUSION_REGISTRY),
        }
    })


@app.route('/api/finish-data', methods=['GET'])
def api_finish_data():
    """Serve all finish IDs and metadata as JSON.
    The UI can use this to auto-populate finish lists without 10K lines of hardcoded JS.
    """
    def _display_name(fid: str) -> str:
        return str(fid).replace("_", " ").title()

    def _category(kind: str, fid: str) -> str:
        f = str(fid).lower()
        if kind == "base":
            if any(s in f for s in ("chrome", "metal", "aluminum", "steel", "titanium", "gold", "copper", "bronze")):
                return "Metals & Chrome"
            if any(s in f for s in ("candy", "clear", "gloss", "wet", "lacquer", "jelly")):
                return "Gloss & Candy"
            if any(s in f for s in ("matte", "flat", "satin", "frozen", "vantablack", "blackout")):
                return "Matte & Satin"
            if any(s in f for s in ("carbon", "fiber", "weave", "forged")):
                return "Carbon & Composite"
            if any(s in f for s in ("patina", "rust", "oxid", "weather", "worn", "destroyed", "crumbling")):
                return "Weathered & Worn"
            if any(s in f for s in ("chameleon", "iridescent", "color", "spectra", "flip", "prism")):
                return "Color Shift"
            return "Bases"
        if kind == "pattern":
            if any(s in f for s in ("carbon", "weave", "fiber", "forged")):
                return "Carbon & Weave"
            if any(s in f for s in ("flake", "sparkle", "glitter", "star", "dust")):
                return "Sparkle & Flake"
            if any(s in f for s in ("wave", "ripple", "flow", "stripe", "line")):
                return "Lines & Flow"
            if any(s in f for s in ("crack", "shatter", "fracture", "stone", "marble")):
                return "Organic & Stone"
            if any(s in f for s in ("hex", "grid", "pixel", "tile", "circuit")):
                return "Geometric"
            return "Patterns"
        if f.startswith("rs_"):
            return "RISING SUN"
        if f.startswith("vm_"):
            return "VIVA MEXICO"
        if any(s in f for s in ("living_", "electric", "neon", "led", "twinkle")):
            return "Living / Motion"
        if any(s in f for s in ("cs_", "cx_", "pf_", "chameleon", "flip", "shift", "prism", "spectral", "hyper")):
            return "Color Shift"
        if any(s in f for s in ("grad", "ghostg", "clr_", "mc_")):
            return "Color Monolithics"
        if any(s in f for s in ("chrome", "metal", "gold", "copper", "steel", "forged", "damascus")):
            return "Metals & Forged"
        if any(s in f for s in ("sparkle", "star", "flake", "dust")):
            return "Sparkle System"
        if any(s in f for s in ("wave", "ripple", "flow", "haze", "pulse")):
            return "Light Waves"
        if any(s in f for s in ("oil", "glass", "pearl", "thin_film", "iridescent")):
            return "Optical / Film"
        return "Specials"

    def _rows(keys, kind):
        return [{
            "id": fid,
            "name": _display_name(fid),
            "category": _category(kind, fid),
            "type": "monolithic" if kind == "monolithic" else kind,
        } for fid in keys]

    category = request.args.get('category')  # filter: 'bases', 'patterns', 'monolithics'
    rich = request.args.get('viewer') == '1' or request.args.get('rich') == '1'
    if rich:
        bases = _rows(BASE_REGISTRY.keys(), "base")
        patterns = _rows(PATTERN_REGISTRY.keys(), "pattern")
        monolithics = _rows(MONOLITHIC_REGISTRY.keys(), "monolithic")
        cultural_groups = {
            "RISING SUN": [fid for fid in MONOLITHIC_REGISTRY.keys() if str(fid).startswith("rs_")],
            "VIVA MEXICO": [fid for fid in MONOLITHIC_REGISTRY.keys() if str(fid).startswith("vm_")],
        }
        cultural_groups = {key: ids for key, ids in cultural_groups.items() if ids}
        return jsonify({
            "status": "ok",
            "bases": bases,
            "patterns": patterns,
            "monolithics": monolithics,
            "specials": monolithics,
            "groups": {
                "bases": {},
                "patterns": {},
                "specials": cultural_groups,
                "monolithics": cultural_groups,
            },
            "counts": {
                "bases": len(bases),
                "patterns": len(patterns),
                "monolithics": len(monolithics),
                "specials": len(monolithics),
                "total": len(bases) + len(patterns) + len(monolithics),
            },
            "retired": sorted(RETIRED_IDS),
        })
    data = {
        "bases": list(BASE_REGISTRY.keys()),
        "patterns": list(PATTERN_REGISTRY.keys()),
        "monolithics": list(MONOLITHIC_REGISTRY.keys()),
        "fusions": list(FUSION_REGISTRY.keys()),
        "retired": sorted(RETIRED_IDS),
        "counts": {
            "bases": len(BASE_REGISTRY),
            "patterns": len(PATTERN_REGISTRY),
            "monolithics": len(MONOLITHIC_REGISTRY),
            "fusions": len(FUSION_REGISTRY),
        }
    }
    if category and category in data:
        return jsonify({category: data[category], "count": len(data[category])})
    return jsonify(data)


@app.route('/api/registry-check', methods=['GET'])
def api_registry_check():
    """Quick health check - tells you what's loaded and what the CS override count is."""
    cs_keys = [k for k in MONOLITHIC_REGISTRY if k.startswith('cs_')]
    cs_preset = [k for k in cs_keys if k in ['cs_deepocean','cs_solarflare','cs_inferno',
                                               'cs_nebula','cs_cool','cs_warm','cs_mystichrome',
                                               'cs_supernova','cs_candypaint','cs_oilslick',
                                               'cs_rosegold','cs_goldrush','cs_toxic','cs_darkflame']]
    cs_duo = [k for k in cs_keys if '_' in k and k not in cs_preset]
    return jsonify({
        "status": "ok",
        "registry": {
            "bases": len(BASE_REGISTRY),
            "patterns": len(PATTERN_REGISTRY),
            "monolithics": len(MONOLITHIC_REGISTRY),
            "fusions": len(FUSION_REGISTRY),
        },
        "v5_overrides": {
            "cs_presets_v5": len(cs_preset),
            "cs_adaptive_v5": len([k for k in cs_keys if k in ['cs_cool','cs_warm']]),
            "cs_duos_total": len([k for k in MONOLITHIC_REGISTRY if k.startswith('cs_') and
                                   any(c in k for c in ['black','white','red','blue','gold'])]),
        },
        "health": "all_systems_go",
    })


@app.route('/api/health', methods=['GET'])
def api_health():
    """Live health check endpoint - runs startup checks and returns JSON."""
    try:
        from server_health import run_startup_checks
        issues = run_startup_checks(
            BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY,
            output_dir=CFG.OUTPUT_DIR
        )
        return jsonify({
            "status": "ok" if not issues else "degraded",
            "issues": issues,
            "registry": {
                "bases": len(BASE_REGISTRY),
                "patterns": len(PATTERN_REGISTRY),
                "monolithics": len(MONOLITHIC_REGISTRY),
                "fusions": len(FUSION_REGISTRY),
            },
            "cs_v5": True,
            "version": CFG.VERSION,
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/finish-packs', methods=['GET'])
def api_finish_packs():
    """List downloadable Finish Packs + installed status. (finish-pack-downloader 2026-06-07)"""
    try:
        from engine import asset_packs
        return jsonify({"status": "ok", "packs": asset_packs.get_packs_manifest()})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e), "packs": []}), 500


@app.route('/api/finish-packs/install', methods=['POST'])
def api_finish_packs_install():
    """Download + extract a Finish Pack into %APPDATA%/ShokkerPaintBooth/asset_packs.
    install_pack() returns {status:'ok'/'error',...}; the frontend checks status==='ok',
    so success is reported correctly. Never 500s on a bad id. (finish-pack-downloader)"""
    try:
        from engine import asset_packs
        body = request.get_json(silent=True) or {}
        pack_id = (body.get("id") or "").strip()
        if not pack_id:
            return jsonify({"status": "error", "reason": "missing pack id"})
        if not asset_packs.get_pack(pack_id):
            return jsonify({"status": "error", "reason": "unknown pack id: %s" % pack_id})
        result = asset_packs.install_pack(pack_id)  # downloads from manifest url + extracts
        result["installed"] = asset_packs.pack_installed(pack_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "reason": str(e)})


@app.route('/status', methods=['GET'])
def status():
    cfg = load_config()
    return jsonify({
        "status": "online",
        "version": CFG.VERSION,
        "build": CFG.BUILD_TAG,
        "pid": os.getpid(),
        "port": CFG.PORT,
        "engine": "Shokker Engine V5 PRO - 24K Arsenal",
        "server_location": os.path.abspath(__file__),
        "swatch": {"highres_mono": True, "note": "Color Shift Duo renders at 256px then downscale."},
        "_v": "py",  # If you see "_v":"py" you are on the Python server from the V5 folder
        "capabilities": {
            "bases": list(BASE_REGISTRY.keys()),
            "patterns": list(PATTERN_REGISTRY.keys()),
            "monolithics": list(MONOLITHIC_REGISTRY.keys()),
            "legacy_finishes": list(FINISH_REGISTRY.keys()),
            "base_count": len(BASE_REGISTRY),
            "pattern_count": len(PATTERN_REGISTRY),
            "monolithic_count": len(MONOLITHIC_REGISTRY),
            "combination_count": len(BASE_REGISTRY) * len(PATTERN_REGISTRY),
            "features": {
                "helmet_spec": False, "suit_spec": False, "wear_slider": True,
                "export_zip": True, "matching_set": False, "dual_spec": True, "live_link": True,
                "swatch_highres_mono": True,
            },
            # [2026-06-12] engine-feature beacon: introspected from the LOADED
            # module, not from version strings — tells us definitively whether
            # the RUNNING process has a given engine capability (stale-pyc /
            # wrong-copy debugging). Add a marker here for every owner-facing
            # engine feature.
            "engine_features": {
                "spec_channel_shift": "SPEC CHANNEL SHIFT" in (getattr(_legacy_engine.build_multi_zone, "__doc__", "") or "") or "_scs_vals" in _legacy_engine.build_multi_zone.__code__.co_names or "spec_channel_shift" in str(_legacy_engine.build_multi_zone.__code__.co_consts),
                "patternless_physical_blend": "apply_physical_spec_blend" in str(getattr(_legacy_engine.build_multi_zone.__code__, "co_names", ())),
                "ghost_lab": "gl_control" in MONOLITHIC_REGISTRY,
                "mono_overlay_hsb": hasattr(_legacy_engine, "_apply_mono_path_base_overlay"),
            },
        },
        "config": {
            "iracing_id": cfg.get("iracing_id", ""),
            "live_link_enabled": cfg.get("live_link_enabled", False),
            "use_custom_number": cfg.get("use_custom_number", True),  # 2026-10-02: the header restored Custom Number on EVERY launch because /status never carried it (undefined !== false)
            "active_car": cfg.get("active_car"),
            "car_paths": cfg.get("car_paths", {}),
        },
        "license": {
            "active": _license_active,
            "key_masked": (_license_key[:12] + "****") if _license_key else "",
        }
    })

# NOTE: For all other endpoints (/render, /preview-render, /config, etc.)
# these are identical to server.py. Rather than duplicating 1800 lines,
# we import and re-use the route functions from server.py.
# This keeps server_v5.py lean - only the V5 differences are here.
try:
    import server as _v4_server
    # Copy all routes from v4 server except the ones we overrode above
    _skip_routes = {'/', '/build-check', '/status', '/<path:filename>'}
    _inherit_ok = 0
    _inherit_fail = 0
    _inherit_first_err = None
    for rule in _v4_server.app.url_map.iter_rules():
        if str(rule) in _skip_routes:
            continue
        try:
            view_fn = _v4_server.app.view_functions[rule.endpoint]
            app.add_url_rule(
                str(rule),
                rule.endpoint + '_v4',
                view_fn,
                methods=list(rule.methods - {'HEAD', 'OPTIONS'}),
            )
            _inherit_ok += 1
        except Exception as _route_ex:
            _inherit_fail += 1
            if _inherit_first_err is None:
                _inherit_first_err = f"{rule} -> {_route_ex}"
    logger.info(
        "[V5] Inherited %s routes from server.py (%s skipped, first error: %s)",
        _inherit_ok,
        _inherit_fail,
        _inherit_first_err or "none",
    )
    if _inherit_ok < 50:
        raise RuntimeError(
            f"server.py route inheritance too thin ({_inherit_ok} ok); "
            f"first error: {_inherit_first_err}"
        )
except Exception as _ex:
    logger.error(f"[V5] Could not inherit server.py routes: {_ex}")
    raise

# Re-export for tests/scripts - swatch render function (same as /api/swatch uses)
try:
    from server import _render_swatch_bytes as render_swatch
except Exception:
    render_swatch = None

# ================================================================
# STARTUP
# ================================================================
def _spb_can_bind_port(host: str, port: int) -> Tuple[bool, str]:
    """Return whether this process can bind host:port right now."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, int(port)))
        return True, ""
    except OSError as exc:
        return False, str(exc)


def _spb_candidate_ports(preferred: int) -> List[int]:
    candidates = [
        preferred,
        59876, 59877, 59878, 59879,
        60876, 60877, 60878, 60879,
        61876, 62876,
    ]
    seen = set()
    out: List[int] = []
    for port in candidates:
        try:
            port_i = int(port)
        except (TypeError, ValueError):
            continue
        if 1024 <= port_i <= 65535 and port_i not in seen:
            seen.add(port_i)
            out.append(port_i)
    return out


def _spb_pick_runtime_port(preferred: int, host: str, allow_fallback: bool = True) -> int:
    bind_host = host if host and host != "0.0.0.0" else "127.0.0.1"
    candidates = _spb_candidate_ports(preferred) if allow_fallback else [int(preferred)]
    blocked: List[str] = []
    for port in candidates:
        ok, why = _spb_can_bind_port(bind_host, port)
        if ok:
            if port != int(preferred):
                logger.warning(
                    "[V5] Port %s unavailable; using fallback port %s",
                    preferred,
                    port,
                )
                if blocked:
                    logger.warning("[V5] Port fallback details: %s", "; ".join(blocked[:4]))
            return port
        blocked.append(f"{port}: {why}")
    if allow_fallback:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((bind_host, 0))
                port = int(sock.getsockname()[1])
            logger.warning("[V5] Fixed fallback ports unavailable; using ephemeral port %s", port)
            return port
        except OSError:
            pass
    raise OSError(
        f"No usable SPB server port found. Tried: {', '.join(blocked) if blocked else preferred}"
    )


def _spb_write_runtime_port(port: int) -> None:
    try:
        port_root = CFG.OUTPUT_DIR if os.environ.get("SPB_NO_LIVE_LINK") else CFG.ROOT_DIR
        with open(os.path.join(port_root, ".server_port"), "w", encoding="utf-8") as fh:
            fh.write(str(int(port)))
    except Exception as exc:
        logger.warning("[V5] Could not write .server_port: %s", exc)


if __name__ == '__main__':
    # [2026-08-22] A PINNED PORT DEFINES SPB'S TRUSTED ORIGIN.
    # START_SERVER.bat and Electron pin SHOKKER_PORT=59876. Silently falling back
    # changes the browser origin, breaks restart continuity, and can make an unrelated
    # process look like the intended backend. A pinned-port bind failure is therefore
    # fatal and visible, including the Windows-reserved-port case:
    #
    #   OSError: [WinError 10013] An attempt was made to access a socket in a way
    #            forbidden by its access permissions
    #
    # That is Windows' Hyper-V stack (Docker Desktop / WSL / BlueStacks) reserving a
    # block of the dynamic port range at boot. The blocks MOVE on every restart, so one
    # morning 59876 simply belongs to Hyper-V and no amount of killing SPB processes
    # helps — nothing is listening, the OS just refuses the bind. SPB_FRESH_START could
    # never fix it because there was nothing to kill.
    #
    # Development launches without SHOKKER_PORT may still choose a free port. A pinned
    # production launch never does. The requested port is written only after a
    # successful selection below.
    _env_pinned_port = bool(os.environ.get("SHOKKER_PORT"))
    _pin_ok, _pin_why = _spb_can_bind_port(
        CFG.HOST if CFG.HOST and CFG.HOST != "0.0.0.0" else "127.0.0.1", CFG.PORT
    )
    _os_reserved = (not _pin_ok) and ("10013" in _pin_why or "forbidden by its access permissions" in _pin_why)
    if _env_pinned_port and _os_reserved:
        logger.warning("=" * 74)
        logger.warning("[V5] PORT %s IS RESERVED BY WINDOWS - not by SPB.", CFG.PORT)
        logger.warning("[V5]   %s", _pin_why)
        logger.warning("[V5] Hyper-V (Docker Desktop / WSL / BlueStacks) grabs blocks of the")
        logger.warning("[V5] dynamic port range at every boot, and those blocks move each time.")
        logger.warning("[V5] Nothing is listening - Windows is simply refusing the bind, so")
        logger.warning("[V5] killing SPB processes cannot help. SPB will not change origin;")
        logger.warning("[V5] startup will stop until the pinned port can be claimed.")
        logger.warning("[V5]")
        logger.warning("[V5] To claim %s permanently, in an ADMIN prompt run:", CFG.PORT)
        logger.warning("[V5]   netsh int ipv4 set dynamicport tcp start=49152 num=10000")
        logger.warning("[V5]   (then reboot, then:)")
        logger.warning("[V5]   netsh int ipv4 add excludedportrange protocol=tcp startport=%s numberofports=1 store=persistent", CFG.PORT)
        logger.warning("=" * 74)
    port = _spb_pick_runtime_port(
        CFG.PORT, CFG.HOST,
        allow_fallback=not _env_pinned_port,
    )
    _spb_write_runtime_port(port)
    debug = CFG.DEBUG

    # ── Startup health check ─────────────────────────────────────
    try:
        from server_health import run_startup_checks
        _issues = run_startup_checks(
            BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY,
            output_dir=CFG.OUTPUT_DIR
        )
        if _issues:
            print(f"  [!] {len(_issues)} health warning(s) - check server_log.txt")
    except Exception as _he:
        logger.warning(f"Health check skipped: {_he}")

    _startup_elapsed = time.perf_counter() - _STARTUP_T0
    print("=" * 60)
    print(f"  {CFG.APP_NAME}")
    print(f"  Build: {CFG.BUILD_TAG} | {'DEV MODE (hot reload)' if debug else 'Modular Architecture'}")
    print(f"  Bases: {len(BASE_REGISTRY)} | Patterns: {len(PATTERN_REGISTRY)} | Monolithics: {len(MONOLITHIC_REGISTRY)}")
    print(f"  Fusions: {len(FUSION_REGISTRY)} | CS System: V5 Direct-RGB")
    print(f"  Startup:      {_startup_elapsed:.2f}s")
    print(f"  Live Link:    http://localhost:{port}")
    print(f"  Registry API: http://localhost:{port}/api/registry-check")
    print(f"  Finish Data:  http://localhost:{port}/api/finish-data")
    print(f"  Health Check: http://localhost:{port}/api/health")
    if debug:
        print(f"  HOT RELOAD: ON - file changes auto-restart server")
    print("=" * 60)
    logger.info(
        "[V5] Ready on %s:%d (startup %.2fs, debug=%s)",
        CFG.HOST, port, _startup_elapsed, debug,
    )

    # Owner 2026-10-02: repair the SAME full-detail masters/cards that categories
    # read. Stable renderer identities skip unchanged bakes. The exported JS
    # catalog carries exact picker tints; no Node or HTTP dependency at startup.
    # OS locking prevents competing bakers. Workers remain below normal priority
    # with all available cores, independent of launcher affinity. Packaging checks
    # coverage first; this background repair covers later renderer changes.
    # Disable with SPB_NO_BOOT_SWATCH_WARM=1.
    if (not os.environ.get("SPB_NO_LIVE_LINK")
            and os.environ.get("SPB_NO_BOOT_SWATCH_WARM") != "1"):
        def _boot_swatch_warm():
            import threading as _th  # noqa: F401 (named thread below)
            import subprocess as _sp
            time.sleep(25)   # let the app/UI settle first
            # Owner 2026-10-02: warming 48px legacy snapshots leaves the current
            # full-detail picker cold. Startup and packaging use ONE baker.
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "bake_faithful_picker.py")
            if not os.path.isfile(script):
                logger.error("[SwatchWarm] full-detail baker missing: %s", script)
                return
            try:
                # [2026-09-05 owner beta test] DETACHED_PROCESS gave the worker NO console, so every
                # console-subsystem child it spawned (python.exe per swatch job) opened a brand-new
                # VISIBLE console window over the app ~25 s after launch. CREATE_NO_WINDOW gives the
                # worker a hidden console that its children inherit - nothing ever pops up.
                flags = 0x4000 | 0x08000000  # BELOW_NORMAL_PRIORITY_CLASS | CREATE_NO_WINDOW
                with open(os.path.join(os.path.dirname(os.path.dirname(script)), "_swatch_warm_boot.log"), "w") as _lg:
                    _sp.Popen([sys.executable, script],
                              cwd=os.path.dirname(os.path.dirname(script)), stdout=_lg, stderr=_sp.STDOUT,
                              creationflags=flags)
                logger.info("[SwatchWarm] current full-detail picker bake repair launched (unchanged identities skipped)")
            except Exception as _sw_err:
                logger.warning("[SwatchWarm] boot warm skipped: %s", _sw_err)
        import threading as _threading_boot
        _threading_boot.Thread(target=_boot_swatch_warm, daemon=True, name="spb-swatch-warm").start()

    from flask import cli
    cli.show_server_banner = lambda *args, **kwargs: None
    # [SPB SPEED-TUNEUP 2026-08-30] Dual-loopback listener — THE 200ms fix.
    # The UI/Electron talk to http://localhost:<port>, but this server bound
    # ONLY 127.0.0.1. On Windows, "localhost" resolves to ::1 first, so EVERY
    # connection (each API call, each of the ~226 boot resources — werkzeug
    # sends Connection: close, so nothing is reused) burned ~200ms failing
    # over from IPv6 to IPv4. Measured: 210ms/request via localhost vs 4.7ms
    # via 127.0.0.1. An extra werkzeug listener on ::1 (same Flask app, same
    # port) makes the first-choice IPv6 connect succeed instantly. The page
    # origin stays "localhost" — localStorage/autosave keys are untouched —
    # and request_security already accepts ::1. Do NOT remove this without
    # re-measuring; it is why Render clicks and slider previews feel instant.
    if CFG.HOST in ("127.0.0.1", "localhost", "0.0.0.0"):  # every IPv4-only bind needs the ::1 twin
        def _spb_serve_ipv6_loopback():
            try:
                from werkzeug.serving import make_server
                _srv6 = make_server("::1", port, app, threaded=CFG.THREADED)
                logger.info(f"[V5] IPv6 loopback listener up on [::1]:{port}")
                _srv6.serve_forever()
            except Exception as _v6_exc:
                logger.warning(f"[V5] IPv6 loopback listener not started (IPv4 still fine): {_v6_exc}")
        import threading as _th6
        _th6.Thread(target=_spb_serve_ipv6_loopback, daemon=True, name="spb-ipv6-loopback").start()
    if debug:
        app.run(host=CFG.HOST, port=port, debug=True, threaded=CFG.THREADED, use_reloader=True)
    else:
        # This is a desktop-local backend, not a public Flask development host.
        # make_server keeps the same threaded Werkzeug request engine without
        # emitting Flask's misleading public-development-server warning.
        from werkzeug.serving import make_server
        _srv4 = make_server(CFG.HOST, port, app, threaded=CFG.THREADED)
        logger.info(f"[V5] IPv4 loopback listener up on {CFG.HOST}:{port}")
        _srv4.serve_forever()
