# -*- coding: utf-8 -*-
"""Executable identity contract for SPB finishes.

M7 and the Finish Law measure quality inside one rendered finish. They do not
prove that the finish owns a unique construction or that its spec belongs to
that construction. This module supplies the mandatory pre-render contract for
those separate questions.

Owner mandate, 2026-09-02: base designs and spec designs must both be unique,
must not be recolours of another card, and must visibly represent the finish's
name and idea.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "spb-finish-identity/1"
CHANNELS = ("M", "R", "Cc")


@dataclass(frozen=True)
class IdentityVerdict:
    ok: bool
    errors: tuple[str, ...]

    def require(self) -> None:
        if not self.ok:
            raise ValueError("Finish identity contract failed: " + "; ".join(self.errors))


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def validate_identity_contract(contract: Mapping[str, Any], finish_id: str) -> IdentityVerdict:
    """Validate the human-authored identity proof before a render is scored."""
    errors: list[str] = []
    if contract.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA!r}")
    if contract.get("finish_id") != finish_id:
        errors.append(f"finish_id must be {finish_id!r}")

    for field in ("display_name", "promise", "carrier_grammar", "spec_grammar"):
        if len(_text(contract.get(field))) < 12:
            errors.append(f"{field} must be a specific non-trivial statement")

    physics = contract.get("reference_physics")
    if not isinstance(physics, Mapping) or len(_text(physics.get("mechanism"))) < 20:
        errors.append("reference_physics.mechanism must explain the real process")
    sources = physics.get("sources", []) if isinstance(physics, Mapping) else []
    if not isinstance(sources, list) or not any(_text(item) for item in sources):
        errors.append("reference_physics.sources must cite at least one research source")

    native = contract.get("native_scale_px")
    valid_native = (
        isinstance(native, list) and len(native) == 2
        and all(isinstance(v, (int, float)) for v in native)
        and 8 <= float(native[0]) <= float(native[1]) <= 32
    )
    # Explicit owner correction for the reviewed ERA120 lane (17 Sep 2026):
    # readable larger primary forms, with fine subordinate details. The default
    # remains 8..32; a module cannot grant itself an arbitrary scale exception.
    if not valid_native and contract.get("owner_scale_authorization") == "ERA120-20260917-reviewed-concepts":
        evidence_path = Path(__file__).resolve().parents[1] / "docs/finish_audits/era120_2026-09-17/owner_scale_authorization.json"
        if evidence_path.is_file():
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            valid_native = (
                finish_id in evidence.get("allowed_finish_ids", [])
                and isinstance(native, list) and len(native) == 2
                and all(isinstance(v, (int, float)) for v in native)
                and 1 <= float(native[0]) <= float(native[1]) <= evidence["maximum_primary_feature_px"]
                and contract.get("fine_detail_scale_px") == [1, 16]
            )
    if not valid_native:
        errors.append("native_scale_px must be [min,max] entirely inside 8..32")

    marks = contract.get("mark_types")
    mark_names: set[str] = set()
    if not isinstance(marks, list) or len(marks) < 5:
        errors.append("mark_types must contain at least five purposeful feature families")
    else:
        for index, mark in enumerate(marks):
            if not isinstance(mark, Mapping):
                errors.append(f"mark_types[{index}] must be an object")
                continue
            name, role = _text(mark.get("name")), _text(mark.get("role"))
            if len(name) < 3 or len(role) < 8:
                errors.append(f"mark_types[{index}] needs a specific name and role")
            if name in mark_names:
                errors.append(f"duplicate mark type {name!r}")
            mark_names.add(name)

    binding = contract.get("material_binding")
    bound: set[str] = set()
    if not isinstance(binding, Mapping):
        errors.append("material_binding must map M, R and Cc to named paint features")
    else:
        for channel in CHANNELS:
            features = binding.get(channel)
            if not isinstance(features, list) or len(set(features)) < 2:
                errors.append(f"material_binding.{channel} must use at least two feature families")
                continue
            unknown = sorted(set(features) - mark_names)
            if unknown:
                errors.append(f"material_binding.{channel} references unknown marks {unknown}")
            bound.update(features)
    if mark_names and bound != mark_names:
        errors.append("every named paint feature must own at least one M/R/Cc response")

    tiers = contract.get("material_tiers")
    if not isinstance(tiers, list) or len(tiers) < 6 or len(set(map(str, tiers))) < 6:
        errors.append("material_tiers must declare at least six distinct material states")

    neighbors = contract.get("nearest_neighbors")
    if not isinstance(neighbors, list) or len(neighbors) < 2:
        errors.append("nearest_neighbors must name at least two collision risks")
    else:
        for index, neighbor in enumerate(neighbors):
            if not isinstance(neighbor, Mapping):
                errors.append(f"nearest_neighbors[{index}] must be an object")
                continue
            if not _text(neighbor.get("finish_id")) or len(_text(neighbor.get("difference"))) < 12:
                errors.append(f"nearest_neighbors[{index}] needs finish_id and structural difference")

    name_truth = contract.get("name_truth")
    evidence = name_truth.get("visible_evidence", []) if isinstance(name_truth, Mapping) else []
    if not isinstance(evidence, list) or len(evidence) < 3 or not all(len(_text(x)) >= 8 for x in evidence):
        errors.append("name_truth.visible_evidence must list at least three visible proofs")
    if not isinstance(name_truth, Mapping) or name_truth.get("hidden_title_verdict") != "pass":
        errors.append("name_truth.hidden_title_verdict must be 'pass'")

    for key in ("construction_key", "spec_key"):
        value = _text(contract.get(key))
        if len(value) < 12 or value.lower() in {"unique", "custom", "different"}:
            errors.append(f"{key} must identify the actual construction, not claim uniqueness")

    return IdentityVerdict(not errors, tuple(errors))


def contract_from_module(module: Any, finish_id: str) -> Mapping[str, Any]:
    contract = getattr(module, "IDENTITY_CONTRACT", None)
    if not isinstance(contract, Mapping):
        raise ValueError(
            f"{module.__name__} must declare IDENTITY_CONTRACT for {finish_id}; "
            "M7 cannot run before identity is defined"
        )
    validate_identity_contract(contract, finish_id).require()
    return contract


def validate_identity_key_uniqueness(
    contract: Mapping[str, Any], registry_paths: list[Path]
) -> IdentityVerdict:
    """Reject reused carrier/spec identities recorded by prior evidence runs."""
    errors: list[str] = []
    finish_id = contract.get("finish_id")
    for path in registry_paths:
        try:
            other = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if other.get("finish_id") == finish_id:
            continue
        for key in ("construction_key", "spec_key"):
            if other.get(key) == contract.get(key):
                errors.append(
                    f"{key} duplicates {other.get('finish_id')!r} in {path.as_posix()}"
                )
    return IdentityVerdict(not errors, tuple(errors))
