"""Private, engine-informed Houdini material proof.

This is deliberately *not* an iRacing renderer or a substitute for matched
track captures.  It makes the same relationship used by the Chameleon engine
visible: high metallic whitens at grazing, low roughness sharpens the response,
and low-valued clearcoat is glossier.  It exists because the former RGB
"grazing" swatch painted every material green/red and was invalid evidence.

Usage: python scripts/spb_houdini_material_probe.py _houdini_i21_p5_native
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np


def _read(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(path)
    if image.ndim == 2:
        image = np.dstack((image, image, image))
    return image[..., :3].astype(np.float32) / 255.0


def _response(paint: np.ndarray, spec: np.ndarray, view: float) -> np.ndarray:
    """A material diagnostic, derived from the engine's M/R/Cc semantics.

    `view` is a grazing proxy: 0 is face-on and 1 is near grazing.  Clearcoat
    values in SPB use 16 as a very glossy coat and higher values as degraded.
    """
    metallic, roughness, clearcoat = (spec[..., i] / 255.0 for i in range(3))
    gloss = np.clip((1.0 - clearcoat) / (1.0 - 16.0 / 255.0), 0.0, 1.0)
    smooth = np.power(np.clip(1.0 - roughness, 0.0, 1.0), 1.18)
    # Schlick-like dielectric sheen plus the stronger high-metal Fresnel
    # described in engine.chameleon.spec_chameleon_v5.
    dielectric = 0.04 + 0.96 * view**5
    metal_flash = view * (0.14 + 0.86 * metallic)
    coat_flash = dielectric * (0.18 + 0.82 * gloss) * (0.20 + 0.80 * smooth)
    flash = np.maximum(metal_flash * (0.22 + 0.78 * smooth), coat_flash)
    # High metal fades toward a cool neutral at grazing while low-metal areas
    # retain the authored pigment.  This is a visibility diagnostic, not RGB
    # recoloring of the spec channels.
    retained = 0.20 + 0.72 * (1.0 - metallic) + 0.08 * smooth
    cool_white = np.array((0.72, 0.89, 1.00), dtype=np.float32)
    body = paint * retained[..., None]
    result = body + cool_white * flash[..., None]
    return np.uint8(np.clip(result, 0.0, 1.0) * 255.0)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: spb_houdini_material_probe.py <private-evidence-dir>")
    root = Path(sys.argv[1]).resolve()
    paint = _read(root / "standard.png")
    spec = np.dstack((_read(root / "metallic.png")[..., 0],
                      _read(root / "roughness.png")[..., 0],
                      _read(root / "clearcoat.png")[..., 0])) * 255.0
    for label, view in (("material_face_sim.png", 0.10),
                        ("material_crosslight_sim.png", 0.56),
                        ("material_grazing_sim.png", 0.90)):
        cv2.imwrite(str(root / label), _response(paint, spec, view))
    # A compact, deliberately labeled comparison prevents a single lighting
    # frame from being mistaken for definitive in-game proof.
    previews = [cv2.resize(_response(paint, spec, v), (512, 512), interpolation=cv2.INTER_AREA)
                for v in (0.10, 0.56, 0.90)]
    sheet = np.concatenate(previews, axis=1)
    for x, label in zip((18, 530, 1042), ("FACE-ON DIAGNOSTIC", "CROSSLIGHT DIAGNOSTIC", "GRAZING DIAGNOSTIC")):
        cv2.putText(sheet, label, (x, 488), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(str(root / "material_response_sheet.png"), sheet)
    print({"proof": str(root), "note": "engine-informed diagnostic; actual track capture still required"})


if __name__ == "__main__":
    main()
