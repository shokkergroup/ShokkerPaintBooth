import numpy as np
from PIL import Image

from _forge_orthographic_panel_registration import border_connected_foreground, contour_warp_panel, largest_foreground_component, register_panel


def test_border_connected_background_preserves_enclosed_white_paint():
    rgb=np.full((20,20,3),255,dtype=np.uint8);rgb[4:16,4:16]=[0,0,120];rgb[6:14,6:14]=255
    foreground=border_connected_foreground(rgb)
    assert foreground[10,10]
    assert not foreground[0,0]


def test_largest_component_discards_detached_preview_frame():
    mask=np.zeros((30,30),dtype=bool);mask[5:25,5:25]=True;mask[0,:]=True
    kept,proof=largest_foreground_component(mask)
    assert kept.sum()==400
    assert proof["detached_pixels_rejected"]==30


def test_complete_panel_registers_and_clips_to_official_owner():
    source=np.zeros((20,30,4),dtype=np.uint8);source[2:18,3:27]=[200,100,50,255]
    mask=np.zeros((100,100),dtype=bool);mask[20:80,30:70]=True
    layer,proof=register_panel(Image.fromarray(source),mask,(30,20,70,80),90)
    alpha=np.asarray(layer)[:,:,3]>0
    assert not (alpha & ~mask).any()
    assert proof["source_pixel_containment_after_registration"]==1.0
    assert proof["target_mask_fill_fraction"]==1.0
    assert proof["projection_mode"]=="isolated_contour_to_official_mask"


def test_contour_warp_skips_transparent_gap_between_foreground_fragments():
    src=np.zeros((4,10,4),dtype=np.uint8);src[:,:3]=[255,0,0,255];src[:,7:]=[0,0,255,255]
    target=np.ones((4,20),dtype=bool)
    warped,_=contour_warp_panel(Image.fromarray(src),target)
    assert not ((warped[:,:,:3]==255).all(axis=2)).any()
    assert set(map(tuple,warped[:,:,:3].reshape(-1,3))) <= {(255,0,0),(0,0,255)}
