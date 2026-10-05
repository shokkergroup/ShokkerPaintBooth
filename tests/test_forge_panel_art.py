import numpy as np
from PIL import Image, ImageDraw

import _forge_panel_art as panel_art


def _sheet() -> Image.Image:
    image = Image.new("RGB", (500, 260), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 45, 210, 185), fill="#b30722")
    draw.rectangle((65, 70, 185, 160), fill="white")
    draw.rectangle((285, 85, 460, 145), fill="#186b38")
    return image


def test_border_connected_white_is_removed_but_enclosed_white_remains() -> None:
    foreground, _background = panel_art.sheet_foreground(_sheet())
    assert not foreground[10, 10]
    assert foreground[100, 100]
    assert foreground[110, 350]


def test_component_cutter_splits_separated_art_and_retains_coverage() -> None:
    components, foreground, _background = panel_art.component_masks(_sheet())
    assert len(components) == 2
    retained = np.zeros_like(foreground)
    for component in components:
        retained |= component["mask"]
    assert (retained & foreground).sum() / foreground.sum() > 0.99


def test_rgba_has_transparent_outside_and_opaque_enclosed_white() -> None:
    image = _sheet()
    components, _foreground, background = panel_art.component_masks(image)
    first = components[0]
    rgba = panel_art.component_rgba(image, first["mask"], first["bbox"], background)
    alpha = np.asarray(rgba.getchannel("A"))
    assert alpha.max() == 255
    assert alpha[60, 60] == 255
    assert rgba.mode == "RGBA"


def test_perceptual_hash_is_stable_for_same_asset() -> None:
    image = Image.new("RGBA", (120, 60), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((10, 10, 110, 50), fill="#c20b27")
    assert panel_art._dhash(image) == panel_art._dhash(image.copy())
    assert panel_art._dhash(image, alpha=True) == panel_art._dhash(image.copy(), alpha=True)


def test_reference_thumbnail_detector_abstains_on_plain_stripe() -> None:
    image = Image.new("RGBA", (600, 120), (0, 0, 0, 0))
    ImageDraw.Draw(image).polygon([(10, 40), (590, 20), (580, 70), (20, 90)], fill="#b30722")
    detected, _evidence = panel_art.likely_reference_thumbnail(image)
    assert not detected
