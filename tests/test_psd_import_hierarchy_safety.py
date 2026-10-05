"""Urgent regression: PSD import must never identify leaves by display name."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from flask import Flask
from PIL import Image

from server_routes.psd_import_routes import register_psd_import_routes
from server_routes.psd_import_tree import build_layer_tree, iter_leaf_layers


class FakeLayer:
    def __init__(
        self,
        name,
        *,
        children=None,
        visible=True,
        opacity=255,
        blend_mode="NORMAL",
        bbox=(0, 0, 16, 16),
        clipping=False,
        color=(180, 70, 30, 255),
    ):
        self.name = name
        self._children = children
        self.kind = "group" if children is not None else "pixel"
        self.visible = visible
        self.opacity = opacity
        self.blend_mode = blend_mode
        self.bbox = bbox
        self.clipping = clipping
        self.color = color

    def is_group(self):
        return self._children is not None

    def __iter__(self):
        return iter(self._children or [])

    def composite(self, force=False):
        width = max(1, self.bbox[2] - self.bbox[0])
        height = max(1, self.bbox[3] - self.bbox[1])
        return Image.new("RGBA", (width, height), self.color)


class FakePSD(list):
    width = 32
    height = 16

    def composite(self):
        return Image.new("RGBA", (self.width, self.height), (90, 120, 150, 255))


def _fixture():
    return [
        FakeLayer(
            "Outer",
            children=[
                FakeLayer(
                    "Inner",
                    children=[
                        FakeLayer("Paint", blend_mode="MULTIPLY"),
                        FakeLayer("Paint", bbox=(16, 0, 32, 16)),
                    ],
                )
            ],
        ),
        FakeLayer(
            "Hidden Parent",
            visible=False,
            children=[FakeLayer("Visible Child", visible=True)],
        ),
    ]


def test_server_tree_uses_full_hierarchy_and_collision_free_positional_keys():
    root = _fixture()
    tree = build_layer_tree(root, 32, 16)
    leaves = list(iter_leaf_layers(root))

    assert [metadata["layer_key"] for metadata, _ in leaves] == ["0.0.0", "0.0.1", "1.0"]
    assert [metadata["path"] for metadata, _ in leaves] == [
        "Outer/Inner/Paint",
        "Outer/Inner/Paint",
        "Hidden Parent/Visible Child",
    ]
    assert len({metadata["layer_key"] for metadata, _ in leaves}) == 3
    assert tree[1]["children"][0]["visible"] is True
    assert tree[1]["children"][0]["effective_visible"] is False


def test_server_tree_preserves_group_compositing_boundaries():
    root = [
        FakeLayer("Outside"),
        FakeLayer(
            "Isolated 40",
            opacity=102,
            blend_mode="NORMAL",
            children=[
                FakeLayer("Base"),
                FakeLayer("Clipped", clipping=True),
                FakeLayer(
                    "Pass",
                    blend_mode="PASS_THROUGH",
                    children=[FakeLayer("Nested")],
                ),
            ],
        ),
    ]
    tree = build_layer_tree(root, 32, 16)
    leaves = list(iter_leaf_layers(root))

    isolated = tree[1]
    passthrough = isolated["children"][2]
    assert isolated["group_mode"] == "isolated"
    assert isolated["opacity"] == 102
    assert passthrough["group_mode"] == "pass-through"
    assert passthrough["blend_mode"] == "PASS_THROUGH"
    nested_meta = leaves[-1][0]
    assert [group["layer_key"] for group in nested_meta["group_chain"]] == ["1", "1.2"]
    assert [group["group_mode"] for group in nested_meta["group_chain"]] == [
        "isolated",
        "pass-through",
    ]


def test_client_tree_and_source_fidelity_gate_are_behavioral():
    module = Path("js/canvas/layer/psd-import-safety.js").resolve()
    tree = build_layer_tree(_fixture(), 32, 16)
    script = f"""
const api = require({json.dumps(str(module))});
const flat = api.flattenLayerTree({json.dumps(tree)}, {{width:32,height:16}});
const reference = new Uint8ClampedArray([220,80,40,255, 200,180,160,255]);
const black = new Uint8ClampedArray([0,0,0,255, 0,0,0,255]);
const same = new Uint8ClampedArray(reference);
console.log(JSON.stringify({{
  keys: flat.map(x => x.rasterKey),
  paths: flat.map(x => x.path),
  visible: flat.map(x => x.visible),
  blend: flat.map(x => x.blendMode),
  ids: flat.map(x => x.id),
  black: api.assessComposite(reference, black, 1),
  same: api.assessComposite(reference, same, 1)
}}));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(proc.stdout)

    assert result["keys"] == ["0.0.0", "0.0.1", "1.0"]
    assert result["paths"][0] == "Outer/Inner/Paint"
    assert result["ids"] == ["psd_0", "psd_1", "psd_2"], (
        "Public sequential IDs must stay compatible with saved zone->Layer bindings."
    )
    assert result["visible"] == [True, True, False]
    assert result["blend"][0] == "multiply"
    assert result["black"]["critical"] is True
    assert result["same"]["critical"] is False


def test_client_group_plan_applies_group_opacity_once_and_never_cross_clips():
    module = Path("js/canvas/layer/psd-import-safety.js").resolve()
    clipping = Path("js/canvas/layer/clipping-mask.js").resolve()
    tree = build_layer_tree(
        [
            FakeLayer("Outside"),
            FakeLayer(
                "Isolated 40",
                opacity=102,
                blend_mode="MULTIPLY",
                children=[
                    FakeLayer("Base"),
                    FakeLayer("Clipped", clipping=True),
                    FakeLayer(
                        "Pass",
                        blend_mode="PASS_THROUGH",
                        children=[FakeLayer("Nested")],
                    ),
                ],
            ),
            FakeLayer(
                "Boundary",
                children=[FakeLayer("Must not bind Outside", clipping=True)],
            ),
            FakeLayer(
                "Unsupported pass opacity",
                opacity=102,
                blend_mode="PASS_THROUGH",
                children=[FakeLayer("Child")],
            ),
        ],
        32,
        16,
    )
    script = f"""
const safety = require({json.dumps(str(module))});
const composite = require({json.dumps(str(clipping))});
const flat = safety.flattenLayerTree({json.dumps(tree)}, {{width:32,height:16}});
const supported = flat.slice(0, 4);
supported.forEach((layer, index) => {{ layer.img = {{id:'img-' + index}}; }});
const log = [];
let canvasId = 0;
function makeContext(id) {{
  return {{
    canvas: {{width:32,height:16,id}}, globalAlpha:1,
    globalCompositeOperation:'source-over',
    save() {{ log.push(['save', id]); }}, restore() {{ log.push(['restore', id]); }},
    clearRect() {{}}, setTransform() {{}},
    drawImage(image, x, y) {{ log.push(['group', id, image.id, this.globalAlpha, this.globalCompositeOperation]); }}
  }};
}}
global.document = {{createElement() {{
  const id = 'scratch-' + (++canvasId);
  const ctx = makeContext(id);
  return {{id, width:0, height:0, getContext() {{ ctx.canvas = this; return ctx; }}}};
}}}};
const target = makeContext('target');
const drawn = [];
const result = composite.composeLayerStack(target, supported, {{
  drawLayer(ctx, layer, index) {{ drawn.push([ctx.canvas.id, layer.name, index]); return true; }}
}});
const unsupported = composite.inspectStack(flat);
console.log(JSON.stringify({{
  chains: flat.map(layer => layer.groupChain.map(group => [group.key, group.opacity, group.mode])),
  issues: flat.groupFidelityIssues,
  result, unsupported, drawn, log,
  validBase: composite.resolveBaseLayer(flat, 2)?.name || null,
  escapedBase: composite.resolveBaseLayer(flat, 4)?.name || null
}}));
"""
    proc = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
    result = json.loads(proc.stdout)

    assert result["chains"][1] == [["1", 102, "isolated"]]
    assert result["chains"][3] == [
        ["1", 102, "isolated"],
        ["1.2", 255, "pass-through"],
    ]
    assert result["validBase"] == "Base"
    assert result["escapedBase"] is None
    assert result["result"]["ok"] is True
    group_commit = next(entry for entry in result["log"] if entry[0] == "group")
    assert group_commit[1] == "target"
    assert abs(group_commit[3] - 0.4) < 1e-9
    assert group_commit[4] == "multiply"
    assert len([entry for entry in result["log"] if entry[0] == "group"]) == 1
    nested_draw = next(entry for entry in result["drawn"] if entry[1] == "Nested")
    assert nested_draw[0].startswith("scratch-")
    assert any("pass-through" in issue["reason"] for issue in result["issues"])
    assert result["unsupported"]["ok"] is False


def test_client_import_fails_closed_to_source_composite_on_missing_or_bad_stack():
    source = Path("paint-booth-3-canvas.js").read_text(encoding="utf-8")
    start = source.index("async function _doPSDImport(psdPath)")
    end = source.index("function countLayers(layers)", start)
    body = source[start:end]

    assert "rasterData.layers[layer.rasterKey]" in body
    assert "await _decodePSDSourceComposite(data.composite, normalizedPath)" in body
    assert "_activatePSDSourceCompositeFallback" in body
    assert "psdImportApi.assessComposite" in body
    assert body.index("await _decodePSDSourceComposite") < body.index("/api/psd-rasterize-all")
    assert "{ stageOnly: true }" in body
    assert "_spbRestoreSourceDocumentState(previous)" in body
    assert "Source Composite (safe fallback)" in source
    assert "importSafetyBase: true" in source


def test_client_composite_and_ownership_share_group_aware_stack_path():
    source = Path("paint-booth-3-canvas.js").read_text(encoding="utf-8")
    assert "function _spbCompositeLayerStack(ctx, layers, options)" in source
    assert "const groupInspection = _spbInspectLayerStack(_psdLayers)" in source
    assert "hasGroupSemantics(_psdLayers)" in source
    assert "identityBlend: true" in source
    assert source.count("_spbCompositeLayerStack(") >= 8
    assert "reason: 'unsupported-psd-group-semantics'" in source
    assert "Unsupported group semantics:" in source
    assert "Merge Visible stopped: grouped PSD Layers" in source


def test_rasterize_all_route_does_not_overwrite_duplicate_names(tmp_path):
    fake_psd = FakePSD(_fixture())
    psd_path = tmp_path / "nested-duplicates.psd"
    psd_path.write_bytes(b"fixture")

    app = Flask(__name__)
    register_psd_import_routes(
        app,
        require_internal_request=lambda: (True, None),
        sanitize_path=lambda value: (value, None),
        get_cached_psd=lambda _value: fake_psd,
        logger=app.logger,
    )
    client = app.test_client()

    tree_response = client.post(
        "/api/psd-import",
        json={"psd_path": str(psd_path)},
        headers={"X-Shokker-Internal": "1"},
    )
    assert tree_response.status_code == 200
    assert tree_response.get_json()["layers"][0]["children"][0]["children"][1]["layer_key"] == "0.0.1"

    raster_response = client.post(
        "/api/psd-rasterize-all",
        json={"psd_path": str(psd_path)},
        headers={"X-Shokker-Internal": "1"},
    )
    assert raster_response.status_code == 200
    payload = raster_response.get_json()
    assert payload["count"] == 3
    assert set(payload["layers"]) == {"0.0.0", "0.0.1", "1.0"}
    assert payload["layers"]["0.0.0"]["path"] == "Outer/Inner/Paint"
    assert payload["layers"]["0.0.1"]["path"] == "Outer/Inner/Paint"


def test_psd_import_reuses_unchanged_composite_and_layer_tree(tmp_path):
    fake_psd = FakePSD(_fixture())
    calls = {"composite": 0}
    original_composite = fake_psd.composite

    def counted_composite():
        calls["composite"] += 1
        return original_composite()

    fake_psd.composite = counted_composite
    psd_path = tmp_path / "cached-template.psd"
    psd_path.write_bytes(b"unchanged fixture")
    app = Flask(__name__)
    register_psd_import_routes(
        app,
        require_internal_request=lambda: (True, None),
        sanitize_path=lambda value: (value, None),
        get_cached_psd=lambda _value: fake_psd,
        logger=app.logger,
    )
    client = app.test_client()
    first = client.post("/api/psd-import", json={"psd_path": str(psd_path), "thumbnail_size": 256})
    second = client.post("/api/psd-import", json={"psd_path": str(psd_path), "thumbnail_size": 256})

    assert first.status_code == second.status_code == 200
    assert first.get_json() == second.get_json()
    assert calls["composite"] == 1, "An unchanged PSD must not spend another full composite pass."

    current = psd_path.stat()
    os.utime(psd_path, ns=(current.st_atime_ns, current.st_mtime_ns + 2_000_000_000))
    changed = client.post("/api/psd-import", json={"psd_path": str(psd_path), "thumbnail_size": 256})
    assert changed.status_code == 200
    assert calls["composite"] == 2, "A changed PSD mtime must invalidate every cached pixel and layer."
