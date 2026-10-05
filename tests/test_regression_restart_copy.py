from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_copy_routes_painters_to_the_packaged_tray_action():
    api = (ROOT / "paint-booth-5-api-render.js").read_text(encoding="utf-8")
    easy = (ROOT / "js" / "features" / "spb-easy-sculpt.js").read_text(encoding="utf-8")
    combined = api + "\n" + easy
    assert "Restart Server from the SPB tray" in combined
    assert "start the server and try again" not in combined
    assert "Restart the server after code changes" not in combined

