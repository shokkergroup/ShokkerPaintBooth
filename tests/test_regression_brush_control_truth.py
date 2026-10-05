from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def test_pass_121_size_control_reports_its_real_one_pixel_endpoint():
    assert 'id="brushSize" name="brushSize" type="range" min="1" max="300"' in HTML
    assert 'aria-label="Brush size in pixels" aria-valuemin="1" aria-valuemax="300"' in HTML
    assert "range 1-300" in HTML
    assert "range 3-300" not in HTML


def test_pass_121_core_brush_controls_keep_live_accessible_values():
    assert 'aria-label="Brush flow percent" aria-valuemin="1" aria-valuemax="100" aria-valuenow="100"' in HTML
    assert 'aria-label="Brush spacing percent of brush size" aria-valuemin="1" aria-valuemax="200" aria-valuenow="25"' in HTML
    assert "this.setAttribute('aria-valuenow',this.value);this.title='Brush flow:" in HTML
    assert "this.setAttribute('aria-valuenow',this.value);this.title='Brush spacing:" in HTML
    assert 'id="brushShape" aria-label="Brush tip shape"' in HTML


def test_pass_121_dynamic_titles_follow_visible_values():
    assert "this.title='Brush / eraser size: '+this.value+'px (range 1-300)" in HTML
    assert "this.title='Active paint tool opacity: '+this.value+'%" in HTML
    assert "this.title='Brush hardness: '+this.value+'%" in HTML


def test_pass_121_runtime_is_cache_busted():
    assert "spb93-brush-control-truth-20260717" in HTML
    assert "spb93-effects-clear-transaction-20260717" in HTML
