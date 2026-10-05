import json
import re
from pathlib import Path

from PIL import Image, ImageStat


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets" / "reference_textures" / "grunge_fun"
MANIFEST = ASSET_DIR / "manifest.json"
FINISH_DATA = ROOT / "paint-booth-0-finish-data.js"


def _manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_grunge_fun_manifest_covers_raw_uploads_and_runtime_assets():
    data = _manifest()
    finishes = data["finishes"]
    raw_uploads = sorted(
        p
        for p in ASSET_DIR.iterdir()
        if p.is_file()
        and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        and not p.stem.lower().startswith("gf_")
    )

    assert data["family"] == "Material World"
    assert len(finishes) == len(raw_uploads) == 48

    ids = [item["id"] for item in finishes]
    assert len(ids) == len(set(ids))

    for item in finishes:
        finish_id = item["id"]
        assert item["source"].startswith("assets/reference_textures/grunge_fun/")
        assert (ROOT / item["source"]).exists()
        assert (ASSET_DIR / f"{finish_id}.png").exists()
        assert (ASSET_DIR / f"{finish_id}_spec.png").exists()
        assert (ASSET_DIR / "jpg_2048" / f"{finish_id}.jpg").exists()
        assert (ASSET_DIR / "jpg_2048" / f"{finish_id}_spec.jpg").exists()


def test_grunge_fun_catalog_names_are_curated_and_searchable():
    stale_names = {
        "Or6ilf0",
        "V6t9 6fpy",
        "Casino",
        "A791 4c92 A2af",
        "44f1 Bfa5",
        "56af 4a68 B801",
        "04f4 4c25",
        "E982 4a17 B396",
        "8c1d",
        "Nwdlx0",
        "O4yijt0",
        "O4yijy0",
        "Oe3t1y0",
        "Oe46fw0",
        "12811 (1)",
    }
    numeric_suffix = re.compile(r"\b(?:0[1-9]|[1-4][0-9])$")

    for item in _manifest()["finishes"]:
        assert item["name"] not in stale_names
        assert not numeric_suffix.search(item["name"])
        assert "#dynamic-spec" in item["desc"]
        assert "#grunge" in item["desc"]
        assert "#fun" in item["desc"]
        assert "dynamic-spec" in item["tags"]


def test_grunge_fun_finish_data_uses_manifest_group_and_rows():
    data = _manifest()
    text = FINISH_DATA.read_text(encoding="utf-8")
    ids = [item["id"] for item in data["finishes"]]

    group_match = re.search(r'"GRUNGE & FUN": \[([^\]]+)\]', text)
    assert group_match, "GRUNGE & FUN group missing from finish-data"
    group_text = group_match.group(1)
    for finish_id in ids:
        assert f'"{finish_id}"' in group_text

    assert '"Material World": ["GRUNGE & FUN", "Atelier' in text
    assert '"Cultural": ["RISING SUN", "VIVA MEXICO", "UNION JACKED", "FORBIDDEN DRAGON"]' in text
    for item in data["finishes"]:
        assert f'name: "{item["name"]}"' in text
        assert "#dynamic-spec" in text


def test_grunge_fun_spec_maps_are_dynamic_not_flat():
    for item in _manifest()["finishes"]:
        spec_path = ASSET_DIR / f"{item['id']}_spec.png"
        with Image.open(spec_path) as img:
            thumb = img.convert("RGBA").resize((128, 128), Image.Resampling.BILINEAR)
        channels = ImageStat.Stat(thumb).extrema[:3]
        channel_spans = [hi - lo for lo, hi in channels]
        assert max(channel_spans) >= 24, f"{item['id']} spec lacks visible dynamic range"
