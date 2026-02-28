import traceback
import sys
from shokker_engine_v2 import compose_paint_mod, BASE_REGISTRY
import numpy as np

def test_bases():
    paint = np.ones((100, 100, 3), dtype=np.float32)
    mask = np.ones((100, 100), dtype=np.float32)
    
    for base_id, base in BASE_REGISTRY.items():
        try:
            compose_paint_mod(base_id, "none", paint.copy(), (100, 100), mask, 150, 1.5, 0.5)
            # print(f"SUCCESS: {base_id}")
        except Exception as e:
            print(f"FAILED: {base_id} - {e}")
            traceback.print_exc()

if __name__ == "__main__":
    test_bases()
