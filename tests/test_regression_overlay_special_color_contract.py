"""Regression guards for Base Overlay Layer color-source semantics."""

from engine.compose import _overlay_mono_color_source


def test_overlay_color_source_uses_special_base_when_same_as_overlay():
    assert _overlay_mono_color_source("mono:firefly_glow", "overlay") == "mono:firefly_glow"


def test_overlay_color_source_uses_explicit_special_color():
    assert _overlay_mono_color_source("f_metallic", "mono:firefly_glow") == "mono:firefly_glow"


def test_overlay_solid_color_beats_special_base_auto_color():
    assert _overlay_mono_color_source("mono:firefly_glow", "solid") is None


def test_legacy_missing_color_source_still_means_same_as_special_base():
    assert _overlay_mono_color_source("mono:firefly_glow", None) == "mono:firefly_glow"
