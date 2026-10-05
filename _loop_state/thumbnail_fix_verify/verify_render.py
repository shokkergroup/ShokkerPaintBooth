"""Side-by-side verify: real-engine picker swatch vs legacy fake-painter swatch.

For each test finish:
  - Renders the new real-engine path (_render_picker_split_snapshot_bytes)
  - Renders the legacy fast-painter path (_render_fast_split_swatch_bytes)
  - Saves both PNGs side-by-side under _loop_state/thumbnail_fix_verify/

Run from project root:
  python _loop_state/thumbnail_fix_verify/verify_render.py
"""
import os
import sys
import io
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault('SHOKKER_SKIP_PICKER_PREBAKE', '1')

import server as s  # noqa: E402

OUT_DIR = os.path.join(ROOT, '_loop_state', 'thumbnail_fix_verify')
os.makedirs(OUT_DIR, exist_ok=True)

TESTS = [
    ('base',       'chrome',          'Base'),
    ('pattern',    'carbon_2x2',      'Pattern'),
    ('monolithic', 'depth_wave',      'Monolithic / Special'),
    ('monolithic', 'mc_fire_storm',   'MC (multi-coat)'),
    ('monolithic', 'grad_sunset',     'Gradient'),
]

SIZE = 96
SEED = 42
COLOR = '8a4242'


def _pick_existing(typ, key):
    """Resolve a fallback key if the canonical one is not in the registry."""
    reg = {
        'base': getattr(s.engine, 'BASE_REGISTRY', {}),
        'pattern': getattr(s.engine, 'PATTERN_REGISTRY', {}),
        'monolithic': getattr(s.engine, 'MONOLITHIC_REGISTRY', {}),
    }[typ]
    if key in reg:
        return key
    # try a prefix match for mc_/grad_
    prefix = key.split('_')[0] + '_'
    for k in reg:
        if k.startswith(prefix):
            return k
    # fallback: first available
    return next(iter(reg), key)


def main():
    print(f"Verify started {datetime.utcnow().isoformat()}Z")
    print(f"Output dir: {OUT_DIR}")
    rows = []
    for typ, key, label in TESTS:
        resolved = _pick_existing(typ, key)
        if resolved != key:
            print(f"  [{label}] {typ}/{key} not in registry; using {resolved}")
        try:
            new_png = s._render_picker_split_snapshot_bytes(typ, resolved, COLOR, SIZE, SEED)
        except Exception as e:
            new_png = None
            print(f"  [{label}] real-engine FAIL: {e}")
        try:
            old_png = s._render_fast_split_swatch_bytes(typ, resolved, COLOR, SIZE, SEED)
        except Exception as e:
            old_png = None
            print(f"  [{label}] fast-painter FAIL: {e}")
        if new_png:
            p = os.path.join(OUT_DIR, f"{typ}__{resolved}__new_engine.png")
            with open(p, 'wb') as f:
                f.write(new_png)
            print(f"  [{label}] wrote {os.path.basename(p)} ({len(new_png)} bytes)")
        if old_png:
            p = os.path.join(OUT_DIR, f"{typ}__{resolved}__old_painter.png")
            with open(p, 'wb') as f:
                f.write(old_png)
            print(f"  [{label}] wrote {os.path.basename(p)} ({len(old_png)} bytes)")
        rows.append({
            'category': label,
            'type': typ,
            'key': resolved,
            'new_engine_bytes': len(new_png) if new_png else 0,
            'old_painter_bytes': len(old_png) if old_png else 0,
            'new_engine_ok': bool(new_png),
            'old_painter_ok': bool(old_png),
        })
        # Stitch side-by-side comparison
        if new_png and old_png:
            try:
                from PIL import Image
                im_new = Image.open(io.BytesIO(new_png)).convert('RGB')
                im_old = Image.open(io.BytesIO(old_png)).convert('RGB')
                h = max(im_new.height, im_old.height)
                w_total = im_new.width + im_old.width + 4
                combo = Image.new('RGB', (w_total, h + 14), (40, 40, 40))
                combo.paste(im_old, (0, 14))
                combo.paste(im_new, (im_old.width + 4, 14))
                from PIL import ImageDraw
                d = ImageDraw.Draw(combo)
                d.text((4, 0), f"OLD (fake) | NEW (engine)  {typ}/{resolved}", fill=(220, 220, 220))
                p = os.path.join(OUT_DIR, f"_compare__{typ}__{resolved}.png")
                combo.save(p, 'PNG')
                print(f"  [{label}] wrote {os.path.basename(p)}")
            except Exception as e:
                print(f"  [{label}] compose FAIL: {e}")
    print()
    print("Summary:")
    for r in rows:
        print(f"  {r['category']:24s} {r['type']:11s} {r['key']:30s}  new={r['new_engine_bytes']:6d}  old={r['old_painter_bytes']:6d}")


if __name__ == '__main__':
    main()
