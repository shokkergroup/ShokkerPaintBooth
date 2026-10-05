from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = ROOT / "paint-booth-3-canvas.js"
STATE = ROOT / "paint-booth-2-state-zones.js"


def test_layer_autosave_returns_structured_component_status():
    source = CANVAS.read_text(encoding="utf-8")
    assert "function _spbLayerAutosaveResult(ok, reason, extra)" in source
    assert "pixelDataSaved: false" in source
    assert "'payload-too-large'" in source
    assert "'quota-exceeded'" in source
    assert "window.__spbLayerAutosaveStatus = result" in source


def test_layer_recovery_is_crash_only_fingerprint_matched_and_confirmed():
    source = CANVAS.read_text(encoding="utf-8")
    assert "_la.cleanClose === false" in source
    assert "_la.sourceFingerprint === _currentFingerprint" in source
    assert "window.confirm('SPB found layer settings from an interrupted session" in source
    assert "source fingerprint did not match" in source
    assert "window.addEventListener('beforeunload', _spbMarkLayerAutosaveCleanClose)" in source
    assert "window.addEventListener('pagehide', _spbMarkLayerAutosaveCleanClose)" in source


def test_zone_badge_cannot_claim_full_success_after_layer_failure():
    source = STATE.read_text(encoding="utf-8")
    assert "const layerResult = _spbWriteLayerAutosaveComponent();" in source
    assert "Zone settings saved · layer recovery FAILED" in source
    assert "Project saves layer pixels" in source
    assert "window.__spbAutosaveStatus" in source


def test_zone_oversize_and_quota_recovery_publish_fresh_component_truth():
    source = STATE.read_text(encoding="utf-8")
    body = source[source.index("function autoSave() {"):source.index("function flushAutoSave() {")]

    oversize = body[body.index("if (json.length > 4 * 1024 * 1024)"):body.index("localStorage.setItem(AUTOSAVE_KEY, json)")]
    assert "reason: 'payload-too-large'" in oversize
    assert "const layerResult = _spbWriteLayerAutosaveComponent();" in oversize
    assert "_spbPublishAutosaveStatus(zoneResult, layerResult);" in oversize
    assert oversize.index("_spbPublishAutosaveStatus") < oversize.index("return;")

    recovery = body[body.index("const recoveredJson ="):body.index("} catch (e2)")]
    assert "reason: 'saved-after-eviction'" in recovery
    assert "const layerResult = _spbWriteLayerAutosaveComponent();" in recovery
    assert "_spbPublishAutosaveStatus(zoneResult, layerResult);" in recovery

    failure_tail = body[body.index("const zoneResult = { ok: false, component: 'zones', reason: e") :]
    assert "const layerResult = _spbWriteLayerAutosaveComponent();" in failure_tail
    assert "_spbPublishAutosaveStatus(zoneResult, layerResult);" in failure_tail
