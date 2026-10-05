"""Render audit swatches for all 30 Let Freedom Ring items via the REAL engine
paths, to thumbnails/audit/letfreedomring/<id>.png.

Conventions (matching the booth's own preview renderers in server.py):
- Spec overlays: LEFT = honest grayscale field (constant gain 2.5 around 0.5,
  NO per-pattern normalize), RIGHT = the real combined [M,R,Cc]->RGB spec.
- Patterns: LEFT = the engine's texture_fn+paint_fn on a neutral zone,
  RIGHT = the raw pattern_val motif field.
- Finishes: LEFT = paint_fn tile, RIGHT = real combined spec (M,R,Cc of the
  uint8 spec map -> RGB).
Also writes _lfr_audit_meta.json (id/name/desc/kind/ai_rating) for the page.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum")
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
OUT = os.path.join(ROOT, "thumbnails", "audit", "letfreedomring")
os.makedirs(OUT, exist_ok=True)
S = 512

draft = json.load(open(os.path.join(ROOT, "docs", "handoff", "lfr_content_draft_20260609.json"), encoding="utf-8"))
built = draft["result"]["built"] if "result" in draft else draft["built"]
META = {}
for kind, cat in zip(("spec_overlay", "pattern", "finish"), built):
    for it in cat["items"]:
        META[it["id"]] = {"id": it["id"], "name": it["name"], "desc": it["desc"], "kind": kind}


def ai_rating(field):
    """Transparent heuristic 1-100: multi-band detail energy + contrast - clipping.
    NOT a quality judgment - a structure meter (owner rating is the real verdict)."""
    f = field.astype(np.float32)
    if f.ndim == 3:
        f = f.mean(axis=2)
    std = float(f.std())
    bands = 0.0
    for sigma in (1.5, 6.0, 24.0):
        lo = cv2.GaussianBlur(f, (0, 0), sigma)
        bands += min(float(np.abs(f - lo).mean()) / 0.04, 1.0)
        f = lo
    clip = float(((field <= 0.002) | (field >= 0.998)).mean())
    score = 30.0 + bands * 14.0 + min(std / 0.18, 1.0) * 22.0 - clip * 25.0
    return int(np.clip(round(score), 1, 100))


def label(bgr, text):
    cv2.rectangle(bgr, (0, bgr.shape[0] - 24), (bgr.shape[1] - 1, bgr.shape[0] - 1), (12, 12, 12), -1)
    cv2.putText(bgr, text, (8, bgr.shape[0] - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (210, 210, 210), 1, cv2.LINE_AA)
    return bgr


def save(pid, left_rgb, right_rgb, ltxt, rtxt):
    l = label(cv2.cvtColor((np.clip(left_rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), ltxt)
    r = label(cv2.cvtColor((np.clip(right_rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), rtxt)
    img = np.hstack([l, np.full((S, 4, 3), 24, np.uint8), r])
    path = os.path.join(OUT, pid + ".png")
    cv2.imwrite(path, img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    return path


# ---- spec overlays (engine/spec_patterns PATTERN_CATALOG; server honest-preview math) ----
from engine import spec_patterns as sp
SPEC_IDS = [i for i in META if META[i]["kind"] == "spec_overlay"]
for pid in SPEC_IDS:
    arr = np.asarray(sp.PATTERN_CATALOG[pid]((S, S), 42, 1.0), dtype=np.float32)
    gray = arr.mean(axis=2) if arr.ndim == 3 else arr
    honest = np.clip(0.5 + (gray - 0.5) * 2.5, 0, 1)        # server GAIN=2.5, no normalize
    left = np.dstack([honest] * 3)
    right = np.clip(arr[:, :, :3], 0, 1) if arr.ndim == 3 else np.dstack([gray, gray, 1.0 - gray])
    META[pid]["ai_rating"] = ai_rating(arr)
    save(pid, left, right, "honest field (gain 2.5)", "combined spec  R=M G=R B=Cc")
    print("spec   ", pid, "ai", META[pid]["ai_rating"])

# ---- patterns (engine pattern path: texture_fn + paint_fn) ----
from engine.pattern_expansion import NEW_PATTERNS
mask = np.ones((S, S), np.float32)
neutral = np.full((S, S, 3), 0.55, np.float32)
PAT_IDS = [i for i in META if META[i]["kind"] == "pattern"]
for pid in PAT_IDS:
    entry = NEW_PATTERNS[pid]
    bb = entry["texture_fn"]((S, S), mask, 42, 1.0)
    painted = entry["paint_fn"](neutral.copy(), (S, S), mask, 42, 1.0, bb)[:, :, :3]
    pv = np.clip(bb["pattern_val"], 0, 1)
    META[pid]["ai_rating"] = ai_rating(pv)
    save(pid, painted, np.dstack([pv] * 3), "painted on neutral zone", "pattern field")
    print("pattern", pid, "ai", META[pid]["ai_rating"])

# ---- finishes (monolithic registry: paint_fn + real uint8 spec) ----
from engine.registry import MONOLITHIC_REGISTRY
fmask = np.ones((S, S), np.float32)
fbase = np.full((S, S, 3), 0.5, np.float32)
FIN_IDS = [i for i in META if META[i]["kind"] == "finish"]
for fid in FIN_IDS:
    spec_fn, paint_fn = MONOLITHIC_REGISTRY[fid]
    painted = paint_fn(fbase.copy(), (S, S), fmask, 42, 1.0, {})[:, :, :3]
    spec = spec_fn((S, S), fmask, 42, 1.0)
    right = spec[:, :, :3].astype(np.float32) / 255.0
    META[fid]["ai_rating"] = ai_rating(painted)
    save(fid, painted, right, "paint", "spec  R=M G=R B=Cc")
    print("finish ", fid, "ai", META[fid]["ai_rating"])

json.dump(list(META.values()), open(os.path.join(ROOT, "scripts", "lfr_audit_meta.json"), "w", encoding="utf-8"), indent=1)
print("DONE: %d swatches -> %s" % (len(META), OUT))
