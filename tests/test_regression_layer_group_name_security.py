from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_imported_group_names_never_enter_inline_javascript():
    source = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
    assert "toggleLayerGroupCollapsed('${_gSafe}')" not in source
    assert "toggleLayerGroupVisibility('${_gSafe}')" not in source
    assert 'data-layer-group-action="collapse"' in source
    assert 'data-layer-group-action="visibility"' in source
    assert "const _gActionIndex = _layerPanelGroupNames.push(_gRun) - 1;" in source
    assert "container._spbLayerPanelGroupNames[index]" in source

