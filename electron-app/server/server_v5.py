"""
Shokker Engine V5 - Local Server
==================================
V5 entry point. Uses engine/ package + config.py for all settings.

To run:
  python server_v5.py                  # Default: http://localhost:59876
  SHOKKER_PORT=59877 python server_v5.py  # Secondary/dev port if needed
  SHOKKER_DEV=1 python server_v5.py       # Hot reload mode
"""

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

# ================================================================
# CLEAR STALE __pycache__ ON EVERY STARTUP
# Prevents cached .pyc bytecode from loading old function signatures
# after code updates (auto-updater changes .py but not .pyc)
# ================================================================
def _clear_pycache():
    _root = os.path.dirname(os.path.abspath(__file__))
    _cleared = 0
    for dirpath, dirnames, filenames in os.walk(_root):
        if '__pycache__' in dirnames:
            _cache_dir = os.path.join(dirpath, '__pycache__')
            try:
                shutil.rmtree(_cache_dir)
                _cleared += 1
            except Exception:
                pass
    if _cleared:
        print(f"[Startup] Cleared {_cleared} __pycache__ directories")

_clear_pycache()

# ================================================================
# CONFIG - single source of truth for port, paths, debug
# ================================================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG



import engine
# Also import legacy engine for pipeline functions not yet migrated
import shokker_engine_v2 as _legacy_engine

# Use V5 registries (which include CS overrides)
from engine.registry import (
    BASE_REGISTRY,
    PATTERN_REGISTRY,
    MONOLITHIC_REGISTRY,
    FINISH_REGISTRY,
    FUSION_REGISTRY,
)

# Patch legacy engine registries to use V5 overrides
# This ensures the render pipeline picks up V5 CS functions
_legacy_engine.BASE_REGISTRY = BASE_REGISTRY
_legacy_engine.PATTERN_REGISTRY = PATTERN_REGISTRY
_legacy_engine.MONOLITHIC_REGISTRY = MONOLITHIC_REGISTRY

# Startup check: confirm image patterns (e.g. upgraded smile) are in registry for render
# Check that our base additions are properly mapped
if "race_day_gloss" in PATTERN_REGISTRY: # Example check just so it knows it loaded
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
VALID_LICENSE_PREFIX = "SHOKKER-"

def load_license():
    try:
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('license_key', ''), data.get('activated', False)
    except Exception:
        pass
    return '', False

def save_license(key, activated):
    try:
        with open(LICENSE_FILE, 'w') as f:
            json.dump({'license_key': key, 'activated': activated, 'timestamp': time.time()}, f)
    except Exception:
        pass

def validate_license_key(key):
    if not key or not isinstance(key, str):
        return False
    key = key.strip().upper()
    if not key.startswith(VALID_LICENSE_PREFIX):
        return False
    parts = key.split('-')
    if len(parts) != 4:
        return False
    for part in parts[1:]:
        if len(part) != 4 or not part.isalnum():
            return False
    return True

_license_key, _license_active = load_license()

# ================================================================
# CONFIG
# ================================================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"iracing_id": "23371", "car_paths": {}, "live_link_enabled": False,
            "active_car": None, "use_custom_number": True}

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

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

    print("=" * 60)
    print(f"  {CFG.APP_NAME}")
    print(f"  Build: {CFG.BUILD_TAG} | {'DEV MODE (hot reload)' if debug else 'Modular Architecture'}")
    print(f"  Bases: {len(BASE_REGISTRY)} | Patterns: {len(PATTERN_REGISTRY)} | Monolithics: {len(MONOLITHIC_REGISTRY)}")
    print(f"  Fusions: {len(FUSION_REGISTRY)} | CS System: V5 Direct-RGB")
    print(f"  Live Link:    http://localhost:{port}")
    print(f"  Registry API: http://localhost:{port}/api/registry-check")
    print(f"  Finish Data:  http://localhost:{port}/api/finish-data")
    print(f"  Health Check: http://localhost:{port}/api/health")
    if debug:
        print(f"  HOT RELOAD: ON - file changes auto-restart server")
    print("=" * 60)
    from flask import cli
    cli.show_server_banner = lambda *args, **kwargs: None
    app.run(host=CFG.HOST, port=port, debug=debug, threaded=CFG.THREADED, use_reloader=debug)
