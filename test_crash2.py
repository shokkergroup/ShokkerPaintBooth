import traceback
import sys
from shokker_engine_v2 import compose_finish, compose_paint_mod, BASE_REGISTRY, PATTERN_REGISTRY
import numpy as np

def test_bases():
    paint = np.ones((100, 100, 3), dtype=np.float32)
    mask = np.ones((100, 100), dtype=np.float32)
    # The browser might send a seed up to 4,294,967,295. Let's send a large valid one.
    seed = 51
    
    for base_id, base in BASE_REGISTRY.items():
        try:
            compose_finish(base_id, "none", (100, 100), mask, seed, 1.5, 1.0, 1.0, 0, 1.0)
            compose_paint_mod(base_id, "none", paint.copy(), (100, 100), mask, seed, 1.5, 0.5)
        except Exception as e:
            print(f"FAILED Base {base_id}: {e}")
            # traceback.print_exc()

    print("Now testing patterns...")
    for pat_id, pat in PATTERN_REGISTRY.items():
        try:
            compose_finish("gloss", pat_id, (100, 100), mask, seed, 1.5, 1.0, 1.0, 0, 1.0)
            compose_paint_mod("gloss", pat_id, paint.copy(), (100, 100), mask, seed, 1.5, 0.5)
        except Exception as e:
            print(f"FAILED Pattern {pat_id}: {e}")

if __name__ == "__main__":
    test_bases()
