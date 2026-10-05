from __future__ import annotations

import io
import json
import uuid
from pathlib import Path

import pytest
from flask import Flask
from PIL import Image

from forge_service import AdapterRegistry, ForgeJobStore, ForgePipeline
from forge_service.contracts import ContractError
from forge_service.evidence_requests import build_evidence_requests
from forge_service.pipeline import _apply_execution_evidence, _surface_anchor_requirements
from server_routes.forge_routes import register_forge_routes


@pytest.fixture()
def service(tmp_path: Path):
    case_root = tmp_path / uuid.uuid4().hex
    workspace = case_root / "workspace"
    dossier = workspace / "_dlm_dossier"
    dossier.mkdir(parents=True)
    (dossier / "template_adapter_seed.json").write_text(
        json.dumps(
            {
                "$schema": "shokk-forge.template-adapter/v1",
                "optional_evidence_roles": {
                    "front_corner_left": {
                        "surface": "nose",
                        "physical_scope": "front_left_corner_transition",
                        "minimum_confidence": 0.85,
                        "slot_confidence": 0.65,
                        "confirmed_confidence": 0.9,
                        "requires_user_attestation": True,
                        "capture_guidance": "direct driver-side front corner",
                        "capture_quality_contract": {"minimum_width": 640, "minimum_height": 360, "minimum_short_edge": 360, "minimum_pixels": 230400, "review_minimum_quad_pixels": 12000, "review_minimum_edge_pixels": 64},
                        "review_contract": {"anchor_field": "front_corner_left_quad", "coordinate_space": "normalized_source_image", "point_order": "screen_tl_tr_br_bl", "minimum_area": 0.005, "seed_quad": [[0.02, 0.02], [0.98, 0.02], [0.98, 0.98], [0.02, 0.98]], "seed_is_authority": False},
                        "prohibited_substitute_roles": ["front", "left", "front_3q"],
                        "request_triggers": [{"reason": "incomplete_surface_coverage", "scope": "nose", "remaining_scope_contains": "front_corner"}],
                    },
                    "front_corner_right": {
                        "surface": "nose",
                        "physical_scope": "front_right_corner_transition",
                        "minimum_confidence": 0.85,
                        "slot_confidence": 0.65,
                        "confirmed_confidence": 0.9,
                        "requires_user_attestation": True,
                        "capture_guidance": "direct passenger-side front corner",
                        "capture_quality_contract": {"minimum_width": 640, "minimum_height": 360, "minimum_short_edge": 360, "minimum_pixels": 230400, "review_minimum_quad_pixels": 12000, "review_minimum_edge_pixels": 64},
                        "review_contract": {"anchor_field": "front_corner_right_quad", "coordinate_space": "normalized_source_image", "point_order": "screen_tl_tr_br_bl", "minimum_area": 0.005, "seed_quad": [[0.02, 0.02], [0.98, 0.02], [0.98, 0.98], [0.02, 0.98]], "seed_is_authority": False},
                        "prohibited_substitute_roles": ["front", "right", "front_3q"],
                        "request_triggers": [{"reason": "incomplete_surface_coverage", "scope": "nose", "remaining_scope_contains": "front_corner"}],
                    },
                    "rear_inside": {
                        "surface": "spoiler_inside",
                        "physical_scope": "rear_spoiler_inside_face",
                        "minimum_confidence": 0.85,
                        "slot_confidence": 0.65,
                        "confirmed_confidence": 0.9,
                        "requires_user_attestation": True,
                        "capture_guidance": "inside spoiler face",
                        "capture_quality_contract": {"minimum_width": 640, "minimum_height": 360, "minimum_short_edge": 360, "minimum_pixels": 230400, "review_minimum_quad_pixels": 12000, "review_minimum_edge_pixels": 64},
                        "review_contract": {"anchor_field": "spoiler_inside_quad", "coordinate_space": "normalized_source_image", "point_order": "screen_tl_tr_br_bl", "minimum_area": 0.005, "seed_quad": [[0.02, 0.02], [0.98, 0.02], [0.98, 0.98], [0.02, 0.98]], "seed_is_authority": False},
                        "prohibited_substitute_roles": ["rear", "rear_3q"],
                        "request_triggers": [{"reason": "missing_car_space_anchors", "scope": "rear", "field_contains": "spoiler_inside_quad"}],
                    },
                },
                "surfaces": {
                    "left_strip": {
                        "family": "side",
                        "side": "left",
                        "paintable": True,
                        "projector": "wheelbase_profile",
                        "inverse_ready": True,
                    },
                    "right_strip": {
                        "family": "side",
                        "side": "right",
                        "paintable": True,
                        "projector": "wheelbase_profile",
                        "inverse_ready": True,
                    },
                    "hood": {
                        "family": "top",
                        "side": "center",
                        "paintable": True,
                        "projector": "top_car_space",
                        "inverse_ready": False,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    adapters = AdapterRegistry(workspace)
    store = ForgeJobStore(case_root / "jobs", adapters)
    pipeline = ForgePipeline(store, adapters)
    app = Flask(__name__)
    register_forge_routes(
        app,
        adapters=adapters,
        job_store=store,
        pipeline=pipeline,
        require_internal_request=lambda: (True, None),
    )
    app.testing = True
    return app.test_client(), store


def _create(client):
    response = client.post(
        "/api/forge/jobs",
        json={"adapter_id": "iracing.dirt_late_model", "mode": "guided"},
    )
    assert response.status_code == 201
    return response.get_json()["job"]


def _png_bytes(role: str) -> io.BytesIO:
    colors = {
        "left": (250, 190, 10),
        "right": (230, 40, 35),
        "top": (25, 25, 25),
        "front": (245, 245, 240),
        "rear": (65, 105, 215),
    }
    image = Image.new("RGB", (640, 360), (238, 238, 238))
    for x in range(80, 560):
        for y in range(90, 290):
            image.putpixel((x, y), colors[role])
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    stream.seek(0)
    return stream


def _optional_png(color: tuple[int, int, int]) -> io.BytesIO:
    image = Image.new("RGB", (960, 600), color)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    stream.seek(0)
    return stream


def _upload_five(client, job_id: str):
    roles = ["left", "right", "top", "front", "rear"]
    response = client.post(
        f"/api/forge/jobs/{job_id}/references",
        data={"roles": roles, "files": [(_png_bytes(role), f"{role}.png") for role in roles]},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    qualified = client.post(f"/api/forge/jobs/{job_id}/qualify")
    assert qualified.status_code == 200
    return qualified.get_json()["job"]


def test_adapter_and_job_contract(service):
    client, store = service
    adapters = client.get("/api/forge/adapters")
    assert adapters.status_code == 200
    assert adapters.get_json()["adapters"][0]["required_views"] == ["left", "right", "top", "front", "rear"]
    assert adapters.get_json()["adapters"][0]["capabilities"]["specialized_surface_readiness"] is False

    job = _create(client)
    assert job["$schema"] == "shokk-forge.job/v1"
    assert job["state"] == "collecting"
    fetched = client.get(f"/api/forge/jobs/{job['job_id']}")
    assert fetched.status_code == 200
    fetched_job = fetched.get_json()["job"]
    assert fetched_job["adapter"]["id"] == "iracing.dirt_late_model"
    assert fetched_job["surface_readiness"]["$schema"] == "shokk-forge.surface-readiness/v1"
    assert fetched_job["surface_readiness"]["summary"]["role_count"] == 3
    assert fetched_job["surface_readiness"]["summary"]["requested_count"] == 0
    with pytest.raises(ContractError):
        store.get("../../escape")


def test_guided_five_view_intake_qualifies(service):
    client, store = service
    job = _create(client)
    job_id = job["job_id"]
    data = {"roles": ["left", "right", "top", "front", "rear"]}
    data["files"] = [(io.BytesIO(f"unique-{role}".encode()), f"{role}.png") for role in data["roles"]]
    upload = client.post(f"/api/forge/jobs/{job_id}/references", data=data, content_type="multipart/form-data")
    assert upload.status_code == 201
    assert len(upload.get_json()["references"]) == 5
    qualify = client.post(f"/api/forge/jobs/{job_id}/qualify")
    assert qualify.status_code == 200
    report = qualify.get_json()["qualification"]
    assert report["qualified"] is True
    assert report["coverage"] == 1.0
    assert report["duplicate_reference_count"] == 0
    resumed = store.get(job_id)
    assert resumed["state"] == "qualified"
    assert resumed["qualification"] == report


def test_forge_page_restores_qualified_job_deep_link():
    workspace = Path(__file__).resolve().parents[1]
    script = (workspace / "forge-page.js").read_text(encoding="utf-8")
    page = (workspace / "forge-page.html").read_text(encoding="utf-8")
    assert "resumeJobFromURL" in script
    assert "URLSearchParams(window.location.search).get('job')" in script
    assert "renderPersistedJob(body.job)" in script
    assert "required views stored" in script
    assert "runReconstruction" in script
    assert "/run`" in script
    assert "jobState !== 'qualified'" in script
    assert "required_corrections" in script
    assert "renderAnchorProposals" in script
    assert "renderSurfaceExecutions" in script
    assert "surface_execution_summary" in script
    assert "renderEvidenceRequests" in script
    assert "uploadRequestedEvidence" in script
    assert "confirmRequestedEvidence" in script
    assert "data-evidence-confirm-role" in script
    assert "data-evidence-review-role" in script
    assert "openEvidenceReview" in script
    assert "/evidence/${role}/quad" in script
    assert "NON-AUTHORITATIVE seed" in script
    assert "replacement_candidate_reference_id" in script
    assert "SUPERSEDE CURRENT REVIEW" in script
    assert "preserved superseded review" in script
    assert "buildEvidenceComparison" in script
    assert "CURRENT AUTHORITY" in script
    assert "NEW CANDIDATE" in script
    assert "LATEST REPLACEMENT REJECTED" in script
    assert "capture_rejected_count" in script
    assert "renderSurfaceReadiness" in script
    assert "exportSurfaceReadiness" in script
    assert "/surface-readiness/export" in script
    assert "ADAPTER REFRESH REQUIRED" in script
    assert "data-evidence-role" in script
    assert "openAnchorEditor" in script
    assert "saveAnchorEditor" in script
    assert "references/${reference.id}/content" in script
    assert "jobState === 'ready' && job.outputs && job.outputs.psd_path" in script
    assert 'id="coverageDetail"' in page
    assert 'id="pipelineGrid"' in page
    assert 'id="surfaceExecutionPanel"' in page
    assert 'id="surfaceExecutionGrid"' in page
    assert 'id="correctionPanel"' in page
    assert 'id="evidenceRequestPanel"' in page
    assert 'id="evidenceRequestGrid"' in page
    assert 'id="surfaceReadinessPanel"' in page
    assert 'id="surfaceReadinessGrid"' in page
    assert 'id="exportReadinessButton"' in page
    assert 'id="anchorProposalPanel"' in page
    assert 'id="anchorProposalGrid"' in page
    assert 'id="anchorEditorDialog"' in page
    assert 'id="anchorEditorOverlay"' in page
    assert 'src="forge-anchor-editor.js' in page
    assert 'data-stage="projection"' in page


def test_missing_or_duplicate_views_abstain(service):
    client, _ = service
    job_id = _create(client)["job_id"]
    upload = client.post(
        f"/api/forge/jobs/{job_id}/references",
        data={
            "roles": ["left", "right"],
            "files": [(io.BytesIO(b"same"), "left.png"), (io.BytesIO(b"same"), "right.png")],
        },
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201
    qualify = client.post(f"/api/forge/jobs/{job_id}/qualify")
    assert qualify.status_code == 409
    report = qualify.get_json()["qualification"]
    assert report["qualified"] is False
    assert set(report["missing_roles"]) == {"right", "top", "front", "rear"}
    assert report["duplicate_reference_count"] == 1
    assert {item["reason"] for item in report["abstentions"]} == {
        "missing_required_views",
        "duplicate_reference_bytes",
    }


def test_surface_evidence_requests_reject_substitutes_and_persist_optional_upload(service):
    client, store = service
    corrections = [
        {
            "scope": "nose",
            "reason": "incomplete_surface_coverage",
            "remaining_scope": "upper_nose_and_both_front_corner_transitions",
        },
        {
            "scope": "rear",
            "reason": "missing_car_space_anchors",
            "fields": ["spoiler_inside_quad"],
        },
    ]
    job = _upload_five(client, _create(client)["job_id"])
    requests = build_evidence_requests(store.adapters.payload(job["adapter"]["id"]), job["inputs"], corrections)
    assert requests["summary"] == {
        "request_count": 3,
        "qualified_count": 0,
        "received_count": 0,
        "duplicate_count": 0,
        "outstanding_count": 3,
        "unsafe_substitutions_accepted": 0,
        "review_required_count": 0,
        "review_confirmed_count": 0,
        "replacement_candidate_count": 0,
        "superseded_review_count": 0,
        "capture_rejected_count": 0,
    }
    by_role = {row["role"]: row for row in requests["requests"]}
    assert by_role["front_corner_left"]["status"] == "requested"
    assert set(by_role["front_corner_left"]["substitute_roles_present"]) == {"front", "left"}
    assert by_role["rear_inside"]["substitute_roles_present"] == ["rear"]
    assert all(row["substitution_allowed"] is False for row in requests["requests"])

    job["evidence_requests"] = requests["requests"]
    store.save(job)
    uploaded = client.post(
        f"/api/forge/jobs/{job['job_id']}/references",
        data={"roles": ["front_corner_left"], "files": [(_optional_png((17, 93, 181)), "front-left-corner.png")]},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201
    saved = uploaded.get_json()["job"]
    left_request = next(row for row in saved["evidence_requests"] if row["role"] == "front_corner_left")
    assert left_request["status"] == "low_confidence"
    assert left_request["qualified"] is False
    assert left_request["confidence"] == 0.65
    qualified = client.post(f"/api/forge/jobs/{job['job_id']}/qualify")
    assert qualified.status_code == 200
    confirmed = client.post(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/confirm",
        json={"reference_id": left_request["qualified_reference_id"]},
    )
    assert confirmed.status_code == 200
    confirmed_job = confirmed.get_json()["job"]
    confirmed_request = next(row for row in confirmed_job["evidence_requests"] if row["role"] == "front_corner_left")
    assert confirmed_request["status"] == "qualified"
    assert confirmed_request["qualified"] is True
    assert confirmed_request["confidence"] == 0.9
    confirmed_input = next(row for row in confirmed_job["inputs"] if row["id"] == left_request["qualified_reference_id"])
    assert confirmed_input["role_source"] == "guided_user_capture_attestation/v1"
    assert confirmed_job["state"] == "qualified"


def test_specialized_surface_review_is_attested_hash_bound_and_non_promoting(service):
    client, store = service
    job = _upload_five(client, _create(client)["job_id"])
    requests = build_evidence_requests(
        store.adapters.payload(job["adapter"]["id"]),
        job["inputs"],
        [{"scope": "nose", "reason": "incomplete_surface_coverage", "remaining_scope": "front_corner"}],
    )
    job["evidence_requests"] = requests["requests"]
    store.save(job)
    uploaded = client.post(
        f"/api/forge/jobs/{job['job_id']}/references",
        data={"roles": ["front_corner_left"], "files": [(_optional_png((41, 123, 201)), "unique-corner.png")]},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201
    reference = uploaded.get_json()["references"][0]
    client.post(f"/api/forge/jobs/{job['job_id']}/qualify")
    locked = client.patch(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/quad",
        json={"reference_id": reference["id"], "quad": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]},
    )
    assert locked.status_code == 400
    assert "capture attestation" in locked.get_json()["error"]
    assert client.post(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/confirm",
        json={"reference_id": reference["id"]},
    ).status_code == 200
    current = store.get(job["job_id"])
    adapter_sha = current["adapter"]["sha256"]
    current["adapter"]["sha256"] = "0" * 64
    store.save(current)
    stale_adapter = client.patch(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/quad",
        json={"reference_id": reference["id"], "quad": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]},
    )
    assert stale_adapter.status_code == 400
    assert "adapter authority is stale" in stale_adapter.get_json()["error"]
    current["adapter"]["sha256"] = adapter_sha
    store.save(current)
    folded = client.patch(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/quad",
        json={"reference_id": reference["id"], "quad": [[0.1, 0.1], [0.9, 0.9], [0.9, 0.1], [0.1, 0.9]]},
    )
    assert folded.status_code == 400
    wrong_role = client.patch(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_right/quad",
        json={"reference_id": reference["id"], "quad": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]},
    )
    assert wrong_role.status_code == 400
    reviewed = client.patch(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/quad",
        json={"reference_id": reference["id"], "quad": [[0.12, 0.14], [0.88, 0.16], [0.84, 0.86], [0.15, 0.82]]},
    )
    assert reviewed.status_code == 200
    saved = reviewed.get_json()["job"]
    record = saved["user_corrections"]["surface_evidence"]["front_corner_left"]
    assert record["$schema"] == "shokk-forge.surface-evidence-review/v1"
    assert record["reference_id"] == reference["id"]
    assert record["reference_sha256"] == reference["sha256"]
    assert record["adapter_sha256"] == saved["adapter"]["sha256"]
    assert record["provenance"] == "guided_user_surface_quad/v1"
    request = next(row for row in saved["evidence_requests"] if row["role"] == "front_corner_left")
    assert request["review_status"] == "confirmed"
    assert request["surface_review"] == record
    assert "front_corner_left" not in saved["user_corrections"]["anchors"]
    assert saved["outputs"]["psd_path"] is None
    assert saved["stages"]["projection"]["status"] == "pending"


def test_specialized_evidence_replacement_selects_new_source_and_preserves_history(service):
    client, store = service
    job = _upload_five(client, _create(client)["job_id"])
    requests = build_evidence_requests(
        store.adapters.payload(job["adapter"]["id"]),
        job["inputs"],
        [{"scope": "nose", "reason": "incomplete_surface_coverage", "remaining_scope": "front_corner"}],
    )
    job["evidence_requests"] = requests["requests"]
    store.save(job)

    first_upload = client.post(
        f"/api/forge/jobs/{job['job_id']}/references",
        data={"roles": ["front_corner_left"], "files": [(_optional_png((20, 90, 180)), "corner-v1.png")]},
        content_type="multipart/form-data",
    ).get_json()["references"][0]
    client.post(f"/api/forge/jobs/{job['job_id']}/qualify")
    assert client.post(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/confirm",
        json={"reference_id": first_upload["id"]},
    ).status_code == 200
    quad_v1 = [[0.12, 0.14], [0.88, 0.16], [0.84, 0.86], [0.15, 0.82]]
    first_review = client.patch(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/quad",
        json={"reference_id": first_upload["id"], "quad": quad_v1},
    ).get_json()["job"]
    assert first_review["user_corrections"]["surface_evidence"]["front_corner_left"]["revision"] == 1

    second_response = client.post(
        f"/api/forge/jobs/{job['job_id']}/references",
        data={"roles": ["front_corner_left"], "files": [(_optional_png((190, 70, 35)), "corner-v2.png")]},
        content_type="multipart/form-data",
    )
    assert second_response.status_code == 201
    second_upload = second_response.get_json()["references"][0]
    candidate_request = next(
        row for row in second_response.get_json()["job"]["evidence_requests"] if row["role"] == "front_corner_left"
    )
    assert candidate_request["selected_reference_id"] == first_upload["id"]
    assert candidate_request["replacement_candidate_reference_id"] == second_upload["id"]
    assert candidate_request["review_status"] == "confirmed"
    assert candidate_request["capture_quality"]["admissible"] is True
    assert candidate_request["replacement_candidate_capture_quality"]["admissible"] is True
    assert candidate_request["replacement_candidate_capture_quality"]["width"] == 960
    client.post(f"/api/forge/jobs/{job['job_id']}/qualify")

    selected = client.post(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/confirm",
        json={"reference_id": second_upload["id"]},
    )
    assert selected.status_code == 200
    selected_job = selected.get_json()["job"]
    selection = selected_job["user_corrections"]["surface_evidence_selection"]["front_corner_left"]
    assert selection["reference_id"] == second_upload["id"]
    assert selection["reference_sha256"] == second_upload["sha256"]
    assert selection["selection_revision"] == 2
    assert "front_corner_left" not in selected_job["user_corrections"]["surface_evidence"]
    history = selected_job["user_corrections"]["surface_evidence_history"]
    assert len(history) == 1
    assert history[0]["reference_id"] == first_upload["id"]
    assert history[0]["quad"] == quad_v1
    assert history[0]["lifecycle"] == {
        "status": "superseded",
        "reason": "selected_reference_replaced",
        "replacement_reference_id": second_upload["id"],
        "selection_revision": 2,
    }
    request = next(row for row in selected_job["evidence_requests"] if row["role"] == "front_corner_left")
    assert request["qualified_reference_id"] == second_upload["id"]
    assert request["selected_reference_id"] == second_upload["id"]
    assert request["review_status"] == "required"
    assert request["superseded_review_count"] == 1

    quad_v2 = [[0.18, 0.12], [0.9, 0.18], [0.82, 0.9], [0.14, 0.8]]
    second_review = client.patch(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/quad",
        json={"reference_id": second_upload["id"], "quad": quad_v2},
    )
    assert second_review.status_code == 200
    resumed = store.get(job["job_id"])
    current = resumed["user_corrections"]["surface_evidence"]["front_corner_left"]
    assert current["reference_id"] == second_upload["id"]
    assert current["revision"] == 2
    assert len(resumed["user_corrections"]["surface_evidence_history"]) == 1
    request = next(row for row in resumed["evidence_requests"] if row["role"] == "front_corner_left")
    assert request["review_status"] == "confirmed"
    assert request["review_revision_count"] == 2
    assert request["replacement_candidate_count"] == 0
    assert resumed["user_corrections"]["anchors"] == {}
    assert resumed["outputs"]["psd_path"] is None

    no_op = client.patch(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/quad",
        json={"reference_id": second_upload["id"], "quad": quad_v2},
    ).get_json()["job"]
    assert len(no_op["user_corrections"]["surface_evidence_history"]) == 1
    assert no_op["user_corrections"]["surface_evidence"]["front_corner_left"]["revision"] == 2


def test_specialized_capture_quality_rejects_low_resolution_and_tiny_review(service):
    client, store = service
    job = _upload_five(client, _create(client)["job_id"])
    job["evidence_requests"] = build_evidence_requests(
        store.adapters.payload(job["adapter"]["id"]),
        job["inputs"],
        [{"scope": "nose", "reason": "incomplete_surface_coverage", "remaining_scope": "front_corner"}],
    )["requests"]
    store.save(job)

    tiny = Image.new("RGB", (160, 90), (80, 100, 120))
    tiny_stream = io.BytesIO()
    tiny.save(tiny_stream, format="PNG")
    tiny_stream.seek(0)
    rejected = client.post(
        f"/api/forge/jobs/{job['job_id']}/references",
        data={"roles": ["front_corner_left"], "files": [(tiny_stream, "too-small.png")]},
        content_type="multipart/form-data",
    ).get_json()
    request = next(row for row in rejected["job"]["evidence_requests"] if row["role"] == "front_corner_left")
    assert request["status"] == "capture_rejected"
    assert request["capture_rejected_count"] == 1
    assert request["latest_capture_rejection"]["admissible"] is False
    assert "short_edge_below_adapter_minimum" in request["latest_capture_rejection"]["hard_failures"]
    denied = client.post(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/confirm",
        json={"reference_id": rejected["references"][0]["id"]},
    )
    assert denied.status_code == 400
    assert "not admissible" in denied.get_json()["error"]

    good = client.post(
        f"/api/forge/jobs/{job['job_id']}/references",
        data={"roles": ["front_corner_left"], "files": [(_optional_png((30, 120, 210)), "direct.png")]},
        content_type="multipart/form-data",
    ).get_json()["references"][0]
    client.post(f"/api/forge/jobs/{job['job_id']}/qualify")
    assert client.post(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/confirm",
        json={"reference_id": good["id"]},
    ).status_code == 200
    tiny_quad = [[0.10, 0.10], [0.20, 0.10], [0.20, 0.16], [0.10, 0.16]]
    review = client.patch(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/quad",
        json={"reference_id": good["id"], "quad": tiny_quad},
    )
    assert review.status_code == 400
    assert "usable source pixels" in review.get_json()["error"]
    resumed = store.get(job["job_id"])
    assert resumed["user_corrections"]["surface_evidence"] == {}
    assert resumed["outputs"]["psd_path"] is None


def test_surface_readiness_matrix_exports_resumable_owner_and_engine_actions(service):
    client, store = service
    job = _upload_five(client, _create(client)["job_id"])
    corrections = [
        {"scope": "nose", "reason": "incomplete_surface_coverage", "remaining_scope": "front_corner"},
        {"scope": "rear", "reason": "missing_car_space_anchors", "fields": ["spoiler_inside_quad"]},
    ]
    job["evidence_requests"] = build_evidence_requests(
        store.adapters.payload(job["adapter"]["id"]), job["inputs"], corrections
    )["requests"]
    store.save(job)
    initial = store.get(job["job_id"])["surface_readiness"]
    assert initial["$schema"] == "shokk-forge.surface-readiness/v1"
    assert initial["summary"]["role_count"] == 3
    assert initial["summary"]["requested_count"] == 3
    assert initial["summary"]["capture_required_count"] == 3
    assert initial["summary"]["owner_action_count"] == 3
    assert initial["summary"]["specialized_projection_executable_count"] == 0
    assert initial["adapter_authority_matches_job"] is True
    assert initial["summary"]["adapter_refresh_required"] is False

    reference = client.post(
        f"/api/forge/jobs/{job['job_id']}/references",
        data={"roles": ["front_corner_left"], "files": [(_optional_png((45, 125, 205)), "corner.png")]},
        content_type="multipart/form-data",
    ).get_json()["references"][0]
    client.post(f"/api/forge/jobs/{job['job_id']}/qualify")
    attestation = store.get(job["job_id"])["surface_readiness"]
    left = next(row for row in attestation["roles"] if row["role"] == "front_corner_left")
    assert left["state"] == "attestation_required"
    assert left["responsible_party"] == "owner"

    assert client.post(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/confirm",
        json={"reference_id": reference["id"]},
    ).status_code == 200
    review_required = store.get(job["job_id"])["surface_readiness"]
    left = next(row for row in review_required["roles"] if row["role"] == "front_corner_left")
    assert left["state"] == "surface_review_required"

    reviewed = client.patch(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/quad",
        json={"reference_id": reference["id"], "quad": [[0.12, 0.14], [0.88, 0.16], [0.84, 0.86], [0.15, 0.82]]},
    )
    assert reviewed.status_code == 200
    readiness = reviewed.get_json()["job"]["surface_readiness"]
    left = next(row for row in readiness["roles"] if row["role"] == "front_corner_left")
    assert left["state"] == "evidence_ready_projector_blocked"
    assert left["responsible_party"] == "forge_engine"
    assert left["specialized_projection_executable"] is False
    assert readiness["summary"]["evidence_ready_count"] == 1
    assert readiness["summary"]["owner_action_count"] == 2
    assert readiness["summary"]["forge_engine_action_count"] == 1
    assert readiness["summary"]["psd_import_unlocked"] is False

    endpoint = client.get(f"/api/forge/jobs/{job['job_id']}/surface-readiness")
    assert endpoint.status_code == 200
    assert endpoint.get_json()["readiness"]["readiness_sha256"] == readiness["readiness_sha256"]
    exported = client.get(f"/api/forge/jobs/{job['job_id']}/surface-readiness/export")
    assert exported.status_code == 200
    assert "attachment;" in exported.headers["Content-Disposition"]
    payload = exported.get_json()
    assert payload["$schema"] == "shokk-forge.surface-correction-export/v1"
    assert len(payload["corrections"]) == 3
    assert payload["quality_gates"] == {
        "adapter_authority_matches_job": True,
        "adapter_refresh_required": False,
        "generic_substitution_allowed": False,
        "mirroring_allowed": False,
        "psd_import_unlocked": False,
        "unreviewed_projection_allowed": False,
    }

    resumed_store = ForgeJobStore(store.root, store.adapters)
    resumed = resumed_store.surface_readiness(job["job_id"])
    assert resumed["readiness_sha256"] == readiness["readiness_sha256"]
    assert resumed["summary"] == readiness["summary"]
    persisted = resumed_store.get(job["job_id"])
    assert persisted["user_corrections"]["anchors"] == {}
    assert persisted["outputs"]["psd_path"] is None

    stale = resumed_store.get(job["job_id"])
    stale["adapter"]["version"] = "8"
    stale["adapter"]["sha256"] = "0" * 64
    resumed_store.save(stale)
    mismatch = resumed_store.surface_readiness(job["job_id"])
    assert mismatch["adapter_authority_matches_job"] is False
    assert mismatch["summary"]["adapter_refresh_required"] is True
    assert mismatch["job_adapter"]["version"] == "8"
    assert mismatch["adapter"]["version"] == store.adapters.get(job["adapter"]["id"])["version"]
    assert mismatch["readiness_sha256"] != readiness["readiness_sha256"]
    assert mismatch["correction_export"]["quality_gates"]["adapter_refresh_required"] is True
    assert mismatch["correction_export"]["quality_gates"]["psd_import_unlocked"] is False
    mismatch_export = client.get(f"/api/forge/jobs/{job['job_id']}/surface-readiness/export")
    assert mismatch_export.status_code == 200
    assert mismatch_export.get_json()["adapter_authority_matches_job"] is False
    assert mismatch_export.get_json()["quality_gates"]["adapter_refresh_required"] is True


def test_requested_optional_role_rejects_duplicate_required_view_bytes(service):
    client, store = service
    job = _upload_five(client, _create(client)["job_id"])
    requests = build_evidence_requests(
        store.adapters.payload(job["adapter"]["id"]),
        job["inputs"],
        [{"scope": "nose", "reason": "incomplete_surface_coverage", "remaining_scope": "front_corner"}],
    )
    job["evidence_requests"] = requests["requests"]
    store.save(job)
    duplicate = client.post(
        f"/api/forge/jobs/{job['job_id']}/references",
        data={"roles": ["front_corner_left"], "files": [(_png_bytes("front"), "reused-front.png")]},
        content_type="multipart/form-data",
    )
    assert duplicate.status_code == 201
    request = next(row for row in duplicate.get_json()["job"]["evidence_requests"] if row["role"] == "front_corner_left")
    assert request["status"] == "duplicate"
    assert request["duplicate_of"] is not None
    assert request["qualified"] is False
    qualification = client.post(f"/api/forge/jobs/{job['job_id']}/qualify")
    assert qualification.status_code == 200
    qualification_report = qualification.get_json()["qualification"]
    assert qualification_report["qualified"] is True
    assert qualification_report["duplicate_reference_count"] == 1
    assert qualification_report["required_duplicate_reference_count"] == 0
    assert qualification_report["optional_duplicate_reference_count"] == 1
    assert qualification_report["abstentions"] == [
        {"scope": "optional_evidence", "reason": "duplicate_optional_reference_bytes"}
    ]
    assert qualification.get_json()["job"]["state"] == "qualified"
    request = next(
        row for row in qualification.get_json()["job"]["evidence_requests"] if row["role"] == "front_corner_left"
    )
    assert request["status"] == "duplicate"
    confirm = client.post(
        f"/api/forge/jobs/{job['job_id']}/evidence/front_corner_left/confirm",
        json={"reference_id": request["qualified_reference_id"] or duplicate.get_json()["references"][0]["id"]},
    )
    assert confirm.status_code == 400
    assert "duplicate evidence" in confirm.get_json()["error"]


def test_requested_optional_role_abstains_below_adapter_confidence(service):
    _, store = service
    adapter = store.adapters.payload("iracing.dirt_late_model")
    report = build_evidence_requests(
        adapter,
        [
            {
                "id": "ref-123456789abc",
                "role": "rear_inside",
                "role_confidence": 0.84,
                "duplicate_of": None,
            }
        ],
        [{"scope": "rear", "reason": "missing_car_space_anchors", "fields": ["spoiler_inside_quad"]}],
    )
    request = report["requests"][0]
    assert request["role"] == "rear_inside"
    assert request["status"] == "low_confidence"
    assert request["confidence"] == 0.84
    assert request["qualified"] is False
    assert report["summary"]["unsafe_substitutions_accepted"] == 0


def test_unknown_adapter_and_bad_reference_are_rejected(service):
    client, _ = service
    bad = client.post("/api/forge/jobs", json={"adapter_id": "unknown.adapter"})
    assert bad.status_code == 400
    job_id = _create(client)["job_id"]
    upload = client.post(
        f"/api/forge/jobs/{job_id}/references",
        data={"roles": ["left"], "files": [(io.BytesIO(b"x"), "payload.exe")]},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 400


def test_run_persists_hash_authorized_geometry_and_abstains_on_missing_anchors(service):
    client, store = service
    job_id = _create(client)["job_id"]
    _upload_five(client, job_id)

    response = client.post(f"/api/forge/jobs/{job_id}/run")
    assert response.status_code == 200
    body = response.get_json()
    job = body["job"]
    run = body["run"]
    assert job["state"] == "needs_input"
    assert run["status"] == "needs_input"
    assert run["blocking_stage"] == "projection"
    assert job["stages"]["geometry"]["status"] == "complete"
    assert job["stages"]["projection"]["status"] == "needs_input"
    assert job["stages"]["semantics"]["status"] == "pending"
    assert job["outputs"]["psd_path"] is None

    geometry_path = store.job_dir(job_id) / job["stages"]["geometry"]["artifact"]
    projection_path = store.job_dir(job_id) / job["stages"]["projection"]["artifact"]
    geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    assert geometry["$schema"] == "shokk-forge.geometry-stage/v1"
    assert geometry["summary"]["reference_count"] == 5
    assert geometry["summary"]["all_source_hashes_verified"] is True
    assert geometry["anchor_proposals"]["$schema"] == "shokk-forge.anchor-proposals/v1"
    assert geometry["anchor_proposals"]["summary"]["role_count"] == 5
    assert all(row["width"] == 640 and row["height"] == 360 for row in geometry["references"])
    assert projection["$schema"] == "shokk-forge.projection-plan/v7"
    assert projection["summary"]["ready_surface_count"] == 0
    assert projection["surface_execution"]["summary"]["executed_surface_count"] == 0
    assert projection["surface_execution"]["summary"]["cross_surface_overlap_pixels"] == 0
    assert projection["summary"]["duplicate_surface_instances"] == 0
    assert {item["reason"] for item in projection["required_corrections"]} == {"missing_car_space_anchors"}
    assert run["anchor_proposals"]["summary"] == geometry["anchor_proposals"]["summary"]
    assert all("proposal_status" in item for item in projection["required_corrections"])

    repeated = client.post(f"/api/forge/jobs/{job_id}/run")
    assert repeated.status_code == 200
    assert repeated.get_json()["run"]["reused_stages"] == ["geometry", "projection"]


def test_corrections_invalidate_downstream_stage_authority(service):
    client, _ = service
    job_id = _create(client)["job_id"]
    _upload_five(client, job_id)
    first = client.post(f"/api/forge/jobs/{job_id}/run")
    assert first.status_code == 200
    authority_before = first.get_json()["run"]["authority_sha256"]

    corrected = client.patch(
        f"/api/forge/jobs/{job_id}/corrections",
        json={
            "anchors": {
                "left": {
                    "rear_wheel_center": [0.2, 0.62],
                    "front_wheel_center": [0.8, 0.62],
                    "body_top_y": 0.22,
                    "rocker_y": 0.82,
                }
            }
        },
    )
    assert corrected.status_code == 200
    corrected_job = corrected.get_json()["job"]
    assert corrected_job["state"] == "qualified"
    assert corrected_job["stages"]["geometry"]["status"] == "pending"
    second = client.post(f"/api/forge/jobs/{job_id}/run")
    assert second.status_code == 200
    assert second.get_json()["run"]["authority_sha256"] != authority_before
    assert second.get_json()["run"]["reused_stages"] == []

    bad = client.patch(f"/api/forge/jobs/{job_id}/corrections", json={"car_name": {"x": 1}})
    assert bad.status_code == 400


def test_reference_content_is_confined_and_anchor_geometry_is_validated(service):
    client, _ = service
    job_id = _create(client)["job_id"]
    job = _upload_five(client, job_id)
    first = job["inputs"][0]
    content = client.get(f"/api/forge/jobs/{job_id}/references/{first['id']}/content")
    assert content.status_code == 200
    assert content.data.startswith(b"\x89PNG")
    assert client.get(f"/api/forge/jobs/{job_id}/references/ref-000000000000/content").status_code == 404
    assert client.get(f"/api/forge/jobs/{job_id}/references/..%2Fescape/content").status_code in {400, 404}

    outside = client.patch(
        f"/api/forge/jobs/{job_id}/corrections",
        json={"anchors": {"front": {"center_x": 1.2}}},
    )
    assert outside.status_code == 400
    folded = client.patch(
        f"/api/forge/jobs/{job_id}/corrections",
        json={"anchors": {"top": {"hood_quad": [[0.1, 0.1], [0.9, 0.9], [0.9, 0.1], [0.1, 0.9]]}}},
    )
    assert folded.status_code == 400
    inverted = client.patch(
        f"/api/forge/jobs/{job_id}/corrections",
        json={"anchors": {"left": {"body_top_y": 0.8, "rocker_y": 0.7}}},
    )
    assert inverted.status_code == 400
    inside_without_evidence = client.patch(
        f"/api/forge/jobs/{job_id}/corrections",
        json={"anchors": {"rear": {"spoiler_inside_quad": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.4], [0.2, 0.4]]}}},
    )
    assert inside_without_evidence.status_code == 400
    assert "direct inside-face reference" in inside_without_evidence.get_json()["error"]


def test_direct_surface_anchor_is_not_blocked_by_unseen_sibling_surface() -> None:
    outside = {
        "family": "rear_aero",
        "projector": "direct_quad",
        "source_anchor": "spoiler_outside_quad",
        "required_anchors": ["spoiler_outside_quad"],
    }
    inside = {
        "family": "rear_aero",
        "projector": "rear_car_space",
        "required_anchors": ["spoiler_inside_quad"],
    }
    assert _surface_anchor_requirements(outside, "rear") == ("spoiler_outside_quad",)
    assert _surface_anchor_requirements(inside, "rear") == ("spoiler_inside_quad",)


def test_front_valance_subprojector_owns_partial_front_anchor_contract() -> None:
    partial = {
        "family": "front",
        "projector": "front_valance_scanline",
        "source_anchor": "front_valance_quad",
        "required_anchors": ["center_x", "half_width", "ground_y", "valance_top_y", "front_valance_quad"],
    }
    assert _surface_anchor_requirements(partial, "front") == (
        "center_x",
        "half_width",
        "ground_y",
        "valance_top_y",
        "front_valance_quad",
    )


def test_packaged_adapter_declares_front_valance_as_partial_surface() -> None:
    workspace = Path(__file__).resolve().parents[1]
    adapter = json.loads((workspace / "_dlm_dossier" / "template_adapter_v1" / "adapter.json").read_text(encoding="utf-8"))
    valance = adapter["surfaces"]["nose"]["qualified_subprojectors"]["front_valance"]
    assert adapter["package_version"] == "10"
    assert valance["coverage_contract"] == "partial_surface/v1"
    assert valance["satisfies_full_surface"] is False
    assert valance["remaining_scope"] == "upper_nose_and_both_front_corner_transitions"


def test_partial_execution_persists_pixels_but_returns_completeness_correction() -> None:
    plan = {"surface": "nose", "status": "ready", "qualified_scope": "front_valance_only"}
    record = {
        "layer_path": "artifacts/surfaces/a/nose.png",
        "layer_sha256": "a" * 64,
        "owned_uv_pixels": 12441,
        "containment": 1.0,
        "owned_mask_coverage": 0.19,
        "surface_completion": "partial",
        "satisfies_full_surface": False,
        "completed_scope": "front_valance_only",
        "remaining_scope": "upper_nose_and_both_front_corner_transitions",
        "coverage_contract": "partial_surface/v1",
    }
    correction = _apply_execution_evidence(plan, record)
    assert plan["status"] == "partial"
    assert plan["owned_uv_pixels"] == 12441
    assert plan["satisfies_full_surface"] is False
    assert correction == {
        "scope": "nose",
        "reason": "incomplete_surface_coverage",
        "completed_scope": "front_valance_only",
        "remaining_scope": "upper_nose_and_both_front_corner_transitions",
        "owned_uv_pixels": 12441,
        "layer_path": "artifacts/surfaces/a/nose.png",
    }


def test_top_anchor_order_and_cross_view_rear_deck_patch_are_persisted(service):
    client, _ = service
    job_id = _create(client)["job_id"]
    _upload_five(client, job_id)
    hood = [[0.10, 0.2], [0.30, 0.2], [0.30, 0.7], [0.10, 0.7]]
    roof = [[0.40, 0.2], [0.58, 0.2], [0.58, 0.7], [0.40, 0.7]]
    deck = [[0.66, 0.2], [0.86, 0.2], [0.86, 0.7], [0.66, 0.7]]
    saved = client.patch(
        f"/api/forge/jobs/{job_id}/corrections",
        json={"anchors": {"top": {"hood_quad": hood, "roof_quad": roof, "rear_deck_quad": deck}, "rear": {"rear_deck_quad": deck}}},
    )
    assert saved.status_code == 200
    anchors = saved.get_json()["job"]["user_corrections"]["anchors"]
    assert anchors["top"]["rear_deck_quad"] == deck
    assert anchors["rear"]["rear_deck_quad"] == deck

    reordered = client.patch(
        f"/api/forge/jobs/{job_id}/corrections",
        json={"anchors": {"top": {"hood_quad": hood, "roof_quad": deck, "rear_deck_quad": roof}}},
    )
    assert reordered.status_code == 400


def test_pipeline_rejects_unqualified_or_tampered_sources(service):
    client, store = service
    unqualified = _create(client)["job_id"]
    assert client.post(f"/api/forge/jobs/{unqualified}/run").status_code == 409

    job_id = _create(client)["job_id"]
    qualified = _upload_five(client, job_id)
    source_path = store.job_dir(job_id) / qualified["inputs"][0]["stored_path"]
    source_path.write_bytes(b"tampered")
    failed = client.post(f"/api/forge/jobs/{job_id}/run")
    assert failed.status_code == 409
    assert failed.get_json()["job"]["state"] == "failed"
    assert "hash changed" in failed.get_json()["error"]
