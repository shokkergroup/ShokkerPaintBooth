"""Regression guard for authored-paint monolithic thumbnail bakes."""

from rebuild_thumbnails import make_zone_for_finish


def test_monolithic_thumbnail_uses_its_own_authored_paint_source():
    zone = make_zone_for_finish("monolithic", "fbl_magenta_whorl")

    assert zone["finish"] == "fbl_magenta_whorl"
    assert zone["base_color_mode"] == "special"
    assert zone["base_color_source"] == "mono:fbl_magenta_whorl"


def test_non_monolithic_thumbnail_payloads_do_not_gain_special_color_source():
    for finish_type, finish_id in (("base", "living_matte"),
                                   ("pattern", "carbon_fiber")):
        zone = make_zone_for_finish(finish_type, finish_id)
        assert "base_color_mode" not in zone
        assert "base_color_source" not in zone
