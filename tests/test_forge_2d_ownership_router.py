import numpy as np
from _forge_2d_ownership_router import route_ownership

def test_overlap_is_assigned_once_deterministically():
    source=np.ones((6,8),bool);a=np.zeros_like(source);b=np.zeros_like(source);a[:,:6]=1;b[:,2:]=1
    routed,proof=route_ownership(source,[a,b])
    assert proof["valid"] and proof["duplicate_pixels"]==0 and np.array_equal(routed[0]|routed[1],source)

def test_gap_is_preserved_and_abstains():
    source=np.ones((4,6),bool);a=np.zeros_like(source);b=np.zeros_like(source);a[:,:2]=1;b[:,4:]=1
    _routed,proof=route_ownership(source,[a,b])
    assert not proof["valid"] and proof["gap_pixels"]==8 and proof["source_accounting_exact"]

def test_single_owner_is_identity():
    source=np.array([[1,0],[1,1]],bool);routed,proof=route_ownership(source,[np.ones_like(source)])
    assert proof["valid"] and np.array_equal(routed[0],source)
