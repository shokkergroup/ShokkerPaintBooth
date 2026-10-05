"""Small, cached runtime-source identity payloads for isolated proof."""

from __future__ import annotations

import hashlib
import json
import os
import re


_SOURCE_HASH_ALGORITHM = (
    "sha256(utf8(concat(role, ':', sha256(file), '\\n') for files in listed order))"
)
_ROLE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def _file_sha256(path) -> str | None:
    try:
        digest = hashlib.sha256()
        with open(path, "rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except (OSError, TypeError, ValueError):
        return None


def _is_within(root: str, candidate: str) -> bool:
    try:
        return os.path.commonpath((root, candidate)) == root
    except (OSError, ValueError):
        return False


def _load_identity_sources(canonical_root, identity_manifest):
    """Load and validate the ordered source list used by every identity tool."""
    root = os.path.realpath(os.path.abspath(os.fspath(canonical_root)))
    manifest_name = os.fspath(identity_manifest)
    manifest_path = os.path.realpath(os.path.abspath(os.path.join(root, manifest_name)))
    if not _is_within(root, manifest_path) or not os.path.isfile(manifest_path):
        raise ValueError("runtime identity manifest is missing or outside canonical root")
    try:
        with open(manifest_path, "r", encoding="utf-8") as source:
            manifest = json.load(source)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("runtime identity manifest is unreadable") from exc
    if not isinstance(manifest, dict):
        raise ValueError("runtime identity manifest must be an object")
    if manifest.get("schema") != 1 or manifest.get("hash") != "sha256":
        raise ValueError("runtime identity manifest schema/hash is unsupported")
    if manifest.get("source_hash_algorithm") != _SOURCE_HASH_ALGORITHM:
        raise ValueError("runtime identity manifest algorithm is unsupported")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("runtime identity manifest files must be a non-empty list")

    seen_roles = set()
    records = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("runtime identity file entry must be an object")
        role = entry.get("role")
        relative = entry.get("path")
        if not isinstance(role, str) or not _ROLE_RE.fullmatch(role) or role in seen_roles:
            raise ValueError(f"invalid or duplicate runtime identity role: {role!r}")
        if not isinstance(relative, str) or not relative or os.path.isabs(relative):
            raise ValueError(f"invalid runtime identity path for role {role}")
        file_path = os.path.realpath(os.path.abspath(os.path.join(root, relative)))
        if not _is_within(root, file_path) or not os.path.isfile(file_path):
            raise ValueError(f"unsafe or missing runtime identity source: {relative}")
        digest = _file_sha256(file_path)
        if digest is None:
            raise ValueError(f"unreadable runtime identity source: {relative}")
        seen_roles.add(role)
        records.append({
            "role": role,
            "path": relative.replace("\\", "/"),
            "sha256": digest,
            "_absolute_path": file_path,
        })

    if not {"server", "launcher"}.issubset(seen_roles):
        raise ValueError("runtime identity manifest requires server and launcher roles")
    return root, manifest_path, manifest, records


def build_runtime_identity(
    *,
    canonical_root,
    server_path,
    launcher_path,
    version,
    port,
    started_at,
    external_writes_disabled,
    identity_manifest="runtime_identity_manifest.json",
) -> dict:
    """Hash the manifest's ordered sources once and return proof metadata."""
    root, manifest_path, manifest, records = _load_identity_sources(
        canonical_root, identity_manifest
    )
    by_role = {record["role"]: record for record in records}
    expected_paths = {"server": server_path, "launcher": launcher_path}
    for role, expected in expected_paths.items():
        expected_path = os.path.realpath(os.path.abspath(os.fspath(expected)))
        if by_role[role]["_absolute_path"] != expected_path:
            raise ValueError(f"runtime identity {role} path disagrees with manifest")

    public_records = [
        {key: record[key] for key in ("role", "path", "sha256")}
        for record in records
    ]
    composite_input = "".join(
        f"{record['role']}:{record['sha256']}\n" for record in records
    ).encode("utf-8")
    composite = hashlib.sha256(composite_input).hexdigest()
    return {
        "canonical_root": root,
        "source_hash": composite,
        "source_hash_manifest": os.path.relpath(manifest_path, root).replace("\\", "/"),
        "source_hash_algorithm": manifest["source_hash_algorithm"],
        "source_hash_files": public_records,
        "server_hash": by_role["server"]["sha256"],
        "launcher_hash": by_role["launcher"]["sha256"],
        "pid": os.getpid(),
        "started_at": float(started_at),
        "version": str(version),
        "port": int(port),
        "external_writes_disabled": bool(external_writes_disabled),
    }
