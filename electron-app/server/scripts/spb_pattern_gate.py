"""SPB PATTERN ANTI-RECYCLE GATE (2026-06-22)
Renders each PROCEDURAL pattern's texture (pattern_val) and compares whole-image
STRUCTURE with the whitened FFT+edge gestalt metric (same method as the finish
gate). Two patterns flag as SAME-DESIGN when struct_sim >= threshold — i.e. they
render the same design (recolor doesn't count, since pattern_val is colorless).
Image-based patterns are skipped (they're unique by file).

Usage:
  python scripts/spb_pattern_gate.py                 # all procedural patterns
  python scripts/spb_pattern_gate.py --ids tron roll_cage ...
  python scripts/spb_pattern_gate.py --struct-thresh 0.95 --top 40
Exit 1 if any SAME-DESIGN pair is found.
"""
import argparse, os, sys
import numpy as np
import cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _u(v):
    v = v.astype(np.float32); n = np.linalg.norm(v)
    return v if n < 1e-9 else v / n


def struct_sig(g01):
    g = g01.astype(np.float32)
    F = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(g - g.mean()))))
    F = _u(cv2.resize(F, (28, 28)).ravel())
    gy, gx = np.gradient(g); mag = np.hypot(gx, gy); ang = (np.arctan2(gy, gx) + np.pi)
    oh, _ = np.histogram(ang, bins=24, range=(0, 2 * np.pi), weights=mag); oh = _u(oh)
    return np.concatenate([F * 0.72, oh * 0.28]).astype(np.float32)


def _whiten(M):
    M = M - M.mean(axis=0, keepdims=True)
    return M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)


def render_pv(entry, res):
    fn = entry.get("texture_fn")
    if fn is None:
        return None
    try:
        tex = fn((res, res), np.ones((res, res), np.float32), 7, 1.0)
        pv = tex["pattern_val"] if isinstance(tex, dict) else tex
        pv = np.asarray(pv, np.float32)
        if pv.ndim == 3:
            pv = pv[..., :3].mean(2)
        lo, hi = float(pv.min()), float(pv.max())
        return (pv - lo) / (hi - lo) if hi - lo > 1e-6 else pv * 0
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", default=None)
    ap.add_argument("--res", type=int, default=144)
    ap.add_argument("--struct-thresh", type=float, default=0.95)
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    import shokker_engine_v2 as E
    PR = E.PATTERN_REGISTRY
    if a.ids:
        ids = [i for i in a.ids if i in PR]
    else:
        ids = sorted(k for k, v in PR.items() if isinstance(v, dict) and v.get("texture_fn") is not None and not v.get("image_path"))
    print(f"[pattern-gate] {len(ids)} procedural patterns @ {a.res}px", flush=True)
    sigs, keep = [], []
    for pid in ids:
        pv = render_pv(PR[pid], a.res)
        if pv is None:
            continue
        sigs.append(struct_sig(pv)); keep.append(pid)
    S = _whiten(np.array(sigs)); SM = S @ S.T; np.fill_diagonal(SM, -1)
    pairs = []
    for i in range(len(keep)):
        for j in range(i + 1, len(keep)):
            pairs.append((float(SM[i, j]), keep[i], keep[j]))
    pairs.sort(reverse=True)
    same = [p for p in pairs if p[0] >= a.struct_thresh]
    print(f"\n  top {a.top} most-similar pairs (struct_sim):", flush=True)
    for s, x, y in pairs[:a.top]:
        print(f"    {s:.3f}  {x} ~ {y}{'   SAME-DESIGN' if s >= a.struct_thresh else ''}", flush=True)
    print(f"\n  SAME-DESIGN pairs (>= {a.struct_thresh}): {len(same)}", flush=True)
    return 1 if same else 0


if __name__ == "__main__":
    sys.exit(main())
