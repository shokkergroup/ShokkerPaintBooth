def _assert_scrubbed_gear_features(status_payload):
    features = status_payload["capabilities"]["features"]
    assert features["helmet_spec"] is False
    assert features["suit_spec"] is False
    assert features["matching_set"] is False
    assert features["wear_slider"] is True
    assert features["export_zip"] is True
    assert features["live_link"] is True


def test_root_status_reports_current_car_only_feature_contract(app_client):
    response = app_client.get("/status")

    assert response.status_code == 200
    _assert_scrubbed_gear_features(response.get_json())


def test_v5_status_reports_current_car_only_feature_contract():
    import server_v5

    server_v5.app.config["TESTING"] = True
    client = server_v5.app.test_client()

    response = client.get("/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["server_location"].endswith("server_v5.py")
    _assert_scrubbed_gear_features(payload)
