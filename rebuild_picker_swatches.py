"""
Picker snapshot builder — offline thumbnails for the finish picker.

Output: thumbnails/picker_split/{base|pattern|monolithic}/{id}.png (~10 KB each)

DAY TO DAY (while editing finishes):
  python rebuild_picker_swatches.py
      → only missing or changed finishes (renderer hash / catalog color)

  python rebuild_picker_swatches.py --category "Foundation" --category "FUSIONS"
      → rebake finishes in those catalog categories

  python rebuild_picker_swatches.py --ids monolithic:depth_wave base:chrome

ALPHA PACKAGING (full ~20 MB library before release):
  python rebuild_picker_swatches.py --package-alpha
      → force-rebake entire catalog + size summary
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime

V5_ROOT = os.path.dirname(os.path.abspath(__file__))
if V5_ROOT not in sys.path:
    sys.path.insert(0, V5_ROOT)
os.environ.setdefault('SHOKKER_SKIP_PICKER_PREBAKE', '1')
# Single-shot baker guard (2026-08-08): server.py calls _start_thumbnail_background_jobs() at IMPORT
# time, and its only kill-switch is SHOKKER_SKIP_SPEC_PREBAKE — SKIP_PICKER_PREBAKE above is read
# nowhere in the tree. Whenever the spec_patterns_{visual,combined} thumb counts sit below
# len(PATTERN_CATALOG) (they do), `import server` spawns the spec-thumb-prebake DAEMON thread. It
# keeps rendering long after main() has written the manifest and returned, so the process never
# reaches interpreter exit: atexit never fires (stale _baker.lock is left behind, which then makes
# the NEXT run no-op for an hour) and RSS climbs ~150 MB/min until the box OOMs. A one-shot CLI baker
# wants none of that background work — opt out before the import that starts it.
os.environ.setdefault('SHOKKER_SKIP_SPEC_PREBAKE', '1')

import server as s  # noqa: E402
from scripts.spb_wilds_release_gate import (  # noqa: E402
    EXPECTED_WILDS_TOTAL,
    acquire_exclusive_lock,
    canonical_wilds_110,
    declared_wilds_110,
    verify_picker_snapshot_postconditions,
)
from scripts.spb_wilds_quality_release_lock import (  # noqa: E402
    DEFAULT_MANIFEST as DEFAULT_WILDS_QUALITY_MANIFEST,
    QualityReleaseBlocked,
    validate_quality_release_manifest,
)


RELEASE_LOCK_WAIT_SECONDS = 30.0  # bounded fail-closed wait; normal runs still do not wait


# Node snippet: load the finish-data file in a minimal sandbox and emit the exact
# id -> swatch the JS picker sends (item.swatch, incl. the dynamically generated
# COLOR_MONOLITHICS). We evaluate rather than regex so generated arrays are caught.
_JS_DUMP_SNIPPET = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
let src = fs.readFileSync(path, 'utf8');
src += '\n;try{globalThis.__BASES=(typeof BASES!=="undefined")?BASES:null;}catch(e){}';
src += '\n;try{globalThis.__PATTERNS=(typeof PATTERNS!=="undefined")?PATTERNS:null;}catch(e){}';
src += '\n;try{globalThis.__MONOLITHICS=(typeof MONOLITHICS!=="undefined")?MONOLITHICS:null;}catch(e){}';
const ctx = {
  document: { getElementById: () => null, querySelectorAll: () => [], addEventListener: () => {},
              createElement: () => ({ style: {}, appendChild() {}, setAttribute() {} }) },
  console: { log: () => {}, warn: () => {}, error: () => {} },
  navigator: {}, location: { href: '' }, setTimeout: () => 0, clearTimeout: () => {},
  fetch: () => Promise.resolve({ json: () => ({}) }),
};
ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
vm.createContext(ctx);
try { vm.runInContext(src, ctx, { filename: path }); } catch (e) {}
const out = [];
function collect(arr, ft) {
  if (!Array.isArray(arr)) return;
  for (const it of arr) { if (it && it.id) out.push([ft, String(it.id), String(it.swatch || '')]); }
}
collect(ctx.__BASES, 'base');
collect(ctx.__PATTERNS, 'pattern');
collect(ctx.__MONOLITHICS, 'monolithic');
process.stdout.write(JSON.stringify(out));
"""


def _normalize_swatch_tint_hex(sw):
    """Mirror _normalizeSwatchTintHex() in swatch-popup-render-controls.js."""
    match = re.fullmatch(r'#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})', str(sw or '').strip())
    if match:
        value = match.group(1).lower()
        if len(value) == 3:
            return ''.join(c * 2 for c in value)
        return value
    return '888888'


def _picker_js_swatch_items():
    """(finish_type, finish_key, color_hex) for every finish the JS picker renders.

    color_hex is the exact tint the picker sends (item.swatch normalized), so the
    warmed swatch_cache key matches the live prefer=live request byte-for-byte.
    """
    data_file = os.path.join(V5_ROOT, 'paint-booth-0-finish-data.js')
    if not os.path.isfile(data_file):
        print(f"  WARN finish data file not found: {data_file}")
        return []
    try:
        proc = subprocess.run(
            ['node', '-e', _JS_DUMP_SNIPPET, data_file],
            capture_output=True, text=True, timeout=120,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    except FileNotFoundError:
        print("  ERROR node not found on PATH; --warm-cache needs node to read JS swatch tints")
        return []
    except subprocess.TimeoutExpired:
        print("  ERROR node JS swatch dump timed out")
        return []
    if proc.returncode != 0 or not proc.stdout.strip():
        print(f"  ERROR node JS swatch dump failed (rc={proc.returncode}): {proc.stderr.strip()[:200]}")
        return []
    try:
        raw = json.loads(proc.stdout)
    except Exception as e:
        print(f"  ERROR could not parse node swatch dump: {e}")
        return []
    items, seen = [], set()
    for ft, fid, sw in raw:
        key = (ft, fid)
        if key in seen:
            continue
        seen.add(key)
        items.append((ft, fid, _normalize_swatch_tint_hex(sw)))
    return items


def _parse_ids_arg(raw_items):
    """Parse base:foo, pattern:bar, monolithic:baz or bare ids (type from registry)."""
    out = []
    reg_items = {(t, k) for t, k in s._picker_swatch_catalog_items()}
    reg_by_id = {}
    for t, k in reg_items:
        reg_by_id.setdefault(k, []).append(t)

    for raw in raw_items:
        raw = (raw or '').strip()
        if not raw:
            continue
        if ':' in raw:
            typ, fid = raw.split(':', 1)
            typ = {'bases': 'base', 'patterns': 'pattern', 'monolithics': 'monolithic', 'mono': 'monolithic'}.get(typ, typ)
            out.append((typ, fid))
        else:
            types = reg_by_id.get(raw)
            if not types:
                print(f"  WARN unknown finish id (skipped): {raw}")
                continue
            for typ in types:
                out.append((typ, raw))
    return out


def _ids_from_categories(category_names):
    """Resolve finish ids from paint-booth-0-catalog-scorecard.js categories."""
    path = os.path.join(V5_ROOT, 'paint-booth-0-catalog-scorecard.js')
    if not os.path.isfile(path):
        print(f"  WARN scorecard not found: {path}")
        return []
    wanted = {c.strip().lower() for c in category_names if c.strip()}
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    out = []
    for m in re.finditer(
        r'"((?:base|pattern|monolithic):[a-z0-9_]+)"\s*:\s*\{[^}]*?"category"\s*:\s*"([^"]+)"',
        text,
        re.IGNORECASE | re.DOTALL,
    ):
        full_key, cat = m.group(1), m.group(2)
        if cat.strip().lower() not in wanted:
            continue
        surface, fid = full_key.split(':', 1)
        ft = 'monolithic' if surface == 'monolithic' else surface
        out.append((ft, fid))
    return out


def _dir_size_bytes(root):
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith('.png'):
                try:
                    total += os.path.getsize(os.path.join(dirpath, name))
                except OSError:
                    pass
    return total


def _run_warm_cache(args, force):
    """Warm thumbnails/swatch_cache/picker_split with the exact prefer=live keys."""
    items = _picker_js_swatch_items()
    if not items:
        print("No JS picker finishes resolved; nothing to warm.")
        return 1

    if args.type != 'all':
        items = [(t, k, c) for t, k, c in items if t == args.type]
    if args.ids:
        wanted = {(t, k) for t, k in _parse_ids_arg(args.ids)}
        items = [(t, k, c) for t, k, c in items if (t, k) in wanted]
    if args.limit > 0:
        items = items[: args.limit]
    if not items:
        print("No finishes matched the warm-cache filters.")
        return 1

    def _progress(ft, fk, status, i, total, detail=None):
        if status == 'ok':
            if i % 50 == 0 or i == total:
                print(f"  [{i}/{total}] warmed {ft}/{fk}")
        elif status == 'fail':
            print(f"  [{i}/{total}] FAIL {ft}/{fk}: {detail}")

    out_dir = os.path.join(s.THUMBNAIL_DIR, 'swatch_cache', 'picker_split')
    print(f"Warming {len(items)} prefer=live split swatches into {out_dir} (force={force})...")
    t0 = time.time()
    baked, skipped, errors = s.warm_picker_split_swatch_cache(
        items,
        force=force,
        on_progress=_progress,
        wilds_quality_manifest=args.wilds_quality_manifest,
    )
    elapsed = time.time() - t0
    n_png = 0
    if os.path.isdir(out_dir):
        n_png = sum(1 for nm in os.listdir(out_dir) if nm.lower().endswith('.png'))
    per = (elapsed / baked) if baked else 0.0
    print(f"Done: {baked} baked, {skipped} up-to-date/skipped, {errors} errors in {elapsed:.1f}s "
          f"({per*1000:.0f} ms/swatch baked)")
    print(f"Warm cache now holds {n_png} PNGs under {out_dir}")
    return 0 if errors == 0 else 1


def _acquire_baker_lock(stale_secs=3600, wait_secs=0, poll_secs=0.25):
    """Single-baker guard (2026-06-27): two thumbnail bakers running at once (e.g. the 25s boot-warm
    plus a manual/dev-reloader re-trigger) race the manifest's load-modify-save and lose each other's
    entries -> the catalog re-bakes next launch. Returns the lock path if WE acquired it, else None
    (another recent baker is running -> caller should exit). A stale lock (crashed baker, older than
    stale_secs) is reclaimed. os.O_EXCL create is atomic, so the winner is unambiguous."""
    lock = os.path.join(s.THUMBNAIL_DIR, s.PICKER_SPLIT_SUBDIR, '_baker.lock')
    return acquire_exclusive_lock(
        lock,
        stale_secs=stale_secs,
        wait_secs=wait_secs,
        poll_secs=poll_secs,
    )


# ~30 MB leaks per baked finish (see _run_chunked), so a worker's peak RSS is roughly
# 650 MB baseline + 30 MB * chunk. 50 keeps a worker near 2 GB; 150 measured at ~5.5 GB.
DEFAULT_CHUNK = 50


def _select_items(args):
    """Resolve CLI selection, with a fail-closed canonical Wilds release path."""
    if args.wilds_110:
        conflicts = []
        if args.ids:
            conflicts.append('--ids')
        if args.category:
            conflicts.append('--category')
        if args.key:
            conflicts.append('--key')
        if args.limit:
            conflicts.append('--limit')
        if args.type not in ('all', 'monolithic'):
            conflicts.append('--type')
        if args.package_alpha:
            conflicts.append('--package-alpha')
        if args.warm_cache:
            conflicts.append('--warm-cache')
        if conflicts:
            raise ValueError(
                '--wilds-110 cannot be combined with ' + ', '.join(conflicts)
            )
        _lanes, ids = canonical_wilds_110(s.engine.MONOLITHIC_REGISTRY)
        items = [('monolithic', fid) for fid in ids]
        if len(items) != EXPECTED_WILDS_TOTAL or len(set(items)) != EXPECTED_WILDS_TOTAL:
            raise RuntimeError(
                f'Canonical Wilds selection is {len(items)} items, expected '
                f'{EXPECTED_WILDS_TOTAL} unique items'
            )
        return items
    if args.ids:
        return _parse_ids_arg(args.ids)
    if args.category:
        items = _ids_from_categories(args.category)
        print(f"Category filter: {len(items)} finishes")
        return items
    items = s._picker_swatch_catalog_items()
    if args.type != 'all':
        items = [(t, k) for t, k in items if t == args.type]
    if args.key:
        items = [(t, k) for t, k in items if k == args.key]
    return items


def _run_chunked(items, force, chunk, wilds_quality_manifest):
    """Bake in bounded worker processes so peak RSS stays flat.

    Measured 2026-08-08: the render path holds roughly 20 MB per baked finish in NATIVE
    (numpy / PIL) buffers, not Python objects — a forced bake went 11 MB -> 9,150 MB over 452
    finishes and was still climbing linearly, i.e. it never plateaus. The engine's own caches are
    NOT the culprit (build_multi_zone._zone_cache is capped at 24 and _SWATCH_CACHE is only fed by
    the HTTP routes), and because plain numeric ndarrays are not gc-tracked those buffers are
    invisible to gc/tracemalloc — which is why this went unnoticed. Nothing in the batch loop frees
    them; only interpreter exit does. So a full-catalog bake in ONE process walks into tens of GB,
    which is what drove this box into memory compression and a system-wide stall (and left a stale
    _baker.lock behind when it was killed, silently no-opping the next run for an hour).

    Slicing the catalog across short-lived workers bounds peak RSS to about one chunk's worth. The
    parent holds the baker lock for the whole run; workers get --worker so they don't fight over it.
    Pass --chunk 0 for the old single-process behaviour.
    """
    total = len(items)
    chunk = max(1, chunk)
    n_chunks = (total + chunk - 1) // chunk
    baked = skipped = errors = 0
    print(f"Chunked bake: {total} finishes across {n_chunks} worker(s) of up to {chunk} "
          f"(bounds peak RSS; --chunk 0 disables)")

    for ci in range(n_chunks):
        part = items[ci * chunk:(ci + 1) * chunk]
        fd, res_path = tempfile.mkstemp(prefix='picker_chunk_', suffix='.json')
        os.close(fd)
        cmd = [sys.executable, os.path.abspath(__file__), '--worker',
               '--result-file', res_path,
               '--wilds-quality-manifest', str(wilds_quality_manifest),
               '--ids']
        cmd += [f'{t}:{k}' for t, k in part]
        if force:
            cmd.append('--force')
        print(f"  [chunk {ci + 1}/{n_chunks}] {len(part)} finishes...")
        try:
            # [2026-09-05] never let a chunk worker open a console window over the app (CREATE_NO_WINDOW on Windows)
            rc = subprocess.call(cmd, cwd=V5_ROOT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if rc != 0:
                print(f"  [chunk {ci + 1}/{n_chunks}] worker exited {rc}")
                errors += len(part)
                continue
            with open(res_path, 'r', encoding='utf-8') as rf:
                r = json.load(rf)
            baked += r.get('baked', 0)
            skipped += r.get('skipped', 0)
            errors += r.get('errors', 0)
        except Exception as e:
            print(f"  [chunk {ci + 1}/{n_chunks}] failed: {e}")
            errors += len(part)
        finally:
            try:
                os.remove(res_path)
            except OSError:
                pass

    return baked, skipped, errors


def main():
    ap = argparse.ArgumentParser(description='Build/update picker_split snapshot PNGs')
    ap.add_argument('--force', action='store_true', help='Rebuild all targets even if up to date')
    ap.add_argument('--package-alpha', action='store_true', help='Force full catalog bake for Alpha release')
    ap.add_argument('--type', choices=('base', 'pattern', 'monolithic', 'all'), default='all')
    ap.add_argument('--key', type=str, default=None, help='Single finish id (with --type)')
    ap.add_argument('--ids', nargs='+', default=None, help='Ids: monolithic:depth_wave or bare id')
    ap.add_argument('--category', action='append', default=None, help='Catalog category (repeatable)')
    ap.add_argument(
        '--wilds-110', action='store_true',
        help='Fail-closed release selection: canonical 20 Cryptid + 50 Morpho + '
             '20 Bloom + 20 Petri callable monolithic renderers.',
    )
    ap.add_argument(
        '--wilds-quality-manifest', default=str(DEFAULT_WILDS_QUALITY_MANIFEST),
        help='Explicit 110-ID owner review manifest required by --wilds-110.',
    )
    ap.add_argument(
        '--release-gate', action='store_true',
        help='Wait for the baker lock and verify every requested PNG path and '
             'manifest renderer hash after the run.',
    )
    ap.add_argument('--limit', type=int, default=0, help='Max items (0 = all)')
    ap.add_argument('--chunk', type=int, default=DEFAULT_CHUNK,
                    help=f'Bake at most N finishes per worker process (default {DEFAULT_CHUNK}, '
                         '0 = one process for everything, the old behaviour). See _run_chunked().')
    ap.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--result-file', default=None, help=argparse.SUPPRESS)
    ap.add_argument('--warm-cache', action='store_true',
                    help='Pre-render the exact per-color split PNGs the prefer=live picker '
                         'route serves (thumbnails/swatch_cache/picker_split) so every picker / '
                         'finish-library thumbnail is a guaranteed instant cache HIT.')
    args = ap.parse_args()

    force = args.force or args.package_alpha
    release_gate = bool(args.release_gate or args.wilds_110)
    if release_gate and args.warm_cache:
        ap.error('release-gated static picker snapshots cannot use --warm-cache')

    # Single-baker guard: never let two bakers race the manifest (root cause of "thumbnails re-bake
    # every launch"). If another recent baker holds the lock, exit cleanly — it will finish the work.
    # --worker children are dispatched by _run_chunked(); the PARENT already holds the lock for the
    # whole run, so a child must not try to take it (it would always lose and no-op the chunk).
    if not args.worker:
        _lock = _acquire_baker_lock(
            wait_secs=RELEASE_LOCK_WAIT_SECONDS if release_gate else 0,
        )
        if _lock is None:
            if release_gate:
                print(
                    f"Release gate could not acquire the thumbnail baker lock after "
                    f"{RELEASE_LOCK_WAIT_SECONDS:.0f}s; failing closed."
                )
                return 1
            print("Another thumbnail baker is already running; skipping to avoid manifest races.")
            return 0
        import atexit
        atexit.register(lambda: (os.remove(_lock) if os.path.exists(_lock) else None))

    if args.warm_cache:
        return _run_warm_cache(args, force)

    try:
        items = _select_items(args)
    except (RuntimeError, ValueError) as exc:
        ap.error(str(exc))

    if args.limit > 0:
        items = items[: args.limit]

    if not items:
        print("No finishes matched.")
        return 1

    _wilds_lanes, all_wilds_ids = declared_wilds_110()
    all_wilds_id_set = set(all_wilds_ids)
    selected_wilds = sorted({
        finish_key for finish_type, finish_key in items
        if finish_type == 'monolithic' and finish_key in all_wilds_id_set
    })
    if selected_wilds and (args.wilds_110 or args.release_gate) and not args.worker:
        try:
            quality = validate_quality_release_manifest(
                args.wilds_quality_manifest,
                all_wilds_ids,
                registry=s.engine.MONOLITHIC_REGISTRY,
            )
        except (OSError, TypeError, QualityReleaseBlocked) as exc:
            print(f"Wilds quality release LOCKED: {exc}")
            return 1
        print(
            f"Wilds quality release lock OPEN: "
            f"{quality['owner_accepted']}/{quality['expected_ids']} owner accepted"
        )

    def _progress(ft, fk, status, i, total, detail=None):
        if status == 'ok':
            print(f"  [{i}/{total}] OK {ft}/{fk}")
        elif status == 'fail':
            print(f"  [{i}/{total}] FAIL {ft}/{fk}: {detail}")

    if args.chunk and not args.worker:
        # Decide what actually needs baking IN THIS process first. The day-to-day run passes the
        # whole catalog (~3.3k) but usually only a handful are stale, and spawning a worker per 50
        # catalog entries just to skip them would be far slower than the single process it replaces.
        # This costs nothing extra: bake_picker_split_batch() runs the same check per item anyway.
        todo = [(t, k) for t, k in items if s.picker_split_needs_rebuild(t, k, force=force)]
        pre_skipped = len(items) - len(todo)
        if pre_skipped:
            print(f"{pre_skipped} finish(es) already up to date; {len(todo)} need baking.")
        if len(todo) > args.chunk:
            baked, skipped, errors = _run_chunked(
                todo, force, args.chunk, args.wilds_quality_manifest,
            )
        else:
            print(f"Baking {len(todo)} picker snapshot(s) (force={force})...")
            baked, skipped, errors = s.bake_picker_split_batch(
                todo,
                force=force,
                on_progress=_progress,
                wilds_quality_manifest=args.wilds_quality_manifest,
            )
        skipped += pre_skipped
    else:
        print(f"Baking {len(items)} picker snapshot(s) (force={force})...")
        baked, skipped, errors = s.bake_picker_split_batch(
            items,
            force=force,
            on_progress=_progress,
            wilds_quality_manifest=args.wilds_quality_manifest,
        )

    if args.result_file:
        try:
            with open(args.result_file, 'w', encoding='utf-8') as rf:
                json.dump({'baked': baked, 'skipped': skipped, 'errors': errors}, rf)
        except Exception as e:
            print(f"  WARN could not write result file: {e}")

    # A worker's per-finish manifest entries are already saved by save_picker_split_snapshot().
    # Stop here so N workers don't each re-walk the whole PNG tree and re-stamp last_run — the
    # parent writes the one authoritative summary below.
    if args.worker:
        return 0 if errors == 0 else 1

    root = os.path.join(s.THUMBNAIL_DIR, s.PICKER_SPLIT_SUBDIR)
    total_bytes = _dir_size_bytes(root)
    manifest = s._load_picker_split_manifest()
    manifest['last_run'] = {
        'generated': datetime.utcnow().isoformat(),
        'baked': baked,
        'skipped': skipped,
        'errors': errors,
        'force': force,
        'total_png_bytes': total_bytes,
    }
    s._save_picker_split_manifest(manifest)

    postcondition_errors = []
    if release_gate:
        postcondition_errors = verify_picker_snapshot_postconditions(s, items)
        if args.wilds_110 and len(items) != EXPECTED_WILDS_TOTAL:
            postcondition_errors.append(
                f'Wilds release selection was {len(items)}, expected {EXPECTED_WILDS_TOTAL}'
            )
        if postcondition_errors:
            print(f"Release postcondition FAIL ({len(postcondition_errors)} error(s)):")
            for error in postcondition_errors[:30]:
                print(f"  {error}")
            if len(postcondition_errors) > 30:
                print(f"  ... and {len(postcondition_errors) - 30} more")
        else:
            print(f"Release postcondition PASS: {len(items)}/{len(items)} requested snapshots current")

    mb = total_bytes / (1024 * 1024)
    print(f"Done: {baked} baked, {skipped} up-to-date, {errors} errors")
    print(f"Picker library: {s._count_picker_split_snapshots()} PNGs, ~{mb:.1f} MB under {root}")
    if args.package_alpha:
        print("Alpha package: copy thumbnails/picker_split/ into your release bundle.")
    return 0 if errors == 0 and not postcondition_errors else 1


if __name__ == '__main__':
    sys.exit(main())
