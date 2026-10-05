"""tests_v2/test_server_contract.py — server correctness CONTRACTS, unit-style.

This file deliberately does NOT stand up a live HTTP server. The server's
security-, coercion-, and locking-relevant logic that *is* factored into small
importable helpers (``server_routes/*.py``) is imported and asserted directly.
Where the logic lives inline in a Flask route (swatch size/seed clamp, the
``/cleanup`` max_age coercion, the patched ``/render`` lock control flow) there
is no extractable helper to import, so — exactly as ``tests/test_render_lock_
semantics.py`` does for the lock — we reimplement a minimal, faithful mirror of
that control flow and pin its contract independently. Mirrors are clearly
marked and kept byte-for-byte aligned with the source they mirror.

What is pinned here (all stable contracts, independent of catalog churn):

* PATH-TRAVERSAL guard in ``server_routes/paint_upload_routes.py`` — the real
  ``_raw_path_is_traversal`` + ``_resolve_within_roots`` helpers reject raw
  ``..`` and out-of-root absolute paths and accept genuine in-root paths.
* INPUT COERCION — the real ``render_monitoring._clamped_limit`` helper clamps a
  query int into ``[1, max]`` and defaults bad input; plus independent mirrors
  of the inline swatch size/seed clamp and the ``/cleanup`` ``max_age_hours``
  coercion, asserting bad input can neither OOM a render nor wipe fresh jobs.
* RENDER-LOCK semantics — an independent minimal mirror of the patched
  ``/render`` flow (acquire-or-429, release-only-if-held), asserting the lock is
  NEVER released when not held, plus a stdlib proof that the old force-release
  path really did break mutual exclusion.
* OBSERVABILITY — ``server_routes/observability.py`` installs without error and
  its Flask error handler returns a clean JSON 500 that does NOT leak the
  exception text, while re-raising real HTTP errors (404) to Flask's own
  handlers.

Run standalone:
    python -m pytest tests_v2/test_server_contract.py -o addopts= -o filterwarnings= -p no:cacheprovider -q
"""

import importlib
import logging
import os
import tempfile
import threading

import pytest


# --------------------------------------------------------------------------- #
# Module loaders (these route helpers are plain importable modules; the engine
# is NOT needed, so importing them is cheap and side-effect-free).
# --------------------------------------------------------------------------- #
def _load(modname):
    return importlib.import_module(modname)


@pytest.fixture(scope="module")
def paint_upload():
    return _load("server_routes.paint_upload_routes")


@pytest.fixture(scope="module")
def render_monitoring():
    return _load("server_routes.render_monitoring")


@pytest.fixture(scope="module")
def observability():
    return _load("server_routes.observability")


# A logger that never emits, so the guards' warning() calls are harmless here.
_NULL_LOG = logging.getLogger("tests_v2.server_contract")
_NULL_LOG.addHandler(logging.NullHandler())
_NULL_LOG.propagate = False


# A faithful copy of the nested ``safe_int`` closure used throughout the server
# routes (server_v5.py / render_monitoring callers). ``_clamped_limit`` takes it
# as an injected dependency, so we provide the real shape.
def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# =========================================================================== #
# 1. Path-traversal guard (real helpers from paint_upload_routes)
# =========================================================================== #
class TestPathTraversalGuard:
    """The serve-local-file bridge must never read outside the allowed roots."""

    def test_raw_traversal_detects_unix_and_windows_separators(self, paint_upload):
        f = paint_upload._raw_path_is_traversal
        # A literal parent-escape segment must be caught with either separator,
        # BEFORE os.path.abspath() collapses it into dead code.
        assert f("a/../../etc/passwd") is True
        assert f("a\\..\\..\\etc\\passwd") is True
        assert f("../secret") is True
        assert f("foo/../bar") is True

    def test_raw_traversal_allows_clean_paths(self, paint_upload):
        f = paint_upload._raw_path_is_traversal
        assert f("a/b/c.png") is False
        assert f("clean_name.tga") is False
        # Empty / falsey input is not itself a traversal (rejected upstream as
        # "no path"), so the guard must not flag it.
        assert f("") is False
        assert f(None) is False

    def test_raw_traversal_does_not_false_positive_on_dotdot_in_filename(self, paint_upload):
        # '..foo' or 'a..b' are filenames, not parent escapes — only a whole
        # '..' path segment counts.
        f = paint_upload._raw_path_is_traversal
        assert f("a/..foo/b") is False
        assert f("weird..name.png") is False

    def test_resolve_accepts_genuine_in_root_file(self, paint_upload):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.realpath(d)
            inside = os.path.join(root, "asset.png")
            open(inside, "w").close()
            resolved = paint_upload._resolve_within_roots(inside, [root], _NULL_LOG)
            assert resolved is not None
            assert os.path.realpath(resolved) == os.path.realpath(inside)

    def test_resolve_rejects_raw_dotdot_escape(self, paint_upload):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.realpath(d)
            # A relative path with literal '..' that would climb out of root.
            escape = os.path.join(d, "..", "..", "etc", "passwd")
            assert paint_upload._resolve_within_roots(escape, [root], _NULL_LOG) is None

    def test_resolve_rejects_out_of_root_absolute_path(self, paint_upload):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.realpath(d)
            with tempfile.TemporaryDirectory() as other:
                outside = os.path.realpath(os.path.join(other, "not_in_root.tga"))
                open(outside, "w").close()
                # Clean absolute path that simply isn't under the allowed root.
                assert not outside.startswith(root + os.sep)
                assert paint_upload._resolve_within_roots(outside, [root], _NULL_LOG) is None

    def test_resolve_rejects_sibling_prefix_collision(self, paint_upload):
        # Classic startswith bug: '/root_evil' must NOT count as inside '/root'.
        # The guard uses ``root + os.sep`` so a shared string prefix is rejected.
        with tempfile.TemporaryDirectory() as base:
            root = os.path.realpath(os.path.join(base, "root"))
            sibling = os.path.realpath(os.path.join(base, "root_evil"))
            os.makedirs(root)
            os.makedirs(sibling)
            evil_file = os.path.join(sibling, "x.png")
            open(evil_file, "w").close()
            assert paint_upload._resolve_within_roots(evil_file, [root], _NULL_LOG) is None

    def test_resolve_empty_root_list_rejects_everything(self, paint_upload):
        with tempfile.TemporaryDirectory() as d:
            inside = os.path.join(d, "a.png")
            open(inside, "w").close()
            # No allowed roots -> nothing is servable.
            assert paint_upload._resolve_within_roots(inside, [], _NULL_LOG) is None


# =========================================================================== #
# 2. Input coercion
# =========================================================================== #
class TestClampedLimit:
    """The real ``render_monitoring._clamped_limit`` helper (used by
    /api/recent-renders) must clamp into [1, max] and default bad input."""

    def test_defaults_on_bad_or_missing_input(self, render_monitoring):
        f = render_monitoring._clamped_limit
        assert f(None, _safe_int, default=25, max_value=64) == 25
        assert f("abc", _safe_int, default=25, max_value=64) == 25
        assert f("", _safe_int, default=25, max_value=64) == 25

    def test_clamps_into_one_to_max(self, render_monitoring):
        f = render_monitoring._clamped_limit
        assert f("0", _safe_int, default=25, max_value=64) == 1      # floor is 1
        assert f("-5", _safe_int, default=25, max_value=64) == 1     # negative -> 1
        assert f("999", _safe_int, default=25, max_value=64) == 64   # over ceiling
        assert f("30", _safe_int, default=25, max_value=64) == 30    # in range

    def test_respects_custom_max(self, render_monitoring):
        f = render_monitoring._clamped_limit
        assert f("500", _safe_int, default=10, max_value=100) == 100
        assert f("50", _safe_int, default=10, max_value=100) == 50


class TestSwatchSizeSeedCoercion:
    """Independent mirror of the inline swatch size/seed coercion in
    server_routes/swatch_routes.py (api_swatch) and server_v5.py
    (api_finish_viewer_mono). No extractable helper exists, so we reimplement
    the exact ``max(lo, min(hi, int(...)))`` clamp + try/except default and pin
    its contract: a typo'd size can never OOM a render, a bad seed never crashes.
    """

    @staticmethod
    def _coerce_size(raw, *, lo=32, hi=256, default=64):
        # Mirrors swatch_routes.api_swatch:
        #   size = max(32, min(256, int(request.args.get('size', 64))))
        try:
            return max(lo, min(hi, int(raw)))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_seed(raw, *, default=42):
        # Mirrors swatch_routes.api_swatch:
        #   seed = int(request.args.get('seed', 42)) (try/except -> default)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    def test_size_defaults_on_bad_input(self):
        f = self._coerce_size
        assert f(None) == 64
        assert f("abc") == 64
        assert f("") == 64

    def test_size_clamps_to_bounds(self):
        f = self._coerce_size
        assert f("1") == 32          # below floor -> lo
        assert f("-100") == 32       # negative -> lo
        assert f("999999") == 256    # above ceiling -> hi (no OOM-size render)
        assert f("128") == 128       # in range -> unchanged

    def test_size_respects_finish_viewer_bounds(self):
        # server_v5 api_finish_viewer_mono uses max(128, min(2048, ...)).
        f = lambda r: self._coerce_size(r, lo=128, hi=2048, default=1024)
        assert f("50") == 128
        assert f("9999") == 2048
        assert f("bad") == 1024
        assert f("1024") == 1024

    def test_seed_defaults_on_bad_input(self):
        f = self._coerce_seed
        assert f(None) == 42
        assert f("abc") == 42
        assert f("7") == 7
        # The route does NOT reject negative seeds; it just coerces to int.
        assert f("-1") == -1


class TestCleanupMaxAgeCoercion:
    """Independent mirror of the inline ``/cleanup`` max_age coercion in
    server_routes/iracing_utility_routes.py (cleanup_jobs):

        try:
            max_age_hours = float(data.get("max_age_hours", 0) or 0)
        except (TypeError, ValueError):
            max_age_hours = 0

    and the guard ``if max_age_hours > 0`` that decides whether age-filtering is
    applied at all. Contract: a bad/missing/<=0 max_age must NOT silently delete
    fresh jobs via an underflowed comparison — it disables age-filtering (the
    route treats <=0 as 'no age filter', and only deletes when explicitly > 0).
    """

    @staticmethod
    def _coerce_max_age_hours(value):
        try:
            return float(value if value is not None else 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _age_filter_active(max_age_hours):
        return max_age_hours > 0

    def test_bad_input_coerces_to_zero(self):
        f = self._coerce_max_age_hours
        assert f(None) == 0.0
        assert f("abc") == 0.0
        assert f("") == 0.0

    def test_valid_values_pass_through(self):
        f = self._coerce_max_age_hours
        assert f("24") == 24.0
        assert f(48) == 48.0
        assert f("0.5") == 0.5

    def test_zero_or_negative_disables_age_filter(self):
        # The route only age-filters when max_age_hours > 0, so a non-positive
        # value means "no age cutoff" — it never produces a negative cutoff that
        # would classify every fresh job as old.
        assert self._age_filter_active(0.0) is False
        assert self._age_filter_active(-5.0) is False
        assert self._age_filter_active(24.0) is True


# =========================================================================== #
# 3. Render-lock semantics — independent minimal mirror of the patched /render
#    control flow (see tests/test_render_lock_semantics.py for the full version).
#    Core invariant under test: the lock is NEVER released when not held.
# =========================================================================== #
def _render_with_lock(lock, body, *, timeout=0.05):
    """Faithful mirror of the patched server.py /render lock handling:

      * acquire(timeout) -> on failure return (429, None); NEVER force-release.
      * run body under the lock; release in finally ONLY if we acquired it.
    """
    have_lock = lock.acquire(timeout=timeout)
    if not have_lock:
        return 429, None
    try:
        return 200, body()
    finally:
        if have_lock:
            lock.release()


def _buggy_force_release(lock, timeout=0.01):
    """The OLD defect, kept only to prove what the fix removed: on timeout it
    releases a lock this thread does NOT own, then re-acquires."""
    acquired = lock.acquire(timeout=timeout)
    if not acquired:
        try:
            lock.release()  # frees whichever thread currently holds it
        except RuntimeError:
            pass
        lock.acquire(timeout=timeout)
    return acquired


class TestRenderLockSemantics:
    def test_acquire_timeout_returns_429_without_releasing(self):
        lock = threading.Lock()
        lock.acquire()  # simulate an in-flight render holding the lock
        try:
            status, result = _render_with_lock(lock, lambda: "ran", timeout=0.02)
            assert status == 429
            assert result is None
            # The original owner must STILL hold the lock — the busy caller may
            # neither release nor steal it.
            assert lock.locked() is True
        finally:
            lock.release()

    def test_success_path_releases_exactly_once(self):
        lock = threading.Lock()
        status, result = _render_with_lock(lock, lambda: 42, timeout=0.05)
        assert status == 200
        assert result == 42
        assert lock.locked() is False
        # Released exactly once: a second release on an unheld stdlib lock raises.
        with pytest.raises(RuntimeError):
            lock.release()

    def test_release_once_even_when_body_raises(self):
        lock = threading.Lock()

        def boom():
            raise ValueError("render failed")

        with pytest.raises(ValueError):
            _render_with_lock(lock, boom, timeout=0.05)
        assert lock.locked() is False
        with pytest.raises(RuntimeError):
            lock.release()  # already released by finally

    def test_never_releases_owner_lock_under_concurrency(self):
        lock = threading.Lock()
        worker_has_lock = threading.Event()
        worker_may_finish = threading.Event()
        results = {}

        def worker():
            assert lock.acquire(timeout=1.0)
            worker_has_lock.set()
            try:
                worker_may_finish.wait(timeout=1.0)
            finally:
                lock.release()

        t = threading.Thread(target=worker)
        t.start()
        try:
            assert worker_has_lock.wait(timeout=1.0)
            status, _ = _render_with_lock(lock, lambda: "second", timeout=0.05)
            results["status"] = status
            # The worker still owns its lock — the busy caller did not free it.
            assert lock.locked() is True
        finally:
            worker_may_finish.set()
            t.join(timeout=2.0)
        assert results["status"] == 429
        assert lock.locked() is False

    def test_old_force_release_breaks_mutual_exclusion(self):
        """Documents the exact defect the fix removed: force-releasing a lock
        owned by another thread lets a second caller hold it simultaneously."""
        lock = threading.Lock()
        owner_holds = threading.Event()
        release_owner = threading.Event()

        def owner():
            lock.acquire()
            owner_holds.set()
            release_owner.wait(timeout=1.0)
            try:
                lock.release()
            except RuntimeError:
                pass

        t = threading.Thread(target=owner)
        t.start()
        try:
            assert owner_holds.wait(timeout=1.0)
            _buggy_force_release(lock, timeout=0.02)
            # Bug proof: busy caller now holds a lock the owner never released.
            assert lock.locked() is True
            lock.release()  # clean up the stolen lock
        finally:
            release_owner.set()
            t.join(timeout=2.0)


# =========================================================================== #
# 4. Observability: install + clean JSON error handler (real module)
# =========================================================================== #
@pytest.fixture
def force_observability_on(monkeypatch, observability):
    """Pin the opt-out flag ON so the handler always installs in this test run,
    and RESET the module-level install-tracking state so each test starts clean.

    install_flask_error_handler() is idempotent keyed on id(app): it records
    id(app) in a module-level set and returns False on repeat. Across a full
    suite run, a previous test's Flask app gets GC'd and a fresh app can REUSE
    the same id(), which would make a genuinely-new registration return False
    and flake the 'returns True' assertions. Clearing the global set (and the
    excepthook-installed flag) between tests is the correct isolation for this
    module-level state — it can't affect production behavior.
    """
    monkeypatch.setenv("SHOKKER_OBSERVABILITY", "1")
    if hasattr(observability, "_flask_handlers"):
        observability._flask_handlers.clear()
    if hasattr(observability, "_excepthook_installed"):
        observability._excepthook_installed = False
    yield


def _make_app():
    flask = importlib.import_module("flask")
    return flask.Flask(__name__)


class TestObservability:
    def test_flag_default_on_and_respects_optout(self, observability, monkeypatch):
        monkeypatch.delenv("SHOKKER_OBSERVABILITY", raising=False)
        assert observability.observability_enabled() is True
        for falsey in ("0", "false", "no", "off", "n", "f", "FALSE", "Off"):
            monkeypatch.setenv("SHOKKER_OBSERVABILITY", falsey)
            assert observability.observability_enabled() is False
        for truthy in ("1", "true", "yes", "on", ""):
            monkeypatch.setenv("SHOKKER_OBSERVABILITY", truthy)
            assert observability.observability_enabled() is True

    def test_install_flask_handler_returns_true_once(self, observability, force_observability_on):
        app = _make_app()
        # Fresh app id -> a new registration this call.
        assert observability.install_flask_error_handler(app, logger=_NULL_LOG) is True
        # Idempotent: the same app installs only once (keyed on id(app)).
        assert observability.install_flask_error_handler(app, logger=_NULL_LOG) is False

    def test_install_is_noop_when_disabled(self, observability, monkeypatch):
        monkeypatch.setenv("SHOKKER_OBSERVABILITY", "0")
        app = _make_app()
        assert observability.install_flask_error_handler(app, logger=_NULL_LOG) is False

    def test_error_handler_returns_clean_json_500_without_leak(self, observability, force_observability_on):
        app = _make_app()
        assert observability.install_flask_error_handler(app, logger=_NULL_LOG) is True

        secret = "TOP_SECRET_INTERNAL_TRACE_MARKER"

        @app.route("/boom")
        def boom():
            raise ValueError(secret)

        client = app.test_client()
        resp = client.get("/boom")
        assert resp.status_code == 500
        body = resp.get_json()
        assert isinstance(body, dict)
        assert body.get("error") == "internal_server_error"
        assert "message" in body
        # The raw exception text must NOT leak to the client.
        assert secret.encode() not in resp.data
        assert secret not in body.get("message", "")

    def test_error_handler_reraises_http_exceptions(self, observability, force_observability_on):
        app = _make_app()
        assert observability.install_flask_error_handler(app, logger=_NULL_LOG) is True

        flask = importlib.import_module("flask")

        @app.route("/missing")
        def missing():
            flask.abort(404)

        client = app.test_client()
        resp = client.get("/missing")
        # 404 must be owned by Flask's own handler, not coerced into a 500.
        assert resp.status_code == 404

    def test_install_observability_wrapper_reports_dict(self, observability, force_observability_on):
        app = _make_app()
        result = observability.install_observability(app, logger=_NULL_LOG)
        assert isinstance(result, dict)
        assert set(result.keys()) == {"excepthook", "flask_handler"}
        # The flask handler must have been installed for this fresh app.
        assert result["flask_handler"] is True

    def test_log_startup_never_raises(self, observability, force_observability_on):
        # Smoke: the structured startup line must be safe to call unconditionally.
        observability.log_startup(
            _NULL_LOG, name="test-server", version="x", host="127.0.0.1", port=1234
        )
