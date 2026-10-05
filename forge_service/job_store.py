"""Atomic, resumable local job storage for SHOKK FORGE."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

from .adapter_registry import AdapterRegistry
from .contracts import (
    JOB_SCHEMA,
    ContractError,
    confine_child,
    validate_job_id,
    validate_reference_filename,
    validate_reference_id,
    validate_reference_role,
)
from .evidence_requests import reconcile_evidence_requests
from .surface_evidence_lineage import archive_review, build_selection, next_review_revision
from .surface_capture_quality import inspect_capture
from .surface_evidence_review import build_surface_review
from .surface_readiness import build_surface_readiness


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ForgeJobStore:
    """Own job state and source bytes; never interpret livery pixels."""

    def __init__(self, jobs_root: str | Path, adapters: AdapterRegistry):
        self.root = Path(jobs_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.adapters = adapters

    def _job_dir(self, job_id: str) -> Path:
        return confine_child(self.root, self.root / validate_job_id(job_id))

    def job_dir(self, job_id: str) -> Path:
        return self._job_dir(job_id)

    def _job_file(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "job.json"

    def create(self, adapter_id: str, mode: str) -> dict[str, Any]:
        adapter = self.adapters.get(adapter_id)
        job_id = uuid.uuid4().hex
        job_dir = self._job_dir(job_id)
        for name in ("sources", "artifacts", "outputs"):
            (job_dir / name).mkdir(parents=True, exist_ok=False)
        job: dict[str, Any] = {
            "$schema": JOB_SCHEMA,
            "job_id": job_id,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "state": "collecting",
            "adapter": {
                "id": adapter["id"],
                "version": adapter["version"],
                "sha256": adapter["adapter_sha256"],
            },
            "mode": mode,
            "inputs": [],
            "qualification": None,
            "evidence_requests": [],
            "surface_readiness": None,
            "user_corrections": {"view_roles": {}, "anchors": {}, "surface_ownership": {}, "readable_orientation": {}, "surface_evidence": {}, "surface_evidence_selection": {}, "surface_evidence_history": []},
            "stages": {key: {"status": "pending", "artifact": None} for key in ("intake", "geometry", "projection", "semantics", "compile", "qa")},
            "outputs": {"psd_path": None, "tga_path": None, "spec_path": None, "showcase_path": None},
            "gates": {"psd_exact": None, "hard_zones": None, "semantic_purity": None, "five_camera": None, "seams": None, "sim_truth": None},
            "error": None,
        }
        self._write(job)
        return job

    def _write(self, job: dict[str, Any]) -> None:
        job["updated_at"] = _utc_now()
        target = self._job_file(job["job_id"])
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix="job-", suffix=".json.tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(job, handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, target)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def save(self, job: dict[str, Any]) -> dict[str, Any]:
        if str(job.get("$schema")) != JOB_SCHEMA:
            raise ContractError("job schema is invalid")
        self._reconcile_evidence(job)
        self._write(job)
        return job

    def get(self, job_id: str) -> dict[str, Any]:
        path = self._job_file(job_id)
        if not path.is_file():
            raise FileNotFoundError("Forge job was not found")
        job = json.loads(path.read_text(encoding="utf-8"))
        self._reconcile_evidence(job)
        return job

    def reference_path(self, job_id: str, reference_id: str) -> Path:
        job = self.get(job_id)
        reference_id = validate_reference_id(reference_id)
        entry = next((item for item in job["inputs"] if item.get("id") == reference_id), None)
        if entry is None:
            raise FileNotFoundError("Forge reference was not found")
        path = confine_child(self._job_dir(job_id), self._job_dir(job_id) / str(entry["stored_path"]))
        if not path.is_file():
            raise FileNotFoundError("Forge reference bytes were not found")
        return path

    def _reconcile_evidence(self, job: dict[str, Any]) -> None:
        corrections = job.setdefault("user_corrections", {})
        job["evidence_requests"] = reconcile_evidence_requests(
            job.get("evidence_requests") or [],
            job.get("inputs") or [],
            corrections.setdefault("surface_evidence", {}),
            corrections.setdefault("surface_evidence_selection", {}),
            corrections.setdefault("surface_evidence_history", []),
        )
        adapter = self.adapters.get(job["adapter"]["id"])
        job["surface_readiness"] = build_surface_readiness(job, adapter)

    def surface_readiness(self, job_id: str) -> dict[str, Any]:
        """Return the persisted matrix, rebuilding in memory for legacy jobs."""

        job = self.get(job_id)
        report = job.get("surface_readiness")
        if isinstance(report, dict) and report.get("$schema") == "shokk-forge.surface-readiness/v1":
            return report
        self._reconcile_evidence(job)
        return job["surface_readiness"]

    @staticmethod
    def _archive_current_review(
        job: dict[str, Any], role: str, *, reason: str, replacement_reference_id: str, selection_revision: int
    ) -> None:
        corrections = job.setdefault("user_corrections", {})
        reviews = corrections.setdefault("surface_evidence", {})
        current = reviews.get(role)
        if not isinstance(current, dict):
            return
        history = corrections.setdefault("surface_evidence_history", [])
        history.append(
            archive_review(
                current,
                reason=reason,
                replacement_reference_id=replacement_reference_id,
                selection_revision=selection_revision,
            )
        )
        del reviews[role]

    def add_reference(self, job_id: str, role: str, filename: str, stream: BinaryIO) -> dict[str, Any]:
        job = self.get(job_id)
        if job["state"] not in {"collecting", "needs_input", "qualified"}:
            raise ContractError("references cannot be added in the current job state")
        adapter = self.adapters.get(job["adapter"]["id"])
        allowed_roles = tuple(adapter["required_views"] + adapter["optional_views"])
        role = validate_reference_role(role, allowed_roles)
        safe_stem, suffix = validate_reference_filename(filename)

        digest = hashlib.sha256()
        body = bytearray()
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            body.extend(chunk)
            digest.update(chunk)
            if len(body) > 64 * 1024 * 1024:
                raise ContractError("reference image exceeds the 64 MB limit")
        if not body:
            raise ContractError("reference image is empty")

        sha256 = digest.hexdigest()
        ref_id = f"ref-{sha256[:12]}"
        duplicate_of = next((item["id"] for item in job["inputs"] if item["sha256"] == sha256), None)
        stored_name = f"{ref_id}-{safe_stem}{suffix}"
        stored_path = self._job_dir(job_id) / "sources" / stored_name
        stored_path.write_bytes(body)
        evidence_spec = (adapter.get("optional_evidence_roles") or {}).get(role) or {}
        role_confidence = float(evidence_spec.get("slot_confidence") or 1.0)
        capture_quality = inspect_capture(bytes(body), evidence_spec.get("capture_quality_contract")) if evidence_spec else None
        entry = {
            "id": ref_id,
            "original_name": Path(filename).name,
            "stored_path": f"sources/{stored_name}",
            "sha256": sha256,
            "bytes": len(body),
            "role": role,
            "role_confidence": role_confidence,
            "role_source": "guided_surface_slot_unconfirmed" if evidence_spec else "guided_user_slot",
            "duplicate_of": duplicate_of,
        }
        if capture_quality is not None:
            entry["capture_quality"] = capture_quality
        job["inputs"].append(entry)
        self._reconcile_evidence(job)
        job["state"] = "collecting"
        job["qualification"] = None
        self._write(job)
        return entry

    def confirm_evidence(self, job_id: str, role: str, reference_id: str) -> dict[str, Any]:
        """Persist hash-bound user attestation for a specialized physical view."""

        job = self.get(job_id)
        adapter = self.adapters.get(job["adapter"]["id"])
        if adapter.get("adapter_sha256") != job["adapter"].get("sha256"):
            raise ContractError("job adapter authority is stale; recreate the Forge job")
        specs = adapter.get("optional_evidence_roles") or {}
        role = validate_reference_role(role, tuple(specs))
        reference_id = validate_reference_id(reference_id)
        spec = specs[role]
        entry = next(
            (item for item in job.get("inputs", []) if item.get("id") == reference_id and item.get("role") == role),
            None,
        )
        if entry is None:
            raise ContractError("evidence reference does not belong to the requested physical role")
        if entry.get("duplicate_of"):
            raise ContractError("duplicate evidence cannot satisfy a physical surface request")
        quality = entry.get("capture_quality") or {}
        if quality.get("admissible") is not True:
            failures = ", ".join(quality.get("hard_failures") or ["capture integrity unavailable"])
            raise ContractError(f"capture evidence is not admissible: {failures}")
        entry["role_confidence"] = float(spec.get("confirmed_confidence") or 0.0)
        entry["role_source"] = "guided_user_capture_attestation/v1"
        corrections = job.setdefault("user_corrections", {})
        selections = corrections.setdefault("surface_evidence_selection", {})
        previous = selections.get(role)
        selection = build_selection(
            role=role,
            reference=entry,
            adapter_sha256=job["adapter"]["sha256"],
            previous=previous,
        )
        current_review = corrections.setdefault("surface_evidence", {}).get(role)
        if isinstance(current_review, dict) and current_review.get("reference_id") != reference_id:
            self._archive_current_review(
                job,
                role,
                reason="selected_reference_replaced",
                replacement_reference_id=reference_id,
                selection_revision=selection["selection_revision"],
            )
        selections[role] = selection
        self._reconcile_evidence(job)
        self._invalidate_downstream(job)
        if (job.get("qualification") or {}).get("qualified"):
            job["state"] = "qualified"
        job["error"] = None
        self._write(job)
        return job

    def review_evidence_quad(
        self, job_id: str, role: str, reference_id: str, quad: Any
    ) -> dict[str, Any]:
        """Persist exact-role surface corners only after capture attestation."""

        job = self.get(job_id)
        if not (job.get("qualification") or {}).get("qualified"):
            raise ContractError("reference intake must qualify before surface review")
        if job["state"] in {"reconstructing", "ready", "imported"}:
            raise ContractError("surface review cannot change in the current job state")
        adapter = self.adapters.get(job["adapter"]["id"])
        if adapter.get("adapter_sha256") != job["adapter"].get("sha256"):
            raise ContractError("job adapter authority is stale; recreate the Forge job")
        specs = adapter.get("optional_evidence_roles") or {}
        role = validate_reference_role(role, tuple(specs))
        reference_id = validate_reference_id(reference_id)
        reference = next(
            (item for item in job.get("inputs", []) if item.get("id") == reference_id and item.get("role") == role),
            None,
        )
        if reference is None:
            raise ContractError("surface review reference does not belong to the requested physical role")
        if reference.get("duplicate_of"):
            raise ContractError("duplicate evidence cannot create a surface review")
        spec = specs[role]
        if (
            reference.get("role_source") != "guided_user_capture_attestation/v1"
            or float(reference.get("role_confidence") or 0.0) < float(spec.get("minimum_confidence") or 1.0)
        ):
            raise ContractError("surface review requires exact-role capture attestation")
        request = next((row for row in job.get("evidence_requests", []) if row.get("role") == role), None)
        if (
            not request
            or not request.get("qualified")
            or request.get("qualified_reference_id") != reference_id
            or request.get("selected_reference_id") != reference_id
        ):
            raise ContractError("surface review requires the currently qualified evidence request")
        review = build_surface_review(
            adapter=adapter,
            adapter_sha256=job["adapter"]["sha256"],
            role=role,
            reference=reference,
            quad=quad,
        )
        corrections = job["user_corrections"]
        reviews = corrections.setdefault("surface_evidence", {})
        history = corrections.setdefault("surface_evidence_history", [])
        selection = corrections.setdefault("surface_evidence_selection", {}).get(role) or {}
        current = reviews.get(role)
        same = bool(
            isinstance(current, dict)
            and current.get("reference_id") == reference_id
            and current.get("reference_sha256") == review.get("reference_sha256")
            and current.get("quad") == review.get("quad")
        )
        if not same:
            if isinstance(current, dict):
                self._archive_current_review(
                    job,
                    role,
                    reason="surface_quad_revised",
                    replacement_reference_id=reference_id,
                    selection_revision=int(selection.get("selection_revision") or 1),
                )
            review["revision"] = next_review_revision(history, role)
            review["selection_revision"] = int(selection.get("selection_revision") or 1)
            reviews[role] = review
        self._reconcile_evidence(job)
        self._invalidate_downstream(job)
        job["state"] = "qualified"
        job["error"] = None
        self._write(job)
        return job

    @staticmethod
    def _invalidate_downstream(job: dict[str, Any]) -> None:
        for stage in ("geometry", "projection", "semantics", "compile", "qa"):
            job["stages"][stage] = {"status": "pending", "artifact": None}
        job["outputs"] = {key: None for key in job["outputs"]}
        job["gates"] = {key: None for key in job["gates"]}

    def qualify(self, job_id: str) -> dict[str, Any]:
        job = self.get(job_id)
        adapter = self.adapters.get(job["adapter"]["id"])
        required = tuple(adapter["required_views"])
        unique_inputs = [item for item in job["inputs"] if not item.get("duplicate_of")]
        roles = {item["role"] for item in unique_inputs}
        missing = [role for role in required if role not in roles]
        duplicate_count = sum(1 for item in job["inputs"] if item.get("duplicate_of"))
        required_duplicate_count = sum(
            1 for item in job["inputs"] if item.get("duplicate_of") and item.get("role") in required
        )
        optional_duplicate_count = duplicate_count - required_duplicate_count
        covered = len(required) - len(missing)
        qualification = {
            "$schema": "shokk-forge.intake-qualification/v2",
            "required_roles": list(required),
            "present_roles": sorted(roles),
            "missing_roles": missing,
            "unique_reference_count": len(unique_inputs),
            "duplicate_reference_count": duplicate_count,
            "required_duplicate_reference_count": required_duplicate_count,
            "optional_duplicate_reference_count": optional_duplicate_count,
            "coverage": covered / len(required) if required else 1.0,
            "qualified": not missing and required_duplicate_count == 0,
            "abstentions": ([{"scope": "full_reconstruction", "reason": "missing_required_views"}] if missing else [])
                + ([{"scope": "duplicate_evidence", "reason": "duplicate_reference_bytes"}] if required_duplicate_count else [])
                + ([{"scope": "optional_evidence", "reason": "duplicate_optional_reference_bytes"}] if optional_duplicate_count else []),
        }
        self._reconcile_evidence(job)
        job["qualification"] = qualification
        job["stages"]["intake"] = {"status": "complete" if qualification["qualified"] else "needs_input", "artifact": "job.json#qualification"}
        job["state"] = "qualified" if qualification["qualified"] else "needs_input"
        self._write(job)
        return qualification

    def update_corrections(self, job_id: str, corrections: dict[str, dict[str, Any]]) -> dict[str, Any]:
        job = self.get(job_id)
        if not (job.get("qualification") or {}).get("qualified"):
            raise ContractError("reference intake must qualify before corrections")
        if job["state"] in {"reconstructing", "ready", "imported"}:
            raise ContractError("corrections cannot change in the current job state")
        rear = (corrections.get("anchors") or {}).get("rear") or {}
        if rear.get("spoiler_inside_quad") is not None:
            adapter = self.adapters.get(job["adapter"]["id"])
            inside_threshold = float(
                ((adapter.get("optional_evidence_roles") or {}).get("rear_inside") or {}).get("minimum_confidence")
                or 1.0
            )
            has_direct_inside = any(
                request.get("role") == "rear_inside" and request.get("qualified")
                for request in job.get("evidence_requests", [])
            ) or any(
                item.get("role") == "rear_inside"
                and not item.get("duplicate_of")
                and float(item.get("role_confidence") or 0.0) >= inside_threshold
                for item in job.get("inputs", [])
            )
            if not has_direct_inside:
                raise ContractError("rear spoiler inside anchors require a qualified direct inside-face reference")
        changed = False
        for section, values in corrections.items():
            target = job["user_corrections"].setdefault(section, {})
            for key, value in values.items():
                if target.get(key) != value:
                    target[key] = value
                    changed = True
        if changed:
            self._invalidate_downstream(job)
            job["state"] = "qualified"
            job["error"] = None
        self._write(job)
        return job
