"""Resumable, hash-authorized SHOKK FORGE pipeline orchestration."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from .adapter_registry import AdapterRegistry
from .anchors import ROLE_ANCHOR_REQUIREMENTS, accepted_anchor_values, propose_anchors
from .contracts import ContractError, confine_child
from .evidence import inspect_reference, sha256_file
from .evidence_requests import build_evidence_requests
from .job_store import ForgeJobStore
from .surface_executor import execute_ready_surfaces


RUN_SCHEMA = "shokk-forge.pipeline-run/v1"
GEOMETRY_SCHEMA = "shokk-forge.geometry-stage/v1"
PROJECTION_SCHEMA = "shokk-forge.projection-plan/v7"
PIPELINE_CONTRACT = "shokk-forge.pipeline+surface-evidence-requests/v8"


def _stable_sha(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _surface_role(surface: dict[str, Any]) -> str | None:
    family = str(surface.get("family") or "")
    side = str(surface.get("side") or "")
    if family in {"side", "front_fender"} and side in {"left", "right"}:
        return side
    if family == "top":
        return "top"
    if family == "front":
        return "front"
    if family == "rear_aero":
        return "rear"
    return None


def _surface_anchor_requirements(surface: dict[str, Any], role: str) -> tuple[str, ...]:
    """Resolve only the anchors owned by one physical surface.

    A missing, unseen spoiler-inside face must not block a directly observed
    spoiler-outside face.  Adapter-declared requirements are authoritative;
    legacy surfaces retain the conservative whole-role contract.
    """
    declared = surface.get("required_anchors")
    if isinstance(declared, list) and declared and all(isinstance(value, str) and value for value in declared):
        return tuple(declared)
    source_anchor = surface.get("source_anchor")
    if surface.get("projector") in {"direct_top_quad", "direct_quad"} and isinstance(source_anchor, str) and source_anchor:
        return (source_anchor,)
    return ROLE_ANCHOR_REQUIREMENTS[role]


def _apply_execution_evidence(plan: dict[str, Any], record: dict[str, Any]) -> dict[str, Any] | None:
    """Persist executed pixels while keeping partial coverage out of readiness.

    Executor success proves that pixels are correctly owned; it does not prove
    that those pixels cover the entire physical surface.  The latter is an
    independent adapter-authored contract.
    """

    plan["layer_path"] = record["layer_path"]
    plan["layer_sha256"] = record["layer_sha256"]
    plan["owned_uv_pixels"] = record["owned_uv_pixels"]
    plan["containment"] = record["containment"]
    plan["owned_mask_coverage"] = record["owned_mask_coverage"]
    plan["surface_completion"] = record.get("surface_completion", "complete")
    plan["satisfies_full_surface"] = record.get("satisfies_full_surface", True)
    if plan["satisfies_full_surface"]:
        plan["status"] = "complete"
        plan["reason"] = "full_surface_execution_complete"
        return None
    plan["status"] = "partial"
    plan["reason"] = "qualified_partial_surface_executed"
    plan["completed_scope"] = record.get("completed_scope") or plan.get("qualified_scope")
    plan["remaining_scope"] = record.get("remaining_scope")
    plan["coverage_contract"] = record.get("coverage_contract")
    return {
        "scope": plan["surface"],
        "reason": "incomplete_surface_coverage",
        "completed_scope": plan["completed_scope"],
        "remaining_scope": plan["remaining_scope"],
        "owned_uv_pixels": plan["owned_uv_pixels"],
        "layer_path": plan["layer_path"],
    }


class ForgePipeline:
    """Run safe deterministic stages and stop whenever geometry is unproved."""

    def __init__(self, job_store: ForgeJobStore, adapters: AdapterRegistry):
        self.job_store = job_store
        self.adapters = adapters

    def _authority(self, job: dict[str, Any]) -> str:
        payload = {
            "pipeline_contract": PIPELINE_CONTRACT,
            "adapter": job["adapter"],
            "inputs": sorted(
                (
                    {
                        "id": row["id"],
                        "sha256": row["sha256"],
                        "role": row["role"],
                        "duplicate_of": row.get("duplicate_of"),
                        "role_confidence": row.get("role_confidence"),
                        "role_source": row.get("role_source"),
                    }
                    for row in job["inputs"]
                ),
                key=lambda row: (row["role"], row["id"]),
            ),
            "user_corrections": job["user_corrections"],
        }
        return _stable_sha(payload)

    def _artifact_path(self, job_id: str, stage: str, authority: str) -> Path:
        root = self.job_store.job_dir(job_id)
        return confine_child(root, root / "artifacts" / stage / f"{authority}.json")

    def _write_artifact(self, job_id: str, stage: str, authority: str, payload: dict[str, Any]) -> tuple[str, str]:
        target = self._artifact_path(job_id, stage, authority)
        target.parent.mkdir(parents=True, exist_ok=True)
        body = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        fd, tmp_name = tempfile.mkstemp(prefix=f"{stage}-", suffix=".json.tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, target)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        relative = target.relative_to(self.job_store.job_dir(job_id)).as_posix()
        return relative, hashlib.sha256(body).hexdigest()

    def _cached_artifact(self, job: dict[str, Any], stage: str, authority: str) -> dict[str, Any] | None:
        record = job["stages"].get(stage) or {}
        relative = record.get("artifact")
        if record.get("authority_sha256") != authority or not relative or not record.get("artifact_sha256"):
            return None
        root = self.job_store.job_dir(job["job_id"])
        path = confine_child(root, root / relative)
        if not path.is_file() or sha256_file(path) != record["artifact_sha256"]:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("authority_sha256") != authority:
            return None
        if stage == "projection":
            for row in (payload.get("surface_execution") or {}).get("records", []):
                if row.get("status") != "complete":
                    continue
                layer = confine_child(root, root / str(row.get("layer_path") or ""))
                mask = Path(str(row.get("mask_path") or ""))
                if (
                    not layer.is_file()
                    or sha256_file(layer) != row.get("layer_sha256")
                    or not mask.is_file()
                    or sha256_file(mask) != row.get("mask_sha256")
                ):
                    return None
        return payload

    def _stage_record(
        self,
        job: dict[str, Any],
        stage: str,
        status: str,
        authority: str,
        relative: str,
        artifact_sha: str,
        elapsed: float,
    ) -> None:
        job["stages"][stage] = {
            "status": status,
            "artifact": relative,
            "authority_sha256": authority,
            "artifact_sha256": artifact_sha,
            "elapsed_seconds": round(elapsed, 4),
        }

    def _geometry(self, job: dict[str, Any], authority: str) -> tuple[dict[str, Any], bool]:
        cached = self._cached_artifact(job, "geometry", authority)
        if cached is not None:
            return cached, True
        started = time.perf_counter()
        job_dir = self.job_store.job_dir(job["job_id"])
        references = [
            inspect_reference(job_dir, entry)
            for entry in job["inputs"]
            if not entry.get("duplicate_of")
        ]
        roles = sorted({row["role"] for row in references})
        valid = bool(references and all(row["valid"] for row in references))
        anchor_proposals = propose_anchors(job_dir, job["inputs"])
        payload = {
            "$schema": GEOMETRY_SCHEMA,
            "job_id": job["job_id"],
            "authority_sha256": authority,
            "adapter": job["adapter"],
            "references": references,
            "anchor_proposals": anchor_proposals,
            "summary": {
                "reference_count": len(references),
                "roles": roles,
                "minimum_geometry_confidence": min((row["geometry_confidence"] for row in references), default=0.0),
                "all_source_hashes_verified": valid,
                "accepted_anchor_roles": anchor_proposals["summary"]["accepted_roles"],
                "review_anchor_roles": anchor_proposals["summary"]["review_roles"],
                "abstained_anchor_roles": anchor_proposals["summary"]["abstained_roles"],
            },
            "valid": valid,
        }
        if not valid:
            raise ContractError("geometry evidence did not validate")
        relative, artifact_sha = self._write_artifact(job["job_id"], "geometry", authority, payload)
        self._stage_record(job, "geometry", "complete", authority, relative, artifact_sha, time.perf_counter() - started)
        return payload, False

    def _projection(self, job: dict[str, Any], authority: str, geometry: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        cached = self._cached_artifact(job, "projection", authority)
        if cached is not None:
            return cached, True
        started = time.perf_counter()
        adapter = self.adapters.payload(job["adapter"]["id"])
        present_roles = set(geometry["summary"]["roles"])
        anchors = job["user_corrections"].get("anchors", {})
        proposals = geometry.get("anchor_proposals") or {"roles": {}}
        ownership = job["user_corrections"].get("surface_ownership", {})
        plans: list[dict[str, Any]] = []
        corrections: list[dict[str, Any]] = []
        resolved_anchors: dict[str, dict[str, Any]] = {}
        for surface_name, surface in adapter.get("surfaces", {}).items():
            if not surface.get("paintable"):
                continue
            role = _surface_role(surface)
            plan: dict[str, Any] = {
                "surface": surface_name,
                "family": surface.get("family"),
                "role": role,
                "projector": surface.get("projector"),
                "status": "abstain",
                "reason": None,
                "reflection_allowed": False,
            }
            if role is None or role not in present_roles:
                plan["reason"] = "missing_direct_view"
                corrections.append({"scope": surface_name, "reason": "missing_direct_view", "role": role})
                plans.append(plan)
                continue
            declared = ownership.get(surface_name) if isinstance(ownership.get(surface_name), dict) else {}
            subprojector_name = declared.get("subprojector")
            subprojector = (surface.get("qualified_subprojectors") or {}).get(subprojector_name)
            qualified_subprojector = None
            effective_surface = surface
            if not surface.get("inverse_ready") and subprojector and subprojector.get("inverse_ready"):
                qualified_subprojector = subprojector
                effective_surface = {**surface, **subprojector}
                plan["projector"] = subprojector.get("projector")
                plan["subprojector"] = subprojector_name
                plan["qualified_scope"] = subprojector.get("qualified_scope")
                plan["source_anchor"] = subprojector.get("source_anchor")
                plan["qualified_projector_config"] = subprojector
            manual_anchors = anchors.get(role) if isinstance(anchors.get(role), dict) else {}
            automatic_anchors = accepted_anchor_values(proposals, role)
            role_anchors = {**automatic_anchors, **manual_anchors}
            plan["anchor_source"] = "user_correction" if manual_anchors else ("accepted_proposal" if automatic_anchors else None)
            required_anchors = _surface_anchor_requirements(effective_surface, role)
            plan["required_anchors"] = list(required_anchors)
            missing = [key for key in required_anchors if key not in role_anchors]
            if missing:
                plan["reason"] = "missing_car_space_anchors"
                plan["missing_anchors"] = missing
                proposal = (proposals.get("roles") or {}).get(role) or {}
                proposed_fields = proposal.get("fields") or {}
                corrections.append(
                    {
                        "scope": role,
                        "reason": "missing_car_space_anchors",
                        "fields": missing,
                        "proposal_status": proposal.get("status", "abstain"),
                        "proposal_confidence": proposal.get("confidence", 0.0),
                        "proposal_fields": {name: proposed_fields.get(name) for name in missing if proposed_fields.get(name)},
                        "reviewable": bool(missing) and all((proposed_fields.get(name) or {}).get("value") is not None for name in missing),
                    }
                )
                plans.append(plan)
                continue
            resolved_anchors[role] = role_anchors
            if surface.get("inverse_ready"):
                plan["status"] = "ready"
                plan["reason"] = "adapter_inverse_ready"
            elif qualified_subprojector is not None:
                plan["status"] = "ready"
                plan["reason"] = "qualified_subprojector_declared"
            else:
                plan["reason"] = "unresolved_projector"
                plan["available_subprojectors"] = sorted((surface.get("qualified_subprojectors") or {}).keys())
                corrections.append(
                    {
                        "scope": surface_name,
                        "reason": "unresolved_projector",
                        "available_subprojectors": plan["available_subprojectors"],
                    }
                )
            plans.append(plan)
        execution = execute_ready_surfaces(
            job_dir=self.job_store.job_dir(job["job_id"]),
            adapter_path=self.adapters.payload_path(job["adapter"]["id"]),
            adapter=adapter,
            inputs=job["inputs"],
            proposals=proposals,
            resolved_anchors=resolved_anchors,
            plans=plans,
            authority=authority,
        )
        execution_by_surface = {row.get("surface"): row for row in execution["records"]}
        for plan in plans:
            if plan.get("status") != "ready":
                continue
            record = execution_by_surface.get(plan["surface"])
            if record and record.get("status") == "complete":
                correction = _apply_execution_evidence(plan, record)
                if correction is not None:
                    corrections.append(correction)
            else:
                reason = (record or {}).get("reason") or "surface executor did not return evidence"
                plan["status"] = "abstain"
                plan["reason"] = "surface_execution_failed"
                plan["execution_error"] = reason
                corrections.append({"scope": plan["surface"], "reason": "surface_execution_failed", "detail": reason})
        unique_corrections = []
        seen = set()
        for item in corrections:
            key = _stable_sha(item)
            if key not in seen:
                unique_corrections.append(item)
                seen.add(key)
        ready_count = sum(plan["status"] == "complete" for plan in plans)
        partial_count = sum(plan["status"] == "partial" for plan in plans)
        evidence_requests = build_evidence_requests(
            adapter,
            job.get("inputs") or [],
            unique_corrections,
            job.get("evidence_requests") or [],
            (job.get("user_corrections") or {}).get("surface_evidence") or {},
            (job.get("user_corrections") or {}).get("surface_evidence_selection") or {},
            (job.get("user_corrections") or {}).get("surface_evidence_history") or [],
        )
        payload = {
            "$schema": PROJECTION_SCHEMA,
            "job_id": job["job_id"],
            "authority_sha256": authority,
            "adapter": job["adapter"],
            "surface_plans": plans,
            "surface_execution": execution,
            "required_corrections": unique_corrections,
            "evidence_requests": evidence_requests,
            "summary": {
                "paintable_surface_count": len(plans),
                "ready_surface_count": ready_count,
                "complete_surface_count": ready_count,
                "partial_surface_count": partial_count,
                "executed_surface_count": execution["summary"]["executed_surface_count"],
                "generated_uv_pixels": execution["summary"]["generated_uv_pixels"],
                "unique_uv_pixels": execution["summary"]["unique_uv_pixels"],
                "cross_surface_overlap_pixels": execution["summary"]["cross_surface_overlap_pixels"],
                "minimum_execution_containment": execution["summary"]["minimum_containment"],
                "abstained_surface_count": len(plans) - ready_count - partial_count,
                "unexecuted_surface_count": len(plans) - ready_count - partial_count,
                "incomplete_surface_count": len(plans) - ready_count,
                "partial_uv_pixels": execution["summary"]["partial_uv_pixels"],
                "reflection_used": False,
                "duplicate_surface_instances": 0,
                "automatic_anchor_roles": sorted(
                    {
                        plan["role"]
                        for plan in plans
                        if plan.get("anchor_source") == "accepted_proposal" and plan.get("role")
                    }
                ),
                "user_anchor_roles": sorted(
                    {
                        plan["role"]
                        for plan in plans
                        if plan.get("anchor_source") == "user_correction" and plan.get("role")
                    }
                ),
            },
            "valid": ready_count == len(plans) and bool(plans),
        }
        relative, artifact_sha = self._write_artifact(job["job_id"], "projection", authority, payload)
        status = "complete" if payload["valid"] else "needs_input"
        self._stage_record(job, "projection", status, authority, relative, artifact_sha, time.perf_counter() - started)
        return payload, False

    def run(self, job_id: str) -> dict[str, Any]:
        job = self.job_store.get(job_id)
        if not (job.get("qualification") or {}).get("qualified"):
            raise ContractError("reference intake must qualify before reconstruction")
        current_adapter = self.adapters.get(job["adapter"]["id"])
        if current_adapter["adapter_sha256"] != job["adapter"]["sha256"]:
            raise ContractError("job adapter hash is stale; create a new job or explicitly migrate it")
        if job["state"] in {"ready", "imported"}:
            raise ContractError("job is already finalized")

        authority = self._authority(job)
        started = time.perf_counter()
        job["state"] = "reconstructing"
        job["error"] = None
        self.job_store.save(job)
        reused: list[str] = []
        try:
            geometry, geometry_cached = self._geometry(job, authority)
            if geometry_cached:
                reused.append("geometry")
            projection, projection_cached = self._projection(job, authority, geometry)
            if projection_cached:
                reused.append("projection")
            if not projection["valid"]:
                job["state"] = "needs_input"
                status = "needs_input"
                blocking_stage = "projection"
                next_stage = "projection"
            else:
                job["state"] = "anchored"
                status = "anchored"
                blocking_stage = None
                next_stage = "semantics"
            job["evidence_requests"] = (projection.get("evidence_requests") or {}).get("requests", [])
            run_report = {
                "$schema": RUN_SCHEMA,
                "job_id": job_id,
                "authority_sha256": authority,
                "status": status,
                "completed_stages": ["intake", "geometry"] + (["projection"] if projection["valid"] else []),
                "reused_stages": reused,
                "blocking_stage": blocking_stage,
                "next_stage": next_stage,
                "required_corrections": projection["required_corrections"],
                "evidence_requests": projection.get("evidence_requests"),
                "anchor_proposals": geometry.get("anchor_proposals"),
                "projection_summary": projection.get("summary"),
                "surface_execution_summary": (projection.get("surface_execution") or {}).get("summary"),
                "surface_executions": (projection.get("surface_execution") or {}).get("records", []),
                "elapsed_seconds": round(time.perf_counter() - started, 4),
            }
            relative, run_sha = self._write_artifact(job_id, "run", authority, run_report)
            job["last_run"] = {"artifact": relative, "artifact_sha256": run_sha, **run_report}
            self.job_store.save(job)
            return run_report
        except Exception as exc:
            job = self.job_store.get(job_id)
            job["state"] = "failed"
            job["error"] = {"stage": "pipeline", "message": str(exc), "authority_sha256": authority}
            self.job_store.save(job)
            if isinstance(exc, ContractError):
                raise
            raise ContractError(f"Forge pipeline failed: {exc}") from exc
