import sys, os
import traceback

sys.path.insert(0, r"c:\Shokker Paint Booth - AntiGravity")

print("Checking Barn Find & Burnt Headers directly in Python Engine...")

try:
    import shokker_engine_v2 as engine
    import numpy as np
    
    # 1. Test Barn Find Chalk registration
    if "barn_find" in engine.BASE_REGISTRY:
        reg = engine.BASE_REGISTRY["barn_find"]
        print("FOUND barn_find in BASE_REGISTRY!")
        print(f"Paint FN: {reg.get('paint_fn')}")
        
        # Test execute it
        dummy_paint = np.zeros((256, 256, 3), dtype=np.float32)
        dummy_mask = np.ones((256, 256), dtype=np.float32)
        
        out = reg['paint_fn'](dummy_paint, (256, 256), dummy_mask, 12, 100, None)
        print(f"Executed barn_find. Mean pixel val: {out.mean():.4f}")
    else:
        print("barn_find NOT found in BASE_REGISTRY!")
        
    # 2. Test Burnt Headers Error 22
    if "burnt_headers" in engine.BASE_REGISTRY:
        print("FOUND burnt_headers in BASE_REGISTRY!")
        reg2 = engine.BASE_REGISTRY["burnt_headers"]
        dummy_paint2 = np.zeros((256, 256, 3), dtype=np.float32)
        out2 = reg2['paint_fn'](dummy_paint2, (256, 256), dummy_mask, 12, 100, None)
        print(f"Executed burnt_headers (No Error 22!). Mean pixel val: {out2.mean():.4f}")
    else:
        print("burnt_headers NOT found in BASE_REGISTRY!")
        
except Exception as e:
    traceback.print_exc()

print("DONE.")
