from __future__ import annotations

import numpy as np

import _forge_reference_psd_compiler as compiler


def _blank() -> np.ndarray:
    return np.zeros((2048, 2048, 4), dtype=np.uint8)


def test_partition_makes_overlapping_surface_layers_disjoint_and_exact() -> None:
    canonical = _blank()
    canonical[10:20, 10:20] = (20, 150, 60, 255)
    canonical[15:25, 15:25] = (230, 30, 20, 255)
    first = _blank()
    first[10:20, 10:20] = canonical[10:20, 10:20]
    second = _blank()
    second[15:25, 15:25] = canonical[15:25, 15:25]
    layers, remainder = compiler.partition_surface_layers(canonical, [("Side", first), ("Fender", second)])
    recomposed = _blank()
    for _name, layer in layers:
        take = layer[:, :, 3] > 0
        assert not np.any((recomposed[:, :, 3] > 0) & take)
        recomposed[take] = layer[take]
    assert remainder == 0
    assert np.array_equal(recomposed, canonical)


def test_partition_exposes_unmatched_canonical_remainder() -> None:
    canonical = _blank()
    canonical[3, 4] = (1, 2, 3, 255)
    layers, remainder = compiler.partition_surface_layers(canonical, [])
    assert remainder == 1
    assert layers[0][0] == "Observed reconciliation remainder"
    assert np.array_equal(layers[0][1], canonical)


def test_case_parser_preserves_generic_name_and_path() -> None:
    name, path = compiler.parse_case("example=some/case")
    assert name == "example"
    assert path.as_posix() == "some/case"
