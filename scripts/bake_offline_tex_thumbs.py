# HELPER_V2 2026-10-04 owner: keep improving the Offline Helper.
# The guided builder's spec-texture choices (snakeskin / croc / dragon / fish scales, "shine only") used
# /api/spec-pattern-preview, a downsampled M/R/Cc split: at 160 px every one of these fine 2048-scale fields
# averages to the same flat grey, so the four choices looked like clones. This bakes a 1:1 DETAIL crop of the
# real spec field (no downsampling) and shades it as a lit metal coupon so each texture's own shape shows.
# Output: thumbnails/offline_builder_tex/<spec_id>.png (thumbnails/ ships with the app).
# Run: python scripts/bake_offline_tex_thumbs.py [ids...]
import os, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, 'thumbnails', 'offline_builder_tex')
IDS = sys.argv[1:] or ['snake_scale_diamond', 'spec_snake_scales', 'croc_delta_armor', 'dragon_scale_macro', 'spec_fish_scales']
CROP, SIZE = 192, 192          # 1:1 pixels from the 2048 canvas = what the buyer sees on the car


def shade(fields, applied):
    a = applied.astype(np.float32) / 255.0
    m, r, cc = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    # stretch each channel inside the crop so the texture's structure carries the picture
    def st(x):
        lo, hi = np.percentile(x, 2), np.percentile(x, 98)
        return np.clip((x - lo) / max(hi - lo, 1e-4), 0, 1)
    ms, rs, cs = st(m), st(r), st(cc)
    # a lit metal coupon: metal + smooth = bright cool highlight, rough = dark warm grit, coat = soft sheen
    light = 0.18 + 0.62 * ms * (1 - 0.7 * rs) + 0.18 * (1 - cs)
    rgb = np.stack([light * 0.92 + 0.05 * rs, light * 0.96, light * 1.06 - 0.04 * rs], axis=2)
    return np.uint8(np.clip(rgb, 0, 1) * 255)


def main():
    from engine.spec_overlay_v2.preview import render_native
    os.makedirs(OUT, exist_ok=True)
    for pid in IDS:
        fields, applied = render_native(pid)
        y0 = x0 = 1024 - CROP // 2
        img = shade(fields, applied[y0:y0 + CROP, x0:x0 + CROP])
        Image.fromarray(img, 'RGB').resize((SIZE, SIZE), Image.NEAREST).save(os.path.join(OUT, pid + '.png'), optimize=True)
        print('OK', pid)


if __name__ == '__main__':
    main()
