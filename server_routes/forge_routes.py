"""Internal local API routes for SHOKK FORGE guided jobs."""

from __future__ import annotations

from flask import jsonify, request, send_file

from forge_service.contracts import ContractError, require_mapping, validate_corrections_payload, validate_create_payload


def register_forge_routes(app, *, adapters, job_store, pipeline, require_internal_request) -> None:
    def _internal_error():
        ok, message = require_internal_request()
        if not ok:
            return jsonify({"error": message}), 403
        return None

    @app.get("/api/forge/adapters")
    def api_forge_adapters():
        denied = _internal_error()
        if denied:
            return denied
        return jsonify({"adapters": adapters.list()})

    @app.post("/api/forge/jobs")
    def api_forge_create_job():
        denied = _internal_error()
        if denied:
            return denied
        try:
            adapter_id, mode = validate_create_payload(request.get_json(silent=True), adapters.ids())
            return jsonify({"job": job_store.create(adapter_id, mode)}), 201
        except ContractError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.get("/api/forge/jobs/<job_id>")
    def api_forge_get_job(job_id):
        denied = _internal_error()
        if denied:
            return denied
        try:
            return jsonify({"job": job_store.get(job_id)})
        except ContractError as exc:
            return jsonify({"error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/forge/jobs/<job_id>/references")
    def api_forge_add_references(job_id):
        denied = _internal_error()
        if denied:
            return denied
        uploads = request.files.getlist("files")
        roles = request.form.getlist("roles")
        if not uploads or len(uploads) != len(roles):
            return jsonify({"error": "files and roles must be non-empty parallel lists"}), 400
        try:
            added = [
                job_store.add_reference(job_id, role, upload.filename, upload.stream)
                for upload, role in zip(uploads, roles)
            ]
            return jsonify({"references": added, "job": job_store.get(job_id)}), 201
        except ContractError as exc:
            return jsonify({"error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.get("/api/forge/jobs/<job_id>/references/<reference_id>/content")
    def api_forge_reference_content(job_id, reference_id):
        denied = _internal_error()
        if denied:
            return denied
        try:
            return send_file(job_store.reference_path(job_id, reference_id), conditional=True, max_age=0)
        except ContractError as exc:
            return jsonify({"error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.get("/api/forge/jobs/<job_id>/surface-readiness")
    def api_forge_surface_readiness(job_id):
        denied = _internal_error()
        if denied:
            return denied
        try:
            return jsonify({"readiness": job_store.surface_readiness(job_id)})
        except ContractError as exc:
            return jsonify({"error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.get("/api/forge/jobs/<job_id>/surface-readiness/export")
    def api_forge_surface_readiness_export(job_id):
        denied = _internal_error()
        if denied:
            return denied
        try:
            report = job_store.surface_readiness(job_id)
            response = jsonify(report["correction_export"])
            response.headers["Content-Disposition"] = (
                f'attachment; filename="forge-{job_id}-surface-corrections.json"'
            )
            response.headers["Cache-Control"] = "no-store"
            return response
        except ContractError as exc:
            return jsonify({"error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/forge/jobs/<job_id>/qualify")
    def api_forge_qualify(job_id):
        denied = _internal_error()
        if denied:
            return denied
        try:
            qualification = job_store.qualify(job_id)
            status = 200 if qualification["qualified"] else 409
            return jsonify({"qualification": qualification, "job": job_store.get(job_id)}), status
        except ContractError as exc:
            return jsonify({"error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/forge/jobs/<job_id>/evidence/<role>/confirm")
    def api_forge_confirm_evidence(job_id, role):
        denied = _internal_error()
        if denied:
            return denied
        try:
            payload = require_mapping(request.get_json(silent=True))
            return jsonify({"job": job_store.confirm_evidence(job_id, role, payload.get("reference_id"))})
        except ContractError as exc:
            return jsonify({"error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.patch("/api/forge/jobs/<job_id>/corrections")
    def api_forge_update_corrections(job_id):
        denied = _internal_error()
        if denied:
            return denied
        try:
            corrections = validate_corrections_payload(request.get_json(silent=True))
            return jsonify({"job": job_store.update_corrections(job_id, corrections)})
        except ContractError as exc:
            return jsonify({"error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.patch("/api/forge/jobs/<job_id>/evidence/<role>/quad")
    def api_forge_review_evidence_quad(job_id, role):
        denied = _internal_error()
        if denied:
            return denied
        try:
            payload = require_mapping(request.get_json(silent=True))
            job = job_store.review_evidence_quad(
                job_id, role, payload.get("reference_id"), payload.get("quad")
            )
            return jsonify({"job": job})
        except ContractError as exc:
            return jsonify({"error": str(exc)}), 400
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/forge/jobs/<job_id>/run")
    def api_forge_run(job_id):
        denied = _internal_error()
        if denied:
            return denied
        try:
            run = pipeline.run(job_id)
            return jsonify({"run": run, "job": job_store.get(job_id)})
        except ContractError as exc:
            return jsonify({"error": str(exc), "job": _safe_job(job_store, job_id)}), 409
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404


def _safe_job(job_store, job_id):
    try:
        return job_store.get(job_id)
    except (ContractError, FileNotFoundError):
        return None
