# -*- coding: utf-8 -*-
"""Mine current app thumbnails for topology outliers versus 17 Wilds survivors.

Color is deliberately suppressed. The descriptor combines normalized grayscale
mass, multi-threshold edges, local contrast and log-FFT structure. Results are
evidence for unused process families, never assets to copy directly.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_wilds_fullres_progress_20260824" / "visual_outlier_mine_20260825"
MONTAGE = ROOT / "_wilds_fullres_progress_20260824" / "accepted_runtime_rollout" / "accepted_17_paint_montage.png"
SOURCES = [ROOT / "thumbnails" / "base", ROOT / "thumbnails" / "monolithic", ROOT / "thumbnails" / "pattern"]


def descriptor(bgr):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (128, 128), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    mean, std = float(gray.mean()), float(gray.std())
    z = (gray - mean) / max(std, .035)
    mass = cv2.resize(z, (20, 20), interpolation=cv2.INTER_AREA).ravel()
    blur1 = cv2.GaussianBlur(gray, (0, 0), 1.2)
    blur3 = cv2.GaussianBlur(gray, (0, 0), 3.2)
    local = cv2.resize(blur1 - blur3, (24, 24), interpolation=cv2.INTER_AREA).ravel() * 4
    gx = cv2.Sobel(blur1, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blur1, cv2.CV_32F, 0, 1, ksize=3)
    edge = cv2.resize(np.hypot(gx, gy), (24, 24), interpolation=cv2.INTER_AREA).ravel() * 3
    fft = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(z))))
    cy, cx = np.array(fft.shape) // 2
    fft[cy-2:cy+3, cx-2:cx+3] = 0
    freq = cv2.resize(fft.astype(np.float32), (20, 20), interpolation=cv2.INTER_AREA).ravel()
    freq = (freq - freq.mean()) / max(float(freq.std()), .05)
    vec = np.concatenate((mass, local, edge, freq, np.asarray([mean, std, np.mean(edge), np.std(edge)])))
    vec /= max(float(np.linalg.norm(vec)), 1e-6)
    return vec.astype(np.float32), mean, std


def accepted_descriptors():
    im = cv2.imread(str(MONTAGE))
    h, w = im.shape[:2]
    cell_w, cell_h = w // 5, h // 4
    rows = []
    for index in range(17):
        row, col = divmod(index, 5)
        crop = im[row * cell_h:row * cell_h + cell_w, col * cell_w:(col + 1) * cell_w]
        rows.append(descriptor(crop)[0])
    return np.stack(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    accepted = accepted_descriptors()
    records, vectors = [], []
    for folder in SOURCES:
        for path in sorted(folder.glob("*.png")):
            im = cv2.imread(str(path))
            if im is None:
                continue
            vec, mean, std = descriptor(im)
            if std < .045 or mean < .035 or mean > .965:
                continue
            similarity = accepted @ vec
            records.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                            "family": folder.name, "name": path.stem,
                            "nearest_accepted_similarity": float(similarity.max()),
                            "outlier_score": float(1 - similarity.max()),
                            "mean": mean, "std": std})
            vectors.append(vec)
    matrix = np.stack(vectors)
    order = np.argsort([-r["outlier_score"] for r in records])[:500]
    # Greedy diversity within the strongest outlier pool.
    selected = [int(order[0])]
    while len(selected) < 48:
        pool = [int(i) for i in order if int(i) not in selected]
        sims = matrix[pool] @ matrix[selected].T
        novelty = 1 - sims.max(axis=1)
        quality = np.asarray([records[i]["outlier_score"] for i in pool])
        pick = pool[int(np.argmax(novelty * .72 + quality * .28))]
        selected.append(pick)
    result = [records[i] for i in selected]
    tiles = []
    for rank, rec in enumerate(result, 1):
        im = cv2.imread(str(ROOT / rec["path"]))
        tile = cv2.resize(im, (256, 256), interpolation=cv2.INTER_NEAREST)
        cv2.rectangle(tile, (0, 202), (256, 256), (0, 0, 0), -1)
        label = f"{rank:02d} {rec['family']}/{rec['name']}"
        if len(label) > 35:
            label = label[:34] + "…"
        cv2.putText(tile, label, (7, 224), cv2.FONT_HERSHEY_SIMPLEX, .42, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(tile, f"outlier {rec['outlier_score']:.3f}", (7, 246), cv2.FONT_HERSHEY_SIMPLEX, .42, (175, 220, 255), 1, cv2.LINE_AA)
        tiles.append(tile)
    montage = np.vstack([np.hstack(tiles[row * 8:(row + 1) * 8]) for row in range(6)])
    cv2.imwrite(str(OUT / "TOP_48_VISUAL_OUTLIERS.png"), montage)
    (OUT / "top_48.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"candidate_count": len(records), "selected": len(result), "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
