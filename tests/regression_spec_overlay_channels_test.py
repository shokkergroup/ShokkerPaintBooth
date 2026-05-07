import numpy as np

from engine.compose import compose_finish


def test_overlay_spec_pattern_clearcoat_channel_targets_only_clearcoat():
    shape = (128, 128)
    mask = np.ones(shape, dtype=np.float32)

    base = compose_finish("gloss", "none", shape, mask, 42, 1.0)
    overlay = compose_finish(
        "gloss",
        "none",
        shape,
        mask,
        42,
        1.0,
        overlay_spec_pattern_stack=[
            {"pattern": "spec_light_leak", "opacity": 1.0, "channels": "C", "range": 80}
        ],
    )

    metallic_delta = np.abs(overlay[:, :, 0].astype(np.int16) - base[:, :, 0].astype(np.int16))
    clearcoat_delta = np.abs(overlay[:, :, 2].astype(np.int16) - base[:, :, 2].astype(np.int16))

    assert metallic_delta.max() == 0
    assert clearcoat_delta.max() > 0
