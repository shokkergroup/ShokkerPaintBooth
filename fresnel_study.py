"""Fresnel study: What pixel-level paint+spec combos create the best color shift illusion?"""
import numpy as np

def sim(paint_rgb, M, R, CC_b, ndotv):
    """Simulate iRacing PBR apparent color at a viewing angle."""
    f0 = np.array([0.04]*3)*(1-M) + np.array(paint_rgb)*M
    fresnel = f0 + (1.0 - f0) * (1.0 - ndotv)**5
    diffuse = np.array(paint_rgb)*(1.0 - M)*ndotv
    spec_s = 1.0 - R*0.7
    spec = fresnel*0.5*spec_s
    cc_on = CC_b >= 16
    cc_r = max(0, (CC_b-16)/239.0) if cc_on else 0
    cc_f = (0.04 + 0.96*(1.0-ndotv)**5) if cc_on else 0
    cc = cc_f*0.5*(1.0 - cc_r*0.7) if cc_on else 0
    return np.clip(diffuse + spec + np.array([cc]*3), 0, 1)

def rgb_to_hsv(r, g, b):
    mx = max(r, g, b)
    mn = min(r, g, b)
    d = mx - mn
    v = mx
    s = d/mx if mx > 0 else 0
    if d == 0:
        h = 0
    elif mx == r:
        h = ((g-b)/d) % 6
    elif mx == g:
        h = (b-r)/d + 2
    else:
        h = (r-g)/d + 4
    h = h * 60
    if h < 0: h += 360
    return h, s, v

print("=" * 70)
print("FRESNEL STUDY: Per-pixel color shift illusion in iRacing PBR")
print("=" * 70)

# Key insight: At GRAZING angles (ndotv -> 0), Fresnel drives ALL metals
# toward white. But the RATE depends on metallic value and F0.
# Higher metallic = more colored reflections head-on, whiter at grazing
# Lower metallic = more diffuse (holds paint color), weaker Fresnel

print("\n--- EXPERIMENT 1: Same teal paint, varying metallic ---")
paint = [0.0, 0.55, 0.45]
for M in [0.5, 0.7, 0.85, 0.95]:
    c_head = sim(paint, M, 0.08, 16, 0.8)
    c_graze = sim(paint, M, 0.08, 16, 0.15)
    h1, s1, v1 = rgb_to_hsv(*c_head)
    h2, s2, v2 = rgb_to_hsv(*c_graze)
    print(f"  M={M:.2f}: Head-on HSV=({h1:.0f}, {s1:.2f}, {v1:.2f}) | Grazing HSV=({h2:.0f}, {s2:.2f}, {v2:.2f}) | Sat drop: {s1-s2:.2f}")

print("\n--- EXPERIMENT 2: Pixel A (teal, high M) vs Pixel B (purple, lower M) ---")
print("  The question: from different angles, which pixel DOMINATES visually?")
angles = [("Head-on", 0.9), ("Normal", 0.6), ("Steep", 0.3), ("Grazing", 0.1)]

# Pixel A: Teal, very metallic, very smooth
# Pixel B: Purple, less metallic, slightly rougher
for name, ndv in angles:
    ca = sim([0.0, 0.55, 0.45], 0.94, 0.06, 16, ndv)
    cb = sim([0.55, 0.1, 0.65], 0.65, 0.18, 20, ndv)
    ha, sa, va = rgb_to_hsv(*ca)
    hb, sb, vb = rgb_to_hsv(*cb)
    brightness_a = sum(ca)/3
    brightness_b = sum(cb)/3
    print(f"  {name:8s} (ndv={ndv:.1f}): A=teal  HSV({ha:5.0f},{sa:.2f},{va:.2f}) bright={brightness_a:.3f}")
    print(f"  {' ':8s}           B=purpl HSV({hb:5.0f},{sb:.2f},{vb:.2f}) bright={brightness_b:.3f}")
    if brightness_a > brightness_b:
        print(f"  {' ':8s}           >>> A is {brightness_a/brightness_b:.1f}x brighter (teal dominates)")
    else:
        print(f"  {' ':8s}           >>> B is {brightness_b/brightness_a:.1f}x brighter (purple dominates)")
    print()

print("\n--- EXPERIMENT 3: The REAL trick - what if we INVERT the relationship? ---")
print("  Make Color A bright head-on but dark at grazing")
print("  Make Color B dark head-on but bright at grazing")
print("  This maximizes the perceived 'shift'!")
print()

# Strategy:
# Color A pixels: bright saturated paint + moderate metallic + low roughness
#   -> Head-on: visible colored reflections
#   -> Grazing: Fresnel washes to white (color lost)
# Color B pixels: darker paint + lower metallic + higher roughness
#   -> Head-on: dim (low metallic = weak reflections, roughness scatters)
#   -> Grazing: retains more of its diffuse color since lower metallic

# BUT WAIT - the real trick might be DIFFERENT:
# What if BOTH are high metallic, but one is SMOOTH and one is ROUGH?
# Smooth: sharp reflections that pick up environment color (overpower paint)
# Rough: diffuse metallic that shows paint color more

print("  Strategy: Both high metallic, but vary roughness per-color")
print("  Color A (teal): M=0.92, R=0.05 (mirror-smooth, reflects environment)")
print("  Color B (purple): M=0.88, R=0.25 (rough metallic, shows paint color)")
print()
for name, ndv in angles:
    ca = sim([0.0, 0.55, 0.45], 0.92, 0.05, 16, ndv)
    cb = sim([0.55, 0.1, 0.65], 0.88, 0.25, 16, ndv)
    ha, sa, va = rgb_to_hsv(*ca)
    hb, sb, vb = rgb_to_hsv(*cb)
    print(f"  {name:8s}: A=({ca[0]:.2f},{ca[1]:.2f},{ca[2]:.2f}) sat={sa:.2f} | B=({cb[0]:.2f},{cb[1]:.2f},{cb[2]:.2f}) sat={sb:.2f}")

print()
print("\n--- EXPERIMENT 4: Checkerboard pixel mixing ---")
print("  If pixels A and B are interleaved like a checkerboard,")
print("  the eye averages them. As angle changes, the dominant")
print("  visible color shifts because A and B respond differently.")
print()

# At each angle, compute the AVERAGE apparent color of 50/50 mix
for name, ndv in angles:
    ca = sim([0.0, 0.55, 0.45], 0.92, 0.05, 16, ndv)
    cb = sim([0.55, 0.1, 0.65], 0.88, 0.25, 16, ndv)
    avg = (ca + cb) / 2.0
    h, s, v = rgb_to_hsv(*avg)
    print(f"  {name:8s}: Avg color = ({avg[0]:.3f},{avg[1]:.3f},{avg[2]:.3f}) HSV=({h:.0f},{s:.2f},{v:.2f})")

print()
print("\n--- EXPERIMENT 5: What about DITHERED mixing at various ratios? ---")
print("  Instead of 50/50, use gradient field to vary the RATIO of A vs B pixels")
print("  Region with 80% A pixels: appears mostly teal")
print("  Region with 80% B pixels: appears mostly purple")
print("  The FRESNEL handles the angle-dependent shift within each pixel!")
print()

for ratio_a in [0.9, 0.7, 0.5, 0.3, 0.1]:
    print(f"  Ratio A={ratio_a:.1f}, B={1-ratio_a:.1f}:")
    for name, ndv in [("Head-on", 0.9), ("Grazing", 0.1)]:
        ca = sim([0.0, 0.55, 0.45], 0.92, 0.05, 16, ndv)
        cb = sim([0.55, 0.1, 0.65], 0.88, 0.25, 16, ndv)
        avg = ca * ratio_a + cb * (1 - ratio_a)
        h, s, v = rgb_to_hsv(*avg)
        print(f"    {name:8s}: HSV=({h:5.0f}, {s:.2f}, {v:.2f}) RGB=({avg[0]:.2f},{avg[1]:.2f},{avg[2]:.2f})")
    print()

print("\n--- EXPERIMENT 6: PURE Fresnel shift - same paint, different spec ---")
print("  What if we DON'T change paint color at all?")
print("  Just alternate spec properties per-pixel on GRAY paint?")
print("  Pixel A: Gray + M=0.95, R=0.03, CC=16 (chrome-like)")
print("  Pixel B: Gray + M=0.60, R=0.30, CC=30 (satin)")
print()

gray = [0.55, 0.55, 0.55]
for name, ndv in angles:
    ca = sim(gray, 0.95, 0.03, 16, ndv)
    cb = sim(gray, 0.60, 0.30, 30, ndv)
    avg = (ca + cb) / 2.0
    print(f"  {name:8s}: Chrome=({ca[0]:.2f},{ca[1]:.2f},{ca[2]:.2f}) Satin=({cb[0]:.2f},{cb[1]:.2f},{cb[2]:.2f}) Avg=({avg[0]:.2f},{avg[1]:.2f},{avg[2]:.2f})")

print()
print("  ^ No hue shift possible on gray - need colored paint for hue change")

print("\n" + "=" * 70)
print("CONCLUSION: The winning strategy for color-shift illusion")
print("=" * 70)
print("""
The key insight from iRacing's PBR:

1. PAINT COLOR determines the HUE of metallic reflections (F0 = albedo for metals)
2. METALLIC value determines how much paint color affects reflections vs diffuse
3. ROUGHNESS determines how sharp/scattered reflections are
4. At GRAZING angles, Fresnel drives everything toward white

THE TRICK: Create a DITHERED pixel pattern where:
- "Color A" pixels: paint=Color1, M=HIGH(0.92), R=LOW(0.05), CC=16
    -> Head-on: vivid Color1 reflections
    -> Grazing: washes to white/silver (Color1 lost)
- "Color B" pixels: paint=Color2, M=MODERATE(0.80), R=HIGHER(0.20), CC=20
    -> Head-on: slightly dimmer Color2 (roughness diffuses it)
    -> Grazing: RETAINS Color2 better (lower metallic = more diffuse hold)

RESULT:
- Head-on: Color A dominates (brighter, sharper reflections)
- Grazing: Color B emerges (holds its color while A fades to white)
- Movement: Camera orbiting the car crosses through different NdotV zones,
  making different regions shift between Color A and Color B dominance

The GRADIENT FIELD controls the RATIO of A-to-B pixels spatially,
creating large visible color regions. The DITHERING at pixel level
creates the angle-dependent shift within each region.

This is FUNDAMENTALLY different from what we were doing before:
- Before: painted colors + generic high-metallic spec = just a colorful chrome car
- Now: CORRELATED per-pixel paint+spec pairs that exploit Fresnel differentially
""")
