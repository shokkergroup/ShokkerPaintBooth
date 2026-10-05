from __future__ import annotations

import ast
import base64
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import zipfile
import gc
import weakref
from pathlib import Path

from flask import Flask
from PIL import Image
from psd_tools import PSDImage

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "electron-app/server"))
REVIEW = ROOT / "_easy_claude_work/ai14h_w83_review"
CANDIDATE = REVIEW / "candidate"
FROZEN = REVIEW / "frozen_w78"
SERVER = CANDIDATE / "server.py"
ROUTES = CANDIDATE / "server_routes/psd_import_routes.py"
EXPECTED = {
    "server": "a845f7ee1cd96b9f87fe1af85d42a1b86dd2059e2a5893e47006a08d773ac2ce",
    "routes": "6a0fce336fc5ef54eb80ef92a220abc0d81e5b22107b2bf3a4e3b0872f51a95d",
    "ora": "189b2943e584c960ae984b45e4318e675e20bb840710d814bf25a66fd0eacf4e",
    "xcf": "5a6b2b01be492611b153badd71b44bc47307031e34023e2093c14f95b168c3fe",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def extract_function(path: Path, name: str, globals_dict: dict):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), globals_dict)
    return globals_dict[name]


def make_psd(path: Path, hidden_rgb, visible_rgb, size=(12, 12)) -> bytes:
    psd = PSDImage.new("RGB", size, (0, 0, 0))
    psd.append(psd.create_pixel_layer(Image.new("RGBA", size, (*visible_rgb, 255)), name="Paint"))
    hidden = psd.create_pixel_layer(Image.new("RGBA", size, (*hidden_rgb, 255)), name="Hidden Secret")
    hidden.visible = False
    psd.append(hidden)
    psd.save(path)
    return path.read_bytes()


def set_mtime(path: Path, ns: int) -> None:
    os.utime(path, ns=(ns, ns))


def pixel(payload: dict) -> list[int]:
    raw = base64.b64decode(payload["composite"].split(",", 1)[1])
    return list(Image.open(io.BytesIO(raw)).convert("RGB").getpixel((3, 3)))


def make_app(cache, open_override=None):
    project = ast.parse((FROZEN / "project_routes.py").read_text(encoding="utf-8"))
    node = next(n for n in project.body if isinstance(n, ast.FunctionDef) and n.name == "_source_fingerprint")
    fp_globals = {"os": os, "hashlib": hashlib}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(FROZEN / "project_routes.py"), "exec"), fp_globals)
    loader_globals = {"os": os, "_psd_cache": cache}
    if open_override is not None:
        loader_globals["open"] = open_override
    get_cached = extract_function(SERVER, "_get_cached_psd", loader_globals)
    route_spec = importlib.util.spec_from_file_location("w83_psd_import_routes", ROUTES)
    route = importlib.util.module_from_spec(route_spec)
    route_spec.loader.exec_module(route)
    route._source_fingerprint = fp_globals["_source_fingerprint"]

    class Log:
        def info(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

    invalidations = []

    def invalidate(path):
        invalidations.append(path)
        return cache.pop(path, None)

    app = Flask("w83-private-route")
    route.register_psd_import_routes(
        app,
        require_internal_request=lambda: (True, None),
        sanitize_path=lambda p: (str(Path(p).resolve()), None),
        get_cached_psd=get_cached,
        logger=Log(),
        invalidate_cached_psd=invalidate,
    )
    return app.test_client(), get_cached, invalidations


def main() -> None:
    assert sha(SERVER) == EXPECTED["server"], "private W83 candidate server changed after test freeze"
    assert sha(ROUTES) == EXPECTED["routes"], "private W83 candidate route changed after test freeze"
    assert sha(ROOT / "electron-app/server/server_routes/ora_import.py") == EXPECTED["ora"], "ORA loader changed during compatibility check"
    assert sha(ROOT / "electron-app/server/server_routes/xcf_import.py") == EXPECTED["xcf"], "XCF loader changed during compatibility check"
    frozen_server_hash = sha(FROZEN / "server.py")
    frozen_route_hash = sha(FROZEN / "psd_import_routes.py")
    assert frozen_server_hash == "1b094f80d81582416b03b0c63f1814665fb78969f2bb1675e5219e710c522294"
    assert frozen_route_hash == "faf99df7eddeed1623342efda2479bbd23fb1d763b5f7759df8068f63ee0d902"

    rows = []
    with tempfile.TemporaryDirectory(prefix="spb-w83-contract-") as td:
        root = Path(td)
        src = root / "paint.psd"
        other = root / "other.psd"
        a = make_psd(src, (1, 2, 3), (200, 10, 20))
        b = make_psd(other, (4, 5, 6), (15, 180, 90))
        fixed_mtime = 1700000000000000000
        set_mtime(src, fixed_mtime)

        # The route fingerprints A. During the parser's first source open, make
        # the open file descriptor observe B and restore path A before reads
        # finish. The immutable-snapshot loader must reject B's digest and retry
        # from A, so the successful payload remains A/A.
        raced = {"done": False}

        def racing_open(file, mode="r", *args, **kwargs):
            if not raced["done"] and Path(file).resolve() == src.resolve() and mode == "rb":
                raced["done"] = True
                src.write_bytes(b)
                set_mtime(src, fixed_mtime)
                handle = open(file, mode, *args, **kwargs)
                src.write_bytes(a)
                set_mtime(src, fixed_mtime)
                return handle
            return open(file, mode, *args, **kwargs)

        cache = {}
        client, get_cached, invalidations = make_app(cache, racing_open)
        reply = client.post("/api/psd-import", json={"psd_path": str(src), "thumbnail_size": 32}, headers={"X-Shokker-Internal": "1"})
        body = reply.get_json()
        assert raced["done"] is True
        assert reply.status_code == 200, body
        assert body["sourceBytesSha256"] == hashlib.sha256(a).hexdigest()
        assert pixel(body) == [200, 10, 20], pixel(body)
        assert len(cache) == 1
        snapshot = next(iter(cache.values()))[3]
        assert getattr(snapshot, "_rolled", False) is False, "small PSD should remain in memory spool"
        rows.append({"id": "transient_A_B_A_same_mtime", "status": reply.status_code, "pixel": pixel(body), "digest": body["sourceBytesSha256"], "verdict": "PASS"})

        # Cache-backed request from the same digest returns the exact parsed A.
        second = client.post("/api/psd-import", json={"psd_path": str(src), "thumbnail_size": 32}, headers={"X-Shokker-Internal": "1"})
        assert second.status_code == 200 and pixel(second.get_json()) == [200, 10, 20]
        rows.append({"id": "stable_cache_hit", "status": second.status_code, "pixel": pixel(second.get_json()), "verdict": "PASS"})

        # Equal visible output does not collapse distinct source files: the
        # hidden layer changes the byte receipt while visible composite stays.
        hidden_variant = root / "hidden-variant.psd"
        hidden_bytes = make_psd(hidden_variant, (222, 1, 88), (200, 10, 20))
        hidden_reply = client.post("/api/psd-import", json={"psd_path": str(hidden_variant), "thumbnail_size": 32}, headers={"X-Shokker-Internal": "1"})
        assert hidden_reply.status_code == 200
        assert pixel(hidden_reply.get_json()) == [200, 10, 20]
        assert hidden_reply.get_json()["sourceBytesSha256"] == hashlib.sha256(hidden_bytes).hexdigest()
        assert hidden_reply.get_json()["sourceBytesSha256"] != body["sourceBytesSha256"]
        rows.append({"id": "hidden_layer_bytes_in_digest", "pixel": pixel(hidden_reply.get_json()), "digestDiffers": True, "verdict": "PASS"})

        # A path that remains B cannot be represented under the expected A
        # receipt; the parser snapshot must reject it and the route return 409.
        src.write_bytes(a)
        set_mtime(src, fixed_mtime)
        permanent = {"done": False}

        def permanent_b_open(file, mode="r", *args, **kwargs):
            if not permanent["done"] and Path(file).resolve() == src.resolve() and mode == "rb":
                permanent["done"] = True
                src.write_bytes(b)
                set_mtime(src, fixed_mtime)
            return open(file, mode, *args, **kwargs)

        cache2 = {}
        client2, _get2, invalidations2 = make_app(cache2, permanent_b_open)
        reply2 = client2.post("/api/psd-import", json={"psd_path": str(src), "thumbnail_size": 32}, headers={"X-Shokker-Internal": "1"})
        assert reply2.status_code == 409, reply2.get_data(as_text=True)
        assert not cache2, "mismatched parser bytes must not enter cache"
        assert len(invalidations2) == 1
        rows.append({"id": "changed_B_post_hash", "status": reply2.status_code, "cacheEntries": len(cache2), "verdict": "PASS"})

        # The old no-digest call still accepts a path and memoizes its result.
        legacy_cache = {}
        legacy_client, legacy_loader, _ = make_app(legacy_cache)
        legacy_first = legacy_loader(str(src))
        legacy_second = legacy_loader(str(src))
        assert legacy_first is legacy_second
        mixed_cache = {}
        _mixed_client, mixed_loader, _mixed_invalidations = make_app(mixed_cache)
        digest_obj = mixed_loader(str(src), source_fingerprint=sha(src))
        legacy_obj = mixed_loader(str(src))
        assert legacy_obj is digest_obj, "legacy lookup of a digest-snapshotted cache entry must return the parser object"

        # Legacy OpenRaster is still dispatched through its path-based parser;
        # XCF retains its path-required loader branch as well.
        ora_path = root / "legacy.ora"
        layer_png = io.BytesIO()
        Image.new("RGBA", (4, 4), (9, 80, 170, 255)).save(layer_png, format="PNG")
        with zipfile.ZipFile(ora_path, "w") as zf:
            zf.writestr("stack.xml", '<image version="0.0.1" w="4" h="4"><stack><layer name="Paint" src="data/layer.png"/></stack></image>')
            zf.writestr("data/layer.png", layer_png.getvalue())
            zf.writestr("mergedimage.png", layer_png.getvalue())
        ora = legacy_loader(str(ora_path))
        assert ora.width == 4 and ora.height == 4
        assert list(ora.composite().convert("RGB").getpixel((1, 1))) == [9, 80, 170]
        server_text = SERVER.read_text(encoding="utf-8")
        frozen_text = (FROZEN / "server.py").read_text(encoding="utf-8")
        assert "elif psd_path.lower().endswith('.xcf')" in server_text
        assert "XcfImage.open(psd_path)" in server_text
        assert "elif psd_path.lower().endswith('.xcf')" in frozen_text
        rows.append({"id": "cache_hit_and_legacy_no_digest_and_ORA_XCF_dispatch", "legacyObjectReused": True, "digestCacheReturnedParserToLegacyCaller": True, "oraCompositePixel": [9, 80, 170], "xcfPathDispatchRetained": True, "verdict": "PASS"})

        # A noisy real PSD larger than the in-memory threshold must roll to a
        # disk-backed spool. Cache removal must not close the snapshot while a
        # caller still owns the parsed document; dropping the last document
        # reference then releases it.
        large_path = root / "large.psd"
        large_size = (1800, 1800)
        large_image = Image.frombytes("RGB", large_size, os.urandom(large_size[0] * large_size[1] * 3)).convert("RGBA")
        large_psd = PSDImage.new("RGB", large_size, (0, 0, 0))
        large_psd.append(large_psd.create_pixel_layer(large_image, name="Large noise"))
        large_psd.save(large_path)
        assert large_path.stat().st_size > 8 * 1024 * 1024, f"fixture unexpectedly small: {large_path.stat().st_size}"
        large_cache = {}
        _large_client, large_loader, _large_invalidations = make_app(large_cache)
        parsed_large = large_loader(str(large_path), source_fingerprint=sha(large_path))
        large_snapshot = large_cache[str(large_path)][3]
        assert getattr(large_snapshot, "_rolled", False) is True
        snapshot_ref = weakref.ref(large_snapshot)
        del large_snapshot
        large_cache.pop(str(large_path))
        assert snapshot_ref() is not None and not snapshot_ref().closed, "active parsed document must retain its input snapshot"
        del parsed_large
        gc.collect()
        assert snapshot_ref() is None or snapshot_ref().closed, "snapshot should release after the parsed document is no longer referenced"
        rows.append({"id": "snapshot_spool_threshold_and_lifetime", "fileBytes": large_path.stat().st_size, "rolledToDisk": True, "releasedAfterParserOwner": True, "verdict": "PASS"})

    assert len(rows) == 6
    print(json.dumps({
        "status": "PASS_WITH_LIMITS",
        "candidateServerSha256": sha(SERVER),
        "candidateRoutesSha256": sha(ROUTES),
        "frozenInputServerSha256": frozen_server_hash,
        "frozenInputRoutesSha256": frozen_route_hash,
        "rows": rows,
        "limitations": [
            "Real psd-tools PSDs and Flask route handlers were exercised; no production server or filesystem paths were touched.",
            "A real noisy PSD larger than 8 MiB exercised disk rollover and the parser-held snapshot lifetime through cache eviction.",
            "ORA/XCF dispatch remains path-based for compatibility and does not receive the new immutable PSD snapshot guarantee. XCF requires a path; ORA uses lazy ZipFile(path) reads. Strong ABA attestation for those formats remains open.",
            "No browser, native app, provider, server restart or raw source transfer was used."
        ]
    }, indent=2))


if __name__ == "__main__":
    main()
