from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess

from PIL import Image

from demo import build_demo_stage as stage
from demo.backend.catalog import DemoCatalog
from demo.backend.recipe import RECIPE_SCHEMA, build_render_recipe


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "demo" / "frontend"
MODULE = FRONTEND / "js" / "branding-recipe.js"
CSS = FRONTEND / "branding-recipe.css"
MANIFEST = ROOT / "demo" / "product-manifest.json"
BRANDING = FRONTEND / "assets" / "branding"

LOGOS = {
    "shokk-handmark.png": {
        "size": (1254, 1254),
        "sha256": "fd5c68df69bc9ef30f080f9ad263ca8b1352c05b8f7946d0058747aadc8c3917",
    },
    "shokker-paint-booth.png": {
        "size": (1672, 941),
        "sha256": "11a8d59f2765fd5ab4fee9f15bd5318e21df64d52be3de477a75e5a37b5375d9",
    },
    "shokker-road.png": {
        "size": (1672, 941),
        "sha256": "b17ed74603ff7af86d85a386fb255c6b4599dda9eb1850dff09ae4406add3809",
    },
}
SPLASH_VIDEO = "spb-splash-intro.mp4"
SPLASH_VIDEO_BYTES = 10_803_903
SPLASH_VIDEO_SHA256 = "5b4cef4b04cdb25f132109710545cf2e9104a0d733b1ab8a52938667388d3ce1"
BRANDING_FILES = set(LOGOS) | {SPLASH_VIDEO}


def test_owner_supplied_brand_assets_are_exact_and_stage_allowlisted() -> None:
    assert {path.name for path in BRANDING.iterdir()} == BRANDING_FILES
    for name, expected in LOGOS.items():
        path = BRANDING / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected["sha256"]
        with Image.open(path) as image:
            assert image.size == expected["size"]
            assert image.format == "PNG"
        assert f"assets/branding/{name}" in stage.FRONTEND_FILES

    splash = BRANDING / SPLASH_VIDEO
    splash_bytes = splash.read_bytes()
    assert len(splash_bytes) == SPLASH_VIDEO_BYTES
    assert hashlib.sha256(splash_bytes).hexdigest() == SPLASH_VIDEO_SHA256
    assert b"ftyp" in splash_bytes[:64]
    assert 0 < splash_bytes.find(b"moov") < splash_bytes.find(b"mdat")
    assert f"assets/branding/{SPLASH_VIDEO}" in stage.FRONTEND_FILES

    allowlisted_branding = {
        Path(item).name for item in stage.FRONTEND_FILES if item.startswith("assets/branding/")
    }
    assert allowlisted_branding == BRANDING_FILES
    assert "recipe.py" in stage.BACKEND_FILES
    assert "js/branding-recipe.js" in stage.FRONTEND_FILES
    assert "branding-recipe.css" in stage.FRONTEND_FILES


def test_runtime_copy_stages_only_the_four_allowlisted_brand_assets(tmp_path: Path) -> None:
    server = tmp_path / "server"
    stage.copy_runtime_sources(ROOT, server)
    staged = server / "frontend" / "assets" / "branding"
    assert {path.name for path in staged.iterdir()} == BRANDING_FILES
    for name in BRANDING_FILES:
        assert (staged / name).read_bytes() == (BRANDING / name).read_bytes()


def test_manifest_declares_only_the_three_reviewed_startup_logos() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    branding = manifest["branding"]
    assert branding["logo_url"] == "/assets/branding/shokker-paint-booth.png"
    assert branding["startup_logos"] == [
        "/assets/branding/shokk-handmark.png",
        "/assets/branding/shokker-paint-booth.png",
        "/assets/branding/shokker-road.png",
    ]


def test_backend_builds_compact_standalone_recipe_contract() -> None:
    catalog = DemoCatalog(MANIFEST)
    zones = [
        {
            "name": "Numbers + logos",
            "_demo_finish_id": "f_chrome",
            "_demo_color_finish_id": "ffo_haz_bloom",
            "_demo_coverage_mode": "colors",
            "_demo_source_layer_restricted": True,
            "_demo_source_layer_scope_id": "scope-1",
            "source_layers": ["numbers", "logos"],
            "color": [{"color_rgb": [255, 0, 0], "tolerance": 22}],
            "exclusions": [{"hex": "#00FF00", "tolerance": 9}],
            "base_color_mode": "special",
            "lock_base_color": True,
            "base_color_strength": 0.65,
            "intensity": 80,
            "base_strength": 0.75,
            "base_spec_strength": 3.0,
            "base_scale": 0.25,
            "base_rotation": 180,
            "spec_scale": 0.5,
            "spec_rotation": 45,
            "base_spec_blend_mode": "overlay",
            "spec_channel_shift": [10, -20, 30],
        }
    ]
    recipe = build_render_recipe(
        request_data={
            "paint_file": r"C:\paints\Starter.psd",
            "car_number": "24",
        },
        zones=zones,
        catalog=catalog,
        job_id="render_1234567890_abcdef1234567890",
        elapsed_seconds=1.23,
        source_transport="file",
        output_status={
            "path": r"C:\iRacing\paint\stockcars",
            "verified": True,
            "pushed_files": ["car_num_23371.tga", "car_spec_23371.tga"],
        },
        preview_urls={
            "RENDER_paint.png": "/preview/job/RENDER_paint.png",
            "RENDER_spec.png": "/preview/job/RENDER_spec.png",
        },
        download_urls={"car_num_23371": "/download/job/car_num_23371.tga"},
        use_custom_number=True,
        iracing_id="23371",
    )

    assert recipe["schema"] == RECIPE_SCHEMA
    assert recipe["render"]["source"]["name"] == "Starter.psd"
    assert recipe["render"]["output"]["verified"] is True
    assert recipe["render"]["number"] == {
        "mode": "custom",
        "value": "24",
        "iracing_id": "23371",
    }
    zone = recipe["zones"][0]
    assert zone["order"] == 1
    assert zone["material"]["name"] == "Chrome (Foundation)"
    assert zone["base_color"]["source"]["name"] == "HAZ Bloom"
    assert zone["base_color"]["locked"] is True
    assert zone["base_color"]["strength"] == 65
    assert zone["coverage"]["colors"] == [{"color": "#FF0000", "tolerance": 22}]
    assert zone["coverage"]["exclusions"] == [{"color": "#00FF00", "tolerance": 9}]
    assert zone["coverage"]["layer_scope"]["ids"] == ["numbers", "logos"]
    assert zone["strengths"] == {"zone": 80, "base": 75, "spec": 300}
    serialized = json.dumps(recipe)
    assert "source_data_url" not in serialized
    assert "source_layer_mask" not in serialized


def test_frontend_module_has_one_time_splash_then_explicit_rotating_entry_gate() -> None:
    source = MODULE.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    html = (FRONTEND / "paint-booth-v2.html").read_text(encoding="utf-8")
    assert "sessionStorage" not in source
    assert "FIRST_LAUNCH_SPLASH_STORAGE_KEY = 'spb_demo_splash_intro_seen_v1'" in source
    assert "FIRST_LAUNCH_SPLASH_URL = '/assets/branding/spb-splash-intro.mp4'" in source
    assert "FIRST_LAUNCH_SPLASH_TIMEOUT_MS = 15000" in source
    assert "FIRST_LAUNCH_SPLASH_STALL_MS = 2200" in source
    assert "localStorage" in source
    assert "markFirstLaunchSplashSeen(storage)" in source
    assert "SKIP INTRO" in source
    assert "ENTER OR ESC" in source
    assert "video.muted = false" in source
    assert "video.muted = true" in source
    assert "video.volume = .75" in source
    assert "complete('ended', true)" in source
    assert "complete('skipped', true)" in source
    assert "complete('error', false)" in source
    assert "complete('stalled', false)" in source
    assert "complete('timeout', false)" in source
    assert "complete('autoplay-blocked', false)" in source
    assert source.index("await runFirstLaunchSplash()") < source.index("await runBrandIntro()")
    assert "runStartupExperience().catch" in source
    assert "DOMContentLoaded" not in source
    assert "shuffledLogoOrder(BRAND_LOGOS, secureRandom)" in source
    assert "while (!signal.aborted)" in source
    assert "INTRO_CARD_HOLD_MS = 2800" in source
    assert "INTRO_CROSSFADE_MS = 800" in source
    assert "INTRO_READY_TIMEOUT_MS = 15000" in source
    assert "ENTER SHOKKER PAINT BOOTH" in source
    assert "PREPARING YOUR STARTER PAINT" in source
    assert "event.key === 'Enter'" in source
    escape_block = source[source.index("if (event.key === 'Escape')") :][:180]
    assert "preventDefault" in escape_block
    assert "admit()" not in escape_block
    assert "aria-modal" in source
    assert "setAttribute('inert'" in source
    assert "demo-spray-canvas" in source
    assert "runSprayReveal" in source
    assert "await waitForAppReady(app)" in source
    assert source.index("await waitForAppReady(app)") < source.index("controller.abort()")
    assert source.index("await waitForAppReady(app)") < source.index("classList.add('admitting')")
    brand_intro = source[source.index("async function runBrandIntro()") : source.index("function lockAppForStartupExperience()")]
    assert brand_intro.index("await runSprayReveal") < brand_intro.index("removeEventListener('keydown'")
    assert "setTimeout(() => runBrandIntro" not in source
    assert "prefers-reduced-motion: reduce" in source
    assert "demo-brand-static-strip" in source
    assert "requestUrl.pathname === '/render'" in source
    assert "spb-demo-render-recipe/1" in source
    assert "source_data_url" not in source
    assert "source_layer_scopes" not in source
    assert "paint-booth-5-api-render.js" not in source
    assert "prefers-reduced-motion: reduce" in css
    assert "body.demo-startup-pending > #app" in css
    assert ".demo-splash-intro.leaving" in css
    assert ".demo-brand-intro.reduced-motion .demo-brand-static-strip" in css
    assert ".demo-brand-intro.admitting .demo-spray-canvas" in css
    assert '<body class="demo-startup-pending">' in html
    assert "media-src 'self'" in html


def test_brand_intro_cache_tokens_are_bumped_together() -> None:
    html = (FRONTEND / "paint-booth-v2.html").read_text(encoding="utf-8")
    css_token = re.search(r"/branding-recipe\.css\?v=([^\"']+)", html)
    js_token = re.search(r"/js/branding-recipe\.js\?v=([^\"']+)", html)
    app_token = re.search(r"/js/app\.js\?v=([^\"']+)", html)
    assert css_token is not None
    assert js_token is not None
    assert app_token is not None
    assert css_token.group(1) == js_token.group(1) == app_token.group(1)
    version = json.loads((ROOT / "demo/product-manifest.json").read_text(encoding="utf-8"))["product"]["version"]
    assert css_token.group(1).startswith('demo' + version.rsplit('.', 1)[-1] + '-')


def test_frontend_recipe_module_parses_and_formats_in_node() -> None:
    script = r"""
import { readFileSync } from 'node:fs';
const source = readFileSync(process.argv[1], 'utf8');
const url = `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const mod = await import(url);
const order = mod.shuffledLogoOrder(['a', 'b', 'c'], () => 0);
const values = new Map();
const storage = {
  getItem: (key) => values.has(key) ? values.get(key) : null,
  setItem: (key, value) => values.set(key, value),
};
const seenBefore = mod.hasSeenFirstLaunchSplash(storage);
const marked = mod.markFirstLaunchSplashSeen(storage);
const seenAfter = mod.hasSeenFirstLaunchSplash(storage);
const reducedValues = new Map();
const reducedStorage = {
  getItem: (key) => reducedValues.has(key) ? reducedValues.get(key) : null,
  setItem: (key, value) => reducedValues.set(key, value),
};
const reducedResult = await mod.runFirstLaunchSplash({ storage: reducedStorage, reducedMotion: true });
const reducedSeen = mod.hasSeenFirstLaunchSplash(reducedStorage);
const text = mod.recipeText({
  render: {
    source: { path: 'Starter.psd' },
    output: { path: 'paint/car.tga' },
    number: { mode: 'custom', value: '24', iracing_id: '23371' },
  },
  zones: [{
    order: 1,
    name: 'Body',
    material: { name: 'Chrome' },
    coverage: { mode: 'remaining' },
    base_color: { mode: 'source', strength: 100 },
    strengths: { zone: 50, base: 100, spec: 100 },
    adjustments: { spec_channels: { metal: 0, rough: 0, coat: 0 } },
  }],
  links: { payhip: 'https://payhip.com/b/AHgpV', discord: 'https://discord.gg/test' },
});
process.stdout.write(JSON.stringify({
  order,
  text,
  timing: [mod.INTRO_CARD_HOLD_MS, mod.INTRO_CROSSFADE_MS, mod.INTRO_SPRAY_MS, mod.INTRO_READY_TIMEOUT_MS],
  splash: {
    key: mod.FIRST_LAUNCH_SPLASH_STORAGE_KEY,
    url: mod.FIRST_LAUNCH_SPLASH_URL,
    timing: [mod.FIRST_LAUNCH_SPLASH_TIMEOUT_MS, mod.FIRST_LAUNCH_SPLASH_STALL_MS, mod.FIRST_LAUNCH_SPLASH_PLAY_TIMEOUT_MS],
    seenBefore,
    marked,
    seenAfter,
    reducedResult,
    reducedSeen,
  },
}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script, str(MODULE)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    value = json.loads(completed.stdout)
    assert value["order"] == ["b", "c", "a"]
    assert value["timing"] == [2800, 800, 820, 15000]
    assert value["splash"] == {
        "key": "spb_demo_splash_intro_seen_v1",
        "url": "/assets/branding/spb-splash-intro.mp4",
        "timing": [15000, 2200, 1400],
        "seenBefore": False,
        "marked": True,
        "seenAfter": True,
        "reducedResult": "reduced-motion",
        "reducedSeen": True,
    }
    assert "RENDER RECIPE" in value["text"]
    assert "Body" in value["text"]
    assert "Chrome" in value["text"]
    assert "Remaining" in value["text"]
