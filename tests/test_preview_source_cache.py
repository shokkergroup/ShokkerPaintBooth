from __future__ import annotations

import base64
import io
import os
from pathlib import Path

import numpy as np
from PIL import Image

from server_routes.preview_source_cache import PreviewSourceCache, PreviewSourceError


ROOT = Path(__file__).resolve().parents[1]


def _png_data_url(color=(20, 40, 60)) -> tuple[str, bytes]:
    out = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(out, "PNG")
    raw = out.getvalue()
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii"), raw


def test_client_preview_keeps_live_scale_and_token_recovery_contract():
    canvas = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
    assert "const LIVE_PREVIEW_MAX_SCALE = 0.5;" in canvas
    assert "const PREVIEW_SETTLE_DEBOUNCE_MS = 140;" in canvas
    assert "body.paint_source_token = _previewPaintSourceMemo.token;" in canvas
    assert "data.code === 'preview_source_missing'" in canvas


def test_preview_source_cache_reuses_content_and_enforces_lru_bounds():
    cache = PreviewSourceCache(max_bytes=1024 * 1024, max_items=2, max_item_bytes=4096)
    first_url, first_raw = _png_data_url((1, 2, 3))
    first = cache.remember_data_url(first_url)
    duplicate = cache.remember_data_url(first_url)
    assert duplicate.token == first.token
    assert cache.resolve(first.token).payload == first_raw

    second = cache.remember_data_url(_png_data_url((4, 5, 6))[0])
    cache.resolve(first.token)  # first is now most recently used
    third = cache.remember_data_url(_png_data_url((7, 8, 9))[0])
    assert cache.resolve(second.token) is None
    assert cache.resolve(first.token) is not None
    assert cache.resolve(third.token) is not None
    assert cache.stats()["items"] == 2


def test_preview_source_cache_rejects_non_png_and_oversize_payloads():
    cache = PreviewSourceCache(max_item_bytes=16)
    invalid = "data:image/png;base64," + base64.b64encode(b"not a png").decode("ascii")
    try:
        cache.remember_data_url(invalid)
    except PreviewSourceError as exc:
        assert "PNG" in str(exc)
    else:
        raise AssertionError("non-PNG source was accepted")

    oversized_raw = b"\x89PNG\r\n\x1a\n" + (b"x" * 32)
    oversized = "data:image/png;base64," + base64.b64encode(oversized_raw).decode("ascii")
    try:
        cache.remember_data_url(oversized)
    except PreviewSourceError as exc:
        assert "limit" in str(exc)
    else:
        raise AssertionError("oversize PNG source was accepted")


def test_preview_source_cache_rejects_truncated_or_gigantic_png_headers():
    cache = PreviewSourceCache(max_item_bytes=4096)

    truncated = "data:image/png;base64," + base64.b64encode(
        b"\x89PNG\r\n\x1a\n"
    ).decode("ascii")
    try:
        cache.remember_data_url(truncated)
    except PreviewSourceError as exc:
        assert "header" in str(exc)
    else:
        raise AssertionError("truncated PNG header was accepted")

    # Only the fixed header is needed to prove the cache rejects a compressed
    # memory-amplification claim before any image decoder sees the payload.
    gigantic_header = (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\x0dIHDR"
        + (50000).to_bytes(4, "big")
        + (2048).to_bytes(4, "big")
    )
    gigantic = "data:image/png;base64," + base64.b64encode(gigantic_header).decode("ascii")
    try:
        cache.remember_data_url(gigantic)
    except PreviewSourceError as exc:
        assert "dimensions" in str(exc)
    else:
        raise AssertionError("gigantic PNG dimensions were accepted")


def test_preview_route_reuses_opaque_source_token_without_changing_pixels(
    app_client, server_module, monkeypatch
):
    source_url, source_raw = _png_data_url()
    observed_sources = []

    def fake_preview_render(paint_file, _zones, **_kwargs):
        with open(paint_file, "rb") as source:
            observed_sources.append(source.read())
        paint = np.full((8, 8, 3), (11, 22, 33), dtype=np.uint8)
        spec = np.full((8, 8, 4), (44, 55, 66, 255), dtype=np.uint8)
        return paint, spec, 7.0

    monkeypatch.setattr(server_module.engine, "preview_render", fake_preview_render)
    server_module.preview_source_cache.clear()
    common = {
        "zones": [{"name": "Everything", "color": "everything", "finish": "gloss", "intensity": 100}],
        "preview_scale": 1.0,
        "settings": {},
    }

    first = app_client.post("/preview-render", json={**common, "paint_image_base64": source_url})
    assert first.status_code == 200, first.get_json(silent=True)
    first_data = first.get_json()
    assert first_data["source_transport"] == "inline"
    assert first_data["source_bytes"] == len(source_raw)
    assert first_data["paint_source_token"]

    second = app_client.post(
        "/preview-render",
        json={**common, "paint_source_token": first_data["paint_source_token"]},
    )
    assert second.status_code == 200, second.get_json(silent=True)
    second_data = second.get_json()
    assert second_data["source_transport"] == "token"
    assert second_data["paint_source_token"] == first_data["paint_source_token"]
    assert second_data["paint_preview"] == first_data["paint_preview"]
    assert second_data["spec_preview"] == first_data["spec_preview"]
    assert observed_sources == [source_raw, source_raw]

    server_module.preview_source_cache.clear()
    missing = app_client.post(
        "/preview-render",
        json={**common, "paint_source_token": first_data["paint_source_token"]},
    )
    assert missing.status_code == 409
    assert missing.get_json()["code"] == "preview_source_missing"


def test_preview_route_cleans_materialized_source_and_recolor_dirs_on_engine_failure(
    app_client, server_module, monkeypatch, tmp_path
):
    source_url, source_raw = _png_data_url()
    created: list[Path] = []

    def fake_mkdtemp(*, prefix):
        directory = tmp_path / f"{prefix}{len(created)}"
        directory.mkdir()
        created.append(directory)
        return str(directory)

    def fake_recolor(_paint_file, _rules, temp_dir):
        target = Path(temp_dir) / "recolored.png"
        target.write_bytes(source_raw)
        return str(target)

    def fail_preview(*_args, **_kwargs):
        raise RuntimeError("intentional preview failure")

    monkeypatch.setattr(server_module, "_spb_mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(server_module, "apply_paint_recolor", fake_recolor)
    monkeypatch.setattr(server_module.engine, "preview_render", fail_preview)
    server_module.preview_source_cache.clear()

    response = app_client.post(
        "/preview-render",
        json={
            "paint_image_base64": source_url,
            "zones": [
                {
                    "name": "Everything",
                    "color": "everything",
                    "finish": "gloss",
                    "intensity": 100,
                }
            ],
            "settings": {},
            "preview_scale": 1.0,
            "recolor_rules": [{"from": "#000000", "to": "#ffffff"}],
        },
    )

    assert response.status_code == 500, response.get_json(silent=True)
    assert len(created) == 2
    assert all(not directory.exists() for directory in created)


def test_native_preview_skips_duplicate_decal_decode_when_no_decal_spec(
    engine_module, tmp_path, monkeypatch
):
    """The live PNG is already paint_file; no spec selection means no second decode."""
    paint_path = tmp_path / "preview_source.png"
    decal_path = tmp_path / "same_composite_decal.png"
    paint_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), (40, 80, 120)).save(paint_path, "PNG")
    Image.new("RGBA", (16, 16), (40, 80, 120, 255)).save(decal_path, "PNG")

    opened: list[str] = []
    original_open = engine_module.Image.open

    def tracking_open(path, *args, **kwargs):
        if isinstance(path, (str, os.PathLike)):
            opened.append(os.path.normcase(os.path.abspath(os.fspath(path))))
        return original_open(path, *args, **kwargs)

    def fake_build_multi_zone(**_kwargs):
        return (
            np.zeros((16, 16, 3), dtype=np.uint8),
            np.zeros((16, 16, 4), dtype=np.uint8),
        )

    monkeypatch.setattr(engine_module.Image, "open", tracking_open)
    monkeypatch.setattr(engine_module, "build_multi_zone", fake_build_multi_zone)
    engine_module.preview_render(
        str(paint_path),
        [{"name": "Everything", "color": "everything", "finish": "gloss", "intensity": 100}],
        preview_scale=1.0,
        decal_paint_path=str(decal_path),
        decal_spec_finishes=None,
    )

    assert os.path.normcase(str(decal_path.resolve())) not in opened


def _clear_engine_preview_source_state(engine_module) -> None:
    engine_module._PREVIEW_SOURCE_RGB_CACHE = None
    if hasattr(engine_module.build_multi_zone, "_zone_cache"):
        engine_module.build_multi_zone._zone_cache.clear()
    if hasattr(engine_module.build_multi_zone, "_color_stats_memo"):
        delattr(engine_module.build_multi_zone, "_color_stats_memo")


def test_native_preview_passes_source_through_without_resample_or_delete(
    engine_module, tmp_path, monkeypatch
):
    paint_path = tmp_path / "native_preview_source.png"
    paint_path.parent.mkdir(parents=True, exist_ok=True)
    source = np.arange(16 * 16 * 3, dtype=np.uint8).reshape((16, 16, 3))
    Image.fromarray(source, mode="RGB").save(paint_path, "PNG")

    observed_paths: list[str] = []
    resize_calls: list[tuple[int, int]] = []
    original_resize = engine_module.Image.Image.resize

    def tracking_resize(image, size, *args, **kwargs):
        resize_calls.append(tuple(size))
        return original_resize(image, size, *args, **kwargs)

    def fake_build_multi_zone(**kwargs):
        observed_paths.append(os.path.normcase(os.path.abspath(kwargs["paint_file"])))
        return source.copy(), np.zeros((16, 16, 4), dtype=np.uint8)

    monkeypatch.setattr(engine_module.Image.Image, "resize", tracking_resize)
    monkeypatch.setattr(engine_module, "build_multi_zone", fake_build_multi_zone)
    paint, _spec, _elapsed = engine_module.preview_render(
        str(paint_path),
        [{"name": "Everything", "color": "everything", "finish": "gloss", "intensity": 100}],
        preview_scale=1.0,
    )

    assert observed_paths == [os.path.normcase(str(paint_path.resolve()))]
    assert resize_calls == []
    assert paint_path.exists()
    assert np.array_equal(paint, source)


def test_native_preview_source_memo_is_cold_warm_cold_byte_identical(
    engine_module, tmp_path, monkeypatch
):
    paint_path = tmp_path / "native_preview_cold_warm_cold.png"
    paint_path.parent.mkdir(parents=True, exist_ok=True)
    yy, xx = np.indices((64, 64), dtype=np.uint16)
    source = np.stack(
        ((xx * 3 + yy) % 256, (xx + yy * 5) % 256, (xx * 7 + yy * 11) % 256),
        axis=2,
    ).astype(np.uint8)
    Image.fromarray(source, mode="RGB").save(paint_path, "PNG")

    normalized_source = os.path.normcase(str(paint_path.resolve()))
    source_opens: list[str] = []
    original_open = engine_module.Image.open

    def tracking_open(path, *args, **kwargs):
        if isinstance(path, (str, os.PathLike)):
            normalized = os.path.normcase(os.path.abspath(os.fspath(path)))
            if normalized == normalized_source:
                source_opens.append(normalized)
        return original_open(path, *args, **kwargs)

    def render_once():
        zones = [
            {
                "name": "Everything",
                "color": "remaining",
                "finish": "gloss",
                "intensity": 100,
                "base_color_mode": "source",
                "hard_edge": True,
            }
        ]
        return engine_module.preview_render(
            str(paint_path), zones, preview_scale=1.0, seed=51
        )[:2]

    monkeypatch.setattr(engine_module.Image, "open", tracking_open)
    try:
        _clear_engine_preview_source_state(engine_module)
        before = len(source_opens)
        cold_paint, cold_spec = render_once()
        cold_opens = len(source_opens) - before

        # Clear render-result caches only: the immutable decoded source should hit.
        if hasattr(engine_module.build_multi_zone, "_zone_cache"):
            engine_module.build_multi_zone._zone_cache.clear()
        if hasattr(engine_module.build_multi_zone, "_color_stats_memo"):
            delattr(engine_module.build_multi_zone, "_color_stats_memo")
        before = len(source_opens)
        warm_paint, warm_spec = render_once()
        warm_opens = len(source_opens) - before

        _clear_engine_preview_source_state(engine_module)
        before = len(source_opens)
        cold_again_paint, cold_again_spec = render_once()
        cold_again_opens = len(source_opens) - before
    finally:
        _clear_engine_preview_source_state(engine_module)

    assert warm_opens < cold_opens
    assert warm_opens < cold_again_opens
    assert np.array_equal(cold_paint, warm_paint)
    assert np.array_equal(cold_paint, cold_again_paint)
    assert np.array_equal(cold_spec, warm_spec)
    assert np.array_equal(cold_spec, cold_again_spec)


def test_preview_source_memo_invalidates_on_exact_encoded_byte_change(
    engine_module, tmp_path
):
    paint_path = tmp_path / "native_preview_source_change.png"
    duplicate_path = tmp_path / "same_preview_bytes_new_request_path.png"
    paint_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _clear_engine_preview_source_state(engine_module)
        Image.new("RGB", (32, 32), (12, 34, 56)).save(paint_path, "PNG")
        first_rgb, first_pixel_digest = engine_module._load_preview_source_rgb(
            str(paint_path)
        )
        duplicate_path.write_bytes(paint_path.read_bytes())
        warm_rgb, warm_pixel_digest = engine_module._load_preview_source_rgb(
            str(duplicate_path)
        )

        Image.new("RGB", (32, 32), (78, 90, 123)).save(paint_path, "PNG")
        changed_rgb, changed_pixel_digest = engine_module._load_preview_source_rgb(
            str(paint_path)
        )
    finally:
        _clear_engine_preview_source_state(engine_module)

    assert warm_rgb is first_rgb
    assert warm_pixel_digest == first_pixel_digest
    assert changed_rgb is not first_rgb
    assert changed_pixel_digest != first_pixel_digest
    assert tuple(changed_rgb[0, 0]) == (78, 90, 123)
    assert not changed_rgb.flags.writeable
