from __future__ import annotations

import numpy as np
from PIL import Image

from engine.spec_sculpt.decal_instances import encode_instance_mask_rle
from scripts.smart_tga_reviewed_instance_crops import export_reviewed_instance_crops


def test_exports_exact_masked_family_reference_without_authority(tmp_path):
    source = np.full((60, 80, 3), 20, np.uint8)
    source[15:35, 20:50] = (230, 40, 50)
    source_path = tmp_path / "source.png"
    Image.fromarray(source).save(source_path)
    local_mask = np.zeros((20, 30), bool)
    local_mask[2:18, 3:27] = True
    record = {
        "instance_id": "di:test",
        "bbox": [20, 15, 30, 20],
        "mask_rle": encode_instance_mask_rle(local_mask),
        "ocr_digit_coverage": 0.7,
        "proposed_owners": ["numbers"],
    }
    inspection = {
        "paint_label": "dirtlatemodel 350/car_num_1.tga",
        "source_1024": str(source_path),
        "route_adjudicator_shadow": {"candidate_evidence": {"decal_instances": {
            "ownership_authority": False,
            "casts_votes": False,
            "features": {"ownership_authority": False, "casts_votes": False, "records": [record]},
        }}},
    }
    labels = [{
        "paint_label": inspection["paint_label"],
        "component_labels": [{
            "layer": "numbers",
            "component_index": 1,
            "expected_bbox": [20, 15, 30, 20],
            "target_layer": "numbers",
            "label": "true_number",
            "family_id": "number:24",
        }],
    }]
    manifest = export_reviewed_instance_crops([inspection], labels, tmp_path / "out")
    assert manifest["reference_count"] == 1
    assert manifest["family_counts"] == {"number:24": 1}
    assert manifest["casts_votes"] is False
    assert manifest["ownership_authority"] is False
    entry = manifest["entries"][0]
    exported_mask = np.asarray(Image.open(entry["mask_image"])) > 0
    assert np.array_equal(exported_mask, local_mask)
    assert entry["bbox"] == [0, 0, 30, 20]
    assert entry["intrinsic_evidence"]["ocr_digit_coverage"] == 0.7
    assert entry["intrinsic_evidence"]["proposed_owners"] == ["numbers"]
