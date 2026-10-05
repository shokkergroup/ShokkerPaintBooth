"""Render file serving and keep/reset helpers for Shokker Paint Booth."""

import io
import os
import json
import time
import shutil
from datetime import datetime

from flask import jsonify, request, send_file
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


_tga_preview_cache = {}
_TGA_CACHE_MAX = 8


def _coerce_output_dir(raw):
    """Resolve a USER-pasted iRacing/output path to an EXISTING directory.

    Local mirror of server._coerce_output_dir (kept tiny so this module stays
    import-light). Accepts a folder OR a file path: customers often paste the
    full ``...\\paint\\<car>\\car_num_<id>.tga`` FILE path into the output-folder
    field; ``os.path.isdir`` of that file is False. If the value isn't a
    directory but its parent IS, use the parent. Returns the directory, or None.
    """
    if not raw:
        return None
    p = os.path.normpath(str(raw).strip().strip('"').strip("'"))
    if os.path.isdir(p):
        return p
    parent = os.path.dirname(p)
    if parent and os.path.isdir(parent):
        return parent
    return None

# [SPB-RECENTS-001] How many recent renders are kept on disk (rotating; oldest
# auto-deleted). Owner ask: "it SAVES the last 10 RENDERS ... overwritten by new
# ones AUTOMATICALLY ... so you could recall one of the previous 10."
_MAX_RECENT_RENDERS = 10


def _purge_recent_renders(base, keep=_MAX_RECENT_RENDERS):
    """Keep only the newest ``keep`` render_* folders under ``base`` (by mtime)."""
    try:
        if not os.path.isdir(base):
            return
        dirs = [
            d for d in os.listdir(base)
            if os.path.isdir(os.path.join(base, d))
        ]
        dirs.sort(key=lambda d: os.path.getmtime(os.path.join(base, d)), reverse=True)
        for old in dirs[keep:]:
            shutil.rmtree(os.path.join(base, old), ignore_errors=True)
    except Exception as _spb_ex:
        _spb_swallow('_purge_recent_renders@L54', _spb_ex)


def register_render_file_routes(
    app, *, output_job_dir_resolver, logger, recent_renders_dir=None, external_write_guard
):
    """Register render output file routes.

    ``recent_renders_dir`` (optional): a writable folder where the rotating last-N
    renders (paint.png + spec.png + recipe.json) are stored for recall.
    """

    @app.route('/save-render-to-keep', methods=['POST'])
    def save_render_to_keep():
        """Copy current render files into a timestamped keep folder."""
        try:
            data = request.get_json() or {}
            if not isinstance(data, dict):
                return jsonify({"success": False, "error": "Request body must be a JSON object"}), 400
            output_dir = (data.get("output_dir") or "").strip()
            iracing_id = ''.join(ch for ch in str(data.get("iracing_id") or "").strip() if ch.isdigit())
            if not output_dir:
                return jsonify({"success": False, "error": "Missing output_dir"}), 400
            if not iracing_id:
                return jsonify({
                    "success": False,
                    "error": "Missing iracing_id. Set the iRacing customer ID before using Save to keep.",
                }), 400
            target_dir = _coerce_output_dir(output_dir)
            if not target_dir:
                return jsonify({
                    "success": False,
                    "error": f"Output folder not found: {os.path.normpath(output_dir)} (point to a FOLDER, not a file)",
                }), 400

            keep_subfolder = "Shokker Paint Booth"
            keep_dir = os.path.join(target_dir, keep_subfolder)
            denial = external_write_guard(keep_dir, "save-render-to-keep")
            if denial:
                return jsonify(denial), 403
            os.makedirs(keep_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            saved = []
            channel_tgas = ("paint_base.tga", "spec_metallic.tga", "spec_roughness.tga", "spec_clearcoat.tga", "spec_mask.tga")
            current_render_tgas = {
                f"car_num_{iracing_id}.tga",
                f"car_{iracing_id}.tga",
                f"car_spec_{iracing_id}.tga",
            }
            for fname in os.listdir(target_dir):
                if not fname.endswith(".tga"):
                    continue
                if fname not in current_render_tgas and fname not in channel_tgas:
                    continue
                src = os.path.join(target_dir, fname)
                if not os.path.isfile(src):
                    continue
                base, ext = os.path.splitext(fname)
                dest_name = f"{base}_{ts}{ext}"
                dest = os.path.join(keep_dir, dest_name)
                try:
                    shutil.copy2(src, dest)
                    saved.append(dest_name)
                except Exception as e:
                    logger.warning(f"save-render-to-keep: could not copy {fname}: {e}")
            if not saved:
                return jsonify({
                    "success": False,
                    "error": "No render TGA files found in the output folder. Render first, then click Save to keep.",
                }), 400
            return jsonify({
                "success": True,
                "path": keep_dir,
                "saved_files": saved,
                "message": f"Saved {len(saved)} file(s) to {keep_subfolder}/",
            })
        except Exception as e:
            logger.exception("save-render-to-keep")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/preview/<job_id>/<filename>', methods=['GET'])
    def get_preview(job_id, filename):
        """Serve preview PNGs to the browser."""
        safe_job = os.path.basename(job_id)
        safe_file = os.path.basename(filename)
        job_root = output_job_dir_resolver(safe_job)
        if job_root:
            path = os.path.join(job_root, safe_file)
            if os.path.exists(path):
                # [ULTRACODE 2026-08-22 M8a] job outputs are content-immutable
                # (the job id uniquifies) — without this header every history
                # thumb rebuild re-downloaded the full ~1MB+ 2048 PNG.
                resp = send_file(path, mimetype='image/png')
                resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                return resp
        return jsonify({"error": "File not found"}), 404

    @app.route('/download/<job_id>/<filename>', methods=['GET'])
    def download_file(job_id, filename):
        """Download output TGA files."""
        safe_job = os.path.basename(job_id)
        safe_file = os.path.basename(filename)
        job_root = output_job_dir_resolver(safe_job)
        if job_root:
            path = os.path.join(job_root, safe_file)
            if os.path.exists(path):
                return send_file(path, as_attachment=True, download_name=safe_file)
        return jsonify({"error": "File not found"}), 404

    @app.route('/reset-backup', methods=['POST'])
    def reset_backup():
        """Delete ORIGINAL_ backups so the next render uses the current source file."""
        try:
            data = request.get_json() or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            paint_file = data.get("paint_file", "")
            if not paint_file:
                return jsonify({"error": "Missing paint_file"}), 400
            paint_file = os.path.normpath(os.path.abspath(paint_file))
            source_dir = os.path.dirname(paint_file)
            denial = external_write_guard(source_dir, "reset-backup")
            if denial:
                return jsonify(denial), 403
            basename = os.path.basename(paint_file)
            backup_path = os.path.join(source_dir, f"ORIGINAL_{basename}")
            deleted = []
            if os.path.exists(backup_path):
                os.remove(backup_path)
                deleted.append(backup_path)
                logger.info(f"Reset backup: deleted {backup_path}")
            output_backup = os.path.join(source_dir, f"ORIGINAL_car_spec_{data.get('iracing_id', '00000')}.tga")
            if os.path.exists(output_backup):
                os.remove(output_backup)
                deleted.append(output_backup)
            return jsonify({
                "success": True,
                "deleted": deleted,
                "message": f"Cleared {len(deleted)} backup(s). Next render will use the current source file.",
            })
        except Exception as e:
            logger.error(f"Reset backup error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/preview-tga', methods=['POST'])
    def preview_tga():
        """Convert a local TGA file to PNG and serve it for browser display."""
        logger.debug("[preview-tga] TGA preview requested")
        try:
            from PIL import Image as PILImage

            data = request.get_json() or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            tga_path = data.get('path', '')
            if not tga_path or not os.path.isfile(tga_path):
                return jsonify({"error": "File not found"}), 404

            try:
                mtime = os.path.getmtime(tga_path)
            except OSError:
                mtime = 0
            cache_key = f"{tga_path}|{mtime}"
            if cache_key in _tga_preview_cache:
                logger.debug(f"[preview-tga] Cache hit: {os.path.basename(tga_path)}")
                buf = io.BytesIO(_tga_preview_cache[cache_key])
                buf.seek(0)
                return send_file(buf, mimetype='image/png')

            img = PILImage.open(tga_path)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            png_bytes = buf.getvalue()

            if len(_tga_preview_cache) >= _TGA_CACHE_MAX:
                oldest_key = next(iter(_tga_preview_cache))
                del _tga_preview_cache[oldest_key]
            _tga_preview_cache[cache_key] = png_bytes
            logger.debug(f"[preview-tga] Cached: {os.path.basename(tga_path)} ({len(png_bytes)//1024}KB)")

            buf.seek(0)
            return send_file(io.BytesIO(png_bytes), mimetype='image/png')
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ====================================================================
    # [SPB-RECENTS-001] Rotating "last N renders" — saved to disk so they can
    # be recalled (full recipe restored) even after an app restart. Oldest is
    # auto-overwritten. Owner: "in the file folder it SAVES the last 10 RENDERS
    # ... and they get overwritten by new ones AUTOMATICALLY ... recall one."
    # ====================================================================
    @app.route('/recent-renders/save', methods=['POST'])
    def recent_renders_save():
        """Copy the just-finished render's paint+spec PNGs and write recipe.json
        into a new rotating slot; prune to the newest ``_MAX_RECENT_RENDERS``."""
        try:
            if not recent_renders_dir:
                return jsonify({"success": False, "error": "Recent renders dir not configured"}), 500
            data = request.get_json(silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"success": False, "error": "Body must be a JSON object"}), 400
            recipe = data.get("recipe") if isinstance(data.get("recipe"), dict) else {}
            job_id = os.path.basename(str(data.get("job_id") or "").strip())

            os.makedirs(recent_renders_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            slot = f"render_{ts}"
            slot_dir = os.path.join(recent_renders_dir, slot)
            _n = 1
            while os.path.exists(slot_dir):
                slot = f"render_{ts}_{_n}"
                slot_dir = os.path.join(recent_renders_dir, slot)
                _n += 1
            os.makedirs(slot_dir, exist_ok=True)

            # Copy the rendered paint + spec preview PNGs out of the job dir so the
            # recall thumbnails survive even after the job's temp dir is cleaned.
            copied = {}
            job_root = output_job_dir_resolver(job_id) if job_id else None
            if job_root and os.path.isdir(job_root):
                for fname in sorted(os.listdir(job_root)):
                    low = fname.lower()
                    if not low.endswith('.png') or 'helmet' in low or 'suit' in low:
                        continue
                    if 'spec' in low and 'spec' not in copied:
                        try:
                            shutil.copy2(os.path.join(job_root, fname), os.path.join(slot_dir, 'spec.png'))
                            copied['spec'] = True
                        except Exception as e:
                            logger.warning(f"recent-renders: spec copy failed: {e}")
                    elif 'paint' in low and 'paint' not in copied:
                        try:
                            shutil.copy2(os.path.join(job_root, fname), os.path.join(slot_dir, 'paint.png'))
                            copied['paint'] = True
                        except Exception as e:
                            logger.warning(f"recent-renders: paint copy failed: {e}")

            # recipe.json carries the full zone snapshot (for recall) + metadata.
            recipe_out = dict(recipe)
            recipe_out['slot'] = slot
            recipe_out.setdefault('saved_at', time.time())
            try:
                with open(os.path.join(slot_dir, 'recipe.json'), 'w', encoding='utf-8') as f:
                    json.dump(recipe_out, f)
            except Exception as e:
                logger.warning(f"recent-renders: recipe write failed: {e}")

            _purge_recent_renders(recent_renders_dir)
            return jsonify({"success": True, "slot": slot, "copied": copied})
        except Exception as e:
            logger.exception("recent-renders/save")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/recent-renders/list', methods=['GET'])
    def recent_renders_list():
        """Newest-first list of saved renders (metadata + recipe + image URLs)."""
        out = []
        try:
            if recent_renders_dir and os.path.isdir(recent_renders_dir):
                dirs = [
                    d for d in os.listdir(recent_renders_dir)
                    if os.path.isdir(os.path.join(recent_renders_dir, d))
                ]
                dirs.sort(key=lambda d: os.path.getmtime(os.path.join(recent_renders_dir, d)), reverse=True)
                for d in dirs[:_MAX_RECENT_RENDERS]:
                    slot_dir = os.path.join(recent_renders_dir, d)
                    recipe = {}
                    rp = os.path.join(slot_dir, 'recipe.json')
                    if os.path.isfile(rp):
                        try:
                            with open(rp, 'r', encoding='utf-8') as f:
                                recipe = json.load(f)
                        except Exception:
                            recipe = {}
                    out.append({
                        "slot": d,
                        "mtime": os.path.getmtime(slot_dir),
                        "has_paint": os.path.isfile(os.path.join(slot_dir, 'paint.png')),
                        "has_spec": os.path.isfile(os.path.join(slot_dir, 'spec.png')),
                        "paint_url": f"/recent-renders/{d}/paint.png",
                        "spec_url": f"/recent-renders/{d}/spec.png",
                        "recipe": recipe,
                    })
            return jsonify({"success": True, "renders": out, "max": _MAX_RECENT_RENDERS})
        except Exception as e:
            logger.exception("recent-renders/list")
            return jsonify({"success": False, "error": str(e), "renders": []}), 500

    @app.route('/recent-renders/<slot>/<filename>', methods=['GET'])
    def recent_renders_file(slot, filename):
        """Serve a saved render's paint.png / spec.png / recipe.json."""
        if not recent_renders_dir:
            return jsonify({"error": "not configured"}), 404
        safe_slot = os.path.basename(slot)
        safe_file = os.path.basename(filename)
        path = os.path.join(recent_renders_dir, safe_slot, safe_file)
        if os.path.isfile(path):
            if safe_file.endswith('.json'):
                return send_file(path, mimetype='application/json')
            return send_file(path, mimetype='image/png')
        return jsonify({"error": "File not found"}), 404
