import zipfile
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
from PIL import Image
from psd_tools import PSDImage

import _forge_layers as layers


def _full(layer, size):
    image = layer.topil().convert("RGBA")
    full = Image.new("RGBA", size, (0, 0, 0, 0))
    full.alpha_composite(image, (int(layer.left), int(layer.top)))
    return full


def test_grouped_psd_and_ora_round_trip_hierarchy_and_pixels(tmp_path: Path) -> None:
    size = (24, 24)
    bottom = Image.new("RGBA", size, (0, 0, 0, 0))
    top = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(2, 14):
        for y in range(3, 18):
            bottom.putpixel((x, y), (20, 180, 60, 255))
    for x in range(8, 22):
        for y in range(6, 21):
            top.putpixel((x, y), (240, 40, 20, 160))
    composite = bottom.copy()
    composite.alpha_composite(top)
    groups = [
        {"name": "10 BASE COLORS", "layers": [("Base", bottom)]},
        {"name": "30 NUMBERS", "layers": [("Door number", top)]},
        {"name": "60 SPEC MAP", "layers": []},
    ]

    layers.write_grouped_layered(groups, composite, str(tmp_path), stem="roundtrip")

    psd = PSDImage.open(tmp_path / "roundtrip.psd")
    assert sorted(str(item.name) for item in psd if item.is_group()) == sorted(group["name"] for group in groups)
    leaves = []
    for group in psd:
        leaves.extend(list(group))
    recomposed = Image.new("RGBA", size, (0, 0, 0, 0))
    for leaf in leaves:
        recomposed.alpha_composite(_full(leaf, size))
    assert np.array_equal(np.asarray(recomposed), np.asarray(composite))
    # The PSD merged-image section is RGB by format choice; straight RGBA is
    # proved by the editable leaves above, while preview equality is RGB.
    assert np.array_equal(np.asarray(psd.composite().convert("RGB")), np.asarray(composite.convert("RGB")))

    with zipfile.ZipFile(tmp_path / "roundtrip.ora") as archive:
        root = ElementTree.fromstring(archive.read("stack.xml"))
        names = [node.attrib["name"] for node in root.findall("./stack/stack")]
        assert sorted(names) == sorted(group["name"] for group in groups)
        with archive.open("mergedimage.png") as handle:
            assert np.array_equal(np.asarray(Image.open(handle).convert("RGBA")), np.asarray(composite))
