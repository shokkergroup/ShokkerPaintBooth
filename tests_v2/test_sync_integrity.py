"""
test_sync_integrity.py — 3-copy runtime sync + manifest integrity (pure Python).

The app ships its Python/JS/CSS runtime in THREE places that must stay in lockstep:
  - the repo root (source of truth)
  - electron-app/server/<f>                          (Electron mirror #1)
  - electron-app/server/pyserver/_internal/<f>       (Electron mirror #2, frozen pyserver)

`scripts/sync-runtime-copies.js` (node) keeps these in sync from the manifest at
`scripts/runtime-sync-manifest.json`. This suite validates the *Python side* of that
contract WITHOUT shelling out to node:

  - the manifest is valid JSON with the expected top-level keys, including the
    2026-05-29 DUP-01 addition `check_only_directories` containing "engine";
  - every entry in `files` is unique (a dup would silently shadow a sync target);
  - for a representative SAMPLE of manifest-managed files, the root copy and BOTH
    mirror copies are byte-identical (catches writable drift — the bug class the
    sync system exists to prevent).

REPORT-ONLY ENGINE DESIGN (intentional, do NOT regress):
  `check_only_directories: ["engine"]` means the sync system *reports* drift across
  the whole engine/ tree but NEVER `--write`s engine files — converging drifted
  finish-output modules is the owner's call (HIGH finish-output risk). So any path
  under an entry of `check_only_directories` is EXEMPT from the byte-identical
  assertion here: engine copies may legitimately differ during a catalog rebuild.
  We still assert engine files at least EXIST in all three locations (a missing
  mirror would crash the served Electron runtime), which is a stable invariant.

These are stable structural contracts, not churning catalog data, so this file is
expected to be 100% green.

Run it:
    python -m pytest tests_v2/test_sync_integrity.py -o addopts= -o filterwarnings= -p no:cacheprovider -q
"""
import json
import hashlib

import pytest

from conftest import REPO_ROOT

MANIFEST_PATH = REPO_ROOT / "scripts" / "runtime-sync-manifest.json"

# Top-level keys the Python sync contract relies on. `check_only_directories` is the
# 2026-05-29 DUP-01 addition that makes engine/ report-only.
REQUIRED_TOP_LEVEL_KEYS = ("files", "directories", "targets", "check_only_directories")

# How many writable (non-engine) files to byte-compare. A representative sample keeps
# the file fast while still catching drift; sampling is deterministic (every Nth +
# first/last), never random, so a green run means the same thing every run.
SAMPLE_SIZE = 60


# ---------------------------------------------------------------------------
# manifest loading (module scope: read once, reuse across tests)
# ---------------------------------------------------------------------------
def _load_manifest():
    """Read + parse the manifest. Raises on invalid JSON (that's the test we want)."""
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    return json.loads(text)


@pytest.fixture(scope="module")
def manifest():
    return _load_manifest()


def _is_check_only(rel_path, check_only_dirs):
    """True if rel_path lives under any check_only directory (e.g. 'engine')."""
    norm = rel_path.replace("\\", "/")
    for d in check_only_dirs:
        d = d.replace("\\", "/").rstrip("/")
        if norm == d or norm.startswith(d + "/"):
            return True
    return False


def _sample(seq, n):
    """Deterministic representative subset: evenly-strided, always incl. first & last."""
    seq = list(seq)
    if len(seq) <= n:
        return seq
    step = len(seq) / float(n)
    idxs = sorted({int(i * step) for i in range(n)} | {0, len(seq) - 1})
    return [seq[i] for i in idxs]


def _sha256(path):
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# Build the writable (sync-managed, NON check-only) sample at import time so it can
# parametrize. If the manifest is unreadable we surface that via the dedicated JSON
# test rather than crashing collection.
try:
    _M = _load_manifest()
    _CHECK_ONLY = _M.get("check_only_directories", []) or []
    _ALL_FILES = _M.get("files", []) or []
    _WRITABLE_FILES = [f for f in _ALL_FILES if not _is_check_only(f, _CHECK_ONLY)]
    _ENGINE_FILES = [f for f in _ALL_FILES if _is_check_only(f, _CHECK_ONLY)]
    _TARGETS = _M.get("targets", []) or []
except Exception:  # pragma: no cover - exercised only if manifest is broken
    _M = None
    _CHECK_ONLY = []
    _ALL_FILES = []
    _WRITABLE_FILES = []
    _ENGINE_FILES = []
    _TARGETS = []

_WRITABLE_SAMPLE = _sample(_WRITABLE_FILES, SAMPLE_SIZE)
_ENGINE_SAMPLE = _sample(_ENGINE_FILES, 12)


# ---------------------------------------------------------------------------
# 1. manifest is structurally valid
# ---------------------------------------------------------------------------
def test_manifest_is_valid_json():
    """The manifest parses as JSON and is a dict (top-level object)."""
    assert MANIFEST_PATH.is_file(), f"manifest missing: {MANIFEST_PATH}"
    data = _load_manifest()  # raises JSONDecodeError on malformed JSON -> red, as desired
    assert isinstance(data, dict), "manifest top-level must be a JSON object"


def test_manifest_has_expected_top_level_keys(manifest):
    """files / directories / targets / check_only_directories all present and list-typed."""
    for key in REQUIRED_TOP_LEVEL_KEYS:
        assert key in manifest, f"manifest missing top-level key: {key!r}"
        assert isinstance(manifest[key], list), f"manifest[{key!r}] must be a list"


def test_check_only_directories_contains_engine(manifest):
    """The DUP-01 report-only-engine design: engine/ is listed as check-only."""
    check_only = manifest["check_only_directories"]
    norm = [str(d).replace("\\", "/").rstrip("/") for d in check_only]
    assert "engine" in norm, (
        "check_only_directories must contain 'engine' (report-only engine design); "
        f"got {check_only!r}"
    )


def test_targets_are_the_known_mirror(manifest):
    """Mirror root(s) the sync script copies into. 2026-06-09: consolidated 3-copy -> 2-copy —
    the vestigial electron-app/server/pyserver/_internal mirror was removed (excluded from the
    installer, shipped to nobody). Sync is now root -> electron-app/server ONLY."""
    targets = [str(t).replace("\\", "/").rstrip("/") for t in manifest["targets"]]
    assert "electron-app/server" in targets
    assert "electron-app/server/pyserver/_internal" not in targets, (
        "the vestigial pyserver/_internal mirror was removed 2026-06-09; do not re-add it"
    )
    assert len(targets) == len(set(targets)), "duplicate target roots in manifest"


# ---------------------------------------------------------------------------
# 2. files entries are unique
# ---------------------------------------------------------------------------
def test_manifest_files_entries_are_unique(manifest):
    """A duplicate `files` entry would silently shadow / double-copy a target."""
    files = manifest["files"]
    # normalize slashes so 'a/b' and 'a\\b' count as the same logical path
    norm = [f.replace("\\", "/") for f in files]
    dupes = sorted({f for f in norm if norm.count(f) > 1})
    assert not dupes, f"duplicate entries in manifest 'files': {dupes}"
    assert len(norm) == len(set(norm))


def test_manifest_files_nonempty(manifest):
    """Sanity: the manifest actually manages files (guards an empty/placeholder file)."""
    assert len(manifest["files"]) > 0, "manifest 'files' is empty"


# ---------------------------------------------------------------------------
# 3. writable (non-engine) sample: root + both mirrors are byte-identical
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _WRITABLE_SAMPLE, reason="no writable manifest files to sample")
@pytest.mark.parametrize("rel", _WRITABLE_SAMPLE)
def test_writable_copies_are_byte_identical(rel):
    """
    For each sampled writable file, the root copy and BOTH electron mirrors must be
    byte-for-byte identical. This is exactly the drift the sync system exists to
    catch; engine/ (check_only) is excluded from this sample by construction.
    """
    root_file = REPO_ROOT / rel
    assert root_file.is_file(), f"root copy missing: {rel}"
    root_h = _sha256(root_file)
    # 2026-06-09: iterate ALL manifest targets (now just electron-app/server) instead of a
    # hardcoded mirror#1/#2 — adapts automatically to the 2-copy layout and any future change.
    for tgt in _TARGETS:
        mirror = REPO_ROOT / tgt / rel
        assert mirror.is_file(), f"mirror copy missing: {tgt}/{rel}"
        assert _sha256(mirror) == root_h, (
            f"DRIFT: {rel} differs between root and {tgt} "
            f"(run `node scripts/sync-runtime-copies.js --write`)"
        )


# ---------------------------------------------------------------------------
# 4. engine (check_only) sample: EXISTS in all three, but bytes are EXEMPT
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not _ENGINE_SAMPLE, reason="no engine/ files listed in manifest")
@pytest.mark.parametrize("rel", _ENGINE_SAMPLE)
def test_engine_copies_exist_but_drift_is_report_only(rel):
    """
    engine/ is report-only (check_only_directories). The served Electron runtime
    still needs the file PRESENT in every location, so we assert existence — but we
    deliberately do NOT assert byte-identity: engine copies may legitimately differ
    during a catalog rebuild and converging them is the owner's manual call.
    """
    root_file = REPO_ROOT / rel
    assert root_file.is_file(), f"root copy missing: {rel}"
    # 2026-06-09: iterate ALL manifest targets (now just electron-app/server) — was hardcoded
    # mirror#1/#2 when a vestigial pyserver/_internal third copy still existed.
    for tgt in _TARGETS:
        mirror = REPO_ROOT / tgt / rel
        assert mirror.is_file(), f"mirror copy missing (Electron runtime would 404): {tgt}/{rel}"
    # No byte-equality assertion here — that is the whole point of report-only engine.


def test_engine_is_exempt_from_byte_identity_by_construction():
    """
    Guard the design itself: every engine/ file is excluded from the byte-identical
    writable set, so a future edit that accidentally moves engine out of
    check_only_directories (making it auto-written) would change this relationship
    and fail here. Keeps the report-only-engine intent from silently regressing.
    """
    assert _ENGINE_FILES, "expected engine/ modules listed in manifest 'files'"
    overlap = set(_WRITABLE_FILES) & set(_ENGINE_FILES)
    assert not overlap, (
        "engine files leaked into the byte-identical writable set (report-only "
        f"engine design broken): {sorted(overlap)[:5]}"
    )
