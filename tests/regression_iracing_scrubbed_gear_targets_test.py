import shutil
import uuid


def _make_iracing_paint_root(tmp_path, name):
    root = tmp_path / f"{name}_{uuid.uuid4().hex}"
    if root.exists():
        shutil.rmtree(root)
    paint_root = root / "Documents" / "iRacing" / "paint"
    paint_root.mkdir(parents=True)
    return root, paint_root


def test_iracing_car_discovery_hides_scrubbed_helmet_and_suit_folders(
    app_client,
    monkeypatch,
    server_module,
    tmp_path,
):
    home_root, paint_root = _make_iracing_paint_root(tmp_path, "iracing_discovery_home")
    for folder in ("dallaraarca", "helmets", "suits", "stockcars2"):
        folder_path = paint_root / folder
        folder_path.mkdir()
        (folder_path / "car_23371.tga").write_bytes(b"fake-tga")

    monkeypatch.setattr(server_module.os.path, "expanduser", lambda _path: str(home_root))

    response = app_client.get("/iracing-cars")

    assert response.status_code == 200
    data = response.get_json()
    names = [car["name"] for car in data["cars"]]
    assert names == ["dallaraarca", "stockcars2"]
    assert data["count"] == 2
    assert "helmets" not in names
    assert "suits" not in names


def test_deploy_to_iracing_rejects_scrubbed_helmet_and_suit_targets_before_copy(
    app_client,
    monkeypatch,
    server_module,
    tmp_path,
):
    home_root, paint_root = _make_iracing_paint_root(tmp_path, "iracing_deploy_home")
    output_root = tmp_path / f"iracing_deploy_output_{uuid.uuid4().hex}"
    if output_root.exists():
        shutil.rmtree(output_root)
    job_dir = output_root / "job_qa-gear-target"
    job_dir.mkdir(parents=True)
    (job_dir / "car_23371.tga").write_bytes(b"fake-paint")

    monkeypatch.setattr(server_module.os.path, "expanduser", lambda _path: str(home_root))
    monkeypatch.setattr(server_module, "OUTPUT_FOLDER", str(output_root))

    for scrubbed_folder in ("helmets", "suits"):
        response = app_client.post(
            "/deploy-to-iracing",
            json={
                "job_id": "qa-gear-target",
                "car_folder": scrubbed_folder,
                "iracing_id": "23371",
            },
        )

        assert response.status_code == 400
        assert "helmet/suit folders are not supported" in response.get_json()["error"]
        assert not (paint_root / scrubbed_folder).exists()

    valid_response = app_client.post(
        "/deploy-to-iracing",
        json={
            "job_id": "qa-gear-target",
            "car_folder": "dallaraarca",
            "iracing_id": "23371",
        },
    )

    assert valid_response.status_code == 200
    assert (paint_root / "dallaraarca" / "car_23371.tga").exists()
