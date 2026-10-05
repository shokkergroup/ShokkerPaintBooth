from pathlib import Path

import numpy as np
from PIL import Image

import _forge_readable_safe_placement as safe


def _layer() -> Image.Image:
    array = np.zeros((2048, 2048, 4), dtype=np.uint8)
    array[100:150, 100:260] = (255, 255, 255, 255)
    return Image.fromarray(array, "RGBA")


def test_readable_cluster_moves_out_of_keepout_without_clipping() -> None:
    allowed = np.ones((2048, 2048), dtype=bool)
    keepout = np.zeros_like(allowed)
    keepout[90:170, 90:280] = True
    result, report = safe.fit_readable_layer(_layer(), allowed, keepout, min_scale=1.0, max_shift=96, shift_step=8)
    assert report["before_keepout_pixels"] == 8000
    assert report["after_keepout_pixels"] == 0
    assert report["after_outside_pixels"] == 0
    assert report["conflict_free"] is True
    assert report["acceptable"] is True
    assert np.count_nonzero(np.asarray(result)[:, :, 3]) == 8000


def test_uniform_scaling_is_used_when_translation_alone_cannot_fit() -> None:
    allowed = np.zeros((2048, 2048), dtype=bool)
    allowed[80:180, 80:280] = True
    keepout = np.zeros_like(allowed)
    keepout[80:180, 210:280] = True
    result, report = safe.fit_readable_layer(_layer(), allowed, keepout, min_scale=0.70, scale_step=0.10, max_shift=48, shift_step=8)
    assert report["after_keepout_pixels"] == 0
    assert report["after_outside_pixels"] == 0
    assert report["clusters"][0]["scale"] < 1.0
    assert np.count_nonzero(np.asarray(result)[:, :, 3]) > 0


def test_excessive_shrink_abstains_even_when_geometry_fits() -> None:
    allowed = np.zeros((2048, 2048), dtype=bool)
    allowed[100:151, 100:181] = True
    keepout = np.zeros_like(allowed)
    _result, report = safe.fit_readable_layer(
        _layer(),
        allowed,
        keepout,
        min_scale=0.50,
        scale_step=0.10,
        max_shift=8,
        shift_step=8,
        acceptance_min_scale=0.75,
    )
    assert report["scale_floor_pass"] is False
    assert report["acceptable"] is False


def test_merge_sources_preserves_separate_editable_evidence(tmp_path: Path) -> None:
    first = np.zeros((2048, 2048, 4), dtype=np.uint8)
    second = np.zeros_like(first)
    first[10:20, 10:20] = (255, 0, 0, 255)
    second[30:40, 30:40] = (0, 0, 255, 255)
    one, two = tmp_path / "one.png", tmp_path / "two.png"
    Image.fromarray(first, "RGBA").save(one)
    Image.fromarray(second, "RGBA").save(two)
    merged = np.asarray(safe.merge_sources([one, two]))
    assert tuple(merged[15, 15]) == (255, 0, 0, 255)
    assert tuple(merged[35, 35]) == (0, 0, 255, 255)


def test_process_job_reserves_prior_semantic_output_as_obstacle(tmp_path: Path) -> None:
    adapter_dir = tmp_path / "adapter"
    adapter_dir.mkdir(exist_ok=True)
    mask = Image.new("L", (2048, 2048), 0)
    mask_array = np.asarray(mask).copy()
    mask_array[90:170, 90:430] = 255
    Image.fromarray(mask_array, "L").save(adapter_dir / "safe.png")
    adapter = {
        "surfaces": {
            "side": {
                "mask_path": "safe.png",
                "semantic_safe_mask_path": "safe.png",
            }
        },
        "semantic_visibility": {},
    }
    (adapter_dir / "adapter.json").write_text(__import__("json").dumps(adapter), encoding="utf-8")

    first = np.zeros((2048, 2048, 4), dtype=np.uint8)
    second = np.zeros_like(first)
    first[100:150, 100:260] = (255, 255, 255, 255)
    second[100:150, 180:340] = (255, 0, 0, 255)
    Image.fromarray(first, "RGBA").save(tmp_path / "first.png")
    Image.fromarray(second, "RGBA").save(tmp_path / "second.png")
    job = {
        "$schema": safe.SCHEMA,
        "root": str(tmp_path),
        "adapter": "adapter/adapter.json",
        "assets": [
            {
                "id": "number",
                "surface": "side",
                "sources": ["first.png"],
                "output": "number.png",
                "search": {"min_scale": 1.0, "max_shift": 0},
            },
            {
                "id": "wordmark",
                "surface": "side",
                "sources": ["second.png"],
                "obstacle_outputs": ["number.png"],
                "output": "wordmark.png",
                "search": {"min_scale": 1.0, "max_shift": 128, "shift_step": 8},
            },
        ],
    }
    job_path = tmp_path / "job.json"
    job_path.write_text(__import__("json").dumps(job), encoding="utf-8")
    report = safe.process_job(job_path, tmp_path / "out")

    assert report["all_acceptable"] is True
    assert report["assets"][1]["after_keepout_pixels"] == 0
    assert report["assets"][1]["obstacles"][0]["path"].endswith("number.png")
    number_alpha = np.asarray(Image.open(tmp_path / "out" / "number.png").getchannel("A")) > 0
    wordmark_alpha = np.asarray(Image.open(tmp_path / "out" / "wordmark.png").getchannel("A")) > 0
    assert not np.any(number_alpha & wordmark_alpha)
