"""Resumable, adapter-driven readiness for specialized physical surfaces.

This report is an instruction/export contract, never inverse-projection
authority.  It explains exactly which owner or Forge action remains while
keeping unsupported physical geometry abstained.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


SCHEMA = "shokk-forge.surface-readiness/v1"
EXPORT_SCHEMA = "shokk-forge.surface-correction-export/v1"


def _stable_sha(payload: Any) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _adapter_authority(adapter: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": adapter.get("id"),
        "version": str(adapter.get("version") or ""),
        "sha256": adapter.get("sha256") or adapter.get("adapter_sha256"),
    }


def _role_readiness(role: str, spec: dict[str, Any], request: dict[str, Any] | None) -> dict[str, Any]:
    requested = isinstance(request, dict)
    request = request or {}
    request_status = str(request.get("status") or "not_requested")
    review_status = str(request.get("review_status") or "locked")
    if not requested:
        state = "not_requested"
        responsible = "none"
        next_action = "No correction is requested for the current authority state."
    elif request_status in {"requested", "duplicate", "capture_rejected"}:
        state = "capture_required"
        responsible = "owner"
        next_action = str(spec.get("capture_guidance") or "Upload a unique direct photograph of this physical face.")
    elif request_status == "low_confidence":
        state = "attestation_required"
        responsible = "owner"
        next_action = "Confirm that the selected photograph directly matches this physical capture contract."
    elif review_status != "confirmed":
        state = "surface_review_required"
        responsible = "owner"
        next_action = "Review and confirm the four physical-surface corners on the selected source."
    else:
        state = "evidence_ready_projector_blocked"
        responsible = "forge_engine"
        next_action = (
            "Direct evidence is reviewed. Keep projection abstained until a livery-neutral projector "
            "passes active, two-control, and withheld direct-photo calibration."
        )
    owner_action = responsible == "owner"
    return {
        "$schema": "shokk-forge.surface-role-readiness/v1",
        "role": role,
        "surface": spec.get("surface"),
        "physical_scope": spec.get("physical_scope"),
        "requested": requested,
        "state": state,
        "responsible_party": responsible,
        "owner_action_required": owner_action,
        "next_action": next_action,
        "capture_status": request_status,
        "capture_guidance": spec.get("capture_guidance"),
        "capture_quality_contract": spec.get("capture_quality_contract"),
        "selected_reference_id": request.get("selected_reference_id") or request.get("qualified_reference_id"),
        "selected_reference_sha256": ((request.get("surface_review") or {}).get("reference_sha256")),
        "capture_quality": request.get("capture_quality"),
        "attestation_confirmed": request_status == "qualified",
        "review_status": review_status,
        "review_revision": int((request.get("surface_review") or {}).get("revision") or 0),
        "review_quality": ((request.get("surface_review") or {}).get("review_quality")),
        "replacement_candidate_reference_id": request.get("replacement_candidate_reference_id"),
        "capture_rejected_count": int(request.get("capture_rejected_count") or 0),
        "latest_capture_rejection": request.get("latest_capture_rejection"),
        "generic_substitution_allowed": False,
        "specialized_projection_executable": False,
        "blocking_reason": (
            None if not requested else ("owner_evidence_incomplete" if owner_action else "specialized_projector_not_calibrated")
        ),
    }


def build_surface_readiness(job: dict[str, Any], adapter: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic matrix and portable correction checklist."""

    requests = {row.get("role"): row for row in (job.get("evidence_requests") or []) if row.get("role")}
    roles = [
        _role_readiness(role, spec, requests.get(role))
        for role, spec in sorted((adapter.get("optional_evidence_roles") or {}).items())
    ]
    requested = [row for row in roles if row["requested"]]
    owner_rows = [row for row in requested if row["owner_action_required"]]
    engine_rows = [row for row in requested if row["responsible_party"] == "forge_engine"]
    job_adapter = _adapter_authority(job.get("adapter") or {})
    registry_adapter = _adapter_authority(adapter)
    adapter_authority_matches_job = job_adapter == registry_adapter
    authority = {
        "job_id": job.get("job_id"),
        "job_adapter": job_adapter,
        "registry_adapter": registry_adapter,
        "roles": roles,
    }
    readiness_sha = _stable_sha(authority)
    corrections = [
        {
            "role": row["role"],
            "surface": row["surface"],
            "physical_scope": row["physical_scope"],
            "state": row["state"],
            "responsible_party": row["responsible_party"],
            "next_action": row["next_action"],
            "capture_guidance": row["capture_guidance"],
            "selected_reference_id": row["selected_reference_id"],
            "review_revision": row["review_revision"],
            "generic_substitution_allowed": False,
        }
        for row in requested
    ]
    return {
        "$schema": SCHEMA,
        "job_id": job.get("job_id"),
        "adapter": registry_adapter,
        "job_adapter": job_adapter,
        "adapter_authority_matches_job": adapter_authority_matches_job,
        "readiness_sha256": readiness_sha,
        "roles": roles,
        "summary": {
            "role_count": len(roles),
            "requested_count": len(requested),
            "capture_required_count": sum(row["state"] == "capture_required" for row in requested),
            "attestation_required_count": sum(row["state"] == "attestation_required" for row in requested),
            "surface_review_required_count": sum(row["state"] == "surface_review_required" for row in requested),
            "evidence_ready_count": len(engine_rows),
            "owner_action_count": len(owner_rows),
            "forge_engine_action_count": len(engine_rows),
            "specialized_projection_executable_count": 0,
            "unsafe_substitutions_accepted": 0,
            "adapter_refresh_required": not adapter_authority_matches_job,
            "psd_import_unlocked": False,
        },
        "correction_export": {
            "$schema": EXPORT_SCHEMA,
            "job_id": job.get("job_id"),
            "adapter": registry_adapter,
            "job_adapter": job_adapter,
            "adapter_authority_matches_job": adapter_authority_matches_job,
            "readiness_sha256": readiness_sha,
            "instructions": (
                "Complete only the listed direct-photo/review actions. Forge must abstain from specialized "
                "projection until the adapter has a calibrated projector for that physical face."
            ),
            "corrections": corrections,
            "quality_gates": {
                "generic_substitution_allowed": False,
                "mirroring_allowed": False,
                "unreviewed_projection_allowed": False,
                "adapter_authority_matches_job": adapter_authority_matches_job,
                "adapter_refresh_required": not adapter_authority_matches_job,
                "psd_import_unlocked": False,
            },
        },
    }
