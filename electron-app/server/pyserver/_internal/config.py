"""config.py - Single Source of Truth for V5 Configuration.

ONE place to change ports, paths, debug mode, build settings.

Never hardcode ports or paths in ``server_v5.py``, ``server.py``, or .bat files.
Everything reads from here. The module exposes a single :data:`CFG` singleton
that is lazily constructed at import time.

How to use
----------
    >>> from config import CFG
    >>> port = CFG.PORT
    >>> debug = CFG.DEBUG

Environment overrides (highest priority)
----------------------------------------
* ``SHOKKER_PORT=59876``    -- override port (e.g. primary/secondary instances)
* ``SHOKKER_DEV=1``         -- enable debug mode + Flask hot reload
* ``SHOKKER_LOG=DEBUG``     -- verbose logging
* ``SHOKKER_NO_CLEAN=1``    -- skip clean boot (do not kill port / other server);
                              use for a second instance
* ``SHOKKER_EXE_DIR``       -- (frozen builds only) path beside packaged .exe

Cross-module dependencies
-------------------------
* ``server_v5.py``       -- main Flask entry; imports :data:`CFG` for paths/port
* ``server.py``          -- legacy routes re-used by V5; imports :data:`CFG`
* ``shokk_manager.py``   -- resolves library/factory dirs from :data:`CFG`
* ``shokker_engine_v2`` and ``engine/*`` -- read :data:`CFG.OUTPUT_DIR`

The object is intended to be *read-only* after construction; treat it as
effectively immutable. The public API is the attribute surface plus
:meth:`_Config.as_dict`, :func:`validate_config`, :func:`repair_config`,
and the :data:`CFG` singleton.
"""

from __future__ import annotations

import logging
import os
import sys
import json
import threading
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "CFG",
    "CONFIG_MODULE_VERSION",
    "DEFAULT_PORT",
    "DEFAULT_HOST",
    "validate_config",
    "repair_config",
    "normalize_path",
    "is_safe_path",
]

# ---------------------------------------------------------------------------
# Module-level constants (replace magic values scattered through the codebase)
# ---------------------------------------------------------------------------

#: Schema/semantic version for this config module itself (bumped on breaking changes).
CONFIG_MODULE_VERSION: str = "1.2.0"

#: Default port for the primary Flask server instance.
DEFAULT_PORT: int = 59876

#: Default secondary port reserved for dev/second-instance usage.
DEFAULT_SECONDARY_PORT: int = 59877

#: Flask host -- ``0.0.0.0`` binds to all interfaces (LAN accessible).
DEFAULT_HOST: str = "0.0.0.0"

#: Minimum acceptable TCP port for user-overrides.
_MIN_PORT: int = 1024

#: Maximum acceptable TCP port.
_MAX_PORT: int = 65535

#: Environment variable names -- centralised so typos are caught in one place.
_ENV_PORT: str = "SHOKKER_PORT"
_ENV_DEV: str = "SHOKKER_DEV"
_ENV_LOG: str = "SHOKKER_LOG"
_ENV_NO_CLEAN: str = "SHOKKER_NO_CLEAN"
_ENV_EXE_DIR: str = "SHOKKER_EXE_DIR"

_TRUTHY: Tuple[str, ...] = ("1", "true", "yes", "on", "y", "t")

logger = logging.getLogger("shokker.config")
if not logger.handlers:
    # Minimal fallback handler so early errors surface even if server_v5 hasn't
    # yet configured root logging. Downstream basicConfig() still wins.
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)
    logger.propagate = False


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def normalize_path(path: str) -> str:
    """Return a normalised, absolute path suitable for cross-platform use.

    Expands ``~`` and environment variables, resolves relative segments,
    and standardises separators via :func:`os.path.normpath`.

    Args:
        path: A filesystem path; may contain ``~`` or ``$VAR``.

    Returns:
        An absolute, normalised filesystem path.

    Raises:
        TypeError: If ``path`` is not a string.
    """
    if not isinstance(path, str):
        raise TypeError(f"normalize_path expected str, got {type(path).__name__}")
    expanded = os.path.expandvars(os.path.expanduser(path))
    return os.path.normpath(os.path.abspath(expanded))


def is_safe_path(base_dir: str, target: str) -> bool:
    """Return True if ``target`` resolves inside ``base_dir`` (anti-traversal).

    Protects against ``..`` path traversal and symlink escape. Callers should
    use this before serving any user-supplied filename.

    Args:
        base_dir: Trusted directory root.
        target: Path or filename being checked.

    Returns:
        True if ``target`` is within ``base_dir``; False otherwise (or on error).
    """
    try:
        base_abs = os.path.realpath(normalize_path(base_dir))
        target_abs = os.path.realpath(normalize_path(os.path.join(base_dir, target)))
        # os.path.commonpath raises on different drives on Windows -- treat as unsafe.
        return os.path.commonpath([base_abs, target_abs]) == base_abs
    except (ValueError, OSError):
        return False


def _env_bool(name: str, default: bool = False) -> bool:
    """Interpret an env var as a boolean, accepting common truthy strings."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY


def _safe_int(raw: str, *, name: str, default: int) -> int:
    """Parse an env var to int with helpful logging on failure."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning(
            "[config] env %s=%r is not an integer; falling back to %d",
            name, raw, default,
        )
        return default


# ---------------------------------------------------------------------------
# Config object
# ---------------------------------------------------------------------------

class _Config:
    """V5 runtime configuration.

    Read-only after :meth:`__init__` finishes. Attribute access is the public
    API; do not mutate instance attributes at runtime (the helpers here assume
    immutability for caching).
    """

    # ------- SERVER --------------------------------------------------------
    PORT: int = DEFAULT_PORT            # Default: primary port
    PRIMARY_PORT: int = DEFAULT_PORT    # Mirror of PORT -- kept for legacy callers
    SECONDARY_PORT: int = DEFAULT_SECONDARY_PORT
    HOST: str = DEFAULT_HOST

    # ------- DEBUG / DEV ---------------------------------------------------
    DEBUG: bool = False        # Flask auto-reload (SHOKKER_DEV=1)
    THREADED: bool = True      # Always use threaded Flask
    VERBOSE: bool = False      # Extra log output

    # ------- PATHS ---------------------------------------------------------
    ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR: str = os.path.join(ROOT_DIR, "output")
    THUMBNAIL_DIR: str = os.path.join(ROOT_DIR, "thumbnails")  # Pre-rendered swatches
    CONFIG_FILE: str = os.path.join(ROOT_DIR, "shokker_config.json")
    LICENSE_FILE: str = os.path.join(ROOT_DIR, "shokker_license.json")
    HTML_FILE: str = os.path.join(ROOT_DIR, "paint-booth-v2.html")
    LOG_FILE: str = os.path.join(ROOT_DIR, "server_log.txt")

    # ------- SHOKK FILE SYSTEM --------------------------------------------
    SHOKK_LIBRARY_DIR: str = os.path.join(
        os.path.expanduser("~"), "Documents", "Shokker Paint Booth", "SHOKK Library"
    )
    SHOKK_FACTORY_DIR: str = os.path.join(ROOT_DIR, "shokk_factory")

    # ------- PATTERNS FOR REVIEW ------------------------------------------
    # Candidate pattern images go here; app lists them and shows engine-rendered
    # swatches so you can approve/tweak before adding to PATTERNS and registry.
    PATTERN_FOR_REVIEW_DIR: str = os.path.join(ROOT_DIR, "assets", "patterns", "for_review")

    # ------- FEATURE FLAGS (flip False to rollback) -----------------------
    ENABLE_THIRD_BASE_OVERLAY: bool = True   # 3rd Base Overlay layer + per-layer pattern

    # ------- BUILD ---------------------------------------------------------
    VERSION: str = "6.2.0-alpha"
    BUILD_TAG: str = "Boil the Ocean"
    APP_NAME: str = "Shokker Paint Booth V6 Alpha"

    # Internal lock for any future thread-safe mutation (e.g. live config reload).
    _lock: threading.RLock

    def __init__(self) -> None:
        """Build the config, apply env overrides, and ensure runtime dirs exist.

        Directory creation failures are logged but *not* fatal -- this lets the
        server start in read-only environments (e.g. CI) and surface the real
        error later when something actually tries to write there.
        """
        # Use object.__setattr__ so lock exists before env overrides can run.
        object.__setattr__(self, "_lock", threading.RLock())
        self._apply_env_overrides()
        self._ensure_runtime_dirs()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_env_overrides(self) -> None:
        """Apply ``SHOKKER_*`` environment variables over class defaults.

        Environment variables win over class defaults. Invalid values are
        logged and ignored rather than crashing startup.
        """
        if _ENV_PORT in os.environ:
            raw = os.environ[_ENV_PORT]
            port = _safe_int(raw, name=_ENV_PORT, default=DEFAULT_PORT)
            if _MIN_PORT <= port <= _MAX_PORT:
                self.PORT = port
                self.PRIMARY_PORT = port
            else:
                logger.warning(
                    "[config] %s=%d out of range [%d, %d]; using default %d",
                    _ENV_PORT, port, _MIN_PORT, _MAX_PORT, DEFAULT_PORT,
                )

        if _env_bool(_ENV_DEV):
            self.DEBUG = True
            self.VERBOSE = True
            logger.info("[config] DEV MODE - hot reload enabled")

        log_level = os.environ.get(_ENV_LOG, "").upper().strip()
        if log_level == "DEBUG":
            self.VERBOSE = True

    def _ensure_runtime_dirs(self) -> None:
        """Create output/library/factory/review directories if missing.

        We swallow :class:`OSError` with a warning -- callers will surface real
        write-failures later (and a readonly FS shouldn't brick startup).
        """
        for key in ("OUTPUT_DIR", "SHOKK_LIBRARY_DIR", "SHOKK_FACTORY_DIR",
                    "PATTERN_FOR_REVIEW_DIR"):
            path = getattr(self, key)
            try:
                os.makedirs(path, exist_ok=True)
            except OSError as e:
                logger.warning("[config] Could not create %s=%s (%s)", key, path, e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the most useful fields.

        Returns:
            A dict with version, build, port, debug and root path keys.
            Intended for ``/status`` / ``/build-check`` endpoints.
        """
        return {
            "version": self.VERSION,
            "build": self.BUILD_TAG,
            "config_schema": CONFIG_MODULE_VERSION,
            "port": self.PORT,
            "debug": self.DEBUG,
            "verbose": self.VERBOSE,
            "root": self.ROOT_DIR,
            "host": self.HOST,
        }

    def as_public_dict(self) -> Dict[str, Any]:
        """Like :meth:`as_dict` but safe to expose to remote clients.

        Strips filesystem paths that could aid attackers in path-traversal
        attempts. Use this for any endpoint reachable over LAN / WAN.
        """
        d = self.as_dict()
        d.pop("root", None)
        return d

    def describe_paths(self) -> Dict[str, str]:
        """Return all path-typed config keys (for debug / diagnostics)."""
        return {
            "ROOT_DIR": self.ROOT_DIR,
            "OUTPUT_DIR": self.OUTPUT_DIR,
            "THUMBNAIL_DIR": self.THUMBNAIL_DIR,
            "CONFIG_FILE": self.CONFIG_FILE,
            "LICENSE_FILE": self.LICENSE_FILE,
            "HTML_FILE": self.HTML_FILE,
            "LOG_FILE": self.LOG_FILE,
            "SHOKK_LIBRARY_DIR": self.SHOKK_LIBRARY_DIR,
            "SHOKK_FACTORY_DIR": self.SHOKK_FACTORY_DIR,
            "PATTERN_FOR_REVIEW_DIR": self.PATTERN_FOR_REVIEW_DIR,
        }

    def __repr__(self) -> str:
        return (
            f"<ShokkerConfig V{self.VERSION} build={self.BUILD_TAG} "
            f"port={self.PORT} debug={self.DEBUG}>"
        )


# ---------------------------------------------------------------------------
# Schema validation / repair helpers for the *user* config JSON
# (``shokker_config.json`` -- not this module).
# ---------------------------------------------------------------------------

#: Expected structure of ``shokker_config.json`` (key -> (type, default)).
_USER_CONFIG_SCHEMA: Dict[str, Tuple[type, Any]] = {
    "iracing_id": (str, "23371"),
    "car_paths": (dict, {}),
    "live_link_enabled": (bool, False),
    "active_car": ((str, type(None)), None),  # type: ignore[assignment]
    "use_custom_number": (bool, True),
}


def validate_config(data: Any) -> List[str]:
    """Return a list of validation problems for a user-config dict.

    Args:
        data: The parsed JSON object (should be a dict).

    Returns:
        A list of human-readable error strings. Empty list == valid.
    """
    errors: List[str] = []
    if not isinstance(data, dict):
        return [f"config must be a dict, got {type(data).__name__}"]
    for key, (expected_type, _default) in _USER_CONFIG_SCHEMA.items():
        if key not in data:
            # Missing keys are not errors -- they fall back to defaults.
            continue
        value = data[key]
        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                errors.append(
                    f"key {key!r}: expected one of "
                    f"{tuple(t.__name__ for t in expected_type)}, got {type(value).__name__}"
                )
        elif not isinstance(value, expected_type):
            errors.append(
                f"key {key!r}: expected {expected_type.__name__}, got {type(value).__name__}"
            )
    return errors


def repair_config(data: Any) -> Dict[str, Any]:
    """Return a dict with missing/invalid keys replaced by schema defaults.

    This is a non-destructive repair -- unknown keys are preserved (we don't
    know if they came from a newer version or a user customisation).

    Args:
        data: A possibly-malformed config dict (or any object).

    Returns:
        A new dict that passes :func:`validate_config`.
    """
    out: Dict[str, Any] = dict(data) if isinstance(data, dict) else {}
    for key, (expected_type, default) in _USER_CONFIG_SCHEMA.items():
        if key not in out:
            out[key] = default() if callable(default) else default
            continue
        value = out[key]
        expected = expected_type if isinstance(expected_type, tuple) else (expected_type,)
        if not isinstance(value, expected):
            out[key] = default() if callable(default) else default
    return out


# ---------------------------------------------------------------------------
# Module-level singleton -- import this everywhere.
# ---------------------------------------------------------------------------

try:
    CFG: _Config = _Config()
except Exception:  # pragma: no cover - defensive: never let import crash the app
    logger.exception("[config] Failed to construct CFG; using bare defaults")
    CFG = _Config.__new__(_Config)  # type: ignore[assignment]
    object.__setattr__(CFG, "_lock", threading.RLock())
