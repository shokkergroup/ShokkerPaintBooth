import json

import numpy as np
from PIL import Image

from engine.spec_sculpt.decal_instances import decode_instance_mask_rle, encode_instance_mask_rle
from scripts.smart_tga_number_context_relative_review import run


def test_review_can_promote_a_visually_verified_number_from_source_mask(tmp_path):
    empty = np.zeros((6, 6), bool)
    dataset = {
        "schema": "test", "records": [{
            "cycle": 1, "paint_label": "dirtlatemodel 350/test.tga", "role": "holdout",
            "proposal_id": "ncp:test", "proposal_bbox": [1, 1, 6, 6],
            "label_kind": "empty_control", "number_pixels": 0,
            "label_mask_rle": encode_instance_mask_rle(empty),
        }],
    }
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
    source = np.zeros((8, 8), np.uint8)
    source[1:7, 1:7] = 255
    source_path = tmp_path / "numbers.png"
    Image.fromarray(source).save(source_path)
    review_path = tmp_path / "review.json"
    review_path.write_text(json.dumps({
        "accept_ids": [], "crop_records": [],
        "promote_records": [{"proposal_id": "ncp:test", "source_mask": str(source_path)}],
    }), encoding="utf-8")
    output = tmp_path / "reviewed.json"
    result = run(dataset_path, review_path, output)
    assert result["number_core_records"] == 1
    assert result["records"][0]["label_kind"] == "number_core"
    assert np.count_nonzero(decode_instance_mask_rle(result["records"][0]["label_mask_rle"])) == 36
