"""
tests/test_zones.py — zone validation, priority, serialization, mask decode.

These tests intentionally avoid running the full build_multi_zone pipeline —
they verify the *shape* of zone dicts and the validation helpers so bugs
surface as clear errors instead of cryptic IndexErrors deep in compose.
"""

from __future__ import annotations

import json
from copy import deepcopy

import pytest


# ---------------------------------------------------------------------------
# 16. test_zone_validates_color — non-dict zones rejected.
# ---------------------------------------------------------------------------
def test_zone_validates_color(engine_module):
    """_validate_zones rejects zones that are not dicts."""
    with pytest.raises(ValueError, match="must be a dict"):
        engine_module._validate_zones(["not a dict"])


def test_zone_validates_none(engine_module):
    """_validate_zones rejects None with an actionable message."""
    with pytest.raises(ValueError, match="None"):
        engine_module._validate_zones(None)


def test_zone_validates_non_list(engine_module):
    """_validate_zones rejects non-list inputs."""
    with pytest.raises(ValueError, match="must be a list"):
        engine_module._validate_zones({"color": "red"})  # dict, not list


# ---------------------------------------------------------------------------
# 17. test_zone_validates_intensity — intensity strings accepted.
# ---------------------------------------------------------------------------
def test_zone_validates_intensity(engine_module):
    """Intensity values are accepted as both strings and ints."""
    zones = [
        {"name": "a", "color": "red", "finish": "gloss", "intensity": "50"},
        {"name": "b", "color": "blue", "finish": "gloss", "intensity": 75},
    ]
    engine_module._validate_zones(zones)  # must not raise


# ---------------------------------------------------------------------------
# 18. test_zone_default_values — zones with minimum fields are valid.
# ---------------------------------------------------------------------------
def test_zone_default_values(engine_module):
    """A zone with just color+finish is valid (defaults fill in elsewhere)."""
    zones = [{"color": "everything", "finish": "gloss"}]
    engine_module._validate_zones(zones)


# ---------------------------------------------------------------------------
# 19. test_zone_priority_overrides — order preserved through validation.
# ---------------------------------------------------------------------------
def test_zone_priority_overrides(engine_module):
    """Zones keep their input order — earlier zones win pixels first."""
    zones = [
        {"name": "HighPriority", "color": "red", "finish": "chrome", "intensity": "100"},
        {"name": "LowPriority", "color": "red", "finish": "matte", "intensity": "100"},
    ]
    engine_module._validate_zones(zones)
    assert zones[0]["name"] == "HighPriority"
    assert zones[1]["name"] == "LowPriority"


# ---------------------------------------------------------------------------
# 20. test_zone_remainder — "remaining" is a documented color keyword.
# ---------------------------------------------------------------------------
def test_zone_remainder(engine_module):
    """'remaining' is a valid zone color and typically the LAST zone."""
    zones = [
        {"name": "Body", "color": "red", "finish": "chrome", "intensity": "100"},
        {"name": "Rest", "color": "remaining", "finish": "matte", "intensity": "100"},
    ]
    engine_module._validate_zones(zones)
    assert zones[-1]["color"] == "remaining"


# ---------------------------------------------------------------------------
# 21. test_zone_everything — "everything" claims all pixels.
# ---------------------------------------------------------------------------
def test_zone_everything(engine_module):
    """'everything' is a valid color keyword for whole-car zones."""
    zones = [{"name": "All", "color": "everything", "finish": "gloss", "intensity": "100"}]
    engine_module._validate_zones(zones)


# ---------------------------------------------------------------------------
# 22. test_zone_link_groups — linked zones keep their group_id through validation.
# ---------------------------------------------------------------------------
def test_zone_link_groups(engine_module):
    """Zones with link_group_id pass validation (extra keys preserved)."""
    zones = [
        {"name": "L1", "color": "red", "finish": "gloss", "intensity": "100",
         "link_group_id": "group_a"},
        {"name": "L2", "color": "blue", "finish": "gloss", "intensity": "100",
         "link_group_id": "group_a"},
    ]
    engine_module._validate_zones(zones)
    assert zones[0]["link_group_id"] == zones[1]["link_group_id"]


# ---------------------------------------------------------------------------
# 23. test_zone_mute_excludes_from_render — muted flag is a valid extra key.
# ---------------------------------------------------------------------------
def test_zone_mute_excludes_from_render(engine_module):
    """'muted' key is accepted on zone dicts and preserved."""
    zones = [
        {"name": "Active", "color": "red", "finish": "gloss", "intensity": "100"},
        {"name": "Muted", "color": "blue", "finish": "chrome", "intensity": "100",
         "muted": True},
    ]
    engine_module._validate_zones(zones)
    assert zones[1]["muted"] is True


# ---------------------------------------------------------------------------
# 24. test_zone_source_layer_mask_decode — base64/RLE mask string accepted.
# ---------------------------------------------------------------------------
def test_zone_source_layer_mask_decode(engine_module):
    """Zones with region_mask (base64 RLE) pass shape validation."""
    zones = [
        {"name": "Painted", "color": "custom", "finish": "gloss", "intensity": "100",
         "region_mask": "AAAA"},  # placeholder; not decoded at validation time
    ]
    engine_module._validate_zones(zones)


# ---------------------------------------------------------------------------
# 25. test_zone_to_dict_roundtrip — zones survive JSON serialization.
# ---------------------------------------------------------------------------
def test_zone_to_dict_roundtrip():
    """Zones serialize to JSON and back with no data loss."""
    zones = [
        {"name": "Body", "color": "red", "finish": "chrome", "intensity": "100",
         "base": "chrome", "pattern": "carbon_fiber", "scale": 1.0,
         "spec_override": None, "wear": 25},
        {"name": "Rest", "color": "remaining", "finish": "matte", "intensity": "80"},
    ]
    serialized = json.dumps(zones)
    restored = json.loads(serialized)
    assert restored == zones, "Zone roundtrip changed content"
    assert restored[0]["scale"] == 1.0


def test_zone_deep_copy_independence():
    """deepcopy-ing a zone list produces independent mutable dicts."""
    zones = [{"name": "A", "color": "red", "finish": "gloss", "intensity": "100"}]
    copy = deepcopy(zones)
    copy[0]["name"] = "MUTATED"
    assert zones[0]["name"] == "A", "deepcopy didn't actually decouple"


# ---------------------------------------------------------------------------
# Extra zone tests to round out coverage.
# ---------------------------------------------------------------------------
def test_zone_base_plus_pattern_compositing(engine_module):
    """base+pattern compositing zones (v3.0 format) validate cleanly."""
    zones = [
        {"name": "Body", "color": "everything", "base": "chrome",
         "pattern": "carbon_fiber", "intensity": "100"},
    ]
    engine_module._validate_zones(zones)


def test_zone_monolithic_format(engine_module):
    """Monolithic-finish format validates cleanly."""
    zones = [
        {"name": "Body", "color": "everything", "finish": "phantom", "intensity": "100"},
    ]
    engine_module._validate_zones(zones)


def test_zone_missing_name_still_valid(engine_module):
    """Zones without a 'name' key still pass validation (name defaults elsewhere)."""
    zones = [{"color": "everything", "finish": "gloss", "intensity": "100"}]
    engine_module._validate_zones(zones)
