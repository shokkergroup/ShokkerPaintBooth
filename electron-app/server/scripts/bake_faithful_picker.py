"""Bake/check the SAME full-detail masters and cards that the picker reads.

After catalog edits: --export-registry, then node scripts/spb_picker_catalog.cjs.
Default: offline bake; unchanged identities skipped. --check fails on stale
source/registry exports or missing masters/cards.
Startup uses this exact baker, independent of Node or HTTP.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SHOKKER_SKIP_SPEC_PREBAKE', '1')
os.environ.setdefault('SHOKKER_SKIP_PICKER_PREBAKE', '1')
os.environ.setdefault('SPB_NO_LIVE_LINK', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
_SERVER = None


@contextlib.contextmanager
def baker_lock(path):
    """OS-owned lock: a crash releases it; startup cannot race another baker."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            lock.seek(0)
            if os.name == 'nt':
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def load_server():
    global _SERVER
    if _SERVER is None:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            # Match the live V5 bootstrap order. Importing server alone can
            # capture the modular registry before the final legacy merge.
            import server_v5
            import server
            server.engine._ensure_expansions_loaded()
            import cv2
            cv2.setNumThreads(1)
        _SERVER = server
    return _SERVER


def configure_worker():
    """Don't inherit a launcher's idle/single-core affinity for bulk baking."""
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.GetProcessAffinityMask.argtypes = [wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
        kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        kernel.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        process = kernel.GetCurrentProcess()
        current, available = ctypes.c_size_t(), ctypes.c_size_t()
        if kernel.GetProcessAffinityMask(process, ctypes.byref(current), ctypes.byref(available)):
            kernel.SetProcessAffinityMask(process, available.value)
        # Let interactive paint/browser work retain scheduling precedence.
        kernel.SetPriorityClass(process, 0x4000)  # BELOW_NORMAL_PRIORITY_CLASS


def identity_for(item):
    s = load_server()
    return [s._picker_finish_renderer_hash(item['type'], item['id']) or s._swatch_cache_token(),
            item['type'], item['id'], item['color'], 42]


def registry_data():
    """The exact payload merged by paint-booth-1-data.js, without HTTP."""
    load_server()
    import server_v5
    with server_v5.app.test_request_context('/api/finish-data'):
        return server_v5.api_finish_data().get_json()


def registry_digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def check_baked_route(s):
    """Build fuse: exercise the real Flask route with an empty isolated cache."""
    import tempfile
    import server_v5
    previous_dir, previous_render = s.THUMBNAIL_DIR, s._render_picker_split_snapshot_bytes
    calls = []
    def forbidden_render(*args):
        calls.append(args)
        raise AssertionError('Category request attempted on-demand rendering')
    with tempfile.TemporaryDirectory(prefix='.baked_gate_probe_',
                                     dir=ROOT / 'thumbnails/swatch_cache') as probe_dir:
        assert Path(probe_dir).resolve().is_relative_to(ROOT.resolve())
        try:
            s.THUMBNAIL_DIR = probe_dir
            s._render_picker_split_snapshot_bytes = forbidden_render
            with server_v5.app.test_client() as client:
                response = client.get('/api/swatch/base/acid_rain?color=abcdef&size=256&mode=split&source=faithful-v1&baked=1')
            if (response.status_code != 503 or calls or
                    b'Current picker bake missing' not in response.data or
                    response.headers.get('Cache-Control') != 'no-store'):
                raise RuntimeError('Baked-only route contract failed; refusing to package on-demand category loading')
        finally:
            s.THUMBNAIL_DIR, s._render_picker_split_snapshot_bytes = previous_dir, previous_render


def bake_pair_ready(paths, verify=False):
    from PIL import Image
    for path, dimensions in zip(paths, [(1024, 512), (512, 256)]):
        try:
            with Image.open(path) as image:
                if image.format != 'PNG' or image.size != dimensions:
                    return False
                if verify:
                    image.verify()
        except (OSError, ValueError):
            return False
    return True


def bake_one(item):
    s = load_server()
    from server_routes.faithful_swatch import faithful_split_bytes
    try:
        # Owner 2026-10-02 explicitly requests persistent thumbnails for the
        # CURRENT picker. Cache its already-exposed runtime output, without
        # publishing curated/static release snapshots or changing any verdict.
        # A release-review lock belongs to promotion, not disposable cache I/O.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            faithful_split_bytes(cache_dir=Path(s.THUMBNAIL_DIR) / 'swatch_cache',
                identity=identity_for(item), size=256,
                render=lambda size: s._render_picker_split_snapshot_bytes(
                    item['type'], item['id'], item['color'], size, 42))
        return item['type'] + ':' + item['id'], None
    except Exception as error:
        return item['type'] + ':' + item['id'], str(error)


def main():
    configure_worker()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', action='append', default=[])
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--export-registry', action='store_true')
    args = parser.parse_args()
    if args.export_registry:
        from engine.atomic_io import atomic_write_json
        data = registry_data()
        atomic_write_json(ROOT / 'thumbnails/faithful_picker_registry.json', data)
        print(f'Picker registry exported: {registry_digest(data)}', flush=True)
        return 0
    with (contextlib.nullcontext(True) if args.check else
          baker_lock(ROOT / 'thumbnails/swatch_cache/faithful_picker_baker.lock')) as acquired:
        if not acquired:
            print('Full-detail picker baker already running; keeping its disk repair.', flush=True)
            return 0
        return run(args)


def run(args):
    catalog = json.loads((ROOT / 'thumbnails/faithful_picker_catalog.json').read_text(encoding='utf8'))
    source = (ROOT / 'paint-booth-0-finish-data.js').read_bytes()
    if catalog['source_sha256'] != hashlib.sha256(source).hexdigest():
        raise SystemExit('Picker catalog is stale; run node scripts/spb_picker_catalog.cjs')
    s = load_server()
    for name, field in [('paint-booth-1-data.js', 'merge_source_sha256'),
                        ('js/spb-retired-catalog.js', 'retirement_source_sha256')]:
        if catalog.get(field) != hashlib.sha256((ROOT / name).read_bytes()).hexdigest():
            raise SystemExit(f'Picker catalog is stale ({name}); export registry and catalog again')
    if catalog.get('registry_sha256') != registry_digest(registry_data()):
        raise SystemExit('Picker registry changed; run baker --export-registry then the Node catalog exporter')
    if args.check:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            check_baked_route(s)
    from server_routes.faithful_swatch import faithful_paths
    items = [item for item in catalog['items'] if not args.prefix or
             any(item['id'].startswith(prefix) for prefix in args.prefix)]
    pending = []
    for item in items:
        paths = faithful_paths(Path(s.THUMBNAIL_DIR) / 'swatch_cache', identity_for(item))
        if not bake_pair_ready(paths, verify=args.check):
            pending.append(item)
    print(f'Faithful picker: {len(items)-len(pending)}/{len(items)} ready; {len(pending)} need baking.', flush=True)
    if args.check:
        for item in pending[:12]:
            print('Missing: ' + item['type'] + ':' + item['id'])
        return int(bool(pending))
    if not pending:
        return 0
    start = time.perf_counter()
    errors = []
    with ProcessPoolExecutor(max_workers=max(1, min(16, args.workers)), initializer=configure_worker) as pool:
        jobs = [pool.submit(bake_one, item) for item in pending]
        for index, job in enumerate(as_completed(jobs), 1):
            key, error = job.result()
            if error:
                errors.append({'key': key, 'error': error})
                print(f'FAIL {key}: {error[:200]}', flush=True)
            if index % 50 == 0 or index == len(jobs):
                print(f'{index}/{len(jobs)} baked; errors={len(errors)}; elapsed={time.perf_counter()-start:.0f}s', flush=True)
    from engine.atomic_io import atomic_write_json
    atomic_write_json(ROOT / 'thumbnails/faithful_picker_bake_report.json', {
        'schema': 'spb-faithful-picker-bake/1', 'total': len(items),
        'baked': len(pending)-len(errors), 'errors': errors})
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
