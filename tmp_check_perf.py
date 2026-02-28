import requests
import time

bases_to_test = [
    "matte_wrap", "gloss_wrap", "stealth_wrap",
    "sprint_car_chrome", "drag_strip_gloss", "dirt_track_satin", "pace_car_pearl", "barn_find",
    "bentley_silver", "lamborghini_verde", "bugatti_blue", "koenigsegg_clear", "maybach_two_tone"
]

def test_swatches():
    print("Testing Custom Logic Render Execution...")
    
    for base in bases_to_test:
        start = time.time()
        try:
            r = requests.get(f'http://127.0.0.1:59876/swatch/{base}/none')
            end = time.time()
            
            if r.status_code == 200:
                print(f"SUCCESS: {base} rendered in {end - start:.2f} seconds.")
            else:
                print(f"FAILED: {base} returned HTTP {r.status_code}")
                print(f"Error Body: {r.text[:200]}")
        except Exception as e:
            print(f"ERROR on {base}: {e}")

if __name__ == "__main__":
    test_swatches()
