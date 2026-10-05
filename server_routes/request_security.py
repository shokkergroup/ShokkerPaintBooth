"""Shared loopback request-origin policy for every SPB Flask entry point."""

from __future__ import annotations

from urllib.parse import urlparse

from flask import jsonify, request


def is_same_spb_origin_url(raw_url: str, host_url: str) -> bool:
    """Return whether *raw_url* is this exact loopback origin and port."""
    try:
        supplied = urlparse(raw_url or "")
        expected = urlparse(host_url or "")
        if supplied.scheme not in {"http", "https"}:
            return False
        if (supplied.hostname or "").lower() not in {"127.0.0.1", "localhost", "::1"}:
            return False
        return supplied.scheme == expected.scheme and supplied.port == expected.port
    except (TypeError, ValueError):
        return False


def is_sensitive_local_path(path: str) -> bool:
    """Identify local endpoints whose browser reads expose private app state."""
    return (
        path.startswith((
            "/api/", "/preview/", "/download/", "/recent-renders/", "/swatch/",
        ))
        or path in {
            "/config", "/license", "/recent-renders", "/iracing-cars",
            "/debug-rotation-log", "/status", "/build-check",
        }
    )


def install_spb_origin_guard(app, *, logger=None):
    """Install the same exact-origin guard on a Flask application.

    Headerless desktop/CLI calls remain supported. Browser-supplied Origin or
    Referer values must name this request's scheme and exact loopback port.
    """

    @app.before_request
    def _spb_block_foreign_origin_requests():
        mutating = request.method in ("POST", "PUT", "DELETE", "PATCH")
        sensitive_read = request.method in ("GET", "HEAD") and is_sensitive_local_path(request.path)
        if not mutating and not sensitive_read:
            return None
        for header_name in ("Origin", "Referer"):
            supplied = request.headers.get(header_name, "")
            if supplied and not is_same_spb_origin_url(supplied, request.host_url):
                if logger is not None:
                    logger.warning(
                        "Blocked cross-origin %s %s from %s=%s",
                        request.method,
                        request.path,
                        header_name,
                        supplied,
                    )
                return jsonify({"error": "cross_origin_forbidden"}), 403
        return None

    return _spb_block_foreign_origin_requests
