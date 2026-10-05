from pathlib import Path
from io import BytesIO


def test_spec_pattern_preview_regenerates_stale_static_png(
    app_client,
    server_module,
    tmp_path,
    monkeypatch,
):
    from PIL import Image

    # spec_light_leak was removed from PATTERN_CATALOG on the 2026-05-24
    # spec-rebuild tick, so the preview route now 404s on it. This test is
    # about cache regeneration, not any specific finish, so use a stable
    # spec pattern that is still present in PATTERN_CATALOG.
    pattern_id = "banded_rows"
    thumb_root = tmp_path / "thumbs_spec_preview_cache"
    stale_dir = thumb_root / "spec_patterns"
    stale_dir.mkdir(parents=True, exist_ok=True)
    stale_path = stale_dir / f"{pattern_id}.png"
    Image.new("RGBA", (194, 64), (255, 0, 255, 255)).save(stale_path)
    stale_bytes = stale_path.read_bytes()

    monkeypatch.setattr(server_module, "THUMBNAIL_DIR", str(thumb_root))

    response = app_client.get(f"/api/spec-pattern-preview/{pattern_id}")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert stale_path.read_bytes() == response.data
    assert response.data != stale_bytes


def test_spec_pattern_visual_preview_uses_square_workbench_style(app_client):
    from PIL import Image

    # spec_light_leak was removed from PATTERN_CATALOG (2026-05-24 rebuild);
    # use a stable still-present spec pattern. This test asserts the square
    # workbench thumbnail style/headers, not a specific finish's look.
    response = app_client.get("/api/spec-pattern-visual-preview/banded_rows?size=96")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert "max-age=86400" in response.headers.get("Cache-Control", "")
    image = Image.open(BytesIO(response.data))
    assert image.size == (96, 96)
    assert image.mode in {"RGB", "RGBA"}
