"""Selection and immutable revision history for specialized surface evidence."""

from __future__ import annotations

import copy
from typing import Any

from .contracts import ContractError, validate_reference_id


SELECTION_SCHEMA = "shokk-forge.surface-evidence-selection/v1"


def build_selection(
    *, role: str, reference: dict[str, Any], adapter_sha256: str, previous: dict[str, Any] | None
) -> dict[str, Any]:
    reference_id = validate_reference_id(reference.get("id"))
    reference_sha256 = str(reference.get("sha256") or "")
    if len(reference_sha256) != 64:
        raise ContractError("selected surface evidence is missing its source hash")
    same = bool(
        isinstance(previous, dict)
        and previous.get("reference_id") == reference_id
        and previous.get("reference_sha256") == reference_sha256
        and previous.get("adapter_sha256") == adapter_sha256
    )
    revision = int((previous or {}).get("selection_revision") or 0) + (0 if same else 1)
    return {
        "$schema": SELECTION_SCHEMA,
        "role": role,
        "reference_id": reference_id,
        "reference_sha256": reference_sha256,
        "adapter_sha256": adapter_sha256,
        "selection_revision": max(1, revision),
        "source": "guided_user_capture_attestation/v1",
    }


def archive_review(
    review: dict[str, Any], *, reason: str, replacement_reference_id: str, selection_revision: int
) -> dict[str, Any]:
    archived = copy.deepcopy(review)
    archived["lifecycle"] = {
        "status": "superseded",
        "reason": reason,
        "replacement_reference_id": validate_reference_id(replacement_reference_id),
        "selection_revision": int(selection_revision),
    }
    return archived


def next_review_revision(history: list[dict[str, Any]], role: str) -> int:
    revisions = [
        int(item.get("revision") or 0)
        for item in history
        if isinstance(item, dict) and item.get("role") == role
    ]
    return max(revisions, default=0) + 1
