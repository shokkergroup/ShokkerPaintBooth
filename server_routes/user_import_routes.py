"""USER IMPORTS routes — local paint/pattern/spec import library."""

from __future__ import annotations

import os
import hashlib
import json
import re
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from flask import Response, jsonify, request, send_file
from PIL import Image
from werkzeug.utils import secure_filename

from engine.paint_v2.user_imports import get_catalog_entries, reload_user_imports, sync_registry
from engine.paint_v2.user_imports_inbox import process_inbox
from engine.paint_v2.user_imports_ingest import (
    build_saved_preview_urls,
    delete_entry,
    export_all_packs,
    export_entry_zip,
    import_pack_zip,
    import_paint_files,
    import_paint_with_spec_files,
    import_pattern_files,
    import_spec_overlay_files,
    preview_fracture_import,
    preview_import,
    preview_paint_with_spec_files,
    preview_spec_overlay_import,
    rebake_dna_spec,
    render_channel_preview_png,
    render_spec_overlay_channel_preview_png,
    resolve_paint_image,
    resolve_preview_image,
    resolve_spec_image,
    resolve_spec_overlay_image,
    update_spec_overlay_channels,
    validate_community_drop_pack,
)
from engine.paint_v2.user_imports_engine_preview import render_engine_uv_bytes
from engine.paint_v2.import_dna_style_catalog import DNA_STYLES
from engine.paint_v2.user_imports_spec_dna import (
    get_dna_style_catalog,
    get_spec_ink_swatches,
    spec_to_rgb_preview,
)
from engine.paint_v2.user_imports_paths import DROP_PACK_EXT, is_drop_pack_filename, user_imports_root
from engine.paint_v2.import_dna_saved_presets import (
    delete_preset,
    list_saved_presets,
    recipe_from_plan,
    save_preset,
)
from engine.paint_v2.user_imports_shokk_world import (
    WORLD_VARIANT_COUNT,
    commit_world_variants,
    generate_world_variant,
    preview_dna_remix,
    purge_staging_for_session,
    reroll_world_variant,
    stage_variant_for_booth,
    start_shokk_world_session,
)
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def register_user_import_routes(
    app,
    *,
    engine_getter,
    finish_catalog_cache_clear,
    logger,
    external_write_guard=None,
) -> None:
    """Register USER IMPORTS CRUD/import/export routes."""

    community_default_base = "https://shokker-paint-booth.downndirtytn.chatgpt.site"
    community_id_re = re.compile(r"^drp_[a-z0-9]{20,64}$")

    class _NoCommunityRedirects(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise urllib.error.HTTPError(req.full_url, code, "Redirect blocked", headers, fp)

    def _community_base() -> str:
        candidate = (os.environ.get("SPB_COMMUNITY_DROPS_API_BASE") or community_default_base).rstrip("/")
        parsed = urllib.parse.urlparse(candidate)
        is_loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        if not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Invalid SHOKK DROPS service origin")
        if parsed.scheme != "https" and not (parsed.scheme == "http" and is_loopback):
            raise ValueError("SHOKK DROPS service must use HTTPS")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("Invalid SHOKK DROPS service origin")
        return candidate

    def _community_url(path: str) -> str:
        base = _community_base()
        url = urllib.parse.urljoin(base + "/", path.lstrip("/"))
        if urllib.parse.urlparse(url).netloc != urllib.parse.urlparse(base).netloc:
            raise ValueError("Community URL escaped its trusted origin")
        return url

    def _community_open(url: str):
        request_headers = {"Accept": "application/json", "User-Agent": "ShokkerPaintBooth/6 SHOKKDrops/1"}
        return urllib.request.build_opener(_NoCommunityRedirects()).open(
            urllib.request.Request(url, headers=request_headers), timeout=20
        )

    def _community_metadata(drop_id: str) -> dict:
        if not community_id_re.fullmatch(drop_id or ""):
            raise ValueError("Invalid SHOKK DROP id")
        with _community_open(_community_url(f"/api/drops/{urllib.parse.quote(drop_id)}")) as response:
            raw = response.read(262_145)
        if len(raw) > 262_144:
            raise ValueError("Community metadata response is too large")
        data = json.loads(raw.decode("utf-8"))
        package = data.get("package") if isinstance(data, dict) else None
        if (
            not isinstance(data, dict)
            or data.get("schema") != "spb-community-drop/1"
            or data.get("id") != drop_id
            or data.get("version") != 1
            or data.get("status") != "approved"
            or not isinstance(package, dict)
            or not re.fullmatch(r"[0-9a-f]{64}", str(package.get("sha256") or ""))
            or not isinstance(package.get("bytes"), int)
            or not (1 <= package["bytes"] <= 32 * 1024 * 1024)
        ):
            raise ValueError("Community service returned invalid or unapproved metadata")
        expected_path = f"/api/drops/{drop_id}/download"
        package_url = _community_url(str(package.get("url") or ""))
        if urllib.parse.urlparse(package_url).path != expected_path:
            raise ValueError("Community package URL is invalid")
        data["package"]["absolute_url"] = package_url
        previews = data.get("previews") or {}
        if not isinstance(previews, dict):
            raise ValueError("Community preview metadata is invalid")
        preview_urls = {}
        for kind in ("paint", "spec"):
            preview_url = _community_url(str(previews.get(kind) or ""))
            if urllib.parse.urlparse(preview_url).path != f"/api/drops/{drop_id}/preview/{kind}":
                raise ValueError("Community preview URL is invalid")
            preview_urls[kind] = preview_url
        data["previews"] = preview_urls
        return data

    @app.before_request
    def _guard_user_import_storage():
        if not request.path.startswith("/api/user-imports") or external_write_guard is None:
            return None
        get_write_exact = {
            "/api/user-imports",
            "/api/user-imports/dna-presets",
            "/api/user-imports/export-all",
        }
        get_write_prefixes = (
            "/api/user-imports/dna-style-thumb/",
            "/api/user-imports/export/",
        )
        writes = request.method in ("POST", "PUT", "PATCH", "DELETE")
        writes = (
            writes
            or request.path in get_write_exact
            or any(request.path.startswith(prefix) for prefix in get_write_prefixes)
        )
        if not writes:
            return None
        denial = external_write_guard(user_imports_root(), "user-import-storage")
        if denial:
            return jsonify(denial), 403
        return None

    def _sync_engine():
        engine = engine_getter()
        count = sync_registry(engine.MONOLITHIC_REGISTRY, engine.PATTERN_REGISTRY)
        finish_catalog_cache_clear()
        return count

    @app.route("/api/user-imports", methods=["GET"])
    def api_user_imports_list():
        try:
            reload_user_imports()
            return jsonify({"entries": get_catalog_entries(), "root": str(user_imports_root())})
        except Exception as e:
            logger.error(f"[user-imports] list error: {e}")
            return jsonify({"entries": [], "error": str(e)})

    @app.route("/api/user-imports/dna-styles", methods=["GET"])
    def api_user_imports_dna_styles():
        from engine.paint_v2.import_dna_style_catalog import WORLD_VARIANT_COUNT as WVC
        from engine.paint_v2.import_dna_style_catalog import (
            WORLD_SLOT_INSANE,
            WORLD_SLOT_REMIX,
            WORLD_SLOT_STANDARD,
        )

        return jsonify({
            "styles": list(DNA_STYLES),
            "catalog": get_dna_style_catalog(),
            "spec_inks": get_spec_ink_swatches(),
            "world_layout": {
                "total": WVC,
                "standard": WORLD_SLOT_STANDARD,
                "remix": WORLD_SLOT_REMIX,
                "insane": WORLD_SLOT_INSANE,
            },
        })

    @app.route("/api/user-imports/dna-style-thumb/<style_id>.png", methods=["GET"])
    def api_user_imports_dna_style_thumb(style_id: str):
        """Spec-preview swatch for DNA style picker (cached on disk)."""
        from engine.paint_v2.dna_style_swatches import ensure_dna_style_swatch

        sid = (style_id or "").strip().replace(".png", "")
        if sid not in DNA_STYLES:
            return jsonify({"error": "Unknown style"}), 404
        try:
            path = ensure_dna_style_swatch(sid)
            return send_file(
                path,
                mimetype="image/png",
                max_age=86400 * 30,
                conditional=True,
            )
        except Exception as e:
            logger.error(f"[dna-style-thumb] {sid}: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/dna-presets", methods=["GET"])
    def api_user_imports_dna_presets_list():
        return jsonify({"presets": list_saved_presets()})

    @app.route("/api/user-imports/dna-presets", methods=["POST"])
    def api_user_imports_dna_presets_save():
        try:
            data = request.get_json(force=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            label = (data.get("label") or "").strip() or None
            recipe = data.get("recipe")
            session_id = (data.get("session_id") or "").strip()
            index = data.get("index")
            if recipe is None and session_id and index is not None:
                import json
                from pathlib import Path

                from engine.paint_v2.user_imports_shokk_world import _session_path

                sp = _session_path(session_id)
                meta_path = sp / "meta.json"
                if not meta_path.exists():
                    return jsonify({"error": "Session not found"}), 404
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                idx = int(index)
                plan = meta["plans"][idx]
                vpath = sp / "variants" / f"{idx:02d}.json"
                if vpath.exists():
                    vmeta = json.loads(vpath.read_text(encoding="utf-8"))
                    recipe = vmeta.get("dna_recipe") or recipe_from_plan(plan)
                else:
                    recipe = recipe_from_plan(plan)
            if not recipe:
                return jsonify({"error": "recipe or session_id+index required"}), 400
            row = save_preset(
                recipe,
                label=label,
                source=data.get("source") or "shokk_world",
            )
            return jsonify({"success": True, "preset": row})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[dna-presets] save error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/dna-presets/<preset_id>", methods=["DELETE"])
    def api_user_imports_dna_presets_delete(preset_id):
        if delete_preset(preset_id):
            return jsonify({"success": True})
        return jsonify({"error": "Preset not found"}), 404

    def _parse_spec_channel_strengths():
        def _one(key):
            raw = request.form.get(key)
            if raw is None or raw == "":
                return None
            try:
                return float(raw)
            except ValueError:
                return None

        return _one("spec_m"), _one("spec_r"), _one("spec_c")

    @app.route("/api/user-imports/import", methods=["POST"])
    def api_user_imports_import():
        kind = (request.form.get("kind") or "paint_monolithic").strip().lower()
        logger.info(f"[user-imports] import requested kind={kind}")
        try:
            display_name = (request.form.get("name") or "").strip()
            spec_channel = (request.form.get("spec_channel") or "M").strip().upper()
            vibe_ref = (request.form.get("vibe_ref") or "").strip() or None
            style_override = (request.form.get("style_override") or "").strip() or None
            also_pattern = (request.form.get("also_pattern") or "").lower() in ("1", "true", "yes")
            # [SPB FRACTURE auto-derive 2026-06-16] When the user drops ONLY a paint (no spec
            # channels) and chooses "FRACTURE the spec", spec_mode -> "fractured" (the paint's own
            # geometry is ignited at render) instead of the default auto-DNA bake.
            fracture = (request.form.get("fracture") or "").lower() in ("1", "true", "yes")
            uploads = request.files.getlist("files") or request.files.getlist("file")
            if not uploads:
                single = request.files.get("paint") or request.files.get("paint_file")
                if single:
                    uploads = [single]
            if not uploads:
                return jsonify({"error": "No files uploaded"}), 400

            temp_dir = tempfile.mkdtemp(prefix="spb_ui_import_")
            saved = []
            try:
                for f in uploads:
                    if not f or not f.filename:
                        continue
                    safe = secure_filename(f.filename) or "upload.png"
                    path = Path(temp_dir) / safe
                    f.save(str(path))
                    saved.append((safe, path))
                if not saved:
                    return jsonify({"error": "No valid files in upload"}), 400
                if kind in ("paint_spec_set", "paint_spec", "spec_set", "paint-spec-set"):
                    spec_m, spec_r, spec_c = _parse_spec_channel_strengths()
                    set_kind = (request.form.get("set_kind") or "paint").strip().lower()
                    if set_kind in ("spec-overlay", "spec"):
                        set_kind = "spec_overlay"
                    _has_spec = any(
                        any(t in n.lower() for t in (
                            "spec", "metallic", "metal", "rough", "clear", "coat", "channel_"))
                        for n, _ in saved
                    )
                    if not _has_spec and set_kind != "spec_overlay":
                        # "None" spec mode — the broadened spec row was shown but no custom
                        # maps were attached. Import the standard way (auto-DNA paint, or a
                        # plain pattern) so Paint/Pattern work without requiring a spec.
                        if set_kind == "pattern":
                            entry = import_pattern_files(saved, display_name=display_name or None)
                        else:
                            entry = import_paint_files(
                                saved,
                                display_name=display_name or None,
                                vibe_ref=vibe_ref,
                                also_pattern=also_pattern,
                                style_override=style_override,
                                fracture=fracture,
                            )
                    else:
                        entry = import_paint_with_spec_files(
                            saved,
                            display_name=display_name or None,
                            kind=set_kind,
                            also_pattern=also_pattern,
                            spec_m=spec_m,
                            spec_r=spec_r,
                            spec_c=spec_c,
                        )
                elif kind == "pattern":
                    entry = import_pattern_files(saved, display_name=display_name or None)
                elif kind in ("spec_overlay", "spec", "spec-overlay"):
                    spec_m, spec_r, spec_c = _parse_spec_channel_strengths()
                    entry = import_spec_overlay_files(
                        saved,
                        display_name=display_name or None,
                        spec_channel=spec_channel,
                        spec_m=spec_m,
                        spec_r=spec_r,
                        spec_c=spec_c,
                    )
                else:
                    entry = import_paint_files(
                        saved,
                        display_name=display_name or None,
                        vibe_ref=vibe_ref,
                        also_pattern=also_pattern,
                        style_override=style_override,
                        fracture=fracture,
                    )
            finally:
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as _spb_ex:
                    _spb_swallow('api_user_imports_import@L318', _spb_ex)

            count = _sync_engine()
            logger.info(f"[user-imports] imported {entry.get('id')} kind={entry.get('kind')} ({count} active)")
            return jsonify({"success": True, "entry": entry, "count": count})
        except Exception as e:
            logger.error(f"[user-imports] import error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/preview", methods=["POST"])
    def api_user_imports_preview():
        """Analyze import without saving — paint DNA or spec overlay plate."""
        try:
            kind = (request.form.get("kind") or "paint_monolithic").strip().lower()
            vibe_ref = (request.form.get("vibe_ref") or "").strip() or None
            style_override = (request.form.get("style_override") or "").strip() or None
            display_name = (request.form.get("name") or "").strip()
            uploads = request.files.getlist("files") or request.files.getlist("file")
            if not uploads:
                return jsonify({"error": "No files uploaded"}), 400
            temp_dir = tempfile.mkdtemp(prefix="spb_ui_preview_")
            saved = []
            try:
                for f in uploads:
                    if not f or not f.filename:
                        continue
                    safe = secure_filename(f.filename) or "upload.png"
                    path = Path(temp_dir) / safe
                    f.save(str(path))
                    saved.append((safe, path))
                if kind in ("paint_spec_set", "paint_spec", "spec_set", "paint-spec-set"):
                    spec_m, spec_r, spec_c = _parse_spec_channel_strengths()
                    set_kind = (request.form.get("set_kind") or "paint").strip().lower()
                    if set_kind in ("spec-overlay", "spec"):
                        set_kind = "spec_overlay"
                    _has_spec = any(
                        any(t in n.lower() for t in (
                            "spec", "metallic", "metal", "rough", "clear", "coat", "channel_"))
                        for n, _ in saved
                    )
                    if not _has_spec and set_kind != "spec_overlay":
                        # [SPB FRACTURE auto-derive 2026-06-16] No spec attached. If the user chose
                        # "FRACTURE the spec", preview the FRACTURE ignition (matches what import
                        # saves); otherwise preview the standard auto-DNA paint result.
                        fracture = (request.form.get("fracture") or "").lower() in ("1", "true", "yes")
                        if fracture:
                            payload = preview_fracture_import(saved, display_name=display_name or None)
                        else:
                            payload = preview_import(
                                saved,
                                display_name=display_name or None,
                                vibe_ref=vibe_ref,
                                style_override=style_override,
                            )
                    else:
                        payload = preview_paint_with_spec_files(
                            saved,
                            display_name=display_name or None,
                            kind=set_kind,
                            spec_m=spec_m,
                            spec_r=spec_r,
                            spec_c=spec_c,
                        )
                elif kind in ("spec_overlay", "spec", "spec-overlay"):
                    spec_m, spec_r, spec_c = _parse_spec_channel_strengths()
                    payload = preview_spec_overlay_import(
                        saved,
                        display_name=display_name or None,
                        spec_m=spec_m,
                        spec_r=spec_r,
                        spec_c=spec_c,
                    )
                else:
                    payload = preview_import(
                        saved,
                        display_name=display_name or None,
                        vibe_ref=vibe_ref,
                        style_override=style_override,
                    )
            finally:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({"success": True, **payload})
        except Exception as e:
            logger.error(f"[user-imports] preview error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/process-inbox", methods=["POST"])
    def api_user_imports_process_inbox():
        try:
            data = request.get_json(force=True, silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            also_pattern = bool(data.get("also_pattern"))
            imported = process_inbox(also_pattern=also_pattern)
            count = _sync_engine()
            return jsonify({"success": True, "imported": imported, "count": count})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/delete", methods=["POST"])
    def api_user_imports_delete():
        try:
            data = request.get_json(force=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            finish_id = (data.get("id") or "").strip()
            if not finish_id:
                return jsonify({"error": "id required"}), 400
            if not delete_entry(finish_id):
                return jsonify({"error": f"Not found: {finish_id}"}), 404
            count = _sync_engine()
            return jsonify({"success": True, "deleted": finish_id, "count": count})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/rebake-dna", methods=["POST"])
    def api_user_imports_rebake_dna():
        """Re-run Import DNA gauntlet on an existing auto-spec paint import."""
        try:
            data = request.get_json(force=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            finish_id = (data.get("id") or "").strip()
            if not finish_id:
                return jsonify({"error": "id required"}), 400
            vibe_ref = (data.get("vibe_ref") or "").strip() or None
            style_override = (data.get("style_override") or "").strip() or None
            entry = rebake_dna_spec(finish_id, vibe_ref=vibe_ref, style_override=style_override)
            count = _sync_engine()
            return jsonify({"success": True, "entry": entry, "count": count})
        except FileNotFoundError:
            return jsonify({"error": "Finish not found"}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[user-imports] rebake-dna error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/fork", methods=["POST"])
    def api_user_imports_fork():
        """Fork a paint drop into a NEW entry with a fresh DNA bake.

        Added 2026-08-09 (SHOKK DROP loop): /rebake-dna OVERWRITES the spec in
        place, so trying a different DNA style meant destroying the version you
        already liked. This re-runs the ordinary import path on the drop's own
        stored paint plate, which mints a new id and leaves the original
        untouched. No new bake logic — same import_paint_files() everything else
        uses, so a fork is indistinguishable from a fresh import.
        """
        try:
            data = request.get_json(force=True, silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            finish_id = (data.get("id") or "").strip()
            if not finish_id:
                return jsonify({"error": "id required"}), 400
            style_override = (data.get("style_override") or "").strip() or None
            vibe_ref = (data.get("vibe_ref") or "").strip() or None
            fracture = str(data.get("fracture") or "").lower() in ("1", "true", "yes")
            display_name = (data.get("name") or "").strip() or None

            entry = next((e for e in get_catalog_entries() if e.get("id") == finish_id), None)
            if entry is None:
                return jsonify({"error": f"Not found: {finish_id}"}), 404
            if (entry.get("kind") or "paint_monolithic") != "paint_monolithic":
                return jsonify({"error": "Only paint drops can be forked"}), 400

            paint_path = user_imports_root() / f"{finish_id}.png"
            if not paint_path.exists():
                return jsonify({"error": "Paint plate missing on disk"}), 404
            if not display_name:
                display_name = f"{entry.get('name') or finish_id} (fork)"

            new_entry = import_paint_files(
                [(paint_path.name, paint_path)],
                display_name=display_name,
                vibe_ref=vibe_ref,
                also_pattern=False,
                style_override=style_override,
                fracture=fracture,
            )
            count = _sync_engine()
            logger.info(f"[user-imports] forked {finish_id} -> {new_entry.get('id')} ({count} active)")
            return jsonify({"success": True, "entry": new_entry, "source_id": finish_id, "count": count})
        except FileNotFoundError:
            return jsonify({"error": "Finish not found"}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[user-imports] fork error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/update-spec-channels", methods=["POST"])
    def api_user_imports_update_spec_channels():
        """Update M/R/CC multipliers on an existing spec overlay drop."""
        try:
            data = request.get_json(force=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            finish_id = (data.get("id") or "").strip()
            if not finish_id:
                return jsonify({"error": "id required"}), 400

            def _opt(key):
                if key not in data or data[key] is None or data[key] == "":
                    return None
                return float(data[key])

            entry = update_spec_overlay_channels(
                finish_id,
                spec_m=_opt("spec_m"),
                spec_r=_opt("spec_r"),
                spec_c=_opt("spec_c"),
            )
            count = _sync_engine()
            return jsonify({"success": True, "entry": entry, "count": count})
        except FileNotFoundError:
            return jsonify({"error": "Finish not found"}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[user-imports] update-spec-channels error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/reload", methods=["POST"])
    def api_user_imports_reload():
        try:
            count = _sync_engine()
            return jsonify({"success": True, "count": count, "entries": get_catalog_entries()})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/engine-preview/<finish_id>", methods=["GET"])
    def api_user_imports_engine_preview(finish_id):
        """build_multi_zone UV preview @ 512² (on-demand, slower than silhouette clip)."""
        try:
            try:
                size = int(request.args.get("size", 512))
            except (TypeError, ValueError):
                return jsonify({"error": "size must be an integer"}), 400
            data = render_engine_uv_bytes(finish_id, size=size, engine=engine_getter())
            return Response(data, mimetype="image/png", headers={"Cache-Control": "public, max-age=300"})
        except FileNotFoundError:
            return jsonify({"error": "Finish not found"}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[user-imports] engine-preview error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/preview-image/<finish_id>", methods=["GET"])
    def api_user_imports_preview_image(finish_id):
        try:
            path = resolve_preview_image(finish_id)
            return send_file(str(path), mimetype="image/png", max_age=3600)
        except FileNotFoundError:
            return jsonify({"error": "Preview not found"}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/paint-image/<finish_id>", methods=["GET"])
    def api_user_imports_paint_image(finish_id):
        try:
            path = resolve_paint_image(finish_id)
            return send_file(str(path), mimetype="image/png", max_age=3600)
        except FileNotFoundError:
            return jsonify({"error": "Paint not found"}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/user-imports/spec-image/<finish_id>", methods=["GET"])
    def api_user_imports_spec_image(finish_id):
        try:
            path = resolve_spec_image(finish_id)
            return send_file(str(path), mimetype="image/png", max_age=3600)
        except FileNotFoundError:
            return jsonify({"error": "Spec not found"}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/user-imports/channel-preview/<finish_id>/<channel>", methods=["GET"])
    def api_user_imports_channel_preview(finish_id, channel):
        try:
            try:
                width = int(request.args.get("width", 640))
            except (TypeError, ValueError):
                return jsonify({"error": "width must be an integer"}), 400
            data = render_channel_preview_png(finish_id, channel, width=width)
            return Response(data, mimetype="image/png", headers={"Cache-Control": "public, max-age=300"})
        except FileNotFoundError:
            return jsonify({"error": "Finish not found"}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[user-imports] channel-preview error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/spec-overlay-image/<finish_id>", methods=["GET"])
    def api_user_imports_spec_overlay_image(finish_id):
        try:
            path = resolve_spec_overlay_image(finish_id)
            return send_file(str(path), mimetype="image/png", max_age=3600)
        except FileNotFoundError:
            return jsonify({"error": "Spec overlay not found"}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/user-imports/spec-overlay-preview/<finish_id>", methods=["GET"])
    def api_user_imports_spec_overlay_preview(finish_id):
        try:
            from io import BytesIO

            spec = Image.open(resolve_spec_overlay_image(finish_id))
            buf = BytesIO()
            spec_to_rgb_preview(spec).save(buf, format="PNG", optimize=True)
            return Response(buf.getvalue(), mimetype="image/png", headers={"Cache-Control": "public, max-age=300"})
        except FileNotFoundError:
            return jsonify({"error": "Spec overlay not found"}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[user-imports] spec-overlay-preview error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/spec-overlay-channel/<finish_id>/<channel>", methods=["GET"])
    def api_user_imports_spec_overlay_channel(finish_id, channel):
        try:
            try:
                width = int(request.args.get("width", 640))
            except (TypeError, ValueError):
                return jsonify({"error": "width must be an integer"}), 400
            data = render_spec_overlay_channel_preview_png(finish_id, channel, width=width)
            return Response(data, mimetype="image/png", headers={"Cache-Control": "public, max-age=300"})
        except FileNotFoundError:
            return jsonify({"error": "Finish not found"}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[user-imports] spec-overlay-channel error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/preview-detail/<finish_id>", methods=["GET"])
    def api_user_imports_preview_detail(finish_id):
        """URL bundle for saved drop — full channel preview grid in Shokk Drop Lab."""
        try:
            entry = next((e for e in get_catalog_entries() if e.get("id") == finish_id), None)
            if not entry:
                return jsonify({"error": "Finish not found"}), 404
            kind = entry.get("kind") or "paint_monolithic"
            if kind not in (None, "paint_monolithic", "spec_overlay"):
                return jsonify({"error": "Preview detail only for paint or spec overlay drops"}), 400
            payload = build_saved_preview_urls(finish_id, kind=kind)
            dna = entry.get("import_dna") or {}
            return jsonify({
                "success": True,
                "id": finish_id,
                "name": entry.get("name") or finish_id,
                "kind": kind,
                "spec_channel_strengths": entry.get("spec_channel_strengths"),
                "dna": dna,
                **payload,
            })
        except FileNotFoundError:
            return jsonify({"error": "Assets not found"}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[user-imports] preview-detail error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/export-all", methods=["GET"])
    def api_user_imports_export_all():
        try:
            root = user_imports_root()
            root.mkdir(parents=True, exist_ok=True)
            out = root / "packs" / f"shokk_drop_batch{DROP_PACK_EXT}"
            export_all_packs(out)
            return send_file(str(out), as_attachment=True, download_name=out.name)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[user-imports] export-all error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/health", methods=["GET"])
    def api_user_imports_health():
        """Report manifest entries the loader can't build ("ghost" drops).

        Added 2026-08-09 (SHOKK DROP loop) after finding a real one: `ui_mag01_2`
        sat in the manifest with only its paint plate (no `_spec.png`), so the
        loader skipped it — invisible in the UI, therefore impossible to delete,
        yet still exported by "Export all .spbdrop" as a spec-less pack that
        would import broken on someone else's machine.

        The live catalog is the AUTHORITY here (we diff against it rather than
        re-implementing the loader's per-kind file rules, which would drift).
        Read-only; cleanup is the owner's explicit action via /delete.
        """
        try:
            root = user_imports_root()
            man_path = root / "manifest.json"
            manifest = {}
            if man_path.exists():
                import json as _json
                manifest = _json.loads(man_path.read_text(encoding="utf-8")) or {}
            man_entries = manifest.get("entries", []) or []
            active_ids = {e.get("id") for e in get_catalog_entries()}
            ghosts = []
            for entry in man_entries:
                fid = entry.get("id")
                if not fid or fid in active_ids:
                    continue
                kind = entry.get("kind", "paint_monolithic")
                spec_mode = entry.get("spec_mode", "auto")
                # Which of the files this kind needs are actually absent —
                # diagnostics only; the skip verdict already came from the loader.
                if kind == "pattern":
                    expected = [f"{fid}_pattern.png"]
                elif kind == "spec_overlay":
                    expected = [f"{fid}_spec_overlay.png", f"{fid}_spec.png"]
                elif spec_mode == "metallic_roughness":
                    expected = [f"{fid}.png", f"{fid}_metallic.png", f"{fid}_roughness.png"]
                else:
                    expected = [f"{fid}.png", f"{fid}_spec.png"]
                missing = [n for n in expected if not (root / n).exists()]
                ghosts.append({
                    "id": fid,
                    "name": entry.get("name") or fid,
                    "kind": kind,
                    "spec_mode": spec_mode,
                    "imported": entry.get("imported"),
                    "missing_files": missing,
                })
            return jsonify({
                "manifest_count": len(man_entries),
                "active_count": len(active_ids),
                "ghost_count": len(ghosts),
                "ghosts": ghosts,
            })
        except Exception as e:
            logger.error(f"[user-imports] health error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/export-selected", methods=["POST"])
    def api_user_imports_export_selected():
        """Bulk-export a chosen subset as ONE .spbdrop bundle.

        Added 2026-08-09 (SHOKK DROP loop): the gallery could export one drop
        or the entire library and nothing in between, which made sharing "these
        four" a four-download chore. Purely additive — export_all_packs(ids=None)
        keeps the whole-library behaviour untouched.
        """
        try:
            data = request.get_json(force=True, silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            ids = data.get("ids")
            if not isinstance(ids, list) or not ids:
                return jsonify({"error": "ids must be a non-empty list"}), 400
            ids = [str(i).strip() for i in ids if str(i).strip()]
            if not ids:
                return jsonify({"error": "ids must contain at least one id"}), 400
            root = user_imports_root()
            root.mkdir(parents=True, exist_ok=True)
            stamp = str(int(time.time()))
            out = root / "packs" / f"shokk_drop_selection_{len(ids)}_{stamp}{DROP_PACK_EXT}"
            export_all_packs(out, ids=ids)
            return send_file(str(out), as_attachment=True, download_name=out.name)
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[user-imports] export-selected error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/export/<finish_id>", methods=["GET"])
    def api_user_imports_export(finish_id):
        try:
            root = user_imports_root()
            root.mkdir(parents=True, exist_ok=True)
            out = root / "packs" / f"{finish_id}{DROP_PACK_EXT}"
            export_entry_zip(finish_id, out)
            return send_file(str(out), as_attachment=True, download_name=out.name)
        except FileNotFoundError:
            return jsonify({"error": "Finish not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/shokk-the-world/start", methods=["POST"])
    def api_shokk_the_world_start():
        """SPB-109: Begin 20-variant explosion session (2048² paint normalized)."""
        try:
            uploads = request.files.getlist("files") or request.files.getlist("file")
            if not uploads:
                single = request.files.get("paint") or request.files.get("paint_file")
                if single:
                    uploads = [single]
            if not uploads:
                return jsonify({"error": "No image uploaded"}), 400
            f = uploads[0]
            temp_dir = tempfile.mkdtemp(prefix="spb_stw_")
            try:
                safe = secure_filename(f.filename) or "upload.png"
                path = Path(temp_dir) / safe
                f.save(str(path))
                raw = Image.open(path)
                display_name = (request.form.get("name") or Path(safe).stem).strip() or Path(safe).stem
                vibe_ref = (request.form.get("vibe_ref") or "").strip() or None
                remix_a = (request.form.get("remix_style_a") or "").strip() or None
                remix_b = (request.form.get("remix_style_b") or "").strip() or None
                try:
                    remix_t = float(request.form.get("remix_t") or "0.5")
                except ValueError:
                    remix_t = 0.5
                try:
                    chroma_scale = float(request.form.get("chroma_scale") or "1.0")
                except ValueError:
                    chroma_scale = 1.0
                palette_overrides = None
                raw_overrides = (request.form.get("palette_overrides") or "").strip()
                if raw_overrides:
                    import json as _json

                    try:
                        parsed = _json.loads(raw_overrides)
                        if isinstance(parsed, dict):
                            palette_overrides = {
                                str(kk): [str(x) for x in vv]
                                for kk, vv in parsed.items()
                                if isinstance(vv, list) and vv
                            }
                    except Exception:
                        palette_overrides = None
                payload = start_shokk_world_session(
                    raw,
                    display_name,
                    vibe_ref=vibe_ref,
                    remix_style_a=remix_a,
                    remix_style_b=remix_b,
                    remix_t=remix_t,
                    chroma_scale=chroma_scale,
                    palette_overrides=palette_overrides,
                )
            finally:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({"success": True, **payload})
        except Exception as e:
            logger.error(f"[shokk-the-world] start error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/shokk-the-world/<session_id>/variant/<int:index>", methods=["GET"])
    def api_shokk_the_world_variant(session_id, index):
        """Generate (or return cached) variant preview — one at a time for UI reveal."""
        try:
            if index < 0 or index >= WORLD_VARIANT_COUNT:
                return jsonify({"error": "index out of range"}), 400
            payload = generate_world_variant(session_id, index)
            return jsonify({"success": True, **payload})
        except FileNotFoundError:
            return jsonify({"error": "Session not found"}), 404
        except Exception as e:
            logger.error(f"[shokk-the-world] variant error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/shokk-the-world/reroll", methods=["POST"])
    def api_shokk_the_world_reroll():
        """SPB-109: rebake a single slot with a fresh seed (new take, same identity)."""
        try:
            data = request.get_json(force=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            session_id = (data.get("session_id") or "").strip()
            index = int(data.get("index"))
            if not session_id or index < 0 or index >= WORLD_VARIANT_COUNT:
                return jsonify({"error": "Bad session/index"}), 400
            payload = reroll_world_variant(session_id, index)
            return jsonify({"success": True, **payload})
        except FileNotFoundError:
            return jsonify({"error": "Session not found"}), 404
        except Exception as e:
            logger.error(f"[shokk-the-world] reroll error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/shokk-the-world/commit", methods=["POST"])
    def api_shokk_the_world_commit():
        """Save selected variant indices as permanent SHOKK DROP library entries."""
        try:
            data = request.get_json(force=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            session_id = (data.get("session_id") or "").strip()
            indices = data.get("indices") or []
            if not session_id:
                return jsonify({"error": "session_id required"}), 400
            if not indices:
                return jsonify({"error": "indices required"}), 400
            name_prefix = (data.get("name_prefix") or "").strip() or None
            imported = commit_world_variants(session_id, indices, name_prefix=name_prefix)
            purge_staging_for_session(session_id)
            count = _sync_engine()
            return jsonify({"success": True, "imported": imported, "count": count})
        except FileNotFoundError:
            return jsonify({"error": "Session not found"}), 404
        except Exception as e:
            logger.error(f"[shokk-the-world] commit error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/shokk-the-world/stage", methods=["POST"])
    def api_shokk_the_world_stage():
        """Stage variant for Paint Booth / Live Link try-before-save."""
        try:
            data = request.get_json(force=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            session_id = (data.get("session_id") or "").strip()
            index = int(data.get("index", -1))
            if not session_id or index < 0:
                return jsonify({"error": "session_id and index required"}), 400
            use_paint = data.get("use_paint_source", True)
            if isinstance(use_paint, str):
                use_paint = use_paint.lower() not in ("0", "false", "no")
            entry = stage_variant_for_booth(
                session_id, index, use_paint_source=bool(use_paint)
            )
            count = _sync_engine()
            return jsonify({"success": True, "entry": entry, "count": count})
        except FileNotFoundError:
            return jsonify({"error": "Session not found"}), 404
        except Exception as e:
            logger.error(f"[shokk-the-world] stage error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/dna-remix-preview", methods=["POST"])
    def api_dna_remix_preview():
        """Live remix preview for DNA slider (requires active shokk-world session)."""
        try:
            data = request.get_json(force=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            session_id = (data.get("session_id") or "").strip()
            style_a = (data.get("style_a") or "").strip()
            style_b = (data.get("style_b") or "").strip()
            try:
                remix_t = float(data.get("remix_t", 0.5))
            except (TypeError, ValueError):
                remix_t = 0.5
            if not session_id:
                return jsonify({"error": "session_id required"}), 400
            if style_a not in DNA_STYLES or style_b not in DNA_STYLES:
                return jsonify({"error": "Invalid DNA styles"}), 400
            payload = preview_dna_remix(session_id, style_a, style_b, remix_t)
            return jsonify({"success": True, **payload})
        except FileNotFoundError:
            return jsonify({"error": "Session not found — start SHOKK THE WORLD first"}), 404
        except Exception as e:
            logger.error(f"[dna-remix] preview error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/import-pack", methods=["POST"])
    def api_user_imports_import_pack():
        try:
            f = request.files.get("pack") or request.files.get("file")
            if not f or not f.filename:
                return jsonify({"error": "No pack file"}), 400
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=DROP_PACK_EXT)
            try:
                f.save(temp.name)
                temp.close()
                if not zipfile.is_zipfile(temp.name):
                    return jsonify({"error": f"Invalid {DROP_PACK_EXT} (zip) file"}), 400
                imported = import_pack_zip(Path(temp.name))
            finally:
                try:
                    os.unlink(temp.name)
                except Exception as _spb_ex:
                    _spb_swallow('api_user_imports_import_pack@L998', _spb_ex)
            count = _sync_engine()
            return jsonify({"success": True, "imported": imported, "count": count})
        except Exception as e:
            logger.error(f"[user-imports] pack import error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/user-imports/community-drop/<drop_id>", methods=["GET"])
    def api_user_imports_community_drop(drop_id):
        """Return owner-approved metadata through SPB's trusted local server."""
        try:
            return jsonify(_community_metadata(drop_id))
        except (ValueError, json.JSONDecodeError, urllib.error.URLError, urllib.error.HTTPError) as e:
            logger.warning(f"[community-drops] metadata rejected id={drop_id}: {e}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[community-drops] metadata error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": "Could not verify this SHOKK DROP"}), 502

    @app.route("/api/user-imports/install-community-drop", methods=["POST"])
    def api_user_imports_install_community_drop():
        """Download, verify again, and install an approved community drop."""
        temp_name = None
        try:
            payload = request.get_json(silent=True) or {}
            drop_id = str(payload.get("id") or "")
            version = payload.get("version", 1)
            if version != 1:
                return jsonify({"error": "Unsupported SHOKK DROP version"}), 400
            metadata = _community_metadata(drop_id)
            package = metadata["package"]
            hasher = hashlib.sha256()
            received = 0
            with tempfile.NamedTemporaryFile(delete=False, suffix=DROP_PACK_EXT) as temp:
                temp_name = temp.name
                with _community_open(package["absolute_url"]) as response:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        received += len(chunk)
                        if received > 32 * 1024 * 1024:
                            raise ValueError("Community SHOKK DROP exceeded the download limit")
                        hasher.update(chunk)
                        temp.write(chunk)
            if received != package["bytes"] or hasher.hexdigest() != package["sha256"]:
                raise ValueError("Community SHOKK DROP failed its size or SHA-256 check")
            local_check = validate_community_drop_pack(Path(temp_name))
            imported = import_pack_zip(Path(temp_name), community_source={
                "id": metadata["id"],
                "version": metadata["version"],
                "sha256": package["sha256"],
                "finish_name": metadata.get("finish_name"),
                "author_name": metadata.get("author_name"),
                "website": metadata.get("author_website"),
            })
            count = _sync_engine()
            return jsonify({
                "success": True,
                "imported": imported,
                "count": count,
                "verification": {
                    "sha256": package["sha256"],
                    "members": local_check["members"],
                    "verified_images": len(local_check["verified_images"]),
                },
            })
        except (ValueError, json.JSONDecodeError, urllib.error.URLError, urllib.error.HTTPError) as e:
            logger.warning(f"[community-drops] install rejected: {e}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"[community-drops] install error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": "SHOKK DROP installation failed"}), 502
        finally:
            if temp_name:
                try:
                    os.unlink(temp_name)
                except Exception as _spb_ex:
                    _spb_swallow('api_user_imports_install_community_drop@cleanup', _spb_ex)
