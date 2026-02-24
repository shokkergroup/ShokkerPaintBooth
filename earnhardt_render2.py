"""Render the Earnhardt #3 with updated gray zone and contingency masking."""
import json, urllib.request, time

render_request = {
    "paint_file": "E:/Claude Code Assistant/12-iRacing Misc/Shokker iRacing/Driver Paints/dalebig3.tga",
    "zones": [
        # --- CONTINGENCY DECAL COLORS -> GLOSS (must be BEFORE the catch-all) ---
        # These grab the unique sponsor logo colors so they get clean gloss
        {
            "name": "Contingency Reds",
            "color": [
                {"color_rgb": [220, 39, 32], "tolerance": 18},
                {"color_rgb": [170, 31, 46], "tolerance": 15},
                {"color_rgb": [237, 25, 45], "tolerance": 15},
                {"color_rgb": [235, 30, 35], "tolerance": 15},
                {"color_rgb": [237, 28, 36], "tolerance": 15},
                {"color_rgb": [209, 33, 39], "tolerance": 15},
            ],
            "intensity": "subtle",
            "base": "gloss",
            "pattern": "none"
        },
        {
            "name": "Contingency Blues",
            "color": [
                {"color_rgb": [26, 93, 173], "tolerance": 20},
                {"color_rgb": [32, 67, 148], "tolerance": 18},
                {"color_rgb": [0, 101, 176], "tolerance": 20},
                {"color_rgb": [31, 58, 112], "tolerance": 18},
            ],
            "intensity": "subtle",
            "base": "gloss",
            "pattern": "none"
        },
        {
            "name": "Contingency Yellows",
            "color": [
                {"color_rgb": [201, 191, 0], "tolerance": 20},
                {"color_rgb": [100, 96, 0], "tolerance": 18},
                {"color_rgb": [255, 185, 53], "tolerance": 20},
            ],
            "intensity": "subtle",
            "base": "gloss",
            "pattern": "none"
        },
        {
            "name": "Contingency Grays",
            "color": [
                {"color_rgb": [217, 217, 217], "tolerance": 10},
                {"color_rgb": [100, 100, 100], "tolerance": 12},
                {"color_rgb": [132, 132, 132], "tolerance": 12},
            ],
            "intensity": "subtle",
            "base": "gloss",
            "pattern": "none"
        },
        # --- MAIN BODY ZONES (same as before except gray) ---
        {
            "name": "Body Color 1",
            "color": [{"color_rgb": [255, 255, 255], "tolerance": 40}],
            "intensity": "aggressive",
            "base": "chrome",
            "pattern": "hex_mesh",
            "scale": 0.6,
            "pattern_opacity": 0.55,
            "pattern_stack": [
                {"id": "diamond_plate", "opacity": 0.2, "scale": 0.8}
            ]
        },
        {
            "name": "Body Color 2",
            "color": [{"color_rgb": [255, 0, 0], "tolerance": 40}],
            "intensity": "aggressive",
            "base": "candy",
            "pattern": "lightning",
            "scale": 0.7,
            "pattern_opacity": 0.4,
            "pattern_stack": [
                {"id": "ember_mesh", "opacity": 0.2, "scale": 0.5}
            ]
        },
        {
            "name": "Body Color 3",
            "color": [{"color_rgb": [253, 81, 0], "tolerance": 40}],
            "intensity": "aggressive",
            "base": "spectraflame",
            "pattern": "dragon_scale",
            "scale": 0.5,
            "pattern_opacity": 0.5,
            "pattern_stack": [
                {"id": "stardust", "opacity": 0.25, "scale": 0.4}
            ]
        },
        # --- UPDATED GRAY ZONE: anodized + stardust + interference ---
        {
            "name": "Body Color 4",
            "color": [{"color_rgb": [180, 180, 180], "tolerance": 40}],
            "intensity": "aggressive",
            "base": "anodized",
            "pattern": "stardust",
            "scale": 0.5,
            "pattern_opacity": 0.55,
            "pattern_stack": [
                {"id": "interference", "opacity": 0.3, "scale": 0.6}
            ]
        },
        {
            "name": "Car Number",
            "color": [{"color_rgb": [255, 242, 0], "tolerance": 35}],
            "intensity": "medium",
            "base": "satin_gold",
            "pattern": "chainmail",
            "scale": 0.6,
            "pattern_opacity": 0.4,
            "pattern_stack": [
                {"id": "mega_flake", "opacity": 0.3, "scale": 0.5}
            ]
        },
        {
            "name": "Custom Art 2",
            "color": [{"color_rgb": [0, 0, 0], "tolerance": 40}],
            "intensity": "aggressive",
            "base": "piano_black",
            "pattern": "carbon_fiber",
            "scale": 0.5,
            "pattern_opacity": 0.45,
            "pattern_stack": [
                {"id": "holographic_flake", "opacity": 0.15, "scale": 0.35}
            ]
        },
        # --- CATCH-ALL: Sponsors/Logos/BK/WeCare all get clean gloss ---
        {
            "name": "Sponsors / Logos",
            "color": "remaining",
            "intensity": "subtle",
            "base": "gloss",
            "pattern": "none"
        }
    ],
    "iracing_id": "23371",
    "seed": 51,
    "live_link": True,
    "output_dir": "C:/Users/Ricky's PC/Documents/iRacing/paint/stockcars2 arcachevy25"
}

print("=" * 60)
print("EARNHARDT #3 SHOWCASE RENDER v2")
print("=" * 60)
print(f"Zones: {len(render_request['zones'])}")
for i, z in enumerate(render_request['zones'], 1):
    stack = z.get('pattern_stack', [])
    stack_str = ' + '.join([f"{s['id']}@{s['opacity']*100:.0f}%" for s in stack]) if stack else '-'
    pat = z.get('pattern', 'none')
    pat_op = z.get('pattern_opacity', 1.0)
    scale = z.get('scale', 1.0)
    print(f"  {i:2d}. {z['name']:25s}: {z['base']:18s} + {pat}@{pat_op*100:.0f}% s={scale} | stack=[{stack_str}] ({z['intensity']})")

print(f"\nSending to server...")
t0 = time.time()
data = json.dumps(render_request).encode('utf-8')
req = urllib.request.Request(
    'http://127.0.0.1:5000/render', 
    data=data, 
    headers={'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req, timeout=300)
result = json.loads(resp.read())
elapsed = time.time() - t0

print(f"\n{'=' * 60}")
if result.get('success'):
    print(f"SUCCESS in {result.get('elapsed_seconds', '?'):.1f}s server / {elapsed:.1f}s total")
    ll = result.get('live_link', {})
    if ll.get('success'):
        print(f"LIVE LINK: Pushed to {ll.get('path', '?')}")
        for f in ll.get('pushed_files', []):
            print(f"  -> {f}")
    print(f"Zones rendered: {result.get('zone_count', '?')}")
else:
    print(f"FAILED: {result.get('error', 'unknown')}")
print("=" * 60)
