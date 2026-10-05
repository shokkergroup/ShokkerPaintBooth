"""Adapter-declared optional evidence requests for incomplete physical surfaces.

The service never guesses that a generic view can stand in for a requested
physical face.  Each template adapter declares its roles and correction
triggers; this module only evaluates those data contracts.
"""

from __future__ import annotations

from typing import Any


SCHEMA = "shokk-forge.surface-evidence-requests/v1"


def _matches(correction: dict[str, Any], trigger: dict[str, Any]) -> bool:
    if trigger.get("reason") and correction.get("reason") != trigger["reason"]:
        return False
    if trigger.get("scope") and correction.get("scope") != trigger["scope"]:
        return False
    needle = str(trigger.get("remaining_scope_contains") or "")
    if needle and needle not in str(correction.get("remaining_scope") or ""):
        return False
    field = str(trigger.get("field_contains") or "")
    if field and field not in (correction.get("fields") or []):
        return False
    return True


def _reconcile_row(
    row: dict[str, Any],
    inputs: list[dict[str, Any]],
    reviews: dict[str, Any] | None = None,
    selections: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result = dict(row)
    role = result["role"]
    matching = [item for item in inputs if item.get("role") == role]
    unique = [item for item in matching if not item.get("duplicate_of")]
    admissible = [item for item in unique if (item.get("capture_quality") or {}).get("admissible") is not False]
    capture_rejected = [item for item in unique if (item.get("capture_quality") or {}).get("admissible") is False]
    duplicates = [item for item in matching if item.get("duplicate_of")]
    threshold = float(result.get("minimum_confidence") or 0.0)
    selection = (selections or {}).get(role)
    selected = next(
        (
            item
            for item in admissible
            if isinstance(selection, dict)
            and selection.get("$schema") == "shokk-forge.surface-evidence-selection/v1"
            and selection.get("role") == role
            and selection.get("reference_id") == item.get("id")
            and selection.get("reference_sha256") == item.get("sha256")
        ),
        None,
    )
    best = selected or max(admissible, key=lambda item: float(item.get("role_confidence") or 0.0), default=None)
    confidence = float((best or {}).get("role_confidence") or 0.0)
    if best is not None and confidence >= threshold:
        status = "qualified"
    elif best is not None:
        status = "low_confidence"
    elif capture_rejected:
        status = "capture_rejected"
    elif duplicates:
        status = "duplicate"
    else:
        status = "requested"
    review = (reviews or {}).get(role)
    review_matches = bool(
        isinstance(review, dict)
        and review.get("$schema") == "shokk-forge.surface-evidence-review/v1"
        and review.get("role") == role
        and review.get("reference_id") == (best or {}).get("id")
        and review.get("reference_sha256") == (best or {}).get("sha256")
        and review.get("user_confirmed") is True
    )
    review_status = "locked" if status != "qualified" else ("confirmed" if review_matches else "required")
    candidates = [
        item
        for item in admissible
        if item.get("id") != (best or {}).get("id")
        and item.get("role_source") != "guided_user_capture_attestation/v1"
    ]
    replacement = candidates[-1] if candidates else None
    role_history = [item for item in (history or []) if isinstance(item, dict) and item.get("role") == role]
    result.update(
        {
            "status": status,
            "received_reference_count": len(matching),
            "unique_reference_count": len(unique),
            "duplicate_reference_count": len(duplicates),
            "capture_rejected_count": len(capture_rejected),
            "qualified_reference_id": (best or {}).get("id"),
            "confidence": round(confidence, 6),
            "duplicate_of": duplicates[0].get("duplicate_of") if duplicates and not unique else None,
            "qualified": status == "qualified",
            "review_status": review_status,
            "review_ready": status == "qualified",
            "surface_review": review if review_matches else None,
            "selected_reference_id": (best or {}).get("id") if selected is not None else None,
            "selection_revision": int((selection or {}).get("selection_revision") or 0) if selected is not None else 0,
            "replacement_candidate_reference_id": (replacement or {}).get("id"),
            "replacement_candidate_confidence": round(float((replacement or {}).get("role_confidence") or 0.0), 6),
            "replacement_candidate_count": len(candidates),
            "review_revision_count": len(role_history) + (1 if review_matches else 0),
            "superseded_review_count": len(role_history),
            "capture_quality": (best or {}).get("capture_quality"),
            "replacement_candidate_capture_quality": (replacement or {}).get("capture_quality"),
            "latest_capture_rejection": (capture_rejected[-1] if capture_rejected else {}).get("capture_quality"),
        }
    )
    return result


def reconcile_evidence_requests(
    requests: list[dict[str, Any]],
    inputs: list[dict[str, Any]],
    reviews: dict[str, Any] | None = None,
    selections: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Refresh persisted request state after resumable reference uploads."""

    return [_reconcile_row(row, inputs, reviews, selections, history) for row in requests]


def build_evidence_requests(
    adapter: dict[str, Any],
    inputs: list[dict[str, Any]],
    corrections: list[dict[str, Any]],
    existing: list[dict[str, Any]] | None = None,
    reviews: dict[str, Any] | None = None,
    selections: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create deterministic requests from adapter data and pipeline corrections."""

    prior = {row.get("role"): row for row in (existing or []) if row.get("role")}
    rows: list[dict[str, Any]] = []
    for role, spec in sorted((adapter.get("optional_evidence_roles") or {}).items()):
        matched = next(
            (
                correction
                for correction in corrections
                for trigger in spec.get("request_triggers", [])
                if _matches(correction, trigger)
            ),
            None,
        )
        if matched is None and role not in prior:
            continue
        row = {
            "$schema": "shokk-forge.surface-evidence-request/v1",
            "role": role,
            "surface": spec.get("surface"),
            "physical_scope": spec.get("physical_scope"),
            "request_reason": (matched or {}).get("reason") or prior[role].get("request_reason"),
            "capture_guidance": spec.get("capture_guidance"),
            "minimum_confidence": float(spec.get("minimum_confidence") or 0.0),
            "requires_user_attestation": bool(spec.get("requires_user_attestation")),
            "review_contract": spec.get("review_contract"),
            "capture_quality_contract": spec.get("capture_quality_contract"),
            "prohibited_substitute_roles": list(spec.get("prohibited_substitute_roles") or []),
            "substitute_roles_present": sorted(
                {
                    item.get("role")
                    for item in inputs
                    if item.get("role") in set(spec.get("prohibited_substitute_roles") or [])
                }
            ),
            "substitution_allowed": False,
        }
        rows.append(_reconcile_row(row, inputs, reviews, selections, history))
    return {
        "$schema": SCHEMA,
        "requests": rows,
        "summary": {
            "request_count": len(rows),
            "qualified_count": sum(row["qualified"] for row in rows),
            "received_count": sum(row["received_reference_count"] > 0 for row in rows),
            "duplicate_count": sum(row["duplicate_reference_count"] for row in rows),
            "outstanding_count": sum(not row["qualified"] for row in rows),
            "unsafe_substitutions_accepted": 0,
            "review_required_count": sum(row["review_status"] == "required" for row in rows),
            "review_confirmed_count": sum(row["review_status"] == "confirmed" for row in rows),
            "replacement_candidate_count": sum(row["replacement_candidate_count"] for row in rows),
            "superseded_review_count": sum(row["superseded_review_count"] for row in rows),
            "capture_rejected_count": sum(row["capture_rejected_count"] for row in rows),
        },
    }
