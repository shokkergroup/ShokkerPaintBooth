import json
import subprocess
from pathlib import Path

from PIL import Image


WORKSPACE = Path(__file__).resolve().parents[1]
MODULE = WORKSPACE / "forge-anchor-editor.js"


def _node(expression: str):
    script = f"const g=require({json.dumps(str(MODULE))}); const out=({expression}); process.stdout.write(JSON.stringify(out));"
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def test_editor_exposes_only_source_owned_review_fields():
    proposal = {
        "fields": {
            "body_top_y": {"value": 0.24, "status": "review"},
            "rocker_y": {"value": 0.78, "status": "accepted"},
            "front_wheel_center": {"value": [0.2, 0.62], "status": "accepted"},
        }
    }
    assert _node(f"g.editableFields('left',{json.dumps(proposal)})") == ["body_top_y"]
    rear = {
        "fields": {
            "rear_deck_quad": {"value": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]], "status": "review"},
            "spoiler_outside_quad": {"value": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.4], [0.2, 0.4]], "status": "review"},
            "spoiler_inside_quad": {"value": None, "status": "abstain"},
        }
    }
    assert _node(f"g.editableFields('rear',{json.dumps(rear)})") == ["spoiler_outside_quad"]


def test_editor_enforces_body_order_and_convex_quads():
    valid_side = {"body_top_y": 0.25, "rocker_y": 0.75}
    assert _node(f"g.validate('left',{json.dumps(valid_side)},[0.1,0.1,0.9,0.85]).valid") is True
    bad_side = {"body_top_y": 0.8, "rocker_y": 0.75}
    assert _node(f"g.validate('left',{json.dumps(bad_side)},[0.1,0.1,0.9,0.85]).valid") is False

    folded = {"spoiler_outside_quad": [[0.2, 0.2], [0.8, 0.6], [0.8, 0.2], [0.2, 0.6]]}
    result = _node(f"g.validate('rear',{json.dumps(folded)},[0.1,0.1,0.9,0.8])")
    assert result["valid"] is False
    assert any("ordered and convex" in message or "folded" in message for message in result["errors"])


def test_editor_requires_consistent_top_surface_order_and_clamps_drag():
    values = {
        "hood_quad": [[0.1, 0.2], [0.3, 0.2], [0.3, 0.7], [0.1, 0.7]],
        "roof_quad": [[0.4, 0.2], [0.58, 0.2], [0.58, 0.7], [0.4, 0.7]],
        "rear_deck_quad": [[0.66, 0.2], [0.86, 0.2], [0.86, 0.7], [0.66, 0.7]],
    }
    assert _node(f"g.validate('top',{json.dumps(values)},[0.05,0.1,0.92,0.8]).valid") is True
    reordered = dict(values)
    reordered["roof_quad"] = values["rear_deck_quad"]
    reordered["rear_deck_quad"] = values["roof_quad"]
    assert _node(f"g.validate('top',{json.dumps(reordered)},[0.05,0.1,0.92,0.8]).valid") is False
    moved = _node("g.moveQuadPoint({q:[[0.1,0.1],[0.2,0.1],[0.2,0.2],[0.1,0.2]]},'q',0,-4,3)")
    assert moved["q"][0] == [0, 1]


def test_rear_confirmation_cannot_smuggle_cross_view_or_inside_fields():
    values = {
        "rear_deck_quad": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]],
        "spoiler_outside_quad": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.4], [0.2, 0.4]],
    }
    confirmed = _node(f"g.confirmationValues('rear',{json.dumps(values)})")
    assert set(confirmed) == {"spoiler_outside_quad"}


def test_specialized_surface_review_supports_exact_roles_and_rejects_reversal():
    contracts = {
        "front_corner_left": "front_corner_left_quad",
        "front_corner_right": "front_corner_right_quad",
        "rear_inside": "spoiler_inside_quad",
    }
    valid = [[0.12, 0.14], [0.88, 0.16], [0.84, 0.86], [0.15, 0.82]]
    for role, field in contracts.items():
        proposal = {"fields": {field: {"value": valid, "status": "review"}}}
        assert _node(f"g.editableFields({json.dumps(role)},{json.dumps(proposal)})") == [field]
        values = {field: valid}
        assert _node(f"g.validate({json.dumps(role)},{json.dumps(values)},[0,0,1,1]).valid") is True
        reversed_values = {field: list(reversed(valid))}
        result = _node(f"g.validate({json.dumps(role)},{json.dumps(reversed_values)},[0,0,1,1])")
        assert result["valid"] is False
        assert any("reversed" in message or "ordered" in message for message in result["errors"])


def test_source_review_renderer_uses_same_direct_ownership_contract(tmp_path):
    job_dir = tmp_path / "job"
    sources = job_dir / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    inputs = []
    roles = {}
    for role in ("left", "right", "top", "front", "rear"):
        source = sources / f"{role}.png"
        Image.new("RGB", (120, 80), "#30343b").save(source)
        inputs.append({"id": f"ref-{role}", "role": role, "stored_path": f"sources/{role}.png", "duplicate_of": None})
        fields = {}
        if role in {"left", "right"}:
            fields = {"body_top_y": {"value": 0.25}}
        elif role == "top":
            fields = {
                "hood_quad": {"value": [[0.1, 0.2], [0.3, 0.2], [0.3, 0.7], [0.1, 0.7]]},
                "roof_quad": {"value": [[0.4, 0.2], [0.58, 0.2], [0.58, 0.7], [0.4, 0.7]]},
                "rear_deck_quad": {"value": [[0.66, 0.2], [0.86, 0.2], [0.86, 0.7], [0.66, 0.7]]},
            }
        elif role == "front":
            fields = {"hood_seam_y": {"value": 0.35}}
        else:
            fields = {"spoiler_outside_quad": {"value": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.4], [0.2, 0.4]]}}
        roles[role] = {"status": "review", "confidence": 0.8, "primary_object_bbox": [0.05, 0.1, 0.95, 0.9], "fields": fields}
    job_path = job_dir / "job.json"
    job_path.write_text(json.dumps({"id": "synthetic", "inputs": inputs, "last_run": {"anchor_proposals": {"roles": roles}}}), encoding="utf-8")
    output = tmp_path / "review"
    subprocess.run(
        ["python", str(WORKSPACE / "_forge_anchor_editor_review.py"), "--job", str(job_path), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads((output / "source_anchor_editor_evidence.json").read_text(encoding="utf-8"))
    rear = next(row for row in report["roles"] if row["role"] == "rear")
    assert rear["editable_fields"] == ["spoiler_outside_quad"]
    assert rear["excluded_fields"] == ["rear_deck_quad (owned by top)", "spoiler_inside_quad (no direct evidence)"]
    assert (output / "WAFFLE_SOURCE_ANCHOR_EDITOR_EVIDENCE.png").stat().st_size > 10_000
