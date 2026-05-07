#!/usr/bin/env python3
"""Extract poster title + tagline from Union Jacked footer strips via OCR.

**Engines:**

1. **Tesseract** — ``pip install pytesseract`` + binary on PATH or at
   ``C:\\Program Files\\Tesseract-OCR\\tesseract.exe`` (auto-detected).
   Required for ``process_union_jacked_assets.py --ocr``.
2. **EasyOCR** — optional; use ``--ocr-easyocr`` only (experimental on ornate footers).

Used by ``process_union_jacked_assets.py --ocr`` before the footer is cropped away.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

# Optional chromatic / pearlescent cues — tune as needed
_CHROMATIC_HINT = re.compile(
    r"chrome|holo|shift|irid|opal|aurora|film|pearl|neon|prism|flare|metallic|union\s+jack",
    re.IGNORECASE,
)

_DIGITS_ONLY = re.compile(r"^[\d\s\-_.]+$")

_EASYOCR_READER = None


def _configure_tesseract() -> bool:
    try:
        import pytesseract
    except ImportError:
        return False

    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    for p in candidates:
        if p.exists():
            pytesseract.pytesseract.tesseract_cmd = str(p)
            break
    return True


def _tesseract_runtime_ok() -> bool:
    if not _configure_tesseract():
        return False
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _easyocr_import_ok() -> bool:
    try:
        import easyocr  # noqa: F401

        return True
    except ImportError:
        return False


def ocr_available() -> bool:
    """Union Jacked footer OCR is validated against **Tesseract** only.

    EasyOCR is optional (see ``easyocr_footer_usable``) but **not** used for
    ``--ocr`` by default — decorative poster strips yield noisy reads.
    """
    return _tesseract_runtime_ok()


def easyocr_footer_usable() -> bool:
    """True if EasyOCR can run (for ``--ocr-easyocr`` experiments only)."""
    return _easyocr_import_ok()


def _get_easyocr_reader():
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        import easyocr

        _EASYOCR_READER = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _EASYOCR_READER


def extract_footer_strip(full_rgb: np.ndarray, crop_exclusive_row: int) -> np.ndarray:
    """Rows [crop_exclusive_row :, :] are discarded from the plate — OCR that band."""
    h = full_rgb.shape[0]
    if crop_exclusive_row <= 0 or crop_exclusive_row >= h:
        # Fallback: bottom 13%
        crop_exclusive_row = max(1, int(h * 0.87))
    return np.ascontiguousarray(full_rgb[crop_exclusive_row:, :, :])


def preprocess_footer_for_ocr(footer_rgb: np.ndarray) -> Image.Image:
    """Upscale + boost contrast; footer was designed to be read upright after plate rotate."""
    pil = Image.fromarray(footer_rgb).convert("RGB")
    # Footer art is often inverted relative to final booth orientation — try OCR upright first.
    pil = ImageOps.exif_transpose(pil)
    w, h = pil.size
    scale = max(1.0, 900.0 / max(h, 1))
    pil = pil.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    gray = pil.convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(1.85)
    gray = ImageEnhance.Sharpness(gray).enhance(1.15)
    return gray


def _ocr_tesseract_footer(footer_rgb: np.ndarray, also_flip: bool) -> str:
    import pytesseract

    _configure_tesseract()
    texts: list[str] = []

    def run(pil_l: Image.Image) -> str:
        return pytesseract.image_to_string(
            pil_l,
            lang="eng",
            config="--oem 3 --psm 6 -c preserve_interword_spaces=1",
        )

    g0 = preprocess_footer_for_ocr(footer_rgb)
    texts.append(run(g0))
    if also_flip:
        g1 = g0.rotate(180, expand=True)
        texts.append(run(g1))

    return "\n".join(t for t in texts if t and t.strip())


def _ocr_easyocr_footer(footer_rgb: np.ndarray, also_flip: bool) -> str:
    """EasyOCR on grayscale PIL converted back to RGB (library expects color ndarray)."""
    reader = _get_easyocr_reader()
    g0 = preprocess_footer_for_ocr(footer_rgb)
    chunks: list[str] = []

    def run(pil_g: Image.Image) -> str:
        rgb = pil_g.convert("RGB")
        arr = np.asarray(rgb)
        lines = reader.readtext(arr, detail=0, paragraph=False)
        if isinstance(lines, list):
            return "\n".join(str(x) for x in lines if x)
        return str(lines)

    chunks.append(run(g0))
    if also_flip:
        chunks.append(run(g0.rotate(180, expand=True)))

    return "\n".join(c for c in chunks if c and c.strip())


def ocr_footer_image(
    footer_rgb: np.ndarray,
    also_flip: bool = True,
    *,
    engine: str = "tesseract",
) -> str:
    """engine: ``tesseract`` (default) or ``easyocr`` (experimental)."""
    if engine == "easyocr":
        if not _easyocr_import_ok():
            raise RuntimeError("easyocr is not installed.")
        return _ocr_easyocr_footer(footer_rgb, also_flip)
    if _tesseract_runtime_ok():
        return _ocr_tesseract_footer(footer_rgb, also_flip)
    raise RuntimeError(
        "Tesseract is not installed or not on PATH. Install from "
        "https://github.com/UB-Mannheim/tesseract/wiki then add to PATH, "
        "or pass --ocr-easyocr to try EasyOCR (experimental)."
    )


def parse_title_description(raw: str) -> tuple[str, str]:
    """First substantive line = title; remaining = description. Strip catalogue numbers."""
    lines = []
    for ln in raw.replace("\r", "\n").split("\n"):
        t = ln.strip()
        if not t:
            continue
        # Drop orphan digit lines (poster index diamonds)
        if _DIGITS_ONLY.match(t):
            continue
        lines.append(t)

    if not lines:
        return "Untitled Plate", ""

    title = lines[0]
    # If title is very short and second line looks like real title, swap heuristic
    if len(lines) >= 2 and len(title) < 4 and len(lines[1]) > 8:
        title = lines[1]
        desc_lines = [lines[0]] + lines[2:]
    else:
        desc_lines = lines[1:]

    desc = " ".join(desc_lines).strip()
    # Cleanup repeated OCR junk
    title = re.sub(r"\s+", " ", title).strip()
    desc = re.sub(r"\s+", " ", desc).strip()
    return title, desc


def slugify_union_jacked_id(title: str, used: set[str]) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "_", title.strip().lower())
    base = re.sub(r"_+", "_", base).strip("_")
    if not base:
        base = "untitled"
    slug = f"uj_{base}"[:96]
    if slug not in used:
        used.add(slug)
        return slug
    i = 2
    while True:
        cand = f"{slug}_{i}"[:96]
        if cand not in used:
            used.add(cand)
            return cand
        i += 1


def infer_chromatic_shift(name: str, desc: str) -> bool:
    blob = f"{name} {desc}"
    return bool(_CHROMATIC_HINT.search(blob))


def sample_swatch_hex(rgb_u8: np.ndarray) -> str:
    """Dominant-ish color from central region of cropped plate (before downscale)."""
    h, w = rgb_u8.shape[:2]
    y0, y1 = int(h * 0.35), int(h * 0.65)
    x0, x1 = int(w * 0.35), int(w * 0.65)
    crop = rgb_u8[y0:y1, x0:x1, :]
    mean = crop.reshape(-1, 3).mean(axis=0)
    r, g, b = [int(np.clip(x, 0, 255)) for x in mean]
    return f"#{r:02x}{g:02x}{b:02x}"
