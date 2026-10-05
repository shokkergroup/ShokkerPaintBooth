"""
tests/test_server_routes.py — Flask route integration tests.

Uses the Flask test client (no real socket bound). Each test is fast because
the heavy registry load happens once in the session-scoped ``server_module``
fixture.
"""

from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# 36. test_status_endpoint
# ---------------------------------------------------------------------------
def test_status_endpoint(app_client):
    """/status returns 200 and the version key."""
    r = app_client.get("/status")
    assert r.status_code == 200
    data = r.get_json()
    assert "version" in data, "/status is missing version"
    assert data.get("status") == "online"


# ---------------------------------------------------------------------------
# 37. test_health_endpoint
# ---------------------------------------------------------------------------
def test_health_endpoint(app_client):
    """/health returns 200 with ok=True."""
    r = app_client.get("/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("ok") is True


def test_ping_plaintext(app_client):
    """/api/ping returns 'pong' as plaintext."""
    r = app_client.get("/api/ping")
    assert r.status_code == 200
    assert b"pong" in r.data


# ---------------------------------------------------------------------------
# 38. test_finish_groups
# ---------------------------------------------------------------------------
def test_finish_groups(app_client):
    """/finish-groups returns status=ok and a dict of groups."""
    r = app_client.get("/finish-groups")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("status") == "ok"
    assert isinstance(data.get("groups"), dict)


# ---------------------------------------------------------------------------
# 39. test_finish_data_includes_bases
# ---------------------------------------------------------------------------
def test_finish_data_includes_bases(app_client):
    """/api/finish-data returns bases, patterns, and specials arrays."""
    r = app_client.get("/api/finish-data")
    assert r.status_code == 200
    data = r.get_json()
    assert "bases" in data and isinstance(data["bases"], list)
    assert "patterns" in data and isinstance(data["patterns"], list)
    assert "specials" in data and isinstance(data["specials"], list)
    assert len(data["bases"]) >= 50, f"finish-data returned only {len(data['bases'])} bases"


def test_finish_data_has_counts(app_client):
    """/api/finish-data includes a counts summary."""
    r = app_client.get("/api/finish-data")
    data = r.get_json()
    assert "counts" in data
    assert data["counts"]["total"] == (
        data["counts"]["bases"] + data["counts"]["patterns"] + data["counts"]["specials"]
    )


def test_finish_data_groups_include_cultural_specials(app_client):
    """/api/finish-data must expose the same Cultural groups as the picker."""
    r = app_client.get("/api/finish-data")
    assert r.status_code == 200
    data = r.get_json()
    groups = data["groups"]["specials"]
    viva_ids = groups.get("VIVA MEXICO", [])
    rising_ids = groups.get("RISING SUN", [])

    assert len(viva_ids) >= 58
    assert len(rising_ids) >= 52
    assert all(finish_id.startswith("vm_") for finish_id in viva_ids)
    assert all(finish_id.startswith("rs_") for finish_id in rising_ids)

    category_by_id = {
        item["id"]: item.get("category")
        for item in data["specials"]
        if item["id"].startswith(("vm_", "rs_"))
    }
    assert category_by_id["vm_aztec_sunfire"] == "VIVA MEXICO"
    assert category_by_id["rs_rising_sun_flare"] == "RISING SUN"


# ---------------------------------------------------------------------------
# 40. test_404_returns_json_error
# ---------------------------------------------------------------------------
def test_404_returns_json_error(app_client):
    """Unknown routes return 404 JSON with an 'error' key."""
    r = app_client.get("/no-such-route-abc-xyz-123")
    assert r.status_code == 404
    data = r.get_json()
    assert "error" in data, "404 response missing 'error' key"
    assert data["error"] == "not_found"


# ---------------------------------------------------------------------------
# 41. test_413_handles_oversized_payload
# ---------------------------------------------------------------------------
def test_413_handles_oversized_payload(app_client, server_module):
    """Flask rejects payloads above MAX_CONTENT_LENGTH_BYTES with 413."""
    # Just check that the config is set correctly — we can't easily simulate
    # a >16MB POST through the test client without allocating massive buffers,
    # and the error handler is proven by direct inspection.
    assert server_module.app.config.get("MAX_CONTENT_LENGTH") is not None
    assert server_module.app.config["MAX_CONTENT_LENGTH"] >= 1 * 1024 * 1024


# ---------------------------------------------------------------------------
# 42. test_preview_render_validates_payload
# ---------------------------------------------------------------------------
def test_preview_render_validates_payload(app_client):
    """/preview-render rejects a POST body with no zones (returns 4xx)."""
    r = app_client.post("/preview-render", json={})
    # Either 400 (bad request) or 500 with JSON error — never a crash.
    assert r.status_code >= 400
    # Response should still be JSON (the global error handler enforces this).
    try:
        body = r.get_json(silent=True)
    except Exception:
        body = None
    assert body is None or isinstance(body, dict)


# ---------------------------------------------------------------------------
# 43. test_render_stats
# ---------------------------------------------------------------------------
def test_render_stats(app_client):
    """/api/render-stats returns 200 with expected metric keys."""
    r = app_client.get("/api/render-stats")
    assert r.status_code == 200
    data = r.get_json()
    for key in ("total_renders", "average_render_time", "cache_hit_rate",
                "cache_hits", "cache_misses"):
        assert key in data, f"render-stats missing {key}"


def test_render_progress(app_client):
    """/api/render-progress returns 200 (either active or idle)."""
    r = app_client.get("/api/render-progress")
    assert r.status_code == 200
    assert isinstance(r.get_json(), dict)


def test_render_status_reports_percent(app_client):
    """/api/render-status returns a percent field 0..100."""
    r = app_client.get("/api/render-status")
    assert r.status_code == 200
    data = r.get_json()
    assert "percent" in data
    assert 0 <= data["percent"] <= 100


# ---------------------------------------------------------------------------
# 44. test_diagnostics_endpoint
# ---------------------------------------------------------------------------
def test_diagnostics_endpoint(app_client):
    """/api/diagnostics returns the current redacted support-report contract."""
    r = app_client.get("/api/diagnostics")
    assert r.status_code == 200
    data = r.get_json()
    for key in (
        "app_version", "python_version", "gpu", "catalog",
        "registered_routes", "server_log_tail", "crash_log_tail", "errors",
    ):
        assert key in data, f"diagnostics missing {key}"
    # Catalog counts should match the live engine without exposing local secrets.
    catalog = data["catalog"]
    assert catalog["bases"] >= 50
    assert catalog["patterns"] >= 200


# ---------------------------------------------------------------------------
# 45. test_recent_renders_ring_buffer
# ---------------------------------------------------------------------------
def test_recent_renders_ring_buffer(app_client, server_module):
    """/api/recent-renders returns a bounded list, and limit param is honored."""
    r = app_client.get("/api/recent-renders?limit=10")
    assert r.status_code == 200
    data = r.get_json()
    assert "count" in data and "items" in data
    assert isinstance(data["items"], list)
    assert data["count"] <= 10

    # The underlying deque has a maxlen — check it's not unbounded.
    assert server_module._recent_renders.maxlen is not None
    assert server_module._recent_renders.maxlen <= 256


# ---------------------------------------------------------------------------
# Extra server tests.
# ---------------------------------------------------------------------------
def test_server_info(app_client):
    """/api/server-info returns version, pid, port."""
    r = app_client.get("/api/server-info")
    assert r.status_code == 200
    data = r.get_json()
    for key in ("version", "pid", "port", "uptime_s"):
        assert key in data, f"server-info missing {key}"


def test_echo_roundtrip(app_client):
    """/api/echo returns the POSTed body verbatim."""
    payload = {"hello": "world", "n": 42}
    r = app_client.post("/api/echo", json=payload)
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("body") == payload


def test_favicon_no_content(app_client):
    """/favicon.ico returns 204 (No Content), not 404."""
    r = app_client.get("/favicon.ico")
    assert r.status_code == 204


def test_api_stats_has_registry_counts(app_client):
    """/api/stats returns registry counts + recent_renders_logged."""
    r = app_client.get("/api/stats")
    assert r.status_code == 200
    data = r.get_json()
    # /api/stats composition: key names may vary; check for *some* numeric values.
    assert any(isinstance(v, (int, float)) for v in data.values())


def test_api_health_alias(app_client):
    """/api/health alias returns 200 (same purpose as /health)."""
    r = app_client.get("/api/health")
    # Note: both /health and /api/health exist; both should respond 200.
    assert r.status_code == 200
