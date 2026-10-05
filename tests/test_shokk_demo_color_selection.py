"""Owner's Cherry Polka regression: selected color, neutral Lab, and lock."""
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_material_selection_starts_with_matching_special_unless_locked():
    app = (ROOT / 'demo/frontend/js/app.js').read_text(encoding='utf-8')
    choose = app[app.index('function chooseFinish('):app.index('function chooseBaseColorSource(')]
    script = """
let zone;
const activeZone=()=>zone;
const renderZones=()=>{}, renderZoneEditor=()=>{}, schedulePreview=()=>{}, saveSession=()=>{}, showToast=()=>{};
const $=()=>({open:false});
""" + choose + """
const results=[];
for (const mode of ['finish','source','solid','special','gradient']) {
  for (const locked of [false,true]) {
    zone={name:'Test',finishId:'f_chrome',finishName:'Chrome',baseColorMode:mode,
      baseColor:'#123456',baseColorSource:'elm_tsunami',lockBaseColor:locked,
      baseColorLabEnabled:true,baseColorDepth:65,baseColorFlip:90,baseColorUnderglow:25,
      baseHueOffset:10,baseBrightnessAdjust:5,baseStrength:75,
      gradientStops:[{position:0,color:'#ff0000'},{position:1,color:'#00ff00'}]};
    const before=structuredClone(zone);
    chooseFinish({id:'cherry_polka',name:'Cherry Polka',swatch:'#bb0011'});
    results.push({before,after:structuredClone(zone)});
  }
}
console.log(JSON.stringify(results));
"""
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True, check=True)
    for row in json.loads(result.stdout):
        before, after = row['before'], row['after']
        assert after['finishId'] == 'cherry_polka'
        assert after['finishName'] == 'Cherry Polka'
        if before['lockBaseColor']:
            assert after == {**before, 'finishId': 'cherry_polka', 'finishName': 'Cherry Polka'}
        else:
            assert after == {**before, 'finishId': 'cherry_polka', 'finishName': 'Cherry Polka',
                'baseColorMode': 'special', 'baseColorSource': 'cherry_polka', 'baseColor': '#bb0011',
                'baseColorDepth': 0, 'baseColorFlip': 0, 'baseColorUnderglow': 0}

    fracture_script = script[:script.index('const results=[];')] + """
zone={lockBaseColor:false};
chooseFinish({id:'fs_core_emerald',name:'Fracture'}, {useFinishColor:true});
const unlocked=structuredClone(zone);
zone={lockBaseColor:true,baseColorMode:'solid',baseColor:'#f10414'};
chooseFinish({id:'fs_core_emerald',name:'Fracture'}, {useFinishColor:true});
console.log(JSON.stringify([unlocked,zone]));
"""
    result = subprocess.run(['node','-e',fracture_script],capture_output=True,text=True,check=True)
    unlocked, locked = json.loads(result.stdout)
    assert unlocked['baseColorMode'] == 'finish' and unlocked['baseColorSource'] == ''
    assert locked['baseColorMode'] == 'solid' and locked['baseColor'] == '#f10414'


@pytest.mark.parametrize('strength', [0, .4, 1])
def test_neutral_color_lab_preserves_selected_rgb_and_strength(strength):
    from demo.backend.compositor import _apply_color_lab_controls
    material = np.array([[[12, 26, 230], [201, 145, 67]]], dtype=np.float32)
    selected = np.array([[[1, 0, 0], [105, 8, 22]]], dtype=np.float32)
    zone = dict(baseColorLabEnabled=True, baseColorDepth=0, baseColorFlip=0,
                baseColorUnderglow=0, baseColorStrength=strength)
    assert np.array_equal(_apply_color_lab_controls(material, selected, zone),
                          material * (1-strength) + selected * strength)


def test_deliberate_candy_depth_still_works_and_neutral_restores_color():
    from demo.backend.compositor import _apply_color_lab_controls
    material = np.full((2, 2, 3), 60, dtype=np.float32)
    selected = np.full((2, 2, 3), (100, 8, 20), dtype=np.float32)
    zone = dict(baseColorLabEnabled=True, baseColorDepth=.65)
    dark = _apply_color_lab_controls(material, selected, zone)
    assert dark.mean() < selected.mean()
    zone['baseColorDepth'] = 0
    assert np.array_equal(_apply_color_lab_controls(material, selected, zone), selected)
