"""SPB GESTALT UNIQUENESS GATE  (anti-recycle wall, 2026-06-22)
================================================================
The OLD uniqueness gate compared downsampled PIXELS, which is position-sensitive:
the same pattern design shifted a few pixels (or facet cells in different spots)
scored as "unique" though it looks identical. That blind spot let recycled
designs through. This gate compares each WHOLE image's STRUCTURE position-
independently (FFT log-magnitude spectrum + edge-orientation histogram) AND its
coarse COLOR layout, so it catches what the eye catches.

Two metrics per pair:
  struct_sim : color-independent design identity  (same pattern -> high, even if recolored)
  color_sim  : coarse color layout               (same colors  -> high)

Flags:
  SAME-DESIGN  struct_sim >= --struct-thresh (default 0.95)  -> two finishes share a
               pattern design (recolor). Owner rule: "ZERO point to build two with the
               same pattern design EVER" -> review/redesign one.
  TRUE-DUPE    struct_sim AND color_sim both high            -> a literal recolor.

Usage:
  python scripts/spb_gestalt_gate.py --prefix grad_
  python scripts/spb_gestalt_gate.py --ids cs_red_gold cs_blue_orange ...
  python scripts/spb_gestalt_gate.py --prefix msh --res 160 --struct-thresh 0.96
Exit code 1 if any SAME-DESIGN pair is found (so it can gate a build).
"""
import argparse
import os
import sys
import numpy as np
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _u(v):
    v = v.astype(np.float32); n = np.linalg.norm(v)
    return v if n < 1e-9 else v / n


def struct_sig(rgb):
    """Color-independent RAW design features (FFT spectrum + edge orientation).
    Returned UN-whitened; the dataset mean is removed in main() so the common
    1/f texture baseline cancels and only distinctive structure remains (that is
    what gives the metric real dynamic range)."""
    g = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    F = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(g - g.mean()))))
    F = _u(cv2.resize(F, (28, 28)).ravel())
    gy, gx = np.gradient(g); mag = np.hypot(gx, gy); ang = (np.arctan2(gy, gx) + np.pi)
    oh, _ = np.histogram(ang, bins=24, range=(0, 2 * np.pi), weights=mag); oh = _u(oh)
    return np.concatenate([F * 0.72, oh * 0.28]).astype(np.float32)


def color_sig(rgb):
    """RAW coarse color layout (hue-aware). Whitened in main()."""
    cl = _u(cv2.resize(np.clip(rgb, 0, 1), (8, 8)).ravel() - 0.5)
    hsv = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    hh, _ = np.histogram(hsv[..., 0].ravel(), bins=24, range=(0, 180),
                         weights=(hsv[..., 1].ravel() / 255.0)); hh = _u(hh)
    return np.concatenate([cl * 0.6, hh * 0.4]).astype(np.float32)


def _whiten_norm(M):
    """Remove the dataset-mean (common baseline) then L2-normalize rows."""
    M = M - M.mean(axis=0, keepdims=True)
    n = np.linalg.norm(M, axis=1, keepdims=True)
    return M / (n + 1e-9)


def _render(E, fid, res):
    if fid in E.MONOLITHIC_REGISTRY:
        _spec, pf = E.MONOLITHIC_REGISTRY[fid]
    elif fid in E.BASE_REGISTRY and isinstance(E.BASE_REGISTRY[fid], dict):
        pf = E.BASE_REGISTRY[fid].get("paint_fn")
    else:
        return None
    if pf is None:
        return None
    col = pf(np.zeros((res, res, 3), np.float32), (res, res), np.ones((res, res), np.float32), 7, 1.0, 0.0)
    return np.clip(np.asarray(col, np.float32)[:, :, :3], 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", default=None)
    ap.add_argument("--prefix", default=None)
    ap.add_argument("--res", type=int, default=144)
    ap.add_argument("--struct-thresh", type=float, default=0.95)
    ap.add_argument("--color-thresh", type=float, default=0.92)
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()

    import shokker_engine_v2 as E
    if args.ids:
        ids = list(args.ids)
    elif args.prefix:
        ids = sorted(set([k for k in E.MONOLITHIC_REGISTRY if k.startswith(args.prefix)] +
                         [k for k in E.BASE_REGISTRY if k.startswith(args.prefix)]))
    else:
        print("give --ids or --prefix"); return 2
    print(f"[gestalt-gate] {len(ids)} finishes @ {args.res}px", flush=True)

    ss, cs, keep = [], [], []
    for fid in ids:
        rgb = _render(E, fid, args.res)
        if rgb is None:
            print(f"  skip (unregistered): {fid}"); continue
        ss.append(struct_sig(rgb)); cs.append(color_sig(rgb)); keep.append(fid)
    if len(keep) < 2:
        print("  nothing to compare"); return 0
    S = _whiten_norm(np.array(ss)); C = _whiten_norm(np.array(cs))   # whiten => real dynamic range
    SM = S @ S.T; CM = C @ C.T
    np.fill_diagonal(SM, -1)
    pairs = []
    for i in range(len(keep)):
        for j in range(i + 1, len(keep)):
            pairs.append((float(SM[i, j]), float(CM[i, j]), keep[i], keep[j]))
    pairs.sort(reverse=True)
    same = [p for p in pairs if p[0] >= args.struct_thresh]
    dupe = [p for p in same if p[1] >= args.color_thresh]
    print(f"\n  top {args.top} by struct_sim (struct / color):")
    for s, c, a, b in pairs[:args.top]:
        tag = "  TRUE-DUPE" if (s >= args.struct_thresh and c >= args.color_thresh) else ("  SAME-DESIGN" if s >= args.struct_thresh else "")
        print(f"    {s:.3f} / {c:.3f}  {a} ~ {b}{tag}", flush=True)
    print(f"\n  SAME-DESIGN pairs (struct>={args.struct_thresh}): {len(same)}   TRUE-DUPE: {len(dupe)}", flush=True)
    return 1 if same else 0


if __name__ == "__main__":
    sys.exit(main())
