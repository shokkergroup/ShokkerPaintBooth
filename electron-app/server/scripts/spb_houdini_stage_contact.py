"""Build compact visual contact sheets for staged FRACTURED HOUDINI cards.

This is evidence for catalog/picker-scale owner-eye review.  It does not
promote cards or claim the required real-track lighting validation.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "_houdini_proof"
SOURCES = {
    "standard": ROOT / "_houdini_thumb_stage_20260830" / "monolithic",
    "picker": ROOT / "_houdini_picker_stage_20260830" / "picker_split" / "monolithic",
}


def make_sheet(label: str, source: Path) -> Path:
    files = sorted(source.glob("houdini_*.png"))
    if len(files) != 20:
        raise RuntimeError(f"expected 20 Houdini {label} cards, found {len(files)}")
    cols, pad, label_h = 5, 8, 25
    first = cv2.imread(str(files[0]), cv2.IMREAD_COLOR)
    h, w = first.shape[:2]
    rows = (len(files) + cols - 1) // cols
    sheet = np.full((rows * (h + label_h + pad) + pad, cols * (w + pad) + pad, 3), 14, np.uint8)
    for index, path in enumerate(files):
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"could not read {path}")
        row, col = divmod(index, cols)
        x, y = pad + col * (w + pad), pad + row * (h + label_h + pad)
        sheet[y:y + h, x:x + w] = image
        name = path.stem.removeprefix("houdini_").replace("_", " ").upper()
        cv2.putText(sheet, name, (x + 3, y + h + 17), cv2.FONT_HERSHEY_SIMPLEX,
                    .39, (230, 230, 230), 1, cv2.LINE_AA)
    out = PROOF / f"houdini_{label}_stage_contact_r7.png"
    cv2.imwrite(str(out), sheet)
    return out


if __name__ == "__main__":
    PROOF.mkdir(exist_ok=True)
    for kind, directory in SOURCES.items():
        print(f"{kind}={make_sheet(kind, directory)}")
