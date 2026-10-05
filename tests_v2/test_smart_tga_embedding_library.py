from __future__ import annotations

import numpy as np
from PIL import Image

from scripts.smart_tga_embedding_library import build_and_evaluate, save_library


def test_real_builder_persists_owner_neutral_library_and_eval(tmp_path):
    image = np.full((160, 320, 3), 20, np.uint8)
    image[20:70, 20:120] = (230, 35, 45)
    image[85:135, 20:120] = (35, 170, 235)
    image[20:70, 180:280] = (230, 35, 45)
    source = tmp_path / "source.png"
    Image.fromarray(image).save(source)
    entries = [
        {"id":"a","role":"reference","family_id":"logo:test","reviewed_owner":"sponsors","source_image":str(source),"bbox":[20,20,100,50]},
        {"id":"b","role":"reference","family_id":"logo:test","reviewed_owner":"sponsors","source_image":str(source),"bbox":[20,85,100,50]},
        {"id":"q","role":"query","expected_family_id":"logo:test","source_image":str(source),"bbox":[180,20,100,50]},
    ]
    references, report = build_and_evaluate({"entries": entries}, min_similarity=0.80)
    assert report["all_passed"] is True
    assert report["casts_votes"] is False
    assert report["ownership_authority"] is False
    save_library(references, report, tmp_path / "library")
    assert (tmp_path / "library" / "library.json").exists()
    assert (tmp_path / "library" / "embeddings.npz").exists()


def test_builder_accepts_exact_instance_masks(tmp_path):
    image = np.zeros((80, 160, 3), np.uint8)
    image[15:65, 20:60] = (240, 30, 30)
    image[15:65, 100:140] = (30, 220, 240)
    mask = np.zeros((80, 160), np.uint8)
    mask[15:65, 20:60] = 255
    mask[15:65, 100:140] = 255
    source = tmp_path / "source.png"
    mask_source = tmp_path / "mask.png"
    Image.fromarray(image).save(source)
    Image.fromarray(mask).save(mask_source)
    entries = [
        {"id":"a","role":"reference","family_id":"logo:masked","reviewed_owner":"sponsors","source_image":str(source),"mask_image":str(mask_source),"bbox":[10,5,60,70]},
        {"id":"b","role":"reference","family_id":"logo:masked","reviewed_owner":"sponsors","source_image":str(source),"mask_image":str(mask_source),"bbox":[90,5,60,70]},
        {"id":"q","role":"query","expected_family_id":"logo:masked","source_image":str(source),"mask_image":str(mask_source),"bbox":[10,5,60,70]},
    ]
    _references, report = build_and_evaluate({"entries": entries}, min_similarity=0.80)
    assert report["all_passed"] is True
