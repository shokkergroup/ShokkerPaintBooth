"""server_v5 must inherit the full server.py route table (boot-critical)."""


def test_server_v5_inherits_core_api_routes():
    import server_v5 as v5

    rules = {str(rule) for rule in v5.app.url_map.iter_rules()}
    required = {
        "/api/custom-finishes",
        "/api/finish-registry-status",
        "/api/default-assets",
        "/license",
        "/check-file",
        "/api/psd-import",
    }
    missing = sorted(required - rules)
    assert not missing, f"server_v5 missing inherited routes: {missing}"
    assert len(rules) >= 80, f"expected full route table, got {len(rules)}"
