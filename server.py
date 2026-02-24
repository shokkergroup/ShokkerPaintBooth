"""
Shokker Engine v4.0 PRO — Local Server
=======================================
Runs locally alongside Paint Booth UI. No cloud, no uploads.
Since everything is local, we use file paths instead of file uploads.

ENDPOINTS:
  GET  /status                         - Server info + engine capabilities
  POST /render                         - Run engine on local files (JSON body)
  POST /preview-render                 - Low-res live preview (base64 PNG response)
  GET  /preview/<job_id>/<filename>    - Serve preview PNGs to browser
  GET  /download/<job_id>/<filename>   - Download output TGA files
  POST /config                         - Save user config (iRacing ID, car paths)
  GET  /config                         - Load user config
  GET  /iracing-cars                   - Discover iRacing paint car folders
  POST /deploy-to-iracing              - One-click deploy rendered TGAs to iRacing
  POST /upload-composited-paint        - Upload decal-composited paint as temp TGA

iRACING LIVE LINK:
  When configured, render output is ALSO copied to the iRacing paint folder.
  User Alt+Tabs to iRacing and presses Ctrl+R — car updates instantly in 3D.
  Config is saved to shokker_config.json next to server.py.
"""

from flask import Flask, request, jsonify, send_file
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

# Import the engine
try:
    import shokker_engine_v2 as engine
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import shokker_engine_v2 as engine

# Setup Flask
app = Flask(__name__)
CORS(app)

@app.errorhandler(404)
def _handle_404(e):
    return jsonify({"error": "not_found", "path": request.path}), 404

# Folders — handle PyInstaller bundle vs normal Python
# When frozen (PyInstaller), __file__ is in a temp dir. Use exe location instead.
if getattr(sys, 'frozen', False):
    # For --onefile PyInstaller/Nuitka builds, sys.executable is in a temp extraction dir.
    # The REAL exe location (where HTML and config live) is the original path the user ran.
    # sys.argv[0] or the parent process's working dir won't help either.
    # Solution: check for SHOKKER_EXE_DIR env var (set by Electron), fall back to sys.executable dir.
    SERVER_DIR = os.environ.get('SHOKKER_EXE_DIR', os.path.dirname(sys.executable))
    BUNDLE_DIR = getattr(sys, '_MEIPASS', SERVER_DIR)  # Where bundled data files live
else:
    SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = SERVER_DIR
OUTPUT_FOLDER = os.path.join(SERVER_DIR, 'output')
CONFIG_FILE = os.path.join(SERVER_DIR, 'shokker_config.json')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Startup log
logger_startup = logging.getLogger('shokker.startup')

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('shokker')

# ===== LICENSING & ACTIVATION =====
LICENSE_FILE = os.path.join(SERVER_DIR, 'shokker_license.json')
VALID_LICENSE_PREFIX = "SHOKKER-"  # Valid keys: SHOKKER-XXXX-XXXX-XXXX

def load_license():
    """Load saved license from disk."""
    try:
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('license_key', ''), data.get('activated', False)
    except Exception:
        pass
    return '', False

def save_license(key, activated):
    """Save license to disk."""
    try:
        with open(LICENSE_FILE, 'w') as f:
            json.dump({'license_key': key, 'activated': activated, 'timestamp': time.time()}, f)
    except Exception:
        pass

def validate_license_key(key):
    """Validate license key format: SHOKKER-XXXX-XXXX-XXXX (alphanumeric)."""
    if not key or not isinstance(key, str):
        return False
    key = key.strip().upper()
    if not key.startswith(VALID_LICENSE_PREFIX):
        return False
    parts = key.split('-')
    if len(parts) != 4:
        return False
    # Each part after SHOKKER should be 4 alphanumeric chars
    for part in parts[1:]:
        if len(part) != 4 or not part.isalnum():
            return False
    return True

# Load license on startup
_license_key, _license_active = load_license()


# ===== SERVE PAINT BOOTH HTML =====
@app.route('/')
def serve_paint_booth():
    """Serve the Paint Booth UI at the root URL for easy access."""
    try:
        with open(r'C:\temp\_spb_build23_proof.log', 'a') as _f:
            _f.write(f"{time.strftime('%H:%M:%S')} ROUTE / HIT — serving HTML\n")
    except:
        pass
    # Check next to exe first, then in bundle dir, then in app/ subdir
    for candidate in [
        os.path.join(SERVER_DIR, 'paint-booth-v2.html'),
        os.path.join(BUNDLE_DIR, 'paint-booth-v2.html'),
        os.path.join(SERVER_DIR, '..', 'app', 'paint-booth-v2.html'),
    ]:
        if os.path.exists(candidate):
            # BUILD 23: Inject proof marker so we can verify Flask served the page (not cache)
            try:
                with open(os.path.abspath(candidate), 'r', encoding='utf-8') as hf:
                    html_content = hf.read()
                html_content = html_content.replace('</head>', f'<!-- FLASK-SERVED-BUILD-27 PID={os.getpid()} TIME={time.strftime("%H:%M:%S")} -->\n</head>', 1)
                from flask import Response
                return Response(html_content, mimetype='text/html')
            except Exception as _e:
                # Fallback to send_file if injection fails
                return send_file(os.path.abspath(candidate), mimetype='text/html')
    return "Paint Booth HTML not found", 404


# ================================================================
# CONFIG — persistent user settings (iRacing ID, car paths, etc.)
# ================================================================

def load_config():
    """Load saved config from shokker_config.json."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "iracing_id": "23371",
        "car_paths": {},
        "live_link_enabled": False,
        "active_car": None,
        "use_custom_number": True,
    }


def save_config(cfg):
    """Save config to shokker_config.json."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)


# ================================================================
# ENDPOINTS
# ================================================================

@app.route('/build-check', methods=['GET'])
def build_check():
    """Diagnostic endpoint — returns server status and configuration."""
    return jsonify({
        "build": 29,
        "version": "6.0.1-alpha",
        "status": "running",
        "pid": os.getpid(),
        "port": int(os.environ.get('SHOKKER_PORT', 59876)),
        "server_dir": SERVER_DIR,
    })

@app.route('/status', methods=['GET'])
def status():
    """Server heartbeat + engine capabilities."""
    cfg = load_config()
    return jsonify({
        "status": "online",
        "version": "6.0.0-alpha",
        "engine": "Shokker Engine v6.0 PRO — 24K Arsenal",
        "capabilities": {
            "bases": list(engine.BASE_REGISTRY.keys()),
            "patterns": list(engine.PATTERN_REGISTRY.keys()),
            "monolithics": list(engine.MONOLITHIC_REGISTRY.keys()),
            "legacy_finishes": list(engine.FINISH_REGISTRY.keys()),
            "base_count": len(engine.BASE_REGISTRY),
            "pattern_count": len(engine.PATTERN_REGISTRY),
            "monolithic_count": len(engine.MONOLITHIC_REGISTRY),
            "combination_count": len(engine.BASE_REGISTRY) * len(engine.PATTERN_REGISTRY),
            "features": {
                "helmet_spec": True,
                "suit_spec": True,
                "wear_slider": True,
                "export_zip": True,
                "matching_set": True,
                "dual_spec": True,
                "live_link": True,
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


@app.route('/license', methods=['GET', 'POST'])
def license_endpoint():
    """Check or activate license."""
    global _license_key, _license_active

    if request.method == 'GET':
        return jsonify({
            "active": _license_active,
            "key_masked": (_license_key[:12] + "****") if _license_key else "",
        })

    # POST — activate a key
    data = request.get_json() or {}
    key = (data.get('key', '') or '').strip().upper()

    if not key:
        return jsonify({"error": "No license key provided"}), 400

    if not validate_license_key(key):
        return jsonify({"error": "Invalid license key format. Expected: SHOKKER-XXXX-XXXX-XXXX"}), 400

    # Key format is valid — activate it
    # In production this would phone home to a license server.
    # For Alpha, valid format = activated.
    _license_key = key
    _license_active = True
    save_license(key, True)
    logger.info(f"License activated: {key[:12]}****")

    return jsonify({
        "active": True,
        "key_masked": key[:12] + "****",
        "message": "License activated successfully!"
    })


@app.route('/license/deactivate', methods=['POST'])
def license_deactivate():
    """Deactivate the current license."""
    global _license_key, _license_active
    _license_key = ''
    _license_active = False
    save_license('', False)
    logger.info("License deactivated")
    return jsonify({"active": False, "message": "License deactivated."})


@app.route('/finish-groups', methods=['GET'])
def finish_groups():
    """Return group metadata for UI organization of 24K Arsenal finishes."""
    try:
        import shokker_24k_expansion as _exp24k
        groups = _exp24k.get_expansion_group_map()
        counts = _exp24k.get_expansion_counts()
        # Merge PARADIGM groups if available
        try:
            import shokker_paradigm_expansion as _paradigm
            paradigm_groups = _paradigm.get_paradigm_group_map()
            for key in ("bases", "patterns", "specials"):
                if key in paradigm_groups:
                    groups.setdefault(key, {}).update(paradigm_groups[key])
        except Exception:
            pass
        return jsonify({
            "status": "ok",
            "groups": groups,
            "expansion_counts": counts,
            "total_bases": len(engine.BASE_REGISTRY),
            "total_patterns": len(engine.PATTERN_REGISTRY),
            "total_specials": len(engine.MONOLITHIC_REGISTRY),
            "total_combinations": len(engine.BASE_REGISTRY) * len(engine.PATTERN_REGISTRY) + len(engine.MONOLITHIC_REGISTRY),
        })
    except ImportError:
        return jsonify({"status": "ok", "groups": {"bases": {}, "patterns": {}, "specials": {}},
                        "expansion_counts": {"bases": 0, "patterns": 0, "specials": 0, "total": 0}})


def apply_paint_recolor(paint_file, rules, job_dir, mask_rle=None, mask_has_include=False):
    """Apply recolor rules to a paint file, saving a recolored copy.

    Each rule: {"source_rgb": [R,G,B], "target_rgb": [R,G,B], "tolerance": 40, "hue_shift": true}
    Uses HSV hue-shift to preserve shading (dark red → dark green, etc.)
    Optional mask_rle: RLE-encoded spatial mask (0=unset, 1=include, 2=exclude).
    Returns path to the recolored file.
    """
    import numpy as np
    from PIL import Image as PILImage
    import colorsys

    img = PILImage.open(paint_file).convert('RGB')
    pixels = np.array(img, dtype=np.float32)
    original = pixels.copy()
    h, w = pixels.shape[:2]

    # Decode spatial mask if provided
    # Format from client: {width, height, runs: [[value, count], ...]}
    spatial_mask = None
    if mask_rle and isinstance(mask_rle, dict) and "runs" in mask_rle:
        try:
            runs = mask_rle["runs"]
            spatial_mask = np.zeros(w * h, dtype=np.uint8)
            idx = 0
            for run in runs:
                val = int(run[0])
                count = int(run[1])
                end = min(idx + count, len(spatial_mask))
                spatial_mask[idx:end] = val
                idx = end
            spatial_mask = spatial_mask.reshape(h, w)
        except Exception as e:
            logger.warning(f"Recolor mask decode failed: {e}")
            spatial_mask = None

    for rule in rules:
        src = np.array(rule["source_rgb"], dtype=np.float32)
        tgt = np.array(rule["target_rgb"], dtype=np.float32)
        tol = float(rule.get("tolerance", 40))
        use_hue_shift = rule.get("hue_shift", True)

        # Build color mask: Euclidean RGB distance (same scaling as client-side)
        diff = original - src[np.newaxis, np.newaxis, :]
        dist_sq = np.sum(diff ** 2, axis=-1)
        mask = dist_sq <= (tol * tol * 3)

        # Apply spatial mask if present
        if spatial_mask is not None:
            # Exclude pixels marked as 2
            mask = mask & (spatial_mask != 2)
            # If include mode active, restrict to included pixels only
            if mask_has_include:
                mask = mask & (spatial_mask == 1)

        if not np.any(mask):
            continue

        if use_hue_shift:
            # Compute HSV deltas
            src_hsv = colorsys.rgb_to_hsv(src[0] / 255, src[1] / 255, src[2] / 255)
            tgt_hsv = colorsys.rgb_to_hsv(tgt[0] / 255, tgt[1] / 255, tgt[2] / 255)
            h_delta = tgt_hsv[0] - src_hsv[0]  # 0-1 range
            s_delta = tgt_hsv[1] - src_hsv[1]
            v_delta = tgt_hsv[2] - src_hsv[2]

            # Vectorized HSV shift on matched pixels
            matched = original[mask] / 255.0
            r_ch, g_ch, b_ch = matched[:, 0], matched[:, 1], matched[:, 2]
            maxc = np.maximum(np.maximum(r_ch, g_ch), b_ch)
            minc = np.minimum(np.minimum(r_ch, g_ch), b_ch)
            delta_c = maxc - minc

            # RGB → H
            hue = np.zeros_like(r_ch)
            nonzero = delta_c > 1e-6
            m_r = (maxc == r_ch) & nonzero
            m_g = (maxc == g_ch) & nonzero & ~m_r
            m_b = nonzero & ~m_r & ~m_g
            hue[m_r] = (((g_ch[m_r] - b_ch[m_r]) / delta_c[m_r]) % 6) / 6.0
            hue[m_g] = (((b_ch[m_g] - r_ch[m_g]) / delta_c[m_g]) + 2) / 6.0
            hue[m_b] = (((r_ch[m_b] - g_ch[m_b]) / delta_c[m_b]) + 4) / 6.0

            sat = np.where(maxc > 0, delta_c / maxc, 0)
            val = maxc

            # Apply shifts
            new_h = (hue + h_delta) % 1.0
            new_s = np.clip(sat + s_delta, 0, 1)
            new_v = np.clip(val + v_delta, 0, 1)

            # HSV → RGB using engine's vectorized function
            new_r, new_g, new_b = engine.hsv_to_rgb_vec(new_h, new_s, new_v)
            pixels[mask, 0] = new_r * 255
            pixels[mask, 1] = new_g * 255
            pixels[mask, 2] = new_b * 255
        else:
            pixels[mask] = tgt

    recolored = np.clip(pixels, 0, 255).astype(np.uint8)
    recolored_path = os.path.join(job_dir, "recolored_paint.tga")
    engine.write_tga_24bit(recolored_path, recolored)
    return recolored_path


def numpy_to_base64_png(arr):
    """Convert a numpy uint8 array to a base64-encoded PNG data URI."""
    from PIL import Image as PILImage
    img = PILImage.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return f"data:image/png;base64,{b64}"


@app.route('/debug-rotation-log', methods=['GET'])
def debug_rotation_log():
    """Return the rotation debug log file contents (deprecated — kept for compat)."""
    return "Debug rotation logging removed in build 29", 200, {'Content-Type': 'text/plain'}

@app.route('/preview-render', methods=['POST'])
def preview_render_endpoint():
    """Low-res live preview — returns base64 PNGs inline (no job directory).

    JSON body:
    {
        "paint_file": "E:/path/to/car_num_23371.tga",
        "zones": [...],
        "seed": 51,
        "preview_scale": 0.25,
        "recolor_rules": []
    }

    Response:
    {
        "success": true,
        "elapsed_ms": 180,
        "paint_preview": "data:image/png;base64,...",
        "spec_preview": "data:image/png;base64,...",
        "resolution": [512, 512]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400


        paint_file = data.get("paint_file")
        if not paint_file or not os.path.exists(paint_file):
            return jsonify({"error": f"Paint file not found: {paint_file}"}), 404

        zones = data.get("zones", [])
        if not zones:
            return jsonify({"error": "No zones provided"}), 400

        seed = data.get("seed", 51)
        preview_scale = float(data.get("preview_scale", 0.25))
        preview_scale = max(0.0625, min(1.0, preview_scale))  # Clamp 1/16 to 1x

        # Apply paint recoloring if rules provided (at preview res this is fast)
        recolor_rules = data.get("recolor_rules", [])
        actual_paint_file = paint_file
        if recolor_rules:
            try:
                # Recolor needs a temp directory for the recolored TGA
                import tempfile
                tmp_dir = tempfile.mkdtemp(prefix="shokker_preview_")
                actual_paint_file = apply_paint_recolor(paint_file, recolor_rules, tmp_dir)
            except Exception:
                actual_paint_file = paint_file  # Fall back to original

        # Build server zones (same format conversion as /render)

        server_zones = []
        for z in zones:
            zone_obj = {
                "name": z.get("name", "Zone"),
                "color": z.get("color", "everything"),
                "intensity": z.get("intensity", "aggressive"),
            }
            # Compositing mode
            if z.get("base"):
                zone_obj["base"] = z["base"]
                zone_obj["pattern"] = z.get("pattern", "none")
                if z.get("scale") and float(z.get("scale", 1.0)) != 1.0:
                    zone_obj["scale"] = float(z["scale"])
                if z.get("rotation") and float(z.get("rotation", 0)) != 0:
                    zone_obj["rotation"] = float(z["rotation"])
                if z.get("pattern_opacity") and float(z.get("pattern_opacity", 1.0)) != 1.0:
                    zone_obj["pattern_opacity"] = float(z["pattern_opacity"])
                if z.get("pattern_stack"):
                    zone_obj["pattern_stack"] = z["pattern_stack"]
            # Monolithic/legacy mode
            elif z.get("finish"):
                zone_obj["finish"] = z["finish"]
                # Pass client color data for fallback rendering
                if z.get("finish_colors"):
                    zone_obj["finish_colors"] = z["finish_colors"]
                # Pass rotation for gradient direction control
                if z.get("rotation") and float(z.get("rotation", 0)) != 0:
                    zone_obj["rotation"] = float(z["rotation"])
                # BUG FIX: Pass pattern data for monolithic zones too — engine supports
                # pattern overlay on monolithics via overlay_pattern_on_spec/overlay_pattern_paint
                if z.get("pattern") and z.get("pattern") != "none":
                    zone_obj["pattern"] = z["pattern"]
                if z.get("scale") and float(z.get("scale", 1.0)) != 1.0:
                    zone_obj["scale"] = float(z["scale"])
                if z.get("pattern_opacity") and float(z.get("pattern_opacity", 1.0)) != 1.0:
                    zone_obj["pattern_opacity"] = float(z["pattern_opacity"])
                if z.get("pattern_stack"):
                    zone_obj["pattern_stack"] = z["pattern_stack"]


            # Pattern spec multiplier (controls spec map punch independently)
            if z.get("pattern_spec_mult") is not None:
                zone_obj["pattern_spec_mult"] = float(z["pattern_spec_mult"])

            # Custom intensity
            if z.get("custom_intensity"):
                zone_obj["custom_intensity"] = z["custom_intensity"]

            # Wear
            if z.get("wear_level"):
                zone_obj["wear_level"] = z["wear_level"]

            # Region mask (base64 RLE from UI)
            if z.get("region_mask"):
                try:
                    import numpy as np
                    from PIL import Image as PILImage
                    rle = z["region_mask"]
                    if isinstance(rle, str):
                        rle = json.loads(rle)
                    rw = rle.get("width", 0)
                    rh = rle.get("height", 0)
                    runs = rle.get("runs", [])
                    flat = np.zeros(rw * rh, dtype=np.float32)
                    pos = 0
                    for run_val, run_len in runs:
                        flat[pos:pos + run_len] = float(run_val) / 255.0
                        pos += run_len
                    zone_obj["region_mask"] = flat.reshape((rh, rw))
                except Exception:
                    pass  # Skip broken masks

            server_zones.append(zone_obj)

        # Import spec map (merge mode)
        import_spec_map = data.get("import_spec_map")
        if import_spec_map and not os.path.exists(import_spec_map):
            import_spec_map = None  # Silently skip if file missing

        # Diagnostic: log zone scale values for debugging
        for zi, sz in enumerate(server_zones):
            parts = [f"Zone {zi+1}"]
            if sz.get("base"): parts.append(f"base={sz['base']}")
            if sz.get("pattern"): parts.append(f"pat={sz['pattern']}")
            if sz.get("scale"): parts.append(f"scale={sz['scale']}")
            if sz.get("pattern_stack"):
                for li, layer in enumerate(sz["pattern_stack"]):
                    parts.append(f"stack[{li}]={layer.get('id','?')}@scale={layer.get('scale',1.0)}")
            logger.info("  ".join(parts))

        # Run the preview render
        paint_rgb, spec_rgba, elapsed_ms = engine.preview_render(
            actual_paint_file, server_zones, seed=seed, preview_scale=preview_scale,
            import_spec_map=import_spec_map
        )

        # Convert to base64 PNGs
        paint_b64 = numpy_to_base64_png(paint_rgb)
        spec_b64 = numpy_to_base64_png(spec_rgba)

        # Cleanup temp recolor dir if created
        if recolor_rules and actual_paint_file != paint_file:
            try:
                shutil.rmtree(os.path.dirname(actual_paint_file), ignore_errors=True)
            except Exception:
                pass

        return jsonify({
            "success": True,
            "elapsed_ms": round(elapsed_ms, 1),
            "paint_preview": paint_b64,
            "spec_preview": spec_b64,
            "resolution": [paint_rgb.shape[1], paint_rgb.shape[0]],
        })

    except Exception as e:
        logger.error(f"Preview render failed: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route('/render', methods=['POST'])
def render():
    """
    Run the engine on local files. No upload needed — everything is local.

    JSON body:
    {
        "paint_file": "E:/path/to/car_num_23371.tga",
        "iracing_id": "23371",
        "seed": 51,
        "zones": [
            {
                "name": "Body",
                "color": "blue",
                "base": "chrome",
                "pattern": "carbon_fiber",
                "intensity": "100"
            }
        ],
        "live_link": true,              // optional: copy to iRacing folder
        "helmet_paint_file": "...",     // optional: helmet paint TGA path
        "suit_paint_file": "...",       // optional: suit paint TGA path
        "wear_level": 0,               // optional: 0-100 wear/age amount
        "export_zip": false             // optional: bundle into ZIP
    }
    """
    # ===== LICENSE GATE (disabled for Alpha testing) =====
    # if not _license_active:
    #     return jsonify({
    #         "error": "License required",
    #         "message": "A valid Shokker Engine license is required for full renders. "
    #                    "Preview mode is always free. Enter your license key in Settings.",
    #         "license_required": True
    #     }), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        paint_file = data.get("paint_file")
        if not paint_file:
            return jsonify({"error": "Missing 'paint_file' path"}), 400
        if not os.path.exists(paint_file):
            return jsonify({"error": f"Paint file not found: {paint_file}"}), 404

        zones = data.get("zones", [])
        if not zones:
            return jsonify({"error": "No zones provided"}), 400

        iracing_id = data.get("iracing_id", "00000")
        seed = data.get("seed", 51)
        use_live_link = data.get("live_link", False)
        output_dir_user = data.get("output_dir", "")  # UI-specified iRacing paint folder
        # Car file naming: car_num_ (custom numbers) vs car_ (no custom numbers)
        use_custom_number = data.get("use_custom_number", None)
        if use_custom_number is None:
            # Fall back to saved config
            _cfg_tmp = load_config()
            use_custom_number = _cfg_tmp.get("use_custom_number", True)
        car_prefix = "car_num" if use_custom_number else "car"
        helmet_paint = data.get("helmet_paint_file")
        suit_paint = data.get("suit_paint_file")
        wear_level = int(data.get("wear_level", 0))
        export_zip = data.get("export_zip", False)
        dual_spec = data.get("dual_spec", False)
        night_boost = float(data.get("night_boost", 0.7))
        import_spec_map = data.get("import_spec_map")
        if import_spec_map and not os.path.exists(import_spec_map):
            logger.warning(f"Import spec map not found: {import_spec_map}")
            import_spec_map = None

        # Validate optional files
        if helmet_paint and not os.path.exists(helmet_paint):
            helmet_paint = None
        if suit_paint and not os.path.exists(suit_paint):
            suit_paint = None

        # Create job output dir
        job_id = f"{int(time.time())}_{iracing_id}"
        job_dir = os.path.join(OUTPUT_FOLDER, f"job_{job_id}")
        os.makedirs(job_dir, exist_ok=True)

        recolor_rules = data.get("recolor_rules", [])
        recolor_mask_rle = data.get("recolor_mask", None)
        recolor_mask_has_include = data.get("recolor_mask_has_include", False)

        logger.info(f"Job {job_id}: {len(zones)} zones, paint={os.path.basename(paint_file)}"
                     f", helmet={'yes' if helmet_paint else 'default'}"
                     f", suit={'yes' if suit_paint else 'default'}"
                     f", wear={wear_level}"
                     f"{f', recolor={len(recolor_rules)} rules' if recolor_rules else ''}"
                     f"{', +mask' if recolor_mask_rle else ''}")
        # Log each zone's render path for diagnostics
        for i, z in enumerate(zones):
            # Determine which render path this zone will take
            if z.get('base'):
                path_label = f"base={z['base']} pattern={z.get('pattern','none')}"
            elif z.get('finish'):
                path_label = f"finish={z['finish']}"
                if z.get('pattern') and z.get('pattern') != 'none':
                    path_label += f" +overlay={z['pattern']}"
            else:
                path_label = "fallback (no base or finish)"
            logger.info(f"  Zone {i+1}: {path_label} "
                        f"color={str(z.get('color','?'))[:40]} intensity={z.get('intensity','?')} "
                        f"wear={z.get('wear_level',0)} stack={len(z.get('pattern_stack',[])) if z.get('pattern_stack') else 0}")
        start = time.time()

        # Apply paint recoloring if any rules are provided
        actual_paint_file = paint_file
        if recolor_rules:
            try:
                actual_paint_file = apply_paint_recolor(paint_file, recolor_rules, job_dir,
                                                         recolor_mask_rle, recolor_mask_has_include)
                logger.info(f"Job {job_id}: Applied {len(recolor_rules)} recolor rules -> {os.path.basename(actual_paint_file)}")
            except Exception as e:
                logger.warning(f"Job {job_id}: Recolor failed ({e}), using original paint")
                actual_paint_file = paint_file

        # Determine car folder name for export
        cfg = load_config()
        car_folder_name = cfg.get("active_car", "unknown")

        # Run the full pipeline (car + helmet + suit + wear + optional zip)
        results = engine.full_render_pipeline(
            car_paint_file=actual_paint_file,
            output_dir=job_dir,
            zones=zones,
            iracing_id=iracing_id,
            seed=seed,
            helmet_paint_file=helmet_paint,
            suit_paint_file=suit_paint,
            wear_level=wear_level,
            car_folder_name=car_folder_name,
            export_zip=export_zip,
            dual_spec=dual_spec,
            night_boost=night_boost,
            import_spec_map=import_spec_map,
            car_prefix=car_prefix,
        )

        elapsed = time.time() - start
        logger.info(f"Job {job_id}: completed in {elapsed:.1f}s")

        # Build preview URLs (scan job dir for all PNGs)
        preview_urls = {}
        for fname in os.listdir(job_dir):
            if fname.endswith('.png'):
                preview_urls[fname] = f"/preview/{job_id}/{fname}"

        # Build download URLs for all TGA files
        download_urls = {}
        for fname in os.listdir(job_dir):
            if fname.endswith('.tga'):
                key = fname.replace('.tga', '')
                download_urls[key] = f"/download/{job_id}/{fname}"

        # ZIP download URL
        zip_url = None
        if export_zip and "export_zip" in results:
            zip_name = os.path.basename(results["export_zip"])
            zip_url = f"/download/{job_id}/{zip_name}"

        # Build list of TGA files to push to the output folder
        # car_prefix is "car_num" (custom numbers) or "car" (no custom numbers)
        # spec is ALWAYS "car_spec" regardless
        files_to_push = [
            (f"{car_prefix}_{iracing_id}.tga", f"{car_prefix}_{iracing_id}.tga"),
            (f"car_spec_{iracing_id}.tga", f"car_spec_{iracing_id}.tga"),
        ]
        if "helmet_spec" in results:
            files_to_push.append(
                (f"helmet_spec_{iracing_id}.tga", f"helmet_spec_{iracing_id}.tga"))
        if "helmet_paint" in results:
            files_to_push.append(
                (f"helmet_{iracing_id}.tga", f"helmet_{iracing_id}.tga"))
        if "suit_spec" in results:
            files_to_push.append(
                (f"suit_spec_{iracing_id}.tga", f"suit_spec_{iracing_id}.tga"))
        if "suit_paint" in results:
            files_to_push.append(
                (f"suit_{iracing_id}.tga", f"suit_{iracing_id}.tga"))

        def _push_files_to_dir(target_dir, label="output"):
            """Copy rendered TGAs to a target directory with backup of originals."""
            pushed = []
            for src_name, dst_name in files_to_push:
                src = os.path.join(job_dir, src_name)
                dst = os.path.join(target_dir, dst_name)
                if os.path.exists(src):
                    # Back up originals (first time only)
                    backup = os.path.join(target_dir, f"ORIGINAL_{dst_name}")
                    if os.path.exists(dst) and not os.path.exists(backup):
                        shutil.copy2(dst, backup)
                    shutil.copy2(src, dst)
                    pushed.append(dst_name)
            logger.info(f"{label}: pushed {len(pushed)} files to {target_dir}")
            return pushed

        # PRIMARY: Copy output TGAs to the user-specified output folder
        output_dir_status = None
        if output_dir_user and output_dir_user.strip():
            target = os.path.normpath(output_dir_user.strip())
            if os.path.isdir(target):
                try:
                    pushed = _push_files_to_dir(target, "Output Dir")
                    output_dir_status = {
                        "success": True,
                        "path": target,
                        "pushed_files": pushed,
                        "message": f"Saved {len(pushed)} files to {target}"
                    }
                except Exception as e:
                    output_dir_status = {"success": False, "path": target, "error": str(e)}
                    logger.error(f"Output Dir error: {e}")
            else:
                output_dir_status = {
                    "success": False,
                    "path": target,
                    "error": f"iRacing folder not found: {target}"
                }

        # SECONDARY: iRacing Live Link (config-based, if user also has it enabled)
        live_link_status = None
        if use_live_link:
            active_car = cfg.get("active_car")
            car_path = cfg.get("car_paths", {}).get(active_car) if active_car else None
            # Use output_dir as live link target if no config car path
            if not car_path and output_dir_user:
                car_path = os.path.normpath(output_dir_user.strip())
                active_car = os.path.basename(car_path)

            if car_path and os.path.isdir(car_path):
                try:
                    pushed = _push_files_to_dir(car_path, "Live Link")
                    live_link_status = {
                        "success": True,
                        "car": active_car,
                        "path": car_path,
                        "pushed_files": pushed,
                        "message": f"Pushed {len(pushed)} files to iRacing! Alt+Tab and Ctrl+R."
                    }
                except Exception as e:
                    live_link_status = {"success": False, "error": str(e)}
                    logger.error(f"Live Link error: {e}")
            else:
                live_link_status = {
                    "success": False,
                    "error": "No active car configured. Set up iRacing Live Link in settings."
                }

        result = {
            "success": True,
            "job_id": job_id,
            "elapsed_seconds": round(elapsed, 2),
            "zone_count": len(zones),
            "wear_level": wear_level,
            "preview_urls": preview_urls,
            "download_urls": download_urls,
            "includes": {
                "car": True,
                "helmet": "helmet_spec" in results,
                "suit": "suit_spec" in results,
                "wear": wear_level > 0,
            },
        }
        if zip_url:
            result["export_zip_url"] = zip_url
        if output_dir_status:
            result["output_dir"] = output_dir_status
        if live_link_status:
            result["live_link"] = live_link_status

        return jsonify(result)

    except Exception as e:
        logger.error(f"Render error: {traceback.format_exc()}")
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route('/preview/<job_id>/<filename>', methods=['GET'])
def get_preview(job_id, filename):
    """Serve preview PNGs to the browser."""
    safe_job = os.path.basename(job_id)
    safe_file = os.path.basename(filename)
    path = os.path.join(OUTPUT_FOLDER, f"job_{safe_job}", safe_file)
    if os.path.exists(path):
        return send_file(path, mimetype='image/png')
    return jsonify({"error": "File not found"}), 404


@app.route('/download/<job_id>/<filename>', methods=['GET'])
def download_file(job_id, filename):
    """Download output TGA files."""
    safe_job = os.path.basename(job_id)
    safe_file = os.path.basename(filename)
    path = os.path.join(OUTPUT_FOLDER, f"job_{safe_job}", safe_file)
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name=safe_file)
    return jsonify({"error": "File not found"}), 404


@app.route('/reset-backup', methods=['POST'])
def reset_backup():
    """Delete the ORIGINAL_ backup so next render creates a fresh one.
    Use this if the backup was accidentally created from an already-rendered file.
    Body: {"paint_file": "E:/path/to/car_num_23371.tga"}
    """
    try:
        data = request.get_json() or {}
        paint_file = data.get("paint_file", "")
        if not paint_file:
            return jsonify({"error": "Missing paint_file"}), 400
        paint_file = os.path.normpath(os.path.abspath(paint_file))
        source_dir = os.path.dirname(paint_file)
        basename = os.path.basename(paint_file)
        backup_path = os.path.join(source_dir, f"ORIGINAL_{basename}")
        deleted = []
        if os.path.exists(backup_path):
            os.remove(backup_path)
            deleted.append(backup_path)
            logger.info(f"Reset backup: deleted {backup_path}")
        # Also check the output folder for any ORIGINAL_ copies
        output_backup = os.path.join(source_dir, f"ORIGINAL_car_spec_{data.get('iracing_id', '00000')}.tga")
        if os.path.exists(output_backup):
            os.remove(output_backup)
            deleted.append(output_backup)
        return jsonify({"success": True, "deleted": deleted,
                        "message": f"Cleared {len(deleted)} backup(s). Next render will use the current source file."})
    except Exception as e:
        logger.error(f"Reset backup error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/preview-tga', methods=['POST'])
def preview_tga():
    """Convert a local TGA file to PNG and serve it for browser display.
    Body: {"path": "E:/path/to/car_num_23371.tga"}
    """
    try:
        from PIL import Image as PILImage
        import io
        data = request.get_json() or {}
        tga_path = data.get('path', '')
        if not tga_path or not os.path.isfile(tga_path):
            return jsonify({"error": "File not found"}), 404
        img = PILImage.open(tga_path)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


### ===== SWATCH GENERATION =====
SWATCH_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swatches')
os.makedirs(SWATCH_FOLDER, exist_ok=True)

# Clear swatch cache on startup so rebuilt finishes get fresh thumbnails
_swatch_files = [f for f in os.listdir(SWATCH_FOLDER) if f.endswith('.png')]
if _swatch_files:
    for f in _swatch_files:
        try:
            os.remove(os.path.join(SWATCH_FOLDER, f))
        except OSError:
            pass
    logger.info(f"Cleared {len(_swatch_files)} cached swatches for fresh regeneration")

@app.route('/swatch/<base_id>/<pattern_id>')
def get_swatch(base_id, pattern_id):
    """Generate a 64x64 swatch thumbnail for a base+pattern finish combination.
    Cached to disk for instant repeat loads."""
    try:
        from PIL import Image as PILImage
        import io
        import numpy as np

        cache_file = os.path.join(SWATCH_FOLDER, f"{base_id}_{pattern_id}.png")
        if os.path.exists(cache_file):
            return send_file(cache_file, mimetype='image/png')

        # Validate IDs
        if base_id not in engine.BASE_REGISTRY:
            return jsonify({"error": f"Unknown base: {base_id}"}), 404
        if pattern_id != "none" and pattern_id not in engine.PATTERN_REGISTRY:
            return jsonify({"error": f"Unknown pattern: {pattern_id}"}), 404

        # Generate at 128x128 for better pattern visibility, downscale to 64x64
        render_shape = (128, 128)
        output_size = (64, 64)
        mask = np.ones(render_shape, dtype=np.float32)
        spec = engine.compose_finish(base_id, pattern_id, render_shape, mask, 51, 1.0)

        # Visualize spec as visible color:
        # Metallic -> brightness, Roughness -> darkness, Clearcoat -> blue tint
        metallic = spec[:,:,0].astype(np.float32) / 255.0
        roughness = spec[:,:,1].astype(np.float32) / 255.0
        clearcoat = np.clip(1.0 - spec[:,:,2].astype(np.float32) / 64.0, 0, 1)

        # Base gray shifted by metallic (bright = more metallic)
        r = np.clip(0.3 + metallic * 0.5 - roughness * 0.15 + clearcoat * 0.1, 0, 1)
        g = np.clip(0.3 + metallic * 0.45 - roughness * 0.15 + clearcoat * 0.15, 0, 1)
        b = np.clip(0.35 + metallic * 0.4 - roughness * 0.1 + clearcoat * 0.2, 0, 1)

        rgb = np.stack([r, g, b], axis=2)
        rgb_uint8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)

        img = PILImage.fromarray(rgb_uint8, 'RGB')
        img = img.resize(output_size, PILImage.LANCZOS)
        img.save(cache_file, 'PNG')
        return send_file(cache_file, mimetype='image/png')

    except Exception as e:
        logger.error(f"Swatch error {base_id}/{pattern_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/swatch/pattern/<pattern_id>')
def get_pattern_swatch(pattern_id):
    """Generate a 64x64 swatch showing the actual pattern texture.
    Renders the texture function at 256x256 and visualizes the pattern_val
    (plus M/R channels if available) as a tinted grayscale image.
    Cached to disk for instant repeat loads."""
    try:
        from PIL import Image as PILImage
        import io
        import numpy as np

        cache_file = os.path.join(SWATCH_FOLDER, f"pat_{pattern_id}.png")
        if os.path.exists(cache_file):
            return send_file(cache_file, mimetype='image/png')

        if pattern_id not in engine.PATTERN_REGISTRY:
            return jsonify({"error": f"Unknown pattern: {pattern_id}"}), 404

        registry = engine.PATTERN_REGISTRY[pattern_id]
        tex_fn = registry.get("texture_fn")
        if tex_fn is None:
            # No texture — return a dark gray placeholder
            img = PILImage.new('RGB', (64, 64), (40, 40, 50))
            img.save(cache_file, 'PNG')
            return send_file(cache_file, mimetype='image/png')

        # Render texture at 256x256 for good detail
        render_shape = (256, 256)
        output_size = (64, 64)
        mask = np.ones(render_shape, dtype=np.float32)

        # Call texture function (handle both 3-arg and 4-arg signatures)
        import inspect
        sig = inspect.signature(tex_fn)
        n_params = len(sig.parameters)
        if n_params >= 4:
            tex = tex_fn(render_shape, mask, 42, 1.0)
        elif n_params >= 2:
            tex = tex_fn(render_shape, 42)
        else:
            tex = tex_fn(render_shape)

        # Extract pattern channels
        if isinstance(tex, dict):
            pv = tex.get("pattern_val", np.zeros(render_shape, dtype=np.float32))
            M_pat = tex.get("M_pattern")
            R_pat = tex.get("R_pattern")
        else:
            pv = tex if isinstance(tex, np.ndarray) else np.zeros(render_shape, dtype=np.float32)
            M_pat = None
            R_pat = None

        # Ensure correct shape
        if pv.shape != render_shape:
            from PIL import Image as _Img
            pv_img = _Img.fromarray((np.clip(pv, 0, 1) * 255).astype(np.uint8))
            pv_img = pv_img.resize(render_shape, _Img.LANCZOS)
            pv = np.array(pv_img, dtype=np.float32) / 255.0

        # Get the swatch tint color from the PATTERNS array (from the HTML)
        # Use a neutral teal/blue tint for the pattern
        swatch_color = registry.get("_swatch_rgb")
        if swatch_color is None:
            # Default: cool slate blue tint for spec-map patterns
            tint_r, tint_g, tint_b = 0.55, 0.65, 0.85

        if M_pat is not None and R_pat is not None:
            # Independent channels: visualize M as brightness, R as inverse darkness
            # M_pat high = bright/chrome, R_pat high = dark/rough
            M_p = np.clip(M_pat, 0, 1) if M_pat.shape == render_shape else np.clip(pv, 0, 1)
            R_p = np.clip(R_pat, 0, 1) if R_pat.shape == render_shape else np.clip(1.0 - pv, 0, 1)
            # Create RGB visualization: M → brightness, 1-R → smoothness highlight
            brightness = M_p * 0.6 + (1.0 - R_p) * 0.4
            r = np.clip(brightness * tint_r + 0.1, 0, 1)
            g = np.clip(brightness * tint_g + 0.08, 0, 1)
            b = np.clip(brightness * tint_b + 0.12, 0, 1)
        else:
            # Simple pattern: use pattern_val as luminance with tint
            pv_n = np.clip(pv, 0, 1)
            r = np.clip(pv_n * tint_r * 0.8 + 0.12, 0, 1)
            g = np.clip(pv_n * tint_g * 0.8 + 0.10, 0, 1)
            b = np.clip(pv_n * tint_b * 0.8 + 0.14, 0, 1)

        # Stack and convert to image
        rgb = np.stack([r, g, b], axis=2)
        rgb_uint8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)

        img = PILImage.fromarray(rgb_uint8, 'RGB')
        img = img.resize(output_size, PILImage.LANCZOS)
        img.save(cache_file, 'PNG')
        return send_file(cache_file, mimetype='image/png')

    except Exception as e:
        logger.error(f"Pattern swatch error {pattern_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/swatch/mono/<finish_id>')
def get_mono_swatch(finish_id):
    """Generate a swatch for a monolithic finish.
    Renders at 256x256 for gradient/noise finishes, then downscales to 64x64.
    This fixes Prizm, Chameleon, Multi, and SHOKK thumbnails that need
    higher resolution to show their effects properly."""
    try:
        from PIL import Image as PILImage
        import io
        import numpy as np

        cache_file = os.path.join(SWATCH_FOLDER, f"mono_{finish_id}.png")
        if os.path.exists(cache_file):
            return send_file(cache_file, mimetype='image/png')

        if finish_id not in engine.MONOLITHIC_REGISTRY:
            return jsonify({"error": f"Unknown monolithic: {finish_id}"}), 404

        # Render at 256x256 for proper gradient/noise visibility, then downscale
        render_size = (256, 256)
        output_size = (64, 64)
        shape = render_size
        mask = np.ones(shape, dtype=np.float32)
        spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[finish_id]

        spec = spec_fn(shape, mask, 51, 1.0)

        # Create a neutral gray paint for the monolithic to modify
        neutral = np.ones((render_size[0], render_size[1], 3), dtype=np.float32) * 0.5
        painted = paint_fn(neutral, shape, mask, 51, 1.0, 0.10)

        # Blend spec visualization with paint color
        metallic = spec[:,:,0].astype(np.float32) / 255.0
        roughness = spec[:,:,1].astype(np.float32) / 255.0

        # Use paint color tinted by spec properties
        paint_rgb = np.clip(painted, 0, 1)
        brightness = 0.6 + metallic * 0.4 - roughness * 0.2
        result = paint_rgb * brightness[:,:,np.newaxis]

        rgb_uint8 = (np.clip(result, 0, 1) * 255).astype(np.uint8)

        img = PILImage.fromarray(rgb_uint8, 'RGB')
        # Downscale from render_size to output_size for clean thumbnail
        if render_size != output_size:
            img = img.resize(output_size, PILImage.LANCZOS)
        img.save(cache_file, 'PNG')
        return send_file(cache_file, mimetype='image/png')

    except Exception as e:
        logger.error(f"Mono swatch error {finish_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/upload-composited-paint', methods=['POST'])
def upload_composited_paint():
    """Receive a composited paint PNG (with decals baked in) and save as temp TGA.
    Body: {"paint_data": "data:image/png;base64,...", "iracing_id": "23371"}
    Returns: {"temp_path": "E:/path/to/temp_composited.tga"}
    """
    try:
        from PIL import Image as PILImage
        import numpy as np

        data = request.get_json() or {}
        paint_data = data.get('paint_data', '')
        iracing_id = data.get('iracing_id', '00000')

        if not paint_data or not paint_data.startswith('data:image'):
            return jsonify({"error": "Missing or invalid paint_data"}), 400

        # Decode base64 PNG
        b64_start = paint_data.index(',') + 1
        img_bytes = base64.b64decode(paint_data[b64_start:])
        img = PILImage.open(io.BytesIO(img_bytes)).convert('RGB')

        # Save as TGA (24-bit, top-left origin matching iRacing format)
        temp_dir = os.path.join(OUTPUT_FOLDER, 'temp_composites')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f'composited_{iracing_id}_{int(time.time())}.tga')

        # PIL can save TGA directly
        img.save(temp_path, 'TGA')

        return jsonify({
            "success": True,
            "temp_path": temp_path.replace("\\", "/"),
            "resolution": [img.width, img.height]
        })

    except Exception as e:
        logger.error(f"Composited paint upload error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/upload-spec-map', methods=['POST'])
def upload_spec_map():
    """Receive a spec map TGA/PNG (base64) for import & merge mode.
    Body: {"spec_data": "data:image/...;base64,..."}
      OR: {"spec_path": "E:/path/to/existing_spec.tga"}
    Returns: {"temp_path": "E:/path/to/imported_spec.tga", "resolution": [w, h]}
    """
    try:
        from PIL import Image as PILImage
        import numpy as np

        data = request.get_json() or {}
        spec_data = data.get('spec_data', '')
        spec_path = data.get('spec_path', '')

        temp_dir = os.path.join(OUTPUT_FOLDER, 'temp_spec_imports')
        os.makedirs(temp_dir, exist_ok=True)

        if spec_path and os.path.isfile(spec_path):
            # Direct file path — just validate and return
            img = PILImage.open(spec_path)
            return jsonify({
                "success": True,
                "temp_path": spec_path.replace("\\", "/"),
                "resolution": [img.width, img.height],
                "mode": img.mode,
            })

        if not spec_data or not spec_data.startswith('data:image'):
            return jsonify({"error": "Missing spec_data or spec_path"}), 400

        # Decode base64 image
        b64_start = spec_data.index(',') + 1
        img_bytes = base64.b64decode(spec_data[b64_start:])
        img = PILImage.open(io.BytesIO(img_bytes))

        # Preserve RGBA if present (spec maps are 32-bit RGBA)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        temp_path = os.path.join(temp_dir, f'imported_spec_{int(time.time())}.tga')
        img.save(temp_path, 'TGA')

        logger.info(f"Spec map imported: {img.width}x{img.height} {img.mode} -> {temp_path}")
        return jsonify({
            "success": True,
            "temp_path": temp_path.replace("\\", "/"),
            "resolution": [img.width, img.height],
            "mode": "RGBA",
        })

    except Exception as e:
        logger.error(f"Spec map upload error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/check-file', methods=['POST'])
def check_file():
    """Check if a file path exists on disk. Used by UI to validate Source Paint paths."""
    try:
        data = request.get_json()
        if not data or 'path' not in data:
            return jsonify({"error": "Missing 'path'"}), 400
        path = data['path']
        exists = os.path.exists(path)
        is_file = os.path.isfile(path) if exists else False
        size = os.path.getsize(path) if is_file else 0
        return jsonify({
            "path": path,
            "exists": exists,
            "is_file": is_file,
            "size": size,
            "size_human": f"{size / 1024:.0f} KB" if size > 0 else "0",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/browse-files', methods=['POST'])
def browse_files():
    """Browse filesystem directories. Returns folders and files for the UI file picker.
    Body: {"path": "E:/some/dir", "filter": ".tga"}  (filter is optional)
    Single-pass scandir — detects large dirs dynamically and switches to folders-only.
    """
    try:
        data = request.get_json() or {}
        browse_path = data.get('path', '')
        file_filter = data.get('filter', '').lower()

        # Default starting locations if no path given
        if not browse_path:
            drives = []
            for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                drive = f"{letter}:/"
                if os.path.exists(drive):
                    drives.append({"name": f"{letter}:", "path": drive, "type": "drive"})
            user_home = os.path.expanduser("~")
            quick_navs = []
            iracing_paint = os.path.join(user_home, "Documents", "iRacing", "paint")
            if os.path.isdir(iracing_paint):
                quick_navs.append({"name": "iRacing Paint Folder", "path": iracing_paint.replace("\\", "/"), "type": "shortcut"})
            cfg = load_config()
            for car_name, car_path in cfg.get("car_paths", {}).items():
                if os.path.isdir(car_path):
                    quick_navs.append({"name": f"Live Link: {car_name}", "path": car_path.replace("\\", "/"), "type": "shortcut"})
            return jsonify({"path": "", "drives": drives, "quick_navs": quick_navs, "items": []})

        browse_path = os.path.normpath(browse_path)
        if not os.path.isdir(browse_path):
            return jsonify({"error": f"Not a directory: {browse_path}"}), 400

        import subprocess as _sp

        MAX_FILES = 200
        LARGE_DIR_THRESHOLD = 300
        folders = []
        files = []
        total_files = 0
        entry_count = 0
        large_dir = False

        # --- FAST PATH: use Windows dir /b /ad to get ONLY folder names ---
        # This avoids Python touching every file entry (which triggers Defender scans).
        # We first try the fast path; if it finds many entries we skip the slow scandir.
        fast_folders = None
        try:
            r = _sp.run(
                ['cmd', '/c', 'dir', '/b', '/ad', browse_path],
                capture_output=True, text=True, timeout=8
            )
            if r.returncode == 0 and r.stdout.strip():
                raw_names = [n.strip() for n in r.stdout.splitlines() if n.strip()]
                fast_folders = []
                for nm in raw_names:
                    if nm.startswith('.'):
                        continue
                    fp = os.path.join(browse_path, nm).replace("\\", "/")
                    fast_folders.append({"name": nm, "path": fp, "type": "folder"})
        except Exception:
            fast_folders = None  # fall back to scandir

        # Decide: if dir /b /ad returned results, use a quick entry count to decide fast vs slow
        if fast_folders is not None:
            # Quick count: how many total entries? Use dir /b (all) piped to find /c
            try:
                r2 = _sp.run(
                    ['cmd', '/c', 'dir', '/b', browse_path, '|', 'find', '/c', '/v', '""'],
                    capture_output=True, text=True, timeout=8, shell=True
                )
                entry_count = int(r2.stdout.strip()) if r2.returncode == 0 else 0
            except Exception:
                entry_count = len(fast_folders) + 500  # assume large if count fails

            if entry_count > LARGE_DIR_THRESHOLD:
                # Large directory — use ONLY the folder names from dir /b /ad
                large_dir = True
                folders = fast_folders
                folders.sort(key=lambda x: x["name"].lower())
                items = folders

                parent = os.path.dirname(browse_path)
                parent_path = parent.replace("\\", "/") if parent != browse_path else ""

                return jsonify({
                    "path": browse_path.replace("\\", "/"),
                    "parent": parent_path,
                    "items": items,
                    "total_folders": len(folders),
                    "total_files": 0,
                    "hidden_files": -1,
                    "large_dir": True,
                    "entry_count": entry_count,
                })

        # --- SLOW PATH: small directory, use scandir for full file listing ---
        try:
            with os.scandir(browse_path) as scanner:
                for entry in scanner:
                    if entry.name.startswith('.'):
                        continue
                    entry_count += 1
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            folders.append({"name": entry.name, "path": entry.path.replace("\\", "/"), "type": "folder"})
                        else:
                            if file_filter and not entry.name.lower().endswith(file_filter):
                                continue
                            total_files += 1
                            if len(files) < MAX_FILES:
                                try:
                                    size = entry.stat(follow_symlinks=False).st_size
                                except OSError:
                                    size = 0
                                files.append({
                                    "name": entry.name,
                                    "path": entry.path.replace("\\", "/"),
                                    "type": "file",
                                    "size": size,
                                    "size_human": f"{size / 1024:.0f} KB" if size > 0 else "0",
                                })
                    except OSError:
                        continue
        except PermissionError:
            return jsonify({"error": "Permission denied", "path": browse_path}), 403

        hidden_files = total_files - len(files)
        folders.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())
        items = folders + files

        parent = os.path.dirname(browse_path)
        parent_path = parent.replace("\\", "/") if parent != browse_path else ""

        return jsonify({
            "path": browse_path.replace("\\", "/"),
            "parent": parent_path,
            "items": items,
            "total_folders": len(folders),
            "total_files": total_files,
            "hidden_files": hidden_files,
            "large_dir": False,
            "entry_count": entry_count,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/iracing-cars', methods=['GET'])
def list_iracing_cars():
    """Discover car folders in the iRacing paint directory.
    Returns list of car folder names that exist in ~/Documents/iRacing/paint/
    """
    try:
        user_home = os.path.expanduser("~")
        iracing_paint = os.path.join(user_home, "Documents", "iRacing", "paint")
        if not os.path.isdir(iracing_paint):
            return jsonify({"cars": [], "paint_dir": "", "error": "iRacing paint folder not found"})

        cars = []
        for entry in sorted(os.listdir(iracing_paint)):
            car_path = os.path.join(iracing_paint, entry)
            if os.path.isdir(car_path):
                # Check for existing paint files
                tga_count = len([f for f in os.listdir(car_path) if f.endswith('.tga')])
                cars.append({
                    "name": entry,
                    "path": car_path.replace("\\", "/"),
                    "tga_count": tga_count
                })

        return jsonify({
            "cars": cars,
            "paint_dir": iracing_paint.replace("\\", "/"),
            "count": len(cars)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/deploy-to-iracing', methods=['POST'])
def deploy_to_iracing():
    """One-click deploy: copy rendered TGAs from a job to an iRacing car folder.
    Body: {"job_id": "...", "car_folder": "dallaraarca", "iracing_id": "23371"}
    """
    try:
        data = request.get_json() or {}
        job_id = data.get("job_id", "")
        car_folder = data.get("car_folder", "")
        iracing_id = data.get("iracing_id", "00000")

        if not job_id:
            return jsonify({"error": "Missing job_id"}), 400
        if not car_folder:
            return jsonify({"error": "Missing car_folder"}), 400

        user_home = os.path.expanduser("~")
        iracing_paint = os.path.join(user_home, "Documents", "iRacing", "paint")
        target_dir = os.path.join(iracing_paint, car_folder)

        # Create car folder if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)

        job_dir = os.path.join(OUTPUT_FOLDER, f"job_{job_id}")
        if not os.path.isdir(job_dir):
            return jsonify({"error": f"Job not found: {job_id}"}), 404

        # Deploy all TGA files
        deployed = []
        for fname in os.listdir(job_dir):
            if fname.endswith('.tga'):
                src = os.path.join(job_dir, fname)
                dst = os.path.join(target_dir, fname)
                # Backup original if exists
                backup = os.path.join(target_dir, f"ORIGINAL_{fname}")
                if os.path.exists(dst) and not os.path.exists(backup):
                    shutil.copy2(dst, backup)
                shutil.copy2(src, dst)
                deployed.append(fname)
                logger.info(f"Deploy: {fname} -> {target_dir}")

        return jsonify({
            "success": True,
            "deployed": deployed,
            "target": target_dir.replace("\\", "/"),
            "message": f"Deployed {len(deployed)} files to {car_folder}. Alt+Tab to iRacing and press Ctrl+R!"
        })

    except Exception as e:
        logger.error(f"Deploy error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/config', methods=['GET'])
def get_config():
    """Return current config."""
    return jsonify(load_config())


@app.route('/config', methods=['POST'])
def set_config():
    """
    Update config. Merges with existing config.

    JSON body (all fields optional):
    {
        "iracing_id": "23371",
        "live_link_enabled": true,
        "active_car": "dallaraarca",
        "car_paths": {
            "dallaraarca": "C:/Users/You/Documents/iRacing/paint/dallaraarca",
            "stockcar_camaro": "C:/Users/You/Documents/iRacing/paint/stockcar_camaro"
        }
    }
    """
    try:
        updates = request.get_json()
        if not updates:
            return jsonify({"error": "No JSON body"}), 400

        cfg = load_config()

        # Merge updates
        if "iracing_id" in updates:
            cfg["iracing_id"] = str(updates["iracing_id"])
        if "live_link_enabled" in updates:
            cfg["live_link_enabled"] = bool(updates["live_link_enabled"])
        if "active_car" in updates:
            cfg["active_car"] = updates["active_car"]
        if "use_custom_number" in updates:
            cfg["use_custom_number"] = bool(updates["use_custom_number"])
        if "car_paths" in updates:
            cfg.setdefault("car_paths", {}).update(updates["car_paths"])

        # Validate car paths exist
        warnings = []
        for car, path in cfg.get("car_paths", {}).items():
            if not os.path.isdir(path):
                warnings.append(f"Path for '{car}' not found: {path}")

        save_config(cfg)
        result = {"success": True, "config": cfg}
        if warnings:
            result["warnings"] = warnings
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Legacy endpoint (backward compat with old UI code)
@app.route('/apply-finish', methods=['POST'])
def apply_finish_legacy():
    """Legacy endpoint — redirects to /render format."""
    try:
        if 'paint_file' not in request.files:
            return jsonify({"error": "No paint file provided. Use /render with JSON instead."}), 400

        file = request.files['paint_file']
        filename = f"upload_{int(time.time())}_{file.filename}"
        upload_path = os.path.join(OUTPUT_FOLDER, 'uploads', filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)

        zones_str = request.form.get('zones', '[]')
        zones = json.loads(zones_str)
        iracing_id = request.form.get('iracing_id', '00000')
        req_id = request.form.get('request_id', str(int(time.time())))
        # Car prefix for legacy endpoint — read from config
        _legacy_cfg = load_config()
        _legacy_prefix = "car_num" if _legacy_cfg.get("use_custom_number", True) else "car"

        job_dir = os.path.join(OUTPUT_FOLDER, f"job_{req_id}")
        os.makedirs(job_dir, exist_ok=True)

        paint_rgb, combined_spec, masks = engine.build_multi_zone(
            paint_file=upload_path,
            output_dir=job_dir,
            zones=zones,
            iracing_id=iracing_id,
            car_prefix=_legacy_prefix,
        )

        return jsonify({
            "success": True,
            "job_id": req_id,
            "files": {
                "paint_tga": os.path.join(job_dir, f"{_legacy_prefix}_{iracing_id}.tga"),
                "spec_tga": os.path.join(job_dir, f"car_spec_{iracing_id}.tga"),
                "preview_paint": f"/preview/{req_id}/PREVIEW_paint.png",
                "preview_spec": f"/preview/{req_id}/PREVIEW_spec.png",
            }
        })

    except Exception as e:
        logger.error(f"Legacy endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


# ================================================================
# CLEANUP OLD RENDER JOBS
# ================================================================

@app.route('/cleanup', methods=['POST'])
def cleanup_jobs():
    """Delete old render job folders to free disk space.
    Body (optional): {"max_age_hours": 24}   (default: delete all jobs)
    """
    try:
        data = request.get_json() or {}
        max_age_hours = data.get("max_age_hours", 0)  # 0 = delete all

        deleted = 0
        freed_bytes = 0
        kept = 0
        now = time.time()

        if not os.path.exists(OUTPUT_FOLDER):
            return jsonify({"success": True, "deleted": 0, "kept": 0, "freed_mb": 0})

        for entry in os.listdir(OUTPUT_FOLDER):
            if not entry.startswith("job_"):
                continue
            job_path = os.path.join(OUTPUT_FOLDER, entry)
            if not os.path.isdir(job_path):
                continue

            # Check age if max_age_hours > 0
            if max_age_hours > 0:
                age_hours = (now - os.path.getmtime(job_path)) / 3600
                if age_hours < max_age_hours:
                    kept += 1
                    continue

            # Calculate size before deleting
            for root, dirs, files in os.walk(job_path):
                for f in files:
                    try:
                        freed_bytes += os.path.getsize(os.path.join(root, f))
                    except:
                        pass

            shutil.rmtree(job_path, ignore_errors=True)
            deleted += 1

        freed_mb = round(freed_bytes / (1024 * 1024), 1)
        logger.info(f"Cleanup: deleted {deleted} jobs, freed {freed_mb}MB, kept {kept}")
        return jsonify({
            "success": True,
            "deleted": deleted,
            "kept": kept,
            "freed_mb": freed_mb,
            "message": f"Cleaned {deleted} render jobs, freed {freed_mb}MB"
        })
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        return jsonify({"error": str(e)}), 500


# ================================================================
# MAIN
# ================================================================

def auto_cleanup_old_jobs(max_age_hours=24):
    """Remove job directories older than max_age_hours to prevent disk bloat."""
    if not os.path.exists(OUTPUT_FOLDER):
        return
    cutoff = time.time() - (max_age_hours * 3600)
    cleaned = 0
    for name in os.listdir(OUTPUT_FOLDER):
        job_path = os.path.join(OUTPUT_FOLDER, name)
        if os.path.isdir(job_path) and name.startswith("job_"):
            try:
                mtime = os.path.getmtime(job_path)
                if mtime < cutoff:
                    shutil.rmtree(job_path, ignore_errors=True)
                    cleaned += 1
            except Exception:
                pass
    if cleaned:
        logger.info(f"Auto-cleanup: removed {cleaned} job dirs older than {max_age_hours}h")


if __name__ == '__main__':
    import socket

    # Auto-cleanup old renders on startup
    auto_cleanup_old_jobs(max_age_hours=24)

    cfg = load_config()
    bases = len(engine.BASE_REGISTRY)
    patterns = len(engine.PATTERN_REGISTRY)
    monos = len(engine.MONOLITHIC_REGISTRY)
    combos = bases * patterns
    has_expansion = bases > 60  # Original engine has ~55 bases

    # BUILD 27: HARDCODED PORT 59876 — eliminates any port-squatting possibility
    # No env var, no scanning, no SO_REUSEADDR ambiguity
    port = 59876

    # Write chosen port for external discovery
    port_file = os.path.join(SERVER_DIR, '.server_port')
    with open(port_file, 'w') as f:
        f.write(str(port))

    print("=" * 60)
    print("  SHOKKER PAINT BOOTH AG — Build 29")
    print("  Powered by Shokker Engine v4.0 PRO — 24K Arsenal")
    if has_expansion:
        print(f"  24K Arsenal LOADED — {bases} bases / {patterns} patterns / {monos} monolithics")
    else:
        print(f"  WARNING: 24K Arsenal NOT loaded — only {bases} bases / {patterns} patterns")
    print(f"  {combos}+ finish combinations ready")
    print(f"  iRacing ID: {cfg.get('iracing_id', 'not set')}")
    if cfg.get("live_link_enabled") and cfg.get("active_car"):
        car_path = cfg.get("car_paths", {}).get(cfg["active_car"], "???")
        print(f"  Live Link: {cfg['active_car']} => {car_path}")
    else:
        print("  Live Link: not configured")
    print(f"  Listening on http://localhost:{port}")
    print("=" * 60)


    # Threaded WSGI server (handles concurrent requests)
    import socketserver
    from wsgiref.simple_server import WSGIServer, WSGIRequestHandler

    class ThreadedWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
        daemon_threads = True
        allow_reuse_address = False  # Will FAIL fast if port already taken

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format, *args):
            # Route HTTP logs through standard logger instead of stderr
            logger.info(format % args)

    try:
        server = ThreadedWSGIServer(('127.0.0.1', port), QuietHandler)
        server.set_app(app)
        logger.info(f"Server bound to port {port} — serving")
        server.serve_forever()
    except OSError as e:
        logger.error(f"Port {port} already in use: {e}")
        # Try fallback port
        alt_port = 59877
        try:
            server = ThreadedWSGIServer(('127.0.0.1', alt_port), QuietHandler)
            server.set_app(app)
            logger.info(f"Fallback: bound to port {alt_port}")
            server.serve_forever()
        except Exception as e2:
            logger.error(f"Fallback port {alt_port} also failed: {e2}")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        logger.error(traceback.format_exc())
