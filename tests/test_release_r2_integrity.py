import base64
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

import deploy_r2
from scripts import spb_release_r2_publish as publisher


def _sha512(data):
    return base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")


def _fixture(tmp_path):
    root = tmp_path
    art = root / "electron-app" / "dist" / "nsis-web"
    art.mkdir(parents=True, exist_ok=True)
    installer = art / "ShokkerPaintBoothV10-1.2.3-Web-Setup.exe"
    package = art / "shokker-paint-booth-v6-1.2.3-x64.nsis.7z"
    payhip = root / "ShokkerPaintBoothV10-1.2.3-Payhip.zip"
    installer.write_bytes(b"installer")
    package.write_bytes(b"payload")
    payhip.write_bytes(b"payhip")
    latest = art / "latest.yml"
    latest.write_text(
        "version: 1.2.3\nfiles:\n"
        f"  - url: {installer.name}\n    sha512: {_sha512(installer.read_bytes())}\n"
        f"path: {installer.name}\nsha512: {_sha512(installer.read_bytes())}\n"
        "packages:\n  x64:\n"
        f"    path: {package.name}\n    size: {package.stat().st_size}\n"
        f"    sha512: {_sha512(package.read_bytes())}\n    file: {package.name}\n",
        encoding="utf-8",
    )
    rows = []
    for role, file, channels in [
        ("updaterPackage", package, ["r2"]),
        ("webInstaller", installer, ["r2", "payhip"]),
        ("payhipBundle", payhip, ["payhip"]),
    ]:
        rows.append({"role": role, "path": file.relative_to(root).as_posix(), "bytes": file.stat().st_size,
                     "sha256": deploy_r2.hash_file(file), "channels": channels})
    evidence = {
        "schemaVersion": 2, "version": "1.2.3", "distributables": rows,
        "latestYml": {"path": latest.relative_to(root).as_posix(), "bytes": latest.stat().st_size,
                      "sha256": deploy_r2.hash_file(latest), "mappings": {
                          "filesUrl": "webInstaller", "path": "webInstaller",
                          "packagesX64Path": "updaterPackage", "packagesX64File": "updaterPackage"}},
    }
    evidence_path = root / "evidence.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    return root, art, evidence_path, installer


def test_local_contract_enumerates_and_hash_binds_every_distributable(tmp_path):
    root, art, evidence, _ = _fixture(tmp_path)
    version, records = deploy_r2.validate_release_contract(root, art, evidence)
    assert version == "1.2.3"
    assert set(records) == {"updaterPackage", "webInstaller", "payhipBundle", "latestYml"}


def test_same_size_substitution_is_rejected(tmp_path):
    root, art, evidence, installer = _fixture(tmp_path)
    installer.write_bytes(b"INSTALLER")
    with pytest.raises(ValueError, match="webInstaller SHA-256"):
        deploy_r2.validate_release_contract(root, art, evidence)


def test_prestage_omits_smoke_but_activation_requires_it(tmp_path):
    root, _art, evidence, _installer = _fixture(tmp_path)
    code = r"""
const fs = require('fs'), c = require('./scripts/spb_release_contract');
const root = process.argv[1], evidence = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const prestage = [], activate = [];
c.validateBuiltEvidence(root, evidence, '1.2.3', false, (m) => prestage.push(m));
c.validateBuiltEvidence(root, evidence, '1.2.3', true, (m) => activate.push(m));
if (prestage.length || !activate.some((m) => m.includes('packaged smoke'))) process.exit(1);
"""
    run = subprocess.run(["node", "-e", code, str(root), str(evidence)], cwd=Path.cwd(), capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr


@pytest.mark.parametrize("head", [
    {"ContentLength": 7, "Metadata": {}},
    {"ContentLength": 7, "Metadata": {"spb-sha256": "0" * 64}},
    {"ContentLength": 6, "Metadata": {"spb-sha256": "a" * 64}},
])
def test_remote_head_requires_exact_size_and_sha_metadata(head):
    record = {"path": Path("payload.7z"), "bytes": 7, "sha256": "a" * 64}
    with pytest.raises(ValueError):
        deploy_r2.validate_head(record, head)


def test_upload_attaches_and_rechecks_sha_metadata(tmp_path):
    file = tmp_path / "payload.7z"
    file.write_bytes(b"payload")
    record = {"role": "updaterPackage", "path": file, "bytes": 7,
              "sha256": deploy_r2.hash_file(file)}

    class FakeS3:
        extra = None

        def upload_file(self, _path, _bucket, _key, ExtraArgs, Config, Callback):
            self.extra = ExtraArgs
            Callback(7)

        def head_object(self, **_kwargs):
            return {"ContentLength": 7, "Metadata": self.extra["Metadata"]}

    fake = FakeS3()
    deploy_r2.upload_record(fake, "bucket", record, "1.2.3", object())
    assert fake.extra["Metadata"]["spb-sha256"] == record["sha256"]


def test_activation_checks_payload_and_installer_before_latest_upload(tmp_path, monkeypatch):
    records = {}
    for role, name, data in [("updaterPackage", "payload.7z", b"payload"),
                             ("webInstaller", "setup.exe", b"installer"),
                             ("payhipBundle", "payhip.zip", b"payhip"),
                             ("latestYml", "latest.yml", b"feed")]:
        file = tmp_path / name
        file.write_bytes(data)
        records[role] = {"role": role, "path": file, "bytes": len(data),
                         "sha256": deploy_r2.hash_file(file)}
    monkeypatch.setattr(publisher, "prepare", lambda _argv: (
        False, True, False, tmp_path, tmp_path / "evidence.json", "1.2.3", records))
    monkeypatch.setattr(deploy_r2, "TransferConfig", lambda **_kwargs: object())
    uploads = []
    monkeypatch.setattr(deploy_r2, "upload_record", lambda *_args: uploads.append(_args[2]["role"]))

    class FakeS3:
        def head_object(self, Bucket, Key):
            record = next(row for row in records.values() if row["path"].name == Key)
            metadata = {"spb-sha256": record["sha256"] if Key == "payload.7z" else "0" * 64}
            return {"ContentLength": record["bytes"], "Metadata": metadata}

    with pytest.raises(ValueError, match="webInstaller"):
        publisher.main(["dist", "--only-latest"], {"R2_BUCKET": "bucket"}, lambda _env: FakeS3())
    assert uploads == []


def test_check_mode_returns_before_credentials_or_client(tmp_path, monkeypatch):
    records = {}
    for role in ("updaterPackage", "webInstaller", "payhipBundle", "latestYml"):
        records[role] = {"role": role, "path": tmp_path / role, "bytes": 1, "sha256": "a" * 64}
    monkeypatch.setattr(publisher, "prepare", lambda _argv: (
        True, False, True, tmp_path, tmp_path / "evidence.json", "1.2.3", records))

    def forbidden_client(_env):
        raise AssertionError("check mode created an R2 client")

    assert publisher.main(["dist", "--hold-latest", "--check-release-contract"], {}, forbidden_client) == 0


def test_release_powershell_has_explicit_non_rebuild_boundaries():
    text = Path("spb_release.ps1").read_text(encoding="utf-8-sig")
    assert 'if ($Phase -eq "all")' in text and "-Phase all is retired" in text
    assert 'if ($Phase -eq "build") {' in text
    assert 'Invoke-ReleasePreflight "prestage"' in text
    assert text.count('Invoke-ReleasePreflight "activate"') >= 2
    assert 'Invoke-R2ReleasePhase "--hold-latest"' in text
    assert text.count('Invoke-R2ReleasePhase "--only-latest"') >= 2
    assert "public latest.yml never matched the exact local SHA-256" in text
    assert "Feed latest.yml has no parseable top-level version" in text
    assert re.search(r'Local build is .*?NOT yet live\."\) "Yellow"\s+exit 1', text, re.S)
    assert re.search(r'Could not read the feed: .*?"Red".*?exit 1', text, re.S)
