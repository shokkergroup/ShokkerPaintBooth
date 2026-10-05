"""Observability helpers for the Shokker Paint Booth Flask servers.

Audit gap (SPB_ALPHA_AUDIT "No observability"): the Python server had no
``sys.excepthook`` and no catch-all Flask error handler, so an uncaught
exception in a background thread or an unexpected exception in a route could
vanish into the void (or leak an internal traceback to the client).

This module is **purely additive and opt-out-safe**:

* Everything is guarded by the ``SHOKKER_OBSERVABILITY`` env flag, which is
  **on by default**. Set ``SHOKKER_OBSERVABILITY=0`` (or ``off``/``no``) to
  disable every hook installed here.
* The crash log is written **local-only** to a rotating file next to the
  server (default ``server_crashes.log``). Nothing is uploaded anywhere.
* Installation never raises: if anything goes wrong wiring a hook up, we log a
  warning and leave the prior behaviour untouched. Importing this module has no
  side effects until one of the ``install_*`` / ``log_*`` functions is called.

Public API
----------
* :func:`observability_enabled`  -- read the opt-out flag.
* :func:`install_excepthook`     -- global ``sys.excepthook`` -> rotating log.
* :func:`install_flask_error_handler` -- ``errorhandler(Exception)`` -> JSON 500.
* :func:`log_startup`            -- one structured startup log line.
* :func:`install_observability`  -- convenience wrapper that does all three.
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows

#: Environment variable that gates every hook in this module. Default ON.
ENV_FLAG = "SHOKKER_OBSERVABILITY"

#: Environment variable to override the crash-log filename/path.
ENV_LOG_PATH = "SHOKKER_CRASH_LOG"

#: Default crash-log filename (written beside the server unless overridden).
DEFAULT_CRASH_LOG = "server_crashes.log"

#: Values (case-insensitive) that count as "false" for the opt-out flag.
_FALSEY = ("0", "false", "no", "off", "n", "f")

# Module-level guards so repeated install calls (e.g. server.py + server_v5.py
# both importing) don't stack duplicate handlers / hooks.
_excepthook_installed = False
_flask_handlers: "set[int]" = set()
_crash_logger: Optional[logging.Logger] = None


def observability_enabled() -> bool:
    """Return ``True`` unless the opt-out flag is explicitly set to a falsey value.

    Default-on: an unset / empty / unrecognised value means enabled.
    """
    raw = os.environ.get(ENV_FLAG)
    if raw is None:
        return True
    return raw.strip().lower() not in _FALSEY


def _resolve_crash_log_path(server_dir: Optional[str]) -> str:
    """Resolve the local rotating crash-log path.

    Order of preference:
      1. ``SHOKKER_CRASH_LOG`` env override (absolute or relative path).
      2. ``<server_dir>/server_crashes.log`` if a server_dir is given.
      3. ``server_crashes.log`` in the current working directory.
    """
    override = os.environ.get(ENV_LOG_PATH)
    if override:
        return os.path.abspath(override)
    if os.environ.get("SPB_NO_LIVE_LINK"):
        try:
            from config import CFG
            return os.path.join(os.path.dirname(CFG.LOG_FILE), DEFAULT_CRASH_LOG)
        except Exception as _spb_ex:
            _spb_swallow('_resolve_crash_log_path@L82', _spb_ex)
    if server_dir:
        return os.path.join(server_dir, DEFAULT_CRASH_LOG)
    return os.path.abspath(DEFAULT_CRASH_LOG)


def get_crash_logger(server_dir: Optional[str] = None) -> Optional[logging.Logger]:
    """Build (once) a dedicated logger that writes to a local rotating file.

    Returns ``None`` if the rotating file handler can't be created (e.g. the
    file is locked by a ghost process) -- callers fall back to stderr/the
    standard logger so a logging failure never masks the original error.
    """
    global _crash_logger
    if _crash_logger is not None:
        return _crash_logger

    crash_logger = logging.getLogger("shokker.crash")
    crash_logger.setLevel(logging.ERROR)
    # Don't double-print through the root logger's stream handler.
    crash_logger.propagate = False

    if not crash_logger.handlers:
        log_path = _resolve_crash_log_path(server_dir)
        try:
            handler = RotatingFileHandler(
                log_path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
            crash_logger.addHandler(handler)
        except Exception:
            # File locked / unwritable: leave the logger handler-less so it
            # falls through to the root logger. Do NOT crash here.
            return None

    _crash_logger = crash_logger
    return _crash_logger


def install_excepthook(
    server_dir: Optional[str] = None,
    fallback_logger: Optional[logging.Logger] = None,
) -> bool:
    """Install a global ``sys.excepthook`` that logs uncaught exceptions.

    Logs the full traceback to the local rotating crash log (and the fallback
    logger if provided). KeyboardInterrupt is passed straight through to the
    original hook so Ctrl-C still works normally. The previously-installed hook
    is always chained after logging so we never swallow another tool's hook.

    Idempotent and no-op when observability is disabled. Returns ``True`` if the
    hook was installed by this call.
    """
    global _excepthook_installed
    if not observability_enabled() or _excepthook_installed:
        return False

    prev_hook = sys.excepthook
    crash_logger = get_crash_logger(server_dir)

    def _hook(exc_type, exc_value, exc_tb):
        # Let Ctrl-C behave normally -- not a crash worth logging loudly.
        if not issubclass(exc_type, KeyboardInterrupt):
            tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            msg = "Uncaught exception (sys.excepthook):\n%s"
            try:
                if crash_logger is not None and crash_logger.handlers:
                    crash_logger.error(msg, tb_text)
                elif fallback_logger is not None:
                    fallback_logger.error(msg, tb_text)
                else:
                    sys.stderr.write("Uncaught exception:\n" + tb_text)
            except Exception:
                # Logging the crash must never itself crash the excepthook.
                try:
                    sys.stderr.write("Uncaught exception (log failed):\n" + tb_text)
                except Exception as _spb_ex:
                    _spb_swallow('_hook@L161', _spb_ex)
        # Chain the previous hook so default reporting still happens.
        try:
            prev_hook(exc_type, exc_value, exc_tb)
        except Exception as _spb_ex:
            _spb_swallow('_hook@L166', _spb_ex)

    try:
        sys.excepthook = _hook
        _excepthook_installed = True
        return True
    except Exception:
        if fallback_logger is not None:
            fallback_logger.warning("Could not install sys.excepthook")
        return False


def install_flask_error_handler(app: Any, logger: Optional[logging.Logger] = None) -> bool:
    """Register a catch-all ``errorhandler(Exception)`` on a Flask ``app``.

    Logs the full traceback server-side and returns a clean JSON 500 to the
    client **without leaking internals** (no traceback / exception string in the
    response body). HTTP exceptions (404, 400, 413, ...) are re-raised so the
    app's existing, more specific handlers still own them.

    Idempotent per app (keyed on ``id(app)``) and a no-op when observability is
    disabled. Returns ``True`` if a handler was registered by this call.
    """
    if not observability_enabled() or app is None:
        return False
    if id(app) in _flask_handlers:
        return False

    log = logger or logging.getLogger("shokker")

    try:
        from flask import jsonify, request, g
        from werkzeug.exceptions import HTTPException
    except Exception:
        if logger is not None:
            log.warning("Flask/werkzeug unavailable; skipping error handler install")
        return False

    @app.errorhandler(Exception)
    def _handle_uncaught(e):  # noqa: ANN001
        # Let Flask's own HTTP error handlers (404/400/413/429/...) take these.
        if isinstance(e, HTTPException):
            return e
        rid = getattr(g, "_rid", None) or "-"
        try:
            path = request.path
        except Exception:
            path = "-"
        log.error(
            "[rid=%s] Uncaught exception on %s: %s\n%s",
            rid, path, e, traceback.format_exc(),
        )
        # Clean, internals-free body.
        return jsonify({
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Check server logs for details.",
            "rid": rid,
        }), 500

    _flask_handlers.add(id(app))
    return True


def log_startup(
    logger: logging.Logger,
    *,
    name: str,
    version: Optional[str] = None,
    engine_version: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a single structured startup log line (key=value pairs).

    Safe to call unconditionally; honours the opt-out flag and never raises.
    """
    if not observability_enabled():
        return
    try:
        fields: Dict[str, Any] = {"event": "startup", "name": name}
        if version is not None:
            fields["version"] = version
        if engine_version is not None:
            fields["engine"] = engine_version
        if host is not None:
            fields["host"] = host
        if port is not None:
            fields["port"] = port
        fields["pid"] = os.getpid()
        fields["python"] = sys.version.split()[0]
        if extra:
            fields.update(extra)
        line = " ".join(f"{k}={v}" for k, v in fields.items())
        logger.info("STARTUP %s", line)
    except Exception as _spb_ex:
        # Startup logging must never block startup.
        _spb_swallow('log_startup@L262', _spb_ex)


def install_observability(
    app: Any = None,
    *,
    logger: Optional[logging.Logger] = None,
    server_dir: Optional[str] = None,
) -> Dict[str, bool]:
    """Convenience wrapper: install the excepthook + Flask handler in one call.

    Returns a dict reporting which hooks were installed this call. No-op (all
    ``False``) when observability is disabled. Never raises.
    """
    result = {"excepthook": False, "flask_handler": False}
    if not observability_enabled():
        return result
    try:
        result["excepthook"] = install_excepthook(
            server_dir=server_dir, fallback_logger=logger
        )
    except Exception as _spb_ex:
        _spb_swallow('install_observability@L285', _spb_ex)
    try:
        result["flask_handler"] = install_flask_error_handler(app, logger=logger)
    except Exception as _spb_ex:
        _spb_swallow('install_observability@L289', _spb_ex)
    return result
