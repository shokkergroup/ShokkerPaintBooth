"""One-click "Report a Problem" diagnostics endpoint for Shokker Paint Booth.

This module powers the user-facing *Report a Problem* button: a NON-technical
user who hits a bug can fetch a single, copy-pasteable support payload that
contains everything the owner needs to debug a failure that happened on the
*user's* machine (e.g. the SHOKK THE WORLD per-variant 500 in shokk-drop.html
that the owner can never see because it lives only in the user's local log).

GET /api/diagnostics returns a JSON support report:
    app_version, python_version, platform/OS, server start time + uptime,
    registered-route count, GPU status, catalog counts, and LOG TAILS
    (last ~300 lines of server_log.txt + last ~60 lines of server_crashes.log).

HARD PRIVACY RULES (enforced here):
  * We NEVER read or return ``spb-license-secrets.json``, the license key, the
    AES key, the license secret, or any password hash. License status is
    surfaced ONLY as a boolean (``licensed: true/false``).
  * Every line of every log tail is run through a redactor that blanks the
    value of anything that looks secret (``secret`` / ``api_key`` / ``password``
    / ``token`` / ``key`` assignments, and long opaque key-like tokens) with
    ``[REDACTED]`` before it leaves the process.

ROBUSTNESS: the whole handler is wrapped in try/except so the diagnostics
endpoint itself NEVER 500s. On a partial failure it returns HTTP 200 with the
fields it *could* gather plus a non-empty ``errors`` list describing what
failed. This matters because the endpoint exists precisely to debug a machine
that is already misbehaving.
"""

from __future__ import annotations

import os
import platform
import re
import sys
import time

from flask import jsonify
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows

# --------------------------------------------------------------------------
# Redaction
# --------------------------------------------------------------------------

# Keys whose right-hand value must be blanked when they appear as
# ``key = value`` / ``key: value`` / ``"key": "value"`` in a log line.
_SECRET_KEY_WORDS = (
    "secret",
    "api_key",
    "apikey",
    "password",
    "passwd",
    "pwd",
    "token",
    "license_key",
    "licensekey",
    "aes_key",
    "aeskey",
    "private_key",
    "privatekey",
    "auth",
    "authorization",
    "bearer",
    "hash",
    "salt",
    "credential",
)

# Match ``<secretword> <sep> <value>`` where sep is = or : (optionally quoted),
# capturing everything up to the secret word + separator so we can keep it and
# replace only the value. Case-insensitive.
_KV_SECRET_RE = re.compile(
    r"(?i)([\"']?(?:" + "|".join(re.escape(w) for w in _SECRET_KEY_WORDS) + r")[\"']?\s*[:=]\s*)"
    r"([\"']?)([^\s\"',;}{]+)([\"']?)"
)

# A bare ``Bearer <token>`` style header value anywhere in the line.
_BEARER_RE = re.compile(r"(?i)\b(bearer\s+)([A-Za-z0-9._\-]{8,})")

# Long opaque key-like blobs: 32+ chars of base64/hex-ish content with no
# spaces. Catches raw AES keys / license blobs that leak without a label.
_LONG_BLOB_RE = re.compile(r"\b([A-Za-z0-9+/=_\-]{32,})\b")

# Things that look like a SHOKKER license key: SHOKKER-XXXX-XXXX-XXXX.
_LICENSE_KEY_RE = re.compile(r"(?i)\bSHOKKER-[A-Z0-9]{2,}(?:-[A-Z0-9]{2,}){2,}\b")

_REDACTED = "[REDACTED]"

# A blob is only redacted if it actually looks high-entropy (mixed classes or
# clearly hex/base64). Plain words / file paths shouldn't be nuked, so we keep
# a small allowlist of obviously-safe long tokens.
_SAFE_LONG_TOKEN_RE = re.compile(r"(?i)^(?:[a-z_]+|[0-9]+)$")


def _looks_secret_blob(token: str) -> bool:
    """Heuristic: True if ``token`` resembles an opaque secret, not a word/path."""
    if len(token) < 32:
        return False
    if _SAFE_LONG_TOKEN_RE.match(token):
        return False
    # Path-like or version-like strings are not secrets.
    if "/" in token or "\\" in token or token.count(".") >= 2:
        return False
    has_upper = any(c.isupper() for c in token)
    has_lower = any(c.islower() for c in token)
    has_digit = any(c.isdigit() for c in token)
    classes = sum((has_upper, has_lower, has_digit))
    # hex-only long strings are also suspicious (AES keys, hashes).
    is_hexish = bool(re.fullmatch(r"[0-9a-fA-F]+", token)) and len(token) >= 32
    return classes >= 2 or is_hexish


def redact_secrets(text: str) -> str:
    """Return ``text`` with secret-looking values replaced by ``[REDACTED]``.

    Defensive: any failure leaves the *original* line out entirely rather than
    risk leaking it, by returning a fully-redacted placeholder.
    """
    if not text:
        return text
    try:
        out = _KV_SECRET_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{_REDACTED}{m.group(4)}", text)
        out = _BEARER_RE.sub(lambda m: f"{m.group(1)}{_REDACTED}", out)
        out = _LICENSE_KEY_RE.sub(_REDACTED, out)
        out = _LONG_BLOB_RE.sub(
            lambda m: _REDACTED if _looks_secret_blob(m.group(1)) else m.group(1),
            out,
        )
        return out
    except Exception:
        # Never let a redaction bug leak a raw secret line.
        return _REDACTED


# --------------------------------------------------------------------------
# Log tailing
# --------------------------------------------------------------------------

# Cap how many bytes we read off the tail so a giant log can't blow up memory
# or response time. 1.5 MB comfortably covers a few hundred lines.
_TAIL_READ_BYTES = 1_500_000


def _tail_lines(path: str, max_lines: int):
    """Return ``(lines, error)``: the last ``max_lines`` REDACTED lines of a file.

    Reads only the trailing chunk of the file. Tolerant of a missing file
    (returns ``([], None)``), unreadable file (returns ``([], "<reason>")``),
    and binary junk (decoded with ``errors='replace'``).
    """
    try:
        if not path or not os.path.isfile(path):
            return [], None
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            if size > _TAIL_READ_BYTES:
                fh.seek(size - _TAIL_READ_BYTES)
                # Drop the partial first line after seeking mid-file.
                fh.readline()
            raw = fh.read()
        decoded = raw.decode("utf-8", errors="replace")
        lines = decoded.splitlines()
        tail = lines[-max_lines:] if max_lines and len(lines) > max_lines else lines
        return [redact_secrets(line) for line in tail], None
    except Exception as exc:  # pragma: no cover - defensive
        return [], f"{type(exc).__name__}: {exc}"


def _first_existing(*paths):
    """Return the first path that exists on disk, else the first non-empty path."""
    fallback = None
    for p in paths:
        if not p:
            continue
        if fallback is None:
            fallback = p
        if os.path.isfile(p):
            return p
    return fallback


# --------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------

def register_diagnostics_report_routes(
    app,
    *,
    app_root_getter,
    version: str = "unknown",
    engine_version: str = "unknown",
    build_id: str = "unknown",
    engine_getter=None,
    gpu_info_func=None,
    license_status_getter=None,
    server_start_time_getter=None,
    server_log_path_getter=None,
    crash_log_path_getter=None,
    recent_errors_getter=None,
    logger=None,
) -> None:
    """Register the GET /api/diagnostics support-report endpoint.

    Args:
        app: Flask app to attach the route to.
        app_root_getter: ``() -> str`` returning the app root dir; log paths are
            resolved relative to it when explicit path getters aren't supplied.
        version: App version string (pass ``config.CFG.VERSION``).
        engine_version: Engine identifier string.
        build_id: Build/family marker string.
        engine_getter: Optional ``() -> engine`` for catalog counts.
        gpu_info_func: Optional ``() -> dict`` GPU status.
        license_status_getter: Optional ``() -> bool`` — TRUE if licensed/active.
            Only the boolean is ever surfaced; the key itself is never read here.
        server_start_time_getter: Optional ``() -> float`` epoch start time.
        server_log_path_getter: Optional ``() -> str`` path to server_log.txt.
        crash_log_path_getter: Optional ``() -> str`` path to server_crashes.log.
        recent_errors_getter: Optional ``() -> list`` recent in-memory errors.
        logger: Optional logger for internal warnings.
    """

    def _log_warn(msg):
        if logger is not None:
            try:
                logger.warning(msg)
            except Exception as _spb_ex:
                _spb_swallow('_log_warn@L225', _spb_ex)

    @app.route("/api/diagnostics", methods=["GET"])
    def api_diagnostics_report():
        """One-click support report. Designed to NEVER 500."""
        errors = []

        # --- app root (used to resolve log paths) ----------------------
        app_root = None
        try:
            app_root = app_root_getter() if app_root_getter is not None else None
        except Exception as exc:
            errors.append(f"app_root: {type(exc).__name__}: {exc}")

        # --- python / platform (cheap, almost never fails) -------------
        python_version = None
        os_block = {}
        try:
            python_version = sys.version.split()[0]
        except Exception as exc:
            errors.append(f"python_version: {exc}")
        try:
            os_block = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "platform": platform.platform(),
                "python_implementation": platform.python_implementation(),
            }
        except Exception as exc:
            errors.append(f"platform: {exc}")

        # --- server timing ---------------------------------------------
        now = time.time()
        server_start_time = None
        server_start_iso = None
        uptime_s = None
        try:
            if server_start_time_getter is not None:
                server_start_time = float(server_start_time_getter())
                uptime_s = int(now - server_start_time)
                server_start_iso = time.strftime(
                    "%Y-%m-%dT%H:%M:%S", time.localtime(server_start_time)
                )
        except Exception as exc:
            errors.append(f"uptime: {type(exc).__name__}: {exc}")

        # --- registered route count ------------------------------------
        registered_routes = None
        try:
            registered_routes = sum(1 for _ in app.url_map.iter_rules())
        except Exception as exc:
            errors.append(f"routes: {type(exc).__name__}: {exc}")

        # --- gpu --------------------------------------------------------
        gpu = None
        try:
            if gpu_info_func is not None:
                gpu = gpu_info_func()
        except Exception as exc:
            errors.append(f"gpu: {type(exc).__name__}: {exc}")

        # --- license status (BOOLEAN ONLY — never the key) -------------
        licensed = None
        try:
            if license_status_getter is not None:
                licensed = bool(license_status_getter())
        except Exception as exc:
            errors.append(f"license: {type(exc).__name__}: {exc}")

        # --- catalog counts (cheap len() over registries) --------------
        catalog = {}
        try:
            engine = engine_getter() if engine_getter is not None else None
            if engine is not None:
                catalog = {
                    "bases": len(getattr(engine, "BASE_REGISTRY", {}) or {}),
                    "patterns": len(getattr(engine, "PATTERN_REGISTRY", {}) or {}),
                    "monolithics": len(getattr(engine, "MONOLITHIC_REGISTRY", {}) or {}),
                }
                # Spec patterns live in engine.spec_patterns.PATTERN_CATALOG, a
                # 30k-line module. Only count it if it's ALREADY imported so the
                # diagnostics call stays cheap and never forces a heavy import.
                spec_mod = sys.modules.get("engine.spec_patterns")
                if spec_mod is not None:
                    catalog["specs"] = len(getattr(spec_mod, "PATTERN_CATALOG", {}) or {})
        except Exception as exc:
            errors.append(f"catalog: {type(exc).__name__}: {exc}")

        # --- resolve log paths -----------------------------------------
        server_log_path = None
        crash_log_path = None
        try:
            if server_log_path_getter is not None:
                server_log_path = server_log_path_getter()
            elif app_root:
                server_log_path = os.path.join(app_root, "server_log.txt")
        except Exception as exc:
            errors.append(f"server_log_path: {type(exc).__name__}: {exc}")
        try:
            if crash_log_path_getter is not None:
                crash_log_path = crash_log_path_getter()
            elif app_root:
                # SHOKKER_CRASH_LOG override mirrors observability._resolve_crash_log_path.
                crash_log_path = os.environ.get("SHOKKER_CRASH_LOG") or os.path.join(
                    app_root, "server_crashes.log"
                )
        except Exception as exc:
            errors.append(f"crash_log_path: {type(exc).__name__}: {exc}")

        # --- log tails (REDACTED) --------------------------------------
        server_log_tail, slog_err = _tail_lines(server_log_path, 300)
        if slog_err:
            errors.append(f"server_log_tail: {slog_err}")
        crash_log_tail, clog_err = _tail_lines(crash_log_path, 60)
        if clog_err:
            errors.append(f"crash_log_tail: {clog_err}")

        # --- recent in-memory errors (already short; redact too) -------
        recent_errors = []
        try:
            if recent_errors_getter is not None:
                raw_recent = recent_errors_getter() or []
                for item in raw_recent:
                    if isinstance(item, dict):
                        safe = dict(item)
                        if "message" in safe and isinstance(safe["message"], str):
                            safe["message"] = redact_secrets(safe["message"])
                        recent_errors.append(safe)
                    else:
                        recent_errors.append(redact_secrets(str(item)))
        except Exception as exc:
            errors.append(f"recent_errors: {type(exc).__name__}: {exc}")

        payload = {
            "ok": len(errors) == 0,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)),
            "app_version": version,
            "engine_version": engine_version,
            "build_id": build_id,
            "python_version": python_version,
            "os": os_block,
            "pid": os.getpid(),
            "server_start_time": server_start_iso,
            "uptime_seconds": uptime_s,
            "registered_routes": registered_routes,
            "gpu": gpu,
            "licensed": licensed,
            "catalog": catalog,
            "log_paths": {
                "server_log": server_log_path,
                "crash_log": crash_log_path,
            },
            "server_log_tail": server_log_tail,
            "crash_log_tail": crash_log_tail,
            "recent_errors": recent_errors,
            "errors": errors,
        }

        try:
            return jsonify(payload)
        except Exception as exc:  # pragma: no cover - last-ditch
            _log_warn(f"[/api/diagnostics] jsonify failed: {exc}")
            return jsonify({
                "ok": False,
                "app_version": version,
                "errors": [f"serialization: {type(exc).__name__}: {exc}"],
            })
