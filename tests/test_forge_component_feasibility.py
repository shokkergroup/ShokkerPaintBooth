from __future__ import annotations

import numpy as np
from PIL import Image

from _forge_component_feasibility import component_feasibility, feasible_shifts


def test_separate_stacked_components_can_fit_when_whole_layer_cannot() -> None:
    image=Image.new("RGBA",(20,16),(0,0,0,0))
    for x in range(5,15):
        for y in range(1,4): image.putpixel((x,y),(255,255,255,255))
        for y in range(11,14): image.putpixel((x,y),(255,255,255,255))
    allowed=np.zeros((16,20),dtype=bool); allowed[5:10]=True
    report=component_feasibility(image,{"bbox":[0,0,20,16],"upright_rotation_deg":0},allowed,max_shift=10,connect_px=1)
    assert report["whole_layer_uniform_shift_count"]==0
    assert report["component_count"]==2
    assert report["component_pack_feasible"]


def test_tall_component_is_infeasible_without_scaling() -> None:
    image=Image.new("RGBA",(20,16),(0,0,0,0))
    for x in range(5,10):
        for y in range(2,12): image.putpixel((x,y),(255,255,255,255))
    allowed=np.zeros((16,20),dtype=bool); allowed[5:10]=True
    report=component_feasibility(image,{"bbox":[0,0,20,16],"upright_rotation_deg":0},allowed,max_shift=10,connect_px=1)
    assert report["infeasible_components"]==1
    assert not report["component_pack_feasible"]


def test_feasible_shifts_reports_exact_uniform_options() -> None:
    mask=np.zeros((10,5),dtype=bool); mask[6:8,2]=True
    allowed=np.zeros_like(mask); allowed[2:6,2]=True
    assert feasible_shifts(mask,allowed,8)==[-4,-3,-2]
