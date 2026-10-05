from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from engine.paint_v2 import user_imports_ingest as ingest


def _png(color=(80, 140, 220, 255)) -> bytes:
    output = BytesIO()
    Image.new("RGBA", (16, 16), color).save(output, "PNG")
    return output.getvalue()


def _pack(path: Path, *, extra: dict[str, bytes] | None = None, bad_spec: bool = False) -> Path:
    finish_id = "ui_community_fixture"
    manifest = {
        "schema_version": 1,
        "category": "SHOKK DROP",
        "entries": [{"id": finish_id, "name": "Community Fixture", "kind": "paint_monolithic"}],
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr(f"{finish_id}.png", _png())
        archive.writestr(f"{finish_id}_spec.png", b"not-png" if bad_spec else _png((120, 90, 200, 255)))
        archive.writestr("preview.png", _png((180, 60, 90, 255)))
        for name, data in (extra or {}).items():
            archive.writestr(name, data)
    return path


def test_community_pack_validation_accepts_export_shape(tmp_path):
    result = ingest.validate_community_drop_pack(_pack(tmp_path / "valid.spbdrop"))

    assert result["finish_id"] == "ui_community_fixture"
    assert result["members"] == 4
    assert len(result["verified_images"]) == 3


@pytest.mark.parametrize(
    "extra",
    [
        {"../escape.png": b"x"},
        {"payload.exe": b"MZ"},
        {"nested/paint.png": b"x"},
    ],
)
def test_community_pack_validation_rejects_unsafe_members(tmp_path, extra):
    with pytest.raises(ValueError):
        ingest.validate_community_drop_pack(_pack(tmp_path / "unsafe.spbdrop", extra=extra))


def test_community_pack_validation_rejects_fake_png(tmp_path):
    with pytest.raises(ValueError, match="invalid PNG"):
        ingest.validate_community_drop_pack(_pack(tmp_path / "fake.spbdrop", bad_spec=True))


def test_community_install_is_idempotent_by_public_id_and_version(tmp_path, monkeypatch):
    library = tmp_path / "library"
    monkeypatch.setattr(ingest, "user_imports_root", lambda: library)
    pack = _pack(tmp_path / "valid.spbdrop")
    source = {
        "id": "drp_0123456789abcdef0123456789abcdef",
        "version": 1,
        "sha256": "a" * 64,
        "finish_name": "Published Finish",
        "author_name": "Fixture Artist",
        "website": "https://example.com",
    }

    first = ingest.import_pack_zip(pack, community_source=source)
    second = ingest.import_pack_zip(pack, community_source=source)
    saved = json.loads((library / "manifest.json").read_text(encoding="utf-8"))

    assert first[0]["id"] == second[0]["id"]
    assert first[0]["name"] == "Published Finish"
    assert first[0]["author"] == "Fixture Artist"
    assert len(saved["entries"]) == 1

