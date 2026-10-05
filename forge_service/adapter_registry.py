"""Versioned template-adapter discovery for SHOKK FORGE."""

from __future__ import annotations

import hashlib
import json
import copy
from pathlib import Path
from typing import Any

from .contracts import ContractError, REQUIRED_DLM_ROLES


class AdapterRegistry:
    """Expose geometry adapters without allowing livery identity into them."""

    def __init__(self, workspace_root: str | Path):
        self.workspace_root = Path(workspace_root).resolve()
        self._payloads: dict[str, dict[str, Any]] = {}
        self._payload_paths: dict[str, Path] = {}
        self._adapters = self._discover()

    def _discover(self) -> dict[str, dict[str, Any]]:
        package_path = self.workspace_root / "_dlm_dossier" / "template_adapter_v1" / "adapter.json"
        seed_path = self.workspace_root / "_dlm_dossier" / "template_adapter_seed.json"
        adapter_path = package_path if package_path.is_file() else seed_path
        if not adapter_path.is_file():
            return {}
        raw = adapter_path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        schema = str(payload.get("$schema") or payload.get("schema") or "unknown")
        evidence_roles = copy.deepcopy(payload.get("optional_evidence_roles") or {})
        legacy_optional = ["left_3q", "right_3q", "front_3q", "rear_3q", "assets"]
        self._payloads["iracing.dirt_late_model"] = payload
        self._payload_paths["iracing.dirt_late_model"] = adapter_path
        return {
            "iracing.dirt_late_model": {
                "id": "iracing.dirt_late_model",
                "name": "iRacing Dirt Late Model",
                "version": str(payload.get("package_version") or "1"),
                "adapter_schema": schema,
                "adapter_sha256": hashlib.sha256(raw).hexdigest(),
                "required_views": list(REQUIRED_DLM_ROLES),
                "optional_views": legacy_optional + sorted(evidence_roles),
                "optional_evidence_roles": evidence_roles,
                "capabilities": {
                    "guided_intake": True,
                    "resumable_jobs": True,
                    "qualified_front_assembly": True,
                    "full_nose_inverse": False,
                    "inverse_surface_execution": adapter_path == package_path,
                    "direct_top_execution": adapter_path == package_path and int(payload.get("package_version") or 0) >= 4,
                    "direct_outside_spoiler_execution": adapter_path == package_path and int(payload.get("package_version") or 0) >= 5,
                    "qualified_front_valance_execution": adapter_path == package_path and int(payload.get("package_version") or 0) >= 6,
                    "partial_surface_completeness": adapter_path == package_path and int(payload.get("package_version") or 0) >= 7,
                    "surface_evidence_requests": adapter_path == package_path and int(payload.get("package_version") or 0) >= 8,
                    "surface_evidence_quad_review": adapter_path == package_path and int(payload.get("package_version") or 0) >= 9,
                    "surface_capture_quality": adapter_path == package_path and int(payload.get("package_version") or 0) >= 10,
                    "specialized_surface_readiness": adapter_path == package_path and int(payload.get("package_version") or 0) >= 10,
                },
            }
        }

    def ids(self) -> set[str]:
        return set(self._adapters)

    def list(self) -> list[dict[str, Any]]:
        return [dict(self._adapters[key]) for key in sorted(self._adapters)]

    def get(self, adapter_id: str) -> dict[str, Any]:
        try:
            return dict(self._adapters[adapter_id])
        except KeyError as exc:
            raise ContractError("adapter_id is not registered") from exc

    def payload(self, adapter_id: str) -> dict[str, Any]:
        """Return adapter geometry as an isolated copy for pipeline planning."""

        self.get(adapter_id)
        return copy.deepcopy(self._payloads[adapter_id])

    def payload_path(self, adapter_id: str) -> Path:
        """Return the immutable adapter JSON authority used by the executor."""

        self.get(adapter_id)
        return self._payload_paths[adapter_id]
