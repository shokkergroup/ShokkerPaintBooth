from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import forge_service.anchors as anchors_module
from forge_service.anchors import accepted_anchor_values, propose_anchors


def _entry(job_dir: Path, role: str, image: Image.Image) -> dict:
    sources = job_dir / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    path = sources / f"direct-{role}.png"
    image.save(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "id": f"ref-{role}",
        "stored_path": path.relative_to(job_dir).as_posix(),
        "sha256": digest,
        "bytes": path.stat().st_size,
        "role": role,
        "role_confidence": 1.0,
        "role_source": "test_direct_slot",
        "duplicate_of": None,
    }


def _sheet_with_profile() -> Image.Image:
    image = Image.new("RGB", (1200, 700), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((90, 25, 920, 48), fill="#151515")
    draw.rectangle((45, 110, 1150, 390), fill="#d2a822")
    draw.polygon(((45, 390), (160, 200), (1150, 210), (1150, 390)), fill="#25394d")
    draw.ellipse((160, 255, 360, 455), fill="#090909", outline="#d6d6d6", width=8)
    draw.ellipse((820, 255, 1020, 455), fill="#090909", outline="#d6d6d6", width=8)
    for x0 in (30, 420, 810):
        draw.rectangle((x0, 505, x0 + 350, 675), outline="#202020", width=4)
        draw.rectangle((x0 + 20, 530, x0 + 330, 650), fill="#737d88")
    return image


def test_dominant_physical_profile_beats_titles_and_detail_panels(tmp_path: Path):
    proposal = propose_anchors(tmp_path, [_entry(tmp_path, "left", _sheet_with_profile())])
    side = proposal["roles"]["left"]
    assert side["primary_object_bbox"][0] < 0.1
    assert side["primary_object_bbox"][2] > 0.9
    assert side["primary_object_bbox"][3] < 0.7
    assert side["fields"]["front_wheel_center"]["value"] is not None
    assert side["fields"]["rear_wheel_center"]["value"] is not None


def test_partial_accepted_fields_are_available_without_promoting_whole_role():
    proposals = {
        "roles": {
            "front": {
                "status": "review",
                "fields": {
                    "center_x": {"status": "accepted", "value": 0.5},
                    "half_width": {"status": "accepted", "value": 0.4},
                    "ground_y": {"status": "accepted", "value": 0.8},
                    "hood_seam_y": {"status": "review", "value": 0.6},
                },
            }
        }
    }
    assert accepted_anchor_values(proposals, "front") == {
        "center_x": 0.5,
        "half_width": 0.4,
        "ground_y": 0.8,
    }


def test_front_seam_stays_review_only_and_rear_inside_abstains(tmp_path: Path):
    front = Image.new("RGB", (900, 600), "white")
    draw = ImageDraw.Draw(front)
    draw.polygon(((170, 120), (730, 120), (840, 510), (60, 510)), fill="#c68b20")
    draw.rectangle((80, 420, 820, 510), fill="#151515")
    rear = Image.new("RGB", (900, 600), "white")
    draw = ImageDraw.Draw(rear)
    draw.rectangle((160, 100, 740, 220), fill="#d5a72d")
    draw.rectangle((190, 220, 710, 520), fill="#171717")
    proposals = propose_anchors(
        tmp_path,
        [_entry(tmp_path, "front", front), _entry(tmp_path, "rear", rear)],
    )
    assert proposals["roles"]["front"]["fields"]["hood_seam_y"]["status"] == "review"
    assert proposals["roles"]["rear"]["fields"]["spoiler_inside_quad"]["status"] == "abstain"
    assert proposals["roles"]["rear"]["status"] == "abstain"


def test_front_sheet_finds_one_disjoint_valance_without_duplicating_hood(tmp_path: Path):
    image = Image.new("RGB", (1200, 700), "white")
    draw = ImageDraw.Draw(image)
    # Assembled front car and a large isolated hood asset are deliberately
    # present; only the wide/shallow disjoint lower strip may qualify.
    draw.polygon(((180, 120), (1020, 120), (1110, 520), (90, 520)), fill="#d9a622")
    draw.rectangle((130, 445, 1070, 520), fill="#161616")
    draw.rectangle((50, 570, 360, 665), fill="#bd2638")
    draw.rectangle((700, 585, 1125, 635), fill="#2b4c8a", outline="#111111", width=4)

    front = propose_anchors(tmp_path, [_entry(tmp_path, "front", image)])["roles"]["front"]
    valance = front["fields"]["front_valance_quad"]
    assert valance["status"] == "review"
    assert valance["provenance"] == "direct_isolated_front_valance_component/v1"
    assert min(point[0] for point in valance["value"]) > 0.5
    assert max(point[1] for point in valance["value"]) > 0.8
    assert front["fields"]["valance_top_y"]["status"] == "review"
    diagnostics = front["diagnostics"]["isolated_front_valance_detection"]
    assert diagnostics["candidate_count"] == 1
    assert diagnostics["primary_overlap"] == 0.0


def test_reusable_module_has_no_livery_identity_branches():
    source = inspect.getsource(anchors_module).lower()
    for forbidden in ("waffle", "jason", "domino", "sex wax", "miller", "mountain dew", "spider"):
        assert forbidden not in source


def test_top_quad_pairing_normalizes_winding_without_reflection():
    # This box ordering reproduces minAreaRect returning the lower parallel
    # edge first.  The normalized contract must still emit a top-first,
    # clockwise screen-space quad for the direct-top executor.
    box = np.asarray([[20.0, 80.0], [180.0, 81.0], [181.0, 20.0], [21.0, 19.0]], dtype=np.float32)
    axis = anchors_module._major_axis(box)
    quad = np.asarray(anchors_module._segment_quad(axis, 0.05, 0.35, 200, 100), dtype=np.float32)
    assert float(quad[:2, 1].mean()) < float(quad[2:, 1].mean())
    assert cv2.contourArea(quad.reshape((-1, 1, 2)), oriented=True) > 0


def test_top_sheet_prefers_direct_isolated_panels_over_fixed_car_fractions(tmp_path: Path):
    image = Image.new("RGB", (1200, 700), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 170, 730, 440), fill="#182634")
    draw.rectangle((80, 195, 260, 415), fill="#d39922")
    draw.rectangle((315, 195, 485, 415), fill="#284c8a")
    draw.rectangle((535, 195, 700, 415), fill="#7a2935")
    draw.rectangle((820, 85, 1010, 255), fill="#d39922")
    draw.rectangle((1030, 85, 1180, 255), fill="#284c8a")
    draw.rectangle((825, 355, 1000, 560), fill="#7a2935")

    proposal = propose_anchors(tmp_path, [_entry(tmp_path, "top", image)])["roles"]["top"]
    assert proposal["status"] == "review"
    assert "isolated_panel_detection" in proposal["diagnostics"]
    assert proposal["diagnostics"]["isolated_panel_detection"]["layout"] == "upper_pair_plus_lower_rear"
    hood = proposal["fields"]["hood_quad"]
    roof = proposal["fields"]["roof_quad"]
    deck = proposal["fields"]["rear_deck_quad"]
    assert hood["provenance"] == "direct_isolated_panel_component+sheet_layout/v1"
    assert hood["value"][0][0] < roof["value"][0][0]
    assert deck["value"][0][1] > hood["value"][0][1]
    assert min(point[0] for point in hood["value"]) > 0.65


def test_rear_sheet_prefers_isolated_spoiler_face_over_assembled_car_bar(tmp_path: Path):
    image = Image.new("RGB", (1200, 700), "white")
    draw = ImageDraw.Draw(image)
    # Dominant assembled rear car with an attached upper bar.
    draw.rectangle((70, 100, 760, 440), fill="#17212c")
    draw.rectangle((75, 100, 755, 175), fill="#b68b22")
    draw.ellipse((110, 280, 280, 500), fill="#090909")
    draw.ellipse((560, 280, 730, 500), fill="#090909")
    # Clean isolated physical spoiler face plus side/rear-panel decoys.
    draw.rectangle((820, 90, 1170, 150), fill="#284c8a", outline="#101010", width=5)
    draw.polygon(((840, 230), (1010, 230), (970, 360), (860, 360)), fill="#7a2935")
    draw.rectangle((805, 440, 1120, 625), fill="#5f4528")

    rear = propose_anchors(tmp_path, [_entry(tmp_path, "rear", image)])["roles"]["rear"]
    field = rear["fields"]["spoiler_outside_quad"]
    assert field["status"] == "review"
    assert field["provenance"] == "direct_isolated_spoiler_face_component/v1"
    assert min(point[0] for point in field["value"]) > 0.65
    assert max(point[1] for point in field["value"]) < 0.3
    diagnostics = rear["diagnostics"]["isolated_spoiler_face_detection"]
    assert diagnostics["candidate_count"] == 1
    assert diagnostics["primary_overlap"] == 0.0
