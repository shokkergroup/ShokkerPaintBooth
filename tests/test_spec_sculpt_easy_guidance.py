"""Behavior contracts for paint-aware Easy Spec Sculpt guidance."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDANCE = ROOT / "js" / "features" / "spb-easy-sculpt-guidance.js"


def _node_json(script: str) -> dict:
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def test_guidance_finds_distinct_dominant_colors_and_plain_profile():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const w = 12, h = 8, px = new Uint8ClampedArray(w*h*4);
for (let y=0; y<h; y++) for (let x=0; x<w; x++) {{
  const i=(y*w+x)*4, c=x<6?[10,205,235]:(y<4?[245,210,20]:[18,20,24]);
  px[i]=c[0]; px[i+1]=c[1]; px[i+2]=c[2]; px[i+3]=255;
}}
console.log(JSON.stringify(g.analyzePixels(px,w,h)));
"""
    result = _node_json(script)

    assert len(result["palette"]) == 3
    assert {entry["name"] for entry in result["palette"]} >= {"CYAN", "YELLOW", "BLACK"}
    assert "vivid" in result["summary"]
    assert result["features"]["contrast"] > 0.2


def test_auto_colors_prioritize_real_accents_before_template_neutrals():
    script = f"""
const g=require({json.dumps(str(GUIDANCE))});
const palette=[
  {{name:'BLACK',color:[6,7,6],coverage:54}},
  {{name:'CHARCOAL',color:[45,48,45],coverage:20}},
  {{name:'CYAN',color:[7,212,240],coverage:14}},
  {{name:'YELLOW',color:[234,254,10],coverage:5}},
  {{name:'SILVER',color:[180,184,180],coverage:4}}
];
console.log(JSON.stringify(g.chooseAutoColors(palette,[],2)));
"""
    result = _node_json(script)
    assert [entry["name"] for entry in result] == ["CYAN", "YELLOW"]


def test_auto_colors_use_contrast_when_the_livery_is_neutral():
    script = f"""
const g=require({json.dumps(str(GUIDANCE))});
const palette=[
  {{name:'BLACK',color:[7,8,7],coverage:70}},
  {{name:'CHARCOAL',color:[45,48,45],coverage:20}},
  {{name:'SILVER',color:[185,188,185],coverage:10}}
];
console.log(JSON.stringify(g.chooseAutoColors(palette,[],2)));
"""
    result = _node_json(script)
    assert [entry["name"] for entry in result] == ["BLACK", "SILVER"]


def test_guidance_keeps_smart_materials_first_and_returns_a_short_diverse_set():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const looks = [
  {{kind:'preset',id:'plain',name:'Plain',category:'Other'}},
  {{kind:'preset',id:'candy_flow',name:'Candy Flow',category:'Candy'}},
  {{kind:'preset',id:'holographic',name:'Holographic',category:'Holo'}},
  {{kind:'preset',id:'mirror_chrome',name:'Mirror Chrome',category:'Metal'}},
  {{kind:'mode',id:'zoned',name:'Smart Materials',category:'Automatic'}},
  {{kind:'preset',id:'carbon_fiber',name:'Carbon Fiber',category:'Texture'}}
];
const ranked = g.rankLooks(looks,{{archetypes:['candy','holo','metal','texture']}},4);
console.log(JSON.stringify({{ids:ranked.map(x=>x.id),count:ranked.length}}));
"""
    result = _node_json(script)

    assert result["ids"][0] == "zoned"
    assert result["count"] == 4
    assert "plain" not in result["ids"]


def test_guidance_uses_dominant_paint_hues_without_losing_smart_materials():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const looks = [
  {{kind:'mode',id:'zoned',name:'Smart Materials',category:'Automatic'}},
  {{kind:'preset',id:'ruby',name:'Ruby Candy',category:'Candy'}},
  {{kind:'preset',id:'cobalt',name:'Cobalt Ice Candy',category:'Candy'}},
  {{kind:'preset',id:'solar',name:'Solar Gold Flake',category:'Flake'}},
  {{kind:'preset',id:'plain',name:'Plain Satin',category:'Soft'}}
];
const cyan = g.rankLooks(looks,{{archetypes:['candy','flake'],palette:[{{name:'CYAN'}},{{name:'YELLOW'}},{{name:'BLACK'}}]}},5);
console.log(JSON.stringify({{ids:cyan.map(x=>x.id)}}));
"""
    result = _node_json(script)

    assert result["ids"][0] == "zoned"
    assert result["ids"].index("cobalt") < result["ids"].index("ruby")
    assert result["ids"].index("solar") < result["ids"].index("ruby")


def test_guidance_uses_the_shortlist_to_demonstrate_material_breadth():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const looks = [{{kind:'mode',id:'zoned',name:'Smart Materials',category:'Automatic'}}];
const families = [
  ['holo','Holographic Prism'],['metal','Brushed Chrome'],['texture','Carbon Weave'],
  ['candy','Wet Candy Pearl'],['soft','Factory Matte Satin'],['flake','Diamond Sparkle Flake']
];
families.forEach(([family,name]) => {{
  for (let i=0;i<4;i++) looks.push({{kind:'preset',id:family+i,name:name+' '+i,category:family}});
}});
const ranked = g.rankLooks(looks,{{archetypes:['holo','metal','texture','candy','soft','flake']}},12);
const familyOf = id => id.replace(/[0-9]+$/,'');
const counts = {{}};
ranked.filter(x=>x.kind!=='mode').forEach(x=>counts[familyOf(x.id)]=(counts[familyOf(x.id)]||0)+1);
console.log(JSON.stringify({{ids:ranked.map(x=>x.id),counts}}));
"""
    result = _node_json(script)

    assert result["ids"][0] == "zoned"
    assert len(result["ids"]) == 12
    assert len(result["counts"]) == 6
    assert max(result["counts"].values()) <= 2


def test_guidance_shortlist_does_not_repeat_a_shared_catalog_recipe():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const looks = [
  {{kind:'mode',id:'zoned',name:'Smart Materials',category:'Automatic'}},
  {{kind:'catalog',swatchType:'base',id:'acid_rain',name:'Satin Acid Rain',category:'Paint Booth Base'}},
  {{kind:'catalog',swatchType:'monolithic',id:'acid_rain',name:'Satin Acid Rain',category:'Paint Booth Special'}},
  {{kind:'catalog',swatchType:'base',id:'chrome',name:'Mirror Chrome',category:'Paint Booth Base'}},
  {{kind:'catalog',swatchType:'base',id:'carbon',name:'Carbon Weave',category:'Paint Booth Base'}}
];
const ranked = g.rankLooks(looks,{{archetypes:['soft','metal','texture']}},4);
console.log(JSON.stringify({{ids:ranked.map(x=>x.id)}}));
"""
    result = _node_json(script)

    assert result["ids"].count("acid_rain") == 1
    assert len(result["ids"]) == 4


def test_material_response_translates_iracings_inverted_clearcoat_for_humans():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const candy = g.describeMaterialResponse([0.72, 0.18, 0.08], [0.2, 0.2, 0.2]);
const dry = g.describeMaterialResponse([0.20, 0.70, 0.92], [0.02, 0.02, 0.02]);
console.log(JSON.stringify({{candy,dry}}));
"""
    result = _node_json(script)

    assert result["candy"]["metrics"]["coat"] == 0.92
    assert "deep clearcoat" in result["candy"]["summary"]
    assert round(result["dry"]["metrics"]["coat"], 2) == 0.08
    assert "restrained clearcoat" in result["dry"]["summary"]


def test_material_layer_seeds_are_deterministic_and_independent():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const baseA = g.stableSeed(4242, 'whole::candy-depth::1.00');
const baseB = g.stableSeed(4242, 'whole::candy-depth::1.00');
const cyanA = g.stableSeed(4242, 'color::#07D4F0::30::black-ice::1.00');
const cyanB = g.stableSeed(4242, 'color::#07D4F0::30::black-ice::1.00');
const yellow = g.stableSeed(4242, 'color::#EAFE0A::30::stealth-gold::1.00');
console.log(JSON.stringify({{baseA,baseB,cyanA,cyanB,yellow}}));
"""
    result = _node_json(script)

    assert result["baseA"] == result["baseB"]
    assert result["cyanA"] == result["cyanB"]
    assert len({result["baseA"], result["cyanA"], result["yellow"]}) == 3


def test_plain_english_search_finds_material_intent_without_renaming_looks():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const looks = [
  {{id:'wet_candy',name:'Liquid Candy',category:'Candy',description:'suspended pearl flake under deep clearcoat'}},
  {{id:'factory_satin',name:'Factory Satin',category:'OEM'}},
  {{id:'carbon_twill',name:'Carbon Twill',category:'Texture'}},
  {{id:'fracture_neon',name:'FRACTURE Neon',category:'Signature'}}
];
const find = q => looks.filter(x => g.matchesLookSearch(x,q)).map(x => x.id);
console.log(JSON.stringify({{sparkly:find('sparkly'),flat:find('flat'),crazy:find('crazy'),fiber:find('fiber'),exact:find('liquid candy')}}));
"""
    result = _node_json(script)

    assert "wet_candy" in result["sparkly"]
    assert "factory_satin" in result["flat"]
    assert "fracture_neon" in result["crazy"]
    assert "carbon_twill" in result["fiber"]
    assert result["exact"] == ["wet_candy"]


def test_plain_english_search_ignores_filler_handles_typos_and_ranks_direct_names_first():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const looks = [
  {{id:'pearl_field',name:'Pearl Field',category:'Flake',description:'soft suspended pearl sparkle'}} ,
  {{id:'metallic_blue',name:'Metallic Blue',category:'Metal',description:'blue aluminum finish'}},
  {{id:'blue_chrome',name:'Blue Chrome',category:'Metal',description:'mirror polished metal'}},
  {{id:'carbon_soft',name:'Soft Carbon',category:'Texture',description:'subtle twill weave'}}
];
const ranked = q => looks.map((look,index)=>({{id:look.id,index,score:g.scoreLookSearch(look,q)}}))
  .filter(x=>x.score>=0).sort((a,b)=>b.score-a.score||a.index-b.index).map(x=>x.id);
console.log(JSON.stringify({{
  natural:ranked('I want shiny blue'),
  typo:ranked('metalic blue'),
  phrase:ranked('something subtle carbon'),
  direct:ranked('blue chrome')
}}));
"""
    result = _node_json(script)

    assert result["natural"][0] == "blue_chrome"
    assert "metallic_blue" in result["typo"]
    assert result["phrase"] == ["carbon_soft"]
    assert result["direct"][0] == "blue_chrome"


def test_conversational_search_translates_softeners_and_negative_phrases():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const looks = [
  {{id:'mirror',name:'Mirror Chrome',category:'Metal',description:'high gloss polished shine'}},
  {{id:'satin',name:'Factory Satin',category:'Soft',description:'clean restrained finish'}},
  {{id:'matte',name:'Stealth Matte',category:'Soft',description:'flat dull finish'}},
  {{id:'flake',name:'Diamond Flake',category:'Flake',description:'sparkle glitter'}},
  {{id:'wild',name:'FRACTURE Neon',category:'Wild',description:'crazy loud dramatic'}}
];
const find = q => looks.filter(x => g.matchesLookSearch(x,q)).map(x => x.id);
console.log(JSON.stringify({{
  softGloss:find('not too shiny'),
  natural:find('show me something kind of shiny please'),
  noSparkle:find('without sparkle'),
  quiet:find('less wild'),
  normalized:g.normalizeSearchQuery('not too shiny purple')
}}));
"""
    result = _node_json(script)

    assert "satin" in result["softGloss"]
    assert "mirror" in result["natural"]
    assert "satin" in result["noSparkle"]
    assert "satin" in result["quiet"]
    assert result["normalized"] == "satin purple"


def test_search_merges_overlapping_material_intents_instead_of_hiding_valid_looks():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const looks = [
  {{id:'mirror',name:'Mirror Polish',category:'Shine',description:'wet glass gloss'}},
  {{id:'metal',name:'Brushed Titanium',category:'Metal',description:'anodized aluminum'}},
  {{id:'factory',name:'Factory Satin',category:'Soft',description:'clean restrained finish'}},
  {{id:'suede',name:'Soft Suede',category:'Matte',description:'flat dull finish'}}
];
const find = q => looks.filter(x => g.matchesLookSearch(x,q)).map(x => x.id);
console.log(JSON.stringify({{chrome:find('chrome'),satin:find('satin')}}));
"""
    result = _node_json(script)

    assert {"mirror", "metal"}.issubset(result["chrome"])
    assert {"factory", "suede"}.issubset(result["satin"])


def test_search_can_offer_material_closest_matches_when_a_color_intersection_is_empty():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const looks = [
  {{id:'carbon',name:'Forged Carbon',category:'Texture',description:'black twill weave'}},
  {{id:'violet',name:'Violet Pearl',category:'Candy',description:'purple amethyst glow'}},
  {{id:'chrome',name:'Mirror Chrome',category:'Metal',description:'polished steel'}}
];
const strict = looks.filter(x => g.scoreLookSearch(x,'purple carbon') >= 0).map(x => x.id);
const relaxed = looks.filter(x => g.scoreLookSearch(x,'purple carbon',true) >= 0).map(x => x.id);
const nonsense = looks.filter(x => g.scoreLookSearch(x,'bananaphone wobble',true) >= 0).map(x => x.id);
console.log(JSON.stringify({{strict,relaxed,nonsense}}));
"""
    result = _node_json(script)

    assert result["strict"] == []
    assert result["relaxed"] == ["carbon"]
    assert result["nonsense"] == []


def test_search_intent_words_do_not_match_opposite_or_unrelated_substrings():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
const looks = [
  {{id:'candy_red',name:'Candy Apple Red',category:'Candy',description:'red candy depth'}},
  {{id:'colored_glass',name:'Jelly Pearl',category:'Candy',description:'like looking through colored glass'}},
  {{id:'mirror',name:'Mirror Chrome',category:'Metal',description:'bright metal with low roughness'}},
  {{id:'grit',name:'Metal Grit',category:'Metal',description:'rough gritty steel texture'}},
  {{id:'holo',name:'Spectral Field',category:'Shift',description:'holographic prism color flip'}}
];
const find = q => looks.filter(x => g.scoreLookSearch(x,q) >= 0).map(x => x.id);
console.log(JSON.stringify({{red:find('candy red'),rough:find('rough metal'),holo:find('holo')}}));
"""
    result = _node_json(script)

    assert result["red"] == ["candy_red"]
    assert result["rough"] == ["grit"]
    assert result["holo"] == ["holo"]


def test_catalog_cards_get_plain_material_family_labels():
    script = f"""
const g = require({json.dumps(str(GUIDANCE))});
console.log(JSON.stringify({{
  shift:g.describeLook({{kind:'catalog',id:'prizm_flip',name:'Prizm Flip'}}),
  texture:g.describeLook({{kind:'catalog',id:'carbon_twill',name:'Carbon Twill'}}),
  metal:g.describeLook({{kind:'catalog',id:'brushed_titanium',name:'Brushed Titanium'}}),
  soft:g.describeLook({{kind:'catalog',id:'factory_satin',name:'Factory Satin'}}),
  paradigm:g.describeLook({{kind:'catalog',id:'p_coronal',name:'PARADIGM Coronal Mass Ejection'}})
}}));
"""
    result = _node_json(script)

    assert result == {
        "shift": "SHIFT · COLOR FLIP",
        "texture": "TEXTURE · WEAVE",
        "metal": "METAL · CHROME",
        "soft": "SOFT · SATIN",
        "paradigm": "WILD · HIGH IMPACT",
    }
