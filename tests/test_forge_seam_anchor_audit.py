import numpy as np
from _forge_seam_anchor_audit import audit_seam_pair


def test_joint_cover_promotes_2d_ownership_when_vertical_split_fails(monkeypatch,tmp_path):
    adapter={"surfaces":{"a":{"bbox":[0,0,10,10],"upright_rotation_deg":0,"car_space_extent":{"x_min":0,"x_max":1,"y_bottom":0,"y_top":1}},"b":{"bbox":[0,0,10,10],"upright_rotation_deg":0,"car_space_extent":{"x_min":0,"x_max":1,"y_bottom":0,"y_top":1}}},"adjacency":[{"a":"a","b":"b"}]}
    masks={"a":np.vstack([np.ones((5,10),bool),np.zeros((5,10),bool)]),"b":np.vstack([np.zeros((5,10),bool),np.ones((5,10),bool)])}
    monkeypatch.setattr("_forge_seam_anchor_audit.surface_contract",lambda _p,s:(masks[s],None,None))
    a={"surface":"a","car_space_box":[0,.1,.5,.9]};b={"surface":"b","car_space_box":[.5,.1,1,.9]}
    result=audit_seam_pair(a,b,adapter,tmp_path,samples=10)
    assert result["valid"] and result["requires_2d_ownership"] and result["gap_samples"]==0


def test_gap_in_both_surfaces_abstains(monkeypatch,tmp_path):
    adapter={"surfaces":{"a":{"bbox":[0,0,10,10],"upright_rotation_deg":0,"car_space_extent":{"x_min":0,"x_max":1,"y_bottom":0,"y_top":1}},"b":{"bbox":[0,0,10,10],"upright_rotation_deg":0,"car_space_extent":{"x_min":0,"x_max":1,"y_bottom":0,"y_top":1}}},"adjacency":[{"a":"a","b":"b"}]}
    mask=np.zeros((10,10),bool);monkeypatch.setattr("_forge_seam_anchor_audit.surface_contract",lambda _p,_s:(mask,None,None))
    a={"surface":"a","car_space_box":[0,.1,.5,.9]};b={"surface":"b","car_space_box":[.5,.1,1,.9]}
    assert not audit_seam_pair(a,b,adapter,tmp_path,samples=10)["valid"]


def test_boundary_discontinuity_abstains(monkeypatch,tmp_path):
    adapter={"surfaces":{"a":{"bbox":[0,0,10,10],"upright_rotation_deg":0,"car_space_extent":{"x_min":0,"x_max":1,"y_bottom":0,"y_top":1}},"b":{"bbox":[0,0,10,10],"upright_rotation_deg":0,"car_space_extent":{"x_min":0,"x_max":1,"y_bottom":0,"y_top":1}}},"adjacency":[{"a":"a","b":"b"}]};mask=np.ones((10,10),bool)
    monkeypatch.setattr("_forge_seam_anchor_audit.surface_contract",lambda _p,_s:(mask,None,None))
    a={"surface":"a","car_space_box":[0,.1,.49,.9]};b={"surface":"b","car_space_box":[.51,.1,1,.9]}
    assert not audit_seam_pair(a,b,adapter,tmp_path,samples=10,boundary_tolerance=.002)["valid"]
