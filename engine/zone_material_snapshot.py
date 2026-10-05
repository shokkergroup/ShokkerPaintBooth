"""Lossless, portable material content for independent Zone copies (SPB-93)."""
import base64
import zlib
import numpy as np

FORMAT = 'spb-zone-material/1'
MAX_PIXELS = 4096 * 4096

def encode(paint, spec, coverage, paint_coverage):
    h, w = coverage.shape
    # Unowned source artwork is not part of a material copy, even as inert data.
    owned_paint = np.where(paint_coverage[:,:,None] > 0, paint, 0)
    owned_spec = np.where(coverage[:,:,None] > 0, spec, 0)
    raw = (np.ascontiguousarray(owned_paint, dtype=np.uint8).tobytes()
           + np.ascontiguousarray(owned_spec, dtype=np.uint8).tobytes()
           + np.ascontiguousarray(coverage, dtype='<f4').tobytes()
           + np.ascontiguousarray(paint_coverage, dtype='<f4').tobytes())
    return dict(format=FORMAT, width=w, height=h,
                data=base64.b64encode(zlib.compress(raw)).decode('ascii'))

def decode(value):
    if not isinstance(value, dict) or value.get('format') != FORMAT:
        raise ValueError('Invalid Zone material snapshot')
    w, h = value.get('width'), value.get('height')
    if type(w) is not int or type(h) is not int or min(w, h) <= 0 or w*h > MAX_PIXELS:
        raise ValueError('Invalid Zone material dimensions')
    n = w*h
    compressed = base64.b64decode(value.get('data', ''), validate=True)
    decoder = zlib.decompressobj()
    raw = decoder.decompress(compressed, n*15+1)
    if len(raw) != n*15 or not decoder.eof or decoder.unused_data:
        raise ValueError('Invalid Zone material content length')
    paint = np.frombuffer(raw, np.uint8, n*3).reshape(h,w,3)
    spec = np.frombuffer(raw, np.uint8, n*4, n*3).reshape(h,w,4)
    coverage = np.frombuffer(raw, '<f4', n, n*7).reshape(h,w)
    paint_coverage = np.frombuffer(raw, '<f4', n, n*11).reshape(h,w)
    if any(not np.isfinite(a).all() or (a < 0).any() or (a > 1).any() for a in (coverage,paint_coverage)):
        raise ValueError('Invalid Zone material coverage')
    return paint, spec, coverage, paint_coverage
