"""SPB-93 Pass 32: spec-channel Select Connected / Select All Similar."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def run_node(script: str) -> dict:
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True
    )
    return json.loads(result.stdout)


def test_connected_stops_at_material_barrier_while_all_finds_both_islands():
    payload = run_node(r"""
const api = require('./js/canvas/zone/spec-material-select.js');
const width = 5, height = 3;
const data = new Uint8ClampedArray(width * height * 4);
for (let y=0; y<height; y++) for (let x=0; x<width; x++) {
  const i=(y*width+x)*4;
  const hit=x<2 || x>2;
  data[i]=hit?10:200; data[i+1]=hit?20:201; data[i+2]=hit?30:202; data[i+3]=hit?255:0;
}
const image={width,height,data};
const sample={m:10,r:20,cc:30,a:255};
const connected=api.buildConnectedMask(image,sample,0,0,1);
const all=api.buildAllMask(image,sample,0);
process.stdout.write(JSON.stringify({
  connected: connected.selected,
  all: all.selected,
  connectedMask: Array.from(connected.mask),
  tolerance: api.clampTolerance(999)
}));
""")
    assert payload["connected"] == 6
    assert payload["all"] == 12
    assert payload["connectedMask"] == [255, 255, 0, 0, 0] * 3
    assert payload["tolerance"] == 255


def test_connected_median_recovers_from_a_rejected_center_flake_but_point_stays_strict():
    payload = run_node(r"""
const api = require('./js/canvas/zone/spec-material-select.js');
const width=5,height=1,data=new Uint8ClampedArray(width*height*4);
for(let x=0;x<width;x++){
  const i=x*4, flake=x===2;
  data[i]=flake?240:40; data[i+1]=flake?5:80; data[i+2]=flake?220:120; data[i+3]=255;
}
const image={width,height,data};
const median={x:2,y:0,sampleSize:3,m:40,r:80,cc:120,a:255};
const point={x:2,y:0,m:40,r:80,cc:120,a:255};
process.stdout.write(JSON.stringify({
  median:api.buildConnectedMask(image,median,0,2,0).selected,
  point:api.buildConnectedMask(image,point,0,2,0).selected,
  seed:api.findNearestMatchingSeed(image,median,0,2,0,3)
}));
""")
    assert payload == {"median": 2, "point": 0, "seed": 1}


def test_resize_and_replace_add_subtract_are_exact_and_noop_measurable():
    payload = run_node(r"""
const api = require('./js/canvas/zone/spec-material-select.js');
const small=new Uint8Array([255,0,0,255]);
const big=api.resizeMaskNearest(small,2,2,4,4);
const existing=new Uint8Array([0,80,255,0]);
const candidate=new Uint8Array([255,255,0,0]);
const replace=api.composeMask(existing,candidate,'replace');
const add=api.composeMask(existing,candidate,'add');
const subtract=api.composeMask(existing,candidate,'subtract');
process.stdout.write(JSON.stringify({
  big:Array.from(big),
  replace:{mask:Array.from(replace.mask),changed:replace.changed,selected:replace.selected},
  add:{mask:Array.from(add.mask),changed:add.changed,selected:add.selected},
  subtract:{mask:Array.from(subtract.mask),changed:subtract.changed,selected:subtract.selected}
}));
""")
    assert payload["big"] == [255, 255, 0, 0, 255, 255, 0, 0, 0, 0, 255, 255, 0, 0, 255, 255]
    assert payload["replace"] == {"mask": [255, 255, 0, 0], "changed": 3, "selected": 2}
    assert payload["add"] == {"mask": [255, 255, 255, 0], "changed": 2, "selected": 3}
    assert payload["subtract"] == {"mask": [0, 0, 255, 0], "changed": 1, "selected": 1}


def test_full_2048_all_scan_and_connected_region_stay_interactive():
    payload = run_node(r"""
const {performance}=require('perf_hooks');
const api=require('./js/canvas/zone/spec-material-select.js');
const w=2048,h=2048,n=w*h;
const data=new Uint8ClampedArray(n*4);
for(let i=0;i<n;i++){data[i*4]=200;data[i*4+1]=200;data[i*4+2]=200;data[i*4+3]=255;}
for(let y=700;y<1100;y++) for(let x=800;x<1200;x++){
  const o=(y*w+x)*4; data[o]=20;data[o+1]=80;data[o+2]=40;data[o+3]=255;
}
const image={width:w,height:h,data}; const sample={m:20,r:80,cc:40,a:255};
let t=performance.now(); const all=api.buildAllMask(image,sample,0); const allMs=performance.now()-t;
t=performance.now(); const connected=api.buildConnectedMask(image,sample,0,900,800); const connectedMs=performance.now()-t;
process.stdout.write(JSON.stringify({all:all.selected,connected:connected.selected,allMs,connectedMs}));
""")
    assert payload["all"] == 160_000
    assert payload["connected"] == 160_000
    assert payload["allMs"] < 750
    assert payload["connectedMs"] < 750


def test_ui_exposes_tolerance_and_both_predictable_selection_scopes():
    html = read("paint-booth-v2.html")
    assert 'id="specMaterialSelectTolerance"' in html
    assert 'id="btnSelectConnectedMaterial"' in html
    assert 'id="btnSelectAllMaterial"' in html
    assert "Uses the current Replace / Add / Subtract selection mode" in html
    module = "js/canvas/zone/spec-material-select.js"
    assert html.index(module) < html.index('<script src="paint-booth-3-canvas.js')
    assert module in json.loads(read("scripts/runtime-sync-manifest.json"))["files"]


def test_controller_validates_candidate_before_actual_zone_mask_history():
    source = read("js/canvas/zone/spec-material-select.js")
    compare_at = source.index("if (!composed || (!composed.changed")
    history_at = source.index("root._spbPushZoneMaskUndoSnapshot(active.index)")
    assign_at = source.index("active.zone.regionMask = composed.mask")
    assert compare_at < history_at < assign_at
    assert "document.getElementById('selectionMode')" in source
    assert "renderRegionOverlay" in source
    assert "updateRegionStatus" in source
    assert "renderContextActionBar" in source
    assert "_psdLayers" not in source


def test_sampler_reset_disables_material_selection_actions_until_new_click():
    source = read("js/canvas/zone/spec-material-sampler.js")
    assert "'btnSelectConnectedMaterial'" in source
    assert "'btnSelectAllMaterial'" in source
    assert "button.disabled = !enabled" in source


def test_selection_activates_area_and_snapshots_flag_only_changes():
    payload = run_node(r"""
const vm=require('node:vm'),fs=require('node:fs');
function run(kind, before, enabled, mode) {
  const zone={regionMask:new Uint8Array(before),useRegion:enabled,spatialMask:new Uint8Array([1,2,3])};
  const snapshots=[];
  const context={Uint8Array,Uint8ClampedArray,performance,zones:[zone],selectedZoneIndex:0,
    document:{getElementById(id){return id==='paintCanvas'?{width:3,height:1}:{value:id==='selectionMode'?mode:'0'};}},
    SPBSpecMaterialSampler:{getLastSample:()=>({x:0,y:0,m:10,r:20,cc:30,a:255}),
      readInspectorImageData:()=>({width:3,height:1,data:new Uint8ClampedArray([10,20,30,255,99,99,99,255,10,20,30,255])})},
    _spbPushZoneMaskUndoSnapshot(){snapshots.push({mask:Array.from(zone.regionMask),enabled:zone.useRegion});}
  };
  context.window=context;
  vm.runInNewContext(fs.readFileSync('./js/canvas/zone/spec-material-select.js','utf8'),context);
  const result=(kind==='connected'?context.selectConnectedSpecMaterial:context.selectAllSimilarSpecMaterial)();
  return {result,mask:Array.from(zone.regionMask),enabled:zone.useRegion,snapshots,spatial:Array.from(zone.spatialMask)};
}
process.stdout.write(JSON.stringify({
  empty:run('all',[0,0,0],false,'replace'),
  connected:run('connected',[0,0,0],false,'replace'),
  disabled:run('all',[255,0,255],false,'replace'),
  unchanged:run('all',[255,0,255],true,'replace'),
  subtract:run('all',[255,0,255],true,'subtract')
}));
""")
    for name in ('empty', 'connected', 'disabled'):
        case = payload[name]
        assert case['result'] and case['enabled']
        assert len(case['snapshots']) == 1
        assert case['snapshots'][0]['enabled'] is False
        assert case['spatial'] == [1, 2, 3]
    assert payload['empty']['mask'] == [255, 0, 255]
    assert payload['connected']['mask'] == [255, 0, 0]
    assert payload['disabled']['snapshots'][0]['mask'] == [255, 0, 255]
    assert payload['unchanged']['result'] is False
    assert payload['unchanged']['snapshots'] == []
    assert payload['subtract']['enabled'] is False
    assert payload['subtract']['mask'] == [0, 0, 0]
    assert payload['subtract']['snapshots'] == [{'mask': [255, 0, 255], 'enabled': True}]
