import numpy as np

from _forge_safe_envelope_solver import solve_safe_envelope


CONTRACT={"car_space_extent":{"x_min":0,"x_max":1,"y_bottom":0,"y_top":1}}


def test_original_exact_fit_passes_without_movement():
    allowed=np.ones((20,30),dtype=bool); mask=np.zeros_like(allowed); mask[5:12,8:18]=True
    result=solve_safe_envelope(mask,allowed,CONTRACT)
    assert result["valid"] and result["best"]["scale"]==1.0 and result["best"]["shift"]==[0,0]


def test_contained_translation_abstains_when_direct_residual_is_too_large():
    allowed=np.zeros((20,30),dtype=bool); allowed[5:12,18:28]=True
    mask=np.zeros_like(allowed); mask[5:12,2:12]=True
    result=solve_safe_envelope(mask,allowed,CONTRACT,residual_limit=.08)
    assert result["exact_containment_exists"] and not result["valid"]
    assert result["abstention_reason"]=="direct_evidence_residual_exceeded"


def test_small_evidence_consistent_translation_passes():
    allowed=np.zeros((100,100),dtype=bool); allowed[22:42,20:40]=True
    mask=np.zeros_like(allowed); mask[20:40,20:40]=True
    result=solve_safe_envelope(mask,allowed,CONTRACT,residual_limit=.03)
    assert result["valid"] and result["best"]["shift"]==[0,2]
