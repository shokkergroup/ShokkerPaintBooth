"""Shared filesystem-write policy for verification-mode HTTP routes."""

from __future__ import annotations

import os


def external_write_denial(
    target_path,
    operation: str,
    *,
    owned_root,
    enabled=None,
    logger=None,
):
    """Return a JSON-safe denial for writes outside *owned_root* when enabled.

    ``enabled=None`` reads ``SPB_NO_LIVE_LINK`` at request time so tests and
    verification launches can toggle the mode without changing normal runtime.
    """
    if enabled is None:
        enabled = bool(os.environ.get("SPB_NO_LIVE_LINK"))
    if not enabled:
        return None
    try:
        target = os.path.realpath(os.path.abspath(os.fspath(target_path)))
        root = os.path.realpath(os.path.abspath(os.fspath(owned_root)))
        common = os.path.commonpath((target, root))
        if os.path.normcase(common) == os.path.normcase(root):
            return None
    except (OSError, TypeError, ValueError):
        target = str(target_path)
    if logger is not None:
        logger.warning("Blocked external write operation=%s target=%s", operation, target)
    return {
        "success": False,
        "error": "external_write_disabled",
        "message": "External filesystem writes are disabled for this verification server.",
        "operation": operation,
    }
