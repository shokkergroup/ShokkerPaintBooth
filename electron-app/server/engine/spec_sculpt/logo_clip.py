"""Optional CLIP-probe GRAPHIC-LOGO detector for the SPONSORS layer (2026-06-27).

OCR catches TEXT sponsors; this catches GRAPHIC-only logos (mascots, brand emblems, contingency
icon-marks) that have no readable text. A small classifier head, trained on CLIP image embeddings of
labeled logo-vs-paint crops, scores candidate regions — the supervised approach that finally beat the
logo-vs-paint-art ambiguity (held-out 0.93 acc; ~3.3x region separation; never grabs the paint design).

FULLY GRACEFUL + OPT-IN: detection is DISABLED (returns None, zero behavior change) unless ALL of:
  - env SPB_LOGO_CLIP=1 (explicit enable), AND
  - `open_clip` + `torch` import, AND
  - the trained probe exists at _logo_data/probe.npz, AND the CLIP model loads.
So this file is safe to ship/import everywhere; it only activates where it's been set up + turned on.
"""
import os
import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROBE = os.path.join(_ROOT, "_logo_data", "probe.npz")
_STATE = None  # None=unloaded; ("off",) disabled; ("ok", torch, model, preprocess, net)


def available():
    return _load()[0] == "ok"


def _load():
    global _STATE
    if _STATE is not None:
        return _STATE
    if os.environ.get("SPB_LOGO_CLIP") != "1" or cv2 is None or not os.path.isfile(_PROBE):
        _STATE = ("off",); return _STATE
    try:
        import torch, open_clip, json
        cfg = {"clip_model": "ViT-B-32", "pretrained": "laion2b_s34b_b79k", "dim": 512}
        _mj = os.path.join(_ROOT, "_logo_data", "model.json")
        if os.path.isfile(_mj):
            try:
                cfg.update(json.load(open(_mj)))
            except Exception:
                pass
        model, _, pre = open_clip.create_model_and_transforms(cfg["clip_model"], pretrained=cfg["pretrained"])
        model = model.eval()
        W = np.load(_PROBE)
        net = torch.nn.Sequential(torch.nn.Linear(int(cfg["dim"]), 128), torch.nn.ReLU(),
                                  torch.nn.Dropout(0.0), torch.nn.Linear(128, 1))
        net.load_state_dict({"0.weight": torch.tensor(W["0.weight"]), "0.bias": torch.tensor(W["0.bias"]),
                             "3.weight": torch.tensor(W["3.weight"]), "3.bias": torch.tensor(W["3.bias"])})
        net.eval()
        _STATE = ("ok", torch, model, pre, net)
    except Exception:
        _STATE = ("off",)
    return _STATE


def _regions(rgb, work=1024):
    """Coarse busy-region proposals (best precision; the classifier rejects non-logo regions)."""
    H0, W0 = rgb.shape[:2]
    sc = work / float(max(H0, W0))
    img = cv2.resize(rgb, (int(W0 * sc), int(H0 * sc))) if sc < 1 else rgb
    H, Wd = img.shape[:2]
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, 3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, 3)
    busy = cv2.blur(np.sqrt(gx * gx + gy * gy), (7, 7))
    hi = busy > np.percentile(busy, 75)
    th = cv2.morphologyEx(hi.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(th, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        fr = a / float(H * Wd)
        if fr < 0.0005 or fr > 0.05 or w > 0.5 * Wd or h > 0.5 * H:
            continue
        # INTERNAL-DETAIL gate (2026-06-27 adversarial fix): a logo/decal is busy THROUGHOUT; a flat
        # body PANEL is busy only at its seam. Require enough high-edge pixels INSIDE the bbox so flat
        # panels (the dominant false-positive on fresh cars) are rejected before they reach the classifier.
        if float(hi[y:y + h, x:x + w].mean()) < 0.16:
            continue
        # also reject low-colour-variance interiors (solid panels) as a second guard
        sub = img[y:y + h, x:x + w].reshape(-1, 3)
        if sub.std(0).mean() < 14:
            continue
        out.append((x / sc, y / sc, w / sc, h / sc))
    return out


def detect_logo_mask(tex, thr=0.74, claimed=None, template=None):
    """Return a uint8 mask (255=graphic logo) at input resolution, or None if disabled/unavailable.
    `claimed`/`template` (uint8 masks) are subtracted so we only ADD genuinely new graphic-logo pixels.
    Conservative threshold (prefer-miss): a missed logo is a quick brush-fix; grabbing paint is not."""
    st = _load()
    if st[0] != "ok" or cv2 is None:
        return None
    _, torch, model, pre, net = st
    try:
        a = np.asarray(tex)
        rgb = (np.clip(a[:, :, :3], 0, 1) * 255).astype(np.uint8) if a.dtype != np.uint8 else a[:, :, :3]
        from PIL import Image
        bx = _regions(rgb)
        if not bx:
            return np.zeros(rgb.shape[:2], np.uint8)
        crops = []
        for (x, y, w, h) in bx:
            pad = int(0.2 * max(w, h))
            x0, y0 = max(0, int(x - pad)), max(0, int(y - pad))
            x1, y1 = min(rgb.shape[1], int(x + w + pad)), min(rgb.shape[0], int(y + h + pad))
            crops.append(pre(Image.fromarray(rgb[y0:y1, x0:x1])))
        with torch.no_grad():
            e = model.encode_image(torch.stack(crops)); e = e / e.norm(dim=-1, keepdim=True)
            p = torch.sigmoid(net(e).squeeze(1)).numpy()
        mask = np.zeros(rgb.shape[:2], np.uint8)
        for (x, y, w, h), pr in zip(bx, p):
            if pr > thr:
                cv2.rectangle(mask, (int(x), int(y)), (int(x + w), int(y + h)), 255, -1)
        if claimed is not None:
            mask[claimed > 0] = 0
        if template is not None:
            mask[template > 0] = 0
        return mask
    except Exception:
        return None
