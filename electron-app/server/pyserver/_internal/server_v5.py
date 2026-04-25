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
    SHOKKER_NO_CLEAN=1 python server_v5.py    # Skip clean_boot (second instance)

Startup sequence
----------------
1. Clear ``__pycache__`` (stale .pyc protection after auto-updates).
2. Import :data:`config.CFG` (applies env overrides).
3. Import V5 engine registries and patch the legacy engine to use them.
4. Wire UI-catalog patterns/monolithics to family fallbacks.
5. Build the Flask app, configure rotating logs.
6. Inherit unmodified routes from ``server.py``.
7. Run :func:`clean_boot.clean_boot` (unless ``SHOKKER_NO_CLEAN=1``).
8. Run :func:`server_health.run_startup_checks`.
9. Start Flask.

Cross-module dependencies
-------------------------
* :mod:`config`             -- paths, port, debug flag.
* :mod:`engine.registry`    -- V5 BASE/PATTERN/MONOLITHIC/FUSION registries.
* :mod:`shokker_engine_v2`  -- legacy pipeline (patched to use V5 registries).
* :mod:`server`             -- provides inherited route handlers.
* :mod:`server_health`      -- startup/liveness checks.
* :mod:`clean_boot`         -- frees port and kills ghost servers on boot.

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

_clear_pycache()

# ================================================================
# CONFIG - single source of truth for port, paths, debug
# ================================================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG



import engine
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
    FUSION_REGISTRY = getattr(_legacy_engine, "FUSION_REGISTRY", {})

    _registry_mod.BASE_REGISTRY = BASE_REGISTRY
    _registry_mod.PATTERN_REGISTRY = PATTERN_REGISTRY
    _registry_mod.MONOLITHIC_REGISTRY = MONOLITHIC_REGISTRY
    _registry_mod.FINISH_REGISTRY = FINISH_REGISTRY
    _registry_mod.FUSION_REGISTRY = FUSION_REGISTRY


_sync_final_legacy_registries()

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
_log_file = os.path.join(CFG.ROOT_DIR, 'server_log.txt')

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


@app.route('/<path:filename>')
def serve_static_assets(filename):
    if filename.endswith(('.js', '.css', '.png', '.svg', '.ico')):
        for candidate_dir in [SERVER_DIR, BUNDLE_DIR]:
            fpath = os.path.join(candidate_dir, filename)
            if os.path.exists(fpath):
                resp = send_file(fpath)
                # JS/CSS: no-store = browser always fetches fresh (never uses cached copy)
                if filename.endswith(('.js', '.css')):
                    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
                    resp.headers.pop('ETag', None)
                    resp.headers.pop('Last-Modified', None)
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
    category = request.args.get('category')  # filter: 'bases', 'patterns', 'monolithics'
    data = {
        "bases": list(BASE_REGISTRY.keys()),
        "patterns": list(PATTERN_REGISTRY.keys()),
        "monolithics": list(MONOLITHIC_REGISTRY.keys()),
        "fusions": list(FUSION_REGISTRY.keys()),
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


@app.route('/status', methods=['GET'])
def status():
    cfg = load_config()
    return jsonify({
        "status": "online",
        "version": "5.0.0",
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
                "helmet_spec": True, "suit_spec": True, "wear_slider": True,
                "export_zip": True, "matching_set": True, "dual_spec": True, "live_link": True,
                "swatch_highres_mono": True,
            },
        },
        "config": {
            "iracing_id": cfg.get("iracing_id", ""),
            "live_link_enabled": cfg.get("live_link_enabled", False),
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
    for rule in _v4_server.app.url_map.iter_rules():
        if str(rule) not in _skip_routes:
            try:
                view_fn = _v4_server.app.view_functions[rule.endpoint]
                app.add_url_rule(str(rule), rule.endpoint + '_v4',
                                view_fn, methods=list(rule.methods - {'HEAD', 'OPTIONS'}))
            except Exception:
                pass
    logger.info(f"[V5] Inherited {len(list(app.url_map.iter_rules()))} routes from v4 server")
except Exception as _ex:
    logger.warning(f"[V5] Could not inherit v4 routes: {_ex}. Render endpoints may be missing.")

# Re-export for tests/scripts - swatch render function (same as /api/swatch uses)
try:
    from server import _render_swatch_bytes as render_swatch
except Exception:
    render_swatch = None

# ================================================================
# STARTUP
# ================================================================
if __name__ == '__main__':
    # ── Clean boot: free port and stop any other Shokker server (fresh start every time) ──
    if os.environ.get("SHOKKER_NO_CLEAN", "0") != "1":
        try:
            from clean_boot import clean_boot
            clean_boot(CFG.PORT, CFG.ROOT_DIR)
        except Exception as _e:
            logger.warning(f"Clean boot skipped: {_e}")

    port = CFG.PORT
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
    from flask import cli
    cli.show_server_banner = lambda *args, **kwargs: None
    app.run(host=CFG.HOST, port=port, debug=debug, threaded=CFG.THREADED, use_reloader=debug)
