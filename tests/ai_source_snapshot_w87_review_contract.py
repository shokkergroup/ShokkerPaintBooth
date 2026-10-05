from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path.cwd()
REVIEW = ROOT / "_easy_claude_work/ai14h_w83_review"
CANDIDATE = REVIEW / "candidate"
ORACLE = ROOT / "_easy_claude_work/ai14h_w87_review/fresh-oracle.json"
EXPECTED_ORACLE = "e2328825b6864dbb86fa2e8b7fa27196835116fff3ad57ca33799a99bd75c025"
EXPECTED_SERVER = "a845f7ee1cd96b9f87fe1af85d42a1b86dd2059e2a5893e47006a08d773ac2ce"
EXPECTED_ROUTES = "6a0fce336fc5ef54eb80ef92a220abc0d81e5b22107b2bf3a4e3b0872f51a95d"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_w83_contract():
    spec = importlib.util.spec_from_file_location("w83_contract_for_w87", ROOT / "tests/ai_source_bytes_transient_aba_w83_contract.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def decode_png(data_uri: str) -> list[int]:
    payload = base64.b64decode(data_uri.split(",", 1)[1])
    return list(Image.open(io.BytesIO(payload)).convert("RGB").getpixel((1, 1)))


def main() -> None:
    assert sha(ORACLE) == EXPECTED_ORACLE, "W87 fresh oracle changed"
    assert sha(CANDIDATE / "server.py") == EXPECTED_SERVER, "W83 candidate server changed"
    assert sha(CANDIDATE / "server_routes/psd_import_routes.py") == EXPECTED_ROUTES, "W83 candidate route changed"
    w83 = load_w83_contract()
    rows = []

    with tempfile.TemporaryDirectory(prefix="spb-w87-route-") as td:
        root = Path(td)
        source = root / "route.psd"
        w83.make_psd(source, (1, 1, 1), (30, 160, 220), size=(8, 8))
        cache = {}
        client, loader, invalidations = w83.make_app(cache)
        headers = {"X-Shokker-Internal": "1"}

        imported = client.post("/api/psd-import", json={"psd_path": str(source), "thumbnail_size": 16}, headers=headers)
        assert imported.status_code == 200, imported.get_data(as_text=True)
        imported_body = imported.get_json()
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert imported_body["sourceBytesSha256"] == digest

        raster = client.post("/api/psd-rasterize-all", json={"psd_path": str(source), "sourceBytesSha256": digest}, headers=headers)
        assert raster.status_code == 200, raster.get_data(as_text=True)
        raster_body = raster.get_json()
        assert raster_body["sourceBytesSha256"] == digest
        assert raster_body["success"] is True
        assert raster_body["layers"], "the real raster route should return the PSD pixel layer"
        first_layer = next(iter(raster_body["layers"].values()))
        assert decode_png(first_layer["image"]) == [30, 160, 220]
        parsed = cache[str(source.resolve())][2]
        assert parsed is loader(str(source.resolve()), source_fingerprint=digest)
        rows.append({"id": "actual_import_then_digest_bound_raster_route", "importStatus": imported.status_code, "rasterStatus": raster.status_code, "digestBound": True, "pixel": decode_png(first_layer["image"]), "cacheObjectIsParsedPSD": True, "parserCacheEntries": len(cache)})

        # A raster request carrying the old receipt cannot accidentally use a
        # same-path parser cache after the selected bytes have changed.
        replacement = root / "replacement.psd"
        w83.make_psd(replacement, (2, 2, 2), (220, 70, 15), size=(8, 8))
        new_bytes = replacement.read_bytes()
        source.write_bytes(new_bytes)
        mismatch = client.post("/api/psd-rasterize-all", json={"psd_path": str(source), "sourceBytesSha256": digest}, headers=headers)
        assert mismatch.status_code == 409, mismatch.get_data(as_text=True)
        rows.append({"id": "raster_old_digest_rejected_after_path_replacement", "status": mismatch.status_code, "verdict": "PASS"})

        # Parse failure must close the temporary byte snapshot, while the route
        # returns failure rather than a success-shaped response.
        import psd_tools
        original_open = psd_tools.PSDImage.open
        spools = []
        original_factory = tempfile.SpooledTemporaryFile

        def tracked_factory(*args, **kwargs):
            spool = original_factory(*args, **kwargs)
            spools.append(spool)
            return spool

        def fail_open(_source, *args, **kwargs):
            raise ValueError("W87 controlled parser failure")

        tempfile.SpooledTemporaryFile = tracked_factory
        psd_tools.PSDImage.open = fail_open
        try:
            broken_cache = {}
            failed_client, _failed_loader, _failed_invalidations = w83.make_app(broken_cache)
            failed = failed_client.post("/api/psd-import", json={"psd_path": str(source), "thumbnail_size": 16}, headers=headers)
            assert failed.status_code == 500, failed.get_data(as_text=True)
            assert spools and all(s.closed for s in spools), "snapshot spool leaked after parser failure"
            assert not broken_cache, "failed parser must not be cached"
            rows.append({"id": "parse_failure_closes_snapshot_and_is_not_success", "status": failed.status_code, "spoolsClosed": len(spools), "cacheEntries": len(broken_cache), "verdict": "PASS"})
        finally:
            psd_tools.PSDImage.open = original_open
            tempfile.SpooledTemporaryFile = original_factory

    print(json.dumps({
        "status": "PASS_WITH_LIMITS",
        "freshOracleCases": 8,
        "freshRouteTrials": len(rows),
        "rows": rows,
        "producerActualRows": 6,
        "producerFrozenOracleDenominator": 8,
        "sourcePins": {"server": EXPECTED_SERVER, "routes": EXPECTED_ROUTES},
        "providerCalls": 0,
        "nativeCalls": 0,
        "limits": [
            "The unchanged W83 producer contract was run separately and reports 6 actual rows against its frozen 8-case oracle; do not treat the denominator as 8 passing executions.",
            "W87 adds actual Flask import→digest-bound raster-route and controlled parser-failure cleanup trials. The cleanup failure is fault injection, not a natural parser failure rate claim.",
            "ORA is exercised as a real legacy OpenRaster fixture by the producer test; XCF is verified only by its retained path-loader dispatch because no real XCF dependency/fixture is installed.",
            "All source files are temporary fixtures and candidate code is loaded/extracted privately; no live backend, filesystem source, renderer, native app, browser or provider is used."
        ]
    }, indent=2))


if __name__ == "__main__":
    main()
