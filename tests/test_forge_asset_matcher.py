from PIL import Image, ImageDraw

import _forge_asset_matcher as matcher


def test_global_similarity_prefers_identical_shape_and_color() -> None:
    first = Image.new("RGBA", (180, 100), (0, 0, 0, 0))
    ImageDraw.Draw(first).polygon([(10, 70), (90, 10), (170, 70)], fill="#c20b2c")
    other = Image.new("RGBA", (180, 100), (0, 0, 0, 0))
    ImageDraw.Draw(other).ellipse((45, 10, 135, 100), fill="#186b38")
    identical = matcher.global_similarity(matcher._canvas(first), matcher._canvas(first))[0]
    different = matcher.global_similarity(matcher._canvas(first), matcher._canvas(other))[0]
    assert identical > 0.99
    assert identical > different + 0.2


def test_text_similarity_requires_meaningful_agreement() -> None:
    assert matcher.text_similarity(["BILSTEIN"], ["BILSTEIN"]) == 1.0
    assert matcher.text_similarity(["BILSTEIN"], ["MOROSO"]) == 0.0
    assert matcher.text_similarity(["ITER"], ["MILLER"]) == 0.0
    assert matcher.text_similarity(["W"], ["W"]) == 0.0


def test_field_consensus_transfers_only_supported_value() -> None:
    ranked = [
        {"confidence": 0.88, "metadata": {"role": "decal"}},
        {"confidence": 0.84, "metadata": {"role": "decal"}},
        {"confidence": 0.62, "metadata": {"role": "number"}},
    ]
    assert matcher._field_consensus(ranked, "role")["value"] == "decal"


def test_field_consensus_abstains_when_neighbors_disagree() -> None:
    ranked = [
        {"confidence": 0.75, "metadata": {"side": "left"}},
        {"confidence": 0.74, "metadata": {"side": "right"}},
    ]
    result = matcher._field_consensus(ranked, "side")
    assert result["value"] is None
    assert result["abstention"]
