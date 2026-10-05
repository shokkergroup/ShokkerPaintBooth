#!/usr/bin/env python3
"""Fail-closed human-quality release lock for all Fractured Wilds IDs.

Delivery/census/hash gates prove that code and thumbnails arrived; they cannot
prove that the owner accepted the art.  This lock requires a separate explicit
review manifest and never infers acceptance from M7, performance, uniqueness,
or any other mechanical metric.

SPB-WILDS WR-RELEASE-QUALITY-1, 2026-08-24.
"""
from __future__ import annotations

import argparse
import ast
import copy
import functools
import hashlib
import inspect
import json
import math
import re
import sys
from pathlib import Path
from typing import Mapping, Sequence

from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "spb-wilds-quality-release/2"
EVIDENCE_SCHEMA = "spb-wilds-quality-evidence/1"
BUYER_PNG_METADATA_KEY = "spb_wilds_quality_evidence"
DEFAULT_MANIFEST = Path(
    "_wilds_rejection_work/release_quality/wilds_110_owner_review_manifest.json"
)
REQUIRED_EVIDENCE = (
    "local_feature_scale",
    "literal_ab",
    "separate_m_r_cc",
    "motif_spec_collision",
    "buyer_96x48",
    "m7",
    "native_2048_perf",
)
SHA256_RE = re.compile(r"[0-9a-f]{64}")
EVIDENCE_SEMANTIC_FIELDS = {
    "local_feature_scale": ("native_min_px", "native_max_px", "mark_count"),
    "literal_ab": ("literal_a", "literal_b", "fractured_flip_pass"),
    "separate_m_r_cc": ("channels", "separate_authorship"),
    "motif_spec_collision": ("motif_pass", "spec_pass", "whole_app_pass"),
    "buyer_96x48": ("width", "height", "topology_readable"),
    "m7": ("score",),
    "native_2048_perf": ("width", "height", "seconds"),
}
REGISTRY_BINDING_FIELDS = (
    "module",
    "qualname",
    "source_path",
    "source_sha256",
    "body_sha256",
    "owner_logic_sha256",
)

# These are low-level, reusable rendering primitives rather than a finish's
# owner-authored composition.  They remain part of the recursive logic hash,
# but sharing them does not make two otherwise dedicated renderers aliases.
SHARED_PRIMITIVE_MODULES = frozenset({
    "engine.paint_v2.fractured_math",
    "engine.spec_sculpt.fracture",
})


class QualityReleaseBlocked(ValueError):
    """Raised whenever the explicit owner-quality release contract is absent."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_bound_file(root: Path, value: object, label: str) -> tuple[Path, str]:
    if not isinstance(value, str) or not value.strip():
        raise QualityReleaseBlocked(f"{label}: path must be a non-empty project-relative string")
    relative = Path(value)
    if relative.is_absolute():
        raise QualityReleaseBlocked(f"{label}: absolute evidence/source paths are forbidden")
    root = root.resolve()
    resolved = (root / relative).resolve()
    try:
        portable = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise QualityReleaseBlocked(f"{label}: path escapes project root: {value!r}") from exc
    if not resolved.is_file():
        raise QualityReleaseBlocked(f"{label}: bound file is missing: {portable}")
    return resolved, portable


def _verify_hash(path: Path, claimed: object, label: str) -> str:
    if not isinstance(claimed, str) or SHA256_RE.fullmatch(claimed) is None:
        raise QualityReleaseBlocked(f"{label}: sha256 must be 64 lowercase hex characters")
    actual = _sha256(path)
    if actual != claimed:
        raise QualityReleaseBlocked(
            f"{label}: sha256 mismatch; manifest={claimed}, current={actual}"
        )
    return actual


def _registry_entry_callables(entry: object, label: str) -> tuple[object, object]:
    if isinstance(entry, (tuple, list)) and len(entry) >= 2:
        return entry[0], entry[1]
    if isinstance(entry, dict):
        return entry.get("spec_fn"), entry.get("paint_fn")
    raise QualityReleaseBlocked(
        f"{label}: final registry entry must expose spec_fn and paint_fn"
    )


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _source_node_for_function(
    function: object,
    *,
    root: Path,
    label: str,
) -> tuple[Path, str, ast.FunctionDef | ast.AsyncFunctionDef]:
    if isinstance(function, functools.partial):
        raise QualityReleaseBlocked(f"{label}: functools.partial registry callables are forbidden")
    if not inspect.isfunction(function):
        raise QualityReleaseBlocked(f"{label}: registry callable must be a Python function")
    if function.__name__ == "<lambda>":
        raise QualityReleaseBlocked(f"{label}: lambda registry callables are forbidden")
    if inspect.iscoroutinefunction(function):
        raise QualityReleaseBlocked(f"{label}: async registry callables are forbidden")
    if "<locals>" in function.__qualname__:
        raise QualityReleaseBlocked(f"{label}: local/factory registry callables are forbidden")
    if function.__closure__:
        raise QualityReleaseBlocked(f"{label}: closure registry callables are forbidden")
    if function.__qualname__ != function.__name__:
        raise QualityReleaseBlocked(
            f"{label}: registry callable must be a dedicated module-level function"
        )
    if (
        function.__code__.co_name != function.__name__
        or function.__code__.co_qualname != function.__qualname__
    ):
        raise QualityReleaseBlocked(
            f"{label}: runtime code identity does not match callable name/qualname"
        )

    source_name = inspect.getsourcefile(function) or function.__code__.co_filename
    if not source_name:
        raise QualityReleaseBlocked(f"{label}: registry callable has no inspectable source file")
    source_path = Path(source_name).resolve()
    root = root.resolve()
    try:
        portable = source_path.relative_to(root).as_posix()
    except ValueError as exc:
        raise QualityReleaseBlocked(
            f"{label}: registry callable source escapes project root: {source_path}"
        ) from exc
    if source_path.suffix.lower() != ".py" or not source_path.is_file():
        raise QualityReleaseBlocked(f"{label}: registry callable source is not a project Python file")
    try:
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        raise QualityReleaseBlocked(f"{label}: source is not parseable Python: {exc}") from exc
    matches = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function.__name__
    ]
    if len(matches) != 1:
        raise QualityReleaseBlocked(
            f"{label}: source must contain exactly one module-level {function.__name__!r}"
        )
    node = matches[0]
    start_line = min(
        [node.lineno, *(decorator.lineno for decorator in node.decorator_list)]
    )
    if not start_line <= function.__code__.co_firstlineno <= (node.end_lineno or node.lineno):
        raise QualityReleaseBlocked(
            f"{label}: runtime code line does not match the bound source definition"
        )
    return source_path, portable, node


def _normalised_function_node(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    normalised = copy.deepcopy(node)
    normalised.name = "__spb_registry_callable__"
    normalised.decorator_list = []
    normalised.body = _strip_docstring(normalised.body)
    return normalised


def _ast_sha256(node: ast.AST) -> str:
    payload = ast.dump(node, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _resolve_call_target(expression: ast.expr, namespace: Mapping[str, object]) -> object | None:
    if isinstance(expression, ast.Name):
        return namespace.get(expression.id)
    if not isinstance(expression, ast.Attribute):
        return None
    parts: list[str] = []
    current: ast.expr = expression
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name) or current.id not in namespace:
        return None
    target = namespace[current.id]
    try:
        for part in reversed(parts):
            target = getattr(target, part)
    except (AttributeError, TypeError):
        return None
    return target


def _project_function(
    target: object,
    *,
    root: Path,
) -> object | None:
    candidate = target
    if not inspect.isfunction(candidate) and hasattr(candidate, "__wrapped__"):
        try:
            candidate = inspect.unwrap(candidate)
        except (TypeError, ValueError):
            return None
    if not inspect.isfunction(candidate):
        return None
    source_name = inspect.getsourcefile(candidate) or candidate.__code__.co_filename
    if not source_name:
        return None
    try:
        Path(source_name).resolve().relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


class _OwnerCallNormaliser(ast.NodeTransformer):
    def __init__(self, replace):
        self._replace = replace

    def visit_Call(self, node: ast.Call):  # noqa: N802 - ast visitor API
        replacement = self._replace(node.func)
        node = self.generic_visit(node)
        if replacement is not None:
            node.func = ast.copy_location(ast.Constant(replacement), node.func)
        return node


def _callable_fingerprint(
    function: object,
    *,
    root: Path,
    label: str,
    cache: dict[int, dict] | None = None,
    stack: set[int] | None = None,
) -> dict:
    cache = {} if cache is None else cache
    stack = set() if stack is None else stack
    key = id(function)
    if key in cache:
        return cache[key]

    source_path, portable, node = _source_node_for_function(
        function, root=root, label=label,
    )
    normalised = _normalised_function_node(node)
    body_sha256 = _ast_sha256(normalised)
    if key in stack:
        return {
            "body_sha256": body_sha256,
            "owner_logic_sha256": hashlib.sha256(
                f"recursive:{body_sha256}".encode("ascii")
            ).hexdigest(),
            "direct_project_callees": (),
            "thin": False,
        }

    stack.add(key)
    direct_callees: dict[int, dict] = {}

    def replace_call(expression: ast.expr) -> str | None:
        target = _resolve_call_target(expression, function.__globals__)
        target = _project_function(target, root=root)
        if target is None:
            return None
        if id(target) == key:
            return f"__spb_recursive__:{body_sha256}"
        child = _callable_fingerprint(
            target,
            root=root,
            label=f"{label} dependency {target.__module__}.{target.__qualname__}",
            cache=cache,
            stack=stack,
        )
        direct_callees[id(target)] = {
            "module": target.__module__,
            "qualname": target.__qualname__,
            "body_sha256": child["body_sha256"],
            "owner_logic_sha256": child["owner_logic_sha256"],
            "shared_primitive": target.__module__ in SHARED_PRIMITIVE_MODULES,
        }
        return f"__spb_project_callee__:{child['owner_logic_sha256']}"

    owner_node = _OwnerCallNormaliser(replace_call).visit(copy.deepcopy(normalised))
    ast.fix_missing_locations(owner_node)
    owner_logic_sha256 = _ast_sha256(owner_node)
    stack.remove(key)
    result = {
        "module": function.__module__,
        "qualname": function.__qualname__,
        "source_path": portable,
        "source_sha256": _sha256(source_path),
        "body_sha256": body_sha256,
        "owner_logic_sha256": owner_logic_sha256,
        "direct_project_callees": tuple(direct_callees.values()),
        "thin": len(_strip_docstring(node.body)) == 1
        and isinstance(_strip_docstring(node.body)[0], (ast.Return, ast.Expr))
        and isinstance(_strip_docstring(node.body)[0].value, ast.Call),
    }
    cache[key] = result
    return result


def describe_registry_callable(
    function: object,
    *,
    root: Path = ROOT,
    label: str = "registry callable",
) -> dict:
    """Return the exact manifest binding for one actual final-registry callable."""
    fingerprint = _callable_fingerprint(function, root=Path(root), label=label)
    return {field: fingerprint[field] for field in REGISTRY_BINDING_FIELDS}


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise QualityReleaseBlocked(f"{label}: must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise QualityReleaseBlocked(f"{label}: must be finite")
    return result


def _validate_evidence_semantics(
    fid: str,
    kind: str,
    binding: dict,
    *,
    origin: str = "binding",
) -> None:
    label = f"{fid}.{kind}.{origin}"
    if binding.get("id") != fid:
        raise QualityReleaseBlocked(f"{label}: evidence id must bind exactly {fid!r}")
    if binding.get("passed") is not True:
        raise QualityReleaseBlocked(f"{label}: passed must be explicit true")

    if kind == "local_feature_scale":
        if binding.get("native_min_px") != 8 or binding.get("native_max_px") != 32:
            raise QualityReleaseBlocked(f"{label}: must bind the exact 8--32 native-px doctrine")
        mark_count = _number(binding.get("mark_count"), f"{label}.mark_count")
        if mark_count < 5 or not mark_count.is_integer():
            raise QualityReleaseBlocked(f"{label}: fewer than five causal mark families")
    elif kind == "literal_ab":
        if binding.get("literal_a") is not True or binding.get("literal_b") is not True:
            raise QualityReleaseBlocked(f"{label}: literal A and B must both be explicit true")
        if binding.get("fractured_flip_pass") is not True:
            raise QualityReleaseBlocked(f"{label}: Fractured A/B flip is not explicitly passed")
    elif kind == "separate_m_r_cc":
        channels = binding.get("channels")
        if channels != ["M", "R", "Cc"]:
            raise QualityReleaseBlocked(f"{label}: channels must be exactly M, R and Cc")
        if binding.get("separate_authorship") is not True:
            raise QualityReleaseBlocked(f"{label}: separate M/R/Cc authorship is not explicit")
    elif kind == "motif_spec_collision":
        for field in ("motif_pass", "spec_pass", "whole_app_pass"):
            if binding.get(field) is not True:
                raise QualityReleaseBlocked(f"{label}: {field} must be explicit true")
    elif kind == "buyer_96x48":
        if binding.get("width") != 96 or binding.get("height") != 48:
            raise QualityReleaseBlocked(f"{label}: evidence must be the actual 96x48 buyer footprint")
        if binding.get("topology_readable") is not True:
            raise QualityReleaseBlocked(f"{label}: buyer topology readability is not explicit")
    elif kind == "m7":
        score = _number(binding.get("score"), f"{label}.score")
        if not 85.0 <= score <= 100.0:
            raise QualityReleaseBlocked(
                f"{label}: M7 {score:g} must be within owner ship-bar range 85..100"
            )
    elif kind == "native_2048_perf":
        if binding.get("width") != 2048 or binding.get("height") != 2048:
            raise QualityReleaseBlocked(f"{label}: performance evidence must be native 2048x2048")
        seconds = _number(binding.get("seconds"), f"{label}.seconds")
        if not 0.0 < seconds <= 3.0:
            raise QualityReleaseBlocked(f"{label}: native render {seconds:g}s exceeds 3s or is invalid")


def _read_json_evidence(path: Path, label: str) -> dict:
    if path.suffix.lower() != ".json":
        raise QualityReleaseBlocked(f"{label}: evidence artifact must be a JSON file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualityReleaseBlocked(f"{label}: evidence artifact is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise QualityReleaseBlocked(f"{label}: evidence artifact must contain a JSON object")
    return payload


def _read_buyer_png_evidence(path: Path, label: str) -> dict:
    if path.suffix.lower() != ".png":
        raise QualityReleaseBlocked(f"{label}: buyer evidence artifact must be an actual PNG")
    try:
        with Image.open(path) as image:
            if image.format != "PNG":
                raise QualityReleaseBlocked(
                    f"{label}: buyer evidence artifact is not PNG data"
                )
            metadata = image.info.get(BUYER_PNG_METADATA_KEY)
            image.load()  # Decode the complete pixel raster; a header-only claim is insufficient.
            decoded_size = image.size
    except QualityReleaseBlocked:
        raise
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        raise QualityReleaseBlocked(
            f"{label}: buyer evidence artifact cannot be decoded as PNG: {exc}"
        ) from exc
    if decoded_size != (96, 48):
        raise QualityReleaseBlocked(
            f"{label}: decoded buyer PNG is {decoded_size[0]}x{decoded_size[1]}, not literal 96x48"
        )
    if not isinstance(metadata, str) or not metadata.strip():
        raise QualityReleaseBlocked(
            f"{label}: buyer PNG lacks embedded {BUYER_PNG_METADATA_KEY!r} assertions"
        )
    try:
        payload = json.loads(metadata)
    except json.JSONDecodeError as exc:
        raise QualityReleaseBlocked(
            f"{label}: buyer PNG evidence assertions are invalid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise QualityReleaseBlocked(
            f"{label}: buyer PNG evidence assertions must be a JSON object"
        )
    return payload


def _semantic_values_match(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        left_number = float(left)
        right_number = float(right)
        return (
            math.isfinite(left_number)
            and math.isfinite(right_number)
            and math.isclose(left_number, right_number, rel_tol=0.0, abs_tol=1e-9)
        )
    return left == right


def _validate_bound_artifact(
    fid: str,
    kind: str,
    binding: dict,
    path: Path,
) -> dict:
    """Parse an evidence artifact and require independent matching assertions."""
    label = f"{fid}.{kind}.artifact"
    payload = (
        _read_buyer_png_evidence(path, label)
        if kind == "buyer_96x48"
        else _read_json_evidence(path, label)
    )
    if payload.get("schema") != EVIDENCE_SCHEMA:
        raise QualityReleaseBlocked(
            f"{label}: artifact schema must be exactly {EVIDENCE_SCHEMA!r}"
        )
    if payload.get("kind") != kind:
        raise QualityReleaseBlocked(f"{label}: artifact kind must bind exactly {kind!r}")
    _validate_evidence_semantics(fid, kind, payload, origin="artifact")
    for field in EVIDENCE_SEMANTIC_FIELDS[kind]:
        if field not in payload:
            raise QualityReleaseBlocked(f"{label}: artifact omits semantic field {field!r}")
        if not _semantic_values_match(payload[field], binding.get(field)):
            raise QualityReleaseBlocked(
                f"{label}: artifact field {field!r}={payload[field]!r} does not match "
                f"binding value {binding.get(field)!r}"
            )
    return payload


def _validate_row(
    row: object,
    *,
    root: Path,
    registry: Mapping[str, object],
    evidence_paths: dict[str, str],
    evidence_hashes: dict[str, str],
    callable_owners: dict[int, str],
    body_owners: dict[str, str],
    logic_owners: dict[str, str],
    thin_callee_owners: dict[str, str],
    callable_cache: dict[int, dict],
) -> dict:
    if not isinstance(row, dict) or not isinstance(row.get("id"), str):
        raise QualityReleaseBlocked("each review row must be an object with a string id")
    fid = row["id"]
    if row.get("owner_accepted") is not True:
        raise QualityReleaseBlocked(
            f"{fid}: owner_accepted must be explicit true; metrics never confer acceptance"
        )
    # A declaration may remain in older manifests for readability, but it is
    # never trusted: production_wired below is derived from the actual object
    # currently stored in the final registry.
    if "production_wired" in row and row.get("production_wired") is not True:
        raise QualityReleaseBlocked(f"{fid}: production_wired declaration contradicts registry")
    if fid not in registry:
        raise QualityReleaseBlocked(f"{fid}: absent from the supplied final registry")
    spec_fn, paint_fn = _registry_entry_callables(registry[fid], f"{fid}.registry")
    if spec_fn is paint_fn:
        raise QualityReleaseBlocked(f"{fid}: spec and paint reuse the same callable object")

    registry_binding = row.get("registry")
    if not isinstance(registry_binding, dict) or set(registry_binding) != {"spec", "paint"}:
        raise QualityReleaseBlocked(
            f"{fid}: registry binding must contain exactly explicit spec and paint objects"
        )

    actual_bindings: dict[str, dict] = {}
    source_paths: set[str] = set()
    for role, function in (("spec", spec_fn), ("paint", paint_fn)):
        label = f"{fid}.registry.{role}"
        claimed = registry_binding[role]
        if not isinstance(claimed, dict) or set(claimed) != set(REGISTRY_BINDING_FIELDS):
            raise QualityReleaseBlocked(
                f"{label}: binding fields must be exactly {list(REGISTRY_BINDING_FIELDS)!r}"
            )
        fingerprint = _callable_fingerprint(
            function,
            root=root,
            label=label,
            cache=callable_cache,
        )
        actual = {field: fingerprint[field] for field in REGISTRY_BINDING_FIELDS}
        for field in REGISTRY_BINDING_FIELDS:
            claimed_value = claimed.get(field)
            if field.endswith("sha256"):
                if not isinstance(claimed_value, str) or SHA256_RE.fullmatch(claimed_value) is None:
                    raise QualityReleaseBlocked(
                        f"{label}.{field}: must be 64 lowercase hex characters"
                    )
            if claimed_value != actual[field]:
                raise QualityReleaseBlocked(
                    f"{label}.{field}: manifest={claimed_value!r}, actual={actual[field]!r}"
                )

        owner_label = f"{fid}.{role}"
        object_key = id(function)
        prior_object = callable_owners.get(object_key)
        if prior_object is not None:
            raise QualityReleaseBlocked(
                f"shared registry callable object: {owner_label} reuses {prior_object}"
            )
        callable_owners[object_key] = owner_label

        prior_body = body_owners.get(fingerprint["body_sha256"])
        if prior_body is not None:
            raise QualityReleaseBlocked(
                f"identical normalized registry body: {owner_label} duplicates {prior_body}"
            )
        body_owners[fingerprint["body_sha256"]] = owner_label

        prior_logic = logic_owners.get(fingerprint["owner_logic_sha256"])
        if prior_logic is not None:
            raise QualityReleaseBlocked(
                f"identical owner-logic fingerprint: {owner_label} duplicates {prior_logic}"
            )
        logic_owners[fingerprint["owner_logic_sha256"]] = owner_label

        if fingerprint["thin"]:
            for callee in fingerprint["direct_project_callees"]:
                if callee["shared_primitive"]:
                    continue
                callee_key = callee["owner_logic_sha256"]
                prior_callee = thin_callee_owners.get(callee_key)
                if prior_callee is not None and not prior_callee.startswith(f"{fid}."):
                    raise QualityReleaseBlocked(
                        f"shared non-allowlisted composer: {owner_label} and {prior_callee} "
                        f"delegate to {callee['module']}.{callee['qualname']}"
                    )
                thin_callee_owners[callee_key] = owner_label

        actual_bindings[role] = actual
        source_paths.add(actual["source_path"])

    evidence = row.get("evidence")
    if not isinstance(evidence, dict):
        raise QualityReleaseBlocked(f"{fid}: evidence bindings are missing")
    actual_kinds = set(evidence)
    required_kinds = set(REQUIRED_EVIDENCE)
    if actual_kinds != required_kinds:
        raise QualityReleaseBlocked(
            f"{fid}: evidence keys mismatch; missing={sorted(required_kinds - actual_kinds)}, "
            f"unexpected={sorted(actual_kinds - required_kinds)}"
        )

    parsed_evidence: dict[str, dict] = {}
    for kind in REQUIRED_EVIDENCE:
        binding = evidence[kind]
        if not isinstance(binding, dict):
            raise QualityReleaseBlocked(f"{fid}.{kind}: binding must be an object")
        _validate_evidence_semantics(fid, kind, binding)
        path, portable = _resolve_bound_file(root, binding.get("path"), f"{fid}.{kind}")
        digest = _verify_hash(path, binding.get("sha256"), f"{fid}.{kind}")
        path_key = portable.casefold()
        if path_key in evidence_paths:
            raise QualityReleaseBlocked(
                f"shared evidence binding: {fid}.{kind} reuses {portable} from {evidence_paths[path_key]}"
            )
        if digest in evidence_hashes:
            raise QualityReleaseBlocked(
                f"shared evidence content: {fid}.{kind} duplicates {evidence_hashes[digest]}"
            )
        evidence_paths[path_key] = f"{fid}.{kind}"
        evidence_hashes[digest] = f"{fid}.{kind}"
        parsed_evidence[kind] = _validate_bound_artifact(fid, kind, binding, path)

    return {
        "id": fid,
        "owner_accepted": True,
        "production_wired": True,
        "registry": actual_bindings,
        "source_paths": sorted(source_paths, key=str.casefold),
        "evidence_count": len(REQUIRED_EVIDENCE),
        "evidence_hashes": {
            kind: evidence[kind]["sha256"] for kind in REQUIRED_EVIDENCE
        },
        "buyer_96x48_decoded": True,
        "m7": float(parsed_evidence["m7"]["score"]),
        "native_2048_seconds": float(parsed_evidence["native_2048_perf"]["seconds"]),
    }


def validate_quality_release_manifest(
    manifest: str | Path,
    expected_ids: Sequence[str],
    *,
    root: Path = ROOT,
    registry: Mapping[str, object] | None = None,
) -> dict:
    """Validate owner review against an injected census and actual final registry."""
    expected = [str(fid) for fid in expected_ids]
    if not expected:
        raise QualityReleaseBlocked("expected Wilds ID set is empty")
    if len(expected) != len(set(expected)):
        raise QualityReleaseBlocked("expected Wilds ID set contains duplicates")
    if registry is None:
        raise QualityReleaseBlocked(
            "actual final registry is required; manifest assertions cannot prove production wiring"
        )

    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = Path(root) / manifest_path
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise QualityReleaseBlocked(
            f"quality review manifest missing: {manifest_path}; owner accepted 0/{len(expected)}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise QualityReleaseBlocked(f"quality review manifest is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        schema = payload.get("schema") if isinstance(payload, dict) else type(payload).__name__
        raise QualityReleaseBlocked(f"unsupported quality review manifest schema: {schema!r}")
    if payload.get("scope") != "fractured_wilds":
        raise QualityReleaseBlocked("quality review manifest scope must be 'fractured_wilds'")
    rows = payload.get("finishes")
    if not isinstance(rows, list):
        raise QualityReleaseBlocked("quality review manifest finishes must be a list")

    ids = [row.get("id") if isinstance(row, dict) else None for row in rows]
    if any(not isinstance(fid, str) for fid in ids):
        raise QualityReleaseBlocked("every quality review row must have a string id")
    duplicates = sorted({fid for fid in ids if fid is not None and ids.count(fid) > 1})
    if duplicates:
        raise QualityReleaseBlocked(f"quality review manifest contains duplicate IDs: {duplicates}")
    actual = {fid for fid in ids if isinstance(fid, str)}
    expected_set = set(expected)
    missing = sorted(expected_set - actual)
    unexpected = sorted(actual - expected_set)
    if missing or unexpected or len(rows) != len(expected):
        accepted = sum(
            1 for row in rows
            if isinstance(row, dict) and row.get("owner_accepted") is True
        )
        raise QualityReleaseBlocked(
            f"quality review manifest census mismatch: missing={missing}, "
            f"unexpected={unexpected}, rows={len(rows)}/{len(expected)}, "
            f"owner accepted={accepted}/{len(expected)}"
        )

    evidence_paths: dict[str, str] = {}
    evidence_hashes: dict[str, str] = {}
    callable_owners: dict[int, str] = {}
    body_owners: dict[str, str] = {}
    logic_owners: dict[str, str] = {}
    thin_callee_owners: dict[str, str] = {}
    callable_cache: dict[int, dict] = {}
    validated = [
        _validate_row(
            row,
            root=Path(root),
            registry=registry,
            evidence_paths=evidence_paths,
            evidence_hashes=evidence_hashes,
            callable_owners=callable_owners,
            body_owners=body_owners,
            logic_owners=logic_owners,
            thin_callee_owners=thin_callee_owners,
            callable_cache=callable_cache,
        )
        for row in rows
    ]
    manifest_sha256 = _sha256(manifest_path)
    review_material = {
        "manifest_sha256": manifest_sha256,
        "finishes": [
            {
                "id": row["id"],
                "registry": row["registry"],
                "evidence_hashes": row["evidence_hashes"],
            }
            for row in sorted(validated, key=lambda item: item["id"])
        ],
    }
    review_bundle_sha256 = hashlib.sha256(
        json.dumps(
            review_material, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema": SCHEMA,
        "status": "quality_release_lock_open",
        "manifest": str(manifest_path),
        "expected_ids": len(expected),
        "enumerated_ids": len(validated),
        "owner_accepted": len(validated),
        "production_wired": len(validated),
        "manifest_sha256": manifest_sha256,
        "review_bundle_sha256": review_bundle_sha256,
        "unique_source_bindings": len(callable_owners),
        "unique_registry_callable_bindings": len(callable_owners),
        "unique_registry_body_fingerprints": len(body_owners),
        "source_paths": sorted(
            {
                source_path
                for row in validated
                for source_path in row["source_paths"]
            },
            key=str.casefold,
        ),
        "unique_evidence_bindings": len(evidence_paths),
        "decoded_buyer_96x48_artifacts": sum(
            1 for row in validated if row["buyer_96x48_decoded"]
        ),
        "m7_minimum": min(row["m7"] for row in validated),
        "native_2048_seconds_maximum": max(
            row["native_2048_seconds"] for row in validated
        ),
        "acceptance_inferred_from_metrics": False,
    }


def validate_current_wilds_quality_release(
    manifest: str | Path = DEFAULT_MANIFEST,
) -> dict:
    from engine.registry import MONOLITHIC_REGISTRY
    from scripts.spb_wilds_release_gate import (
        EXPECTED_WILDS_TOTAL,
        canonical_wilds_110,
    )

    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    if not manifest_path.is_file():
        raise QualityReleaseBlocked(
            f"quality review manifest missing: {manifest_path}; "
            f"owner accepted 0/{EXPECTED_WILDS_TOTAL}"
        )
    _lanes, ids = canonical_wilds_110(MONOLITHIC_REGISTRY)
    return validate_quality_release_manifest(
        manifest_path,
        ids,
        registry=MONOLITHIC_REGISTRY,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = validate_current_wilds_quality_release(args.manifest)
    except (ImportError, KeyError, OSError, TypeError, QualityReleaseBlocked) as exc:
        if args.json:
            print(json.dumps({
                "schema": SCHEMA,
                "status": "quality_release_blocked",
                "owner_accepted": 0,
                "error": str(exc),
            }, indent=2))
        else:
            print(f"BLOCKED: {exc}")
        return 1
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            "PASS: Wilds quality release lock open; "
            f"{report['owner_accepted']}/{report['expected_ids']} owner accepted, "
            f"{report['production_wired']}/{report['expected_ids']} production wired"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
