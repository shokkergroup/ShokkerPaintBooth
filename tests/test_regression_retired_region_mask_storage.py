from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dead_periodic_region_mask_writer_is_removed():
    canvas = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
    assert "localStorage.setItem('spb_lastRegionMask_'" not in canvas
    assert "[69 retired 2026-08-22]" in canvas


def test_legacy_region_mask_keys_are_boot_cleaned_and_quota_evictable():
    state = (ROOT / "paint-booth-2-state-zones.js").read_text(encoding="utf-8")
    assert state.count("key.indexOf('spb_lastRegionMask_') === 0") >= 2
    assert "localStorage.removeItem(key); freed = true" in state

