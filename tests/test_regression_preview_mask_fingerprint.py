import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASK_STATS = ROOT / "js" / "canvas" / "zone" / "mask-stats.js"
CANVAS = ROOT / "paint-booth-3-canvas.js"


def test_mask_fingerprint_is_position_sensitive_and_explicitly_invalidatable():
    script = r"""
const stats = require('./js/canvas/zone/mask-stats.js');

const left = new Uint8Array(128);
left[3] = 255;
left[77] = 128;
const right = new Uint8Array(128);
right[4] = 255;
right[76] = 128;

const leftKey = stats.fingerprint(left);
const rightKey = stats.fingerprint(right);
if (leftKey === rightKey) throw new Error('equal-sum masks collided');

const before = stats.fingerprint(left);
left[3] = 0;
left[4] = 255;
stats.invalidate(left);
const after = stats.fingerprint(left);
if (before === after) throw new Error('in-place edit survived explicit invalidation');
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_preview_and_incremental_zone_keys_cover_all_mutable_masks():
    source = CANVAS.read_text(encoding="utf-8")
    assert "patternStrengthMapFingerprint" in source
    assert "rmFingerprint" in source
    assert "smFingerprint" in source
    assert "strengthMapFingerprint" in source
    assert "window.SPBMaskStats.invalidate();" in source
    assert "window.__spbPreviewBodyMemo = null;" in source
    assert "patternStrengthMapSum" not in source
    assert "_spbFastMaskSum" not in source


def test_native_preview_does_not_schedule_retired_enhancement_stages():
    source = CANVAS.read_text(encoding="utf-8")
    assert "_previewStage2Timer = setTimeout" not in source
    assert "_previewEnhanceTimer = setTimeout" not in source


def test_preview_fails_closed_when_canonical_render_serializer_is_missing():
    source = CANVAS.read_text(encoding="utf-8")
    guard = "if (!_pbMemo && typeof window.buildServerZonesForRender !== 'function')"
    builder = "const serverZones = _pbMemo ? _pbMemo.serverZones"
    assert guard in source
    assert "Canonical render serializer unavailable" in source
    assert source.index(guard) < source.index(builder)
