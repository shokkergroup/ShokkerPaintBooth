import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def test_zone_mask_noop_helpers_detect_identical_copy_and_symmetric_mirror():
    script = r"""
const api = require('./js/canvas/zone/zone-mask-history.js');
const symmetric = new Uint8Array([
  1,2,2,1,
  0,9,9,0
]);
const asymmetric = new Uint8Array([
  1,2,3,4,
  0,9,9,0
]);
process.stdout.write(JSON.stringify({
  same: api.masksEqual(symmetric, new Uint8Array(symmetric)),
  different: api.masksEqual(symmetric, asymmetric),
  symmetricMirrorChanges: api.horizontalMirrorDiffers(symmetric, 4, 2),
  asymmetricMirrorChanges: api.horizontalMirrorDiffers(asymmetric, 4, 2)
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert json.loads(result.stdout) == {
        "same": True,
        "different": False,
        "symmetricMirrorChanges": False,
        "asymmetricMirrorChanges": True,
    }


def test_copy_and_mirror_refuse_noops_before_history():
    copy_start = CANVAS.index("function copyMaskToZone(targetIndex)")
    copy_end = CANVAS.index("function mirrorRegionMask()", copy_start)
    copy_body = CANVAS[copy_start:copy_end]
    mirror_start = copy_end
    mirror_end = CANVAS.index("function setOverlayOpacity", mirror_start)
    mirror_body = CANVAS[mirror_start:mirror_end]

    assert copy_body.index("masksEqual") < copy_body.index("pushUndo(targetIndex)")
    assert "return false;" in copy_body[copy_body.index("masksEqual"):copy_body.index("pushUndo(targetIndex)")]
    assert copy_body.index("showToast(`Copied mask") < copy_body.index("return true;")
    assert mirror_body.index("horizontalMirrorDiffers") < mirror_body.index("pushUndo(selectedZoneIndex)")
    assert "return false;" in mirror_body[mirror_body.index("horizontalMirrorDiffers"):mirror_body.index("pushUndo(selectedZoneIndex)")]


def test_visible_advanced_mask_mutations_share_complete_ui_settlement():
    settlement = CANVAS[
        CANVAS.index("function _refreshZoneMaskHistoryUI"):
        CANVAS.index("function pushZoneMaskUndoSnapshotForRedo")
    ]
    for call in (
        "renderRegionOverlay()", "renderZoneDetail(selectedZoneIndex)",
        "renderZones()", "updateRegionStatus()", "renderContextActionBar()",
        "triggerPreviewRender()",
    ):
        assert call in settlement

    invert = CANVAS[
        CANVAS.index("function invertRegionMask()"):
        CANVAS.index("function _selectionRefineContext")
    ]
    copy = CANVAS[
        CANVAS.index("function copyMaskToZone(targetIndex)"):
        CANVAS.index("function mirrorRegionMask()")
    ]
    mirror = CANVAS[
        CANVAS.index("function mirrorRegionMask()"):
        CANVAS.index("function setOverlayOpacity")
    ]
    for body in (invert, copy, mirror):
        assert body.count("_refreshZoneMaskHistoryUI()") == 1
        assert "renderRegionOverlay()" not in body
        assert "triggerPreviewRender()" not in body


def test_copy_mask_menu_portals_its_targets_out_of_hidden_tool_options():
    start = CANVAS.index("function toggleCopyMaskDropdown(e)")
    end = CANVAS.index("function copyMaskToZone(targetIndex)", start)
    body = CANVAS[start:end]
    assert "dd.getClientRects().length > 0" in body
    assert "document.body.appendChild(dd)" in body
    assert "trigger?.getBoundingClientRect?.()" in body
    assert "dd._spbTrigger = trigger" in body
    assert "_closeCopyMaskDropdown(true)" in body
    assert "_closeCopyMaskDropdown(false)" in body
    assert "document.removeEventListener('mousedown', dd._spbOutsideClose)" in CANVAS
    assert "dd.style.position = 'fixed'" in body
    assert "role=\"menuitem\"" in body
    assert "aria-label', 'Copy mask to Zone'" in body
    assert "ev.key === 'Escape'" in body
    assert "ev.key === 'ArrowDown' || ev.key === 'ArrowUp'" in body


def test_zone_mask_noop_runtime_is_cache_busted_and_mirrored():
    assert "zone-mask-history.js?v=spb93-zone-mask-noop-truth-20260808a" in HTML
    assert 'src="paint-booth-3-canvas.js?v=' in HTML
    for relative in (
        "js/canvas/zone/zone-mask-history.js",
        "paint-booth-3-canvas.js",
        "paint-booth-v2.html",
    ):
        assert (ROOT / relative).read_bytes() == (ROOT / "electron-app/server" / relative).read_bytes()
