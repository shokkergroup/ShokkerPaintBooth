from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_iracing_coexistence_mode_is_loaded_last_and_default_on():
    html = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")

    coexistence_link = "css/spb-iracing-coexistence.css?v=spb-iracing-coexistence-20260824a"
    gallery_link = "css/spb-look-gallery-20260728.css?v=spb-look-gallery-20260728a"
    assert coexistence_link in html
    assert html.index(coexistence_link) > html.index(gallery_link)
    assert "spb_iracing_performance_mode" in html
    assert "return stored !== 'off';" in html
    assert "reduce || readIracingPerformanceMode()" in html
    assert "window.setSpbIracingPerformanceMode" in html


def test_iracing_coexistence_css_stops_only_frontend_compositor_effects():
    css = (ROOT / "css" / "spb-iracing-coexistence.css").read_text(encoding="utf-8")

    assert "body.fx-off *" in css
    assert "animation: none !important" in css
    assert "transition-duration: 0s !important" in css
    assert "will-change: auto !important" in css
    assert "backdrop-filter: none !important" in css
    # The coexistence layer must not monkey-patch functional render/timer APIs.
    for forbidden in ("requestAnimationFrame", "setInterval", "fetch(", "WebSocket"):
        assert forbidden not in css


def test_iracing_coexistence_css_is_runtime_synced():
    manifest = (ROOT / "scripts" / "runtime-sync-manifest.json").read_text(encoding="utf-8")
    assert '"css/spb-iracing-coexistence.css"' in manifest


def test_background_connectivity_poll_uses_tiny_health_payload():
    api = (ROOT / "paint-booth-5-api-render.js").read_text(encoding="utf-8")

    assert "async checkStatusLight()" in api
    assert "fetch(this.baseUrl + '/health'" in api
    assert "if (!this._portDiscovered) return this.checkStatus();" in api
    assert "if (wasOffline && this.online) return this.checkStatus();" in api
    assert "this.checkStatusLight().then(() =>" in api
    assert "ShokkerAPI.checkStatusLight().then(d =>" in api
