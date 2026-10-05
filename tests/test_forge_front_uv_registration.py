import numpy as np

from _forge_front_uv_registration import front_v_range_from_landmarks, project_front_to_mask_scanline, project_front_to_stored_rot90ccw, register_isolated_asset, splat_front_asset_colors


def test_front_vertical_normalization_uses_two_half_widths():
    assert front_v_range_from_landmarks(552, 504, 454) == (0.0, 48 / 908)


def test_rot90_front_orientation_maps_left_to_uv_bottom_and_ground_to_right():
    px, py = project_front_to_stored_rot90ccw(np.array([-1.0, 0.0, 1.0]), np.array([0.0, 0.0, 0.0]), (10, 20, 40, 80), (0.0, 0.4))
    assert px.tolist() == [39, 39, 39]
    assert py.tolist() == [79, 50, 20]


def test_isolated_asset_registration_reports_mask_containment():
    foreground = np.ones((6, 20), dtype=bool)
    mask = np.ones((100, 100), dtype=bool)
    proof, projected = register_isolated_asset(foreground, (0.0, 0.1), (0.0, 0.4), (10, 20, 50, 80), mask)
    assert proof["source_pixel_containment"] == 1.0
    assert proof["mask_snap_mean_px"] == 0.0
    assert proof["orientation"]["front_left_tip_uv"][1] == 79
    assert proof["orientation"]["front_right_tip_uv"][1] == 20
    assert projected.sum() > 0


def test_scanline_projection_follows_nonrectangular_mask_edge():
    mask = np.zeros((100, 100), dtype=bool)
    for row in range(20, 80):
        mask[row, 10:40 + (row - 20) // 3] = True
    px, py = project_front_to_mask_scanline(np.array([-1.0, 0.0, 1.0]), np.zeros(3), (10, 20, 70, 80), (0.0, 0.4), mask)
    assert mask[py, px].all()
    assert py.tolist() == [79, 50, 20]


def test_color_splat_produces_owned_rgba_without_duplication():
    rgb=np.zeros((6,20,3),dtype=np.uint8);rgb[:,:10]=[255,0,0];rgb[:,10:]=[0,0,255]
    fg=np.ones((6,20),dtype=bool);mask=np.ones((100,100),dtype=bool)
    layer=splat_front_asset_colors(rgb,fg,(0,.1),(0,.4),(10,20,50,80),mask)
    a=np.asarray(layer);alpha=a[:,:,3]>0
    assert alpha.any() and not (alpha&~mask).any()
    assert {tuple(c) for c in a[alpha,:3]} <= {(255,0,0),(0,0,255)}
