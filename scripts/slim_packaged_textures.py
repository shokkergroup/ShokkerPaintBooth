"""Shrink the reference / generated texture PNGs inside the PACKAGED server only (11.0.2 slim).

Owner 2026-10-16: "6GB" with picture quality kept. Each PNG under assets/reference_textures/ and
assets/generated/ in the packaged tree is re-encoded as lossless WebP *but keeps its .png name*:
89 engine modules and the finish-data JS name these files by path, and Pillow, OpenCV and Chromium
all pick the decoder from the file's first bytes, not its extension. A file is swapped only when
Pillow (same mode, same bytes) and OpenCV (IMREAD_UNCHANGED and IMREAD_COLOR) decode it back to the
exact original pixels; anything else (grayscale, palette, 16-bit, tRNS, no gain) keeps its PNG.

The repo copy is never touched - only electron-app/dist/win-unpacked (electron-builder afterPack,
see electron-app/after-pack-slim.js). Verified results are cached by source sha256 so rebuilds copy.

  python scripts/slim_packaged_textures.py apply --server <packaged server dir>
"""
import argparse, hashlib, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = ('assets/reference_textures', 'assets/generated')
MIN_GAIN = 0.97  # keep the PNG unless the WebP is at least 3% smaller


def is_webp(head):
    return head[:4] == b'RIFF' and head[8:12] == b'WEBP'


def _decode_all(data):
    import io
    import cv2, numpy as np
    from PIL import Image
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        pil = (im.mode, im.size, im.tobytes(), im.info.get('transparency'))
    buf = np.frombuffer(data, np.uint8)
    return pil, cv2.imdecode(buf, cv2.IMREAD_UNCHANGED), cv2.imdecode(buf, cv2.IMREAD_COLOR)


def convert(src_bytes):
    """Return verified lossless WebP bytes for src_bytes, or None to keep the PNG."""
    import cv2, numpy as np
    pil, raw, color = _decode_all(src_bytes)
    if pil[0] not in ('RGB', 'RGBA') or pil[3] is not None or raw is None or raw.dtype != np.uint8 \
            or raw.ndim != 3 or raw.shape[2] != (4 if pil[0] == 'RGBA' else 3):
        return None
    ok, enc = cv2.imencode('.webp', raw, [cv2.IMWRITE_WEBP_QUALITY, 101])
    if not ok or len(enc) > len(src_bytes) * MIN_GAIN:
        return None
    out = enc.tobytes()
    pil2, raw2, color2 = _decode_all(out)
    if pil2[:3] != pil[:3] or not np.array_equal(raw2, raw) or not np.array_equal(color2, color):
        return None
    return out


def _write(path, data):
    tmp = path.with_name(path.name + '.slim.tmp')
    tmp.write_bytes(data)
    os.replace(tmp, path)


def one(job):
    path, cache = Path(job[0]), Path(job[1])
    data = path.read_bytes()
    if is_webp(data[:12]):
        return 'already', len(data), len(data)
    key = hashlib.sha256(data).hexdigest()
    hit, keep = cache / (key + '.webp'), cache / (key + '.keep')
    if keep.exists():
        return 'kept', len(data), len(data)
    if not hit.exists():
        out = convert(data)
        if out is None:
            keep.write_bytes(b'')
            return 'kept', len(data), len(data)
        _write(hit, out)
    out = hit.read_bytes()
    _write(path, out)
    return 'webp', len(data), len(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['apply'])
    ap.add_argument('--server', required=True)
    ap.add_argument('--cache', default=str(ROOT / '_build_cache' / 'packaged_textures'))
    ap.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 4) - 2))
    a = ap.parse_args()
    server, cache = Path(a.server), Path(a.cache)
    if (server / '.git').exists() or server.resolve() in (ROOT, ROOT / 'electron-app' / 'server'):
        sys.exit('SLIM TEXTURES FAIL - refusing to rewrite a source tree: ' + str(server))
    cache.mkdir(parents=True, exist_ok=True)
    jobs = [(str(p), str(cache)) for d in DIRS for p in sorted((server / d).rglob('*.png'))]
    if not jobs:
        sys.exit('SLIM TEXTURES FAIL - no textures under ' + str(server))
    tally, before, after = {}, 0, 0
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for i, (kind, b, n) in enumerate(pool.map(one, jobs, chunksize=4), 1):
            tally[kind] = tally.get(kind, 0) + 1
            before += b; after += n
            if i % 100 == 0:
                print(f'  {i}/{len(jobs)} ...', flush=True)
    print(f'SLIM TEXTURES OK - {len(jobs)} files {before/1e9:.2f} GB -> {after/1e9:.2f} GB '
          f'({", ".join(f"{k} {v}" for k, v in sorted(tally.items()))})')


if __name__ == '__main__':
    main()
