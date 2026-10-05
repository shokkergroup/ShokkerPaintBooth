"""Smoke-test lightweight Flask routes extracted from server.py.

This is intentionally narrow for SPB-105: it checks route wiring and response
shape for already-extracted endpoints without running render/export workflows.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _expect(name, response, expected_status):
    status = response.status_code
    payload = response.get_json(silent=True)
    if status != expected_status:
        raise AssertionError(f"{name}: expected {expected_status}, got {status}: {payload!r}")
    print(f"{name}: {status} {json.dumps(payload, sort_keys=True)[:300]}")
    return payload


def main() -> int:
    import server

    client = server.app.test_client()

    favicon = client.get("/favicon.ico")
    if favicon.status_code != 204:
        raise AssertionError(f"favicon expected 204, got {favicon.status_code}")
    print(f"favicon: {favicon.status_code}")

    static_js = client.get("/paint-booth-1-data.js")
    if static_js.status_code != 200:
        raise AssertionError(f"static JS expected 200, got {static_js.status_code}")
    cache_control = static_js.headers.get("Cache-Control", "")
    if "no-store" not in cache_control:
        raise AssertionError(f"static JS missing no-store cache header: {cache_control!r}")
    print(f"static JS: {static_js.status_code}")

    missing_thumb = client.get("/thumbnails/__missing__.png")
    if missing_thumb.status_code != 404:
        raise AssertionError(f"missing thumbnail expected 404, got {missing_thumb.status_code}")
    print(f"missing thumbnail: {missing_thumb.status_code}")

    first_base = next(iter(server.engine.BASE_REGISTRY))
    finish_lookup = _expect("finish-by-id valid", client.get(f"/api/finish-by-id/{first_base}"), 200)
    if finish_lookup.get("id") != first_base or finish_lookup.get("kind") != "base":
        raise AssertionError(f"finish-by-id valid mismatch: {finish_lookup!r}")

    missing_finish = client.get("/api/finish-by-id/__missing_finish__")
    if missing_finish.status_code != 404:
        raise AssertionError(f"finish-by-id missing expected 404, got {missing_finish.status_code}")
    print(f"finish-by-id missing: {missing_finish.status_code}")

    finish_groups = _expect("finish-groups GET", client.get("/finish-groups"), 200)
    if finish_groups.get("status") != "ok" or "groups" not in finish_groups:
        raise AssertionError(f"finish-groups response shape mismatch: {finish_groups!r}")

    registry_status = _expect("finish-registry-status GET", client.get("/api/finish-registry-status"), 200)
    if not registry_status.get("count") or "registered" not in registry_status:
        raise AssertionError(f"finish-registry-status shape mismatch: {registry_status!r}")

    finish_data_bases = _expect("finish-data bases GET", client.get("/api/finish-data?type=bases"), 200)
    if finish_data_bases.get("status") != "ok" or finish_data_bases.get("count", 0) <= 0:
        raise AssertionError(f"finish-data bases response shape mismatch: {finish_data_bases!r}")

    license_payload = _expect("license GET", client.get("/license"), 200)
    if "active" not in license_payload or "key_masked" not in license_payload:
        raise AssertionError("license GET missing active/key_masked")

    bad_license = client.post("/license", json={"key": "BAD"})
    if bad_license.status_code != 400:
        raise AssertionError(f"bad license POST expected 400, got {bad_license.status_code}")
    print(f"license bad POST: {bad_license.status_code}")

    assets = _expect("default-assets GET", client.get("/api/default-assets"), 200)
    if not assets.get("ok") or "assets" not in assets:
        raise AssertionError("default-assets response missing ok/assets")

    blank = _expect(
        "blank-canvas GET",
        client.get("/api/blank-canvas?width=64&height=64&color=112233&mode=json"),
        200,
    )
    if blank.get("width") != 64 or blank.get("height") != 64 or blank.get("color") != "112233":
        raise AssertionError(f"blank-canvas response shape mismatch: {blank!r}")

    exchange_root = _expect("photoshop exchange root", client.get("/api/photoshop-exchange-root"), 200)
    if not exchange_root.get("path"):
        raise AssertionError("photoshop exchange root missing path")

    with tempfile.TemporaryDirectory() as tmp:
        ps_list = _expect("photoshop import list", client.get(f"/api/photoshop-import-list?exchange_folder={tmp}"), 200)
        if ps_list != {"files": [], "subfolders": []}:
            raise AssertionError(f"unexpected empty photoshop list: {ps_list!r}")

        missing_file = client.get(f"/api/photoshop-import-file?exchange_folder={tmp}&path=missing.tga")
        if missing_file.status_code != 404:
            raise AssertionError(f"missing photoshop import file expected 404, got {missing_file.status_code}")
        print(f"photoshop missing file: {missing_file.status_code}")

        no_last_spec = client.post("/api/photoshop-import-spec-from-last-export", json={"exchange_folder": tmp})
        if no_last_spec.status_code != 404:
            raise AssertionError(f"photoshop last spec expected 404, got {no_last_spec.status_code}")
        print(f"photoshop no-last-spec: {no_last_spec.status_code}")

    save_missing_dir = client.post("/save-render-to-keep", json={})
    if save_missing_dir.status_code != 400:
        raise AssertionError(f"save-render-to-keep empty body expected 400, got {save_missing_dir.status_code}")
    print(f"save-render-to-keep empty body: {save_missing_dir.status_code}")

    preview_missing = client.get("/preview/missing-job/missing.png")
    if preview_missing.status_code != 404:
        raise AssertionError(f"missing preview expected 404, got {preview_missing.status_code}")
    print(f"missing preview: {preview_missing.status_code}")

    download_missing = client.get("/download/missing-job/missing.tga")
    if download_missing.status_code != 404:
        raise AssertionError(f"missing download expected 404, got {download_missing.status_code}")
    print(f"missing download: {download_missing.status_code}")

    reset_missing_file = client.post("/reset-backup", json={})
    if reset_missing_file.status_code != 400:
        raise AssertionError(f"reset-backup empty body expected 400, got {reset_missing_file.status_code}")
    print(f"reset-backup empty body: {reset_missing_file.status_code}")

    tga_missing = client.post("/preview-tga", json={"path": "__missing__.tga"})
    if tga_missing.status_code != 404:
        raise AssertionError(f"preview-tga missing file expected 404, got {tga_missing.status_code}")
    print(f"preview-tga missing file: {tga_missing.status_code}")

    check_empty = client.post("/check-file", json={})
    if check_empty.status_code != 400:
        raise AssertionError(f"check-file empty body expected 400, got {check_empty.status_code}")
    print(f"check-file empty body: {check_empty.status_code}")

    check_self = _expect("check-file self", client.post("/check-file", json={"path": str(ROOT / "server.py")}), 200)
    if not check_self.get("exists") or not check_self.get("is_file"):
        raise AssertionError(f"check-file self mismatch: {check_self!r}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "sample.tga").write_bytes(b"not-a-real-tga")
        (tmp_path / "notes.txt").write_text("skip", encoding="utf-8")
        browse = _expect("browse-files tga filter", client.post("/browse-files", json={"path": tmp, "filter": ".tga"}), 200)
        names = [item["name"] for item in browse.get("items", [])]
        if names != ["sample.tga"]:
            raise AssertionError(f"browse-files filter mismatch: {names!r}")

        upload_bad = client.post("/upload-composited-paint", json={})
        if upload_bad.status_code != 400:
            raise AssertionError(f"upload-composited-paint empty body expected 400, got {upload_bad.status_code}")
        print(f"upload-composited-paint empty body: {upload_bad.status_code}")

        upload_missing = client.post("/api/upload-paint-file", data={})
        if upload_missing.status_code != 400:
            raise AssertionError(f"upload-paint-file empty body expected 400, got {upload_missing.status_code}")
        print(f"upload-paint-file empty body: {upload_missing.status_code}")

        decal_missing = client.post("/api/upload-tga-decal", data={})
        if decal_missing.status_code != 400:
            raise AssertionError(f"upload-tga-decal empty body expected 400, got {decal_missing.status_code}")
        print(f"upload-tga-decal empty body: {decal_missing.status_code}")

        local_missing = client.post("/api/serve-local-file", json={})
        if local_missing.status_code != 400:
            raise AssertionError(f"serve-local-file empty body expected 400, got {local_missing.status_code}")
        print(f"serve-local-file empty body: {local_missing.status_code}")

        local_ok = _expect("serve-local-file existing", client.post("/api/serve-local-file", json={"path": str(tmp_path / "sample.tga")}), 200)
        if not local_ok.get("url"):
            raise AssertionError(f"serve-local-file existing missing url: {local_ok!r}")

        non_image_path = urllib.parse.quote(str(tmp_path / "notes.txt"), safe="")
        non_image_download = client.get(f"/api/serve-local-file/download?p={non_image_path}")
        if non_image_download.status_code != 400:
            raise AssertionError(f"serve-local-file non-image expected 400, got {non_image_download.status_code}")
        print(f"serve-local-file non-image: {non_image_download.status_code}")

    iracing_cars = _expect("iracing-cars GET", client.get("/iracing-cars"), 200)
    if "cars" not in iracing_cars:
        raise AssertionError(f"iracing-cars response missing cars: {iracing_cars!r}")

    original_output = server.OUTPUT_FOLDER
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        job_dir = tmp_path / "job_cleanup_smoke"
        job_dir.mkdir()
        (job_dir / "old.tga").write_bytes(b"cleanup-smoke")
        (tmp_path / "not_a_job").mkdir()
        try:
            server.OUTPUT_FOLDER = tmp
            cleanup = _expect("cleanup temp job", client.post("/cleanup", json={"max_age_hours": 0}), 200)
        finally:
            server.OUTPUT_FOLDER = original_output
        if cleanup.get("deleted") != 1 or job_dir.exists():
            raise AssertionError(f"cleanup temp job mismatch: {cleanup!r}")

    validate_missing = client.post("/api/validate-paint-file", json={"path": "__missing__.tga"})
    if validate_missing.status_code != 404:
        raise AssertionError(f"validate-paint-file missing expected 404, got {validate_missing.status_code}")
    print(f"validate-paint-file missing: {validate_missing.status_code}")

    with tempfile.TemporaryDirectory() as tmp:
        from PIL import Image

        img_path = Path(tmp) / "coverage.png"
        Image.new("RGB", (4, 4), (255, 0, 0)).save(img_path)
        valid = _expect(
            "validate-paint-file valid image",
            client.post("/api/validate-paint-file", json={"path": str(img_path), "expect_size": [4, 4]}),
            200,
        )
        if not valid.get("valid") or valid.get("dimensions") != [4, 4]:
            raise AssertionError(f"validate-paint-file valid mismatch: {valid!r}")

        coverage = _expect(
            "zone-coverage-estimate red",
            client.post("/api/zone-coverage-estimate", json={
                "paint_file": str(img_path),
                "zones": [{"name": "Red", "color": "red"}],
            }),
            200,
        )
        if coverage.get("coverage", [{}])[0].get("pct") != 100.0:
            raise AssertionError(f"zone coverage mismatch: {coverage!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
