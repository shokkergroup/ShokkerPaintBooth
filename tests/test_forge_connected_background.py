import numpy as np
import pytest
from PIL import Image, ImageDraw

from _forge_connected_background import ConnectedBackgroundError, remove_background


def _outlined_white_asset() -> Image.Image:
    image = Image.new("RGBA", (80, 60), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 15, 60, 45), fill=(8, 35, 80, 255))
    draw.rectangle((25, 20, 55, 40), fill=(255, 255, 255, 255))
    return image


def test_connected_border_removal_preserves_enclosed_white_artwork():
    result = np.asarray(remove_background(_outlined_white_asset(), {"mode": "near_white_connected_border", "threshold": 245}))
    assert result[0, 0, 3] == 0
    assert result[30, 40, 3] == 255
    assert tuple(result[30, 40, :3]) == (255, 255, 255)


def test_legacy_near_white_mode_removes_all_near_white_pixels():
    result = np.asarray(remove_background(_outlined_white_asset(), {"mode": "near_white", "threshold": 245}))
    assert result[0, 0, 3] == 0
    assert result[30, 40, 3] == 0


def test_invalid_mode_and_threshold_fail_closed():
    with pytest.raises(ConnectedBackgroundError, match="unknown_background_removal"):
        remove_background(_outlined_white_asset(), {"mode": "guess"})
    with pytest.raises(ConnectedBackgroundError, match="invalid_background_threshold"):
        remove_background(_outlined_white_asset(), {"mode": "near_white", "threshold": 999})
