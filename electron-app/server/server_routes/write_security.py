"""Shared filesystem-write policy for verification-mode HTTP routes."""

from __future__ import annotations

import os


# [SPB orchestrator 2026-10-10] Lane test servers in the dev tree (any port but the
# owner's live 59876; Electron and START_SERVER.bat pin 59876) never write into
# Documents\iRacing\paint. Lane renders overwrote the owner's real car_23371 files
# three times on 2026-10-10 (03:35, 04:37, 05:35) despite a written rule.
# Opt out for one server: SPB_ALLOW_IRACING_WRITES=1.
def _dev_lane_server():
    if os.environ.get("SPB_ALLOW_IRACING_WRITES"):
        return False
    port = (os.environ.get("SHOKKER_PORT") or "").strip()
    if not port or port == "59876":
        return False
    return os.path.isdir(os.path.join(os.getcwd(), "_easy_claude_work"))


def _is_iracing_paint_path(target_path):
    try:
        p = os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(target_path))))
    except (OSError, TypeError, ValueError):
        p = os.path.normcase(str(target_path))
    p = p.replace("/", "\\")
    return "\\iracing\\paint" in p


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
        if _dev_lane_server() and _is_iracing_paint_path(target_path):
            if logger is not None:
                logger.warning("Lane server: blocked write into the iRacing paint folder operation=%s target=%s", operation, target_path)
            return {
                "success": False,
                "error": "external_write_disabled",
                "message": "This test server may not write into the iRacing paint folder.",
                "operation": operation,
            }
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
