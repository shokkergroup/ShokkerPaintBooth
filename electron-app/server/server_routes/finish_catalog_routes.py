"""Finish catalogue/status routes for Shokker Paint Booth."""

import traceback

from flask import jsonify, request
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def id_to_display_name(finish_id):
    """Convert snake_case finish ID to Title Case display name."""
    return finish_id.replace('_', ' ').title()


def register_finish_catalog_routes(app, *, engine_getter, cache_headers, logger):
    """Register finish catalogue endpoints and return cache helper functions."""

    finish_data_cache = {"payload": None}

    def build_finish_data_payload():
        """Build the full finish catalogue from live Python registries."""
        engine = engine_getter()
        import shokker_24k_expansion as _exp24k

        groups = _exp24k.get_expansion_group_map()

        try:
            import shokker_paradigm_expansion as _paradigm
            for key in ("bases", "patterns", "specials"):
                paradigm_g = _paradigm.get_paradigm_group_map().get(key, {})
                groups.setdefault(key, {}).update(paradigm_g)
        except Exception as _spb_ex:
            _spb_swallow('build_finish_data_payload@L30', _spb_ex)

        try:
            try:
                import shokker_fusions_expansion as _fusions
            except ImportError:
                from engine.expansions import fusions as _fusions
            fusion_g = _fusions.get_fusion_group_map().get("fusions", {})
            groups.setdefault("specials", {}).update(fusion_g)
        except Exception as _spb_ex:
            _spb_swallow('build_finish_data_payload@L40', _spb_ex)

        # IMAGE FORGE (2026-06-11): NEW owner-art ids dropped in a category
        # subfolder join that picker group; the UI registry sync then surfaces
        # them in the matching Zone Popout lane automatically.
        try:
            from engine.expansions.image_forge_2026 import get_forge_group_map
            _sp = groups.setdefault("specials", {})
            for _gname, _ids in get_forge_group_map().items():
                _cur = list(_sp.get(_gname, []))
                _cur.extend(i for i in _ids if i not in _cur)
                _sp[_gname] = _cur
        except Exception as _spb_ex:
            _spb_swallow('build_finish_data_payload@L53', _spb_ex)

        def add_monolithic_prefix_group(group_name, prefix):
            ids = [
                fid for fid in engine.MONOLITHIC_REGISTRY.keys()
                if str(fid).startswith(prefix)
            ]
            if not ids:
                return
            specials = groups.setdefault("specials", {})
            existing = list(specials.get(group_name, []))
            seen = set(existing)
            existing.extend(fid for fid in ids if fid not in seen)
            specials[group_name] = existing

        add_monolithic_prefix_group("RISING SUN", "rs_")
        add_monolithic_prefix_group("VIVA MEXICO", "vm_")

        ui_name_by_id = {}
        try:
            from engine.paint_v2.user_imports import get_catalog_entries
            from engine.paint_v2.user_imports_paths import CATEGORY_NAME

            ui_entries = get_catalog_entries()
            ui_ids = [
                e["id"] for e in ui_entries
                if e.get("kind", "paint_monolithic") == "paint_monolithic"
            ]
            ui_pattern_ids = [e["id"] for e in ui_entries if e.get("kind") == "pattern"]
            ui_name_by_id = {
                e["id"]: (e.get("name") or id_to_display_name(e["id"]))
                for e in ui_entries
                if e.get("kind", "paint_monolithic") == "paint_monolithic"
            }
            if ui_ids:
                specials = groups.setdefault("specials", {})
                specials[CATEGORY_NAME] = ui_ids
            if ui_pattern_ids:
                patterns = groups.setdefault("patterns", {})
                patterns[CATEGORY_NAME] = ui_pattern_ids
        except Exception as _spb_ex:
            _spb_swallow('build_finish_data_payload@L94', _spb_ex)

        try:
            from engine.paint_v2.guest_designers import get_catalog_for_picker

            for entry in get_catalog_for_picker():
                fid = entry.get("id")
                if not fid:
                    continue
                ui_name_by_id[fid] = entry.get("name") or id_to_display_name(fid)
                group = entry.get("group") or "Guest Designer"
                specials = groups.setdefault("specials", {})
                specials.setdefault(group, [])
                if fid not in specials[group]:
                    specials[group].append(fid)
        except Exception as _spb_ex:
            _spb_swallow('build_finish_data_payload@L110', _spb_ex)

        from engine.paint_v2.core_works_2026.collection import apply_groups as _core_groups
        core_metadata = _core_groups(groups)
        id_to_cat = {"bases": {}, "patterns": {}, "specials": {}}
        for reg_key in ("bases", "patterns", "specials"):
            for cat_name, id_list in groups.get(reg_key, {}).items():
                for fid in id_list:
                    id_to_cat[reg_key][fid] = cat_name

        def make_entries(registry_keys, reg_type, default_swatch, swatch_type):
            out = []
            seen = set()
            for fid in registry_keys:
                if fid in seen:
                    continue
                seen.add(fid)
                entry = {
                    "id": fid,
                    "name": ui_name_by_id.get(fid, id_to_display_name(fid)),
                    "category": id_to_cat[reg_type].get(fid, "Other"),
                    "swatch": default_swatch,
                    "type": swatch_type,
                }
                if reg_type == "bases" and fid in core_metadata:
                    entry.update(core_metadata[fid])
                out.append(entry)
            out.sort(key=lambda x: (x["category"], x["name"]))
            return out

        bases = make_entries(engine.BASE_REGISTRY.keys(), "bases", "#888888", "base")
        patterns = make_entries(engine.PATTERN_REGISTRY.keys(), "patterns", "#555577", "pattern")
        specials = make_entries(engine.MONOLITHIC_REGISTRY.keys(), "specials", "#446688", "monolithic")

        total = len(bases) + len(patterns) + len(specials)
        return {
            "bases": bases,
            "patterns": patterns,
            "specials": specials,
            "groups": groups,
            "counts": {
                "bases": len(bases),
                "patterns": len(patterns),
                "specials": len(specials),
                "total": total,
            },
        }

    def clear_finish_data_cache():
        had_cache = finish_data_cache["payload"] is not None
        finish_data_cache["payload"] = None
        return had_cache

    def prewarm_finish_data_cache():
        finish_data_cache["payload"] = build_finish_data_payload()
        return finish_data_cache["payload"]

    @app.route('/finish-groups', methods=['GET'])
    def finish_groups():
        """Return group metadata for UI organization of 24K Arsenal finishes."""
        logger.info("[finish-groups] Requested")
        try:
            engine = engine_getter()
            import shokker_24k_expansion as _exp24k
            groups = _exp24k.get_expansion_group_map()
            counts = _exp24k.get_expansion_counts()
            try:
                import shokker_paradigm_expansion as _paradigm
                paradigm_groups = _paradigm.get_paradigm_group_map()
                for key in ("bases", "patterns", "specials"):
                    if key in paradigm_groups:
                        groups.setdefault(key, {}).update(paradigm_groups[key])
            except Exception as _spb_ex:
                _spb_swallow('finish_groups@L178', _spb_ex)
            try:
                try:
                    import shokker_fusions_expansion as _fusions
                except ImportError:
                    from engine.expansions import fusions as _fusions
                fusion_groups = _fusions.get_fusion_group_map()
                if "fusions" in fusion_groups:
                    groups.setdefault("specials", {}).update(fusion_groups["fusions"])
            except Exception as _spb_ex:
                _spb_swallow('finish_groups@L188', _spb_ex)
            from engine.paint_v2.core_works_2026.collection import apply_groups as _core_groups
            _core_groups(groups)
            return jsonify({
                "status": "ok",
                "groups": groups,
                "expansion_counts": counts,
                "total_bases": len(engine.BASE_REGISTRY),
                "total_patterns": len(engine.PATTERN_REGISTRY),
                "total_specials": len(engine.MONOLITHIC_REGISTRY),
                "total_fusions": len(getattr(engine, 'FUSION_REGISTRY', {})),
                "total_combinations": len(engine.BASE_REGISTRY) * len(engine.PATTERN_REGISTRY) + len(engine.MONOLITHIC_REGISTRY),
            })
        except ImportError:
            return jsonify({
                "status": "ok",
                "groups": {"bases": {}, "patterns": {}, "specials": {}},
                "expansion_counts": {"bases": 0, "patterns": 0, "specials": 0, "total": 0},
            })

    @app.route('/api/finish-registry-status', methods=['GET'])
    def api_finish_registry_status():
        """Return which finish IDs are registered in the engine vs. unregistered."""
        try:
            from shokker_engine_v2 import MONOLITHIC_REGISTRY, BASE_REGISTRY, PATTERN_REGISTRY
            registered = set()
            registered.update(MONOLITHIC_REGISTRY.keys())
            registered.update(BASE_REGISTRY.keys())
            registered.update(PATTERN_REGISTRY.keys())
            return jsonify({
                "registered": sorted(registered),
                "count": len(registered),
                "mono": len(MONOLITHIC_REGISTRY),
                "base": len(BASE_REGISTRY),
                "pattern": len(PATTERN_REGISTRY),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/finish-data', methods=['GET'])
    def api_finish_data():
        """Serve the full finish catalogue as JSON."""
        logger.info(
            f"[finish-data] Requested (nocache={request.args.get('nocache')}, "
            f"type={request.args.get('type')})"
        )
        try:
            force = request.args.get("nocache") == "1"
            if finish_data_cache["payload"] is None or force:
                logger.debug("[finish-data] Building payload from registries")
                finish_data_cache["payload"] = build_finish_data_payload()
            payload = finish_data_cache["payload"]

            filter_type = request.args.get("type")
            if filter_type and filter_type in payload:
                resp = jsonify({
                    "status": "ok",
                    filter_type: payload[filter_type],
                    "count": len(payload[filter_type]),
                })
            else:
                resp = jsonify({"status": "ok", **payload})

            for key, value in cache_headers.items():
                resp.headers[key] = value
            return resp
        except Exception as e:
            logger.error(f"/api/finish-data failed: {e}\n{traceback.format_exc()}")
            return jsonify({"status": "error", "error": str(e)}), 500

    return {
        "clear": clear_finish_data_cache,
        "prewarm": prewarm_finish_data_cache,
        "build": build_finish_data_payload,
    }
