import numpy as np
from _forge_front_assembly_gate import audit_assembly

def test_disjoint_owned_layers_with_unique_instances_pass():
    hood=np.zeros((10,10),bool);hood[:5]=True;nose=np.zeros((10,10),bool);nose[5:]=True
    proof=audit_assembly([{"surface":"hood","physical_instance_id":"hood_art","alpha":hood},{"surface":"nose","physical_instance_id":"valance_art","alpha":nose}],{"hood":hood,"nose":nose})
    assert proof["valid"] and proof["cross_layer_overlap_pixels"]==0

def test_duplicate_or_cross_owner_pixels_reject():
    hood=np.zeros((10,10),bool);hood[:6]=True;nose=np.zeros((10,10),bool);nose[5:]=True
    proof=audit_assembly([{"surface":"hood","physical_instance_id":"same","alpha":hood},{"surface":"nose","physical_instance_id":"same","alpha":nose}],{"hood":hood,"nose":nose})
    assert not proof["valid"] and proof["duplicate_physical_instance_ids"]==["same"]
