"""Transactional deployment of one exact iRacing paint/spec TGA pair.

The public helper in this module deliberately accepts the two source files
explicitly.  It never scans a render directory or copies an arbitrary set of
TGAs, so a successful result always means that the expected paint and spec
names were both validated, staged, committed, and verified.

Two fixed filenames cannot be replaced atomically as a single filesystem
operation.  This module therefore provides the strongest practical contract
for SPB's in-process writers: deployments to the same normalized car folder
are serialized, both files are staged beside the live files, and any failure
after the first replace restores the byte-exact prior pair before returning.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shutil
import threading
import time
from typing import Any, Callable, Mapping
import uuid

from PIL import Image
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


_TARGET_LOCKS: dict[str, threading.RLock] = {}
_TARGET_LOCKS_GUARD = threading.Lock()
_IRACING_ID_RE = re.compile(r"^[0-9]{4,7}$")
_VALID_PAINT_PREFIXES = frozenset({"car", "car_num"})


class PairDeploymentError(RuntimeError):
    """A pair deployment failed without reporting a partial success."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        rollback_error: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.rollback_error = rollback_error


def _normalized_target_key(target_dir: Path) -> str:
    """Return one lock identity for equivalent spellings of a target path."""

    return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(target_dir))))


def _target_lock(target_dir: Path) -> threading.RLock:
    key = _normalized_target_key(target_dir)
    with _TARGET_LOCKS_GUARD:
        lock = _TARGET_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _TARGET_LOCKS[key] = lock
        return lock


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inspect_tga(path: Path, *, require_dimensions: tuple[int, int]) -> dict[str, Any]:
    """Decode and fingerprint a TGA, rejecting empty, corrupt, or wrong-size files."""

    if not path.is_file():
        raise PairDeploymentError(
            f"Required iRacing TGA is missing: {path}",
            code="missing_source",
        )
    byte_count = path.stat().st_size
    if byte_count <= 18:
        raise PairDeploymentError(
            f"Required iRacing TGA is empty or truncated: {path}",
            code="invalid_source",
        )
    try:
        with Image.open(path) as image:
            image_format = str(image.format or "").upper()
            dimensions = tuple(image.size)
            image.load()
    except PairDeploymentError:
        raise
    except Exception as exc:
        raise PairDeploymentError(
            f"Required iRacing TGA cannot be decoded: {path}: {exc}",
            code="invalid_source",
        ) from exc
    if image_format != "TGA":
        raise PairDeploymentError(
            f"Expected a TGA file, got {image_format or 'unknown'}: {path}",
            code="invalid_source",
        )
    if dimensions != require_dimensions:
        raise PairDeploymentError(
            f"iRacing TGA must be {require_dimensions[0]}x{require_dimensions[1]}; "
            f"got {dimensions[0]}x{dimensions[1]}: {path}",
            code="invalid_dimensions",
        )
    return {
        "bytes": byte_count,
        "sha256": _sha256(path),
        "width": dimensions[0],
        "height": dimensions[1],
    }


def _snapshot(path: Path) -> dict[str, Any]:
    """Fingerprint an existing live file without requiring it to be a valid TGA."""

    return {
        "exists": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else None,
        "sha256": _sha256(path) if path.is_file() else None,
    }


def _copy_fsynced(source: Path, destination: Path) -> None:
    """Create one private staged/rollback copy and flush it before commit."""

    with source.open("rb") as src, destination.open("xb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
        dst.flush()
        os.fsync(dst.fileno())


def _replace_with_retries(source: Path, destination: Path, attempts: int = 8) -> None:
    """Replace one staged file, tolerating short Windows viewer/sim locks."""

    for attempt in range(attempts):
        try:
            os.replace(source, destination)
            return
        except OSError:
            if attempt >= attempts - 1:
                raise
            time.sleep(0.05 + attempt * 0.05)


def _assert_same_file(
    actual_path: Path,
    expected: Mapping[str, Any],
    *,
    require_dimensions: tuple[int, int] | None,
) -> dict[str, Any]:
    if require_dimensions is None:
        actual = _snapshot(actual_path)
        if not actual["exists"]:
            raise PairDeploymentError(
                f"Verification target is missing: {actual_path}",
                code="verification_failed",
            )
    else:
        actual = _inspect_tga(actual_path, require_dimensions=require_dimensions)
    if actual.get("bytes") != expected.get("bytes") or actual.get("sha256") != expected.get("sha256"):
        raise PairDeploymentError(
            f"Byte verification failed for {actual_path.name}",
            code="verification_failed",
        )
    return actual


def _cleanup(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError as _spb_ex:
            # A stale private transaction artifact is safer than masking the
            # actual deploy/rollback result. A later deploy uses a new UUID.
            _spb_swallow('_cleanup@L179', _spb_ex)


def _restore_pair(
    live_paths: tuple[Path, Path],
    rollback_paths: tuple[Path, Path],
    old_state: tuple[Mapping[str, Any], Mapping[str, Any]],
) -> None:
    errors: list[str] = []
    for live, rollback, prior in zip(live_paths, rollback_paths, old_state):
        try:
            if prior["exists"]:
                if not rollback.is_file():
                    raise OSError(f"rollback copy missing: {rollback}")
                current = _snapshot(live)
                if not current["exists"] or current.get("bytes") != prior.get("bytes") or current.get("sha256") != prior.get("sha256"):
                    _replace_with_retries(rollback, live)
            else:
                live.unlink(missing_ok=True)
        except OSError as exc:
            errors.append(f"{live.name}: {exc}")

    for live, prior in zip(live_paths, old_state):
        try:
            if prior["exists"]:
                _assert_same_file(live, prior, require_dimensions=None)
            elif live.exists():
                raise OSError("new target remained after rollback")
        except Exception as exc:  # noqa: BLE001 - collect every rollback defect
            errors.append(f"{live.name} verification: {exc}")

    if errors:
        raise PairDeploymentError(
            "Pair rollback could not restore the prior target: " + "; ".join(errors),
            code="rollback_failed",
        )


def deploy_iracing_tga_pair(
    paint_source: str | os.PathLike[str],
    spec_source: str | os.PathLike[str],
    target_dir: str | os.PathLike[str],
    iracing_id: str,
    *,
    paint_prefix: str = "car_num",
    expected_dimensions: tuple[int, int] = (2048, 2048),
    fault_injector: Callable[[str, Mapping[str, str]], None] | None = None,
) -> dict[str, Any]:
    """Install exactly one paint/spec pair, or leave the prior pair unchanged.

    ``fault_injector`` is a deterministic test seam. Production callers should
    omit it. If it raises at any named step, the normal rollback path runs.
    """

    raw_id = str(iracing_id or "").strip()
    if not _IRACING_ID_RE.fullmatch(raw_id):
        raise PairDeploymentError(
            "iracing_id must be 4-7 digits",
            code="invalid_iracing_id",
        )
    if paint_prefix not in _VALID_PAINT_PREFIXES:
        raise PairDeploymentError(
            "paint_prefix must be 'car' or 'car_num'",
            code="invalid_paint_prefix",
        )
    try:
        dimensions = (int(expected_dimensions[0]), int(expected_dimensions[1]))
    except (TypeError, ValueError, IndexError) as exc:
        raise PairDeploymentError(
            "expected_dimensions must be a positive (width, height) pair",
            code="invalid_dimensions",
        ) from exc
    if dimensions[0] <= 0 or dimensions[1] <= 0:
        raise PairDeploymentError(
            "expected_dimensions must be a positive (width, height) pair",
            code="invalid_dimensions",
        )

    paint_source_path = Path(paint_source)
    spec_source_path = Path(spec_source)
    target_path = Path(target_dir)
    paint_name = f"{paint_prefix}_{raw_id}.tga"
    spec_name = f"car_spec_{raw_id}.tga"

    if paint_source_path.name != paint_name:
        raise PairDeploymentError(
            f"Expected paint source named {paint_name}; got {paint_source_path.name}",
            code="unexpected_source_name",
        )
    if spec_source_path.name != spec_name:
        raise PairDeploymentError(
            f"Expected spec source named {spec_name}; got {spec_source_path.name}",
            code="unexpected_source_name",
        )
    try:
        if paint_source_path.resolve(strict=False) == spec_source_path.resolve(strict=False):
            raise PairDeploymentError(
                "Paint and spec sources must be different files",
                code="invalid_source_pair",
            )
    except OSError as exc:
        raise PairDeploymentError(
            f"Could not normalize source paths: {exc}",
            code="invalid_source_pair",
        ) from exc

    # Validate both inputs before creating or changing anything in the target.
    source_meta = (
        _inspect_tga(paint_source_path, require_dimensions=dimensions),
        _inspect_tga(spec_source_path, require_dimensions=dimensions),
    )

    try:
        target_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PairDeploymentError(
            f"Could not create iRacing target directory {target_path}: {exc}",
            code="invalid_target",
        ) from exc
    if not target_path.is_dir():
        raise PairDeploymentError(
            f"iRacing target is not a directory: {target_path}",
            code="invalid_target",
        )

    lock = _target_lock(target_path)
    with lock:
        transaction_id = uuid.uuid4().hex
        live_paths = (target_path / paint_name, target_path / spec_name)
        stage_paths = tuple(
            target_path / f".spb-pair-{transaction_id}-{name}.stage"
            for name in (paint_name, spec_name)
        )
        rollback_paths = tuple(
            target_path / f".spb-pair-{transaction_id}-{name}.rollback"
            for name in (paint_name, spec_name)
        )
        private_paths = [*stage_paths, *rollback_paths]
        hook_context = {
            "target": str(target_path),
            "paint": str(live_paths[0]),
            "spec": str(live_paths[1]),
            "transaction_id": transaction_id,
        }

        def checkpoint(step: str) -> None:
            if fault_injector is not None:
                fault_injector(step, hook_context)

        commit_started = False
        old_state: tuple[Mapping[str, Any], Mapping[str, Any]] | None = None
        try:
            checkpoint("before_stage")
            for source, stage, expected in zip(
                (paint_source_path, spec_source_path), stage_paths, source_meta
            ):
                _copy_fsynced(source, stage)
                _assert_same_file(stage, expected, require_dimensions=dimensions)
            checkpoint("after_stage_verified")

            old_state = (_snapshot(live_paths[0]), _snapshot(live_paths[1]))
            for live, rollback, prior in zip(live_paths, rollback_paths, old_state):
                if prior["exists"]:
                    _copy_fsynced(live, rollback)
                    _assert_same_file(rollback, prior, require_dimensions=None)

            # Preserve SPB's long-standing recoverable ORIGINAL_* contract,
            # but create it inside the same target lock and before either live
            # file changes. The first known pair wins; later installs never
            # overwrite the owner's original snapshot.
            for live, prior in zip(live_paths, old_state):
                original = target_path / f"ORIGINAL_{live.name}"
                if prior["exists"] and not original.exists():
                    original_stage = target_path / f".spb-pair-{transaction_id}-{live.name}.original"
                    private_paths.append(original_stage)
                    _copy_fsynced(live, original_stage)
                    _assert_same_file(original_stage, prior, require_dimensions=None)
                    _replace_with_retries(original_stage, original)
            checkpoint("after_rollback_copies")

            commit_started = True
            _replace_with_retries(stage_paths[0], live_paths[0])
            checkpoint("after_paint_commit")
            _replace_with_retries(stage_paths[1], live_paths[1])
            checkpoint("after_spec_commit")

            verified = tuple(
                _assert_same_file(live, expected, require_dimensions=dimensions)
                for live, expected in zip(live_paths, source_meta)
            )
            checkpoint("after_pair_verified")
            return {
                "success": True,
                "verified": True,
                "deployed": [paint_name, spec_name],
                "files": [
                    {"name": live.name, **metadata}
                    for live, metadata in zip(live_paths, verified)
                ],
                "target": str(target_path).replace("\\", "/"),
                "iracing_id": raw_id,
                "transaction_id": transaction_id,
            }
        except BaseException as exc:
            if commit_started and old_state is not None:
                try:
                    _restore_pair(live_paths, rollback_paths, old_state)
                except BaseException as rollback_exc:
                    raise PairDeploymentError(
                        f"Pair deployment failed and rollback failed: {exc}; {rollback_exc}",
                        code="rollback_failed",
                        rollback_error=rollback_exc,
                    ) from exc
            if isinstance(exc, PairDeploymentError):
                raise
            code = "commit_failed_rolled_back" if commit_started else "staging_failed"
            raise PairDeploymentError(
                f"Pair deployment failed; prior target was preserved: {exc}",
                code=code,
            ) from exc
        finally:
            _cleanup(private_paths)
