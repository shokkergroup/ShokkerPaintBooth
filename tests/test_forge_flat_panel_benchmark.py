from pathlib import Path

import numpy as np
from PIL import Image

import _forge_flat_panel_benchmark as benchmark


def test_score_candidate_penalizes_wrong_orientation() -> None:
    reference = Image.new("RGBA", (2048, 2048), (0, 0, 0, 0))
    pixels = np.zeros((2048, 2048, 4), dtype=np.uint8)
    pixels[200:500, 300:900] = (238, 190, 12, 255)
    pixels[240:460, 330:450] = (8, 8, 8, 255)
    reference = Image.fromarray(pixels, "RGBA")
    exact = Image.new("RGB", reference.size, (238, 190, 12))
    exact.paste(reference.convert("RGB"), mask=reference.getchannel("A"))

    wrong_pixels = np.asarray(exact, dtype=np.uint8).copy()
    local = wrong_pixels[200:500, 300:900].copy()
    wrong_pixels[200:500, 300:900] = np.flip(local, axis=1)
    wrong = Image.fromarray(wrong_pixels, "RGB")

    exact_metrics, _ = benchmark.score_candidate(reference, exact)
    wrong_metrics, _ = benchmark.score_candidate(reference, wrong)
    assert exact_metrics["visual_fidelity"] > 99.0
    assert wrong_metrics["visual_fidelity"] < exact_metrics["visual_fidelity"] - 10.0


def test_resolve_preserves_absolute_paths(tmp_path: Path) -> None:
    absolute = tmp_path / "evidence.png"
    assert benchmark._resolve(Path("C:/elsewhere"), str(absolute)) == absolute
