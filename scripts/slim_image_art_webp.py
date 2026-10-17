"""slim_image_art_webp.py - ship the picture finishes' art as lossless WebP, pixel-identical.

[11.0.2 slim download 2026-10-16, Claude] Owner: "Keep everything offline except the big
hover previews, about 7 GB." The ~200 picture finishes (era_image_2026, all_that_image_2026,
flaw_lab_rebuild_2026) load 2048x2048 PNG art with cv2.imdecode(..., IMREAD_COLOR). A
lossless WebP of that exact decode gives the renderer the SAME pixels at a fraction of the
size. The PNGs stay in the tree as source art; the installer ships only the WebP twins.

  convert  write <fid>_<kind>.webp beside every PNG, verified decode-equal; resumable
  check    build gate: every PNG has a decode-equal WebP twin (non-zero exit otherwise)
  patch    point the three loaders at the WebP twin, PNG as fallback (idempotent)
"""
from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ('era_image_2026', 'all_that_image_2026', 'flaw_lab_rebuild_2026')
HELPER = (
    "def _asset(fid,kind):\n"
    "    # [11.0.2 slim download 2026-10-16, Claude] lossless WebP twin (pixel-identical under\n"
    "    # IMREAD_COLOR, gated by scripts/slim_image_art_webp.py check); PNG is the fallback.\n"
    "    webp=HERE/'assets'/f'{fid}_{kind}.webp'\n"
    "    return webp if webp.is_file() else HERE/'assets'/f'{fid}_{kind}.png'\n\n")
EDITS = (
    ("path=HERE/'assets'/f'{fid}_{kind}.png'", "path=_asset(fid,kind)"),
    ("(HERE/'assets'/f'{fid}_{k}.png').stat().st_mtime_ns", "_asset(fid,k).stat().st_mtime_ns"),
    ("(HERE/'assets'/f'{fid}_{k}.png').is_file()", "_asset(fid,k).is_file()"),
)


def art(root):
    return sorted(p for pkg in PACKAGES for p in (root / 'engine' / 'paint_v2' / pkg / 'assets').glob('*.png'))


def _decode(path):
    import cv2
    import numpy as np
    return cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), cv2.IMREAD_COLOR)


def twin_ok(png):
    import numpy as np
    webp = png.with_suffix('.webp')
    if not webp.is_file():
        return False
    a, b = _decode(png), _decode(webp)
    return a is not None and b is not None and a.shape == b.shape and np.array_equal(a, b)


def convert_one(png):
    png = Path(png)
    if twin_ok(png):
        return str(png), 'kept', png.with_suffix('.webp').stat().st_size
    import cv2
    pixels = _decode(png)
    if pixels is None:
        return str(png), 'unreadable', 0
    ok, data = cv2.imencode('.webp', pixels, [cv2.IMWRITE_WEBP_QUALITY, 101])   # >100 = lossless
    if not ok:
        return str(png), 'encode-failed', 0
    tmp = png.with_suffix('.webp.tmp')
    tmp.write_bytes(data.tobytes())
    os.replace(tmp, png.with_suffix('.webp'))
    if not twin_ok(png):
        png.with_suffix('.webp').unlink()   # never leave a twin that differs
        return str(png), 'not-identical', 0
    return str(png), 'written', len(data)


def convert(root, workers):
    files = art(root)
    before = sum(p.stat().st_size for p in files)
    after, bad = 0, []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for index, (name, status, size) in enumerate(pool.map(convert_one, files, chunksize=4), 1):
            after += size
            if status not in ('kept', 'written'):
                bad.append((name, status))
            if index % 50 == 0:
                print(f'  {index}/{len(files)} ...', flush=True)
    print(f'WEBP {"OK" if not bad else "FAIL"} - {len(files)} PNG {before / 1e9:.2f} GB -> WebP {after / 1e9:.2f} GB'
          + (f'; {len(bad)} kept as PNG only, e.g. {bad[0]}' if bad else ''))
    return int(bool(bad))


def check(root, workers):
    files = art(root)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        missing = [str(p) for p, ok in zip(files, pool.map(twin_ok, files, chunksize=4)) if not ok]
    if not files or missing:
        print(f'FAIL: {len(missing)}/{len(files)} picture-finish PNGs lack a decode-equal WebP twin'
              + (f', e.g. {missing[0]}' if missing else '') + '. Run: py -3 scripts/slim_image_art_webp.py convert')
        return 1
    print(f'WEBP TWINS OK - {len(files)}/{len(files)} pixel-identical')
    return 0


def patch(root):
    for pkg in PACKAGES:
        init = root / 'engine' / 'paint_v2' / pkg / '__init__.py'
        text = init.read_text(encoding='utf8')
        if 'def _asset(fid,kind):' in text:
            print(f'{pkg}: already patched')
            continue
        for old, new in EDITS:
            if text.count(old) != 1:
                print(f'FAIL: {pkg}/__init__.py does not contain exactly one {old!r}; nothing written')
                return 1
            text = text.replace(old, new)
        anchor = '@lru_cache(maxsize=4)\n'
        if text.count(anchor) != 1:
            print(f'FAIL: {pkg}/__init__.py has no single {anchor.strip()} anchor; nothing written')
            return 1
        text = text.replace(anchor, HELPER + anchor)
        tmp = init.with_suffix('.py.tmp')
        tmp.write_text(text, encoding='utf8')
        os.replace(tmp, init)
        print(f'{pkg}: patched')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('mode', choices=('convert', 'check', 'patch'))
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--workers', type=int, default=max(1, min(8, (os.cpu_count() or 2) - 1)))
    args = parser.parse_args(argv)
    if args.mode == 'patch':
        return patch(args.root)
    return (convert if args.mode == 'convert' else check)(args.root, args.workers)


if __name__ == '__main__':
    sys.exit(main())
