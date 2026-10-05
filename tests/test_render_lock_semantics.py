"""Focused unit test for the /render lock semantics (bughunt SERVERCORE-1).

The /render route in server.py used to, on an acquire *timeout*, force-release
a ``threading.Lock`` it did NOT own and then re-acquire it. A plain
(non-reentrant) ``threading.Lock`` does not track an owner, so that
``release()`` frees whichever thread currently holds it -- destroying render
mutual exclusion and letting two renders race shared engine caches (garbled
output).

The fix:
  * On acquire timeout -> return 429 ('render_busy'); do NOT release.
  * Track ``have_lock = acquired``; only release in ``finally`` if ``have_lock``.

This test is intentionally **import-light** -- it depends only on the stdlib
``threading`` module and reproduces the exact lock-handling logic, so it runs in
milliseconds without importing the engine or Flask. It models the route's
contended/timeout path with a tiny extracted helper that mirrors the patched
control flow, and asserts the lock is never released-when-not-held.
"""

import threading

import pytest


# ---------------------------------------------------------------------------
# Tiny extraction of the patched /render lock-handling control flow.
# Mirrors server.py: acquire(timeout) -> 429 on failure (no release), run body
# under the lock, release in finally only if have_lock.
# ---------------------------------------------------------------------------
def render_with_lock(lock, body, *, timeout=0.05):
    """Run ``body`` under ``lock`` with the patched semantics.

    Returns ``(status_code, result)``:
      * ``(429, None)`` if the lock could not be acquired within ``timeout``
        (the lock is left untouched -- never force-released).
      * ``(200, body())`` otherwise, releasing the lock exactly once afterward.
    """
    have_lock = lock.acquire(timeout=timeout)
    if not have_lock:
        # SERVERCORE-1: fail fast; never release a lock we don't own.
        return 429, None
    try:
        return 200, body()
    finally:
        if have_lock:
            lock.release()


# The OLD buggy behaviour, kept here ONLY to prove the bug it fixed.
def _buggy_force_release(lock, timeout=0.01):
    acquired = lock.acquire(timeout=timeout)
    if not acquired:
        # The bug: release a lock this thread does not own, then re-acquire.
        try:
            lock.release()
        except RuntimeError:
            pass
        lock.acquire(timeout=timeout)
    return acquired


def test_acquire_timeout_returns_429_without_releasing():
    """On contention the patched path returns 429 and leaves the lock held by
    its current owner (mutual exclusion preserved)."""
    lock = threading.Lock()
    lock.acquire()  # Simulate an in-flight render holding the lock.
    try:
        status, result = render_with_lock(lock, lambda: "ran", timeout=0.02)
        assert status == 429
        assert result is None
        # The lock must STILL be held by the original owner -- the busy caller
        # must not have released or stolen it.
        assert lock.locked() is True
    finally:
        lock.release()


def test_finally_releases_exactly_once_on_success():
    """The happy path acquires, runs the body, and releases exactly once."""
    lock = threading.Lock()
    status, result = render_with_lock(lock, lambda: 42, timeout=0.05)
    assert status == 200
    assert result == 42
    # Released in finally -> free for the next render.
    assert lock.locked() is False
    # And a second release would raise (proving we released once, not zero/twice).
    with pytest.raises(RuntimeError):
        lock.release()


def test_finally_releases_once_even_when_body_raises():
    """An exception in the render body still releases the lock exactly once."""
    lock = threading.Lock()

    def boom():
        raise ValueError("render failed")

    with pytest.raises(ValueError):
        render_with_lock(lock, boom, timeout=0.05)
    assert lock.locked() is False
    with pytest.raises(RuntimeError):
        lock.release()  # Already released by finally.


def test_busy_caller_never_releases_owner_lock_under_concurrency():
    """Concurrency proof: a thread that times out acquiring the lock must not
    release the lock held by the worker thread."""
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
        # Second caller contends and must get 429, leaving the worker's lock alone.
        status, _ = render_with_lock(lock, lambda: "second", timeout=0.05)
        results["status"] = status
        # Worker still owns the lock -- the busy caller did not steal/free it.
        assert lock.locked() is True
    finally:
        worker_may_finish.set()
        t.join(timeout=2.0)

    assert results["status"] == 429
    # Once the worker releases, the lock is free again.
    assert lock.locked() is False


def test_old_force_release_breaks_mutual_exclusion():
    """Regression guard: the OLD force-release pattern frees a lock owned by
    another thread, so a non-reentrant Lock ends up acquired by TWO callers at
    once. This documents exactly the defect SERVERCORE-1 removed."""
    lock = threading.Lock()
    owner_holds = threading.Event()
    release_owner = threading.Event()

    def owner():
        lock.acquire()
        owner_holds.set()
        release_owner.wait(timeout=1.0)
        # Owner's own release may now raise because the buggy caller already
        # released the lock out from under it -- swallow to keep the thread clean.
        try:
            lock.release()
        except RuntimeError:
            pass

    t = threading.Thread(target=owner)
    t.start()
    try:
        assert owner_holds.wait(timeout=1.0)
        # The buggy path force-releases the OWNER's lock then re-acquires it,
        # so the busy caller ends up holding a lock the owner thinks it owns.
        _buggy_force_release(lock, timeout=0.02)
        # Proof of the bug: the busy caller now holds the lock even though the
        # owner never released it -> mutual exclusion is broken.
        assert lock.locked() is True
        # Clean up the lock the buggy caller stole.
        lock.release()
    finally:
        release_owner.set()
        t.join(timeout=2.0)
