from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from _forge_semantic_asset_completion import extract_exemplar, inspect_fragment, render_instance


def _sheet(path: Path) -> None:
    image = Image.new("RGB", (200, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 25, 179, 74), fill="#ffd100", outline="black", width=3)
    draw.rectangle((45, 35, 70, 65), fill="black")
    draw.rectangle((100, 35, 125, 65), fill="black")
    image.save(path)


def test_clipped_fragment_abstains_and_full_instance_is_emitted(tmp_path: Path) -> None:
    sheet = tmp_path / "sheet.png"
    _sheet(sheet)
    exemplar = extract_exemplar(sheet, {"bbox": [15, 20, 185, 80], "background_rgb": [255, 255, 255], "background_tolerance": 8, "trim": True})
    fragment = Image.new("RGBA", (2048, 2048), (0, 0, 0, 0))
    fragment.alpha_composite(exemplar.crop((0, 0, exemplar.width // 2, exemplar.height)), (100, 200))
    fragment_path = tmp_path / "fragment.png"
    fragment.save(fragment_path)
    result = inspect_fragment(fragment_path, exemplar, {"id": "side", "bbox": [100, 200, 100 + exemplar.width, 200 + exemplar.height], "min_reference_recall": 0.8, "min_density_ratio": 0.7, "max_density_ratio": 1.3, "replacement_instance_id": "full"})
    assert result["complete"] is False
    assert result["decision"] == "abstain_replace"
    canvas = render_instance(exemplar, {"target_bbox": [300, 400, 700, 520]})
    assert canvas.size == (2048, 2048)
    assert np.count_nonzero(np.asarray(canvas)[:, :, 3]) > 0


def test_complete_candidate_is_retained(tmp_path: Path) -> None:
    sheet = tmp_path / "sheet.png"
    _sheet(sheet)
    exemplar = extract_exemplar(sheet, {"bbox": [15, 20, 185, 80], "background_rgb": [255, 255, 255], "background_tolerance": 8, "trim": True})
    candidate = Image.new("RGBA", (2048, 2048), (0, 0, 0, 0))
    candidate.alpha_composite(exemplar, (50, 60))
    path = tmp_path / "candidate.png"
    candidate.save(path)
    result = inspect_fragment(path, exemplar, {"id": "side", "bbox": [50, 60, 50 + exemplar.width, 60 + exemplar.height], "min_reference_recall": 0.9, "min_density_ratio": 0.9, "max_density_ratio": 1.1})
    assert result["complete"] is True
    assert result["reference_recall"] == 1.0
