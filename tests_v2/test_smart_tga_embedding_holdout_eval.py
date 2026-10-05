from __future__ import annotations

import numpy as np
from PIL import Image

from scripts.smart_tga_embedding_holdout_eval import evaluate_holdouts


def test_holdout_eval_requires_repeated_family_and_rejects_cross_family(tmp_path):
    entries = []
    for family, shape_kind in (("logo:plus", "plus"), ("number:ring", "ring")):
        for index in range(3):
            image = np.full((64, 64, 3), 30 + index * 15, np.uint8)
            mask = np.zeros((64, 64), np.uint8)
            if shape_kind == "plus":
                mask[10:54, 26:38] = 255
                mask[26:38, 10:54] = 255
            else:
                yy, xx = np.ogrid[:64, :64]
                radius = np.sqrt((xx - 32) ** 2 + (yy - 32) ** 2)
                mask[(radius >= 16) & (radius <= 25)] = 255
            image[mask > 0] = (230 - index * 20, 50 + index * 30, 80)
            source = tmp_path / f"{shape_kind}_{index}.png"
            mask_source = tmp_path / f"{shape_kind}_{index}.mask.png"
            Image.fromarray(image).save(source)
            Image.fromarray(mask).save(mask_source)
            entries.append({
                "id": f"{shape_kind}_{index}",
                "family_id": family,
                "reviewed_owner": "sponsors" if shape_kind == "plus" else "numbers",
                "review_label": "reviewed",
                "paint_label": f"paint/{index}.tga",
                "source_image": str(source),
                "mask_image": str(mask_source),
                "bbox": [0, 0, 64, 64],
            })
    report = evaluate_holdouts(entries, min_similarity=0.80, ambiguity_margin=0.03)
    assert report["positive_trials"] == 6
    assert report["positive_passed"] == 6
    assert report["negative_trials"] == 6
    assert report["negative_passed"] == 6
    assert report["cross_paint_positive_families"] == ["logo:plus", "number:ring"]
    assert report["all_passed"] is True
    assert report["casts_votes"] is False
    assert report["ownership_authority"] is False
