"""Focused, isolated contracts for SPB Projects v2.

These tests never start or contact the live Paint Booth server.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
import subprocess
import tempfile
import textwrap

import pytest
from flask import Flask

from server_routes.project_routes import register_project_routes


ROOT = Path(__file__).resolve().parents[1]
PROJECT_JS = ROOT / "js" / "features" / "spb-projects.js"
ONE_PIXEL_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/"
    "W9nGAAAAAElFTkSuQmCC"
)


@pytest.fixture()
def project_api():
    with tempfile.TemporaryDirectory(prefix="spb-projects-test-") as temp:
        root = Path(temp)
        projects_dir = root / "projects"
        app = Flask(__name__)
        app.config.update(TESTING=True)
        register_project_routes(
            app,
            logging.getLogger("spb-project-test"),
            projects_dir_getter=lambda: str(projects_dir),
        )
        yield app.test_client(), projects_dir, root


def _source(tmp_path: Path, payload: bytes = b"source-paint-v1") -> Path:
    path = tmp_path / "owner-paint.psd"
    path.write_bytes(payload)
    return path


def _envelope(source: Path, name: str = "Exact Workflow") -> dict:
    return {
        "name": name,
        "project": {
            "_spb_project": True,
            "version": "2.0",
            "schemaVersion": 2,
            "name": name,
            "sourcePaintFile": str(source),
            "selectedLayerId": "painted_numbers",
            "config": {
                "paintFile": str(source),
                "zones": [{
                    "name": "Numbers",
                    "sourceLayer": "painted_numbers",
                    "sourceLayers": ["painted_numbers"],
                }],
            },
            "layers": [{
                "id": "painted_numbers",
                "path": "Artwork/Numbers",
                "name": "Numbers",
                "imgData": ONE_PIXEL_PNG,
            }],
        },
    }


def test_save_stamps_schema_and_content_fingerprint(project_api):
    client, projects_dir, root = project_api
    source = _source(root)

    response = client.post("/api/projects/save", json=_envelope(source))
    assert response.status_code == 200
    saved = response.get_json()
    assert saved["ok"] is True
    assert saved["schemaVersion"] == 2

    on_disk = json.loads((projects_dir / saved["file"]).read_text(encoding="utf-8"))
    assert on_disk["version"] == "2.0"
    assert on_disk["schemaVersion"] == 2
    assert on_disk["layers"][0]["id"] == "painted_numbers"
    assert on_disk["layers"][0]["imgData"] == ONE_PIXEL_PNG
    assert on_disk["sourceFingerprint"]["sha256"] == hashlib.sha256(
        source.read_bytes()).hexdigest()

    opened = client.post("/api/projects/open", json={"file": saved["file"]})
    assert opened.status_code == 200
    status = opened.get_json()["sourceStatus"]
    assert status["exists"] is True
    assert status["matchesSavedFingerprint"] is True
    assert status["legacyUnverified"] is False
    verified = client.post("/api/projects/verify-source", json={"file": saved["file"]})
    assert verified.status_code == 200
    assert verified.get_json()["sourceStatus"]["matchesSavedFingerprint"] is True


def test_changed_or_missing_source_is_reported_before_client_restore(project_api):
    client, _, root = project_api
    source = _source(root)
    saved = client.post("/api/projects/save", json=_envelope(source)).get_json()

    source.write_bytes(b"changed-after-save")
    changed = client.post("/api/projects/open", json={"file": saved["file"]})
    assert changed.get_json()["sourceStatus"]["matchesSavedFingerprint"] is False
    changed_again = client.post("/api/projects/verify-source", json={"file": saved["file"]})
    assert changed_again.get_json()["sourceStatus"]["matchesSavedFingerprint"] is False

    source.unlink()
    missing = client.post("/api/projects/open", json={"file": saved["file"]})
    status = missing.get_json()["sourceStatus"]
    assert status["exists"] is False
    assert status["matchesSavedFingerprint"] is False


def test_missing_source_refuses_save_without_creating_project(project_api):
    client, projects_dir, root = project_api
    missing = root / "gone.psd"
    response = client.post("/api/projects/save", json=_envelope(missing))
    assert response.status_code == 409
    assert response.get_json()["code"] == "source_unavailable"
    assert not list(projects_dir.glob("*.spbproj"))


def test_chunk_upload_round_trips_payload_and_rejects_out_of_order(project_api):
    client, _, root = project_api
    source = _source(root)
    raw = json.dumps(_envelope(source), ensure_ascii=False).encode("utf-8")

    start = client.post("/api/projects/save/start", json={"totalBytes": len(raw)})
    upload_id = start.get_json()["uploadId"]
    split = max(1, len(raw) // 3)
    parts = [raw[index:index + split] for index in range(0, len(raw), split)]
    for index, part in enumerate(parts):
        response = client.post(
            f"/api/projects/save/chunk/{upload_id}",
            data=part,
            headers={"X-SPB-Chunk-Index": str(index)},
            content_type="application/octet-stream",
        )
        assert response.status_code == 200
    committed = client.post(f"/api/projects/save/commit/{upload_id}")
    assert committed.status_code == 200
    assert committed.get_json()["ok"] is True

    second = client.post("/api/projects/save/start", json={"totalBytes": len(raw)})
    second_id = second.get_json()["uploadId"]
    out_of_order = client.post(
        f"/api/projects/save/chunk/{second_id}",
        data=raw[:10],
        headers={"X-SPB-Chunk-Index": "1"},
        content_type="application/octet-stream",
    )
    assert out_of_order.status_code == 409
    assert out_of_order.get_json()["code"] == "invalid_chunk"
    assert client.post(f"/api/projects/save/abort/{second_id}").status_code == 200


def test_legacy_project_remains_readable_but_is_marked_unverified(project_api):
    client, projects_dir, root = project_api
    source = _source(root)
    projects_dir.mkdir(parents=True, exist_ok=True)
    legacy = _envelope(source)["project"]
    legacy.pop("schemaVersion")
    legacy.pop("sourceFingerprint", None)
    legacy["version"] = "1.0"
    (projects_dir / "Legacy.spbproj").write_text(json.dumps(legacy), encoding="utf-8")

    opened = client.post("/api/projects/open", json={"file": "Legacy.spbproj"})
    assert opened.status_code == 200
    status = opened.get_json()["sourceStatus"]
    assert status["exists"] is True
    assert status["matchesSavedFingerprint"] is None
    assert status["legacyUnverified"] is True


def test_client_serializes_psd_backed_pixels_and_never_builds_dynamic_html():
    source = PROJECT_JS.read_text(encoding="utf-8")
    assert "record.id =" not in source  # ID is declared in the record itself.
    assert "id: String(layer.id" in source
    assert "record.imgData = _layerRasterDataUrl(layer)" in source
    assert "groupChain: Array.isArray(layer.groupChain) ? _clone(layer.groupChain) : []" in source
    assert "if (Array.isArray(record.groupChain))" in source
    assert "layer.groupChain = _clone(record.groupChain)" in source
    assert "if (!layer.path" not in source
    assert "flatResult = await window.loadPaintByPath(source)" in source
    assert "if (!window.loadPaintByPath(source))" not in source
    assert "transaction.captureDocumentState()" in source
    assert "snapshot.transaction.restoreDocumentState(snapshot.sourceState)" in source
    assert ".innerHTML" not in source
    assert "onclick=" not in source
    assert "element.textContent = String(text)" in source


def test_client_fail_closed_and_remaps_layer_ids_in_node():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');
        const assert = require('assert');
        const code = fs.readFileSync(__PROJECT_JS__, 'utf8');

        function copy(value) { return JSON.parse(JSON.stringify(value)); }

        function contextFor(openPayload, verifyPayload) {
          const toasts = [];
          let fetchCount = 0;
          let configCalls = 0;
          let failProjectConfig = false;
          const state = {
            source: 'A.psd', fingerprint: 'fingerprint-A', generation: 1,
            paintToken: 'pixels-A', selected: 'a-layer',
            config: { marker: 'A', paintFile: 'A.psd', zones: [{ name: 'A zone' }] },
          };
          const aLayer = {
            id: 'a-layer', path: 'A/Artwork', name: 'A artwork',
            img: { marker: 'pixels-A', toDataURL() { return __PNG__; } },
          };
          const sandbox = {
            console, setTimeout, clearTimeout, Blob,
            Image: function() {},
            document: {
              getElementById() { return null; },
              createElement() { return { style: {}, addEventListener() {}, appendChild() {}, getContext() { return null; } }; },
              body: { appendChild() {} },
            },
            _psdLayers: [aLayer],
          };
          const manager = {
            committedPath: state.source,
            committedFingerprint: state.fingerprint,
            getGeneration() { return state.generation; },
            getCommittedPath() { return this.committedPath; },
            getCommittedFingerprint() { return this.committedFingerprint; },
            captureDocumentState() {
              return {
                source: state.source, fingerprint: state.fingerprint,
                paintToken: state.paintToken, selected: state.selected,
                layers: sandbox._psdLayers, psdData: sandbox.window._psdData,
                layersLoaded: sandbox.window._psdLayersLoaded,
              };
            },
            restoreDocumentState(snapshot) {
              state.generation += 1;
              state.source = snapshot.source;
              state.fingerprint = snapshot.fingerprint;
              state.paintToken = snapshot.paintToken;
              state.selected = snapshot.selected;
              sandbox._psdLayers = snapshot.layers;
              sandbox.window._psdLayers = snapshot.layers;
              sandbox.window._psdData = snapshot.psdData;
              sandbox.window._psdLayersLoaded = snapshot.layersLoaded;
              sandbox.window._selectedLayerId = snapshot.selected;
              this.committedPath = snapshot.source;
              this.committedFingerprint = snapshot.fingerprint;
              return { ok: true };
            },
          };
          sandbox.window = {
            showToast(message) { toasts.push(String(message)); },
            getCurrentSourcePaintFile() { return state.source; },
            getConfig() { return copy(state.config); },
            loadConfigFromObj(config) {
              configCalls += 1;
              if (failProjectConfig && config.marker === 'B') {
                throw new Error('synthetic config failure');
              }
              state.config = copy(config);
            },
            SPBSourceLoadTransaction: manager,
            _psdLayers: sandbox._psdLayers,
            _psdLayersLoaded: true,
            _psdData: { success: true, source: 'A' },
            _selectedLayerId: state.selected,
          };
          sandbox.fetch = async () => {
            const payload = fetchCount++ === 0 ? openPayload : (verifyPayload || openPayload);
            return { status: 200, async text() { return JSON.stringify(payload); } };
          };
          vm.createContext(sandbox);
          vm.runInContext(code, sandbox);

          function installSuccessfulB(layers) {
            sandbox.window.importPSDFromPath = async (path) => {
              state.generation += 1;
              state.source = path;
              state.fingerprint = 'fingerprint-B';
              state.paintToken = 'pixels-B';
              state.selected = layers[0] ? layers[0].id : null;
              sandbox._psdLayers = layers;
              sandbox.window._psdLayers = layers;
              sandbox.window._psdLayersLoaded = true;
              sandbox.window._psdData = { success: true, source: 'B' };
              manager.committedPath = path;
              manager.committedFingerprint = state.fingerprint;
              return {
                ok: true, requestedPath: path, committedPath: path,
                generation: state.generation, fingerprint: state.fingerprint, error: null,
              };
            };
          }

          function digest() {
            return JSON.stringify({
              source: state.source, fingerprint: state.fingerprint,
              paintToken: state.paintToken, selected: state.selected,
              config: state.config,
              layers: sandbox._psdLayers.map(layer => ({
                id: layer.id, path: layer.path, name: layer.name,
                marker: layer.img && layer.img.marker,
              })),
            });
          }

          return {
            sandbox, state, toasts, digest, installSuccessfulB,
            configCalls: () => configCalls,
            failProjectConfig() { failProjectConfig = true; },
          };
        }

        const status = { requestedPath: 'B.psd', exists: true, matchesSavedFingerprint: true };
        const baseProject = {
          _spb_project: true, schemaVersion: 2, name: 'B',
          sourcePaintFile: 'B.psd', config: { marker: 'B', zones: [] }, layers: [],
        };
        const record = { id: 'psd_0', path: 'Artwork/Numbers', name: 'Numbers',
          elementLinkGroups: [[{x1:10,y1:20,x2:30,y2:40,layerId:'psd_0'}]],
          elementInstances: [{sourceBbox:{x1:10,y1:20,x2:30,y2:40},instanceBbox:{x1:50,y1:20,x2:70,y2:40},sourcePixelSnapshot:__PNG__}],
        };
        const goodProject = {
          ...baseProject, selectedLayerId: 'psd_0', layers: [record],
          config: { marker: 'B', zones: [{ name: 'Numbers', sourceLayer: 'psd_0', sourceLayers: ['psd_0'] }] },
        };
        const open = project => ({ ok: true, project, sourceStatus: status });
        const sourceLayers = () => [
          { id: 'psd_0', path: 'Artwork/Numbers', name: 'Numbers', img: { marker: 'source-B' } },
          { id: 'psd_1', path: 'Artwork/Deleted', name: 'Source extra', img: { marker: 'extra-B' } },
        ];
        function assertRestoredA(context, before) {
          assert.strictEqual(context.digest(), before, 'document A must be restored byte/state-identically');
          assert(context.toasts.some(value => value.includes('previous document was restored')));
          assert(!context.toasts.some(value => value.includes(' restored — ')), 'failure must not toast success');
        }

        (async () => {
          // PSD-backed live pixels and stable IDs are always captured.
          const capturedContext = contextFor(open(baseProject));
          const captured = capturedContext.sandbox.window.SPBProjects.buildProjectPayload('Capture');
          assert.strictEqual(captured.layers[0].id, 'a-layer');
          assert.strictEqual(captured.layers[0].imgData, __PNG__);
          assert.strictEqual(captured.layers[0].pixelState, 'embedded');

          // A missing/malformed loader contract fails closed and restores A.
          const malformed = contextFor(open(baseProject));
          const malformedBefore = malformed.digest();
          malformed.sandbox.window.importPSDFromPath = async () => undefined;
          assert.strictEqual(await malformed.sandbox.window.loadSpbProject('B.spbproj'), false);
          assertRestoredA(malformed, malformedBefore);
          assert(malformed.toasts.some(value => value.includes('no transactional result')));

          // Pure config remapping preserves both canonical and legacy mirrors.
          const mapped = malformed.sandbox.window.SPBProjects.remapProjectConfig(
            { zones: [{ name: 'Numbers', sourceLayer: 'old', sourceLayers: ['old'] }] },
            { old: 'new' }, new Set(['new'])
          );
          assert.deepStrictEqual(Array.from(mapped.config.zones[0].sourceLayers), ['new']);
          assert.strictEqual(mapped.config.zones[0].sourceLayer, 'new');
          assert.deepStrictEqual(Array.from(mapped.missing), []);

          // A fully confirmed import commits exactly once.
          const good = contextFor(open(goodProject));
          good.installSuccessfulB(sourceLayers());
          good.sandbox.window.recompositeFromLayers = () => true;
          good.sandbox.window.renderLayerPanel = () => true;
          good.sandbox.window.selectPSDLayer = id => { good.state.selected = id; };
          assert.strictEqual(await good.sandbox.window.loadSpbProject('B.spbproj'), true);
          assert.strictEqual(good.configCalls(), 1);
          assert.strictEqual(good.sandbox._psdLayers.length, 1, 'v2 must keep deleted source Layers deleted');
          assert(good.toasts.some(value => value.includes(' restored — ')));

          // A late server fingerprint mismatch after B commits restores A.
          const changedStatus = { requestedPath: 'B.psd', exists: true, matchesSavedFingerprint: false };
          const fingerprint = contextFor(open(goodProject), { ok: true, sourceStatus: changedStatus });
          const fingerprintBefore = fingerprint.digest();
          fingerprint.installSuccessfulB(sourceLayers());
          assert.strictEqual(await fingerprint.sandbox.window.loadSpbProject('B.spbproj'), false);
          assertRestoredA(fingerprint, fingerprintBefore);

          // An unresolved saved Layer after B commits restores A.
          const missingProject = {
            ...baseProject,
            layers: [{ id: 'gone', path: 'Missing/Layer', name: 'Gone' }],
          };
          const missing = contextFor(open(missingProject));
          const missingBefore = missing.digest();
          missing.installSuccessfulB(sourceLayers());
          assert.strictEqual(await missing.sandbox.window.loadSpbProject('B.spbproj'), false);
          assertRestoredA(missing, missingBefore);

          // Explicit Project restore and subsequent capture preserve independent element topology.
          const linked = contextFor(open(goodProject));
          linked.installSuccessfulB(sourceLayers());
          linked.sandbox.window.recompositeFromLayers = () => true;
          linked.sandbox.window.renderLayerPanel = () => true;
          assert.strictEqual(await linked.sandbox.window.loadSpbProject('B.spbproj'), true);
          const linkedLayer = linked.sandbox._psdLayers.find(layer => layer.id === 'psd_0');
          assert.deepStrictEqual(copy(linkedLayer.elementInstances), record.elementInstances);
          assert.deepStrictEqual(copy(linkedLayer.elementLinkGroups), record.elementLinkGroups);
          linkedLayer.img = {toDataURL() {return __PNG__;}};
          const recaptured = linked.sandbox.window.SPBProjects.buildProjectPayload('Linked');
          const linkedRecord = recaptured.layers.find(layer => layer.id === 'psd_0');
          assert.deepStrictEqual(copy(linkedRecord.elementInstances), record.elementInstances);
          linkedLayer.elementInstances[0].instanceBbox.x1 = 99;
          assert.strictEqual(linkedRecord.elementInstances[0].instanceBbox.x1, 50, 'saved link metadata must be immutable');

          // A config exception after Layer mutation restores A, not source B.
          const configFault = contextFor(open(goodProject));
          const configBefore = configFault.digest();
          configFault.installSuccessfulB(sourceLayers());
          configFault.sandbox.window.recompositeFromLayers = () => true;
          configFault.sandbox.window.renderLayerPanel = () => true;
          configFault.failProjectConfig();
          assert.strictEqual(await configFault.sandbox.window.loadSpbProject('B.spbproj'), false);
          assertRestoredA(configFault, configBefore);
        })().catch(error => { console.error(error); process.exit(1); });
        """
    ).replace("__PROJECT_JS__", json.dumps(str(PROJECT_JS))).replace(
        "__PNG__", json.dumps(ONE_PIXEL_PNG)
    )
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
