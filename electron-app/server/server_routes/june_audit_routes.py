"""June Complete Audit — owner verdict logging for the living audits.

Mirrors the Spec Sculpt preset-audit endpoint (SPB-89 lineage) but is
*category-keyed* so the three living HTML audits (spec overlays / bases /
regular patterns) each persist to their own safe store under ``_audit/``:

    _audit/june_<category>_audit.json          (current verdict per finish id)
    _audit/june_<category>_audit_history.jsonl (append-only submit log)

Verdict vocabulary: keep | rebuild | replace | rename | remove ("rename" added 2026-06-09).
Categories are sanitized free-form (any [a-z0-9_] key) so a new audit needs no backend edit.
Owner rating: integer 1-100 (slider, step 1). ``ai_rating`` is the current
engine score baked into the page so we can see how far off we are.

Register from server.py:
    from server_routes.june_audit_routes import register_june_audit_routes
    register_june_audit_routes(app, server_dir=SERVER_DIR, logger=logger)
"""
from __future__ import annotations

import json
import os
import re
import time
import traceback
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows

# Verdict vocabulary (owner mandate 2026-06-02; "rename" added 2026-06-09 for a good item that
# just needs a better name): keep | rebuild | replace | rename | remove
_VALID_VERDICTS = {"keep", "rebuild", "replace", "rename", "remove"}
# 2026-06-09: categories are no longer a fixed whitelist — any safe [a-z0-9_] key is accepted, so a
# NEW audit (finish, pattern, spec_overlay, lfr_finish, ...) needs ZERO backend change. The category
# is only used as part of the _audit/june_<cat>_audit.json filename; this regex prevents traversal.
_CATEGORY_RE = re.compile(r"^[a-z0-9_]{1,40}$")


def register_june_audit_routes(
    app,
    *,
    server_dir,
    logger,
    external_write_guard=None,
) -> None:
    from flask import jsonify, request

    audit_dir = os.path.join(server_dir, "_audit")

    def _paths(cat: str):
        return (
            os.path.join(audit_dir, f"june_{cat}_audit.json"),
            os.path.join(audit_dir, f"june_{cat}_audit_history.jsonl"),
        )

    def _load(cat: str) -> dict:
        # [2026-09-05 codebase-health S3] a corrupt verdict file is moved aside as
        # <file>.corrupt-<ts> and logged -- never silently treated as empty and then
        # overwritten by the next click with only that click's entries.
        from engine.atomic_io import load_json_guarded
        jp, _ = _paths(cat)
        data = load_json_guarded(jp, default=dict, logger=logger, what=f"june_{cat}_audit.json")
        return data.get("entries", {}) if isinstance(data, dict) else {}

    def _counts(entries: dict) -> dict:
        c = {v: 0 for v in _VALID_VERDICTS}
        for e in entries.values():
            v = (e or {}).get("verdict")
            if v in c:
                c[v] += 1
        return c

    def _safe_int(v, default=0) -> int:
        try:
            return int(round(float(v)))
        except (TypeError, ValueError):
            return default

    @app.route("/api/june-audit/<category>", methods=["GET"])
    def june_audit_get(category):
        """Preload saved verdicts so already-decided finishes stay hidden on reload."""
        if not _CATEGORY_RE.match(category or ""):
            return jsonify({"ok": False, "error": f"unknown category '{category}'"}), 400
        try:
            entries = _load(category)
            return jsonify({
                "ok": True, "category": category, "entries": entries,
                "total": len(entries), "counts": _counts(entries),
            })
        except Exception as e:  # noqa: BLE001
            logger.error(f"/api/june-audit/{category} GET failed: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/june-audit/<category>", methods=["POST"])
    def june_audit_post(category):
        """Merge posted verdicts into _audit/june_<category>_audit.json (+ history).

        Body: ``{"entries": {finish_id: {verdict, rating, ai_rating, notes, ts}}}``.
        ts-based merge keeps the newest decision per finish across tabs.
        """
        if not _CATEGORY_RE.match(category or ""):
            return jsonify({"ok": False, "error": f"unknown category '{category}'"}), 400
        try:
            if external_write_guard is not None:
                denial = external_write_guard(audit_dir, "june-audit-save")
                if denial:
                    return jsonify(denial), 403
            data = request.get_json(silent=True) or {}
            incoming = data.get("entries")
            if not isinstance(incoming, dict):
                return jsonify({"ok": False, "error": "body needs an 'entries' object"}), 400

            os.makedirs(audit_dir, exist_ok=True)
            jp, hp = _paths(category)
            # [2026-09-05 codebase-health S3] load -> merge -> write is exclusive per category
            # (two audit tabs saving at once used to drop one tab's batch) and the write is
            # atomic (temp + os.replace), so a crash mid-save cannot truncate 797 owner verdicts.
            from engine.atomic_io import atomic_write_json, file_lock
            with file_lock(jp):
                merged = _load(category)
                changed = 0
                for fid, raw in incoming.items():
                    if not isinstance(raw, dict):
                        continue
                    verdict = raw.get("verdict")
                    if verdict is not None and verdict not in _VALID_VERDICTS:
                        verdict = None
                    rating = raw.get("rating")
                    if rating in (None, "", 0):
                        rating = None
                    else:
                        rating = max(1, min(100, _safe_int(rating)))
                    clean = {
                        "verdict": verdict,
                        "rating": rating,
                        "ai_rating": _safe_int(raw.get("ai_rating"), 0) or None,
                        "reasons": [str(r)[:60] for r in (raw.get("reasons") or []) if r][:20],
                        "notes": str(raw.get("notes") or "")[:4000],
                        "ts": _safe_int(raw.get("ts"), 0),
                    }
                    prev = merged.get(fid)
                    if prev and int(prev.get("ts", 0)) > int(clean["ts"] or 0):
                        continue  # keep newer existing decision
                    merged[fid] = clean
                    changed += 1

                atomic_write_json(jp, {"category": category, "entries": merged,
                                       "updated": int(time.time())}, indent=2)
                try:
                    with open(hp, "a", encoding="utf-8") as hf:
                        hf.write(json.dumps({"ts": int(time.time()), "changed": changed,
                                             "total": len(merged)}) + "\n")
                except OSError as _spb_ex:
                    _spb_swallow('june_audit_post@L150', _spb_ex)

            return jsonify({"ok": True, "category": category, "total": len(merged),
                            "changed": changed, "counts": _counts(merged)})
        except Exception as e:  # noqa: BLE001
            logger.error(f"/api/june-audit/{category} POST failed: {e}\n{traceback.format_exc()}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # --- serve the living audit pages (the global static-page route is a whitelist) ---
    from flask import send_file, abort

    def _serve_page(name: str):
        path = os.path.join(server_dir, name)
        if os.path.isfile(path):
            return send_file(os.path.abspath(path), mimetype="text/html")
        abort(404)

    @app.route("/SPB_JUNE_AUDIT_SPEC_OVERLAYS.html")
    def _june_page_spec_overlays():
        return _serve_page("SPB_JUNE_AUDIT_SPEC_OVERLAYS.html")

    @app.route("/SPB_JUNE_AUDIT_BASES.html")
    def _june_page_bases():
        return _serve_page("SPB_JUNE_AUDIT_BASES.html")

    @app.route("/SPB_JUNE_AUDIT_PATTERNS.html")
    def _june_page_patterns():
        return _serve_page("SPB_JUNE_AUDIT_PATTERNS.html")

    # 2026-06-09: generic loader so ANY new audit page (SPB_AUDIT_<name>.html) is served with ZERO
    # backend change — just drop the file in server_dir and sync. (The static-page catch-all only
    # serves .js/.css/.png/.svg/.ico, so .html audit pages need an explicit route; this is the one.)
    _AUDIT_PAGE_RE = re.compile(r"^[A-Za-z0-9_\-]{1,80}$")

    @app.route("/SPB_AUDIT_<name>.html")
    def _audit_page_generic(name):
        if not _AUDIT_PAGE_RE.match(name or ""):
            abort(404)
        return _serve_page(f"SPB_AUDIT_{name}.html")
