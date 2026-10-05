def _assert_same_truth(status_payload, build_payload, info_payload):
    from config import CFG

    assert status_payload["version"] == CFG.VERSION
    assert build_payload["version"] == CFG.VERSION
    assert info_payload["version"] == CFG.VERSION

    assert status_payload["build"] == CFG.BUILD_TAG
    assert build_payload["build"] == CFG.BUILD_TAG
    assert info_payload["build"] == CFG.BUILD_TAG

    assert int(status_payload["port"]) == int(build_payload["port"])
    assert int(info_payload["port"]) == int(build_payload["port"])
    assert int(status_payload["pid"]) > 0
    assert int(build_payload["pid"]) > 0
    assert int(info_payload["pid"]) > 0


def test_root_version_truth_surfaces_agree(app_client):
    status_payload = app_client.get("/status").get_json()
    build_payload = app_client.get("/build-check").get_json()
    info_payload = app_client.get("/api/server-info").get_json()

    _assert_same_truth(status_payload, build_payload, info_payload)


def test_v5_version_truth_surfaces_agree():
    import server_v5

    server_v5.app.config["TESTING"] = True
    client = server_v5.app.test_client()

    status_payload = client.get("/status").get_json()
    build_payload = client.get("/build-check").get_json()
    info_payload = client.get("/api/server-info").get_json()

    _assert_same_truth(status_payload, build_payload, info_payload)


def test_client_version_constant_matches_canonical_server_version():
    from pathlib import Path
    from config import CFG

    source = Path("paint-booth-5-api-render.js").read_text(encoding="utf-8")

    assert f"const CLIENT_VERSION = '{CFG.VERSION}';" in source
